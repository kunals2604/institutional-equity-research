# Master Contradiction Log — Bharti Airtel Limited (BHARTIARTL) · run 20261012T132311Z

Each block covers one material disagreement: between specialists, between a specialist and the CIO audit, or flagged by `scripts/reconcile_numbers.py` (10 numeric conflicts, tolerance 1%). No disagreement is resolved by taking a midpoint. Where a method decides the outcome, the method is stated.

**Summary.**
- **Numeric conflicts N1–N10:** none is a substantive disagreement about a fact. Six are definitional (different metric definitions or bases); four are different entities, scenarios or measures stored under one metric key.
- **Substantive disagreements X1–X9:** all are adjudicated below. Two stay partly unresolved: the documentary basis for the ICIL swap terms (X6), and the tariff-round timing (X4), which can only be judged as a probability.

---

## Part A — Numeric conflicts flagged by `reconcile_numbers.py`

### N1 — FY2026 consolidated EBITDA: ₹1,21,268 cr vs ₹1,19,674.5 cr vs ₹1,16,514 cr
- **Specialist positions:**
  - BEAR-C002: ₹1,21,268 cr, the company's Quarterly Report KPI basis.
  - FIN-C002: ₹1,19,674.5 cr, the `METRIC_DEFINITIONS` basis (revenue − operating expenses, excluding other income, post Ind AS 116).
  - FIN-C062: ₹1,16,514 cr, Screener aggregator.
- **Evidence for each:**
  - BEAR-C002 itself records that the statutory "profit before D&A, finance cost and exceptional items" is ₹1,22,492 cr including other income, and that the KPI line excludes other income and adds back items such as charity.
  - FIN-C002 is computed from the audited P&L lines.
  - FIN-C062 is a tier-5 classification.
- **Contrary evidence:** none on the underlying statements. The three figures measure different things.
- **Assumptions required:** none.
- **Independent check (CIO):** the company KPI margin of 57.5% (CIO-C041) reconciles to BEAR-C002. The FY2026 revenue in CIO-C010 matches the denominator of FIN-C002. [CIO-C041; CIO-C010]
- **Resolution:**
  - FIN-C002 (₹1,19,674.5 cr) is adopted as the run's `ebitda`, because it is the methodology definition.
  - BEAR-C002 is used only for company-convention multiples, as BEAR-C054 does.
  - FIN-C062 (aggregator) is rejected.
- **Confidence:** High. The definitional causes are documented in both ledgers.
- **Investment impact:** none on the conclusions. EV/EBITDA must state its basis (see N3).

### N2 — FY2020 equity issued: ₹39,339 cr vs ₹24,939 cr vs ₹14,400 cr
- **Specialist positions:**
  - BEAR-C021: ₹39,339 cr, the rights issue plus the QIP, gross.
  - MGT-C033: ₹24,939 cr, the rights issue only.
  - MGT-C034: ₹14,400 cr, the QIP only.
  - Related: FIN-C016 gives ₹39,181 cr net of issue costs, on a consolidated cash basis.
- **Evidence for each:** all four rest on the same tier-1 Board's-report and cash-flow figures.
- **Contrary evidence:** none.
- **Assumptions required:** none.
- **Independent check (CIO):** arithmetic. MGT-C033 + MGT-C034 = BEAR-C021, the gross total. FIN-C016 is the same total net of transaction costs.
- **Resolution:** this is components versus total, gross versus net. There is no disagreement. FIN-C016 (₹39,181 cr net) is used for capital-allocation arithmetic.
- **Confidence:** High.
- **Investment impact:** none.

### N3 — TTM EV/EBITDA: 10.1x vs 10.86x
- **Specialist positions:**
  - BEAR-C054: 10.1x on the company convention (market cap + net debt including leases and DoT liabilities, no minorities).
  - VAL-C031: 10.0x on the company basis, 10.9x including minorities at market value.
