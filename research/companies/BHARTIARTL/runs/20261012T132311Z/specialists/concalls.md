---
specialist: concalls
company: Bharti Airtel Limited
ticker: BHARTIARTL
exchange: NSE
run_id: 20261012T132311Z
research_cutoff: 2026-10-12
report_status: complete
model_requested: opus
independence_attestation: "Initial investigation completed without reading other specialists' reports or prior-run conclusions for this company."
coverage_exception: ""
---

# Bharti Airtel: Concalls and Management-Guidance Record

## 1. Mandate, Scope and Independence

**Decision questions answered.** The agent definition sets seven questions:
1. What share of commitments was delivered?
2. Is guidance biased, and does the bias differ by topic?
3. Have goalposts moved?
4. Where do statements and statutory disclosures diverge?
5. How candid are explanations of misses?
6. Which analyst concerns recur?
7. Which current guidance deserves the least trust?

**In scope.**
- 40 quarters of original earnings-call transcripts, from Q3FY2016 (29-Jan-2016) to Q1FY2027 (5-Aug-2026).
- Extraction of quantified and dated commitments.
- Verification of outcomes against Airtel's filed results, including the Quarterly Report trend tables reproduced in the exchange results filings.
- A 70-row promise database: `specialists/concalls_workpapers/promise_database.csv`, built by `calc/concalls_promise_db.py`.
- Scripted statistics: `calc/concalls_stats.py` → `calc/concalls_stats.out`.
- Goalpost tracking, an analyst-concern tracker and a credibility weighting of current guidance.

**Out of scope.**
- Integrity and governance verdicts, which belong to management.
- Financial-statement analysis, which belongs to financials.
- Scores, layer choice and recommendations.
- The Hexacom portion of the joint webinars held since Q1FY2025, except where Airtel management spoke about Airtel.

**Method.** I read the Q&A first and then the prepared remarks.
- A sentence-level discovery filter (`calc/concalls_filter.py`) flagged forward-looking sentences and analyst questions with their page numbers.
- I confirmed every database row against the cited page of the transcript. Page numbers are PDF pages.
- Outcomes come from filed results. Material arithmetic is done in the scripts.

**Sector playbooks.** §16 Telecom (ARPU, capex/revenue, net debt incl. leases and DoT dues, 5G, home broadband) and §18 Holding companies (Indus, Africa, Nxtra and Hexacom statements).

**Blockers.**
- The Airtel IR CDN returned repeated SSL errors on several downloads on 12–13 Oct 2026: the Quarterly Reports for Q4FY2025, Q2FY2026 and Q1FY2027, and the Q1FY2027 and Q4FY2024 press releases. These are logged in `source_retrievals.csv`.
- I substituted the corpus copies of the filed results, which contain the same trend tables, plus the call transcripts.
- Nothing material was left unresolved because of this, so the status is complete.

## 2. Key Findings

1. **The overall record is mid-range, with a clear split by topic.**
   - Of 56 resolved commitments, 31 (55%) were exceeded, delivered or mostly delivered. Five were partially delivered, 10 were delayed and 10 were missed or withdrawn [CALCULATION: CON-C200].
   - Balance-sheet commitments were 6 of 6 on target: the leverage band, leverage of about 2x, net-debt reduction, spectrum prepayment and dividend step-ups [CALCULATION: CON-C204].
   - Capex commitments were 7 of 17 on target (41%) [CALCULATION: CON-C200].
2. **Capex guidance has a persistent overspend bias that has widened since 5G** [INFERENCE: CON-C201; CON-C202].
   - Level guidance overran by a median of +7.6% (mean +19.1%), and 9 of 11 outcomes came in above the guided level [CALCULATION: CON-C201].
   - Statements made from FY2023 onward overran by a median of 18.6%, against 6.9% before [CALCULATION: CON-C202].
3. **The most consequential miss was the 5G capex claim.**
   - In Feb-2021 management said 5G would bring no "material change in the capex profile" [MANAGEMENT STATEMENT: CON-C019].
   - India and South Asia capex then rose from ₹20,773 crore in FY2022 to ₹33,379 crore in FY2024 [FACT: CON-C111; FACT: CON-C113].
   - The narrative moved in steps: "same 3-year level" [MANAGEMENT STATEMENT: CON-C020], then "advancement of capex" (CON-C020 basis), then "₹28,000–31,000 crore" [MANAGEMENT STATEMENT: CON-C022], then "FY2024 peak" [MANAGEMENT STATEMENT: CON-C023].
4. **The latest "capex will fall" promise failed.**
   - Management said in May-2025: "our FY2026 capex will be lower than FY2025" [MANAGEMENT STATEMENT: CON-C024].
   - FY2026 capex rose 12.4% consolidated and 2.4% for India excluding passive infrastructure [CALCULATION: CON-C208].
   - The rise was pre-signalled in Nov-2025 as "some amount of elevated capex" [MANAGEMENT STATEMENT: CON-C028].
   - The current FY2027 guide is "ballpark of this year" [MANAGEMENT STATEMENT: CON-C025]. One call later, management spoke of "a period of rapid capex spend" on data centres [MANAGEMENT STATEMENT: CON-C029]. **This is the guidance the CIO should trust least** [JUDGMENT].
5. **The ARPU thesis has been consistent; its timing has been optimistic.**
   - "₹200 in the short term" (May-2020, ARPU ₹154) [MANAGEMENT STATEMENT: CON-C033] was first reached in Q1FY2024 [FACT: CON-C136], about 13 quarters later.
   - "₹200 preferably in 2022" ended at ₹193 in Dec-2022 [FACT: CON-C135].
   - The open target is "close to ₹300 ... in the next five years" from May-2022 [MANAGEMENT STATEMENT: CON-C036]. It needs a further 13.6% from Q1FY2027's ₹264 [CALCULATION: CON-C206], with no tariff repair announced.
6. **Dated technology and new-venture milestones usually slip but are eventually delivered.**
   - Ten resolved items were delayed and none was early [CALCULATION: CON-C205]. Examples: 5G launch "starting August" 2022 [MANAGEMENT STATEMENT: CON-C040]; VoLTE nationally in "6 to 9 months" [MANAGEMENT STATEMENT: CON-C044]; FWA "ready in the next six months" [MANAGEMENT STATEMENT: CON-C047]; cloud "in the next few months" [MANAGEMENT STATEMENT: CON-C057].
   - SA on FWA "within this quarter" (Aug-2024) was deferred twice and is now "at the right point in time" [MANAGEMENT STATEMENT: CON-C046].
7. **Capex guidance policy itself shifted.**
   - Management promised FY2020 guidance "next quarter" [MANAGEMENT STATEMENT: CON-C016], then withdrew formal capex guidance in May-2019 [MANAGEMENT STATEMENT: CON-C067].
   - It has since said repeatedly that it does not guide [MANAGEMENT STATEMENT: CON-C068], yet it referred to "the Rs 28,000 to Rs 31,000 Crore guidance that we have given" for FY2024 [MANAGEMENT STATEMENT: CON-C022].
   - Informal guidance therefore exists, but it is not consistently disclosed or tracked [INFERENCE].
8. **Home broadband roll-out targets were met or beaten, although the target itself was revised three times.**
   - 20–25 million home passes was reached on time [MANAGEMENT STATEMENT: CON-C060].
   - The 35 million three-year target reached 96% of target by Oct-2024 [CALCULATION: CON-C210].
   - The 40 million target was exceeded, with more than 45 million by Mar-2026 [MANAGEMENT STATEMENT: CON-C062].

## 3. Data Coverage

| Data series | Periods covered | Count | Sources and tier | Verification | Gaps and exceptions |
|---|---|---|---|---|---|
| Earnings-call transcripts (original) | Q3FY2016–Q1FY2027 | 40 quarters [CALCULATION: CON-C001] | Airtel IR CDN PDFs (25, via fetch_source.py) and FilingForge corpus (15); tier 4 | Full: every database row checked on its page | Q1FY2017, Q4FY2018 and Q1FY2020 not found on the IR results page. The catalog omits the Q1FY2025 transcript that is in the library [FACT: CON-C002] |
| Outcome data: capex, ARPU, net debt, leverage, DPS | FY2016–FY2026; quarterly ARPU Q3FY2018–Q1FY2027 | 11 fiscal years | Filed results with Quarterly-Report trend tables (FilingForge, tier 1); Q2FY2026 press release (tier 3) | Full for every outcome used; page-located | Three basis breaks: Infratel deconsolidation recast (FY2018–FY2020), Indus consolidation recast (from Q3FY2025) [FACT: CON-C122], subscriber/ARPU definition change (Q3FY2019) |
| Annual-report MD&A targets | FY2017–FY2025 (corpus) | 9 | FilingForge | Sampled only | The transcript window (from FY2016) covers the long-dated targets, so AR letters were not mined separately (see §14) |
| Investor presentations | Not used | 0 | — | — | The call transcripts carry the commitments |

