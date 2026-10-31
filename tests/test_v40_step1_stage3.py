"""Defect group B: evidence must not be lost in Stage 3 (docs/V4_DEFECT_REGISTER.md)."""

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import golden_tools as gt  # noqa: E402
import research_lib as rl  # noqa: E402
import synthesis  # noqa: E402

LABELS = ROOT / "tests" / "golden" / "gating_labels.csv"
GOOD_ENTRY = """# Master Contradiction Log

## X-01 — which liquidity cover is right (CC-T1-1)
- **Specialist positions:** financials 0.86x; valuation 1.1x [FACT: FIN-C041]
- **Evidence for each:** the maturity note
- **Contrary evidence:** none
- **Assumptions required:** none
- **Independent check (CIO):** recomputed from the note [CALCULATION: CIO-C014]
- **Resolution:** 0.86x stands
- **Confidence:** High — primary source
- **Investment impact:** BQ4

## X-02 — next
- **Resolution:** Unresolved
"""


class GatingTests(unittest.TestCase):
    """B14: gating means a real red flag, not a keyword or a dimension."""

    @classmethod
    def setUpClass(cls):
        tmp = Path(tempfile.mkdtemp(prefix="eqr-gating-"))
        cls.items = gt.registry_items(gt.scratch_copy(tmp))
        shutil.rmtree(tmp, ignore_errors=True)
        with LABELS.open(encoding="utf-8", newline="") as f:
            cls.labels = {r["text_sha1"]: r for r in csv.DictReader(f)}

    def label(self, item):
        return self.labels.get(hashlib.sha1(item["text"].encode()).hexdigest()[:12], {}).get("label")

    def test_every_real_red_flag_of_the_real_run_stays_gating(self):
        required = [i for i in self.items if self.label(i) == "required"]
        self.assertEqual(len(required), 11)
        self.assertEqual([i["text"][:80] for i in required if i["materiality"] != "gating"], [])

    def test_the_three_known_dropped_findings_are_gating(self):
        gating = "\n".join(i["text"] for i in self.items if i["materiality"] == "gating")
        for needle in ("0.86", "Payments Bank"):
            self.assertIn(needle, gating)
        self.assertRegex(gating.lower(), "emphasis of matter|eoms?")

    def test_the_gating_count_is_a_reviewable_number(self):
        n = sum(i["materiality"] == "gating" for i in self.items)
        self.assertLessEqual(n, 30)
        self.assertGreaterEqual(n, 11)

    def test_almost_no_labelled_noise_stays_gating(self):
        noise = [i["text"][:70] for i in self.items if i["materiality"] == "gating" and self.label(i) == "noise"]
        self.assertLessEqual(len(noise), 3, noise)


class RedFlagTests(unittest.TestCase):
    rules = staticmethod(synthesis.materiality_rules)

    def flag(self, text):
        return synthesis.red_flag(text, self.rules())

    def test_a_negated_sentence_is_not_a_red_flag(self):
        self.assertFalse(self.flag("Short-seller, SEBI and fraud searches found nothing material."))
        self.assertFalse(self.flag("Liquidity is not a constraint; there is no liquidity gap."))
        self.assertFalse(self.flag("No going concern doubt was raised."))

    def test_a_clear_sentence_after_a_negated_one_still_counts(self):
        self.assertTrue(self.flag("No other issue arose. RBI imposed a penalty for KYC breaches."))

    def test_with_or_without_is_not_a_negation(self):
        self.assertTrue(self.flag("The route to a permanent loss is a price war, with or without an FX shock."))

    def test_words_inside_other_words_do_not_fire(self):
        self.assertFalse(self.flag("Confirm the cost of equity with the default-spread adjustment."))
        self.assertFalse(self.flag("The stake changes the minority leakage maths."))
        self.assertFalse(self.flag("FY2019 revenue was restated for discontinued operations."))

    def test_real_events_fire(self):
        for text in ("The auditor resigned mid-year.", "The company defaulted on its NCDs.", "A loan default followed.",
                     "An emphasis of matter covers the AGR dues.", "SEBI issued a show cause notice.",
                     "Promoters hold pledged shares.", "The liquidity gap is tight against maturities."):
            self.assertTrue(self.flag(text), text)


