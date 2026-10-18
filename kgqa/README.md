# kgqa: questions in plain English over the research-publications knowledge graph

## What it does

kgqa answers English questions about the research-publications knowledge graph in this
repository (papers, authors, citations, conferences, journals, reviews). A language model
turns the question into a SPARQL query; the query is checked and run on the graph, and a
second model call writes a short answer that may only use the returned rows. The system is
evaluated against 15 hand-checked reference queries.

## How it works

```
question
   |
   v
[1] LLM: instructions + schema (+ 4 worked examples) + question
         -> {"answerable": true/false, "sparql": "...", "reason": "..."}
   |        answerable = false  ->  "This graph cannot answer the question: <reason>"
   v
[2] validate: does it parse? is it a SELECT? does every sdm: term exist in the TBox?
   |        failure -> one retry, with the failed reply and the error message; then give up
   v
[3] run on the graph (separate worker process, 30 s timeout, at most 10,000 rows)
   |        error or timeout -> the same single retry
   v
[4] LLM: question + query + first 50 rows (+ total count) -> short answer from the rows only
   |        0 rows -> fixed sentence, no LLM call
   v
answer + SPARQL query + rows, so the user can check the answer
```

- **Graph.** `output_files/tbox.ttl` + `abox.ttl`. The ABox contains no `rdf:type` triples, so
  types only exist through RDFS inference. The RDFS closure is computed once with owlrl,
  cached as N-Triples (`kgqa/cache/closure.nt`) and loaded into pyoxigraph, an in-process
  SPARQL engine. No database server is needed.
- **Schema text.** Generated from the TBox: classes with their superclass, properties as
  `domain --property--> range`, plus three real example values for four literal properties
  (`python -m kgqa.schema` prints it).
