"""Step 6: the verdict is a reasoned judgment. No gate, test, table or threshold sets or caps it; the guide stands beside it."""

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_scorecard as bs  # noqa: E402
import research_lib as rl  # noqa: E402

REASONING = {"for": "Returns on capital rose for a decade on rising share [FACT: FIN-C031].",
             "against": "The price needs growth the record does not show [CALCULATION: VAL-C044].",
             "judgment": "On balance the evidence for the franchise outweighs the valuation risk for a five-year holder."}


class VerdictBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-verdict-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.base = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))

    def check(self, sc):
        path = self.tmp / "scorecard.json"
        path.write_text(json.dumps(sc), encoding="utf-8")
        return rl.validate_scorecard(path)

    def errors(self, sc):
        return [e for e in self.check(sc).errors if "erdict" in e or "guide" in e or "easoning" in e or "eparture" in e]


class ValidationTests(VerdictBase):
    def test_the_example_is_a_valid_judgment(self):
        self.assertEqual(self.check(self.base).errors, [])

    def test_a_verdict_may_differ_from_the_guide_with_its_reason(self):
        sc = copy.deepcopy(self.base)
        sc["verdict"] = "BUY"
        sc["guide_departure"] = "The guide's margin-of-safety table cannot see the owner's five-year horizon here."
        self.assertEqual(self.errors(sc), [])

    def test_no_distance_from_the_guide_is_too_far(self):
        sc = copy.deepcopy(self.base)
        sc["verdict"] = "STRONG BUY"
        sc["guide_departure"] = "The guide weighs a single gap several times over, and the evidence does not."
        self.assertNotEqual(sc["verdict"], sc["mapped_verdict"])
        self.assertEqual(self.errors(sc), [])

    def test_a_departure_must_say_why(self):
        sc = copy.deepcopy(self.base)
        sc["verdict"] = "BUY"
        sc.pop("guide_departure", None)
        self.assertTrue(self.errors(sc))

    def test_a_verdict_needs_its_reasoning(self):
        sc = copy.deepcopy(self.base)
        sc.pop("verdict_reasoning")
        self.assertTrue(self.errors(sc))

    def test_the_reasoning_must_weigh_both_sides(self):
        sc = copy.deepcopy(self.base)
        sc["verdict_reasoning"] = dict(REASONING, against="")
        self.assertTrue(self.errors(sc))

    def test_the_reasoning_must_cite_the_evidence(self):
        sc = copy.deepcopy(self.base)
        sc["verdict_reasoning"] = {k: "words without any citation at all, however many of them there are." for k in REASONING}
        self.assertTrue(self.errors(sc))

    def test_the_guide_itself_cannot_be_changed(self):
        sc = copy.deepcopy(self.base)
        sc["mapped_verdict"] = "STRONG BUY"
        self.assertTrue(any("maps to" in e for e in self.check(sc).errors))

    def test_a_stale_price_is_refused(self):
        sc = copy.deepcopy(self.base)
        sc["price"]["timestamp"] = "2025-01-01 15:30 IST close"
        self.assertTrue(any("before the cutoff" in e for e in self.check(sc).errors))

    def test_a_score_cannot_be_reverse_engineered_past_the_recomputation(self):
        sc = copy.deepcopy(self.base)
        sc["investment_attractiveness"]["final"] += 15
        self.assertTrue(self.check(sc).errors)


class EarlierRunsTests(VerdictBase):
    """A run keeps the contract it was made under."""

    def older(self, **change):
        return dict(copy.deepcopy(self.base), methodology_version="3.2.0", **change)

    def test_a_3_2_scorecard_keeps_its_one_notch_rule(self):
        sc = self.older(verdict="STRONG BUY", override_reason="because")
        self.assertTrue(any("notches" in e for e in self.check(sc).errors))

    def test_a_3_2_scorecard_needs_no_reasoning_block(self):
        sc = self.older()
        sc.pop("verdict_reasoning")
        self.assertEqual(self.errors(sc), [])


class BuildTests(VerdictBase):
    def inputs(self, **change):
        sc = copy.deepcopy(self.base)
        for k in ("mapped_verdict", "decision"):
            sc.pop(k, None)
        sc.update(change)
        return sc

    def test_the_cio_writes_the_verdict_and_the_build_does_not_change_it(self):
        sc = bs.compute(self.inputs(verdict="BUY", guide_departure="A reason the guide cannot see in its tables."))
        self.assertEqual(sc["verdict"], "BUY")
        self.assertEqual(sc["mapped_verdict"], "HOLD / NEUTRAL")

    def test_a_scorecard_with_no_verdict_is_refused(self):
        sc = self.inputs()
        sc.pop("verdict")
        with self.assertRaisesRegex(ValueError, "the CIO writes the verdict"):
            bs.compute(sc)


if __name__ == "__main__":
    unittest.main()