## 4. Coverage of Communications

All calls listed below were read Q&A-first through the discovery filter. Database rows were confirmed on the cited page. "Web" means downloaded from assets.airtel.in via `scripts/fetch_source.py` and logged with its SHA-256. "Corpus" means FilingForge doc ID.

| Quarter | Call date | Channel / identifier |
|---|---|---|
| Q3FY2016 | 29-Jan-2016 | Web: Final-Cut transcript 4EA7F76F |
| Q4FY2016 | 28-Apr-2016 | Web: Transcript-of-web-cast 1FDD2458 |
| Q2FY2017 | 26-Oct-2016 | Web: 0EC37C4D |
| Q3FY2017 | 25-Jan-2017 | Web: 048526FB |
| Q4FY2017 | 10-May-2017 | Web: 1B2C95B4 |
| Q1FY2018 | 26-Jul-2017 | Web: F290617A |
| Q2FY2018 | 1-Nov-2017 | Web: 9B88DCBC |
| Q3FY2018 | 19-Jan-2018 | Web: F0AFBEE4 |
| Q1FY2019 | 27-Jul-2018 | Web: 0AABECC8 |
| Q2FY2019 | 26-Oct-2018 | Web: A754244B |
| Q3FY2019 | 1-Feb-2019 | Web: DE34C105 |
| Q4FY2019 | May-2019 (day not stated) | Web: CDC139CA |
| Q2FY2020 | 30-Oct-2019 | Web: C4B11DB7 (duplicate copy at Earnings_Call_Transcript-Q2FY20) |
| Q3FY2020 | 5-Feb-2020 | Web: Transcript…17022020 |
| Q4FY2020 | 19-May-2020 | Web: simplycms 01062020 |
| Q1FY2021 | 30-Jul-2020 | Web: simplycms (IR-moderated Q&A) |
| Q2FY2021 | Oct-2020 | Web: simplycms |
| Q3FY2021 | Feb-2021 | Web: simplycms 010321 |
| Q4FY2021 | 18-May-2021 | Web: simplycms 010621 |
| Q1FY2022 | 4-Aug-2021 | Web: simplycms 11082021 |
| Q2FY2022 | 3-Nov-2021 | Web: simplycms 6dec |
| Q3FY2022 | 9-Feb-2022 | Web: simplycms 01032022 |
| Q4FY2022 | 18-May-2022 | Web: simplycms 052422 |
| Q1FY2023 | 9-Aug-2022 | Web: simplycms 17082022 |
| Q2FY2023 | 1-Nov-2022 | Corpus 9b74c67a |
| Q3FY2023 | 8-Feb-2023 | Corpus fa591d96 |
| Q4FY2023 | 17-May-2023 | Corpus e5705279 (web copy identical) |
| Q1FY2024 | 4-Aug-2023 | Corpus 30e022d6 |
| Q2FY2024 | 1-Nov-2023 | Corpus 15fbc749 |
| Q3FY2024 | 6-Feb-2024 | Corpus 5f889b5d |
| Q4FY2024 | 15-May-2024 | Corpus 955dc315 |
| Q1FY2025 | 6-Aug-2024 | Corpus b6f3d368 (web copy identical) |
| Q2FY2025 | 29-Oct-2024 | Corpus 9a7c6df2 |
| Q3FY2025 | 7-Feb-2025 | Corpus 40b11be9 |
| Q4FY2025 | 14-May-2025 | Corpus 8e8cf451 |
| Q1FY2026 | 6-Aug-2025 | Corpus b9941a72 |
| Q2FY2026 | 4-Nov-2025 | Corpus ba4a97f1 |
| Q3FY2026 | 6-Feb-2026 | Corpus bccb6f0b |
| Q4FY2026 | 14-May-2026 | Web: quarterly_results/2025-26/Q4 transcript |
| Q1FY2027 | 5-Aug-2026 | Corpus a46861ad |

**Communication pattern.**
- Airtel moved from operator-run conference calls (to FY2020) to IR-moderated webinars with pre-collected questions (Q1FY2021–Q2FY2021).
- It then returned to open analyst Q&A. Since Q1FY2025 the calls have been joint Airtel and Hexacom webinars.
- From Q2FY2025 the speakers changed: Gopal Vittal as Vice-Chairman/Executive Vice Chairman and Shashwat Sharma as India MD & CEO. The MD & CEO succession happened as promised [MANAGEMENT STATEMENT: CON-C056].
- An IR link labelled "2026-27/Q2" transcript sits on the IR page. It postdates the cutoff and was not used.

## 5. Promise-to-Delivery Database

The full 70-row database, with every locator, outcome source and computed variance, is at `specialists/concalls_workpapers/promise_database.csv`.

**Conventions.**
- Variance = outcome ÷ target − 1, scripted. For capex, a positive variance means overspend.
- Capex outcomes are on the basis prevailing when the guidance was given (as reported). Recast bases are used only where the guidance was later restated on them.
- The material rows are shown below. "Locator" is the transcript PDF page.

