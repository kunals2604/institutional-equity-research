#!/usr/bin/env python3
"""Build calc/valuation_scenarios.json for valuation_tools.py scenario-irr / price-ladder.
Horizon (5-year) value per share = today's scenario DCF value rolled forward at the cost of equity, less the
future value of dividends paid in between (i.e. the price converges to scenario intrinsic value at the horizon).
Run: python3 -I calc/valuation_build_scenarios.py RUN_DIR"""
import json, sys
from pathlib import Path
run = Path(sys.argv[1]); C = run / "calc"
ke = json.loads((C / "valuation_wacc.json").read_text())["cost_of_equity"]
T = 5
today = {  # INR per share, low/high from scripts/valuation_tools.py dcf outputs (see _sources)
    "bear": [627.0, 787.0],   # valuation_dcf_bear.json sensitivity, WACC 11.53% / 10.53%
    "base": [1145.0, 1342.0], # valuation_dcf_base_lo.json / valuation_dcf_base_hi.json (point 1,215: valuation_dcf.json)
    "bull": [1690.0, 2123.0], # valuation_dcf_bull.json sensitivity, WACC 11.53% / 10.53%
}
dps = {"bear": [24.0, 24.0], "base": [27.0, 45.0], "bull": [29.0, 55.0]}
prob = {"bear": 0.20, "base": 0.55, "bull": 0.25}
def path(a, b): return [a + (b - a) * i / (T - 1) for i in range(T)]
sc = {}
for k in today:
    d = path(*dps[k]); fv_div = sum(x * (1 + ke) ** (T - 1 - i) for i, x in enumerate(d))
    hv = [round(v * (1 + ke) ** T - fv_div) for v in today[k]]
    sc[k] = {"probability": prob[k], "value_per_share": hv, "dps": dps[k], "value_today": today[k]}
out = {"_comment": "5-year horizon values = scenario DCF value today x (1+Ke)^5 - FV of interim dividends; probabilities: bear 20% (reference: one destructive price war, 2016-19, in ~20 years of Indian wireless history, now a 2.5-player market), base 55%, bull 25% (two tariff rounds plus adjacencies scaling).",
       "_sources": {"value_today": "VAL-C044, VAL-C045, VAL-C046", "ke/hurdle": "VAL-C026", "dps": "VAL-C039 (FY2026 INR 24) and VAL-C047", "price": "CIO-C001", "probabilities": "VAL-C047"},
       "price": 1778.70, "horizon_years": T, "hurdle_rate": round(ke, 6),
       "intrinsic_value_today": {"low": today["base"][0], "high": today["base"][1]}, "scenarios": sc}
(C / "valuation_scenarios.json").write_text(json.dumps(out, indent=2)); print(json.dumps(out, indent=2))