- **Model.** Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`, Google AI Studio free tier),
  behind a small client interface; another provider is one class in `kgqa/llm.py`.

| File | Role |
|---|---|
| `graph.py` | RDFS closure + cache, pyoxigraph store, query runner with timeout |
| `schema.py` | schema text for the prompt, list of known terms |
| `prompts.py` | all prompt text, including the 4 worked examples |
| `llm.py` | Gemini client (rate limiting, retries on 429/5xx), cache + JSONL log |
| `validate.py` | pre-execution checks |
| `pipeline.py` | the steps above; configurations A/B/C |
| `compare.py`, `evaluate.py` | result comparison, evaluation, reports |
| `check_graph.py` | sanity check of the graph against the original report |
| `eval/questions.yaml` | the test set |

## How to run

No database server is needed. From the repository root, in PowerShell:

```powershell
py -3.10 -m venv kgqa\.venv                       # Python 3.10 or newer
kgqa\.venv\Scripts\python.exe -m pip install -r kgqa\requirements.txt
Copy-Item kgqa\.env.example kgqa\.env              # then put your Gemini API key in kgqa\.env
```

Commands (always from the repository root; `python` = `kgqa\.venv\Scripts\python.exe`):

```powershell
python -m kgqa.check_graph            # build/check the graph (first run ~25-35 min: owlrl reasoning; then ~4 s)
python -m kgqa.schema                 # print the schema text used in the prompt
python -m kgqa ask "Which 3 keywords have the most papers?"   # [--config A|B|C], default C
python -m kgqa gold [--id J2]         # run the reference queries of the test set
python -m kgqa eval                   # evaluate configs A, B, C -> kgqa/eval/results/
python -m pytest kgqa/tests -q        # tests (no LLM calls)
```

LLM calls are logged to `kgqa/logs/llm_calls.jsonl` and cached in `kgqa/cache/llm_responses.jsonl`;
an identical request is answered from the cache. Re-running the evaluation therefore makes no
new calls and gives the same scores (checked with repeated runs). One exception: rows that tie
in an `ORDER BY` can come back in a different order, which changes the answer prompt and causes
a new (unscored) answer call. Results without `ORDER BY` are sorted for this reason.

## Results

Model `gemini-3.5-flash-lite`, default temperature, single run (18 October 2026), 15 verified
questions: 12 answerable (3 lookup, 3 join, 3 aggregation, 3 inference) and 3 unanswerable.
The three configurations use the same model and test set:

- **A**: instructions + schema only; no examples, no validation, no retry
- **B**: A + 4 worked examples
- **C**: B + validation and one retry

| Metric | A | B | C |
|---|---|---|---|
| Correct overall | 10/15 (67%) | 13/15 (87%) | 13/15 (87%) |
| Execution accuracy (answerable items) | 7/12 (58%) | 10/12 (83%) | 10/12 (83%) |
| Valid-query rate (answerable items) | 8/12 (67%) | 11/12 (92%) | 11/12 (92%) |
| Correct refusals (unanswerable items) | 3/3 | 3/3 | 3/3 |
| Wrong refusals (answerable items) | 1/12 | 1/12 | 1/12 |
| Items that used the retry | 0 | 0 | 0 |

| Category | A | B | C |
|---|---|---|---|
| lookup | 2/3 | 3/3 | 3/3 |
| join | 3/3 | 3/3 | 3/3 |
| aggregation | 1/3 | 1/3 | 1/3 |
| inference | 1/3 | 3/3 | 3/3 |
| unanswerable | 3/3 | 3/3 | 3/3 |

Definitions: *execution accuracy* = the generated query returns the same rows as the reference
query (compared as sets; column order, variable names and extra columns are ignored; numbers
rounded to 4 decimals; top-k questions compare the top-k sets, and every top-k reference has
no tie at the cut-off). *Valid query* = the model wrote a query that parses, passes validation
and executes (validation is checked afterwards for A and B too).

What the numbers show:

- **The worked examples (A → B) fixed three items**, and all three failed for the same
  mechanical reason (failure case 3 below), not for lack of understanding.
- **Validation and retry (B → C) changed nothing on this test set.** No query written in B
  failed validation or execution, so the retry was never used. B and C send identical first
  prompts, so the response cache gave C exactly B's first replies; B vs C is therefore a paired
  comparison in which only the validation/retry step differs.
- **Abstention worked on the unanswerable items** (funding, affiliations, Google Scholar
  citations) in all configurations, but the model also refused one hard answerable question.
- **Both aggregation questions taken from the original report (A1, A2) fail in every
  configuration.**
- Cost and speed: €0 (free tier); 49 API calls for the whole A/B/C run; median call latency
  0.8 s; at most 328 output tokens per call. A run takes a few minutes because of the
  free tier's 15 requests/minute limit.

Per-item results: `eval/results/results.csv`; every failure with generated and reference
query: `eval/results/failures.md`.

## Three instructive failures

**1. A2: a valid, plausible, but wrong query (all configurations).**
"For each keyword, which paper about that keyword is cited the most? Give the 15
keyword-paper pairs with the highest citation counts." The model counted citations per
(keyword, paper) pair and took the 15 largest overall. The reference first keeps the most
cited paper *per keyword* and then ranks. The model's list contains "computervision" three
times (with three different papers) and its `LIMIT 15` cuts through a five-way tie at 17
citations. 12 of its 15 rows coincide with the reference, the query passes every check, and
the written answer is fluent. Nothing in the pipeline can detect this kind of error; only a
reference query or a person reading the SPARQL can. This is why the answer is always shown
together with the query.

**2. A1: refusing a hard but answerable question (all configurations).**
The question (report query 1) asks for average citations per publication type and year,
with an exact definition and 0 for empty combinations. The model replied `answerable: false`:
"The schema does not provide a direct way to compute ... with a default of 0." The prompt
says to refuse only when the graph has *no data*; here the model treated "hard to express"
as "not possible". A refusal is a safe failure (no wrong numbers), but it shows the trade-off
of the abstention rule: the same instruction that makes all three unanswerable questions
correct also costs coverage on difficult ones.

**3. L2, I2, I3 in config A: an undeclared prefix.**
Without examples, the model wrote `?person rdf:type sdm:Person` without a `PREFIX rdf:` line.
pyoxigraph rejects this ("Prefix not found"), so three otherwise correct queries failed,
including two of the three inference questions. With the examples (config B), the model used
the `a` shorthand or left out the unnecessary type pattern, and all three succeeded. The
validator would not have caught this (rdflib accepts the undeclared `rdf:` prefix); in
config C the execution error would have triggered the retry. So most of the A → B gain is
about query form, not about understanding the data.

## Limitations

- **Small, self-written test set.** 15 questions (3 per category), drafted with an AI
  assistant and checked by me one by one (A1 and A2, the two most complex reference queries,
  with the help of an LLM). One item is 6.7 percentage points of the total, so the numbers
  show tendencies, not precise rates. The prompt (rules and worked examples) was written
  before the test set and was not tuned on it.
- **Single run, one model.** The model runs at its default temperature (Google recommends
  1.0 for Gemini 3 models and warns that lower values can cause looping), so a new run can
  give different results. The response cache makes this run exactly reproducible. Results
  depend on the model; only one free-tier model was evaluated.
- **Strict comparison.** A result counts as correct only if it contains the same rows as the
  reference (extra columns are allowed, missing ones are not). A correct answer in a different
  shape, for example two numbers in one row instead of two rows, counts as wrong.
- **Synthetic and noisy data.** Parts of the graph are generated or come from noisy extraction:
  93% of the abstracts (8,077 of 8,642) are the text "nan"; the `is_workshop` flags and the
  keyword assignments look random (ICCV, ACL and CIKM are marked as workshops); 3 papers have
  `year_written` 0; keyword names include extraction noise ("aggregatio", "proach"); coordinator
  names are generated first names; one paper with 274 authors dominates co-author rankings.
  Answers are correct with respect to the graph, not to the real world.
- **Inference.** owlrl's RDFS closure takes 25-35 minutes once. owlrl treats `false` and `0` as
  the same literal and adds wrong triples; these are filtered out (`graph.py`). All 13 class
  counts match the original GraphDB report; the total differs by 118 schema-level triples.

## Design choices for safe use

- **Read-only.** Generated queries are only passed to pyoxigraph's `Store.query()`, which cannot
  modify data. In addition, the validator rejects anything that is not a SELECT (INSERT, DELETE,
  LOAD, CLEAR, CONSTRUCT, ASK, DESCRIBE).
- **Schema-term check.** Every IRI in the query is extracted from the parsed query; unknown
  `sdm:` classes or properties and IRIs from other namespaces are rejected before running, and
  listed in the error sent back to the model.
- **Abstention.** The model must reply `answerable: false` when the graph has no data for the
  question instead of writing an approximate query; this is measured separately.
- **Answers grounded in the returned rows.** The answer call only sees the question, the query
  and the rows, and is told not to add outside knowledge. An empty result gets a fixed sentence
  without an LLM call. The answer is always returned together with the query and the rows.
- **Resource limits.** 30 s query timeout (enforced by stopping a worker process), 10,000-row
  cap, 4,000 output tokens per LLM call, one retry at most.
- **Full logging.** Every LLM call (prompt, response, tokens, latency, cached or not) is
  appended to a JSONL log. The API key lives in `kgqa/.env`, which is git-ignored.

## Differences from the original plan

- Python 3.10 instead of 3.11 (the version installed); the code avoids 3.11-only features.
- Gemini (free tier) instead of Anthropic, because of budget; one model instead of two.
- Default temperature instead of 0 (see Limitations).
- 15 test items instead of 25-30, to keep manual verification feasible.
