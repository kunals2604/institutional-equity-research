"""Defect group C: the engine must see what a session really did (docs/V4_DEFECT_REGISTER.md)."""

import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import agent_driver as ad  # noqa: E402
import research_lib as rl  # noqa: E402
from test_v31_reading_stage import EngineCase  # noqa: E402

REAL_ABORT = ('{"type":"system","subtype":"api_error","level":"error","error":{"message":"Connection error.",'
              '"formatted":"Connection lost while your computer was asleep","connection":{"code":"StreamSuspended",'
              '"isSSLError":false}},"retryInMs":621,"retryAttempt":1,"maxRetries":10}\n')


class TranscriptReadingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-trans-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.t = self.tmp / "s.jsonl"

    def test_a_sleep_abort_in_the_real_format_is_counted(self):
        self.t.write_text(REAL_ABORT * 3, encoding="utf-8")
        self.assertEqual(ad.api_errors(self.t)[0], {"StreamSuspended": 3})

    def test_only_new_lines_are_counted_from_an_offset(self):
        self.t.write_text(REAL_ABORT, encoding="utf-8")
        _, offset = ad.api_errors(self.t)
        with self.t.open("a", encoding="utf-8") as f:
            f.write(REAL_ABORT * 2)
        self.assertEqual(ad.api_errors(self.t, offset)[0], {"StreamSuspended": 2})

    def test_a_line_still_being_written_waits_for_the_next_read(self):
        self.t.write_text(REAL_ABORT + REAL_ABORT[:40], encoding="utf-8")
        found, offset = ad.api_errors(self.t)
        self.assertEqual(found, {"StreamSuspended": 1})
        self.assertEqual(offset, len(REAL_ABORT.encode()))

    def test_another_cause_keeps_its_own_name(self):
        self.t.write_text(REAL_ABORT.replace("StreamSuspended", "ENOTFOUND"), encoding="utf-8")
        self.assertEqual(ad.api_errors(self.t)[0], {"ENOTFOUND": 1})

    def test_a_missing_transcript_is_no_error(self):
        self.assertEqual(ad.api_errors(self.tmp / "none.jsonl"), ({}, 0))

    def test_assistant_turns_counts_either_json_spacing(self):
        self.t.write_text('{"type":"assistant"}\n{"type": "assistant"}\n{"type":"user"}\n', encoding="utf-8")
        self.assertEqual(ad.assistant_turns(self.t), 2)


def attempt(cost, before, after, errors=None, at="2026-10-24T00:00:00"):
    row = {"cost_usd": cost, "util_before": {"seven_day": before}, "util_after": {"seven_day": after}, "at": at}
    return dict(row, api_errors=errors) if errors else row


class CapacityTests(unittest.TestCase):
    """C6: one capacity figure, from clean work."""

    def test_a_clean_stretch_gives_the_true_rate(self):
        rows = [attempt(8.3, 0.10 + i * 0.05, 0.15 + i * 0.05, at="2026-10-24T0%d:00:00" % i) for i in range(4)]
        self.assertAlmostEqual(ad.window_cost(rows)["seven_day"], 166.0, places=0)

    def test_a_stretch_of_failed_streams_does_not_pollute_it(self):
        rows = [attempt(8.3, 0.10 + i * 0.05, 0.15 + i * 0.05, at="2026-10-24T0%d:00:00" % i) for i in range(4)]
        rows.append(attempt(2.0, 0.30, 0.60, at="2026-10-24T09:00:00"))
        self.assertAlmostEqual(ad.window_cost(rows)["seven_day"], 166.0, places=0)

    def test_an_attempt_with_retried_errors_is_not_clean(self):
        rows = [attempt(8.3, 0.10, 0.15, at="2026-10-24T01:00:00"), attempt(8.3, 0.15, 0.20, at="2026-10-24T02:00:00"),
                attempt(8.3, 0.20, 0.25, {"StreamSuspended": 1}, at="2026-10-24T03:00:00")]
        self.assertAlmostEqual(ad.window_cost(rows)["seven_day"], 166.0, places=0)

    def test_too_little_movement_measures_nothing(self):
        self.assertEqual(ad.window_cost([attempt(1.0, 0.10, 0.12)]), {})

    def test_a_gap_is_reported_when_the_meter_moves_without_cost(self):
        self.assertGreater(ad.meter_gap(attempt(2.0, 0.71, 1.0)), 0.25)
        self.assertEqual(ad.meter_gap(attempt(8.3, 0.10, 0.15)), 0.0)

    def test_a_window_past_its_reset_is_not_reported(self):
        gone = {"unifiedWindows": {"seven_day": {"utilization": 0.9, "resetsAt": time.time() - 10}}}
        self.assertEqual(ad.windows_of(gone), {})


