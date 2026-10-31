"""Every step of the pipeline against every fault, generated from config/pipeline.json so a new step is covered at once.

The promise: a fault never loses work, never repeats paid work and never passes falsely. This proves the plumbing, not
judgment: nothing here shows that an agent reasons well, which only the first live run can.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import orchestrate as oc  # noqa: E402
import switches  # noqa: E402
from test_v40_orchestrate import new_run  # noqa: E402

FAULTS = {"a killed process": -9, "a stream abort": 1, "a usage limit that outlasts the wait": 2, "an empty result": 0, "a failed check": 0}


class FaultInjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-fault-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.run_dir = new_run(self.tmp)
        self.saved = dict(oc.CHECKS)
        self.addCleanup(self.restore)

    def restore(self):
        oc.CHECKS.clear()
        oc.CHECKS.update(self.saved)

    def at(self, steps, index):
        """A world in which every step before `index` is done, and the rest are not."""
        self.done = {s["done_when"] for s in steps[:index]}
        for name in oc.CHECKS:
            oc.CHECKS[name] = (lambda n: lambda r: n in self.done)(name)

    def each(self, profile):
        values = switches.resolve(profile)["values"]
        steps = oc.active_steps(values)
        rl_write = oc.values_of
        oc.values_of = lambda r: values
        self.addCleanup(setattr, oc, "values_of", rl_write)
        for i, step in enumerate(steps):
            if step["type"] != "cio":
                for fault, rc in FAULTS.items():
                    yield steps, i, step, fault, rc

    def test_a_fault_stops_at_the_same_step_with_nothing_lost(self):
        for profile in ("standard", "deep"):
            for steps, i, step, fault, rc in self.each(profile):
                with self.subTest(profile=profile, step=step["id"], fault=fault):
                    self.at(steps, i)
                    self.assertEqual(oc.run_steps(self.run_dir, lambda m: None, lambda c: rc), 1)
                    self.assertEqual(oc.next_step(self.run_dir)["id"], step["id"])

    def test_a_restart_goes_on_from_the_step_and_repeats_no_paid_work(self):
        for profile in ("standard", "deep"):
            for steps, i, step, fault, rc in self.each(profile):
                with self.subTest(profile=profile, step=step["id"], fault=fault):
                    self.at(steps, i)
                    oc.run_steps(self.run_dir, lambda m: None, lambda c: rc)
                    ran = []

                    def finish(cmd):
                        ran.append(cmd)
                        self.done.add(next_id["done_when"])
                        return 0
                    next_id = oc.next_step(self.run_dir)
                    oc.run_steps(self.run_dir, lambda m: None, finish)
                    self.assertEqual(ran[0], oc.command(step, self.run_dir))
                    earlier = {oc.command(s, self.run_dir) for s in steps[:i] if s["type"] != "cio"}
                    self.assertFalse(set(ran) & earlier, "a finished step ran again")

    def test_no_fault_counts_as_a_pass(self):
        for steps, i, step, fault, rc in self.each("standard"):
            with self.subTest(step=step["id"], fault=fault):
                self.at(steps, i)
                oc.run_steps(self.run_dir, lambda m: None, lambda c: rc)
                self.assertNotIn(step["done_when"], self.done)


if __name__ == "__main__":
    unittest.main()
