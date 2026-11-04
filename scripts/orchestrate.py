#!/usr/bin/env python3
"""The pipeline: which step comes next, run from the steps in config/pipeline.json.

  python3 scripts/orchestrate.py plan   [--profile lean|standard|deep|max] [--set name=value]   # the steps; writes nothing
  python3 scripts/orchestrate.py next   RUN_DIR     # the next step, computed from the manifest and the disk
  python3 scripts/orchestrate.py run    RUN_DIR     # runs script and agent steps until a judgment step or a failure
  python3 scripts/orchestrate.py status RUN_DIR     # where the run is, what it has spent, how to go deeper
  python3 scripts/orchestrate.py explain <step>

Code runs the process and agents supply judgment. `next` is a pure function of the manifest and the disk, so it survives
any crash, compaction or lost session: open a fresh session and ask again. `run` stops at every `cio` step with its stage
skill, its output and its check; the CIO stays in the main session, one fresh session per stage.

Exit: `next` 0 with a step, 3 when the run is finished. `run` 0 at a judgment step or the end, 1 when a step failed.
"""

import argparse
import datetime as dt
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import switches  # noqa: E402

STAGE_SKILLS = {"0": "cio-stage-0", "0b": "cio-stage-0", "0c": "cio-stage-0", "1": "cio-stage-1", "2": "cio-stage-1",
                "3": "cio-stage-3", "4": "cio-stage-4"}


def pipeline() -> List[dict]:
    return rl.load_json(rl.ROOT / "config" / "pipeline.json")["steps"]


def manifest(run: Path) -> dict:
    return rl.load_json(run / rl.RUN_MANIFEST)


def exists(run: Path, *rels: str) -> bool:
    return all((run / r).exists() for r in rels)


def nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def has_data_rows(path: Path, least: int = 1) -> bool:
    if not path.exists():
        return False
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) > least


def filled(run: Path, rel: str) -> bool:
    """Written by someone: no longer the template new_run copied in (it records each one's checksum)."""
    p = run / rel
    if not nonempty(p):
        return False
    return hashlib.sha256(p.read_bytes()).hexdigest() != status_json(run, "engine/templates.json").get(rel)


def status_is(run: Path, *values: str) -> bool:
    return manifest(run).get("status") in values


def invoked(run: Path, agent: str) -> bool:
    m = manifest(run)
    for group in (m.get("workers") or {}, m.get("specialists") or {}, {"auditor": m.get("auditor") or {}}):
        if (group.get(agent) or {}).get("invocations"):
            return True
    return False


def missing_documents(run: Path) -> bool:
    p = run / "corpus" / "document_map.csv"
    if not p.exists():
        return False
    with p.open(encoding="utf-8", newline="") as f:
        import csv
        return any((r.get("status") or "") in ("missing", "download_failed") for r in csv.DictReader(f))


def key_question_errors(run: Path) -> List[str]:
    """Three to ten questions, and only questions: what the price implies stays out of the briefs until the forecast is
    committed, or it would anchor the work it is meant to test."""
    p = run / "engine" / "key_questions.md"
    if not p.exists():
        return ["engine/key_questions.md does not exist yet"]
    lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if re.match(r"\s*\d+[.)]\s", l)]
    errs = [] if 3 <= len(lines) <= 10 else ["write 3 to 10 numbered questions, not %d" % len(lines)]
    errs += ["not a question: %s" % l[:80] for l in lines if not l.rstrip("*_ ").endswith("?")]
    errs += ["a question carries a number that could anchor the work: %s" % l[:80] for l in lines
             if re.search(r"(?:₹|INR|Rs\.?|\$)\s*\d|\d\s*(?:%|x\b|crore|lakh|bn\b|mn\b)", re.sub(r"^\d+[.)]\s", "", l))]
    return errs


def status_json(run: Path, rel: str) -> dict:
    return rl.load_json(run / rel) if (run / rel).exists() else {}


