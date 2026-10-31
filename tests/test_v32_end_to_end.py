"""Methodology 3.2.0 end to end: a run with the reading stage off (the web-digest record), eleven specialists (the
forecasting specialist included), a sector module and the synthesis pipeline (registry, theme briefs, layer drafts,
section files, assembly) passes the Stage-2 barrier and the final stage and finalizes; the same run fails the final
stage when a gating finding never reaches the report, when a key quantity is stated two ways, when a contradiction
candidate is not in the contradiction log, and when the report is edited after assembly. A reading-on run passes the
same pipeline. The engine confines the synthesis agents (a theme analyst never sees the CIO's report or another theme,
a layer analyst never sees another layer, a section writer has no web), specialists never read synthesis/ before
cross-examination, and the auditor recomputes the scorecard only under audit/.
"""

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import synthesis  # noqa: E402
from test_research_system import FixtureRun, fact_row, run, write_ledger  # noqa: E402

LIQUIDITY = "Liquidity is tight: liquid assets cover 0.86x of 12-month maturities [FACT: FIN-C003]."
PRICE_VIEW = ("at the verified price the layer's base case implies a return close to the hurdle, so price alone offers "
              "no margin of safety for this layer [JUDGMENT].")
DIGEST_COVERAGE = ("# Web digest — run fixture\n\nReading stage OFF: no page was read by readers.\n\n"
                   "| Document | Summaries found | Items | Page-confirmed | Leads |\n|---|---|---|---|---|\n"
                   "| Annual report FY2025 | 1 | 1 | 1 | 0 |\n")
DIGEST_ITEM = {"type": "contingent_liability", "period": "FY2025", "doc_key": "AR-FY2025", "basis": "consolidated",
               "fields": {"category": "Income tax matters", "amount_current": "1,234.56", "unit_of_amount": "INR crore"},
               "source_url": "https://news.example.com/fixtureco-fy2025", "snapshot": "_cache/digest/snap.pdf",
               "snapshot_page": 2, "publisher": "Example News", "source_kind": "news", "tier": 6,
               "quote": "FixtureCo reported contingent liabilities on income tax matters of Rs 1,234.56 crore in FY2025."}


def write_digest(run_dir: Path, specialists) -> None:
    """The Stage-0c record of a reading-off run (as digest.py plan, confirm and build would write it)."""
    import digest
    d = run_dir / rl.DIGEST_DIR
    (d / "items").mkdir(parents=True, exist_ok=True)
    (d / "packs").mkdir(parents=True, exist_ok=True)
    rl.write_json(d / "plan.json", {"scope": {"years": 10, "quarters": 24, "ppt_quarters": 12}, "documents": [
        {"key": "AR-FY2025", "doc_type": "annual_report", "period": "FY2025", "label": "Annual report FY2025"}]})
    (d / "items" / "AR-FY2025.jsonl").write_text(json.dumps(DIGEST_ITEM) + "\n", encoding="utf-8")
    iid = digest.item_id("AR-FY2025", DIGEST_ITEM)
    (d / "confirmations.jsonl").write_text(json.dumps({"id": iid, "status": "page_confirmed", "page": 41}) + "\n",
                                           encoding="utf-8")
    (run_dir / rl.DIGEST_COVERAGE).write_text(DIGEST_COVERAGE, encoding="utf-8")
    rl.write_json(run_dir / rl.DIGEST_STATUS, {"complete": True, "pending": 0,
                                               "coverage_sha256": hashlib.sha256(DIGEST_COVERAGE.encode()).hexdigest()})
    (run_dir / rl.DIGEST_INDEX).write_text("# Digest index — fixture\n", encoding="utf-8")
    for name in specialists:
        (d / "packs" / ("%s.md" % name)).write_text("# Digest pack — %s\n" % name, encoding="utf-8")
    (run_dir / rl.STRUCTURED_SUMMARY).write_text("# Structured exchange filings — fixture\n", encoding="utf-8")
    (run_dir / "qc").mkdir(exist_ok=True)
    rl.write_json(run_dir / "qc" / "verification.json", {"run_id": "fixture", "stage": "final", "status": "PASS",
                                                         "run_findings": [], "specialists": {}})


