"""Tests for the institutional research layer: depth standard, metrics engine, valuation math,
provenance tooling, numeric reconciliation, evidence statistics and decision outputs.

Run:  python3 -m unittest discover tests -v
All data here is synthetic (FIXTURECO / example.invalid). Nothing is research on a real company.
"""

import copy
import csv
import http.server
import json
import math
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import fin_metrics  # noqa: E402
import valuation_tools as vt  # noqa: E402
import html_tables  # noqa: E402
from test_research_system import FixtureRun, run, write_ledger, fact_row, specialist_report  # noqa: E402


class TestHistoricalDepthStandard(unittest.TestCase):
    def setUp(self):
        self.fx = FixtureRun()

    def tearDown(self):
        self.fx.cleanup()

    def check(self, name, text):
        p = self.fx.dir / "specialists" / ("%s.md" % name)
        p.write_text(text, encoding="utf-8")
        _, ids = rl.validate_ledger(self.fx.dir / "specialists" / ("%s_ledger.csv" % name))
        return rl.validate_specialist_report(p, ids)

    def test_short_history_is_an_error_for_hard_rules(self):
        for name in ("financials", "concalls", "valuation"):
            res = self.check(name, specialist_report(name, self.fx.run_id, coverage=False))
            self.assertTrue(any("Historical depth" in e for e in res.errors), (name, res.errors))

    def test_exception_downgrades_to_warning(self):
        text = specialist_report("financials", self.fx.run_id, coverage=False).replace(
            "report_status: complete", "report_status: complete\ncoverage_exception: Listed in 2019; RHP gives FY2016-FY2018")
        res = self.check("financials", text)
        self.assertFalse(any("Historical depth" in e for e in res.errors))
        self.assertTrue(any("coverage_exception" in w for w in res.warnings))

    def test_soft_rules_warn_only(self):
        res = self.check("management", specialist_report("management", self.fx.run_id, coverage=False))
        self.assertFalse(any("Historical depth" in e for e in res.errors))
        self.assertTrue(any("Historical depth" in w for w in res.warnings))

    def test_full_coverage_passes(self):
        for name in ("financials", "concalls", "valuation"):
            res = self.check(name, specialist_report(name, self.fx.run_id))
            self.assertFalse(any("Historical depth" in e for e in res.errors), name)

    def test_period_counters(self):
        self.assertEqual(len(rl.fiscal_years("FY2011 FY12 FY 2013 | FY2013")), 3)
        self.assertEqual(rl.quarters("Q1FY25, Q1 FY2025, Q2FY2025"), {"Q1FY2025", "Q2FY2025"})


def write_history(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fin_metrics.REQUIRED_COLS)
        w.writeheader()
        for r in rows:
            base = {"unit": "INR crore", "basis": "consolidated", "source_tier": "1",
                    "source_url_or_id": "https://example.invalid/ar.pdf", "locator": "p.1", "verified": "Y", "note": ""}
            base.update(r)
            w.writerow(base)


def general_history(years=range(2014, 2026)):
    rows = []
    for i, y in enumerate(years):
        rev = 1000 * 1.1 ** i
        pbt = 0.20 * rev + 10 - 20
        tax = 0.25 * pbt
        pat = pbt - tax
        items = {"revenue": rev, "cogs": 0.5 * rev, "employee_cost": 0.1 * rev, "other_opex": 0.15 * rev,
                 "depreciation": 0.05 * rev, "other_income": 10, "interest_expense": 20, "pbt": pbt, "tax": tax,
                 "pat": pat, "pat_attributable": pat, "total_assets": 1.2 * rev, "current_assets": 0.4 * rev,
                 "current_liabilities": 0.3 * rev, "cash_and_equivalents": 0.05 * rev, "total_debt": 0.2 * rev,
                 "total_equity": 0.6 * rev, "trade_receivables": 0.1 * rev, "inventories": 0.1 * rev,
                 "trade_payables": 0.12 * rev, "net_fixed_assets": 0.5 * rev, "cfo": 0.9 * pat, "capex": 0.06 * rev,
                 "dividends_paid": 0.3 * pat, "shares_basic": 10, "shares_diluted": 10}
        for k, v in items.items():
            row = {"item": k, "period": "FY%d" % y, "value": "%.6f" % v}
            if k.startswith("shares"):
                row["unit"] = "crore shares"
            rows.append(row)
    return rows