- **Evidence for each:** both use CIO-C001. Each states its definition.
- **Contrary evidence:** none.
- **Assumptions required:** whether minority claims (about ₹1.09 lakh cr at market, VAL-C032) belong in EV.
- **Independent check (CIO):** the minority claims at market are consistent with the listed-stake values special-situations computed separately (SPS-C075). For example, the 30% Hexacom minority is about ₹22,820 cr, and Airtel Africa's is about 20.9% of its market value. Excluding them overstates how cheap the equity is.
- **Resolution:**
  - VAL-C031 (10.9x, minorities at market) is the economic multiple the run uses.
  - The company-basis 10.0–10.1x is quoted only when comparing with the company's own history, which uses that definition.
- **Confidence:** High.
- **Investment impact:** IA5 and the historical-percentile cross-check use the economic basis.

### N4 — Expected annual return 2026–2031: 8.98% vs 4.69%
- **Specialist positions:**
  - VAL-C048: about 9.0% base, about 8% probability-weighted. This is the return decomposition, tagged ESTIMATE: 15% EPS growth and an exit P/E of 28x.
  - VAL-C049: E[IRR] of 4.69% (CALCULATION). This is the IRR of probability-weighted horizon value plus dividends.
- **Evidence for each:**
  - The decomposition assumes faster EPS growth and a retained premium multiple.
  - The DCF-based E[IRR] assumes the price converges to the scenario value at the cost of equity.
- **Contrary evidence:** bear-case B1 gives about −4% a year over three years at an exit P/E of 22x (BEAR-C057), which is lower than both.
- **Assumptions required:** the exit multiple, and EPS growth versus NOPAT growth.
- **Independent check (CIO):**
  - I re-ran `valuation_tools.py scenario-irr` on the cited inputs and reproduced 4.69% and an asymmetry ratio of 4.80 exactly [CIO-C054].
  - `METRIC_DEFINITIONS.md` names E[IRR] as the decision metric. The decomposition is a sanity check.
- **Resolution:**
  - E[IRR] 4.69% (VAL-C049) is adopted for IA2.
  - The decomposition (about 8%) is reported as an upper cross-check. Both are 3–7 pp below the 11.68% hurdle [CIO-C052], so the choice does not change the IA2 band direction.
- **Confidence:** High on the sign; Medium on the level.
- **Investment impact:** IA2.

### N5 — Market capitalisation on 12-Oct-2026: ₹11,09,998.5 cr / ₹11,10,088 cr vs ₹99,652 cr
- **Specialist positions:**
  - CIO-C003: ₹11,09,998.53 cr, fully paid shares only.
  - VAL-C003: ₹11,10,088 cr, fully paid plus the economic value of partly paid shares.
  - VAL-C036: ₹99,652 cr. This is **Indus Towers'** market cap, stored under the same `market_cap` key.
- **Evidence for each:** CIO-C003 and VAL-C003 both rest on CIO-C001 and CIO-C002. The ₹89.5 cr difference is the partly paid shares' value net of the unpaid call (`calc/cio_preflight_mcap.out`).
- **Contrary evidence:** none.
- **Assumptions required:** none.
- **Independent check (CIO):** `calc/cio_preflight_mcap.out` gives a total of ₹11,10,088.04 cr, which equals VAL-C003. The share count is reconciled in CIO-C036.
- **Resolution:**
  - VAL-C036 is a different entity, not a conflict.
  - CIO-C003 and VAL-C003 differ by definition only (0.008%).
  - The run uses ₹11,10,088 cr where partly paid shares matter and ₹11,09,999 cr otherwise.
- **Confidence:** High.
- **Investment impact:** none.

### N6 — "Market share" in QE Jun-2026: 40.5% vs 2.88%
- **Specialist positions:**
  - MOAT-C033: Bharti's share of top-4 access AGR, 40.5%.
  - MOAT-C061: **BSNL's** share of top-4 access AGR, 2.88%.
