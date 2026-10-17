"""Remuneration vs performance (indicative). Inputs: specialists/management_workpapers/remuneration_series.csv,
net income MGT-C038/C039, EPS MGT-C062. Run: python3 calc/management_remuneration.py"""
import csv, os
here = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(here, "..", "specialists", "management_workpapers", "remuneration_series.csv"))))
ni = {"FY2017":3799.7,"FY2018":1099.0,"FY2019":409.5,"FY2020":-32183.2,"FY2021":-15083.5,"FY2022":4254.9,"FY2023":8345.9,"FY2024":7467.0,"FY2025":33556.1,"FY2026":26695.2}  # Rs crore
def get(fy, person):
    for r in rows:
        if r["fiscal_year"] == fy and r["person"] == person: return r
for fy in ["FY2017","FY2019","FY2021","FY2023","FY2024","FY2025","FY2026"]:
    c = get(fy, "Sunil Bharti Mittal"); v = get(fy, "Gopal Vittal")
    cp = float(c["remuneration_inr"])/1e7; vp = float(v["remuneration_inr"])/1e7
    ve = float(v["esop_perquisite_excluded_inr"] or 0)/1e7
    pct = (cp+vp)/ni[fy]*100 if ni[fy] > 0 else float("nan")
    print(f"{fy}: Chairman Rs {cp:.2f} cr; MD/EVC Rs {vp:.2f} cr (+ESOP perquisite Rs {ve:.2f} cr); two exec directors as % of consolidated net income: {pct:.2f}%")
v17 = float(get("FY2017","Gopal Vittal")["remuneration_inr"]); v26 = float(get("FY2026","Gopal Vittal")["remuneration_inr"])
print(f"Vittal cash remuneration CAGR FY2017-FY2026 (9y): {((v26/v17)**(1/9)-1):.1%}")
eps17, eps26 = 9.51, 46.0
print(f"Reported basic EPS CAGR FY2017-FY2026 (9y, bases differ: FY2026 restated for Indus): {((eps26/eps17)**(1/9)-1):.1%}")
esop = sum(float(r["esop_perquisite_excluded_inr"] or 0) for r in rows if r["person"]=="Gopal Vittal")/1e7
print(f"Vittal ESOP exercise perquisites FY2017-FY2026 total Rs {esop:.1f} cr")
# --- executive holdings and block-deal implied prices (MGT-C008, CIO-C001, MGT-C051)
print(f"Vittal holding value at Rs1,778.70: Rs {1_184_348*1778.70/1e7:.1f} cr")
print(f"ICIL Feb-2025 implied average price: Rs {8485.11e7/51.1e6:,.0f}")
print(f"Mar-2020 promoter % = BTL 38.79 + foreign promoters 20.19 = {38.79+20.19:.2f}")
