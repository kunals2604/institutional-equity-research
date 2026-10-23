---
name: research-company
description: Run the full institutional equity research workflow on one listed company. The current session becomes the CIO, validates identity, creates a UTC-timestamped run, acquires and cross-checks the company's filings from NSE, BSE, the IR site, the Internet Archive and the local corpus, has every in-scope page read once and recorded by reader agents (critical sections read twice), runs the ten specialist subagents (one at a time by default), closes coverage gaps, adjudicates their evidence, writes its own independent analysis and synthesis before scoring, completes the four-layer assessment and both scores, commissions an independent audit and resolves its findings, passes QC, updates COMPANY_SCOREBOARD.csv and latest_run.txt, and commits and pushes. Also supports --validate-only, --dry-run and --resume. Expensive in full mode; runs only when the user invokes it.
argument-hint: "\"<Company name>\" <TICKER> <EXCHANGE> [--cutoff YYYY-MM-DD] [--hurdle 0.12] [--reference-position 5000000] [--effort max] [--notes \"...\"] [--parallel] | --validate-only [--probe] | --dry-run \"<Company>\" <TICKER> <EXCHANGE> | --resume <TICKER> <RUN_ID>"
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

Options for full mode: `--cutoff YYYY-MM-DD` (default today, UTC), `--hurdle <decimal>` (default 0.12, a placeholder the CIO must confirm with cited inputs), `--reference-position <amount>` (default 5,000,000 in the reporting currency, used for the exit-liquidity gate), `--notes "<text for the brief>"`, `--effort <low|medium|high|xhigh|max>` (overrides the pinned effort of every Opus subagent for this run; recorded as `model.effort_override`; default: the pinned efforts of `methodology/MODEL_POLICY.md`), `--parallel` (launch all ten specialists at once instead of one at a time; same depth, more exposed to session limits and download failures; the reading stage is always sequential).

**Validation rules (full and dry-run):**
- All three identifiers are required: a quoted company name, a ticker (A–Z, 0–9, `&._-`), and an exchange (NSE, BSE, NSE-SME, BSE-SME, or a named foreign exchange).
- If any is missing, show the syntax with an example and **stop**.
- In full mode, Stage 0 verifies that the ticker on that exchange is the named company's listed equity. On a mismatch (for example the ticker belongs to another company, a different share class, or a delisted entity), or if several securities match, **stop and ask**. Never research a guess.

Example: `/research-company "TVS Motor Company Limited" TVSMOTOR NSE`

## 2. Validate-only and dry-run

**`--validate-only`:**
1. `python3 scripts/validate_system.py`
2. `python3 -m unittest discover tests`
3. If `--probe` is given, run `python3 scripts/agent_driver.py probe` (the same check through the engine: one headless, isolated `bear-case` session on Haiku), and invoke the `bear-case` agent **once** via the Agent tool with this prompt: "CONFIGURATION CHECK ONLY. Do not research, use web tools, write files or run commands. Reply in one line: PRELOADED=<Y/N>; PREFIX=<your claim-ID prefix>; MODEL=<model id in your system context>; AGENT_TOOL=<Y/N>." Report the reply verbatim. Expected: `PREFIX=BEAR`, `AGENT_TOOL=N`.
4. Summarize pass or fail per check. State plainly that these checks verify configuration and contracts, not that a research run will succeed.

**`--dry-run "<Company>" <TICKER> <EXCHANGE>`:** validate the syntax, then run `python3 scripts/new_run.py --ticker <T> --company "<Company>" --exchange <EX> --segment <main|sme> --dry-run` and show its output. Do not retrieve prices or research the company.

## 3. Full research

You are now the **CIO**. Do not spawn a CIO subagent; this session is the orchestrating parent.