class V32Run(FixtureRun):
    """A current-version run: reading off (or on), sector module nbfc, the forecasting specialist."""

    def __init__(self, reading="off"):
        super().__init__(version=None, reading=reading)
        m = rl.load_json(self.dir / rl.RUN_MANIFEST)
        m["sector_modules"] = ["nbfc"]
        rl.write_json(self.dir / rl.RUN_MANIFEST, m)
        for name in self.specialists:          # one checklist row per sector-module step, as the brief asks
            steps = rl.sector_steps_for(self.dir, name)
            if not steps:
                continue
            p = self.dir / "specialists" / ("%s.md" % name)
            text = p.read_text(encoding="utf-8")
            body = rl.section(text, rl.CHECKLIST_SECTION)
            n0 = len(rl.method_steps(name))
            rows = "\n".join("| %d | %s %s | Done | %s section |" % (n0 + k, s["id"], s["step"], rl.CHECKLIST_SECTION)
                             for k, s in enumerate(steps, 1))
            p.write_text(text.replace(body, body.rstrip() + "\n" + rows + "\n\n", 1), encoding="utf-8")
        p = self.dir / "specialists" / "financials.md"            # a gating finding with a claim of its own
        text = p.read_text(encoding="utf-8")
        p.write_text(text.replace("## Key Findings\n", "## Key Findings\n- %s\n" % LIQUIDITY, 1), encoding="utf-8")
        led = self.dir / "specialists" / "financials_ledger.csv"
        rows = rl.read_csv(led)[1]
        write_ledger(led, rows + [dict(fact_row("FIN-C003", "financials", "Liquidity cover"), metric="alm_gap_1y_ratio",
                                       value="0.86", unit="x")])
        if reading == "off":
            write_digest(self.dir, self.specialists)

    def forecast_handoff(self):
        """Valuation on the forecast (cio.md Stage 3, step 6)."""
        rl.write_json(self.dir / "calc" / "forecasting_to_valuation.json", {"years": 5, "base_revenue": 100.0})
        rl.write_json(self.dir / "calc" / "forecasting_reconcile.json",
                      {"comparisons": {"revenue_cagr": {"forecast": 0.1, "valuation": 0.1}}, "flags": []})
        (self.dir / "specialists" / "valuation_followup_1.md").write_text(
            "---\nspecialist: valuation\ncompany: x\nticker: x\nexchange: NSE\nrun_id: x\nresearch_cutoff: 2026-01-01\n"
            "report_status: complete\nmodel_requested: opus\nindependence_attestation: \"x\"\n---\n\n"
            "# Valuation on the forecast\n\nThe base path gives the same range [FACT: VAL-C001].\n", encoding="utf-8")

    def build_report(self, drop_gating=False, kq_value=None, log_candidates=True):
        self.forecast_handoff()
        """Stage 3 as the pipeline leaves it: the scorecard and the legacy-format sections split into the writers'
        and the CIO's section files, theme briefs and layer drafts that disposition every item, then assembly."""
        from test_research_system import final_report
        sc = self.finalize("PASS")
        assert run("merge_ledgers.py", self.dir).returncode == 0
        synthesis.build_registry(self.dir, log=lambda m: None)
        reg = synthesis.load_registry(self.dir)
        by_id = {i["id"]: i for i in reg}
        sl = rl.load_json(self.dir / "synthesis" / "slices.json")
        tdir = self.dir / "synthesis" / "themes"
        tdir.mkdir(parents=True, exist_ok=True)
        f_claims, ccs = {}, []
        for tid in sl:
            scope = sorted(synthesis.theme_scope(self.dir, tid))
            claims = sorted({c for i in scope for c in by_id.get(i, {}).get("claim_ids", [])
                             if rl.agent_of_prefix(c) in rl.SPECIALISTS})
            f_claims[tid] = claims
            secs = {s: "none" for s in rl.read_block(synthesis.SYNTHESIS_MD, "THEME_BRIEF_SECTIONS")}
            secs["Integrated Findings"] = ("F1. **Theme evidence.** As the specialists found [FACT: %s] (R-ids: %s)." % (
                "; ".join(claims), ", ".join(scope[:3])) if claims else "none")
            if tid == "T1":
                cc = "CC-T1-01"
                ccs.append(cc)
                secs["Contradiction Candidates"] = ("- %s. **Liquidity cover.** financials 0.86x [FACT: FIN-C003] against "
                                                    "the funding plan [FACT: FIN-C001]." % cc)
            secs["Disposition Register"] = "| id | disposition | pointer | reason |\n|---|---|---|---|\n" + "\n".join(
                "| %s | integrated | F1 | |" % i for i in scope)
            (tdir / ("%s.md" % tid)).write_text("# %s\n\n" % tid + "\n\n".join("## %s\n%s" % kv for kv in secs.items())
                                                + "\n", encoding="utf-8")
        log = "# Contradiction log\n\n" + "".join(
            "## %s — Liquidity cover\n- **Specialist positions:** financials 0.86x [FACT: FIN-C003]\n- **Evidence for each:** the maturity note\n"
            "- **Contrary evidence:** none\n- **Assumptions required:** none\n- **Independent check (CIO):** recomputed [FACT: CIO-C001]\n"
            "- **Resolution:** the cover is 0.86x [FACT: FIN-C003]\n- **Confidence:** High — primary source\n"
            "- **Investment impact:** BQ4\n" % c
            for c in (ccs if log_candidates else []))
        (self.dir / "cio" / "contradiction_log.md").write_text(log, encoding="utf-8")
        synthesis.layer_inputs(self.dir, log=lambda m: None)
        for L in synthesis.LAYERS:
            rows = sorted(synthesis.layer_scope(self.dir, L))
            body = "\n".join("- **%s:** %s" % (f, PRICE_VIEW if f == "Current-price assessment" else
                                                "fixture [FACT: FIN-C002]") for f in rl.LAYER_BLOCK_FIELDS)
            (self.dir / "synthesis" / "layers" / ("%s_draft.md" % L)).write_text(
                "# %s\n\n## Layer Assessment\n%s\n\n## Proposed Layer Fit\nProposed layer-fit score: %d/100\n"
                "Proposed confidence: Low\n\n## Crosswalk Disposition Register\n| id | disposition | pointer | reason |\n"
                "|---|---|---|---|\n%s\n" % (L, body, sc["layer_fit"][L]["score"],
                                             "\n".join("| %s | integrated | Layer Assessment | |" % r for r in rows)),
                encoding="utf-8")
        # the legacy-format report, split by section into the writers' files and the CIO's
        blocks = dict(synthesis.h2_blocks(final_report(sc, self.run_id)))
        groups = synthesis.writer_groups()
        writer_of = {rl.norm_heading(s): w for w, g in groups.items() for s in g["sections"]}
        sdir = self.dir / "synthesis" / "sections"
        sdir.mkdir(parents=True, exist_ok=True)
        files = {w: [] for w in groups}
        cio = []
        for head, body in blocks.items():
            key = rl.norm_heading(head)
            if key == rl.norm_heading("Evidence Integration Register"):
                continue
            if key == rl.norm_heading("Contradiction and Evidence Audit"):
                body = body.split("<!-- %s:BEGIN -->" % rl.COVERAGE_BLOCK)[0].rstrip() + "\n"
            if key == rl.norm_heading("Executive Investment Thesis") and kq_value:
                body = body.rstrip() + "\nLiquidity cover was %s of 12-month maturities [FACT: FIN-C003].\n" % kq_value
            (files[writer_of[key]] if key in writer_of else cio).append(body)
        for w, g in groups.items():
            cite = sorted({c for tid in g.get("themes", []) for c in f_claims.get(tid, [])})
            if drop_gating:
                cite = [c for c in cite if c != "FIN-C003"]
            if files[w] and cite:
                files[w][0] = files[w][0].rstrip() + "\nThe theme evidence [FACT: %s].\n" % "; ".join(cite)
            nc = "\n".join("| F1 | %s | dropped for the test |" % tid for tid in g.get("themes", []) if drop_gating)
            (sdir / ("%s.md" % w)).write_text("\n".join(files[w]) + "\n## Not Carried\n| finding | theme | reason |\n"
                                              "|---|---|---|\n%s\n" % nc, encoding="utf-8")
        (self.dir / "cio" / "sections").mkdir(parents=True, exist_ok=True)
        (self.dir / "cio" / "sections" / "cio.md").write_text("\n".join(cio), encoding="utf-8")
        rl.write_json(self.dir / "cio" / "scorecard_inputs.json", {"key_quantities": [
            {"label": "liquidity cover", "aliases": ["liquid assets cover"], "value": "0.86x", "claim_ids": ["FIN-C003"]}]})
        problems = synthesis.assemble(self.dir, log=lambda m: None)
        assert problems == [], problems
        (self.dir / "qc" / "verification.json").touch()     # the verification ran after the last ledger was written
        return sc


