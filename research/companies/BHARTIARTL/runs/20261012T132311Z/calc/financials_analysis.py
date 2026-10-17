#!/usr/bin/env python3
"""Supplementary deterministic calculations for the financials report (INR crore unless stated).
Inputs: financial_history.csv (built by financials_build_history.py), financials_side_items.csv,
segment_history_inr_mn.csv, plus the cited note-level inputs typed below (INR million).
Run: python3 calc/financials_analysis.py > calc/financials_analysis.out"""
import csv
from pathlib import Path

RUN = Path(__file__).resolve().parent.parent
H = {}
for r in csv.DictReader(open(RUN / "specialists/financials_workpapers/financial_history.csv")):
    H[(r["item"], r["period"])] = float(r["value"])
S = {}
for r in csv.DictReader(open(RUN / "calc/financials_side_items.csv")):
    S[r["period"]] = {k: float(v) for k, v in r.items() if k != "period" and v != ""}
YRS = ["FY%d" % y for y in range(2011, 2027)]


def h(item, y):
    return H.get((item, y))


def fmt(x, d=1):
    return "-" if x is None else ("{:,.%df}" % d).format(x)


print("=== A. Annual cash conversion (INR crore) ===")
print("FY | PAT | PAT_attr | CFO | capex(ex-spectrum) | spectrum | lease principal | interest paid | FCF=CFO-capex | FCF after spectrum+leases | equity FCF (after interest)")
ann = {}
for y in YRS:
    pat, pa, cfo, cx = h("pat", y), h("pat_attributable", y), h("cfo", y), h("capex", y)
    sp, lp, ip = S[y].get("spectrum_paid", 0), S[y].get("lease_paid", 0), S[y].get("interest_paid", 0)
    fcf = cfo - cx
    fcf2 = fcf - sp - lp
    efcf = fcf2 - ip
    ann[y] = dict(pat=pat, pa=pa, cfo=cfo, capex=cx, sp=sp, lp=lp, ip=ip, fcf=fcf, fcf2=fcf2, efcf=efcf)
    print(y, *[fmt(v) for v in (pat, pa, cfo, cx, sp, lp, ip, fcf, fcf2, efcf)], sep=" | ")

print("\n=== B. Cumulative conversion windows ending FY2026 ===")
for n in (3, 5, 10, 15):
    ys = YRS[-n:]
    sm = lambda k: sum(ann[y][k] for y in ys)  # noqa: E731
    print("%2dy (%s-%s): sumPAT %s sumPAT_attr %s sumCFO %s | CFO/PAT %.2f | FCF/PAT %.2f | FCF after spectrum+leases/PAT %.2f | equity FCF/PAT %.2f | equity FCF/PAT_attr %.2f"
          % (n, ys[0], ys[-1], fmt(sm("pat")), fmt(sm("pa")), fmt(sm("cfo")), sm("cfo") / sm("pat"), sm("fcf") / sm("pat"),
             sm("fcf2") / sm("pat"), sm("efcf") / sm("pat"), sm("efcf") / sm("pa")))

print("\n=== C. Underlying (pre-exceptional, ex one-off tax) profit attributable, INR crore ===")
# one-offs from the exceptional-items notes (INR mn): (pre-tax exceptional, one-off tax effect (+ = credit), NCI share of one-offs (+ = NCI benefit))
ONE = {
    "FY2019": (29288, -9986, -579),    # AR FY2020 note 31: tax net charge 9,579 + 407; NCI charge 579
    "FY2020": (-402344, 114221, -7032),  # AR FY2020 note 31: tax net benefit 114,221; NCI charge 7,032
    "FY2021": (-159145 + 94496, -73502, 1117),  # AR FY2021/22: continuing exceptional + Infratel deemed-disposal gain (discontinued); tax net charge 73,502; NCI benefit 1,117
    "FY2022": (16986, -1033, 8681),    # AR FY2022 note 31
    "FY2023": (-6698, 14825, 6222),    # AR FY2024 note 32
    "FY2024": (-75723, 554 + 18760 + 690 - 2263, -19598),  # AR FY2024 note 32
    "FY2025": (72868, -9125 + 3840 + 4380 - 323 + 2068 + 85732, -392),  # AR FY2026 note 32 (incl. DTA recognition 85,732)
    "FY2026": (-34175, 650 + 1402 - 1377 + 487 + 30952, 30),  # AR FY2026 note 32 (incl. DTL reversal 30,952)
}
adj = {}
for y, (ex, tx, nci) in ONE.items():
    tot = ex + tx
    attr = tot - nci
    pa_mn = h("pat_attributable", y) * 10
    adj[y] = (pa_mn - attr) / 10.0
    sb = h("shares_basic", y)
    print("%s: reported PAT_attr %s | one-offs total %s, attributable %s | underlying PAT_attr %s | underlying EPS (adj. basic shares %.2f cr) %s"
          % (y, fmt(pa_mn / 10), fmt(tot / 10), fmt(attr / 10), fmt(adj[y]), sb, fmt(adj[y] / sb, 2)))

