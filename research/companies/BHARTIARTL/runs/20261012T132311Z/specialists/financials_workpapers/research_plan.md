# Financials — Research Plan (BHARTIARTL, run 20261012T132311Z)

## Decision questions
1. Through-cycle ROCE/ROIC and incremental ROIC (3y/5y) on capital retained 2016–2026.
2. CFO/PAT and FCF/PAT (3/5/10-year cumulative); explain gaps (spectrum, leases, AGR, FX, minorities).
3. Normalized owner earnings vs. reported PAT (maintenance capex estimate, lease payments, spectrum instalments).
4. Worst years (FY2017–FY2020 Jio price war; AGR FY2020; naira devaluations FY2024) and today's balance-sheet resilience
   (net debt incl./excl. leases and deferred spectrum; maturities; guarantees; Africa debt).
5. Per-share capital allocation over 10+ years: rights issue 2021 (partly paid), QIP Jan-2020, FCCBs, Africa IPO, Indus merger, dividends.
6. Scaling economics, normalized vs current earnings, funding needs (crosswalk).

## Basis choice
- Primary basis: **consolidated (as reported)**, INR crore, shares in crore. This is the only basis with ≥15 years of consistent statements.
- Secondary: **segment:India** and **segment:Africa** from the segment note (revenue, EBITDA/EBIT, capex where disclosed),
  and standalone (Bharti Airtel Ltd) for the parent-level debt and guarantee picture.
- No captive lender is consolidated in a material way (Airtel Payments Bank is a subsidiary/JV — confirm; it is small);
  the lender profile is not applied unless APB is material. Indus Towers is consolidated from 19-Nov-2024: present FY2025/FY2026
  with and without Indus where disclosures allow.

## Years
- Target FY2011–FY2026 (16 years) consolidated. FY2011 = first full year with Zain Africa (acquired Jun-2010).
- Accounting breaks: Indian GAAP to FY2015/FY2016 (IFRS quarterly reports to FY2016); Ind AS from FY2017 (FY2016 restated comparatives);
  Ind AS 116 from FY2020 (EBITDA jumps; lease liabilities on BS); Indus Towers subsidiary from Q3FY2025 (gross-up);
  Ind AS 29 hyperinflation (Ethiopia? / Airtel Africa entities — confirm) ; Africa naira devaluations FY2024/FY2025.

## Expected anomaly years
- FY2017–FY2019: Jio entry; revenue/EBITDA decline; PAT collapse.
- FY2020: AGR Supreme Court judgment (Oct-2019) → large exceptional charge; QIP + FCCB raise; Ind AS 116 adoption.
- FY2021: AGR further charges; deferred tax; loss year? Rights issue announced Aug-2021 (FY2022).
- FY2022: Rights issue (₹21,000 crore, partly paid); Indus stake.
- FY2023: 5G spectrum auction (Aug-2022).
- FY2024: Naira devaluation (exceptional/FX losses).
- FY2025: Indus consolidation (remeasurement gain?), deferred spectrum prepayments.
- FY2026: latest year; partly paid conversion (Aug-2026 completed — FY2027 event).

## Sources (in order of preference)
1. Annual reports FY2017–FY2025 (corpus, tier 1): consolidated statements, segment note, borrowings, leases, EPS, exceptional items.
2. FY2026: Q4FY2026 audited results (corpus, tier 1) + FY2026 annual report from airtel.in (web).
3. FY2011–FY2016: annual reports from airtel.in / BSE (web), and the FY2017 AR's restated FY2016 comparatives.
4. Airtel quarterly reports (IR) for segment KPIs, net debt incl. leases, capex by segment.
5. Tier-5 aggregator (Screener) for the long tail cross-check only.

## Sector KPIs (SECTOR_PLAYBOOKS §16, §18)
EBITDA pre/post Ind AS 116; capex/revenue; net debt/EBITDA incl. leases; deferred spectrum & AGR liabilities; India mobile ARPU (context only — industry/concalls own KPIs);
Africa FX; minority leakage (Airtel Africa ~ 40% minority? Hexacom 30%, Indus ~50%); look-through earnings attributable.

## Scripts
- `scripts/fin_metrics.py` on `financial_history.csv` (consolidated) and a segment file.
- `calc/financials_stress.py` (stress test), `calc/financials_owner_earnings.py`, `calc/financials_cum.py` (cumulative sources/uses, cumulative conversion).
