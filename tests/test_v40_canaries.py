"""Step 5: known-false claims among the checkers' samples. A measured catch rate for every run, and nothing in the evidence."""

import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import agent_driver as ad  # noqa: E402
import audit_tools  # noqa: E402
import research_lib as rl  # noqa: E402
import verify  # noqa: E402
from test_v40_orchestrate import new_run  # noqa: E402

COLS = rl.ledger_columns()


class CanaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-canary-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_with_ledger(self, *flags):
        run = new_run(self.tmp, *flags)
        with (run / "specialists" / "filings_ledger.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
            w.writeheader()
            for i in range(1, 11):
                w.writerow({"claim_id": "FIL-C%03d" % i, "tag": "FACT", "claim": "Revenue was %d,000 crore" % (10 + i), "value": "%d,000" % (10 + i),
                            "unit": "INR crore", "source_url_or_id": "https://x.example/ar.pdf", "locator": "PDF page %d" % i})
        (run / "specialists" / "filings.md").write_text("## Domain Conclusion\nx [FACT: FIL-C001]\n", encoding="utf-8")
        return run

    def planted(self, run):
        return json.loads(verify.canary_path(run, "filings").read_text(encoding="utf-8"))

    def answer(self, run, result_for_canary, write=True):
        sample = run / "qc" / "verification" / "filings_sample.csv"
        ids = [r["claim_id"] for r in csv.DictReader(sample.open(encoding="utf-8", newline=""))]
        canary = self.planted(run)["claims"][0]
        with (run / "qc" / "verification" / "filings_claims.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["claim_id", "result", "evidence", "source_opened", "note"])
            w.writeheader()
            for c in ids:
                w.writerow({"claim_id": c, "result": result_for_canary if c == canary else "Confirmed", "evidence": "the page differs",
                            "source_opened": "ar.pdf"})
        return verify.claims_result(run, "filings", write=write)

    def test_a_sample_carries_one_false_claim_with_an_id_no_ledger_holds(self):
        run = self.run_with_ledger()
        rows = verify.sample(run, "filings")
        ids = {r["claim_id"] for r in verify.ledger_rows(verify.ledgers_of(run, "filings"))}
        extra = [r for r in rows if r["claim_id"] not in ids]
        self.assertEqual(len(extra), 1)
        self.assertEqual(extra[0]["claim_id"], self.planted(run)["claims"][0])

    def test_the_false_value_is_materially_wrong_in_its_printed_form(self):
        run = self.run_with_ledger()
        rows = verify.sample(run, "filings")
        canary = next(r for r in rows if r["claim_id"] == self.planted(run)["claims"][0])
        true = float(self.planted(run)["true_value"].replace(",", ""))
        false = float(canary["value"].replace(",", ""))
        self.assertGreater(abs(false - true) / true, 0.2)
        self.assertIn(",", canary["value"])
        self.assertIn(canary["value"], canary["claim"])

    def test_it_looks_like_any_other_row(self):
        run = self.run_with_ledger()
        rows = verify.sample(run, "filings")
        canary = next(r for r in rows if r["claim_id"] == self.planted(run)["claims"][0])
        self.assertEqual(canary["source_url_or_id"], "https://x.example/ar.pdf")
        self.assertRegex(canary["claim_id"], r"^FIL-C\d{4}$")

    def test_a_caught_canary_scores_and_raises_no_finding(self):
        run = self.run_with_ledger()
        verify.sample(run, "filings")
        rec, errs = self.answer(run, "Material discrepancy")
        self.assertEqual(errs, [])
        self.assertEqual(rec["canaries"], {"planted": 1, "caught": 1})
        self.assertEqual(rec["findings"], [])

    def test_a_missed_canary_scores_zero(self):
        run = self.run_with_ledger()
        verify.sample(run, "filings")
        rec, _ = self.answer(run, "Confirmed")
        self.assertEqual(rec["canaries"], {"planted": 1, "caught": 0})

    def test_it_never_counts_as_a_sampled_claim(self):
        run = self.run_with_ledger()
        rows = verify.sample(run, "filings")
        rec, _ = self.answer(run, "Material discrepancy")
        self.assertEqual(rec["sampled"], len(rows) - 1)
        self.assertNotIn(self.planted(run)["claims"][0], rec["claims"])

    def test_a_run_with_canaries_off_has_none(self):
        run = self.run_with_ledger("--set", "canaries=off")
        verify.sample(run, "filings")
        self.assertFalse(verify.canary_path(run, "filings").exists())

    def test_no_agent_may_read_the_list(self):
        run = self.run_with_ledger()
        rules = ad.verifier_assignment(run, "filings", "x").denied + ad.independence_denies(run, "filings")
        self.assertTrue(any("_cache/engine" in r for r in rules))
        self.assertIn("_cache/engine", str(verify.canary_path(run, "filings")))

    def test_the_auditor_sample_carries_them_and_is_scored(self):
        run = self.run_with_ledger()
        rl.update_json(run / rl.RUN_MANIFEST, lambda m: m)
        (run / "evidence_ledger.csv").write_text((run / "specialists" / "filings_ledger.csv").read_text(encoding="utf-8"), encoding="utf-8")
        out = run / "audit" / "sample.csv"
        audit_tools.sample(run, 8, "seed", out)
        planted = set(json.loads(verify.canary_path(run, "auditor").read_text(encoding="utf-8"))["claims"])
        self.assertEqual(len(planted), 2)
        rows = list(csv.DictReader(out.open(encoding="utf-8", newline="")))
        self.assertTrue(planted <= {r["claim_id"] for r in rows})
        for r in rows:
            r["result"] = "Material discrepancy" if r["claim_id"] in planted else "Confirmed"
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        self.assertEqual(verify.audit_canaries(run), {"planted": 2, "caught": 2})

    def test_the_rate_adds_up_across_checkers(self):
        per = {"a": {"tier_b": {"canaries": {"planted": 1, "caught": 1}}}, "b": {"tier_b": {"canaries": {"planted": 1, "caught": 0}}}}
        self.assertEqual(verify.canary_score(per), {"planted": 2, "caught": 1, "rate": 0.5})

    def test_no_canaries_means_no_rate_not_a_perfect_one(self):
        self.assertIsNone(verify.canary_score({})["rate"])


if __name__ == "__main__":
    unittest.main()
