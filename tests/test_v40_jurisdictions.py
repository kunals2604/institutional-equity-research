"""v4.0 Step 9: jurisdictions, and the US path tested on stored real data.

tests/fixtures/edgar/ holds trimmed copies of what SEC EDGAR, Nasdaq and the Treasury served on 2026-11-04 for Apple
(CIK 320193): its submissions, its XBRL company facts (annual 10-K values from FY2018 filings on, and cover-page share
counts), 300 daily closes and the 2026 par yield curve. Figures checked against Apple's published results: FY2024
revenue 391,035 and net income 93,736 (USD million).
"""

import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_driver as ad  # noqa: E402
import edgar  # noqa: E402
import jurisdiction  # noqa: E402
import new_run  # noqa: E402
import orchestrate as oc  # noqa: E402
import research_lib as rl  # noqa: E402
import scan  # noqa: E402
import triage  # noqa: E402
import warehouse as wh  # noqa: E402

FX = ROOT / "tests" / "fixtures" / "edgar"
FACTS = json.loads((FX / "CIK0000320193_companyfacts.json").read_text(encoding="utf-8"))
SUBS = json.loads((FX / "CIK0000320193_submissions.json").read_text(encoding="utf-8"))


class JurisdictionTests(unittest.TestCase):
    def test_every_exchange_has_one_jurisdiction(self):
        self.assertEqual([jurisdiction.for_exchange(x) for x in ("NSE", "BSE", "NSE-SME", "NYSE", "NASDAQ")],
                         ["IN", "IN", "IN", "US", "US"])
        with self.assertRaises(ValueError):
            jurisdiction.for_exchange("XETRA")

    def test_a_run_without_the_field_is_indian(self):
        self.assertEqual(jurisdiction.of_manifest({}), "IN")

    def test_india_needs_no_translation_and_the_us_gets_one(self):
        self.assertEqual(jurisdiction.brief_text("IN"), "")
        text = jurisdiction.brief_text("US")
        for word in ("controlling shareholder", "SEC", "PCAOB", "US GAAP", "10-K", "DEF 14A", "USD million", "price return"):
            self.assertIn(word, text)

    def test_both_files_say_the_same_things(self):
        a, b = jurisdiction.load("IN"), jurisdiction.load("US")
        self.assertEqual(set(a) - {"user_agent"}, set(b) - {"user_agent"})
        self.assertEqual(set(a["filings"]), set(b["filings"]))
        self.assertEqual(set(a["vocabulary"]), set(b["vocabulary"]))


class NewRunTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="eqr-juris-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def make(self, exchange, ticker, *extra):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = new_run.main(["--ticker", ticker, "--company", "%s Inc." % ticker, "--exchange", exchange, "--segment", "main",
                               "--cutoff", "2026-11-04", "--run-id", "20261104T140000Z", "--root", str(self.root)] + list(extra))
        self.assertEqual(rc, 0)
        return self.root / out.getvalue().strip()

    def test_a_us_run_takes_its_defaults_from_its_jurisdiction(self):
        m = rl.load_json(self.make("NASDAQ", "AAPL") / rl.RUN_MANIFEST)
        self.assertEqual((m["jurisdiction"], m["currency"], m["fiscal_year_end"]), ("US", "USD", "12-31"))

    def test_an_indian_run_is_as_before(self):
        m = rl.load_json(self.make("NSE", "TVSMOTOR") / rl.RUN_MANIFEST)
        self.assertEqual((m["jurisdiction"], m["currency"], m["fiscal_year_end"]), ("IN", "INR", "03-31"))

    def test_given_values_win(self):
        m = rl.load_json(self.make("NASDAQ", "AAPL", "--fy-end", "09-30") / rl.RUN_MANIFEST)
        self.assertEqual(m["fiscal_year_end"], "09-30")

    def test_the_brief_carries_the_translation_for_a_us_run_only(self):
        us = self.make("NASDAQ", "AAPL")
        rl.update_json(us / rl.RUN_MANIFEST, lambda m: m.update(sector_modules=[]))
        (us / "engine").mkdir(exist_ok=True)
        (us / "engine" / "identity.md").write_text("Apple Inc.", encoding="utf-8")
        self.assertIn("JURISDICTION: United States", ad.specialist_prompt(us, "financials"))
        self.assertNotIn("{{JURISDICTION}}", ad.specialist_prompt(us, "financials"))

    def test_a_us_run_needs_no_indian_structured_filings(self):
        us = self.make("NASDAQ", "AAPL")
        (us / "corpus" / "DOCUMENT_MAP.md").write_text("map", encoding="utf-8")
        self.assertTrue(oc.CHECKS["document_map_built"](us))
        rl.update_json(us / rl.RUN_MANIFEST, lambda m: m.update(jurisdiction="IN"))
        self.assertFalse(oc.CHECKS["document_map_built"](us), "an Indian run still needs corpus/STRUCTURED.md")


