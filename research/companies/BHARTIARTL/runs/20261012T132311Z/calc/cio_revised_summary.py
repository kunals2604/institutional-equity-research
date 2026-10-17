"""CIO: summary figures for the revised (one-round base) scenario set."""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
s = json.load(open(os.path.join(H, "cio_scenarios_inputs.json")))["scenarios"]
r = json.load(open(os.path.join(H, "cio_scenario_irr_revised.json")))
pwv = sum(v["probability"] * sum(v["value_today"]) / 2 for v in s.values())
base_mid = sum(s["base"]["value_today"]) / 2
price = 1778.70
print("probability_weighted_value_today=%.0f" % pwv)
print("base_mid=%.1f price_premium_to_base_mid=%.3f" % (base_mid, price / base_mid - 1))
print("expected_irr=%.4f mos=%.4f" % (r["expected_irr"], r["margin_of_safety"]))
print("two_round_point (BEAR-C085)=1519; price_premium_to_two_round=%.3f" % (price / 1519 - 1))
