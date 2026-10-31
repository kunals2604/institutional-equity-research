# v4.0 defect register

The defects found in methodology 3.2.0 (commit 8f7e65d) by the read-only code audit, the review of the stored runs and the
v4.0 design review, all on 2026-10-31. Step 1 of the v4.0 build works through this list. Every fix starts with a test
that fails. `Status` changes as fixes land.

**How far to trust this list.** Every item was found by reading the code. Those marked **ran** were also confirmed by
executing the code. None has been observed in a real 3.2.0 run, because no 3.2.0 run has ever finished; the only real
evidence behind them is the stored Bharti run (methodology 2.2.0) and the stopped BAJFINANCE run (3.1.0).

Severity: **H** can let a wrong number, a dropped finding or a false pass through without an error. **M** breaks a stated
contract or a pipeline path. **L** is smaller drift.

## A. Wrong numbers can pass

| ID | Sev | Defect | Failure | Where | Status |
|---|---|---|---|---|---|
| A1 | H | Digest confirmation ignores order of magnitude (**ran**) | `amount_in` strips trailing zeros, so a summary's 2,500 crore gets a page-confirmed mark against 25,000 printed in the filing; `calibrate` recall is inflated too | `digest.py:210` | Fixed |
| A2 | H | `NUMBER_NOT_SEEN` has the same blindness, by design | Digits compare without separators, decimal point or leading and trailing zeros (change log v3.1.0 item 16), so a 10x error reads as seen. Needs a unit-normalised magnitude check | `verify.py` | Fixed |
| A3 | H | A digest number can become a FACT | Exact-URL match misses `www` or query-string variants; the digest pack counts as seen; unopened sources up to 3 claims or 10 % only downgrade to major | `verify.py:321,167,368` | Fixed |
| A4 | H | FACTs with prose sources skip the source checks | `source_url_or_id = "BSE filing, Jan 2024"` skips SOURCE_NOT_OPENED, PAGE_NOT_OPENED and the verifier sample | `verify.py:340,347,599` | Fixed |
| A5 | H | A waiver covers a whole check, not a claim | Waiving `financials-NUMBER_NOT_SEEN` for one claim silences every later unseen number from that specialist | `verify.py:556,557` | Fixed |
| A6 | H | A specialist can waive its own blocking finding | `verify.py` is not in `CIO_ONLY_SCRIPTS`; waivers record no actor; `qc/` is not fingerprinted | `agent_driver.py:132,661`, `verify.py:931` | Fixed |
| A7 | M | Digest IDs collide; `confirm` is optional | Two facts from one quote share an ID and one takes the other's page; skipping `digest.py confirm` still gives status complete | `digest.py:145,416,636` | Fixed |

Calibrated on the real Bharti sessions (552 FACT and MANAGEMENT STATEMENT claims): the new `SCALE_NOT_SEEN` raises 62,
mostly crore-to-million conversions, so it is major (one correction round) rather than blocking; `SOURCE_UNCHECKABLE`
raises 0, so it blocks. A true unit conversion no longer page-confirms a digest item: it stays a lead, flagged
`scale_differs`, which is the safe direction.

## B. Evidence lost in Stage 3

| ID | Sev | Defect | Failure | Where | Status |
|---|---|---|---|---|---|
| B1 | H | Open verification findings never reach the registry | Reads `open` or `findings`; `verify.py` writes `run_findings` and `specialists`. The `verification` kind is always empty | `synthesis.py:264`, `verify.py:897` | Open |
| B2 | H | Contradictions in split themes bypass adjudication | `T[0-9].md` skips `T1.p2.md`, so a candidate raised only in a part brief is invisible to `followups`, `packet` and integration | `synthesis.py:896,1197,715,731` | Open |
| B3 | H | Gating items have two unchecked exits | `unverified_lead` is not checked for provenance and a `superseded` pointer need not exist; `check_layer` validates no pointers | `synthesis.py:1112,735,742,841` | Open |
| B4 | H | "Adjudicated" means mentioned | A bare ID in the log passes; positions, the independent check and the resolution are never checked | `synthesis.py:906`, `validate_run.py:302` | Open |
| B5 | H | Stage 3 order not enforced | Layers run with no check of themes, staleness or the log; writers test only that a scorecard exists; `check_layer` records no input hash | `agent_driver.py:893,897`, `synthesis.py:787` | Open (Step 4 completes it) |
| B6 | M | Documented Stage 4 order always fails first time | `qc/verification.json` is a registry input and carries `checked_at`, so `verify.py run` makes the registry stale | `synthesis.py:450`, `verify.py:897` | Open |
| B7 | M | Dead ends with no tool path | `needs_follow_up` passes `check_theme` but fails integration, and a theme whose answer went elsewhere never re-runs; a gating `contested` item with no claims can never count as reached (**ran**) | `agent_driver.py:908`, `synthesis.py:733,938,392` | Open |
| B8 | M | SME runs cannot be assembled | The SME section is dropped as "not a section of the final report" | `synthesis.py:1280,1299`, `research_lib.py:978` | Open |
| B9 | M | The CIO packet misses its contract | Layer proposals are empty; it is not rebuilt after follow-ups; "every item has a disposition" is hard-coded; over budget only logs | `synthesis.py:1195,1228`, `cio.md:326` | Open |
| B10 | M | Material findings are listed, not blocked | `cio.md` says an unreached material item is an error; only gating items are | `synthesis.py:1112`, `cio.md:439` | Open |
| B11 | M | Key-quantity check gives false failures (**ran**) | Label "Price" fails on `price_timestamp` and "Price-to-book"; `1000` against `1000.0` fails | `synthesis.py:1002` | Open |
| B12 | M | Cluster IDs truncate (**ran**) | `other:cost/income` stops the ID at the slash, so it reads as undispositioned | `synthesis.py:578,595`, `research_lib.py:231` | Open |
| B13 | M | Split-theme checkpoints are unwritable | `T1.p2` is told to write to `workpapers/T1_p2/`, outside its allowed directory | `agent_driver.py:815,781` | Open |
| B14 | M | **Gating over-fires on real data** (**ran** on the Bharti replay) | 112 of 1,407 items are gating, 59 only by dimension; a spot-check of 14 found 4 or 5 real red flags; "default" matched "default-spread". Only 22 of 112 have all their claims in the real report, so the rule forces about 90 errors. Fix by content, not author or substring; hand-label the 112; owner confirms | `synthesis.py:414` | Open |

