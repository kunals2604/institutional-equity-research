"""v4.0 Step 10: the operating surface — the main session's guard, the owner's skills, the scoreboard's new fields."""

import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import guard  # noqa: E402
import research_lib as rl  # noqa: E402
import scoreboard as sb  # noqa: E402

SKILLS = ("run-status", "switches", "scan", "triage", "deepen", "refresh", "decide", "ic", "rank", "postmortem")
PAID = ("triage", "deepen", "refresh")


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="eqr-guard-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.addCleanup(setattr, guard, "ROOT", guard.ROOT)
        guard.ROOT = self.root
        for rid, status in (("20261001T000000Z", "complete"), ("20261102T000000Z", "stage_3")):
            run = self.root / "research" / "companies" / "ACME" / "runs" / rid
            (run / "cio").mkdir(parents=True)
            (run / "synthesis" / "sections").mkdir(parents=True)
            rl.write_json(run / rl.RUN_MANIFEST, {"run_id": rid, "status": status})
            (run / "cio" / "final_report.md").write_text("assembled", encoding="utf-8")
        self.done = "research/companies/ACME/runs/20261001T000000Z"
        self.live = "research/companies/ACME/runs/20261102T000000Z"

    def edit(self, path):
        return guard.decide({"tool_name": "Edit", "tool_input": {"file_path": path}})

    def bash(self, cmd):
        return guard.decide({"tool_name": "Bash", "tool_input": {"command": cmd}})

    def test_what_is_never_hand_edited(self):
        self.assertIn("finalize_run.py", self.edit("COMPANY_SCOREBOARD.csv"))
        self.assertIn("finalize_run.py", self.edit("research/companies/ACME/latest_run.txt"))
        self.assertIn("non-operative", self.edit("archive/old_agent.md"))
        self.assertIn("rule 5", self.edit(self.done + "/qc/quality_control.md"))
        self.assertIn("synthesis.py assemble", self.edit(self.live + "/cio/final_report.md"))

    def test_what_stays_editable(self):
        for path in (self.live + "/cio/sections/04_verdict.md", self.live + "/cio/scorecard_inputs.json", "scripts/scan.py",
                     str(self.root / self.live / "specialists" / "financials.md")):
            self.assertEqual(self.edit(path), "", path)

    def test_a_report_not_yet_assembled_may_be_written(self):
        (self.root / self.live / "synthesis" / "sections").rmdir()
        self.assertEqual(self.edit(self.live + "/cio/final_report.md"), "")

    def test_shell_writes_are_caught_and_reads_are_not(self):
        self.assertTrue(self.bash("echo x >> COMPANY_SCOREBOARD.csv"))
        self.assertTrue(self.bash("sed -i '' 's/a/b/' %s/cio/final_report.md" % self.done))
        self.assertTrue(self.bash("cp /tmp/x %s/qc/x.md" % self.done))
        self.assertTrue(self.bash("rm -f archive/a.md"))
        self.assertTrue(self.bash("mv %s/qc/x.md /tmp/" % self.done))
        for cmd in ("cat COMPANY_SCOREBOARD.csv", "cp %s/cio/final_report.md /tmp/r.md" % self.done,
                    "grep -n x archive/a.md > /tmp/out", "python3 scripts/finalize_run.py %s" % self.live,
                    "python3 scripts/synthesis.py assemble %s" % self.live):
            self.assertEqual(self.bash(cmd), "", cmd)

    def test_it_fails_closed(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "guard.py")], input="not json", capture_output=True, text=True)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_it_is_installed_for_the_main_session(self):
        hooks = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
        self.assertTrue(any("guard.py" in h["command"] and "Bash" in e["matcher"] and "Edit" in e["matcher"]
                            for e in hooks for h in e["hooks"]))


class SkillTests(unittest.TestCase):
    def test_every_owner_skill_exists_and_runs_real_commands(self):
        for name in SKILLS:
            text = (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\nname: %s\n" % name), name)
            for script in set(re.findall(r"scripts/([a-z_]+\.py)", text)):
                self.assertTrue((ROOT / "scripts" / script).exists(), "%s names %s" % (name, script))

    def test_the_skills_that_spend_run_only_when_the_owner_asks(self):
        for name in SKILLS:
            text = (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertEqual("disable-model-invocation: true" in text, name in PAID, name)

    def test_decide_never_supplies_the_decision(self):
        text = (ROOT / ".claude" / "skills" / "decide" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("never infer it", text)


class ScoreboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-sb-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.board = self.tmp / "board.csv"

    def row(self, version="4.0.0", **kw):
        r = {"company": "Acme", "ticker": "ACME", "exchange": "NSE", "assessment_date": "2026-11-04",
             "latest_run_id": "20261104T000000Z", "price": "100", "currency": "INR", "price_timestamp": "close",
             "methodology_version": version, "business_quality_score": "70", "investment_attractiveness_score": "55",
             "preset": "standard", "verdict": "WATCHLIST", "primary_layer": "Layer 1", "sector": "fmcg",
             "confidence": "Medium/High", "expected_irr_5y": "0.14"}
        r.update(kw)
        return r

    def test_a_v4_row_carries_the_six_fields(self):
        sb.write_header_if_missing(self.board)
        sb.upsert(self.board, self.row())
        self.assertEqual(sb.read_rows(self.board)[0]["verdict"], "WATCHLIST")
        with self.assertRaises(sb.ScoreboardError):
            sb.upsert(self.board, self.row(latest_run_id="20261105T000000Z", verdict="n/a"))

    def test_a_pre_4_row_records_them_as_not_recorded(self):
        sb.write_header_if_missing(self.board)
        r = {k: v for k, v in self.row("2.2.0").items() if k in sb.LEGACY_COLUMNS}
        sb.upsert(self.board, r)
        self.assertEqual(sb.read_rows(self.board)[0]["preset"], "n/a")

    def test_the_old_header_is_read_until_rewritten(self):
        with self.board.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=sb.LEGACY_COLUMNS)
            w.writeheader()
            w.writerow({k: v for k, v in self.row("2.2.0", ticker="OLD").items() if k in sb.LEGACY_COLUMNS})
        self.assertEqual(sb.read_rows(self.board)[0]["verdict"], "n/a")
        sb.upsert(self.board, self.row())
        self.assertEqual(rl.read_csv(self.board)[0], sb.COLUMNS, "written with the new header")
        self.assertEqual(len(sb.read_rows(self.board)), 2)

    def test_values_are_checked(self):
        self.assertTrue(sb.validate_rows([self.row(confidence="Sure")]))
        self.assertTrue(sb.validate_rows([self.row(expected_irr_5y="high")]))
        self.assertEqual(sb.validate_rows([self.row()]), [])


if __name__ == "__main__":
    unittest.main()
