# Operations Guide

## 1. Commands

| Purpose | Command | Cost |
|---|---|---|
| Full research run | `/research-company "TVS Motor Company Limited" TVSMOTOR NSE` | High: Stage-0 acquisition and structured filings, the **reading stage** (every page of the latest 5 fiscal years' annual reports and the core sections of the 5 before, 24 quarters of transcripts, 12 of presentations and the forensic exchange filings read once and recorded: Sonnet readers, critical sections also by Opus, run headless by `agent_driver.py`), ten Opus specialists at xhigh effort, **one at a time**, each its own headless session that cannot see the others' work, the gap-closure loop, CIO synthesis, the reading audit and an independent audit |
| Lower effort for a run | `/research-company "<Name>" <TICKER> <EX> --effort high` | Lower: every Opus agent runs at that effort for this run (recorded in the manifest); Sonnet readers keep theirs |
| Parallel specialists | `/research-company "<Name>" <TICKER> <EX> --parallel` | Same research and depth; faster wall-clock, but more exposed to session limits and to download failures under load |
| With options | `/research-company "Bajaj Finance Limited" BAJFINANCE NSE --cutoff 2026-10-12 --notes "focus on credit costs"` | High |
| SME company | `/research-company "<Name>" <TICKER> NSE-SME --reference-position 2000000` | High |
| Validate configuration | `/research-company --validate-only` | Negligible: static checks and unit tests, no agents |
| Validate + delegation probe | `/research-company --validate-only --probe` | Small: one specialist answers a configuration check |
| Dry run | `/research-company --dry-run "TVS Motor Company Limited" TVSMOTOR NSE` | Negligible: prints the plan and paths, writes nothing |
| Resume an interrupted run | `/research-company --resume TVSMOTOR 20261012T074500Z` | Only the missing work |

Arguments (full mode): the quoted company name, ticker and exchange are **all required**. Options: `--cutoff YYYY-MM-DD` (default today, UTC), `--hurdle <decimal>` (default 0.12, a placeholder the CIO confirms with cited inputs), `--reference-position <amount>` (default 5,000,000 in the reporting currency), `--effort <low|medium|high|xhigh|max>` (overrides the pinned effort of every Opus subagent for this run), `--notes "<text>"`. Missing identifiers are rejected. If the name, ticker and exchange do not identify the same security, the CIO stops and asks.

Models and efforts are pinned per agent in `methodology/MODEL_POLICY.md` (the CIO and every specialist, the auditor and the critical reader on Opus at xhigh; the reader and the librarian on Sonnet at high; `--effort max` raises every Opus agent for one run). Start the session on Opus at xhigh: the CIO checks it at Stage 0 (`reading_audit.py session`) and tells you if it is not.

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
| `build_scorecard.py` | Builds `cio/scorecard.json` from the CIO's judgments in `cio/scorecard_inputs.json`. Methodology 3.0.0: evidence ceiling on dimension confidence, price metrics at the verified price from `scenario_inputs`, the robustness grid, the layer weight profile, effective scores, gates, must-pass tests, required margin of safety, conviction, the mapped verdict and its path; optional one-notch override; then validates. 2.x scorecards keep the 2.x arithmetic |
| `validate_scorecard.py` | Scorecard arithmetic, gates, verdict mapping, layer rules and decision outputs |
| `validate_run.py` | Stage-2 barrier (`--stage specialists`) and final automated QC (`--stage final`, which includes evidence statistics and the numeric-conflict gate). Validates each run against its own methodology version; a finalized run is checked read-only |
| `merge_ledgers.py` | Build `evidence_ledger.csv` (specialist, CIO and auditor ledgers) |
| `reading.py` | Stage-0b reading stage: `fetch-filings` (the exchange announcements forensic work needs), `plan [--years 5] [--core-years 5] [--no-reuse] [--replan "<reason>"]` (the fiscal-year scope, passages, sections, critical classes, repeats read once, VIEW REQUIRED pages, chunks, documents reused from earlier runs), `accept-gap` (why an in-scope report cannot be had), `next [--restart "<why>"]` (the next reader launch and its exact prompt, logged in the manifest; resolutions when two reads disagree), `check` (assembles a reader's parts; anchors in their passages, every number in every field printed there, a receipt for every page, VIEW REQUIRED pages viewed), `render` (a page image at a chosen resolution, rotation and split), `compare`, `dossiers` (topic dossiers and one reading pack per specialist), `status` (page ledger and `COVERAGE.md`), `bakeoff plan|score` (calibration), `sample` (the auditor's re-read sample) |
| `agent_driver.py` | The engine: runs every agent except the CIO as its own headless Claude Code session outside the CIO's context — `reading RUN_DIR [--parallel N] [--bakeoff]`, `librarian`, `specialists [--only a,b] [--parallel N]`, `followup AGENT --stage 2\|3\|4 --message-file F [--output REL]`, `audit`; pinned model and effort, a permission profile per agent (readers write only their parts; a specialist cannot read another's work, `cio/`, `audit/` or other runs and writes only its own files; the auditor writes only `audit/`), a one-hour cache, usage limits waited out, a weekly reserve (`--weekly-ceiling`), parallel sessions only below `--parallel-ceiling` of the five-hour window, checks resumed with their errors, long agents handed to a fresh session at `--context-limit` after a checkpoint, file fingerprints around each specialist segment; records in `corpus/reading/launches.json` and `engine/jobs.json` (+ `engine/ENGINE.md`). `prompt RUN_DIR NAME` (the filled specialist brief), `show` (time, tokens, cost and usage per session), `usage [--probe]` (the account's five-hour and weekly utilization), `probe` (configuration check), `cli` |
| `verify.py` | The verification loop: `specialist RUN_DIR NAME` (script checks of one specialist from its transcripts and files: values it never saw, sources and pages it never opened, its reading pack, checklist evidence, independence, integrity, model and effort), `sample` / `claims` (the `verifier` agent's re-check of a claim sample at the sources), `run --stage specialists\|final` (the whole research: `qc/VERIFICATION.md`, required by `validate_run.py`), `waive FINDING_ID --reason`, `lessons` (what earlier runs' verification found, per agent and check; fed into the next briefs) |
| `reading_audit.py` | `session`: this session's model and effort (Stage 0). `run`: from the agents' own transcripts, every agent on its pinned model and effort, every reader received every line of its chunks and opened every VIEW REQUIRED page, every specialist read its reading pack → `qc/READING_AUDIT.md` |
| `audit_tools.py` | The auditor's aids: `tieout` (every cited number in the report against its ledger value; flags incomplete citations and unsupported numbers) and `sample` (a reproducible stratified claim sample with the local file to open) |
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
| `netfetch.py` | Transport library: system curl first (Python's LibreSSL 2.8.3 is unreliable), host request profiles (NSE API, NSE archives, BSE API over HTTP/2, BSE files, SEC, default), retries, payload validation (error pages, truncated PDFs, corrupt ZIPs), Internet Archive lookups, safe ZIP extraction |
| `fetch_source.py` | Download a document with provenance (SHA-256, time, HTTP status, method, validation) into `RUN_DIR/_cache/`; logs failures too. Order: in-run reuse → the URL → `--alt` mirrors → the archive's raw copy; ZIPs unpacked with member hashes |
| `exchange_index.py` | Stage-0 index of NSE (annual reports, full announcement history, results XBRL and integrated filings, shareholding, board meetings, corporate actions, PIT, SAST), BSE (annual reports, announcements by year, scrip/ISIN lookup), the IR site (bounded crawl) and the Internet Archive; `show` lists filings by type and period |
| `document_map.py` | Stage-0 document map: every required annual report, transcript, presentation, results and shareholding filing, with local and exchange copies; downloads the core documents once; cross-checks the two channels (page counts, first-page text, period labels, duplicates, extraction quality) → `corpus/DOCUMENT_MAP.md`. `add` registers a document the librarian found elsewhere (validated, text layer built) |
| `structured_filings.py` | Stage-0 structured exchange filings (exact, tier 1): BRSR XBRL by year, AGM and postal-ballot voting results by shareholder category, the Integrated Filings' audit-opinion statements and board composition → `corpus/structured/` and `corpus/STRUCTURED.md`; tells the reading planner which BRSR pages the XBRL covers |
| `doc_text.py` | Text layer for large PDFs: spreads split, prose in reading order, tables rebuilt from word coordinates (empty cells kept), page anchors with PDF and printed page numbers, a section index (`toc`), cross-document `search`, `page` and `verify`; flags pages to read on the rendered PDF (image-only, rotated, table mismatch or alignment, encoding). Run by `document_map.py` for every core document |
| `xbrl_facts.py` | Exchange XBRL results (XML to FY2024, Integrated Filing tables from 2025) → financial-history rows (tier 1); `reconcile` against the specialist's history with likely causes for common definitional gaps |
| `market_data.py` | NSE bhavcopy (tier 1): `close` (the price claim), `adtv` (traded value and delivery), `history` (split/bonus-adjusted monthly or weekly closes, CAGR, total return, maximum drawdown) |
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
3. Run `/research-company …`. The CIO catalogs the library automatically, indexes the exchanges and the IR site, downloads the exchange copy of every core document and **cross-checks the two** (`corpus/DOCUMENT_MAP.md` lists every disagreement: page counts, content, period labels, duplicate labels). Specialists read the Markdown (about 25× fewer tokens than the PDFs), cite PDF page numbers via `corpus.py locate`, read the exchange copy wherever the map flags a local defect, and run full web research at par. If the company is not in the library, the CIO asks once: download first, or proceed without it (the exchange copies are acquired either way).
4. After a run, re-download in FilingForge any document the map flags as defective in your library.

The library is never modified, and its documents are not copied into git. Runs record each document's ID, path and SHA-256 in `corpus/catalog.csv`.

## 6c. Reading stage and model policy (3.1.0)

Why: in run BHARTIARTL 20261012T132311Z the ten agents together saw 11–17 % of each annual report's text while their
reports implied more, and every agent ran at effort *high* while the session was believed to be at *max*. Now:

1. **Every in-scope page is read once** in small fresh contexts: `reading.py plan` splits each page into passages
   (every line of text is a passage or page furniture: a lone `420` or `-` in a statement is a value), marks critical
   sections (auditor's reports, CARO, IFC, critical notes, Board's report, AOC-1/2, secretarial audit, related-party
   filings), and marks sentences of 60 characters or more, and whole tables, that repeat word for word in another year
   or section so they are read once (their items are carried to every place they repeat). Labels, values, headings and
   column headers are always read, and the repeated sentence just before new text is shown as context. Pages with no
   reliable text, with raster images (10 % of the page or more, logos and backgrounds excluded), or whose numbers must
   be confirmed (including tables the text layer printed one cell per line) are **VIEW REQUIRED** on the rendered page
   (`reading.py render` makes a larger or upright image). **Scope** (owner's decision, 2026-10-19): every page of the
   annual reports of the latest five fiscal years and the core sections of the five before them (auditor's reports,
   CARO, IFC, statements and every note, Board's report and its statutory annexures, MD&A), fixed by fiscal year; an
   in-scope report missing from the map blocks the plan until the librarian finds it or `reading.py accept-gap`
   records why it cannot be had. **`agent_driver.py reading RUN_DIR`** then runs the launches `reading.py next` issues,
   **one at a time** by default (`--parallel N` below the five-hour ceiling), about one chunk each, each as its own headless Claude Code session (`claude -p --agent
   reader|critical-reader`, the pinned model and effort, a one-hour prompt cache, writes confined to the readers'
   parts directories, the two reads of a chunk unable to see each other's, the shell only for `reading.py check` and
   `render`), outside the CIO's context; it waits out
   usage limits and resumes the same session, resumes a session whose check fails, and records every session's time
   and tokens on its launch (`agent_driver.py show RUN_DIR`). Readers cite each fact's passage and a few of its words
   (`anchor`) and write in parts; `reading.py check` assembles the parts, attaches the printed text as the quote, and
   checks every anchor and every number of every field against the passage, a receipt for every page, and every VIEW
   REQUIRED page viewed. Critical chunks are read by both models independently, and every disagreement (an item one
   read lacks, or an amount in a different field) is resolved against the page. A document an earlier run of the
   company read and audited (same SHA-256, same reading format and schema) is reused, not read again.
2. **Specialists start from complete dossiers** (`corpus/dossiers/`, one reading pack each), verify on the page and cite
   the document, never the dossier, and never state their own coverage: `corpus/reading/COVERAGE.md` is the record.
   Each topic dossier has three parts: series (every value of every recurring line across all years, each with its
   page; changed comparatives between reports flagged), material items with their full printed text, and a reference
   file of every other item. A pack's must-read part (series and material items of the topics it owns) is stated with
   its token size; the reading audit checks that part. Readers write tags, not transcriptions (schema 1.2: key fields,
   `to` spans, one `table` tag per table expanded row by row by script).
   **Calibrating a format change:** `reading.py reference RUN_DIR save --chunks <ids>` freezes reads as the reference
   and marks those chunks; `agent_driver.py reading RUN_DIR --bakeoff` reads them in the current format;
   `reading.py reference RUN_DIR score` writes `corpus/reading/REFERENCE_SCORE.md` (recall by class and model,
   material misses, cost per chunk).
3. **The reading audit** (`reading_audit.py run`) checks from the transcripts that this all happened as recorded.

Volume (measured on BHARTIARTL FY2024–FY2026): about 67 chunks and 0.6–0.75M tokens of text and page images per
annual report, about a third of it (about 90 pages) in critical chunks read by both models; 120–150 pages of each
report are viewed on the image; about 20k tokens per transcript. Read-once saves about 10 % of an older report's text
(another 10 % repeats but is shown as context). The core sections are about half of a report, so five full years and
five core years come to roughly 5M tokens of annual-report reading content; the critical sections (about 2.2M over
ten years) are all core, so the Opus volume is the same as for ten full years.

Cost (measured, BHARTIARTL bake-off, 2026-10-19): an Opus critical read at max effort run as a subagent took 20–33
minutes and 1.7–2.8M processed tokens for one chunk of 10–15k tokens; most of the time was thinking, two turns over
five minutes let the subagent's five-minute prompt cache expire, and the CIO's own turns around four launches
processed three times what the readers did. One five-hour usage window held about four such launches. The driver
removes the CIO's turns and the cache expiry, the anchors remove the retyping of quotes, and the readers' Opus effort
is now xhigh; their combined effect is measured by `agent_driver.py show` on the first launches it runs (not yet
recorded here). Even so, a first ten-year read of a large company is a multi-day, multi-window job; a later run
reads only the new reports and quarters, because the rest is reused. While `MODEL_POLICY.md` calibration is
`pending`, every chunk is read by both models (more Opus usage); after the bake-off, the classes that pass are read by
Sonnet alone.

Check a run: `python3 scripts/reading.py status RUN_DIR` (pages read / repeat / structured / out of scope / pending),
`qc/READING_AUDIT.md` (models, efforts, lines received, packs read).

## 6d. The verification loop (3.1.0)

A validator checks the shape of a report; the verification loop checks the work against what the agent actually did
(`scripts/verify.py`, `.claude/agents/verifier.md`). Calibrated on run BHARTIARTL 20261012T132311Z (read-only), it found
what every validator had passed: sums of printed figures recorded as FACT values (for example a deferred-payment balance
that was three maturity buckets added up and converted to crore), values that never appeared in anything the agent read,
cited pages never opened, and every agent below its pinned effort.

| Tier | When | What | Who fixes it |
|---|---|---|---|
| A, scripts | each specialist, the moment its report passes its validator (inside `agent_driver.py specialists`) | FACT / MANAGEMENT STATEMENT values never seen in the agent's tool results or brief; cited sources and pages never opened; must-read dossiers not read in full; Done checklist rows pointing nowhere; independence, integrity, model and effort | the engine resumes the specialist with every fixable blocking finding until it passes, then sends the major ones once; the CIO for independence, integrity, model and effort |
| B, `verifier` agent (Opus) | after Tier A passes | re-opens a sample of the specialist's claims (its conclusion's claims first, then numeric facts; more for an agent whose earlier runs had discrepancies) at the sources | each material discrepancy and unverifiable claim goes back to the specialist, then the verifier re-checks (two rounds); what is left goes to the CIO |
| Run | Stage 2 (`verify.py run --stage specialists`) and Stage 4 (`--stage final`) | every specialist again, the reading stage and reading audit, the audit's resolutions, the CIO's own ledger against the CIO's sessions | the CIO: follow-ups, re-runs, or a waiver with its reason (`verify.py waive`); `validate_run.py` fails until PASS |

**Learning.** Every run's findings stay in its `qc/verification.json`. `verify.py lessons` counts, per agent and check,
the earlier runs in which a check found something (plus `config/verification_lessons_seed.json`, from the calibration
above); each specialist's brief carries its lessons as process rules (never another company's facts or conclusions),
the verifier samples more of an agent that had discrepancies, and a check the CIO keeps waiving is listed for the owner
to review. The reading stage learns inside each run: the in-run calibration decides from the run's own sample which
non-critical classes Sonnet reads alone.

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
| Many failed downloads (`SSL`, `EOF`, 403) | `netfetch.py` uses curl first and retries; check `source_retrievals.csv` (`method`, `validation`, `error`). If a source still fails, the agent tries the alternatives in `RESEARCH_PLAYBOOK.md` §1a and records the gap in its Method Coverage Checklist |
| An exchange endpoint stops working | `corpus/index_summary.json` lists failing endpoints. Re-run `exchange_index.py` for that source; check `SOURCE_GUIDE.md` §6 for the request profile; update `netfetch.PROFILES` if the exchange changed its requirements, and re-verify |
| Document map shows `missing` core documents | Search the IR site and the web for the exact title; `exchange_index.py wayback --prefix <IR document folder>` for moved files; then record the gap |
| `reading.py next` re-issues the same chunk | Its extraction fails `check`: run `reading.py check RUN_DIR <chunk> --role <role>` to see why; the next launch lists only the unfinished chunks |
| `reading.py plan` refuses: "in-scope annual reports are missing" | Run the librarian for each named report. Only if one truly cannot be had (not yet listed, never published), record why: `reading.py accept-gap RUN_DIR AR-FY<year> --reason "..."`; COVERAGE.md lists it |
| `agent_driver.py` exits 1 | The last lines of `_cache/engine/engine.log` say why: a launch or job whose check still failed after its fix rounds (its record in `corpus/reading/launches.json` or `engine/jobs.json` has the errors), a session that could not be finished, a usage window that resets after `--max-wait-hours`, or the weekly window above `--weekly-ceiling`. Fix the cause and run it again; it resumes the open sessions |
| `verify.py run` FAIL, or `validate_run.py` says verification failed | Read `qc/VERIFICATION.md` and `qc/verification/<name>.json`: fixable findings go back to the specialist (`agent_driver.py followup ... --stage 2`, or `agent_driver.py verify RUN_DIR --only <name>` for the verifier's re-check); independence or integrity breaches mean a clean re-run; accept only with `verify.py waive RUN_DIR <id> --reason` |
| `INDEPENDENCE` in the engine log or the reading audit | A specialist's independent work touched another specialist's files, `cio/`, `audit/`, another run or the archive (from its transcript), or changed a file it does not own (the engine's fingerprints). Re-run that specialist from a clean start, or record exactly what it saw and why its conclusions stand |
| `reading.py next` refuses: "the engine runs" | One engine per run issues the launches. Wait for it, or stop it (it is safe to stop and restart) |
| `agent_driver.py cli` finds no binary | Set `CLAUDE_BIN` to the `claude` executable (the VS Code extension ships one under `~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/`), or run the loop through the Agent tool (`cio.md` Stage 0b) |
| `reading.py plan` refuses: "this run already has reader extractions" | A new plan changes passage ids under the existing reads. Re-plan only for a stated reason: `reading.py plan RUN_DIR --replan "<reason>"` moves the extractions to `corpus/reading/superseded/<time>/` and marks the earlier launches superseded (the reading audit lists them as warnings, not failures) |
| A VIEW REQUIRED page is too small or sideways to read | `reading.py render RUN_DIR <chunk> <page> --dpi 200 [--rotate 90|270] [--parts 2]` writes PNGs under `_cache/reading/render/`; Read them. The reading audit counts a read of these images as a view of the page |
| Plan warns "images not checked" | poppler's `pdfimages`/`pdfinfo` were missing or the PDF was not found, so pages with raster images were not marked for viewing; `COVERAGE.md` says so. Install poppler and re-plan before any reader starts |
| Reading audit FAIL | `qc/READING_AUDIT.md` names the agent and what is missing: re-launch the reader for its chunks, re-invoke a specialist to read the dossiers it skipped, or record a model/effort deviation as an accepted limitation |
| Session not on Opus at xhigh | Switch in the model picker before starting; the CIO asks at Stage 0 and records your answer |
| Audit opinion Qualified or Adverse | Resolve each finding in `cio/audit_resolutions.md`; re-invoke the auditor for Critical findings until each is Closed; `validate_run.py --stage final` will not pass otherwise |
| `Merged ledger is stale` | Re-run `merge_ledgers.py` |
| Run outcome not `complete` | Read the `finalize_run.py` output and `run_manifest.json` `status_history` |
| Push failed | Commits are local. Fix authentication, or rebase or merge manually if the branch diverged (never force-push). |

## 9. Data hygiene

- Source documents are not committed. Use `RUN_DIR/_cache/` (git-ignored) for downloads, and cite by URL or identifier and locator.
- The untracked `research/companies/BAJFINANCE/raw_financials.md` predates this system. Its title says "audited", but it has an aggregator layout, quarterly data and no source line. Treat it as an unverified lead.
