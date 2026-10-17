"""Tests for the v2.3.0 framework additions: method coverage checklist, round-half-up, deterministic scorecard
builder, score guides, hurdle-adjusted asymmetry, event uplifts, scenario build, robustness grid, transcript
classification and robust retrieval helpers. Synthetic data only.

Run:  python3 -m unittest discover tests -v
"""

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import research_lib as rl  # noqa: E402
import build_scorecard as bs  # noqa: E402
import corpus  # noqa: E402
import fetch_source as fs  # noqa: E402
import score_guides as sg  # noqa: E402
import valuation_tools as vt  # noqa: E402
from test_research_system import FixtureRun, specialist_report  # noqa: E402

PY = sys.executable
EXAMPLE = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))


def judgments_only(sc):
    x = json.loads(json.dumps(sc))
    for key in ("business_quality", "investment_attractiveness"):
        for f in ("weighted_raw", "final"):
            x[key].pop(f, None)
    for f in ("mapped_verdict", "verdict"):
        x.pop(f, None)
    return x


class RoundingTest(unittest.TestCase):
    def test_round_half_up(self):
        self.assertEqual(rl.round_half_up(60.5), 61)
        self.assertEqual(rl.round_half_up(60.49), 60)
        self.assertEqual(rl.round_half_up(2.5), 3)       # Python's round() gives 2
        self.assertEqual(rl.round_half_up(0.0), 0)
        self.assertEqual(rl.round_half_up(99.5), 100)


class MethodChecklistTest(unittest.TestCase):
    def check(self, text, name="moat"):
        res = rl.Result("t")
        rl.check_method_checklist(name, text, res)
        return res

    def test_every_specialist_has_method_steps(self):
        for name in rl.SPECIALISTS:
            self.assertGreaterEqual(len(rl.method_steps(name)), 5, name)

    def test_valid_report_passes(self):
        text = specialist_report("moat", "20260101T090000Z")
        self.assertTrue(self.check(text).ok)

    def test_missing_rows_and_status_are_errors(self):
        text = specialist_report("moat", "20260101T090000Z")
        lines = text.splitlines()
        rows = [i for i, l in enumerate(lines) if l.startswith("| 1 | ") or l.startswith("| 2 | ")]
        short = "\n".join(l for i, l in enumerate(lines) if i != rows[0])
        self.assertFalse(self.check(short).ok)
        bad = text.replace("| 2 | %s | Done |" % rl.method_steps("moat")[1], "| 2 | %s | Maybe |" % rl.method_steps("moat")[1])
        self.assertFalse(self.check(bad).ok)


