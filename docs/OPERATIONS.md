# Operations Guide

## 1. Commands

| Purpose | Command | Cost |
|---|---|---|
| Full research run | `/research-company "TVS Motor Company Limited" TVSMOTOR NSE` | High: nine Opus specialists with web research, run **one at a time** by default, then the gap-closure loop and CIO synthesis |
| Parallel specialists | `/research-company "<Name>" <TICKER> <EX> --parallel` | Same research and depth; faster wall-clock, but more exposed to session limits and to download failures under load |
| With options | `/research-company "Bajaj Finance Limited" BAJFINANCE NSE --cutoff 2026-10-12 --notes "focus on credit costs"` | High |
| SME company | `/research-company "<Name>" <TICKER> NSE-SME --reference-position 2000000` | High |
| Validate configuration | `/research-company --validate-only` | Negligible: static checks and unit tests, no agents |
| Validate + delegation probe | `/research-company --validate-only --probe` | Small: one specialist answers a configuration check |
| Dry run | `/research-company --dry-run "TVS Motor Company Limited" TVSMOTOR NSE` | Negligible: prints the plan and paths, writes nothing |
| Resume an interrupted run | `/research-company --resume TVSMOTOR 20261012T074500Z` | Only the missing work |

Arguments (full mode): the quoted company name, ticker and exchange are **all required**. Options: `--cutoff YYYY-MM-DD` (default today, UTC), `--hurdle <decimal>` (default 0.12, a placeholder the CIO confirms with cited inputs), `--reference-position <amount>` (default 5,000,000 in the reporting currency), `--notes "<text>"`. Missing identifiers are rejected. If the name, ticker and exchange do not identify the same security, the CIO stops and asks.

Specialists run sequentially by default: each one is launched, finishes, and is validated before the next starts. A session-limit stop then interrupts at most one specialist, which resumes from its `progress.md` checkpoint with its finished work intact. Sequential mode changes the order, never the depth: no specialist is ever asked to shorten its work because of an interruption.

The full run proceeds without asking permission between stages. It finishes with a summary giving the outcome, verdict, both scores and their confidence, layers, QC status, commit SHAs and push status, and the paths to `final_report.md` and `scorecard.json`.

## 2. Outcomes and what changes

| Outcome (`run_manifest.json` status) | Scoreboard | `latest_run.txt` | Git |
|---|---|---|---|
| `complete` | Row upserted | Updated | Batch 1 + batch 2, pushed |
| `insufficient_evidence` (no scores issued; reasons in report) | **Unchanged** | **Unchanged** | Committed with a truthful message |
| `qc_failed` | **Unchanged** | **Unchanged** | Committed with a truthful message |
| `failed` / `interrupted` | **Unchanged** | **Unchanged** | Whatever batches completed; resume with `--resume` |

The triggers for insufficient evidence are predefined in `methodology/SCORING.md` §8.

## 3. Scoreboard

`COMPANY_SCOREBOARD.csv` is a compact screening index, with one row per company (ticker and exchange):

`company, ticker, exchange, assessment_date, latest_run_id, price, currency, price_timestamp, methodology_version, business_quality_score, investment_attractiveness_score`

- Only `scripts/finalize_run.py` writes it, via `scripts/scoreboard.py`. Writes take an exclusive file lock, re-read the file inside the lock, write to a temp file with fsync, replace it atomically, then re-verify. Concurrent runs cannot lose rows.
- A newer run is never replaced by an older one. Failed or insufficient runs never touch it.
- Compare scores only across rows with the same `methodology_version`.
- Check it with: `python3 scripts/scoreboard.py validate --check-runs`. This verifies every row against its run's scorecard and QC status.

Everything else (layers, verdict, valuation, reasoning) lives in the run directory named by `latest_run_id`.

## 4. Git policy (research runs)