def verification_of(run: Path, stage: str) -> bool:
    v = status_json(run, "qc/verification.json")
    return v.get("status") == "PASS" and (v.get("stage") == stage or stage == "specialists")


def registry_checks(run: Path, fn: str) -> bool:
    import synthesis
    return not getattr(synthesis, fn)(run)


def specialists_pass(run: Path) -> bool:
    """A partly written report exists after a crash, so the validator decides, not the file's presence."""
    import agent_driver as ad
    return all(exists(run, "specialists/%s.md" % n) and not ad.report_check(run, "specialists/%s.md" % n, "specialist")()
               for n in rl.run_specialists(run))


def themes_pass(run: Path) -> bool:
    import synthesis
    if not exists(run, "synthesis/registry.jsonl") or synthesis.stale(run):
        return False
    return not any(synthesis.check_theme(run, t) for t in synthesis.active_themes(run))


def contradictions_adjudicated(run: Path) -> bool:
    import synthesis
    return exists(run, "cio/contradiction_log.md") and not synthesis.followups(run, log=lambda m: None, write=False)["open_candidates"]


def followups_closed(run: Path) -> bool:
    import synthesis
    disp = synthesis.all_dispositions(run)
    return not synthesis.handoff_errors(run) and not any(d["disposition"] == "needs_follow_up" for d in disp.values())


def layers_pass(run: Path) -> bool:
    import synthesis
    return exists(run, "synthesis/CIO_PACKET.md") and not any(synthesis.check_layer(run, L) for L in synthesis.LAYERS)


def writers_pass(run: Path) -> bool:
    import synthesis
    return not any(synthesis.check_section(run, w) for w in synthesis.writer_groups(run))


def report_assembled(run: Path) -> bool:
    import synthesis
    return exists(run, "cio/final_report.md") and not synthesis.integration(run, write=False)["errors"]


def audit_resolved(run: Path) -> bool:
    res = rl.Result("audit resolutions")
    text = (run / rl.AUDIT_REPORT).read_text(encoding="utf-8") if exists(run, rl.AUDIT_REPORT) else ""
    if not text:
        return False
    rl.check_audit_resolutions(run, rl.audit_findings(text), res)
    return res.ok


def qc_done(run: Path) -> bool:
    return exists(run, rl.QC_RECORD) and "QC status: PASS" in (run / rl.QC_RECORD).read_text(encoding="utf-8")


def git_batch_done(run: Path, batch: str) -> bool:
    return bool((manifest(run).get("git") or {}).get(batch))


