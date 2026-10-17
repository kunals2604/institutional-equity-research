# Verification log — financials (BHARTIARTL, run 20261012T132311Z)

Basis: consolidated. Units in source: INR million (converted /10 to INR crore in `financial_history.csv`).
Tolerance per RESEARCH_PLAYBOOK §3: >1 % or a >1 pp ratio change = discrepancy.

## Coverage of tier-1 reading
| Years | Primary document read | Second tier-1 read (cross-check) | Status |
|---|---|---|---|
| FY2026 | AR FY2026 Consolidated FS (airtel.in PDF, pp.424-428, notes 18, 20, 29-34) | Q4FY2026 audited results (FilingForge:b5c6beda…, OCR text) | revenue, PAT, CFO, BS totals identical |
| FY2025 | AR FY2025 (FilingForge:ef981e1b…) | AR FY2026 comparatives | identical |
| FY2024 | AR FY2024 (FilingForge:fa581014…) | AR FY2025 comparatives | totals identical; S&M (81,326 → 107,882) and other expenses (86,618 → 60,062) reclassified; EBITDA unchanged |
| FY2023 | AR FY2023 (FilingForge:80756f27…) | AR FY2024 comparatives | identical |
| FY2022 | AR FY2022 (FilingForge:1c7c2552…) | AR FY2023 comparatives | identical (segment table restated: India mobile 632,054 → 629,149) |
| FY2021 | AR FY2021 (FilingForge:3e7fff81…) | AR FY2022 comparatives | statements identical; EPS restated -27.65 → -27.52 for the bonus element of the Oct-2021 rights issue |
| FY2020 | AR FY2020 (FilingForge:49889f5f…) | AR FY2021 comparatives | **Discrepancy (restatement)**: P&L restated to continuing operations after Infratel deconsolidation: revenue 875,390 → 846,765 (-3.3 %); EBITDA incl. OI 369,343 → 357,891. Balance sheet reclassifications: trade payables 250,199 → 243,668; provisions 451,093 → 450,722. Series keeps the as-reported FY2020 (scope consistent with the FY2020 balance sheet). |
| FY2019 | AR FY2020 comparatives | AR FY2019 (FilingForge:e52e5a27…) | **Discrepancy (reclassification)**: CFO 197,880 (AR19) vs 200,702 (AR20) = +1.4 %; finance costs 110,134 vs 106,222 with offsetting finance income; opex 549,613 vs 550,164 (-0.1 %); TA 2,751,975 vs 2,751,560. Revenue identical 807,802. EPS 1.03 originally → 0.96 rights-adjusted. |
| FY2018 | AR FY2018 (FilingForge:AR-532454-2018) | AR FY2019 comparatives | **Discrepancy (reclassification)**: revenue 836,879 (AR18) vs 826,388 (AR19) = -1.25 %; opex 536,088 vs 525,597; EBITDA (incl. OI) 303,279 unchanged. Series keeps AR18 values; EBITDA margin effect +0.4 pp if restated. Screener (tier 5) shows 82,639 crore (= restated). |
| FY2017 | AR FY2018 comparatives | AR FY2017 (FilingForge:AR-532454-2017) | **Discrepancy (reclassification)**: CFO 292,309 (AR17) vs 282,799 (AR18) = -3.3 % (dividend received 9,510 moved to investing); TA 2,327,502 vs 2,332,652; trade receivables 49,838 vs 47,402; bank deposits 3,360 vs other bank balances 38,166. P&L identical. |
| FY2016 | AR FY2017 Ind AS comparatives | Q4FY2016 Quarterly Report (IFRS, tier 3) | GAAP difference: revenue identical 965,321; PAT attributable Ind AS 60,767 vs IFRS 54,842 (+10.8 %, exceptional items 21,741 vs 14,505 and tax); equity 667,693 vs 656,301 (+1.7 %); CFO 279,423 vs 283,205 (-1.3 %). |
| FY2011-FY2015 | IFRS consolidated statements in Q4 Quarterly Reports (tier 3; "extracts from audited consolidated financial statements prepared in accordance with IFRS") | FY2013-FY2015 cross-checked to AR FY2017 Financial Highlights p.10 (revenue 769,045 / 857,461 / 920,394; net profit 22,757 / 27,727 / 51,835; net debt 583,567 / 605,416 / 668,417) | Not verified against statutory (Indian GAAP) statements; verified=N. FY2011-FY2012 are pre-IFRS 11 (Indus 42 % proportionately consolidated): FY2013 revenue 803,112 (old basis) vs 769,045 (IFRS 11 restated) = -4.2 % scope break. |

## Escalation
Four sampled years (FY2017, FY2018, FY2019, FY2020) show >1 % differences between first and later presentations. All are documented reclassifications/restatements, not transcription or aggregator errors. Every year FY2016-FY2026 was already read in full from tier-1 statements (full verification for revenue, EBITDA, PAT, equity, debt, CFO, capex, shares), so no further escalation was needed.

## Aggregator cross-check (Screener consolidated page, tier 5, fetched 2026-10-12 via WebFetch, navigation only)
| FY | Screener sales | Ours (revenue) | Screener op. profit | Ours EBITDA | Screener net profit | Ours PAT | Screener CFO | Ours CFO | Note |
|---|---|---|---|---|---|---|---|---|---|
| FY2015 | 96,101 | 92,039 (IFRS) | 33,602 | 31,293 | 5,048 | 5,308 | 28,059 | 27,602 | Screener on Indian GAAP (Indus proportionate); ours IFRS |
| FY2018 | 82,639 | 83,688 | 30,079 | 30,079 | 2,184 | 2,184 | 29,854 | 29,854 | revenue restated in AR19 |
| FY2021 | 100,616 | 100,616 | 45,279 | 45,372 | -12,364 | -12,364 | 48,205 | 48,205 | 0.2 % EBITDA difference |
| FY2024 | 149,982 | 149,982 | 77,893 | 78,292 | 8,558 | 8,558 | 78,898 | 78,898 | 0.5 % EBITDA difference |
| FY2025 | 172,985 | 172,985 | 85,060 | 93,159 | 37,481 | 37,481 | 98,332 | 98,332 | **8.7 % EBITDA gap**: Screener deducts items we do not (likely charity/other non-operating classification); tier-1 statements govern |
| FY2026 | 210,973 | 210,973 | 116,514 | 119,675 | 33,823 | 33,823 | 122,230 | 122,230 | 2.6 % EBITDA gap, same cause |
Screener "borrowings" include lease liabilities (FY2026 195,412 = 121,671 + 73,740).