| ID | Call | Commitment (abridged) | Locator | Outcome | Class | Var % |
|---|---|---|---|---|---|---|
| P01 | Q3FY2016 | FY2016 capex US$3.2–3.4bn, raised from US$3bn [MANAGEMENT STATEMENT: CON-C010] | p.4 | US$3,145 Mn [FACT: CON-C100] | Mostly delivered | −1.7 |
| P02 | Q4FY2016 | FY2017 capex ~US$3bn [MANAGEMENT STATEMENT: CON-C011] | p.6, p.19 | US$2,959 Mn [FACT: CON-C101] | Delivered | −1.4 |
| P04 | Q4FY2017 | FY2018 capex ~US$3bn [MANAGEMENT STATEMENT: CON-C012] | p.4, p.6 | US$4,162 Mn [FACT: CON-C102] | Missed | +38.7 |
| P05 | Q2FY2018 | FY2018 guide raised from ₹20,000 cr to ₹25,000 cr [MANAGEMENT STATEMENT: CON-C013] | p.5 | ₹26,818 cr [FACT: CON-C103] | Partially delivered | +7.3 |
| P06 | Q1FY2019 | FY2019 capex ₹270bn [MANAGEMENT STATEMENT: CON-C014] | p.5 | ₹28,743 cr [FACT: CON-C104] | Partially delivered | +6.5 |
| P07 | Q4FY2019 | FY2020 capex lower than FY2019 [MANAGEMENT STATEMENT: CON-C015] | p.5, p.11 | ₹25,359 cr [FACT: CON-C105] | Delivered | −11.8 |
| P08 | Q3FY2019 | "come back to you next quarter with [capex] guidance" [MANAGEMENT STATEMENT: CON-C016] | p.7 | Guidance withdrawn [MANAGEMENT STATEMENT: CON-C067] | Abandoned/withdrawn | — |
| P09 | Q4FY2020 | FY2021 capex lower [MANAGEMENT STATEMENT: CON-C017] | p.5, p.14 | ₹24,169 cr vs ₹24,487 cr recast [FACT: CON-C107; FACT: CON-C106] | Delivered | −1.3 |
| P10 | Q4FY2021 | FY2022 capex around FY2021 level [MANAGEMENT STATEMENT: CON-C018] | p.7 | ₹25,662 cr [FACT: CON-C108] | Delivered | +6.2 |
| P11 | Q3FY2021 | 5G brings no material change to the capex profile [MANAGEMENT STATEMENT: CON-C019] | p.6, p.8 | India&SA FY2024 ₹33,379 cr vs FY2022 ₹20,773 cr [FACT: CON-C113; FACT: CON-C111] | Missed | +60.7 |
| P18 | Q2FY2021 | "peak levels of capex ... now behind us" [MANAGEMENT STATEMENT: CON-C027] | p.5 | FY2024 ₹39,482 cr vs FY2019 ₹28,743 cr [FACT: CON-C110; FACT: CON-C104] | Missed | +37.4 |
| P12 | Q1FY2023 | 3-year capex at the same level (~₹23–24k cr/yr) [MANAGEMENT STATEMENT: CON-C020] | p.4–p.6 | FY2023–25 India ~₹91,806 cr [CALCULATION: CON-C207] | Missed | +30.2 |
| P13 | Q4FY2023 | FY2024 capex in the "same ballpark" as FY2023 [MANAGEMENT STATEMENT: CON-C021] | p.6 | ₹33,379 cr vs ₹28,155 cr [FACT: CON-C113; FACT: CON-C112] | Missed | +18.6 |
| P14 | Q1FY2024 | FY2024 India capex ₹28,000–31,000 cr [MANAGEMENT STATEMENT: CON-C022] | p.3 | ₹33,353 cr [FACT: CON-C114] | Partially delivered | +7.6 |
| P15 | Q2FY2024 | FY2024 the peak; FY2025 lower [MANAGEMENT STATEMENT: CON-C023] | p.7 | Recast ₹42,290 cr vs ₹48,927 cr [FACT: CON-C116; FACT: CON-C115] | Delivered | −13.6 |
| P16 | Q4FY2025 | "FY2026 capex will be lower than FY2025" [MANAGEMENT STATEMENT: CON-C024] | p.5 | ₹47,522 cr [FACT: CON-C117] | Missed | +12.4 |
| P20 | Q3FY2018 | "unlikely to see this kind of ARPU erosion going forward" [MANAGEMENT STATEMENT: CON-C030] | p.5 | ARPU ₹123 → ₹100 [FACT: CON-C130; FACT: CON-C131] | Missed | −18.7 |
| P21 | Q2FY2019 | ARPU trajectory "northward ... from here on" [MANAGEMENT STATEMENT: CON-C031] | p.10 | ₹129 by Q1FY2020 [FACT: CON-C132] | Delivered* | +29.0 |
| P22 | Q3FY2020 | Q4 ARPU better than Q3 [MANAGEMENT STATEMENT: CON-C032] | p.8 | ₹154 vs ₹135 [FACT: CON-C134; FACT: CON-C133] | Delivered | +14.1 |
| P23 | Q4FY2020 | ARPU ₹200 "in the short term" [MANAGEMENT STATEMENT: CON-C033] | p.3 | First ₹200 in Q1FY2024 [FACT: CON-C136] | Delayed | ~13 qtrs |
| P24 | Q3FY2022 | ARPU ₹200 "preferably in 2022" [MANAGEMENT STATEMENT: CON-C034] | p.9 | ₹193 in Dec-2022 [FACT: CON-C135] | Mostly delivered | −3.5 |
| P25 | Q3FY2022 | "I do expect a tariff hike sometime in 2022" [MANAGEMENT STATEMENT: CON-C035] | p.9 | Entry-plan repricing only; headline repair Jul-2024 [MANAGEMENT STATEMENT: CON-C037] | Partially delivered | — |
| P27 | Q1FY2025 | Jul-2024 repair flows through in two quarters [MANAGEMENT STATEMENT: CON-C037] | p.4 | ARPU ₹211 → ₹233 → ₹245 [FACT: CON-C137; FACT: CON-C138] | Delivered | — |
| P29 | Q1FY2023 | 5G launch "starting August" [MANAGEMENT STATEMENT: CON-C040] | p.4 | Commenced by the 1-Nov-2022 call | Delayed | — |
| P31 | Q4FY2022 | "more moderated rollout of 5G in the coming year" [MANAGEMENT STATEMENT: CON-C042] | p.6 | Switched to rapid pan-India rollout | Missed (plan reversed) | — |
| P32 | Q1FY2023 | No material spectrum spend "for many years" [MANAGEMENT STATEMENT: CON-C043] | p.4 | ~₹6,850 cr in Jun-2024 vs ₹43,040 cr in 2022 [MANAGEMENT STATEMENT: CON-C098] | Delivered | — |
| P33 | Q1FY2018 | VoLTE national in "6 to 9 months" [MANAGEMENT STATEMENT: CON-C044] | p.8 | Still "next 6 months" in Jul-2018 | Delayed | — |
| P34 | Q2FY2020 | 3G shut / 2100 MHz refarmed by Mar-2020 [MANAGEMENT STATEMENT: CON-C045] | p.8 | More refarming in "the coming quarter" (Q4FY2020 p.14) | Delayed | — |
| P35 | Q1FY2025 | SA on FWA "within this quarter" [MANAGEMENT STATEMENT: CON-C046] | p.5 | "by December", then "at the right point in time" | Abandoned/withdrawn | — |
| P36 | Q3FY2023 | FWA ready "in the next six months" [MANAGEMENT STATEMENT: CON-C047] | p.9 | Full roll-out end-CY2023, then "Q2" FY2025 | Delayed | — |
| P37 | Q4FY2024 | ~25,000 sites [MANAGEMENT STATEMENT: CON-C048] | p.5 | "about 25,000 new sites" in FY2025 | Delivered | 0.0 |
| P39 | Q3FY2016 | Robi merger complete in H1 2016 [MANAGEMENT STATEMENT: CON-C050] | p.3 | Completion announced by Jan-2017 | Delayed | — |
| P40 | Q2FY2018 | Telenor complete by Q4 FY2018 [MANAGEMENT STATEMENT: CON-C051] | p.4 | Completed 14-May-2018 | Delayed | ~6 wks |
| P41 | Q2FY2019 | Airtel Africa IPO, proceeds to debt [MANAGEMENT STATEMENT: CON-C052] | p.4 | Listed by Q2FY2020 | Delivered | — |
| P42 | Q2FY2021 | Indus–Infratel close in 10–20 days [MANAGEMENT STATEMENT: CON-C053] | p.6 | Completed 19-Nov-2020 | Delivered | — |
| P43 | Q1FY2023 | Decide on the ₹15,000+ cr rights calls "in the coming few months" [MANAGEMENT STATEMENT: CON-C054] | p.9 | Called only in FY2026 ("no provision to foreclose") | Delayed | — |
| P46 | Q2FY2025 | Cloud to market "in the next few months" [MANAGEMENT STATEMENT: CON-C057] | p.7 | Launched by Aug-2025 | Delayed | — |
| P48 | Q4FY2021 | 20–25 mn home passes in ~2 years [MANAGEMENT STATEMENT: CON-C060] | p.10 | 24–25 mn by Feb-2023 | Delivered | +20.0 |
| P49 | Q1FY2022 | 35 mn home passes, 2,000 towns, 3 years [MANAGEMENT STATEMENT: CON-C061] | p.3 | 33.5 mn by Oct-2024 [CALCULATION: CON-C210] | Mostly delivered | −4.3 |
| P50 | Q2FY2024 | 40 mn home passes target [MANAGEMENT STATEMENT: CON-C062] | p.5 | >45 mn by Mar-2026 | Exceeded | +12.5 |
| P51 | Q3FY2021 | LCO model in ~1,000 cities in a year [MANAGEMENT STATEMENT: CON-C063] | p.5 | 672 towns by Feb-2022 | Partially delivered | −32.8 |
| P52 | Q1FY2025 | 1.5 mn home passes per quarter [MANAGEMENT STATEMENT: CON-C064] | p.13 | ~7.2 mn in FY2025 | Exceeded | +20.0 |
| P54 | Q3FY2021 | Leverage 2x–3x [MANAGEMENT STATEMENT: CON-C070] | p.6 | 2.76x / 2.97x / 2.59x for FY2022–24 [FACT: CON-C150; FACT: CON-C151; FACT: CON-C152] | Delivered | — |
| P55 | Q1FY2024 | Leverage "closer to two" [MANAGEMENT STATEMENT: CON-C071] | p.10 | 1.86x Mar-2025; 1.29x Mar-2026 [FACT: CON-C153; FACT: CON-C154] | Delivered | −7.0 |
| P56 | Q3FY2023 | Net debt down in FY2024 [MANAGEMENT STATEMENT: CON-C072] | p.3 | ₹2,13,126 cr → ₹2,04,646 cr [FACT: CON-C155; FACT: CON-C156] | Delivered | −4.0 |
| P57 | Q4FY2024 | "further debt reduction going forward" [MANAGEMENT STATEMENT: CON-C073] | p.3 | Up in FY2025 (recast), −19% in FY2026 [FACT: CON-C157; FACT: CON-C158] | Delivered | −15.2 |
| P58 | Q3FY2022 | Prepay >₹15,000 cr of spectrum dues [MANAGEMENT STATEMENT: CON-C074] | p.3 | Paid in the quarter | Delivered | — |
| P59 | Q3FY2025 | "step-up of dividend for sure" [MANAGEMENT STATEMENT: CON-C075] | p.6 | DPS ₹8 → ₹16 → ₹24 [FACT: CON-C161; MANAGEMENT STATEMENT: CON-C162] | Delivered | — |
| P61 | Q3FY2018 | Three-operator structure by Mar-2019 [MANAGEMENT STATEMENT: CON-C083] | p.6 | VIL merger approved Jul-2018 | Delivered | — |
| P63 | Q2FY2023 | Nxtra 50% renewable power within 12 months [MANAGEMENT STATEMENT: CON-C081] | p.3 | "nearly half" by Aug-2025 | Delayed | — |
| P26 | Q4FY2022 | ARPU "close to Rs 300 ... in the next five years" [MANAGEMENT STATEMENT: CON-C036] | p.12 | ₹264 in Q1FY2027 [MANAGEMENT STATEMENT: CON-C141] | Not yet due | −12.0 to date |
| P19 | Q4FY2026 | FY2027 capex "in the ballpark of this year" [MANAGEMENT STATEMENT: CON-C025] | p.7 | — | Not yet due | — |
| P66 | Q3FY2026 | Data centres to 1 GW in 3–4 years from 120–130 MW [MANAGEMENT STATEMENT: CON-C091] | p.5, p.6 | — | Not yet due | — |

