"""Tests for the research system's configuration and deterministic tooling.

Run:  python3 -m unittest discover tests -v

A complete synthetic run for a fictional company (FIXTURECO) is generated in a
temp directory. Nothing here is research on a real company.
"""

import copy
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import research_lib as rl  # noqa: E402

PY = sys.executable


def run(script, *args):
    return subprocess.run([PY, str(ROOT / "scripts" / script)] + [str(a) for a in args],
                          capture_output=True, text=True)


def write_ledger(path, rows):
    cols = rl.ledger_columns()
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def fact_row(cid, author, claim="Fixture fact", locator="p.10, Note 3"):
    return {"claim_id": cid, "author": author, "claim": claim, "tag": "FACT", "value": "100",
            "unit": "INR crore", "period": "FY2025", "basis": "consolidated",
            "source_title": "Fixture Annual Report 2024-25", "source_issuer": "FixtureCo Ltd",
            "source_url_or_id": "https://example.invalid/fixture-ar-2025.pdf", "source_date": "2025-06-30",
            "retrieved_date": "2026-01-01", "locator": locator, "source_tier": "1", "primary": "Y",
            "confidence": "H"}


def calc_row(cid, author, inputs):
    return {"claim_id": cid, "author": author, "claim": "Fixture ratio", "tag": "CALCULATION",
            "value": "0.2", "unit": "ratio", "period": "FY2025", "basis": "consolidated",
            "confidence": "M", "formula_or_inputs": "%s / %s" % inputs}


def crosswalk():
    parts = ["## Four-Layer Evidence Crosswalk\n"]
    for layer in rl.canonical_layers():
        parts.append("### %s\n- **Relevant evidence:** fixture\n- **Supports:** fixture\n- **Weakens:** fixture\n"
                     "- **Domain implications:** fixture\n- **Missing information:** none\n"
                     "- **Plausibility effect:** No change — fixture domain is silent.\n" % layer)
    return "\n".join(parts)


def specialist_report(name, run_id, ticker="FIXTURECO", extra=""):
    prefix = rl.SPECIALISTS[name]
    fm = ("---\nspecialist: %s\ncompany: FixtureCo Ltd\nticker: %s\nexchange: NSE\nrun_id: %s\n"
          "research_cutoff: 2026-01-01\nreport_status: complete\nmodel_requested: opus\n"
          "independence_attestation: \"Initial investigation completed independently.\"\n---\n\n" % (name, ticker, run_id))
    common = rl.common_sections()
    body = ["# %s report — FixtureCo\n" % name]
    for s in common[:2]:
        body.append("## %s\nRevenue was ₹100 crore [FACT: %s-C001]; ratio 0.2 [CALCULATION: %s-C002]; price per CIO-C001 [FACT: CIO-C001].\n"
                    % (s, prefix, prefix))
    for s in rl.agent_sections(name):
        body.append("## %s\nFixture content [INFERENCE].\n" % s)
    body.append(crosswalk())
    for s in common[3:]:
        body.append("## %s\nFixture content [JUDGMENT]. Source: https://example.invalid/fixture-ar-2025.pdf\n" % s)
    return fm + "\n".join(body) + extra


def final_report(sc, run_id):
    fm = {
        "company": "FixtureCo Ltd", "ticker": sc["ticker"], "exchange": "NSE", "run_id": run_id,
        "research_cutoff": "2026-01-01", "price": sc["price"]["value"], "price_timestamp": "close CIO-C001",
        "currency": "INR", "primary_layer": sc["primary_layer"],
        "secondary_layers": ", ".join(sc["secondary_layers"]) or "None",
        "business_quality": sc["business_quality"]["final"],
        "business_quality_confidence": sc["business_quality"]["confidence"],
        "investment_attractiveness": sc["investment_attractiveness"]["final"],
        "investment_attractiveness_confidence": sc["investment_attractiveness"]["confidence"],
        "verdict": sc["verdict"], "valuation_status": sc["valuation_status"], "qc_status": sc["qc_status"],
        "model_effective": "unverified",
    }
    out = ["---"] + ["%s: %s" % kv for kv in fm.items()] + ["---", "", "# FixtureCo — Final Report", ""]
    for s in rl.agent_sections("cio"):
        out.append("## %s" % s)
        if s == "Four-Layer Analysis":
            for i, layer in enumerate(rl.canonical_layers(), 1):
                out.append("### %s\nLayer-fit score: %d/100\nEvidence [FACT: FIN-C001] [JUDGMENT].\n"
                           % (layer, sc["layer_fit"]["L%d" % i]["score"]))
        else:
            out.append("Fixture synthesis [FACT: CIO-C001] [JUDGMENT].\n")
    return "\n".join(out)


