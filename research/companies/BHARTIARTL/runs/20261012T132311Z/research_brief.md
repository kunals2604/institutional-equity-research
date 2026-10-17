# Research Brief — Bharti Airtel Limited (BHARTIARTL)

Run: `20261012T132311Z` · Created: 2026-10-12T13:23:11+00:00 · Research cutoff: **2026-10-12**

> Factual starting point for every specialist. **No investment hypotheses, layer guesses or conclusions belong here.**

## Identity
| Field | Value | Claim |
|---|---|---|
| Legal name | Bharti Airtel Limited | CIO-C005 |
| Ticker / exchange | BHARTIARTL / NSE (series EQ); BSE scrip 532454 | CIO-C005, CIO-C006 |
| Listing segment | Main board | CIO-C005 |
| ISIN | INE397D01024 (fully paid). Residual partly-paid line: AIRTELPP, ISIN IN9397D01014, BSE 890157 | CIO-C005, CIO-C004, CIO-C006 |
| CIN | L74899HR1995PLC095967 | CIO-C006 |
| Reporting currency | INR | |
| Fiscal year end | 31 March (FY2026 = year ending 31-Mar-2026) | |
| Listing date | Not verified in preflight. Listed on NSE/BSE since at least the early 2000s; financial history for ≥10 years exists. The specialist that needs it (valuation) should confirm it. | — |

Identity check: the NSE ticker, ISIN and legal name identify the same security, and on 12-Oct-2026 BHARTIARTL EQ was the only Airtel equity series that traded on NSE [CIO-C005].

## Price snapshot
- `CIO-C001`: price = **INR 1,778.70**, NSE close on 12-Oct-2026 (NSE CM bhavcopy; tier 1). Yahoo Finance's last print (15:29:33 IST) agrees.
- `CIO-C002`: fully paid shares outstanding = **6,240,504,481** (company filing, 24-Jul-2026). `CIO-C004`: **649,835** partly paid shares remain (₹1.25 paid of ₹5; call of ₹401.25 per share unpaid). `CIO-C008`: the conversion completed on 18-Aug-2026, but corporate actions failed for 493 shares.
- `CIO-C003`: market cap = CIO-C001 × CIO-C002 = **about ₹11,09,999 crore** (₹11.10 lakh crore). The partly paid shares add about ₹90 crore of economic value, which is immaterial.
- `CIO-C009`: 12-Oct-2026 NSE turnover was ₹854.30 crore (one day only; valuation owns the 90-day ADTV).
- Share-count caveat: allotments after 24-Jul-2026 (ESOP or other) were not checked in preflight. Valuation reconciles them to the Sep-2026 shareholding pattern and the latest diluted count (any outstanding convertibles or ESOP overhang).

## Conventions for this run
- **Units:** ₹ crore unless stated. Airtel's quarterly reports often present ₹ million, so convert explicitly (₹1 crore = ₹10 million). Airtel Africa reports in US$; record the FX rate and date for every conversion.
- **Consolidated vs. standalone (known basis issues):**
  - **Indus Towers** has been a **subsidiary since close of business on 18-Nov-2024** [CIO-C007]. Before that it was a joint venture or associate. Consolidated revenue, EBITDA, debt and lease figures therefore **break at Q3FY2025**. State whether every series is reported as filed or adjusted for comparability, and treat the inter-company tower rentals that are now eliminated explicitly.
  - **Airtel Africa plc**, a listed subsidiary (London Stock Exchange and Nigerian Exchange), is consolidated. Its FX translation, currency devaluations (notably the Nigerian naira) and hyperinflation accounting can dominate consolidated reported profit. Analyze India, Africa and the other segments separately using the segment note and quarterly reports.
  - **Bharti Hexacom Limited**, a listed subsidiary (NSE/BSE), serves part of the Indian market (Rajasthan and the North East circles) and sits inside the India figures.
  - Other group entities named in the FY2025 annual report: Nxtra Data (data centres; a stake transfer is mentioned), Airtel Payments Bank, Beetel Teletech, and the DTH and enterprise businesses. Their scope and accounting treatment must be confirmed from the FY2025 and FY2026 subsidiary notes and AOC-1.
  - **Telecom basis traps** (sector playbook §16): EBITDA before and after Ind AS 116; deferred spectrum liabilities and AGR dues as quasi-debt; capitalized spectrum and its amortization; net debt including and excluding leases; any conversion of government dues to equity.
- **Group structure leads:** promoter Bharti Telecom Limited (BTL), which itself is held by the Mittal family entities and Singtel. Verify every holding and percentage from the shareholding pattern and annual reports.
- **Sector playbooks:** `methodology/SECTOR_PLAYBOOKS.md` **§16 Telecom and media** (primary). **§18 Holding companies and conglomerates** applies to the listed-subsidiary structure (Airtel Africa, Indus Towers, Bharti Hexacom) and any SOTP. **§15 (energy and utilities)** offers a useful analogue for tower infrastructure economics.
- **SME enhanced-scrutiny mode:** OFF (main board).
- **Investment policy** (`config/investment_policy.json`): **CONFIRMED by the owner**. Hurdle = this run's cited cost of equity (valuation computes it with `valuation_tools.py wacc`). Horizon 5 years. Benchmark Nifty 500 TRI. Reference position for the exit-liquidity test ₹50,00,000. No position or risk limits.
- **Historical depth required** (`methodology/RESEARCH_PLAYBOOK.md` §2): at least 10 fiscal years of financials, 12 quarters of calls and results, and 10 years of valuation and industry history. Use more where available. Telecom tariff and capex cycles (2016 market entry and price war, 2019 tariff repair, 4G and 5G capex) call for **15+ years** where obtainable.

## Local filing corpus (FilingForge) and its gaps
The catalog is at `RUN_DIR/corpus/CATALOG.md`: 79 documents, 78 core. It is **one of two channels at par with full web research, never a limit** (`methodology/SOURCE_GUIDE.md` §0).

| Series | In corpus | Known gaps to fill from the web |
|---|---|---|
| Annual reports | FY2017–FY2025 (9 years) | **FY2026 annual report missing (the latest completed year; critical).** FY2016 and earlier missing (needed for ≥10-year and 15-year history). |
| Quarterly results | 30 quarters, Q3FY2019–Q1FY2027 | **Q2FY2026 (Oct/Nov 2025) missing.** Possible label glitch: the 14-May-2024 "Q4FY2024" results carry a headline saying "year ended March 31, 2023"; confirm the period in the document. |
| Earnings-call transcripts | 14 quarters, Q2FY2023–Q1FY2027 | **Q1FY2025 and Q4FY2026 missing.** Everything before Q2FY2023 is missing (needed for 20–40 quarters of promise tracking). |
| Investor presentations / quarterly reports | 2 only | Airtel publishes a detailed **Quarterly Report** (KPIs: ARPU, subscribers, churn, data usage, capex, segment results) on the IR site each quarter. Almost all are missing from the corpus. |
| Shareholding, SAST, PIT, credit ratings, orders | Not in corpus | All from the web. |

## User notes
_none_
