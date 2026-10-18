"""Tests for methodology 2.4 (acquisition layer, text layer, audit, scuttlebutt, SME) and 3.0 (the decision engine).
Synthetic data only; no network (a local HTTP server stands in for remote hosts).

Run:  python3 -m unittest discover tests -v
"""

import csv
import datetime as dt
import http.server
import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import research_lib as rl  # noqa: E402
import audit_tools  # noqa: E402
import build_scorecard as bs  # noqa: E402
import doc_text  # noqa: E402
import document_map as dmap  # noqa: E402
import exchange_index as ei  # noqa: E402
import fetch_source as fs  # noqa: E402
import market_data as md  # noqa: E402
import netfetch as nf  # noqa: E402
import valuation_tools as vt  # noqa: E402
import xbrl_facts as xf  # noqa: E402
from test_research_system import FixtureRun, audit_report, audit_resolutions, specialist_report  # noqa: E402

PY = sys.executable
TEMPLATE = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))
LEGACY = json.loads((ROOT / "tests" / "fixtures" / "scorecard_v2.example.json").read_text(encoding="utf-8"))


def write(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")
    return path


def make_pdf(path: Path, pages):
    """A minimal valid PDF: pages = [(width, height, [(x, y_from_top, text), ...]), ...] in Helvetica 10 pt."""
    objs = {1: b"<< /Type /Catalog /Pages 2 0 R >>", 3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"}
    kids, n = [], 4
    for w, h, items in pages:
        stream = "".join("BT /F1 10 Tf 1 0 0 1 %.2f %.2f Tm (%s) Tj ET\n" % (x, h - y, t.replace("(", "\\(").replace(")", "\\)"))
                         for x, y, t in items).encode("latin-1")
        objs[n] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources << /Font << /F1 3 0 R >> >> "
                   "/Contents %d 0 R >>" % (w, h, n + 1)).encode()
        objs[n + 1] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream"
        kids.append("%d 0 R" % n)
        n += 2
    objs[2] = ("<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join(kids), len(kids))).encode()
    out, offsets = io.BytesIO(), {}
    out.write(b"%PDF-1.4\n")
    for i in sorted(objs):
        offsets[i] = out.tell()
        out.write(b"%d 0 obj\n" % i + objs[i] + b"\nendobj\n")
    xref = out.tell()
    size = max(objs) + 1
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % size)
    for i in range(1, size):
        out.write(b"%010d 00000 n \n" % offsets[i])
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref))
    write(path, out.getvalue())
    return path


def right(x_right, text, size=10.0):
    return x_right - len(text) * 0.556 * size


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class NetfetchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_sniff_and_validation(self):
        good = make_pdf(self.tmp / "g.pdf", [(595, 842, [(50, 50, "Hello world")])])
        self.assertEqual(nf.sniff(str(good)), "pdf")
        kind, problems, info = nf.validate_payload(str(good), "pdf")
        self.assertEqual((kind, problems), ("pdf", []))
        self.assertEqual(info.get("pages"), 1)
        err = write(self.tmp / "e.pdf", "<html><head><title>Access Denied</title></head><body>no</body></html>")
        kind, problems, _ = nf.validate_payload(str(err), "pdf")
        self.assertEqual(kind, "html")
        self.assertTrue(any("error or bot-check" in p for p in problems) and any("expected pdf" in p for p in problems))
        trunc = write(self.tmp / "t.pdf", good.read_bytes()[:-30])
        self.assertTrue(nf.validate_payload(str(trunc), "pdf")[1], "a truncated PDF must not validate")
        small_json = write(self.tmp / "j.json", '{"data":[]}')
        self.assertEqual(nf.validate_payload(str(small_json), "json")[1], [], "an empty but valid JSON reply is fine")
        z = self.tmp / "a.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("../evil/report.pdf", good.read_bytes())
        self.assertEqual(nf.validate_payload(str(z), "pdf")[1], [], "exchanges publish older reports as ZIPs of PDFs")
        members = nf.extract_zip(str(z), str(self.tmp / "out"))
        self.assertEqual(len(members), 1)
        self.assertTrue(str(Path(members[0]["path"]).resolve()).startswith(str((self.tmp / "out").resolve())),
                        "a ZIP member named '../evil/...' is written inside the output folder")

    def test_profiles_and_hosts(self):
        self.assertEqual(nf.profile_for("https://www.nseindia.com/api/annual-reports?x=1")["name"], "nse-api")
        self.assertEqual(nf.profile_for("https://nsearchives.nseindia.com/corporate/a.pdf")["name"], "nse-archive")
        bse = nf.profile_for("https://api.bseindia.com/BseIndiaAPI/api/AnnualReport_New/w?scripcode=1")
        self.assertTrue(bse["http2"] and "sec-ch-ua" in bse["headers"])
        self.assertEqual(nf.profile_for("https://example.com/x")["name"], "default")
        self.assertFalse(nf.is_public_host("http://127.0.0.1:8000/a.pdf"))
        self.assertFalse(nf.is_public_host("http://localhost/a.pdf"))
        self.assertTrue(nf.is_public_host("https://assets.example.com/a.pdf"))
        self.assertEqual(nf.expected_kind("https://x.com/a/b.PDF"), "pdf")
        self.assertEqual(nf.expected_kind("https://www.nseindia.com/api/foo"), "json")


