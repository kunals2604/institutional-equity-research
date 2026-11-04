"""v4.0 Step 8: the funnel — scan (scripts only over the warehouse) and triage (one session, KILL or CONTINUE).

Hermetic: a small warehouse built here. The share-count, bonus and market-value logic was checked first on real
filings and prices (HDFC Bank's 2025 1:1 bonus, Bajaj Finance's 2025 split and bonus).
"""

import csv
import datetime as dt
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_driver as ad  # noqa: E402
import reading_audit as ra  # noqa: E402
import research_lib as rl  # noqa: E402
import scan  # noqa: E402
import triage  # noqa: E402
import warehouse as wh  # noqa: E402

DAY = "2026-10-23"
BONUS = "2026-06-01"


def weekdays(start: str, end: str):
    d, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    while d <= e:
        if d.weekday() < 5:
            yield d.isoformat()
        d += dt.timedelta(days=1)


def fact(con, t, metric, fy, value, known="2026-05-01", basis="consolidated"):
    wh.add_fact(con, t, metric, "FY%d" % fy, basis, value, "INR crore", known, "https://x/%s.xml" % t, "", "1", "xbrl")


def build(con):
    """GOOD: profitable, a 1:1 bonus on BONUS after its last filing. CASHLESS: profit without cash, receivables racing
    ahead, heavy debt. BANKCO: a lender. NIFTYBEES: an ETF."""
    days = list(weekdays("2025-09-01", DAY))
    for sym, isin in (("GOOD", "INE000G01011"), ("CASHLESS", "INE000C01011"), ("BANKCO", "INE000B01011"),
                      ("NIFTYBEES", "INF000N01011")):
        con.execute("INSERT INTO securities VALUES ('NSE',?,?,?,?,?,?,?,?)",
                    (sym, isin, sym, "EQ", "IN", days[0], DAY, wh.isin_kind(isin)))
        prev = None
        for i, d in enumerate(days):
            close = 100.0 + 20.0 * i / len(days)
            if sym == "GOOD" and d >= BONUS:
                close /= 2
            pc = prev if prev is not None else close
            if sym == "GOOD" and d == BONUS:
                pc = prev / 2                         # NSE adjusts the previous close on the ex-date
            con.execute("INSERT INTO prices VALUES ('NSE',?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (sym, d, "EQ", close, close, close, close, pc, 1000, 5e7, 10, None, "u", "s"))
            prev = close
    for y, rev, pat, cfo in ((2023, 1000, 100, 110), (2024, 1100, 115, 120), (2025, 1250, 130, 140), (2026, 1400, 150, 160)):
        k = "%d-05-01" % y                                  # each year known when its results were filed
        fact(con, "GOOD", "revenue", y, rev, k)
        fact(con, "GOOD", "pat", y, pat, k)
        fact(con, "GOOD", "pat_attributable", y, pat, k)
        fact(con, "GOOD", "cfo", y, cfo, k)
        fact(con, "GOOD", "total_equity", y, 600 + 100 * (y - 2023), k)
        fact(con, "GOOD", "trade_receivables", y, 100 + 10 * (y - 2023), k)
        fact(con, "GOOD", "total_debt", y, 50, k)
    for y in (2023, 2026):
        wh.add_fact(con, "GOOD", "shares_outstanding", "FY%d" % y, "consolidated", 1e8, "shares", "%d-05-01" % y, "u", "", "1", "xbrl")
    for y, rev, pat, cfo, rec in ((2024, 900, 90, 5, 100), (2025, 1000, 100, 10, 200), (2026, 1100, 110, 15, 400)):
        fact(con, "CASHLESS", "revenue", y, rev)
        fact(con, "CASHLESS", "pat", y, pat)
        fact(con, "CASHLESS", "pat_attributable", y, pat)
        fact(con, "CASHLESS", "cfo", y, cfo)
        fact(con, "CASHLESS", "trade_receivables", y, rec)
        fact(con, "CASHLESS", "total_equity", y, 300)
        fact(con, "CASHLESS", "total_debt", y, 900)
    wh.add_fact(con, "CASHLESS", "shares_outstanding", "FY2026", "consolidated", 5e7, "shares", "2026-05-01", "u", "", "1", "xbrl")
    for y, ii, pat in ((2023, 500, 50), (2026, 800, 90), (2025, 700, 80)):
        fact(con, "BANKCO", "interest_income", y, ii)
        fact(con, "BANKCO", "pat_attributable", y, pat)
        fact(con, "BANKCO", "total_equity", y, 700)
        fact(con, "BANKCO", "cfo", y, -500)                     # a lender's cash flow says nothing about its earnings
        fact(con, "BANKCO", "advances", y, 5000)
    con.commit()


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-funnel-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.con = wh.connect(self.tmp / "t.sqlite")
        self.addCleanup(self.con.close)
        build(self.con)
        self.rows = {r["symbol"]: r for r in scan.scan(self.con, DAY)}


class ScanTests(Tmp):
    def test_the_universe_is_companies(self):
        self.assertEqual(sorted(self.rows), ["BANKCO", "CASHLESS", "GOOD"])

    def test_market_value_follows_a_bonus_after_the_filing(self):
        g = self.rows["GOOD"]
        self.assertAlmostEqual(g["market_cap_cr"], 2e8 * g["close"] / 1e7, places=6, msg="1e8 shares filed, doubled by the bonus")
        self.assertAlmostEqual(g["earnings_yield"], 150 / g["market_cap_cr"])

    def test_a_bonus_is_not_a_crash_or_a_dilution(self):
        g = self.rows["GOOD"]
        self.assertGreater(g["return_1y"], 0, "the price rose on today's share basis")
        self.assertGreater(g["max_drawdown_1y"], -0.05)
        self.assertEqual(g["flags"], [])

    def test_quality_and_growth(self):
        g = self.rows["GOOD"]
        self.assertAlmostEqual(g["roe"], 150 / ((900 + 800) / 2))
        self.assertAlmostEqual(g["growth_3y"], (1400 / 1000) ** (1 / 3) - 1)

    def test_the_forensic_flags(self):
        flags = self.rows["CASHLESS"]["flags"]
        self.assertIn("cash flow below half of profit (3y)", flags)
        self.assertIn("receivables outgrowing revenue", flags)
        self.assertIn("debt above twice equity", flags)

    def test_a_lender_is_not_held_to_tests_that_do_not_fit_it(self):
        b = self.rows["BANKCO"]
        self.assertTrue(b["lender"])
        self.assertEqual(b["flags"], [])
        self.assertAlmostEqual(b["growth_3y"], (800 / 500) ** (1 / 3) - 1, msg="a lender grows by its interest income")

    def test_the_rank_orders_and_flags_are_never_netted(self):
        ranked = [r["symbol"] for r in scan.scan(self.con, DAY) if r.get("rank_score") is not None]
        self.assertEqual(len(ranked), 3)
        self.assertIn("debt above twice equity", self.rows["CASHLESS"]["flags"])

    def test_a_past_date_sees_only_what_was_known(self):
        rows = {r["symbol"]: r for r in scan.scan(self.con, "2026-04-30")}
        self.assertEqual(rows["GOOD"].get("latest_fy"), "FY2025", "FY2026 was filed on 1 May 2026")

    def test_files_are_written_outside_the_runs(self):
        md = scan.write(scan.scan(self.con, DAY), DAY, "NSE", 10, self.tmp / "scan")
        self.assertTrue((self.tmp / "scan" / ("%s_NSE.csv" % DAY)).exists())
        text = md.read_text(encoding="utf-8")
        self.assertIn("never a decision", text)
        self.assertIn("Survivor-biased", text)


GOOD_SHEET = """# Tear sheet — Good Ltd (GOOD), 2026-10-23

Decision: CONTINUE

## What the company does
It makes widgets ([site](https://good.example/about)).

## The numbers
- Revenue FY2026: 1,400 crore (PACK); profit 150 crore (PACK).
- Order book 2,345 crore (https://good.example/results).

## Red flags
None found in searches of SEBI orders and news.

## What would have to be true
Growth near 12 a year for five more years.

## Why
Clean numbers and a reasonable price; the questions below decide it.

## If CONTINUE: what the full run must answer first
1. Is the growth from price or volume?
2. Who are the customers?
3. Can margins hold?

## Sources opened
- https://good.example/about
- https://good.example/results
"""


class TriageTests(Tmp):
    def setUp(self):
        super().setUp()
        self.dir = triage.prepare(self.con, "GOOD", DAY, home=self.tmp / "triage")

    def write(self, text):
        (self.dir / triage.SHEET).write_text(text, encoding="utf-8")

    def test_prepare_builds_the_pack_from_the_warehouse_as_known(self):
        m = rl.load_json(self.dir / rl.RUN_MANIFEST)
        self.assertEqual((m["kind"], m["ticker"], m["research_cutoff"]), ("triage", "GOOD", DAY))
        pack = (self.dir / "PACK.md").read_text(encoding="utf-8")
        self.assertIn("| revenue |", pack)
        self.assertIn("1,400.00", pack)
        self.assertIn("Survivor-biased", pack)
        self.assertTrue((self.dir / "corpus" / "facts" / "facts.csv").exists())

    def test_a_good_sheet_passes(self):
        self.write(GOOD_SHEET)
        self.assertEqual(triage.errors(self.dir), [])

    def test_the_decision_is_required(self):
        self.write(GOOD_SHEET.replace("Decision: CONTINUE", "Verdict: maybe"))
        self.assertTrue(any("Decision: KILL" in e for e in triage.errors(self.dir)))

    def test_continue_needs_the_questions(self):
        self.write(GOOD_SHEET.split("## If CONTINUE")[0] + "## Sources opened\n- https://good.example/about\n- https://good.example/results\n")
        self.assertTrue(any("3 to 5 numbered questions" in e for e in triage.errors(self.dir)))

    def test_a_figure_from_nowhere_is_caught(self):
        self.write(GOOD_SHEET.replace("profit 150 crore (PACK)", "profit 175 crore (PACK)"))
        self.assertTrue(any("`175`" in e for e in triage.errors(self.dir)))

    def test_every_cited_url_is_listed(self):
        self.write(GOOD_SHEET.replace("- https://good.example/results\n", ""))
        self.assertTrue(any("Sources opened" in e for e in triage.errors(self.dir)))

    def test_kill_needs_no_questions_but_a_reason(self):
        sheet = GOOD_SHEET.replace("Decision: CONTINUE", "Decision: KILL").split("## If CONTINUE")[0] + \
            "## Sources opened\n- https://good.example/about\n- https://good.example/results\n"
        self.write(sheet)
        self.assertEqual(triage.errors(self.dir), [])
        self.write(sheet.replace("Clean numbers and a reasonable price; the questions below decide it.", ""))
        self.assertTrue(any("say why" in e for e in triage.errors(self.dir)))

    def test_record_logs_a_passing_sheet_and_refuses_a_failing_one(self):
        self.write(GOOD_SHEET.replace("Decision: CONTINUE", "Decision: maybe"))
        with self.assertRaises(SystemExit):
            triage.record(self.dir, home=self.tmp / "triage")
        self.write(GOOD_SHEET)
        row = triage.record(self.dir, home=self.tmp / "triage")
        self.assertEqual((row["symbol"], row["decision"]), ("GOOD", "CONTINUE"))
        with (self.tmp / "triage" / "TRIAGE_LOG.csv").open(encoding="utf-8") as f:
            self.assertEqual([r["decision"] for r in csv.DictReader(f)], ["CONTINUE"])


class EngineTests(Tmp):
    def test_the_triage_session_writes_only_its_sheet_and_reads_no_run(self):
        d = triage.prepare(self.con, "GOOD", DAY, home=self.tmp / "triage")
        asg = ad.triage_assignment(d, "p")
        self.assertEqual((asg.model, asg.effort), ("opus", "high"))
        writes = [r for r in asg.allowed if r.startswith(("Write(", "Edit("))]
        self.assertTrue(writes and all(r.endswith("TEAR_SHEET.md)") for r in writes))
        self.assertTrue(any(r.endswith("research/warehouse/**)") for r in asg.denied))
        self.assertIn("Bash(python3 scripts/triage.py record:*)", asg.denied)
        self.assertFalse(any(r.endswith("/research/funnel/**)") for r in asg.denied), "it reads its own pack")
        self.assertTrue(asg.check(), "no sheet yet")

    def test_specialists_are_denied_the_funnel_and_the_audit_flags_it(self):
        run = self.tmp / "run"
        run.mkdir()
        self.assertTrue(any(r.endswith("/research/funnel/**)") for r in ad.independence_denies(run, "moat")))
        calls, _ = ra.independence_patterns("moat", "R")
        for cmd in ("cat research/funnel/scan/2026-10-23_NSE.csv", "python3 scripts/scan.py run --date 2026-10-23",
                    "python3 scripts/triage.py prepare GOOD"):
            self.assertIsNotNone(calls.search(cmd), cmd)

    def test_triage_is_pinned_and_registered(self):
        self.assertIn("triage", rl.WORKERS)
        self.assertEqual(rl.model_policy()["agents"]["triage"], {"model": "opus", "effort": "high", "kind": "worker"})


if __name__ == "__main__":
    unittest.main()
