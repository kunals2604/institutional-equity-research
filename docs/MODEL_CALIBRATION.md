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

| Measure | Value | Source |
|---|---|---|
| Cost per Opus critical read (per chunk) | to be measured | `agent_driver.py show` |
| Cost per Sonnet read (per chunk) | to be measured | `agent_driver.py show` |
| Classes Sonnet read alone, and their recall | to be measured | the run's `BAKEOFF.md` |
| Cost per specialist (sessions, hand-overs, fix rounds) | to be measured | `engine/ENGINE.md` |
| Cost of the verification loop (verifier sessions, fix rounds) | to be measured | `engine/ENGINE.md` |
| Cost of a five-hour and a weekly usage window | to be measured | `agent_driver.py show` (from utilization) |