class FetchFallbackTest(unittest.TestCase):
    def setUp(self):
        self.fx = FixtureRun()
        self.www = Path(tempfile.mkdtemp())
        make_pdf(self.www / "mirror.pdf", [(595, 842, [(50, 50, "Annual report mirror copy")])])
        write(self.www / "denied.pdf", "<html><head><title>Access Denied</title></head><body>blocked</body></html>")
        handler = lambda *a, **k: _Quiet(*a, directory=str(self.www), **k)  # noqa: E731
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.www, ignore_errors=True)
        self.fx.cleanup()

    def test_mirror_after_missing_primary_and_error_page_rejected(self):
        res = fs.retrieve(self.fx.dir, self.base + "/missing.pdf", "filings", "AR", alts=[self.base + "/mirror.pdf"], retries=1)
        self.assertIsNotNone(res["path"])
        self.assertIn("mirror 1", res["method"])
        bad = fs.retrieve(self.fx.dir, self.base + "/denied.pdf", "filings", "AR", retries=1)
        self.assertIsNone(bad["path"], "an HTML error page served as a PDF is a failed retrieval")
        _, rows = rl.read_csv(self.fx.dir / "source_retrievals.csv")
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[-1]["error"])


class ExchangeIndexTest(unittest.TestCase):
    def test_classification(self):
        cases = {
            ("Analysts/Institutional Investor Meet/Con. Call Updates", "informed the Exchange about Transcript"): "transcript",
            ("Analysts/Institutional Investor Meet/Con. Call Updates", "about Schedule of meet"): "call_schedule",
            ("Analysts/Institutional Investor Meet/Con. Call Updates", "about Link of Recording"): "audio_recording",
            ("Bharti-Transcript-of-30th-AGM.pdf",): "agm_transcript",
            ("Trading Window", "closure"): "trading_window",
            ("Action(s) taken or orders passed", "penalty"): "penalty_order",
            ("Credit Rating", ""): "credit_rating",
            ("Shareholders meeting", "Voting results"): "voting_results",
        }
        for parts, want in cases.items():
            self.assertEqual(ei.classify(*parts), want, parts)

    def test_periods(self):
        d = dt.date(2026, 8, 10)
        self.assertEqual(ei.quarter_label(dt.date(2026, 6, 30)), "Q1FY2027")
        self.assertEqual(ei.quarter_label(dt.date(2026, 3, 31)), "Q4FY2026")
        self.assertEqual(ei.quarter_label(dt.date(2025, 3, 31), fy_end_month=12), "Q1FY2025")
        self.assertEqual(ei.infer_period("transcript", d, "Transcript_Q1_FY12_25947_1518520400727.pdf"), "Q1FY2012")
        self.assertEqual(ei.infer_period("transcript", d, "BAL_2QFY14_Transcript.pdf"), "Q2FY2014")
        self.assertEqual(ei.infer_period("transcript", d, "Second-Quarter-Ended-September-30-2018-Call"), "Q2FY2019")
        self.assertEqual(ei.infer_period("transcript", d, "quarterly_results/2025-26/Q2/Earning-Call-Transcript.pdf"), "Q2FY2026")
        self.assertEqual(ei.infer_period("transcript", d, "informed the Exchange about Transcript"), "Q1FY2027")
        self.assertEqual(ei.infer_period("annual_report", None, "Annual Report 2024-2025"), "FY2025")
        self.assertIsNone(ei.guess_date("Transcript_1518520400727.pdf"), "long numeric IDs are not dates")
        self.assertEqual(ei.guess_date("results_2024-05-14.pdf"), dt.date(2024, 5, 14))

    def test_nse_normalization_and_bse_lookup(self):
        fx = FixtureRun()
        try:
            ix = ei.Indexer(fx.dir, sleep=0)
            data = {
                "nse_annual_reports": {"data": [{"fromYr": "2024", "toYr": "2025", "broadcast_dttm": "16-JUL-2025 22:57:38",
                                                 "fileName": "https://nsearchives.nseindia.com/annual_reports/AR_1.pdf"}]},
                "nse_announcements": [{"an_dt": "11-Aug-2025 19:02:14", "desc": "Analysts/Institutional Investor Meet/Con. Call Updates",
                                       "attchmntText": "informed the Exchange about Transcript",
                                       "attchmntFile": "https://nsearchives.nseindia.com/corporate/X_Transcript.pdf", "seq_id": "1"}],
                "nse_results_quarterly": [{"toDate": "30-Jun-2025", "fromDate": "01-Apr-2025", "consolidated": "Consolidated",
                                           "relatingTo": "First Quarter", "financialYear": "01-Apr-2025 To 31-Mar-2026",
                                           "audited": "Un-Audited", "xbrl": "https://nsearchives.nseindia.com/corporate/xbrl/a.xml",
                                           "broadCastDate": "05-Aug-2025 17:00:00", "seqNumber": "9"}],
            }
            ix.get_json = lambda label, url: data.get(label)
            n = ix.nse("FIXTURECO", years=1, cutoff=dt.date(2026, 1, 1))
            self.assertEqual(n, 3)
            types = {(r["doc_type"], r["fiscal_period"]) for r in ix.rows}
            self.assertIn(("annual_report", "FY2025"), types)
            self.assertIn(("transcript", "Q1FY2026"), types)
            self.assertIn(("results_xbrl", "Q1FY2026"), types)
            ix.write()
            self.assertTrue((fx.dir / "corpus" / "index_summary.json").exists())
            self.assertEqual(len(ei.read_index(fx.dir)), 3)
        finally:
            fx.cleanup()


