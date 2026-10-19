"""Tests for methodology 3.1.0: the reading stage, structured filings, the model policy and the reading audit.

Run:  python3 -m unittest discover tests -v

Two synthetic annual reports of a fictional company are built as text layers in a temporary run; nothing here is
research on a real company and nothing touches the network.
"""

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import research_lib as rl  # noqa: E402
import reading  # noqa: E402
import reading_audit  # noqa: E402
import agent_driver  # noqa: E402
import verify  # noqa: E402
import structured_filings as sf  # noqa: E402

PY = sys.executable
LONG_NARRATIVE = ("Fixture Co continued to expand its network across the country during the year under review, adding "
                  "thousands of new sites in rural districts. The company also completed the upgrade of its core platform "
                  "for enterprise customers ahead of the schedule it had announced. Our strategy remains focused on "
                  "premium customers and digital services across every circle.")


def auditor_page(fy):
    return ("Independent Auditor's Report\n\nTo the Members of Fixture Co Limited\n\nOpinion\n\n"
            "We have audited the accompanying standalone financial statements of Fixture Co Limited, which comprise the "
            "Standalone Balance Sheet as at March 31, %d and the Statement of Profit and Loss for the year then ended. "
            "In our opinion, the financial statements give a true and fair view of the state of affairs of the Company." % fy)


def notes_page(cur, prior):
    return ("Notes to the Standalone Financial Statements\n\n34. Contingent liabilities\n\n"
            "| Claims not acknowledged as debts | %s | %s |\n| Guarantees given to banks | 500 | 400 |" % (cur, prior))


def make_text_layer(base: Path, key: str, pages, flags=None) -> Path:
    d = base / "_cache" / "text" / key
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# Text layer — fixture %s" % key, ""]
    index = []
    for i, text in enumerate(pages, 1):
        start = len(lines) + 1
        lines.append("<<<PAGE %d/%d>>>" % (i, len(pages)))
        lines += text.split("\n") if text else ["(no text layer on this page: read the rendered page)"]
        lines.append("")
        index.append({"page": i, "start_line": start, "end_line": len(lines), "printed": str(i),
                      "flags": (flags or {}).get(i, []), "regions": [{"sections": []}]})
    (d / "pages.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    meta = {"source": str(d / "report.pdf"), "sha256": hashlib.sha256(key.encode()).hexdigest(), "pages": len(pages),
            "page_index": index, "toc": [], "flagged_pages": {}}
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return d / "pages.md"


