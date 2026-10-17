# Quality Control — Bharti Airtel Limited (BHARTIARTL) · run 20261012T132311Z

## Automated checks

`python3 scripts/validate_run.py RUN_DIR --stage final` → **final stage: PASS (0 errors, 13 warnings, 28 targets)**, run 2026-10-17. Outputs are in `qc/auto_checks.json`, `qc/evidence_stats.json` and `qc/numeric_conflicts.csv`.

| Target | Result |
|---|---|
| Nine specialist reports (financials, filings, management, industry, moat, concalls, valuation, bear-case, special-situations) | PASS, 0 errors |
| Ten specialist and follow-up ledgers, plus the CIO ledger | PASS, 0 errors. The 13 warnings are all "FACT supported only by tier 6 source": BEAR-C034, C064–C067; FIL-C049, C059, C066; MOAT-C025, C056; VAL-C036, C038, C056 |
| `bear-case_followup_1.md` and its ledger (adversarial review) | PASS (0 errors, 0 warnings) |
| `cio/scorecard.json` (`validate_scorecard.py`) | PASS (0 errors, 0 warnings) |
| `cio/final_report.md` (`validate_report.py --kind final`) | PASS (0 errors, 0 warnings) |
| Numeric conflicts (`reconcile_numbers.py`) | 10 flagged; all 10 adjudicated in `cio/contradiction_log.md` (N1–N10), citing the conflicting claim IDs |

**Evidence statistics** (`qc/evidence_stats.json`):
- 808 claims in total.
- Primary share: 90.3% overall, with valuation the lowest specialist at 65.5%.
- NOT_LOCATED share: 0.9%.
- Low-tier FACT share: 7.9% overall, with bear-case the highest specialist at 19.6%.
- No threshold breached. The lowest specialist count (valuation, 58 claims) is above the minimum of 25.

**How the 13 tier-6 warnings were handled:**
- Each is flagged at confidence M or L in its ledger and listed in the reporting specialist's missing-evidence section.
- None supports a decision-critical number without corroboration:
  - The ICIL share count and price were re-verified at tier 1 [CIO-C035].
  - The S&P BBB+ upgrade and the Vodafone Idea relief are used only as context or at low confidence.
  - The Indus stake in VAL-C036 is cross-checked by SPS-C028 (tier 1).

## Manual checklist

| Check | Result | Notes |
|---|---|---|
| Canonical layer names everywhere; four layers analysed separately; fit excludes price | Satisfied | Validator checks the layer names. The L1/L2/L3/L4 blocks differ in substance (durability, scaling, cycle and catalyst, options). Price enters only the current-price assessments. |
| Historical Depth Standard met by every specialist, or exceptions justified | Satisfied | Every Data Coverage table meets the minimums. Stated exceptions: filings (pre-FY2017 annual reports unavailable over SSL), management (3 quarters missing from the IR archive), industry (peer 10-year margins), moat (operator-level AGR before FY2025), special-situations (corporate actions not traced back to listing), bear-case (long tail from an aggregator). None touches a decision-critical claim; financials provides 16 verified years. |
| ≥12 decision-critical claims re-verified; ≥3 calculations recomputed | Satisfied | 19 claims re-verified from primary sources, none contradicted. 5 calculations recomputed by re-running the scripts, all reproducing exactly: CIO-C050 to CIO-C054, plus CIO-C036. |
| Every `reconcile_numbers.py` conflict adjudicated; single cost-of-capital set; price × shares reconciles to market cap and EV | Satisfied | N1–N10 adjudicated. One set: Ke 11.68%, WACC 11.03% [CIO-C052]. Price CIO-C001 × shares CIO-C002 gives market cap CIO-C003. The share bridge to Mar-2026 reconciles [CIO-C036]. EV with minorities at market comes from VAL-C032. |
| Standalone/consolidated and FY/TTM labelled consistently | Satisfied | Consolidated throughout. Segment and TTM-Q1FY2027 bases are labelled. The Indus consolidation break (18-Nov-2024) is flagged wherever growth is cited. |
| Contradiction log complete; every resolution has an independent check | Satisfied with one partial | X1–X11 and N1–N10 each carry a CIO check. X6 (ICIL corporate-opportunity question) is honestly marked partly unresolved: the swap documents could not be retrieved. |
| Evidence-statistics thresholds met (or breaches explained); confidence consistent | Satisfied | No breach. BQ and IA confidence is set at Medium because of the two key-assumption dependencies (discount rate, multiple path), not because of source quality. |
| No FACT rests only on tier 6–7; no probability without a basis or band | Satisfied with disclosure | The 13 tier-6-only FACTs are flagged at M/L and none is decision-critical (see above). Every probability uses a constitution band with a stated reference class (X4, BEAR-C083, VAL-C047). |
| BQ judged without price; IA not derived from BQ | Satisfied | BQ dimensions cite only operating, financial and governance evidence. IA dimensions come from the price ladder and price-related claims. BQ enters only the verdict mapping. |
| IA1, IA2, IA4 match the price ladder (or the deviation is explained) | Satisfied with documented deviation | IA1 (23) and IA2 (35) equal the tool's anchors at INR 1,778.70. IA4 is a documented deviation: hurdle-adjusted 2 against the tool's 100. The reason is given in the scorecard and report, and the adversarial review judged the deviation economically correct (BEAR-C090). Both ladders are reported. |
| Variant perception, key debates, thesis-disproof, triggers, position risk, predictions and review date present | Satisfied | All sections present. 7 predictions with probabilities between 0.35 and 0.85. Review date 2027-02-28. |
| Symmetric adversarial review run when required | Satisfied | The draft verdict was AVOID, so bear-case was re-invoked (logged at stage 3) to steelman ownership. Outcome: the base case now carries one tariff round (CIO-C056); the verdict is unchanged (contradiction log X10–X11). |
| No out-of-scope advice (sizing beyond the IPS ceiling, pairs, shorts) | Satisfied | Only a position-risk profile is given. No sizing ceiling, because the IPS sets no limits. |
| Cross-company calibration done; prior predictions resolved where due | Satisfied (none available) | See the section below. There is no prior complete run, so no predictions were due. |
| Insufficient-evidence triggers (SCORING.md §8) checked | Satisfied | (a) Price and share count verified. (b) All nine specialists complete. (c) 19 of 19 re-verified claims confirmed from tier 1–2 sources (tier 5 for the two rate inputs, which are corroboration only). (d) FY2026 consolidated financials available. **No trigger holds.** |