print("\n=== D. Owner earnings FY2026 (INR crore) ===")
cfo, wc = 1222296, (-5654 + 24977 - 1982 + 18276 + 33760 + 2665)   # AR FY2026 CF, changes in assets & liabilities
lease, intp = 67197, 148876
ppe_dep, rou_dep, amort = 312347, 98331, 116430   # AR FY2026 note 29
share_attr = 266952 / 338228
for label, mc, spn, sh in (("low", 400000, 140000, 0.75), ("base", ppe_dep, amort, share_attr), ("high", 250000, 90000, 0.80)):
    firm = cfo - wc - lease - intp - mc - spn
    print("%s: CFO %s - WC release %s - lease principal %s - interest paid %s - maintenance capex %s - normalised spectrum %s = firm OE %s; x owners' share %.3f = owner earnings %s"
          % (label, fmt(cfo / 10), fmt(wc / 10), fmt(lease / 10), fmt(intp / 10), fmt(mc / 10), fmt(spn / 10), fmt(firm / 10), sh, fmt(firm * sh / 10)))
print("reconciliation: equity FCF FY2026 (CFO - capex - spectrum - leases - interest) = %s; difference vs base firm OE arises from growth capex (cash capex %s vs maintenance %s), WC release and spectrum cash timing"
      % (fmt(ann["FY2026"]["efcf"]), fmt(ann["FY2026"]["capex"]), fmt(ppe_dep / 10)))
print("maintenance capex cross-check: base %.1f%% of FY2026 revenue; range 250,000-400,000 mn = %.1f%%-%.1f%% of revenue"
      % (ppe_dep / 2109728 * 100, 250000 / 2109728 * 100, 400000 / 2109728 * 100))

print("\n=== E. Debt variants at 31-Mar (INR crore) ===")
for y, bor, dpl, lease_l, cash, ci, obb, mm, agr_prov, agr_ind, ebitda, lease_int, lease_pr in (
        ("FY2026", 1216714, 906430, 737403, 137222, 137006, 166546, 132061, 347042, 166725 + 24886, 1196745, 67505, 67197),
        ("FY2025", 1483123, 923980, 653298, 61056, 16532, 106143, 81480, 352108, 195029 + 28757, 931592, 61117, 71538)):
    nd = bor - cash - ci
    print("%s: borrowings %s (of which DoT deferred payment liabilities %s) | net debt (excl. leases) %s | + other bank balances net of mobile-money trust %s -> %s | incl. leases %s | net financial debt ex-DPL %s | + non-indemnified AGR provision %s -> quasi-debt total incl. leases %s"
          % (y, fmt(bor / 10), fmt(dpl / 10), fmt(nd / 10), fmt((obb - mm) / 10), fmt((nd - (obb - mm)) / 10), fmt((nd + lease_l) / 10),
             fmt((nd - dpl) / 10), fmt((agr_prov - agr_ind) / 10), fmt((nd + lease_l + agr_prov - agr_ind) / 10)))
    pre_lease = ebitda - lease_int - lease_pr
    print("   EBITDA (post-116) %s; pre-lease EBITDA proxy (EBITDA - lease interest - lease principal) %s; net debt/EBITDA %.2fx; (net debt+leases)/EBITDA %.2fx; net debt/pre-lease EBITDA %.2fx; (net debt + leases + AGR prov)/EBITDA %.2fx"
          % (fmt(ebitda / 10), fmt(pre_lease / 10), nd / ebitda, (nd + lease_l) / ebitda, nd / pre_lease, (nd + lease_l + agr_prov - agr_ind) / ebitda))

