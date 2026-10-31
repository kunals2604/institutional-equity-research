# Quality Control — {company} ({ticker}) · run {run_id}

## Automated checks
Paste the summary of `qc/auto_checks.json` (errors, warnings, pass/fail per target).

## Manual checklist
| Check | Result | Notes |
|---|---|---|
| Canonical layer names everywhere; four layers analysed separately; fit excludes price | | |
| ≥12 decision-critical claims re-verified; ≥3 calculations recomputed | | |
| Single cost-of-capital set; price × shares reconciles to market cap / EV | | |
| Standalone/consolidated and FY/TTM labelled consistently | | |
| Contradiction log complete; every resolution has an independent check | | |
| No FACT rests only on tier 6–7; no probability without basis/band | | |
| Insufficient-evidence triggers (SCORING.md §8) checked | | |
| BQ judged without price; IA not derived from BQ | | |
| Thesis-disproof questions all answered | | |
| No out-of-scope advice (sizing / pairs / shorts) | | |
| Cross-company calibration comparison done | | |
| Document map built from both channels; every missing core document searched; every cross-check flag handled | | |
| Price is the exchange close (bhavcopy URL and SHA-256); ADTV and price history from exchange data | | |
| Zero-loss rule: decision-critical numbers verified on the rendered page and with `doc_text.py verify`; flagged pages read visually | | |
| Every dimension carries its own confidence; the decision drivers, must-pass table, required margin of safety and conviction are in the report; the verdict path is stated | | |
| Independent audit run; every Critical/Major finding resolved; Critical findings Closed by a re-audit | | |
| Ground-truth (scuttlebutt) evidence reflected in the synthesis and variant perception | | |
| SME runs: SME Enhanced Scrutiny sections present | | |
| Reading on: reading stage complete (`reading.py status --strict`); every critical chunk read twice and every disagreement resolved | | |
| Reading off (3.2.0): digest complete (`digest.py status --strict`); every number run through `digest.py confirm`; no digest lead cited as FACT (`DIGEST_AS_FACT`) | | |
| Reading audit PASS (`qc/READING_AUDIT.md`): agents on their pinned models and efforts, specialists read their packs, and with reading on readers received every line and opened every VIEW REQUIRED page | | |
| Auditor's reading or digest sample: no material omission (or the affected chunks re-read, the leads re-checked) | | |
| Final report carries the run's coverage record (`corpus/reading/COVERAGE.md` or `corpus/digest/COVERAGE.md`) unchanged; no report states its own reading coverage | | |
| 3.2.0: sector modules selected in Stage 0; every module step Done with its metric evidence, or in the gap register | | |
| 3.2.0: forecasting base path valued in a Stage-3 valuation follow-up; `calc/forecasting_reconcile.json` gaps explained | | |
| 3.2.0: every registry item has a disposition; theme briefs, layer drafts and sections pass their checks; every `immaterial` call read | | |
| 3.2.0: every contradiction candidate in the contradiction log; every layer fit >10 points from its analyst's proposal states the deviation | | |
| 3.2.0: `key_quantities` stated alike throughout; `synthesis.py integration` no errors, warnings explained; report assembled from section files | | |
| 3.2.0: auditor's Evidence Integration Audit findings resolved | | |
| Structured exchange filings (`corpus/STRUCTURED.md`) used before reading for the facts they cover | | |

## Cross-company calibration
Closest companies on COMPANY_SCOREBOARD.csv and whether relative BQ / IA ordering is defensible:

## Accepted limitations
(each with reason and why it does not touch a decision-critical claim)

## QC status: PENDING