- **Evidence for each:** both use the same TRAI table.
- **Contrary evidence:** none.
- **Assumptions required:** none.
- **Independent check (CIO):** in the QE Mar-26 TRAI table, Bharti has ₹28,773.59 cr of ₹72,488 cr total access AGR, 39.69% [CIO-C046]. That figure is on total access AGR, consistent with IND-C034 (39.7%). MOAT-C033 uses a top-4 denominator (40.2% in QE Mar-26).
- **Resolution:**
  - Different entities, not a conflict.
  - The run's revenue-share measure is IND-C034 / CIO-C046 (all-access denominator). MOAT-C033's top-4 basis is noted as about 0.5 pp higher.
- **Confidence:** High.
- **Investment impact:** none. This is a monitoring baseline.

### N7 — FY2026 net debt including leases: ₹1,64,789 cr vs ₹1,67,988.9 cr
- **Specialist positions:**
  - BEAR-C005 and CON-C158: ₹1,64,788.8 cr, the company definition.
  - FIN-C027: ₹1,67,988.9 cr, the financials' definition.
- **Evidence for each:**
  - The company figure is in the Q4FY2026 Quarterly Report.
  - FIN excludes "other bank balances" from cash, because most of that balance is restricted mobile-money trust money (FIN-C041; FIL-C001 shows ₹13,206 cr of restricted cash).
- **Contrary evidence:** none.
- **Assumptions required:** whether restricted Africa mobile-money balances count as cash.
- **Independent check (CIO):** the Q4FY2026 filing shows net debt of ₹16,47,888 mn and a leverage of 1.29x [CIO-C039], which equals BEAR-C005 and CON-C158. FIN's conservative exclusion explains the 1.9% gap.
- **Resolution:**
  - Both figures are correct on their own definitions.
  - FIN-C027 is used for resilience analysis (conservative).
  - The company figure is used for comparison with company leverage history and CRISIL triggers.
- **Confidence:** High.
- **Investment impact:** none material (BQ5).

### N8 — Years with ROCE above the hurdle, FY2017–FY2026: 3 vs 5
- **Specialist positions:**
  - MOAT-C007: 3 of 10 years, at a 10–12% WACC placeholder (central 11% → 14.7% pre-tax).
  - MOAT-C067: 5 of 10 years at an 8–9% WACC. This is a sensitivity.
- **Evidence for each:** both come from the same company-reported ROCE series.
- **Contrary evidence:** none.
- **Assumptions required:** the WACC.
- **Independent check (CIO):**
  - The run's WACC is 11.03% [CIO-C052], which equals moat's central case (11.03% / (1 − 0.2517) = 14.74% pre-tax).
  - On the methodology ROIC (constant 25.17% tax, FIN-C024), only FY2026 (13.9%) clears an 11.03% WACC. The 10-year median ROIC is 7.1%, a spread of −3.9 pp (`calc/cio_bq_guides.out`).
- **Resolution:** MOAT-C007 (3 of 10 years) applies at the run's cost of capital. MOAT-C067 is a labelled sensitivity.
- **Confidence:** High.
- **Investment impact:** BQ1 (band 30–44) and the L1 return-duration test.

### N9 — "Price" on 12-Oct-2026: ₹1,778.70 vs ₹375.65
- **Specialist positions:**
  - VAL-C001 and CIO-C001: ₹1,778.70, BHARTIARTL.
  - VAL-C035: ₹375.65, the **Indus Towers** close, stored under the same `price` key.
- **Evidence for each:** both come from the NSE bhavcopy.
- **Contrary evidence:** none.
- **Assumptions required:** none.
- **Independent check (CIO):** the bhavcopy row for BHARTIARTL EQ shows a close of ₹1,778.70 [CIO-C001; CIO-C005].
- **Resolution:** different security, not a conflict.
- **Confidence:** High.
- **Investment impact:** none.

