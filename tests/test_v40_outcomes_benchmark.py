"""v4.0: a verdict is judged against the market over its holding period, not only against the hurdle (O2)."""

import datetime as dt
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import outcomes  # noqa: E402


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="eqr-bench-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        rows = []
        for t, ex, verdict in (("UPCO", "NSE", "BUY"), ("SHORTCO", "NSE", "AVOID"), ("USCO", "NASDAQ", "BUY"), ("MIDCO", "NSE", "HOLD")):
            rows.append({c: "" for c in outcomes.DECISION_COLS} | {"run_id": "20251001T000000Z", "ticker": t, "exchange": ex,
                         "as_of_date": "2025-10-01", "price": "100", "verdict": verdict, "hurdle_rate": "0.12"})
        outcomes.write_rows(outcomes.out_dir(self.root) / "decisions.csv", outcomes.DECISION_COLS, rows)
        self.asked = []

    def bench(self, juris, start, end):
        self.asked.append(juris)
        return (0.20, "Nifty 500 TRI") if juris == "IN" else (0.10, "SPY price return (dividends not included)")

    def quote(self, ticker, day):
        return {"close": {"UPCO": 115.0, "SHORTCO": 110.0, "USCO": 125.0, "MIDCO": 130.0}[ticker]}

    def test_a_buy_that_rose_less_than_the_market_lagged_it(self):
        out = outcomes.score(self.root, dt.date(2026, 10, 1), self.quote, self.root / "log.md", self.bench)
        v = {r["ticker"]: r for r in out["verdicts"]}
        self.assertEqual(v["UPCO"]["judged"], "right", "15 % beat the 12 % hurdle")
        self.assertEqual(v["UPCO"]["against_benchmark"], "lagged", "but the market made 20 %")
        self.assertAlmostEqual(v["UPCO"]["excess_return"], -0.05)
        self.assertEqual(v["SHORTCO"]["against_benchmark"], "right", "an AVOID that trailed the market was right")
        self.assertEqual(v["USCO"]["benchmark"], "SPY price return (dividends not included)")
        self.assertEqual(v["USCO"]["against_benchmark"], "beat")
        self.assertTrue(v["MIDCO"]["against_benchmark"].startswith("not judged"))
        self.assertEqual(sorted(set(self.asked)), ["IN", "US"], "each company against its own market")
        self.assertIn("Nifty 500 TRI", (self.root / "log.md").read_text(encoding="utf-8"))

    def test_too_early_is_not_judged_and_no_benchmark_is_invented(self):
        out = outcomes.score(self.root, dt.date(2026, 1, 1), self.quote, self.root / "log.md", self.bench)
        self.assertTrue(all(r["benchmark_return"] is None for r in out["verdicts"]))
        out = outcomes.score(self.root, dt.date(2026, 10, 1), self.quote, self.root / "log.md", lambda j, a, b: None)
        self.assertTrue(all(r["benchmark_return"] is None and r["against_benchmark"] == "" for r in out["verdicts"]))


if __name__ == "__main__":
    unittest.main()
