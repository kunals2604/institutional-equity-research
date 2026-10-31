"""Methodology 3.2.0: the forecasting specialist's tools, the residual-income model, and the sector modules."""

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import research_lib as rl  # noqa: E402
import forecast_tools as ft  # noqa: E402
import valuation_tools as vt  # noqa: E402

PY = sys.executable

LENDER = {
    "base_year": "FY2026", "horizon": 5, "units": "INR crore",
    "base": {"aum": 1000.0, "equity": 200.0, "pat": 38.0, "shares": 10.0},
    "base_prev": {"aum": 800.0},
    "base_drivers": {"nim": 0.10, "cost_ratio": 0.035, "credit_cost": 0.02, "tax": 0.25, "aum_growth": 0.25},
    "drivers": {"aum_growth": {"bear": 0.10, "base": [0.22, 0.14], "bull": 0.25},
                "nim": {"bear": 0.09, "base": 0.10, "bull": 0.105},
                "cost_ratio": 0.035, "credit_cost": {"bear": 0.04, "base": 0.02, "bull": 0.018},
                "tax": 0.25, "payout": 0.2},
    "lines": [{"name": "aum", "formula": "aum_prev * (1 + aum_growth)"},
              {"name": "avg_aum", "formula": "(aum + aum_prev) / 2"},
              {"name": "nii", "formula": "avg_aum * nim"},
              {"name": "pat", "formula": "(nii - avg_aum * cost_ratio - avg_aum * credit_cost) * (1 - tax)"},
              {"name": "dividends", "formula": "pat * payout"},
              {"name": "equity", "formula": "equity_prev + pat - dividends"},
              {"name": "eps", "formula": "pat / 10"}],
    "ties": {"pat": 30.375}, "tie_tolerance": 0.01,
    "outputs": ["aum", "pat", "equity", "eps"],
}


class ForecastToolsTest(unittest.TestCase):
    def test_base_year_ties_and_scenarios_order(self):
        res = ft.model(json.loads(json.dumps(LENDER)))
        self.assertEqual(res["errors"], [])
        self.assertTrue(res["ties"][0]["ok"], res["ties"])
        last = {sc: res["scenarios"][sc]["rows"][-1]["pat"] for sc in ft.SCENARIOS}
        self.assertLess(last["bear"], last["base"])
        self.assertLess(last["base"], last["bull"])
        self.assertEqual(res["scenarios"]["base"]["rows"][0]["label"], "FY2027")

    def test_base_year_tie_fails_when_the_tree_does_not_reproduce_the_reported_figure(self):
        bad = json.loads(json.dumps(LENDER))
        bad["ties"] = {"pat": 45.0}
        res = ft.model(bad)
        self.assertTrue(any("base-year tie pat" in e for e in res["errors"]))

    def test_formulas_are_arithmetic_only(self):
        with self.assertRaises(ValueError):
            ft.safe_eval("__import__('os').system('true')", {})
        self.assertEqual(ft.safe_eval("max(a, 2) * 3", {"a": 1.0}), 6.0)

    def test_hand_off_to_residual_income_and_reconcile(self):
        res = ft.model(json.loads(json.dumps(LENDER)))
        ri = ft.to_valuation(res, "base", "ri", {"cost_of_equity": 0.13, "terminal_growth": 0.06, "shares_diluted": 10})
        self.assertEqual(len(ri["profit"]), 5)
        val = vt.residual_income(ri)
        self.assertGreater(val["value_per_share"], 0)
        rec = ft.reconcile(res, dict(ri, profit=[p * 1.5 for p in ri["profit"]]))
        self.assertTrue(rec["flags"], "a 50 % higher profit path must be flagged")

    def test_consensus_surprise_and_peers(self):
        c = ft.consensus({"snapshots": [{"date": "2026-01-01", "source": "a", "metric": "eps", "period": "FY2027", "mean": 50},
                                        {"date": "2026-06-01", "source": "a", "metric": "eps", "period": "FY2027", "mean": 45,
                                         "high": 50, "low": 40}]})
        self.assertAlmostEqual(c["rows"][0]["revision"], -0.1)
        s = ft.surprise({"quarters": [{"period": "Q1FY2026", "metric": "pat", "actual": 110, "consensus": 100},
                                      {"period": "Q2FY2026", "metric": "pat", "actual": 95, "consensus": 100}]})
        self.assertEqual(s["stats"]["pat"]["beat_rate"], 0.5)
        p = ft.peers({"subject": "A", "higher_is_better": {"pe": False},
                      "rows": [{"company": "A", "roe": 0.2, "pe": 30}, {"company": "B", "roe": 0.1, "pe": 20},
                               {"company": "C", "roe": 0.15, "pe": 10}]})
        self.assertEqual(p["metrics"]["roe"]["subject_percentile"], 1.0)
        self.assertEqual(p["metrics"]["pe"]["subject_percentile"], 0.0)