1. Read `.claude/agents/cio.md` **in full** (the operative protocol) and the documents it lists.
2. Run the protocol end to end, continuously, without pausing at milestones:
   - **Stage 0:** session check (`reading_audit.py session`: if not Opus at xhigh, tell the user once) → identity validation → `new_run.py` → price `CIO-C001` = exchange close (`market_data.py close`) → `manifest.py` → **local corpus** (`corpus.py status` / `catalog`; if the company is missing from the FilingForge library, ask once: download first, or proceed without it) → **document acquisition** (`exchange_index.py all` for NSE, BSE, the IR site and the archive → `document_map.py build`, which downloads and validates the core documents and cross-checks them against the corpus → `structured_filings.py fetch` and `xbrl_facts.py extract` → `reading.py fetch-filings` → the `librarian` agent for every missing or failed document) → the `historian` (`agent_driver.py events RUN_DIR` in the background: the ten-year timeline of major events, checked by `verify.py events`) → brief (with the document-map coverage, flags and the reading plan) and source register (leads only).
   - **Stage 0b (reading, one agent at a time by default):** `reading.py plan --years 5 --core-years 5` (every page of the latest five fiscal years, the core sections of the five before; a missing in-scope report: the librarian, or `reading.py accept-gap` with the reason) → `agent_driver.py reading RUN_DIR` in the background (headless `reader` / `critical-reader` sessions; resolutions when two reads disagree; usage limits waited out) until it exits 0 — without the CLI, loop `reading.py next` and launch exactly the agent, description and prompt it prints → `reading.py dossiers` → `reading.py status --strict`.
   - **Stage 1 (sequential by default; ten independent heads):** write the identity block to `RUN_DIR/engine/identity.md`, then `agent_driver.py specialists RUN_DIR` in the background (`--parallel 2` with `--parallel`): each specialist in the order of `cio.md` Stage 1 (financials, filings, industry, scuttlebutt, moat, management, concalls, valuation, special-situations, bear-case) as its own headless session from the one brief `templates/specialist_prompt.md`, unable to read another's work, validated with `validate_report.py` and resumed with the errors until it passes; usage limits waited out; a context past 250k handed to a fresh session after a checkpoint. Without the CLI, one Agent call at a time with the prompt `agent_driver.py prompt` prints and the description `<name> <RUN_ID>`; resume after a limit with SendMessage. Never ask a specialist to shorten its work.
   - **Stage 2:** `verify.py run --stage specialists` (fix or waive every open finding) → `validate_run.py --stage specialists` → targeted re-invocations → **gap-closure loop** (`cio/gap_register.md`: every Partial / Not available checklist row, every unresolved `missing` or flagged document-map row, and every material missing-evidence item, classified closable or irreducible; closable gaps go back to the owning specialist) → `git_publish.py --batch specialists --push`.
   - **Stage 3 (synthesis first, scores last):** read everything → `reconcile_numbers.py` + `evidence_stats.py` (adopt the audited financials dataset as the numeric base) → audit at least 12 claims and recompute at least 3 with the scripts → correlated-evidence check → contradiction log (every numeric conflict) → follow-ups → **CIO independent analysis** (`cio/cio_analysis.md`, including `score_guides.py`) → **written synthesis** (variant perception, key debates, four independent layer assessments, classification, thesis-disproof) → insufficient-evidence check → **score from the synthesis**: `cio/scorecard_inputs.json` → `build_scorecard.py` → **confidence assessment** (`valuation_tools.py robustness`, SCORING.md §4) → symmetric adversarial review (any buy or avoid verdict, or a verdict change), then rebuild → decision triggers (price ladder), position risk, structured predictions, review date → every earlier prediction now due resolved (`outcomes.py due` / `record`) → change analysis → final report.
   - **Stage 4:** **reading audit** (`reading_audit.py run`: fix every failure) → **independent audit** (`merge_ledgers.py` → `agent_driver.py audit` (the `auditor` agent) → `validate_report.py --kind audit` → resolve every finding in `cio/audit_resolutions.md` → re-audit until every Critical finding is Closed → report section *Independent Audit and Resolutions*) → `merge_ledgers.py` → `verify.py run --stage final` (the CIO's own ledger included) → `validate_run.py --stage final` → `quality_control.md` → `finalize_run.py` → `git_publish.py --batch final --push` → completion summary with the paths to `final_report.md` and `scorecard.json`.

## 4. Resume

`--resume <TICKER> <RUN_ID>`: set `RUN_DIR = research/companies/<TICKER>/runs/<RUN_ID>`. Refuse if it does not exist, or if its manifest status is `complete`. Read `cio.md`, then:
- `python3 scripts/manifest.py RUN_DIR show` and `python3 scripts/validate_run.py RUN_DIR --stage specialists` to find which specialists are complete.
- For a specialist interrupted mid-work whose agent is still addressable, resume it with SendMessage; otherwise re-launch **only** the missing or failed specialists (one at a time unless the run's `execution_mode` is `parallel`; same template, same identity, cutoff and price; logged as stage `1-resume`). A re-launched specialist reads its own `progress.md` and workpapers and continues at full depth.
- Continue from the first incomplete stage. Never delete or overwrite completed specialist work. If the cutoff or price is stale for the decision, say so in the report. Do not silently change them.

## 5. Honesty rules

Never claim an agent ran, a source was read, a check passed, a commit happened or a push succeeded when it did not. If a step fails, record it in the manifest, the QC record and the completion summary.
