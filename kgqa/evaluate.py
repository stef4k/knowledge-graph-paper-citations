"""Steps 7-9: the test set, the evaluation and its reports.

Run with:  python -m kgqa eval [--configs A B C]
"""

import csv
from pathlib import Path

import yaml

from kgqa.compare import results_match
from kgqa.config import KGQA_DIR
from kgqa.graph import run_select
from kgqa.pipeline import CONFIGS, Pipeline, Result
from kgqa.validate import ValidationError, validate_query

QUESTIONS_PATH = KGQA_DIR / "eval" / "questions.yaml"
RESULTS_DIR = KGQA_DIR / "eval" / "results"
CATEGORIES = ["lookup", "join", "aggregation", "inference", "unanswerable"]
REQUIRED_FIELDS = {"id", "category", "question", "gold_sparql", "verified", "notes"}


def load_questions(path: Path = QUESTIONS_PATH, only_verified: bool = True) -> list[dict]:
    items = yaml.safe_load(path.read_text(encoding="utf-8"))
    for item in items:
        missing = REQUIRED_FIELDS - set(item)
        if missing:
            raise ValueError(f"Item {item.get('id')} is missing fields: {sorted(missing)}")
        if item["category"] not in CATEGORIES:
            raise ValueError(f"Item {item['id']} has unknown category {item['category']!r}")
        if (item["category"] == "unanswerable") != (item["gold_sparql"] is None):
            raise ValueError(f"Item {item['id']}: only unanswerable items have gold_sparql: null")
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate item ids in the test set.")
    return [item for item in items if item["verified"] is True or not only_verified]


def passes_validation(sparql: str, terms: set[str]) -> bool:
    try:
        validate_query(sparql, terms)
        return True
    except ValidationError:
        return False


def score(item: dict, result: Result, gold_rows: list[tuple] | None, terms: set[str]) -> dict:
    """One CSV row. For answerable items: valid query + result match. For unanswerable: did it refuse?"""
    answerable = gold_rows is not None
    wrote_query = result.answerable is True and result.sparql is not None
    if answerable:
        # Valid = parses, passes validation and executes (validation is checked here for A and B too).
        valid = wrote_query and result.error is None and passes_validation(result.sparql, terms)
        correct = wrote_query and result.error is None and not result.truncated and results_match(gold_rows, result.rows)
    else:
        valid = None
        correct = result.answerable is False
    return {
        "config": result.config,
        "id": item["id"],
        "category": item["category"],
        "correct": correct,
        "valid_query": valid,
        "expected_answerable": answerable,
        "model_answerable": result.answerable,
        "retries": result.retries,
        "gold_rows": len(gold_rows) if answerable else "",
        "model_rows": len(result.rows) if wrote_query and result.error is None else "",
        "error": result.error or "",
        "llm_calls": result.llm_calls,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "question": item["question"],
        "sparql": result.sparql or "",
        "gold_sparql": item["gold_sparql"] or "",
        "reason": result.reason,
        "answer": result.answer or "",
    }


def problem(row: dict) -> str:
    """Automatic one-line description of why an item failed."""
    if not row["expected_answerable"]:
        return "Should have refused (no data in the graph), but wrote a query."
    if row["model_answerable"] is False:
        return f"Wrongly refused: {row['reason']}"
    if row["error"]:
        return "Failed: " + " ".join(row["error"].split())[:160]  # one line, even for multi-line errors
    return f"Wrong result: {row['model_rows']} rows, gold has {row['gold_rows']} rows."


def run_evaluation(config_names: list[str], with_answer: bool = True) -> list[dict]:
    items = load_questions()
    if not items:
        raise SystemExit("No verified items in kgqa/eval/questions.yaml (set verified: true after checking).")
    rows = []
    with Pipeline() as pipeline:
        gold = {item["id"]: run_select(pipeline.store, item["gold_sparql"])[1] if item["gold_sparql"] else None
                for item in items}
        for name in config_names:
            for item in items:
                result = pipeline.ask(item["question"], CONFIGS[name], with_answer=with_answer)
                row = score(item, result, gold[item["id"]], pipeline.terms)
                rows.append(row)
                print(f"[{name}] {item['id']:<3} {'correct' if row['correct'] else 'WRONG  '}  "
                      f"retries={row['retries']}  calls={row['llm_calls']}")
    return rows


def _pct(count: int, total: int) -> str:
    return f"{count}/{total} ({100 * count / total:.0f}%)" if total else "-"


def summary_markdown(rows: list[dict], config_names: list[str]) -> str:
    def metrics(config_rows):
        answerable = [r for r in config_rows if r["expected_answerable"]]
        unanswerable = [r for r in config_rows if not r["expected_answerable"]]
        return {
            "Correct overall": _pct(sum(r["correct"] for r in config_rows), len(config_rows)),
            "Execution accuracy (answerable items)": _pct(sum(r["correct"] for r in answerable), len(answerable)),
            "Valid-query rate (answerable items)": _pct(sum(bool(r["valid_query"]) for r in answerable), len(answerable)),
            "Correct refusals (unanswerable items)": _pct(sum(r["correct"] for r in unanswerable), len(unanswerable)),
            "Wrong refusals (answerable items)": _pct(sum(r["model_answerable"] is False for r in answerable), len(answerable)),
            "Items that used the retry": str(sum(r["retries"] for r in config_rows)),
            "LLM calls": str(sum(r["llm_calls"] for r in config_rows)),
            "Tokens in / out": f"{sum(r['input_tokens'] for r in config_rows)} / {sum(r['output_tokens'] for r in config_rows)}",
        }

    by_config = {name: [r for r in rows if r["config"] == name] for name in config_names}
    table = {name: metrics(config_rows) for name, config_rows in by_config.items()}
    lines = ["| Metric | " + " | ".join(config_names) + " |", "|---|" + "---|" * len(config_names)]
    for metric in next(iter(table.values())):
        lines.append(f"| {metric} | " + " | ".join(table[name][metric] for name in config_names) + " |")

    lines += ["", "Correct items per category:", "",
              "| Category | " + " | ".join(config_names) + " |", "|---|" + "---|" * len(config_names)]
    for category in CATEGORIES:
        cells = []
        for name in config_names:
            in_category = [r for r in by_config[name] if r["category"] == category]
            cells.append(f"{sum(r['correct'] for r in in_category)}/{len(in_category)}" if in_category else "-")
        lines.append(f"| {category} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def failures_markdown(rows: list[dict]) -> str:
    lines = ["# Failed items", "", "Edit the 'Diagnosis' lines. (Re-running the evaluation overwrites this file.)", ""]
    for row in rows:
        if row["correct"]:
            continue
        lines += [
            f"## Config {row['config']} / {row['id']} ({row['category']})",
            "",
            f"**Question:** {row['question']}",
            "",
            f"- Problem (automatic): {problem(row)}",
            "- Diagnosis: ...",
            "",
            "Generated query:",
            "```sparql",
            row["sparql"] or "(none)",
            "```",
            "Gold query:",
            "```sparql",
            (row["gold_sparql"] or "(none: the expected reply is answerable=false)").rstrip(),
            "```",
            "",
        ]
    return "\n".join(lines)


def write_reports(rows: list[dict], config_names: list[str], out_dir: Path = RESULTS_DIR) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "results.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summary_markdown(rows, config_names)
    (out_dir / "summary.md").write_text(summary + "\n", encoding="utf-8")
    (out_dir / "failures.md").write_text(failures_markdown(rows), encoding="utf-8")
    return summary