class ResidualIncomeTest(unittest.TestCase):
    BASE = {"years": 10, "base_equity": 100000, "profit": [19000 * 1.15 ** i for i in range(10)], "payout": 0.2,
            "cost_of_equity": 0.13, "terminal_growth": 0.06, "terminal_roe": 0.15, "shares_diluted": 6226}

    def test_value_above_book_when_roe_exceeds_cost_of_equity(self):
        r = vt.residual_income(dict(self.BASE))
        self.assertGreater(r["price_to_book_at_value"], 1.0)
        self.assertAlmostEqual(r["justified_pb_terminal_roe"], (0.15 - 0.06) / (0.13 - 0.06))

    def test_equity_raised_without_more_profit_dilutes(self):
        before = vt.residual_income(dict(self.BASE))["value_per_share"]
        cheap = vt.residual_income(dict(self.BASE, equity_issuance=[17500] + [0] * 9, issue_price=20.0))["value_per_share"]
        self.assertLess(cheap, before)

    def test_issuance_needs_a_price(self):
        with self.assertRaises(ValueError):
            vt.residual_income(dict(self.BASE, equity_issuance=[1000] + [0] * 9))


class SectorModulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-mod-"))
        r = subprocess.run([PY, str(ROOT / "scripts" / "new_run.py"), "--ticker", "FIXCO", "--company", "FixCo Ltd",
                            "--exchange", "NSE", "--segment", "main", "--cutoff", "2026-03-01", "--run-id",
                            "20260301T090000Z", "--root", str(self.tmp)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        self.run = self.tmp / r.stdout.strip()
        m = rl.load_json(self.run / rl.RUN_MANIFEST)
        m["methodology_version"] = "3.2.0"
        m["sector_modules"] = ["nbfc"]
        rl.write_json(self.run / rl.RUN_MANIFEST, m)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_catalogue_and_run_steps(self):
        steps = rl.sector_steps_for(self.run, "financials")
        self.assertEqual([s["id"] for s in steps], ["NBFC-1", "NBFC-2", "NBFC-4"])
        self.assertEqual(rl.sector_steps_for(self.run, "valuation"), [])

    def test_checklist_needs_a_row_per_module_step(self):
        body = "## Method Coverage Checklist\n\n| # | Step | Status | Where | Notes |\n|---|---|---|---|---|\n"
        body += "".join("| %d | %s | Done | x | |\n" % (i, s) for i, s in enumerate(rl.method_steps("financials", rl.V32), 1))
        res = rl.Result("t")
        extra = [(s["id"], s["step"]) for s in rl.sector_steps_for(self.run, "financials")]
        rl.check_method_checklist("financials", body + "\n## Next\n", res, rl.V32, extra)
        self.assertTrue(any("NBFC-1" in e for e in res.errors))
        body += "| N1 | NBFC-1 ALM | Done | x | |\n| N2 | NBFC-2 funding | Done | x | |\n| N4 | NBFC-4 lagged | Partial | x | tried |\n"
        res = rl.Result("t")
        rl.check_method_checklist("financials", body + "\n## Next\n", res, rl.V32, extra)
        self.assertFalse([e for e in res.errors if "sector-module" in e], res.errors)

    def test_done_module_step_needs_its_metric_series(self):
        import verify
        rep = self.run / "specialists" / "financials.md"
        rep.write_text("## Method Coverage Checklist\n\n| # | Step | Status | Where | Notes |\n|---|---|---|---|---|\n"
                       "| N1 | NBFC-1 ALM | Done | FIN-C001 | |\n\n## Next\n", encoding="utf-8")
        rows = [{"claim_id": "FIN-C001", "tag": "FACT", "metric": "alm_gap_1y_ratio", "value": "0.05", "period": "FY2026"}]
        f = verify.sector_module_findings(self.run, "financials", rows)
        self.assertEqual(f[0]["check"], "SECTOR_MODULE_EVIDENCE")
        rows = [dict(rows[0], claim_id="FIN-C%03d" % i, period="FY%d" % (2022 + i)) for i in range(5)]
        self.assertEqual(verify.sector_module_findings(self.run, "financials", rows), [])

    def test_brief_carries_the_steps_and_refuses_without_a_selection(self):
        import agent_driver
        (self.run / "engine").mkdir(exist_ok=True)
        (self.run / "engine" / "identity.md").write_text("IDENTITY\n", encoding="utf-8")
        text = agent_driver.specialist_prompt(self.run, "filings")
        self.assertIn("NBFC-3 Stage-wise ECL roll-forward", text)
        m = rl.load_json(self.run / rl.RUN_MANIFEST)
        m["sector_modules"] = None
        rl.write_json(self.run / rl.RUN_MANIFEST, m)
        with self.assertRaises(SystemExit):
            agent_driver.specialist_prompt(self.run, "filings")


if __name__ == "__main__":
    unittest.main()
