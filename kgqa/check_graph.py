"""Step 1 sanity check: build/load the closure and compare with the original report.

Run with:  python -m kgqa.check_graph
"""

import sys
import time

import pyoxigraph as ox

from kgqa.config import ABOX_PATH, CLOSURE_PATH, QUERIES_DIR, TBOX_PATH
from kgqa.graph import build_closure, load_store, run_select, shorten_iri

# Instance counts reported in the original project (GraphDB, RDFS-optimized ruleset).
REPORT_CLASS_COUNTS = {
    "Paper": 8642, "Author": 19636, "Person": 20443, "Reviewer": 14348,
    "Review": 25926, "Keyword": 225, "Conference": 119, "ConferenceEdition": 398,
    "Journal": 688, "JournalVolume": 2541, "Coordinator": 807,
    "ConferenceChair": 119, "JournalEditor": 688,
}
REPORT_TOTALS = {"explicit": 277_811, "inferred": 103_321, "total": 381_132}


def print_table(variables: list[str], rows: list[tuple], max_rows: int = 80) -> None:
    print("  " + " | ".join(variables))
    for row in rows[:max_rows]:
        print("  " + " | ".join(shorten_iri(v) for v in row))
    if len(rows) > max_rows:
        print(f"  ... ({len(rows) - max_rows} more rows)")


def count_triples(store: ox.Store) -> int:
    _, rows = run_select(store, "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
    return rows[0][0]


def main() -> None:
    # Some titles/keywords are non-ASCII (e.g. "δg"); the Windows console default (cp1252) can't print them.
    sys.stdout.reconfigure(encoding="utf-8")
    if not CLOSURE_PATH.exists():
        print(f"No cache at {CLOSURE_PATH}; computing RDFS closure with owlrl ...")
        start = time.perf_counter()
        build_closure()
        print(f"  done in {time.perf_counter() - start:.1f}s (parse + reasoning + filtering + writing)")
    stats_path = CLOSURE_PATH.with_suffix(".stats.json")
    if stats_path.exists():
        print("\n== Closure build stats (from cache) ==")
        print(stats_path.read_text(encoding="utf-8"))

    # Explicit triples: load the original Turtle files into a separate store.
    explicit_store = ox.Store()
    for path in (TBOX_PATH, ABOX_PATH):
        explicit_store.load(path=str(path), format=ox.RdfFormat.TURTLE)
    n_explicit = count_triples(explicit_store)

    start = time.perf_counter()
    store = load_store()
    print(f"\nLoaded closure into pyoxigraph in {time.perf_counter() - start:.1f}s")
    n_total = count_triples(store)

    print("\n== Triple counts (ours vs report) ==")
    ours = {"explicit": n_explicit, "inferred": n_total - n_explicit, "total": n_total}
    for key, expected in REPORT_TOTALS.items():
        print(f"  {key:9s} ours={ours[key]:>8,}  report={expected:>8,}  diff={ours[key] - expected:+,}")

    print("\n== Instances per class (queries/class_instances.txt) ==")
    _, rows = run_select(store, (QUERIES_DIR / "class_instances.txt").read_text(encoding="utf-8"))
    ours_by_class = {shorten_iri(cls).removeprefix("sdm:"): n for cls, n in rows}
    all_ok = True
    for cls, expected in REPORT_CLASS_COUNTS.items():
        got = ours_by_class.get(cls, 0)
        flag = "ok" if got == expected else "MISMATCH"
        all_ok &= got == expected
        print(f"  {cls:18s} ours={got:>6}  report={expected:>6}  {flag}")
    extra = set(ours_by_class) - set(REPORT_CLASS_COUNTS)
    if extra:
        print(f"  classes not in report: {sorted(extra)}")
    print(f"  all class counts match: {all_ok}")

    for name in ("query1.txt", "query2.txt", "query3.txt"):
        sparql = (QUERIES_DIR / name).read_text(encoding="utf-8")
        start = time.perf_counter()
        variables, rows = run_select(store, sparql)
        elapsed = time.perf_counter() - start
        print(f"\n== {name}: {sparql.splitlines()[0].lstrip('# ')} ==")
        print(f"  {len(rows)} rows in {elapsed * 1000:.0f} ms")
        print_table(variables, rows)


if __name__ == "__main__":
    main()
