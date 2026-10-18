import pytest

from kgqa.config import QUERIES_DIR
from kgqa.schema import load_tbox, schema_terms
from kgqa.validate import ValidationError, validate_query

TERMS = schema_terms(load_tbox())
P = "PREFIX sdm: <http://sdm_upc.org/ontology/>\n"


@pytest.mark.parametrize("name", ["query1.txt", "query2.txt", "query3.txt"])
def test_accepts_the_report_queries(name):
    # query1 uses the dbo: prefix for the same namespace; that must not matter.
    validate_query((QUERIES_DIR / name).read_text(encoding="utf-8"), TERMS)


def test_accepts_select_with_rdf_type_and_property_path():
    validate_query(P + "SELECT ?q WHERE { ?p a sdm:Paper ; sdm:cites+ ?q } LIMIT 5", TERMS)


@pytest.mark.parametrize("query", [
    P + 'INSERT DATA { sdm:x sdm:title "t" }',
    P + "DELETE WHERE { ?s sdm:title ?t }",
    "LOAD <http://example.org/data.ttl>",
    "CLEAR ALL",
])
def test_rejects_updates(query):
    with pytest.raises(ValidationError, match="Only SELECT"):
        validate_query(query, TERMS)


@pytest.mark.parametrize("query", [
    P + "CONSTRUCT { ?s sdm:title ?t } WHERE { ?s sdm:title ?t }",
    P + "ASK { ?s sdm:title ?t }",
    P + "DESCRIBE ?s WHERE { ?s sdm:title ?t }",
])
def test_rejects_other_query_forms(query):
    with pytest.raises(ValidationError, match="Only SELECT"):
        validate_query(query, TERMS)


def test_lists_all_unknown_terms():
    with pytest.raises(ValidationError) as info:
        validate_query(P + "SELECT ?a WHERE { ?x a sdm:University ; sdm:affiliation ?a }", TERMS)
    assert "sdm:University" in str(info.value)
    assert "sdm:affiliation" in str(info.value)


def test_finds_unknown_terms_inside_property_paths():
    with pytest.raises(ValidationError, match="sdm:cited_by"):
        validate_query(P + "SELECT ?q WHERE { ?p sdm:cites/sdm:cited_by ?q }", TERMS)


def test_rejects_iris_from_other_namespaces():
    query = "PREFIX foaf: <http://xmlns.com/foaf/0.1/>\nSELECT ?n WHERE { ?x foaf:name ?n }"
    with pytest.raises(ValidationError, match="foaf"):
        validate_query(query, TERMS)


def test_rejects_syntax_errors():
    with pytest.raises(ValidationError, match="syntax error"):
        validate_query(P + "SELECT ?x WHERE { ?x sdm:title }", TERMS)