class DocumentMapTest(unittest.TestCase):
    def test_statuses_and_two_channel_flags(self):
        fx = FixtureRun()
        try:
            rows = [
                {"source": "NSE", "doc_type": "annual_report", "date": "2025-07-16", "fiscal_period": "FY2025", "title": "AR",
                 "category": "", "url": "https://nsearchives.nseindia.com/AR25.pdf", "alt_url": "", "size": "", "ref": ""},
                {"source": "BSE", "doc_type": "annual_report", "date": "2024-07-29", "fiscal_period": "FY2024", "title": "AR",
                 "category": "", "url": "https://www.bseindia.com/AR24.pdf", "alt_url": "", "size": "", "ref": ""},
                {"source": "NSE", "doc_type": "transcript", "date": "2025-08-11", "fiscal_period": "Q1FY2026", "title": "T",
                 "category": "", "url": "https://nsearchives.nseindia.com/T.pdf", "alt_url": "", "size": "", "ref": ""},
                {"source": "NSE", "doc_type": "results_xbrl", "date": "2025-08-05", "fiscal_period": "Q1FY2026", "title": "R",
                 "category": "", "url": "https://nsearchives.nseindia.com/r.xml", "alt_url": "", "size": "", "ref": ""},
            ]
            idx = fx.dir / "_cache" / "index" / "exchange_index.csv"
            idx.parent.mkdir(parents=True, exist_ok=True)
            with idx.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=ei.INDEX_COLUMNS)
                w.writeheader()
                w.writerows(rows)
            cat = fx.dir / "corpus" / "catalog.csv"
            cat.parent.mkdir(parents=True, exist_ok=True)
            cols = ["doc_id", "doc_type", "value", "quality", "date", "fiscal_period", "period_basis", "headline", "md_path", "pdf_path"]
            with cat.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                # the FY2024 report is mislabelled FY2023 locally: the cross-check must catch it
                w.writerow({"doc_id": "L24", "doc_type": "annual_report", "value": "core", "quality": "ok", "date": "2024-07-30",
                            "fiscal_period": "FY2023", "headline": "AR", "md_path": "", "pdf_path": ""})
                w.writerow({"doc_id": "T1", "doc_type": "concall_transcript", "value": "core", "quality": "thin-extraction",
                            "date": "2025-08-11", "fiscal_period": "Q1FY2026", "headline": "T", "md_path": "", "pdf_path": ""})
            m = rl.load_json(fx.dir / rl.RUN_MANIFEST)
            m["research_cutoff"] = "2026-01-01"
            rl.write_json(fx.dir / rl.RUN_MANIFEST, m)
            res = dmap.build(fx.dir, years=3, quarters=2, download="none", sleep=0, log=lambda *_: None)
            self.assertTrue(res["anomalies"], "local FY2023 label vs exchange FY2024 filing of the same date")
            with (fx.dir / "corpus" / "document_map.csv").open(newline="", encoding="utf-8") as f:
                got = {(r["doc_type"], r["period"]): r for r in csv.DictReader(f)}
            self.assertEqual(got[("annual_report", "FY2025")]["status"], "exchange_only")
            self.assertEqual(got[("transcript", "Q1FY2026")]["status"], "both")
            self.assertIn("local_quality:thin-extraction", got[("transcript", "Q1FY2026")]["flags"])
            self.assertEqual(got[("annual_report", "FY2023")]["status"], "local_only")
            self.assertIn("period_label_mismatch", got[("annual_report", "FY2023")]["flags"])
            self.assertTrue((fx.dir / "corpus" / "DOCUMENT_MAP.md").exists())
        finally:
            fx.cleanup()

    def test_quarter_helpers(self):
        self.assertEqual(dmap.quarter_end("Q1FY2027"), dt.date(2026, 6, 30))
        self.assertEqual(dmap.quarter_end("Q4FY2026"), dt.date(2026, 3, 31))
        self.assertEqual(dmap.previous_quarters("Q1FY2027", 3), ["Q1FY2027", "Q4FY2026", "Q3FY2026"])


