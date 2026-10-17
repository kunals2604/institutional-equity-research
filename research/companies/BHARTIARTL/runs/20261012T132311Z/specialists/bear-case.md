---
specialist: bear-case
company: Bharti Airtel Limited
ticker: BHARTIARTL
exchange: NSE
run_id: 20261012T132311Z
research_cutoff: 2026-10-12
report_status: complete
model_requested: opus
independence_attestation: "Initial investigation completed without reading other specialists' reports or prior-run conclusions for this company."
coverage_exception: "Tier-1 annual figures were read for FY2016-FY2020 and FY2026 (the trough cycle and the latest year); FY2015 and FY2021-FY2025 rely on a tier-5 aggregator for the long tail (the financials specialist owns full verification). Share-price history covers Jul-2002 to Oct-2026 (monthly). Before Q2FY2023, transcript-based promise tracking was not possible: the corpus has no older transcripts. The litigation and regulatory search used company notes and web or news sources. Court and SEBI portals were not queried directly, and a tier-6 summary is the only source for some items, which are flagged in the ledger."
---

# Bharti Airtel Limited (BHARTIARTL): Bear-Case and Adversarial Report

## 1. Mandate, Scope and Independence

**Decision questions answered** (from the agent definition):
1. What is the strongest bull case, and which 3–5 assumptions does it rest on?
2. For each assumption: what supports it, what contradicts it, what is the base rate, and what is the value impact if it is wrong?
3. Pre-mortem: it is October 2029 and the shares have lost 50 %. What happened?
4. What would make a loss permanent rather than temporary volatility?
5. How can the risks combine?
6. Is this a value trap, or the reverse (a quality trap at a premium multiple)?
7. Which leading indicators and which thesis-breakers should be monitored?

**In scope:**
- Reconstructing the bull thesis.
- An audit of the hidden assumptions.
- A pre-mortem, failure scenarios with arithmetic (`calc/bear-case_scenarios.py`) and a correlated-risk case.
- Layer-specific failure modes and a value-trap test.
- A search for short-seller reports, litigation, regulatory actions and rating actions.
- Early-warning indicators and thesis-breakers.

**Out of scope:**
- The definitive forensic register (filings).
- Valuation models and the cost of equity (valuation).
- Moat verdicts (moat).
- Scores, layer selection and any verdict.

**Sector playbooks applied:** `SECTOR_PLAYBOOKS.md` §16 (Telecom and media: lease-distorted EBITDA, deferred spectrum and AGR liabilities as quasi-debt, FX translation in overseas units, technology capex cycles) and §18 (holding companies: listed subsidiaries Airtel Africa, Indus Towers and Bharti Hexacom, and minority leakage).

**Lenses owned:**
- T4, inversion: the Hidden-Assumption Audit and the Pre-Mortem.
- T13, base rates: the Indian telecom price-war history and Airtel's own drawdowns.
- T9, consensus: the expectations gap against sell-side EPS.

**Blockers:** none material. Two API-session interruptions occurred during this run. Work resumed from the on-disk ledger and workpapers (`bear-case_workpapers/findings_log.md`), and no figure was reconstructed from memory.

**Price basis:** INR 1,778.70, the NSE close on 12-Oct-2026 [FACT: CIO-C001], on 6,240,504,481 fully paid shares [FACT: CIO-C002]. That gives a market cap of about INR 11.10 lakh crore [CALCULATION: CIO-C003].

## 2. Key Findings

1. **The bear case does not rest on balance-sheet failure.** It rests on whether earnings can grow as fast as the price and consensus assume without another tariff round.
   - Management says FY2026 delivered ARPU growth "despite the absence of tariff repair" [MANAGEMENT STATEMENT: BEAR-C031].
   - In August 2026 it framed long-run ARPU growth at "4% or 5%, maybe slightly higher" a year and conditioned faster growth on an industry-wide change in price architecture [MANAGEMENT STATEMENT: BEAR-C036].
   - The 34-analyst consensus has EPS up 29 % in FY2027 and 31 % in FY2028 (to INR 82.26) [ESTIMATE: BEAR-C040]. Under my model that needs roughly 16 % annual EBITDA growth [CALCULATION: BEAR-C056].
2. **Pricing is stalled, not just slowing.**
   - India mobile ARPU went 245 → 250 → 256 → 259 → 257 over the five quarters to Q4FY2026: it fell quarter on quarter in Q4 and rose 5.0 % year on year [FACT: BEAR-C006]. It reached 264 in Q1FY2027 with an extra day [MANAGEMENT STATEMENT: BEAR-C035].
   - No industry tariff increase has been announced since July 2024 [INFERENCE: BEAR-C044].
   - In February 2023 management called INR 300 ARPU "critical for a respectable return on capital employed" [MANAGEMENT STATEMENT: BEAR-C038]. More than three years later ARPU is about 14 % short of that.
3. **The trailing P/E is high; the enterprise multiple is not.**
   - Pro-forma trailing P/E is about 36.8x [CALCULATION: BEAR-C053].
   - EV/EBITDA on the company's convention is about 10.1x (10.4x adding book NCI) [CALCULATION: BEAR-C054]. That sits inside its own 7.75x–14.14x range since FY2019 [FACT: BEAR-C048].
   - FY2026 free cash flow after capex, spectrum, leases and interest was about 4.9 % of market cap [CALCULATION: BEAR-C055].
   - So pure de-rating with no operating shock gives roughly −12 % over three years (scenario B1) [ESTIMATE: BEAR-C057]. That is an opportunity-cost loss, not a ≥30 % permanent loss.
4. **The route to a ≥30 % permanent loss is a competitive reset in India mobile, with or without an Africa currency shock.**
   - A 10 % ARPU reset on top of B1 gives about −42 % (B2) [ESTIMATE: BEAR-C058]. Adding a 30 % rupee-terms fall in Africa EBITDA gives about −58 % (B3) [ESTIMATE: BEAR-C059]. A straight replay of FY2016–FY2019 gives about −48 % [CALCULATION: BEAR-C060].
   - Precedent: after the 2016 Jio entry, consolidated revenue fell 16 %, EBITDA 23 % and net income 93 % between FY2016 and FY2019 [FACT: BEAR-C016; FACT: BEAR-C019]. ARPU bottomed near INR 100–104 [FACT: BEAR-C039], and FY2020 closed with a net loss of INR 32,183 crore [FACT: BEAR-C020].
5. **The structure is moving towards more competitive capital, not consolidation.**
   - Vodafone Idea got a five-year freeze on INR 87,695 crore of AGR dues [FACT: BEAR-C034] and is seeking bank funding for multi-year capex [ESTIMATE: BEAR-C045].
   - Jio has filed for a roughly INR 37,700 crore fresh-issue IPO [ESTIMATE: BEAR-C043].
   - Airtel was refused equivalent AGR relief [FACT: BEAR-C033] and began paying it: INR 8,612 crore on 31-Mar-2026, with about INR 34,386 crore of AGR deferred payments left [FACT: BEAR-C025].
   - The "three-player market drifts to a duopoly" leg of the bull thesis has weakened.
6. **Capital intensity and diversification are rising just as pricing stalls.**
   - FY2026 capex was INR 47,522 crore, and Q4 was the highest quarter shown [FACT: BEAR-C008].
   - Management signals "a period of rapid capex spend" and a 1 GW data-centre build, and says it "will not hold back on capex" [MANAGEMENT STATEMENT: BEAR-C037].
   - Airtel will fund 70 % of a INR 20,000 crore NBFC [MANAGEMENT STATEMENT: BEAR-C012].
   - Mobile India earns about 9.8 % pre-tax annualised EBIT on cumulative gross investment [CALCULATION: BEAR-C062].
7. **Per-share dilution has been the release valve in past stress.**
   - Shares outstanding rose about 56 % from FY2019 to July 2026 [CALCULATION: BEAR-C052]. Sources: the 2019 rights issue at INR 220, the 2020 QIP at INR 445 [FACT: BEAR-C021], the 2021 rights issue [FACT: BEAR-C022], and a 146.8 million-share swap at INR 1,923 for 16.31 % of Airtel Africa [FACT: BEAR-C013].
8. **The searches found no thesis-breaking forensic, governance or legal item.**
   - Short-seller, SEBI and fraud searches found nothing material against the company [FACT: BEAR-C065].
   - Quantifiable regulatory claims are about INR 21 a share at 50 % crystallisation, and the unindemnified sub-judice AGR provision is about INR 25 a share [CALCULATION: BEAR-C061]. Both are small next to the price.
   - Credit is improving: S&P BBB+ [FACT: BEAR-C042], CRISIL AAA/Stable [FACT: BEAR-C063]. Contrast the 2019 Moody's downgrade to Ba1 [FACT: BEAR-C041].

