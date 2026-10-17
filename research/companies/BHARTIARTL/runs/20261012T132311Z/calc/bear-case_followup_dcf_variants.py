"""Stage-3 steelman: re-run the draft base DCF (calc/valuation_dcf_inputs.json) through scripts/valuation_tools.dcf with
single, labelled changes; then re-map IA1/IA2/IA4 with the SCORING.md anchors, holding every other draft IA score fixed.
Run from the run directory: python3 calc/bear-case_followup_dcf_variants.py > calc/bear-case_followup_dcf_variants.out"""
import json, sys, copy, os, math
sys.path.insert(0, os.path.abspath("../../../../../scripts"))
from valuation_tools import dcf, path_of   # deterministic tool used by the draft

base = json.load(open("calc/valuation_dcf_inputs.json"))
scen = json.load(open("calc/valuation_scenarios.json"))
PRICE = 1778.70
N = int(base["years"])
WD, KD_AT = 0.1142, 0.059864           # calc/valuation_wacc.json
def wacc_from_ke(ke): return ke * (1 - WD) + KD_AT * WD
KE_DRAFT = 0.116796

def tariff_round(inp, years, uplift):
    """A tariff round in year k: revenue +uplift that year, 90% EBIT flow-through, margin uplift persists."""
    g = path_of(inp["revenue_growth"], N); m = path_of(inp["ebit_margin"], N)
    for k in years:
        g[k - 1] += uplift
        for j in range(k - 1, N):
            m[j] = (m[j] + 0.9 * uplift) / (1 + uplift)
    out = copy.deepcopy(inp); out["revenue_growth"] = g; out["ebit_margin"] = m
    return out

# uplift: realised +8% on India mobile revenue (headline rounds were 10-25%; INDUSTRY-reported realised ARPU +14-16%)
MOB_SHARE = 1129954.0 / 2109728.0       # FY2026 Mobile India segment revenue / consolidated revenue (BEAR-C049, BEAR-C001)
U = 0.08 * MOB_SHARE
variants = []
variants.append(("V0 draft base", base, KE_DRAFT))
v = copy.deepcopy(base); ke = 0.069 - 0.0187 + 0.87 * 0.0708; v["wacc"] = wacc_from_ke(ke)
variants.append(("V1 rf normalised to 6.90%% (Apr-2026 level) -> Ke %.2f%%" % (100 * ke), v, ke))
variants.append(("V2 base + one realised +8%% mobile round in year 2 (consolidated +%.1f%%)" % (100 * U), tariff_round(base, [2], U), KE_DRAFT))
variants.append(("V3 base + two rounds (years 2 and 5)", tariff_round(base, [2, 5], U), KE_DRAFT))
v4 = tariff_round(base, [2, 5], U); v4["wacc"] = wacc_from_ke(ke)
variants.append(("V4 = V3 + V1", v4, ke))
v5 = copy.deepcopy(v4); v5["tax_rate"] = 0.2517
variants.append(("V5 = V4 + tax 25.17% (draft WACC tax input) instead of 27%", v5, ke))
v6 = copy.deepcopy(base); v6["sales_to_capital"] = 1.0
variants.append(("V6 (bear-side check) base with sales-to-capital 1.0 (approx. FY2021-26 incremental)", v6, KE_DRAFT))

def ia1(mos):
    bands = [(0.40, 1.00, 90, 100), (0.25, 0.40, 75, 89), (0.10, 0.25, 60, 74), (-0.10, 0.10, 40, 59), (-0.30, -0.10, 20, 39)]
    for lo, hi, a, b in bands:
        if lo <= mos < hi: return a + (b - a) * (mos - lo) / (hi - lo)
    if mos >= 1.0: return 100
    return max(0.0, 19 * (1 - (-0.30 - mos) / 0.70))
def ia2(eirr, h):
    bands = [(h + 0.08, h + 0.16, 90, 100), (h + 0.04, h + 0.08, 75, 89), (h, h + 0.04, 60, 74), (h - 0.04, h, 40, 59), (0.0, h - 0.04, 20, 39)]
    for lo, hi, a, b in bands:
        if lo <= eirr < hi: return a + (b - a) * (eirr - lo) / (hi - lo)
    return 100 if eirr >= h + 0.16 else max(0.0, 19 * (1 + eirr / 0.20))
