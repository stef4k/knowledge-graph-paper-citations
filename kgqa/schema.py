"""Step 2: a compact description of the ontology for the prompt, generated from the TBox.

Run with:  python -m kgqa.schema   (prints the exact text that goes into the prompt)
"""

import sys

import pyoxigraph as ox
import rdflib
from rdflib import RDF, RDFS

from kgqa.config import SDM, TBOX_PATH
from kgqa.config import XSD_NS as XSD
from kgqa.graph import load_store, run_select

# Literal properties whose value format the model should see.
EXAMPLE_PROPERTIES = ["keyword_name", "journal_name", "conference_name", "conference_city"]


def short(term) -> str:
    return str(term).replace(SDM, "sdm:").replace(XSD, "xsd:")


def load_tbox(path=TBOX_PATH) -> rdflib.Graph:
    graph = rdflib.Graph()
    graph.parse(path)
    return graph


def schema_terms(tbox: rdflib.Graph) -> set[str]:
    """All classes and properties declared in the TBox, as 'sdm:Name' strings."""
    declared = set(tbox.subjects(RDF.type, RDFS.Class)) | set(tbox.subjects(RDF.type, RDF.Property))
    return {short(term) for term in declared if str(term).startswith(SDM)}


def describe_tbox(tbox: rdflib.Graph) -> str:
    """Classes with their superclass, then properties as `domain --property--> range`."""
    lines = ["Classes:"]
    for cls in sorted(tbox.subjects(RDF.type, RDFS.Class), key=short):
        parent = tbox.value(cls, RDFS.subClassOf)
        lines.append(f"  {short(cls)}" + (f"  (subclass of {short(parent)})" if parent else ""))

    object_lines, literal_lines = [], []
    properties = tbox.subjects(RDF.type, RDF.Property)
    for prop in sorted(properties, key=lambda p: (short(tbox.value(p, RDFS.domain)), short(p))):
        range_ = tbox.value(prop, RDFS.range)
        line = f"  {short(tbox.value(prop, RDFS.domain))} --{short(prop)}--> {short(range_)}"
        parent = tbox.value(prop, RDFS.subPropertyOf)
        if parent:
            line += f"  (sub-property of {short(parent)})"
        (literal_lines if str(range_).startswith(XSD) else object_lines).append(line)

    lines += ["", "Object properties (domain --property--> range):", *object_lines]
    lines += ["", "Literal properties (domain --property--> datatype):", *literal_lines]
    return "\n".join(lines)


def sample_values(store: ox.Store, properties=EXAMPLE_PROPERTIES, k: int = 3) -> dict[str, list[str]]:
    """k real values per property, most-linked resources first (deterministic, so prompts are stable)."""
    examples = {}
    for name in properties:
        query = f"""
            SELECT ?value (COUNT(?link) AS ?n) WHERE {{
              ?s <{SDM}{name}> ?value .
              OPTIONAL {{ ?link ?p ?s }}
            }}
            GROUP BY ?value ORDER BY DESC(?n) ?value LIMIT {k}"""
        _, rows = run_select(store, query)
        examples[f"sdm:{name}"] = [value for value, _ in rows]
    return examples


def schema_text(tbox: rdflib.Graph, examples: dict[str, list[str]]) -> str:
    lines = [f"PREFIX sdm: <{SDM}>", "", describe_tbox(tbox), "", "Example values:"]
    for prop, values in examples.items():
        lines.append(f"  {prop}: " + ", ".join(f'"{v}"' for v in values))
    return "\n".join(lines)


def build_schema_text(store: ox.Store) -> str:
    return schema_text(load_tbox(), sample_values(store))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(build_schema_text(load_store()))