class ReadingFixture:
    def __init__(self, pages25=None, pages24=None, flags25=None, flags24=None, tmp=None, run_id="20260301T090000Z",
                 years=2, core_years=0, plan_now=True):
        self.tmp = tmp or Path(tempfile.mkdtemp(prefix="eqr-read-"))
        self.run_id = run_id
        r = subprocess.run([PY, str(ROOT / "scripts" / "new_run.py"), "--ticker", "FIXREAD", "--company", "Fixture Co Ltd",
                            "--exchange", "NSE", "--segment", "main", "--cutoff", "2026-03-01", "--run-id", self.run_id,
                            "--root", str(self.tmp)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        self.dir = self.tmp / r.stdout.strip()
        if pages25 is None:
            pages25 = ["Integrated Report 2024-25\n\n" + LONG_NARRATIVE, auditor_page(2025), notes_page("1,23,456", "1,10,234"), ""]
            flags25 = {4: ["image_only"]}
        if pages24 is None:
            pages24 = ["Integrated Report 2023-24\n\n" + LONG_NARRATIVE, auditor_page(2024), notes_page("1,10,234", "98,765"), ""]
            flags24 = {4: ["image_only"]}
        p25 = make_text_layer(self.dir, "ar2025", pages25, flags25)
        p24 = make_text_layer(self.dir, "ar2024", pages24, flags24)
        with (self.dir / "corpus" / "document_map.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["doc_type", "period", "status", "text_path", "filed"])
            w.writeheader()
            w.writerow({"doc_type": "annual_report", "period": "FY2025", "status": "both",
                        "text_path": str(p25.relative_to(self.dir)), "filed": "2025-07-01"})
            w.writerow({"doc_type": "annual_report", "period": "FY2024", "status": "both",
                        "text_path": str(p24.relative_to(self.dir)), "filed": "2024-07-01"})
        self.plan = reading.plan(self.dir, years, 24, 12, core_years, log=lambda m: None) if plan_now else None

    def store(self, cid):
        return reading.chunk_cache(self.dir, cid)

    def write_audit_pass(self):
        """A passed reading audit of this run (as reading_audit.py writes it) for every extraction it holds."""
        rows = []
        for f in sorted((self.dir / reading.READING / "extractions").glob("*.jsonl")):
            cid, role = f.name[:-len(".jsonl")].rsplit(".", 1)
            rows.append({"agent": reading.ROLE_AGENT[role], "launch": "L001", "role": role, "chunk": cid,
                         "lines_seen": 10, "lines_total": 10, "first_missing_lines": [], "view_pages_missing": []})
        (self.dir / "qc").mkdir(exist_ok=True)
        (self.dir / rl.READING_AUDIT).write_text(json.dumps({"status": "PASS", "readers": rows, "reused": []}))

    def write_extraction(self, cid, role, drop_cl=False, mutate=None):
        st = self.store(cid)
        rows = []
        for lid in st["order"]:
            u = st["units"][lid]
            if "Claims not acknowledged" in u["text"] and not drop_cl:
                amounts = [c.strip() for c in u["text"].strip("| ").split("|")][1:]
                rows.append({"type": "contingent_liability", "unit": lid, "page": u["page"], "period": "as at 31-Mar",
                             "basis": "standalone", "quote": u["text"].strip(),
                             "fields": {"category": "Claims not acknowledged as debts", "amount_current": amounts[0],
                                        "amount_prior": amounts[1], "unit_of_amount": "INR million", "description": ""}})
            if u["text"].startswith("Fixture Co continued"):
                rows.append({"type": "other_fact", "unit": lid, "page": u["page"], "period": "", "basis": "na",
                             "quote": u["text"][:60], "fields": {"description": "network expansion"}})
        for k, u in st["units"].items():
            if u.get("visual"):
                rows.append({"type": "other_fact", "unit": k, "page": u["page"], "period": "", "basis": "na", "quote": "",
                             "source": "rendered", "fields": {"description": "photograph of a tower"}})
        cited = {r["page"] for r in rows}
        view = set(reading.view_pages(st))
        for pg in st["pages"]:
            rows.append({"type": "page_receipt", "page": pg, "status": "items" if pg in cited else "no_items",
                         "reason": "" if pg in cited else "headings only", "viewed": pg in view})
        rows.append({"type": "chunk_receipt", "chunk": cid, "role": role, "model": "fixture-model",
                     "units_read": st["new_units"], "pages_viewed": sorted(view)})
        if mutate:
            rows = mutate(rows)
        path = reading.extraction_path(self.dir, cid, role)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return path

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.fx = ReadingFixture()

    def tearDown(self):
        self.fx.cleanup()

    def test_classes_repeats_and_visual_pages(self):
        p = self.fx.plan
        docs = {d["key"]: d for d in p["documents"]}
        self.assertEqual([d["key"] for d in p["documents"]], ["AR-FY2025", "AR-FY2024"], "newest first")
        r25 = {r["page"]: r for r in docs["AR-FY2025"]["page_records"]}
        r24 = {r["page"]: r for r in docs["AR-FY2024"]["page_records"]}
        self.assertEqual(r25[2]["class"], "auditor_report")
        self.assertTrue(r25[2]["critical"])
        self.assertTrue(r25[3]["critical"], "a contingent-liability note is critical")
        self.assertFalse(r25[1]["critical"])
        self.assertTrue(r25[4]["visual"])
        # FY2024 page 1 repeats FY2025's narrative sentence for sentence except its title: only the title is new
        self.assertGreaterEqual(r24[1]["repeat"], 3)
        units = json.loads((self.fx.dir / reading.CACHE / "units" / "AR-FY2024.json").read_text())["pages"]
        rep = [u for u in units["2"] if u.get("status") == "repeat"]
        self.assertTrue(any("true and fair view" in u["text"] for u in rep), "an unchanged audit sentence is read once")

    def test_chunk_files_state_line_count_and_view_pages(self):
        for c in self.fx.plan["chunks"]:
            st = self.fx.store(c["id"])
            text = (self.fx.dir / reading.CACHE / "chunks" / ("%s.md" % c["id"])).read_text()
            self.assertEqual(text.count("\n"), st["lines"])
            self.assertIn("This file has %d lines" % st["lines"], text)
            for pg in st["visual_pages"]:
                self.assertIn("<<<PAGE %d" % pg, text)
                self.assertIn("VIEW REQUIRED", text)

    def test_navigation_lines_and_titles(self):
        bodies = [["Overview", "Statutory Reports", "Financial Statements", "page %d text" % i] for i in range(20)]
        nav = reading.navigation_lines(bodies)
        self.assertIn("statutory reports", nav)
        title = reading.page_sections({"regions": []}, ["Independent Auditor's Report", "", "To the Members of X"], nav)
        self.assertIn("independent_auditors_report", title)
        inside = reading.page_sections({"regions": []}, [
            "The other information comprises the information included in the Annual Report, but does not include the",
            "Board's Report including Annexures to Board's Report, Business Responsibility and Sustainability Report",
            "and the financial statements and our auditor's report thereon."], nav)
        self.assertNotIn("boards_report", inside, "a section named inside a paragraph is not a title")


class TestReadingLoop(unittest.TestCase):
    def setUp(self):
        self.fx = ReadingFixture()

    def tearDown(self):
        self.fx.cleanup()

    def test_full_loop_with_disagreement_dossiers_and_status(self):
        self.assertEqual(rl.model_policy()["calibration"]["status"], "pending")
        act = reading.next_action(self.fx.dir)
        self.assertEqual(act["action"], "launch")
        self.assertEqual(act["agent"], "critical-reader", "uncalibrated chunks are read by both models")
        self.assertIn(self.fx.run_id, act["description"])
        chunks = [c["id"] for c in self.fx.plan["chunks"]]
        crit_chunk = next(c["id"] for c in self.fx.plan["chunks"] if c["critical"] and c["doc"] == "AR-FY2025")
        for cid in chunks:
            self.fx.write_extraction(cid, "critical")
            self.fx.write_extraction(cid, "reader", drop_cl=(cid == crit_chunk))
            for role in ("critical", "reader"):
                res = reading.check(self.fx.dir, cid, role)
                self.assertTrue(res.ok, (cid, role, res.errors))
        act = reading.next_action(self.fx.dir)
        self.assertEqual(act["role"], "resolved")
        self.assertIn(crit_chunk, act["chunks"])
        dis = json.loads((self.fx.dir / reading.READING / "disagreements" / ("%s.json" % crit_chunk)).read_text())
        self.assertEqual(dis["count"], 1)
        d = dis["disagreements"][0]
        self.assertEqual((d["kind"], d["type"]), ("only_A", "contingent_liability"))
        res_rows = [{"type": "resolution", "id": d["id"], "decision": "A", "reason": "the row is on the page", "items": d["A"]},
                    {"type": "chunk_receipt", "chunk": crit_chunk, "role": "resolved", "model": "fixture-model"}]
        reading.extraction_path(self.fx.dir, crit_chunk, "resolved").write_text(
            "\n".join(json.dumps(r) for r in res_rows) + "\n", encoding="utf-8")
        self.assertTrue(reading.check(self.fx.dir, crit_chunk, "resolved").ok)
        self.assertEqual(reading.next_action(self.fx.dir)["action"], "done")
        reading.dossiers(self.fx.dir, log=lambda m: None)
        cont = (self.fx.dir / reading.DOSSIERS / "contingencies.md").read_text()
        self.assertIn("1,23,456", cont)
        self.assertIn("1,10,234", cont)
        self.assertIn("**Claims not acknowledged as debts** · contingent_liability · standalone · inr million: "
                      "FY2025 1,23,456 (AR-FY2025 p.3) · FY2024 1,10,234 (AR-FY2025 p.3, AR-FY2024 p.3) · "
                      "FY2023 98,765 (AR-FY2024 p.3)", cont, "one line per series, every year and page")
        self.assertNotIn("Changed comparatives", cont, "the comparatives agree")
        other = (self.fx.dir / reading.DOSSIERS / "other.reference.md").read_text()
        self.assertIn("also in: AR-FY2024 p.1", other, "a repeated passage carries its items to every place it repeats")
        pack = (self.fx.dir / reading.DOSSIERS / "packs" / "filings.md").read_text()
        self.assertIn("| `corpus/dossiers/contingencies.md` |", pack)
        self.assertIn("- corpus/dossiers/contingencies.reference.md", pack, "reference parts are listed, not required")
        self.assertNotIn("`corpus/dossiers/contingencies.reference.md`", pack)
        for name in rl.SPECIALISTS:
            self.assertTrue((self.fx.dir / reading.DOSSIERS / "packs" / ("%s.md" % name)).exists())
        st = reading.status(self.fx.dir, log=lambda m: None)
        self.assertTrue(st["complete"], st)
        self.assertEqual(st["pending"], 0)
        cov = (self.fx.dir / rl.READING_COVERAGE).read_text()
        self.assertEqual(hashlib.sha256(cov.encode()).hexdigest(), st["coverage_sha256"])
        # the final report must carry the block unchanged
        res = rl.Result("final")
        rl.check_reading_coverage_block("x <!-- READING_COVERAGE:BEGIN -->\n%s\n<!-- READING_COVERAGE:END -->" % cov.strip(),
                                        self.fx.dir, res)
        self.assertTrue(res.ok, res.errors)
        res2 = rl.Result("final")
        rl.check_reading_coverage_block("<!-- READING_COVERAGE:BEGIN -->\nEvery page read.\n<!-- READING_COVERAGE:END -->",
                                        self.fx.dir, res2)
        self.assertFalse(res2.ok)

    def test_a_changed_comparative_is_flagged_on_both_pages(self):
        fx = ReadingFixture(pages24=["Integrated Report 2023-24\n\n" + LONG_NARRATIVE, auditor_page(2024),
                                     notes_page("1,10,000", "98,765"), ""], flags24={4: ["image_only"]})
        try:
            for c in fx.plan["chunks"]:
                for role in reading.required_roles(c):
                    fx.write_extraction(c["id"], role)
            reading.dossiers(fx.dir, log=lambda m: None)
            cont = (fx.dir / reading.DOSSIERS / "contingencies.md").read_text()
            self.assertIn("## Changed comparatives (1)", cont)
            self.assertIn("FY2024: 1,10,234 (AR-FY2025 p.3) ≠ 1,10,000 (AR-FY2024 p.3)", cont)
        finally:
            fx.cleanup()

    def test_pending_chunks_make_status_incomplete(self):
        st = reading.status(self.fx.dir, log=lambda m: None)
        self.assertFalse(st["complete"])
        self.assertGreater(st["pending"], 0)


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.fx = ReadingFixture()
        self.cid = next(c["id"] for c in self.fx.plan["chunks"] if c["critical"] and c["doc"] == "AR-FY2025")
        self.vid = next(c["id"] for c in self.fx.plan["chunks"] if c["visual_pages"])

    def tearDown(self):
        self.fx.cleanup()

    def errors(self, cid, mutate):
        self.fx.write_extraction(cid, "reader", mutate=mutate)
        return " | ".join(reading.check(self.fx.dir, cid, "reader").errors)

    def test_quote_must_be_in_its_passage(self):
        def bad(rows):
            for r in rows:
                if r["type"] == "contingent_liability":
                    r["quote"] = "Claims not acknowledged as debts 9,99,999"
            return rows
        self.assertIn("quote not found verbatim", self.errors(self.cid, bad))

    def test_amount_must_be_printed_in_the_quote(self):
        def bad(rows):
            for r in rows:
                if r["type"] == "contingent_liability":
                    r["fields"]["amount_current"] = "123456"
            return rows
        self.assertIn("is not printed in the quote", self.errors(self.cid, bad))

    def test_every_page_needs_one_receipt(self):
        self.assertIn("expected one page_receipt", self.errors(self.cid, lambda rows: [r for r in rows if r["type"] != "page_receipt"]))

    def test_view_required_page_must_be_viewed(self):
        def bad(rows):
            for r in rows:
                if r["type"] == "page_receipt":
                    r["viewed"] = False
                if r["type"] == "chunk_receipt":
                    r["pages_viewed"] = []
            return rows
        e = self.errors(self.vid, bad)
        self.assertIn("VIEW REQUIRED", e)
        self.assertIn("pages_viewed lacks", e)

    def test_units_read_must_match_the_chunk(self):
        def bad(rows):
            rows[-1]["units_read"] = 1
            return rows
        self.assertIn("units_read", self.errors(self.cid, bad))

    def test_valid_extraction_passes(self):
        self.fx.write_extraction(self.cid, "reader")
        res = reading.check(self.fx.dir, self.cid, "reader")
        self.assertTrue(res.ok, res.errors)


class TestReadingAudit(unittest.TestCase):
    def setUp(self):
        self.fx = ReadingFixture()
        self.tdir = self.fx.tmp / "transcripts"
        act = reading.next_action(self.fx.dir)                  # issues launch L001 (critical-reader)
        self.launch = act["launch"]
        self.chunks = act["chunks"]

    def tearDown(self):
        self.fx.cleanup()

    def transcript(self, name, agent_type, desc, model, effort, full=True, view=True):
        sub = self.tdir / "session1" / "subagents"
        sub.mkdir(parents=True, exist_ok=True)
        (sub / ("%s.meta.json" % name)).write_text(json.dumps({"agentType": agent_type, "description": desc}))
        entries = [{"type": "user", "timestamp": "2026-03-01T10:00:00Z",
                    "message": {"role": "user", "content": "You are the reader for run %s" % self.fx.run_id}}]
        n = 0
        for cid in self.chunks:
            st = self.fx.store(cid)
            path = self.fx.dir / reading.CACHE / "chunks" / ("%s.md" % cid)
            lines = path.read_text().split("\n")
            shown = lines if full else lines[: len(lines) // 2]
            n += 1
            entries.append({"type": "assistant", "effort": effort, "timestamp": "2026-03-01T10:01:00Z",
                            "message": {"id": "m%d" % n, "model": model, "content": [
                                {"type": "tool_use", "id": "t%d" % n, "name": "Read", "input": {"file_path": st["file"]}}]}})
            entries.append({"type": "user", "timestamp": "2026-03-01T10:01:01Z", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t%d" % n,
                 "content": "\n".join("%d\t%s" % (i, ln) for i, ln in enumerate(shown, 1))}]}})
            if view:
                for pg in reading.view_pages(st):
                    n += 1
                    entries.append({"type": "assistant", "effort": effort, "message": {"id": "m%d" % n, "model": model, "content": [
                        {"type": "tool_use", "id": "t%d" % n, "name": "Read", "input": {"file_path": st["pdf"], "pages": str(pg)}}]}})
                    entries.append({"type": "user", "message": {"content": [
                        {"type": "tool_result", "tool_use_id": "t%d" % n, "content": "[page image]"}]}})
        (sub / ("%s.jsonl" % name)).write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    def test_complete_read_on_pinned_model_passes(self):
        self.transcript("agent-a", "critical-reader", "critical-reader %s %s" % (self.fx.run_id, self.launch), "claude-opus-5-5", "max")
        res = reading_audit.run_audit(self.fx.dir, self.tdir)
        self.assertEqual(res["status"], "PASS", res["errors"])
        self.assertTrue(res["readers"])

    def test_missing_lines_views_and_effort_are_errors(self):
        self.transcript("agent-b", "critical-reader", "critical-reader %s %s" % (self.fx.run_id, self.launch), "claude-opus-5-5", "high",
                        full=False, view=False)
        res = reading_audit.run_audit(self.fx.dir, self.tdir)
        self.assertEqual(res["status"], "FAIL")
        text = " | ".join(res["errors"])
        self.assertIn("did not receive every line", text)
        self.assertIn("did not open VIEW REQUIRED pages", text)
        self.assertIn("ran at effort ['high'], pinned xhigh", text)

    def test_wrong_model_is_an_error(self):
        self.transcript("agent-c", "critical-reader", "critical-reader %s %s" % (self.fx.run_id, self.launch), "claude-sonnet-5-5", "max")
        res = reading_audit.run_audit(self.fx.dir, self.tdir)
        self.assertIn("pinned opus", " | ".join(res["errors"]))

    def test_no_transcripts_is_not_measurable(self):
        res = reading_audit.run_audit(self.fx.dir, self.fx.tmp / "nowhere")
        self.assertEqual(res["status"], "NOT_MEASURABLE")


class TestStructuredFilings(unittest.TestCase):
    XBRL = """<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
  xmlns:in-capmkt="http://example.invalid/capmkt" xmlns:ax="http://example.invalid/axes">
 <xbrli:context id="D1"><xbrli:entity><xbrli:identifier scheme="x">X</xbrli:identifier>
  <xbrli:segment><xbrldi:explicitMember dimension="ax:CategoryAxis">ax:PublicMember</xbrldi:explicitMember>
  <xbrldi:typedMember dimension="ax:ResolutionAxis"><ax:ResolutionDomain>3</ax:ResolutionDomain></xbrldi:typedMember></xbrli:segment>
  </xbrli:entity><xbrli:period><xbrli:startDate>2025-04-01</xbrli:startDate><xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:unit id="U"><xbrli:measure>shares</xbrli:measure></xbrli:unit>
 <in-capmkt:NumberOfVotesAgainst contextRef="D1" unitRef="U" decimals="0">12345</in-capmkt:NumberOfVotesAgainst>
 <in-capmkt:DescriptionOfResolutionConsidered contextRef="D1">Approval of related party transactions with Fixture Holdings</in-capmkt:DescriptionOfResolutionConsidered>
</xbrli:xbrl>"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-sf-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dimensional_instance(self):
        p = self.tmp / "v.xml"
        p.write_text(self.XBRL, encoding="utf-8")
        ctx, facts = sf.parse_instance(p)
        self.assertEqual(ctx["D1"]["dims"], {"CategoryAxis": "PublicMember", "ResolutionAxis": "3"})
        rows = sf.fact_rows(ctx, facts, {"meeting_type": "AGM"})
        votes = next(r for r in rows if r["concept"] == "NumberOfVotesAgainst")
        self.assertEqual((votes["value"], votes["period"]), ("12345", "2025-04-01..2026-03-31"))
        self.assertIn("ResolutionAxis=3", votes["dims"])

    def test_audit_opinion_view(self):
        html = ("<table><tr><td>Declaration of unmodified opinion or statement on impact of audit qualification</td>"
                "<td>Declaration of unmodified opinion</td></tr><tr><td>Details of Impact of Audit Qualification</td></tr>"
                "<tr><th>Sr No.</th><th>Audit firm's name</th><th>Peer review</th></tr>"
                "<tr><td>1</td><td>Fixture &amp; Co LLP</td><td>Yes</td></tr>"
                "<tr><td>Share of profit of associates</td><td>12</td></tr></table>")
        a = sf.audit_opinion_from_view(html)
        self.assertEqual(a["declaration"], "Declaration of unmodified opinion")
        self.assertEqual(a["firms"], ["Fixture & Co LLP"])

    def test_brsr_page_covered_only_when_numbers_and_text_match(self):
        run = self.tmp / "run"
        (run / "corpus" / "structured").mkdir(parents=True)
        rows = [{"fy": "FY2025", "concept": "c%d" % i, "value": str(v)} for i, v in enumerate((1234.5, 0.455, 98765, 4321, 777))]
        narrative = "The company has a board approved policy on human rights covering all employees and value chain partners"
        rows.append({"fy": "FY2025", "concept": "t", "value": narrative})
        with (run / "corpus" / "structured" / "brsr_facts.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["fy", "concept", "value", "source_url"], extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        test = sf.brsr_coverage_tester(run)
        ok, why = test(2025, ["| Employees | 1,234.5 | 45.5% | 98,765 |", "| Trainings | 4,321 | 777 |", narrative + "."])
        self.assertTrue(ok, why)
        ok2, _ = test(2025, ["| Employees | 1,234.5 | 45.5% | 98,765 |", "| Trainings | 4,321 | 999 |",
                             "A new incident occurred at the plant that the filing does not mention in any form at all."])
        self.assertFalse(ok2)


class TestPolicyAndContracts(unittest.TestCase):
    def test_policy_pins_every_agent_and_workers_are_registered(self):
        pol = rl.model_policy()["agents"]
        self.assertEqual(set(pol), set(rl.SPECIALISTS) | {"cio", rl.AUDITOR} | set(rl.WORKERS))
        for name, spec in pol.items():
            fm = rl.parse_front_matter((rl.AGENTS_DIR / ("%s.md" % name)).read_text(encoding="utf-8"))
            self.assertEqual((fm.get("model"), fm.get("effort")), (spec["model"], spec["effort"]), name)
        self.assertEqual((pol["reader"]["model"], pol["critical-reader"]["model"]), ("sonnet", "opus"))
        for name in set(rl.SPECIALISTS) | {"cio", rl.AUDITOR}:
            self.assertEqual((pol[name]["model"], pol[name]["effort"]), ("opus", "xhigh"), name)   # owner decision 2026-10-19

    def test_specialists_must_not_claim_their_own_coverage(self):
        res = rl.Result("r")
        rl.check_no_coverage_claims("Annual reports FY2016-FY2025 were read in full.\nKAMs read in substance.", res)
        self.assertEqual(len(res.errors), 2)
        ok = rl.Result("r")
        rl.check_no_coverage_claims("Periods used: FY2016-FY2025 (corpus/reading/COVERAGE.md).", ok)
        self.assertTrue(ok.ok)

    def test_reading_schema_is_consistent(self):
        sch = rl.reading_schema()
        for t, spec in sch["types"].items():
            self.assertIn(spec["topic"], sch["topics"], t)
            self.assertTrue(set(spec["amounts"]) <= set(spec["fields"]), t)
        for c in reading.SECTION_TO_CLASS.values():
            self.assertIn(c, sch["classes"])
        crit = {c for c, v in sch["classes"].items() if v["critical"]}
        self.assertTrue({"auditor_report", "caro", "ifc", "notes_critical", "board", "aoc2", "secretarial"} <= crit)

    def test_required_roles_follow_calibration(self):
        chunk = {"critical": False, "classes": ["narrative"]}
        pending = {"calibration": {"status": "pending", "single_read_classes": []}}
        passed = {"calibration": {"status": "passed", "single_read_classes": ["narrative"]}}
        self.assertEqual(reading.required_roles(chunk, pending), ["critical", "reader"])
        self.assertEqual(reading.required_roles(chunk, passed), ["reader"])
        self.assertEqual(reading.required_roles(dict(chunk, critical=True), passed), ["critical", "reader"])
        self.assertEqual(reading.required_roles(dict(chunk, classes=["narrative", "mdna"]), passed), ["critical", "reader"])


CASH_FLOW = ("Consolidated Statement of Cash Flows\n\nFor the year ended\n\nMarch 31, 2025\n\nMarch 31, 2024\n\n"
             "Net loss on derivative financial instruments\n\n420\n\n6,319\n\n"
             "Acquisition of a subsidiary, net of cash proceeds (refer note 4(o))\n\n-\n\n(6,428)\n\n"
             "Interest income\n\n(5,306)\n\n(6,493)\n\nFinance costs\n\n216,258\n\n219,337\n\n"
             "Inventories\n\n(1,416)\n\n(771)\n\nOther non-cash items\n\n396\n\n823\n\n1")
PARA_A = ("The Company maintains a robust risk management framework approved by the Board of Directors. "
          "During the year the Company added 12,345 new sites across rural districts of the country. "
          "The framework is reviewed every year by the Risk Management Committee of the Board.")
PARA_B = ("The Company maintains a robust risk management framework approved by the Board of Directors. "
          "During the year the Company added 23,456 new sites across rural districts of the country. "
          "The framework is reviewed every year by the Risk Management Committee of the Board.")
TABLE_SAME = "| Name of the director | Category of directorship held |\n| Fixture Person One | Independent and non-executive |"
TABLE_A = TABLE_SAME + "\n| Fixture Person Two | Executive director and managing director |"
TABLE_B = TABLE_SAME + "\n| Fixture Person Three | Executive director and managing director |"
LONG_LABEL = "Purchase of property, plant and equipment and capital work-in-progress"


class TestPassagesAndReadOnce(unittest.TestCase):
    """Run BHARTIARTL 20261017T000000Z L001 found: short values and dashes hidden as trivial, labels and column
    headers hidden as repeats, an ambiguous multi-line format, image pages never viewed."""

    def setUp(self):
        p25 = [CASH_FLOW, PARA_A, "Board of Directors\n\n" + TABLE_A + "\n\nCommittees\n\n" + TABLE_SAME,
               LONG_LABEL + "\n\n(379,077)\n\n(381,915)"]
        p24 = [CASH_FLOW.replace("420", "512"), PARA_B, "Board of Directors\n\n" + TABLE_B + "\n\nCommittees\n\n" + TABLE_SAME,
               LONG_LABEL + "\n\n(381,915)\n\n(300,111)"]
        self.fx = ReadingFixture(p25, p24, {}, {})

    def tearDown(self):
        self.fx.cleanup()

    def units(self, key):
        return json.loads((self.fx.dir / reading.CACHE / "units" / ("%s.json" % key)).read_text())["pages"]

    def chunk_of(self, doc, page):
        return next(c for c in self.fx.plan["chunks"] if c["doc"] == doc and page in c["pages"])

    def test_values_dashes_are_passages_and_page_number_is_furniture(self):
        us = self.units("AR-FY2025")["1"]
        texts = {u["text"]: u for u in us}
        for v in ("420", "-", "(6,428)", "(771)", "396"):
            self.assertTrue(texts[v]["id"], "%r must be a passage (a value), not hidden" % v)
        self.assertEqual(texts["1"].get("marker"), "page_number", "the printed page number is furniture")
        c = self.chunk_of("AR-FY2025", 1)
        self.assertIn(1, c["verify_pages"], "a table printed one cell per line is confirmed on the image")
        text = (self.fx.dir / reading.CACHE / "chunks" / ("%s.md" % c["id"])).read_text()
        self.assertIn("VIEW REQUIRED (cell_layout)", text)
        self.assertIn("(page number) 1", text)

    def test_quote_runs_on_from_a_label_to_its_values(self):
        c = self.chunk_of("AR-FY2025", 1)
        st = self.fx.store(c["id"])
        lid = next(k for k in st["order"] if st["units"][k]["text"] == "Net loss on derivative financial instruments")
        val = next(k for k in st["order"] if st["units"][k]["text"] == "420")

        def rows(unit, quote):
            return [{"type": "statement_line", "unit": unit, "page": 1, "period": "FY2025", "basis": "consolidated",
                     "quote": quote, "fields": {"statement": "cash flow", "line_item": "Net loss on derivative financial instruments",
                                                "value_current": "420", "value_prior": "6,319", "unit_of_amount": ""}}]
        ok = self.fx.write_extraction(c["id"], "reader", mutate=lambda r: rows(lid, "Net loss on derivative financial instruments 420 6,319") + r)
        self.assertTrue(reading.check(self.fx.dir, c["id"], "reader").ok, reading.check(self.fx.dir, c["id"], "reader").errors)
        self.fx.write_extraction(c["id"], "reader", mutate=lambda r: rows(lid, "420 6,319") + r)
        self.assertIn("starting in passage", " | ".join(reading.check(self.fx.dir, c["id"], "reader").errors))
        self.fx.write_extraction(c["id"], "reader", mutate=lambda r: rows(val, "420 6,319") + r)
        self.assertTrue(reading.check(self.fx.dir, c["id"], "reader").ok)
        self.assertTrue(ok)

    def test_short_text_labels_and_changed_tables_are_always_read(self):
        u24 = self.units("AR-FY2024")
        st = {u["text"]: u.get("status") for pg in u24.values() for u in pg if u.get("id")}
        self.assertEqual(st["Net loss on derivative financial instruments"], "new", "a short label is always read")
        self.assertEqual(st["For the year ended"], "new", "a column header is always read")
        self.assertEqual(st[LONG_LABEL], "new", "a long label followed by its values is always read")
        p3 = [u for u in u24["3"] if u.get("id") and u["kind"] == "table"]
        self.assertEqual([u["status"] for u in p3[:3]], ["new"] * 3,
                         "every row of a changed table is read, the unchanged header and row included")
        self.assertEqual([u["status"] for u in p3[3:]], ["repeat", "repeat"], "a whole table that repeats is read once")

    def test_repeated_sentence_before_new_text_is_context(self):
        u24 = self.units("AR-FY2024")["2"]
        st = [(u["text"][:40], u.get("status")) for u in u24 if u.get("id")]
        self.assertEqual([s for _, s in st], ["context", "new", "repeat"], st)
        c = self.chunk_of("AR-FY2024", 2)
        text = (self.fx.dir / reading.CACHE / "chunks" / ("%s.md" % c["id"])).read_text()
        self.assertIn("· context (read in AR-FY2025 p.2): The Company maintains a robust", text)
        self.assertIn("⟲ 1 passage", text)
        store = self.fx.store(c["id"])
        self.assertFalse(any("robust risk management" in u["text"] for u in store["units"].values()),
                         "context is not citable")

    def test_continuation_lines_are_indented(self):
        fx = ReadingFixture(["As per our report of even date\nFor Fixture & Co LLP\nChartered Accountants\n\nPartner name"],
                            ["Integrated Report 2023-24"], {}, {})
        try:
            c = fx.plan["chunks"][0]
            text = (fx.dir / reading.CACHE / "chunks" / ("%s.md" % c["id"])).read_text()
            self.assertIn("[a1] As per our report of even date\n    For Fixture & Co LLP\n    Chartered Accountants", text)
        finally:
            fx.cleanup()


class TestNumbersAndRendered(unittest.TestCase):
    def setUp(self):
        self.fx = ReadingFixture()
        self.cid = next(c["id"] for c in self.fx.plan["chunks"] if c["critical"] and c["doc"] == "AR-FY2025")

    def tearDown(self):
        self.fx.cleanup()

    def item(self, t, unit, quote, fields, **kw):
        st = self.fx.store(self.cid)
        return dict({"type": t, "unit": unit, "page": st["units"][unit]["page"], "period": "", "basis": "na",
                     "quote": quote, "fields": fields}, **kw)

    def errs(self, extra):
        self.fx.write_extraction(self.cid, "reader", mutate=lambda rows: extra + rows)
        return " | ".join(reading.check(self.fx.dir, self.cid, "reader").errors)

    def test_numbers_in_free_text_must_be_printed_in_the_quote(self):
        st = self.fx.store(self.cid)
        cl = next(k for k in st["order"] if "Claims not acknowledged" in st["units"][k]["text"])
        g = next(k for k in st["order"] if "Guarantees given" in st["units"][k]["text"])
        bad = self.item("other_fact", cl, "Claims not acknowledged as debts", {"description": "claims of 7,733,594 in total"})
        self.assertIn("field description has 7733594", self.errs([bad]))
        ok = self.item("other_fact", cl, "Claims not acknowledged as debts 1,23,456", {"description": "claims of 1,23,456"})
        self.assertEqual(self.errs([ok]), "")
        unusual = self.item("unusual", cl, "Claims not acknowledged as debts 1,23,456",
                            {"description": "claims 1,23,456 exceed the guarantees of 500", "why_unusual": "comparison"})
        self.assertIn("or its related passages", self.errs([unusual]))
        self.assertEqual(self.errs([dict(unusual, related=[g])]), "")
        self.assertIn("is not a passage of this chunk", self.errs([dict(unusual, related=["a999"])]))

    def test_rendered_unit_only_on_view_required_pages(self):
        st = self.fx.store(self.cid)
        pg = st["units"][st["order"][0]]["page"]
        it = {"type": "other_fact", "unit": "p%d" % pg, "page": pg, "period": "", "basis": "na", "quote": "",
              "source": "rendered", "fields": {"description": "x"}}
        self.assertIn("is not a passage of this chunk", self.errs([it]))

    def test_swapped_current_and_prior_amounts_are_a_disagreement(self):
        def swap(rows):
            for r in rows:
                if r["type"] == "contingent_liability":
                    f = r["fields"]
                    f["amount_current"], f["amount_prior"] = f["amount_prior"], f["amount_current"]
            return rows
        self.fx.write_extraction(self.cid, "critical")
        self.fx.write_extraction(self.cid, "reader", mutate=swap)
        self.assertTrue(reading.check(self.fx.dir, self.cid, "reader").ok, "both amounts are printed: the check passes")
        dis = reading.compare_chunk(self.fx.dir, self.cid, write=False)
        self.assertEqual([(d["kind"], d["type"]) for d in dis], [("differ", "contingent_liability")])


class TestRenderAndImages(unittest.TestCase):
    def test_pgm_rotate_split_and_png(self):
        import struct
        import zlib
        w, h, pix = reading.pgm_parse(b"P5\n# comment\n3 2\n255\n" + bytes([1, 2, 3, 4, 5, 6]))
        self.assertEqual((w, h, pix), (3, 2, bytes([1, 2, 3, 4, 5, 6])))
        self.assertEqual(reading.rotate_gray(w, h, pix, 90), (2, 3, bytes([4, 1, 5, 2, 6, 3])))
        self.assertEqual(reading.rotate_gray(w, h, pix, 270), (2, 3, bytes([3, 6, 2, 5, 1, 4])))
        self.assertEqual(reading.rotate_gray(w, h, pix, 180), (3, 2, bytes([6, 5, 4, 3, 2, 1])))
        parts = reading.split_gray(4, 1, bytes([1, 2, 3, 4]), 2)
        self.assertEqual([p[2] for p in parts], [bytes([1, 2]), bytes([3, 4])])
        png = reading.png_gray(w, h, pix)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(struct.unpack(">II", png[16:24]), (3, 2))
        idat = png[png.index(b"IDAT") + 4:png.index(b"IEND") - 8]
        self.assertEqual(zlib.decompress(idat), b"\x00\x01\x02\x03\x00\x04\x05\x06")

    def test_image_shares_ignore_furniture_and_masks(self):
        info = "Page    1 size: 612 x 792 pts (letter)\nPage    2 size: 612 x 792 pts (letter)\n"
        head = "page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio\n" + "-" * 90 + "\n"
        rows = ["   1     0 image    1530  1980  rgb     3   8  jpeg   no        10  0   300   300  200K 2.3%",   # 36 % of p1
                "   1     1 smask    1530  1980  gray    1   8  image  no        11  0   300   300   20K 1.0%"]
        rows += ["   %d     2 image     300   100  rgb     3   8  jpeg   no        12  0   300   300   10K 1.0%%" % pg
                 for pg in range(1, 8)]                                                                       # a logo on 7 pages
        rows.append("   2     3 image     300   300  rgb     3   8  jpeg   no        13  0   300   300   10K 1.0%")   # 1.8 %
        got = reading.shares_from_listing(info, head + "\n".join(rows))
        self.assertAlmostEqual(got[1], 0.36, places=2)          # 5.1 x 6.6 in of 8.5 x 11 in
        self.assertLess(got[2], reading.IMAGE_MIN_SHARE)
        self.assertNotIn(5, got, "an image drawn on many pages is furniture")


class TestLaunchesReplanAndAudit(unittest.TestCase):
    def setUp(self):
        self.fx = ReadingFixture()

    def tearDown(self):
        self.fx.cleanup()

    def test_launch_packs_small_chunks_and_logs_the_manifest(self):
        small = [{"id": "c%d" % i, "est_tokens": 3000} for i in range(6)]
        self.assertEqual([c["id"] for c in reading.take_launch(small)], ["c0", "c1", "c2", "c3"])
        self.assertEqual(len(reading.take_launch([{"id": "big", "est_tokens": 15000}, {"id": "x", "est_tokens": 3000}])), 1)
        act = reading.next_action(self.fx.dir)
        again = reading.next_action(self.fx.dir)
        self.assertEqual(act["launch"], again["launch"], "an unfinished launch is re-issued, not duplicated")
        m = json.loads((self.fx.dir / rl.RUN_MANIFEST).read_text())
        inv = m["workers"][act["agent"]]["invocations"]
        self.assertEqual(len(inv), 1)
        self.assertTrue(inv[0]["purpose"].startswith(act["launch"]))

    def test_replan_supersedes_work_and_the_audit_accounts_for_it(self):
        act = reading.next_action(self.fx.dir)
        self.fx.write_extraction(act["chunks"][0], "critical")
        with self.assertRaises(SystemExit):
            reading.plan(self.fx.dir, 2, 24, 12, 0, log=lambda m: None)
        reading.plan(self.fx.dir, 2, 24, 12, 0, log=lambda m: None, replan="format fix")
        sup = list((self.fx.dir / reading.READING / "superseded").glob("*/extractions/*.jsonl"))
        self.assertEqual(len(sup), 1)
        self.assertFalse(list((self.fx.dir / reading.READING).glob("extractions/*.jsonl")))
        launches = json.loads(reading.launches_path(self.fx.dir).read_text())["launches"]
        self.assertTrue(launches[0]["superseded_at"])
        nxt = reading.next_action(self.fx.dir)
        self.assertNotEqual(nxt["launch"], act["launch"], "a new plan issues new launch ids")
        tdir = self.fx.tmp / "t" / "s1" / "subagents"
        tdir.mkdir(parents=True)
        (tdir / "agent-x.meta.json").write_text(json.dumps({"agentType": "critical-reader",
                                                            "description": "critical-reader %s %s" % (self.fx.run_id, act["launch"])}))
        (tdir / "agent-x.jsonl").write_text(json.dumps({"type": "assistant", "effort": "max",
                                                        "message": {"id": "m1", "model": "claude-opus-5-5", "content": []}}) + "\n")
        res = reading_audit.run_audit(self.fx.dir, self.fx.tmp / "t")
        self.assertEqual(res["errors"], [])
        self.assertIn("superseded", " | ".join(res["warnings"]))

    def test_audit_counts_a_render_image_as_a_view(self):
        st = self.fx.store(next(c["id"] for c in self.fx.plan["chunks"] if c["visual_pages"]))
        pg = st["visual_pages"][0]
        events = [({"name": "Read", "input": {"file_path": "/x/run/_cache/reading/render/%s-p%d-200dpi-r90.png" % (st["doc"], pg)}}, "")]
        self.assertIn(pg, reading_audit.pages_viewed(events, st["pdf"], st["doc"]))
        self.assertNotIn(pg, reading_audit.pages_viewed(events, st["pdf"], "AR-FY1999"))



def anchored_rows(store, cid, role, bad_anchor=False):
    """What a reader writes under the anchor protocol: a few words of each cited passage, never the passage."""
    rows = []
    for lid in store["order"]:
        u = store["units"][lid]
        if "Claims not acknowledged" in u["text"]:
            amounts = [c.strip() for c in u["text"].strip("| ").split("|")][1:]
            rows.append({"type": "contingent_liability", "unit": lid, "page": u["page"], "period": "as at 31-Mar",
                         "basis": "standalone", "anchor": "Claims acknowledged as debts" if bad_anchor else
                         "Claims not acknowledged as debts",
                         "fields": {"category": "Claims not acknowledged as debts", "amount_current": amounts[0],
                                    "amount_prior": amounts[1], "unit_of_amount": "INR million", "description": ""}})
        if u["text"].startswith("Fixture Co continued"):
            rows.append({"type": "other_fact", "unit": lid, "page": u["page"], "period": "", "basis": "na",
                         "anchor": "Fixture Co continued to expand", "fields": {"description": "network expansion"}})
    for k, u in store["units"].items():
        if u.get("visual"):
            rows.append({"type": "other_fact", "unit": k, "page": u["page"], "period": "", "basis": "na",
                         "source": "rendered", "fields": {"description": "photograph of a tower"}})
    cited = {r["page"] for r in rows}
    view = set(reading.view_pages(store))
    receipts = [{"type": "page_receipt", "page": pg, "status": "items" if pg in cited else "no_items",
                 "reason": "" if pg in cited else "headings only", "viewed": pg in view} for pg in store["pages"]]
    receipts.append({"type": "chunk_receipt", "chunk": cid, "role": role, "model": "fixture-model",
                     "units_read": store["new_units"], "pages_viewed": sorted(view)})
    return rows, receipts


def write_parts(run_dir, cid, role, parts):
    d = reading.parts_dir(run_dir, cid, role)
    d.mkdir(parents=True, exist_ok=True)
    for i, rows in enumerate(parts, 1):
        (d / ("%02d.jsonl" % i)).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def receipts_for(store, cid, role, rows):
    cited = {r["page"] for r in rows}
    view = set(reading.view_pages(store))
    out = [{"type": "page_receipt", "page": pg, "status": "items" if pg in cited else "no_items",
            "reason": "" if pg in cited else "headings only", "viewed": pg in view} for pg in store["pages"]]
    out.append({"type": "chunk_receipt", "chunk": cid, "role": role, "model": "fixture-model",
                "units_read": store["new_units"], "pages_viewed": sorted(view)})
    return out


class TestTablesAndSpans(unittest.TestCase):
    """Schema 1.2, tag, do not transcribe: a table is tagged once and the check writes every row exactly as printed
    (a row it cannot expand is an error until the reader writes it); a fact over several passages is tagged over its
    span and quoted in full; only the key fields are required."""

    def setUp(self):
        self.fx = ReadingFixture()
        self.cid = "AR-FY2025-c02"
        self.st = self.fx.store(self.cid)

    def tearDown(self):
        self.fx.cleanup()

    def tag(self, **fields):
        f = {"item_type": "contingent_liability", "label_cell": 1, "columns": {"amount_current": 2, "amount_prior": 3},
             "static": {"unit_of_amount": "INR million"}}
        f.update(fields)
        return {"type": "table", "unit": "a8", "to": "a9", "page": 3, "period": "as at 31-Mar", "basis": "standalone",
                "anchor": "Claims not acknowledged", "fields": f}

    def test_a_table_tag_becomes_every_row_exactly_as_printed(self):
        rows = [self.tag()]
        write_parts(self.fx.dir, self.cid, "critical", [rows, receipts_for(self.st, self.cid, "critical", rows)])
        res = reading.check(self.fx.dir, self.cid, "critical")
        self.assertTrue(res.ok, res.errors)
        items = reading.items_of(self.fx.dir, self.cid, "critical")
        self.assertEqual([(i["unit"], i["fields"]["category"], i["fields"]["amount_current"], i["fields"]["amount_prior"])
                          for i in items], [("a8", "Claims not acknowledged as debts", "1,23,456", "1,10,234"),
                                            ("a9", "Guarantees given to banks", "500", "400")])
        self.assertTrue(all(i["from_table"] == "a8" and i["quote_by"] == "script" for i in items))
        self.assertEqual(items[0]["section"], "", "no heading row above")
        raw = reading.extraction_path(self.fx.dir, self.cid, "critical").read_text()
        self.assertIn('"type": "table"', raw, "the tag is kept in the record, followed by its rows")

    def test_a_tagged_table_agrees_with_rows_written_one_by_one(self):
        rows = [self.tag()]
        write_parts(self.fx.dir, self.cid, "critical", [rows, receipts_for(self.st, self.cid, "critical", rows)])
        explicit = []
        for lid, cat, cur, pri in (("a8", "Claims not acknowledged as debts", "1,23,456", "1,10,234"),
                                   ("a9", "Guarantees given to banks", "500", "400")):
            explicit.append({"type": "contingent_liability", "unit": lid, "page": 3, "period": "as at 31-Mar",
                             "basis": "standalone", "anchor": cat, "fields": {"category": cat, "amount_current": cur,
                                                                              "amount_prior": pri, "unit_of_amount": ""}})
        write_parts(self.fx.dir, self.cid, "reader", [explicit, receipts_for(self.st, self.cid, "reader", explicit)])
        self.assertTrue(reading.check(self.fx.dir, self.cid, "critical").ok)
        self.assertTrue(reading.check(self.fx.dir, self.cid, "reader").ok)
        self.assertEqual(reading.compare_chunk(self.fx.dir, self.cid), [])
        swapped = self.tag(columns={"amount_current": 3, "amount_prior": 2})
        write_parts(self.fx.dir, self.cid, "critical", [[swapped], receipts_for(self.st, self.cid, "critical", [swapped])])
        self.assertTrue(reading.check(self.fx.dir, self.cid, "critical").ok)
        self.assertEqual(len(reading.compare_chunk(self.fx.dir, self.cid)), 2, "a swapped column is a disagreement per row")

    def test_rows_the_tag_cannot_expand_must_be_written_or_skipped_with_a_reason(self):
        bad = self.tag(columns={"amount_current": 2, "amount_prior": 5})
        write_parts(self.fx.dir, self.cid, "critical", [[bad], receipts_for(self.st, self.cid, "critical", [bad])])
        errs = " | ".join(reading.check(self.fx.dir, self.cid, "critical").errors)
        self.assertIn("row a8", errs)
        self.assertIn("write this row's item yourself", errs)
        own = {"type": "contingent_liability", "unit": "a8", "page": 3, "period": "as at 31-Mar", "basis": "standalone",
               "anchor": "Claims not acknowledged", "fields": {"category": "Claims", "amount_current": "1,23,456",
                                                               "amount_prior": "1,10,234", "unit_of_amount": ""}}
        bad["fields"]["skip"] = {"a9": "fixture: merged cells"}
        write_parts(self.fx.dir, self.cid, "critical", [[bad, own], receipts_for(self.st, self.cid, "critical", [own])])
        res = reading.check(self.fx.dir, self.cid, "critical")
        self.assertTrue(res.ok, res.errors)
        self.assertEqual([i["unit"] for i in reading.items_of(self.fx.dir, self.cid, "critical")], ["a8"])
        for broken, msg in (({"columns": {"category": 2}}, "must be amount fields"),
                            ({"columns": {}, "series": {}}, "exactly one of columns"),
                            ({"item_type": "other_fact"}, "amount fields"),
                            ({"static": {"unit_of_amount": "INR 99 million"}}, "not printed in the table")):
            t = self.tag(**broken)
            write_parts(self.fx.dir, self.cid, "critical", [[t], receipts_for(self.st, self.cid, "critical", [t])])
            self.assertIn(msg, " | ".join(reading.check(self.fx.dir, self.cid, "critical").errors), broken)

    def test_cell_layout_tables_and_rows_with_a_missing_cell(self):
        fx = ReadingFixture([CASH_FLOW, PARA_A, "x", "y"], [CASH_FLOW, PARA_B, "x", "y"], {}, {})
        try:
            cid = next(c["id"] for c in fx.plan["chunks"] if c["doc"] == "AR-FY2025" and 1 in c["pages"])
            st = fx.store(cid)
            tag = {"type": "table", "unit": "a2", "to": "a22", "page": 1, "period": "FY2025", "basis": "consolidated",
                   "anchor": "For the year ended", "fields": {"item_type": "statement_line", "layout": "cells",
                                                              "values_per_row": 2, "label_cell": 1,
                                                              "columns": {"value_current": 1, "value_prior": 2},
                                                              "static": {"statement": "Cash flows"}}}
            fx.write_extraction(cid, "reader", mutate=lambda r: [tag] + r)
            res, rows, _ = reading._check(fx.dir, cid, "reader")
            self.assertTrue(res.ok, res.errors)
            got = [(r["fields"]["line_item"], r["fields"]["value_current"], r["fields"]["value_prior"]) for r in rows
                   if r.get("from_table")]
            self.assertEqual(got[0], ("Net loss on derivative financial instruments", "420", "6,319"))
            self.assertIn(("Acquisition of a subsidiary, net of cash proceeds (refer note 4(o))", "-", "(6,428)"), got)
            self.assertEqual(len(got), 6)
            first = next(r for r in rows if r.get("from_table"))
            self.assertEqual((first["unit"], first["to"]), ("a5", "a7"))
            self.assertEqual(first["section"], "March 31, 2025 / March 31, 2024", "the headings above the row")
        finally:
            fx.cleanup()
        short = CASH_FLOW.replace("Other non-cash items\n\n396\n\n823", "Other non-cash items\n\n396")
        fx = ReadingFixture([short, PARA_A, "x", "y"], [short, PARA_B, "x", "y"], {}, {})
        try:
            cid = next(c["id"] for c in fx.plan["chunks"] if c["doc"] == "AR-FY2025" and 1 in c["pages"])
            st = fx.store(cid)
            last = st["order"][[st["units"][k]["text"] for k in st["order"]].index("396")]
            tag["to"] = last
            fx.write_extraction(cid, "reader", mutate=lambda r: [tag] + r)
            errs = " | ".join(reading._check(fx.dir, cid, "reader")[0].errors)
            self.assertIn("'Other non-cash items' has 1 value cells, not 2", errs)
            self.assertIn("shift its values into the wrong column", errs)
        finally:
            fx.cleanup()

    def test_a_span_quotes_the_whole_fact_and_only_key_fields_are_required(self):
        st = self.fx.store("AR-FY2025-c01")
        claim = {"type": "management_claim", "unit": "a2", "to": "a4", "page": 1, "period": "FY2025", "basis": "na",
                 "anchor": "Fixture Co continued to expand", "fields": {"topic": "network", "speaker": ""}}
        rows = [claim, {"type": "other_fact", "unit": "a3", "page": 1, "period": "", "basis": "na",
                        "anchor": "The company also completed", "fields": {}}]
        write_parts(self.fx.dir, "AR-FY2025-c01", "reader", [rows, receipts_for(st, "AR-FY2025-c01", "reader", rows)])
        res = reading.check(self.fx.dir, "AR-FY2025-c01", "reader")
        self.assertTrue(res.ok, res.errors)
        got = reading.items_of(self.fx.dir, "AR-FY2025-c01", "reader")[0]
        self.assertTrue(got["quote"].startswith("Fixture Co continued") and got["quote"].endswith("every circle."),
                        "the quote is the whole span, word for word")
        for bad, msg in (({"to": "a1"}, "comes before unit"), ({"to": "a99"}, "not a passage"),
                         ({"fields": {"topic": "network"}}, "key fields missing ['speaker']")):
            c = dict(claim, **bad)
            write_parts(self.fx.dir, "AR-FY2025-c01", "reader", [[c], receipts_for(st, "AR-FY2025-c01", "reader", [c])])
            self.assertIn(msg, " | ".join(reading.check(self.fx.dir, "AR-FY2025-c01", "reader").errors))
        wordy = dict(claim, fields={"topic": "network", "speaker": "", "claim": " ".join(["word"] * 40)})
        write_parts(self.fx.dir, "AR-FY2025-c01", "reader", [[wordy], receipts_for(st, "AR-FY2025-c01", "reader", [wordy])])
        res = reading.check(self.fx.dir, "AR-FY2025-c01", "reader")
        self.assertTrue(res.ok)
        self.assertIn("a non-key field is a short label", " | ".join(res.warnings))


class TestInRunCalibration(unittest.TestCase):
    """Each run proves on its own pages which non-critical classes Sonnet reads alone: the calibration sample is read
    by both models first, the other non-critical chunks wait, and a class without enough evidence stays double-read."""

    def test_the_sample_is_read_first_and_decides_the_rest(self):
        fx = ReadingFixture(plan_now=False)
        try:
            reading.plan(fx.dir, 2, 24, 12, 0, log=lambda m: None, calibrate=False)
            self.assertFalse(reading.calibration_path(fx.dir).exists(), "--no-calibration: every chunk double-read")
            picked = reading.start_calibration(fx.dir, n=1, log=lambda m: None)
            self.assertEqual(json.loads(reading.calibration_path(fx.dir).read_text())["status"], "in_progress")
            p = json.loads((fx.dir / reading.READING / "plan.json").read_text())
            held = [c["id"] for c in p["chunks"] if not c["critical"] and c["id"] not in picked]
            self.assertTrue(held)
            issued = set()
            for _ in range(10):
                act = reading.next_action(fx.dir)
                if act["action"] != "launch" or set(act["chunks"]) & set(held):
                    break
                issued |= set(act["chunks"])
                for cid in act["chunks"]:
                    fx.write_extraction(cid, act["role"])
            self.assertFalse(issued & set(held), "held chunks wait for the calibration")
            cal = json.loads(reading.calibration_path(fx.dir).read_text())
            self.assertEqual(cal["status"], "failed", "too few items to prove any class")
            self.assertEqual(cal["single_read_classes"], [])
            self.assertTrue((fx.dir / reading.READING / "BAKEOFF.md").exists())
            c = next(c for c in p["chunks"] if c["id"] == held[0])
            self.assertEqual(reading.required_roles(c, reading.run_policy(fx.dir)), ["critical", "reader"])
            passed = dict(cal, status="passed", single_read_classes=c["classes"])
            reading.calibration_path(fx.dir).write_text(json.dumps(passed))
            self.assertEqual(reading.required_roles(c, reading.run_policy(fx.dir)), ["reader"],
                             "a class this run proved is read by Sonnet alone")
        finally:
            fx.cleanup()


class TestReferenceScore(unittest.TestCase):
    """A change of reading format is scored against frozen reads: a table tag expanded by script finds the rows a
    reader wrote by hand, and a material item the new read lacks is listed."""

    def test_tagged_reads_score_against_hand_written_rows(self):
        fx = ReadingFixture()
        try:
            cid = "AR-FY2025-c02"
            st = fx.store(cid)
            fx.write_extraction(cid, "critical")              # the reference: every row written by hand
            reading.reference_save(fx.dir, [cid], log=lambda m: None)
            self.assertTrue(next(c for c in json.loads((fx.dir / reading.READING / "plan.json").read_text())["chunks"]
                                 if c["id"] == cid)["bakeoff"])
            tag = {"type": "table", "unit": "a8", "to": "a9", "page": 3, "period": "as at 31-Mar", "basis": "standalone",
                   "anchor": "Claims not acknowledged", "fields": {"item_type": "contingent_liability", "label_cell": 1,
                                                                   "columns": {"amount_current": 2, "amount_prior": 3}}}
            reading.extraction_path(fx.dir, cid, "critical").unlink()
            write_parts(fx.dir, cid, "critical", [[tag], receipts_for(st, cid, "critical", [tag])])
            self.assertTrue(reading.check(fx.dir, cid, "critical").ok)
            out = reading.reference_score(fx.dir, log=lambda m: None)
            row = next(r for r in out["rows"] if r["model"] == "opus")
            self.assertEqual((row["recall"], row["material_recall"], out["material_misses"]), (1.0, 1.0, []))
            tag["to"] = "a8"                                    # the new read stops one row short
            write_parts(fx.dir, cid, "critical", [[tag], receipts_for(st, cid, "critical", [tag])])
            reading.check(fx.dir, cid, "critical")
            out = reading.reference_score(fx.dir, log=lambda m: None)
            self.assertEqual(out["material_misses"], [])        # the fixture's reference holds only the claims row
            self.assertTrue((fx.dir / reading.READING / "REFERENCE_SCORE.md").exists())
        finally:
            fx.cleanup()


class TestScopeAndGaps(unittest.TestCase):
    """Owner decision 2026-10-19: every page of the latest five fiscal years, the core sections of the five before.
    The window is anchored on fiscal years, so a missing report is a gap, never a silently shifted window."""

    def setUp(self):
        self.fx = ReadingFixture(plan_now=False)

    def tearDown(self):
        self.fx.cleanup()

    def test_missing_reports_in_the_window_refuse_the_plan_until_accepted(self):
        with self.assertRaises(SystemExit) as cm:
            reading.plan(self.fx.dir, 5, 24, 12, 5, log=lambda m: None)
        msg = str(cm.exception)
        for y in range(2016, 2024):
            self.assertIn("AR-FY%d" % y, msg)
        self.assertIn("AR-FY2023 (full)", msg)
        self.assertIn("AR-FY2020 (core)", msg)
        for y in range(2016, 2024):
            reading.accept_gap(self.fx.dir, "AR-FY%d" % y, "fixture: listed in 2023")
        p = reading.plan(self.fx.dir, 5, 24, 12, 5, log=lambda m: None)
        self.assertEqual(p["scope"]["full_fys"], [2025, 2024, 2023, 2022, 2021])
        self.assertEqual(p["scope"]["core_fys"], [2020, 2019, 2018, 2017, 2016])
        self.assertTrue(all(g["accepted"] for g in p["gaps"]))
        reading.status(self.fx.dir, log=lambda m: None)
        cov = (self.fx.dir / rl.READING_COVERAGE).read_text()
        self.assertIn("accepted: fixture: listed in 2023", cov)
        self.assertIn("every page of the annual reports of FY2025, FY2024", cov)

    def test_window_is_anchored_on_the_report_due_by_the_cutoff(self):
        m = json.loads((self.fx.dir / rl.RUN_MANIFEST).read_text())
        m["research_cutoff"] = "2026-10-17"               # FY2026's report (year ended March 2026) is due by September
        (self.fx.dir / rl.RUN_MANIFEST).write_text(json.dumps(m))
        self.assertEqual(reading.due_fiscal_year(self.fx.dir), 2026)
        docs, excluded, gaps = reading.select(self.fx.dir, 2, 24, 12, 0)
        self.assertEqual([g["key"] for g in gaps], ["AR-FY2026"], "the missing latest report is a gap")
        self.assertEqual([d["key"] for d in docs if d["doc_type"] == "annual_report"], ["AR-FY2025"])
        self.assertEqual([d["key"] for d in excluded], ["AR-FY2024"], "the window does not slide back to FY2024")

    def test_core_years_read_only_the_core_sections(self):
        p = reading.plan(self.fx.dir, 1, 24, 12, 1, log=lambda m: None)
        docs = {d["key"]: d for d in p["documents"]}
        self.assertEqual((docs["AR-FY2025"]["scope"], docs["AR-FY2024"]["scope"]), ("full", "core"))
        r24 = {r["page"]: r for r in docs["AR-FY2024"]["page_records"]}
        self.assertEqual(r24[1]["status"], "out_of_scope", "the narrative of a core-year report is not read")
        self.assertIn("core sections", r24[1]["reason"])
        self.assertNotEqual(r24[2]["status"], "out_of_scope", "its auditor's report is read")
        self.assertNotEqual(r24[3]["status"], "out_of_scope", "its notes are read")
        r25 = {r["page"]: r for r in docs["AR-FY2025"]["page_records"]}
        self.assertFalse(any(r["status"] == "out_of_scope" for r in r25.values()), "every page of a full year is read")
        core = reading.core_classes(reading.schema())
        for c in ("auditor_report", "caro", "ifc", "statements", "notes", "notes_critical", "board", "aoc1", "aoc2",
                  "secretarial", "mdna"):
            self.assertIn(c, core)
        for c in ("narrative", "brsr", "cg", "notice"):
            self.assertNotIn(c, core)


class TestAnchorsAndParts(unittest.TestCase):
    """Readers cite a passage and a few of its words; the check attaches the printed text and checks every number."""

    def setUp(self):
        self.fx = ReadingFixture()
        self.cid = next(c["id"] for c in self.fx.plan["chunks"] if c["critical"] and c["doc"] == "AR-FY2025")
        self.st = self.fx.store(self.cid)

    def tearDown(self):
        self.fx.cleanup()

    def test_anchored_parts_are_assembled_with_the_printed_text_as_quote(self):
        items, receipts = anchored_rows(self.st, self.cid, "critical")
        write_parts(self.fx.dir, self.cid, "critical", [items, receipts])
        res = reading.check(self.fx.dir, self.cid, "critical")
        self.assertTrue(res.ok, res.errors)
        rows = [json.loads(x) for x in reading.extraction_path(self.fx.dir, self.cid, "critical").read_text().splitlines()]
        cl = next(r for r in rows if r["type"] == "contingent_liability")
        self.assertEqual(cl["quote_by"], "script")
        self.assertIn("1,23,456", cl["quote"])
        self.assertEqual(sum(1 for r in rows if r["type"] == "page_receipt"), len(self.st["pages"]))
        self.assertFalse(any(k.startswith("_") for r in rows for k in r), "internal keys are not written")

    def test_anchor_errors_name_the_part_and_line(self):
        items, receipts = anchored_rows(self.st, self.cid, "critical", bad_anchor=True)
        write_parts(self.fx.dir, self.cid, "critical", [receipts, items])
        errs = " | ".join(reading.check(self.fx.dir, self.cid, "critical").errors)
        self.assertIn("02.jsonl line 1", errs)
        self.assertIn("is not printed verbatim", errs)

    def test_short_anchor_and_unprinted_numbers_are_errors(self):
        items, receipts = anchored_rows(self.st, self.cid, "critical")
        cl = next(r for r in items if r["type"] == "contingent_liability")
        cl["anchor"] = "Claims"
        write_parts(self.fx.dir, self.cid, "critical", [items + receipts])
        self.assertIn("at least 3 consecutive words", " | ".join(reading.check(self.fx.dir, self.cid, "critical").errors))
        cl["anchor"] = "Claims not acknowledged as debts"
        cl["fields"]["amount_current"] = "1,99,999"
        write_parts(self.fx.dir, self.cid, "critical", [items + receipts])
        self.assertIn("1,99,999 not printed", " | ".join(reading.check(self.fx.dir, self.cid, "critical").errors))

    def test_anchor_runs_on_from_a_label_to_its_values(self):
        fx = ReadingFixture([CASH_FLOW, PARA_A, "x", "y"], [CASH_FLOW, PARA_B, "x", "y"], {}, {})
        try:
            c = next(c for c in fx.plan["chunks"] if c["doc"] == "AR-FY2025" and 1 in c["pages"])
            st = fx.store(c["id"])
            lid = next(k for k in st["order"] if st["units"][k]["text"] == "Net loss on derivative financial instruments")
            item = {"type": "statement_line", "unit": lid, "page": 1, "period": "FY2025", "basis": "consolidated",
                    "anchor": "Net loss on derivative financial instruments",
                    "fields": {"statement": "cash flow", "line_item": "Net loss on derivative financial instruments",
                               "value_current": "420", "value_prior": "6,319", "unit_of_amount": ""}}
            fx.write_extraction(c["id"], "reader", mutate=lambda r: [item] + [x for x in r if x.get("type") != "other_fact"
                                                                             or x.get("source") == "rendered"])
            res, rows, _ = reading._check(fx.dir, c["id"], "reader")
            self.assertTrue(res.ok, res.errors)
            got = next(r for r in rows if r["type"] == "statement_line")
            self.assertEqual(got["quote"], "Net loss on derivative financial instruments 420 6,319",
                             "the label's passage runs on into its values")
        finally:
            fx.cleanup()

    def test_a_new_launch_sets_aside_unfinished_parts_and_next_waits_for_the_driver(self):
        act = reading.next_action(self.fx.dir)
        cid = act["chunks"][0]
        write_parts(self.fx.dir, cid, act["role"], [[{"type": "page_receipt", "page": 1, "status": "items"}]])
        again = reading.next_action(self.fx.dir)
        self.assertEqual(again["launch"], act["launch"], "an open launch keeps its parts")
        self.assertTrue(reading.parts_dir(self.fx.dir, cid, act["role"]).exists())
        reading.update_launch(self.fx.dir, act["launch"], closed_at=reading.now_iso(), outcome="abandoned")
        fresh = reading.next_action(self.fx.dir)
        self.assertNotEqual(fresh["launch"], act["launch"])
        self.assertFalse(reading.parts_dir(self.fx.dir, cid, act["role"]).exists(), "the new reader starts from nothing")
        self.assertTrue((self.fx.dir / reading.CACHE / "abandoned" / fresh["launch"]).exists(), "nothing is deleted")
        lock = self.fx.dir / "_cache" / "engine" / "engine.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        import socket
        lock.write_text(json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "started_at": "now"}))
        self.assertEqual(reading.main(["next", str(self.fx.dir)]), 1, "next refuses while the driver runs")
        lock.unlink()


FAKE_CLAUDE = r"""#!%(py)s
# A stand-in for `claude -p` in the engine tests. Readers: it "reads" every line of its chunk files (as a transcript
# would record it), writes anchored items in parts, and can stop once on a usage limit or write one bad part first.
# Other agents ("long" mode): each turn does one unit of work and grows the context by 60k tokens; it stops at
# --max-turns, writes progress and replies CHECKPOINTED when asked, and continues from its progress file in a fresh
# session. Every run streams a rate_limit_event (FAKE_FIVE / FAKE_WEEK utilization) before its result.
import json, os, re, sys, time, uuid
from pathlib import Path
sys.path.insert(0, %(scripts)r)
import reading
args = sys.argv[1:]
def opt(n):
    return args[args.index(n) + 1] if n in args else None
msg, sid = args[args.index("-p") + 1], opt("--session-id") or opt("--resume")
model, effort, agent = opt("--model"), opt("--effort"), opt("--agent")
week_reset = time.time() + float(os.environ.get("FAKE_WEEK_RESET_S", 3 * 86400))
print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "unifiedWindows": {
    "five_hour": {"utilization": float(os.environ.get("FAKE_FIVE", 0.1)), "resetsAt": int(time.time() + 3600)},
    "seven_day": {"utilization": float(os.environ.get("FAKE_WEEK", 0.1)), "resetsAt": int(week_reset)}}}}), flush=True)
