# Concalls research plan — BHARTIARTL run 20261012T132311Z

## Decision questions (agent definition)
1. Share of quantified commitments delivered / partly / delayed / missed / abandoned; variance.
2. Guidance bias by topic (ARPU/tariff, capex, 5G rollout, deleveraging, home broadband, enterprise, data centres, Africa).
3. Goalpost moves (timelines, definitions, metric switches).
4. Statements vs statutory disclosures.
5. Responses to misses: candid/specific; external vs execution.
6. Recurring analyst concerns and answer evolution.
7. Current guidance the CIO should trust least.

## Data series and depth
- Transcripts: corpus 14 (Q2FY2023-Q1FY2027 ex Q1FY2025, Q4FY2026). Fetch Q1FY2025, Q4FY2026 and as many pre-Q2FY2023 calls as exist on airtel.in IR (target back to ~Q1FY2019 => 30+ quarters).
- Annual reports FY2017-FY2025 (corpus): Chairman / MD letters for long-dated targets (ARPU, 4G/5G, deleveraging, Africa IPO, Indus merger).
- Outcomes: quarterly reports (IR KPI packs) and results filings: ARPU, capex, net debt, 5G coverage, homes broadband, data-centre MW, dividend.

## Sources
- airtel.in/about-bharti/equity/results (transcripts, quarterly reports)
- BSE/NSE filings for transcripts
- FilingForge corpus (transcripts tier 4, results tier 1, AR tier 1)

## Workflow
1. Coverage table (workpapers/coverage.csv)
2. Extract commitments per transcript -> promise_database.csv (append as read)
3. Outcomes from quarterly reports/results -> outcome locators
4. calc/concalls_stats.py -> delivery rates by topic & period
5. Write report section by section; validate.