## 3. Data Coverage

| Data series | Periods covered | Count | Sources and tier | Verification | Gaps and exceptions |
|---|---|---|---|---|---|
| Consolidated revenue, EBITDA, PAT (trough cycle) | FY2016, FY2017, FY2018, FY2019, FY2020 | 5 years | Annual reports FY2017–FY2020 (tier 1, corpus) | Full for these years | FY2008–FY2015 tier-1 statements not read; price history covers that period |
| Consolidated P&L, BS, CF (long tail) | FY2015–FY2026 | 12 years | Screener (tier 5), `bear-case_workpapers/screener/` | Aggregator-only except FY2016–FY2020 and FY2026 | Screener "net profit" includes NCI; EBITDA classification differs from the company KPI pack |
| Latest year and quarter | FY2026, Q4FY2026, Q1FY2027 | 1 year + 5 quarters | Q4FY2026 results and Quarterly Report; Q1FY2027 results; FY2026 consolidated financial statements and MD&A (tier 1, downloaded) | Full | Q1FY2027 KPI pack not retrieved; Q1FY2027 EBITDA approximated from the statutory line |
| India mobile ARPU / churn | Q3FY2018, Q2FY2019, Q3FY2019, Q4FY2025–Q1FY2027 | 9 quarter points | Quarterly Reports, transcripts (tier 3/4) | Sampled | Continuous ARPU series FY2016–FY2025 not compiled (industry/concalls own it) |
| Company-reported EV/EBITDA | Q3FY2019–Q4FY2026 | 20 quarters | Quarterly Reports (tier 3) | Sampled from the corpus search | Definitions change at Ind AS 116 (FY2020) and Indus consolidation (Q3FY2025) |
| Share price, drawdowns | Jul-2002 – Oct-2026 | 24 years monthly | Yahoo chart API (tier 5); reconciles to the company-reported BSE close at Mar-2026 | Spot-checked | Monthly closes understate intramonth extremes |
| Management commitments (ARPU, capex, pricing) | Q3FY2023–Q1FY2027 | 6 transcripts read in part | Corpus transcripts (tier 4) | Quotations checked against the text | Transcripts before Q2FY2023 missing from the corpus |
| AGR, DPL, contingencies | FY2025–FY2026 | 2 years | FY2026 consolidated financial statements notes 18, 23 and provisions (tier 1) | Full | Earlier contingency trend owned by filings |
| Ratings | 2014–2026 | 12 years (events) | S&P/Moody's via news (tier 6); CRISIL rationale (tier 5) | Partial | Moody's and Fitch actions after 2019 not located |
| Short-seller, SEBI, CCI, litigation, data breach | 2016–2026 | 10 years | Web search, news (tier 6), company notes (tier 1) | Partial | SEBI, CCI and court portals not queried directly |
| Consensus | Aug-2026 snapshot | 1 | StockAnalysis / S&P Global (tier 5) | Rendering only | No broker reports read |

## 4. Bull Thesis Reconstruction

**The steelman, in one paragraph.** India now has a three-private-player mobile market (plus state-owned BSNL), and Airtel holds the premium position in it. It has gained revenue share to an all-time high of 39.7 % [MANAGEMENT STATEMENT: BEAR-C031], has an industry-leading ARPU [FACT: BEAR-C006], and runs a fast-growing postpaid, homes and enterprise mix.

The heavy 4G/5G and spectrum spending is largely done. EBITDA therefore converts into falling leverage: net debt including leases to EBITDA fell from 1.86x to 1.29x in FY2026 [FACT: BEAR-C005; FACT: BEAR-C009], ratings were upgraded [FACT: BEAR-C042; FACT: BEAR-C063], and cash flow after capex, leases and interest reached about INR 54,000 crore [CALCULATION: BEAR-C055].

Each tariff round falls almost entirely through to EBITDA, because the network is already built. Africa is a second compounding engine: constant-currency revenue grew 22.3 % in Q4FY2026 and Airtel Money is heading for a listing. Indus Towers, data centres and payments/NBFC add optionality. The 2026 swap that raised the Africa stake to about 79 % [FACT: BEAR-C013] concentrates that compounding in Airtel's hands.

**Consensus (T9).** The sell side buys it: 34 analysts, "Strong Buy", average target INR 2,318, FY2027 EPS INR 62.75 and FY2028 EPS INR 82.26 [ESTIMATE: BEAR-C040]. At INR 1,778.70 that is about 28x FY2027E and 22x FY2028E. On the bull view, a stock that has been flat for 18 months while pre-exceptional net income rose 51 % [CALCULATION: BEAR-C024] has already de-rated and offers about 30 % upside to the consensus target.

**The load-bearing assumptions.**

| # | Assumption | Why the bull case needs it |
|---|---|---|
| A1 | **Tariff repair resumes**: at least one industry round of about 10–15 % in FY2027–FY2028, then periodic rounds | Consensus EPS needs about 16 % EBITDA CAGR [CALCULATION: BEAR-C056]; organic ARPU growth of 4–5 % [MANAGEMENT STATEMENT: BEAR-C036] does not get there |
| A2 | **Market structure stays rational**: no share-grab by Jio after its IPO, Vi survives without disrupting prices, satcom is complementary | Every past ARPU collapse came from a structural break (2008–2012 entrants, 2016 Jio) [FACT: BEAR-C039; CALCULATION: BEAR-C023] |
| A3 | **Capital intensity falls and incremental capital earns more than its cost**, even as data centres (to 1 GW), NBFC lending and fibre are added | FCF growth and deleveraging depend on capex moderating, which CRISIL assumes [FACT: BEAR-C063] but management contradicts [MANAGEMENT STATEMENT: BEAR-C037] |
| A4 | **Africa compounds in hard-currency terms**: FX translation does not wipe out constant-currency growth | Africa is about 29 % of segment results in Q1FY2027 [FACT: BEAR-C004] and about 79 % owned after the swap [FACT: BEAR-C013] |
| A5 | **The multiple holds**: investors keep paying about 37x trailing P/E [CALCULATION: BEAR-C053] for a telecom operator | The return at today's price leans on rerating staying intact; without it the IRR is close to zero (scenario B1) [ESTIMATE: BEAR-C057] |

## 5. Hidden-Assumption Audit

Probability bands follow the constitution: remote <5 %, low 5–20 %, moderate 20–40 %, elevated 40–60 %, high >60 %. They are judgments about the next 3–5 years, anchored on the reference classes named in each row.

