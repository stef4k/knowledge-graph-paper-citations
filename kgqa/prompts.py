"""Step 3: the prompt that turns a question into SPARQL.

Run with:  python -m kgqa.prompts   (prints the exact system prompt)
"""

import json
import sys

from kgqa.graph import shorten_iri

INSTRUCTIONS = """\
You translate questions about a research-publications knowledge graph into SPARQL 1.1 queries.

Reply with a JSON object: {"answerable": true or false, "sparql": "<query>" or null, "reason": "<one short sentence>"}.

Rules:
1. Write exactly one SELECT query. Never use INSERT, DELETE, LOAD, CLEAR, CONSTRUCT, ASK or DESCRIBE.
2. Start the query with PREFIX lines and use the sdm: prefix for every class and property.
3. Use only the classes and properties listed in the schema below. Never invent new ones.
4. If the graph has no data for the question, set "answerable" to false and "sparql" to null,
   and say what is missing in "reason". Do not write an approximate query instead.
5. Add LIMIT 100, unless the question asks for a count or for a complete ranking.

Facts about the data:
- Every resource has rdf:type triples for its class and all superclasses
  (for example, every sdm:Reviewer is also an sdm:Author and an sdm:Person).
- Resource IRIs are opaque IDs. Find things through their literal values (names, titles), never by guessing an IRI.
- Person names are not unique. Group and count by the person resource, not by the name.
- Literal values are stored exactly as in the example values below (same spelling and case)."""

# Worked examples. These questions must NOT appear in the test set (kgqa/eval/questions.yaml).
EXAMPLES = [
    {
        "question": "List the titles of papers about the keyword 'blockchain'.",
        "answer": {
            "answerable": True,
            "sparql": (
                "PREFIX sdm: <http://sdm_upc.org/ontology/>\n"
                "SELECT ?title WHERE {\n"
                "  ?paper sdm:is_about ?keyword ;\n"
                "         sdm:title ?title .\n"
                '  ?keyword sdm:keyword_name "blockchain" .\n'
                "}\n"
                "LIMIT 100"
            ),
            "reason": "Papers are linked to keywords with sdm:is_about.",
        },
    },
    {
        "question": "Which 5 journals have the most volumes?",
        "answer": {
            "answerable": True,
            "sparql": (
                "PREFIX sdm: <http://sdm_upc.org/ontology/>\n"
                "SELECT ?journal_name (COUNT(?volume) AS ?volumes) WHERE {\n"
                "  ?volume sdm:is_volume_of ?journal .\n"
                "  ?journal sdm:journal_name ?journal_name .\n"
                "}\n"
                "GROUP BY ?journal ?journal_name\n"
                "ORDER BY DESC(?volumes)\n"
                "LIMIT 5"
            ),
            "reason": "Volumes point to their journal with sdm:is_volume_of; group by the journal resource.",
        },
    },
    {
        "question": "In which cities were editions of workshops held?",
        "answer": {
            "answerable": True,
            "sparql": (
                "PREFIX sdm: <http://sdm_upc.org/ontology/>\n"
                "SELECT DISTINCT ?city WHERE {\n"
                "  ?conference sdm:is_workshop true .\n"
                "  ?edition sdm:is_edition_of_conf ?conference ;\n"
                "           sdm:conference_city ?city .\n"
                "}\n"
                "LIMIT 100"
            ),
            "reason": "Workshops are conferences with sdm:is_workshop true; their editions have a city.",
        },
    },
    {
        "question": "What is the email address of the editor of the journal 'Bioinformatics'?",
        "answer": {
            "answerable": False,
            "sparql": None,
            "reason": "The graph stores only a name and an ID for persons, no email addresses.",
        },
    },
]


def sparql_system_prompt(schema: str, use_examples: bool = True) -> str:
    """Instructions + schema (+ worked examples). The question goes in the user message."""
    parts = [INSTRUCTIONS, "Schema:\n" + schema]
    if use_examples:
        shown = [f"Question: {ex['question']}\n{json.dumps(ex['answer'], indent=2)}" for ex in EXAMPLES]
        parts.append("Examples:\n\n" + "\n\n".join(shown))
    return "\n\n".join(parts)


def sparql_user_prompt(question: str) -> str:
    return f"Question: {question}"


def sparql_retry_prompt(question: str, previous_reply: str, error: str) -> str:
    """The single retry: same system prompt, plus the failed reply and its error message."""
    return (
        f"Question: {question}\n\n"
        f"Your previous reply was:\n{previous_reply}\n\n"
        f"It failed with this error:\n{error}\n\n"
        "Return a corrected JSON reply."
    )


# Step 5: writing the answer from the result rows.
ANSWER_INSTRUCTIONS = """\
You answer a question about a research-publications knowledge graph, using only the result rows
of a SPARQL query that was run on that graph.

Rules:
1. Use only the rows given. Do not add facts, names or numbers from your own knowledge.
2. If the rows do not answer the question, say so.
3. If only part of the rows is shown, say that the answer is based on the rows shown.
4. Keep it short: one to four sentences, or a short list.
5. Copy names, titles and numbers exactly as they appear in the rows."""

ANSWER_MAX_ROWS = 50  # rows shown to the model; the total count is always given


def answer_user_prompt(question: str, sparql: str, columns: list[str], rows: list[tuple], truncated: bool) -> str:
    total = f"more than {len(rows)}" if truncated else str(len(rows))
    shown = rows[:ANSWER_MAX_ROWS]
    header = f"{total} rows" + (f", showing the first {len(shown)}" if len(shown) < len(rows) or truncated else "")
    table = "\n".join(" | ".join("" if v is None else shorten_iri(v) for v in row) for row in shown)
    return (
        f"Question: {question}\n\n"
        f"SPARQL query:\n{sparql}\n\n"
        f"Result ({header}):\n{' | '.join(columns)}\n{table}"
    )


if __name__ == "__main__":
    from kgqa.graph import load_store
    from kgqa.schema import build_schema_text

    sys.stdout.reconfigure(encoding="utf-8")
    print(sparql_system_prompt(build_schema_text(load_store())))
