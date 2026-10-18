import pytest

from kgqa.pipeline import parse_sparql_reply


def test_parses_an_answerable_reply():
    draft = parse_sparql_reply('{"answerable": true, "sparql": "SELECT ?x WHERE {}", "reason": "ok"}')
    assert draft.answerable and draft.sparql == "SELECT ?x WHERE {}"


def test_parses_an_unanswerable_reply():
    draft = parse_sparql_reply('{"answerable": false, "sparql": null, "reason": "no funding data"}')
    assert not draft.answerable and draft.sparql is None and draft.reason == "no funding data"


@pytest.mark.parametrize("text", [
    "not json at all",
    '{"sparql": "SELECT ?x WHERE {}"}',  # no answerable field
    '{"answerable": true, "sparql": null, "reason": "?"}',  # answerable but no query
])
def test_rejects_unusable_replies(text):
    with pytest.raises(ValueError):
        parse_sparql_reply(text)