class MarketDataTest(unittest.TestCase):
    SEC = ("SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, "
           "TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
           "FIXCO, EQ, 12-Oct-2026, 100, 101, 105, 99, 103, 103.5, 102, 1000, 10.5, 50, 600, 60.00\n"
           "FIXCO, BL, 12-Oct-2026, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1\n")

    def test_formats(self):
        r = md.parse_bhavcopy("sec_full", self.SEC.encode(), "FIXCO")
        self.assertEqual((r["series"], r["close"], r["traded_value_inr"], r["delivery_pct"]), ("EQ", 103.5, 1050000.0, 60.0))
        hist = io.BytesIO()
        with zipfile.ZipFile(hist, "w") as zf:
            zf.writestr("cm.csv", "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN\n"
                                  "FIXCO,EQ,1,2,1,1.5,1.5,1,10,15,15-JAN-2016,3,INE000\n")
        self.assertEqual(md.parse_bhavcopy("cm_hist", hist.getvalue(), "FIXCO")["close"], 1.5)
        self.assertEqual([f for f, _ in md.urls_for(dt.date(2016, 1, 15))], ["cm_hist"])
        self.assertEqual([f for f, _ in md.urls_for(dt.date(2025, 1, 15))][0], "sec_full")

    def test_corporate_actions_and_history(self):
        fx = FixtureRun()
        try:
            raw = fx.dir / "_cache" / "index" / "raw" / "nse_corporate_actions.json"
            write(raw, json.dumps([
                {"subject": "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 5/- Per Share", "exDate": "01-Jul-2021"},
                {"subject": "Dividend - Rs 2 Per Share", "exDate": "01-Aug-2021"}]))
            ev = md.corporate_actions(fx.dir, "FIXCO")
            self.assertEqual([e["kind"] for e in ev], ["split", "dividend"])
            self.assertAlmostEqual(ev[0]["factor"], 2.0)
            mk = md.Market(fx.dir)
            def close(d):
                if d < dt.date(2021, 7, 1):
                    return 200.0                  # before the 2:1 split
                return 50.0 if d.year == 2022 else 100.0
            mk.quote = lambda sym, d, back=8: {"trade_date": d.isoformat(), "close": close(d), "volume": 1, "traded_value_inr": 1}
            h = md.history(mk, fx.dir, "FIXCO", dt.date(2023, 12, 31), 3, "monthly")
            self.assertAlmostEqual(h["points"][0]["adj_close"], 100.0, msg="pre-split close halved")
            self.assertAlmostEqual(h["max_drawdown"], -0.5, msg="the split is not a drawdown; the 2022 fall is")
        finally:
            fx.cleanup()


XBRL = """<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in="http://example/in">
<xbrli:context id="FourD"><xbrli:entity><xbrli:identifier scheme="s">FIXCO</xbrli:identifier></xbrli:entity>
<xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-03-31</xbrli:endDate></xbrli:period></xbrli:context>
<in:NatureOfReportStandaloneConsolidated contextRef="OneD">Consolidated</in:NatureOfReportStandaloneConsolidated>
<in:DateOfStartOfReportingPeriod contextRef="OneD">2025-01-01</in:DateOfStartOfReportingPeriod>
<in:DateOfEndOfReportingPeriod contextRef="OneD">2025-03-31</in:DateOfEndOfReportingPeriod>
<in:DateOfStartOfReportingPeriod contextRef="FourD">2024-04-01</in:DateOfStartOfReportingPeriod>
<in:DateOfEndOfReportingPeriod contextRef="FourD">2025-03-31</in:DateOfEndOfReportingPeriod>
<in:RevenueFromOperations contextRef="OneD" unitRef="INR">25000000000</in:RevenueFromOperations>
<in:RevenueFromOperations contextRef="FourD" unitRef="INR">100000000000</in:RevenueFromOperations>
<in:ProfitBeforeTax contextRef="FourD" unitRef="INR">10000000000</in:ProfitBeforeTax>
<in:ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod contextRef="FourD" unitRef="INR">2000000000</in:ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod>
<in:BorrowingsNoncurrent contextRef="OneI" unitRef="INR">30000000000</in:BorrowingsNoncurrent>
<in:BorrowingsCurrent contextRef="OneI" unitRef="INR">5000000000</in:BorrowingsCurrent>
</xbrli:xbrl>"""


class XbrlTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_nse_quirks_and_mapping(self):
        p = write(self.tmp / "x.xml", XBRL)
        ctx, facts, text = xf.parse_xbrl(str(p))
        self.assertEqual((ctx["FourD"]["start"], ctx["FourD"]["end"]), ("2024-04-01", "2025-03-31"),
                         "the year-to-date period comes from the reporting-period facts, not the mislabelled context")
        self.assertFalse(ctx["OneD"]["dims"], "an undefined base context is dimension-free")
        self.assertEqual(ctx["OneI"]["instant"], "2025-03-31")
        rows = {(r["item"], r["period"]): r["value"] for r in xf.rows_from_filing(str(p), "u", "consolidated", "INR crore", 3, False)}
        self.assertEqual(rows[("revenue", "FY2025")], 10000.0)
        self.assertEqual(rows[("total_debt", "FY2025")], 3500.0)
        self.assertNotIn(("revenue", "Q4FY2025"), rows)
        self.assertEqual(xf.rows_from_filing(str(p), "u", "standalone", "INR crore", 3, False), [], "basis respected")

    def test_integrated_filing_table_and_reconcile(self):
        html = """<html><body>
<table><tr><td>Level of rounding used in financial results</td><td>Lakhs</td></tr>
<tr><td>Nature of report standalone or consolidated</td><td>Consolidated</td></tr></table>
<table><tr><td>A</td><td>Date of start of reporting period</td><td>01-01-2026</td><td>01-04-2025</td></tr>
<tr><td>B</td><td>Date of end of reporting period</td><td>31-03-2026</td><td>31-03-2026</td></tr>
<tr><td></td><td>Revenue from operations</td><td>2,50,000.00</td><td>10,00,000.00</td></tr>
<tr><td></td><td>Other income</td><td>1,000.00</td><td>4,000.00</td></tr>
<tr><td></td><td>Total income</td><td>2,51,000.00</td><td>10,04,000.00</td></tr>
<tr><td></td><td>Total profit before tax</td><td>(500.00)</td><td>80,000.00</td></tr></table>
</body></html>"""
        p = write(self.tmp / "INTEGRATED_FILING_INDAS_1_iXBRL_WEB.html", html)
        rows = {(r["item"], r["period"]): r["value"] for r in xf.rows_from_integrated(str(p), "u", "consolidated", "INR crore", 3, True)}
        self.assertEqual(rows[("revenue", "FY2026")], 10000.0)
        self.assertEqual(rows[("pbt", "Q4FY2026")], -5.0)
        facts = self.tmp / "facts.csv"
        hist = self.tmp / "hist.csv"
        for path, rws in ((facts, [("pbt", "FY2025", 1000.0), ("other:share_of_associates_jv", "FY2025", 200.0)]),
                          (hist, [("pbt", "FY2025", 1200.0)])):
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["item", "period", "value", "unit", "basis", "source_url_or_id", "locator"])
                for it, per, v in rws:
                    w.writerow([it, per, v, "INR crore", "consolidated", "u", "l"])
        out = xf.reconcile(hist, facts, 0.01)
        self.assertEqual(len(out), 1)
        self.assertFalse(out[0]["within_tolerance"])
        self.assertIn("share of associates", out[0]["likely_cause"])


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.fx = FixtureRun()
        (self.fx.dir / "audit").mkdir(exist_ok=True)

    def tearDown(self):
        self.fx.cleanup()

    def check(self, findings, opinion, resolutions=None, followup=None):
        write(self.fx.dir / rl.AUDIT_REPORT, audit_report(self.fx.run_id, findings=findings, opinion=opinion))
        if resolutions is not None:
            write(self.fx.dir / "cio" / "audit_resolutions.md", resolutions)
        if followup:
            write(self.fx.dir / "audit" / "audit_followup_1.md", followup)
        res, found = rl.validate_audit_report(self.fx.dir / rl.AUDIT_REPORT)
        rl.check_audit_resolutions(self.fx.dir, found, res)
        return res

    def test_opinion_must_match_findings(self):
        self.assertFalse(self.check((("AUD-F01", "Critical"),), "Qualified", audit_resolutions((("AUD-F01", "Critical"),))).ok)
        self.assertFalse(self.check((("AUD-F01", "Major"),), "Clean with minor findings", audit_resolutions((("AUD-F01", "Major"),))).ok)
        self.assertTrue(self.check((("AUD-F01", "Minor"),), "Clean with minor findings", audit_resolutions()).ok)

    def test_critical_needs_fix_and_closed_reauditing(self):
        crit = (("AUD-F01", "Critical"),)
        r = self.check(crit, "Adverse", audit_resolutions(crit, "Accepted limitation"))
        self.assertTrue(any("cannot" in e or "not accepted" in e or "must be fixed" in e for e in r.errors), r.errors)
        r = self.check(crit, "Adverse", audit_resolutions(crit, "Fixed"))
        self.assertTrue(any("re-audit" in e for e in r.errors), r.errors)
        r = self.check(crit, "Adverse", audit_resolutions(crit, "Fixed"), "| AUD-F01 | Closed | checked the fix |")
        self.assertTrue(r.ok, r.errors)
        r = self.check((("AUD-F02", "Major"),), "Qualified", "# none\n")
        self.assertTrue(any("AUD-F02" in e for e in r.errors))


