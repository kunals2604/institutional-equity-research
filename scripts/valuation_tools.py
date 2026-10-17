#!/usr/bin/env python3
"""Deterministic valuation math: assumptions come from analysts, arithmetic comes from code.

Subcommands (inputs are JSON files saved under RUN_DIR/calc/; see templates/valuation_inputs.example.json):
  wacc           --inputs F                 cost of equity (CAPM) and WACC
  dcf            --inputs F                 FCFF DCF with fade paths, terminal value via RONIC, sanity checks, sensitivity
  reverse-dcf    --inputs F --price P [--solve growth|margin]   implied growth or margin
  scenario-build --inputs F                 scenario-irr inputs from scenario values TODAY (horizon value = value x (1+hurdle)^T
                                            less the future value of interim dividends: the price converges to value)
  scenario-irr   --inputs F                 bear/base/bull IRRs, E[IRR], asymmetry (hurdle-adjusted), margin of safety
  price-ladder   --inputs F [--scorecard S] [--prices a,b,c | --range lo:hi:step]
                                            IA1/IA2/IA4 per price (SCORING.md anchors), IA and mapped verdict per price
  decompose      --inputs F                 expected-return decomposition (EPS growth, multiple change, yield, dilution)
  sizing-ceiling --inputs F [--policy config/investment_policy.json]   position ceiling from IPS risk limits
  robustness     --inputs F --scorecard S [--price P]   is the mapped verdict stable across the plausible ranges of the
                                            decisive assumptions? (input to the confidence rule, SCORING.md §4)

DCF inputs may carry "event_uplifts": [{"year": 2, "revenue_uplift": 0.043, "flow_through": 0.9, "label": "..."}]
for discrete, evidenced step changes (tariff rounds, price increases, capacity additions): revenue growth in that
year rises by the uplift and the margin from that year on absorbs flow_through x uplift.

Every command prints a markdown result and, with --out, writes JSON. Definitions:
methodology/METRIC_DEFINITIONS.md and methodology/SCORING.md.
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def path_of(spec, n: int) -> List[float]:
    """A scalar, a [start, end] linear fade, or an explicit list of length n."""
    if isinstance(spec, (int, float)):
        return [float(spec)] * n
    if isinstance(spec, list) and len(spec) == n:
        return [float(x) for x in spec]
    if isinstance(spec, list) and len(spec) == 2:
        a, b = float(spec[0]), float(spec[1])
        return [a + (b - a) * i / max(1, n - 1) for i in range(n)]
    raise ValueError("path must be a number, [start, end] or a list of %d values" % n)


# ---------------------------------------------------------------------------
def wacc(inp: dict) -> dict:
    ke = inp["risk_free_rate"] + inp["beta"] * inp["equity_risk_premium"] + inp.get("additional_premium", 0.0)
    kd = inp.get("cost_of_debt_pretax", 0.0) * (1 - inp.get("tax_rate", 0.0))
    wd = inp.get("debt_weight", 0.0)
    w = ke * (1 - wd) + kd * wd
    return {"cost_of_equity": ke, "cost_of_debt_after_tax": kd, "debt_weight": wd, "wacc": w,
            "formula": "Ke = rf + beta*ERP + premium; WACC = Ke*(1-wd) + Kd*(1-t)*wd"}


def dcf(inp: dict, override: Optional[dict] = None) -> dict:
    p = dict(inp, **(override or {}))
    n = int(p["years"])
    g = path_of(p["revenue_growth"], n)
    m = path_of(p["ebit_margin"], n)
    events = []
    for ev in p.get("event_uplifts") or []:
        k, u = int(ev["year"]), float(ev["revenue_uplift"])
        f = float(ev.get("flow_through", 0.9))
        if not 1 <= k <= n:
            raise ValueError("event_uplifts year %d outside 1..%d" % (k, n))
        g[k - 1] += u
        for j in range(k - 1, n):
            m[j] = (m[j] + f * u) / (1 + u)
        events.append({"year": k, "revenue_uplift": u, "flow_through": f, "label": ev.get("label", "")})
    t, r, gt = float(p["tax_rate"]), float(p["wacc"]), float(p["terminal_growth"])
    if gt >= r:
        raise ValueError("terminal_growth must be below wacc")
    ronic = float(p.get("terminal_roic", r))
    rev_prev = float(p["base_revenue"])
    rows, pv_sum = [], 0.0
    for i in range(n):
        rev = rev_prev * (1 + g[i])
        nopat = rev * m[i] * (1 - t)
        if "sales_to_capital" in p:
            reinv = (rev - rev_prev) / float(p["sales_to_capital"])
        else:
            reinv = nopat * float(p.get("reinvestment_rate", 0.0))
        fcff = nopat - reinv
        exponent = (i + 0.5) if p.get("mid_year", True) else (i + 1)
        df = 1 / (1 + r) ** exponent
        pv_sum += fcff * df
        rows.append({"year": i + 1, "revenue": rev, "growth": g[i], "ebit_margin": m[i], "nopat": nopat,
                     "reinvestment": reinv, "fcff": fcff, "discount_factor": df, "pv": fcff * df})
        rev_prev = rev
    nopat_next = rev_prev * (1 + gt) * m[-1] * (1 - t)
    tv = nopat_next * (1 - gt / ronic) / (r - gt)
    pv_tv = tv / (1 + r) ** n
    ev = pv_sum + pv_tv
    equity = ev + float(p.get("non_operating_assets", 0)) - float(p.get("net_debt", 0)) - float(p.get("minority_interest", 0))
    per_share = equity / float(p["shares_diluted"])
    warnings = []
    if pv_tv / ev > 0.75:
        warnings.append("terminal value is %.0f%% of EV (> 75%%): conclusion rests on terminal assumptions" % (100 * pv_tv / ev))
    if "risk_free_rate" in p and gt > p["risk_free_rate"]:
        warnings.append("terminal growth exceeds the risk-free rate")
    if ronic < r:
        warnings.append("terminal ROIC below WACC: terminal growth destroys value")
    last_ebit = rows[-1]["revenue"] * m[-1]
    return {"rows": rows, "terminal_value": tv, "pv_terminal": pv_tv, "pv_explicit": pv_sum, "enterprise_value": ev,
            "equity_value": equity, "value_per_share": per_share, "terminal_share_of_ev": pv_tv / ev,
            "implied_exit_ev_ebit": tv / last_ebit if last_ebit else None,
            "terminal_reinvestment_rate": gt / ronic, "events_applied": events, "warnings": warnings}


def dcf_sensitivity(inp: dict) -> List[dict]:
    out = []
    for dw in (-0.01, -0.005, 0, 0.005, 0.01):
        for dg in (-0.01, -0.005, 0, 0.005, 0.01):
            w, gg = inp["wacc"] + dw, inp["terminal_growth"] + dg
            if gg >= w - 0.005:
                out.append({"wacc": w, "terminal_growth": gg, "value_per_share": None})
                continue
            out.append({"wacc": w, "terminal_growth": gg, "value_per_share": dcf(inp, {"wacc": w, "terminal_growth": gg})["value_per_share"]})
    return out


def bisect(f, lo: float, hi: float, tol: float = 1e-7, it: int = 200) -> Optional[float]:
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None
    for _ in range(it):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(fm) < tol or (hi - lo) < tol:
            return mid
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def reverse_dcf(inp: dict, price: float, solve: str) -> dict:
    if solve == "growth":
        f = lambda x: dcf(inp, {"revenue_growth": x})["value_per_share"] - price  # noqa: E731
        x = bisect(f, -0.20, 0.80)
        label = "constant annual revenue growth over the explicit period"
    else:
        start = path_of(inp["ebit_margin"], int(inp["years"]))[0]
        f = lambda x: dcf(inp, {"ebit_margin": [start, x]})["value_per_share"] - price  # noqa: E731
        x = bisect(f, -0.10, 0.90)
        label = "EBIT margin reached by the final explicit year (linear path from the current margin)"
    if x is None:
        return {"solved": None, "note": "no solution in search bounds; the price is outside what this model can justify"}
    res = dcf(inp, {"revenue_growth": x} if solve == "growth" else {"ebit_margin": [path_of(inp["ebit_margin"], int(inp["years"]))[0], x]})
    return {"solve_for": solve, "implied_value": x, "meaning": label,
            "implied_final_year_revenue": res["rows"][-1]["revenue"], "implied_final_year_nopat": res["rows"][-1]["nopat"],
            "check_value_per_share": res["value_per_share"], "price": price}


def irr(flows: List[float]) -> float:
    if sum(flows[1:]) <= 0:
        return -1.0
    npv = lambda r: sum(cf / (1 + r) ** i for i, cf in enumerate(flows))  # noqa: E731
    x = bisect(npv, -0.9999, 10.0)
    return x if x is not None else float("nan")


def _value(v) -> float:
    return (float(v[0]) + float(v[1])) / 2 if isinstance(v, list) else float(v)


def _dps(spec, n: int) -> List[float]:
    if spec is None:
        return [0.0] * n
    return path_of(spec, n)


def scenarios(inp: dict, price: Optional[float] = None) -> dict:
    P = float(price if price is not None else inp["price"])
    T = int(inp["horizon_years"])
    sc = inp["scenarios"]
    probs = {k: float(v["probability"]) for k, v in sc.items()}
    if abs(sum(probs.values()) - 1) > 0.011:
        raise ValueError("scenario probabilities sum to %.3f" % sum(probs.values()))
    out, exp_div, exp_v = {}, [0.0] * T, 0.0
    up = down = mean_irr = 0.0
    h = inp.get("hurdle_rate")
    bar = P * (1 + float(h)) ** T if h is not None else P   # hurdle-adjusted asymmetry compares with the price compounded at H
    up_h = down_h = 0.0
    for k, v in sc.items():
        V, d = _value(v["value_per_share"]), _dps(v.get("dps"), T)
        r = irr([-P] + d[:-1] + [d[-1] + V])
        total = V + sum(d)
        out[k] = {"probability": probs[k], "horizon_value": V, "dividends": sum(d), "irr": r}
        exp_v += probs[k] * V
        exp_div = [a + probs[k] * b for a, b in zip(exp_div, d)]
        up += probs[k] * max(total - P, 0)
        down += probs[k] * max(P - total, 0)
        up_h += probs[k] * max(total - bar, 0)
        down_h += probs[k] * max(bar - total, 0)
        mean_irr += probs[k] * r
    e_irr = irr([-P] + exp_div[:-1] + [exp_div[-1] + exp_v])
    iv = inp.get("intrinsic_value_today")
    base = (float(iv["low"]) + float(iv["high"])) / 2 if iv else None
    return {"price": P, "horizon_years": T, "scenarios": out, "expected_horizon_value": exp_v,
            "expected_irr": e_irr, "mean_of_scenario_irrs": mean_irr,
            "asymmetry_ratio": (up_h / down_h) if down_h > 0 else float("inf"),
            "asymmetry_basis": ("hurdle-adjusted: horizon value + dividends vs price x (1+hurdle)^T (SCORING.md IA4)"
                                if h is not None else "undiscounted: no hurdle_rate in inputs (add one for scoring)"),
            "asymmetry_ratio_undiscounted": (up / down) if down > 0 else float("inf"),
            "base_value_today": base, "margin_of_safety": (base - P) / base if base else None}


# SCORING.md anchors, interpolated linearly within each band ---------------
def ia1(m: Optional[float]) -> Optional[int]:
    if m is None:
        return None
    m = round(m, 10)  # avoid float artifacts at band edges
    if m >= 0.40:
        s = 90 + min(10, (m - 0.40) / 0.20 * 10)
    elif m >= 0.25:
        s = 75 + (m - 0.25) / 0.15 * 14
    elif m >= 0.10:
        s = 60 + (m - 0.10) / 0.15 * 14
    elif m >= -0.10:
        s = 40 + (m + 0.10) / 0.20 * 19
    elif m >= -0.30:
        s = 20 + (m + 0.30) / 0.20 * 19
    else:
        s = max(0.0, 19 * (1 + (m + 0.30) / 0.70))
    return rl.round_half_up(s)


def ia2(e: float, h: float) -> int:
    e, d = round(e, 10), round(e - h, 10)  # avoid float artifacts at band edges
    if d >= 0.08:
        s = 90 + min(10, (d - 0.08) / 0.08 * 10)
    elif d >= 0.04:
        s = 75 + (d - 0.04) / 0.04 * 14
    elif d >= 0:
        s = 60 + d / 0.04 * 14
    elif d >= -0.04:
        s = 40 + (d + 0.04) / 0.04 * 19
    elif e >= 0:
        s = 20 + (e / (h - 0.04)) * 19 if h - 0.04 > 0 else 20
    else:
        s = max(0.0, 19 * (1 + e / 0.20))
    return rl.round_half_up(s)


def ia4(r: float) -> int:
    if math.isinf(r):
        return 100
    r = round(r, 10)
    if r >= 3:
        s = 90 + min(10, (r - 3) / 2 * 10)
    elif r >= 2:
        s = 70 + (r - 2) * 19
    elif r >= 1.2:
        s = 50 + (r - 1.2) / 0.8 * 19
    elif r >= 0.8:
        s = 30 + (r - 0.8) / 0.4 * 19
    else:
        s = max(0.0, r / 0.8 * 29)
    return rl.round_half_up(s)


def price_ladder(inp: dict, prices: List[float], scorecard: Optional[dict]) -> dict:
    if inp.get("hurdle_rate") is None:
        raise ValueError("hurdle_rate missing: use the run's cost of equity from `valuation_tools.py wacc` (SCORING.md §3)")
    h = float(inp["hurdle_rate"])
    weights = {d: w for d, _, w in rl.dimension_weights("IA")}
    fixed, caps, ctx = {}, [], None
    if scorecard:
        ia = scorecard["investment_attractiveness"]
        fixed = {d["id"]: d["score"] for d in ia["dimensions"] if d["id"] not in ("IA1", "IA2", "IA4")}
        gate_caps = rl.gates("IA")
        caps = [gate_caps[g][1] for g in ia.get("gates_triggered") or [] if g in gate_caps and gate_caps[g][1] is not None]
        ctx = {"bq": scorecard["business_quality"]["final"], "conf": ia.get("confidence", "Medium"),
               "gates": sorted(set(ia.get("gates_triggered") or []) | set(scorecard["business_quality"].get("gates_triggered") or [])),
               "layer": scorecard.get("primary_layer") or "None"}
    rows = []
    for P in prices:
        s = scenarios(inp, P)
        dims = {"IA1": ia1(s["margin_of_safety"]), "IA2": ia2(s["expected_irr"], h), "IA4": ia4(s["asymmetry_ratio"])}
        row = {"price": P, "margin_of_safety": s["margin_of_safety"], "expected_irr": s["expected_irr"],
               "asymmetry_ratio": s["asymmetry_ratio"], **dims}
        if scorecard and dims["IA1"] is not None:
            allv = dict(fixed, **dims)
            raw = sum(allv[k] * w for k, w in weights.items()) / 100.0
            final = min([rl.round_half_up(raw)] + caps)
            row.update({"ia_raw": raw, "ia_final": final,
                        "mapped_verdict": rl.mapped_verdict(ctx["bq"], final, ctx["conf"], ctx["gates"], ctx["layer"])})
        rows.append(row)
    triggers = {}
    if scorecard:
        def best(cond):
            ok = [r["price"] for r in rows if cond(r)]
            return max(ok) if ok else None
        triggers = {"buy_below": best(lambda r: rl.NOTCH.get(r.get("mapped_verdict"), -1) >= 3),
                    "strong_buy_below": best(lambda r: r.get("mapped_verdict") == "STRONG BUY"),
                    "avoid_above": min([r["price"] for r in rows if rl.NOTCH.get(r.get("mapped_verdict"), 9) <= 1], default=None)}
    return {"hurdle_rate": h, "rows": rows, "decision_triggers": triggers,
            "note": "IA3, IA5-IA8 held at the scorecard's values; IA5 (expectations gap) is also price-sensitive, so review it near the trigger prices."}


def scenario_build(inp: dict) -> dict:
    """Build scenario-irr inputs from scenario values TODAY. Convention (METRIC_DEFINITIONS.md): the price converges to
    scenario value by the horizon, so horizon value = value_today x (1+H)^T - future value of interim dividends."""
    T = int(inp["horizon_years"])
    H = float(inp["hurdle_rate"])
    sc = {}
    for k, v in inp["scenarios"].items():
        d = _dps(v.get("dps"), T)
        fv_div = sum(x * (1 + H) ** (T - 1 - i) for i, x in enumerate(d))
        vt = v["value_today"] if isinstance(v["value_today"], list) else [v["value_today"], v["value_today"]]
        sc[k] = {"probability": float(v["probability"]), "value_today": [float(x) for x in vt],
                 "value_per_share": [round(float(x) * (1 + H) ** T - fv_div, 2) for x in vt],
                 "dps": v.get("dps")}
    base = inp.get("intrinsic_value_today") or {"low": sc["base"]["value_today"][0], "high": sc["base"]["value_today"][1]}
    return {"price": float(inp["price"]), "horizon_years": T, "hurdle_rate": H, "intrinsic_value_today": base,
            "scenarios": sc, "convention": "horizon value = value_today x (1+hurdle)^T - FV(interim dividends)"}


def robustness(inp: dict, scorecard: dict, price: Optional[float] = None, value_shift: float = 0.15,
               prob_shift: float = 0.10, hurdle_shift: float = 0.01) -> dict:
    """Mapped verdict across the plausible ranges of the decisive assumptions: base value +/- value_shift,
    probability moved prob_shift from base to bear or to bull, hurdle +/- hurdle_shift. Inputs are scenario-build
    inputs (values TODAY). The verdict is 'robust' if every combination maps to the same verdict."""
    P = float(price if price is not None else inp["price"])
    rows = []
    for vs in (-value_shift, 0.0, value_shift):
        for tilt in ("bear", "none", "bull"):
            for hs in (-hurdle_shift, 0.0, hurdle_shift):
                x = json.loads(json.dumps(inp))
                x["hurdle_rate"] = float(inp["hurdle_rate"]) + hs
                b = x["scenarios"]["base"]
                b["value_today"] = [v * (1 + vs) for v in (b["value_today"] if isinstance(b["value_today"], list) else [b["value_today"]] * 2)]
                if x.get("intrinsic_value_today"):
                    x["intrinsic_value_today"] = {"low": x["intrinsic_value_today"]["low"] * (1 + vs),
                                                  "high": x["intrinsic_value_today"]["high"] * (1 + vs)}
                if tilt != "none" and "base" in x["scenarios"] and tilt in x["scenarios"]:
                    mv = min(prob_shift, x["scenarios"]["base"]["probability"])
                    x["scenarios"]["base"]["probability"] -= mv
                    x["scenarios"][tilt]["probability"] += mv
                built = scenario_build(x)
                lad = price_ladder(built, [P], scorecard)["rows"][0]
                rows.append({"base_value_shift": vs, "probability_tilt": tilt, "hurdle_shift": hs,
                             "expected_irr": lad["expected_irr"], "ia_final": lad.get("ia_final"),
                             "mapped_verdict": lad.get("mapped_verdict")})
    verdicts = sorted({r["mapped_verdict"] for r in rows})
    ias = [r["ia_final"] for r in rows if r["ia_final"] is not None]
    return {"price": P, "combinations": len(rows), "verdicts": verdicts, "robust": len(verdicts) == 1,
            "ia_range": [min(ias), max(ias)] if ias else None, "rows": rows,
            "note": "High IA confidence requires robust = true (SCORING.md §4); IA3 and IA5-IA8 held at scorecard values."}


def decompose(inp: dict) -> dict:
    n = float(inp["years"])
    g = float(inp["eps_growth"])
    mult = (float(inp["end_pe"]) / float(inp["start_pe"])) ** (1 / n) - 1
    dil = float(inp.get("annual_dilution", 0.0))
    y = float(inp.get("dividend_yield", 0.0))
    total = (1 + g) * (1 + mult) * (1 - dil) - 1 + y
    return {"eps_growth": g, "annual_multiple_change": mult, "annual_dilution": dil, "dividend_yield": y,
            "approx_annual_return": total,
            "formula": "(1+EPS growth)*(1+annualized multiple change)*(1-dilution) - 1 + dividend yield"}


def sizing_ceiling(inp: dict, policy: dict) -> dict:
    lim = policy.get("risk_limits", {})
    liq = policy.get("liquidity", {})
    P, bear = float(inp["price"]), float(inp["bear_value_with_dividends"])
    loss = max(0.0, (P - bear) / P)
    parts = {}
    if lim.get("max_position_pct") is not None:
        parts["policy_max_position_pct"] = float(lim["max_position_pct"])
    if lim.get("max_loss_per_position_pct") is not None and loss > 0:
        parts["loss_budget_cap_pct"] = float(lim["max_loss_per_position_pct"]) / loss
    if lim.get("portfolio_aum") and inp.get("adtv"):
        cap_value = float(inp["adtv"]) * float(liq.get("max_adtv_participation", 0.2)) * float(liq.get("max_days_to_exit", 20))
        parts["liquidity_cap_pct"] = 100.0 * cap_value / float(lim["portfolio_aum"])
    if inp.get("speculative") and lim.get("speculative_max_position_pct") is not None:
        parts["speculative_cap_pct"] = float(lim["speculative_max_position_pct"])
    days = None
    if inp.get("adtv"):
        days = float(policy.get("reference_position", 0)) / (float(inp["adtv"]) * float(liq.get("max_adtv_participation", 0.2)))
    return {"bear_case_loss_pct": 100 * loss, "days_to_exit_reference_position": days,
            "components": parts, "sizing_ceiling_pct": min(parts.values()) if parts else None,
            "basis": "min(" + ", ".join(parts) + ")" if parts else "no ceiling: IPS risk limits not set (config/investment_policy.json)",
            "policy_confirmed": bool(policy.get("confirmed_by_user"))}


# ---------------------------------------------------------------------------
def clean(o):
    """Strict-JSON friendly: infinities and NaN become None."""
    if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
        return None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o


def fmt(x) -> str:
    if x is None:
        return "–"
    if isinstance(x, float):
        if math.isinf(x):
            return "∞"
        return "%.4g" % x
    return str(x)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["wacc", "dcf", "reverse-dcf", "scenario-build", "scenario-irr", "price-ladder", "decompose",
                                        "sizing-ceiling", "robustness"])
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--price", type=float)
    ap.add_argument("--solve", choices=["growth", "margin"], default="growth")
    ap.add_argument("--scorecard")
    ap.add_argument("--prices")
    ap.add_argument("--range")
    ap.add_argument("--policy", default=str(rl.INVESTMENT_POLICY))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    inp = load(a.inputs)
    try:
        if a.command == "wacc":
            res = wacc(inp)
        elif a.command == "dcf":
            res = dcf(inp)
            res["sensitivity"] = dcf_sensitivity(inp)
        elif a.command == "reverse-dcf":
            if a.price is None:
                ap.error("--price is required")
            res = reverse_dcf(inp, a.price, a.solve)
        elif a.command == "scenario-build":
            res = scenario_build(inp)
        elif a.command == "scenario-irr":
            res = scenarios(inp)
        elif a.command == "robustness":
            if not a.scorecard:
                ap.error("--scorecard is required")
            res = robustness(inp, rl.load_json(Path(a.scorecard)), a.price)
        elif a.command == "price-ladder":
            if a.prices:
                prices = [float(x) for x in a.prices.split(",")]
            elif a.range:
                lo, hi, step = (float(x) for x in a.range.split(":"))
                prices, x = [], lo
                while x <= hi + 1e-9:
                    prices.append(round(x, 6))
                    x += step
            else:
                ap.error("--prices or --range is required")
            res = price_ladder(inp, prices, rl.load_json(Path(a.scorecard)) if a.scorecard else None)
        elif a.command == "decompose":
            res = decompose(inp)
        else:
            res = sizing_ceiling(inp, rl.load_json(Path(a.policy)))
    except (KeyError, ValueError) as exc:
        print("ERROR: %s" % exc)
        return 1

    if a.command == "dcf":
        print("| year | revenue | growth | EBIT margin | NOPAT | reinvestment | FCFF | PV |\n|---|---|---|---|---|---|---|---|")
        for r in res["rows"]:
            print("| %d | %s | %s | %s | %s | %s | %s | %s |" % (r["year"], fmt(r["revenue"]), fmt(r["growth"]), fmt(r["ebit_margin"]),
                                                             fmt(r["nopat"]), fmt(r["reinvestment"]), fmt(r["fcff"]), fmt(r["pv"])))
        for k in ("pv_explicit", "pv_terminal", "enterprise_value", "equity_value", "value_per_share", "terminal_share_of_ev", "implied_exit_ev_ebit"):
            print("%s: %s" % (k, fmt(res[k])))
        for w in res["warnings"]:
            print("WARNING: " + w)
        print("\nSensitivity (value per share): WACC x terminal growth")
        for r in res["sensitivity"]:
            print("  wacc %.3f  g %.3f  -> %s" % (r["wacc"], r["terminal_growth"], fmt(r["value_per_share"])))
    elif a.command == "price-ladder":
        cols = ["price", "margin_of_safety", "expected_irr", "asymmetry_ratio", "IA1", "IA2", "IA4", "ia_final", "mapped_verdict"]
        print("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
        for r in res["rows"]:
            print("| " + " | ".join(fmt(r.get(c)) for c in cols) + " |")
        if res["decision_triggers"]:
            print("\nDecision triggers: %s" % res["decision_triggers"])
        print(res["note"])
    else:
        print(json.dumps(clean(res), indent=2))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(clean(res), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