### N10 — "Value per share FY2029E": ₹1,560 vs ₹1,039 vs ₹751
- **Specialist positions:** BEAR-C057 (scenario B1), BEAR-C058 (B2) and BEAR-C059 (B3) are three separate bear scenarios.
- **Evidence for each:** `calc/bear-case_scenarios.out`.
- **Contrary evidence:** none.
- **Assumptions required:** the scenario definitions.
- **Independent check (CIO):** the scenarios are distinct by design and are not alternative estimates of one quantity.
- **Resolution:** not a conflict. The run's probability-weighted downside comes from the valuation scenario set (VAL-C045, VAL-C049). The bear-case scenarios inform IA3 and the pre-mortem.
- **Confidence:** High.
- **Investment impact:** IA3, as context.

---

## Part B — Substantive disagreements

### X1 — Cost of capital: placeholder 10–12% (moat) vs 11.03% (valuation); 11.7% vs 13.5% cost of equity
- **Specialist positions:**
  - Moat used a 10–12% placeholder (MOAT-C006).
  - Valuation set a cost of equity of 11.68% and a WACC of 11.03% (VAL-C026, VAL-C027). It subtracted India's 1.87% default spread from the G-Sec yield, and shows 13.5% without that adjustment.
- **Evidence for each:**
  - Rf 7.39% (VAL-C023, tier 5).
  - Damodaran ERP 7.08%, default spread 1.87% (VAL-C024).
  - Beta 0.87, Blume-adjusted from a 5-year weekly regression (VAL-C022).
- **Contrary evidence:**
  - The market price implies a WACC of about 9.5% (cost of equity about 9.9%) on base operations (VAL-C052).
  - The valuation narrative's "repo hike to 5.50% on 7-Oct-2026" is not corroborated [CIO-C047]. It is context only.
- **Assumptions required:** that Damodaran's total ERP already contains country risk, so the default spread must not be counted twice.
- **Independent check (CIO):**
  - Investing.com shows a 10-year G-Sec close of 7.382% on 12-Oct-2026 [CIO-C047].
  - Damodaran's table is confirmed: Baa3, 1.87%, 2.85%, 7.08% [CIO-C048].
  - `valuation_tools.py wacc` re-run gives exactly 11.68% / 11.03% [CIO-C052].
- **Resolution:**
  - Adopt a cost of equity of 11.68% as the run's hurdle and a WACC of 11.03%. This is the only cost-of-capital set used.
  - The default-spread adjustment is methodologically correct for a local-currency rate plus a total ERP.
  - 13.5% is a labelled upper alternative. The market-implied 9.9% is reported as an expectation, not adopted.
- **Confidence:** Medium. The level of the discount rate is the single most decision-sensitive input (±1 pp WACC moves base value by −19% / +27%, VAL-C057). Even at a 10.1% WACC the base value of about ₹1,538 is below the price.
- **Investment impact:** IA1, IA2 and IA4 (the hurdle), BQ1 (spread), and moat's spread count (N8).

### X2 — Layer 1 plausibility: industry "Raises" and special-situations "Raises" vs moat "Lowers" and bear-case "Lowers"
- **Specialist positions:**
  - Industry: the structure has become a rational oligopoly. CR3 rose from 76.5% to 95.8%, HHI to about 3,700, and there have been three synchronised tariff repairs (IND-C035, IND-C066).
  - Special-situations: corporate actions are cash-returning and simplifying.
  - Moat: the 10-year return test fails (MOAT-C007), real ARPU fell 12–17% (MOAT-C020), and Jio breached the position in 2016 (MOAT-C014). The CAP is 5–10 years.
  - Bear-case: the through-cycle record includes a near-wipeout of earnings and 56% dilution (BEAR-C052; BEAR-C060).
- **Evidence for each:** as above, all tier 1–2 primary.
- **Contrary evidence:** financials shows incremental ROIC of 23–28% since FY2021 (FIN-C025), but partly on a depressed base and partly from the inorganic Indus consolidation.
- **Assumptions required:** whether the post-2019 structure is a durable new regime or one phase of a pricing cycle.
- **Independent check (CIO):**
  - The ROIC series reproduces exactly [CIO-C051].
  - The TRAI share is confirmed at 39.7% [CIO-C046].
  - The 10-year median ROIC of 7.1% versus an 11.03% WACC is computed by script (`calc/cio_bq_guides.out`).