class TieoutTest(unittest.TestCase):
    def test_statuses(self):
        fx = FixtureRun()
        try:
            ledger = fx.dir / "cio" / "cio_ledger.csv"
            from test_research_system import write_ledger, fact_row
            rows = [fact_row("CIO-C001", "cio", "Price"), fact_row("CIO-C002", "cio", "Revenue")]
            rows[0].update({"value": "1778.7", "unit": "INR", "metric": "price"})
            rows[1].update({"value": "172985.2", "unit": "INR crore", "metric": "revenue"})
            write_ledger(ledger, rows)
            report = write(fx.dir / "cio" / "final_report.md",
                           "## Decision Dashboard\nThe price is 1,778.70 [FACT: CIO-C001].\n"
                           "Revenue was 1.73 lakh crore [FACT: CIO-C002].\n"
                           "Revenue was 172,985.2 crore while the price is shown [FACT: CIO-C001].\n"
                           "Something else entirely 4,242 [FACT: CIO-C001].\n")
            out = fx.dir / "audit" / "tieout.csv"
            audit_tools.tieout(fx.dir, report, out)
            with out.open(newline="", encoding="utf-8") as f:
                st = [r["status"] for r in csv.DictReader(f)]
            self.assertEqual(sorted(st), ["match", "match", "mismatch", "other_claim"])
            s1 = fx.dir / "audit" / "s1.csv"
            s2 = fx.dir / "audit" / "s2.csv"
            audit_tools.sample(fx.dir, 5, "seed", s1)
            audit_tools.sample(fx.dir, 5, "seed", s2)
            self.assertEqual(s1.read_text(encoding="utf-8"), s2.read_text(encoding="utf-8"), "the sample is reproducible")
            self.assertIn("decision-critical", s1.read_text(encoding="utf-8"))
        finally:
            fx.cleanup()


