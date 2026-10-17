"""WACC sensitivity for the return-duration test (moat). Run: python3 calc/moat_sensitivity.py"""
import csv, os
D = os.path.dirname(os.path.abspath(__file__))
roce = {r["period"]: float(r["roce_pct_reported"]) for r in csv.DictReader(open(os.path.join(D, "moat_roce_reported.csv")))}
yrs10 = [f"FY{y}" for y in range(2017, 2027)]
with open(os.path.join(D, "moat_sensitivity.out"), "w") as fh:
    for w in (8, 9, 10, 11, 12, 13):
        h = w / (1 - 0.2517)
        line = f"wacc={w}% pretax_hurdle={h:.2f}% years_above_last10={sum(roce[y] > h for y in yrs10)} years={[y for y in yrs10 if roce[y] > h]}"
        print(line); fh.write(line + "\n")
