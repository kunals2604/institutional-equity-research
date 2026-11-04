---
name: triage
description: One company, one agent session, a tear sheet that says KILL (not worth a full run now) or CONTINUE (with the questions a full run must answer first). Costs one Opus session. Runs only when the owner invokes it.
argument-hint: "<SYMBOL> [--exchange NSE|BSE|US] [--date YYYY-MM-DD] [--company \"Name\"]"
disable-model-invocation: true
---

# /triage

**Arguments:** `$ARGUMENTS`

1. `python3 scripts/triage.py prepare <SYMBOL> --exchange <ex> --date <date> [--company "..."]` and read the `PACK.md` it
   writes. If the pack says the warehouse holds no results for the company, tell the owner and ask whether to load them
   (`warehouse.py crawl-xbrl --symbols <file>`) or triage from the web alone.
2. `python3 scripts/agent_driver.py triage <DIR>` (Bash, in the background): the `triage` agent writes `TEAR_SHEET.md`
   and runs its check until it passes. Do not write the tear sheet yourself.
3. `python3 scripts/triage.py check <DIR>`; if it passes, show the tear sheet and `python3 scripts/triage.py record <DIR>`.
4. A triage is not a verdict and a later run does not read it. For a CONTINUE, the next step is `/research-company`,
   which the owner starts.
