"""Planted errors in real Bharti material: which controls catch them, measured.

Each mutation is a mistake a real run could make. The catch rate per class is the release gate (the plan's acceptance):
at least 95 % of the classes scripts can detect. Classes only a person or the verifier can judge (a right number
attributed to the wrong period, say) are listed, so the gap is stated, not hidden.
"""

import copy
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import golden_tools as gt  # noqa: E402

ROOT = gt.ROOT
sys.path.insert(0, str(ROOT / "scripts"))
import audit_tools  # noqa: E402
import claim_graph  # noqa: E402
import reading_audit as ra  # noqa: E402
import research_lib as rl  # noqa: E402
import synthesis  # noqa: E402
import verify  # noqa: E402

CUTOFF = "2026-10-12"
PLANTED = "73,219.40"                # within rounding of no claim of the run
NEEDS_JUDGMENT = ("a right number attributed to the wrong period", "a right number from the wrong entity",
                  "a misread sentence that keeps its numbers")


@unittest.skipUnless(gt.RUN.exists(), "the golden run is not on this machine")
class MutationSuite(unittest.TestCase):
    results = {}

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="eqr-mutate-"))
        cls.rd = gt.scratch_copy(cls.tmp)
        cls.items = gt.registry_items(cls.rd)
        cls.rows = verify.ledger_rows(verify.ledgers_of(gt.RUN, "filings"))
        cls.seen = verify.Seen(verify.agent_sessions(gt.RUN, "filings"))
        cls.keys = verify.source_keys(gt.RUN)
        cls.report = (cls.rd / "cio" / "final_report.md").read_text(encoding="utf-8")
        cls.clean = cls.checks(cls.rows)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)
        caught = sum(cls.results.values())
        print("\nmutation suite: %d of %d planted errors caught" % (caught, len(cls.results)))
        for name, ok in sorted(cls.results.items()):
            if not ok:
                print("  MISSED: %s" % name)

    @classmethod
    def checks(cls, rows):
        return {f["check"]: set(f["claims"]) for f in verify.claim_checks(rows, cls.seen, cls.keys, "filings", CUTOFF)}

    def fact(self, numeric=True):
        for r in self.rows:
            value = r.get("value") or ""
            seen_exactly = len(verify.NUM_RE.findall(value)) == 1 and verify.exact(verify.NUM_RE.findall(value)[0]) in self.seen.numbers
            if r.get("tag") == "FACT" and (not numeric or (len(verify.digits(value)) >= 4 and seen_exactly)):
                return r
        self.fail("no suitable claim")

    def caught(self, name, ok):
        type(self).results[name] = bool(ok)
        self.assertTrue(ok, name)

    def planted(self, check, **change):
        """Is a claim changed like this reported under the check, when the clean run was not?"""
        r = self.fact()
        rows = [dict(x, **change) if x is r else x for x in self.rows]
        new = self.checks(rows).get(check, set()) - self.clean.get(check, set())
        return any(r["claim_id"] in c for c in new)

    # -- numbers ------------------------------------------------------------------------------------------------
    def test_a_wrong_digit(self):
        r = self.fact()
        self.caught("a wrong digit", self.planted("NUMBER_NOT_SEEN", value=re.sub(r"\d", "7", r["value"], 2)))

    def test_a_ten_times_error(self):
        r = self.fact()
        v = verify.NUM_RE.findall(r["value"])[0].replace(",", "")
        self.caught("a ten-times error", self.planted("SCALE_NOT_SEEN", value=str(float(v) * 10)))

    def test_a_hundred_times_error(self):
        r = self.fact()
        v = verify.NUM_RE.findall(r["value"])[0].replace(",", "")
        self.caught("a hundred-times error", self.planted("SCALE_NOT_SEEN", value=str(float(v) * 100)))

    # -- sources ------------------------------------------------------------------------------------------------
    def test_a_prose_source(self):
        self.caught("a prose source", self.planted("SOURCE_UNCHECKABLE", source_url_or_id="BSE filing, January 2024"))

    def test_a_source_nobody_opened(self):
        self.caught("a fabricated source", self.planted("SOURCE_NOT_OPENED", source_url_or_id="https://made.up.example/report.pdf"))

    def test_a_source_after_the_cutoff(self):
        self.caught("a source after the cutoff", self.planted("AFTER_CUTOFF", source_date="2026-11-01"))

    def test_a_digest_summary_as_a_fact(self):
        items = self.rd / rl.DIGEST_DIR / "items"
        items.mkdir(parents=True, exist_ok=True)
        (items / "ar.jsonl").write_text(json.dumps({"source_url": "https://news.example.com/summary"}) + "\n", encoding="utf-8")
        got = verify.digest_fact_findings(self.rd, [dict(self.fact(), source_url_or_id="https://www.news.example.com/summary?x=1")], "filings")
        self.caught("a digest summary as a fact", got)

    # -- the report ---------------------------------------------------------------------------------------------
    def tie(self, text):
        path = self.rd / "cio" / "mutated.md"
        path.write_text(text, encoding="utf-8")
        return audit_tools.tieout_rows(self.rd, path)

    def test_a_changed_number_in_the_report(self):
        base = self.tie(self.report)
        lines = self.report.splitlines()
        hit = next(r for r in base if r["status"] == "match" and re.search(r"\d{3,}", lines[int(r["line"]) - 1].split("[")[0]))
        n = int(hit["line"]) - 1
        number = re.search(r"\d[\d,]*\.?\d*", lines[n].split("[")[0][lines[n].index("|", 2):]).group(0)
        lines[n] = lines[n].replace(number, PLANTED, 1)
        row = next(r for r in self.tie("\n".join(lines)) if int(r["line"]) == n + 1)
        self.caught("a changed number in the report", row["status"] != "match" or PLANTED in row["unsupported"])

    def test_the_number_screen_compares_exactly(self):
        """Within 0.6 % and across unit shifts a random number matches some claim of the run 60-80 % of the time, so a
        whole-run comparison must be exact to say anything."""
        self.assertTrue(audit_tools.matches("91,778.70", 91800.0, ""))
        self.assertFalse(audit_tools.same_number("91,778.70", 91800.0, ""))
        self.assertTrue(audit_tools.same_number("1,778.70", 1778.7, ""))

    def test_a_dropped_gating_finding(self):
        item = next(i for i in self.items if i["materiality"] == "gating" and "0.86" in i["text"] and i.get("claim_ids"))
        own = set(item["claim_ids"])
        self.caught("a dropped gating finding", not synthesis.reached(item, {}, set(), set()) and own)

    def test_an_opinion_restated_as_unmodified(self):
        reg = [{"kind": "corpus_item", "type": "emphasis_of_matter", "text": "EOM on AGR", "id": "R-1"}]
        self.caught("an opinion restated as unmodified", synthesis.consistency_errors(self.rd, "The audit opinion was unmodified.", reg))

    def test_a_key_number_stated_two_ways(self):
        kq = [{"label": "permanent-loss band", "value": "10-20%"}]
        self.caught("a key number stated two ways", synthesis.key_quantity_errors("The permanent-loss band is 5-20%.", kq))

    # -- scores -------------------------------------------------------------------------------------------------
    def card(self):
        return json.loads((self.rd / "cio" / "scorecard.json").read_text(encoding="utf-8"))

    def invalid(self, c):
        p = self.rd / "cio" / "scorecard_mut.json"
        p.write_text(json.dumps(c), encoding="utf-8")
        return not rl.validate_scorecard(p, version=rl.version_tuple("2.2.0")).ok

    def test_a_tampered_final_score(self):
        c = self.card()
        c["investment_attractiveness"]["final"] += 20
        self.caught("a tampered final score", self.invalid(c))

    def test_a_tampered_dimension(self):
        c = self.card()
        c["investment_attractiveness"]["dimensions"][0]["score"] += 30
        self.caught("a tampered dimension score", self.invalid(c))

    def test_a_tampered_verdict(self):
        c = self.card()
        c["verdict"] = "STRONG BUY"
        self.caught("a tampered verdict with no reason", self.invalid(c))

    def test_a_stale_price(self):
        c = self.card()
        c["price"]["timestamp"] = "NSE close 12-Aug-2026 (NSE CM bhavcopy)"
        self.caught("a stale price", rl.price_date_errors(c, CUTOFF))

    # -- independence and the graph -----------------------------------------------------------------------------
    def test_reading_a_peers_report(self):
        calls, _ = ra.independence_patterns("moat", "R")
        self.caught("reading a peer's report", calls.search("cat specialists/filings.md"))

    def test_reading_the_cio_scorecard(self):
        calls, _ = ra.independence_patterns("moat", "R")
        self.caught("reading the CIO's scorecard", calls.search("cat cio/scorecard.json"))

    def test_a_calculation_with_no_inputs(self):
        led = self.rd / "specialists" / "filings_ledger.csv"
        original = led.read_text(encoding="utf-8")
        row = next(r for r in verify.ledger_rows([led]) if r.get("tag") == "CALCULATION")
        led.write_text(original.replace(row["formula_or_inputs"], "worked out", 1), encoding="utf-8")
        try:
            self.caught("a calculation with no inputs", claim_graph.build(self.rd, write=False)["errors"]["calculation_without_inputs"])
        finally:
            led.write_text(original, encoding="utf-8")

    def test_the_list_of_what_only_judgment_can_catch_is_stated(self):
        self.assertEqual(len(NEEDS_JUDGMENT), 3)


if __name__ == "__main__":
    unittest.main()