- **Resolution:** the two sides answer different parts of the L1 question, so there is no real conflict.
  - Industry structure supplies the mechanism: an entry barrier plus discipline. That mechanism is present.
  - Moat and financials show it has produced excess returns for only about 3 years and failed once against a well-funded entrant.
  - Under the fit scale, that is "mechanism present but unproven or materially constrained": a plausible fit (41–60), not a strong one.
- **Confidence:** Medium.
- **Investment impact:** L1 fit 52; BQ1; BQ2.

### X3 — Layer 3 plausibility: financials, moat, management and concalls "Raises" vs valuation and special-situations "Lowers"
- **Specialist positions:**
  - Raises: returns are driven by the pricing cycle (MOAT, FIN), and management executes restructurings (MGT).
  - Lowers: the stock is at record margins and the 71st-percentile multiple, the turnaround is complete and the catalyst is Soft and partly priced (VAL-C031; SPS-C069; SPS-C080).
- **Evidence for each:** consistent facts. The disagreement is about whether "cyclicality as a driver" equals "fit to the L3 opportunity archetype".
- **Contrary evidence:** management says ₹300 ARPU is needed for adequate returns (MOAT-C062; CON-C036), which implies current earnings may sit *below* the normalised level for this structure.
- **Assumptions required:** whether the structure persists.
- **Independent check (CIO):** ARPU of ₹257 [CIO-C038] and three repair rounds of +14–16% (IND-C066) are confirmed. Valuation's cycle-position evidence and the floor arithmetic (SPS-C082) are consistent.
- **Resolution:** the L3 mechanism exists: repeated industry tariff steps with about 90% flow-through. But it is undated, partly priced, and starts from a mid-cycle rather than a trough base. Plausible but constrained: L3 fit 44. The price question belongs to IA, not to fit.
- **Confidence:** Medium.
- **Investment impact:** L3 fit and the secondary-layer choice.

### X4 — Probability and timing of the next tariff round
- **Specialist positions:**
  - Special-situations: moderate (20–40%) within 12 months, elevated (40–60%) within 24 months (SPS-C071, SPS-C086).
  - Bear-case: "no meaningful round by end-FY2028" is moderate (20–40%), which implies 60–80% that one comes by FY2028.
  - Industry: base case is no headline round for 12–24 months.
  - Concalls: low probability (5–20%) of about ₹300 ARPU by mid-2027 without a tariff move.
  - Brokers (tier 6, SPS-C066) forecast a 15–20% round in 2026, which has not happened.
- **Evidence for each:**
  - Three rounds in about 4.5 years (Dec-2019, Nov-2021, Jul-2024; IND-C048).
  - Management frames 4–5% organic ARPU growth (BEAR-C036; IND-C051) and says Airtel cannot repair pricing alone (SPS-C060).
- **Contrary evidence:**
  - The Vi rescue and Jio's IPO capital could cut either way (BEAR-C034; SPS-C063).
  - Management's tariff-timing calls have been optimistic (CON-C033; CON-C035).
- **Assumptions required:** competitor conduct.
- **Independent check (CIO):** none possible from primary sources; this is forward-looking. The bands are mutually consistent.
- **Resolution:** adopt moderate (20–40%) within 12 months and elevated (40–60%) within 24 months. The timing cannot be settled before the cutoff.
- **Confidence:** Low–Medium.
- **Investment impact:** the bull-scenario probability (25%, VAL-C047), IA6, predictions P1 and P3, key debate D1.

### X5 — Capex trajectory: falling (CRISIL, the bull case) vs rising (management, concalls)
- **Specialist positions:**
  - CRISIL expects capex intensity to moderate (BEAR-C063, tier 5).
  - Management says "period of rapid capex spend" and "will not hold back on capex" (BEAR-C037; CON-C029).
  - Concalls: capex-level guidance has overrun by a median 18.6% since FY2023 (CON-C202), and the "FY2026 lower than FY2025" claim failed (CON-C024; CON-C208).
