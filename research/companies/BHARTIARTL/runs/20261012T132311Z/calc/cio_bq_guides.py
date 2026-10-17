"""CIO: quantitative-guide inputs for BQ1, BQ4, BQ5 (methodology/SCORING.md §2) from the audited financials metrics."""
import csv, os, statistics
base = os.path.dirname(__file__)
m = {}
for r in csv.DictReader(open(os.path.join(base, "financials_metrics.csv"), encoding="utf-8")):
    k = r.get("metric") or r.get("item")
    try:
        m[(k, r["period"])] = float(r["value"])
    except (TypeError, ValueError):
        pass
WACC = 0.110294  # CIO-C052 / VAL-C027
yrs = ["FY%d" % y for y in range(2017, 2027)]
roic = [m.get(("roic", y)) for y in yrs]
print("roic_reported_tax FY2017-26:", [None if v is None else round(v, 4) for v in roic])
vals = [v for v in roic if v is not None]
med = statistics.median(vals)
print("median_roic_10y=%.4f spread_vs_wacc_pp=%.2f" % (med, (med - WACC) * 100))
# constant-tax ROIC series published by financials (FIN-C024) for comparison
const = {"FY2017": .067, "FY2018": .045, "FY2019": .018, "FY2020": .032, "FY2021": .053, "FY2022": .075, "FY2023": .091, "FY2024": .091, "FY2025": .106, "FY2026": .139}
cm = statistics.median(const.values())
print("median_roic_const_tax_10y=%.4f spread_pp=%.2f" % (cm, (cm - WACC) * 100))
print("years_roic_const_tax_above_wacc=%d of 10" % sum(1 for v in const.values() if v > WACC))
fcf = [m.get(("fcf", y)) for y in yrs]
print("fcf FY2017-26:", fcf, "positive_years=%d" % sum(1 for v in fcf if v is not None and v > 0))
cfo = sum(m.get(("cfo", y), 0) for y in yrs); pat = sum(m.get(("pat", y), 0) for y in yrs)
print("cfo_to_pat_10y_cum=%.2f" % (cfo / pat if pat else float('nan')))
print("net_debt_to_ebitda_FY2026=%.3f interest_coverage_FY2026=%.2f interest_coverage_FY2019=%.2f" % (m.get(("net_debt_to_ebitda","FY2026")), m.get(("interest_coverage","FY2026"), float('nan')), m.get(("interest_coverage","FY2019"), float('nan'))))
