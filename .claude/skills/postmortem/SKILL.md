---
name: postmortem
description: What happened after a finished run — its predictions scored against outcomes, its triggers checked, and for each miss the claims it rested on — written as a postmortem the owner can learn from. Read-only on the run; writes only research/outcomes/postmortems/.
argument-hint: "<TICKER> | <RUN_DIR>"
---

# /postmortem

**Arguments:** `$ARGUMENTS`

1. `python3 scripts/outcomes.py resolve` and `python3 scripts/outcomes.py score` (prices from the exchanges as of today;
   `--offline` when the owner asks), then `python3 scripts/outcomes.py due --ticker <TICKER> --cutoff <today>` for what is still open.
2. For the run's resolved predictions and the price since its cutoff: which predictions held, which failed, and for each
   failure the claims it rested on (`python3 scripts/claim_graph.py up <RUN_DIR> <ids> --no-write`) and whether those
   claims were wrong or the reasoning from them was.
3. The hindsight rule: you know how things turned out, so judge only what the run could have known at its cutoff, from
   its own sources. Do not rewrite the past report and do not score the company again.
4. Write `research/outcomes/postmortems/<TICKER>_<RUN_ID>.md` (what was predicted, what happened, the misses and their
   cause, what the method should learn) and show it.
