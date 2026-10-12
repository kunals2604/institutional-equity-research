---
name: research-company
description: Run the full institutional equity research workflow on one listed company. The current session becomes the CIO, validates identity, creates a UTC-timestamped run, launches the nine specialist subagents in parallel, adjudicates their evidence, completes the four-layer assessment and both scores, passes QC, updates COMPANY_SCOREBOARD.csv and latest_run.txt, and commits and pushes. Also supports --validate-only, --dry-run and --resume. Expensive in full mode; runs only when the user invokes it.
argument-hint: "\"<Company name>\" <TICKER> <EXCHANGE> [--cutoff YYYY-MM-DD] [--hurdle 0.12] [--reference-position 5000000] [--notes \"...\"] | --validate-only [--probe] | --dry-run \"<Company>\" <TICKER> <EXCHANGE> | --resume <TICKER> <RUN_ID>"
disable-model-invocation: true
---

# /research-company

**Arguments:** `$ARGUMENTS`

## 1. Parse the argument contract

| Mode | Syntax | What happens |
|---|---|---|
| **Full research** | `"<Company name>" <TICKER> <EXCHANGE> [options]` | The complete CIO workflow (§3) |
| **Validate only** | `--validate-only [--probe]` | Configuration and contract checks; **no research, no specialist agents** (unless `--probe`, which runs one harmless delegation check). Nothing is written to `research/` or the scoreboard. |
| **Dry run** | `--dry-run "<Company name>" <TICKER> <EXCHANGE>` | Shows the identity as parsed, the run directory that would be created, prior runs, artifact paths and stages. **Writes nothing and launches no agents.** Never present this as research. |
| **Resume** | `--resume <TICKER> <RUN_ID>` | Continues an interrupted run in place (§4) |

Options for full mode: `--cutoff YYYY-MM-DD` (default today, UTC), `--hurdle <decimal>` (default 0.12, a placeholder the CIO must confirm with cited inputs), `--reference-position <amount>` (default 5,000,000 in the reporting currency, used for the exit-liquidity gate), `--notes "<text for the brief>"`.

**Validation rules (full and dry-run):**
- All three identifiers are required: a quoted company name, a ticker (A–Z, 0–9, `&._-`), and an exchange (NSE, BSE, NSE-SME, BSE-SME, or a named foreign exchange).
- If any is missing, show the syntax with an example and **stop**.
- In full mode, Stage 0 verifies that the ticker on that exchange is the named company's listed equity. On a mismatch (for example the ticker belongs to another company, a different share class, or a delisted entity), or if several securities match, **stop and ask**. Never research a guess.

Example: `/research-company "TVS Motor Company Limited" TVSMOTOR NSE`

## 2. Validate-only and dry-run

**`--validate-only`:**
1. `python3 scripts/validate_system.py`
2. `python3 -m unittest discover tests`
3. If `--probe` is given, invoke the `bear-case` agent **once** via the Agent tool with this prompt: "CONFIGURATION CHECK ONLY. Do not research, use web tools, write files or run commands. Reply in one line: PRELOADED=<Y/N>; PREFIX=<your claim-ID prefix>; MODEL=<model id in your system context>; AGENT_TOOL=<Y/N>." Report the reply verbatim. Expected: `PREFIX=BEAR`, `AGENT_TOOL=N`.
4. Summarize pass or fail per check. State plainly that these checks verify configuration and contracts, not that a research run will succeed.

**`--dry-run "<Company>" <TICKER> <EXCHANGE>`:** validate the syntax, then run `python3 scripts/new_run.py --ticker <T> --company "<Company>" --exchange <EX> --segment <main|sme> --dry-run` and show its output. Do not retrieve prices or research the company.

## 3. Full research

You are now the **CIO**. Do not spawn a CIO subagent; this session is the orchestrating parent.

1. Read `.claude/agents/cio.md` **in full** (the operative protocol) and the documents it lists.
2. Run the protocol end to end, continuously, without pausing at milestones:
   - **Stage 0:** identity validation → price `CIO-C001` → `new_run.py` → `manifest.py` → brief and source register (leads only).
   - **Stage 1:** nine parallel Agent calls in **one message** (`financials`, `filings`, `management`, `industry`, `moat`, `concalls`, `valuation`, `bear-case`, `special-situations`), then wait for all nine.
   - **Stage 2:** `validate_run.py --stage specialists` → targeted re-invocations → `git_publish.py --batch specialists --push`.
   - **Stage 3:** read everything; audit at least 12 claims and recompute at least 3; contradiction log; follow-ups; four independent layer assessments; classification; adversarial review when the draft verdict is a buy; thesis-disproof; insufficient-evidence check; `scorecard.json` + `validate_scorecard.py`; final report.
   - **Stage 4:** `merge_ledgers.py` → `validate_run.py --stage final` → `quality_control.md` → `finalize_run.py` → `git_publish.py --batch final --push` → completion summary with the paths to `final_report.md` and `scorecard.json`.

## 4. Resume

`--resume <TICKER> <RUN_ID>`: set `RUN_DIR = research/companies/<TICKER>/runs/<RUN_ID>`. Refuse if it does not exist, or if its manifest status is `complete`. Read `cio.md`, then:
- `python3 scripts/manifest.py RUN_DIR show` and `python3 scripts/validate_run.py RUN_DIR --stage specialists` to find which specialists are complete.
- Re-launch **only** the missing or failed specialists (in parallel, same template, same identity, cutoff and price; logged as stage `1-resume`).
- Continue from the first incomplete stage. Never delete or overwrite completed specialist work. If the cutoff or price is stale for the decision, say so in the report. Do not silently change them.

## 5. Honesty rules

Never claim an agent ran, a source was read, a check passed, a commit happened or a push succeeded when it did not. If a step fails, record it in the manifest, the QC record and the completion summary.