class EdgarFactsTests(unittest.TestCase):
    def setUp(self):
        self.rows, self.problems = edgar.latest(edgar.annual_values(FACTS, 9))
        self.by = {(r["item"], r["period"]): r for r in self.rows}

    def test_the_figures_tie_to_apples_published_results(self):
        self.assertEqual(self.by[("revenue", "FY2024")]["value"], 391035.0)
        self.assertEqual(self.by[("pat_attributable", "FY2024")]["value"], 93736.0)
        self.assertEqual(self.by[("cfo", "FY2024")]["value"], 118254.0)
        self.assertEqual(self.by[("capex", "FY2024")]["value"], 9447.0)
        self.assertEqual(self.by[("revenue", "FY2024")]["unit"], "USD million")

    def test_a_concept_renamed_over_the_years_is_one_series(self):
        self.assertIn(("revenue", "FY2017"), self.by, "SalesRevenueNet before 2018")
        self.assertIn(("revenue", "FY2025"), self.by, "RevenueFromContractWithCustomerExcludingAssessedTax after")

    def test_a_split_is_a_recorded_restatement_and_the_latest_filing_wins(self):
        self.assertTrue(any("shares_diluted FY2019" in p for p in self.problems))
        self.assertGreater(self.by[("shares_diluted", "FY2019")]["value"], 1.5e10, "restated for the 2020 4-for-1 split")

    def test_every_value_keeps_its_filing_and_date(self):
        r = self.by[("revenue", "FY2024")]
        self.assertTrue(r["source_url_or_id"].startswith("https://www.sec.gov/Archives/edgar/data/320193/"))
        self.assertIn("filed", r["locator"])
        self.assertTrue(r["filed"].startswith("20"))

    def test_a_cutoff_hides_what_was_filed_later(self):
        rows, _ = edgar.latest(edgar.annual_values(FACTS, 9, cutoff="2025-01-01"))
        self.assertNotIn(("revenue", "FY2025"), {(r["item"], r["period"]) for r in rows})

    def test_a_52_53_week_year_is_labelled_by_its_fiscal_year(self):
        import datetime as dt
        self.assertEqual(edgar.fiscal_year(dt.date(2022, 10, 1), 9), 2022)
        self.assertEqual(edgar.fiscal_year(dt.date(2024, 9, 28), 9), 2024)
        self.assertEqual(edgar.fiscal_year(dt.date(2026, 1, 2), 12), 2025)

    def test_facts_land_where_an_indian_runs_do(self):
        root = Path(tempfile.mkdtemp(prefix="eqr-edgar-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        rl.write_json(root / rl.RUN_MANIFEST, {"run_id": "R", "fiscal_year_end": "09-30", "research_cutoff": "2026-11-04"})
        out, _ = edgar.write_facts(root, FACTS)
        self.assertEqual(out, root / "calc" / "xbrl_facts.csv")
        with out.open(encoding="utf-8") as f:
            r = list(csv.DictReader(f))
        self.assertEqual(list(r[0]), edgar.COLUMNS)


class EdgarIndexTests(unittest.TestCase):
    def test_forms_become_the_index_types_the_document_map_knows(self):
        rows = edgar.filing_rows(SUBS, 15, "2026-11-04", 9)
        types = {r["doc_type"] for r in rows}
        self.assertTrue({"annual_report", "results", "insider_sast"} <= types)
        ar = [r for r in rows if r["doc_type"] == "annual_report"]
        self.assertEqual(ar[0]["fiscal_period"], "FY2026")
        self.assertTrue(ar[0]["url"].endswith(".htm"))

    def test_8k_items_decide_the_type(self):
        self.assertEqual(edgar.doc_type("8-K", "2.02,9.01"), "results")
        self.assertEqual(edgar.doc_type("8-K", "5.07"), "voting_results")
        self.assertEqual(edgar.doc_type("8-K", "4.01"), "auditor")
        self.assertEqual(edgar.doc_type("DEF 14A", ""), "agm_egm")
        self.assertEqual(edgar.doc_type("10-K", ""), "annual_report")

    def test_www_sec_gov_is_refused_without_a_declared_agent(self):
        import os
        old = os.environ.pop("EQUITY_RESEARCH_USER_AGENT", None)
        self.addCleanup(lambda: old is not None and os.environ.__setitem__("EQUITY_RESEARCH_USER_AGENT", old))
        with self.assertRaises(SystemExit) as cm:
            edgar.need_declared(edgar.TICKERS)
        self.assertIn("EQUITY_RESEARCH_USER_AGENT", str(cm.exception))
        edgar.need_declared(edgar.FACTS % 320193)       # data.sec.gov answers anyone (measured)


class UsPricesAndRatesTests(unittest.TestCase):
    def test_nasdaq_rows(self):
        rows = edgar.parse_nasdaq(json.loads((FX / "nasdaq_AAPL.json").read_text(encoding="utf-8")))
        self.assertEqual(len(rows), 300)
        self.assertEqual(rows[-1], {"date": "2026-11-03", "open": 325.58, "high": 334.5, "low": 325.33, "close": 331.9,
                                    "volume": 63160030.0})
        self.assertLess(rows[0]["date"], rows[-1]["date"])

    def test_treasury(self):
        series = edgar.parse_treasury((FX / "treasury_2026.csv").read_text(encoding="utf-8"))
        self.assertEqual(series["2026-11-03"], 4.95)


class UsWarehouseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-uswh-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.con = wh.connect(self.tmp / "t.sqlite")
        self.addCleanup(self.con.close)
        wh.ingest_edgar(self.con, "AAPL", FACTS, 9)
        wh.ingest_us_prices(self.con, "AAPL", edgar.parse_nasdaq(json.loads((FX / "nasdaq_AAPL.json").read_text(encoding="utf-8"))), "fx")

    def test_us_facts_are_kept_apart_from_indian_symbols(self):
        self.assertEqual({t for (t,) in self.con.execute("SELECT DISTINCT ticker FROM facts")}, {"AAPL.US"})
        self.assertEqual(wh.key("AAPL", "US"), "AAPL.US")
        self.assertEqual(wh.key("BHARTIARTL", "IN"), "BHARTIARTL")

    def test_every_filing_is_a_version(self):
        got = self.con.execute("SELECT COUNT(DISTINCT known_at) FROM facts WHERE metric = 'revenue' AND period = 'FY2024'").fetchone()[0]
        self.assertGreaterEqual(got, 2, "the FY2024 figure was filed in the FY2024 10-K and again as a comparative")

    def test_a_us_scan_uses_the_cover_share_count(self):
        rows = {r["symbol"]: r for r in scan.scan(self.con, "2026-11-03", "US")}
        a = rows["AAPL"]
        self.assertAlmostEqual(a["market_cap"] * 1e6, 14532182000 * 331.9, delta=1e3, msg="USD million, the facts' unit")
        self.assertEqual(a["latest_fy"], "FY2026")
        self.assertAlmostEqual(a["earnings_yield"], 132175.0 * 1e6 / (14532182000 * 331.9), places=6)

    def test_a_us_triage_pack(self):
        d = triage.prepare(self.con, "AAPL", "2026-11-03", "US", "Apple Inc.", home=self.tmp / "triage")
        pack = (d / "PACK.md").read_text(encoding="utf-8")
        self.assertIn("USD million", pack)
        self.assertIn("391,035.00", pack)
        self.assertEqual(rl.load_json(d / rl.RUN_MANIFEST)["jurisdiction"], "US")


if __name__ == "__main__":
    unittest.main()