class EndToEndV32Test(unittest.TestCase):
    def setUp(self):
        self.fx = V32Run()

    def tearDown(self):
        self.fx.cleanup()

    def final(self):
        return run("validate_run.py", self.fx.dir, "--stage", "final")

    def test_specialist_barrier_with_reading_off_and_a_sector_module(self):
        m = rl.load_json(self.fx.dir / rl.RUN_MANIFEST)
        self.assertEqual(m["methodology_version"], rl.methodology_version())
        self.assertEqual(m["reading_mode"], "off")
        self.assertIn("forecasting", m["specialists"])
        r = run("validate_run.py", self.fx.dir, "--stage", "specialists")
        self.assertEqual(r.returncode, 0, r.stdout)
        p = self.fx.dir / "specialists" / "financials.md"     # a missing sector-module row fails the barrier
        step = rl.sector_steps_for(self.fx.dir, "financials")[0]["id"]
        p.write_text("\n".join(l for l in p.read_text(encoding="utf-8").splitlines() if step not in l), encoding="utf-8")
        r = run("validate_run.py", self.fx.dir, "--stage", "specialists")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(step, r.stdout)

    def test_the_assembled_run_passes_and_finalizes(self):
        self.fx.build_report()
        r = self.final()
        self.assertEqual(r.returncode, 0, r.stdout)
        report = (self.fx.dir / "cio" / "final_report.md").read_text(encoding="utf-8")
        self.assertIn(DIGEST_COVERAGE.strip().splitlines()[0], report, "the digest's coverage record is carried")
        self.assertIsNotNone(synthesis.register_block_of(report))
        integ = rl.load_json(self.fx.dir / "qc" / "integration.json")
        self.assertEqual(integ["errors"], [])
        self.assertTrue(any(i["kind"] == "corpus_item" and i["provenance"] == "digest_page_confirmed"
                            for i in synthesis.load_registry(self.fx.dir)), "the digest item is in the registry")
        board = self.fx.tmp / "COMPANY_SCOREBOARD.csv"
        f = run("finalize_run.py", self.fx.dir, "--scoreboard", board)
        self.assertEqual(f.returncode, 0, f.stdout + f.stderr)
        self.assertEqual(rl.load_json(self.fx.dir / rl.RUN_MANIFEST)["status"], "complete")
        self.assertEqual(rl.read_csv(board)[1][0]["methodology_version"], rl.methodology_version())

    def test_a_reading_on_run_passes_through_the_same_pipeline(self):
        self.fx.cleanup()
        self.fx = V32Run(reading="on")
        self.fx.build_report()
        r = self.final()
        self.assertEqual(r.returncode, 0, r.stdout)
        report = (self.fx.dir / "cio" / "final_report.md").read_text(encoding="utf-8")
        self.assertIn("Every in-scope page has been read or accounted for.", report, "the reading coverage record")

    def test_a_gating_finding_that_never_reaches_the_report_fails(self):
        self.fx.build_report(drop_gating=True)
        r = self.final()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("never reaches the report", r.stdout)

    def test_a_key_quantity_stated_two_ways_fails(self):
        self.fx.build_report(kq_value="0.91x")
        r = self.final()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("key_quantities", r.stdout)

    def test_an_unlogged_contradiction_candidate_fails(self):
        self.fx.build_report(log_candidates=False)
        r = self.final()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CC-T1-01", r.stdout)

    def test_a_report_edited_after_assembly_fails(self):
        self.fx.build_report()
        fr = self.fx.dir / "cio" / "final_report.md"
        text = fr.read_text(encoding="utf-8")
        block = synthesis.register_block_of(text)
        fr.write_text(text.replace(block, block + "\n| hand-edited | row |"), encoding="utf-8")
        r = self.final()
        self.assertNotEqual(r.returncode, 0)