## C. Engine

| ID | Sev | Defect | Failure | Where | Status |
|---|---|---|---|---|---|
| C1 | H | **Sleep aborts are invisible** (**ran**: measured in the transcripts) | One chunk hit 42 "computer was asleep" stream aborts; four launches moved the weekly meter 40 points for $8 recorded. `StreamSuspended` appears nowhere in `scripts/` or `docs/`. `caffeinate -s` works on mains power only | `agent_driver.py:1813` | Open |
| C2 | H | A job can pass having produced nothing | `a.check()` alone closes a job: follow-ups without `--output`, re-audits reusing a name, zero-item digests, empty verifier samples, checkpoints of a passing report. Real case: librarian J001 was denied Bash, found nothing and passed | `agent_driver.py:1556,1564,664,700`, `digest.py:229,636`, `verify.py:840` | Open |
| C3 | H | Stage 3 follow-ups can lose the brief | `a.prompt = message` stores only the fix text, then a later fresh session uses it as the base, with no RUN_DIR, identity, cutoff or sector modules | `agent_driver.py:2083,2095` | Open |
| C4 | H | `resumes` never resets | A third abort across a multi-day specialist abandons it | `agent_driver.py:1425,1545` | Open |
| C5 | M | State files are neither atomic nor locked | A kill truncates `jobs.json`; `validate_run` holds the manifest for its whole run, so an engine record written meanwhile is lost | `research_lib.py:1725`, `reading.py:288`, `manifest.py:64`, `validate_run.py:198,338` | Open |
| C6 | M | `window_cost` is biased | Divides recorded cost by meter movement, so failed streams and any other usage pollute it. Measured clean figure is about $166 a week, not the $38 it reports | `agent_driver.py:2146,2258` | Open |
| C7 | M | Weekly ceiling can lapse | An event carrying only `five_hour` replaces the record, so the 95 % reserve passes with no weekly data (trigger unconfirmed) | `agent_driver.py:1306,1284` | Open |
| C8 | L | Liveness and resume gaps | A reused PID hangs the engine; hand-over skips `CONTINUATIONS`; `--parallel` runs a reduce with its parts; failed jobs restart with no note; `digest` and `events` re-run passed jobs; `events --dry-run` raises | `agent_driver.py:1431,1537,890,2045,2446,2509` | Open |

## D. Forecasting

| ID | Sev | Defect | Failure | Where | Status |
|---|---|---|---|---|---|
| D1 | H | Handoff to valuation is prose only | No script references `forecasting_to_valuation`; Stage 3 passes with no reconcile and no re-valuation | `synthesis.py:276`, `cio.md:346` | Open |
| D2 | H | `reconcile` reports agreement when nothing was compared (**ran**) | Mismatched inputs give empty flags and "agree within the thresholds", exit 0 | `forecast_tools.py:351,292` | Open |
| D3 | M | Year-1 growth silently 0 % (**ran**) | Without `base_revenue` the first step divides by itself; a model failing its tie is still written | `forecast_tools.py:256,355` | Open |
| D4 | M | ROE compared on a fixed base (**ran**) | Identical profit paths gave 18.0 % against 51.9 %, a spurious contradiction | `forecast_tools.py:306` | Open |
| D5 | M | `valuation.md` command cannot run | Passes a nonexistent `--verify` and omits the required `--end`, so `market_data.py` exits 2 | `valuation.md:41`, `market_data.py:290` | Open |
| D6 | M | `fy_end` key never matches | The manifest key is `fiscal_year_end`, so every company is treated as March year-end and non-March events match the wrong year | `digest.py:447,510`, `reading.py:2437,2601` | Open |

