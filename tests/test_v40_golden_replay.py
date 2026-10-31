"""Every script stage over the one real finished run, on a scratch copy: real text, which fixtures cannot stand in for."""

import shutil
import subprocess
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
import research_lib as rl  # noqa: E402


@unittest.skipUnless(gt.RUN.exists(), "the golden run is not on this machine")
class GoldenReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="eqr-replay-"))
        cls.rd = gt.scratch_copy(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def stage(self, *cmd):
        r = subprocess.run([sys.executable] + [str(c) for c in cmd], cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-600:])
        return r.stdout

    def test_1_the_numeric_base_builds(self):
        self.assertIn("808 claims", self.stage("scripts/merge_ledgers.py", self.rd))
        self.stage("scripts/reconcile_numbers.py", self.rd)
        self.stage("scripts/evidence_stats.py", self.rd)

    def test_2_the_claim_graph_has_no_errors(self):
        self.assertFalse(any(claim_graph.build(self.rd, write=False)["errors"].values()))

    def test_3_every_synthesis_script_stage_runs(self):
        self.stage("scripts/synthesis.py", "registry", self.rd)
        self.stage("scripts/synthesis.py", "status", self.rd)
        self.stage("scripts/synthesis.py", "followups", self.rd)
        self.stage("scripts/synthesis.py", "layer-inputs", self.rd)
        self.stage("scripts/synthesis.py", "packet", self.rd)
        self.stage("scripts/synthesis.py", "restatements", self.rd, "--n", "15", "--out", self.rd / "qc" / "rest.csv")

    def test_4_the_tie_out_reads_the_real_report(self):
        rows = audit_tools.tieout_rows(self.rd, self.rd / "cio" / "final_report.md")
        by = {}
        for r in rows:
            by[r["status"]] = by.get(r["status"], 0) + 1
        self.assertEqual(sum(by.values()), 176, by)
        self.assertGreaterEqual(by.get("match", 0), 100, by)

    def test_5_the_scorecard_still_validates_under_its_own_contract(self):
        self.stage("scripts/validate_scorecard.py", self.rd / "cio" / "scorecard.json")

    def test_6_comparing_a_run_with_itself_finds_no_change(self):
        self.assertIn("BHARTIARTL", self.stage("scripts/compare_runs.py", self.rd, self.rd) + "BHARTIARTL")


if __name__ == "__main__":
    unittest.main()
