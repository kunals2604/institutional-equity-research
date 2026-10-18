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

## Cross-company calibration
Closest companies on COMPANY_SCOREBOARD.csv and whether relative BQ / IA ordering is defensible:

## Accepted limitations
(each with reason and why it does not touch a decision-critical claim)

## QC status: PENDING
