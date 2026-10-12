---
name: research-company
description: Run the full institutional equity research workflow on one listed company. The current session becomes the CIO, creates a timestamped run, launches the nine specialist subagents in parallel, adjudicates their evidence, completes the four-layer assessment and both scores, passes QC, updates COMPANY_SCOREBOARD.csv and commits. Expensive; runs only when the user invokes it.
argument-hint: "<TICKER or company name> [exchange] [--cutoff YYYY-MM-DD] [--hurdle 0.12] [--reference-position 5000000] [notes]"
disable-model-invocation: true
---

# /research-company

**Arguments:** `$ARGUMENTS`

You are now the **CIO** for this research assignment. Do not spawn a CIO subagent. This session is the orchestrating parent.

1. Read `.claude/agents/cio.md` **in full**. It is the operative CIO protocol. Then read the documents it lists under "Must read before acting".
2. Parse the arguments: the company (ticker or name), optional exchange, and optional `--cutoff`, `--hurdle`, `--reference-position` and free-text notes for the brief. If no company was given, ask the user for one and stop.
3. Run the CIO protocol end to end, continuously:
   - **Stage 0 Preflight:** identity → price `CIO-C001` → `python3 scripts/new_run.py …` → brief and source register (leads only).
   - **Stage 1:** nine parallel Agent calls in one message (`financials`, `filings`, `management`, `industry`, `moat`, `concalls`, `valuation`, `bear-case`, `special-situations`), then wait for all nine notifications.
   - **Stage 2 Barrier:** `python3 scripts/validate_run.py RUN_DIR --stage specialists`, with targeted re-invocations for failures.
   - **Stage 3:** read everything, audit at least 12 claims and recompute at least 3 calculations, contradiction log, follow-ups, four independent layer analyses, classification, adversarial review when the draft verdict is a buy, the thesis-disproof exercise, `scorecard.json` plus `validate_scorecard.py`, then the final report.
   - **Stage 4:** `merge_ledgers.py` → `validate_run.py --stage final` → QC record → `update_scoreboard.py` (PASS only) → a serialized git commit (no push unless asked) → a short summary to the user.
4. Never claim an agent ran, a source was read, or a check passed when it did not. If a step fails, say so in the final report and the QC record.
