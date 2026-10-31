"""Step 4: the pipeline as data. `next` must be a pure function of the disk, and a step must end only when its work exists."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import orchestrate as oc  # noqa: E402
import research_lib as rl  # noqa: E402
import switches  # noqa: E402

PY = sys.executable


def new_run(tmp, *extra):
    r = subprocess.run([PY, str(ROOT / "scripts" / "new_run.py"), "--ticker", "FIXCO", "--company", "FixCo Ltd", "--exchange", "NSE",
                        "--segment", "main", "--root", str(tmp)] + list(extra), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return tmp / r.stdout.strip()


def tree_hash(d):
    h = hashlib.sha256()
    for p in sorted(d.rglob("*")):
        if p.is_file() and p.suffix != ".lock":
            h.update(str(p.relative_to(d)).encode() + p.read_bytes())
    return h.hexdigest()


class PipelineShapeTests(unittest.TestCase):
    def test_every_step_has_a_check_that_exists(self):
        self.assertEqual([s["id"] for s in oc.pipeline() if s["done_when"] not in oc.CHECKS], [])

    def test_step_ids_are_unique(self):
        ids = [s["id"] for s in oc.pipeline()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_check_is_left_unused(self):
        used = {s["done_when"] for s in oc.pipeline()}
        self.assertEqual(sorted(set(oc.CHECKS) - used), [])

    def test_every_judgment_stage_has_a_skill(self):
        for s in oc.pipeline():
            if s["type"] == "cio":
                self.assertTrue((ROOT / ".claude" / "skills" / oc.STAGE_SKILLS[s["stage"]] / "SKILL.md").exists(), s["id"])

    def test_every_when_names_a_real_switch(self):
        reg = switches.registry()["switches"]
        for s in oc.pipeline():
            self.assertTrue(set(s.get("when") or {}) <= set(reg), s["id"])

    def test_a_reading_off_run_has_the_digest_and_no_reading(self):
        ids = [s["id"] for s in oc.active_steps(switches.resolve("standard")["values"])]
        self.assertIn("digest", ids)
        self.assertNotIn("reading", ids)

    def test_a_reading_on_run_has_the_reading_and_no_digest(self):
        ids = [s["id"] for s in oc.active_steps(switches.resolve("deep")["values"])]
        self.assertIn("reading", ids)
        self.assertNotIn("digest", ids)

    def test_the_order_is_the_order_the_method_needs(self):
        ids = [s["id"] for s in oc.pipeline()]
        for a, b in (("specialists", "barrier"), ("themes", "contradictions"), ("contradictions", "layers"), ("layers", "decide"),
                     ("decide", "writers"), ("writers", "assemble"), ("assemble", "audit"), ("audit", "resolve_audit"),
                     ("validate_final", "finalize"), ("finalize", "archive")):
            self.assertLess(ids.index(a), ids.index(b), (a, b))


class NextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-orch-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.run_dir = new_run(self.tmp)

    def test_a_new_run_starts_at_identity(self):
        self.assertEqual(oc.next_step(self.run_dir)["id"], "identity")

    def test_next_writes_nothing_and_answers_the_same_twice(self):
        before = tree_hash(self.run_dir)
        a, b = oc.next_step(self.run_dir), oc.next_step(self.run_dir)
        self.assertEqual(a, b)
        self.assertEqual(tree_hash(self.run_dir), before)

    def test_a_template_is_not_a_finished_brief(self):
        rl.update_json(self.run_dir / rl.RUN_MANIFEST, lambda m: m["price"].update(value=100))
        self.assertEqual(oc.next_step(self.run_dir)["id"], "identity")

    def test_an_edited_brief_moves_it_on(self):
        rl.update_json(self.run_dir / rl.RUN_MANIFEST, lambda m: m["price"].update(value=100))
        with (self.run_dir / "research_brief.md").open("a", encoding="utf-8") as f:
            f.write("\nFilled in.\n")
        self.assertEqual(oc.next_step(self.run_dir)["id"], "acquire")

    def test_a_partly_written_specialist_report_is_not_done(self):
        (self.run_dir / "specialists" / "financials.md").write_text("half a report", encoding="utf-8")
        self.assertFalse(oc.specialists_pass(self.run_dir))

    def test_the_cli_says_when_a_run_is_finished(self):
        out = subprocess.run([PY, str(ROOT / "scripts" / "orchestrate.py"), "next", str(self.run_dir)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("identity", out.stdout)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-orchrun-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.run_dir = new_run(self.tmp)
        self.log = []
        self.steps = [{"id": "one", "stage": "1", "type": "script", "title": "x", "run": "x {run}", "done_when": "a"},
                      {"id": "two", "stage": "1", "type": "cio", "title": "y", "output": "o", "done_when": "b"}]
        self.done = {"a": False, "b": False}
        self.saved = (oc.pipeline, dict(oc.CHECKS))
        oc.pipeline = lambda: self.steps
        oc.CHECKS.update(a=lambda r: self.done["a"], b=lambda r: self.done["b"])

    def tearDown(self):
        oc.pipeline = self.saved[0]
        oc.CHECKS.clear()
        oc.CHECKS.update(self.saved[1])

    def test_it_runs_a_script_step_and_stops_at_a_judgment_step(self):
        def runner(cmd):
            self.done["a"] = True
            return 0
        self.assertEqual(oc.run_steps(self.run_dir, self.log.append, runner), 0)
        self.assertIn("cio-stage-1", "\n".join(self.log))

    def test_a_step_that_exits_clean_without_its_work_is_a_failure(self):
        self.assertEqual(oc.run_steps(self.run_dir, self.log.append, lambda c: 0), 1)
        self.assertIn("check a fails", "\n".join(self.log))

    def test_a_failed_step_stops_the_run(self):
        self.assertEqual(oc.run_steps(self.run_dir, self.log.append, lambda c: 1), 1)

    def test_a_non_zero_exit_with_the_work_done_carries_on(self):
        """A commit made but a push that failed: the work is there, the push is reported, the run goes on."""
        def runner(cmd):
            self.done["a"] = True
            return 4
        self.assertEqual(oc.run_steps(self.run_dir, self.log.append, runner), 0)
        self.assertIn("carrying on", "\n".join(self.log))

    def test_the_run_ends_when_nothing_is_left(self):
        self.done.update(a=True, b=True)
        self.assertEqual(oc.run_steps(self.run_dir, self.log.append, lambda c: 0), 0)
        self.assertIn("finished", self.log[-1])


class EndToEndTests(unittest.TestCase):
    """The checks against a whole run the end-to-end fixture built, so each is tested on the files it is meant to read."""

    @classmethod
    def setUpClass(cls):
        import test_v32_end_to_end as e2e
        cls.fx = e2e.V32Run()
        cls.fx.build_report()

    @classmethod
    def tearDownClass(cls):
        cls.fx.cleanup()

    def test_the_stage_3_checks_hold_on_a_finished_stage_3(self):
        for name in ("themes_pass", "contradictions_adjudicated", "followups_closed", "writers_pass", "report_assembled", "decision_done"):
            self.assertTrue(oc.CHECKS[name](self.fx.dir), name)

    def test_the_final_stage_checks_wait_for_their_work(self):
        for name in ("finalized", "archived", "git_final_done"):
            self.assertFalse(oc.CHECKS[name](self.fx.dir), name)


class CompactSynthesisTests(unittest.TestCase):
    def setUp(self):
        import synthesis
        self.syn = synthesis
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-compact-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_a_compact_run_has_two_themes_covering_every_owner(self):
        run = new_run(self.tmp, "--profile", "lean")
        rl.update_json(run / rl.RUN_MANIFEST, lambda m: m.update(sector_modules=[]))
        th = self.syn.active_themes(run)
        self.assertEqual(sorted(th), ["T1", "T2"])
        authors = {a for t in th.values() for a in t["authors"]}
        self.assertTrue(set(rl.SPECIALISTS) <= authors, set(rl.SPECIALISTS) - authors)

    def test_a_compact_run_keeps_every_report_section_with_a_writer(self):
        run = new_run(self.tmp, "--profile", "lean")
        full = {s for g in self.syn.writer_groups().values() for s in g["sections"]}
        compact = {s for g in self.syn.writer_groups(run).values() for s in g["sections"]}
        self.assertEqual(compact, full)
        self.assertEqual(sorted(self.syn.writer_groups(run)), ["W1", "W7"])

    def test_a_standard_run_keeps_the_full_pipeline(self):
        run = new_run(self.tmp)
        self.assertGreaterEqual(len(self.syn.active_themes(run)), 5)
        self.assertEqual(len(self.syn.writer_groups(run)), 7)


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-orchst-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_status_says_where_the_run_is_and_how_to_go_deeper(self):
        text = oc.status(new_run(self.tmp, "--profile", "lean"))
        for needle in ("Steps done: 0", "Next:", "Spent so far: $0.00", "of a $150 ceiling", "lean", "--deepen"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
