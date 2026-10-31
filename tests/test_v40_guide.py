"""The computed guide behaves sensibly across business types. It tests the guide only: it does not constrain a verdict."""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import research_lib as rl  # noqa: E402
import valuation_tools as vt  # noqa: E402

LAYERS = {"L1": "Layer 1 — Bedrock Compounder", "L2": "Layer 2 — High-Growth Business",
          "L3": "Layer 3 — Cyclical / Event-Driven Opportunity", "L4": "Layer 4 — Venture-Style / Optionality Bet"}
PRICES = [300, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1500, 2000, 3000]
BUY_CLASS = ("STRONG BUY", "BUY", "SPECULATIVE BUY")
BASE = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))


def card(layer, conf, bq, other):
    c = copy.deepcopy(BASE)
    c.update(methodology_version=rl.methodology_version(), primary_layer=LAYERS[layer], secondary_layers=[])
    for d in c["business_quality"]["dimensions"]:
        d.update(score=bq, confidence=conf)
    c["business_quality"].update(confidence=conf, gates_triggered=[])
    for d in c["investment_attractiveness"]["dimensions"]:
        d["confidence"] = conf
        if d["id"] not in ("IA1", "IA2", "IA4"):
            d["score"] = other
    c["investment_attractiveness"].update(confidence=conf, gates_triggered=[])
    return c


def scenarios(bear, base, bull, h=0.12):
    return vt.scenario_build({"price": 1000, "horizon_years": 5, "hurdle_rate": h, "scenarios": {
        "bear": {"probability": .25, "value_today": bear, "dps": 0}, "base": {"probability": .5, "value_today": base, "dps": 0},
        "bull": {"probability": .25, "value_today": bull, "dps": 0}}})


def verdicts(c, s):
    return [(r["price"], r["mapped_verdict"]) for r in vt.price_ladder(s, PRICES, c)["rows"]]


ARCHETYPES = {
    "compounder": ("L1", "High", 85, 75, (700, 1000, 1400)),
    "good compounder": ("L1", "Medium", 75, 65, (700, 1000, 1400)),
    "grower": ("L2", "Medium", 80, 70, (600, 1000, 1800)),
    "cyclical": ("L3", "Medium", 70, 70, (500, 1000, 1600)),
    "option": ("L4", "Medium", 70, 70, (200, 1000, 4000)),
    "weak business": ("L1", "Medium", 45, 40, (500, 800, 1100)),
}


class GuideTests(unittest.TestCase):
    def test_a_lower_price_never_gives_a_worse_guide(self):
        for name, (layer, conf, bq, other, s) in ARCHETYPES.items():
            notches = [rl.NOTCH[v] for _, v in verdicts(card(layer, conf, bq, other), scenarios(*s))]
            self.assertEqual(notches, sorted(notches, reverse=True), name)

    def test_every_sound_archetype_can_reach_a_buy_class_guide(self):
        for name, (layer, conf, bq, other, s) in ARCHETYPES.items():
            if name == "weak business":
                continue
            got = {v for _, v in verdicts(card(layer, conf, bq, other), scenarios(*s))}
            self.assertTrue(got & set(BUY_CLASS), "%s: %s" % (name, got))

    def test_a_high_enough_price_stops_being_a_buy_for_every_archetype(self):
        for name, (layer, conf, bq, other, s) in ARCHETYPES.items():
            self.assertNotIn(verdicts(card(layer, conf, bq, other), scenarios(*s))[-1][1], BUY_CLASS, name)

    def test_a_weak_business_at_a_rich_price_is_an_avoid_class_guide(self):
        got = dict(verdicts(card("L1", "Medium", 45, 25), scenarios(500, 800, 1100)))
        self.assertIn(got[3000], ("AVOID", "STRONG AVOID"))


if __name__ == "__main__":
    unittest.main()
