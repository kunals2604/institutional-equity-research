#!/usr/bin/env python3
"""Render markdown tables for the financials report from financial_history.csv, financials_metrics.csv
and financials_side_items.csv (no new arithmetic beyond simple ratios shown with their formula).
Run: python3 calc/financials_tables.py > calc/financials_tables.md"""
import csv
from pathlib import Path

RUN = Path(__file__).resolve().parent.parent
H, M, S = {}, {}, {}
for r in csv.DictReader(open(RUN / "specialists/financials_workpapers/financial_history.csv")):
    H[(r["item"], r["period"])] = float(r["value"])
for r in csv.DictReader(open(RUN / "calc/financials_metrics.csv")):
    M[(r["metric"], r["period"])] = float(r["value"])
for r in csv.DictReader(open(RUN / "calc/financials_side_items.csv")):
    S[r["period"]] = {k: float(v) for k, v in r.items() if k != "period" and v != ""}
T = 0.2517


def table(years, rows):
    print("| Item | " + " | ".join(years) + " |")
    print("|---|" + "---|" * len(years))
    for label, fn in rows:
        vals = []
        for y in years:
            try:
                v = fn(y)
            except (KeyError, TypeError, ZeroDivisionError):
                v = None
            vals.append(v if isinstance(v, str) else ("-" if v is None else v))
        print("| " + label + " | " + " | ".join(str(v) for v in vals) + " |")
    print()


def c(x):
    return "{:,.0f}".format(x) if x is not None else None


def p(x):
    return "{:.1f}%".format(x * 100) if x is not None else None


def ic(y):
    return H[("total_equity", y)] + H[("minority_interest_bs", y)] + H[("total_debt", y)] + H[("lease_liabilities", y)] - H[("cash_and_equivalents", y)] - H[("current_investments", y)]


YRS = ["FY%d" % y for y in range(2011, 2027)]
eq_fcf = lambda y: H[("cfo", y)] - H[("capex", y)] - S[y]["spectrum_paid"] - S[y]["lease_paid"] - S[y]["interest_paid"]  # noqa: E731
rows = [
    ("Revenue", lambda y: c(H[("revenue", y)])),
    ("Revenue growth", lambda y: p(M.get(("revenue_growth", y)))),
    ("EBITDA (excl. other income)", lambda y: c(H[("ebitda", y)])),
    ("EBITDA margin", lambda y: p(M[("ebitda_margin", y)])),
    ("Depreciation & amortisation", lambda y: c(H[("depreciation", y)])),
    ("EBIT", lambda y: c(M[("ebit", y)])),
    ("Other income (net)", lambda y: c(H[("other_income", y)])),
    ("Finance costs", lambda y: c(H[("interest_expense", y)])),
    ("Exceptional items (gain +)", lambda y: c(H[("exceptional_items", y)])),
    ("PBT", lambda y: c(H[("pbt", y)])),
    ("PAT (incl. NCI)", lambda y: c(H[("pat", y)])),
    ("PAT attributable", lambda y: c(H[("pat_attributable", y)])),
    ("EPS basic, rights-adjusted (INR)", lambda y: "{:.2f}".format(M[("eps", y)])),
    ("CFO", lambda y: c(H[("cfo", y)])),
    ("Capex ex-spectrum", lambda y: c(H[("capex", y)])),
    ("Spectrum cash paid", lambda y: c(S[y]["spectrum_paid"])),
    ("Lease principal paid", lambda y: c(S[y]["lease_paid"])),
    ("Interest paid", lambda y: c(S[y]["interest_paid"])),
    ("FCF (CFO - capex)", lambda y: c(M[("fcf", y)])),
    ("Equity FCF (after spectrum, leases, interest)", lambda y: c(eq_fcf(y))),
    ("Equity attributable", lambda y: c(H[("total_equity", y)])),
    ("Non-controlling interests", lambda y: c(H[("minority_interest_bs", y)])),
    ("Borrowings incl. DoT deferred liabilities", lambda y: c(H[("total_debt", y)])),
    ("Lease liabilities", lambda y: c(H[("lease_liabilities", y)])),
    ("Net debt (excl. leases)", lambda y: c(M[("net_debt", y)])),
    ("Net debt / EBITDA (x)", lambda y: "{:.2f}".format(M[("net_debt_to_ebitda", y)])),
    ("EBIT / finance costs (x)", lambda y: "{:.2f}".format(M[("interest_coverage", y)])),
    ("ROCE (pre-tax)", lambda y: p(M[("roce", y)])),
    ("ROIC at 25.17% tax", lambda y: p((M[("ebit", y)]) * (1 - T) / ((ic(y) + ic("FY%d" % (int(y[2:]) - 1))) / 2))),
    ("ROE", lambda y: p(M[("roe", y)])),
    ("Year-end shares, rights-adj. (crore)", lambda y: "{:.1f}".format(H[("shares_diluted", y)])),
]
print("### Table 1 — Consolidated summary, INR crore (FY2011-FY2015 IFRS from Q4 Quarterly Reports; FY2016-FY2026 Ind AS audited statements)\n")
table(YRS, rows)
