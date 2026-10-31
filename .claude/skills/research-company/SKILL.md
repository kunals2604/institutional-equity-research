---
name: research-company
description: Run the full institutional equity research workflow on one listed company. The current session becomes the CIO, validates identity, creates a UTC-timestamped run, acquires and cross-checks the company's filings from NSE, BSE, the IR site, the Internet Archive and the local corpus, has every in-scope page read once and recorded by reader agents when the run's reading mode is on (critical sections read twice) or has web summaries digested as page-checked leads when it is off (the 3.2.0 default), runs the specialist subagents (eleven from methodology 3.2.0, one at a time by default), closes coverage gaps, builds the final report through the synthesis pipeline so that every finding has a recorded fate, adjudicates their evidence, writes its own independent analysis and synthesis before scoring, completes the four-layer assessment and both scores, commissions an independent audit and resolves its findings, passes QC, updates COMPANY_SCOREBOARD.csv and latest_run.txt, and commits and pushes. Also supports --validate-only, --dry-run and --resume. Expensive in full mode; runs only when the user invokes it.
argument-hint: "\"<Company name>\" <TICKER> <EXCHANGE> [--cutoff YYYY-MM-DD] [--hurdle <decimal>] [--reference-position 5000000] [--effort max] [--notes \"...\"] [--parallel] | --validate-only [--probe] | --dry-run \"<Company>\" <TICKER> <EXCHANGE> | --resume <TICKER> <RUN_ID>"
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

Options for full mode: `--cutoff YYYY-MM-DD` (default today, UTC), `--hurdle <decimal>` (an override; by default the hurdle is the run's cited cost of equity, `config/investment_policy.json`), `--reference-position <amount>` (default 5,000,000 in the reporting currency, used for the exit-liquidity gate), `--notes "<text for the brief>"`, `--effort <low|medium|high|xhigh|max>` (overrides the pinned effort of every Opus subagent for this run; recorded as `model.effort_override`; default: the pinned efforts of `methodology/MODEL_POLICY.md`), `--parallel` (launch the specialists two at a time instead of one at a time; same depth, more exposed to session limits and download failures; the reading stage is always sequential), `--reading on|off` (methodology 3.2.0; default **off**: the reading stage is switched off and the `digest` agent records web summaries as leads instead; **on** runs the full reading stage; passed to `new_run.py --reading`, recorded as the manifest's `reading_mode`, and fixed once Stage 1 starts).

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

1. Read `.claude/agents/cio.md` and the investment constitution.
2. Pick the depth: `--profile lean|standard|deep|max` and any `--set name=value` from `$ARGUMENTS` (default standard; `docs/SWITCHES.md`). Before anything is spent, show the owner the preset's steps and estimate with `python3 scripts/orchestrate.py plan --profile <preset>`, and say the estimate is not a measurement.
3. Create the run after validating the company's identity (`cio-stage-0`), with `python3 scripts/new_run.py ... --profile <preset>`.
4. Then loop until `orchestrate.py next` says the run is finished:
   - `python3 scripts/orchestrate.py run RUN_DIR` in the background runs every script and engine step and stops at a judgment step.
   - The step names its stage skill: load it, do the step, and write its output.
5. Keep the Mac on mains power with the lid open: a session cut by sleep costs real capacity, and the engine stops at three such aborts.
6. Start a fresh session for each stage. `orchestrate.py next` picks up from the disk, so nothing is lost, and the token bound is what keeps the decision sharp.
7. `python3 scripts/orchestrate.py status RUN_DIR` answers "where is it, what has it spent, how do I go deeper" at any moment.

## 4. Resume

`--resume <TICKER> <RUN_ID>`: set `RUN_DIR = research/companies/<TICKER>/runs/<RUN_ID>`. Refuse if it does not exist, or if its manifest status is `complete`. Read `cio.md`, then:
- `python3 scripts/manifest.py RUN_DIR show` and `python3 scripts/validate_run.py RUN_DIR --stage specialists` to find which specialists are complete.
- For a specialist interrupted mid-work whose agent is still addressable, resume it with SendMessage; otherwise re-launch **only** the missing or failed specialists (one at a time unless the run's `execution_mode` is `parallel`; same template, same identity, cutoff and price; logged as stage `1-resume`). A re-launched specialist reads its own `progress.md` and workpapers and continues at full depth.
- Continue from the first incomplete stage. Never delete or overwrite completed specialist work. If the cutoff or price is stale for the decision, say so in the report. Do not silently change them.

## 5. Honesty rules

Never claim an agent ran, a source was read, a check passed, a commit happened or a push succeeded when it did not. If a step fails, record it in the manifest, the QC record and the completion summary.