- **Evidence for each:** above. Filed FY2026 capex was ₹47,522 cr, +12% [CIO-C040].
- **Contrary evidence:** India mobile capex/revenue fell to 16.2% (FIN-C047), so the core mobile build has peaked.
- **Assumptions required:** data-centre (1 GW) and fibre plans.
- **Independent check (CIO):** the FY2026 capex figure is confirmed [CIO-C040].
- **Resolution:** management's own intent plus the overrun record outweigh the rating agency's base case. Consolidated capex stays at or above about 22% of revenue through FY2028. Valuation's base sales-to-capital of 1.5 is consistent with this; a falling-intensity case belongs in the bull scenario only.
- **Confidence:** Medium.
- **Investment impact:** BQ3, the base FCF path, prediction P2, key debate D2.

### X6 — ICIL share swap (June 2026): fair to minorities?
- **Specialist positions:**
  - Filings and management: the reported terms favour minorities on market prices (a 9.5% premium on the shares issued, an 11.6% discount on the Airtel Africa shares acquired; FIL-C066, MGT-C049, tier 6), with 99.97% public institutional approval (MGT-C050, tier 6).
  - Management also raises a corporate-opportunity concern: ICIL bought Airtel Africa at about GBP 1.07 in 2024 and sold to Airtel at about GBP 3.66 (MGT-C056, tier 6, confidence L).
  - Special-situations: negative marked to market, ₹26,104 cr given versus ₹21,759 cr received after Airtel Africa fell 30% (SPS-C079).
- **Evidence for each:** the share count and issue price are tier 1 (CIO-C035). The relative-pricing terms, the vote and ICIL's purchase price are tier 6.
- **Contrary evidence:** ICIL is classified "not related" under Ind AS 24 in the FY2026 note (FIL-C022), although it is promoter group under SEBI (FIL-C065).
- **Assumptions required:** that the news-reported terms are accurate. The valuer's report, EGM notice and scrutiniser's report were not retrieved (NSE returned 403; SSL failures).
- **Independent check (CIO):**
  - From the Q1FY2027 filing: 146,761,335 shares at ₹1,923 (₹28,222 cr), excess over the change in NCI ₹23,260 cr booked in equity, effective Africa stake 62.62% → 78.93% → 79.11% [CIO-C035; CIO-C037].
  - The share bridge reconciles [CIO-C036].
- **Resolution:** **partly unresolved.**
  - *At signing*, the evidence (tier 6 for the terms) suggests no value transfer from minorities.
  - The mark-to-market loss reflects Airtel Africa's subsequent fall, which is price risk, not governance.
  - The corporate-opportunity question cannot be closed without the swap documents. It is recorded as a governance "some concern", not as evidence of extraction.
- **Confidence:** Medium on "no transfer at signing"; Low on the corporate-opportunity question.
- **Investment impact:** BQ7 (held at 74, with this item preventing a higher score); monitoring of future promoter-linked transactions (Airtel Money NBFC 70/30, FIL-C020).

### X7 — Retained earnings FY2017–FY2026: about ₹2,600 cr (declared basis) vs about ₹14,500 cr (cash basis)
- **Specialist positions:**
  - MGT-C045 (ESTIMATE): ₹38,361 cr cumulative net income less about ₹35,737 cr of dividends *declared*, leaving about ₹2,600 cr. Value-per-rupee-retained is "not meaningful".
  - FIN-C038: dividends *paid* to owners of ₹23,879 cr over the same years.