\*P21 is partly flattered by the subscriber-definition change [MANAGEMENT STATEMENT: CON-C099].

Rows not shown include reaffirmations, rows that cannot be determined (5G every-town coverage by Mar-2024, transfer of 16,100 towers to Indus, copper shutdown, Africa disposals) and the other not-yet-due items (postpaid >50 mn, Nxtra 3x, Airtel Money listing, 56 edge DCs, BTL stake path). All are in the CSV.

## 6. Guidance Accuracy Statistics

All counts come from `calc/concalls_stats.py` (output in `calc/concalls_stats.out`). Rows marked as reaffirmations (stats=N) are excluded.

**Sample.** There are 68 commitments. Of these, 56 are resolved, 8 are not yet due and 4 cannot be determined [CALCULATION: CON-C200]. With 56 resolved items the overall rates are reasonably robust. Topic sub-samples below 10 are **indicative only** (lens T17).

| Outcome class | Count (of 56 resolved) | Share |
|---|---|---|
| Exceeded | 3 | 5% |
| Delivered | 24 | 43% |
| Mostly delivered | 4 | 7% |
| **On-target subtotal** | **31** | **55%** [CALCULATION: CON-C200] |
| Partially delivered | 5 | 9% |
| Delayed | 10 | 18% [CALCULATION: CON-C205] |
| Missed | 8 | 14% |
| Abandoned/withdrawn | 2 | 4% |

The share column is scripted counts divided by 56, rounded.

**By topic (resolved).**

| Topic group | n | On-target | Partial | Delayed | Missed/abandoned | On-target % |
|---|---|---|---|---|---|---|
| Balance sheet / capital return | 6 | 6 | 0 | 0 | 0 | 100% [CALCULATION: CON-C204] |
| Homes | 5 | 4 | 1 | 0 | 0 | 80% (indicative) |
| ARPU / tariff | 7 | 4 | 1 | 1 | 1 | 57% (indicative) |
| Corporate / M&A | 7 | 4 | 0 | 3 | 0 | 57% (indicative) |
| Capex (incl. guidance policy) | 17 | 7 | 3 | 0 | 7 | 41% |
| Network / 5G / technology | 10 | 4 | 0 | 4 | 2 | 40% |
| New ventures (cloud, Nxtra ESG) | 2 | 0 | 0 | 2 | 0 | 0% (indicative) |
| Industry calls | 2 | 2 | 0 | 0 | 0 | 100% (indicative) |

**By period of statement.** On-target rates were broadly stable [CALCULATION: CON-C200]:
- FY2016–FY2019: 9 of 17 (53%).
- FY2020–FY2022: 10 of 17 (59%).
- FY2023–FY2027: 12 of 22 (55%).

The stability masks a change in mix. Recent misses cluster in capex, while recent hits cluster in deleveraging and dividends [INFERENCE].

**Capex variance.**
- Level guidance (n=11) shows variances of −1.7, −1.4, +38.7, +7.3, +6.5, +6.2, +60.7, +30.2, +18.6, +7.6 and +37.4%. The mean is +19.1%, the median +7.6%, and 9 of 11 were above guidance [CALCULATION: CON-C201].
- Statements made from FY2023 onward have a median of +18.6% (n=3), against +6.9% for FY2016–FY2022 (n=8) [CALCULATION: CON-C202].
- Directional "capex will be lower next year" calls were right in 3 of 4 cases (FY2020, FY2021, FY2025) and wrong for FY2026 [CALCULATION: CON-C203].

**Bias direction.**
- **Capex: optimistic.** Spend usually exceeds what is guided, and restraint statements are revised upward within one to three quarters.
- **ARPU: direction accurate, timing optimistic.**
- **Technology timelines: optimistic.** There were 10 delays and no early deliveries.
- **Balance sheet: accurate to conservative.** Leverage reached about 2x roughly on schedule and then fell to 1.29x [FACT: CON-C154].

[JUDGMENT: CON-C300]

**Signal vs. noise (T17).**
- The capex overspend is not a single-year artefact. It appears in FY2018, FY2019, FY2023, FY2024 and FY2026, across two technology cycles, with 9 of 11 observations on the same side [CALCULATION: CON-C201].
- The "balance sheet always delivered" result rests on only 6 items, all in a period of strong EBITDA growth after the tariff repair. It has not been tested in a downturn [INFERENCE: CON-C204].

## 7. Goalpost Changes and Revisions

Goalpost codes match the `goalpost_link` column in the database.

