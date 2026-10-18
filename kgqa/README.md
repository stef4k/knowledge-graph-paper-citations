# kgqa: questions in plain English over the research-publications knowledge graph

## What it does

kgqa answers English questions about the research-publications knowledge graph in this
repository (papers, authors, citations, conferences, journals, reviews). The language model
is Google's **Gemini 3.5 Flash Lite** (`gemini-3.5-flash-lite`, free tier of the Gemini API):
it turns the question into a SPARQL query, the query is checked and run on the graph, and a
second call to the same model writes a short answer that may only use the returned rows.
The system is evaluated against 15 hand-checked reference queries.

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

- **Small test set:** 15 questions, drafted with an AI assistant and checked by me (A1 and A2
  with an LLM's help). One item = 6.7 points, so the numbers show tendencies. The prompt was
  written before the test set and not tuned on it.
- **One model, one run** at default temperature (Google advises 1.0 for Gemini 3); new runs can
  differ, but the cache makes this run reproducible.
- **Strict comparison:** a correct answer in another shape (e.g. two numbers in one row instead
  of two rows) counts as wrong.
- **Noisy, partly synthetic data:** 93% of abstracts are the text "nan"; `is_workshop` flags and
  keyword assignments look random (ICCV, ACL, CIKM are "workshops"); 3 papers have year 0;
  noisy keyword names; generated coordinator names; one 274-author paper dominates co-author
  rankings. Answers are correct for the graph, not for the real world.
- **Inference:** owlrl needs 25-35 min once and treats `false` as `0`, adding wrong triples
  (filtered out). Class counts match the GraphDB report; the total differs by 118 schema-level
  triples.

## Design choices for safe use

- **Read-only:** generated queries only go to `Store.query()`, which cannot modify data; the
  validator also rejects every non-SELECT form.
- **Schema check:** every IRI in the parsed query must be a known `sdm:` term or come from the
  rdf, rdfs, xsd or resource namespaces; unknown terms are listed in the error sent to the retry.
- **Abstention:** the model must reply `answerable: false` instead of approximating; measured
  separately.
- **Grounded answers:** the answer call sees only question, query and rows; empty results get
  a fixed sentence without an LLM call; query and rows are always returned with the answer.
- **Limits:** 30 s timeout (killable worker process), 10,000 rows, 4,000 output tokens per call,
  one retry.
- **Logging:** every call (prompt, response, tokens, latency, cached?) in a JSONL log; API key
  in the git-ignored `kgqa/.env`.

## Differences from the original plan

Python 3.10 instead of 3.11; Gemini free tier instead of Anthropic (budget), one model instead
of two; default temperature instead of 0; 15 test items instead of 25-30 (manual checking).