class AtomicStateTests(unittest.TestCase):
    """C5: a kill cannot truncate state, and two writers cannot lose a change."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-state-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_a_failed_write_leaves_the_old_file_whole(self):
        path = self.tmp / "jobs.json"
        rl.write_json(path, {"jobs": [1]})
        with self.assertRaises(TypeError):
            rl.write_json(path, {"bad": object()})
        self.assertEqual(rl.load_json(path), {"jobs": [1]})

    def test_writers_under_the_lock_lose_nothing(self):
        path = self.tmp / "run_manifest.json"
        rl.write_json(path, {"n": []})
        add = lambda k: rl.update_json(path, lambda d: d["n"].append(k))  # noqa: E731
        threads = [threading.Thread(target=add, args=(k,)) for k in range(30)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(rl.load_json(path)["n"]), list(range(30)))


class EngineBehaviourTests(EngineCase):
    def assignment(self, name="filings", **over):
        a = ad.specialist_assignment(self.fx.dir, name, "You are the %s specialist for run %s." % (name, self.fx.run_id))
        report = self.fx.dir / "specialists" / ("%s.md" % name)
        a.check = lambda: [] if report.exists() and "DONE" in report.read_text() else ["%s.md does not exist yet" % name]
        for k, v in over.items():
            setattr(a, k, v)
        return a

    def run_one(self, a, **opts):
        eng = self.engine(**opts)
        with ad.Session(eng, "specialists"):
            rc = ad.run_jobs(eng, [(a, ad.open_job(eng, a.agent, a.kind))], 1)
        return rc, json.loads((self.fx.dir / "engine" / "jobs.json").read_text())["jobs"], eng

    def test_c1_sleep_aborts_stop_the_session_and_say_why(self):
        with mock.patch.object(ad, "WATCH_S", 0.05), self.env(FAKE_SLEEP_ABORTS="3", FAKE_UNITS="2"):
            started = time.time()
            rc, jobs, eng = self.run_one(self.assignment(), context_limit=10 ** 7)
        self.assertLess(time.time() - started, 15, "the watchdog stopped it; the fake would hang 30 s")
        self.assertIn("sleep", eng.stop)
        self.assertEqual(jobs[-1]["sessions"][-1]["attempts"][-1]["api_errors"], {"StreamSuspended": 3})
        self.assertNotEqual(jobs[-1].get("status"), "pass")

    def test_c1_the_session_resumes_when_the_engine_runs_again(self):
        with mock.patch.object(ad, "WATCH_S", 0.05), self.env(FAKE_SLEEP_ABORTS="3", FAKE_UNITS="2"):
            self.run_one(self.assignment(), context_limit=10 ** 7)
            rc, jobs, _ = self.run_one(self.assignment(), context_limit=10 ** 7)
        self.assertEqual(rc, 0, self.logs)
        self.assertEqual(jobs[-1]["status"], "pass")
        self.assertEqual(len(jobs), 1, "the same job went on")

    def test_c4_a_session_that_advances_between_failures_is_not_given_up(self):
        with self.env(FAKE_CRASHES="4", FAKE_UNITS="2"):
            with mock.patch.object(ad, "RESUME_WAIT_S", 0):
                rc, jobs, _ = self.run_one(self.assignment(), context_limit=10 ** 7)
        self.assertEqual(rc, 0, self.logs)
        self.assertEqual(jobs[-1]["status"], "pass")

    def test_c4_a_session_that_never_advances_is_still_given_up(self):
        with self.env(FAKE_DEAD="1", FAKE_UNITS="2"):
            with mock.patch.object(ad, "RESUME_WAIT_S", 0):
                rc, jobs, _ = self.run_one(self.assignment(), context_limit=10 ** 7)
        self.assertEqual(jobs[-1]["status"], "abandoned")

    def test_c2_a_passing_check_with_no_new_work_is_not_a_pass(self):
        report = self.fx.dir / "specialists" / "filings.md"
        report.parent.mkdir(exist_ok=True)
        report.write_text("DONE earlier\n", encoding="utf-8")
        with self.env(FAKE_IDLE="1", FAKE_UNITS="2"):
            rc, jobs, _ = self.run_one(self.assignment(), context_limit=10 ** 7)
        self.assertEqual(jobs[-1]["status"], "failed")
        self.assertIn("changed none of its files", json.dumps(jobs[-1]))

    def librarian(self, **over):
        a = ad.librarian_assignment(self.fx.dir, "find the documents")
        log = self.fx.dir / "corpus" / "librarian_log.md"
        log.parent.mkdir(exist_ok=True)
        log.write_text("searched\n", encoding="utf-8")
        for k, v in over.items():
            setattr(a, k, v)
        return a

    def test_c2_a_librarian_that_was_free_to_look_may_find_nothing(self):
        with self.env(FAKE_IDLE="1"):
            rc, jobs, _ = self.run_one(self.librarian(mcp=()))
        self.assertEqual(jobs[-1]["status"], "pass")

    def test_c2_a_librarian_denied_its_tools_has_not_found_nothing(self):
        with self.env(FAKE_IDLE="denied"):
            rc, jobs, _ = self.run_one(self.librarian(mcp=()))
        self.assertEqual(jobs[-1]["status"], "failed")
        self.assertIn("denied", json.dumps(jobs[-1]))

    def test_c3_a_fresh_followup_keeps_the_brief_after_a_resumed_one(self):
        eng = self.engine(context_limit=10 ** 7)
        report = self.fx.dir / "specialists" / "filings.md"
        with self.env(FAKE_UNITS="1"):
            first = self.assignment()
            with ad.Session(eng, "specialists"):
                ad.run_jobs(eng, [(first, ad.open_job(eng, "filings", "specialist"))], 1)
            fix = self.assignment(stage="2", purpose="validator errors")
            fix, job = ad.resume_or_fresh(eng, fix, "fix these two errors")
            self.assertIsNotNone(job, "a small context resumes")
            fresh = self.assignment(stage="3", purpose="cross-examination")
            fresh, job = ad.resume_or_fresh(eng, fresh, "look at the moat claim")
        self.assertIsNone(job)
        self.assertIn("You are the filings specialist", fresh.prompt)
        self.assertNotIn("fix these two errors", fresh.prompt)
        self.assertTrue(report.exists())


if __name__ == "__main__":
    unittest.main()
