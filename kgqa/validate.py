"""Step 4: check a generated query before it runs.

Checks: it parses, it is a SELECT, and every ontology term it uses exists in the TBox.
Parsing uses rdflib. rdflib is slightly more lenient than pyoxigraph (e.g. it knows the xsd:
prefix without a PREFIX line); such queries pass here and fail at execution, which also
counts as a failure and triggers the retry.
"""

from rdflib import URIRef
from rdflib.paths import Path
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parser import parseUpdate

from kgqa.config import RDF_NS, RDFS_NS, RES, SDM, XSD_NS

# IRIs outside these namespaces cannot match anything in our graph.
ALLOWED_NAMESPACES = (SDM, RES, RDF_NS, RDFS_NS, XSD_NS)


class ValidationError(ValueError):
    pass


def validate_query(sparql: str, known_terms: set[str]) -> None:
    """Raise ValidationError if the query is invalid. known_terms are 'sdm:Name' strings."""
    try:
        query = prepareQuery(sparql)
    except Exception as error:  # rdflib raises several exception types for bad syntax
        if _is_update(sparql):
            raise ValidationError("Only SELECT queries are allowed, but this is an update (e.g. INSERT/DELETE/LOAD/CLEAR).") from None
        raise ValidationError(f"SPARQL syntax error: {error}") from None

    if query.algebra.name != "SelectQuery":
        kind = query.algebra.name.removesuffix("Query").upper()
        raise ValidationError(f"Only SELECT queries are allowed, not {kind}.")

    unknown = sorted(_short(iri) for iri in _iris(query.algebra) if not _is_known(iri, known_terms))
    if unknown:
        raise ValidationError(f"Unknown terms (not in the schema): {', '.join(unknown)}")


def _is_update(sparql: str) -> bool:
    try:
        parseUpdate(sparql)
        return True
    except Exception:
        return False


def _is_known(iri: str, known_terms: set[str]) -> bool:
    if iri.startswith(SDM):
        return _short(iri) in known_terms
    return iri.startswith(ALLOWED_NAMESPACES)


def _short(iri: str) -> str:
    return iri.replace(SDM, "sdm:")


def _iris(node) -> set[str]:
    """All IRIs in rdflib's parsed query (a tree of dicts, lists, tuples and property paths).

    Returned as plain str: rdflib's URIRef overrides startswith() and mishandles a tuple of prefixes.
    """
    if isinstance(node, URIRef):
        return {str(node)}
    if isinstance(node, dict):  # rdflib's CompValue nodes are dicts
        children = node.values()
    elif isinstance(node, (list, tuple, set)):
        children = node
    elif isinstance(node, Path):  # property paths such as sdm:cites+ or sdm:a/sdm:b
        children = vars(node).values()
    else:
        return set()
    found = set()
    for child in children:
        found |= _iris(child)
    return found