class VerificationItemsTests(unittest.TestCase):
    """B1 and B6: open findings reach the registry, and a timestamp does not make it stale."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-vitems-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "qc").mkdir()

    def write(self, data):
        (self.tmp / "qc" / "verification.json").write_text(json.dumps(data), encoding="utf-8")

    def sample(self, checked_at="t1"):
        return {"checked_at": checked_at, "stage": "specialists", "run_findings": [
            {"check": "AUDIT_OPEN", "agent": "cio", "detail": "an audit finding is open", "severity": "blocking"}],
            "specialists": {"filings": {"findings": [
                {"check": "CLAIM_DISCREPANCY", "detail": "the page says otherwise", "severity": "blocking", "waived": False},
                {"check": "WORKPAPERS", "detail": "waived one", "severity": "minor", "waived": True},
                {"check": "VISUAL_ONLY", "detail": "information only", "severity": "info", "waived": False}]}}}

    def test_open_findings_become_items_and_waived_ones_do_not(self):
        self.write(self.sample())
        items = synthesis.verification_items(self.tmp)
        self.assertEqual(sorted(i["section"] for i in items), ["AUDIT_OPEN", "CLAIM_DISCREPANCY"])
        self.assertEqual({i["author"] for i in items}, {"cio", "filings"})

    def test_a_new_timestamp_does_not_change_the_input_hash(self):
        p = self.tmp / "qc" / "verification.json"
        self.write(self.sample("t1"))
        first = synthesis.input_hash(p)
        self.write(self.sample("t2"))
        self.assertEqual(synthesis.input_hash(p), first)

    def test_a_new_open_finding_does_change_it(self):
        p = self.tmp / "qc" / "verification.json"
        self.write(self.sample())
        first = synthesis.input_hash(p)
        data = self.sample()
        data["run_findings"].append({"check": "READING_AUDIT", "agent": "cio", "detail": "new", "severity": "blocking"})
        self.write(data)
        self.assertNotEqual(synthesis.input_hash(p), first)


class ContradictionLogTests(unittest.TestCase):
    """B4: adjudicated means adjudicated."""

    def test_a_bare_mention_is_not_an_adjudication(self):
        self.assertTrue(synthesis.adjudication_gaps("Discussed CC-T1-1 in passing.", "CC-T1-1"))

    def test_a_full_entry_is(self):
        self.assertEqual(synthesis.adjudication_gaps(GOOD_ENTRY, "CC-T1-1"), [])

    def test_an_absent_id_is_reported(self):
        self.assertTrue(synthesis.adjudication_gaps(GOOD_ENTRY, "CC-T9-9"))

    def test_an_unfilled_template_entry_is_not_an_adjudication(self):
        blank = GOOD_ENTRY.replace("recomputed from the note [CALCULATION: CIO-C014]", "…").replace("0.86x stands", "…")
        self.assertTrue(synthesis.adjudication_gaps(blank, "CC-T1-1"))

    def test_the_cio_check_must_cite_a_cio_claim(self):
        self.assertTrue(synthesis.adjudication_gaps(GOOD_ENTRY.replace("CIO-C014", "FIN-C014"), "CC-T1-1"))

    def test_unresolved_is_a_valid_outcome(self):
        self.assertEqual(synthesis.adjudication_gaps(GOOD_ENTRY.replace("0.86x stands", "Unresolved"), "CC-T1-1"), [])

    def test_a_numeric_conflict_needs_a_resolved_block_holding_its_claims(self):
        self.assertTrue(synthesis.conflict_adjudicated(GOOD_ENTRY, ["FIN-C041"]))
        self.assertFalse(synthesis.conflict_adjudicated("We note FIN-C041 and move on.", ["FIN-C041"]))


class FollowupTests(unittest.TestCase):
    """B2: a contradiction raised only in a part brief is still seen."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-parts-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "synthesis" / "themes").mkdir(parents=True)
        (self.tmp / "cio").mkdir()
        (self.tmp / "synthesis" / "themes" / "T1.md").write_text(
            "## Contradiction Candidates\n\n- none\n\n## Gaps and Follow-up Requests\n\n- none\n", encoding="utf-8")
        (self.tmp / "synthesis" / "themes" / "T1.p2.md").write_text(
            "## Contradiction Candidates\n\n- CC-T1-7 two audit views\n\n## Gaps and Follow-up Requests\n\n- FU-T1-3 ask\n",
            encoding="utf-8")

    def test_a_part_brief_is_read(self):
        out = synthesis.followups(self.tmp, log=lambda m: None, write=False)
        self.assertEqual(out["open_candidates"], ["CC-T1-7"])
        self.assertEqual([f["id"] for f in out["followups"]], ["FU-T1-3"])

    def test_a_part_of_a_theme_counts_in_the_theme_briefs(self):
        self.assertEqual([p.name for p in synthesis.theme_briefs(self.tmp)], ["T1.md", "T1.p2.md"])