## Cross-company calibration

`COMPANY_SCOREBOARD.csv` is empty: this is the first company scored under methodology 2.2.0. No same-version comparison is therefore possible. As an informal sanity check against the methodology's calibration meanings:
- **BQ 61 ("good but with an identifiable structural weakness").** This is defensible for a capital-intensive oligopolist whose through-cycle ROIC sits below WACC despite strong current returns.
- **IA 38 ("unattractive").** This is consistent with an E[IRR] below the risk-free rate.

The comparison must be repeated when the next company is scored, as `SCORING.md` §7 requires.

## Accepted limitations

Each has a reason, and none touches a decision-critical claim as used.

1. **ICIL swap documents not retrieved** (valuer's report, EGM statement, scrutiniser's report): NSE returned 403 and the IR site does not carry them. The share count and price are tier 1 [CIO-C035]. The fairness terms rest on tier-6 sources and affect only BQ7 within its band. Recorded as partly unresolved (X6).
2. **Jio DRHP/RHP not read.** Affects confidence in the tariff timing (X4). Already reflected in the Low–Medium confidence on D1 and in prediction P1.
3. **Vodafone Idea relief terms from press only.** Used as structure context at low confidence; no valuation input depends on it.
4. **Pre-FY2017 annual reports unavailable over SSL.** FY2011–FY2015 rest on tier-3 IFRS Quarterly Reports, used for through-cycle context only. The BQ1 median ROIC uses FY2017–FY2026 (tier 1).
5. **Rate inputs (Rf, ERP) from tier 5.** Two independent tier-5 sources agree on Rf within 1 bp [CIO-C047], and Damodaran's table is the standard ERP source [CIO-C048]. No tier-2 RBI/FBIL print was located.
6. **Report completed on 17-Oct-2026, five days after the 12-Oct-2026 cutoff.** No later information was used. The price snapshot is the cutoff close. Events after the cutoff (the Airtel Money admission on 14-Oct-2026; any Jio IPO pricing) are treated as scheduled, not as outcomes.
7. **Corpus defects reported to the owner:**
   - The FY2026 annual report is missing from the corpus; it was fetched from airtel.in.
   - The 14-May-2024 results file is labelled FY2023 but contains FY2024.
   - The Q1FY2025 transcript is in the library but the catalog lists it as missing.
8. **Six API session-limit interruptions during Stage 1.** All are recorded in the manifest. Every specialist resumed with its context intact and completed. No figures were reconstructed from memory: each specialist attested this, and the CIO's audit found no discrepancies.

## QC status: PASS
