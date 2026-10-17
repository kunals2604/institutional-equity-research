"""CIO price ladder with HURDLE-ADJUSTED IA4 (documented deviation from the tool's undiscounted asymmetry).

Why: valuation_tools.py measures asymmetry as sum p*max(V_T + divs - P, 0) / sum p*max(P - V_T - divs, 0), comparing
5-year horizon values with TODAY's price. When every scenario's horizon value has merely compounded at the cost of equity,
the ratio is large even for an over-priced stock (VAL-C049: 4.8). The economically consistent comparison is against the
price compounded at the hurdle over the same horizon (VAL-C050: 0.06). IA1 and IA2 are the tool's own anchors, unchanged.

Usage: python3 calc/cio_price_ladder_hurdle_adj.py <scenarios.json> <scorecard.json> lo:hi:step
"""
import json, sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import valuation_tools as vt   # noqa: E402
import research_lib as rl      # noqa: E402

inp = json.load(open(sys.argv[1])); sc = json.load(open(sys.argv[2]))
lo, hi, step = (float(x) for x in sys.argv[3].split(":"))
h = float(inp["hurdle_rate"]); T = int(inp["horizon_years"])
weights = {d: w for d, _, w in rl.dimension_weights("IA")}
ia = sc["investment_attractiveness"]
fixed = {d["id"]: d["score"] for d in ia["dimensions"] if d["id"] not in ("IA1", "IA2", "IA4")}
ctx_bq = sc["business_quality"]["final"]; conf = ia["confidence"]
gates = sorted(set(ia.get("gates_triggered") or []) | set(sc["business_quality"].get("gates_triggered") or []))
layer = sc.get("primary_layer") or "None"

def hurdle_asym(P):
    up = down = 0.0
    hurdle_value = P * (1 + h) ** T
    for k, v in inp["scenarios"].items():
        V = vt._value(v["value_per_share"]); d = vt._dps(v.get("dps"), T)
        total = V + sum(d)
        up += v["probability"] * max(total - hurdle_value, 0)
        down += v["probability"] * max(hurdle_value - total, 0)
    return (up / down) if down > 0 else float("inf")

rows = []
P = lo
while P <= hi + 1e-9:
    s = vt.scenarios(inp, P)
    a_h = hurdle_asym(P)
    dims = {"IA1": vt.ia1(s["margin_of_safety"]), "IA2": vt.ia2(s["expected_irr"], h), "IA4": vt.ia4(a_h)}
    allv = dict(fixed, **dims)
    raw = sum(allv[k] * w for k, w in weights.items()) / 100.0
    final = int(round(raw))
    mv = rl.mapped_verdict(ctx_bq, final, conf, gates, layer)
    rows.append({"price": round(P, 2), "margin_of_safety": round(s["margin_of_safety"], 4), "expected_irr": round(s["expected_irr"], 4),
                 "asym_tool": round(s["asymmetry_ratio"], 3), "asym_hurdle_adj": round(a_h, 4),
                 "IA1": dims["IA1"], "IA2": dims["IA2"], "IA4_hurdle_adj": dims["IA4"], "IA4_tool": vt.ia4(s["asymmetry_ratio"]),
                 "ia_raw": round(raw, 2), "ia_final": final, "mapped_verdict": mv})
    P += step

def best(cond):
    ok = [r["price"] for r in rows if cond(r)]
    return max(ok) if ok else None
trig = {"buy_below": best(lambda r: rl.NOTCH.get(r["mapped_verdict"], -1) >= 3),
        "strong_buy_below": best(lambda r: r["mapped_verdict"] == "STRONG BUY"),
        "avoid_above": min([r["price"] for r in rows if rl.NOTCH.get(r["mapped_verdict"], 9) <= 1], default=None),
        "hold_or_watchlist_band": [r["price"] for r in rows if r["mapped_verdict"] in ("HOLD / NEUTRAL", "WATCHLIST — WAIT FOR BETTER PRICE")]}
trig["hold_or_watchlist_band"] = [min(trig["hold_or_watchlist_band"]), max(trig["hold_or_watchlist_band"])] if trig["hold_or_watchlist_band"] else None
out = {"hurdle_rate": h, "method": __doc__.strip().splitlines()[0], "rows": rows, "decision_triggers": trig}
print("price | MoS | E[IRR] | asym_tool | asym_h | IA1 | IA2 | IA4_h | IA4_tool | IA | verdict")
for r in rows:
    print("%7.0f | %6.1f%% | %5.1f%% | %7.2f | %6.3f | %3d | %3d | %3d | %3d | %3d | %s" % (r["price"], 100*r["margin_of_safety"], 100*r["expected_irr"], r["asym_tool"], r["asym_hurdle_adj"], r["IA1"], r["IA2"], r["IA4_hurdle_adj"], r["IA4_tool"], r["ia_final"], r["mapped_verdict"]))
print("triggers:", json.dumps(trig))
if len(sys.argv) > 4:
    json.dump(out, open(sys.argv[4], "w"), indent=2)
