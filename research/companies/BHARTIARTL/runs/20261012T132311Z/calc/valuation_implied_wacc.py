#!/usr/bin/env python3
"""Solve for the WACC that equates the BASE DCF (calc/valuation_dcf_inputs.json, operating assumptions held) and the BULL DCF to the price.
Uses scripts/valuation_tools.dcf (no new valuation math). Run: python3 calc/valuation_implied_wacc.py RUN_DIR"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[6] / "scripts"))
import valuation_tools as vt
run = Path(sys.argv[1]); price = 1778.70
out = {}
for name in ("", "_bull", "_base_hi"):
    inp = json.loads((run / ("calc/valuation_dcf_inputs%s.json" % name)).read_text())
    f = lambda w: vt.dcf(inp, {"wacc": w})["value_per_share"] - price
    w = vt.bisect(f, inp["terminal_growth"] + 0.006, 0.20)
    out["implied_wacc" + (name or "_base")] = w
# Ke equivalent if debt weight and Kd unchanged (VAL-C027 inputs)
wi = json.loads((run / "calc/valuation_wacc_inputs.json").read_text())
kd = wi["cost_of_debt_pretax"] * (1 - wi["tax_rate"]); wd = wi["debt_weight"]
out["implied_ke"] = {k.replace("implied_wacc", "ke"): (v - kd * wd) / (1 - wd) for k, v in out.items() if v}
(run / "calc/valuation_implied_wacc.json").write_text(json.dumps(out, indent=2)); print(json.dumps(out, indent=2))
