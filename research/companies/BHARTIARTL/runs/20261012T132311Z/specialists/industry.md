---
specialist: industry
company: Bharti Airtel Limited
ticker: BHARTIARTL
exchange: NSE
run_id: 20261012T132311Z
research_cutoff: 2026-10-12
report_status: complete
model_requested: opus
independence_attestation: "Initial investigation completed without reading other specialists' reports or prior-run conclusions for this company."
coverage_exception: "Industry share history meets 10+ years (TRAI FY2009-FY2010 and FY2013-Q1FY2027; FY2011-FY2012 TRAI PDFs are corrupt on the TRAI server). Competitor 10-year margin/return history for Jio and Vodafone Idea was not retrieved (BSE returned HTTP 403, Vi IR pages 404, repeated SSL failures); the 10-year competitor benchmark therefore uses TRAI operator-level AGR and subscribers, with FY2026 financials only for peers."
---

# Industry and Industry Economics: Bharti Airtel Limited (BHARTIARTL)

## 1. Mandate, Scope and Independence

**Decision questions answered.** (1) How money is made in Indian (and African) telecom and what sets price, volume, margin and capital intensity; (2) where the profit pools sit and who has bargaining power; (3) how large the reachable market is and how penetrated; (4) whether Airtel has gained or lost share over 10+ years and why; (5) whether current growth is structural, cyclical or share-driven, and where the cycle stands; (6) which macro factors move the economics and by how much; (7) which regulatory, technological or competitive changes could permanently change the economics.

**In scope.** India wireless (mobile) as the core profit pool, with India home broadband, enterprise (Airtel Business), DTH, towers (Indus Towers, a subsidiary since 18-Nov-2024 [FACT: CIO-C007]) and data centres covered more briefly; Africa (Airtel Africa plc, 14 markets) as a separate industry structure. **Out of scope:** the moat verdict (moat specialist), valuation multiples (valuation), scores, layer choice and any recommendation.

**Playbooks applied.** `SECTOR_PLAYBOOKS.md` §16 Telecom and media (primary) and §18 Holding companies (listed-subsidiary structure, used only to frame Africa/Indus/Hexacom scope). Lenses owned: T1 (business research), T8 (cycle position), T11 (category), T13 (industry base rates).

**Method and evidence.** The spine of this report is 18 TRAI Performance Indicator Reports (March quarter of FY2009, FY2010 and FY2013–FY2026, plus the June-2026 quarter and the FY2025-26 Yearly report), downloaded with `fetch_source.py`, converted with `pdftotext`, and every transcribed number page-verified by script (`industry_workpapers/trai_page_verification_log.txt`). Company KPIs come from the local corpus (results packs with embedded Quarterly Reports, transcripts, annual reports) and from Airtel IR Quarterly Reports/KPI workbooks for FY2014–FY2021. Peer data: RIL's Q4FY2026 media release for Jio (tier 3); Vodafone Idea only from secondary reports (tier 6) because primary retrieval failed.

**Blockers (none fatal).** TRAI FY2011 and FY2012 PDFs are corrupt at source; several Airtel IR files, the TRAI spectrum press release and Airtel Africa's RNS failed with SSL errors (logged in `source_retrievals.csv`); BSE's API returned HTTP 403. Each gap is listed in Section 17.

## 2. Key Findings

1. **India mobile is now a three-private-player market that has concentrated sharply, and Airtel has been the main beneficiary after Jio.** Top-3 share of access-services AGR rose from 76.5% (FY2013) to 95.8% (FY2026) and the HHI of listed providers from about 2,400 to about 3,700 [CALCULATION: IND-C035]. Airtel's revenue (AGR) share went 28.9% (FY2013) → 30.2% (FY2016) → 22.7% trough (FY2019) → 39.7% (FY2026) → 40.0% (Q1FY2027); Jio holds 44.8% and Vodafone Idea 11.3% [CALCULATION: IND-C034].
2. **The 2016–2019 Jio entry was a structural reset, not a normal cycle.** Industry access AGR fell 36.2% from FY2016 Q4 to FY2018 Q4, then compounded 14.0% a year to FY2026 [CALCULATION: IND-C046]. Airtel ARPU fell from Rs 194 (Q4FY2016) to Rs 116 (Q4FY2018) and has since risen to Rs 257 (Q4FY2026) and Rs 264 (Q1FY2027) [MANAGEMENT STATEMENT: IND-C042; IND-C053].
3. **Over ten years, Airtel's growth has been roughly two-thirds industry and one-third share gain.** FY2016–FY2026: Airtel TRAI AGR grew 9.1% a year vs industry 6.2%, i.e. ~6.0 pp/yr from the market and ~2.7 pp/yr from share [CALCULATION: IND-C045]. Reported India mobile revenue grew 7.3% a year, split ARPU 2.9% and customers 4.0% [CALCULATION: IND-C044]. Since FY2019 the mix has been ARPU-led (ARPU 11.1%/yr, customers 4.1%/yr).
4. **Pricing power is collective, not individual, and has been exercised three times in seven years.** Repairs in Dec-2019, Nov-2021 and Jul-2024 [MANAGEMENT STATEMENT: IND-C048] each lifted Airtel ARPU ~14–16% over two quarters while customers kept growing (+2.7% through the 2024 round) [CALCULATION: IND-C066]. No headline hike has happened since July 2024 and management says the price architecture (cheap unlimited data) still needs repair [MANAGEMENT STATEMENT: IND-C049]. Organic ARPU drift without hikes was +8.3% (FY2024) and +4.9% (FY2026) [CALCULATION: IND-C066].
5. **Industry growth has slowed to mid/high single digits absent tariff action.** Industry AGR grew 10.4% in FY2026 [FACT: IND-C037], industry wireless ARPU only 3.6% on an M2M-diluted basis [FACT: IND-C038], and management puts underlying wireless market growth at ~6% [MANAGEMENT STATEMENT: IND-C050]. Realisation per GB fell 10.6% to Rs 8.02 while usage rose 24.7% [FACT: IND-C041].
6. **The weakest competitor has been stabilised by the state, which lowers both exit odds and price-war odds.** Vodafone Idea received AGR relief (dues frozen, payments capped; liability remeasured from ~Rs 80,502 cr to ~Rs 24,880 cr per press reports) and recorded its first net subscriber addition since the merger in Q1FY2027 [FACT: IND-C063, low confidence]. A three-player market is now the base case rather than a two-player one.
7. **Africa is a different industry at a different stage.** 14 markets, ~45% tele-density and ~50–52% smartphone penetration [MANAGEMENT STATEMENT: IND-C060; FACT: IND-C059]; Airtel Africa grew 24% in constant currency in FY2026 with a 49% EBITDA margin [FACT: IND-C058]. FX is the dominant swing factor: a 10% translation fall in African currencies cuts consolidated EBITDA ~2.3% [CALCULATION: IND-C068].
8. **Tariffs are the single largest industry-level value driver.** A 10% mobile tariff increase with no subscriber loss adds roughly 8% to FY2026 consolidated EBITDA (about 6.5% with a 2% subscriber loss) [ESTIMATE: IND-C067].
9. **Cycle position: mid-cycle in a structurally consolidated market, with spectrum and capex cycles past their peak but a new auction pending.** 5G capex has rolled over in mobile (FY2026 mobile capex -3%) [FACT: IND-C055]; TRAI has recommended a large auction with lower reserve prices [FACT: IND-C065]; 2022 spectrum instalments resume from Aug-2026 [FACT: IND-C064].

## 3. Data Coverage

