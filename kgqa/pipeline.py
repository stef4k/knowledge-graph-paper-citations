"""The question-answering pipeline: question -> SPARQL -> validate -> run -> answer."""

import json
import re
from dataclasses import dataclass, field

from kgqa.graph import QueryRunner, QueryTimeout, load_store
from kgqa.llm import LLMResponse, LoggedClient, make_client
from kgqa.prompts import (
    ANSWER_INSTRUCTIONS,
    answer_user_prompt,
    sparql_retry_prompt,
    sparql_system_prompt,
    sparql_user_prompt,
)
from kgqa.schema import build_schema_text, load_tbox, schema_terms
from kgqa.validate import validate_query

# JSON schema the model's reply must follow (enforced by the provider's structured-output mode).
SPARQL_REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "sparql": {"type": ["string", "null"]},
        "reason": {"type": "string"},
    },
    "required": ["answerable", "sparql", "reason"],
}

# Failures that are sent back to the model for the retry: bad JSON or failed validation
# (ValueError), pyoxigraph parse/evaluation errors (SyntaxError/RuntimeError), and timeouts.
QUERY_FAILURES = (ValueError, SyntaxError, RuntimeError, QueryTimeout)


@dataclass(frozen=True)
class Config:
    name: str
    use_examples: bool
    validate_and_retry: bool


CONFIGS = {
    "A": Config("A", use_examples=False, validate_and_retry=False),
    "B": Config("B", use_examples=True, validate_and_retry=False),
    "C": Config("C", use_examples=True, validate_and_retry=True),
}


@dataclass
class SparqlDraft:
    answerable: bool
    sparql: str | None
    reason: str


@dataclass
class Result:
    question: str
    config: str
    answerable: bool | None = None  # None: the model never gave a usable reply
    sparql: str | None = None
    reason: str = ""
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    truncated: bool = False
    answer: str | None = None
    error: str | None = None  # set when no query could be run successfully
    retries: int = 0
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def track(self, response: LLMResponse) -> None:
        self.llm_calls += 1
        self.input_tokens += response.input_tokens or 0
        self.output_tokens += response.output_tokens or 0


def parse_sparql_reply(text: str) -> SparqlDraft:
    """Parse the model's JSON reply; raises ValueError if it is malformed."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Reply is not valid JSON: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("answerable"), bool):
        raise ValueError(f"Reply has no boolean 'answerable' field: {text[:200]}")
    sparql = data.get("sparql") or None
    if data["answerable"] and not sparql:
        raise ValueError("Reply says answerable=true but contains no SPARQL query.")
    return SparqlDraft(data["answerable"], sparql, str(data.get("reason", "")))


class Pipeline:
    """Holds what every question needs: schema text, known terms, LLM client and query runner."""

    def __init__(self, client: LoggedClient | None = None, runner: QueryRunner | None = None):
        self.store = load_store()  # for trusted queries only (schema examples, gold queries)
        self.schema = build_schema_text(self.store)
        self.terms = schema_terms(load_tbox())
        self.client = client or make_client()
        self.runner = runner or QueryRunner()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.runner.close()

    def ask(self, question: str, config: Config = CONFIGS["C"], with_answer: bool = True) -> Result:
        result = Result(question, config.name)
        system = sparql_system_prompt(self.schema, config.use_examples)
        user = sparql_user_prompt(question)
        attempts = 2 if config.validate_and_retry else 1

        for attempt in range(attempts):
            result.retries = attempt
            response = self.client.complete(system, user, SPARQL_REPLY_SCHEMA, step="sparql" if attempt == 0 else "sparql_retry")
            result.track(response)
            try:
                draft = parse_sparql_reply(response.text)
                result.answerable, result.sparql, result.reason = draft.answerable, draft.sparql, draft.reason
                if not draft.answerable:
                    result.error = None
                    result.answer = f"This graph cannot answer the question: {draft.reason}"
                    return result
                if config.validate_and_retry:
                    validate_query(draft.sparql, self.terms)
                result.columns, result.rows, result.truncated = self.runner.run(draft.sparql)
                if not re.search(r"\bORDER\s+BY\b", draft.sparql, re.IGNORECASE):
                    # The engine returns unordered results in a different order on each run;
                    # sorting keeps the output and the answer prompt (and so the cache) reproducible.
                    result.rows.sort(key=lambda row: tuple("" if v is None else str(v) for v in row))
                result.error = None
                break
            except QUERY_FAILURES as error:
                result.error = f"{type(error).__name__}: {error}"
                user = sparql_retry_prompt(question, response.text, result.error)

        if result.error is None and with_answer:
            result.answer = self.write_answer(result)
        return result

    def write_answer(self, result: Result) -> str:
        """Step 5: a second LLM call that may use only the returned rows."""
        if not result.rows:
            # No call needed, and no chance for the model to guess.
            return "The query returned no rows, so the graph gives no answer to this question."
        prompt = answer_user_prompt(result.question, result.sparql, result.columns, result.rows, result.truncated)
        response = self.client.complete(ANSWER_INSTRUCTIONS, prompt, step="answer")
        result.track(response)
        return response.text.strip()