def ia4(x):
    bands = [(3.0, 6.0, 90, 100), (2.0, 3.0, 70, 89), (1.2, 2.0, 50, 69), (0.8, 1.2, 30, 49), (0.0, 0.8, 0, 29)]
    for lo, hi, a, b in bands:
        if lo <= x < hi: return a + (b - a) * (x - lo) / (hi - lo)
    return 100
OTHER = {"IA3": 58, "IA5": 30, "IA6": 58, "IA7": 80, "IA8": 72}
W = {"IA1": .25, "IA2": .20, "IA3": .20, "IA4": .10, "IA5": .10, "IA6": .05, "IA7": .05, "IA8": .05}

def ia_total(base_value, ke, probs=(0.20, 0.55, 0.25), shift_all=False):
    s = scen["scenarios"]
    bear_v = sum(s["bear"]["value_today"]) / 2; bull_v = sum(s["bull"]["value_today"]) / 2
    draft_base = sum(s["base"]["value_today"]) / 2
    if shift_all:   # bear and bull move by the same ratio as the base (e.g. a discount-rate change)
        bear_v *= base_value / draft_base; bull_v *= base_value / draft_base
    divs = {"bear": 120.0, "base": 180.0, "bull": 210.0}   # calc/valuation_scenario_irr.json
    vals = {"bear": bear_v, "base": base_value, "bull": bull_v}
    pb = dict(zip(("bear", "base", "bull"), probs))
    irr_draft = json.load(open("calc/valuation_scenario_irr.json"))["scenarios"]
    draft_vals = {"bear": sum(s["bear"]["value_today"]) / 2, "base": draft_base, "bull": sum(s["bull"]["value_today"]) / 2}
    # FV-of-dividend deduction implied by the draft: V_today x (1+Ke_draft)^5 - horizon_value, per scenario
    fvd = {k: draft_vals[k] * (1 + KE_DRAFT) ** 5 - irr_draft[k]["horizon_value"] for k in vals}
    hv = {k: vals[k] * (1 + ke) ** 5 - fvd[k] for k in vals}   # draft construction
    ev = sum(pb[k] * (hv[k] + divs[k]) for k in hv)
    eirr = (ev / PRICE) ** 0.2 - 1
    hurdle_p = PRICE * (1 + ke) ** 5
    up = sum(pb[k] * max(hv[k] + divs[k] - hurdle_p, 0) for k in hv); dn = sum(pb[k] * max(hurdle_p - hv[k] - divs[k], 0) for k in hv)
    asym = up / dn if dn else 9.9
    mos = (base_value - PRICE) / base_value
    sc = dict(OTHER, IA1=ia1(mos), IA2=ia2(eirr, ke), IA4=ia4(asym))
    return mos, eirr, asym, sc, sum(W[k] * sc[k] for k in W)

print("price", PRICE)
for name, inp, ke in variants:
    r = dcf(inp)
    v = r["value_per_share"]
    mos, eirr, asym, sc, tot = ia_total(v, ke)
    print(f"\n{name}\n  WACC {inp['wacc']:.4f}; value/share INR {v:,.0f}; terminal share {r['terminal_share_of_ev']:.0%}; exit EV/EBIT {r['implied_exit_ev_ebit']:.1f}x")
    print(f"  MoS {mos:+.1%}; E[IRR] {eirr:.1%} vs hurdle {ke:.2%}; hurdle-adj asymmetry {asym:.2f}; IA1 {sc['IA1']:.0f} IA2 {sc['IA2']:.0f} IA4 {sc['IA4']:.0f} -> IA {tot:.1f}")

print("\n== Probability-weight test on draft values (bear/base/bull unchanged), draft Ke")
for probs in ((0.20, 0.55, 0.25), (0.15, 0.50, 0.35), (0.10, 0.45, 0.45)):
    mos, eirr, asym, sc, tot = ia_total(1243.5, KE_DRAFT, probs)
    print(f"  probs {probs}: E[IRR] {eirr:.1%}; asym {asym:.2f}; IA {tot:.1f}")

print("\n== Draft IA check (should reproduce ~35.5)")
mos, eirr, asym, sc, tot = ia_total(1243.5, KE_DRAFT)
print(f"  MoS {mos:+.1%} E[IRR] {eirr:.1%} asym {asym:.2f} IA {tot:.1f}")
