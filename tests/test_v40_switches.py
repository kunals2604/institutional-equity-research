"""Step 3: depth is a dial, recorded and disclosed; the run contract; the spend ceiling."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import research_lib as rl  # noqa: E402
import switches  # noqa: E402
import synthesis  # noqa: E402
import verify  # noqa: E402

PY = sys.executable


def new_run(tmp, *extra):
    r = subprocess.run([PY, str(ROOT / "scripts" / "new_run.py"), "--ticker", "FIXCO", "--company", "FixCo Ltd", "--exchange", "NSE",
                        "--segment", "main", "--root", str(tmp)] + list(extra), capture_output=True, text=True)
    return r, (tmp / r.stdout.strip()) if r.returncode == 0 else None


class ResolveTests(unittest.TestCase):
    def test_the_default_is_standard(self):
        self.assertEqual(switches.resolve()["profile"], "standard")

    def test_a_set_changes_one_switch(self):
        r = switches.resolve("lean", ["effort=xhigh"])
        self.assertEqual(r["values"]["effort"], "xhigh")
        self.assertEqual(r["values"]["specialists"], "core")

    def test_numbers_and_none_parse(self):
        self.assertEqual(switches.resolve("lean", ["history_years=10"])["values"]["history_years"], 10)
        self.assertIsNone(switches.resolve("lean", ["spend_ceiling=none"])["values"]["spend_ceiling"])
        self.assertEqual(switches.resolve("lean", ["spend_ceiling=200"])["values"]["spend_ceiling"], 200)

    def test_an_unknown_switch_or_value_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unknown switch"):
            switches.resolve("lean", ["depth=lots"])
        with self.assertRaisesRegex(ValueError, "cannot be"):
            switches.resolve("lean", ["effort=extreme"])
        with self.assertRaisesRegex(ValueError, "unknown profile"):
            switches.resolve("heavy")

    def test_turning_reading_on_moves_what_depends_on_it(self):
        v = switches.resolve("standard", ["reading=on"])["values"]
        self.assertEqual((v["reading"], v["digest"]), ("on", "off"))

    def test_turning_reading_off_moves_it_back(self):
        v = switches.resolve("deep", ["reading=off"])["values"]
        self.assertEqual((v["digest"], v["second_reads"]), ("on", "off"))

    def test_an_impossible_combination_is_refused(self):
        with self.assertRaisesRegex(ValueError, "digest must be on"):
            switches.resolve("standard", ["digest=off"])

    def test_every_preset_is_valid_and_complete(self):
        reg = switches.registry()["switches"]
        for name, p in switches.presets()["profiles"].items():
            self.assertEqual(switches.problems(p["switches"]), [], name)
            self.assertEqual(set(p["switches"]), set(reg), name)


class DisclosureTests(unittest.TestCase):
    def manifest(self, profile):
        r = switches.resolve(profile)
        return {"run_id": "R1", "profile": profile, "switches": r["values"], "reading_mode": r["values"]["reading"]}

    def test_a_lean_run_says_what_it_left_out_and_how_to_go_deeper(self):
        text = switches.disclosure(self.manifest("lean"))
        for needle in ("specialists", "core", "--deepen R1", "--profile deep", "No switch caps"):
            self.assertIn(needle, text)

    def test_the_extra_cost_is_labelled_an_estimate(self):
        self.assertIn("an estimate, not a measurement", switches.disclosure(self.manifest("standard")))

    def test_a_deep_run_has_nothing_to_disclose(self):
        self.assertIn("deepest setting", switches.disclosure(self.manifest("deep")))

    def test_max_is_not_below_deep(self):
        self.assertNotIn("| reading |", switches.disclosure(self.manifest("max")))

    def test_a_run_from_before_switches_reads_as_what_it_was(self):
        values = switches.of_manifest({"reading_mode": "off"})
        self.assertEqual(values["reading"], "off")
        self.assertEqual(values["early_stop"], "off")


class RunCreationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-sw-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_a_run_records_its_switches_and_contract(self):
        r, run = new_run(self.tmp, "--profile", "lean")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = rl.load_json(run / rl.RUN_MANIFEST)
        self.assertEqual(m["profile"], "lean")
        self.assertEqual(m["switches"]["specialists"], "core")
        c = rl.load_json(run / "contract.json")
        self.assertEqual(c["methodology_version"], m["methodology_version"])
        self.assertEqual(c["switches"], m["switches"])
        self.assertIn("gating_patterns", c["materiality"])

    def test_a_core_run_has_six_specialists(self):
        _, run = new_run(self.tmp, "--profile", "lean")
        self.assertEqual(sorted(rl.run_specialists(run)), sorted(switches.registry()["core_specialists"]))
        self.assertEqual(len(rl.load_json(run / rl.RUN_MANIFEST)["specialists"]), 6)

    def test_the_default_run_has_all_of_them(self):
        _, run = new_run(self.tmp)
        self.assertEqual(len(rl.run_specialists(run)), len(rl.SPECIALISTS))

    def test_the_effort_switch_sets_the_override(self):
        _, lean = new_run(self.tmp, "--profile", "lean")
        self.assertEqual(rl.load_json(lean / rl.RUN_MANIFEST)["model"]["effort_override"], "high")

    def test_the_standard_effort_needs_no_override(self):
        _, run = new_run(self.tmp)
        self.assertIsNone(rl.load_json(run / rl.RUN_MANIFEST)["model"]["effort_override"])

    def test_the_old_reading_flag_still_works(self):
        _, run = new_run(self.tmp, "--reading", "on")
        m = rl.load_json(run / rl.RUN_MANIFEST)
        self.assertEqual((m["reading_mode"], m["switches"]["digest"]), ("on", "off"))

    def test_a_bad_switch_is_refused_at_creation(self):
        r, _ = new_run(self.tmp, "--set", "effort=extreme")
        self.assertNotEqual(r.returncode, 0)

    def test_switches_cannot_be_edited_after_creation(self):
        _, run = new_run(self.tmp)
        r = subprocess.run([PY, str(ROOT / "scripts" / "manifest.py"), str(run), "set", "switches.effort=high"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)

    def test_the_ceiling_can_change_and_says_so(self):
        _, run = new_run(self.tmp)
        r = subprocess.run([PY, str(ROOT / "scripts" / "manifest.py"), str(run), "ceiling", "500"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        m = rl.load_json(run / rl.RUN_MANIFEST)
        self.assertEqual(m["switches"]["spend_ceiling"], 500.0)
        self.assertIn("spend_ceiling", m["notes"][-1]["text"])

    def test_the_mode_command_keeps_the_switches_and_contract_in_step(self):
        _, run = new_run(self.tmp)
        r = subprocess.run([PY, str(ROOT / "scripts" / "manifest.py"), str(run), "mode", "reading", "on", "--reason", "more depth"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(rl.load_json(run / rl.RUN_MANIFEST)["switches"]["digest"], "off")
        self.assertEqual(rl.load_json(run / "contract.json")["switches"]["reading"], "on")

    def test_a_run_keeps_the_rules_it_started_under(self):
        _, run = new_run(self.tmp)
        c = rl.load_json(run / "contract.json")
        c["materiality"]["gating_patterns"] = ["\\bzebra\\b"]
        rl.write_json(run / "contract.json", c)
        self.assertEqual(synthesis.run_rules(run)["gating_patterns"], ["\\bzebra\\b"])

    def test_a_run_with_no_contract_takes_the_current_rules(self):
        self.assertEqual(synthesis.run_rules(self.tmp), synthesis.materiality_rules())


class HonestyTests(unittest.TestCase):
    def test_an_unwired_switch_is_listed_in_the_reference(self):
        for name in switches.registry().get("not_yet_wired", {}):
            self.assertIn("`%s`:" % name, switches.docs_text())

    def test_every_estimate_says_how_far_to_trust_it(self):
        for name, p in switches.presets()["profiles"].items():
            self.assertTrue(p["estimate_status"], name)
        self.assertIn("unmeasured", switches.presets()["profiles"]["lean"]["estimate_status"])


class DepthStandardTests(unittest.TestCase):
    def test_a_shorter_history_switch_lowers_only_the_year_minimums(self):
        res = rl.Result("x")
        rl.check_coverage("financials", "## Historical Financial Summary\n" + " ".join("FY%d" % y for y in range(2019, 2026)), {}, res,
                          history_years=7)
        self.assertEqual([e for e in res.errors if "fiscal years" in e], [])

    def test_the_standard_still_applies_without_it(self):
        res = rl.Result("x")
        rl.check_coverage("financials", "## Historical Financial Summary\n" + " ".join("FY%d" % y for y in range(2019, 2026)), {}, res)
        self.assertTrue(res.errors)


if __name__ == "__main__":
    unittest.main()