| # | Assumption | Supporting evidence | Disconfirming evidence | Base rate / reference class (T13) | Probability it fails | Value impact if wrong |
|---|---|---|---|---|---|---|
| A1 | Tariff repair resumes | ARPU rose 17 % in FY2025 on the July-2024 hike (CRISIL) [FACT: BEAR-C063]; brokers expect 12–15 % within months [INFERENCE: BEAR-C044]; Jio's IPO gives it a reason to show ARPU growth [ESTIMATE: BEAR-C043] | No hike since July 2024 [INFERENCE: BEAR-C044]; "absence of tariff repair" [MANAGEMENT STATEMENT: BEAR-C031]; management steers to organic ARPU growth of 4–5 % a year and says architecture repair is long-term [MANAGEMENT STATEMENT: BEAR-C036]; ARPU fell QoQ in Q4FY2026 [FACT: BEAR-C006]; the INR 300 target from 2023 is still unmet [MANAGEMENT STATEMENT: BEAR-C038] | Indian private telcos raised headline tariffs in Dec-2019, Nov-2021 and Jul-2024: roughly one round every 2–3 years since repair began (the Dec-2019 and Nov-2021 dates are recalled and were not verified in this run; only the 2024 round is ledgered, via BEAR-C063) | **Moderate** (20–40 %) that no meaningful round happens by end-FY2028 | EPS about 20 % below consensus FY2028 at 10 % EBITDA growth [CALCULATION: BEAR-C056]; with a de-rating to 22x, −12 % over three years (B1) [ESTIMATE: BEAR-C057]. Mostly an **opportunity-cost** loss: it delays but does not destroy value |
| A2 | Market structure stays rational | Vi is capital-starved (seeking bank debt) [ESTIMATE: BEAR-C045]; Jio needs profitable growth for its IPO valuation [ESTIMATE: BEAR-C043]; Airtel's churn is steady at 2.3–2.6 % [FACT: BEAR-C007] | Government rescued Vi rather than allowing exit [FACT: BEAR-C034]; Jio raises fresh primary capital [ESTIMATE: BEAR-C043]; TRAI recommends lower spectrum caps (40 % → 35 %) and lower reserve prices that ease entry and expansion [FACT: BEAR-C015]; satcom licences granted [ESTIMATE: BEAR-C046] | Two structural price resets in about 18 years (the post-2008 multi-entrant war; the 2016 Jio entry). Each cut Airtel's share price 44–50 % [CALCULATION: BEAR-C023], and the 2016 reset cut EBITDA 23 % [CALCULATION: BEAR-C060]. Roughly a once-a-decade event, usually set off by a well-capitalised entrant or a share-grab | **Low** (5–20 %) for a reset of ≥10 % in ARPU within five years | −42 % (B2) [ESTIMATE: BEAR-C058]; −48 % in a full 2016–2019 replay [CALCULATION: BEAR-C060]. **Permanent** for holders at today's price: history shows 3–5 years to recover and equity issuance at trough prices [FACT: BEAR-C021] |
| A3 | Capital intensity falls; incremental returns exceed cost | Net leverage fell to 1.29x [FACT: BEAR-C009]; FCF of INR 54,000 crore [CALCULATION: BEAR-C055]; CRISIL expects capex to moderate [FACT: BEAR-C063] | "Rapid capex spend", 1 GW of data centres, "will not hold back" [MANAGEMENT STATEMENT: BEAR-C037]; Q4FY2026 capex was the highest quarter shown [FACT: BEAR-C008]; NBFC of INR 20,000 crore [MANAGEMENT STATEMENT: BEAR-C012]; mobile India EBIT is about 9.8 % of gross cumulative investment [CALCULATION: BEAR-C062]; Indus revenue per tower falling [FACT: BEAR-C014] | Telecom operators diversifying into adjacencies (data centres, fintech, media) have a mixed record. No cited reference class: qualitative only | **Moderate** (20–40 %) that consolidated capex/revenue stays at or above about 22 % through FY2029 | D&A grows faster than EBITDA, and FCF stalls near INR 50,000 crore; the effect is folded into B1. The NBFC alone is about INR 22 a share of capital at risk [CALCULATION: BEAR-C061 inputs; see calc section 5] |
| A4 | Africa compounds in INR | Constant-currency growth strong; Africa net income rose from a loss to INR 6,001 crore [FACT: BEAR-C047]; credit agencies cite Africa growth [FACT: BEAR-C063] | Africa lost money in FY2024 on devaluation [FACT: BEAR-C047]; a central bank cancelled historical FX allocations (INR 483 crore contested) [FACT: BEAR-C030]; Airtel just raised its exposure to about 79 % [FACT: BEAR-C013] | Frontier-market FX: the naira lost most of its USD value over 2023–2024 (not verified in this run beyond the FY2024 Africa loss in BEAR-C047) | **Moderate** that Africa's INR EBITDA falls ≥20 % at some point in five years | About −5 to −8 percentage points of value per share on its own (B3 minus B2) [ESTIMATE: BEAR-C059]. Mostly **temporary** unless it coincides with A2 |
| A5 | The multiple holds | EV/EBITDA of about 10x sits mid-range [CALCULATION: BEAR-C054; FACT: BEAR-C048]; FCF yield is about 4.9 % [CALCULATION: BEAR-C055] | P/E of about 37x trailing [CALCULATION: BEAR-C053]; price already 18 % below its Nov-2025 high [CALCULATION: BEAR-C068]; promoter-affiliate Singtel has been a repeated seller [FACT: BEAR-C067] | Airtel's own adjusted share price was flat from 2008 to 2018 [CALCULATION: BEAR-C023], so a decade of zero return has happened before | **Moderate** that the trailing P/E falls below about 25x within three years | Folded into B1/B2. On its own this is a de-rating loss, which is permanent for today's buyer only if earnings growth also disappoints |

**The single most damaging assumption (T4).** The most damaging assumption is **A2, market structure**, not A1. A1 failing merely stretches the timeline: management's own 4–5 % ARPU path still compounds earnings at roughly 10–13 % a year. A2 failing changes the earnings level and has historically forced dilution [FACT: BEAR-C021; CALCULATION: BEAR-C052]. The most *probable* disappointment is A1. The two are linked: the longer the industry goes without a tariff round, the stronger the incentive for a challenger (Vi with fresh debt, or Jio after its IPO) to buy share instead.

## 6. Pre-Mortem

*It is October 2029. BHARTIARTL trades about 50 % below INR 1,778.70. The three most plausible stories, each traceable to evidence available today:*

**Narrative 1: "The tariff round that never came, then the share war" (most plausible path to −50 %).**
- FY2027–FY2028 pass without an industry tariff round. Management had already prepared investors for "organic" ARPU growth of 4–5 % a year [MANAGEMENT STATEMENT: BEAR-C036], and ARPU had stalled at INR 257–264 [FACT: BEAR-C006; MANAGEMENT STATEMENT: BEAR-C035].
- Jio, newly listed with fresh primary capital [ESTIMATE: BEAR-C043], needs subscriber growth to justify a US$130–180 billion valuation. Vi, with frozen AGR dues and new bank lines [FACT: BEAR-C034; ESTIMATE: BEAR-C045], finally fixes coverage and prices aggressively to win back share. Bundled 5G home broadband and generous data packs become the weapons.
- Airtel's postpaid and premiumisation lever runs out. ARPU slips about 10 % from its peak, as it fell 15.5 % year on year in Q3FY2019 [FACT: BEAR-C039], while capex continues at a "rapid" pace [MANAGEMENT STATEMENT: BEAR-C037].
- FY2029 EPS lands in the INR 50s, not the INR 80–90s the market expected [ESTIMATE: BEAR-C058]. The multiple compresses to a high-teens P/E as Airtel is re-rated from "compounder" to "utility in a price war".
- Result: about −40 to −50 %, with no balance-sheet stress and no accounting issue. It is a pure expectations-and-structure failure.

**Narrative 2: "Capital-allocation drift plus a frontier-currency shock."**
- India grows at management's 4–5 % ARPU pace, but capital flows into 1 GW of data centres, a INR 20,000 crore NBFC [MANAGEMENT STATEMENT: BEAR-C012] and fibre at returns below the cost of capital. Mobile India already earns only about 9.8 % pre-tax on gross cumulative investment [CALCULATION: BEAR-C062].
- A Nigerian or East African devaluation of the 2023–2024 kind recurs. Africa had swung to a reported loss in FY2024 [FACT: BEAR-C047], and Airtel now owns about 79 % of it, having issued 146.8 million of its own shares to buy more [FACT: BEAR-C013].
- An NBFC credit cycle produces the first provisions in a new business. The market applies a conglomerate discount.
- Result: about −30 % (B1 de-rating plus Africa), with the loss concentrated per share because of the 2026 swap.

**Narrative 3: "Regulatory relitigation" (least likely of the three to produce −50 %).**
- DoT spectrum renewals (TRAI refers to spectrum expiring in 2026–27) [INFERENCE: BEAR-C015] and the next auction under lower caps force Airtel to pay up to defend holdings.
- The OTSC appeal and licence-fee disputes go against the company: about INR 6,607 crore of OTSC balance is contingent [FACT: BEAR-C029], and contingent liabilities total INR 19,184 crore and are rising [FACT: BEAR-C028].
- The Supreme Court declines any AGR relief [FACT: BEAR-C033].
- Quantified, these claims are small, about INR 21–25 a share [CALCULATION: BEAR-C061]. They matter only as a trigger that coincides with Narrative 1.

**What the pre-mortem does *not* support.** A collapse caused by solvency, fraud or governance. Leverage is falling [FACT: BEAR-C009], ratings are rising [FACT: BEAR-C042; FACT: BEAR-C063], the auditor's opinion on FY2026 is unmodified [FACT: BEAR-C070], and no short-seller or regulatory finding was located (section 11).

## 7. Failure Scenarios and Impairment Mechanisms

All arithmetic is in `calc/bear-case_scenarios.py` → `calc/bear-case_scenarios.out`.

Method:
- The value at a three-year horizon (about FY2029) is FY2029 EPS × exit P/E, plus cumulative dividends, on a constant 6,240.5 million shares.
- EPS is modelled from FY2026 KPI EBITDA, D&A, finance cost and tax with an NCI share of 18 % after the swap. The model reconstructs FY2026 EPS at INR 47.5 against about INR 43–46 reported, so it slightly *overstates* earnings, which makes the bear scenarios conservative [CALCULATION: BEAR-C056].
- Exit multiples are bear-case judgments benchmarked to the company's own EV/EBITDA range [FACT: BEAR-C048].

