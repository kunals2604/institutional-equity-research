"""Defect group A: wrong numbers must not pass (docs/V4_DEFECT_REGISTER.md).

Each test states the failure it guards against. In web-digest mode, the default, these are the checks that stand between
a third-party summary and a number the report treats as a fact.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_driver as ad  # noqa: E402
import digest  # noqa: E402
import reading_audit as ra  # noqa: E402
import research_lib as rl  # noqa: E402
import verify  # noqa: E402


class FakeSeen:
    """What claim_checks reads from a session, with every source opened unless a test says otherwise."""

    def __init__(self, text="", opened=True):
        self.digits = verify.digit_set(text)
        self.numbers = verify.exact_set(text)
        self._opened = opened

    def viewed(self, keys):
        return False

    def opened(self, keys):
        return self._opened

    def anchored(self, keys):
        return False


def claim(value="1,000", source="https://example.com/ar.pdf", tag="FACT", cid="FIN-C001", unit=""):
    return {"claim_id": cid, "tag": tag, "value": value, "source_url_or_id": source, "locator": "", "unit": unit}


def checks(rows, seen):
    return {f["check"]: f for f in verify.claim_checks(rows, seen, {}, "financials")}


class DigestAmountTests(unittest.TestCase):
    """A1: 2,500 crore in a summary must never confirm against 25,000 in the filing."""

    def test_a_ten_times_difference_does_not_match(self):
        self.assertFalse(digest.amount_in("Revenue stood at 25,000 crore", "2500"))
        self.assertFalse(digest.amount_in("was 250", "25000"))
        self.assertFalse(digest.amount_in("was 10", "100"))

    def test_the_same_number_in_any_print_form_matches(self):
        self.assertTrue(digest.amount_in("Revenue stood at 25,000 crore", "25,000"))
        self.assertTrue(digest.amount_in("Revenue stood at 25000 crore", "25,000"))
        self.assertTrue(digest.amount_in("Total 2,50,000", "250000"))
        self.assertTrue(digest.amount_in("margin of 12.50 %", "12.5"))
        self.assertTrue(digest.amount_in("margin of 12.5 %", "12.50"))

    def test_a_value_with_no_digits_is_not_a_mismatch(self):
        self.assertTrue(digest.amount_in("anything", "n/a"))

    def test_a_scale_only_match_is_recognised_separately(self):
        self.assertTrue(digest.scaled_amount_in("Revenue stood at 25,000 crore", "2500"))
        self.assertFalse(digest.scaled_amount_in("Revenue stood at 26,000 crore", "2500"))


class DigestConfirmTests(unittest.TestCase):
    """A1 and A7, end to end through the function that assigns a confirmation."""

    def spec(self):
        return {"amounts": ["amount"], "label": ["label"]}

    def confirm(self, pages, amount="2500", label="Revenue from operations"):
        return digest.confirm_item({"fields": {"amount": amount, "label": label}}, self.spec(), pages)

    def test_a_scale_error_is_a_conflict_not_a_confirmation(self):
        got = self.confirm({12: ["Revenue from operations 25,000"]})
        self.assertEqual(got["status"], "conflict")
        self.assertTrue(got.get("scale_differs"))

    def test_the_right_number_beside_its_label_is_confirmed(self):
        self.assertEqual(self.confirm({12: ["Revenue from operations 2,500"]})["status"], "page_confirmed")

    def test_a_different_number_beside_the_label_is_a_plain_conflict(self):
        got = self.confirm({12: ["Revenue from operations 3,100"]})
        self.assertEqual(got["status"], "conflict")
        self.assertFalse(got.get("scale_differs"))

    def test_two_facts_from_one_quote_have_different_ids(self):
        base = {"type": "metric", "source_url": "https://x.example/a", "snapshot_page": 1, "quote": "Revenue 10, profit 2"}
        a = digest.item_id("AR-FY2024", dict(base, fields={"label": "Revenue", "amount": "10"}))
        b = digest.item_id("AR-FY2024", dict(base, fields={"label": "Profit", "amount": "2"}))
        self.assertNotEqual(a, b)


class ExactNumberTests(unittest.TestCase):
    """A2: digits alone cannot tell 2,500 from 25,000."""

    def test_exact_values_keep_their_magnitude(self):
        self.assertEqual(verify.exact_set("1,234.50 and 25,000"), {"1234.5", "25000"})
        self.assertNotEqual(verify.exact_set("2,500"), verify.exact_set("25,000"))

    def test_a_scale_only_match_is_a_major_finding(self):
        got = checks([claim("2,500")], FakeSeen("Revenue was 25,000"))
        self.assertNotIn("NUMBER_NOT_SEEN", got)
        self.assertEqual(got["SCALE_NOT_SEEN"]["severity"], "major")
        self.assertIn("FIN-C001", got["SCALE_NOT_SEEN"]["claims"][0])

    def test_the_exact_number_raises_nothing(self):
        self.assertEqual(checks([claim("2,500")], FakeSeen("Revenue was 2,500")), {})

    def test_a_number_never_seen_at_any_scale_still_blocks(self):
        got = checks([claim("7,301")], FakeSeen("Revenue was 25,000"))
        self.assertEqual(got["NUMBER_NOT_SEEN"]["severity"], "blocking")

    def test_a_value_holding_several_numbers_is_left_to_the_digit_check(self):
        self.assertNotIn("SCALE_NOT_SEEN", checks([claim("12 to 15")], FakeSeen("12 15 1215")))


class DigestLaunderingTests(unittest.TestCase):
    """A3: a digest number must not reach a FACT by any spelling of its source."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-laundry-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        items = self.tmp / rl.DIGEST_DIR / "items"
        items.mkdir(parents=True)
        (items / "ar.jsonl").write_text(json.dumps(
            {"source_url": "https://news.example.com/airtel-ar-summary", "snapshot": "_cache/digest/a.pdf"}) + "\n",
            encoding="utf-8")

    def hits(self, source, locator=""):
        return verify.digest_fact_findings(self.tmp, [dict(claim(source=source), locator=locator)], "financials")

    def test_every_spelling_of_a_digest_url_is_caught(self):
        for src in ("https://news.example.com/airtel-ar-summary", "http://www.news.example.com/airtel-ar-summary/",
                    "https://news.example.com/airtel-ar-summary?utm_source=x", "https://NEWS.example.com/airtel-ar-summary#top"):
            self.assertTrue(self.hits(src), src)

    def test_a_digest_item_id_or_pack_path_is_caught(self):
        self.assertTrue(self.hits("D-0123456789"))
        self.assertTrue(self.hits("https://www.bseindia.com/x.pdf", "digest item D-0123456789"))
        self.assertTrue(self.hits("corpus/digest/packs/financials.md"))

    def test_a_filing_is_not_caught(self):
        self.assertEqual(self.hits("https://www.bseindia.com/x.pdf", "PDF page 12"), [])

    def test_a_number_seen_only_in_a_digest_pack_does_not_count_as_seen(self):
        pack = {"name": "Read", "id": "t1", "input": {"file_path": "corpus/digest/packs/financials.md"}}
        filing = {"name": "Read", "id": "t2", "input": {"file_path": "corpus/text/ar.txt"}}
        entries = [
            {"type": "assistant", "message": {"content": [dict(pack, type="tool_use"), dict(filing, type="tool_use")]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "digest says 7,301"},
                {"type": "tool_result", "tool_use_id": "t2", "content": "the filing says 2,500"}]}}]
        seen = verify.Seen([{"entries": entries}])
        self.assertNotIn("7301", seen.digits)
        self.assertIn("25", seen.digits)
        self.assertNotIn("7301", seen.numbers)


