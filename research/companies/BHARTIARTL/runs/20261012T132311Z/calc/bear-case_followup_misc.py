"""Stage-3 supporting arithmetic. Run: python3 calc/bear-case_followup_misc.py > calc/bear-case_followup_misc.out"""
SH = 6240.504481; PRICE = 1778.70
# 1. Crude incremental sales-to-capital FY2021-FY2026 from Screener (INR crore): equity capital + reserves + borrowings (incl. leases, DPL); excludes NCI
ic21 = 2746 + 56207 + 162785; ic26 = 3047 + 146010 + 195412
rev21, rev26 = 100616, 210973
print(f"Crude IC FY2021 {ic21:,} FY2026 {ic26:,}; dRev {rev26-rev21:,}; dIC {ic26-ic21:,}; incremental sales/capital {(rev26-rev21)/(ic26-ic21):.2f}")
print("  caveats: excludes NCI (rises with Indus consolidation -> ratio overstated); Indus revenue is inorganic; FX on Africa")
# 2. ICIL swap price vs current price (BEAR-C013 in the initial ledger; re-recorded as BEAR-C100)
print(f"ICIL swap price 1,923 vs 1,778.70: {1923/PRICE-1:+.1%}")
# 3. Tax assets per share (Q4FY2026 Quarterly Report balance sheet)
print(f"Income & deferred tax assets 211,594 mn = INR {211594/SH:.1f}/share; net of DTL 67,789 = INR {(211594-67789)/SH:.1f}/share")
print(f"FY2026 effective tax rate {113499/451727:.1%}; cash tax paid / P&L tax {62839/113499:.0%}")
# 4. Q1FY2027 YoY growth (Q1FY2027 results p.2-3, INR mn)
for name, a, b in (("Revenue", 585391, 494626), ("Mobile India", 299289, 273966), ("Africa", 175657, 120834), ("Homes", 22875, 17179), ("Airtel Business", 56654, 50571), ("Passive infra", 85254, 80913)):
    print(f"Q1FY27 YoY {name}: {a/b-1:+.1%}")
print(f"Q1FY27 EBITDA ex other income (342,094-9,066) vs Q1FY26 (283,475-5,088): {(342094-9066)/(283475-5088)-1:+.1%}")
# 5. Draft DCF EV vs TTM EBITDA
print(f"Draft base DCF EV 10,242,005 / approx TTM EBITDA 1,264,036 = {10242005/1264036:.2f}x")
# 6. Draft base DCF: implied year-1 incremental return on reinvestment (calc/valuation_dcf.json; TTM EBIT margin 32.6%, tax 27%)
import json
d = json.load(open("calc/valuation_dcf.json")); r1 = d["rows"][0]
nopat0 = 2200493 * 0.326 * (1 - 0.27)
print(f"Draft base year-1 dNOPAT/reinvestment: ({r1['nopat']:,.0f} - {nopat0:,.0f}) / {r1['reinvestment']:,.0f} = {(r1['nopat']-nopat0)/r1['reinvestment']:.0%}")
# 7. Bond-yield-plus-premium cross-check of Ke: pre-tax Kd 8.0% (calc/valuation_wacc_inputs.json) + 3-4% premium
print("Bond-yield-plus-premium Ke range: %.1f%% to %.1f%%" % (8.0 + 3.0, 8.0 + 4.0))