if not sid:                                     # the engine's usage probe
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "OK"}))
    sys.exit(0)
tj = Path(os.environ["CLAUDE_TRANSCRIPTS_DIR"]) / (sid + ".jsonl")
state_path = Path(os.environ["FAKE_STATE"])
state = json.loads(state_path.read_text()) if state_path.exists() else {}
now = time.strftime("%%Y-%%m-%%dT%%H:%%M:%%SZ", time.gmtime())
call = {"id": uuid.uuid4().hex, "sid": sid, "agent": agent, "max_turns": opt("--max-turns"), "msg": msg[:80], "t": time.time()}
with open(os.environ["FAKE_STATE"] + ".calls", "a") as f:     # append-only: sessions may run at the same time
    f.write(json.dumps(call) + "\n")
def emit(*entries):
    with tj.open("a") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
def finish(result, subtype="success", is_error=False):
    with open(os.environ["FAKE_STATE"] + ".calls", "a") as f:
        f.write(json.dumps({"id": call["id"], "end": time.time()}) + "\n")
    state_path.write_text(json.dumps(state))
    print(json.dumps({"type": "result", "subtype": subtype, "is_error": is_error, "result": result, "session_id": sid,
                      "total_cost_usd": 0.5, "num_turns": 1}))
    sys.exit(0)
