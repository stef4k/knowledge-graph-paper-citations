import rdflib

from kgqa.schema import describe_tbox, load_tbox, schema_terms, schema_text

TINY_TBOX = """
@prefix sdm: <http://sdm_upc.org/ontology/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

sdm:Person a rdfs:Class .
sdm:Author a rdfs:Class ; rdfs:subClassOf sdm:Person .
sdm:Paper a rdfs:Class .
sdm:is_written a rdf:Property ; rdfs:domain sdm:Paper ; rdfs:range sdm:Author .
sdm:is_corresponding_author a rdf:Property ; rdfs:domain sdm:Paper ; rdfs:range sdm:Author ;
    rdfs:subPropertyOf sdm:is_written .
sdm:title a rdf:Property ; rdfs:domain sdm:Paper ; rdfs:range xsd:string .
"""


def tiny_tbox() -> rdflib.Graph:
    graph = rdflib.Graph()
    graph.parse(data=TINY_TBOX, format="turtle")
    return graph


def test_classes_show_their_superclass():
    lines = describe_tbox(tiny_tbox()).splitlines()
    assert "  sdm:Author  (subclass of sdm:Person)" in lines
    assert "  sdm:Paper" in lines  # no superclass, so nothing after the name


def test_properties_are_written_as_domain_property_range():
    lines = describe_tbox(tiny_tbox()).splitlines()
    assert "  sdm:Paper --sdm:is_written--> sdm:Author" in lines
    assert "  sdm:Paper --sdm:is_corresponding_author--> sdm:Author  (sub-property of sdm:is_written)" in lines


def test_literal_properties_are_listed_separately_with_their_datatype():
    object_part, literal_part = describe_tbox(tiny_tbox()).split("Literal properties")
    assert "sdm:Paper --sdm:title--> xsd:string" in literal_part
    assert "sdm:title" not in object_part


def test_schema_text_has_prefix_and_example_values():
    text = schema_text(tiny_tbox(), {"sdm:title": ["First title", "Second title"]})
    assert text.startswith("PREFIX sdm: <http://sdm_upc.org/ontology/>")
    assert '  sdm:title: "First title", "Second title"' in text.splitlines()


def test_schema_terms_of_the_real_tbox():
    terms = schema_terms(load_tbox())
    assert len(terms) == 13 + 27  # classes + properties
    assert {"sdm:Paper", "sdm:Reviewer", "sdm:is_written", "sdm:keyword_name"} <= terms