| Data series | Periods covered | Count | Sources and tier | Verification | Gaps and exceptions |
|---|---|---|---|---|---|
| India access AGR by operator (Q4 snapshot) | FY2010, FY2013–FY2026, Q1FY2027 | 16 periods (17 fiscal years spanned) | TRAI Performance Indicator Reports (tier 2) | Full: every value page-verified by script | FY2011–FY2012 PDFs corrupt; FY2010 table is gross revenue (GR) not AGR; FY2015 column mislabelled (see §15) |
| India wireless subscribers by operator (March) | FY2009, FY2010, FY2013–FY2026, Q1FY2027 | 17 | TRAI (tier 2) | Full (page-verified) | Definition break at Dec-2025 (Airtel M2M added); FY2014–FY2015 RCom row not captured |
| Industry totals FY2026 (GR, AGR, ARPU, data, M2M) | FY2025–FY2026 | 2 | TRAI Yearly Performance Indicators 2025-26 (tier 2) | Full | — |
| Airtel India mobile ARPU and customers | FY2014–FY2026, Q1FY2027 | 13 years + latest quarter | Airtel Quarterly Reports / KPI workbooks / results packs (tier 3) | Sampled against two sources where overlapping (FY2018: 115.6 vs 116) | Q4FY2012–Q4FY2013 reports failed to download; Q4FY2022 customer count not captured |
| Airtel India mobile revenue | FY2014–FY2019 (QR/AR), FY2020–FY2026 (segment note) | 12 years (FY2015 included) | Audited segment results (tier 1); QR (tier 3) | Sampled | Segment scope changes (Airtel Money, IFRS→Ind AS, Indus recast) |
| Competitor financials | FY2026 (Jio), FY2026/Q1FY2027 (Vi) | 1–2 | RIL release (tier 3); press (tier 6) | Jio full; Vi not verified | 10-year peer margins not retrieved (coverage exception) |
| Regulatory events | 2016–2026 | — | Airtel ARs/QR (tier 1/3), TRAI (via Airtel summary) | Sampled | TRAI PR 25/2026 and DoT originals not retrieved |
| Africa | FY2026 (+ management context) | 1 | Airtel QR (tier 3); Airtel Africa RNS via WebFetch (tier 1, M) | Partial | Country-level market shares not retrieved |

## 4. Business Model and Economic Engine

**Conclusion.** India mobile is a high-fixed-cost, spectrum-gated network business where revenue is subscribers × ARPU, incremental subscribers and incremental data are close to costless at the margin until capacity binds, and returns are set almost entirely by industry pricing discipline [JUDGMENT]. Airtel's India mobile segment earned a 60.2% EBITDA margin on Rs 1,129,954 mn of FY2026 revenue with capex of Rs 186,027 mn [FACT: IND-C055].