| Scenario | Trigger | Mechanism | Earnings / cash / balance-sheet effect | Value per share (incl. divs) | vs INR 1,778.70 | Permanent or temporary |
|---|---|---|---|---|---|---|
| Reference (bull-like) | Tariff round(s) arrive | 13 % EBITDA CAGR; finance cost falls 3 % a year | FY2029 EBITDA about INR 174,977 crore; EPS about 88.8 | about INR 2,569 at 28x | +44 % | n/a (shown for calibration only) |
| **B1 No repair + capex super-cycle** | No industry hike through FY2028; data-centre and fibre capex | EBITDA +9 % a year (ARPU 4–5 % plus subscriber growth); D&A +11 % a year; P/E de-rates to 22x | FY2029 EBITDA about INR 157,045 crore; EPS about 67.4; FCF flat | about INR 1,560 [ESTIMATE: BEAR-C057] | −12 % (IRR about −4 % a year) | **Mostly temporary / opportunity cost**: the business keeps compounding and the loss comes from paying for growth that arrives late |
| **B2 Competitive reset** | Jio post-IPO share push or Vi re-entry; failed hike | B1 plus a 10 % India mobile ARPU reset by FY2029 with 100 % flow-through (network costs fixed) | EBITDA about INR 143,203 crore; EPS about 53.7 | about INR 1,039 at 18x [ESTIMATE: BEAR-C058] | −42 % | **Permanent for today's buyer**: the 2016–2019 precedent took more than five years to recover and needed rights issues at INR 220 [FACT: BEAR-C021] |
| **B4 2016–2019 replay** (stress) | Well-capitalised disruptor prices for share | Consolidated EBITDA −20 % vs FY2026; EV/EBITDA 8.0x (Q3FY2019 was 8.91x, Q2FY2021 7.75x) [FACT: BEAR-C048]; net debt incl. leases rises to INR 2.0 lakh crore | Matches the history of −16 % revenue, −23 % EBITDA, −93 % net income FY2016–FY2019 [CALCULATION: BEAR-C060] | about INR 923 [CALCULATION: BEAR-C060] | −48 % | **Permanent**: the equity is likely to be diluted to protect the balance sheet (share count +56 % since FY2019 [CALCULATION: BEAR-C052]) |
| Regulatory crystallisation | Adverse SC or TDSAT outcomes on OTSC, licence fee, SUC; no AGR relief | 50 % of contingent liabilities plus OTSC balance paid | About INR 12,900 crore one-off cash | −INR 21 a share [CALCULATION: BEAR-C061] | −1 % | Permanent but immaterial |
| Capital-allocation drift | NBFC, data centres earn below the cost of capital | INR 14,000 crore Airtel NBFC equity [MANAGEMENT STATEMENT: BEAR-C012] plus data-centre equity at a low ROIC | About INR 22 a share for the NBFC alone (calc section 5) | Folded into B1 | — | Permanent if returns stay sub-par |

**Sensitivity of the main driver.** Each 10 % change in India mobile ARPU is worth about INR 13,800 crore of FY2029 EBITDA, about INR 13.6 of EPS, and INR 245–300 a share at 18–22x P/E. That is roughly 14–17 % of today's price [CALCULATION: BEAR-C069].

## 8. Correlated-Risk Scenario

**B3, "share war + FX + no deleveraging"** [ESTIMATE: BEAR-C059]: value about INR 751 a share including dividends, **−58 %**.

The chain, and why the risks reinforce each other:
1. **Trigger:** a challenger (Jio post-IPO [ESTIMATE: BEAR-C043], or a refinanced Vi [ESTIMATE: BEAR-C045]) prices for share while no tariff round is under way [INFERENCE: BEAR-C044]. India mobile ARPU resets about 10 % (B2 mechanics).
2. **Reinforcing loop 1, capex:** management has said it "will not hold back on capex" in order "to be competitive" [MANAGEMENT STATEMENT: BEAR-C037]. In a share war capex rises just as EBITDA falls, so FCF compresses on both lines. FY2026 FCF of about INR 54,000 crore [CALCULATION: BEAR-C055] could plausibly halve.
3. **Reinforcing loop 2, fixed DoT schedules:** AGR deferred payments of about INR 5,861 crore fall due within one year and INR 6,330 crore in the year after [FACT: BEAR-C025], plus spectrum instalments [FACT: BEAR-C026] and spectrum renewals. These cannot flex with revenue. DoT has refused Airtel the relief it gave Vi [FACT: BEAR-C033].
4. **Reinforcing loop 3, Africa FX at the same time:** EM-wide risk-off episodes tend to hit frontier currencies as well. A 30 % INR fall in Africa EBITDA [FACT: BEAR-C047 precedent] removes the second engine just when it is needed, and Airtel now carries about 79 % of that exposure [FACT: BEAR-C013].
5. **Balance sheet and per-share outcome:** net debt including leases stops falling (modelled as finance cost flat), and the multiple compresses to 16x. The 2019–2021 response was rights issues and a QIP at depressed prices [FACT: BEAR-C021; FACT: BEAR-C022]. A repeat would make the loss permanent per share even if the franchise recovers.

Probability of the full correlated case within five years: **low** (5–20 %). Each leg is individually low or moderate, and the legs are positively correlated through EM risk appetite and the competitive capex response [JUDGMENT].

## 9. Layer-Specific Failure Modes

How an investor using each layer's lens would lose money here:

- **Layer 1 — Bedrock Compounder lens (moat erosion, fading reinvestment returns, multiple de-rating).**
  - The L1 investor pays about 37x trailing earnings [CALCULATION: BEAR-C053] for a "rational oligopoly compounder".
  - Failure mode 1, reinvestment: the reinvestment runway shifts from high-return mobile pricing to capital-heavy adjacencies (data centres to 1 GW, NBFC lending) at unproven returns [MANAGEMENT STATEMENT: BEAR-C037; MANAGEMENT STATEMENT: BEAR-C012]. Mobile India's EBIT on gross cumulative investment is only about 9.8 % [CALCULATION: BEAR-C062].
  - Failure mode 2, per-share compounding: past stress was absorbed with equity, and shares are up 56 % since FY2019 [CALCULATION: BEAR-C052].
  - Even without a moat failure, a de-rating from 37x to 22x erases about three years of 13 % EPS growth (B1, −12 %) [ESTIMATE: BEAR-C057].
  - The L1 investor's error would be using today's peak-ish returns (ROCE 20.4 % in Q4FY2026, company definition [FACT: BEAR-C009]) as if they held through the cycle. Through-cycle, Airtel earned near-zero net income in FY2019 and a large loss in FY2020 [FACT: BEAR-C019; FACT: BEAR-C020].
- **Layer 2 — High-Growth Business lens (growth stall, saturation, unit economics, dilution).**
  - India mobile subscribers grow about 3 % a year [FACT: BEAR-C007], and ARPU growth without tariff rounds is guided at 4–5 % [MANAGEMENT STATEMENT: BEAR-C036], so core growth is about nominal GDP.
  - The high-growth pockets carry their own risks:
    - Homes: net adds moderated to 473k in Q1FY2027 [MANAGEMENT STATEMENT: BEAR-C035], and ARPU fell 3 % year on year in Q4FY2026 (Quarterly Report s.4.3).
    - Africa: FX-exposed [FACT: BEAR-C047].
    - Data centres and NBFC: early stage.
  - The L2 failure is paying for 15–30 % consolidated EPS growth (consensus [ESTIMATE: BEAR-C040]) that is really one-off tariff and deleveraging effects plus an Africa FX tailwind.
- **Layer 3 — Cyclical / Event-Driven Opportunity lens (catalyst failure, value trap, structural decline, trough solvency).**
  - The obvious catalyst is the "next tariff hike" [INFERENCE: BEAR-C044]. Its realisation mechanism is outside Airtel's control: it needs Jio, and in effect the government's tolerance. It has not happened in 27 months [INFERENCE: BEAR-C044].
  - If the hike comes but the market already prices it (consensus EPS embeds about 16 % EBITDA CAGR [CALCULATION: BEAR-C056]), the event investor earns little.
  - Trough solvency is *not* the risk now: net debt to EBITDA is 1.29x, against the CRISIL trigger of 2.5–2.7x [FACT: BEAR-C009; FACT: BEAR-C063]. That is unlike 2019, when Moody's cut Airtel to junk [FACT: BEAR-C041].
- **Layer 4 — Venture-Style / Optionality Bet lens (milestone failure, funding gaps, dilution cascades).**
  - The options are data centres (Nxtra, US$1 billion external round), the NBFC, the Airtel Money listing, and satcom partnerships.
  - Failure modes:
    - Option value is diluted at the subsidiary level (external investors in Nxtra) or consumed by capital calls (NBFC INR 20,000 crore over several years [MANAGEMENT STATEMENT: BEAR-C012]).
    - The Airtel Money IPO slips: already moved from H1 to H2 2026 per Airtel Africa disclosures (search lead, not ledgered).
    - Related-party co-investment with the promoter's Bharti Enterprises in the NBFC [MANAGEMENT STATEMENT: BEAR-C012] creates allocation conflicts (governance owned by the management specialist).
  - These options are small relative to an INR 11.1 lakh crore market cap, so paying for them in the multiple is the risk.