class VersionGatingTest(unittest.TestCase):
    def test_since_tagged_sections_and_roster(self):
        all_fin = rl.agent_sections("financials")
        old_fin = rl.agent_sections("financials", (2, 3, 0))
        self.assertIn("Debt Structure, Maturities and Refinancing", all_fin)
        self.assertNotIn("Debt Structure, Maturities and Refinancing", old_fin)
        self.assertTrue(all("(since" not in s for s in all_fin))
        self.assertNotIn("scuttlebutt", rl.specialists_for((2, 3, 0)))
        self.assertIn("scuttlebutt", rl.specialists_for((2, 4, 0)))
        self.assertNotIn("Ground-Truth Evidence", rl.final_sections_for((2, 3, 0)))
        self.assertIn("Ground-Truth Evidence", rl.final_sections_for((2, 4, 0)))

    def test_sme_section_required_for_sme_runs(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            text = specialist_report("moat", "20260101T090000Z")
            p = write(tmp / "moat.md", text)
            self.assertTrue(rl.validate_specialist_report(p, segment="main").ok)
            self.assertFalse(rl.validate_specialist_report(p, segment="sme").ok)
            write(p, text + "\n## %s\nSME content [INFERENCE].\n" % rl.SME_SECTION)
            self.assertTrue(rl.validate_specialist_report(p, segment="sme").ok)
        finally:
            shutil.rmtree(tmp)


def v3(**changes):
    sc = json.loads(json.dumps(TEMPLATE))
    for k, v in changes.items():
        sc[k] = v
    return sc


def set_dims(sc, key, scores=None, confidence=None):
    for d in sc[key]["dimensions"]:
        if scores and d["id"] in scores:
            d["score"] = scores[d["id"]]
        if confidence:
            d["confidence"] = confidence.get(d["id"], confidence.get("*", d["confidence"]))
    return sc


class DecisionEngineTest(unittest.TestCase):
    def test_profiles_sum_and_match_base(self):
        prof = rl.weight_profiles()
        base = {d: w for d, _, w in rl.dimension_weights("BQ") + rl.dimension_weights("IA")}
        self.assertEqual({k: float(v) for k, v in base.items()}, prof["Base"], "Base column repeats the dimension tables")
        for name, w in prof.items():
            self.assertAlmostEqual(sum(v for k, v in w.items() if k.startswith("BQ")), 100.0, msg=name)
            self.assertAlmostEqual(sum(v for k, v in w.items() if k.startswith("IA")), 100.0, msg=name)
        self.assertEqual(set(rl.dimension_owners()), set(base))

    def test_uncertainty_never_rewarded(self):
        self.assertEqual(rl.effective_score(90, "High"), 90.0)
        self.assertAlmostEqual(rl.effective_score(90, "Low"), 76.0)
        self.assertEqual(rl.effective_score(30, "Low"), 30.0, "weak evidence never raises a low score")

    def test_template_reproduces_and_validates(self):
        sc = bs.compute(json.loads(json.dumps(TEMPLATE)), None)
        for key in ("business_quality", "investment_attractiveness"):
            self.assertEqual(sc[key]["final"], TEMPLATE[key]["final"])
        self.assertEqual(sc["mapped_verdict"], TEMPLATE["mapped_verdict"])
        self.assertTrue(rl.validate_scorecard(ROOT / "templates" / "scorecard.example.json").ok)

    def strong(self, layer="Layer 1 — Bedrock Compounder"):
        sc = v3(primary_layer=layer, hybrid=False)
        set_dims(sc, "business_quality", {"BQ1": 85, "BQ2": 85, "BQ3": 80, "BQ4": 85, "BQ5": 80, "BQ6": 85, "BQ7": 85, "BQ8": 70},
                 {"*": "High"})
        set_dims(sc, "investment_attractiveness", {"IA1": 85, "IA2": 90, "IA3": 85, "IA4": 85, "IA5": 80, "IA6": 80, "IA7": 90, "IA8": 85},
                 {"*": "High"})
        sc["investment_attractiveness"]["confidence"] = "High"
        sc["price_metrics"] = {"margin_of_safety": 0.35, "expected_irr": 0.24, "hurdle_rate": 0.12, "asymmetry_ratio": 3.5, "robust": True}
        sc["layer_fit"]["L1"]["score"] = 80
        return sc

    def test_strong_buy_requires_high_conviction(self):
        ev = rl.evaluate_v3(self.strong())
        self.assertEqual((ev["mapped_verdict"], ev["conviction"]), ("STRONG BUY", "High"))
        sc = self.strong()
        sc["price_metrics"]["robust"] = False
        sc["price_metrics"]["asymmetry_ratio"] = 1.2          # 3 (edge) + 0 + 2 (High) + 0 = 5 points: Medium
        ev = rl.evaluate_v3(sc)
        self.assertEqual((ev["mapped_verdict"], ev["conviction"], ev["conviction_points"]), ("BUY", "Medium", 5))

    def test_must_pass_and_required_margin(self):
        sc = self.strong()
        set_dims(sc, "business_quality", {"BQ1": 55})
        self.assertEqual(rl.evaluate_v3(sc)["mapped_verdict"], "HOLD / NEUTRAL", "a compounder below its cost of capital is no buy")
        sc = self.strong()
        sc["investment_attractiveness"]["confidence"] = "Medium"
        sc["price_metrics"]["margin_of_safety"] = 0.05
        ev = rl.evaluate_v3(sc)
        self.assertEqual((ev["required_margin_of_safety"], ev["mapped_verdict"]), (0.10, "WATCHLIST — WAIT FOR BETTER PRICE"))
        sc = self.strong()
        sc["investment_attractiveness"]["confidence"] = "Low"
        self.assertEqual(rl.evaluate_v3(sc)["mapped_verdict"], "WATCHLIST — WAIT FOR BETTER PRICE", "no buy at Low confidence")
        sc = self.strong("Layer 4 — Venture-Style / Optionality Bet")
        sc["layer_fit"]["L4"]["score"] = 70
        ev = rl.evaluate_v3(sc)
        self.assertEqual(ev["mapped_verdict"], "SPECULATIVE BUY")
        self.assertEqual(ev["weight_profile"], "L4")

    def test_hybrid_and_gates(self):
        sc = self.strong()
        sc["hybrid"] = True
        sc["secondary_layers"] = ["Layer 3 — Cyclical / Event-Driven Opportunity"]
        ev = rl.evaluate_v3(sc)
        self.assertEqual(ev["weight_profile"], "L1+L3")
        self.assertEqual(ev["required_margin_of_safety"], 0.20, "a hybrid takes the stricter requirement")
        sc = self.strong()
        sc["classifications"]["governance"] = "Compromised"
        self.assertEqual(rl.evaluate_v3(sc)["mapped_verdict"], "STRONG AVOID")

    def test_validator_rejects_tampering_and_legacy_still_validates(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            sc = json.loads(json.dumps(TEMPLATE))
            sc["decision"]["conviction"] = "High"
            p = write(tmp / "s.json", json.dumps(sc))
            self.assertFalse(rl.validate_scorecard(p).ok)
            sc = json.loads(json.dumps(TEMPLATE))
            sc["decision_drivers"] = sc["decision_drivers"][:2]
            p = write(tmp / "s.json", json.dumps(sc))
            self.assertFalse(rl.validate_scorecard(p).ok)
            p = write(tmp / "legacy.json", json.dumps(LEGACY))
            self.assertTrue(rl.validate_scorecard(p).ok, "2.x scorecards keep their 2.x rules")
        finally:
            shutil.rmtree(tmp)

    def test_owner_evidence_ceiling(self):
        fx = FixtureRun()
        try:
            write(fx.dir / "qc" / "evidence_stats.json", json.dumps({"by_author": {"moat": {"primary_share": 0.3, "not_located_share": 0.0}}}))
            sc = self.strong()
            out = bs.compute(sc, fx.dir)
            bq1 = next(d for d in out["business_quality"]["dimensions"] if d["id"] == "BQ1")
            self.assertEqual(bq1["confidence"], "Medium")
            self.assertIn("moat", bq1["confidence_note"])
        finally:
            fx.cleanup()

    def test_price_ladder_applies_the_decision_sequence(self):
        sc = self.strong()
        inp = {"price": 100, "horizon_years": 5, "hurdle_rate": 0.12, "intrinsic_value_today": {"low": 140, "high": 160},
               "scenarios": {"bear": {"probability": 0.2, "value_per_share": 120}, "base": {"probability": 0.6, "value_per_share": 260},
                             "bull": {"probability": 0.2, "value_per_share": 400}}}
        lad = vt.price_ladder(inp, [100, 150, 200], rl.evaluate_v3(sc) and sc)
        verdicts = [r["mapped_verdict"] for r in lad["rows"]]
        self.assertIn(verdicts[0], ("BUY", "STRONG BUY"))
        self.assertNotIn(verdicts[-1], ("BUY", "STRONG BUY"), "no buy where the margin of safety is gone")
        self.assertIn("verdict_path", lad["rows"][0])


@unittest.skipUnless(doc_text.tool("pdftotext") and doc_text.tool("pdfinfo"), "poppler not installed")
class TextLayerTest(unittest.TestCase):
    def test_spread_table_and_prose(self):
        fx = FixtureRun()
        try:
            rows = [("Property, plant and equipment", "5", "1,432,724", "1,066,121"), ("Loans", "", "865", "-"),
                    ("Trade receivables", "14", "2,131", "1,805"), ("Total assets", "", "5,143,604", "4,445,310")]
            left = [(40, 60, "Consolidated Balance Sheet")]
            for i, (label, note, a, b) in enumerate(rows):
                y = 100 + 18 * i
                left.append((40, y, label))
                if note:
                    left.append((right(330, note), y, note))
                left.append((right(450, a), y, a))
                left.append((right(550, b), y, b))
            right_half = [(640, 60, "Independent Auditor's Report"), (640, 100, "First paragraph of the opinion."),
                          (640, 118, "Second paragraph follows the first.")]
            pdf = make_pdf(fx.dir / "_cache" / "cio" / "ar.pdf", [(1190, 842, left + right_half), (595, 842, [])])
            out = doc_text.convert(pdf, fx.dir / "_cache" / "text", "test AR")
            meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
            text = (out / "pages.md").read_text(encoding="utf-8")
            p1 = meta["page_index"][0]
            self.assertIn("spread_split", p1["flags"])
            self.assertIn("[L half", text)
            self.assertIn("| Loans |  | 865 | - |", text.replace("|  |  |", "|  |"), "the empty notes cell stays empty")
            self.assertIn("1,432,724 | 1,066,121", text)
            self.assertLess(text.index("First paragraph"), text.index("Second paragraph"))
            self.assertIn("independent_auditors_report", [e["section"] for e in meta["toc"]])
            self.assertTrue(meta["flagged_pages"]["blank_or_graphic"] or meta["flagged_pages"]["image_only"])
            r = subprocess.run([PY, str(ROOT / "scripts" / "doc_text.py"), "verify", str(fx.dir), str(pdf), "1", "1,432,724"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run([PY, str(ROOT / "scripts" / "doc_text.py"), "verify", str(fx.dir), str(pdf), "1", "9,999,999"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
        finally:
            fx.cleanup()


if __name__ == "__main__":
    unittest.main()