print("\n=== F. Resilience stress test on FY2026 base (INR crore) ===")
rev, ebitda = 2109728, 1196745
var_costs = 55416 + 153729   # access charges + licence fee/spectrum charges (revenue-linked), AR FY2026 P&L
tax_rate = 0.2517
cash_liq = 137222 + 137006 + (166546 - 132061)
due24 = 216257 + 143104
float_debt = 159521
for label, e in (("A: -20% revenue, margin -300bp (agent definition)", 0.8 * rev * (ebitda / rev - 0.03)),
                 ("B: -20% revenue with only revenue-linked costs variable (operating leverage)", 0.8 * rev - (rev * 1.0 - (rev - ebitda)) + 0.2 * var_costs - (rev - ebitda - var_costs) * 0 - 0)):
    pass
eA = 0.8 * rev * (ebitda / rev - 0.03)
fixed = (rev - ebitda) - var_costs
eB = 0.8 * rev - fixed - 0.8 * var_costs
for label, e in (("A: revenue -20% and EBITDA margin -300bp", eA), ("B: revenue -20%, only access + licence costs flex (operating leverage)", eB)):
    d = ebitda - e
    cfo_s = 1222296 - d * (1 - tax_rate)
    print("%s: EBITDA %s (-%s); stressed CFO ~ %s (EBITDA loss x (1 - %.4f tax shield)); stressed CFO - interest paid - lease principal - maintenance capex(base) = %s"
          % (label, fmt(e / 10), fmt(d / 10), fmt(cfo_s / 10), tax_rate, fmt((cfo_s - 148876 - 67197 - 312347) / 10)))
    nd = 1216714 - 137222 - 137006
    print("   net debt/stressed EBITDA %.2fx; (net debt+leases)/stressed EBITDA %.2fx" % (nd / e, (nd + 737403) / e))
rs = 0.02 * float_debt + 0.02 * 216257
print("Rate shock +200bp: floating-rate borrowings %s -> +%s/yr; plus refinancing of 12-month maturities %s at +200bp -> +%s; total ~ +%s/yr = %.1f%% of FY2026 equity FCF"
      % (fmt(float_debt / 10), fmt(0.02 * float_debt / 10), fmt(216257 / 10), fmt(0.02 * 216257 / 10), fmt(rs / 10), rs / (ann["FY2026"]["efcf"] * 10) * 100))
print("Liquidity: cash %s + current investments %s + unrestricted other bank balances (approx.) %s = %s vs gross debt maturing in 24 months %s (cover %.2fx)"
      % (fmt(137222 / 10), fmt(137006 / 10), fmt((166546 - 132061) / 10), fmt(cash_liq / 10), fmt(due24 / 10), cash_liq / due24))

print("\n=== G. Sources and uses FY2017-FY2026 (cash-flow statement, INR crore) ===")
NET_BORROW = {"FY2017": 258584 - 274608 + 25377, "FY2018": 197664 - 130717 - 26874, "FY2019": 353141 - 345359 + 98101,
              "FY2020": 377400 - 439813 - 117140 + 70456, "FY2021": 327276 - 409779 - 35659, "FY2022": 254785 - 337212 + 63649,
              "FY2023": 136077 - 178227 - 70972, "FY2024": 67123 - 100803 + 15516, "FY2025": 235597 - 178594 + 36927,
              "FY2026": 140131 - 420773 - 44087}
NCI_NET = {"FY2017": 61863 + 1245 - 10684, "FY2018": 57189 + 21, "FY2019": 104341 + 16238 - 5409, "FY2020": 57144 + 71370,
           "FY2021": 36048 + 7000 - 10243, "FY2022": 10880 + 40911 - 13523, "FY2023": -641, "FY2024": 4391 - 870 - 1693,
           "FY2025": 829 - 37348 - 86292, "FY2026": 75 - 19056}
