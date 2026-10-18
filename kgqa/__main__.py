"""Command line.

  python -m kgqa ask "Which 3 keywords have the most papers?" [--config A|B|C]
  python -m kgqa gold [--id L1]     run the gold queries of the test set (for checking them)
  python -m kgqa eval [--configs A B C] [--no-answer]
"""

import argparse
import sys
import time

from kgqa.evaluate import RESULTS_DIR, load_questions, run_evaluation, write_reports
from kgqa.graph import load_store, run_select, shorten_iri
from kgqa.pipeline import CONFIGS, Pipeline, Result

SHOW_ROWS = 20


def print_rows(columns: list[str], rows: list[tuple], limit: int | None = SHOW_ROWS) -> None:
    """Print rows as a simple table; limit=None prints all of them."""
    print(f"Rows: {len(rows)}   columns: {', '.join(columns)}")
    for row in rows[:limit]:
        print("  " + " | ".join("" if v is None else shorten_iri(v) for v in row))
    if limit is not None and len(rows) > limit:
        print(f"  ... ({len(rows) - limit} more)")


def show_gold(item_id: str | None) -> None:
    store = load_store()
    for item in load_questions(only_verified=False):
        if item_id and item["id"] != item_id:
            continue
        print(f"\n===== {item['id']} [{item['category']}] verified={item['verified']}")
        print(f"Q: {item['question']}")
        if item["gold_sparql"] is None:
            print("Expected: answerable=false (no gold query)")
            continue
        start = time.perf_counter()
        columns, rows = run_select(store, item["gold_sparql"])
        print(f"({(time.perf_counter() - start) * 1000:.0f} ms)  ", end="")
        print_rows(columns, rows, limit=None if item_id else SHOW_ROWS)


def print_result(result: Result) -> None:
    print(f"Question:   {result.question}")
    print(f"Config:     {result.config}   answerable={result.answerable}   retries={result.retries}   "
          f"LLM calls={result.llm_calls}   tokens in/out={result.input_tokens}/{result.output_tokens}")
    if result.sparql:
        print("\nSPARQL:\n" + result.sparql)
    if result.error:
        print(f"\nERROR: {result.error}")
        return
    if result.answerable:
        print("\n" + ("(truncated) " if result.truncated else ""), end="")
        print_rows(result.columns, result.rows)
    print(f"\nAnswer: {result.answer}")


def main(argv: list[str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="python -m kgqa")
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser("ask", help="answer one question")
    ask.add_argument("question")
    ask.add_argument("--config", choices=sorted(CONFIGS), default="C",
                     help="A: schema only; B: + examples; C: + validation and retry (default)")
    gold = commands.add_parser("gold", help="run the gold queries of the test set")
    gold.add_argument("--id", help="only this item (shows all its rows)")
    evaluate = commands.add_parser("eval", help="evaluate the verified test items")
    evaluate.add_argument("--configs", nargs="+", choices=sorted(CONFIGS), default=["A", "B", "C"])
    evaluate.add_argument("--no-answer", action="store_true", help="skip the answer-writing call (not scored)")
    args = parser.parse_args(argv)

    if args.command == "ask":
        with Pipeline() as pipeline:
            print_result(pipeline.ask(args.question, CONFIGS[args.config]))
    elif args.command == "gold":
        show_gold(args.id)
    elif args.command == "eval":
        rows = run_evaluation(args.configs, with_answer=not args.no_answer)
        print("\n" + write_reports(rows, args.configs))
        print(f"\nWritten: {RESULTS_DIR / 'results.csv'}, summary.md, failures.md")


if __name__ == "__main__":
    main()