CHECKS: Dict[str, Callable[[Path], bool]] = {
    "identity_done": lambda r: bool((manifest(r).get("price") or {}).get("value")) and filled(r, "research_brief.md"),
    "document_map_built": lambda r: exists(r, "corpus/DOCUMENT_MAP.md", "corpus/STRUCTURED.md"),
    "no_document_gaps": lambda r: not missing_documents(r) or invoked(r, "librarian"),
    "events_done": lambda r: exists(r, "corpus/events.csv", "corpus/EVENTS.md"),
    "facts_materialised": lambda r: exists(r, "corpus/facts/FACTS.md"),
    "sector_modules_set": lambda r: manifest(r).get("sector_modules") is not None,
    "reading_planned": lambda r: exists(r, "corpus/reading/plan.json"),
    "reading_complete": lambda r: bool(status_json(r, rl.READING_STATUS).get("complete")),
    "digest_planned": lambda r: exists(r, rl.DIGEST_DIR + "/plan.json"),
    "digest_items_done": lambda r: exists(r, rl.DIGEST_DIR + "/SEARCH_LOG.md") and any((r / rl.DIGEST_DIR / "items").glob("*.jsonl")),
    "digest_complete": lambda r: bool(status_json(r, rl.DIGEST_STATUS).get("complete")),
    "identity_block_done": lambda r: nonempty(r / "engine" / "identity.md"),
    "specialists_pass": lambda r: specialists_pass(r),
    "verified_specialists": lambda r: verification_of(r, "specialists"),
    "gaps_recorded": lambda r: filled(r, "cio/gap_register.md"),
    "barrier_passed": lambda r: status_is(r, "specialists_complete", "synthesis", "qc_auto_passed", "qc_auto_failed", "complete"),
    "git_specialists_done": lambda r: git_batch_done(r, "specialists"),
    "numeric_base_done": lambda r: exists(r, "evidence_ledger.csv", "qc/evidence_stats.json"),
    "themes_pass": themes_pass,
    "contradictions_adjudicated": contradictions_adjudicated,
    "followups_closed": followups_closed,
    "key_questions_done": lambda r: not key_question_errors(r),
    "adversarial_done": lambda r: bool(list((r / "specialists").glob("bear-case_followup_*.md"))),
    "cio_analysis_done": lambda r: filled(r, "cio/cio_analysis.md"),
    "layers_pass": layers_pass,
    "decision_done": lambda r: exists(r, "cio/scorecard.json") and any((r / "cio" / "sections").glob("*.md")) if exists(r, "cio/sections") else False,
    "writers_pass": writers_pass,
    "report_assembled": report_assembled,
    "reading_audited": lambda r: exists(r, "qc/READING_AUDIT.md"),
    "audit_done": lambda r: exists(r, rl.AUDIT_REPORT),
    "audit_resolved": audit_resolved,
    "verified_final": lambda r: verification_of(r, "final"),
    "final_validated": lambda r: status_is(r, "qc_auto_passed", "complete"),
    "qc_done": qc_done,
    "finalized": lambda r: status_is(r, "complete", "insufficient_evidence", "incomplete"),
    "promoted": lambda r: exists(r, "qc/promoted.json"),
    "archived": lambda r: run_archived(r),
    "git_final_done": lambda r: git_batch_done(r, "final"),
}


def run_archived(run: Path) -> bool:
    import reading_audit
    return bool(reading_audit.archived_paths(manifest(run).get("run_id", run.name)))


def applies(step: dict, values: Dict[str, object]) -> bool:
    return all(values.get(k) == v for k, v in (step.get("when") or {}).items())


def active_steps(values: Dict[str, object]) -> List[dict]:
    return [s for s in pipeline() if applies(s, values)]


def values_of(run: Path) -> Dict[str, object]:
    return switches.of_manifest(manifest(run))


def is_done(step: dict, run: Path) -> bool:
    return bool(CHECKS[step["done_when"]](run))


def early_stop_open(run: Path) -> Optional[dict]:
    rec = status_json(run, "engine/early_stop.json")
    return rec if rec and not rec.get("decision") else None


def decide_early(run: Path, decision: str, reason: str) -> None:
    """The owner's answer to the early-stop pause."""
    if not reason.strip():
        raise SystemExit("say why: this is the record of the decision")
    rl.update_json(run / "engine" / "early_stop.json", lambda d: d.update(decision=decision, reason=reason, at=rl_now()))
    if decision == "stop":
        rl.update_json(run / rl.RUN_MANIFEST, lambda m: m.update(status="stopped_gate"))


def rl_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def next_step(run: Path) -> Optional[dict]:
    """The first step of this run that is not done. Nothing but the manifest and the disk decides it."""
    if status_is(run, "stopped_gate"):
        return None
    pause = early_stop_open(run)
    if pause:
        return {"id": "early_stop", "stage": "1", "type": "owner", "done_when": "early_stop", "output": "the owner's decision",
                "title": "%s raised a red flag (%s). Read its report, then decide: orchestrate.py decide-early RUN_DIR continue|stop --reason ..." % (
                    pause["agent"], pause["flag"])}
    for s in active_steps(values_of(run)):
        if not is_done(s, run):
            return s
    return None


def command(step: dict, run: Path) -> str:
    return step["run"].replace("{run}", str(run))