class FixtureRun:
    """Builds a fully valid synthetic run in a temporary repository root."""

    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-test-"))
        self.run_id = "20260101-0900"
        r = run("new_run.py", "--ticker", "FIXTURECO", "--company", "FixtureCo Ltd", "--exchange", "NSE",
                "--segment", "main", "--cutoff", "2026-01-01", "--run-id", self.run_id, "--root", self.tmp)
        assert r.returncode == 0, r.stderr
        self.dir = self.tmp / r.stdout.strip()
        write_ledger(self.dir / "cio" / "cio_ledger.csv", [fact_row("CIO-C001", "cio", "Price snapshot")])
        for name, prefix in rl.SPECIALISTS.items():
            write_ledger(self.dir / "specialists" / ("%s_ledger.csv" % name),
                         [fact_row("%s-C001" % prefix, name),
                          calc_row("%s-C002" % prefix, name, ("%s-C001" % prefix, "%s-C001" % prefix))])
            (self.dir / "specialists" / ("%s.md" % name)).write_text(specialist_report(name, self.run_id), encoding="utf-8")

    def finalize(self, qc="PASS"):
        sc = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))
        sc.update({"run_id": self.run_id, "ticker": "FIXTURECO", "qc_status": qc})
        self.write_scorecard(sc)
        (self.dir / "cio" / "final_report.md").write_text(final_report(sc, self.run_id), encoding="utf-8")
        qc_path = self.dir / "cio" / "qc_record.md"
        qc_path.write_text(qc_path.read_text(encoding="utf-8").replace("QC status: PENDING", "QC status: %s" % qc),
                           encoding="utf-8")
        cl = self.dir / "cio" / "contradiction_log.md"
        cl.write_text(cl.read_text(encoding="utf-8").replace("<question>", "Fixture question"), encoding="utf-8")
        return sc

    def write_scorecard(self, sc):
        (self.dir / "cio" / "scorecard.json").write_text(json.dumps(sc, indent=2, ensure_ascii=False), encoding="utf-8")

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---------------------------------------------------------------------------