if agent not in ("reader", "critical-reader"):
    run_dir = Path(os.environ["FAKE_RUN_DIR"])
    total = int(os.environ.get("FAKE_UNITS", 10))
    ctx = state.setdefault("ctx", {})
    if "--session-id" in args:
        ctx[sid] = 30000
        emit({"type": "user", "timestamp": now, "message": {"role": "user", "content": msg}})
    if os.environ.get("FAKE_TOUCH") and not state.get("touched"):
        state["touched"] = True
        with (run_dir / os.environ["FAKE_TOUCH"]).open("a") as f:
            f.write("changed by %%s\n" %% agent)
    def turn(tool=None):
        ctx[sid] += 60000
        n = uuid.uuid4().hex[:8]
        content = [{"type": "tool_use", "id": "t%%s" %% n, "name": tool[0], "input": tool[1]}] if tool else [{"type": "text", "text": "working"}]
        emit({"type": "assistant", "timestamp": now, "effort": effort, "message": {"id": "m" + uuid.uuid4().hex,
              "model": "claude-%%s-5-5" %% model, "usage": {"input_tokens": 10, "cache_read_input_tokens": ctx[sid] - 10,
              "output_tokens": 100}, "content": content}})
        if tool:
            emit({"type": "user", "timestamp": now, "message": {"content": [{"type": "tool_result", "tool_use_id": "t%%s" %% n,
                  "content": "1\tsome text; revenue 12,345 and 12,000 as printed"}]}})
    if "CHECKPOINTED" in msg:
        turn()
        (run_dir / "progress.txt").write_text(str(state.get("units", 0)))
        finish("CHECKPOINTED")
    if os.environ.get("FAKE_PEEK") and not state.get("peeked"):
        state["peeked"] = True
        turn(("Read", {"file_path": str(run_dir / "specialists" / "moat.md")}))
    max_turns = int(opt("--max-turns") or 10 ** 6)
    for i in range(max_turns):
        if state.get("units", 0) >= total:
            break
        state["units"] = state.get("units", 0) + 1
        turn()
    if agent == "verifier":
        import csv as _csv
        name = re.search(r"checking the ([\w-]+) specialist|the ([\w-]+) specialist corrected", msg)
        name = name.group(1) or name.group(2)
        sample = list(_csv.DictReader((run_dir / "qc" / "verification" / (name + "_sample.csv")).open()))
        bad = os.environ.get("FAKE_DISCREPANCY") and not state.get("discrepancy_sent")
        state["discrepancy_sent"] = True
        rows = [{"claim_id": r["claim_id"], "result": "Material discrepancy" if bad and i == 0 else "Confirmed",
                 "evidence": "the page prints 12,000" if bad and i == 0 else "", "source_opened": "doc.pdf p.1", "note": ""}
                for i, r in enumerate(sample)]
        with (run_dir / "qc" / "verification" / (name + "_claims.csv")).open("w", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=["claim_id", "result", "evidence", "source_opened", "note"])
            w.writeheader()
            w.writerows(rows)
        turn()
        finish("%%s: %%d claims" %% (name, len(rows)))
    if state.get("units", 0) >= total:
        out = run_dir / "specialists" / ("%%s.md" %% agent)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("DONE\n")
        if os.environ.get("FAKE_LEDGER"):
            turn(("WebFetch", {"url": "https://example.com/report.pdf"}))
            log_saw = json.loads(tj.read_text().splitlines()[-1])
            led = run_dir / "specialists" / ("%%s_ledger.csv" %% agent)
            unseen = os.environ.get("FAKE_UNSEEN") and not msg.startswith("Your work does not pass")
            fixed_value = "msg.startswith('The verifier')"
            rows = [("C001", "FACT", "12,345"), ("C002", "CALCULATION" if not unseen else "FACT", "98,765")]
            if "The verifier re-opened" in msg:
                state["corrected"] = True
            hdr = "claim_id,author,claim,tag,metric,value,unit,period,basis,source_title,source_issuer,source_url_or_id,source_date,retrieved_date,locator,source_tier,primary,confidence,corroborated_by,contradicted_by,formula_or_inputs,notes\n"
            led.write_text(hdr + "".join("%%s-%%s,%%s,claim,%%s,,\"%%s\",INR mn,FY2025,consolidated,Report,Co,https://example.com/report.pdf,,,,1,Y,H,,,,\n" %% (
                {"filings": "FIL"}.get(agent, "X"), cid, agent, tag, "12,000" if cid == "C001" and state.get("corrected") else val)
                for cid, tag, val in rows))
        finish("STATUS: complete")
    finish("Reached maximum number of turns (%%d)" %% max_turns, "error_max_turns", True)
