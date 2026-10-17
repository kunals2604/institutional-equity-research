"""CIO adjudication of the Stage-3 adversarial review (BEAR-C084/C085): add ONE realised tariff round in year 2
(+8% on India mobile revenue = consolidated +4.3%, 90% EBIT flow-through; method of calc/bear-case_followup_dcf_variants.py)
to valuation's own base inputs (lo / point / hi). Also report the capital-intensity check (sales-to-capital 1.0, BEAR-C088/C089).
Then rebuild the scenario set with valuation's horizon convention (calc/valuation_build_scenarios.py)."""
import json, os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", "..", "scripts")))
from valuation_tools import dcf, path_of  # noqa: E402
def load(n): return json.load(open(os.path.join(HERE, n)))
U = 0.08 * 1129954.0 / 2109728.0      # India mobile share of FY2026 revenue (IND-C055; CIO-C010)
def one_round(inp, k=2):
    N = int(inp["years"]); g = path_of(inp["revenue_growth"], N); m = path_of(inp["ebit_margin"], N)
    g[k - 1] += U
    for j in range(k - 1, N): m[j] = (m[j] + 0.9 * U) / (1 + U)
    o = copy.deepcopy(inp); o["revenue_growth"] = g; o["ebit_margin"] = m; return o
res = {}
for tag, f in (("lo", "valuation_dcf_inputs_base_lo.json"), ("point", "valuation_dcf_inputs.json"), ("hi", "valuation_dcf_inputs_base_hi.json")):
    inp = load(f)
    res[tag + "_draft"] = round(dcf(inp)["value_per_share"], 1)
    res[tag + "_one_round"] = round(dcf(one_round(inp))["value_per_share"], 1)
chk = copy.deepcopy(load("valuation_dcf_inputs.json")); chk["sales_to_capital"] = 1.0
res["point_one_round_stc_1.0"] = round(dcf(one_round(chk))["value_per_share"], 1)
print(json.dumps(res, indent=2))
# Rebuild scenarios: base value today = one-round lo..hi; bear and bull unchanged (bull already has two rounds; bear none)
ke = load("valuation_wacc.json")["cost_of_equity"]; T = 5
today = {"bear": [627.0, 787.0], "base": [round(res["lo_one_round"]), round(res["hi_one_round"])], "bull": [1690.0, 2123.0]}
dps = {"bear": [24.0, 24.0], "base": [27.0, 45.0], "bull": [29.0, 55.0]}; prob = {"bear": 0.20, "base": 0.55, "bull": 0.25}
def path(a, b): return [a + (b - a) * i / (T - 1) for i in range(T)]
sc = {}
for k in today:
    d = path(*dps[k]); fv = sum(x * (1 + ke) ** (T - 1 - i) for i, x in enumerate(d))
    sc[k] = {"probability": prob[k], "value_per_share": [round(v * (1 + ke) ** T - fv) for v in today[k]], "dps": dps[k], "value_today": today[k]}
out = {"_comment": "CIO revised scenario set (Stage-3 adjudication): base includes one realised tariff round in year 2 (BEAR-C084/C085); bear (no round) and bull (two rounds) unchanged; horizon convention as valuation_build_scenarios.py.",
       "_sources": {"value_today": "base: calc/cio_base_one_round.out; bear/bull: VAL-C045, VAL-C046", "ke/hurdle": "CIO-C052", "dps": "VAL-C047", "price": "CIO-C001", "probabilities": "VAL-C047"},
       "price": 1778.70, "horizon_years": T, "hurdle_rate": round(ke, 6),
       "intrinsic_value_today": {"low": today["base"][0], "high": today["base"][1]}, "scenarios": sc}
json.dump(out, open(os.path.join(HERE, "cio_scenarios_inputs.json"), "w"), indent=2)
print("base_today", today["base"], "base_horizon", sc["base"]["value_per_share"])