| Code | Target | How it moved | Disclosed and explained? |
|---|---|---|---|
| G1 | Capex level | FY2018: US$3bn [MANAGEMENT STATEMENT: CON-C012], then ₹20,000 cr, then ₹25,000 cr [MANAGEMENT STATEMENT: CON-C013]. 5G cycle: "no material change" (Feb-2021) [MANAGEMENT STATEMENT: CON-C019], then "3-year same level, 18-month advancement" (Aug-2022) [MANAGEMENT STATEMENT: CON-C020], then "~₹23–24k cr per year" baseline (Nov-2022), then "FY2024 same ballpark as FY2023" [MANAGEMENT STATEMENT: CON-C021], then "₹28–31k cr guidance" [MANAGEMENT STATEMENT: CON-C022], then "FY2024 the peak" [MANAGEMENT STATEMENT: CON-C023]. FY2026: "will be lower" [MANAGEMENT STATEMENT: CON-C024], then "some amount of elevated capex" [MANAGEMENT STATEMENT: CON-C028]. FY2027: "ballpark of this year" [MANAGEMENT STATEMENT: CON-C025], then "a period of rapid capex spend" [MANAGEMENT STATEMENT: CON-C029] | Each upward step was disclosed on a call, usually with a reason (Jio competition, 5G front-loading, rural rollout, homes and Nxtra). The earlier statement being replaced was not acknowledged [INFERENCE] |
| G2 | Capex guidance itself | Annual capex guidance was given FY2016–FY2019. Management promised FY2020 guidance "next quarter" [MANAGEMENT STATEMENT: CON-C016], then withdrew it [MANAGEMENT STATEMENT: CON-C067]. Later it cited "the guidance that we have given" for FY2024 [MANAGEMENT STATEMENT: CON-C022] | Disclosed. Rationale: "we normally do not give guidance on revenue or profit". Metric switch from numeric guidance to directional statements |
| G3 | ARPU definition | Q3FY2019 introduced a "more stringent" revenue-earning subscriber definition, quoting exit ARPU ₹118 against reported ₹104 [MANAGEMENT STATEMENT: CON-C099; FACT: CON-C131] | Disclosed. It flatters the ARPU "northward" call (P21) |
| G4 | ARPU ₹200 / ₹300 | ₹200 "short term" (May-2020) [MANAGEMENT STATEMENT: CON-C033], then "preferably in 2022" [MANAGEMENT STATEMENT: CON-C034], then "first goal post 200, eventual 300" (May-2022). ₹300: "end stage" (Feb-2020), then "in the next five years" (May-2022) [MANAGEMENT STATEMENT: CON-C036], then "longer-term goal post" (Aug-2023). By FY2026 the framing became "pricing architecture ... broken and needs to be repaired" with organic levers in the meantime [MANAGEMENT STATEMENT: CON-C085] | The ₹300 date was given once (May-2022) and not repeated. The framing moved from a dated target to an industry-structure argument [INFERENCE] |
| G5 | VoLTE national | "6 to 9 months" (Jul-2017) [MANAGEMENT STATEMENT: CON-C044], then "major cities by end FY18", then "next 6 months" (Jul-2018) | The slip was not explained |
| G6 | FWA / 5G SA | FWA "ready in six months" (Feb-2023) [MANAGEMENT STATEMENT: CON-C047], then "full by end CY2023", then "full scale in Q2" FY2025. SA on FWA "this quarter" (Aug-2024) [MANAGEMENT STATEMENT: CON-C046], then "by December", then "at the right point in time" | Partly explained (indoor CPE issues; "no need to hurry" on SA) |
| G7 | Indus–Infratel merger | Long-stop extended repeatedly in FY2020: "no assurance that this can be completed within the due time" [MANAGEMENT STATEMENT: CON-C069]. Closed Nov-2020 [MANAGEMENT STATEMENT: CON-C053] | Disclosed. The cause was external (Vodafone Idea and AGR uncertainty) |
| G8 | Rights-issue residual call (~₹15,000 cr) | "Evaluate in the coming few months" (Aug-2022) [MANAGEMENT STATEMENT: CON-C054], then "no necessity" (FY2024), then called in FY2026 because "3 years ... is now over, we have no provision to foreclose" | Disclosed. The reason given (a contractual end-date) needs checking against the letter of offer (see §11) |
| G9 | Home passes | 20–25 mn in two years (May-2021) [MANAGEMENT STATEMENT: CON-C060], then 35 mn in three years (Aug-2021) [MANAGEMENT STATEMENT: CON-C061], then "on track to 30 million" (Feb-2023) [MANAGEMENT STATEMENT: CON-C066], then "40 million targeted" (Nov-2023) [MANAGEMENT STATEMENT: CON-C062] | The cut to 30 mn was not presented as a cut. The later raise to 40 mn was achieved |

**Basis changes that affect tracking.** These are disclosed but break the series:
- The Infratel deconsolidation recast (FY2018–FY2020 capex restated) [FACT: CON-C106].
- The Indus consolidation recast of capex and net debt (from Q3FY2025) [FACT: CON-C122].
- The Q3FY2019 subscriber definition [MANAGEMENT STATEMENT: CON-C099].

Net debt "reduction" after Mar-2024 must be read on the recast basis. On that basis consolidated net debt rose in FY2025 before falling 19% in FY2026 [FACT: CON-C157; FACT: CON-C158].

## 8. Statements versus Statutory Disclosures

1. **"We do not give capex guidance" vs. guidance actually cited.** Management stated repeatedly that it does not guide [MANAGEMENT STATEMENT: CON-C067; MANAGEMENT STATEMENT: CON-C068]. On the Q1FY2024 call it referred to "the Rs 28,000 to Rs 31,000 Crore guidance that we have given for the year" [MANAGEMENT STATEMENT: CON-C022]. I did not locate where that range was first given (§14). The pattern is selective, informal guidance that is hard to hold to account [INFERENCE].
2. **5G capex neutrality vs. filed capex.** The claim that 5G would bring no "material change in the capex profile" [MANAGEMENT STATEMENT: CON-C019] compares with filed India and South Asia capex up 61% between FY2022 and FY2024 [FACT: CON-C111; FACT: CON-C113].
3. **FY2026 "lower capex" vs. filed FY2026 capex.** Consolidated capex was ₹4,75,218 Mn against ₹4,22,904 Mn [FACT: CON-C117; FACT: CON-C116]. The filing itself attributes the rise to 5G densification, fibre, homes, B2B and data centres. Homes capex rose 58% and passive-infrastructure capex 28% [FACT: CON-C120; FACT: CON-C121].
4. **"Further debt reduction" (May-2024) vs. reported net debt.** Consolidated recast net debt rose from ₹19,43,799 Mn to ₹20,38,384 Mn in FY2025 [FACT: CON-C157]. Indus consolidation explains part of this. It fell sharply in FY2026 [FACT: CON-C158]. Over two years the statement holds; over one year it does not.
5. **Internal inconsistency on the Q4FY2025 call.** FY2025 site additions were stated as "19,858 network sites" (p.3) and "about 25,000 new sites" (p.4) on the same call [MANAGEMENT STATEMENT: CON-C048]. These are probably different definitions (5G sites vs. network sites), but the call did not reconcile them [INFERENCE].
6. **Rights issue.** The statement that there was "no provision to foreclose" the call after three years (Q3FY2026 p.6) [MANAGEMENT STATEMENT: CON-C054] needs checking against the 2021 letter of offer. That is a dependency for filings.
7. **ARPU reporting is consistent with filings.** Every ARPU figure management quoted on calls that I checked matched the filed trend tables (for example Q4FY2020 ₹154, Q1FY2024 ₹200, Q3FY2025 ₹245) [FACT: CON-C134; FACT: CON-C136; FACT: CON-C138]. I found no case of a call figure contradicting a filing [INFERENCE].
8. **Corpus label glitch.** The 14-May-2024 results document headed "year ended March 31, 2023" is in fact the FY2024 filing [FACT: CON-C003].

## 9. Responses to Misses

| Miss | Explanation offered | Plausibly external? | Candour |
|---|---|---|---|
| FY2018 capex overrun (P04/P05) | Raised mid-year to "tactically advance" capex to win revenue market share against a below-cost new entrant [MANAGEMENT STATEMENT: CON-C013] | Partly. Competitive entry is external; the decision to spend was internal | Pre-announced and specific. High |
| ARPU erosion after Jan-2018 (P20) | Entrant pricing; industry revenue said to fall from ~₹45,000 cr to ~₹30,000 cr a quarter (Q2FY2019 p.3); later the minimum-ARPU plans | Largely external and industry-wide (TRAI data would verify; industry specialist) | Specific |
| 5G capex overrun (P11–P14) | "Advancement of capex from the following year" (Q2FY2023 p.6); "three-year view" (Q3FY2023 p.7); then "peak year" | Mostly internal. The pace was management's choice after the Aug-2022 auction [MANAGEMENT STATEMENT: CON-C098] | **Selective.** The original "no material change" claim was never acknowledged; the comparison window kept shifting [INFERENCE] |
| FY2026 capex rise (P16) | Pre-signalled in Nov-2025 [MANAGEMENT STATEMENT: CON-C028]: fibre "land grab", Nxtra, 5G densification | Internal growth choices | Disclosed in advance, but presented as a change of plan rather than a miss |
| Tariff hike not in 2022 (P25) | Always caveated: "cannot commit", depends on competitors | External (industry pricing) | Consistent caveats. Standard |
| Telenor / Robi / Indus delays (P39, P40, G7) | Regulatory approvals; long-stop extensions | External and verifiable through approvals | High (G7 explicitly warned of "no assurance") |
| VoLTE / 3G / FWA / SA / cloud slips | VoLTE: device certification; FWA: indoor CPE problems (Q2FY2024 p.8); SA: "no need to hurry" (Q2FY2025 p.12); cloud: not explained | Mixed; mostly execution or technology readiness | Variable. VoLTE and cloud slips were not explicitly acknowledged |