m = re.search(r"Read and follow (\S+) exactly", msg)
if m:
    state.setdefault("launch_of", {})[sid] = m.group(1)
    state.setdefault("rundir_of", {})[sid] = re.search(r"RUN_DIR: (\S+)", msg).group(1)
    emit({"type": "user", "timestamp": now, "message": {"role": "user", "content": msg}})
if os.environ.get("FAKE_LIMIT_ONCE") and not state.get("limited"):
    state["limited"] = True
    state_path.write_text(json.dumps(state))
    emit({"type": "assistant", "timestamp": now, "error": "rate_limit", "isApiErrorMessage": True,
          "apiError": "usage_limit_reached", "quotaLimits": {"status": "rejected", "resetsAt": time.time() + 1},
          "message": {"model": "<synthetic>", "content": [{"type": "text", "text": "You've hit your session limit"}]}})
    print(json.dumps({"type": "result", "is_error": True, "result": "You've hit your session limit · resets 2:30pm",
                      "session_id": sid}))
    sys.exit(1)
run_dir = Path(state["rundir_of"][sid])
launch = Path(state["launch_of"][sid])
launch = launch if launch.is_absolute() else Path(%(root)r) / launch
text = launch.read_text()
role = re.search(r"role `(\w+)`", text).group(1)
bad = bool(os.environ.get("FAKE_BAD_ONCE")) and not state.get("bad_done") and not msg.startswith("The reading check")
n = 0
time.sleep(float(os.environ.get("FAKE_SLEEP", 0)))
for cid in re.findall(r"^\| ([A-Z]+-[A-Za-z0-9]+-c\d+) \|", text, re.M):
    st = reading.chunk_cache(run_dir, cid)
    chunk_md = run_dir / reading.CACHE / "chunks" / (cid + ".md")
    lines = chunk_md.read_text().split("\n")
    n += 1
    emit({"type": "assistant", "timestamp": now, "effort": effort, "message": {"id": "m" + uuid.uuid4().hex, "model": "claude-%%s-5-5" %% model,
          "usage": {"input_tokens": 10, "output_tokens": 100}, "content": [{"type": "tool_use", "id": "t%%d" %% n, "name": "Read",
          "input": {"file_path": str(chunk_md)}}]}},
         {"type": "user", "timestamp": now, "message": {"content": [{"type": "tool_result", "tool_use_id": "t%%d" %% n,
          "content": "\n".join("%%d\t%%s" %% (i, ln) for i, ln in enumerate(lines, 1))}]}})
    for pg in reading.view_pages(st):
        n += 1
        emit({"type": "assistant", "timestamp": now, "effort": effort, "message": {"id": "m" + uuid.uuid4().hex, "model": "claude-%%s-5-5" %% model,
              "content": [{"type": "tool_use", "id": "t%%d" %% n, "name": "Read", "input": {"file_path": st["pdf"], "pages": str(pg)}}]}},
             {"type": "user", "timestamp": now, "message": {"content": [{"type": "tool_result", "tool_use_id": "t%%d" %% n, "content": "[image]"}]}})
    rows, receipts = [], []
    for lid in st["order"]:
        u = st["units"][lid]
        if "Claims not acknowledged" in u["text"]:
            amounts = [c.strip() for c in u["text"].strip("| ").split("|")][1:]
            rows.append({"type": "contingent_liability", "unit": lid, "page": u["page"], "period": "as at 31-Mar", "basis": "standalone",
                         "anchor": "Claims acknowledged" if bad else "Claims not acknowledged as debts",
                         "fields": {"category": "Claims not acknowledged as debts", "amount_current": amounts[0], "amount_prior": amounts[1],
                                    "unit_of_amount": "INR million", "description": ""}})
    for k, u in st["units"].items():
        if u.get("visual"):
            rows.append({"type": "other_fact", "unit": k, "page": u["page"], "period": "", "basis": "na", "source": "rendered",
                         "fields": {"description": "photograph"}})
    cited = {r["page"] for r in rows}
    view = set(reading.view_pages(st))
    receipts = [{"type": "page_receipt", "page": pg, "status": "items" if pg in cited else "no_items",
                 "reason": "" if pg in cited else "headings only", "viewed": pg in view} for pg in st["pages"]]
    receipts.append({"type": "chunk_receipt", "chunk": cid, "role": role, "model": "fake", "units_read": st["new_units"],
                     "pages_viewed": sorted(view)})
    d = reading.parts_dir(run_dir, cid, role)
    d.mkdir(parents=True, exist_ok=True)
    (d / "01.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (d / "02.jsonl").write_text("".join(json.dumps(r) + "\n" for r in receipts))
if bad:
    state["bad_done"] = True
finish("done")
"""


class EngineCase(unittest.TestCase):
    """A run fixture, a stand-in CLI and an isolated usage log for the engine tests."""

    def setUp(self):
        self.fx = ReadingFixture()
        self.tdir = self.fx.tmp / "transcripts"
        self.tdir.mkdir()
        self.fake = self.fx.tmp / "bin" / "claude"
        self.fake.parent.mkdir()
        self.fake.write_text(FAKE_CLAUDE % {"py": PY, "scripts": str(ROOT / "scripts"), "root": str(ROOT)})
        self.fake.chmod(0o755)
        self.saved = (agent_driver.LIMIT_SLACK_S, agent_driver.POLL_S)
        agent_driver.LIMIT_SLACK_S, agent_driver.POLL_S = 0, 0.05
        self.logs = []

    def tearDown(self):
        agent_driver.LIMIT_SLACK_S, agent_driver.POLL_S = self.saved
        self.fx.cleanup()

    def env(self, **extra):
        return mock.patch.dict(os.environ, dict({"CLAUDE_TRANSCRIPTS_DIR": str(self.tdir), "EQR_NO_CAFFEINATE": "1",
                                                 "EQR_USAGE_LOG": str(self.fx.tmp / "usage.jsonl"),
                                                 "FAKE_STATE": str(self.fx.tmp / "fake_state.json"),
                                                 "FAKE_RUN_DIR": str(self.fx.dir)}, **extra))

    def engine(self, **opts):
        return agent_driver.Engine(self.fx.dir, str(self.fake), agent_driver.options(**opts), log=self.logs.append)

    def calls(self):
        out = {}
        for line in (self.fx.tmp / "fake_state.json.calls").read_text().splitlines():
            o = json.loads(line)
            out.setdefault(o["id"], {}).update(o)
        return sorted(out.values(), key=lambda c: c.get("t", 0))


class TestEngineReading(EngineCase):
    """Readers through the engine: one at a time or in parallel, through a usage limit, with a record the audit checks."""

    def test_reads_everything_through_a_usage_limit_and_the_audit_passes(self):
        with self.env(FAKE_LIMIT_ONCE="1", CLAUDE_EFFORT="low", CLAUDECODE="1"):
            eng = self.engine(timeout_s=600, max_wait_s=3600)
            with agent_driver.Session(eng, "reading"):
                rc = agent_driver.cmd_reading(eng, False, 0, 1)
        self.assertEqual(rc, 0, self.logs)
        launches = json.loads(reading.launches_path(self.fx.dir).read_text())["launches"]
        self.assertTrue(launches)
        self.assertTrue(all(l["outcome"] == "pass" and l["runner"] == "headless" for l in launches))
        first = launches[0]["sessions"][0]
        self.assertEqual([a["kind"] for a in first["attempts"]], ["start", "resume"], "the same session is resumed")
        self.assertTrue(first["attempts"][0].get("limit_resets_at"))
        self.assertEqual(first["attempts"][1]["util_after"].get("seven_day"), 0.1, "the session's usage is recorded")
        pinned = rl.model_policy()["agents"]
        for l in launches:
            s = l["sessions"][0]
            self.assertEqual((s["model"], s["effort"]), (pinned[l["agent"]]["model"], pinned[l["agent"]]["effort"]),
                             "the pinned model and effort, not the parent session's CLAUDE_EFFORT")
        st = reading.status(self.fx.dir, log=lambda m: None)
        self.assertTrue(st["complete"], st)
        self.assertFalse((self.fx.dir / "_cache" / "engine" / "engine.lock").exists())
        res = reading_audit.run_audit(self.fx.dir, self.tdir)
        self.assertEqual(res["errors"], [])
        self.assertEqual(res["status"], "PASS")
        self.assertTrue(any(r.get("session") for r in res["readers"]), "headless sessions are audited")
        self.assertFalse(res["cio"], "a reader session is not taken for the CIO's")

    def test_parallel_readers_never_share_a_chunk(self):
        with self.env(FAKE_SLEEP="0.4"):
            eng = self.engine()
            with agent_driver.Session(eng, "reading"):
                rc = agent_driver.cmd_reading(eng, False, 0, 3)
        self.assertEqual(rc, 0, self.logs)
        launches = json.loads(reading.launches_path(self.fx.dir).read_text())["launches"]
        keys = [(c, l["role"]) for l in launches for c in l["chunks"]]
        self.assertEqual(len(keys), len(set(keys)), "each chunk and role is read by one launch")
        calls = [c for c in self.calls() if c["agent"] in ("reader", "critical-reader")]
        overlap = any(a["t"] < b.get("end", 0) and b["t"] < a.get("end", 0) for i, a in enumerate(calls) for b in calls[i + 1:])
        self.assertTrue(overlap, "sessions ran at the same time while the five-hour window had room")
        self.assertTrue(reading.status(self.fx.dir, log=lambda m: None)["complete"])
        self.assertEqual(reading_audit.run_audit(self.fx.dir, self.tdir)["errors"], [])

    def test_no_parallel_session_when_the_window_is_full(self):
        with self.env(FAKE_SLEEP="0.2", FAKE_FIVE="0.9"):
            eng = self.engine()
            with agent_driver.Session(eng, "reading"):
                rc = agent_driver.cmd_reading(eng, False, 0, 3)
        self.assertEqual(rc, 0, self.logs)
        calls = [c for c in self.calls() if c["agent"] in ("reader", "critical-reader")]
        self.assertFalse(any(a["t"] < b.get("end", 0) and b["t"] < a.get("end", 0)
                             for i, a in enumerate(calls) for b in calls[i + 1:]), "one at a time above the ceiling")

    def test_a_failing_check_resumes_the_session_with_the_errors(self):
        with self.env(FAKE_BAD_ONCE="1"):
            eng = self.engine()
            with agent_driver.Session(eng, "reading"):
                rc = agent_driver.cmd_reading(eng, False, 1, 1)
        self.assertEqual(rc, 0, self.logs)
        l = json.loads(reading.launches_path(self.fx.dir).read_text())["launches"][0]
        self.assertEqual([a["kind"] for a in l["sessions"][0]["attempts"]], ["start", "fix"])
        self.assertEqual(l["outcome"], "pass")

    def test_reader_command_pins_the_agent_and_confines_writes(self):
        act = {"agent": "critical-reader", "model": "opus", "effort": "xhigh", "chunks": [], "role": "critical",
               "launch": "L001", "prompt": "p"}
        cmd = self.engine().command(agent_driver.reader_assignment(self.fx.dir, act), "sid", "prompt", False, 0)
        for flag, val in (("--agent", "critical-reader"), ("--model", "opus"), ("--effort", "xhigh"),
                          ("--permission-mode", "dontAsk"), ("--tools", "Read,Write,Edit,Bash"), ("--session-id", "sid"),
                          ("--output-format", "stream-json")):
            self.assertEqual(cmd[cmd.index(flag) + 1], val)
        self.assertIn("--strict-mcp-config", cmd)
        self.assertNotIn("--max-turns", cmd, "a reader is never cut into segments")
        parts = str((self.fx.dir / reading.CACHE / "parts").resolve())
        self.assertIn("Write(/%s/**)" % parts, cmd)
        self.assertFalse(any(x.startswith("Bash(") and "reading.py" not in x for x in cmd), "the shell only for reading.py")
        with mock.patch.dict(os.environ, {"CLAUDECODE": "1", "CLAUDE_EFFORT": "max", "CLAUDE_CODE_SESSION_ID": "x",
                                          "CLAUDE_CODE_USE_BEDROCK": "1"}):
            env = agent_driver.child_env()
        self.assertNotIn("CLAUDECODE", env)
        self.assertNotIn("CLAUDE_EFFORT", env)
        self.assertNotIn("CLAUDE_CODE_SESSION_ID", env)
        self.assertIn("CLAUDE_CODE_USE_BEDROCK", env)


class TestEngineSpecialists(EngineCase):
    """Long agents: segments, a checkpoint and fresh continuations at the context limit; the weekly ceiling; the
    independence profile, fingerprints and the transcript audit."""

    def assignment(self, name="filings"):
        a = agent_driver.specialist_assignment(self.fx.dir, name, "You are the %s specialist for run %s." % (
            name, self.fx.run_id))
        report = self.fx.dir / "specialists" / ("%s.md" % name)
        a.check = lambda: [] if report.exists() and "DONE" in report.read_text() else ["%s.md does not exist yet" % name]
        return a

    def run_one(self, a, **opts):
        eng = self.engine(**opts)
        with agent_driver.Session(eng, "specialists"):
            rc = agent_driver.run_jobs(eng, [(a, agent_driver.open_job(eng, a.agent, a.kind))], 1)
        return rc, json.loads((self.fx.dir / "engine" / "jobs.json").read_text())["jobs"]

    def test_context_limit_hands_over_to_fresh_sessions_after_a_checkpoint(self):
        with self.env(FAKE_UNITS="10"):
            rc, jobs = self.run_one(self.assignment(), context_limit=200000, segment_turns=3)
        self.assertEqual(rc, 0, self.logs)
        job = jobs[-1]
        self.assertEqual(job["status"], "pass")
        self.assertEqual(len(job["sessions"]), 4, "10 units at 3 turns a segment and a 200k limit: four sessions")
        for s in job["sessions"][:-1]:
            self.assertEqual([a["kind"] for a in s["attempts"]], ["start" if s is job["sessions"][0] else "start", "checkpoint"])
            self.assertEqual(s.get("ended_because"), "handed over")
        calls = [c for c in self.calls() if c["agent"] == "filings"]
        self.assertTrue(all(c["max_turns"] for c in calls), "every segment is bounded")
        self.assertTrue(any("CONTINUATION" in c["msg"] or c["msg"].startswith("You are the filings") for c in calls))
        m = json.loads((self.fx.dir / rl.RUN_MANIFEST).read_text())
        stages = [i["stage"] for i in m["specialists"]["filings"]["invocations"]]
        self.assertEqual(stages, ["1", "1-continue", "1-continue", "1-continue"])
        self.assertTrue((self.fx.dir / "engine" / "ENGINE.md").exists())
        self.assertEqual(job["cost_usd"], 0.5 * sum(len(s["attempts"]) for s in job["sessions"]))

    def test_small_context_continues_the_same_session(self):
        with self.env(FAKE_UNITS="7"):
            rc, jobs = self.run_one(self.assignment(), context_limit=10 ** 7, segment_turns=3)
        self.assertEqual(rc, 0, self.logs)
        s = jobs[-1]["sessions"]
        self.assertEqual(len(s), 1)
        self.assertEqual([a["kind"] for a in s[0]["attempts"]], ["start", "continue", "continue"])

    def test_weekly_ceiling_waits_for_a_near_reset_and_stops_for_a_far_one(self):
        with self.env(FAKE_UNITS="4", FAKE_WEEK="0.97", FAKE_WEEK_RESET_S="1"):
            rc, jobs = self.run_one(self.assignment(), context_limit=10 ** 7, segment_turns=2)
        self.assertEqual(rc, 0, self.logs)
        self.assertTrue(any("weekly usage window at 97%" in m for m in self.logs))
        (self.fx.dir / "specialists" / "moat.md").parent.mkdir(exist_ok=True)
        (self.fx.tmp / "fake_state.json").unlink()
        (self.fx.tmp / "fake_state.json.calls").unlink()
        with self.env(FAKE_UNITS="4", FAKE_WEEK="0.97"):
            rc, jobs = self.run_one(self.assignment("moat"), context_limit=10 ** 7, segment_turns=2, max_wait_s=60)
        self.assertEqual(rc, 1)
        job = jobs[-1]
        self.assertEqual(job["status"], "paused", "stopped at a segment boundary, resumable")
        self.assertEqual(len(job["sessions"][0]["attempts"]), 1)
        log = self.fx.tmp / "usage.jsonl"
        with log.open("a") as f:                  # after the reset, the probe sees a fresh week
            f.write(json.dumps({"at": time.time() + 5, "info": {"unifiedWindows": {"seven_day": {"utilization": 0.01,
                                                                     "resetsAt": time.time() + 7 * 86400}}}}) + "\n")
        with self.env(FAKE_UNITS="4"):
            rc, jobs = self.run_one(self.assignment("moat"), context_limit=10 ** 7, segment_turns=2)
        self.assertEqual(rc, 0, self.logs)
        self.assertEqual(jobs[-1]["id"], job["id"], "the paused job is resumed, not started again")
        self.assertEqual(len(jobs[-1]["sessions"]), 1, "in its own session")
        self.assertEqual(jobs[-1]["sessions"][0]["attempts"][1]["kind"], "resume")

    def test_specialist_profile_denies_other_agents_work_and_confines_writes(self):
        a = agent_driver.specialist_assignment(self.fx.dir, "filings", "p")
        cmd = self.engine().command(a, "sid", "p", False, 25)
        run = str(self.fx.dir.resolve())
        self.assertEqual(cmd[cmd.index("--tools") + 1], "Read,Write,Edit,Bash,WebSearch,WebFetch")
        self.assertEqual(cmd[cmd.index("--max-turns") + 1], "25")
        denied = cmd[cmd.index("--disallowedTools") + 1:cmd.index("--max-turns")]
        for rule in ("Read(/%s/specialists/moat.md)" % run, "Read(/%s/specialists/moat_workpapers/**)" % run,
                     "Read(/%s/calc/valuation_*)" % run, "Read(/%s/cio/**)" % run, "Read(/%s/engine/**)" % run,
                     "Read(/%s/_cache/scratch/bear-case/**)" % run, "Bash(git:*)", "Bash(python3 scripts/git_publish.py:*)"):
            self.assertIn(rule, denied)
        self.assertFalse(any("/specialists/filings" in r for r in denied), "its own files stay readable")
        writes = [x for x in cmd[cmd.index("--allowedTools") + 1:cmd.index("--disallowedTools")] if x.startswith(("Write(", "Edit("))]
        self.assertTrue(writes)
        self.assertTrue(all("/specialists/filings" in w or "/calc/filings_" in w or "/scratch/filings/" in w for w in writes))
        sp = cmd[cmd.index("--append-system-prompt-file") + 1]
        self.assertIn("EPISTEMIC_TAGS:BEGIN", Path(sp).read_text(), "the constitution is injected: a headless main "
                                                                    "session does not preload its skills")
        reader_cmd = self.engine().command(agent_driver.reader_assignment(self.fx.dir, {
            "agent": "reader", "model": "sonnet", "effort": "high", "chunks": [], "role": "reader", "launch": "L1",
            "prompt": "p"}), "sid", "p", False, 0)
        self.assertNotIn("--append-system-prompt-file", reader_cmd, "readers preload nothing")
        review = self.engine().command(agent_driver.specialist_assignment(self.fx.dir, "bear-case", "p", stage="3"),
                                       "sid", "p", False, 25)
        self.assertNotIn("Read(/%s/specialists/valuation.md)" % run, review, "Stage-3 cross-examination may read peers")
        self.assertIn("Read(/%s/cio/**)" % run, review)

    def test_touching_another_specialists_file_fails_the_audit(self):
        (self.fx.dir / "specialists").mkdir(exist_ok=True)
        (self.fx.dir / "specialists" / "moat.md").write_text("moat report\n")
        with self.env(FAKE_UNITS="2", FAKE_TOUCH="specialists/moat.md", FAKE_PEEK="1"):
            rc, jobs = self.run_one(self.assignment(), context_limit=10 ** 7, segment_turns=5)
        self.assertEqual(rc, 0, self.logs)
        self.assertEqual(jobs[-1]["integrity"], ["specialists/moat.md"])
        res = reading_audit.run_audit(self.fx.dir, self.tdir)
        errs = " | ".join(res["errors"])
        self.assertIn("INDEPENDENCE filings J001 changed files it does not own: specialists/moat.md", errs)
        self.assertIn("INDEPENDENCE filings", errs.replace("J001 changed", ""))
        self.assertIn("Read call names 'specialists/moat.md'", errs)

    def test_independent_specialist_passes_the_independence_audit(self):
        with self.env(FAKE_UNITS="2"):
            rc, jobs = self.run_one(self.assignment(), context_limit=10 ** 7, segment_turns=5)
        res = reading_audit.run_audit(self.fx.dir, self.tdir)
        self.assertFalse([e for e in res["errors"] if "INDEPENDENCE" in e], res["errors"])
        self.assertEqual([r["breaches"] for r in res["independence"]], [0])
        self.assertTrue(any(a["agent"] == "filings" and a["expected_effort"] == "xhigh" for a in res["agents"]))

    def test_prompt_template_is_filled_from_the_identity_block(self):
        with self.assertRaises(SystemExit):
            agent_driver.specialist_prompt(self.fx.dir, "moat")
        (self.fx.dir / "engine").mkdir(exist_ok=True)
        (self.fx.dir / "engine" / "identity.md").write_text("IDENTITY\n- Legal name: Fixture Co Ltd\n")
        p = agent_driver.specialist_prompt(self.fx.dir, "moat")
        self.assertIn("You are the moat specialist for run %s." % self.fx.run_id, p)
        self.assertIn("- Legal name: Fixture Co Ltd", p)
        self.assertIn("specialists/moat_workpapers/progress.md", p)
        self.assertNotIn("{{", p)
        self.assertIn("INITIAL INDEPENDENT", p)


class TestVerificationLoop(EngineCase):
    """The verification loop: a value the specialist never saw is sent back until it is fixed; the verifier's material
    discrepancy goes back to the specialist and is re-checked; findings and lessons are recorded."""

    def run_specialist(self, **env):
        with self.env(FAKE_UNITS="2", FAKE_LEDGER="1", **env), \
                mock.patch.object(agent_driver, "report_check", lambda run_dir, report, *a, **k: (
                    lambda: [] if (run_dir / report).exists() else ["%s does not exist yet" % report])):
            eng = self.engine(context_limit=10 ** 7, segment_turns=5)
            (self.fx.dir / "engine").mkdir(exist_ok=True)
            (self.fx.dir / "engine" / "identity.md").write_text("IDENTITY\n- Legal name: Fixture Co Ltd\n")
            with agent_driver.Session(eng, "specialists"):
                rc = agent_driver.cmd_specialists(eng, ["filings"], 1)
        return rc, json.loads((self.fx.dir / "engine" / "jobs.json").read_text())["jobs"]

    def test_an_unseen_fact_value_is_sent_back_until_fixed_and_the_verifier_rechecks(self):
        rc, jobs = self.run_specialist(FAKE_UNSEEN="1", FAKE_DISCREPANCY="1")
        self.assertEqual(rc, 0, self.logs)
        spec = [j for j in jobs if j["agent"] == "filings"]
        kinds = [a["kind"] for s in spec[0]["sessions"] for a in s["attempts"]]
        self.assertIn("fix", kinds, "the unseen value went back to the specialist")
        fix_calls = [c for c in self.calls() if c["agent"] == "filings" and c["msg"].startswith("Your work does not pass")]
        self.assertTrue(fix_calls)
        ver = [j for j in jobs if j["agent"] == "verifier"]
        self.assertEqual(len(ver), 2, "a first check and a re-check")
        self.assertEqual(ver[0]["subject"], "filings")
        self.assertTrue(any(j["stage"] == "1-verify" for j in spec), "the discrepancy went back to the specialist")
        rec = json.loads((self.fx.dir / "qc" / "verification" / "filings.json").read_text())
        self.assertEqual(rec["status"], "PASS", rec)
        self.assertEqual(rec["tier_b"]["results"], {"Confirmed": 1}, "the corrected claim is confirmed on re-check")
        self.assertTrue(rec["rounds"])

    def test_tier_a_reads_the_transcripts(self):
        rc, jobs = self.run_specialist()
        self.assertEqual(rc, 0, self.logs)
        led = self.fx.dir / "specialists" / "filings_ledger.csv"
        with led.open() as fh:
            rows = list(csv.DictReader(fh))
        rows[1].update(tag="FACT", value="55,555")
        rows.append(dict(rows[0], claim_id="FIL-C003", value="1", source_url_or_id="https://example.com/never-opened.pdf"))
        with led.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        with self.env():
            rec = verify.specialist(self.fx.dir, "filings", self.tdir)
        checks = {f["check"]: f for f in rec["tier_a"]}
        self.assertIn("NUMBER_NOT_SEEN", checks)
        self.assertIn("FIL-C002 (value 55,555)", checks["NUMBER_NOT_SEEN"]["claims"])
        self.assertEqual(checks["SOURCE_NOT_OPENED"]["severity"], "major", "one unopened source of three is not blocking")
        self.assertEqual(rec["status"], "FAIL")
        verify.waive(self.fx.dir, "filings-NUMBER_NOT_SEEN", "fixture: accepted")
        with self.env():
            self.assertEqual(verify.specialist(self.fx.dir, "filings", self.tdir)["status"], "PASS",
                             "a waived finding does not block; the waiver is kept")
        with self.env():
            out = verify.run(self.fx.dir, "specialists", self.tdir)
        self.assertIn("filings", out["specialists"])
        self.assertTrue((self.fx.dir / "qc" / "VERIFICATION.md").exists())

    def test_validate_run_requires_a_passing_verification(self):
        import validate_run
        res = []
        validate_run.check_verification(self.fx.dir, res, "specialists")
        self.assertIn("verification missing", " ".join(res[0].errors))
        (self.fx.dir / "qc").mkdir(exist_ok=True)
        (self.fx.dir / "qc" / "verification.json").write_text(json.dumps({"stage": "specialists", "status": "FAIL",
            "run_findings": [], "specialists": {"moat": {"status": "FAIL", "findings": [{"check": "NUMBER_NOT_SEEN"}]}}}))
        res = []
        validate_run.check_verification(self.fx.dir, res, "final")
        errs = " ".join(res[0].errors)
        self.assertIn("run verify.py run RUN_DIR --stage final", errs)
        self.assertIn("moat: NUMBER_NOT_SEEN", errs)

    def test_the_seed_carries_the_calibration_lessons(self):
        text = verify.lessons_text("financials")
        self.assertIn("NUMBER_NOT_SEEN", text)
        self.assertIn("CALCULATION", text)
        self.assertNotIn("BHARTIARTL", text)

    def test_lessons_reach_the_next_brief_without_any_company_content(self):
        root = self.fx.tmp / "lessons"
        d = root / "OLDCO" / "runs" / "20250101T000000Z" / "qc"
        d.mkdir(parents=True)
        (d / "verification.json").write_text(json.dumps({"run_id": "20250101T000000Z", "specialists": {"filings": {
            "findings": [{"id": "filings-NUMBER_NOT_SEEN", "check": "NUMBER_NOT_SEEN", "severity": "blocking",
                          "owner": "agent", "detail": "OLDCO revenue 9,999", "waived": False}]}}}))
        text = verify.lessons_text("filings", root)
        self.assertIn("NUMBER_NOT_SEEN (found in 1 of the last verified runs)", text)
        self.assertNotIn("OLDCO", text)
        self.assertNotIn("9,999", text)
        self.assertEqual(verify.lessons_text("moat", root), "")


class TestReuse(unittest.TestCase):
    """A document read in an earlier run (same file, read and audited there) is reused, not read again."""

    def setUp(self):
        self.a = ReadingFixture()
        for c in self.a.plan["chunks"]:
            for role in reading.required_roles(c):
                self.a.write_extraction(c["id"], role)
        self.assertTrue(reading.status(self.a.dir, log=lambda m: None)["complete"])
        self.a.write_audit_pass()

    def tearDown(self):
        self.a.cleanup()

    def test_reused_documents_need_no_reader_and_their_copies_are_verified(self):
        b = ReadingFixture(tmp=self.a.tmp, run_id="20260601T090000Z")
        docs = {d["key"]: d for d in b.plan["documents"]}
        self.assertEqual({d.get("reused_from") for d in docs.values()}, {self.a.run_id})
        self.assertTrue(all(c.get("reused") for c in b.plan["chunks"]))
        self.assertEqual(reading.next_action(b.dir)["action"], "done", "nothing to read again")
        st = reading.status(b.dir, log=lambda m: None)
        self.assertTrue(st["complete"])
        self.assertGreater(st["reused_pages"], 0)
        self.assertIn("run %s" % self.a.run_id, (b.dir / rl.READING_COVERAGE).read_text())
        res = reading_audit.run_audit(b.dir, b.tmp / "no-transcripts")
        self.assertEqual(res["status"], "PASS", res["errors"])
        self.assertTrue(all(r["verified"] for r in res["reused"]))
        f = next((b.dir / reading.READING / "extractions").glob("*.jsonl"))
        f.write_text(f.read_text() + "\n")
        res = reading_audit.run_audit(b.dir, b.tmp / "no-transcripts")
        self.assertIn("changed since the copy", " | ".join(res["errors"]))

    def test_a_changed_file_is_read_again_and_so_is_every_document_that_repeats_it(self):
        b = ReadingFixture(tmp=self.a.tmp, run_id="20260601T090000Z", plan_now=False)
        meta = b.dir / "_cache" / "text" / "ar2025" / "meta.json"
        m = json.loads(meta.read_text())
        m["sha256"] = hashlib.sha256(b"a revised FY2025 report").hexdigest()
        meta.write_text(json.dumps(m))
        p = reading.plan(b.dir, 2, 24, 12, 0, log=lambda m: None)
        self.assertFalse(any(d.get("reused_from") for d in p["documents"]),
                         "FY2024 repeats FY2025's text, so it is read again with it")
        self.assertEqual(reading.next_action(b.dir)["action"], "launch")

    def test_no_reuse_without_a_passed_audit(self):
        (self.a.dir / rl.READING_AUDIT).write_text(json.dumps({"status": "FAIL", "readers": []}))
        b = ReadingFixture(tmp=self.a.tmp, run_id="20260601T090000Z")
        self.assertFalse(any(c.get("reused") for c in b.plan["chunks"]))

if __name__ == "__main__":
    unittest.main()