- **Evidence for each:** cumulative attributable net income of ₹38,361 cr equals the sum of financials' Table 1 FY2017–FY2026 (FIN-C010 series). The two dividend figures differ by basis.
- **Contrary evidence:** none.
- **Assumptions required:** timing. The FY2026 final dividend (₹24 a share, declared May-2026) is paid in FY2027 and so is outside FIN's cash window.
- **Independent check (CIO):** about 609 crore shares × ₹24 is about ₹14,600 cr, which explains most of the gap. The arithmetic is an approximation; the conclusion does not depend on precision.
- **Resolution:** both are right on their own bases. Either way, retained earnings over the decade were small relative to the ₹1.03 lakh cr of equity issued (MGT-C044). Growth was funded by external equity and debt, not retained profit.
- **Confidence:** High on the conclusion.
- **Investment impact:** BQ6; L1 per-share test.

### X8 — Per-share compounding rates: BVPS 3.9% (management) vs 4.7% (financials); EPS 11.7% vs 12.5%
- **Specialist positions:**
  - MGT-C065: FY2016–FY2026, as-reported shares.
  - FIN-C036: rights-adjusted year-end shares.
- **Evidence for each:** the bases differ. FIN adjusts for the bonus element of the rights issues using the company's own factors.
- **Contrary evidence:** none.
- **Assumptions required:** none.
- **Independent check (CIO):** FIN's adjusted series is the methodology-consistent per-share basis (`METRIC_DEFINITIONS`: adjust per-share history for splits and bonuses).
- **Resolution:** FIN-C036 is used. Both show modest per-share compounding.
- **Confidence:** High.
- **Investment impact:** none on direction.

### X9 — Subscriber share break in Mar-2026: TRAI 477.74 mn / 481.48 mn vs company 373.2 mn
- **Specialist positions:**
  - MOAT-C030: a TRAI definition change, probably M2M.
  - IND-C039: Airtel began reporting M2M connections, which other operators had always included.
- **Evidence for each:** TRAI table vs company KPI.
- **Contrary evidence:** none.
- **Assumptions required:** none.
- **Independent check (CIO):** the TRAI FY2026 report shows Bharti wireless subscribers of 481.48 mn, 37.55% (TRAI PIR FY2026). Revenue share is unaffected [CIO-C046].
- **Resolution:** definitional. Revenue (AGR) share is the run's share measure. Subscriber share from FY2026 onward is not comparable with earlier years.
- **Confidence:** High.
- **Investment impact:** monitoring baseline only.

---

## Correlated-evidence check (Stage 3 step 5)

| Conclusion relied on | Reports citing it | Underlying source | Treated as |
|---|---|---|---|
| Management frames 4–5% organic ARPU growth and needs industry repair | BEAR-C036, IND-C051, SPS-C060, CON-C085 | The same Q3FY2026/Q1FY2027 calls (tier 4) | **One** management statement; not independent confirmation |
| Vodafone Idea AGR relief | BEAR-C034, MOAT-C056, IND-C063, SPS-C062 | Press (tier 6), no primary DoT document | One low-confidence fact |
| Jio IPO size and timing | VAL-C038/C056, BEAR-C043, SPS-C063, MOAT-C058 | Press (tier 6) | One low-confidence fact |
| ICIL swap terms (premium/discount, vote) | FIL-C066, MGT-C049/C050, VAL-C004 (count tier 1) | News for the terms; the Q1FY2027 filing for count and price | Count/price high confidence [CIO-C035]; terms one tier-6 source |
| ARPU history and current ₹257 | MOAT-C019, IND-C042, BEAR-C006, CON-C134..C141 | The same company Quarterly Reports | One primary series, verified [CIO-C038] |
| Consensus estimates | BEAR-C040 only | StockAnalysis (tier 5) | Single tier-5 source; used only for the variant-perception framing |

---

## Part C — Symmetric adversarial review (Stage 3, bear-case follow-up 1)

### X10 — Does the draft AVOID omit value? Base case without any tariff round
- **Specialist positions:**
  - The draft base DCF (growth 12% → 7%, sales-to-capital 1.5) carries no explicit industry tariff round over ten years (BEAR-C084).
  - A Poisson base rate on the post-2019 rounds gives P(≥1 round in 5 years) of 76–89% (BEAR-C083).
  - One realised +8% India mobile round in year 2 lifts the base point from INR 1,215 to INR 1,378 (BEAR-C085).
  - Against that, the same review finds sales-to-capital of 1.5 generous: history is about 0.9 (BEAR-C089), and at 1.0 the base would be INR 1,110 (BEAR-C088).