class EnginePermissionsTest(unittest.TestCase):
    """The synthesis agents' confinements, the specialists' denial of synthesis/, and the auditor's recomputation."""

    def setUp(self):
        self.fx = V32Run()
        synthesis.build_registry(self.fx.dir, log=lambda m: None)

    def tearDown(self):
        self.fx.cleanup()

    def test_synthesis_agents_are_confined(self):
        import agent_driver as ad
        d = self.fx.dir
        th = ad.synthesis_assignment(d, "theme-analyst", "T1", "x")
        self.assertIn(ad.abs_rule("Read", d / "cio" / "final_report.md"), th.denied, "a theme analyst never sees the report")
        self.assertIn(ad.abs_rule("Read", d / "cio" / "scorecard.json"), th.denied)
        others = [x for x in synthesis.active_themes(d) if x != "T1"]
        self.assertTrue(others)
        for o in others:
            self.assertIn(ad.abs_rule("Read", d / "synthesis" / "themes", "/%s*.md" % o), th.denied)
        self.assertIn(ad.abs_rule("Write", d / "synthesis" / "themes" / "T1.md"), th.allowed)
        self.assertFalse([r for r in th.allowed if r.startswith(("Write(", "Edit(")) and "/themes/T2" in r])
        la = ad.synthesis_assignment(d, "layer-analyst", "L1", "x")
        for o in ("L2", "L3", "L4"):
            self.assertIn(ad.abs_rule("Read", d / "synthesis" / "layers", "/%s_*" % o), la.denied, "L1 never sees %s" % o)
        self.assertIn(ad.abs_rule("Read", d, "/cio/**"), la.denied)
        sw = ad.synthesis_assignment(d, "section-writer", "W1", "x")
        self.assertFalse({"WebSearch", "WebFetch"} & set(sw.tools) | {"WebSearch", "WebFetch"} & set(sw.allowed))
        self.assertIn(ad.abs_rule("Read", d, "/audit/**"), sw.denied)

    def test_specialists_never_read_synthesis_until_cross_examination(self):
        import agent_driver as ad
        d = self.fx.dir
        rule = ad.abs_rule("Read", d, "/synthesis/**")
        self.assertIn(rule, ad.independence_denies(d, "financials"))
        self.assertNotIn(rule, ad.independence_denies(d, "financials", review=True))
        self.assertIn(rule, ad.specialist_assignment(d, "forecasting", "x").denied)

    def test_the_auditor_recomputes_the_scorecard_only_under_audit(self):
        import agent_driver as ad
        a = ad.auditor_assignment(self.fx.dir, "x")
        self.assertIn("Bash(python3 scripts/build_scorecard.py:*)", a.denied)
        self.assertNotIn("Bash(python3 scripts/audit_tools.py:*)", a.denied)
        for out in (self.fx.dir / "cio" / "scorecard.json", self.fx.tmp / "elsewhere.json"):
            r = run("audit_tools.py", "recompute-scorecard", self.fx.dir, "--out", out)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("under RUN_DIR/audit/ only", r.stdout)
        r = run("audit_tools.py", "recompute-scorecard", self.fx.dir)
        self.assertNotIn("under RUN_DIR/audit/ only", r.stdout)


if __name__ == "__main__":
    unittest.main()
