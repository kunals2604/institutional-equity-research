#!/usr/bin/env python3
"""Quarterly trend table (INR crore) from specialists/financials_workpapers/quarterly_inr_mn.csv."""
import csv
from pathlib import Path
RUN = Path(__file__).resolve().parent.parent
Q = list(csv.DictReader(open(RUN / "specialists/financials_workpapers/quarterly_inr_mn.csv")))
idx = {r["quarter"]: r for r in Q}
print("| Quarter | Revenue | YoY | EBITDA (excl. OI) | EBITDA margin | Exceptional (gain +) | PAT | PAT attributable |")
print("|---|---|---|---|---|---|---|---|")
for r in Q:
    q = r["quarter"]; prev = "Q%sFY%d" % (q[1], int(q[4:]) - 1)
    rev = float(r["revenue"]); e = rev - float(r["opex"])
    yoy = "%.1f%%" % ((rev / float(idx[prev]["revenue"]) - 1) * 100) if prev in idx else "-"
    print("| %s | %s | %s | %s | %.1f%% | %s | %s | %s |" % (q, "{:,.0f}".format(rev / 10), yoy, "{:,.0f}".format(e / 10), e / rev * 100,
          "{:,.0f}".format(float(r["exceptional_gain"]) / 10), "{:,.0f}".format(float(r["pat"]) / 10), "{:,.0f}".format(float(r["pat_attributable"]) / 10)))
