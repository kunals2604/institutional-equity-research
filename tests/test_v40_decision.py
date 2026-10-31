"""Step 6: the rest of the decision engine. Questions before checklists, the forecast before the market's view, a pause that
asks, the owner's own record, and the first page."""

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import agent_driver as ad  # noqa: E402
import decide  # noqa: E402
import forecast_tools as ft  # noqa: E402
import ideas  # noqa: E402
import notes  # noqa: E402
import orchestrate as oc  # noqa: E402
import outcomes  # noqa: E402
import research_lib as rl  # noqa: E402
import verify  # noqa: E402
from test_v40_orchestrate import new_run  # noqa: E402

QUESTIONS = "1. Can tariffs rise without share loss?\n2. Does the Africa stake earn its cost of capital?\n3. Who funds the next capex cycle?\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-dec-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_dir(self, *flags):
        return new_run(self.tmp, *flags)


class KeyQuestionTests(Base):
    def write(self, run, text):
        (run / "engine" / "key_questions.md").write_text(text, encoding="utf-8")

    def test_three_real_questions_pass(self):
        run = self.run_dir()
        self.write(run, QUESTIONS)
        self.assertEqual(oc.key_question_errors(run), [])

    def test_a_statement_is_not_a_question(self):
        run = self.run_dir()
        self.write(run, QUESTIONS + "4. Margins will expand.\n")
        self.assertTrue(oc.key_question_errors(run))

    def test_a_price_implied_number_is_refused(self):
        run = self.run_dir()
        for bad in ("Can it grow 14.4% for ten years?", "Is INR 1,778 fair?", "Does it deserve 11x EBITDA?"):
            self.write(run, QUESTIONS + "4. %s\n" % bad)
            self.assertTrue(oc.key_question_errors(run), bad)

    def test_every_specialist_gets_the_same_questions(self):
        run = self.run_dir()
        self.write(run, QUESTIONS)
        (run / "engine" / "identity.md").write_text("identity", encoding="utf-8")
        rl.update_json(run / rl.RUN_MANIFEST, lambda m: m.update(sector_modules=[]))
        block = ad.key_questions_text(run)
        self.assertIn("Can tariffs rise", block)
        for name in ("moat", "filings"):
            self.assertIn(block, ad.specialist_prompt(run, name))


class EarlyStopTests(Base):
    def report(self, run, name, text):
        (run / "specialists" / ("%s.md" % name)).write_text("## Domain Conclusion\n\n%s\n" % text, encoding="utf-8")

    def test_management_moves_to_third_with_the_switch_on(self):
        self.assertEqual(ad.specialist_order(self.run_dir())[:3], ["financials", "filings", "management"])

    def test_the_order_stays_with_the_switch_off(self):
        self.assertEqual(ad.specialist_order(self.run_dir("--set", "early_stop=off")), list(ad.SPECIALIST_ORDER))

    def test_a_stated_red_flag_is_found(self):
        run = self.run_dir()
        self.report(run, "filings", "**Reporting reliability:** Highly concerning")
        self.assertIn("G1", ad.early_flag(run, "filings"))
        self.report(run, "management", "- **Governance:** Compromised")
        self.assertIn("G3", ad.early_flag(run, "management"))

    def test_a_sound_conclusion_raises_nothing(self):
        run = self.run_dir()
        self.report(run, "filings", "**Reporting reliability:** Generally reliable")
        self.assertEqual(ad.early_flag(run, "filings"), "")

    def test_with_the_switch_off_nothing_pauses(self):
        run = self.run_dir("--set", "early_stop=off")
        self.report(run, "filings", "**Reporting reliability:** Highly concerning")
        self.assertEqual(ad.early_flag(run, "filings"), "")

    def pause(self, run):
        rl.write_json(run / "engine" / "early_stop.json", {"agent": "filings", "flag": "G1: Highly concerning", "decision": None})

    def test_a_pause_asks_the_owner_and_nothing_goes_on_without_an_answer(self):
        run = self.run_dir()
        self.pause(run)
        step = oc.next_step(run)
        self.assertEqual((step["id"], step["type"]), ("early_stop", "owner"))
        self.assertEqual(oc.run_steps(run, lambda m: None, lambda c: self.fail("ran a step during the pause")), 0)

    def test_continue_goes_on_and_does_not_ask_twice(self):
        run = self.run_dir()
        self.pause(run)
        self.report(run, "filings", "**Reporting reliability:** Highly concerning")
        oc.decide_early(run, "continue", "The accounting issue is known and priced.")
        self.assertNotEqual(oc.next_step(run)["id"], "early_stop")
        self.assertEqual(ad.early_flag(run, "filings"), "")

    def test_stop_ends_the_run_and_records_why(self):
        run = self.run_dir()
        self.pause(run)
        oc.decide_early(run, "stop", "Not worth the rest of the spend.")
        self.assertIsNone(oc.next_step(run))
        self.assertEqual(rl.load_json(run / rl.RUN_MANIFEST)["status"], "stopped_gate")

    def test_a_decision_needs_a_reason(self):
        run = self.run_dir()
        self.pause(run)
        with self.assertRaises(SystemExit):
            oc.decide_early(run, "stop", "  ")


