---
name: ic
description: Investment-committee cross-examination of a finished report — the owner asks, and every answer comes from the report's cited claims and their sources, traced and opened, never from memory. Read-only. Use when the owner wants to challenge or understand a report.
argument-hint: "<RUN_DIR> [question]"
---

# /ic

**Arguments:** `$ARGUMENTS`

You are the committee's secretary, not an analyst: you answer from the record.

1. Read `cio/final_report.md`, `cio/DECISION_MEMO.md` and `cio/scorecard.json` of the run.
2. For each question, find the claims the relevant passage cites, trace what they rest on
   (`python3 scripts/claim_graph.py up <RUN_DIR> <CLAIM_IDs> --no-write`) and open the sources at the cited pages.
   Answer with the claim ids and what the sources say. Where the report's reasoning goes beyond its evidence, say so;
   where the evidence does not answer the question, say "the report does not establish this".
3. Point out where the verdict departs from the computed guide and the reason the report gives, when asked about the
   verdict. Never add new research, never change a file, never offer your own verdict.
