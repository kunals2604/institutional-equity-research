"""Tests for the transcript archive (scripts/archive_transcripts.py) and its fallback in the audit's lookups.

Verification and the reading audit read agents' transcripts, which Claude Code deletes silently after its retention
period. These tests delete the live copies and check that a run can still be audited from the archive.
"""

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_driver as ad  # noqa: E402
import archive_transcripts as at  # noqa: E402
import reading_audit as ra  # noqa: E402
import research_lib as rl  # noqa: E402
import verify  # noqa: E402

RUN_ID = "20260101T000000Z"
HEADLESS = "11111111-1111-1111-1111-111111111111"


class ArchiveBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-archive-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.live = self.tmp / "live"
        self.archive = self.tmp / "archive"
        self.live.mkdir()
        old = os.environ.get("EQR_TRANSCRIPT_ARCHIVE")
        os.environ["EQR_TRANSCRIPT_ARCHIVE"] = str(self.archive)
        self.addCleanup(self._restore, old)
        (self.live / "main.jsonl").write_text('{"note": "run %s"}\n' % RUN_ID, encoding="utf-8")
        (self.live / "other.jsonl").write_text('{"note": "another run"}\n', encoding="utf-8")
        (self.live / ("%s.jsonl" % HEADLESS)).write_text('{"note": "reader"}\n', encoding="utf-8")
        sub = self.live / "main" / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-a.jsonl").write_text('{"note": "work"}\n', encoding="utf-8")
        (sub / "agent-a.meta.json").write_text(json.dumps({"agentType": "moat", "description": "moat %s" % RUN_ID}),
                                               encoding="utf-8")
        self.run_dir = self.tmp / "run"
        (self.run_dir / "engine").mkdir(parents=True)
        (self.run_dir / rl.RUN_MANIFEST).write_text(json.dumps({"run_id": RUN_ID}), encoding="utf-8")
        (self.run_dir / "engine" / "jobs.json").write_text(json.dumps({"jobs": [
            {"id": "J001", "agent": "reader", "sessions": [{"session_id": HEADLESS}]}]}), encoding="utf-8")

    @staticmethod
    def _restore(old):
        if old is None:
            os.environ.pop("EQR_TRANSCRIPT_ARCHIVE", None)
        else:
            os.environ["EQR_TRANSCRIPT_ARCHIVE"] = old

    def delete_live(self):
        shutil.rmtree(self.live)
        self.live.mkdir()