- **Evidence for each:**
  - Three rounds in about 4.5 years (IND-C048).
  - The draft itself assigned an elevated probability (40–60%) to a round within 24 months (contradiction log X4).
  - Capital-intensity history is in BEAR-C089.
- **Contrary evidence:**
  - Management frames 4–5% organic ARPU growth and says Airtel cannot repair pricing alone (BEAR-C036; SPS-C060).
  - The 2024 round was largely anticipated (SPS-C080).
- **Assumptions required:** the size of a realised round. +8% on India mobile revenue is conservative against the +14–16% realised per past round (IND-C066).
- **Independent check (CIO):**
  - Applied the one-round adjustment to valuation's own low, point and high base inputs: INR 1,306–1,509 (point 1,378). The same point with sales-to-capital 1.0 is INR 1,266 [CIO-C056].
  - Re-ran scenario-irr and both price ladders on the revised set: E[IRR] 6.2%, MoS −26%, hurdle-adjusted asymmetry 0.06, IA 38 [CIO-C057; CIO-C058].
- **Resolution:**
  - **Accepted.** The base case now carries one round. The bull case keeps two rounds and the bear case none.
  - The sales-to-capital objection is recorded as a downside sensitivity (INR 1,266). It was not netted against the round, to avoid a convenient offset.
  - Net effect: base value +13%; the verdict stays **AVOID** (IA 35 → 38).
  - Decision triggers move up: BUY ≤ ~INR 1,175; AVOID ≥ ~INR 1,600.
- **Confidence:** Medium.
- **Investment impact:** IA1, IA2, the scenario set, the L1 and L3 current-price assessments, the triggers.

### X11 — Other challenges in the adversarial review
- **Specialist positions** (BEAR-C080 to BEAR-C106):
  - The 11.68% cost of equity is not wrong. The beta range is 0.77–0.89 (BEAR-C081). The spot 7.39% G-Sec is a three-year high; normalising it to 6.90% adds about INR 126 a share and about 1.5 IA points (BEAR-C086). Nothing supports the ~9.9% the price implies (BEAR-C106).
  - The IA4 deviation is economically correct (BEAR-C090).
  - Bull weights of 35–45% lift IA only to 36–37 (BEAR-C091).
  - IA1, IA2, IA4 and IA5 (65% of IA weight) restate the same DCF-versus-price gap (BEAR-C101).
  - E[IRR] assumes convergence to about 8.1x EBITDA (BEAR-C093). If 10.9x holds, an owner earns about 10.4–13.7% a year (BEAR-C092).
  - The full steelman stack (two rounds, normalised rate, 25.17% tax) reaches INR 1,672–1,730 and IA 44.7–46.0 (BEAR-C087).
- **Evidence for each:** `calc/bear-case_followup_*.out`.
- **Contrary evidence:** the draft's own sensitivity at a 10.1% WACC (INR 1,538) is consistent with these figures (VAL-C057).
- **Assumptions required:** the exit multiple; the rate regime.
- **Independent check (CIO):** the draft IA is reproduced at about 35.4 by the reviewer's own script (BEAR-C090). The multiple-reversion assumption is stated explicitly in the final report [CIO-C059].
- **Resolution:**
  - The cost of equity is kept at 11.68%; normalised rates are a labelled sensitivity.
  - IA4 deviation kept.
  - Probabilities kept at 20/55/25.
  - The multiple-reversion premise and the IA redundancy are disclosed in the report.
  - Even the full steelman stack only reaches the AVOID/HOLD boundary, so no override is warranted.
- **Confidence:** Medium.
- **Investment impact:** report disclosures; no score change beyond X10.