def describe(step: dict, run: Optional[Path] = None) -> List[str]:
    lines = ["Stage %s · %s · %s: %s" % (step["stage"], step["id"], step["type"], step["title"])]
    if step["type"] == "owner":
        return lines
    if step["type"] == "cio":
        lines += ["Load the skill `%s`, follow its section for this step, and write: %s" % (STAGE_SKILLS[step["stage"]], step["output"])]
    elif run is not None:
        lines += ["Run: %s" % command(step, run)]
    lines += ["Done when: %s%s" % (step["done_when"], " (offered again until it passes)" if step.get("loop") else "")]
    return lines


def run_steps(run: Path, log=print, runner=None) -> int:
    """Script and agent steps run here, one at a time, until a judgment step, a failure or the end."""
    runner = runner or (lambda cmd: subprocess.run(cmd, shell=True, cwd=str(rl.ROOT)).returncode)
    with rl.locked(run / "engine" / "orchestrate"):
        while True:
            step = next_step(run)
            if step is None:
                log("the run is finished")
                return 0
            if step["type"] in ("cio", "owner"):
                log("\n".join(describe(step, run)))
                return 0
            log("running %s: %s" % (step["id"], step["title"]))
            rc = runner(command(step, run))
            if not is_done(step, run):      # the check decides, not the exit code: a push that failed left the commit done
                log("step %s %s: its check %s fails; see its output, fix the cause and run this again" % (
                    step["id"], "failed (exit %s)" % rc if rc else "ran", step["done_when"]))
                return 1
            if rc:
                log("step %s exited %s, but its check passes: carrying on" % (step["id"], rc))


def status(run: Path) -> str:
    import agent_driver as ad
    m = manifest(run)
    values = values_of(run)
    steps = active_steps(values)
    step = next_step(run)
    done = steps.index(step) if step else len(steps)   # the first unfinished step: a later check may already hold vacuously
    spent = ad.run_cost(run)
    ceiling = values.get("spend_ceiling")
    lines = ["Run %s · %s (%s) · preset %s" % (m.get("run_id"), m.get("ticker"), m.get("status"), m.get("profile") or "(set by hand)"),
             "Steps done: %d of %d" % (done, len(steps)),
             "Next: %s" % (describe(step, run)[0] if step else "nothing: the run is finished"),
             "Spent so far: $%.2f%s (API-equivalent; sleep aborts and other retries are not in this figure)" % (
                 spent, " of a $%.0f ceiling" % float(ceiling) if ceiling else "")]
    lines += ["", switches.disclosure(m)]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--profile")
    p.add_argument("--set", action="append", default=[])
    for name in ("next", "run", "status"):
        sub.add_parser(name).add_argument("run_dir")
    sub.add_parser("explain").add_argument("step")
    de = sub.add_parser("decide-early")
    de.add_argument("run_dir")
    de.add_argument("decision", choices=["continue", "stop"])
    de.add_argument("--reason", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        try:
            r = switches.resolve(a.profile, a.set)
        except ValueError as exc:
            print("ERROR: %s" % exc)
            return 1
        print("Preset %s" % r["profile"])
        for s in active_steps(r["values"]):
            print("  %-3s %-20s %-6s %s" % (s["stage"], s["id"], s["type"], s["title"]))
        pre = switches.presets()["profiles"][r["profile"]]
        print("Estimated usage: %s (%s)" % ("$%.0f" % pre["estimate_usd"] if pre.get("estimate_usd") else "not estimated", pre["estimate_status"]))
        return 0
    if a.cmd == "explain":
        step = next((s for s in pipeline() if s["id"] == a.step), None)
        if step is None:
            print("unknown step %r: %s" % (a.step, ", ".join(s["id"] for s in pipeline())))
            return 1
        print("\n".join(describe(step)))
        return 0
    run = Path(a.run_dir)
    if a.cmd == "decide-early":
        decide_early(run, a.decision, a.reason)
        print("recorded: %s" % a.decision)
        return 0
    if a.cmd == "status":
        print(status(run))
        return 0
    if a.cmd == "run":
        return run_steps(run)
    step = next_step(run)
    if step is None:
        print("the run is finished")
        return 3
    print("\n".join(describe(step, run)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