`scripts/git_publish.py RUN_DIR --batch specialists|final --push` (CIO only):
- Stages **only** the run directory (plus the scoreboard and pointer in the final batch). Your other changes are untouched.
- The commit message states the true status.
- Pushes the current branch to `origin` with a plain `git push`. **No force, no merge, no pull.**
- If the push fails, the commit stays local and the problem is reported (exit 4). Fix the authentication or branch issue, then `git push` manually.
- Pushes go to whatever branch is checked out. Check out the branch you want research committed to before starting a run.

## 5. Re-runs, comparison and follow-ups

- Re-running a company creates a new UTC `RUN_ID`. Earlier runs are untouched, and specialists never see them.
- `python3 scripts/compare_runs.py <old RUN_DIR> <new RUN_DIR>` produces a change table of scores, dimensions, layer fits, verdict, price and methodology version. The CIO includes it under "Change Since Prior Run".
- To go deeper on a finished run, ask in a session, for example: "Re-invoke `moat` on run R to test X". The output goes to `specialists/moat_followup_<n>.md`. If conclusions change, write a new scorecard and repeat Stage 4.

## 6. Scripts

**Orchestration and QC (CIO)**

| Script | Use |
|---|---|
| `validate_system.py` | Static validation of agents, skills, taxonomy, methodology, contracts, investment policy, scoreboard schema, run preservation, stale references, Antigravity remnants and secrets. `--live-probe` adds one headless delegation check. |
| `new_run.py` | Create a run (UTC ID, manifest with the investment-policy snapshot, templates); `--dry-run` writes nothing |
| `manifest.py` | Deterministic manifest updates (`set`, `status`, `invocation`, `note`, `show`) |
| `validate_report.py` | Lint one report (`--kind specialist|followup|final|any`), including Historical Depth Standard counts |
| `validate_ledger.py` | Check claim ledgers (tags, sources, locators, metric keys) |
| `build_scorecard.py` | Builds `cio/scorecard.json` from the CIO's judgments in `cio/scorecard_inputs.json`: weighted raw scores, implied gates, caps, round-half-up finals, mapped verdict, optional one-notch override; then validates |
| `validate_scorecard.py` | Scorecard arithmetic, gates, verdict mapping, layer rules and decision outputs |
| `validate_run.py` | Stage-2 barrier (`--stage specialists`) and final automated QC (`--stage final`, which includes evidence statistics and the numeric-conflict gate). Validates each run against its own methodology version; a finalized run is checked read-only |
| `merge_ledgers.py` | Build `evidence_ledger.csv` |
| `reconcile_numbers.py` | Cross-ledger numeric conflicts (same metric, period, basis, unit), written to `qc/numeric_conflicts.csv` |
| `evidence_stats.py` | Evidence quality by agent (claims, primary share, tiers, NOT_LOCATED), checked against thresholds |
| `finalize_run.py` | Apply the outcome policy; the only scoreboard and pointer writer |
| `scoreboard.py` | Scoreboard schema, locked upsert, `validate` |
| `git_publish.py` | Scoped commit and push batches |
| `compare_runs.py` | Run-to-run change table plus the prior predictions to resolve |

**Research and analytics (specialists and CIO)**

| Script | Use |
|---|---|
| `corpus.py` | Local FilingForge library: `status`, `catalog` (CATALOG.md + SHA-256 + coverage), `search` (regex across all years with line numbers), `locate` (PDF page for a passage), `pages` (page-marked text) |
| `fetch_source.py` | Download a document with provenance (SHA-256, time, HTTP status) into `RUN_DIR/_cache/`; logs failures too. Retries transient failures with backoff, falls back to system `curl` (TLS errors, 403), and reuses a document another agent already downloaded in the run (`--no-reuse`, `--retries`) |
| `html_tables.py` | Deterministic HTML table → CSV extraction |
| `fin_metrics.py` | Ratios, CAGRs (3/5/10/15 years), per-share compounding, incremental ROIC and forensic screens (accruals, Beneish, Piotroski) from `financial_history.csv`; `general` and `lender` profiles |
| `valuation_tools.py` | `wacc`, `dcf` (with sensitivity and sanity warnings), `reverse-dcf`, `scenario-irr` (E[IRR], asymmetry, MoS), `price-ladder` (IA1/IA2/IA4 by price, giving decision triggers), `decompose`, `sizing-ceiling`, `scenario-build` (scenario values at the horizon from DCF inputs, net of dividends), `robustness` (verdict stability grid for the confidence test). `dcf` accepts `event_uplifts`; asymmetry is measured against the price compounded at the hurdle |
| `score_guides.py` | SCORING.md quantitative-guide bands for BQ1/BQ4/BQ5 from `fin_metrics.py` output and the history, with the flags that justify moving a band (lender mode: ROE vs cost of equity) |
| `research_lib.py` | Shared library (parses canonical blocks from the markdown) |