class TestFinMetrics(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def compute(self, rows, profile="general"):
        p = self.tmp / "h.csv"
        write_history(p, rows)
        kept, errors, _ = fin_metrics.load(p, None)
        self.assertEqual(errors, [])
        out, _ = fin_metrics.compute(fin_metrics.Data(kept, "consolidated"), profile)
        return {(r["metric"], r["period"]): r["value"] for r in out}

    def test_general_formulas(self):
        m = self.compute(general_history())
        rev = lambda y: 1000 * 1.1 ** (y - 2014)  # noqa: E731
        self.assertAlmostEqual(m[("ebitda_margin", "FY2025")], 0.25, places=6)
        self.assertAlmostEqual(m[("ebit_margin", "FY2025")], 0.20, places=6)
        self.assertAlmostEqual(m[("roce", "FY2025")], 0.2 * rev(2025) / (0.9 * (rev(2024) + rev(2025)) / 2), places=6)
        self.assertAlmostEqual(m[("dso", "FY2025")], 36.5, places=4)
        self.assertAlmostEqual(m[("cagr_revenue_10y", "FY2025")], 0.10, places=6)
        self.assertAlmostEqual(m[("revenue_growth", "FY2025")], 0.10, places=6)
        pat = (0.2 * rev(2025) - 10) * 0.75
        self.assertAlmostEqual(m[("eps", "FY2025")], pat / 10, places=4)
        self.assertAlmostEqual(m[("cfo_to_pat", "FY2025")], 0.9, places=6)
        self.assertAlmostEqual(m[("net_debt", "FY2025")], 0.15 * rev(2025), places=4)
        for k in ("roic", "incremental_roic_5y", "piotroski_f_score", "beneish_m_score", "accruals_ratio", "reinvestment_rate"):
            self.assertIn((k, "FY2025"), m, k)

    def test_lender_profile(self):
        rows = []
        for i, y in enumerate((2023, 2024, 2025)):
            adv = 1000 * (1 + 0.2 * i)
            vals = {"interest_income": 0.14 * adv, "interest_expense": 0.07 * adv, "fee_income": 0.02 * adv,
                    "opex": 0.03 * adv, "provisions": 0.015 * adv, "pat": 0.03 * adv, "pat_attributable": 0.03 * adv,
                    "advances": adv, "total_assets": 1.1 * adv, "total_equity": 0.18 * adv, "gnpa": 0.03 * adv,
                    "nnpa": 0.012 * adv, "borrowings": 0.85 * adv}
            rows += [{"item": k, "period": "FY%d" % y, "value": "%.6f" % v} for k, v in vals.items()]
        m = self.compute(rows, "lender")
        self.assertAlmostEqual(m[("nii", "FY2025")], 0.07 * 1400, places=4)
        self.assertAlmostEqual(m[("nim", "FY2025")], 0.07 * 1400 / 1300, places=6)
        self.assertAlmostEqual(m[("pcr", "FY2025")], 0.6, places=6)
        self.assertAlmostEqual(m[("credit_cost", "FY2025")], 0.015 * 1400 / 1300, places=6)
        self.assertIn(("cost_to_income", "FY2025"), m)

    def test_dataset_validation(self):
        bad = general_history(range(2024, 2026))
        bad.append(dict(bad[0]))                                        # duplicate
        bad.append({"item": "revenue", "period": "FY2023", "value": "1", "locator": ""})  # no locator
        bad.append({"item": "pat", "period": "FY2023", "value": "1", "source_tier": "5", "verified": "Y"})
        bad.append({"item": "cfo", "period": "FY2023", "value": "1", "unit": "INR million"})
        bad.append({"item": "magic_number", "period": "FY2023", "value": "1"})
        p = self.tmp / "bad.csv"
        write_history(p, bad)
        _, errors, _ = fin_metrics.load(p, None)
        text = " ".join(errors)
        for frag in ("duplicate", "locator", "verified=Y", "mixed units", "not a METRIC_DEFINITIONS key"):
            self.assertIn(frag, text)

    def test_cli_and_depth_warning(self):
        p = self.tmp / "h.csv"
        write_history(p, general_history(range(2020, 2026)))
        r = run("fin_metrics.py", p, "--out", self.tmp / "m.csv")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Historical Depth Standard", r.stdout)
        self.assertTrue((self.tmp / "m.csv").exists())


class TestValuationTools(unittest.TestCase):
    base = {"base_revenue": 1000, "years": 5, "revenue_growth": 0.0, "ebit_margin": 0.2, "tax_rate": 0.25,
            "sales_to_capital": 2.0, "wacc": 0.10, "terminal_growth": 0.0, "terminal_roic": 0.10,
            "net_debt": 0, "shares_diluted": 10, "mid_year": False}

    def test_dcf_perpetuity_identity(self):
        res = vt.dcf(self.base)
        nopat = 1000 * 0.2 * 0.75
        self.assertAlmostEqual(res["enterprise_value"], nopat / 0.10, places=6)
        self.assertAlmostEqual(res["value_per_share"], nopat / 0.10 / 10, places=6)

    def test_dcf_rejects_g_above_wacc_and_warns(self):
        with self.assertRaises(ValueError):
            vt.dcf(dict(self.base, terminal_growth=0.12))
        res = vt.dcf(dict(self.base, terminal_growth=0.05, terminal_roic=0.08, risk_free_rate=0.04))
        self.assertTrue(any("below WACC" in w for w in res["warnings"]))
        self.assertTrue(any("risk-free" in w for w in res["warnings"]))

    def test_reverse_dcf_recovers_growth(self):
        inp = dict(self.base, terminal_growth=0.03, terminal_roic=0.15)
        price = vt.dcf(inp, {"revenue_growth": 0.08})["value_per_share"]
        res = vt.reverse_dcf(inp, price, "growth")
        self.assertAlmostEqual(res["implied_value"], 0.08, places=4)

    def test_irr_and_scenarios(self):
        self.assertAlmostEqual(vt.irr([-1000, 0, 0, 0, 0, 2000]), 2 ** 0.2 - 1, places=6)
        inp = {"price": 1000, "horizon_years": 5, "intrinsic_value_today": {"low": 900, "high": 1100},
               "scenarios": {"bear": {"probability": 0.5, "value_per_share": 500},
                             "bull": {"probability": 0.5, "value_per_share": 2500}}}
        s = vt.scenarios(inp)
        self.assertAlmostEqual(s["expected_irr"], 1.5 ** 0.2 - 1, places=6)
        self.assertAlmostEqual(s["asymmetry_ratio"], 3.0, places=6)
        self.assertAlmostEqual(s["margin_of_safety"], 0.0, places=6)
        with self.assertRaises(ValueError):
            vt.scenarios(dict(inp, scenarios={"x": {"probability": 0.7, "value_per_share": 1}}))

    def test_anchor_mapping_matches_scoring_bands(self):
        for m, s in ((0.40, 90), (0.25, 75), (0.10, 60), (-0.10, 40), (-0.30, 20)):
            self.assertEqual(vt.ia1(m), s, m)
        h = 0.12
        for e, s in ((h + 0.08, 90), (h + 0.04, 75), (h, 60), (h - 0.04, 40), (0.0, 20)):
            self.assertEqual(vt.ia2(e, h), s, e)
        for r, s in ((3, 90), (2, 70), (1.2, 50), (0.8, 30), (float("inf"), 100)):
            self.assertEqual(vt.ia4(r), s, r)

    def test_price_ladder_monotone_with_triggers(self):
        sc = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))
        inp = json.loads((ROOT / "templates" / "scenarios.example.json").read_text(encoding="utf-8"))
        res = vt.price_ladder(inp, [600, 800, 1000, 1200, 1400, 1800], sc)
        ias = [r["ia_final"] for r in res["rows"]]
        self.assertEqual(ias, sorted(ias, reverse=True))
        self.assertIn("buy_below", res["decision_triggers"])

    def test_sizing_and_decompose(self):
        policy = {"reference_position": 1_000_000, "liquidity": {"max_days_to_exit": 20, "max_adtv_participation": 0.2},
                  "risk_limits": {"portfolio_aum": 100_000_000, "max_position_pct": 8, "max_loss_per_position_pct": 2,
                                  "speculative_max_position_pct": 2}}
        res = vt.sizing_ceiling({"price": 100, "bear_value_with_dividends": 60, "adtv": 5_000_000}, policy)
        self.assertAlmostEqual(res["components"]["loss_budget_cap_pct"], 5.0)
        self.assertAlmostEqual(res["components"]["liquidity_cap_pct"], 20.0)
        self.assertAlmostEqual(res["sizing_ceiling_pct"], 5.0)
        self.assertAlmostEqual(res["days_to_exit_reference_position"], 1.0)
        none = vt.sizing_ceiling({"price": 100, "bear_value_with_dividends": 60}, {"risk_limits": {}})
        self.assertIsNone(none["sizing_ceiling_pct"])
        d = vt.decompose({"years": 5, "eps_growth": 0.10, "start_pe": 20, "end_pe": 20, "dividend_yield": 0.02})
        self.assertAlmostEqual(d["approx_annual_return"], 0.12, places=9)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class TestProvenanceTools(unittest.TestCase):
    def setUp(self):
        self.fx = FixtureRun()
        self.www = Path(tempfile.mkdtemp())
        (self.www / "ar.pdf").write_bytes(b"%PDF-1.4\n1 0 obj << /Type /Page >> 2 0 obj << /Type /Page >> /Type /Pages\n%%EOF")
        (self.www / "t.html").write_text("<html><body><table><tr><th>Item</th><th colspan='2'>FY</th></tr>"
                                         "<tr><td>Revenue</td><td>1,000</td><td>1,100</td></tr></table>"
                                         "<table><tr><td>Other</td></tr></table></body></html>", encoding="utf-8")
        handler = lambda *a, **k: _QuietHandler(*a, directory=str(self.www), **k)  # noqa: E731
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.www, ignore_errors=True)
        self.fx.cleanup()

    def test_fetch_logs_hash_reuses_cache_and_logs_failures(self):
        r = run("fetch_source.py", self.base + "/ar.pdf", "--run", self.fx.dir, "--author", "financials", "--name", "AR FY2025")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("approx. 2 pages", r.stdout)
        r2 = run("fetch_source.py", self.base + "/ar.pdf", "--run", self.fx.dir, "--author", "financials")
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(len(list((self.fx.dir / "_cache" / "financials").glob("*.pdf"))), 1, "same SHA reuses the cached file")
        r3 = run("fetch_source.py", self.base + "/missing.pdf", "--run", self.fx.dir, "--author", "filings")
        self.assertEqual(r3.returncode, 1)
        _, rows = rl.read_csv(self.fx.dir / "source_retrievals.csv")
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(rows[0]["sha256"]), 64)
        self.assertTrue(rows[2]["error"])
        self.assertNotEqual(run("fetch_source.py", "file:///etc/passwd", "--run", self.fx.dir, "--author", "financials").returncode, 0)

    def test_html_tables(self):
        r = run("fetch_source.py", self.base + "/t.html", "--run", self.fx.dir, "--author", "industry")
        path = Path(r.stdout.splitlines()[0])
        tables = html_tables.extract(path.read_text(encoding="utf-8"))
        self.assertEqual(tables[0][0], ["Item", "FY", "FY"])
        self.assertEqual(tables[0][1], ["Revenue", "1,000", "1,100"])
        out = self.fx.tmp / "tables"
        self.assertEqual(run("html_tables.py", path, "--match", "revenue", "--out-dir", out).returncode, 0)
        self.assertEqual(len(list(out.glob("*.csv"))), 1)


