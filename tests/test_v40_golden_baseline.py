"""The one real finished run stays exactly as it was, and old contracts keep judging it the same way."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import golden_tools as gt  # noqa: E402


@unittest.skipUnless(gt.RUN.exists() and gt.BASELINE.exists(), "the golden run is not on this machine")
class GoldenBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = gt.baseline()

    def test_the_run_files_are_unchanged(self):
        self.assertEqual(gt.run_files(), self.base["files"])

    def test_validator_output_is_unchanged_at_both_stages(self):
        for stage in ("specialists", "final"):
            self.assertEqual(gt.validator_output(stage), self.base["validator"][stage], stage)

    def test_the_registry_parses_the_real_reports_completely(self):
        tmp = Path(tempfile.mkdtemp(prefix="eqr-golden-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        got = gt.registry_summary(gt.registry_items(gt.scratch_copy(tmp)))
        self.assertNotIn("unparsed", got["kind"])
        self.assertEqual(got["author"], self.base["registry_3_2_0"]["author"])
        self.assertEqual(got["items"], self.base["registry_3_2_0"]["items"])


if __name__ == "__main__":
    unittest.main()