**Pattern.** Externally caused misses (regulation, competitor pricing) are explained specifically and early. Self-chosen misses (capex pace, technology dates) are reframed rather than acknowledged [JUDGMENT: CON-C302]. This is a communication pattern only. I make no finding of intent, and that judgement belongs to management/CIO.

## 10. Analyst Concern Tracker

The locators below are transcript pages where the analyst question appears. The answers are summarised from management statements already in the ledger.

| Concern | Quarters in which it recurred (examples, page) | How the answer evolved |
|---|---|---|
| Tariffs and ARPU path | Q2FY2018 p.15 ("ARPU back to Rs.200?"), Q1FY2019 p.6, Q3FY2020 p.6, Q1FY2022 p.11, Q3FY2022 p.9, Q4FY2022 p.6/p.11, Q2FY2024 p.12, Q4FY2024 p.6, Q2FY2025 p.8/p.10, Q3FY2026 p.8, Q4FY2026 p.6/p.12, Q1FY2027 p.6: asked in almost every call | FY2017–18: "ARPU game", no number. FY2020: ₹200 short term / ₹300 end state [MANAGEMENT STATEMENT: CON-C033]. FY2022: "hope 2022", "cannot commit" [MANAGEMENT STATEMENT: CON-C035]. FY2024: industry-wide "repair ... a couple of rounds". FY2026–27: "pricing architecture broken", organic levers [MANAGEMENT STATEMENT: CON-C085] |
| Capex level and intensity | Q2FY2017 p.5, Q4FY2017 p.8, Q3FY2018 p.5, Q1FY2019 p.5/p.8, Q3FY2019 p.16, Q4FY2019 p.5, Q4FY2021 p.6, Q1FY2022 p.7 ("India capex elevated ... while guidance flattish"), Q2FY2022 p.10 ("capex has been pretty sticky"), Q1FY2023 p.5, Q3FY2023 p.7, Q4FY2023 p.6, Q1FY2024 p.8, Q3FY2024 p.5, Q4FY2024 p.9/p.12, Q2FY2025 p.6, Q4FY2025 p.6, Q1FY2026 p.8, Q2FY2026 p.16, Q3FY2026 p.15, Q4FY2026 p.7/p.8, Q1FY2027 p.7 | From numeric guidance (to FY2019), to "will be lower", to a "three-year view", to "we do not give guidance but ... ballpark", to "we will not hold back on capex" [MANAGEMENT STATEMENT: CON-C029]. **The most persistent analyst doubt, and the one the record vindicates** [INFERENCE: CON-C201] |
| Leverage, ratings, deleveraging | Q2FY2017 p.14, Q3FY2017 p.12, Q4FY2017 p.14 (Moody's 3x), Q3FY2018 p.6/p.10, Q1FY2019 p.7, Q3FY2020 p.10/p.12, Q1FY2021 p.10, Q4FY2021 p.11, Q2FY2023 p.13, Q1FY2024 p.10, Q3FY2024 p.7/p.9, Q3FY2026 p.12 | 2x–3x band [MANAGEMENT STATEMENT: CON-C070], then "closer to two" [MANAGEMENT STATEMENT: CON-C071], then delivered. The concern has faded as leverage reached 1.29x [FACT: CON-C154] |
| Dividends, rights call, use of FCF | Q3FY2021 p.10, Q1FY2023 p.9, Q4FY2023 p.12, Q3FY2024 p.8/p.9, Q4FY2024 p.14/p.16, Q1FY2025 p.6, Q4FY2025 p.6/p.12, Q1FY2026 p.10, Q3FY2026 p.6/p.7, Q4FY2026 p.5 | Dividends to deleverage, then "time will come to return money", then "progressive dividend" (₹4 → ₹8 → ₹16 → ₹24) [FACT: CON-C160; FACT: CON-C161; MANAGEMENT STATEMENT: CON-C162]. Q4FY2026 analysts noted payout below ~40% of FCF |
| Home broadband share vs. competition | Q4FY2017 p.9, Q2FY2019 p.7, Q2FY2021 p.9, Q4FY2021 p.9, Q4FY2024 p.7, Q1FY2025 p.10, Q3FY2025 p.6, Q2FY2026 p.7/p.13, Q1FY2027 p.10 | Management admitted "we are not competitively where we should be" (Q3FY2025 p.6). Roll-out targets were met (G9), but no share target was set |
| 5G monetisation and timing | Q1FY2021 p.8, Q3FY2021 p.6/p.8, Q2FY2022 p.11, Q4FY2022 p.10, Q1FY2023 p.5/p.11, Q4FY2023 p.7, Q2FY2024 p.10, Q3FY2024 p.8, Q1FY2025 p.11, Q3FY2025 p.10, Q3FY2026 p.8 | "Couple of years out" (accurate). After launch: "5G has become really about free data" (Q3FY2024 p.8); differential pricing "we will have to rethink" (Q3FY2026 p.8) |
| B2B growth slowdown | Q1FY2025 p.9 ("sudden slowdown"), Q3FY2025 p.12, Q4FY2025 p.11, Q4FY2026 p.10 | Explained by exiting a low-margin commodity business; delivered as guided [MANAGEMENT STATEMENT: CON-C058] |
| AGR dues | Q2FY2020 p.5/p.8/p.14, Q1FY2021 p.7, Q2FY2025 p.8, Q2FY2026 p.7, Q3FY2026 p.7/p.9 | Consistent: awaiting government/DoT; seeks parity with relief given to others |
| Data centres (new) | Q4FY2025 p.7/p.10, Q2FY2026 p.6/p.7, Q3FY2026 p.6/p.9/p.12, Q1FY2027 p.7/p.9 | From "modest ... aspirations" [MANAGEMENT STATEMENT: CON-C084] to 1 GW in 3–4 years [MANAGEMENT STATEMENT: CON-C091], with Nxtra to "lever up". This is the new capex worry |

## 11. Current Guidance and Credibility-Weighted View

The credibility weight reflects the track record for each topic (§6). Probability bands follow the constitution and are judgments.

| Current guidance (latest call) | Track-record base | Credibility | What it means for the CIO |
|---|---|---|---|
| FY2027 capex "in the ballpark of this year, give or take" [MANAGEMENT STATEMENT: CON-C025], in the context of Q1FY2027's "period of rapid capex spend" [MANAGEMENT STATEMENT: CON-C029] | Capex level calls: median +7.6% overspend; FY2023+ median +18.6% [CALCULATION: CON-C201; CON-C202] | **Lowest** | Elevated probability (40–60%) that FY2027 consolidated capex exceeds FY2026 by more than 5%, driven by Nxtra, fibre and the Indus build [JUDGMENT]. Model capex above guidance |
| ARPU "close to ₹300 ... in the next five years" (May-2022) [MANAGEMENT STATEMENT: CON-C036] | ARPU timing optimistic (P23 delayed, P24 short); +13.6% still needed [CALCULATION: CON-C206] | Low on timing, high on direction | Low probability (5–20%) of ~₹300 by mid-2027 without an industry tariff move [JUDGMENT]. Treat tariff repair as an unpriced event, not a dated guide |
| Data centres to 1 GW in 3–4 years [MANAGEMENT STATEMENT: CON-C091]; Nxtra 3x revenue/EBITDA in 2–3 years [MANAGEMENT STATEMENT: CON-C095] | New-venture and technology milestones: 0 of 2 and 4 of 10 on time [CALCULATION: CON-C205] | Low to moderate | Expect slippage of one to several quarters. Capacity claims need MW-commissioned disclosure every quarter, which is not yet reported in what I read |
| Postpaid "upwards of 50 million over the next few years" [MANAGEMENT STATEMENT: CON-C090] | No resolved precedent | Unrated | No date, so it cannot be held to account |
| Progressive dividend, continued deleveraging [MANAGEMENT STATEMENT: CON-C075] | 6 of 6 balance-sheet items on target [CALCULATION: CON-C204] | **Highest** | High probability (>60%) of FY2027 DPS ≥ ₹24 absent a large acquisition [JUDGMENT]. Watch for Nxtra debt and Africa stake purchases diluting the deleveraging line |
| ~₹50,000 crore India FCF "on track" [MANAGEMENT STATEMENT: CON-C097] | Not resolved; the period definition was unclear on the call | Moderate | The financials specialist should reconcile it to the cash-flow statement |
| Airtel Money London listing in H2 2026 [MANAGEMENT STATEMENT: CON-C092] | Airtel Africa IPO delivered (P41); corporate-event timelines delayed in 3 of 7 cases | Moderate | Event risk to timing, not to intent |
| BTL to buy 3.6% over 3–4 years; buybacks "in the next couple of years" (Chairman) [MANAGEMENT STATEMENT: CON-C094] | No precedent | Unrated | Signals a promoter-funding motive for higher payouts and buybacks (management specialist) |

**What management is setting expectations to (T9).** The current framing does three things [INFERENCE: CON-C029; CON-C085; CON-C091]:
- It shifts the growth narrative from tariff repair, which is outside management's control, to adjacencies: data centres, cloud and finance.
- It pre-positions higher capex as "investing for growth".
- It keeps the ₹300 ARPU as a structural argument rather than a dated promise.

On this record, consensus models that assume capex intensity keeps falling are most exposed [JUDGMENT].

## Four-Layer Evidence Crosswalk

### Layer 1 — Bedrock Compounder
- **Relevant evidence:** The consistency of long-run strategic statements and of the reinvestment promises that set the capital intensity of compounding.
- **Supports:** The strategy has been stated in the same terms since FY2020: quality customers, ARPU to ₹300 for a ~15% return on capital, and deleveraging [MANAGEMENT STATEMENT: CON-C036; JUDGMENT: CON-C303]. Balance-sheet commitments were 6 of 6 on target [CALCULATION: CON-C204].
- **Weakens:** Promises of capital restraint are unreliable. Capex-level guidance overran by a median of 7.6%, and by 18.6% since FY2023 [CALCULATION: CON-C201; CALCULATION: CON-C202]. The claim that 5G was capex-neutral failed [MANAGEMENT STATEMENT: CON-C019; FACT: CON-C113]. This means the reinvestment needed to defend returns has repeatedly been larger than signalled.
- **Domain implications:** Through-cycle ROCE and FCF models should not take management's capex trajectory at face value. Incremental returns must be measured on actual, not guided, capex.
- **Missing information:** Management's own ROCE targets ("we do not set those as targets", Q1FY2027 p.11). The source of the FY2024 ₹28–31k crore guidance.
- **Plausibility effect:** No change — strategic consistency and balance-sheet delivery offset the capex-restraint record.

### Layer 2 — High-Growth Business
- **Relevant evidence:** The record on growth targets, launches and scaling milestones (homes, postpaid, B2B, 5G/FWA).
- **Supports:** Home-pass targets were delivered or exceeded: 20–25 mn on time, 35 mn at 96%, 40 mn exceeded [MANAGEMENT STATEMENT: CON-C060; CALCULATION: CON-C210; MANAGEMENT STATEMENT: CON-C062]. Roll-out pace beat guidance (1.5 mn per quarter guided, ~7.2 mn per year delivered) [MANAGEMENT STATEMENT: CON-C064].
- **Weakens:** Product launches slipped: FWA, SA, cloud and the LCO city count (672 vs. 1,000) [MANAGEMENT STATEMENT: CON-C047; MANAGEMENT STATEMENT: CON-C046; MANAGEMENT STATEMENT: CON-C057; MANAGEMENT STATEMENT: CON-C063]. Management concedes home-broadband share is behind (Q3FY2025 p.6).
- **Domain implications:** Infrastructure-build targets are credible. Share and monetisation outcomes from that build are not yet evidenced and carry no targets.
- **Missing information:** Home-broadband market-share data (industry); postpaid net-add history against the 50 mn ambition.
- **Plausibility effect:** Raises — build-out commitments in the growth segments have been met or beaten, although monetisation remains unproven.

### Layer 3 — Cyclical / Event-Driven Opportunity
- **Relevant evidence:** The record on tariff-repair predictions, turnaround timelines, deleveraging and capital-return promises.
- **Supports:** Deleveraging and capital-return promises were delivered: leverage 2.97x to 1.29x, DPS ₹4 to ₹24 [FACT: CON-C151; FACT: CON-C154; FACT: CON-C160; MANAGEMENT STATEMENT: CON-C162]. The Jul-2024 repair flowed through as guided [MANAGEMENT STATEMENT: CON-C037; FACT: CON-C138].
- **Weakens:** Management's dates for tariff repair have been unreliable as catalyst timing. "₹200 short term" took about 13 quarters; "tariff hike in 2022" did not happen [MANAGEMENT STATEMENT: CON-C033; MANAGEMENT STATEMENT: CON-C035]. The next repair is now framed as an industry "architecture" change with no date [MANAGEMENT STATEMENT: CON-C085].
- **Domain implications:** A repair-driven Layer-3 thesis should not borrow management's timing. Deleveraging and payout statements can be weighted more heavily.
- **Missing information:** Competitor pricing intent (industry specialist); the rights-issue terms (filings specialist).
- **Plausibility effect:** Raises — capital-return and deleveraging promises are the most reliable part of the record, but catalyst timing must come from outside management guidance.

### Layer 4 — Venture-Style / Optionality Bet
- **Relevant evidence:** The record on new-venture milestones (cloud, Nxtra, FWA/SA, Payments Bank and Airtel Money listings) and the financing statements behind them.
- **Supports:** The Airtel Africa IPO and the Indus merger closed as indicated once approvals arrived [MANAGEMENT STATEMENT: CON-C052; MANAGEMENT STATEMENT: CON-C053]. Cloud did launch [MANAGEMENT STATEMENT: CON-C057].
- **Weakens:**
  - New-venture and technology milestones were 0 of 2 and 4 of 10 on time [CALCULATION: CON-C205].
  - Management itself called its data-centre ambitions "modest" until 2025 [MANAGEMENT STATEMENT: CON-C084].
  - The 1 GW target in 3–4 years [MANAGEMENT STATEMENT: CON-C091] is new, large relative to 120–130 MW, and to be partly debt-funded at Nxtra [MANAGEMENT STATEMENT: CON-C029].
- **Domain implications:** Optionality claims (data centres, cloud, finance) should be valued with timelines extended and probabilities haircut against management's stated milestones.
- **Missing information:** Quarterly MW commissioned, Nxtra capex and funding plan, cloud customer and revenue disclosure.
- **Plausibility effect:** Lowers — the record on dated new-venture milestones is weak, so the timing of optionality claims deserves a discount.

## Contradictions and Data Conflicts

| Item | Values | Likely cause | Resolution | Confidence |
|---|---|---|---|---|
| FY2018–FY2020 consolidated capex | As reported ₹2,68,176 / ₹2,87,427 / ₹2,53,586 Mn vs recast ₹2,56,870 / ₹2,78,319 / ₹2,44,866 Mn [FACT: CON-C104; FACT: CON-C106] | Infratel deconsolidation recast | Guidance compared on the basis prevailing when it was given (as reported). The FY2021 test uses the recast basis | H |
| FY2022–FY2024 capex | Pre-Indus ₹2,56,616 / ₹3,41,947 / ₹3,94,821 Mn vs recast ₹2,85,563 / ₹3,82,145 / ₹4,89,268 Mn [FACT: CON-C110; FACT: CON-C115] | Indus consolidation recast [FACT: CON-C122] | As above. FY2025 and FY2026 tests use the recast basis plus India ex-passive | H |
| FY2025 site additions | "19,858 network sites" vs "about 25,000 new sites" on the same call [MANAGEMENT STATEMENT: CON-C048] | Different site definitions | Treated P37 as delivered on management's own 25,000 framing; flagged | M |
| Q3FY2019 ARPU | Reported ₹104 vs exit ₹118 on the new definition [FACT: CON-C131; MANAGEMENT STATEMENT: CON-C099] | Definition change | Reported series used | H |
| FY2024 guidance range | "We do not give guidance" vs "₹28,000–31,000 crore guidance that we have given" [MANAGEMENT STATEMENT: CON-C068; MANAGEMENT STATEMENT: CON-C022] | Informal guidance channel | Treated as guidance (P14) | M |
| Corpus catalog | Catalog says the Q1FY2025 transcript is missing; the library holds it [FACT: CON-C002] | Catalog/period inference | Used the library copy; the web copy is identical | H |

## Assumptions, Uncertainty and Missing Evidence

| # | Assumption | Why necessary | Supporting evidence | Plausible alternative | Effect if wrong | Confidence |
|---|---|---|---|---|---|---|
| 1 | FY2016–FY2019 capex guidance was on a consolidated basis | Guidance basis not always stated | ₹82.1bn Q1FY2019 capex matches the consolidated quarterly figure | India-only basis | FY2018/19 overrun would be larger (India below consolidated) | H |
| 2 | FY2024 ₹28–31k crore guidance was India capex | The call paired it with India OFCF and Q1 India capex ₹9,300 cr | Q1FY2024 p.3 context | India mobile only | If mobile-only (₹25,273 cr), P14 would be delivered | M |
| 3 | The P12 three-year baseline is ~₹23,500 cr/yr | Management gave "Rs 23,000 Crore to 24,000 Crore" in Nov-2022 | Q2FY2023 p.12 | Baseline of FY2022 actual ₹20,773 cr | The miss would be larger | M |
| 4 | Capex classification rule: overspend >5–10% = partially delivered, >10% = missed | Spend guidance has no "≥80% delivered" analogue | Documented in `calc/concalls_promise_db.py` | Symmetric ±10% band | P05, P06 and P14 would become "Delivered"; on-target share would rise to ~61% | M |
| 5 | Mid-year reaffirmations are not separate observations | Avoids double counting | stats=N rows | Count each reaffirmation | Inflates the sample without new information | H |

**Missing evidence.**
- Downloads of the Quarterly Reports for Q4FY2025, Q2FY2026 and Q1FY2027 and of the Q4FY2024/Q1FY2027 press releases failed with SSL errors (logged). The filed results in the corpus provided the trend tables. Q1FY2027 ARPU rests on the call statement (confidence M) [MANAGEMENT STATEMENT: CON-C141].
- Transcripts for Q1FY2017, Q4FY2018 and Q1FY2020 were not linked on the IR results page. Exchange archives were not searched for them. The impact is low, because adjacent calls repeat the commitments.
- Completion evidence for 5G coverage of every town by Mar-2024 (P30), the 16,100-tower transfer to Indus (P44) and the copper shutdown (P53) was not located. These rows are classified as cannot be determined.
- The origin of the FY2024 ₹28–31k crore capex guidance (possibly an investor event or the Q4FY2023 call outside the filtered sentences) was not located.
- Annual-report Chairman/MD letters FY2017–FY2025 were not separately mined for targets. The transcript window from FY2016 already covers the multi-year targets, but a few AR-only aspirations may be missing.
- The 2021 rights-issue letter of offer (call timing terms) was not retrieved.

## Questions and Dependencies for the CIO

1. **Filings:** check the 2021 rights-issue letter of offer. Was a call mandatory after 36 months, as management implied on Q3FY2026 p.6 [MANAGEMENT STATEMENT: CON-C054]? This tests a statement made to justify the timing.
2. **Financials:** reconcile the "~₹50,000 crore India FCF" claim [MANAGEMENT STATEMENT: CON-C097] to the cash-flow statement. Use actual (not guided) capex in incremental-return work. My capex figures are reported capex (gross fixed-asset additions excluding spectrum), not cash capex [FACT: CON-C117].
3. **Valuation / bear-case:** the FY2027–FY2029 capex path should sit above management's "ballpark" guidance given the record [CALCULATION: CON-C201] and the data-centre plan [MANAGEMENT STATEMENT: CON-C091].
4. **Industry:** verify the industry-revenue collapse management cited in FY2019, and the competitor tariff behaviour behind the 2022 non-hike, to confirm the external attribution of the ARPU misses (P20, P25).
5. **Management:** the Chairman's statements on the BTL stake path and buybacks [MANAGEMENT STATEMENT: CON-C094] bear on the payout motive. The leadership succession was delivered as promised [MANAGEMENT STATEMENT: CON-C056].

## Domain Conclusion

**Answers to the decision questions.**
1. **Delivery rate:** 55% on target (31 of 56). 9% partial, 18% delayed, 18% missed or withdrawn [CALCULATION: CON-C200]. Capex level variance: median +7.6%, mean +19.1% [CALCULATION: CON-C201].
2. **Bias by topic:**
   - Optimistic on capex restraint and on technology and new-venture timelines.
   - Accurate on ARPU direction but optimistic on ARPU timing.
   - Accurate to conservative on balance sheet and dividends [JUDGMENT: CON-C300].
3. **Goalposts:**
   - Yes, for the capex trajectory (G1), capex guidance policy (G2), home-pass targets (G9) and FWA/SA dates (G6).
   - Changes were disclosed on calls but rarely acknowledged as revisions of earlier statements.
4. **Statement vs. disclosure:**
   - The main gaps are 5G "capex-neutral" vs. filed capex, "no guidance" vs. cited guidance, and FY2026 "lower capex" vs. filed.
   - No ARPU or KPI figure quoted on calls contradicted filings.
5. **Responses to misses:** External misses (regulation, competitor pricing) are explained specifically and early. Self-chosen misses are reframed. This is a communication pattern only, with no intent inferred.
6. **Recurring analyst concerns:** Tariffs/ARPU (almost every call), capex intensity (at least 22 of the 40 calls), leverage, dividends and the rights call, home-broadband share, 5G monetisation, and now data-centre capex.
7. **Least-trusted current guidance:** The FY2027 capex "ballpark of this year" statement, followed by the dated optionality milestones (1 GW of data centres in 3–4 years, Nxtra 3x) and the ₹300 ARPU timing.

**Formal classifications.**
- **Forecast accuracy:** Inconsistent [JUDGMENT: CON-C300]
- **Execution against commitments:** Mixed (Reliable on deleveraging and capital return) [JUDGMENT: CON-C301]
- **Transparency:** Standard [JUDGMENT: CON-C302]
- **Strategic consistency:** Consistent [JUDGMENT: CON-C303]

## Source Register

| ID | Title | Issuer | Date | URL / identifier | Retrieved | Tier |
|---|---|---|---|---|---|---|
| S1 | Earnings-call transcripts Q3FY2016–Q1FY2023 (24 calls) and Q4FY2026 | Bharti Airtel Limited | 2016-01-29 to 2026-05-14 | https://assets.airtel.in/static-assets/cms/investor/docs/bsy/iportal/images/ (FY2016–FY2020); https://assets.airtel.in/teams/simplycms/web/docs/ (FY2020–FY2023); https://assets.airtel.in/static-assets/cms/investor/docs/quarterly_results/2025-26/Q4/ (full URLs in `calc/concalls_promise_db.py` and `source_retrievals.csv`) | 2026-10-12 | 4 |
| S2 | Earnings-call transcripts Q2FY2023–Q1FY2027 (15 calls) | Bharti Airtel Limited (exchange filings) | 2022-11-07 to 2026-08-10 | FilingForge:9b74c67a…, fa591d96…, e5705279…, 30e022d6…, 15fbc749…, 5f889b5d…, 955dc315…, b6f3d368…, 9a7c6df2…, 40b11be9…, 8e8cf451…, b9941a72…, ba4a97f1…, bccb6f0b…, a46861ad… | 2026-10-12 | 4 |
| S3 | Financial results incl. Quarterly Report trend tables, Q3FY2019–Q4FY2026 | Bharti Airtel Limited (NSE/BSE filings) | 2019-01-31 to 2026-05-13 | FilingForge:16609b54…, 3a9e77b3…, 0f5ab988…, 9c2cf62e…, 979fa9c6…, 7a06ce79…, 18075121…, 4f6dbf86…, 89f465d1…, 80518aeb…, 49e04d6d…, b5c6beda… | 2026-10-12 | 1 |
| S4 | Press release Q2FY2026 | Bharti Airtel Limited | 2025-11 | https://assets.airtel.in/static-assets/cms/investor/docs/quarterly_results/2025-26/Q2/Press-Release.pdf | 2026-10-13 | 3 |
| S5 | Airtel IR results archive page | Bharti Airtel Limited | 2026-10-12 | https://www.airtel.in/about-bharti/equity/results | 2026-10-12 | 3 |
| W1 | Promise database (70 rows) | concalls workpaper | 2026-10-13 | specialists/concalls_workpapers/promise_database.csv; calc/concalls_promise_db.py; calc/concalls_stats.py; calc/concalls_stats.out | — | — |