class TestNumericControls(unittest.TestCase):
    def setUp(self):
        self.fx = FixtureRun()

    def tearDown(self):
        self.fx.cleanup()

    def test_conflict_blocks_final_qc_until_adjudicated(self):
        led = self.fx.dir / "specialists" / "industry_ledger.csv"
        _, rows = rl.read_csv(led)
        extra = fact_row("IND-C003", "industry")
        extra["value"] = "120"
        write_ledger(led, rows + [extra])
        self.fx.finalize("PASS")
        run("merge_ledgers.py", self.fx.dir)
        r = run("validate_run.py", self.fx.dir, "--stage", "final")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unadjudicated numeric conflict", r.stdout)
        self.assertEqual(run("reconcile_numbers.py", self.fx.dir).returncode, 0)
        self.assertTrue((self.fx.dir / "qc" / "numeric_conflicts.csv").exists())
        log = self.fx.dir / "cio" / "contradiction_log.md"
        log.write_text(log.read_text(encoding="utf-8") + "\n## X-02 — revenue FY2025: IND-C003 (120) vs FIN-C001 (100); filing p.10 supports 100.\n",
                       encoding="utf-8")
        r = run("validate_run.py", self.fx.dir, "--stage", "final")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_ledger_requires_metric_for_quantitative_claims(self):
        led = self.fx.dir / "specialists" / "moat_ledger.csv"
        row = fact_row("MOAT-C009", "moat")
        row["metric"] = ""
        bad = fact_row("MOAT-C010", "moat")
        bad["metric"] = "secret_sauce"
        write_ledger(led, [row, bad])
        errs = " ".join(rl.validate_ledger(led, "MOAT")[0].errors)
        self.assertIn("requires a metric key", errs)
        self.assertIn("not in METRIC_DEFINITIONS", errs)

    def test_evidence_stats_flags_thin_ledgers(self):
        r = run("evidence_stats.py", self.fx.dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("evidence base may be thin", r.stdout)
        stats = rl.load_json(self.fx.dir / "qc" / "evidence_stats.json")
        self.assertEqual(stats["overall"]["claims"], 19)


class TestDecisionOutputs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.base = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def errors(self, sc):
        p = self.tmp / "sc.json"
        p.write_text(json.dumps(sc, ensure_ascii=False), encoding="utf-8")
        return " ".join(rl.validate_scorecard(p).errors)

    def test_example_is_valid(self):
        self.assertEqual(self.errors(self.base), "")

    def test_each_requirement(self):
        cases = []
        sc = copy.deepcopy(self.base); sc["predictions"] = sc["predictions"][:2]; cases.append((sc, "3-7"))
        sc = copy.deepcopy(self.base); sc["predictions"][0]["probability"] = 1.0; cases.append((sc, "0.05 and 0.95"))
        sc = copy.deepcopy(self.base); sc["predictions"][0]["due"] = "2025-01-01"; cases.append((sc, "after the as-of"))
        sc = copy.deepcopy(self.base); sc["next_review_due"] = "2028-01-01"; cases.append((sc, "within 12 months"))
        sc = copy.deepcopy(self.base); sc["position_risk"]["p_permanent_loss_band"] = "small"; cases.append((sc, "p_permanent_loss_band"))
        sc = copy.deepcopy(self.base); del sc["decision_triggers"]; cases.append((sc, "decision_triggers"))
        sc = copy.deepcopy(self.base); sc["coverage"]["financial_years"] = 6; cases.append((sc, "below the depth standard"))
        for sc, frag in cases:
            self.assertIn(frag, self.errors(sc), frag)
        sc = copy.deepcopy(self.base); sc["coverage"]["financial_years"] = 6; sc["coverage"]["exception"] = "Listed 2020"
        self.assertNotIn("depth standard", self.errors(sc))


class TestInvestmentPolicy(unittest.TestCase):
    def test_new_run_snapshots_policy(self):
        fx = FixtureRun()
        try:
            m = rl.load_json(fx.dir / rl.RUN_MANIFEST)
            self.assertIn("investment_policy", m)
            self.assertFalse(m["ips_confirmed"])
            self.assertEqual(m["hurdle_rate"], rl.investment_policy()["hurdle_rate"])
            self.assertIn("PLACEHOLDER", (fx.dir / "research_brief.md").read_text(encoding="utf-8"))
        finally:
            fx.cleanup()


if __name__ == "__main__":
    unittest.main()
