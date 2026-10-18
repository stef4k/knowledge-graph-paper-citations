"""Build the RDFS closure once, cache it, and query it with pyoxigraph."""

import json
import multiprocessing
import time
from collections import Counter
from pathlib import Path

import owlrl
import pyoxigraph as ox
import rdflib
from rdflib import RDFS

from kgqa.config import ABOX_PATH, CLOSURE_PATH, RES, SDM, TBOX_PATH
from kgqa.config import XSD_NS as XSD

INTEGER_TYPES = {XSD + "integer", XSD + "int", XSD + "long"}
FLOAT_TYPES = {XSD + "decimal", XSD + "double", XSD + "float"}


def _drop_reason(s, p, o) -> str | None:
    """Why an owlrl-inferred triple should not go into the cache (None = keep it)."""
    if isinstance(s, rdflib.Literal):
        return "literal subject (not valid RDF, e.g. \"Andrea\" a xsd:string)"
    if o == RDFS.Resource:
        return "x a / subClassOf rdfs:Resource (true for everything)"
    if isinstance(o, rdflib.Literal):
        # In this TBox, RDFS only derives rdf:type and is_written triples, whose
        # objects are IRIs. owlrl conflates "false"^^xsd:boolean with "0"^^xsd:integer
        # (Python: False == 0) and copies values between them.
        return "new literal value (owlrl bug: false == 0)"
    return None


def build_closure(out_path: Path = CLOSURE_PATH) -> dict:
    """Parse TBox + ABox, materialise the RDFS closure with owlrl, write N-Triples.

    Explicit triples are always kept; inferred triples are filtered by _drop_reason.
    Returns counts for reporting (also saved next to the cache as JSON).
    """
    graph = rdflib.Graph()
    graph.parse(TBOX_PATH)
    graph.parse(ABOX_PATH)
    explicit = set(graph)

    start = time.perf_counter()
    owlrl.DeductiveClosure(
        owlrl.RDFS_Semantics, axiomatic_triples=False, datatype_axioms=False
    ).expand(graph)
    seconds = time.perf_counter() - start
    n_after_owlrl = len(graph)

    dropped = Counter()
    for triple in set(graph) - explicit:
        reason = _drop_reason(*triple)
        if reason:
            graph.remove(triple)
            dropped[reason] += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(out_path, format="nt", encoding="utf-8")
    stats = {
        "explicit": len(explicit),
        "owlrl_added": n_after_owlrl - len(explicit),
        "dropped": dict(dropped),
        "kept_inferred": len(graph) - len(explicit),
        "written": len(graph),
        "reasoning_seconds": round(seconds, 1),
    }
    out_path.with_suffix(".stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def load_store(path: Path = CLOSURE_PATH) -> ox.Store:
    """Load the cached closure into an in-memory pyoxigraph store (builds it if missing)."""
    if not path.exists():
        build_closure(path)
    store = ox.Store()
    store.bulk_load(path=str(path), format=ox.RdfFormat.N_TRIPLES)
    return store


def to_python(term: ox.NamedNode | ox.BlankNode | ox.Literal | None):
    """Convert a pyoxigraph term to a plain Python value (IRIs stay full strings)."""
    if term is None:  # unbound variable, e.g. from OPTIONAL
        return None
    if isinstance(term, ox.Literal):
        datatype = term.datatype.value
        if datatype in INTEGER_TYPES:
            return int(term.value)
        if datatype in FLOAT_TYPES:
            return float(term.value)
        if datatype == XSD + "boolean":
            return term.value in ("true", "1")
        return term.value
    return term.value


def shorten_iri(value) -> str:
    """Display helper: full IRIs -> sdm:/res: prefixed names."""
    return str(value).replace(SDM, "sdm:").replace(RES, "res:")


def run_select(store: ox.Store, sparql: str, max_rows: int | None = None) -> tuple[list[str], list[tuple]]:
    """Run a SELECT query and return (variable names, rows of Python values), at most max_rows rows."""
    result = store.query(sparql)
    if not isinstance(result, ox.QuerySolutions):
        raise ValueError("Only SELECT queries are supported.")
    variables = [v.value for v in result.variables]
    rows = []
    for solution in result:  # pyoxigraph evaluates lazily, so stopping early saves work
        if max_rows is not None and len(rows) == max_rows:
            break
        rows.append(tuple(to_python(solution[i]) for i in range(len(variables))))
    return variables, rows


class QueryTimeout(Exception):
    pass


class QueryRunner:
    """Runs generated SELECT queries in a separate worker process with a time limit.

    pyoxigraph has no query timeout, and a Python thread cannot be stopped, so a slow
    query is stopped by terminating the worker process (a new one is started on the next call).
    Only Store.query() is ever called, which cannot modify data: the store is read-only for us.
    """

    def __init__(self, timeout_s: float = 30, max_rows: int = 10_000):
        self.timeout_s = timeout_s
        self.max_rows = max_rows
        self._pool = None

    def run(self, sparql: str) -> tuple[list[str], list[tuple], bool]:
        """Return (columns, rows, truncated). truncated=True means more than max_rows rows exist."""
        if self._pool is None:
            self._pool = multiprocessing.Pool(1, initializer=_init_worker)
        job = self._pool.apply_async(_worker_select, (sparql, self.max_rows + 1))
        try:
            columns, rows = job.get(timeout=self.timeout_s)
        except multiprocessing.TimeoutError:
            self.close()
            raise QueryTimeout(f"Query was stopped after {self.timeout_s:.0f} s.") from None
        return columns, rows[: self.max_rows], len(rows) > self.max_rows

    def close(self) -> None:
        if self._pool is not None:
            self._pool.terminate()
            self._pool = None


# Each worker process loads its own copy of the store once (in _init_worker) and reuses it.
_worker_store: ox.Store | None = None


def _init_worker() -> None:
    global _worker_store
    _worker_store = load_store()


def _worker_select(sparql: str, max_rows: int) -> tuple[list[str], list[tuple]]:
    return run_select(_worker_store, sparql, max_rows)
