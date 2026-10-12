"""Tests for the local filing corpus integration (scripts/corpus.py) using a synthetic
FilingForge-style library. No real company data."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
import research_lib as rl  # noqa: E402
from test_research_system import FixtureRun, run  # noqa: E402


def tiny_pdf(pages):
    """Minimal valid PDF with one line of Helvetica text per page."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in pages:
        stream = "BT /F1 12 Tf 72 720 Td (%s) Tj ET" % text
        objs.append("<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        content_id = len(objs)
        objs.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
                    "/Resources << /Font << /F1 3 0 R >> >> >>" % content_id)
        kids.append("%d 0 R" % len(objs))
    objs[1] = "<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join(kids), len(kids))
    out, offsets = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out.encode()))
        out += "%d 0 obj\n%s\nendobj\n" % (i, o)
    xref = len(out.encode())
    out += "xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += "".join("%010d 00000 n \n" % o for o in offsets)
    out += "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return out.encode()


def doc(lib, ticker, category, year, date, headline, body, pdf_pages=None, did="x"):
    d = lib / ticker / category / str(year)
    d.mkdir(parents=True, exist_ok=True)
    stem = "%s_%s__%s" % (date, headline.replace(" ", "_")[:60], did)
    fm = "---\nheadline: %s\ndate: %s\ncategory: %s\nnews_id: %s\nextracted: ok\n---\n\n" % (headline, date, category, did)
    (d / (stem + ".md")).write_text(fm + body, encoding="utf-8")
    if pdf_pages:
        (d / (stem + ".pdf")).write_bytes(tiny_pdf(pdf_pages))
    return d / (stem + ".md")


class TestCorpus(unittest.TestCase):
    def setUp(self):
        self.lib = Path(tempfile.mkdtemp())
        big = "Statement of Profit and Loss\n" + ("filler text line\n" * 3000)
        for y in range(2014, 2026):
            doc(self.lib, "FIXCO", "annual-reports", y, "%d-07-15" % y, "Annual Report %d" % y, big + "Related Party Transactions note\n", did="ar%d" % y)
        self.ar = doc(self.lib, "FIXCO", "annual-reports", 2026, "2026-06-20", "Integrated Annual Report for FY 2025-26",
                      big + "Contingent liabilities schedule 12\n", pdf_pages=["Cover page", "Contingent liabilities schedule 12 total"], did="ar2026")
        doc(self.lib, "FIXCO", "annual-reports", 2024, "2024-05-18", "Pursuant to Regulation 34", "tiny", did="thin")
        for i, (date, held) in enumerate([("2025-08-04", "July 31, 2025"), ("2025-11-05", "October 30, 2025"), ("2026-02-03", "January 29, 2026")]):
            doc(self.lib, "FIXCO", "concalls", int(date[:4]), date, "Transcript of Earnings Conference Call held on %s" % held,
                "Management guided 20% growth.\n" * 200, did="tr%d" % i)
        doc(self.lib, "FIXCO", "quarterly", 2025, "2025-11-05", "Financial Results for the quarter ended 30th September 2025",
            "Revenue table\n" * 500, did="q1")
        doc(self.lib, "FIXCO", "analyst-meets", 2025, "2025-09-01", "Intimation of schedule of Analyst Meet", "Meeting on ..." * 300, did="n1")

    def tearDown(self):
        shutil.rmtree(self.lib, ignore_errors=True)

    def docs(self):
        return {d["doc_id"]: d for d in corpus.scan(self.lib, "FIXCO")}

    def test_classification_periods_and_quality(self):
        d = self.docs()
        self.assertEqual(d["ar2026"]["fiscal_period"], "FY2026")
        self.assertEqual(d["ar2026"]["period_basis"], "stated")
        self.assertEqual(d["ar2015"]["fiscal_period"], "FY2015")
        self.assertTrue(d["thin"]["quality"].startswith("thin"))
        self.assertEqual(d["n1"]["value"], "noise")
        self.assertEqual(d["tr0"]["doc_type"], "concall_transcript")
        self.assertEqual(d["tr0"]["fiscal_period"], "Q1FY2026")
        self.assertEqual(d["tr2"]["fiscal_period"], "Q3FY2026")
        self.assertEqual(d["q1"]["fiscal_period"], "Q2FY2026")
        self.assertEqual(d["q1"]["period_basis"], "stated")

    def test_coverage_and_catalog(self):
        cov = corpus.coverage(corpus.scan(self.lib, "FIXCO"))
        self.assertEqual(len(cov["annual_reports"]), 13)
        self.assertEqual(cov["gaps"]["annual_reports"], 0)
        self.assertEqual(cov["gaps"]["transcript_quarters"], rl.depth_minimums()["concalls.quarters"] - 3)
        fx = FixtureRun()
        try:
            r = run("corpus.py", "catalog", "--ticker", "FIXCO", "--run", fx.dir, "--library", self.lib)
            self.assertEqual(r.returncode, 0, r.stdout)
            cat = (fx.dir / "corpus" / "CATALOG.md").read_text(encoding="utf-8")
            self.assertIn("Gaps to fill", cat)
            self.assertNotIn("Intimation of schedule", cat)
            _, rows = rl.read_csv(fx.dir / "corpus" / "catalog.csv")
            self.assertTrue(all(len(r["md_sha256"]) == 64 for r in rows))
            self.assertEqual(run("corpus.py", "catalog", "--ticker", "NOPE", "--run", fx.dir, "--library", self.lib).returncode, 2)
        finally:
            fx.cleanup()

    def test_search_with_per_document_cap(self):
        r = run("corpus.py", "search", "--ticker", "FIXCO", "Related Party", "--types", "annual_report", "--library", self.lib)
        self.assertEqual(r.returncode, 0)
        self.assertIn("12 hit(s)", r.stdout)
        r = run("corpus.py", "search", "--ticker", "FIXCO", "filler", "--types", "annual_report", "--per-doc", "2",
                "--max", "100", "--library", self.lib)
        self.assertIn("26 hit(s)", r.stdout)

    @unittest.skipUnless(corpus.pdftotext_bin(), "poppler (pdftotext) not installed")
    def test_locate_pdf_page(self):
        fx = FixtureRun()
        try:
            self.assertEqual(corpus.locate(self.ar, fx.dir, "Contingent liabilities schedule 12"), [2])
            r = run("corpus.py", "locate", "--run", fx.dir, self.ar, "Contingent liabilities schedule 12")
            self.assertIn("PDF page(s): 2", r.stdout)
            r = run("corpus.py", "pages", "--run", fx.dir, self.ar)
            self.assertIn("2 pages", r.stdout)
        finally:
            fx.cleanup()


if __name__ == "__main__":
    unittest.main()