Tests: `python3 -m unittest discover tests`.

## 6a. Investment policy

`config/investment_policy.json` is the Investment Policy Statement: hurdle rate, horizon, benchmark, reference position, liquidity rule and risk limits. **Review it and set `"confirmed_by_user": true`.** Until then, every report flags the values as placeholders. Risk limits left `null` mean no sizing ceiling is computed.

## 6b. FilingForge library (local filings, token-efficient)

1. In the FilingForge app, download the company (annual reports, results, concalls, investor presentations; more categories are fine). The app saves to `~/Documents/FilingForgeLibrary/<TICKER>/` (path in `config/data_sources.json`). FilingForge has no external API, so this step is manual.
2. Check what you have: `python3 scripts/corpus.py status --ticker <TICKER>`. It shows coverage against the 10-year depth standard and the gaps.
3. Run `/research-company …`. The CIO catalogs the library automatically, and specialists read the Markdown (about 25× fewer tokens than the PDFs), cite PDF page numbers via `corpus.py locate`, and run full web research at par (the library may be incomplete or have download glitches; it never limits research). If the company is not in the library, the CIO asks once: download first, or proceed web-only.

The library is never modified, and its documents are not copied into git. Runs record each document's ID, path and SHA-256 in `corpus/catalog.csv`.

## 7. Changing the methodology

1. Edit the authoritative file (see `PROJECT_INSTRUCTIONS.md` §1). Canonical lists sit between `<!-- NAME:BEGIN/END -->` markers.
2. If scoring dimensions, weights, anchors, gates, verdict mapping or the outcome policy change, bump `METHODOLOGY_VERSION` in `methodology/SCORING.md`.
3. Record the change in `docs/FRAMEWORK_CHANGES.md`.
4. Run `python3 scripts/validate_system.py` and the tests, then commit.

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `Agent type 'financials' not found` or `/research-company` missing | Agent and skill definitions load at session start. Open a new Claude Code session in the repository root. |
| Settings permission rules ignored | Accept the workspace trust dialog once in an interactive session |
| Specialists stall on permission prompts | `.claude/settings.json` allows WebSearch, WebFetch and `python3 scripts/*`. File writes follow your permission mode. |
| Specialist fails the barrier | The CIO re-invokes it with the validator errors while they are fixable, otherwise records the gap |
| Session limit hit mid-run | Say "continue" after the reset. The CIO resumes the interrupted specialist with SendMessage (it reads its `progress.md`), then carries on with the next one. Nothing finished is redone or shortened. |
| Many failed downloads (`SSL`, `EOF`, 403) | `fetch_source.py` already retries and falls back to curl. If a source still fails, the agent tries the alternatives in `RESEARCH_PLAYBOOK.md` §1a and records the gap in its Method Coverage Checklist |
| `Merged ledger is stale` | Re-run `merge_ledgers.py` |
| Run outcome not `complete` | Read the `finalize_run.py` output and `run_manifest.json` `status_history` |
| Push failed | Commits are local. Fix authentication, or rebase or merge manually if the branch diverged (never force-push). |

## 9. Data hygiene

- Source documents are not committed. Use `RUN_DIR/_cache/` (git-ignored) for downloads, and cite by URL or identifier and locator.
- The untracked `research/companies/BAJFINANCE/raw_financials.md` predates this system. Its title says "audited", but it has an aggregator layout, quarterly data and no source line. Treat it as an unverified lead.