## 10. Value-Trap Test

**This is not a classic value trap. It is closer to a "quality-premium trap" test.**

**Is it cheap?** No, on earnings: about 36.8x pro-forma trailing EPS [CALCULATION: BEAR-C053]. Partly, on cash and enterprise value: EV/EBITDA is about 10.1x, within its own history [CALCULATION: BEAR-C054], and the equity FCF yield is about 4.9 % [CALCULATION: BEAR-C055].

**Why might it be cheap on EV and FCF?**
- Large D&A on capitalised spectrum and on the Indus purchase-price allocation (D&A INR 527,108 million, and 21 % of FY2026 profit belonging to minorities) [FACT: BEAR-C071].
- Big minority interests in Indus, Africa and Hexacom. Company EV excludes them [FACT: BEAR-C009], which flatters EV/EBITDA.
- DoT liabilities in debt: about 45 % of gross debt [FACT: BEAR-C063].
- These are permanent features, so the EV/EBITDA "discount" to global high-growth peers is structural, not a mispricing.

**What would make a rating discount persist?**
- The tariff architecture is not repaired [MANAGEMENT STATEMENT: BEAR-C036].
- A three-plus-one structure with government-backed Vi [FACT: BEAR-C034].
- Continuing heavy capex [MANAGEMENT STATEMENT: BEAR-C037].

**What closes it?** A tariff round, or a visible fall in capex intensity. Both are plausible, but neither is in management's own guidance.

**Conclusion.** The bear risk here is overpaying for a high-quality franchise whose earnings growth is being extrapolated from one-off effects (the July-2024 tariff round, deleveraging, Africa FX normalisation), not owning a cheap business that stays cheap. The asymmetry worsens at prices above about INR 2,000. At INR 1,778.70 the stock already sits 18 % below its Nov-2025 high [CALCULATION: BEAR-C068] [JUDGMENT].

## 11. Short-Seller, Litigation and Regulatory Search

**Search log (10-year window, 2016–Oct-2026).**

| Source / query | What was searched | Result |
|---|---|---|
| Web search: "Bharti Airtel short seller report OR forensic accounting allegations OR SEBI order" | Hindenburg, Muddy Waters, Viceroy, GMT, Grizzly and generic forensic reports | **None found** on Airtel; results concerned Adani, Ebixcash and others [FACT: BEAR-C065] |
| Web search: "Bharti Airtel SEBI penalty OR adjudication OR settlement order" | SEBI enforcement | Only a c.2017 settlement of about INR 2.17 lakh by promoter entity ICIL for a disclosure lapse; **no SEBI order against the company** located [FACT: BEAR-C065] |
| Web search: CCI cartel / POI case | CCI, Supreme Court | CCI probe into alleged incumbent cartelisation against Jio quashed (SC dismissed CCI appeal 5-Dec-2018); TRAI-recommended POI penalty of INR 3,050 crore across three incumbents referred to DoT, current status unverified [FACT: BEAR-C066]; CCI INR 1 crore s.43A penalty (2023) [FACT: BEAR-C065] |
| FY2026 consolidated statements note 23 and provisions | Tax, DoT, OTSC, licence fee, SUC, arbitration | Contingent liabilities INR 19,184 crore (up from 16,918) [FACT: BEAR-C028]; OTSC balance INR 6,607 crore contingent, with INR 1,808 crore principal plus INR 12,138 crore interest already provided [FACT: BEAR-C029]; DoT appeals on ISP licence fee and SUC pending in the SC; Africa FX-allocation dispute INR 483 crore, unprovided [FACT: BEAR-C030] |
| AGR: SC orders, DoT | AGR relief, payment schedule | SC dismissed waiver petitions 19-May-2025; DoT refused parity relief 30-Mar-2026 [FACT: BEAR-C033]; first instalment paid; AGR DPL about INR 34,386 crore remaining [FACT: BEAR-C025]; sub-judice AGR provision INR 34,704 crore, about INR 15,543 crore unindemnified [FACT: BEAR-C027; CALCULATION: BEAR-C061] |
| Rating actions | S&P, Moody's, Fitch, CRISIL, ICRA | Moody's to Ba1 (junk), negative, Feb-2019 [FACT: BEAR-C041]; S&P BBB- (2014) → BBB (Nov-2025) → BBB+ (Jun-2026) [FACT: BEAR-C042]; CRISIL AA+/Positive → AAA/Stable (Jul-2025), reaffirmed Jul-2026 [FACT: BEAR-C063]. **No downgrade or negative outlook since 2019 found.** Fitch and Moody's actions after 2019 not located |
| Data security | Breach allegations | July-2024 dark-web claim covering 375 million records, denied by Airtel and doubted by researchers; no regulator finding located [FACT: BEAR-C064] |
| Auditor opinion FY2026 | Auditor's report | Unmodified opinion; KAMs on revenue/IT systems and regulatory matters [FACT: BEAR-C070] |
| Promoter / affiliate selling | Block deals | Singtel (Pastel) sold about 1.2 % in May-2025 at INR 1,814 and about 0.8 % in Nov-2025 at a floor of INR 2,030 [FACT: BEAR-C067]; no 2026 sale found |

Not searched directly: the SEBI, CCI and NCLT portals, eCourts, and Nigerian, Kenyan and Tanzanian court and tax records (Airtel Africa). These gaps are listed in section 16.

**Assessment.** Allegations are treated as allegations. Nothing located amounts to evidence of misconduct, and the quantifiable legal and regulatory exposure is about 1–2 % of market value [CALCULATION: BEAR-C061]. The real regulatory risk is policy, not litigation: tariff forbearance, the Vi rescue [FACT: BEAR-C034], spectrum caps and reserve prices [FACT: BEAR-C015], and satcom entry [ESTIMATE: BEAR-C046] [JUDGMENT].

## 12. Early-Warning Indicators and Thesis-Breakers

The warning and break levels below are bear-case judgments. They are calibrated, where possible, to history (FY2016–FY2019), to CRISIL's rating triggers [FACT: BEAR-C063], and to management's own guidance.

| Metric / event | Current (cited) | Healthy | Warning | Thesis break | Why it matters |
|---|---|---|---|---|---|
| India mobile ARPU, YoY growth | INR 257 in Q4FY2026, +5.0 % YoY, −0.6 % QoQ [FACT: BEAR-C006]; INR 264 in Q1FY2027 (extra day) [MANAGEMENT STATEMENT: BEAR-C035] | ≥ 8 % YoY | < 4 % YoY for two quarters | Any YoY decline, or two consecutive QoQ declines | The lead indicator of pricing power (A1/A2). In 2018 ARPU fell 15.5 % YoY [FACT: BEAR-C039] before EBITDA collapsed |
| Industry tariff action | No round since Jul-2024 [INFERENCE: BEAR-C044] | A round by FY2027 | No round by 31-Mar-2027 | A major operator cuts mass-plan prices ≥ 10 %, or adds data at a lower price, after Jio lists | Consensus needs it [CALCULATION: BEAR-C056] |
| India mobile monthly churn | 2.4 % [FACT: BEAR-C007] | ≤ 2.5 % | ≥ 2.8 % for two quarters | ≥ 3.2 % with falling ARPU | Share loss shows in churn before revenue |
| Revenue market share | 39.7 % (management) [MANAGEMENT STATEMENT: BEAR-C031] | Stable or rising | −1 pp YoY | −2 pp YoY | A CRISIL downgrade trigger [FACT: BEAR-C063] |
| Capex / revenue (consolidated) | 22.5 % FY2026; 29.0 % Q4FY2026 [CALCULATION: BEAR-C072] | ≤ 20 % | > 25 % for a fiscal year | > 28 % with ARPU growth < 4 % | Capex rising while pricing stalls is the B1→B3 path |
| FCF after capex, spectrum, leases, interest | about INR 54,222 crore FY2026 [CALCULATION: BEAR-C055] | Rising | < INR 40,000 crore | < INR 27,000 crore (halved) | Deleveraging, dividends and avoiding equity issuance all depend on it |
| Net debt incl. leases / EBITDA | 1.29x [FACT: BEAR-C009] | ≤ 1.5x | > 1.8x | ≥ 2.5x (CRISIL downgrade band) [FACT: BEAR-C063] | Trough solvency and dilution risk |
| Share count / equity issuance | 6,240.5 million fully paid [FACT: CIO-C002]; +56 % since FY2019 [CALCULATION: BEAR-C052] | No net issuance | Any further share swap or preferential issue | Rights issue or QIP to fund the balance sheet | Per-share compounding is the L1 test |
| Africa reported net income | INR 6,001 crore FY2026 [FACT: BEAR-C047] | Growing in INR | A ≥ 20 % devaluation in a major market (Nigeria) in a quarter | A full-year reported loss (FY2024 precedent) [FACT: BEAR-C047] | About 79 % owned now [FACT: BEAR-C013] |
| Competitor capital | Vi seeking about INR 25,000 crore of debt [ESTIMATE: BEAR-C045]; Jio fresh issue of about INR 37,700 crore [ESTIMATE: BEAR-C043] | Capital used for coverage, with pricing discipline | Vi funding closes and Vi posts net subscriber adds for two quarters | Jio or Vi undercuts Airtel's mass-plan prices | Structural-break precursor (A2) |
| Indus Towers sharing factor | 1.62 [FACT: BEAR-C014] | ≥ 1.62 | < 1.58 | Vi tenancy exits | A Vi network pull-back hits Indus first |
| Consensus FY2028 EPS | INR 82.26 [ESTIMATE: BEAR-C040] | Stable | Cut > 10 % | Cut > 20 % | The expectations gap (T9) closing the wrong way |
| NBFC and data-centre capital calls | INR 20,000 crore NBFC plan, 70 % Airtel [MANAGEMENT STATEMENT: BEAR-C012] | Within plan, with disclosed ROE | Airtel share above INR 14,000 crore, or NBFC credit costs disclosed > 3 % | Group-level guarantees or capital calls beyond plan | Capital-allocation drift (L1 / L4 failure modes) |