class DispositionTests(unittest.TestCase):
    """B3: the two exits a gating item could leave by."""

    reg = {"R-aaa": {"kind": "key_finding", "materiality": "gating", "provenance": "specialist"},
           "R-bbb": {"kind": "corpus_item", "materiality": "material", "provenance": "digest_unconfirmed_lead"},
           "R-ccc": {"kind": "event", "materiality": "material", "provenance": "historian"}}

    def errors(self, rid, disp, ptr, reason="a reason of enough length to pass every word count here"):
        return synthesis.pointer_errors(rid, disp, ptr, reason, self.reg, {"FIN-C001"}, {"C-cluster-1"})

    def test_superseded_must_point_at_something_real(self):
        self.assertTrue(self.errors("R-aaa", "superseded", "R-doesnotexist"))
        self.assertTrue(self.errors("R-aaa", "superseded", "FIN-C999"))
        self.assertEqual(self.errors("R-aaa", "superseded", "R-bbb"), [])
        self.assertEqual(self.errors("R-aaa", "superseded", "FIN-C001"), [])
        self.assertEqual(self.errors("R-aaa", "superseded", "C-cluster-1"), [])

    def test_a_specialist_finding_is_not_an_unverified_lead(self):
        self.assertTrue(self.errors("R-aaa", "unverified_lead", ""))

    def test_a_digest_or_historian_lead_may_be_one(self):
        self.assertEqual(self.errors("R-bbb", "unverified_lead", ""), [])
        self.assertEqual(self.errors("R-ccc", "unverified_lead", ""), [])

    def test_a_short_reason_for_a_gating_supersession_is_refused(self):
        self.assertTrue(self.errors("R-aaa", "superseded", "R-bbb", "replaced"))

    def test_a_contested_item_with_no_claims_reaches_through_its_candidate(self):
        item = {"materiality": "gating", "claim_ids": []}
        self.assertFalse(synthesis.reached(item, {"disposition": "contested", "pointer": "CC-T1-1"}, set(), set(), "no mention"))
        self.assertTrue(synthesis.reached(item, {"disposition": "contested", "pointer": "CC-T1-1"}, set(), set(), "see CC-T1-1"))


class KeyQuantityTests(unittest.TestCase):
    """B11: the check must read a line the way a person does."""

    kq = [{"label": "Price", "value": "1000"}]

    def test_a_longer_word_is_not_the_label(self):
        self.assertEqual(synthesis.key_quantity_errors("price_timestamp: 2026-01-01 10:00", self.kq), [])
        self.assertEqual(synthesis.key_quantity_errors("Price-to-book was 3.2x", self.kq), [])

    def test_the_same_value_in_another_form_passes(self):
        self.assertEqual(synthesis.key_quantity_errors("Price was 1,000.00 at the close", self.kq), [])

    def test_a_different_value_still_fails(self):
        self.assertTrue(synthesis.key_quantity_errors("Price was 1,100 at the close", self.kq))

    def test_the_front_matter_is_not_read(self):
        self.assertEqual(synthesis.key_quantity_errors("---\nprice: 999\n---\nPrice was 1,000.", self.kq), [])


class OrderTests(unittest.TestCase):
    """B5, B7, B8, B12: the order of Stage 3 and its dead ends."""

    def test_a_cluster_id_keeps_only_safe_characters(self):
        self.assertEqual(synthesis.cluster_slug("other:cost/income"), "other_cost_income")
        self.assertEqual(synthesis.cluster_slug("other:gnpa%"), "other_gnpa")

    def test_an_id_from_a_slug_fits_the_register(self):
        row = "| C-financials-%s | immaterial | | reason |" % synthesis.cluster_slug("other:cost/income")
        self.assertIsNotNone(synthesis.DISP_ROW_RE.match(row))


if __name__ == "__main__":
    unittest.main()
