"""Pipeline control flow with a fake LLM that returns scripted replies (no API calls)."""

import json

import pytest

from kgqa.llm import LLMResponse
from kgqa.pipeline import CONFIGS, Pipeline

P = "PREFIX sdm: <http://sdm_upc.org/ontology/>\n"
BAD_QUERY = P + "SELECT ?a WHERE { ?p sdm:affiliation ?a }"  # sdm:affiliation does not exist
GOOD_QUERY = P + "SELECT (COUNT(?p) AS ?n) WHERE { ?p a sdm:Paper }"
EMPTY_QUERY = P + 'SELECT ?p WHERE { ?p sdm:title "No paper has this title" }'


def reply(sparql=None, answerable=True) -> str:
    return json.dumps({"answerable": answerable, "sparql": sparql, "reason": "test"})


class FakeClient:
    model = "fake"

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.prompts = []  # (step, user prompt) of every call

    def complete(self, system, user, json_schema=None, step=""):
        self.prompts.append((step, user))
        return LLMResponse(self.replies.pop(0), input_tokens=10, output_tokens=5, latency_s=0.0)


@pytest.fixture(scope="module")
def pipeline():
    with Pipeline(client=FakeClient([])) as pipeline:
        yield pipeline


def ask(pipeline, replies, config="C"):
    pipeline.client = FakeClient(replies)
    return pipeline.ask("How many papers are there?", CONFIGS[config])


def test_config_c_retries_once_with_the_error_message(pipeline):
    result = ask(pipeline, [reply(BAD_QUERY), reply(GOOD_QUERY), "There are 8642 papers."])
    assert result.error is None and result.retries == 1
    assert result.rows == [(8642,)]
    step, retry_prompt = pipeline.client.prompts[1]
    assert step == "sparql_retry" and "sdm:affiliation" in retry_prompt


def test_config_c_gives_up_after_one_retry(pipeline):
    result = ask(pipeline, [reply(BAD_QUERY), reply(BAD_QUERY)])
    assert result.retries == 1 and "Unknown terms" in result.error
    assert result.answer is None


def test_config_b_has_no_validation_and_no_retry(pipeline):
    # The unknown term is not caught before running; the query just returns no rows.
    result = ask(pipeline, [reply(BAD_QUERY)], config="B")
    assert result.retries == 0 and result.error is None and result.rows == []
    assert len(pipeline.client.prompts) == 1  # empty result: no answer call either


def test_unanswerable_reply_runs_no_query(pipeline):
    result = ask(pipeline, [reply(answerable=False)])
    assert result.answerable is False and result.sparql is None
    assert result.answer.startswith("This graph cannot answer")


def test_empty_result_is_answered_without_an_llm_call(pipeline):
    result = ask(pipeline, [reply(EMPTY_QUERY)])
    assert result.rows == [] and "no rows" in result.answer
    assert [step for step, _ in pipeline.client.prompts] == ["sparql"]