class TestCanonicalConfiguration(unittest.TestCase):
    def test_four_canonical_layers(self):
        self.assertEqual(rl.canonical_layers(), [
            "Layer 1 — Bedrock Compounder",
            "Layer 2 — High-Growth Business",
            "Layer 3 — Cyclical / Event-Driven Opportunity",
            "Layer 4 — Venture-Style / Optionality Bet",
        ])

    def test_six_epistemic_tags(self):
        self.assertEqual(rl.epistemic_tags(), ["FACT", "MANAGEMENT STATEMENT", "CALCULATION",
                                               "ESTIMATE", "INFERENCE", "JUDGMENT"])

    def test_weights_sum_to_100(self):
        for kind in ("BQ", "IA"):
            self.assertEqual(sum(w for _, _, w in rl.dimension_weights(kind)), 100, kind)

    def test_ten_agents_with_valid_frontmatter(self):
        names = set(rl.SPECIALISTS) | {"cio"}
        files = {p.stem for p in rl.AGENTS_DIR.glob("*.md")}
        self.assertEqual(files, names)
        for name in names:
            text = (rl.AGENTS_DIR / ("%s.md" % name)).read_text(encoding="utf-8")
            fm = rl.parse_front_matter(text)
            self.assertEqual(fm.get("name"), name)
            self.assertEqual(fm.get("model"), "opus", name)
            self.assertIn("investment-constitution", text, name)
            self.assertTrue(fm.get("description"), name)

    def test_specialists_cannot_spawn_agents_and_declare_prefix(self):
        for name, prefix in rl.SPECIALISTS.items():
            text = (rl.AGENTS_DIR / ("%s.md" % name)).read_text(encoding="utf-8")
            tools = [t.strip() for t in rl.parse_front_matter(text).get("tools", "").split(",")]
            self.assertNotIn("Agent", tools, name)
            self.assertIn("Write", tools, name)
            self.assertIn("`%s`" % prefix, text, name)
            self.assertTrue(rl.agent_sections(name), name)

    def test_every_specialist_crosswalk_angle_and_layer_awareness(self):
        for name in rl.SPECIALISTS:
            text = (rl.AGENTS_DIR / ("%s.md" % name)).read_text(encoding="utf-8")
            self.assertIn("## Crosswalk angle", text, name)
            for n in ("L1", "L2", "L3", "L4"):
                self.assertIn(n, text, "%s lacks %s" % (name, n))

    def test_no_operative_definitions_outside_claude_dir(self):
        self.assertFalse((ROOT / "agents").exists(), "legacy agents/ must be archived")
        self.assertFalse((ROOT / ".agents").exists(), "legacy .agents/ must be archived")

    def test_skills_exist(self):
        for skill in ("research-company", "investment-constitution"):
            text = (ROOT / ".claude" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertEqual(rl.parse_front_matter(text).get("name"), skill)
        rc = (ROOT / ".claude" / "skills" / "research-company" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("disable-model-invocation: true", rc)

    def test_governing_docs_use_canonical_layer_names(self):
        for doc in ("MASTER_RESEARCH_FRAMEWORK.md", "PROJECT_INSTRUCTIONS.md", "CLAUDE.md", "README.md"):
            res = rl.Result(doc)
            rl.check_layer_names((ROOT / doc).read_text(encoding="utf-8"), res)
            self.assertEqual(res.errors, [], doc)
            self.assertEqual(res.warnings, [], doc)

    def test_example_scorecard_validates(self):
        self.assertTrue(rl.validate_scorecard(ROOT / "templates" / "scorecard.example.json").ok)


class TestLayerDriftDetection(unittest.TestCase):
    def check(self, text):
        res = rl.Result("t")
        rl.check_layer_names(text, res)
        return res

    def test_tvs_style_redefinition_is_error(self):
        for bad in ("**Layer 3: Enduring High-ROIC Compounder**",
                    "│ Layer 1 │ Deep Value / Cyclical / Special Situation │",
                    "│ Layer 2 │ Capital-Intensive Low-Moat Commodity │",
                    "│ Layer 4 │ Structural Growth at Excessive Price │"):
            self.assertTrue(self.check(bad).errors, bad)

    def test_canonical_and_short_forms_pass(self):
        res = self.check("### Layer 2 — High-Growth Business\nLayer 1 — Bedrock Compounder\nLayer 3 — Cyclical / Event-Driven")
        self.assertEqual(res.errors, [])
        self.assertEqual(res.warnings, [])

    def test_label_drift_is_warning(self):
        res = self.check("### Layer 3 — Cyclical / Event / Special Situation / Deep Value")
        self.assertFalse(res.errors)
        self.assertTrue(res.warnings)

    @unittest.skipUnless((ROOT / "research/companies/TVSMOTOR/runs/legacy-antigravity-v1/final_report.md").exists(),
                         "legacy TVS report not present")
    def test_legacy_tvs_report_fails(self):
        p = ROOT / "research/companies/TVSMOTOR/runs/legacy-antigravity-v1/final_report.md"
        self.assertGreaterEqual(len(self.check(p.read_text(encoding="utf-8")).errors), 4)


class TestLedgerValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_valid_ledger(self):
        p = self.tmp / "financials_ledger.csv"
        write_ledger(p, [fact_row("FIN-C001", "financials"), calc_row("FIN-C002", "financials", ("FIN-C001", "FIN-C001"))])
        res, ids = rl.validate_ledger(p, "FIN")
        self.assertTrue(res.ok, res.errors)
        self.assertEqual(ids, {"FIN-C001", "FIN-C002"})

    def test_fact_without_source_or_locator_fails(self):
        row = fact_row("FIN-C001", "financials")
        row.update({"source_url_or_id": "", "locator": ""})
        p = self.tmp / "l.csv"
        write_ledger(p, [row])
        res, _ = rl.validate_ledger(p, "FIN")
        self.assertEqual(len([e for e in res.errors if "requires" in e]), 2)

    def test_not_located_with_high_confidence_fails(self):
        p = self.tmp / "l.csv"
        write_ledger(p, [fact_row("FIN-C001", "financials", locator="NOT_LOCATED")])
        self.assertFalse(rl.validate_ledger(p, "FIN")[0].ok)

    def test_calculation_without_formula_and_bad_tag_and_duplicates(self):
        bad_calc = calc_row("FIN-C002", "financials", ("FIN-C001", "FIN-C001"))
        bad_calc["formula_or_inputs"] = ""
        bad_tag = fact_row("FIN-C003", "financials")
        bad_tag["tag"] = "MANAGEMENT CLAIM"
        p = self.tmp / "l.csv"
        write_ledger(p, [fact_row("FIN-C001", "financials"), bad_calc, bad_tag, fact_row("FIN-C001", "financials")])
        errs = " ".join(rl.validate_ledger(p, "FIN")[0].errors)
        for frag in ("formula_or_inputs", "not canonical", "duplicate"):
            self.assertIn(frag, errs)

    def test_wrong_prefix_and_header(self):
        p = self.tmp / "l.csv"
        write_ledger(p, [fact_row("VAL-C001", "financials")])
        self.assertIn("prefix", " ".join(rl.validate_ledger(p, "FIN")[0].errors))
        p.write_text("claim_id,claim\nFIN-C001,x\n", encoding="utf-8")
        self.assertIn("Header mismatch", " ".join(rl.validate_ledger(p, "FIN")[0].errors))


class TestScorecardValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.base = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def validate(self, sc):
        p = self.tmp / "sc.json"
        p.write_text(json.dumps(sc, ensure_ascii=False), encoding="utf-8")
        return rl.validate_scorecard(p)

    def test_arithmetic_mismatch(self):
        sc = copy.deepcopy(self.base)
        sc["business_quality"]["final"] = 75
        self.assertIn("final", " ".join(self.validate(sc).errors))

    def test_gate_implied_by_classification(self):
        sc = copy.deepcopy(self.base)
        sc["classifications"]["reporting_reliability"] = "Material concerns"
        errs = " ".join(self.validate(sc).errors)
        self.assertIn("G2", errs)

    def test_gate_cap_applied(self):
        sc = copy.deepcopy(self.base)
        sc["classifications"]["reporting_reliability"] = "Material concerns"
        sc["business_quality"]["gates_triggered"] = ["G2"]
        sc["investment_attractiveness"]["gates_triggered"] = ["G2"]
        sc["business_quality"]["final"] = 55
        sc["investment_attractiveness"]["final"] = 45
        sc["mapped_verdict"] = sc["verdict"] = "HOLD / NEUTRAL"
        self.assertTrue(self.validate(sc).ok, self.validate(sc).errors)

    def test_verdict_override_rules(self):
        sc = copy.deepcopy(self.base)
        sc["verdict"] = "BUY"
        self.assertIn("override_reason", " ".join(self.validate(sc).errors))
        sc["override_reason"] = "Fixture reason"
        self.assertTrue(self.validate(sc).ok)
        sc["verdict"] = "STRONG BUY"
        self.assertIn("notches", " ".join(self.validate(sc).errors))

    def test_probabilities_and_primary_layer_rules(self):
        sc = copy.deepcopy(self.base)
        sc["scenarios"]["bull"]["probability"] = 0.5
        self.assertIn("sum", " ".join(self.validate(sc).errors))
        sc = copy.deepcopy(self.base)
        sc["primary_layer"] = "Layer 3 — Deep Value"
        self.assertIn("not canonical", " ".join(self.validate(sc).errors))
        sc["primary_layer"] = "Layer 3 — Cyclical / Event-Driven Opportunity"
        self.assertIn("fit >= 41", " ".join(self.validate(sc).errors))

    def test_layer4_buy_maps_to_speculative(self):
        self.assertEqual(rl.mapped_verdict(60, 70, "Medium", [], "Layer 4 — Venture-Style / Optionality Bet"),
                         "SPECULATIVE BUY")
        self.assertEqual(rl.mapped_verdict(90, 55, "High", [], "Layer 1 — Bedrock Compounder"),
                         "WATCHLIST — WAIT FOR BETTER PRICE")
        self.assertEqual(rl.mapped_verdict(90, 85, "Low", [], "Layer 1 — Bedrock Compounder"), "BUY")
        self.assertEqual(rl.mapped_verdict(90, 85, "High", ["G3"], "Layer 1 — Bedrock Compounder"), "STRONG AVOID")


class TestEndToEndRun(unittest.TestCase):
    def setUp(self):
        self.fx = FixtureRun()

    def tearDown(self):
        self.fx.cleanup()

    def test_new_run_structure(self):
        m = rl.load_json(self.fx.dir / "manifest.json")
        self.assertEqual(set(m["specialists"]), set(rl.SPECIALISTS))
        self.assertEqual(m["methodology_version"], rl.methodology_version())
        for p in ("research_brief.md", "source_register.csv", "cio/cio_ledger.csv", "cio/qc_record.md"):
            self.assertTrue((self.fx.dir / p).exists(), p)
        self.assertNotEqual(run("new_run.py", "--ticker", "FIXTURECO", "--company", "x", "--exchange", "NSE",
                                "--segment", "main", "--run-id", self.fx.run_id, "--root", self.fx.tmp).returncode, 0,
                            "must refuse to overwrite an existing run")

    def test_specialist_barrier_passes_then_detects_missing(self):
        r = run("validate_run.py", self.fx.dir, "--stage", "specialists")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(all(v["status"] == "complete" for v in rl.load_json(self.fx.dir / "manifest.json")["specialists"].values()))
        (self.fx.dir / "specialists" / "moat.md").unlink()
        r = run("validate_run.py", self.fx.dir, "--stage", "specialists")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(rl.load_json(self.fx.dir / "manifest.json")["specialists"]["moat"]["status"], "missing")

    def test_specialist_report_failures(self):
        p = self.fx.dir / "specialists" / "industry.md"
        text = p.read_text(encoding="utf-8")
        cases = {
            "uncited fact": text + "\nShare was 18% [FACT].\n",
            "unknown id": text + "\nShare was 18% [FACT: IND-C999].\n",
            "missing crosswalk layer": text.replace("### Layer 4 — Venture-Style / Optionality Bet", "### Layer 4 — something"),
            "missing section": text.replace("## Market Share and Company Position", "## Something Else"),
            "wrong ticker": text.replace("ticker: FIXTURECO", "ticker: OTHERCO"),
        }
        for label, bad in cases.items():
            p.write_text(bad, encoding="utf-8")
            r = run("validate_report.py", p, "--kind", "specialist",
                    "--ledger", self.fx.dir / "specialists" / "industry_ledger.csv")
            if label == "wrong ticker":
                res = rl.validate_specialist_report(p, set(), {"ticker": "FIXTURECO", "run_id": self.fx.run_id})
                self.assertFalse(res.ok, label)
            else:
                self.assertNotEqual(r.returncode, 0, label)

    def test_final_stage_scoreboard_and_refusals(self):
        self.fx.finalize("PASS")
        board = self.fx.tmp / "COMPANY_SCOREBOARD.csv"
        # Refuse before automated QC has run.
        self.assertNotEqual(run("update_scoreboard.py", self.fx.dir, "--scoreboard", board).returncode, 0)
        # Stale/missing merged ledger fails final stage.
        self.assertNotEqual(run("validate_run.py", self.fx.dir, "--stage", "final").returncode, 0)
        self.assertEqual(run("merge_ledgers.py", self.fx.dir).returncode, 0)
        r = run("validate_run.py", self.fx.dir, "--stage", "final")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(rl.load_json(self.fx.dir / "qc" / "auto_checks.json")["passed"])
        r = run("update_scoreboard.py", self.fx.dir, "--scoreboard", board)
        self.assertEqual(r.returncode, 0, r.stderr)
        _, rows = rl.read_csv(board)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["verdict"], "HOLD / NEUTRAL")
        self.assertEqual((self.fx.dir.parent.parent / "LATEST_RUN.txt").read_text().strip(), self.fx.run_id)
        # Idempotent upsert.
        self.assertEqual(run("update_scoreboard.py", self.fx.dir, "--scoreboard", board).returncode, 0)
        self.assertEqual(len(rl.read_csv(board)[1]), 1)

    def test_final_report_inconsistency_and_banned_phrase(self):
        sc = self.fx.finalize("PASS")
        fr = self.fx.dir / "cio" / "final_report.md"
        good = fr.read_text(encoding="utf-8")
        run("merge_ledgers.py", self.fx.dir)
        fr.write_text(good.replace("business_quality: %d" % sc["business_quality"]["final"], "business_quality: 91"), encoding="utf-8")
        self.assertNotEqual(run("validate_run.py", self.fx.dir, "--stage", "final").returncode, 0)
        fr.write_text(good + "\nThe balance sheet is pristine [JUDGMENT].\n", encoding="utf-8")
        self.assertNotEqual(run("validate_run.py", self.fx.dir, "--stage", "final").returncode, 0)
        fr.write_text(good.replace("Layer-fit score: 66/100", "Layer-fit score: 70/100"), encoding="utf-8")
        r = run("validate_run.py", self.fx.dir, "--stage", "final")
        self.assertIn("fit", r.stdout)
        self.assertNotEqual(r.returncode, 0)

    def test_scoreboard_refuses_failed_qc(self):
        self.fx.finalize("FAIL")
        run("merge_ledgers.py", self.fx.dir)
        run("validate_run.py", self.fx.dir, "--stage", "final")
        board = self.fx.tmp / "COMPANY_SCOREBOARD.csv"
        self.assertNotEqual(run("update_scoreboard.py", self.fx.dir, "--scoreboard", board).returncode, 0)
        self.assertFalse(board.exists())


if __name__ == "__main__":
    unittest.main()
