# CIO synthesis working notes (Stage 3) — run 20261012T132311Z

Working memory for the CIO. Not a deliverable. Every number below cites its claim ID; re-read the source before using it in the report.

## Stage 2 outcome
- validate_run --stage specialists: PASS (0 errors, 13 warnings; all are tier-6-only FACTs: BEAR-C034/C064/C065/C066/C067, FIL-C049/C059/C066, MOAT-C025/C056, VAL-C036/C038/C056).
- Git batch 1: f058b6e, pushed.
- evidence_stats: 759 claims; 91% primary; 1% NOT_LOCATED; 8% low-tier FACT. All thresholds met (min per specialist 37 [cio] / 58 [valuation]).

## Numeric conflicts from reconcile_numbers.py (10): to adjudicate in the contradiction log
1. ebitda FY2026: BEAR-C002 121,268 / FIN-C002 119,674.5 / FIN-C062 116,514 (Screener). FIN-C002 = revenue − opex excl. other income (metric definition). BEAR-C002 likely = company "profit before D&A" including other income (121,268 ≈ 119,674 + 2,817 − ... check). FIN-C062 = aggregator. Adopt FIN-C002.
2. equity_issued FY2020 standalone: BEAR-C021 39,339 / MGT-C033 24,939 / MGT-C034 14,400. Likely rights issue 24,939 + QIP 14,400 = 39,339. Components vs total. FIN-C016 says 39,181 consolidated (FY2020 cash). Check.
3. ev_ebitda TTM: BEAR-C054 10.1 (company convention, no NCI) vs VAL-C031 10.86 (minorities at market). Definitional; both valid; VAL-C031 for valuation.
4. expected_irr: VAL-C048 0.0898 (decomposition base case ESTIMATE) vs VAL-C049 0.0469 (E[IRR] CALCULATION). Different measures; VAL-C049 is decision metric (METRIC_DEFINITIONS).
5. market_cap: VAL-C036 99,652 = Indus Towers market cap (mis-keyed as Airtel market_cap, tier 6) vs CIO-C003 / VAL-C003. Different entity. CIO-C003 1,109,998.53 (fully paid) vs VAL-C003 1,110,088 (incl. partly paid economic value, +89.5) — both consistent with calc/cio_preflight_mcap.out total.
6. market_share QE-Jun-2026: MOAT-C033 40.5 vs MOAT-C061 2.88. Different definitions (check MOAT-C061: probably Airtel share of something else, e.g. satellite/FWA?). Read.
7. net_debt_incl_leases FY2026: BEAR-C005 164,789 / CON-C158 164,788.8 (company IR definition) vs FIN-C027 167,988.9 (financials' definition: cash excludes other bank balances/mobile-money trust). Definitional; ~1.9%.
8. years_roce_above_hurdle: MOAT-C007 3 (WACC 10-12% placeholder) vs MOAT-C067 5 (8-9% WACC). Sensitivity, not conflict. Re-do at run WACC 11.0% (pre-tax hurdle).
9. price: VAL-C035 375.65 = Indus Towers price (different security). Not a conflict.
10. value_per_share FY2029E: BEAR-C057/C058/C059 = three separate bear scenarios (B1/B2/B3). Not a conflict.

## Financials (read in full)
- Numeric base: financial_history.csv, 16 FY (FY2011–FY2026), 374 verified rows. FY2016–FY2026 tier 1; FY2011–15 IFRS tier 3.
- ROCE 11.0% FY16 → 2.5% FY19 → 18.8% FY26 (FIN-C022). ROIC@25.17% tax: 13.9% FY26, through-cycle mostly 5–9% FY12–18, <5% FY18–21 (FIN-C024). Incremental ROIC 28% 5y / 23% 3y / 17% 10y (FIN-C025), caveats: depressed base; Indus inorganic.
- CFO/PAT 4.18x 5y; equity FCF/PAT 0.72x 5y, 0.23x 10y (FIN-C030, C031). FY26 equity FCF 53,054 cr vs attributable PAT 26,695 (FIN-C032); spectrum cash only 855 cr in FY26 after 21,349 FY25 prepay.
- Underlying attributable PAT: FY25 17,573 vs reported 33,556; FY26 26,904 vs 26,695 (FIN-C033). Exceptionals net −57,857 cr FY17–26 (FIN-C045).
- Owner earnings FY26: 29,600–47,500 cr, base 39,900 (FIN-C035) — ESTIMATE.
- Net debt ex leases 94,249 (0.79x), incl leases 1.40x, incl AGR provision 1.53x (FIN-C026, C027). DoT deferred 90,643 of borrowings; net financial debt ex-DoT 3,606 (FIN-C028). 24-month maturity cover 0.86x (FIN-C041).
- Per share 10y: revenue 8.1% vs rev/share 4.4%; share count +3.5%/yr; EPS 12.5%, BVPS 4.7% (FIN-C036). Trough needed 39,181 cr equity FY2020 (FIN-C016).
- Segments FY26: India Mobile rev 112,995 cr, result margin 31.7%, segment EBITDA 60.2%; Africa rev 56,806, margin 33.1%, 26.9% of group revenue (FIN-C042). India Mobile capex/rev 16.2% (FIN-C047).
- EBITDA margin 56.7% FY26 (excl OI), plateau ~57% for 4 quarters (FIN-C063). Q1FY27 rev 58,539 +18.4% yoy like-for-like.
- Crosswalk: L1 No change; L2 Lowers; L3 Raises; L4 Lowers.
- Classifications: trajectory Strengthening; earnings quality Adequate; BS resilience Adequate; per-share compounding Moderate.
- Open: share-count gap (RESOLVED by CIO-C036); cost of capital; AGR provision vs deferred liability mapping; exceptional classification.

## Valuation (read in full)
- Cost of capital: Rf 7.39% (VAL-C023, Trading Economics tier 5, 12-Oct-2026), ERP 7.08% (VAL-C024 Damodaran), default spread −1.87%, beta 0.87 Blume (raw 0.81) (VAL-C022). CoE 11.68% (VAL-C026) = hurdle; WACC 11.03% (VAL-C027). Alt: 13.5% without default-spread adjustment.
- DCF: base 1,145–1,342 (point 1,215) (VAL-C044); bear 627–787 (VAL-C045); bull 1,690–2,123 (point 1,887) (VAL-C046). Probabilities 20/55/25 (VAL-C047).
- E[IRR] 4.7% (VAL-C049); mean of scenario IRRs 3.8%; decomposition ~8% (VAL-C048). MoS −43% vs base midpoint 1,244. Asymmetry tool 4.8 (undiscounted) vs hurdle-adjusted 0.06 (VAL-C050). Bear 5-yr loss incl dividends −33% (−41% at low end).
- Reverse DCF: 14.4% revenue growth for 10y, or 51.9% EBIT margin, or WACC 9.5% (CoE ~9.9%) (VAL-C042, VAL-C052).
- Multiples: EV/EBITDA 10.0x company / 10.9x incl minorities at market; 71st pct of FY2010–26 (median 8.99) (VAL-C031). P/E 38.3x TTM. Record EBIT margin 32.6%.
- Segment implied: Africa ~6.0x, India incl Indus/Hexacom ~12.4x (VAL-C053).
- Price ladder (VAL-C051): E[IRR]=hurdle at ~1,300; MoS>0 below ~1,245. IA1 15, IA2 32, IA4 99 at current price (tool). IA4 from undiscounted asymmetry: CIO must judge vs 0.06.
- Liquidity: 90d ADTV ~1,209 cr; G5 not triggered (VAL-C013, C014).
- TSR 10y 20.9% vs Nifty 500 price 11.2%; 15y 12.4%, 20y 11.7% ~ market; max DD −57% (12y recovery) (VAL-C018, C019).
- Net debt incl leases 30-Jun-2026 1,57,240 cr (VAL-C006); "investments & receivables" 35,222 cr deducted — liquidity unverified (up to −56/share).
- Minorities at market ~1,08,980 cr (VAL-C032); full EV ~13.76 lakh cr.
- Status: Expensive; expectations Demanding.
- Crosswalk: L1 No change; L2 Lowers; L3 Lowers; L4 No change.
- Issues for audit: Rf from tier 5 (no RBI/FBIL print) — CIO should verify 10y G-Sec 12-Oct-2026 from a tier 1-2 source if possible. Default-spread adjustment choice. Scenario probabilities basis (L confidence).

## Filings (read in full)
- Reporting reliability: **Generally reliable** (gates G1/G2 NOT triggered). Disclosure Adequate. Credit Improving.
- Exceptionals net INR 578,571 mn FY17–26 = ₹57,857 cr (= FIN-C045, consistent), 0.88x cumulative PAT; net charge 7/10 years (FIL-C033, C032).
- FY25 non-operating credits: Indus fair-value gain INR 107,025 mn (₹10,703 cr) + DTA recognition 85,732 mn (₹8,573 cr) (FIL-C038, C017, C009). RESOLVED: FIN-C054's ₹14,322.5 cr is the total business-combination gain incl. the ₹10,702.5 cr fair-value gain on the existing stake; consistent with FIL-C017.
- FY26 DTL reversal 30,952 mn (₹3,095 cr, = FIN) booked with 31,607 mn levy re-assessment charge (FIL-C058).
- Contingent liabilities 191,842 mn (12.9% of owners' equity), up to 20.6% incl OTSC 66,065 + ISP 48,619 (FIL-C010, C011, C036). AGR sub-judice provision 347,042 mn, 55.2% indemnified; non-indemnified 155,431 mn (= FIN 15,543 cr) (FIL-C012, C039). Disputed payables 245,350 mn (FIL-C014). Deferred dues in borrowings 906,430 mn (FIL-C013).
- FCF after leases/interest/AGR principal FY26: 476,263 mn vs 746,608 before (FIL-C035). (Financials equity FCF ₹53,054 cr differs in definition — financials includes? check: FIN equity FCF = CFO − capex − spectrum − lease − interest = 122,230−46,714−855−6,720−14,888 = 53,053; filings additionally deducts AGR principal 5,427 cr → 47,626. Definitional: AGR instalment is debt repayment.)
- Audit: unmodified FY17–26; EOMs FY17–24 (OTSC, then Vodafone Idea at Indus); KAM regulatory/tax since FY20. Deloitte → S.R. Batliboi at 2027 AGM (FIL-C041).
- ICIL swap: 146,761,335 shares, ₹28,222 cr; 9.5% premium / 11.6% discount at signing (FIL-C066, tier 6); 5.7x NCI carrying value (FIL-C067). ICIL listed as not related under Ind AS 24 in FY26 note but promoter group per SEBI (FIL-C022, C065).
- Ratings: CRISIL AAA (Jul-2025), Moody's Baa2, S&P BBB (Mar-26), BBB+ Jun-26 (tier 6) (FIL-C044, C049). CRISIL downgrade trigger net leverage incl dues+leases >2.5–2.7x; 2.1x FY25 (FIL-C047).
- BTL holdco gross debt ~₹39,975 cr, serviced by Airtel dividends; shares unencumbered (FIL-C048). Dividends to BTL INR 37,737 mn FY26.
- Indus: goodwill 208,593 mn; Vodafone Idea concentration; receivables at acquisition 95,071 mn (FIL-C017, C018).
- Mobile money restricted cash 132,061 mn in other bank balances (FIL-C001).
- Airtel Money NBFC: Bharti Enterprises 30% co-investor, terms undisclosed (FIL-C020).
- Crosswalk: L1 No change; L2 No change; L3 No change; L4 Insufficient evidence.

## Moat (read in full)
- Verdict: **Narrow**, trajectory **Stable**, CAP **5–10 years (central ~7)**. Primary mechanism: entry barrier (spectrum, network scale, capital ~₹2.7–2.9 lakh cr, MOAT-C060 ESTIMATE L) in consolidated oligopoly, shared with Jio; secondary: premium mix ARPU +20.1% vs Jio (MOAT-C024).
- Company-defined ROCE (EBIT/(equity+net debt)) FY13–26: 5.68…2.53(FY19)…19.0(FY26) (MOAT-C001..C005). Pre-tax hurdle at 11% WACC = 14.7% — **equals the run WACC 11.03% → 14.74% pre-tax**. So MOAT-C007 "3 of 10 years" is at the run WACC (conflict #8 resolved: adopt MOAT-C007; MOAT-C067 is the 8–9% sensitivity). Median post-tax spread −3.4 pp FY17–26.
- India mobile return on avg gross segment assets: 9.4% FY16, −3.5% FY19, 12.8% FY26 (MOAT-C012); net segment assets 24.9% (MOAT-C066). Incremental pre-tax 46% FY21–26 (MOAT-C042).
- Pricing: ARPU Rs194 (Q4FY16) → Rs100 (Q2FY19) → Rs257 (Q4FY26); real ARPU −12–17% over decade (MOAT-C020). Churn 2.4% vs Jio 1.7% (MOAT-C019, C023).
- Attack test: Jio 2016 — India mobile revenue −25.9% FY16–19, segment result swing −₹18,508 cr (MOAT-C014); ~6–7 years to recover returns.
- Segments: Airtel Business 18–25% pre-tax ROA every year FY19–26 (MOAT-C040) — the most durable; Africa 0.7%→16.7% (MOAT-C041); Homes 18.1%→8.7% (MOAT-C039), Jio leads FWA (13 Mn vs >3 Mn) and wired (30.45% vs ~22%) (MOAT-C023, C063); DTH 32%→−3%; Indus 11% (≈ CoC).
- Management statements: India ROCE "low at 9.4%" FY24, "only 11%" FY25; need Rs300 ARPU (MOAT-C051, C052, C062).
- Probability of a return-destroying price war within 5 years: low (5–20%) (JUDGMENT; reference class: 1 episode/decade).
- Leading indicators: ARPU premium vs Jio <10%; AGR share <40% two quarters; churn; Jio tariff cuts post-IPO; Homes ROA; satcom pricing; Vi state-backed price-led.
- MOAT-C061 2.88 = BSNL share of top-4 access AGR (not Airtel) → conflict #6 is different entities.
- Mar-2026 TRAI Bharti subscribers 477.74 Mn vs company 373.2 Mn: definitional (M2M) (MOAT-C030; industry IND-C039 says Airtel began reporting M2M).
- Corpus catalog mislabels Q1FY2025 transcript (b6f3d368) as missing — owner flag.
- Crosswalk: L1 Lowers; L2 Lowers; L3 Raises; L4 Insufficient evidence.

## Industry (read in full)
- Classifications: attractiveness **Moderate**; phase **Growing**; cycle **Mid-cycle**; Airtel share **Gaining**.
- TRAI access AGR share: Airtel 30.2% FY16 → 22.7% FY19 → 39.7% FY26 → 40.0% Q1FY27; Jio 44.8%, Vi 11.3%, BSNL 2.9% (IND-C034). CR3 76.5%→95.8%; HHI 2,427→3,719 (IND-C035). Caveat IUC distortion pre-2021 (IND-C047).
- Growth decomposition FY16–26: Airtel AGR 9.1%/yr vs industry 6.2%; ~6.0 pp industry, 2.7 pp share (IND-C045). Reported India mobile revenue CAGR 7.3% = ARPU 2.9% + customers 4.0% (IND-C044). FY21–26 cleaner: industry 13.4%, Airtel 17.1%; ARPU 12.1%.
- Industry access AGR −36.2% FY16Q4→FY18Q4, then +14.0% CAGR to FY26 (IND-C046).
- Tariff repairs Dec-2019, Nov-2021, Jul-2024 each +14–16% ARPU over two quarters (IND-C066, IND-C048). None since Jul-2024 (27 months). No-hike drift +8.3% FY24, +4.9% FY26. Management frames 4–5%/yr ARPU growth (IND-C051).
- Industry AGR +10.4% FY26 (IND-C037); industry ARPU +3.6% (M2M-diluted) (IND-C038); underlying wireless market ~6% (IND-C050); revenue/GB −10.6% to Rs 8.02 (IND-C041).
- Vi AGR relief (press, tier 6, L): dues frozen, payments capped; three-player base case (IND-C063).
- Sensitivities: +10% tariff no churn ≈ +₹10,200 cr EBITDA (+8.4% consolidated); 2% churn → +6.5% (IND-C067 ESTIMATE). African FX −10% → EBITDA −2.3% (IND-C068). INR −10% → capex +₹1,600–2,400 cr (IND-C069). Licence fee ±1pp ≈ ₹1,400 cr.
- Spectrum: TRAI recommended auction 24-Feb-2026, lower reserve prices (IND-C065); 2022 instalments resume Aug-2026 (IND-C064).
- Benchmark FY26: Airtel India mobile rev ₹1,12,995 cr +12.7%, EBITDA 60.2%; Jio Platforms ₹1,46,885 cr +14.6%, 51.9%; Vi ~₹44,873 cr ~42% (IND-C070, C062, C063). ARPU 257/214/190.
- Africa: cc revenue +24%, EBITDA margin ~49%, churn 4.3% (IND-C058); FY26 aided by currency appreciation.
- Industry scenarios: bull ~15% repair within 2y, AGR 12–14%/yr; base no round 12–24 months, AGR 7–9%; bear promo pricing, AGR 3–5%.
- Crosswalk: L1 Raises; L2 Lowers; L3 No change; L4 Insufficient evidence.

## Management (read in full)
- Classifications: competence **High**; governance **Clean / Standard** with one "some concerns" item (ICIL/Airtel Africa corporate-opportunity pattern) — **G3 NOT triggered**; capital allocation **Good**.
- Promoters 68.29% Mar-2011 → 48.87% Dec-2025 → 50.07% Jun-2026; zero pledge/NDU/encumbrance in 39 quarters (MGT-C022, C011, C008, C025). Net sold 255.4 mn shares (7.9% of stake) Dec-24→Dec-25 via Pastel (Singtel) & ICIL; BTL net buyer 85.1 mn (MGT-C046, C027, C051, C052).
- ICIL swap: corporate-opportunity question — ICIL bought Airtel Africa at ~GBP 1.07 in 2024, sold to Airtel at ~GBP 3.66 (MGT-C056, tier 6, L); swap terms favourable on market prices (MGT-C049, tier 6 M); 99.97% public institutional votes (MGT-C050, tier 6). Valuer report/EGM docs not retrieved.
- Dilution: 3,997.4 mn (Mar-16) → 6,240.5 mn (Jul-26), +56.1%, 4.32%/yr (MGT-C042). Equity issued ~₹1.03 lakh cr (₹72,600 cr cash) (MGT-C044). Price CAGR 16.7% unadjusted (MGT-C043). BVPS 3.9%/yr (MGT-C065; differs from FIN-C036 4.7% rights-adjusted year-end shares — basis difference). Cumulative NI FY17–26 ₹38,361 cr (= financials table sum, consistent); dividends DECLARED ~₹35,737 cr (MGT-C045 ESTIMATE) vs FIN-C038 dividends PAID to owners ₹23,879 cr FY17–26 → gap mostly timing (FY26 final DPS 24 declared, paid in FY27 ≈ ₹14.6k cr). Both "near-zero retained earnings" (declared basis) and "~₹14.5k cr retained" (cash basis) — note in contradiction log (not numeric-flagged).
- Rights 2019 ₹220 (₹24,939 cr, MGT-C033); QIP Jan-2020 ₹445 (₹14,400 cr, MGT-C034) + FCCB; 2021 rights ₹535 (call ₹401.25 collected Mar-2026, ₹15,696 cr, MGT-C020); Google 71.18 mn at ₹734 (MGT-C036).
- Succession: Shashwat Sharma MD & CEO from 1-Jan-2026; Vittal Executive Vice Chairman; Soumen Ray Group CFO; Akhil Garg CFO India (MGT-C003, C004). Chairman re-appointed to Sep-2031: ~₹30 cr + up to GBP 2.2 mn from UK sub (MGT-C030, C029). Founder succession unaddressed.
- Board: Audit & HR/Nomination fully independent; 98% attendance; 6/12 independent (exact minimum) (MGT-C057, C019).
- Integrity: APB RBI ₹5 cr penalty 2018 (MGT-C054). No SEBI orders found (limited search).
- LTI scorecard includes revenue market share (can reward growth over per-share value) and relative TSR (MGT-C014). Dividend policy: pass through 100% of subsidiary dividends (MGT-C059).
- Crosswalk: L1 No change; L2 Insufficient evidence; L3 Raises; L4 No change.

## Concalls (read in full)
- Classifications: forecast accuracy **Inconsistent**; execution **Mixed (Reliable on deleveraging and capital return)**; transparency **Standard**; strategic consistency **Consistent**.
- 40 quarters Q3FY2016–Q1FY2027 (CON-C001); 70-row promise DB; 56 resolved: 31 on target (55%) (CON-C200). Balance sheet 6/6 (CON-C204); capex 7/17 (41%); network/tech 4/10; new ventures 0/2 (CON-C205).
- Capex level guidance overrun: median +7.6%, mean +19.1%, 9/11 above (CON-C201); FY2023+ median +18.6% (CON-C202). 5G "no material change" (CON-C019) vs India&SA capex ₹20,773 cr FY22 → ₹33,379 cr FY24 (+61%) (CON-C111, C113). "FY26 lower than FY25" (CON-C024) → consolidated capex ₹47,522 cr, +12.4% (CON-C117, C208). FY27 "ballpark of this year" (CON-C025) then "period of rapid capex spend" (CON-C029). → least-trusted guidance.
- ARPU: ₹200 "short term" (May-2020) reached Q1FY24 (~13 quarters) (CON-C033, C136); ₹300 "in next five years" (May-2022) needs +13.6% from ₹264 (CON-C036, C206). Low probability (5–20%) of ~₹300 by mid-2027 without tariff move (JUDGMENT).
- Leverage (net debt incl leases/EBITDA, company): 2.97x FY23 → 1.86x FY25 → 1.29x FY26 (CON-C151, C153, C154). Recast net debt ₹2,03,838 cr FY25 → FY26 −19% (CON-C157, C158; CON-C158 = ₹1,64,788.8 cr incl leases).
- DPS ₹4 → ₹8 → ₹16 → ₹24 (CON-C160–C162). High probability (>60%) FY2027 DPS ≥ ₹24 (JUDGMENT).
- Data centres: 1 GW in 3–4 years from 120–130 MW (CON-C091); Nxtra to "lever up"; Nxtra 3x revenue/EBITDA in 2–3 years (CON-C095). Airtel Money London listing H2 2026 (CON-C092). BTL to buy 3.6% over 3–4 years; buybacks "next couple of years" (Chairman) (CON-C094). ~₹50,000 cr India FCF "on track" (CON-C097) – unreconciled.
- Elevated probability (40–60%) FY2027 consolidated capex > FY2026 by >5% (JUDGMENT).
- Crosswalk: L1 No change; L2 Raises; L3 Raises; L4 Lowers.

## Bear-case (read lines 1–348; tail next)
- Bear-risk classification Moderate; P(loss ≥30% over 5y) low (5–20%).
- Key: risk is paying for expected growth, not solvency. Consensus 34 analysts, FY27 EPS 62.75, FY28 82.26, avg target ₹2,318 (BEAR-C040, tier 5 ESTIMATE). Needs ~16% EBITDA CAGR (BEAR-C056).
- P/E ~36.8x pro-forma TTM (BEAR-C053); EV/EBITDA 10.1x company convention (BEAR-C054), own range 7.75–14.14x since FY2019 (BEAR-C048); FCF after capex/spectrum/leases/interest ~₹54,222 cr = 4.9% of mcap (BEAR-C055) (≈ FIN-C032 ₹53,054 cr; small definitional diff).
- Scenarios (3-yr horizon FY2029, EPS × exit P/E + divs): Reference +44% (₹2,569 at 28x); B1 no repair + capex supercycle ₹1,560 (−12%) (BEAR-C057); B2 10% ARPU reset ₹1,039 (−42%) (BEAR-C058); B3 + Africa FX −30% + no delever ₹751 (−58%) (BEAR-C059); B4 2016–19 replay ₹923 (−48%) (BEAR-C060). Regulatory crystallisation −₹21/share; unindemnified AGR ₹25/share (BEAR-C061).
- Probabilities: A1 no tariff round by FY2028 moderate (20–40%); A2 structure break (≥10% ARPU reset in 5y) low (5–20%); A3 capex/rev ≥22% through FY2029 moderate; A4 Africa INR EBITDA −20% at some point moderate; A5 P/E < 25x within 3y moderate. Correlated B3 low (5–20%).
- Most damaging assumption: A2 (structure); most probable disappointment A1.
- Searches: no short-seller, no SEBI order vs company (BEAR-C065 tier 6); CCI matters (BEAR-C066); data-breach claim denied (BEAR-C064); Singtel block sales (BEAR-C067). Contingent liabilities ₹19,184 cr (BEAR-C028); OTSC contingent ₹6,607 cr (BEAR-C029).
- Mobile India EBIT ~9.8% of gross cumulative investment ₹3.79 lakh cr (BEAR-C062).
- ARPU sensitivity: 10% ARPU = ~₹13,842 cr FY2029 EBITDA = ₹245–300/share at 18–22x (BEAR-C069).
- Value-trap test: "quality-premium trap" risk, not value trap.
- Crosswalk: L1 Lowers; L2 Lowers; L3 No change; L4 Insufficient evidence.
- Note BEAR-C002 EBITDA FY2026 121,268 = company KPI (likely incl. other income?) → check ledger row.

## Bear-case tail (read)
- Conflict #1 resolved by BEAR's own note: BEAR-C002 ₹1,21,268 cr = company KPI EBITDA (excl. other income, adds back charity etc.); statutory "profit before D&A" ₹1,22,492 cr incl. other income; FIN-C002 ₹1,19,674.5 cr = METRIC_DEFINITIONS ebitda (revenue − opex excl OI). Adopt FIN-C002 for metric ebitda; company KPI basis only for company-convention multiples. FIN-C062 Screener aggregator rejected.
- BEAR market share conflict: mgmt revenue share 39.7% vs CRISIL subscriber share 37.55% → industry IND-C034 (TRAI AGR 39.7%) resolves; definitional.

## Special-situations (read in full)
- Classification: **No meaningful special situation**; closest = cyclical inflection (tariff repair), **Soft**.
- K2 tariff round: moderate (20–40%) in 12 months; elevated (40–60%) in 24 months; gross ₹61–86 (+5%), ₹123–173 (+10%), ₹184–259 (+15%) per share (SPS-C086 ESTIMATE); partly priced (2024 round −1.9% excess, SPS-C080).
- SOTP: listed stakes ₹2,09,615 cr = ₹336/share = 18.9% of mcap (SPS-C075): Airtel Africa 79.11% ₹1,05,574 cr (₹169/sh); Hexacom 70% ₹53,246 cr (₹85/sh); Indus 51.256% ₹50,796 cr (₹81/sh). Airtel Money look-through 61.59% = ₹66/sh (SPS-C076). Nxtra ~₹29/sh (ESTIMATE ~61% post-deal stake, SPS-C077). Implied India EV/EBITDAaL ~12.6x annualised (SPS-C078). No discount-closure mechanism.
- Airtel Money LSE admission 14-Oct-2026 (after cutoff) — Hard, but secondary; no cash to group (SPS-C043–C047).
- ICIL swap marked to market now negative: gave ₹26,104 cr stock vs ₹21,759 cr AAF shares (AAF −30% since) (SPS-C079). ICIL total holding 3.25% (existing + new) vs SPS 2.35% (new shares share of fully paid) — reconciled by MGT-C008/C007.
- Downside floor (earnings): trough multiples 6.65–8.0x × India EBITDAaL → ₹915–1,113/sh; stress (EBITDAaL −15%, Africa −50%) ₹685–853; 10x → ₹1,101–1,405 (SPS-C082). India SA net debt ex-leases ₹69,314 cr (SPS-C094). Note: company net debt includes DoT deferred liabilities (VAL-C006: 88,713 cr in net debt) → floor question resolved: DPL is inside reported net debt.
- Cycle: late-recovery/expansion (T8); turnaround complete; EBITDA margin 57.5% company basis (SPS-C070); capex intensity 35.6% FY19 → 22.5% FY26 (SPS-C090); Q1FY27 EV/EBITDA 9.77x vs FY21–26 range 8.99–11.83x (SPS-C074).
- Event calendar: Q2FY27 results ~5-Nov-2026 (tentative, SPS-C058); Jio IPO ~late Oct-2026 (SPS-C063); AAF buyback to 27-Nov-2026; Q3FY27 3-Feb-2027; Q4FY27 18-May-2027; auditor rotation 2027 AGM; 2022 5G instalments from Aug-2026; AGR instalments to FY2031; spectrum auction undated.
- Management event record: demerger "unlock" withdrawn (SPS-C014); DTH merger talks terminated May-2025 (SPS-C061).
- Crosswalk: L1 Raises; L2 No change; L3 Lowers; L4 No change.

## CROSSWALK TALLY (specialists → plausibility effect)
| Layer | FIN | FIL | MGT | IND | MOAT | CON | VAL | BEAR | SPS |
| L1 | NC | NC | NC | Raises | Lowers | NC | NC | Lowers | Raises |
| L2 | Lowers | NC | IE | Lowers | Lowers | Raises | Lowers | Lowers | NC |
| L3 | Raises | NC | Raises | NC | Raises | Raises | Lowers | NC | Lowers |
| L4 | Lowers | IE | NC | IE | IE | Lowers | NC | IE | NC |

## CIO AUDIT RESULT (Stage 3 step 4) — done
- Re-verified ≥12 decision-critical claims, all CONFIRMED, none contradicted: price CIO-C001; shares CIO-C002/C036; revenue/PAT/equity/CFO FY2017/24/25/26 CIO-C010..C033 (match FIN Table 1; 'borrowings_as_reported' = borrowings incl DoT 121,671 + leases 73,740 = 195,411 ✔); ICIL swap CIO-C035; ARPU 257 CIO-C038; net debt/leverage 1.29x CIO-C039; capex 47,522 CIO-C040; EBITDA margin 57.5% CIO-C041; AGR provision CIO-C042; CL 191,842 CIO-C043; DPL 906,430 CIO-C044; OTSC CIO-C045; TRAI AGR share 39.7% CIO-C046; Rf 7.382% CIO-C047; Damodaran ERP CIO-C048; Q1FY27 revenue CIO-C049; exceptional FY26 CIO-C055.
- Recomputed 5: fin_metrics (609 rows identical) CIO-C051; WACC CIO-C052; DCF base 1,214.5 CIO-C053; scenario E[IRR] 4.69% CIO-C054; ADTV 1,209 CIO-C050 (+ share bridge CIO-C036).
- Unverified context item: "RBI repo hike to 5.50% on 7-Oct-2026" (valuation narrative) — NOT corroborated; not a model input (CIO-C047 notes).

## CIO DRAFT DECISIONS (to finalize after adversarial review)
- Hurdle = CoE 11.68% (CIO-C052; VAL-C026). Default-spread adjustment accepted (Damodaran method avoids double count). Alt 13.5% labelled.
- BQ guide inputs (calc/cio_bq_guides.out): median 10y ROIC 7.1% (const tax) / 8.2% (reported tax, 7 yrs) vs WACC 11.03% → spread −3.9/−2.8 pp → BQ1 band 30–44. FCF>0 8/10 yrs; CFO/PAT 10y 8.61x (FIN-C030). ND/EBITDA 0.79x; interest coverage FY2019 0.42x (trough) → BQ5 one band down.
- BQ draft: BQ1 44 | BQ2 62 | BQ3 58 | BQ4 72 (guide 85–100, one band down: equity FCF/PAT 0.23x 10y, recurring exceptionals 0.88x PAT) | BQ5 70 | BQ6 66 | BQ7 74 | BQ8 45 → ~60. Confidence Medium, band ±8. No BQ gates.
- IA draft: IA1 15 (tool) | IA2 32 (tool) | IA3 58 (P(loss≥30%) 10–20%; bear loss 33–41%) | IA4 2 (DEVIATION from tool 99: hurdle-adjusted asymmetry 0.063, VAL-C050; tool's undiscounted definition conflates 5y time value with upside) | IA5 30 (price ≈ bull case) | IA6 58 | IA7 80 | IA8 72 → ~35 → AVOID. Confidence Medium, band ±8. No IA gates.
- Layer fit: L1 52 (M) primary; L2 30 (M); L3 44 (M) secondary; L4 12 (H). Not hybrid (none ≥61).
- Valuation status: Expensive (price 33–55% above base range; 43% vs midpoint → guide says Extremely Expensive >35%; CIO chooses Expensive because EV/EBITDA within own history (71st pct), bull brackets price, and at labelled 10.1% WACC base value 1,538 → 16% above). STATE THIS EXPLICITLY.
- Adversarial review REQUIRED (draft verdict AVOID) → re-invoke bear-case with draft conclusion, attack errors of omission.