## E. Scoring honesty

| ID | Sev | Defect | Failure | Where | Status |
|---|---|---|---|---|---|
| E1 | H | Report says "no override" while one manual score decided the verdict | Bharti: IA4 set to 2 where the tool gave 100; with 100, IA is about 48, HOLD. Show every departure from a computed guide (disclosure, not a block) | `research_lib.py:1640` | Open |
| E2 | M | The ladder leaves price bands undefined | Bharti: 1,175–1,200 and 1,575–1,600 carry no decision | `valuation_tools.py:343` | Open |
| E3 | M | Hurdle documentation conflicts | The skill says default 0.12; policy says null. Nothing compares `hurdle_rate` with the computed cost of equity; `outcomes.py:334` treats a missing hurdle as 0 | `SKILL.md:21`, `new_run.py:65` | Open |

## F. Contracts and enforcement

| ID | Sev | Defect | Failure | Where | Status |
|---|---|---|---|---|---|
| F1 | M | Roster and counts are stale | "ten", "nine", "fifteen" agents across 15+ files, including `templates/cio_analysis.md`, copied into every new run | `README.md:3,16,32`, `PROJECT_INSTRUCTIONS.md:3`, `SCORING.md:398`, others | Open |
| F2 | M | Model contracts contradict the code | Opus at high reads every chunk; docs say xhigh and Sonnet-only in places | `MODEL_POLICY.md:9,38,40,68,110`, `CLAUDE.md:6`, `cio.md:103`, `reader.md:3` | Open |
| F3 | M | Injection rule missing where access is widest | Absent from `cio.md`, the three readers and the constitution | | Open |
| F4 | M | `--cutoff` is mostly a label | Unenforced in `digest`, `connectors`, `corpus`, `fetch_source`, `browser`; no placeholder reaches specialists; `2026-13-45` is accepted | `new_run.py:79`, `agent_driver.py:602` | Open |
| F5 | M | A replay would overwrite live state | Ordering uses run IDs, so a 2018-cutoff run today replaces the scoreboard row and `latest_run.txt` | `scoreboard.py:101`, `finalize_run.py` | Open |
| F6 | M | Run plumbing is loose | `reading` runs on a reading-off run; `research_cutoff`, `sector_modules`, `fiscal_year_end` and `price` stay mutable; `effort_override` takes any string | `agent_driver.py:2439`, `manifest.py:28` | Open |
| F7 | M | Write confinement is weaker than stated | The auditor has unrestricted Bash and no guard; new files are ignored; the FilingForge deny rule is hard-coded | `agent_driver.py:693,704,1200,937` | Open |
| F8 | M | Independence checks have gaps | `cd <run>; cat cio/scorecard.json` matches nothing; `evidence_ledger.csv` is not denied; read denies do not bind Bash | `reading_audit.py:217`, `agent_driver.py:339` | Open |
| F9 | M | Verification coverage gaps | Follow-up claims are never sampled; no freshness check against later ledger edits; the CIO check silently skips with no transcript | `agent_driver.py:1975`, `validate_run.py:77`, `verify.py:807` | Open |
| F10 | L | Smaller drift | `--update` ignored; split key unused; docstring wrong on `review`; version stamped from current rather than run; `new_run` dirty check omits `config/` and `templates/`; `assemble` errors before Stage 4 exists | `synthesis.py:563,1353`, `validate_run.py:344`, `build_scorecard.py:145`, `new_run.py:33` | Open |
| F11 | S | Analysts may be unable to run their own check (suspected) | `Bash(python3 scripts/synthesis.py check-:*)` may need a word boundary; one headless test settles it | `agent_driver.py:764,808` | Open |

## Stated rules with no mechanical check

| Rule | Status today |
|---|---|
| Material arithmetic from scripts | Not enforced: formula text and inputs only (`research_lib.py:772`) |
| Never edit legacy runs or `archive/` | Not enforced (`.claude/settings.json` has no deny rule; Step 10 hook) |
| Never overwrite a previous run | Partial: `new_run.py:113`, `validate_run.py:39`; not `synthesis.py:1301`, `verify.py:904`, `finalize_run.py:108` |
| CIO-only scoreboard and git | Partial: prefix denies; `python3 ./scripts/…` bypasses them |
| Quantitative claims carry a metric key | Partial: MANAGEMENT STATEMENT and empty `value` exempt; any `other:` accepted |

## Warnings where the documents imply a block

Layer-fit deviation over 10 points (`synthesis.py:1145`); over-budget packet (`:1228`); placeholder contradiction log, empty
gap register, thin CIO analysis (`validate_run.py:314-318`); PAGE_NOT_OPENED, CHECKLIST_EVIDENCE and CLAIM_UNVERIFIABLE
(`verify.py:75,77,92,576`); tier-6 or 7 FACT (`research_lib.py:770`); missing crosswalk fields (`:678`); citing a peer's claim
in an initial report (`:641`).