> **If these variables deteriorate beyond the thesis-break levels, reassess the investment thesis.**

## 13. Strongest Evidence for the Bull Case

On the evidence, the bear case is **moderate, not severe**. The strongest counter-evidence:

1. **The balance sheet is no longer the transmission mechanism for a loss.**
   - Net debt including leases to EBITDA was 1.29x at Mar-2026, down from 1.86x a year earlier [FACT: BEAR-C009].
   - India and passive-infrastructure external debt is negative, excluding DoT and lease liabilities [MANAGEMENT STATEMENT: BEAR-C073].
   - CRISIL AAA/Stable and S&P BBB+ [FACT: BEAR-C063; FACT: BEAR-C042], against the Moody's junk rating of 2019 [FACT: BEAR-C041].
   - A FY2019-style forced rights issue is far less likely today.
2. **Cash generation is real and audited.**
   - FY2026 CFO was INR 1,22,230 crore [FACT: BEAR-C051], and FCF after capex, spectrum, leases and interest about INR 54,222 crore [CALCULATION: BEAR-C055].
   - The opinion is unmodified [FACT: BEAR-C070], and no short-seller or SEBI finding was located [FACT: BEAR-C065].
3. **Valuation is less stretched than the P/E suggests.** EV/EBITDA is about 10.1x, mid-range in its own seven-year history [CALCULATION: BEAR-C054; FACT: BEAR-C048]. A pure de-rating gives about −12 % over three years, not −50 % [ESTIMATE: BEAR-C057].
4. **Earnings are compounding without tariff help.**
   - FY2026 net income before exceptional items rose 51 %, and the share price has absorbed that by de-rating [CALCULATION: BEAR-C024].
   - Management's 4–5 % organic ARPU plus subscriber growth plus deleveraging still supports roughly 10–13 % EPS growth (scenario model, section 2 of `calc/bear-case_scenarios.out`).
5. **Rivals' incentives point to discipline, not war.** Jio's IPO investors are buying ARPU growth [ESTIMATE: BEAR-C043]. Vi is rationed by lenders [ESTIMATE: BEAR-C045]. Airtel's churn is stable [FACT: BEAR-C007] while its revenue share rises [MANAGEMENT STATEMENT: BEAR-C031].
6. **Regulatory claims are bounded:** about INR 21–25 a share [CALCULATION: BEAR-C061].

**Where the bear case is weak.** It depends on a structural break (A2) whose base rate is roughly once a decade, and whose most likely instigator (Jio) currently has strong reasons to raise prices rather than cut them. Absent that break, the realistic downside is an opportunity-cost outcome (B1), not permanent impairment [JUDGMENT].

## 14. Four-Layer Evidence Crosswalk

### Layer 1 — Bedrock Compounder
- **Relevant evidence:** through-cycle earnings and per-share dilution; incremental returns on the new capex wave; how durable pricing power is without tariff rounds.
- **Supports:** leverage falling and ratings rising [FACT: BEAR-C009; FACT: BEAR-C063]; revenue share at a record 39.7 % [MANAGEMENT STATEMENT: BEAR-C031]; FCF of about INR 54,222 crore [CALCULATION: BEAR-C055].
- **Weakens:**
  - Through-cycle record: FY2016–FY2019 net income −93 % and a FY2020 loss of INR 32,183 crore [CALCULATION: BEAR-C060; FACT: BEAR-C020].
  - Share count +56 % since FY2019 [CALCULATION: BEAR-C052].
  - Adjusted share price flat 2008–2018 [CALCULATION: BEAR-C023].
  - Mobile India EBIT about 9.8 % of gross cumulative investment [CALCULATION: BEAR-C062].
  - Capex accelerating into adjacencies [MANAGEMENT STATEMENT: BEAR-C037].
- **Domain implications:** the L1 failure mode is a multiple de-rating plus reinvestment at mediocre returns. B1 gives about −12 % over three years [ESTIMATE: BEAR-C057].
- **Missing information:** segment-level ROIC on net (not gross) invested capital; data-centre and NBFC return targets.
- **Plausibility effect:** Lowers — the through-cycle record includes a near-wipeout of earnings and heavy dilution within the last eight years.

### Layer 2 — High-Growth Business
- **Relevant evidence:** growth drivers beyond tariffs (homes, postpaid, enterprise, Africa); the saturation of India mobile.
- **Supports:** Africa constant-currency growth and net income recovery [FACT: BEAR-C047]; homes customers +41.7 % YoY at Mar-2026 (Quarterly Report s.4.3, via BEAR-C006 source); postpaid gains [MANAGEMENT STATEMENT: BEAR-C035].
- **Weakens:** India mobile subscribers +3.2 % [FACT: BEAR-C007]; ARPU guided to 4–5 % a year organically [MANAGEMENT STATEMENT: BEAR-C036]; homes net adds moderating [MANAGEMENT STATEMENT: BEAR-C035].
- **Domain implications:** consolidated growth after FY2027 converges towards about 10 % EBITDA unless pricing resets. Consensus implies about 16 % [CALCULATION: BEAR-C056].
- **Missing information:** a homes and enterprise unit-economics cohort; data-centre pipeline economics.
- **Plausibility effect:** Lowers — the growth is real but mostly GDP-plus in the core. The high-growth pockets are small or FX-exposed.

### Layer 3 — Cyclical / Event-Driven Opportunity
- **Relevant evidence:** the tariff cycle as a catalyst; Jio's IPO; Vi's fate; trough solvency.
- **Supports:** a tariff round would move EPS sharply, since each 10 % of ARPU is worth INR 245–300 a share [CALCULATION: BEAR-C069]; brokers expect a round [INFERENCE: BEAR-C044]; trough solvency is strong [FACT: BEAR-C009].
- **Weakens:** the catalyst is outside Airtel's control and 27 months overdue [INFERENCE: BEAR-C044]; the Vi rescue removes consolidation as an event [FACT: BEAR-C034]; consensus already embeds it [ESTIMATE: BEAR-C040].
- **Domain implications:** an event-driven buyer at INR 1,778.70 is buying a widely expected catalyst. The downside if it fails is B1, about −12 %, rather than a floor of zero.
- **Missing information:** Jio RHP pricing and post-IPO tariff intent; the auction calendar and reserve prices.
- **Plausibility effect:** No change — the tariff catalyst exists but is consensus. The downside is bounded by the balance sheet.

### Layer 4 — Venture-Style / Optionality Bet
- **Relevant evidence:** data centres (to 1 GW), the NBFC, the Airtel Money listing, satcom partnerships.
- **Supports:** management commitment and external capital for data centres [MANAGEMENT STATEMENT: BEAR-C037]; RBI approval for lending (Q4FY2026 release).
- **Weakens:** capital calls of INR 14,000 crore for the NBFC [MANAGEMENT STATEMENT: BEAR-C012]; the options are small relative to an INR 11.1 lakh crore market cap [FACT: CIO-C003]; promoter co-investment creates conflicts.
- **Domain implications:** the option value is unlikely to drive per-share outcomes, and the failure mode is capital leakage.
- **Missing information:** NBFC business plan, ROE target and credit policy; data-centre contracted capacity.
- **Plausibility effect:** Insufficient evidence — the options are early, and evidence of adoption at scale was not in scope.

