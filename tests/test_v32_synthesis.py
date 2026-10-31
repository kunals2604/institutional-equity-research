"""Methodology 3.2.0: the synthesis pipeline's scripts (registry, theme check, integration checks, assembly)."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import synthesis  # noqa: E402
from test_research_system import crosswalk, write_ledger, fact_row  # noqa: E402

PY = sys.executable


def report(name: str, prefix: str, findings: list) -> str:
    fm = ("---\nspecialist: %s\ncompany: FixCo Ltd\nticker: FIXCO\nexchange: NSE\nrun_id: 20260301T090000Z\n"
          "research_cutoff: 2026-03-01\nreport_status: complete\nmodel_requested: opus\n"
          "independence_attestation: \"x\"\n---\n\n" % name)
    kf = "\n".join("- %s [FACT: %s-C%03d]" % (f, prefix, i) for i, f in enumerate(findings, 1))
    return (fm + "# %s\n\n## Mandate, Scope and Independence\nx\n\n## Key Findings\n%s\n\n## Data Coverage\nx\n\n%s\n\n"
            "## Method Coverage Checklist\n| # | Step | Status | Where | Notes |\n|---|---|---|---|---|\n"
            "| 1 | Plan | Done | x | |\n| 2 | Peers | Partial | x | tried two sources |\n\n"
            "## Contradictions and Data Conflicts\n- None.\n\n## Assumptions, Uncertainty and Missing Evidence\n"
            "| # | Assumption | Why |\n|---|---|---|\n| 1 | Rates stay | needed |\n\n- Missing: the FY2018 transcript.\n\n"
            "## Questions and Dependencies for the CIO\n- Check the ALM gap with filings.\n\n## Domain Conclusion\n"
            "- **Verdict of the domain:** sound [FACT: %s-C001].\n\n## Source Register\nhttps://example.invalid\n"
            % (name, kf, crosswalk(), prefix))


class SynthesisTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-syn-"))
        r = subprocess.run([PY, str(ROOT / "scripts" / "new_run.py"), "--ticker", "FIXCO", "--company", "FixCo Ltd",
                            "--exchange", "NSE", "--segment", "main", "--cutoff", "2026-03-01", "--run-id",
                            "20260301T090000Z", "--root", str(self.tmp)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        self.run = self.tmp / r.stdout.strip()
        m = rl.load_json(self.run / rl.RUN_MANIFEST)
        m["sector_modules"] = []
        rl.write_json(self.run / rl.RUN_MANIFEST, m)
        sp = self.run / "specialists"
        (sp / "financials.md").write_text(report("financials", "FIN", [
            "Liquidity is tight: liquid assets cover 0.86x of 24-month maturities.", "ROE averaged 18%."]), encoding="utf-8")
        (sp / "filings.md").write_text(report("filings", "FIL", [
            "Every audit report since FY2017 carries an emphasis of matter on regulatory dues."]), encoding="utf-8")
        write_ledger(sp / "financials_ledger.csv", [fact_row("FIN-C001", "financials", "Liquidity cover"),
                                                    fact_row("FIN-C002", "financials", "ROE"),
                                                    fact_row("FIN-C003", "financials", "Unused fact")])
        write_ledger(sp / "filings_ledger.csv", [fact_row("FIL-C001", "filings", "EOM every year")])
        write_ledger(self.run / "cio" / "cio_ledger.csv", [fact_row("CIO-C001", "cio", "Price")])
        synthesis.build_registry(self.run, log=lambda m: None)
        self.reg = synthesis.load_registry(self.run)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def items(self, kind, author=None):
        return [i for i in self.reg if i["kind"] == kind and (author is None or i["author"] == author)]

    def test_registry_captures_every_finding_and_crosswalk_row(self):
        self.assertEqual(len(self.items("key_finding", "financials")), 2)
        self.assertEqual(len(self.items("crosswalk", "financials")), 24)
        liq = next(i for i in self.items("key_finding") if "Liquidity" in i["text"])
        self.assertEqual(liq["materiality"], "gating")
        self.assertEqual(liq["owner_theme"], "T1")
        self.assertEqual(len(self.items("checklist_gap")), 2)
        unused = next(i for i in self.items("ledger_claim") if i["claim_ids"] == ["FIN-C003"])
        self.assertEqual(unused["materiality"], "reference")
        self.assertTrue(unused["cluster"].startswith("C-financials"))

    def test_ids_are_stable_and_staleness_is_detected(self):
        before = sorted(i["id"] for i in self.reg)
        synthesis.build_registry(self.run, log=lambda m: None)
        self.assertEqual(before, sorted(i["id"] for i in synthesis.load_registry(self.run)))
        self.assertEqual(synthesis.stale(self.run), [])
        p = self.run / "specialists" / "filings.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assertIn("specialists/filings.md", synthesis.stale(self.run))

    def brief(self, rows, findings="F1. **Liquidity.** Tight [FACT: FIN-C001] (R-ids: %s; financials)."):
        scope = sorted(synthesis.theme_scope(self.run, "T1"))
        secs = {s: "x" for s in rl.read_block(synthesis.SYNTHESIS_MD, "THEME_BRIEF_SECTIONS")}
        secs["Integrated Findings"] = findings % scope[0]
        secs["Contradiction Candidates"] = "CC-T1-01. Two views on liquidity."
        secs["Gaps and Follow-up Requests"] = "FU-T1-01 -> financials: the ALM note."
        secs["Disposition Register"] = "| id | disposition | pointer | reason |\n|---|---|---|---|\n" + "\n".join(rows(scope))
        (self.run / "synthesis" / "themes").mkdir(parents=True, exist_ok=True)
        (self.run / "synthesis" / "themes" / "T1.md").write_text(
            "# T1\n\n" + "\n\n".join("## %s\n%s" % kv for kv in secs.items()) + "\n", encoding="utf-8")
        return scope

    def test_theme_check(self):
        self.brief(lambda scope: ["| %s | integrated | F1 | |" % i for i in scope])
        self.assertEqual(synthesis.check_theme(self.run, "T1"), [])
        self.brief(lambda scope: ["| %s | integrated | F1 | |" % i for i in scope[1:]])
        self.assertTrue(any("without a disposition" in e for e in synthesis.check_theme(self.run, "T1")))
        gating = next(i["id"] for i in self.reg if i["owner_theme"] == "T1" and i["materiality"] == "gating")
        self.brief(lambda scope: ["| %s | %s | %s | %s |" % (i, "immaterial" if i == gating else "integrated",
                                                             "-" if i == gating else "F1",
                                                             "not relevant to the decision for many good reasons here" if i == gating else "")
                                  for i in scope])
        self.assertTrue(any("gating item cannot be immaterial" in e for e in synthesis.check_theme(self.run, "T1")))
        self.brief(lambda scope: ["| %s | integrated | F9 | |" % i for i in scope])
        self.assertTrue(any("must point to an Integrated Finding" in e for e in synthesis.check_theme(self.run, "T1")))

    def test_key_quantities_and_consistency_rules(self):
        kq = [{"label": "permanent-loss band", "aliases": ["permanent loss"], "value": "5–20%", "claim_ids": ["BEAR-C001"]}]
        text = "The permanent loss probability is 10–20%.\nThe permanent-loss band is 5–20%.\n"
        errs = synthesis.key_quantity_errors(text, kq)
        self.assertEqual(len(errs), 1)
        self.assertIn("line 1", errs[0])
        reg = [{"kind": "corpus_item", "type": "emphasis_of_matter", "text": "x"}]
        self.assertTrue(synthesis.consistency_errors(self.run, "Opinions were unmodified throughout.\n", reg))
        self.assertFalse(synthesis.consistency_errors(self.run, "Unmodified, with an emphasis of matter each year.\n", reg))

    def test_item_reaches_the_report_through_its_finding(self):
        it = {"claim_ids": ["FIL-C001"]}
        self.assertTrue(synthesis.reached(it, {}, {"FIL-C001"}))
        self.assertTrue(synthesis.reached({"claim_ids": []}, {"f_claims": ["FIN-C001"]}, {"FIN-C001"}))
        self.assertFalse(synthesis.reached({"claim_ids": ["FIN-C003"]}, {}, {"FIN-C001"}))
        gating = {"materiality": "gating", "claim_ids": ["FIN-C003", "FIN-C001", "CIO-C001"]}
        self.assertFalse(synthesis.reached(gating, {}, {"FIN-C001", "CIO-C001"}, {"CIO-C001"}),
                         "a gating finding is not reached while one of its own claims is missing")
        self.assertTrue(synthesis.reached(gating, {}, {"FIN-C003", "FIN-C001"}, {"CIO-C001"}))
        self.assertTrue(synthesis.reached(gating, {}, {"FIN-C003"}, {"FIN-C001", "CIO-C001"}),
                        "a widely shared claim is not required")

    def test_assemble_orders_sections_and_carries_the_scorecard(self):
        required = rl.final_sections_for(rl.V32)
        self.assertIn("Evidence Integration Register", required)
        (self.run / "cio" / "sections").mkdir(parents=True, exist_ok=True)
        own = [s for s in required if s != "Evidence Integration Register"]
        (self.run / "cio" / "sections" / "all.md").write_text("\n".join("## %s\ntext of %s\n" % (s, s) for s in reversed(own)),
                                                              encoding="utf-8")
        sc = {"run_id": "20260301T090000Z", "ticker": "FIXCO", "price": {"value": 100, "timestamp": "close", "claim_id": "CIO-C001"},
              "business_quality": {"final": 70, "confidence": "Medium"}, "investment_attractiveness": {"final": 55, "confidence": "Low"},
              "verdict": "HOLD / NEUTRAL", "valuation_status": "Fair-to-Full", "assessment_status": "complete",
              "qc_status": "PASS", "primary_layer": rl.canonical_layers()[0], "secondary_layers": []}
        rl.write_json(self.run / "cio" / "scorecard.json", sc)
        m = rl.load_json(self.run / rl.RUN_MANIFEST)
        m["methodology_version"] = "3.2.0"
        rl.write_json(self.run / rl.RUN_MANIFEST, m)
        errs = synthesis.assemble(self.run, log=lambda m_: None)
        self.assertEqual(errs, [])
        text = (self.run / "cio" / "final_report.md").read_text(encoding="utf-8")
        fm = rl.parse_front_matter(text)
        self.assertEqual(fm["business_quality"], "70")
        self.assertEqual(fm["verdict"], "HOLD / NEUTRAL")
        heads = rl.h2_headings(text)
        self.assertEqual(heads, [rl.norm_heading(s) for s in required])
        self.assertIsNotNone(synthesis.register_block_of(text))


class IntegrationEndToEndTest(SynthesisTest):
    """A well-formed synthesis passes the integration checks; dropping a gating finding from the body fails them."""

    def build_all(self, drop_gating=False, kq_value="100"):
        reg = synthesis.load_registry(self.run)
        sl = rl.load_json(self.run / "synthesis" / "slices.json")
        tdir = self.run / "synthesis" / "themes"
        tdir.mkdir(parents=True, exist_ok=True)
        f_claims = {}
        for tid in sl:
            scope = sorted(synthesis.theme_scope(self.run, tid))
            claims = sorted({c for i in reg if i["id"] in scope for c in i.get("claim_ids", [])
                             if rl.agent_of_prefix(c) in rl.SPECIALISTS})
            f_claims[tid] = claims
            secs = {s: "none" for s in rl.read_block(synthesis.SYNTHESIS_MD, "THEME_BRIEF_SECTIONS")}
            secs["Integrated Findings"] = ("F1. **Theme evidence.** As the specialists found [FACT: %s] (R-ids: %s)." % (
                "; ".join(claims), ", ".join(scope[:3])) if claims else "none")
            secs["Disposition Register"] = "| id | disposition | pointer | reason |\n|---|---|---|---|\n" + "\n".join(
                "| %s | integrated | F1 | |" % i for i in scope)
            (tdir / ("%s.md" % tid)).write_text("# %s\n\n" % tid + "\n\n".join("## %s\n%s" % kv for kv in secs.items()) + "\n",
                                                encoding="utf-8")
        synthesis.layer_inputs(self.run, log=lambda m: None)
        for L in synthesis.LAYERS:
            rows = sorted(synthesis.layer_scope(self.run, L))
            body = "\n".join("- **%s:** fixture [FACT: FIN-C002]" % f for f in rl.LAYER_BLOCK_FIELDS)
            (self.run / "synthesis" / "layers" / ("%s_draft.md" % L)).write_text(
                "# %s\n\n## Layer Assessment\n%s\n\n## Proposed Layer Fit\nProposed layer-fit score: 30/100\n"
                "Proposed confidence: Low\n\n## Crosswalk Disposition Register\n| id | disposition | pointer | reason |\n"
                "|---|---|---|---|\n%s\n" % (L, body, "\n".join("| %s | integrated | Layer Assessment | |" % r for r in rows)),
                encoding="utf-8")
        sdir = self.run / "synthesis" / "sections"
        sdir.mkdir(parents=True, exist_ok=True)
        groups = synthesis.writer_groups()
        for w, g in groups.items():
            cite = sorted({c for tid in g.get("themes", []) for c in f_claims.get(tid, [])})
            if drop_gating:
                cite = [c for c in cite if c != "FIN-C001"]
            text = "\n".join("## %s\nThe evidence%s.\n" % (s, " [FACT: %s]" % "; ".join(cite) if cite else "")
                             for s in g["sections"])
            nc = "\n".join("| F1 | %s | dropped for the test |" % tid for tid in g.get("themes", []) if drop_gating)
            (sdir / ("%s.md" % w)).write_text(text + "\n## Not Carried\n| finding | theme | reason |\n|---|---|---|\n%s\n" % nc,
                                              encoding="utf-8")
        writer_secs = {rl.norm_heading(s) for g in groups.values() for s in g["sections"]}
        own = [s for s in rl.final_sections_for(rl.V32) if rl.norm_heading(s) not in writer_secs
               and s != "Evidence Integration Register"]
        (self.run / "cio" / "sections").mkdir(parents=True, exist_ok=True)
        (self.run / "cio" / "sections" / "cio.md").write_text(
            "\n".join("## %s\nThe CIO's text. ROE averaged %s [FACT: FIN-C002].\n" % (s, kq_value) if s == "Executive Investment Thesis"
                      else "## %s\nThe CIO's text.\n" % s for s in own), encoding="utf-8")
        sc = {"run_id": "20260301T090000Z", "ticker": "FIXCO", "price": {"value": 100, "timestamp": "close", "claim_id": "CIO-C001"},
              "business_quality": {"final": 70, "confidence": "Medium"}, "investment_attractiveness": {"final": 55, "confidence": "Low"},
              "verdict": "HOLD / NEUTRAL", "valuation_status": "Fair-to-Full", "assessment_status": "complete", "qc_status": "PASS",
              "primary_layer": rl.canonical_layers()[0], "secondary_layers": [],
              "layer_fit": {L: {"score": 30, "confidence": "Low"} for L in synthesis.LAYERS}}
        rl.write_json(self.run / "cio" / "scorecard.json", sc)
        rl.write_json(self.run / "cio" / "scorecard_inputs.json",
                      {"key_quantities": [{"label": "average ROE", "aliases": ["roe averaged"], "value": "100", "claim_ids": ["FIN-C002"]}]})
        (self.run / "cio" / "contradiction_log.md").write_text("# Contradiction log\n", encoding="utf-8")
        m = rl.load_json(self.run / rl.RUN_MANIFEST)
        m["methodology_version"] = "3.2.0"
        rl.write_json(self.run / rl.RUN_MANIFEST, m)
        self.assertEqual(synthesis.assemble(self.run, log=lambda m_: None), [])
        return synthesis.integration(self.run)

    def test_well_formed_synthesis_passes(self):
        got = self.build_all()
        self.assertEqual(got["errors"], [])
        fin = next(u for u in got["uptake"] if u["specialist"] == "financials")
        self.assertEqual(fin["key_findings_reached"], fin["key_findings"])

    def test_dropping_a_gating_finding_fails(self):
        got = self.build_all(drop_gating=True)
        self.assertTrue(any("never reaches the report's body" in e for e in got["errors"]), got["errors"])

    def test_a_key_quantity_stated_two_ways_fails(self):
        got = self.build_all(kq_value="21")
        self.assertTrue(any("key_quantities" in e for e in got["errors"]), got["errors"])


if __name__ == "__main__":
    unittest.main()
