# Institutional Equity Research

A Claude Code–native, multi-agent research system for evaluating listed companies, run like a fund for one owner's
capital. Indian equities (NSE and BSE) first; US companies (NYSE, NASDAQ) on the same method. A **CIO** (the main
session) acquires and cross-checks the company's filings, runs eleven **independent specialists** that never see each
other's work, verifies every specialist against its own sources, builds the report through a **synthesis pipeline**
that gives every piece of evidence a recorded fate, and writes a **verdict that is a reasoned judgment**: scores,
must-pass tests and the price ladder inform it as a computed guide shown beside it, and never decide it. An
**independent auditor** checks the draft before it can pass QC, and the owner makes the final call. Every material
claim is traceable to a source location.

```text
/scan 2026-11-04                                   # every company in the warehouse, as a lead list (scripts only)
/triage TVSMOTOR                                   # one session: KILL, or CONTINUE with the questions to answer
/research-company "TVS Motor Company Limited" TVSMOTOR NSE      # a full run, at the standard preset
/run-status TVSMOTOR                               # where it is, what it has spent, how to go deeper
/deepen <RUN_ID> --profile deep                    # the same question, deeper, reusing what was done
/decide <RUN_DIR> --action buy --reason "..."      # the owner's own decision, recorded apart from the verdict
```

## How a run moves

`config/pipeline.json` lists the steps; `scripts/orchestrate.py` decides what comes next from the run's files alone
(so a crash or a lost session loses nothing) and runs every script and engine step itself, stopping only where the CIO
must judge. Each step ends when its check passes, never on an exit code.

| Stage | What happens |
|---|---|
| 0 Acquisition | Identity and price (the exchange close); the filings indexed and downloaded from the exchanges, the IR site, the Internet Archive and the local library, cross-checked (`corpus/DOCUMENT_MAP.md`); structured filings; a ten-year events timeline from the web; what the warehouse already knows, as of the cutoff (`corpus/facts/`); sector modules; three to ten key questions |
| 0b / 0c Reading | Switch `reading` on: every in-scope page read once and recorded, critical sections twice. Off (the default): web summaries recorded as tier-6 leads, each number page-confirmed by script |
| 1–2 Specialists | Financials, filings, industry, scuttlebutt, moat, management, concalls, forecasting, valuation, special situations, bear case: one at a time, each verified against its own transcripts and by an independent verifier the moment it finishes; an early-stop pause for a disqualifying flag; the gap loop; git batch 1 |
| 3 Synthesis | The evidence registry; theme analysts give every item a disposition; the CIO adjudicates contradictions; four layer analysts; the CIO decides from a bounded packet and writes the verdict's reasoning (for, against, the judgment, and where it departs from the computed guide); adversarial review of every verdict; section writers; the report assembled as a build artifact |
| 4 Audit and publish | The reading and independence audit; the independent auditor (with planted canaries to measure what it catches); QC; finalization (scoreboard, pointer, decision record); facts promoted to the warehouse; transcripts archived; git batch 2 |

**Depth is a dial, and always disclosed.** Fourteen documented switches (`docs/SWITCHES.md`) grouped in four presets:
lean (a design target, unmeasured), standard (about $340–380, the default), deep (about $1,400) and max. Every report
ends with a Depth Disclosure: what was off, what that may cost in confidence, and the exact command to go deeper. No
switch caps a verdict or a confidence level.

**The four investment layers (immutable):** Layer 1 — Bedrock Compounder · Layer 2 — High-Growth Business · Layer 3 —
Cyclical / Event-Driven Opportunity · Layer 4 — Venture-Style / Optionality Bet.

**Two scores, never mixed:** Business Quality (0–100, price-independent) and Investment Attractiveness (0–100, at the
verified price), each with fixed dimensions, gates and confidence.

## Around the runs

| | |
|---|---|
| Warehouse | `research/warehouse/eqr.sqlite`: point-in-time prices (NSE and BSE bhavcopies; US daily closes) and reported facts (exchange XBRL and EDGAR, each with the day it was filed), plus the verified facts of finished runs, never their conclusions. Agents never read it; a run gets what was known at its cutoff |
| Funnel | `scan.py` (every company as known on a date, a rank that orders and never decides), `triage.py` (one session, KILL or CONTINUE), child runs (`new_run.py --deepen` and `--refresh`, which reuse a parent's work by copy and never change it) |
| Base rates | `base_rates.py`: how often companies actually did what a forecast assumes; survivor-biased, and every result says so |
| Jurisdictions | `config/jurisdictions/IN.json` and `US.json`: sources, units, filings, regulators and words. A US run's specialists are told what the methodology's Indian words mean there |
| Decisions and outcomes | `decide.py` (the owner's call), `ideas.py rank`, `outcomes.py` (predictions scored, verdicts judged against the hurdle and the market over the same months) |
| Guard | A main-session hook (`scripts/guard.py`): a finished run, an assembled report, `archive/` and the scoreboard are never hand-edited |

## Repository map

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Compact session instructions |
| `.claude/agents/` | The agent definitions: `cio`, the eleven specialists, `auditor`, `verifier`, the readers, `librarian`, `historian`, `digest`, `triage` and the synthesis roles |
| `.claude/skills/` | `/research-company`, the CIO's stage skills, the owner's skills (`/run-status`, `/switches`, `/scan`, `/triage`, `/deepen`, `/refresh`, `/decide`, `/ic`, `/rank`, `/postmortem`) and the investment constitution |
| `methodology/` | Scoring (the verdict as a judgment, §0), evidence standards, report contracts, research playbook, reading schemas, synthesis, model policy, metric dictionary, sector playbooks (19 sections and their modules), source guide, investor lenses |
| `config/` | The investment policy (no position or risk limits), switches and presets, the pipeline, jurisdictions, data sources |
| `research/companies/` | One directory per run; `latest_run.txt` points to the latest finished one. `COMPANY_SCOREBOARD.csv` indexes them |
| `research/outcomes/`, `research/funnel/`, `research/warehouse/` | Decisions and outcomes; scans and tear sheets; the warehouse (gitignored) |
| `scripts/`, `tests/` | Deterministic tools and their tests (standard library only) |
| `docs/` | Operations, architecture, switches, the change log, the v4.0 defect register |
| `archive/` | Pre-migration definitions (non-operative) |

## Requirements

- Claude Code with Opus and Sonnet (and Haiku for second reads). Models and efforts are pinned per agent in
  `methodology/MODEL_POLICY.md`; the CIO session runs on Opus at xhigh.
- Web search and fetch enabled: research depends on retrieving primary documents.
- Python 3.9 or newer, standard library only.
- For a US run: `EQUITY_RESEARCH_USER_AGENT` set to a name and contact (SEC asks for it). For the batch reading
  transport: `ANTHROPIC_API_KEY` (it spends real money).

See `docs/OPERATIONS.md` for running, resuming, deepening and troubleshooting, and `docs/FRAMEWORK_CHANGES.md` for what
changed in each version.