## 15. Contradictions and Data Conflicts

| Item | Source A | Source B | Gap / likely cause | Resolution | Confidence |
|---|---|---|---|---|---|
| FY2026 EBITDA | KPI pack INR 1,212,676 million [FACT: BEAR-C002] | Statutory "profit before D&A…" INR 1,224,918 million | The statutory line includes other income (INR 28,173 million); the KPI line excludes it and adds back items such as charity | KPI EBITDA used for multiples | H |
| FY2026 profit | Company attributable INR 26,695 crore [FACT: BEAR-C003] | Screener "net profit" INR 33,823 crore; CRISIL "adjusted PAT" INR 33,823 crore [FACT: BEAR-C063] | Aggregator and CRISIL include NCI | Company attributable figure used | H |
| FY2018 revenue | FY2018 AR INR 836,879 million [FACT: BEAR-C018] | FY2019 AR restated INR 826,388 million | Reclassification | Noted; immaterial to the trough analysis | H |
| Capex outlook | CRISIL expects capex intensity to moderate [FACT: BEAR-C063] | Management: "period of rapid capex spend", "will not hold back" [MANAGEMENT STATEMENT: BEAR-C037] | Rater's base case vs management's intent | Management is the better guide to capex intent; the rater's view is a benchmark | M |
| Market share | Management revenue share 39.7 % [MANAGEMENT STATEMENT: BEAR-C031] | CRISIL subscriber share 37.55 % and revenue share about 34.9 % [FACT: BEAR-C063] | Different definitions (revenue vs subscriber; AGR basis) | Both shown; industry specialist to reconcile with TRAI | M |
| Share price, Mar-2026 | Yahoo monthly close INR 1,782.4 [CALCULATION: BEAR-C023] | Company BSE close INR 1,784 [FACT: BEAR-C009] | Exchange (NSE vs BSE) | Consistent within 0.1 % | H |
| Model FY2026 EPS | Model reconstruction INR 47.5 | Reported basic EPS INR 45.96 (incl. exceptional) [FACT: BEAR-C003] | KPI EBITDA vs statutory items; weighted shares | The model overstates, so bear scenarios are conservative | M |

## 16. Assumptions, Uncertainty and Missing Evidence

| # | Assumption | Why necessary | Supporting evidence | Plausible alternative | Effect if wrong | Confidence |
|---|---|---|---|---|---|---|
| 1 | NCI share of profit falls to about 18 % after the ICIL swap | Attributable EPS modelling | Africa NCI cut from about 37 % to about 21 % [FACT: BEAR-C013] | Indus or Hexacom NCI grows faster | ±2–3 % on EPS | M |
| 2 | 7 % a year India mobile revenue growth without repair | B1–B3 base | ARPU 4–5 % plus subscribers about 3 % [MANAGEMENT STATEMENT: BEAR-C036; FACT: BEAR-C007] | 9–10 % with mix and postpaid | B1 value about +5 % | M |
| 3 | 100 % flow-through of an ARPU reset to EBITDA | B2 | Fixed-cost network (EBITDA margin about 60 %) [FACT: BEAR-C049] | 80 % flow-through with cost cuts | B2 about −35 % instead of −42 % | M |
| 4 | Exit P/E of 22x / 18x / 16x | Scenario values | EV/EBITDA history 7.75–14.14x [FACT: BEAR-C048] | Market keeps a 30x+ premium | Bear losses about halve | L |
| 5 | D&A grows 9–11 % a year | Capex step-up | Q4FY2026 capex at 29 % of revenue [CALCULATION: BEAR-C072] | Capex moderates (CRISIL) | EPS higher by about 3–5 % | M |
| 6 | Cumulative dividends of INR 60–84 over three years | Total-return arithmetic | FY2026 DPS INR 24 | Payout raised | Small | M |
| 7 | Probability bands for A1–A5 | Hidden-assumption audit | Reference classes in section 5 | — | Changes the weighting, not the mechanisms | L |

**Missing evidence:**
- **Q1FY2027 Quarterly Report (KPI pack):** not retrieved, so Q1FY2027 EBITDA was approximated from the statutory line [CALCULATION: BEAR-C054]. Low impact.
- **Jio DRHP and RHP:** not read, so Jio's capital use and pricing intent are unknown. High relevance to A2.
- **Vi exchange filings:** the AGR reassessment figure and the status of bank funding come from tier-6 summaries [FACT: BEAR-C034; ESTIMATE: BEAR-C045]. The industry specialist should verify them.
- **The SEBI, CCI and court portals, and African tax and court records:** not queried directly. Medium relevance; Africa tax disputes are partly covered in note 23.
- **Fitch and Moody's rating actions after 2019:** not located.
- **A continuous ARPU series FY2016–FY2025 and TRAI market-share data:** owned by the industry specialist.
- **The current status of the DoT interconnection (POI) penalty:** not verified [FACT: BEAR-C066].
- **Tariff-round dates before 2024:** recalled, not verified in this run (section 5, row A1).
- **Corpus defects noted:** the Q4FY2024 results file is labelled "year ended March 31, 2023" in its headline (not opened by bear-case). The FY2026 AR is absent from the corpus and was retrieved from airtel.in.

## 17. Questions and Dependencies for the CIO

1. **Valuation:** test B1/B2 against the run's cost of equity and the DCF. The bear finding that B1 is an IRR of about −4 % a year [ESTIMATE: BEAR-C057] depends on an exit P/E of 22x. Does valuation's reverse DCF imply a tariff round?
2. **Industry:** verify the pre-2024 tariff-round dates; Vi's AGR reassessment and funding [FACT: BEAR-C034; ESTIMATE: BEAR-C045]; and TRAI revenue and subscriber share (the conflict in section 15). Assess whether Jio's IPO raises or lowers the probability of a price war.
3. **Financials:** confirm segment net invested capital and incremental ROIC for Mobile India (BEAR-C062 uses gross cumulative investment), and the NCI share after the swap.
4. **Management / filings:** review the NBFC co-investment with Bharti Enterprises (related-party terms) [MANAGEMENT STATEMENT: BEAR-C012]; Singtel's selling pattern [FACT: BEAR-C067]; and the trend in contingent liabilities [FACT: BEAR-C028].
5. **Special situations:** check whether the ICIL share swap at INR 1,923 [FACT: BEAR-C013] created or destroyed per-share value, given Airtel Africa's market price at the time.
6. **Moat:** does Airtel's premiumisation (postpaid, Fast Lane) protect ARPU in a Jio share push, or did it fail in 2016–2018 [FACT: BEAR-C039]?

## 18. Domain Conclusion

**Answers to the decision questions.**
1. **Bull case:** a rational three-player market plus premium positioning, deleveraging and Africa compounding. It rests on A1 (tariff repair), A2 (structure stays rational), A3 (capex moderates), A4 (Africa FX) and A5 (the multiple holds). See sections 4–5.
2. **Assumption audit:**
   - A1 fails with **moderate** probability, but it is mostly an opportunity-cost risk.
   - A2 is the most damaging, with a **low** probability of failure and a once-a-decade base rate.
   - A3 and A5: moderate.
   - A4: moderate, but temporary on its own.
3. **Pre-mortem:** no tariff round, then a post-IPO share war, plus capex staying high. That combination delivers −40 to −58 % (B2/B3) [ESTIMATE: BEAR-C058; ESTIMATE: BEAR-C059].
4. **Permanent-loss mechanisms:**
   - (a) A structural ARPU reset that lowers the earnings level.
   - (b) Equity issuance at depressed prices in a downturn [FACT: BEAR-C021; CALCULATION: BEAR-C052].
   - (c) Capital reinvested below the cost of capital [CALCULATION: BEAR-C062].
   - (d) Concentrated Africa FX exposure after the swap [FACT: BEAR-C013].
   - De-rating alone is mostly temporary, or an opportunity cost.
5. **Correlation:** the share war, the capex response, fixed DoT instalments and Africa FX reinforce each other (section 8).
6. **Value trap:** no. The risk is a quality premium paid for growth that is partly one-off (section 10).
7. **Indicators:** section 12.

**Bear-risk classification: Moderate.**
- The franchise, balance sheet and accounting do not present a high or severe risk of permanent loss.
- The risk lies in the price paid relative to earnings growth that depends on industry pricing behaviour Airtel does not control.
- The base rate for that behaviour turning hostile is about one break per decade, with −44 % to −50 % share-price outcomes [CALCULATION: BEAR-C023] [JUDGMENT].

