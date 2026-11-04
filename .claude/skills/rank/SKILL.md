---
name: rank
description: Every company's latest decision on one table, ordered by expected return over the hurdle, with the permanent-loss band and any holdings. It compares and never decides. Read-only.
argument-hint: "[--held <file of held tickers>]"
---

# /rank

**Arguments:** `$ARGUMENTS`

1. `python3 scripts/ideas.py rank [--held <file>]` and show the table as it is.
2. Say what the order rests on (each run's E[IRR], hurdle and permanent-loss band, as of each run's own cutoff, so older
   runs are staler) and that it is no allocation: there are no position limits by the owner's policy, and the decision
   on each name is the owner's (`/decide`).
