# Model Calibration — which reading work a single Sonnet read may cover

This is the record behind `calibration` in `methodology/MODEL_POLICY.md`. A non-critical section class is read by
Sonnet alone only after a bake-off shows that, on this framework's own documents and schema, Sonnet's read matches the
adjudicated result: **zero material misses and recall ≥ 0.98** for that class. Until then every chunk is read by both
models (`reading.py` treats an uncalibrated class as a double read), and critical classes are always read twice.

Procedure: `methodology/MODEL_POLICY.md` § The bake-off. Each entry below records the run, the chunks, the per-class
result (`corpus/reading/BAKEOFF.md` of that run) and the change made to the policy.

## Status

**Calibrated in every run** (owner's decision, 2026-10-19; `methodology/MODEL_POLICY.md` "In-run calibration"): each run
reads its own calibration sample with both models first and decides from it which non-critical classes Sonnet reads
alone (`corpus/reading/calibration.json` and `BAKEOFF.md` of the run). The global record below stays pending.

The format pilot of 2026-10-19 was stopped by the owner before it ran: the seven exhaustive Opus reads of run
BHARTIARTL 20261017T000000Z are frozen as a reference in the scratch pilot run (`reading.py reference ... score` can
score any later read against them), and the first full research run is the live test of the reading format 1.2
(tags, table tags, spans), the engine and the verification loop. Its measured costs go here:

One-shot reading, measured 2026-10-22 on the scratch run (chunks c46 auditor's report, c17 MD&A), against the frozen
exhaustive agentic Opus reads:

| Read | Cost | Exact recall | Same passage+type | Material |
|---|---|---|---|---|
| Agentic Opus at xhigh (v3.1 reader session) | $2.27–3.43 | reference | reference | reference |
| c46 Opus high, passage accounting | $0.88 | 92 % | — | 32/36 |
| c46 Opus medium, no accounting | $0.53 | 33 % | 66 % | 7/36 |
| c46 Opus medium, accounting | $0.55 | 47 % | 79 % | 35/36 by passage |
| c46 Sonnet high, accounting | $0.41 | 41 % | 60 % | 21/36 by passage |
| c17 Opus high, accounting | $0.68 | 74 % | 80 % | 26/33 by passage |
| c17 Opus medium, accounting | $0.66 | 72 % | 80 % | 26/33 by passage |
| c17 Sonnet high, accounting | $0.49 | 59 % | 76 % | 24/33 by passage |
| c17 Haiku high, accounting | $0.06 | 46 % | 65 % | 24/33 by passage |

**End to end, 2026-10-23** (the engine's production path on the same two chunks: one-shot reads with passage and number
accounting, fix turns, the second read and Opus resolutions; `reading.py reference ... score`). *Strict*: an item of the
same type with the same amounts and key answers cites the passage. *Content*: some item of the reconciled record cites
the passage and carries every amount of the reference item, whatever its type (the dossier prints the passage itself).

| Chunk | Reconciled record: strict material recall | Content material recall | Cost (calls) |
|---|---|---|---|
| c46 auditor's report (critical: Opus + Sonnet + resolution) | 0.861 (31/36) | 0.972 | $1.10 (2) + $0.69 (2) + $0.47 (1) = $2.26 |
| c17 MD&A (Opus + Haiku + resolution) | 0.879 (29/33) | 1.000 | $1.53 (3) + $0.22 (3) + $0.19 (1) = $1.94 |

- The first pass found a systematic depth gap: all three c46 reads (Opus, Sonnet, the resolution) wrote a CARO table
  of clauses per company as one item per company ("Clause 3(i)(a) 1, (b) 2, (c) 3&4"), losing each clause's footnote
  (strict material recall 0.25). Fixed by the rule "one fact per item, one CARO clause per item"
  (`READING_SCHEMAS.md` rule 2) and a check that rejects an item naming several clauses; the re-read wrote 34 clause
  items against the reference's 25.
- What the reconciled records still miss, strictly: 5 `unusual` observations of the exhaustive reader (for example
  "the audit-trail statement covers only certain associates"; the passage itself is in the record and the dossier),
  3 type choices (`management_claim` where the reference has `explanation_of_variance` or
  `capital_allocation_statement`), 1 CARO "not reported" recorded as `other_fact`, 1 clause cited at its table's
  clause column instead of its company column. No material fact or amount was missed on either chunk.
- Also fixed from the live run: a fiscal-year tail (the 26 of "FY 2025–26") counted as a number to record; opinions
  compared by wording instead of kind (unmodified, qualified, adverse, disclaimer); a session the CLI never created
  resumed instead of started; a missing PDF reported as an image error.
- Cost: output tokens are about two thirds of an Opus read ($20 per million output against $8 per million for the
  hour-cached prompt, solved from the calls' usage); a fix turn re-caches the previous answer ($0.2–0.4).
  Per 12k-token chunk: Opus $1.23, Sonnet $0.60, Haiku $0.20, resolution $0.31: **critical ≈ $2.14, other ≈ $1.74**
  (`agent_driver.py` `READ_COST_PER_12K`).
- **Fix turns (2026-10-23, later the same day).** A fresh-call fix (new session, the byte-identical chunk, then the
  fix block) was measured on c17: the cache served only the system prompt across sessions (18.3k tokens read) and the
  chunk was written again (~33k tokens), so a fresh fix cost $0.28–0.36 like a resumed one, and without its earlier
  answer the model needed a second round (Opus c17 $1.73 against $1.53 resumed). Fix turns resume as before
  (`ONESHOT_FRESH_FIX` off). What does cut them: most first-pass errors were false alarms of the check, now calibrated
  (`reading.py` `derive_quote`, `page_years`, `TABLE_HEAD`; `TestCheckCalibration`). Re-checked on the stored first
  answers: c17 22 → 7 errors (the rest: three anchors the model paraphrased, one table it tagged badly), c46 19 → 2
  (both now accepted). The pre-answer checklist in the one-shot rules removed the short-heading anchors (none in the
  read made with it).
- **Strict recall is noisy; content recall is the depth measure.** Two Opus reads of c17 with the same rules scored
  0.88 and 0.61 strict material recall (one tags a growth rate `kpi`, the other `segment_data`; one records an
  explanation as its own item, the other inside the cited passage) and 1.00 and 1.00 content recall. Report both;
  judge depth by content recall, and type agreement by strict recall.
- Usage: the five-hour utilization measured during this check (≈ $10–13 per window) includes the interactive Claude Code
  session running at the same time (15 % of the window was used before the engine started); the clean measurement of
  2026-10-19 ($28 per window) stands until the first run, where the CIO session waits while the engine reads.

| Measure | Value | Source |
|---|---|---|
| Cost per Opus primary read (per 12k-token chunk, with fix turns) | $1.23 (two chunks, 2026-10-23) | `agent_driver.py show` |
| Cost per Sonnet / Haiku second read; per resolution | $0.60 / $0.20; $0.31 (same) | `agent_driver.py show` |
| Classes Sonnet read alone, and their recall | to be measured | the run's `BAKEOFF.md` |
| Cost per specialist (sessions, hand-overs, fix rounds) | to be measured | `engine/ENGINE.md` |
| Cost of the verification loop (verifier sessions, fix rounds) | to be measured | `engine/ENGINE.md` |
| Cost of a five-hour and a weekly usage window | to be measured | `agent_driver.py show` (from utilization) |