NCI_DIV = {"FY2017": 12869, "FY2018": 3933, "FY2019": 22638, "FY2020": 18425, "FY2021": 16303, "FY2022": 16537,
           "FY2023": 17100, "FY2024": 19593, "FY2025": 22348, "FY2026": 20168}
Y10 = YRS[-10:]
src = dict(CFO=sum(h("cfo", y) for y in Y10), equity_issued=sum(h("equity_issued", y) for y in Y10),
           NCI_net_inflow=sum(NCI_NET[y] for y in Y10) / 10, net_borrowing=sum(NET_BORROW[y] for y in Y10) / 10)
use = dict(capex=sum(h("capex", y) for y in Y10), spectrum=sum(S[y]["spectrum_paid"] for y in Y10),
           lease_principal=sum(S[y]["lease_paid"] for y in Y10), interest_paid=sum(S[y]["interest_paid"] for y in Y10),
           acquisitions=sum(h("acquisitions", y) for y in Y10), dividends_owners=sum(h("dividends_paid", y) for y in Y10),
           dividends_NCI=sum(NCI_DIV[y] for y in Y10) / 10)
for k, v in src.items():
    print("source %s %s (%.1f%%)" % (k, fmt(v), v / sum(src.values()) * 100))
for k, v in use.items():
    print("use %s %s (%.1f%%)" % (k, fmt(v), v / sum(use.values()) * 100))
print("total sources %s vs listed uses %s; residual (other investing incl. JV, treasury, derivatives, FX, cash build) %s"
      % (fmt(sum(src.values())), fmt(sum(use.values())), fmt(sum(src.values()) - sum(use.values()))))

print("\n=== H. Per-share (rights-adjusted) ===")
for a, b in (("FY2016", "FY2026"), ("FY2021", "FY2026"), ("FY2011", "FY2026"), ("FY2023", "FY2026")):
    n = int(b[2:]) - int(a[2:])
    sa, sb_ = h("shares_diluted", a), h("shares_diluted", b)
    e_a, e_b = ann[a]["efcf"] / sa, ann[b]["efcf"] / sb_
    print("%s->%s (%dy): year-end shares %.2f -> %.2f cr (CAGR %.2f%%); equity FCF/share %s -> %s; revenue CAGR %.1f%%; revenue/share CAGR %.1f%%"
          % (a, b, n, sa, sb_, ((sb_ / sa) ** (1 / n) - 1) * 100, fmt(e_a, 2), fmt(e_b, 2),
             ((h("revenue", b) / h("revenue", a)) ** (1 / n) - 1) * 100,
             (((h("revenue", b) / sb_) / (h("revenue", a) / sa)) ** (1 / n) - 1) * 100))
ua, ub = adj["FY2022"] / h("shares_basic", "FY2022"), adj["FY2026"] / h("shares_basic", "FY2026")
print("underlying EPS FY2022 %.2f -> FY2026 %.2f (4y CAGR %.1f%%)" % (ua, ub, ((ub / ua) ** 0.25 - 1) * 100))

print("\n=== I. Incremental returns with a stated 25.17% tax rate (other: metric; fin_metrics NOPAT is blank in loss years) ===")
T = 0.2517
ic = {}
for y in YRS:
    ic[y] = h("total_equity", y) + h("minority_interest_bs", y) + h("total_debt", y) + h("lease_liabilities", y) - h("cash_and_equivalents", y) - h("current_investments", y)
for b, n in (("FY2026", 5), ("FY2026", 3), ("FY2025", 5), ("FY2026", 10)):
    a = "FY%d" % (int(b[2:]) - n)
    ebit_b = h("ebitda", b) - h("depreciation", b)
    ebit_a = h("ebitda", a) - h("depreciation", a)
    dn = (ebit_b - ebit_a) * (1 - T)
    pa, pb = "FY%d" % (int(a[2:]) - 1), "FY%d" % (int(b[2:]) - 1)
    di = ic[pb] - ic[pa]
    print("%s vs %s: dNOPAT(25.17%%) %s / dIC(%s->%s) %s = %.1f%%" % (b, a, fmt(dn), pa, pb, fmt(di), dn / di * 100))
