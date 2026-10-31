"""Defect group D: the forecast must really reach the valuation (docs/V4_DEFECT_REGISTER.md)."""

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import forecast_tools as ft  # noqa: E402
import research_lib as rl  # noqa: E402
import synthesis  # noqa: E402


def model(rows=None, errors=None):
    rows = rows or [{"revenue": 110.0, "ebit": 22.0, "pat": 18.0, "equity": 100.0},
                    {"revenue": 121.0, "ebit": 24.2, "pat": 18.0, "equity": 118.0}]
    return {"base_year": 2026, "errors": errors or [],
            "scenarios": {"base": {"rows": rows, "summary": {"cagr_revenue": 0.10}}}}


class ReconcileTests(unittest.TestCase):
    """D2 and D4."""

    def test_a_comparison_of_nothing_is_an_error_not_agreement(self):
        with self.assertRaisesRegex(ValueError, "nothing"):
            ft.reconcile(model(), {"unrelated": 1})

    def test_a_forecast_with_no_revenue_summary_compares_nothing(self):
        m = model()
        m["scenarios"]["base"]["summary"] = {}
        with self.assertRaisesRegex(ValueError, "nothing"):
            ft.reconcile(m, {"revenue_growth": 0.1})

    def test_the_same_path_agrees(self):
        self.assertEqual(ft.reconcile(model(), {"revenue_growth": 0.10})["flags"], [])

    def test_a_real_difference_is_flagged(self):
        self.assertTrue(ft.reconcile(model(), {"revenue_growth": 0.20})["flags"])

    def test_identical_profit_paths_give_the_same_roe(self):
        got = ft.reconcile(model(), {"profit": [18.0, 18.0], "base_equity": 34.7})
        self.assertEqual(got["flags"], [])
        self.assertAlmostEqual(got["comparisons"]["average_roe"]["forecast"], got["comparisons"]["average_roe"]["valuation"])

    def test_the_command_exits_non_zero_when_nothing_was_compared(self):
        tmp = Path(tempfile.mkdtemp(prefix="eqr-rec-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "f.json").write_text(json.dumps(model()), encoding="utf-8")
        (tmp / "v.json").write_text("{}", encoding="utf-8")
        self.assertEqual(ft.main(["reconcile", "--forecast", str(tmp / "f.json"), "--valuation", str(tmp / "v.json")]), 1)


class ToValuationTests(unittest.TestCase):
    """D3."""

    def test_an_unknown_base_is_refused_rather_than_assumed_flat(self):
        with self.assertRaisesRegex(ValueError, "base_revenue"):
            ft.to_valuation(model(), "base", "fcff", {})

    def test_a_given_base_gives_the_true_first_year(self):
        got = ft.to_valuation(model(), "base", "fcff", {"base_revenue": 100.0})
        self.assertAlmostEqual(got["revenue_growth"][0], 0.10)

    def test_a_driver_growth_is_enough(self):
        rows = [dict(r, revenue_growth=0.10) for r in model()["scenarios"]["base"]["rows"]]
        got = ft.to_valuation(model(rows), "base", "fcff", {})
        self.assertAlmostEqual(got["revenue_growth"][0], 0.10)

    def test_a_model_that_failed_its_own_checks_is_not_handed_on(self):
        with self.assertRaisesRegex(ValueError, "failed its own checks"):
            ft.to_valuation(model(errors=["the base year does not tie"]), "base", "fcff", {"base_revenue": 100.0})


class HandoffTests(unittest.TestCase):
    """D1: valuation on the forecast is a step that happened, not a sentence in cio.md."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-handoff-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "specialists").mkdir()
        (self.tmp / "calc").mkdir()
        (self.tmp / rl.RUN_MANIFEST).write_text(json.dumps({"methodology_version": "3.2.0"}), encoding="utf-8")
        (self.tmp / "specialists" / "forecasting.md").write_text("x", encoding="utf-8")

    def done(self):
        (self.tmp / "calc" / "forecasting_to_valuation.json").write_text("{}", encoding="utf-8")
        (self.tmp / "calc" / "forecasting_reconcile.json").write_text(
            json.dumps({"comparisons": {"revenue_cagr": {}}, "flags": []}), encoding="utf-8")
        (self.tmp / "specialists" / "valuation_followup_1.md").write_text("x", encoding="utf-8")

    def test_a_run_that_skipped_it_is_stopped(self):
        self.assertEqual(len(synthesis.handoff_errors(self.tmp)), 3)

    def test_a_reconcile_that_compared_nothing_does_not_count(self):
        self.done()
        (self.tmp / "calc" / "forecasting_reconcile.json").write_text('{"comparisons": {}}', encoding="utf-8")
        self.assertEqual(len(synthesis.handoff_errors(self.tmp)), 1)

    def test_a_run_that_did_it_passes(self):
        self.done()
        self.assertEqual(synthesis.handoff_errors(self.tmp), [])

    def test_a_run_with_no_forecasting_report_is_not_asked(self):
        (self.tmp / "specialists" / "forecasting.md").unlink()
        self.assertEqual(synthesis.handoff_errors(self.tmp), [])


class ContractTests(unittest.TestCase):
    def test_d5_the_valuation_command_uses_only_flags_the_script_has(self):
        text = (ROOT / ".claude" / "agents" / "valuation.md").read_text(encoding="utf-8")
        line = next(l for l in text.splitlines() if "market_data.py history" in l)
        src = (ROOT / "scripts" / "market_data.py").read_text(encoding="utf-8")
        for flag in re.findall(r"(--[a-z-]+)", line.split("`")[1]):
            self.assertIn('"%s"' % flag, src, flag)
        self.assertIn("--end", line)

    def test_d6_a_non_march_year_end_is_read_from_the_manifest(self):
        self.assertEqual(rl.fy_end_month({"fiscal_year_end": "12-31"}), 12)
        self.assertEqual(rl.fy_end_month({}), 3)
        self.assertEqual(rl.fy_end_month({"fiscal_year_end": "bad"}), 3)


if __name__ == "__main__":
    unittest.main()