**Single biggest reason not to invest.**

At INR 1,778.70 the stock trades at about 37x pro-forma trailing earnings [CALCULATION: BEAR-C053], and sell-side consensus needs EPS to rise from about INR 48 to INR 82 by FY2028 [ESTIMATE: BEAR-C040]. Under this report's model that needs about 16 % annual EBITDA growth [CALCULATION: BEAR-C056].

Management itself has stopped promising tariff repair. It describes FY2026 as a year without it [MANAGEMENT STATEMENT: BEAR-C031], frames sustainable ARPU growth at 4–5 % a year [MANAGEMENT STATEMENT: BEAR-C036], and is entering "a period of rapid capex spend" [MANAGEMENT STATEMENT: BEAR-C037], while ARPU stalled at INR 257–264 [FACT: BEAR-C006; MANAGEMENT STATEMENT: BEAR-C035].

Meanwhile the industry is getting more capital, not less. Vi has been rescued [FACT: BEAR-C034] and Jio is raising IPO money [ESTIMATE: BEAR-C043]. The price therefore depends on a tariff round that Airtel cannot deliver alone. The last time industry pricing broke, earnings fell by more than 90 % and the company had to issue equity at INR 220 [FACT: BEAR-C019; FACT: BEAR-C021].

**Probability of a permanent loss of ≥30 % over five years: low (5–20 %).**
- Reasoning: a ≥30 % loss needs the competitive-reset branch (B2/B3, or a 2016–2019 replay [CALCULATION: BEAR-C060]). Its reference-class frequency is about two breaks in about 18 years [CALCULATION: BEAR-C023], which puts a five-year incidence in the low-to-moderate band.
- That is moderated by today's materially stronger balance sheet [FACT: BEAR-C009] and by Jio's current incentive to raise, not cut, prices [ESTIMATE: BEAR-C043].
- The more likely bad outcome, no tariff round plus a de-rating, produces returns well below a normal equity hurdle (B1, about −12 % over three years [ESTIMATE: BEAR-C057]), not a ≥30 % permanent loss [JUDGMENT].

## 19. Source Register

| ID | Title | Issuer | Date | URL or identifier | Retrieved | Tier |
|---|---|---|---|---|---|---|
| S1 | Audited results and Quarterly Report Q4FY2026 (incl. media release) | Bharti Airtel Limited | 2026-05-13 | FilingForge:b5c6beda-7ade-4dd3-ad4f-bff5e5efe4c1 | 2026-10-12 | 1/3 |
| S2 | Audited results Q1FY2027 | Bharti Airtel Limited | 2026-08-04 | FilingForge:3a61007b-6d5a-449e-be4d-84dca645422b | 2026-10-12 | 1 |
| S3 | FY2026 Consolidated Financial Statements | Bharti Airtel Limited | 2026-07 | https://www.airtel.in/airtel-annual-report-2025-26/files/pdfs/Consolidated-Financial-Statements.pdf | 2026-10-12 | 1 |
| S4 | FY2026 Management Discussion and Analysis | Bharti Airtel Limited | 2026-07 | https://www.airtel.in/airtel-annual-report-2025-26/files/pdfs/Management-Discussion-And-Analysis.pdf | 2026-10-12 | 1 |
| S5 | Annual Reports FY2017, FY2018, FY2019, FY2020, FY2021 | Bharti Airtel Limited | 2017–2021 | FilingForge:AR-532454-2017; AR-532454-2018; e52e5a27-cfee-4e32-aac2-04337c03baeb; 49889f5f-b097-41be-8be7-8bad6d949760; 3e7fff81-d3bf-4662-8dd5-8c18db7db532 | 2026-10-12 | 1 |
| S6 | Quarterly Report Q3FY2019; Q2FY2021 | Bharti Airtel Limited | 2019-01-31; 2020-10-27 | FilingForge:16609b54-18cb-4a9b-9cf0-624572bc7d35; FilingForge:0a99ebcf-7da7-484a-9868-81b346144036 | 2026-10-12 | 3 |
| S7 | Earnings transcripts Q3FY2023, Q2FY2026, Q1FY2027 | Bharti Airtel Limited | 2023-02-15; 2025-11-11; 2026-08-10 | FilingForge:fa591d96-dbad-4607-9a1c-595b9a0f814e; ba4a97f1-0054-42d7-b24b-151c74e4a78f; a46861ad-47c4-4fb1-9001-f56835e1a897 | 2026-10-12 | 4 |
| S8 | Monthly price history BHARTIARTL.NS | Yahoo Finance | 2026-10-12 | https://query1.finance.yahoo.com/v8/finance/chart/BHARTIARTL.NS?range=max&interval=1mo | 2026-10-12 | 5 |
| S9 | Consolidated financials (12 years) | Screener | 2026-10-12 | https://www.screener.in/company/BHARTIARTL/consolidated/ | 2026-10-12 | 5 |
| S10 | Rating rationale, Bharti Airtel, 17-Jul-2026 | CRISIL Ratings | 2026-07-17 | https://www.crisil.com/mnt/winshare/Ratings/RatingList/RatingDocs/BhartiAirtelLimited_July 17_ 2026_RR_399750.html | 2026-10-12 | 5 |
| S11 | Consensus forecast page | StockAnalysis (S&P Global) | 2026-08-13 | https://stockanalysis.com/quote/nse/BHARTIARTL/forecast/ | 2026-10-12 | 5 |
| S12 | DoT denies AGR relief parity to Airtel and Tata Teleservices | Fox Mandal | 2026-03-31 | https://foxmandal.in/News/dot-denies-agr-relief-parity-to-airtel-and-tata-teleservices/ | 2026-10-12 | 6 |
| S13 | Moody's downgrades Bharti Airtel to Ba1 | Business Standard | 2019-02-05 | https://www.business-standard.com/amp/article/companies/moody-s-downgrades-bharti-airtel-rating-to-ba1-over-cash-flow-situation-119020501540_1.html | 2026-10-12 | 6 |
| S14 | S&P upgrades Bharti Airtel to BBB+ | FilingReader | 2026-06-24 | https://filingreader.com/news-wire/mumbai/2026-06-24/sp-upgrades-bharti-airtel-to-bbb-on-strong-earnings | 2026-10-12 | 6 |
| S15 | Jio IPO nears launch | YourStory | 2026-10 | https://yourstory.com/2026/10/jio-ipo-nears-launch-drhp-filed-sebi-clears-path | 2026-10-12 | 6 |
| S16 | Tariff-hike outlook (Centrum) | Free Press Journal | 2026-08 | https://freepressjournal.in/tech/reliance-jio-airtel-vi-may-raise-mobile-tariffs-by-12-15-in-india-over-next-three-to-four-months | 2026-10-12 | 6 |
| S17 | Vodafone Idea rating rationale | CARE Ratings | 2026-01-07 | https://www.careratings.com/upload/CompanyFiles/PR/202601070127_Vodafone_Idea_Limited.pdf | 2026-10-12 | 5/6 |
| S18 | Starlink final nod for India launch | RCR Wireless | 2026-09 | https://www.rcrwireless.com/?p=421701 | 2026-10-12 | 6 |
| S19 | Airtel denies 375m-record breach | Moneylife | 2024-07-05 | https://moneylife.in/article/airtel-denies-breach-after-hacker-lists-data-of-375-million-customers-on-dark-web/74580.html | 2026-10-12 | 6 |
| S20 | SEBI settlement by promoter entity | Business Standard | 2017-04-05 | https://www.business-standard.com/article/pti-stories/bharti-airtel-promoter-pays-rs-2-17-l-to-settle-case-with-sebi-117040500839_1.html | 2026-10-12 | 6 |
| S21 | SC rejects CCI appeal in POI cartel case | AZB & Partners | 2018-12-31 | https://www.azbpartners.com/bank/supreme-court-rejects-appeal-on-cartel-investigation-against-airtel-vodafone-and-idea/ | 2026-10-12 | 6 |
| S22 | Singtel unit to sell Airtel stake | Business Standard | 2025-11-06 | https://www.business-standard.com/amp/industry/news/singtel-unit-to-sell-bharti-airtel-stake-worth-rs-10300-cr-125110601792_1.html | 2026-10-12 | 6 |
| S23 | Price, shares, market cap (preflight) | NSE / Bharti Airtel | 2026-10-12 | CIO-C001, CIO-C002, CIO-C003 | 2026-10-12 | 1 |
| C1 | Bear-case calculations | bear-case | 2026-10-13 | calc/bear-case_scenarios.py, calc/bear-case_drawdowns.py (+ .out) | — | — |