print("NOPAT(25.17%%) / avg IC: " + "; ".join("%s %.1f%%" % (y, (h("ebitda", y) - h("depreciation", y)) * (1 - T) / ((ic[y] + ic["FY%d" % (int(y[2:]) - 1)]) / 2) * 100) for y in YRS[1:]))

print("\n=== J. Segment economics (INR crore; segment result = EBIT before exceptional incl. JV share) ===")
for r in csv.DictReader(open(RUN / "specialists/financials_workpapers/segment_history_inr_mn.csv")):
    g = lambda k: float(r[k]) if r[k] else None  # noqa: E731
    msi, msa = g("msi_revenue"), g("msa_revenue")
    line = "%s: India mobile rev %s result %s (%.1f%%) | Africa rev %s result %s (%.1f%%) | Africa share of group revenue %.1f%%" % (
        r["period"], fmt(msi / 10), fmt(g("msi_result") / 10), g("msi_result") / msi * 100, fmt(msa / 10), fmt(g("msa_result") / 10),
        g("msa_result") / msa * 100, msa / g("group_revenue") * 100)
    if g("msi_capex"):
        line += " | capex/rev India %.1f%% Africa %.1f%%" % (g("msi_capex") / msi * 100, g("msa_capex") / msa * 100)
    if g("msi_da"):
        line += " | segment EBITDA margin India %.1f%% Africa %.1f%% | result/segment assets India %.1f%% Africa %.1f%%" % (
            (g("msi_result") + g("msi_da")) / msi * 100, (g("msa_result") + g("msa_da")) / msa * 100,
            g("msi_result") / g("msi_assets") * 100, g("msa_result") / g("msa_assets") * 100)
    print(line)
for a, b in (("FY2016", "FY2026"), ("FY2021", "FY2026"), ("FY2019", "FY2026")):
    rows = {r["period"]: r for r in csv.DictReader(open(RUN / "specialists/financials_workpapers/segment_history_inr_mn.csv"))}
    n = int(b[2:]) - int(a[2:])
    print("%s->%s revenue CAGR India mobile %.1f%%, Africa (INR) %.1f%%" % (a, b, ((float(rows[b]["msi_revenue"]) / float(rows[a]["msi_revenue"])) ** (1 / n) - 1) * 100,
                                                                         ((float(rows[b]["msa_revenue"]) / float(rows[a]["msa_revenue"])) ** (1 / n) - 1) * 100))

print("\n=== K. Exceptional items history (INR crore, gain +) and share of |PBT before exceptional| ===")
tot = 0
for y in YRS:
    ex = h("exceptional_items", y)
    tot += ex
    pbe = h("pbt", y) - ex
    print("%s exceptional %s; PBT before exceptional %s" % (y, fmt(ex), fmt(pbe)))
print("cumulative FY2011-FY2026 exceptional items %s; FY2017-FY2026 %s" % (fmt(tot), fmt(sum(h("exceptional_items", y) for y in YRS[-10:]))))

print("\n=== L. Trough vs. peak (INR crore) ===")
for y in ("FY2016", "FY2017", "FY2018", "FY2019", "FY2020", "FY2021"):
    print("%s revenue %s EBITDA %s margin %.1f%% CFO %s capex %s net debt %s" % (y, fmt(h("revenue", y)), fmt(h("ebitda", y)), h("ebitda", y) / h("revenue", y) * 100,
                                                                              fmt(h("cfo", y)), fmt(h("capex", y)), fmt(h("total_debt", y) - h("cash_and_equivalents", y) - h("current_investments", y))))
r16, r19 = h("revenue", "FY2016"), h("revenue", "FY2019")
e16, e19 = h("ebitda", "FY2016"), h("ebitda", "FY2019")
print("FY2016->FY2019 revenue %.1f%%, EBITDA %.1f%%; India mobile revenue FY2017->FY2019 %.1f%%" % ((r19 / r16 - 1) * 100, (e19 / e16 - 1) * 100, (415540 / 565511 - 1) * 100))
