---
specialist: bear-case
company: Bharti Airtel Limited
ticker: BHARTIARTL
exchange: NSE
run_id: 20261012T132311Z
research_cutoff: 2026-10-12
report_status: complete
model_requested: opus
independence_attestation: "Stage-3 follow-up: read only the CIO-authorised files (cio/scorecard.json, calc/cio_price_ladder*.json, calc/valuation_*.json, calc/cio_bq_guides.out, calc/cio_layer3_value.out) and primary documents in _cache; no other specialist reports were read."
coverage_exception: ""
---

# Bharti Airtel: Stage-3 Adversarial Review of the Draft AVOID (Follow-up 1)

## 1. Mandate and Bottom Line

**Mandate.** Attack the CIO's draft AVOID (IA 35, BQ 61) in the direction of omission. I steelman the case for owning at INR 1,778.70 [FACT: CIO-C001], test the draft's cost of capital, its IA4 deviation, its base-case operating assumptions and its scenario weights with arithmetic, and say plainly where the AVOID holds. No scores or recommendation.

**Bottom line.**
1. **One draft input looks materially one-sided: the base case carries no tariff round over ten years.**
   - The base growth and margin path matches organic drivers. The bull case is defined as "two further tariff rounds", and the Layer-3 value adds a round on top of the base [INFERENCE: BEAR-C084].
   - Three industry rounds have occurred since late 2019, at gaps of about 23 and 32 months [FACT: BEAR-C082]. A simple base rate puts the probability of at least one round in five years at 76–89 % [CALCULATION: BEAR-C083].
   - A conservatively sized round (realised +8 % on India mobile revenue, against the +14–16 % the draft itself cites per past round) adds about INR 163 a share to the base. Two rounds add about INR 304 [CALCULATION: BEAR-C085].
2. **The cost of equity is not materially wrong.**
   - Beta 0.87 sits inside my own regression range of 0.77–0.89 [CALCULATION: BEAR-C081].
   - The 7.39 % risk-free rate matches the 12-Oct-2026 G-Sec yield [FACT: BEAR-C080]. That yield is, however, a three-year high, and normalising it to about 6.9 % adds about INR 126 a share [CALCULATION: BEAR-C086]. That is a judgment call, not an error.
3. **The IA4 deviation is economically correct, not unfair.** The issue it reveals is redundancy: about 65 % of the IA weight expresses one DCF-versus-price gap [INFERENCE: BEAR-C101].
4. **Even the full steelman stack reaches only the AVOID/HOLD boundary.**
   - Two rounds plus a normalised risk-free rate plus a 25 % tax rate gives a base of INR 1,672–1,730 and a re-mapped IA of about 45–46 [CALCULATION: BEAR-C087].
   - That is one notch, to HOLD/NEUTRAL, and nowhere near BUY (IA ≥ 65).
   - The draft's other conservative-looking input, sales-to-capital 1.5, is in fact *generous* against history [CALCULATION: BEAR-C089]. Correcting it in the bear direction lowers the base to INR 1,110 [CALCULATION: BEAR-C088].
5. **The draft omits the owner's lens.**
   - E[IRR] of 4.7 % assumes the price converges to an 8.1x-EBITDA DCF value within five years [CALCULATION: BEAR-C093].
   - An owner who expects the current 10.9x multiple (minorities at market) to hold earns about 10–14 % a year on 8–10 % EBITDA growth [CALCULATION: BEAR-C092]: about the hurdle, not 7 points below it.
   - The AVOID therefore rests on a de-rating to near the FY2019–FY2021 trough multiple of 7.75–8.9x [FACT: BEAR-C094]. That is plausible, but it should be stated as the thesis.

## 2. Argument 1: The Base Case Omits the Base-Rate Tariff Path (the strongest omission)

**Evidence.**
- Rounds: late Nov/Dec-2019; 26-Nov-2021 (Airtel +20–25 %); 3-Jul-2024 (Airtel +10–21 %, after Jio moved on 27-Jun-2024) [FACT: BEAR-C082].
- At the cutoff, 27 months had elapsed since the last round, between the two prior gaps.
- Jio's IPO (DRHP filed 19-Jun-2026; fresh issue of about INR 37,700 crore; listing indicated for late October) [ESTIMATE: BEAR-C104] gives the price leader an obvious reason to show ARPU growth.
- Management frames ARPU growth of 4–5 % a year under a repaired architecture [MANAGEMENT STATEMENT: BEAR-C103]. That is not guidance of zero rounds.