class ForecastCommitTests(Base):
    def test_the_commit_records_the_model(self):
        model = self.tmp / "m.json"
        model.write_text("{}", encoding="utf-8")
        out = self.tmp / "commit.json"
        self.assertEqual(ft.main(["commit", "--model", str(model), "--out", str(out)]), 0)
        self.assertEqual(len(json.loads(out.read_text())["sha256"]), 64)

    def test_the_definition_commits_before_the_market_views(self):
        text = (ROOT / ".claude" / "agents" / "forecasting.md").read_text(encoding="utf-8")
        self.assertLess(text.index("Commit the base model"), text.index("Consensus and revisions"))


class OwnerRecordTests(Base):
    def card(self, run, **change):
        sc = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))
        sc.update(change)
        rl.write_json(run / "cio" / "scorecard.json", sc)
        return sc

    def test_the_owners_action_is_kept_apart_from_the_verdict(self):
        run = self.run_dir()
        self.card(run, verdict="AVOID")
        row = decide.record(run, "buy", "I weigh the Africa stake more heavily.", root=self.tmp)
        self.assertEqual((row["system_verdict"], row["action"]), ("AVOID", "buy"))
        rows = list(csv.DictReader((outcomes.out_dir(self.tmp) / "owner_decisions.csv").open(encoding="utf-8", newline="")))
        self.assertEqual(rows[0]["reason"], "I weigh the Africa stake more heavily.")

    def test_the_record_only_grows(self):
        run = self.run_dir()
        self.card(run)
        decide.record(run, "wait", "Not yet.", root=self.tmp)
        decide.record(run, "buy", "Now.", root=self.tmp)
        self.assertEqual(len(list(csv.DictReader((outcomes.out_dir(self.tmp) / "owner_decisions.csv").open(encoding="utf-8", newline="")))), 2)

    def test_by_default_the_record_sits_with_the_other_outcomes(self):
        self.assertEqual(outcomes.out_dir(decide.RESEARCH), rl.ROOT / "research" / "outcomes")

    def test_an_action_needs_a_reason(self):
        run = self.run_dir()
        self.card(run)
        with self.assertRaises(SystemExit):
            decide.record(run, "buy", "", root=self.tmp)

    def test_the_memo_fits_a_page_and_carries_the_decision(self):
        run = self.run_dir()
        self.card(run)
        text = decide.memo(run)
        for needle in ("Decision memo", "The case for", "The case against", "How they were weighed", "Computed guide", "What this run left out"):
            self.assertIn(needle, text)
        self.assertLess(len(text.split()), 700)

    def test_a_held_position_gets_an_action(self):
        run = self.run_dir("--held", "--cost-basis", "900")
        self.card(run, held_action="TRIM")
        self.assertIn("**TRIM**", decide.memo(run))


class HeldBuildTests(Base):
    def test_a_held_name_cannot_finish_without_an_action(self):
        import build_scorecard as bs
        run = self.run_dir("--held")
        sc = json.loads((ROOT / "templates" / "scorecard.example.json").read_text(encoding="utf-8"))
        for k in ("mapped_verdict", "decision"):
            sc.pop(k, None)
        with self.assertRaisesRegex(ValueError, "held_action"):
            self._compute(bs, sc, run)

    def _compute(self, bs, sc, run):
        import unittest.mock as um
        with um.patch.object(bs, "fill_price_metrics", lambda *a: None), um.patch.object(bs, "cap_confidence_by_owners", lambda *a: []):
            return bs.compute(sc, run)


class NotesTests(Base):
    def test_a_note_needs_its_attestation(self):
        run = self.run_dir()
        with self.assertRaises(SystemExit):
            notes.add(run, "Dealer call", "2026-10-30", "text", "ok")

    def test_a_note_is_citable_and_a_lead_not_a_fact(self):
        run = self.run_dir()
        path = notes.add(run, "Dealer call", "2026-10-30", "Stock is high.", "my own call, no insider information")
        text = path.read_text(encoding="utf-8")
        self.assertIn("owner-note:001", text)
        self.assertIn("tier 7", text)
        self.assertTrue(verify.checkable_source("owner-note:001"))

    def test_a_bad_date_is_refused(self):
        run = self.run_dir()
        with self.assertRaises(ValueError):
            notes.add(run, "x", "2026-13-01", "t", "my own call, no insider information")


class RankTests(unittest.TestCase):
    def test_the_real_book_ranks(self):
        got = ideas.rows()
        self.assertTrue(any(r["ticker"] == "BHARTIARTL" for r in got))

    def test_higher_edge_comes_first(self):
        tmp = Path(tempfile.mkdtemp(prefix="eqr-rank-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for t, irr in (("AAA", 0.10), ("BBB", 0.20)):
            run = tmp / "research" / "companies" / t / "runs" / "R1"
            (run / "cio").mkdir(parents=True)
            (run.parent.parent / rl.LATEST_POINTER).write_text("R1\n", encoding="utf-8")
            rl.write_json(run / rl.RUN_MANIFEST, {"methodology_version": "4.0.0"})
            rl.write_json(run / "cio" / "scorecard.json", {"ticker": t, "price_metrics": {"expected_irr": irr, "hurdle_rate": 0.12}})
        self.assertEqual([r["ticker"] for r in ideas.rows(tmp)], ["BBB", "AAA"])


if __name__ == "__main__":
    unittest.main()
