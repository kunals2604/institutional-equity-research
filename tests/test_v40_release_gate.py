"""v4.0 Step 11: the release gate — every criterion checked by script, and the owner's own step left to the owner."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import release_gate as rg  # noqa: E402


class Done:
    def __init__(self, rc=0, out=""):
        self.returncode, self.stdout, self.stderr = rc, out, ""


def fake_run(tests_ok=True, caught=18, planted=18):
    def run(cmd, **kw):
        if "validate_system.py" in " ".join(cmd):
            return Done(0, "438 checks, 0 failed: SYSTEM VALID\n")
        return Done(0 if tests_ok else 1, "mutation suite: %d of %d planted errors caught\nRan 700 tests in 60s\n%s" % (
            caught, planted, "OK" if tests_ok else "FAIL: test_x (tests.t.T)"))
    return run


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-gate-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        for name in ("LABELS", "CONFIRMATION", "REGISTER"):
            self.addCleanup(setattr, rg, name, getattr(rg, name))
        rg.LABELS = self.tmp / "labels.csv"
        rg.LABELS.write_text("item,label\nA,required\n", encoding="utf-8")
        rg.CONFIRMATION = self.tmp / "labels.confirmed.json"
        rg.REGISTER = self.tmp / "register.md"
        rg.REGISTER.write_text("| ID | Sev | Item | Known | Status |\n|---|---|---|---|---|\n"
                               "| O1 | H | BSE results | none found | **Open, release item**: measure first |\n"
                               "| O3 | M | US path live | stored data only | Open: the first US run is its test |\n"
                               "| W1 | H | Index page | 20 rows | Fixed |\n", encoding="utf-8")

    def rows(self, **kw):
        return {name: (ok, detail) for name, ok, detail in rg.check(run=fake_run(**kw))}

    def test_open_release_items_block_and_other_open_items_are_only_listed(self):
        blocking, other = rg.open_items()
        self.assertEqual([b.split(":")[0] for b in blocking], ["O1"])
        self.assertEqual([o.split(":")[0] for o in other], ["O3"])
        got = self.rows()
        self.assertFalse(got["no item of the defect register is open for the release"][0])

    def test_unconfirmed_or_changed_labels_block(self):
        self.assertFalse(self.rows()["the owner has confirmed the gating labels"][0])
        rg.main(["confirm-labels", "--by", "the owner"])
        self.assertTrue(rg.labels_confirmed()[0])
        rg.LABELS.write_text("item,label\nA,noise\n", encoding="utf-8")
        ok, why = rg.labels_confirmed()
        self.assertFalse(ok)
        self.assertIn("changed since", why)

    def test_failing_tests_or_a_weak_mutation_suite_block(self):
        self.assertFalse(self.rows(tests_ok=False)["the test suite passes (golden replay, mutation, fault injection, contracts)"][0])
        self.assertFalse(self.rows(caught=17, planted=20)["the mutation suite catches at least 95 % of planted errors"][0])
        self.assertTrue(self.rows()["the mutation suite catches at least 95 % of planted errors"][0])

    def test_skipping_the_tests_cannot_pass(self):
        rows = {n: ok for n, ok, _ in rg.check(skip_tests=True, run=fake_run())}
        self.assertFalse(rows["the test suite passes"])

    def test_it_never_tags_or_pushes(self):
        text = (ROOT / "scripts" / "release_gate.py").read_text(encoding="utf-8")
        self.assertNotIn('"tag"', text)
        self.assertNotIn('"push"', text)

    def test_the_real_register_parses(self):
        rg.REGISTER = ROOT / "docs" / "V4_DEFECT_REGISTER.md"
        blocking, other = rg.open_items()
        self.assertTrue(all(b.startswith("O") for b in blocking))


if __name__ == "__main__":
    unittest.main()