**What the draft does.** The base (growth 12 % fading to 7 %, EBIT margin 33.5 % to 37 %) appears to embed no round [INFERENCE: BEAR-C084]. The draft's own P1 prediction puts 35 % on a round within 12 months, and the scorecard calls a round "elevated (40–60 %) in 24 months". A base case with a 40–60 % event in two years, and an 89 % event in five on the historical rate, should carry at least one round. Alternatively, the base should be the probability-weighted path.

**Arithmetic** (`calc/bear-case_followup_dcf_variants.py`, using `scripts/valuation_tools.dcf` on the draft's own inputs) [CALCULATION: BEAR-C085]:
- One round in year 2, at a realised +8 % on Mobile India revenue (53.6 % of consolidated revenue [CALCULATION: BEAR-C098]) with 90 % EBIT flow-through: base INR 1,215 → INR 1,378.
- Two rounds (years 2 and 5): INR 1,519. MoS −17 %; IA about 40.8 on draft weights.

**Caveat (bear side).** Three events is a tiny sample [CALCULATION: BEAR-C083], and Vodafone Idea's state-backed survival and new satcom entrants are a different regime. Still, the asymmetry of the draft's construction is that the bear case gets a stalled-repair path while the base gets the same no-round path.

## 3. Argument 2: The Cost of Equity (tested; mostly stands)

| Test | Result | Implication |
|---|---|---|
| Beta 0.87 | Weekly 2y 0.89, 5y 0.83, 10y 0.77; monthly 5y 0.80, 10y 0.77; Blume 0.85–0.92 [CALCULATION: BEAR-C081] | Not too high. A defensible range is 0.80–0.90 |
| Risk-free rate 7.39 % | 12-Oct-2026 10-year G-Sec at 7.3707 %, a three-year high after +54 bp in eight weeks and an RBI hike; about 6.9 % in April 2026 [FACT: BEAR-C080] | Spot is the convention. A normalised 6.9 % gives Ke 11.19 %, WACC 10.60 % and base INR 1,341 [CALCULATION: BEAR-C086] |
| "A AAA/BBB+ incumbent deserves a lower Ke" | A bond-yield-plus-premium check (pre-tax cost of debt 8.0 % per the draft WACC inputs, plus a 3–4 % equity premium) gives about 11–12 % [ESTIMATE: BEAR-C106] | No evidence-based route to the roughly 9.9 % Ke the price implies |

**Verdict on Argument 2.** It contributes at most about INR 125 a share and about 1.5 IA points [CALCULATION: BEAR-C086]. On its own the AVOID is unchanged.

## 4. Argument 3: IA4, the Scenario Weights and the Construction of E[IRR]

- **The IA4 deviation is correct economics.** The draft's horizon values are *constructed* as value today × (1+Ke)^5 less the future value of dividends [INFERENCE: BEAR-C101]. Comparing them with an uncompounded price, as the tool does, mixes bases and manufactures upside: the "asymmetry 4.8". The hurdle-adjusted 0.06 is reproducible; I get 0.05 [CALCULATION: BEAR-C090]. Using the tool's 99 would be an artefact, not a steelman.
- **But the scoring double-counts one input.** IA1 (MoS), IA2 (E[IRR]), IA4 (hurdle-adjusted asymmetry) and IA5 (reverse DCF), together 65 % of IA weight, all restate the base-DCF-versus-price gap [INFERENCE: BEAR-C101]. One conservative base input therefore moves four dimensions at once. That is why the base value, not IA4, decides the verdict: in every variant I ran, hurdle-adjusted IA4 stays at 2–4.
- **Scenario weights are not the swing factor.** Re-weighting the draft's own values to 15/50/35 or 10/45/45 lifts E[IRR] only to 6.0–7.4 % and IA to 36–37 [CALCULATION: BEAR-C091]. The bull's 25 % is not too low *as defined*: it bundles two rounds with sales-to-capital 2.0, a terminal ROIC of 18 % and a 42 % margin. The omission is that the tariff path should sit in the base (Argument 1), not that the bull weight should rise.

## 5. Argument 4: What a Five-Year-Plus Owner Sees That the Draft Misses

- **Cash and growth are real.**
  - FY2026 FCF after capex, spectrum, leases and interest was about INR 54,222 crore, 4.9 % of market cap [CALCULATION: BEAR-C102].
  - Q1FY2027 revenue was up 18.4 % YoY and EBITDA excluding other income about 19.6 % [CALCULATION: BEAR-C097].
- **But the growth mix needs care.**
  - Africa was +45.4 % in INR, partly from translation [CALCULATION: BEAR-C097].
  - Mobile India was +9.2 %, which matches the draft's 12 % → 7 % path rather than refuting it.
  - FY2026 spectrum cash was flattered by the FY2025 prepayment. FY2025–FY2026 licence additions averaged about INR 8,700 crore against amortisation of about INR 9,500–10,000 crore [FACT: BEAR-C096], so D&A is not obviously overstating replacement needs.
- **The return depends on the multiple path, not the DCF.**
  - The base DCF EV is about 8.1x TTM EBITDA [CALCULATION: BEAR-C093], against 10.9x at the price with minorities at market [CALCULATION: BEAR-C092]. The draft's E[IRR] assumes the market converges to the DCF in five years.
  - A constant multiple gives 10.4–11.6 % a year at 8 % EBITDA growth, 12.6–13.7 % at 10 % and 14.8–15.9 % at 12 % [CALCULATION: BEAR-C092]. A de-rating to 8.2x cuts that to 3.3–8.9 %.
  - The draft should state explicitly that the AVOID is a call that the multiple falls to about the FY2019–FY2021 trough (7.75–8.9x) [FACT: BEAR-C094], when ROIC was about 4–7 % rather than the 13.9 % in the draft's BQ1.
- **Smaller omitted items.**
  - Net tax assets of about INR 23 a share; FY2026 cash tax was only 55 % of the P&L charge [FACT: BEAR-C099]. The draft DCF taxes NOPAT at 27 % against a 25.1 % effective rate.
  - The promoter-group swap at INR 1,923, 8.1 % above the price [FACT: BEAR-C100]. This is weak evidence: it is related-party and partly reflects the Africa price.

## 6. Where the AVOID Is Well Founded

1. **The DCF is not conservative on capital intensity.**
   - Crude incremental sales-to-capital over FY2021–FY2026 was about 0.9, against the draft's 1.5 [CALCULATION: BEAR-C089]. That is overstated because NCI is excluded and Indus revenue is inorganic.
   - At 1.0 the base falls to INR 1,110 [CALCULATION: BEAR-C088].
   - The base's explicit-period reinvestment already implies an incremental ROIC well above the terminal 14 % (year-1 ΔNOPAT ÷ reinvestment ≈ 45 %) [CALCULATION: BEAR-C105].
2. **The cost of capital survives testing** [CALCULATION: BEAR-C081; FACT: BEAR-C080].
3. **IA4 handling is right** [CALCULATION: BEAR-C090].
4. **No combination of defensible changes produces BUY.** The best steelman lands at IA 45–46 [CALCULATION: BEAR-C087], and it stacks every judgment in the bull direction at once.
5. **Management guides to heavy capex** ("will not hold back") [MANAGEMENT STATEMENT: BEAR-C103]. The constant-multiple owner return needs 10 %+ EBITDA growth with no rise in capital intensity.

## 7. Effect on Value and IA (for the CIO's adjudication)

| Variant | Base value (INR/share) | MoS | E[IRR] (draft construction) | IA (re-mapped IA1/2/4; others held) |
|---|---|---|---|---|
| Draft base (reproduced) | 1,215 | −43 % (mid 1,244) | 4.5 % | 35.4 [CALCULATION: BEAR-C090] |
| Normalised risk-free rate (6.9 %) | 1,341 | −33 % | 4.9 % | 36.5 [CALCULATION: BEAR-C086] |
| One tariff round (year 2) | 1,378 | −29 % | 5.7 % | 37.4 [CALCULATION: BEAR-C085] |
| Two rounds (years 2 and 5) | 1,519 | −17 % | 6.9 % | 40.8 [CALCULATION: BEAR-C085] |
| Two rounds + normalised risk-free rate | 1,672 | −6 % | 7.7 % | 44.7 [CALCULATION: BEAR-C087] |
| + tax 25.17 % | 1,730 | −3 % | 8.1 % | 46.0 [CALCULATION: BEAR-C087] |
| Bear check: sales-to-capital 1.0 | 1,110 | −60 % | 3.3 % | 33.6 [CALCULATION: BEAR-C088] |

Draft bear and bull values were held fixed in these variants, which slightly understates the steelman.

**Suggested adjudication** [JUDGMENT]:
- **Materially wrong:** only the base-case tariff omission. A one-round base (about INR 1,378) is the defensible correction. It leaves MoS at about −29 % and IA at about 37, so **AVOID stands**.
- **Price ladder:** the AVOID threshold rises. The draft's "AVOID above INR 1,450" would move to roughly INR 1,650–1,750 on a two-round base.
- **Thesis statement:** the draft should say that its AVOID is a de-rating call [CALCULATION: BEAR-C092].

## 8. Questions for the CIO

1. Does the valuation specialist's base intentionally exclude any tariff round? If so, the Layer-1 base and the IA1 base should be the probability-weighted tariff path, not the zero-round path [INFERENCE: BEAR-C084].
2. Should the risk-free rate be the spot three-year high or a normalised level for a long-duration L1 valuation? Record it as a labelled sensitivity [CALCULATION: BEAR-C086].
3. Reconcile sales-to-capital 1.5 with history (about 0.9 crude) [CALCULATION: BEAR-C089]. If 1.5 stays, the base already contains a post-5G capital-light assumption favourable to the bull case.
4. State the multiple path behind E[IRR] 4.7 % [CALCULATION: BEAR-C093].

## 9. Source Register

| ID | Title | Issuer | Date | URL or identifier | Retrieved | Tier |
|---|---|---|---|---|---|---|
| S1 | Draft scorecard, valuation inputs and outputs | CIO / valuation (run files) | 2026-10-17 | cio/scorecard.json; calc/valuation_dcf_inputs*.json; calc/valuation_scenarios.json; calc/valuation_scenario_irr.json; calc/valuation_hurdle_asymmetry.json; calc/valuation_wacc*.json | 2026-10-17 | — |
| S2 | FY2026 Consolidated Financial Statements | Bharti Airtel Limited | 2026-07 | https://www.airtel.in/airtel-annual-report-2025-26/files/pdfs/Consolidated-Financial-Statements.pdf | 2026-10-12 | 1 |
| S3 | Q4FY2026 results and Quarterly Report | Bharti Airtel Limited | 2026-05-13 | FilingForge:b5c6beda-7ade-4dd3-ad4f-bff5e5efe4c1 | 2026-10-12 | 1/3 |
| S4 | Q1FY2027 results | Bharti Airtel Limited | 2026-08-04 | FilingForge:3a61007b-6d5a-449e-be4d-84dca645422b | 2026-10-12 | 1 |
| S5 | Q1FY2027 earnings transcript | Bharti Airtel Limited | 2026-08-10 | FilingForge:a46861ad-47c4-4fb1-9001-f56835e1a897 | 2026-10-12 | 4 |
| S6 | Quarterly Reports Q3FY2019, Q2FY2021, Q2FY2025 | Bharti Airtel Limited | 2019–2024 | FilingForge:16609b54-18cb-4a9b-9cf0-624572bc7d35; 0a99ebcf-7da7-484a-9868-81b346144036; 89f465d1-ee73-46a7-b90c-ecc6f49fcad8 | 2026-10-12 | 3 |
| S7 | Price series BHARTIARTL.NS and NIFTY 50 (weekly, monthly) | Yahoo Finance | 2026-10-17 (truncated at 2026-10-12) | https://query1.finance.yahoo.com/v8/finance/chart/BHARTIARTL.NS?range=10y&interval=1wk ; https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=10y&interval=1wk | 2026-10-17 | 5 |
| S8 | India 10-year bond yield at 3-year high | Kotak Neo | 2026-10-12 | https://www.kotakneo.com/news/global-markets/india-10-year-bond-yield-hits-3-year-high-rbi-liquidity-measures/ | 2026-10-17 | 6 |
| S9 | Airtel tariff-round coverage | Light Reading; Outlook Business | 2021-11; 2024-07 | https://www.lightreading.com/business-management/india-s-airtel-hikes-prepaid-tariffs-by-25- ; https://www.outlookbusiness.com/news/bharti-airtel-raises-mobile-tariffs-by-up-to-21-following-reliance-jios-move | 2026-10-17 | 6 |
| S10 | Jio IPO coverage | YourStory | 2026-10 | https://yourstory.com/2026/10/jio-ipo-nears-launch-drhp-filed-sebi-clears-path | 2026-10-12 | 6 |
| S11 | Screener consolidated tables | Screener | 2026-10-12 | https://www.screener.in/company/BHARTIARTL/consolidated/ | 2026-10-12 | 5 |
| C1 | Follow-up calculations | bear-case | 2026-10-17 | calc/bear-case_followup_dcf_variants.py, calc/bear-case_followup_owner_return.py, calc/bear-case_followup_beta.py, calc/bear-case_followup_misc.py (+ .out) | — | — |