class BuildScorecardTest(unittest.TestCase):
    def test_reproduces_example(self):
        sc = bs.compute(judgments_only(EXAMPLE))
        for key in ("business_quality", "investment_attractiveness"):
            self.assertEqual(sc[key]["final"], EXAMPLE[key]["final"])
            self.assertAlmostEqual(sc[key]["weighted_raw"], EXAMPLE[key]["weighted_raw"], places=2)
        self.assertEqual(sc["verdict"], EXAMPLE["verdict"])

    def test_classification_gate_caps_and_validates(self):
        x = judgments_only(EXAMPLE)
        x["classifications"]["governance"] = "Compromised"
        sc = bs.compute(x)
        self.assertIn("G3", sc["business_quality"]["gates_triggered"])
        self.assertLessEqual(sc["business_quality"]["final"], rl.gates("BQ")["G3"][1])
        self.assertLessEqual(sc["investment_attractiveness"]["final"], rl.gates("IA")["G3"][1])
        tmp = Path(tempfile.mkdtemp())
        try:
            p = tmp / "scorecard.json"
            p.write_text(json.dumps(sc), encoding="utf-8")
            res = rl.validate_scorecard(p)
            self.assertFalse([e for e in res.errors if "final" in e.lower() or "gate" in e.lower()], res.errors)
        finally:
            shutil.rmtree(tmp)

    def test_override_limits(self):
        x = judgments_only(EXAMPLE)
        x["override_verdict"] = "STRONG BUY"
        x["override_reason"] = "test"
        with self.assertRaises(ValueError):
            bs.compute(x)
        x["override_verdict"] = "BUY"
        x["override_reason"] = ""
        with self.assertRaises(ValueError):
            bs.compute(x)
        x["override_reason"] = "documented reason"
        self.assertEqual(bs.compute(x)["verdict"], "BUY")

    def test_cli_writes_valid_scorecard(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "cio").mkdir()
            (tmp / "cio" / "scorecard_inputs.json").write_text(json.dumps(judgments_only(EXAMPLE)), encoding="utf-8")
            r = subprocess.run([PY, str(ROOT / "scripts" / "build_scorecard.py"), str(tmp)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((tmp / "cio" / "scorecard.json").exists())
        finally:
            shutil.rmtree(tmp)


class ScoreGuidesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        years = range(2017, 2027)
        with (self.tmp / "m.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["metric", "period", "value"])
            for y in years:
                w.writerow(["roic", "FY%d" % y, 0.25])
                w.writerow(["fcf", "FY%d" % y, 10])
                w.writerow(["net_debt", "FY%d" % y, -5])
                w.writerow(["net_debt_to_ebitda", "FY%d" % y, -0.2])
                w.writerow(["interest_coverage", "FY%d" % y, 20])
            w.writerow(["incremental_roic_5y", "FY2026", 0.05])
        with (self.tmp / "h.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["item", "period", "value"])
            for y in years:
                w.writerow(["cfo", "FY%d" % y, 12])
                w.writerow(["pat", "FY%d" % y, 10])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_bands(self):
        m = sg.load(self.tmp / "m.csv", "metric")
        h = sg.load(self.tmp / "h.csv", "item")
        years = list(range(2017, 2027))
        b1 = sg.bq1(m, years, 0.10, False, None)
        self.assertEqual(b1["band"], "90-100")                # spread 15 pp
        self.assertTrue(any("incremental_roic_5y" in f for f in b1["flags"]))
        b4 = sg.bq4(m, h, years)
        self.assertEqual(b4["cum_cfo_to_pat"], 1.2)
        self.assertEqual(b4["band"], "85-100")
        self.assertEqual(sg.bq5(m, years)["band"], "90-100")  # net cash

    def test_band_edges(self):
        self.assertEqual(sg.band(8.0, [(15, "a"), (8, "b")], "c"), "b")
        self.assertEqual(sg.band(-6, [(0, "a"), (-5, "b")], "c"), "c")


class ValuationEnhancementsTest(unittest.TestCase):
    DCF = {"years": 5, "base_revenue": 100.0, "revenue_growth": 0.10, "ebit_margin": 0.20, "tax_rate": 0.25,
           "wacc": 0.11, "terminal_growth": 0.05, "reinvestment_rate": 0.3, "shares_diluted": 10, "net_debt": 0}

    def test_event_uplift_raises_value(self):
        base = vt.dcf(self.DCF)
        up = vt.dcf(dict(self.DCF, event_uplifts=[{"year": 2, "revenue_uplift": 0.10, "flow_through": 0.9}]))
        self.assertEqual(len(up["events_applied"]), 1)
        self.assertGreater(up["value_per_share"], base["value_per_share"])
        self.assertAlmostEqual(up["rows"][1]["growth"], 0.20)
        with self.assertRaises(ValueError):
            vt.dcf(dict(self.DCF, event_uplifts=[{"year": 9, "revenue_uplift": 0.1}]))

    def test_hurdle_adjusted_asymmetry(self):
        inp = {"price": 100, "horizon_years": 1, "hurdle_rate": 0.10,
               "scenarios": {"bear": {"probability": 0.5, "value_per_share": 90},
                             "bull": {"probability": 0.5, "value_per_share": 130}}}
        s = vt.scenarios(inp)
        # undiscounted: up 15 / down 5 = 3.0; hurdle bar 110: up 10 / down 10 = 1.0
        self.assertAlmostEqual(s["asymmetry_ratio_undiscounted"], 3.0)
        self.assertAlmostEqual(s["asymmetry_ratio"], 1.0)
        self.assertTrue(s["asymmetry_basis"].startswith("hurdle-adjusted"))

    def test_scenario_build_convention(self):
        b = vt.scenario_build({"price": 100, "horizon_years": 2, "hurdle_rate": 0.10,
                               "scenarios": {"base": {"probability": 1.0, "value_today": 100, "dps": 0}}})
        self.assertEqual(b["scenarios"]["base"]["value_per_share"], [121.0, 121.0])
        # fair value today compounds at the hurdle, so E[IRR] equals the hurdle
        self.assertAlmostEqual(vt.scenarios(b)["expected_irr"], 0.10, places=6)

    def test_robustness_grid(self):
        inp = {"price": 100, "horizon_years": 3, "hurdle_rate": 0.12,
               "scenarios": {"bear": {"probability": 0.25, "value_today": 30},
                             "base": {"probability": 0.5, "value_today": [45, 55]},
                             "bull": {"probability": 0.25, "value_today": 70}}}
        r = vt.robustness(inp, EXAMPLE)
        self.assertEqual(r["combinations"], 27)
        self.assertTrue(r["robust"], r["verdicts"])
        self.assertLessEqual(r["ia_range"][0], r["ia_range"][1])


class RetrievalAndCorpusTest(unittest.TestCase):
    def test_transcript_classification(self):
        self.assertTrue(corpus.is_concall_transcript("concall", {}, "Q2 FY25 Earnings Call", ""))
        self.assertTrue(corpus.is_concall_transcript("other", {"category": "Concall Transcript"}, "Q2", ""))
        self.assertFalse(corpus.is_concall_transcript("concall", {}, "Intimation of schedule of analyst meet", "transcript"))
        self.assertFalse(corpus.is_concall_transcript("concall", {}, "Audio recording link", ""))

    def test_transient(self):
        self.assertTrue(fs._transient(urllib.error.HTTPError("u", 503, "x", {}, None)))
        self.assertFalse(fs._transient(urllib.error.HTTPError("u", 404, "x", {}, None)))
        self.assertTrue(fs._transient(urllib.error.URLError("EOF occurred in violation of protocol")))

    def test_prior_success_reuse(self):
        run = Path(tempfile.mkdtemp())
        try:
            (run / "_cache").mkdir()
            (run / "_cache" / "a.pdf").write_bytes(b"%PDF-1.4 x")
            fs.log_row(run, {"author": "filings", "url": "https://x.invalid/a.pdf", "http_status": 200, "local_path": "_cache/a.pdf"})
            fs.log_row(run, {"author": "moat", "url": "https://x.invalid/b.pdf", "http_status": "", "error": "SSL EOF"})
            self.assertEqual(fs.prior_success(run, "https://x.invalid/a.pdf")[0], "filings")
            self.assertIsNone(fs.prior_success(run, "https://x.invalid/b.pdf"))
        finally:
            shutil.rmtree(run)


class LegacyAndReadOnlyRunTest(unittest.TestCase):
    def test_version_gate(self):
        self.assertTrue(rl.is_legacy("2.2.0"))
        self.assertTrue(rl.is_legacy("unversioned"))
        self.assertFalse(rl.is_legacy("2.3.0"))
        self.assertFalse(rl.is_legacy("2.10.1"))

    def test_legacy_report_without_checklist_passes_only_as_legacy(self):
        text = specialist_report("moat", "20260101T090000Z")
        start = text.index("## %s" % rl.CHECKLIST_SECTION)
        end = text.index("\n## ", start + 3)
        stripped = text[:start] + text[end + 1:]
        tmp = Path(tempfile.mkdtemp())
        try:
            p = tmp / "moat.md"
            p.write_text(stripped, encoding="utf-8")
            self.assertFalse(rl.validate_specialist_report(p).ok)
            self.assertTrue(rl.validate_specialist_report(p, legacy=True).ok,
                            rl.validate_specialist_report(p, legacy=True).errors)
        finally:
            shutil.rmtree(tmp)

    def test_finalized_run_is_not_modified(self):
        fx = FixtureRun()
        try:
            mpath = fx.dir / rl.RUN_MANIFEST
            m = json.loads(mpath.read_text(encoding="utf-8"))
            m["status"] = "complete"
            mpath.write_text(json.dumps(m, indent=2), encoding="utf-8")
            before = mpath.read_bytes()
            r = subprocess.run([PY, str(ROOT / "scripts" / "validate_run.py"), str(fx.dir), "--stage", "final"],
                               capture_output=True, text=True)
            self.assertIn("read-only", r.stdout)
            self.assertEqual(mpath.read_bytes(), before)
            self.assertFalse((fx.dir / "qc" / "auto_checks.json").exists())
        finally:
            fx.cleanup()


if __name__ == "__main__":
    unittest.main()