class ArchiveTests(ArchiveBase):
    def test_archive_copies_every_session_of_the_run_and_no_other(self):
        at.archive_run(self.run_dir, self.live)
        got = {str(p.relative_to(self.archive)) for p in self.archive.rglob("*") if p.is_file()}
        self.assertEqual(got, {"main.jsonl", "%s.jsonl" % HEADLESS, "main/subagents/agent-a.jsonl",
                               "main/subagents/agent-a.meta.json", at.MANIFEST})

    def test_manifest_records_a_correct_checksum_for_each_file(self):
        at.archive_run(self.run_dir, self.live)
        with (self.archive / at.MANIFEST).open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 4)
        for r in rows:
            data = (self.archive / r["path"]).read_bytes()
            self.assertEqual(r["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(int(r["bytes"]), len(data))
            self.assertEqual(r["run_id"], RUN_ID)

    def test_archiving_twice_does_not_duplicate_rows(self):
        at.archive_run(self.run_dir, self.live)
        at.archive_run(self.run_dir, self.live)
        with (self.archive / at.MANIFEST).open(encoding="utf-8", newline="") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 4)

    def test_a_grown_session_is_recopied(self):
        at.archive_run(self.run_dir, self.live)
        with (self.live / "main.jsonl").open("a", encoding="utf-8") as f:
            f.write('{"note": "later"}\n')
        at.archive_run(self.run_dir, self.live)
        self.assertIn("later", (self.archive / "main.jsonl").read_text(encoding="utf-8"))

    def test_archiving_again_after_the_live_files_are_gone_keeps_the_record(self):
        at.archive_run(self.run_dir, self.live)
        self.delete_live()
        self.assertEqual(at.archive_run(self.run_dir, self.live)[:2], (4, 0))
        self.assertEqual(len(at.load_manifest(self.archive)), 4)
        self.assertEqual(at.verify_archive(), [])

    def test_without_its_manifest_nothing_counts_as_archived_for_a_run(self):
        at.archive_run(self.run_dir, self.live)
        self.delete_live()
        (self.archive / at.MANIFEST).unlink()
        self.assertEqual(ra.find_main_sessions(self.live, RUN_ID), [])
        self.assertEqual(ra.find_agents(self.live, RUN_ID), [])

    def test_verify_reports_a_good_archive_and_a_damaged_one(self):
        at.archive_run(self.run_dir, self.live)
        self.assertEqual(at.verify_archive(), [])
        (self.archive / "main.jsonl").write_text("tampered", encoding="utf-8")
        self.assertEqual(len(at.verify_archive()), 1)

    def test_a_file_lost_from_the_archive_is_reported(self):
        at.archive_run(self.run_dir, self.live)
        (self.archive / "main.jsonl").unlink()
        self.assertEqual(len(at.verify_archive()), 1)


class FallbackTests(ArchiveBase):
    def test_nothing_is_found_when_live_files_are_gone_and_no_archive_exists(self):
        self.delete_live()
        self.assertEqual(ra.find_agents(self.live, RUN_ID), [])
        self.assertEqual(ra.find_main_sessions(self.live, RUN_ID), [])

    def test_lookups_fall_back_to_the_archive_after_deletion(self):
        at.archive_run(self.run_dir, self.live)
        self.delete_live()
        agents = ra.find_agents(self.live, RUN_ID)
        self.assertEqual([a["type"] for a in agents], ["moat"])
        self.assertTrue(agents[0]["path"].exists())
        self.assertEqual([p.name for p in ra.find_main_sessions(self.live, RUN_ID)], ["main.jsonl"])
        headless = ra.headless_sessions(self.run_dir, self.live)
        self.assertEqual([h["session_id"] for h in headless], [HEADLESS])
        self.assertTrue(headless[0]["path"].exists())

    def test_verify_finds_sessions_when_the_live_directory_itself_is_gone(self):
        at.archive_run(self.run_dir, self.live)
        shutil.rmtree(self.live)
        self.assertEqual([s["type"] for s in verify.agent_sessions(self.run_dir, "reader", self.live)], ["reader"])

    def test_an_archived_session_counts_only_for_the_run_it_was_archived_for(self):
        at.archive_run(self.run_dir, self.live)
        mentions = self.archive / "unrelated.jsonl"
        mentions.write_text('{"note": "a design session mentions %s and OTHER"}\n' % RUN_ID, encoding="utf-8")
        self.delete_live()
        self.assertEqual([p.name for p in ra.find_main_sessions(self.live, RUN_ID)], ["main.jsonl"])
        self.assertEqual(ra.find_main_sessions(self.live, "OTHER"), [])
        self.assertEqual(ra.find_agents(self.live, "OTHER"), [])

    def test_a_live_file_is_used_in_preference_to_its_archived_copy(self):
        at.archive_run(self.run_dir, self.live)
        paths = ra.find_main_sessions(self.live, RUN_ID)
        self.assertEqual(paths, [self.live / "main.jsonl"])

    def test_a_session_in_both_places_is_counted_once(self):
        at.archive_run(self.run_dir, self.live)
        self.assertEqual(len(ra.find_agents(self.live, RUN_ID)), 1)
        self.assertEqual(len(ra.headless_sessions(self.run_dir, self.live)), 1)


class IndependenceTests(unittest.TestCase):
    """The archive holds every specialist's session, so it stands behind the same wall as the live transcripts."""

    def test_agents_are_denied_the_archive(self):
        archive = "%s/research/_archive/**" % rl.ROOT.resolve()
        self.assertTrue(any(archive in rule for rule in ad.DENY_TRANSCRIPTS))
        self.assertTrue(any(archive in rule for rule in ad.independence_denies(rl.ROOT / "x", "moat")))
        self.assertTrue(any(archive in rule for rule in ad.independence_denies(rl.ROOT / "x", "moat", review=True)))

    def test_the_audit_flags_a_tool_call_that_names_the_archive(self):
        calls, _ = ra.independence_patterns("moat", RUN_ID)
        self.assertIsNotNone(calls.search("cat research/_archive/transcripts/main.jsonl"))

    def test_only_the_cio_runs_the_archiver(self):
        self.assertIn("archive_transcripts.py", ad.CIO_ONLY_SCRIPTS)


if __name__ == "__main__":
    unittest.main()