class ProseSourceTests(unittest.TestCase):
    """A4: a FACT nobody can open is not a FACT."""

    def test_a_prose_source_blocks(self):
        got = checks([claim(source="BSE filing, Jan 2024", value="")], FakeSeen())
        self.assertEqual(got["SOURCE_UNCHECKABLE"]["severity"], "blocking")

    def test_a_claim_id_as_source_blocks(self):
        self.assertIn("SOURCE_UNCHECKABLE", checks([claim(source="FIN-C012", value="")], FakeSeen()))

    def test_a_url_and_a_file_do_not(self):
        rows = [claim(value=""), claim(source="corpus/text/ar.txt", value="", cid="FIN-C002")]
        self.assertNotIn("SOURCE_UNCHECKABLE", checks(rows, FakeSeen()))

    def test_an_estimate_is_not_held_to_it(self):
        self.assertNotIn("SOURCE_UNCHECKABLE", checks([claim(source="our judgment", value="", tag="ESTIMATE")], FakeSeen()))


class WaiverTests(unittest.TestCase):
    """A5 and A6: a waiver covers what it was given for, and only the CIO gives it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-waive-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / rl.RUN_MANIFEST).write_text(json.dumps({"run_id": "R"}), encoding="utf-8")

    def record(self, claims):
        f = verify.finding("NUMBER_NOT_SEEN", "financials", "values", "fix", claims)
        return verify.merge_record(self.tmp, "financials", [f], 10, 1)

    def test_a_waiver_stays_on_the_claims_it_named(self):
        self.record(["FIN-C001 (value 1)"])
        verify.waive(self.tmp, "financials-NUMBER_NOT_SEEN", "printed in an image")
        rec = self.record(["FIN-C001 (value 1)"])
        self.assertTrue(rec["tier_a"][0].get("waived"))
        self.assertEqual(verify.open_findings(rec), [])

    def test_a_later_claim_under_the_same_check_stays_open(self):
        self.record(["FIN-C001 (value 1)"])
        verify.waive(self.tmp, "financials-NUMBER_NOT_SEEN", "printed in an image")
        rec = self.record(["FIN-C001 (value 1)", "FIN-C002 (value 2)"])
        self.assertFalse(rec["tier_a"][0].get("waived"))
        self.assertEqual(rec["tier_a"][0]["claims"], ["FIN-C002 (value 2)"])

    def test_a_waiver_records_who_gave_it_and_what_it_covered(self):
        self.record(["FIN-C001 (value 1)"])
        verify.waive(self.tmp, "financials-NUMBER_NOT_SEEN", "printed in an image")
        entry = rl.load_json(self.tmp / "qc" / "verification" / "financials.json")["waived"]["financials-NUMBER_NOT_SEEN"]
        self.assertEqual(entry["by"], "cio")
        self.assertEqual(entry["claims"], ["FIN-C001 (value 1)"])

    def test_an_older_waiver_with_no_claim_list_keeps_its_meaning(self):
        f = verify.finding("NUMBER_NOT_SEEN", "financials", "values", "fix", ["FIN-C009 (value 9)"])
        verify.apply_waiver(f, {"reason": "old", "at": "x"})
        self.assertTrue(f.get("waived"))

    def test_agents_are_denied_the_waive_command(self):
        self.assertIn("Bash(python3 scripts/verify.py waive:*)", ad.shell_denies())

    def test_the_audit_flags_a_specialist_that_waives(self):
        calls, _ = ra.independence_patterns("moat", "R")
        self.assertIsNotNone(calls.search("python3 ./scripts/verify.py waive RUN moat-NUMBER_NOT_SEEN --reason x"))


if __name__ == "__main__":
    unittest.main()