**Engine (inputs → cash).**
- *Inputs:* spectrum bought at auction from the state (20-year rights, paid upfront or in deferred instalments) [FACT: IND-C064]; passive infrastructure leased from tower companies (Indus Towers, now consolidated, 1.62 tenants per tower) [FACT: IND-C057]; radio and core equipment (largely imported); fibre backhaul (Airtel: 532,388 route km) [FACT: IND-C071]; energy; distribution (retail recharge channel, digital app).
- *Customer and payer:* overwhelmingly prepaid consumers (92% of Airtel's mobile base) [FACT: IND-C054], paying monthly or 28/84-day bundles of unlimited voice plus a data allowance; postpaid (29.0 mn), enterprise and IoT/M2M (106 mn postpaid incl. IoT) are smaller but higher value [FACT: IND-C054].
- *Why they pay:* connectivity is non-discretionary; switching costs are low technically (number portability) but the network-quality and bundle (OTT, roaming, family plans) differences matter at the premium end.
- *Price setter:* the industry's headline prepaid plan grid, moved collectively in rounds [MANAGEMENT STATEMENT: IND-C048]; Airtel's ARPU premium (Rs 257 vs Jio Rs 214 and Vi Rs 190 in Q4FY2026) comes from mix (postpaid, smartphone, roaming, urban) more than list price [FACT: IND-C062; IND-C063] [INFERENCE].
- *Margin drivers:* operating leverage on a largely fixed network cost base (towers, energy, staff) plus a variable 8% licence fee and spectrum usage charges on AGR (assumption set in IND-C067); ARPU increases fall through at roughly 90% [ESTIMATE: IND-C067].
- *Capital intensity:* lumpy generational capex (4G 2016–2019, 5G 2022–2025) and spectrum. India (including towers) capex was Rs 396,539 mn in FY2026, about a quarter of India revenue [FACT: IND-C055].

**The 10–20 KPIs that drive value, and why** (dashboard in §14):

| KPI | Why it matters |
|---|---|
| Industry ARPU and Airtel ARPU | Price × mix; >90% flow-through to EBITDA |
| Revenue (AGR) market share | Captures share and price together; regulator-sourced |
| Subscriber share and net adds | Volume; churn signals competitive aggression |
| Monthly churn | Price-war early warning (Airtel 2.4%, Jio 1.7%) [FACT: IND-C054; IND-C062] |
| Smartphone/4G-5G data customer % | Upgrade runway (Airtel 80.1% data customers) [FACT: IND-C054] |
| Data usage per user and revenue per GB | Capacity need vs monetisation (Rs 8.02/GB, -10.6%) [FACT: IND-C041] |
| Postpaid share | Highest-ARPU cohort |
| Capex/revenue and towers/base stations | Capital intensity and network cycle |
| Spectrum holdings and deferred dues | Quasi-debt; auction cycles |
| Number of viable competitors (Vi health) | Structure determines price |
| HHI / CR3 | Concentration trend |
| Tower tenancy and rent per tower | Passive-infrastructure profit pool |
| Home broadband subs and ARPU | Second growth vector |
| Africa constant-currency growth, ARPU, FX | Africa engine and translation risk |
| Mobile-money customers/revenue | Africa adjacency profit pool |

## 5. Value Chain and Profit Pools

**Conclusion.** The industry's profit pool is concentrated in the two scaled private operators; the state takes a large and partly fixed share (spectrum, licence fee, SUC, GST); tower companies earn steady utility-like rents but have weakened bargaining power as tenancy has fallen; equipment vendors and handset makers sit outside Airtel's control; OTT platforms capture much of the consumer surplus from cheap data [JUDGMENT].

| Layer | Who | Evidence of economics | Bargaining power vs operators |
|---|---|---|---|
| Spectrum / licence (state) | DoT | Rs 6,936 cr licence fee and Rs 1,017 cr SUC in Q4FY2026 alone [FACT: IND-C072]; auctions: Rs 65,789 cr (2016), Airtel Rs 43,040 cr (2022) [FACT: IND-C064] | High (monopoly supplier), but now pro-industry: reserve prices being cut [FACT: IND-C065]; relief for Vi [FACT: IND-C063] |
| Passive infrastructure | Indus Towers (Airtel subsidiary), others | 264,514 towers, 1.62 sharing factor (1.64 a year earlier), sharing revenue per tower -2.9% YoY [FACT: IND-C057] | Moderate; tenancy falling as operators shrink to three; Airtel's consolidation of Indus internalises this pool |
| Active network and devices | Global vendors; handset OEMs | Memory/chipset prices hurt FWA device economics [MANAGEMENT STATEMENT: IND-C061] | Moderate; import-linked (INR sensitivity, §11) |
| Operators (access) | Jio 44.8%, Airtel 39.7%, Vi 11.3%, BSNL 2.9% of Q4FY2026 access AGR [CALCULATION: IND-C034] | Airtel mobile EBITDA margin 60.2%; Jio Platforms 51.9%; Vi ~42% [CALCULATION: IND-C070] | Customers fragmented (no buyer power individually); collective consumer resistance limits tariff steps |
| Content / OTT / apps | OTT platforms, messaging apps | Enterprise SMS/wholesale pressured by migration to WhatsApp-type apps [MANAGEMENT STATEMENT: IND-C073] | High at the application layer; operators are bundling OTT to defend ARPU |

**Profit-pool arithmetic.** In Q4FY2026 the top two private operators took 84.5% of access AGR (Jio 44.8% + Airtel 39.7%) [CALCULATION: IND-C034]. Industry AGR was Rs 3,34,659 cr in FY2026, of which access services were 83.6% in Q4FY2026 [FACT: IND-C037; IND-C072]. The industry's return problem has historically sat at the operator layer: management reported a 11.2% India ROCE in Q2FY2025 even after two repair rounds [MANAGEMENT STATEMENT: IND-C052].

## 6. Market Size and Reachable Market

**Conclusion.** The relevant market is India access services, Rs 72,488 cr of AGR in Q4FY2026 (about Rs 2.9 lakh crore annualised) [FACT: IND-C015], growing ~10% in FY2026 including the tail of the 2024 hike [FACT: IND-C037]. Subscriber penetration is mature (1,141.85 mn mobile connections ex-M2M, 84.57% overall tele-density ex-M2M) [FACT: IND-C040], so the reachable growth is ARPU (price architecture, premiumisation, postpaid, 5G), not users [INFERENCE: IND-C040; IND-C050].

**Industry size history (TRAI, Q4 access AGR, Rs crore; page-verified):**

| Fiscal year (Q4) | Access AGR, Rs cr | YoY | Claim |
|---|---|---|---|
| FY2010 (GR basis) | 31,154 | — | IND-C001 |
| FY2013 | 27,802 | — | IND-C002 |
| FY2014 | 31,922 | +14.8% | IND-C003 |
| FY2015 | 35,938 | +12.6% | IND-C004 |
| FY2016 | 39,886 | +11.0% | IND-C005 |
| FY2017 | 31,595 | -20.8% | IND-C006 |
| FY2018 | 25,448 | -19.5% | IND-C007 |
| FY2019 | 26,096 | +2.5% | IND-C008 |
| FY2020 | 34,496 | +32.2% | IND-C009 |
| FY2021 | 38,608 | +11.9% | IND-C010 |
| FY2022 | 46,421 | +20.2% | IND-C011 |
| FY2023 | 51,631 | +11.2% | IND-C012 |
| FY2024 | 56,540 | +9.5% | IND-C013 |
| FY2025 | 66,563 | +17.7% | IND-C014 |
| FY2026 | 72,488 | +8.9% | IND-C015 |
| Q1FY2027 | 74,457 | — | IND-C016 |

YoY changes are computed by `calc/industry_market_share.py` inputs (access totals) and summarised in [CALCULATION: IND-C046]; the FY2016→FY2018 fall (-36.2%) and the FY2018→FY2026 recovery (14.0% CAGR) are the decision-relevant facts.

**TAM → serviceable → reachable.**
- *Claimed TAM (management):* no single India TAM figure is used here; management frames growth as ARPU (4–5% a year sustainable "with a sensible price architecture") [MANAGEMENT STATEMENT: IND-C051] and new pools (data centres at ~12% share, 1 GW ambition; homes; B2B digital) [MANAGEMENT STATEMENT: IND-C061].
- *Third-party estimates:* none relied on (no named third-party India telecom TAM retrieved in this run).
- *Own reachable-market arithmetic:* the reachable mobile pool is the access-AGR pool itself, ~Rs 2.9 lakh crore annualised [FACT: IND-C015]. Volume headroom is limited: 1,141.85 mn mobile connections ex-M2M against a tele-density of 84.57% ex-M2M, and connections double-count multi-SIM users [FACT: IND-C040] [INFERENCE]. The reachable growth is therefore (a) ARPU uplift: each 10% ARPU on Airtel's base ≈ Rs 11,300 cr revenue [ESTIMATE: IND-C067]; (b) smartphone conversion: Airtel still has ~20% non-data customers [FACT: IND-C054]; (c) adjacent pools: home broadband (Airtel 14.2 mn homes vs Jio 27.1 mn fixed broadband at ~43% share) [FACT: IND-C056; IND-C062]; nationally 46.54 mn wired internet subscribers plus 16.61 mn FWA subscribers at Mar-2026 [FACT: IND-C076; IND-C040], against a national household base that is several times larger (household count not retrieved in this run, so penetration is not quantified) [INFERENCE].
- *Africa:* ~680 mn population across 14 markets with ~45% tele-density and 2% home broadband penetration [MANAGEMENT STATEMENT: IND-C060]: the reachable market there is still volume-led.

## 7. Industry Structure and Competitive Intensity

**Conclusion.** The structure moved from a fragmented 10–12-operator market (FY2010–FY2016) to an effective three-private-player oligopoly with a state-owned fourth player (BSNL) of shrinking relevance. Concentration is high (HHI ≈ 3,700 on revenue) and still rising slowly [CALCULATION: IND-C035]. Behaviour since 2019 has been rational on price (three synchronised repairs, no price war) but competitive on network, bundles and FWA [JUDGMENT: IND-C048; IND-C049].

| Fiscal year | CR3 (access AGR) | HHI (listed providers) | No. of providers with >1% AGR share | Claim |
|---|---|---|---|---|
| FY2013 | 76.5% | 2,427 | 9 | IND-C035 (inputs IND-C002) |
| FY2016 | 79.5% | 2,710 | 9 | IND-C035 (IND-C005) |
| FY2019 | 87.7% | 2,752 | 5 | IND-C035 (IND-C008) |
| FY2022 | 94.5% | 3,426 | 4 | IND-C035 (IND-C011) |
| FY2026 | 95.8% | 3,719 | 5 incl. Tata at 1.0% | IND-C035 (IND-C015) |
| Q1FY2027 | 96.0% | 3,731 | — | IND-C035 (IND-C016) |

**Evidence of behaviour, not a checklist.**
- *Price war (2016–2019):* Jio's free services produced negative AGR in Q4FY2017 (Rs -1,179 cr) [FACT: IND-C006]; industry AGR fell 36% [CALCULATION: IND-C046]; Aircel, Telenor, Tata, RCom, Sistema and others exited or were absorbed (their rows disappear from TRAI tables by FY2019–FY2021) [FACT: IND-C007; IND-C008; IND-C010].
- *Capacity discipline:* the 2024 spectrum auction was small and TRAI now recommends cutting reserve prices because spectrum went unsold in 2022 and 2024 [FACT: IND-C065]: operators are not bidding up scarce capacity.
- *Coordinated repair:* three rounds in which all private operators raised prices within days; customer losses were small and transient [MANAGEMENT STATEMENT: IND-C052; IND-C048].
- *Non-price rivalry:* Jio leads FWA/fixed broadband (AirFiber ~13 mn) [FACT: IND-C062]; Airtel pulled back from low-quality FWA acquisition [MANAGEMENT STATEMENT: IND-C061]; Vi is spending (press: three-year capex plan Rs 45,000 cr) [FACT: IND-C063].

**Barriers to entry.** Spectrum (Rs tens of thousands of crore per national footprint) [FACT: IND-C064], a national tower and fibre grid, distribution reach to ~800,000 villages (Airtel coverage table) [FACT: IND-C054], and the experience that even a deep-pocketed entrant (Jio) ran negative access AGR in its launch phase [FACT: IND-C006] and took about three years to reach revenue leadership [CALCULATION: IND-C034]. The credible new-entry vector is satellite broadband, not terrestrial mobile (§12).

**Substitutes outside the narrow industry.** OTT messaging/voice already substitutes SMS and paid voice; public Wi-Fi and the newly delicensed lower 6 GHz band (Jan-2026 rules) [FACT: IND-C074] marginally substitute mobile data indoors; satellite broadband substitutes rural home connectivity at the edges.

**Buyer and supplier power.** Consumers are fragmented and price-sensitive at entry level, but demand has proved inelastic in each repair round [CALCULATION: IND-C066]. The state is the most powerful supplier (spectrum, licence fees) and also the arbiter of competitive structure (Vi relief, BSNL support).

## 8. Market Share and Company Position

**Conclusion.** On a 10-year view (FY2016–FY2026) Airtel is **gaining** revenue share in India mobile: from 30.2% to 39.7% of access AGR (+9.5 pp), with the entire gain achieved after the FY2019 trough of 22.7% [CALCULATION: IND-C034; IND-C070]. On subscribers, its share rose from 24.3% (Mar-2016) to 33.6% (Mar-2025) on the old definition [CALCULATION: IND-C036]. Airtel is second to Jio on both measures but holds the highest ARPU.

**Revenue (AGR) share, Q4 of each fiscal year (TRAI access services; Bharti group incl. Hexacom):**

| Fiscal year | Airtel | Jio | Vodafone + Idea / Vi | BSNL | Source claim |
|---|---|---|---|---|---|
| FY2010 (GR basis) | 28.1% | — | 30.0% | 15.5% | IND-C001 |
| FY2013 | 28.9% | — | 36.9% | 10.7% | IND-C002 |
| FY2014 | 28.7% | — | 37.5% | 10.6% | IND-C003 |
| FY2015 | 29.0% | — | 39.6% | 8.6% | IND-C004 |
| FY2016 | 30.2% | 0.0% | 40.4% | 8.9% | IND-C005 |
| FY2017 | 32.8% | -3.7% | 43.2% | 10.5% | IND-C006 |
| FY2018 | 27.8% | 24.4% | 35.3% | 8.4% | IND-C007 |
| FY2019 | 22.7% | 37.7% | 27.3% | 7.8% | IND-C008 |
| FY2020 | 28.2% | 38.9% | 22.8% | 6.6% | IND-C009 |
| FY2021 | 33.8% | 42.5% | 15.9% | 5.1% | IND-C010 |
| FY2022 | 34.5% | 44.5% | 15.5% | 3.8% | IND-C011 |
| FY2023 | 35.8% | 44.5% | 14.0% | 4.0% | IND-C012 |
| FY2024 | 37.1% | 44.8% | 13.0% | 3.5% | IND-C013 |
| FY2025 | 39.5% | 44.3% | 11.5% | 3.4% | IND-C014 |
| FY2026 | 39.7% | 44.8% | 11.3% | 2.9% | IND-C015 |
| Q1FY2027 | 40.0% | 44.6% | 11.3% | 2.8% | IND-C016 |

Shares computed in `calc/industry_market_share.py` [CALCULATION: IND-C034]. **Definition:** TRAI access-services AGR (gross revenue less pass-through charges such as interconnect usage charges and roaming paid to other operators), quarterly snapshot, all India, all access services (mobile dominant). Caveats: AGR deducted IUC paid until IUC was abolished on 1-Jan-2021, so FY2017–FY2020 shares are distorted (annualised Q4 TRAI AGR was only 0.57× Airtel's reported India mobile revenue in FY2019 but 1.02× in FY2026) [CALCULATION: IND-C047]; Jio's negative AGR in FY2017 is a free-service artefact.

**Wireless subscriber share, end-March (TRAI):**

| Date | Airtel subs (mn) | Airtel share | Jio share | Vodafone+Idea / Vi share | Claim |
|---|---|---|---|---|---|
| Mar-2009 | 93.92 | 24.0% | — | 26.5% | IND-C017 |
| Mar-2010 | 127.62 | 21.8% | — | 28.2% | IND-C018 |
| Mar-2013 | 188.20 | 21.7% | — | 31.6% | IND-C019 |
| Mar-2014 | 205.39 | 22.7% | — | 33.4% | IND-C020 |
| Mar-2015 | 226.02 | 23.3% | — | 35.2% | IND-C021 |
| Mar-2016 | 251.24 | 24.3% | — | 36.1% | IND-C022 |
| Mar-2017 | 273.65 | 23.4% | 9.3% | 34.6% | IND-C023 |
| Mar-2018 | 304.19 | 25.7% | 15.8% | 36.7% | IND-C024 |
| Mar-2019 | 325.18 | 28.0% | 26.4% | 34.0% | IND-C025 |
| Mar-2020 | 327.81 | 28.3% | 33.5% | 27.6% | IND-C026 |
| Mar-2021 | 352.39 | 29.8% | 35.8% | 24.0% | IND-C027 |
| Mar-2022 | 360.33 | 31.5% | 35.4% | 22.8% | IND-C028 |
| Mar-2023 | 370.91 | 32.4% | 37.6% | 20.7% | IND-C029 |
| Mar-2024 | 385.76 | 33.1% | 40.3% | 18.9% | IND-C030 |
| Mar-2025 | 391.00 | 33.6% | 40.8% | 17.6% | IND-C031 |
| Mar-2026 (new basis) | 481.48 | 37.5% | 39.7% | 15.5% | IND-C032 |
| Jun-2026 (new basis) | 490.62 | 37.7% | 39.8% | 15.3% | IND-C033 |

Shares from `calc/industry_market_share.py` [CALCULATION: IND-C036]. **Definition break:** from FY2025-26 Airtel began reporting M2M connections, which other operators had always included [FACT: IND-C039]; pre-2026 shares therefore understate Airtel on a like-for-like basis, and the Mar-2026 jump is not a share gain.

**Growth decomposition (reconciles to reported growth).**

| Window | Industry access AGR CAGR | Airtel AGR CAGR | From industry (pp/yr, log) | From share (pp/yr, log) | Airtel reported India mobile revenue CAGR | of which ARPU | of which customers | Claim |
|---|---|---|---|---|---|---|---|---|
| FY2016–FY2026 | 6.2% | 9.1% | 6.0 | 2.7 | 7.3% | 2.9% | 4.0% | IND-C045; IND-C044 |
| FY2016–FY2019 | -13.2% | -21.1% | -14.1 | -9.5 | -9.5% | -14.1% | 4.0% | IND-C045; IND-C044 |
| FY2019–FY2026 | 15.7% | 25.3% | 14.6 | 8.0 | 15.4% | 11.1% | 4.1% | IND-C045; IND-C044 |
| FY2021–FY2026 | 13.4% | 17.1% | 12.6 | 3.2 | 15.3% | 12.1% | 3.0% | IND-C045; IND-C044 |

The ARPU × customers decomposition reconciles to reported revenue within ~1 pp a year (residual 0.2 pp/yr over FY2016–FY2026) [CALCULATION: IND-C044]. The TRAI-based decomposition overstates Airtel's FY2019–FY2026 share gain because the FY2019 base is IUC-depressed [CALCULATION: IND-C047]; FY2021–FY2026 (post-IUC) is the cleaner read: ~3 pp a year of share-driven growth on top of ~13% industry growth, the latter itself mostly two tariff rounds [INFERENCE: IND-C045; IND-C066]. No acquisition contributes materially to India mobile in these windows (the Tata consumer mobile and Telenor absorptions of 2018–2020 are inside FY2016–FY2021 subscriber counts [FACT: IND-C026]).

**Why share moved.** FY2016–FY2019 losses: Jio's free/near-free 4G offer and Airtel's deliberate exit from low-ARPU 2G customers (customers fell 7.1% in FY2019 while ARPU rose) [FACT: IND-C075]. FY2019 onward gains: Vodafone Idea's under-investment and balance-sheet distress (its revenue share fell from 27.3% to 11.3%) [CALCULATION: IND-C034], BSNL's decline, and Airtel's skew to postpaid/smartphone customers [INFERENCE].

**Other segments (company position, management-sourced):** home broadband 14.2 mn customers, +41.7% YoY [FACT: IND-C056] vs Jio fixed broadband 27.1 mn (~43% share) [FACT: IND-C062]; data centres ~12% share [MANAGEMENT STATEMENT: IND-C061]; DTH 16.0 mn customers, revenue -1% in FY2026 [FACT: IND-C055; IND-C077].

## 9. Pricing Mechanisms and Bargaining Power

**Conclusion.** Indian mobile pricing is set by the industry plan grid, which moves in coordinated rounds; individual operators have mix-driven pricing headroom (premiumisation) but not unilateral list-price power. Evidence of demand inelasticity is strong: each repair lifted ARPU ~14–16% with transient customer losses [CALCULATION: IND-C066; MANAGEMENT STATEMENT: IND-C052]. This is collective pricing power in a concentrated market, not cost pass-through (there was no input-cost shock behind any round) and not shortage pricing [JUDGMENT].

**Price vs volume evidence (Airtel India mobile):**

| Episode | ARPU before → after | Change | Volume response | Claim |
|---|---|---|---|---|
| Dec-2019 repair (Q3FY20→Q4FY20) | Rs 135 → 154 (IUC-inclusive) | +14.1% | Customers flat FY2020 (282.6 → 283.7 mn) | IND-C066; IND-C042 |
| Nov-2021 repair (Q2FY22→Q4FY22) | Rs 153 → 178 | +16.3% | Customers still grew (321.4 mn Mar-21; 335.4 mn Mar-23) | IND-C066; IND-C042 |
| Jul-2024 repair (Q1FY25→Q3FY25) | Rs 211 → 245 | +16.1% | 2.9 mn SIM-consolidation loss in Q2FY25, normalised in ~2 quarters; customers +2.7% Mar-24→Mar-25 | IND-C066; IND-C052 |
| No-hike year FY2024 | Rs 193 → 209 | +8.3% | Mix/premiumisation | IND-C066 |
| No-hike year FY2026 | Rs 245 → 257 | +4.9% | Mix/premiumisation; Q1FY2027 Rs 264 (extra day) | IND-C066; IND-C053 |

**Separating the sources of ARPU growth.** (a) *Genuine collective pricing power:* the three rounds; (b) *mix-driven ASP:* postpaid (>8% of base and record adds), feature-phone to smartphone conversion, international roaming [MANAGEMENT STATEMENT: IND-C053; IND-C050]; (c) *structural price decline per unit:* revenue per GB fell 10.6% in FY2026 [FACT: IND-C041], so pricing per unit of output is still deflationary, which is what management means by a broken "price architecture" [MANAGEMENT STATEMENT: IND-C049]. Management's own medium-term framing is 4–5% a year ARPU growth from architecture repair, without raising entry prices [MANAGEMENT STATEMENT: IND-C051].

**Relative pricing.** Airtel's Q4FY2026 ARPU (Rs 257) was 20% above Jio's (Rs 214.0) and 35% above Vi's (Rs 190) [FACT: IND-C062; IND-C063; MANAGEMENT STATEMENT: IND-C042]. Because list prices are near-identical across the three, the gap is customer mix [INFERENCE].

**Bargaining power summary.** Consumers: low individually, moderate collectively (political salience of tariffs). State: high (spectrum, fees) but currently supportive (reserve-price cuts, Vi relief) [FACT: IND-C065; IND-C063]. Tower companies: falling (sharing factor 1.64→1.62, rent per tower -2.9%) [FACT: IND-C057]. Enterprise customers: high in wholesale/connectivity (low-single-digit market growth, price pressure) [MANAGEMENT STATEMENT: IND-C073].

## 10. Cycle versus Structural Growth

**Conclusion.** Indian telecom has three overlapping cycles: (1) a *competitive-structure cycle* (fragmentation → price war → consolidation), which has run its course and now sits in a consolidated phase; (2) a *tariff-repair cycle* (step increases every 2–3 years: Dec-2019, Nov-2021, Jul-2024), now 27 months since the last round; (3) a *technology capex/spectrum cycle* (4G 2016–2019, 5G 2022–2025), now past peak in mobile capex but with a new auction recommended. Current position: **Mid-cycle** [JUDGMENT: IND-C046; IND-C049; IND-C055; IND-C065].

**Historical peak, trough and mid-cycle (industry).**

| Phase | Years | Industry access AGR (Q4, Rs cr) | Airtel AGR share | Airtel ARPU (Q4) | Claim |
|---|---|---|---|---|---|
| Fragmented growth (pre-Jio) | FY2013–FY2016 | 27,802 → 39,886 | 28.9% → 30.2% | Rs 196 (FY2014) → 194 (FY2016) | IND-C002; IND-C005; IND-C034; IND-C042 |
| Price war trough | FY2017–FY2019 | 25,448 (FY2018 low) | 22.7% (FY2019 low) | Rs 116 (FY2018 low) | IND-C007; IND-C034; IND-C042 |
| Repair and consolidation | FY2020–FY2026 | 34,496 → 72,488 | 28.2% → 39.7% | Rs 154 → 257 | IND-C009; IND-C015; IND-C034; IND-C042 |

**Structural vs cyclical vs share-driven vs one-off (FY2021–FY2026, post-IUC).** Industry AGR +13.4% a year, of which the bulk is tariff rounds (cyclical-structural: one-off step-ups that do not reverse) plus ~6% underlying wireless growth [MANAGEMENT STATEMENT: IND-C050]; Airtel share gain +3.2 pp/yr (share-driven, largely from Vi's decline) [CALCULATION: IND-C045]; subscriber volume +3% a year (structural but slowing) [CALCULATION: IND-C044]. One-offs: IUC abolition (Jan-2021) and the M2M definition change (2025-26) are reporting effects, not growth [CALCULATION: IND-C047; FACT: IND-C039].

**Evidence for "mid-cycle" rather than "peak".** Airtel mobile EBITDA margin is at a high (60.2%) [FACT: IND-C055] but management-reported India ROCE was only 11.2% in Q2FY2025 [MANAGEMENT STATEMENT: IND-C052], below a level that would signal over-earning; no capacity glut or new entrant threatens price; mobile capex is falling [FACT: IND-C055]. Evidence against: industry ARPU growth decelerated to 3.6% in FY2026 [FACT: IND-C038]; Vi is re-investing with fresh funding [FACT: IND-C063], which could revive share competition; the next tariff round is not announced [MANAGEMENT STATEMENT: IND-C049].

**Africa.** A volume/penetration growth phase (constant-currency revenue +24%, customers +10.5%) with a separate macro/FX cycle: FY2026 benefited from currency appreciation (reported +29.5% vs cc +24.0%; naira 1,529 → 1,386 per USD) after prior devaluation years [FACT: IND-C059; IND-C058].

## 11. Macro and Factor Sensitivities

**Conclusion.** The Indian business is weakly linked to GDP/credit cycles (non-discretionary demand) and strongly linked to regulatory and competitive variables; the consolidated group is materially exposed to African FX. First-order sensitivities on the FY2026 base (computed in `calc/industry_sensitivities.py`):

| Factor | Mechanism | Approximate sensitivity | Claim |
|---|---|---|---|
| India mobile tariff (industry round) | ~90% flow-through after licence fee/SUC | +10% tariff, no churn: +Rs ~10,200 cr EBITDA (+8.4% consolidated); with 2% subscriber loss: +6.5% | IND-C067 |
| African currencies vs reporting currency | Translation of Africa revenue/EBITDA | -10%: consolidated revenue -2.7%, EBITDA -2.3%; -25%: -6.7% / -5.8% | IND-C068 |
| INR vs USD | Import-linked network capex | -10% INR: capex +Rs 1,600–2,400 cr (1.9–2.9% of India ex-tower EBITDA) at 40–60% import content (assumed) | IND-C069 |
| Licence fee / regulatory levies | 8% of AGR licence fee | ±1 pp ≈ Rs 1,400 cr (1.7% of India ex-tower EBITDA) | IND-C069 |
| Spectrum prices | Auction reserve prices; deferred instalments | TRAI recommends lower reserve prices (directionally positive for future cost of capacity) | IND-C065 |
| Interest rates | Cost of deferred spectrum dues and debt | Not quantified here (financials/valuation own leverage); 2022 spectrum instalments resume from Aug-2026 | IND-C064 |
| GDP / rural income | Prepaid recharge affordability, smartphone upgrades | Low elasticity evidenced by repair rounds; not quantified | IND-C066 |
| Energy (diesel/grid power) | Tower operating costs (Indus) | Not quantified (Indus cost data not extracted); management targets diesel reduction | IND-C060 source context; see §17 |
| Device/memory prices | FWA CPE and handset upgrade cost | Hurt FWA economics in 2026 | IND-C061 |

These are static, first-order estimates; competitive response and pass-through are ignored [ESTIMATE: IND-C067; IND-C069].

## 12. Regulation, Technology and Disruption

**Conclusion.** Regulation has swung from hostile (2016–2020: IUC cuts, the AGR definition dispute) to supportive (2021 onward: reform package, cheaper spectrum, relief for Vi), and is now the main force *preserving* a three-player structure. Technology is primarily an opportunity for scaled incumbents (5G capacity, FWA, data centres, B2B digital) with satellite broadband the main new-entrant vector, credible only at the rural/edge margin on current evidence [JUDGMENT].

| Change vector | Direction for Airtel/industry economics | Magnitude | Timing | Evidence quality |
|---|---|---|---|---|
| Vodafone Idea AGR relief (dues frozen; payments capped at Rs 124 cr/yr Mar-2026–Mar-2031; reassessment) | Mixed: lowers price-war/exit risk, but keeps a third competitor alive and caps Airtel/Jio share gains from Vi's decline | Large for structure | Effective FY2026 | Low (press only) [FACT: IND-C063] |
| Spectrum auction (TRAI 24-Feb-2026: all bands incl. 600 MHz, lower reserve prices, 35% caps) | Positive for cost of capacity; lower caps limit hoarding | Moderate | DoT decision/auction date not found by cutoff | Medium [FACT: IND-C065] |
| 2022 spectrum instalments resuming from Aug-2026 | Cash outflow (quasi-debt) | Material for cash flow | FY2027 onward | High [FACT: IND-C064] |
| Lower 6 GHz delicensing (Jan-2026) | Mild substitute (Wi-Fi offload) and enabler for home broadband | Small | Now | Medium [FACT: IND-C074] |
| Satellite broadband (Starlink/OneWeb/Jio-SES) | New entrant at rural/premium edge; also partnership opportunity | Small near term | Spectrum assignment pending; launch dates have slipped repeatedly (press, not verified) | Low (no primary DoT order retrieved) [INFERENCE] |
| 5G and network slicing (Airtel "Fast Lane" postpaid) | Premiumisation lever; capex already sunk | Moderate | Now | Management statement [MANAGEMENT STATEMENT: IND-C053] |
| FWA (5G home broadband) | Expands homes TAM but low entry pricing and device costs strain economics | Moderate | Now | [MANAGEMENT STATEMENT: IND-C061; FACT: IND-C062] |
| Data centres / AI demand | New profit pool; Airtel ~12% share | Potentially large | Multi-year | [MANAGEMENT STATEMENT: IND-C061] |
| OTT substitution of SMS/voice | Ongoing erosion of messaging/wholesale | Small-moderate | Ongoing | [MANAGEMENT STATEMENT: IND-C073] |
| Jio Platforms listing | Market price discovery for the leader; possible pressure for Jio to show margins (supportive of rational pricing) | Indirect | RIL says steps toward listing taken | [FACT: IND-C062] |

Disruption timelines (satellite especially) are uncertain and are not presented as certain.

## 13. Competitor Benchmarking

**Conclusion.** On FY2026 operating metrics Airtel's mobile business has the highest ARPU and segment margin among Indian operators; Jio has the larger customer base, lower churn, faster revenue growth (whole-platform basis) and leads fixed broadband; Vi is sub-scale and dependent on state relief and fresh capital [CALCULATION: IND-C070; FACT: IND-C062; IND-C063].

**FY2026 snapshot (scopes differ; see notes):**

| Metric | Airtel India mobile | Jio Platforms | Vodafone Idea | BSNL |
|---|---|---|---|---|
| Revenue FY2026 | Rs 1,12,995 cr [FACT: IND-C043] | Rs 1,46,885 cr [FACT: IND-C062] | ~Rs 44,873 cr [FACT: IND-C063] | n/a |
| Revenue growth | +12.7% [CALCULATION: IND-C070] | +14.6% [FACT: IND-C062] | ~+3% [FACT: IND-C063] | n/a |
| EBITDA margin | 60.2% [FACT: IND-C055] | 51.9% [FACT: IND-C062] | ~42.3% [CALCULATION: IND-C070] | n/a |
| ARPU (Q4FY2026, Rs/month) | 257 [MANAGEMENT STATEMENT: IND-C042] | 214.0 [FACT: IND-C062] | 190 [FACT: IND-C063] | n/a |
| Customers (Q4FY2026) | 373.2 mn [FACT: IND-C054] | 524.4 mn [FACT: IND-C062] | 192.8 mn [FACT: IND-C063] | 92.9 mn wireless (TRAI) [FACT: IND-C032] |
| Monthly churn | 2.4% [FACT: IND-C054] | 1.7% [FACT: IND-C062] | n/a | n/a |
| Access AGR share Q4FY2026 | 39.7% | 44.8% | 11.3% | 2.9% [CALCULATION: IND-C034] |
| Share change FY2016→FY2026 | +9.5 pp | +44.8 pp | -29.1 pp | -6.0 pp [CALCULATION: IND-C070] |
| Fixed broadband | 14.2 mn homes [FACT: IND-C056] | 27.1 mn (~43% share) [FACT: IND-C062] | n/a | n/a |

Scope notes: Airtel figure is the Mobile Services India segment (management reporting); Jio is all of Jio Platforms (mobility, fixed broadband, enterprise, digital services), so its margin is not like-for-like; Vi figures are secondary-source and low confidence.

**10-year benchmark (revenue share, all operators, TRAI).** The share table in §8 is the 10-year competitor benchmark on revenue: Vodafone + Idea went from 40.4% (FY2016) to 11.3% (FY2026); BSNL from 8.9% to 2.9%; Jio from zero to 44.8%; Airtel from 30.2% to 39.7% [CALCULATION: IND-C034]. Ten-year margin and return histories for Jio and Vi were not retrieved (coverage exception in front matter).

**Why own Airtel's industry position rather than the strongest competitor's (industry-level evidence only)?** Airtel has the higher-ARPU customer mix and the higher mobile margin; Jio has scale, lower churn and fixed-broadband leadership. Whether that mix advantage is durable is the moat specialist's verdict; the industry evidence here is that both leaders have gained share from the same weakening third player [INFERENCE: IND-C034; IND-C070].

**Africa peers.** MTN, Vodacom and other African operators were not benchmarked from primary filings in this run (gap, §17). Airtel Africa's own FY2026 metrics: cc revenue +24%, EBITDA margin ~49%, churn 4.3%/month [FACT: IND-C058].

## 14. Sector KPI Dashboard

| KPI | Latest | Prior / trend | Source |
|---|---|---|---|
| Industry access AGR (quarter) | Rs 74,457 cr (Q1FY2027) | Rs 72,488 cr (Q4FY2026); total industry AGR +9.19% YoY in Q1FY2027 | IND-C016; IND-C015; IND-C077 |
| Industry AGR (year) | Rs 3,34,659 cr FY2026 | +10.44% | IND-C037 |
| Industry wireless ARPU (TRAI, monthly) | Rs 180.73 FY2026 | Rs 174.46 FY2025 (+3.6%, M2M-diluted) | IND-C038 |
| Airtel ARPU | Rs 264 (Q1FY2027) | Rs 257 (Q4FY2026); Rs 245 (Q4FY2025) | IND-C053; IND-C042 |
| Airtel AGR share | 40.0% (Q1FY2027) | 39.7% (Q4FY2026); 30.2% (FY2016) | IND-C034 |
| CR3 / HHI (access AGR) | 96.0% / 3,731 (Q1FY2027) | 95.8% / 3,719 (FY2026) | IND-C035 |
| Airtel subscriber share (TRAI, new basis) | 37.7% (Jun-2026) | 33.6% Mar-2025 (old basis) | IND-C036 |
| Airtel monthly churn | 2.4% (Q4FY2026) | 2.3% (Q4FY2025) | IND-C054 |
| Airtel data customers % | 80.1% | 77.8% a year earlier | IND-C054 |
| Data use per Airtel customer | 31.4 GB/month | 25.1 GB a year earlier | IND-C054 |
| Industry revenue per GB | Rs 8.02 | Rs 8.97 (-10.6%) | IND-C041 |
| Airtel India mobile EBITDA margin | 60.2% FY2026 | 57.8% FY2025 | IND-C055; IND-C077 |
| Airtel India capex (incl. towers) | Rs 39,654 cr FY2026 | +8% | IND-C055 |
| Indus sharing factor | 1.62 | 1.64 | IND-C057 |
| Airtel homes customers | 14.2 mn | +41.7% YoY | IND-C056 |
| Airtel Africa cc revenue growth / EBITDA margin | +24% / 49.0% FY2026 | — | IND-C058 |
| Airtel Africa customers / churn | 183.5 mn / 4.3% | +10.5% | IND-C058 |
| Tariff rounds | Dec-2019, Nov-2021, Jul-2024 | none since | IND-C048; IND-C049 |
| Spectrum | TRAI auction recommendation 24-Feb-2026; 2022 instalments from Aug-2026 | — | IND-C065; IND-C064 |

## 15. Four-Layer Evidence Crosswalk

### Layer 1 — Bedrock Compounder
- **Relevant evidence:** structure durability (CR3, HHI), rational pricing behaviour, industry long-run return profile, share trend of the company.
- **Supports:** concentration rose to CR3 95.8% / HHI ~3,700 [CALCULATION: IND-C035]; three synchronised repairs with inelastic demand [CALCULATION: IND-C066]; Airtel revenue share gained ~9.5 pp over ten years [CALCULATION: IND-C070]; high entry barriers (spectrum, network) [FACT: IND-C064]; regulator now supportive [FACT: IND-C065].
- **Weakens:** the industry destroyed value for a decade (2016–2019 price war; ROCE only 11.2% for Airtel India in Q2FY2025 even after repairs) [MANAGEMENT STATEMENT: IND-C052]; a structural deflation in price per GB (-10.6% in FY2026) [FACT: IND-C041]; pricing depends on collective behaviour and politics; capex is generational and lumpy; the state keeps a third player alive [FACT: IND-C063].
- **Domain implications:** the industry now has the structure that typically supports above-cost-of-capital returns, but that has been true for only ~5 years and has not been tested by a downturn or a new entrant.
- **Missing information:** 10-year industry ROCE series (all operators), peer ROCE; through-cycle returns sit with financials.
- **Plausibility effect:** Raises — the market structure has moved decisively toward a rational oligopoly, though the record of rational behaviour is short.

### Layer 2 — High-Growth Business
- **Relevant evidence:** penetration headroom, market expansion vs share gain, saturation timing.
- **Supports:** ARPU levers (postpaid >8% of base, ~20% non-data customers, 5G) [MANAGEMENT STATEMENT: IND-C053; FACT: IND-C054]; home broadband (Airtel homes +41.7%) [FACT: IND-C056]; Africa volume growth (+24% cc, tele-density ~45%) [FACT: IND-C058; MANAGEMENT STATEMENT: IND-C060]; data centres at ~12% share [MANAGEMENT STATEMENT: IND-C061].
- **Weakens:** India mobile subscribers are saturated (1,141.85 mn ex-M2M) [FACT: IND-C040]; underlying wireless market growth ~6% [MANAGEMENT STATEMENT: IND-C050]; ten-year Airtel India mobile revenue CAGR only 7.3% [CALCULATION: IND-C044]; share gains from Vi are now slowing as Vi stabilises [FACT: IND-C063].
- **Domain implications:** India mobile is a mature, mid-single-digit-plus-price-rounds market, not a high-growth one; high growth exists only in sub-segments (homes, DC, B2B digital, Africa).
- **Missing information:** reachable home-broadband market (households), DC market size from a named source, Africa country shares.
- **Plausibility effect:** Lowers — the core India mobile market is saturated in volume; high growth is confined to smaller segments and Africa.

### Layer 3 — Cyclical / Event-Driven Opportunity
- **Relevant evidence:** tariff and capex cycles, cycle position, regulatory events.
- **Supports:** tariff rounds are discrete events with large EBITDA impact (+10% tariff ≈ +8% consolidated EBITDA) [ESTIMATE: IND-C067]; 27 months since the last round with management calling for repair [MANAGEMENT STATEMENT: IND-C049]; spectrum auction and Vi relief are identifiable regulatory events [FACT: IND-C065; IND-C063]; Africa FX swings [CALCULATION: IND-C068].
- **Weakens:** cycle position is mid-cycle rather than trough; management itself suggests tariff hikes may be less frequent and growth more organic [MANAGEMENT STATEMENT: IND-C049; IND-C051]; consolidation trough is long past (FY2019).
- **Domain implications:** the event set (next tariff round, auction terms, Jio listing) can move earnings, but not from a depressed base.
- **Missing information:** timing/probability of the next tariff round (no primary signal), DoT auction decision.
- **Plausibility effect:** No change — catalysts exist but the industry is not at a cyclical trough.

### Layer 4 — Venture-Style / Optionality Bet
- **Relevant evidence:** emerging platforms (data centres, B2B digital/cloud, Airtel Money/fintech in Africa and India), adoption curves.
- **Supports:** DC 1 GW ambition from ~12% share [MANAGEMENT STATEMENT: IND-C061]; Airtel Money revenue US$1,355 mn (+28.4% cc) with a planned London listing [FACT: IND-C059; MANAGEMENT STATEMENT: IND-C060].
- **Weakens:** these options are small relative to the mobile core (B2B revenue fell 4% in FY2026) [FACT: IND-C055]; competition from hyperscalers and Jio in DC/cloud; satellite could compete at the edges.
- **Domain implications:** optionality exists but is embedded in a large, mature cash-generating business; the outcome distribution is not venture-shaped at group level.
- **Missing information:** DC market size and margin benchmarks; fintech economics.
- **Plausibility effect:** Insufficient evidence — options are identifiable but unquantified at industry level in this run.

## 16. Contradictions and Data Conflicts

| Conflict | Values | Likely cause | Resolution | Confidence |
|---|---|---|---|---|
| TRAI FY2015 Q4 table labelled "QE Dec-14 / QE Sep-14" | Grand total Rs 35,938.26 cr = Mar-15 access AGR in Table 3.2 | Stale column headers in TRAI report | Treated as Mar-15 (IND-C004, confidence M) | M |
| TRAI FY2010 table titled "Service Provider wise Gross Revenue" | Grand total equals access GR | Different metric (GR not AGR) | Kept, flagged as GR basis; excluded from AGR decompositions | M |
| Airtel subscriber jump Mar-25 → Mar-26 (391.0 → 481.5 mn TRAI) vs company 361.6 → 373.2 mn | ~90 mn difference | TRAI now includes Airtel M2M (and FWA) [FACT: IND-C039] | Use company KPI for mobile; TRAI new-basis share flagged | H |
| TRAI Bharti AGR vs Airtel reported mobile revenue (FY2019 ratio 0.57) | 4×Q4 AGR Rs 23,681 cr vs revenue Rs 41,554 cr | IUC and other pass-through deductions pre-2021; scope (Hexacom, fixed access) | AGR share used for trend; reported revenue for growth | M [CALCULATION: IND-C047] |
| Q4FY2022 Airtel mobile revenue | Rs 176,168 mn (FY2022 pack) vs Rs 175,261 mn (FY2023 pack comparative) | Restatement/reclassification | FY2022 annual figure from FY2022 pack used | M |
| Smartphone penetration in Africa | 52% (Airtel India call) vs 49.5% (Airtel Africa RNS) | Different definitions/dates | Report both [MANAGEMENT STATEMENT: IND-C060; FACT: IND-C059] | M |
| Vi AGR exceptional gain | Rs 55,622 / 57,491 / 58,116 cr across press reports | Different line items (gross vs net, quarter vs year) | Not used numerically; primary filing needed | L |
| Airtel ARPU FY2018 | 115.6 (KPI workbook) vs 116 (QR Q4FY19) | Rounding | 116 used | H |

## 17. Assumptions, Uncertainty and Missing Evidence

| # | Assumption | Why necessary | Supporting evidence | Plausible alternative | Effect if wrong | Confidence |
|---|---|---|---|---|---|---|
| 1 | Q4 access-AGR share is representative of the fiscal year | Annual operator AGR not extracted | Quarterly shares move slowly post-2021 | Seasonal/one-off quarter effects | ±1 pp on share levels | M |
| 2 | TRAI "Bharti" = Bharti group (Airtel + Hexacom) across years | Consistent series | FY2025 report restates Mar-24 "Bharti Group" = prior "Bharti Airtel" figure (IND-C013/C014) | Pre-2019 scope differences | Small level shifts | M |
| 3 | Licence fee 8% + SUC ~2% on incremental AGR | Tariff sensitivity | DoT licence terms (not retrieved this run) | SUC near zero on post-2022 spectrum | Sensitivity ±1–2% | M |
| 4 | 40–60% of India capex is import-linked | INR sensitivity | None disclosed | Lower with local manufacturing (PLI) | Halves/doubles the sensitivity | L |
| 5 | Vi stabilised by relief (three-player base case) | Structure conclusion | Press reports of DoT relief, funding, net adds | Vi relapse or merger | Share and pricing outlook | M |
| 6 | Mid-cycle classification | Cycle position | Margins high, ROCE modest, capex falling, no hike for 27 months | "Peak" if no further repair and Vi re-accelerates | Normalised earnings view | M |

**Missing evidence (sought, where, why unavailable, effect):**
- TRAI PIR FY2011 and FY2012: PDFs corrupt on TRAI server (Read/pdftotext both fail); fills from TRAI press releases not attempted; minor effect (the FY2010 and FY2013 points bracket the gap).
- Vodafone Idea primary results (FY2016–FY2026): BSE API HTTP 403; Vi IR URLs 404. Vi figures are low-confidence; peer 10-year margin history missing.
- Jio 10-year history (RIL segment data FY2017–FY2025): not retrieved; FY2026 only.
- Airtel Quarterly Reports Q4FY2012, Q4FY2013, Q4FY2014, Q4FY2017 and KPI files: SSL errors; ARPU history therefore starts FY2014.
- TRAI PR No.25 of 2026 (spectrum) and Airtel Africa FY2026 RNS: SSL failures; used Airtel's summary (tier 3) and WebFetch rendering (confidence M).
- DoT decision/date for the next auction, satellite spectrum assignment terms: not found by cutoff.
- Africa country-level market shares and peer (MTN, Vodacom) benchmarks: not retrieved; Africa structure analysis is thin.
- Indus Towers energy-cost and tenancy history beyond Mar-25/Mar-26: not extracted.
- Corpus defect noted: results file of 14-May-2024 carries a FY2023 headline but contains Q4FY2024 data (confirmed by contents; IND-C042 inputs).

## 18. Questions and Dependencies for the CIO

1. **Moat specialist:** Is Airtel's ARPU premium over Jio (Rs 257 vs 214) durable mix advantage or temporary? Industry evidence: IND-C042, IND-C062, IND-C066.
2. **Financials:** Through-cycle India ROCE and incremental returns; this report uses management's 11.2% (IND-C052) only as context. Spectrum instalments from Aug-2026 (IND-C064) and Vi-relief read-across to AGR dues for Airtel are financial/filings items.
3. **Filings / special-situations:** Confirm Vi AGR-relief terms from primary DoT/Vi filings (IND-C063 is tier 6) and whether any AGR reassessment applies to Airtel.
4. **Valuation:** Use the tariff sensitivity (IND-C067) and Africa FX sensitivity (IND-C068) in scenarios; consider the Jio Platforms listing (IND-C062) as a market reference for the peer.
5. **Bear-case:** Test a "no further repair + Vi re-investment" path (§10 evidence against mid-cycle) and satellite entry at the rural edge.

## 19. Domain Conclusion

1. **Economic engine:** a spectrum-gated, high-fixed-cost network business; revenue = subscribers × ARPU; ~90% incremental flow-through; returns set by industry pricing discipline [ESTIMATE: IND-C067; FACT: IND-C055].
2. **Profit pools:** concentrated in Jio and Airtel (84.5% of access AGR); the state takes a large levy share; tower rents are under mild pressure [CALCULATION: IND-C034; FACT: IND-C057; IND-C072].
3. **Reachable market:** ~Rs 2.9 lakh crore annualised access AGR; volume-saturated in India mobile; growth via ARPU, homes, B2B digital, DC and Africa [FACT: IND-C015; IND-C040].
4. **Share:** Airtel gained ~9.5 pp of revenue share in FY2016–FY2026 (trough 22.7% in FY2019, now ~40%) [CALCULATION: IND-C034]; growth ≈ two-thirds industry, one-third share [CALCULATION: IND-C045].
5. **Cycle:** consolidated structure, three tariff rounds, 5G capex past peak, auction pending: mid-cycle [JUDGMENT].
6. **Macro:** tariffs dominate (+10% ≈ +8% consolidated EBITDA); Africa FX second (-10% ≈ -2.3% EBITDA) [ESTIMATE: IND-C067; CALCULATION: IND-C068].
7. **Change vectors:** supportive regulation (auction terms, Vi relief) preserves three players; satellite and FWA are edge risks; DC/B2B digital are opportunities [FACT: IND-C065; IND-C063; MANAGEMENT STATEMENT: IND-C061].

**Industry scenarios (industry-level, not valuation):**
- *Bull:* one more repair round of ~15% within two years plus 4–5% organic ARPU drift; Vi remains sub-scale; industry access AGR growth ~12–14% a year for three years [ESTIMATE: IND-C066; IND-C051].
- *Base:* no headline round for another 12–24 months; ARPU drift ~5% plus ~2–3% connection growth; industry AGR growth ~7–9% [ESTIMATE: IND-C050; IND-C066].
- *Bear:* Vi re-investment and satellite/FWA competition trigger promotional pricing; ARPU flat; industry AGR growth 3–5% and margin pressure from spectrum instalments and capex [ESTIMATE: IND-C063; IND-C041].

**Formal classifications:**
- **Industry attractiveness:** Moderate (high concentration and rational pricing now, but a short record, regulatory dependence, deflationary unit pricing and lumpy capex).
- **Industry phase:** Growing (India mobile value growth mid-to-high single digit; volumes mature; Africa growing faster).
- **Cycle position:** Mid-cycle.
- **Company share trajectory (10-year):** Gaining (India mobile/access services revenue share, FY2016–FY2026; also wireless subscriber share on the pre-2026 basis).

## 20. Source Register

| ID | Title | Issuer | Date | URL or identifier | Retrieved | Tier |
|---|---|---|---|---|---|---|
| S1 | Indian Telecom Services Performance Indicators (Jan–Mar of FY2009, FY2010, FY2013–FY2026; Apr–Jun 2026) | TRAI | 2009–2026 | https://www.trai.gov.in/sites/default/files/ (paths listed in ledger rows IND-C001–IND-C033) | 2026-10-12 | 2 |
| S2 | Indian Telecom Services Yearly Performance Indicators 2025-26 | TRAI | 2026-10-05 | https://www.trai.gov.in/sites/default/files/2026-10/YIR_05102026.pdf | 2026-10-12 | 2 |
| S3 | Results and Quarterly Report Q4FY2026 | Bharti Airtel | 2026-05-13 | FilingForge:b5c6beda-7ade-4dd3-ad4f-bff5e5efe4c1 | 2026-10-12 | 1/3 |
| S4 | Results packs FY2019–FY2026 (segment notes, Quarterly Report trend tables) | Bharti Airtel | 2019–2026 | FilingForge results documents (see airtel_india_mobile_kpis.csv) | 2026-10-12 | 1/3 |
| S5 | Quarterly Reports Q4FY2015, Q4FY2016, Q4FY2019; KPI workbooks Q4FY2018, Q4FY2021, Q2FY2026 | Bharti Airtel | 2015–2025 | https://assets.airtel.in/static-assets/cms/investor/docs/... (URLs in source_retrievals.csv) | 2026-10-13 | 3 |
| S6 | Annual Reports FY2017, FY2018, FY2021, FY2022, FY2024, FY2025 | Bharti Airtel | 2017–2025 | FilingForge:AR-532454-2017; AR-532454-2018; 3e7fff81-d3bf-4662-8dd5-8c18db7db532; 1c7c2552-7d96-4a40-ae4b-afed2435fdcf; fa581014-8329-4051-a7b5-54eddb9ab932; ef981e1b-4d0f-478c-ae63-5e3f2ca4316f | 2026-10-12 | 1 |
| S7 | Earnings call transcripts Q2FY2025, Q3FY2026, Q1FY2027 | Bharti Airtel | 2024–2026 | FilingForge:9a7c6df2-bb49-4e60-95bc-89bbf247bfc8; bccb6f0b-0ac6-4ecc-ad71-c50ee10d52fe; a46861ad-47c4-4fb1-9001-f56835e1a897 | 2026-10-12 | 4 |
| S8 | RIL Media Release Q4 FY2025-26 | Reliance Industries | 2026-04-24 | https://www.ril.com/sites/default/files/2026-04/24042026_Media_Release_RIL_Q4_FY2025-26_Financial_and_Operational_Performance.pdf | 2026-10-13 | 3 |
| S9 | Airtel Africa plc FY2026 final results (RNS) | Airtel Africa plc | 2026-05 | https://data.fca.org.uk/artefacts/NSM/RNS/de128532-d4a4-4f3c-8221-d406e66ee8d0.html | 2026-10-14 | 1 (read via WebFetch) |
| S10 | Press reports on Vodafone Idea Q4FY26/Q1FY27 results and AGR relief | tele.net.in; Business Today; Outlook Business | 2026 | URLs in IND-C063 | 2026-10-14 | 6 |
| S11 | Calculations | industry specialist | 2026-10-13/14 | calc/industry_market_share.py; industry_growth_decomposition.py; industry_tariff_response.py; industry_sensitivities.py; industry_competitor_benchmark.py | — | — |
| S12 | Price snapshot | CIO | 2026-10-12 | CIO-C001 (NSE bhavcopy) | — | 1 |
