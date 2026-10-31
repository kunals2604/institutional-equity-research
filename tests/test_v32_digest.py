"""Methodology 3.2.0: the reading switch and the web digest (reading off).

Covers: the run's reading mode (default for old runs; the guarded switch), the digest's check (search log, schema,
logged snapshot, quote on the snapshot page, amounts in the quote), the page confirmation against a filing's Stage-0
text layer, the build (topic files, packs, coverage record, status), the Stage-2 barrier with reading off, and the
DIGEST_AS_FACT verification check.
"""

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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import doc_text  # noqa: E402
from test_v24_acquisition_and_v3_scoring import make_pdf  # noqa: E402

PY = sys.executable
POPPLER = bool(doc_text.tool("pdftotext") and doc_text.tool("pdfinfo"))
RETRIEVAL_COLS = ["retrieved_at_utc", "author", "name", "url", "final_url", "http_status", "content_type", "bytes",
                  "sha256", "local_path", "error", "method", "validation"]
SNAP_URL = "https://news.example.com/fixco-fy2025-annual-report-highlights"
QUOTE = "FixCo reported contingent liabilities on income tax matters of Rs 1,234.56 crore in FY2025."


def new_run(tmp: Path, reading: str = "off") -> Path:
    r = subprocess.run([PY, str(ROOT / "scripts" / "new_run.py"), "--ticker", "FIXCO", "--company", "FixCo Ltd",
                        "--exchange", "NSE", "--segment", "main", "--cutoff", "2026-03-01", "--run-id", "20260301T090000Z",
                        "--root", str(tmp), "--reading", reading], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return tmp / r.stdout.strip()


@unittest.skipUnless(POPPLER, "poppler not installed")
class DigestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-digest-"))
        self.run = new_run(self.tmp)
        run = self.run
        # A filing with a Stage-0 text layer: the annual report FY2025.
        filing = make_pdf(run / "_cache" / "cio" / "ar_fy2025.pdf", [
            (595, 842, [(50, 60, "FixCo Ltd Annual Report 2024-25"), (50, 90, "Contingent liabilities not provided for")]),
            (595, 842, [(50, 60, "Note 41 Contingent liabilities"), (50, 90, "Income tax matters under appeal"),
                        (400, 90, "1,234.56"), (480, 90, "1,010.00")]),
        ])
        idx = doc_text.convert_many(run, [filing], log=lambda m: None)
        text_rel = str(Path(idx[str(filing)]["text"]).relative_to(run))
        with (run / "corpus" / "document_map.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["doc_type", "period", "status", "local_doc_id", "local_path", "local_pages",
                                              "primary_source", "primary_url", "alt_urls", "filed", "cached_path",
                                              "cached_sha256", "cached_pages", "text_path", "text_flags", "flags"])
            w.writeheader()
            w.writerow({"doc_type": "annual_report", "period": "FY2025", "status": "exchange_only",
                        "primary_url": "https://nse.example/ar25.pdf", "filed": "2025-07-01",
                        "cached_path": "_cache/cio/ar_fy2025.pdf", "cached_pages": "2", "text_path": text_rel})
            w.writerow({"doc_type": "transcript", "period": "Q4FY2025", "status": "exchange_only", "flags": "short_document",
                        "primary_url": "https://nse.example/tr.pdf", "filed": "2025-05-01"})
        # A web summary of it, snapshotted and logged.
        snap = make_pdf(run / "_cache" / "digest" / "snap.pdf", [
            (595, 842, [(40, 40, "FixCo FY2025 annual report: the highlights")]),
            (595, 842, [(40, 40, QUOTE)]),
        ])
        with (run / "source_retrievals.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=RETRIEVAL_COLS, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerow({"retrieved_at_utc": "2026-03-01T00:00:00+00:00", "author": "digest", "name": "AR-FY2025 news",
                        "url": SNAP_URL, "final_url": SNAP_URL, "http_status": "200", "content_type": "application/pdf",
                        "local_path": str(snap.relative_to(run)), "method": "chrome-snapshot", "validation": "ok"})
        import digest
        self.digest = digest
        digest.plan(run, log=lambda m: None)
        self.item = {"type": "contingent_liability", "fields": {"category": "Income tax matters", "amount_current": "1,234.56",
                                                                 "unit_of_amount": "INR crore"},
                     "period": "FY2025", "doc_key": "AR-FY2025", "basis": "standalone", "source_url": SNAP_URL,
                     "snapshot": str(snap.relative_to(run)), "snapshot_page": 2, "quote": QUOTE,
                     "publisher": "news.example.com", "source_kind": "news", "tier": 6}
        self.write_items([self.item])
        self.write_log(["AR-FY2025", "TR-Q4FY2025"])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_items(self, items, key="AR-FY2025"):
        d = self.run / rl.DIGEST_DIR / "items"
        d.mkdir(parents=True, exist_ok=True)
        (d / ("%s.jsonl" % key)).write_text("".join(json.dumps(i) + "\n" for i in items), encoding="utf-8")

    def write_log(self, keys):
        rows = ["| doc | queries run | sources opened | items | result |", "|---|---|---|---|---|"]
        rows += ["| %s | \"FixCo\" %s summary | news.example.com | 1 | %s |" % (k, k, "found" if k.startswith("AR") else
                                                                              "none found: 3 searches") for k in keys]
        (self.run / rl.DIGEST_DIR / "SEARCH_LOG.md").write_text("\n".join(rows) + "\n", encoding="utf-8")

    def errors(self):
        return self.digest.check_errors(self.run, tdir=self.tmp / "no-transcripts")

    def test_plan_scope(self):
        pl = self.digest.load_plan(self.run)
        self.assertEqual([d["key"] for d in pl["documents"]], ["AR-FY2025", "TR-Q4FY2025"])
        self.assertTrue(pl["documents"][1]["cover_letter_only"])
        self.assertIn("contingent_liability", pl["documents"][0]["types"])

    def test_check_passes_on_a_valid_digest(self):
        self.assertEqual(self.errors(), [])

    def test_check_rejects_quote_not_on_snapshot_page(self):
        self.write_items([dict(self.item, snapshot_page=1)])
        self.assertTrue(any("not printed on snapshot page 1" in e for e in self.errors()))

    def test_check_rejects_amount_not_in_quote(self):
        self.write_items([dict(self.item, fields=dict(self.item["fields"], amount_current="1,999.00"))])
        self.assertTrue(any("amount_current" in e for e in self.errors()))

    def test_check_rejects_missing_search_log_row(self):
        self.write_log(["AR-FY2025"])
        self.assertTrue(any("TR-Q4FY2025: no row in SEARCH_LOG.md" in e for e in self.errors()))

    def test_check_rejects_unlogged_snapshot_and_wrong_tier(self):
        self.write_items([dict(self.item, snapshot="_cache/digest/other.pdf", tier=3)])
        errs = self.errors()
        self.assertTrue(any("tier must be 6" in e for e in errs))
        self.assertTrue(any("not a logged page snapshot" in e for e in errs))

    def test_confirm_build_and_barrier_with_reading_off(self):
        counts = self.digest.confirm(self.run, log=lambda m: None)
        self.assertEqual(counts.get("page_confirmed"), 1)
        items = self.digest.digest_items(self.run)
        self.assertEqual(items[0]["provenance"], "digest_page_confirmed")
        self.assertEqual(items[0]["confirm"]["page"], 2)
        st = self.digest.build(self.run, tdir=self.tmp / "no-transcripts", log=lambda m: None)
        self.assertTrue(st["complete"], st)
        cov = (self.run / rl.DIGEST_COVERAGE).read_text(encoding="utf-8")
        self.assertTrue(cov.startswith("Reading stage OFF"))
        pack = (self.run / rl.pack_rel(self.run, "filings")).read_text(encoding="utf-8")
        self.assertIn("`corpus/digest/contingencies.md`", pack)
        self.assertIn("✓ AR-FY2025 p.2", (self.run / rl.DIGEST_DIR / "contingencies.md").read_text(encoding="utf-8"))
        # the Stage-2 barrier's reading check, with reading off
        import validate_run
        (self.run / rl.STRUCTURED_SUMMARY).write_text("# structured\n", encoding="utf-8")
        results = []
        validate_run.check_reading(self.run, results, "specialists", rl.current_version())
        errs = [e for r in results for e in r.errors]
        self.assertEqual(errs, [])

    def test_digest_as_fact_is_blocked(self):
        import verify
        rows = [{"claim_id": "FIL-C001", "tag": "FACT", "source_url_or_id": SNAP_URL},
                {"claim_id": "FIL-C002", "tag": "FACT", "source_url_or_id": "https://nse.example/ar25.pdf"},
                {"claim_id": "FIL-C003", "tag": "INFERENCE", "source_url_or_id": SNAP_URL}]
        f = verify.digest_fact_findings(self.run, rows, "filings")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["check"], "DIGEST_AS_FACT")
        self.assertIn("FIL-C001", " ".join(f[0]["claims"]))
        self.assertNotIn("FIL-C002", " ".join(f[0]["claims"]))


class ReadingModeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-mode-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_new_runs_default_off_and_old_runs_count_as_on(self):
        run = new_run(self.tmp)
        self.assertEqual(rl.reading_mode(run), "off")
        self.assertEqual(rl.pack_rel(run, "moat"), "corpus/digest/packs/moat.md")
        m = rl.load_json(run / rl.RUN_MANIFEST)
        del m["reading_mode"]
        rl.write_json(run / rl.RUN_MANIFEST, m)
        self.assertEqual(rl.reading_mode(run), "on")
        self.assertEqual(rl.coverage_rel(run), rl.READING_COVERAGE)

    def test_mode_switch_is_refused_after_a_specialist_ran(self):
        run = new_run(self.tmp)
        mp = [PY, str(ROOT / "scripts" / "manifest.py"), str(run)]
        r = subprocess.run(mp + ["set", "reading_mode=on"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        r = subprocess.run(mp + ["mode", "reading", "on", "--reason", "max plan"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(rl.reading_mode(run), "on")
        subprocess.run(mp + ["invocation", "financials", "--stage", "1", "--purpose", "x"], capture_output=True, text=True)
        r = subprocess.run(mp + ["mode", "reading", "off", "--reason", "x"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("specialists already ran", r.stderr)

    def test_specialist_prompt_follows_the_mode(self):
        import agent_driver
        run = new_run(self.tmp)
        (run / "engine").mkdir(exist_ok=True)
        (run / "engine" / "identity.md").write_text("IDENTITY\n- Legal name: FixCo Ltd\n", encoding="utf-8")
        with self.assertRaises(SystemExit):          # 3.2.0: no brief before the sector modules are selected
            agent_driver.specialist_prompt(run, "financials")
        m = rl.load_json(run / rl.RUN_MANIFEST)
        m["sector_modules"] = ["nbfc"]
        rl.write_json(run / rl.RUN_MANIFEST, m)
        text = agent_driver.specialist_prompt(run, "financials")
        self.assertIn("corpus/digest/packs/financials.md", text)
        for s in rl.sector_steps_for(run, "financials"):
            self.assertIn(s["id"], text)
        self.assertIn("READING STAGE OFF", text)
        self.assertNotIn("{{", text)


if __name__ == "__main__":
    unittest.main()
