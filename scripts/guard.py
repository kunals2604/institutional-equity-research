#!/usr/bin/env python3
"""The main session's guard (a PreToolUse hook in .claude/settings.json): files that are built, never hand-edited.

Denied to Write, Edit, MultiEdit and NotebookEdit, and to shell commands that write to them:
- a run's `cio/final_report.md` once it has been assembled: it is a build artifact of `cio/sections/` and
  `synthesis/sections/` (`synthesis.py assemble`); edit the sections and assemble again;
- any file of a finished run (status complete, insufficient_evidence or incomplete): never overwrite a previous run
  (CLAUDE.md rule 5); a change is a new run (`new_run.py --refresh` or `--deepen`);
- `archive/`, which is non-operative;
- `COMPANY_SCOREBOARD.csv` and `latest_run.txt`, which only `scripts/finalize_run.py` writes.

The scripts that legitimately write these files run as `python3 scripts/...` and are not shell writes to the path, so
they pass. Headless agent sessions run with every hook disabled (agent_driver.ISOLATION): this binds the CIO only.
It fails closed: if the guard itself fails, the tool call is denied with the reason, never waved through. It is a
convenience, not the gate: the validators remain the real check.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
REDIRECT = re.compile(r"(?<![<>&\d])>>?\s*(?P<path>[^\s'\";|&<>]+)")
FINAL = {"complete", "insufficient_evidence", "incomplete"}


def reason_for(path_text: str) -> str:
    """Why this path may not be hand-edited, or "" when it may."""
    try:
        p = Path(path_text)
        p = (p if p.is_absolute() else ROOT / p).resolve()
        rel = p.relative_to(ROOT.resolve())
    except (ValueError, OSError):
        return ""
    parts = rel.parts
    if parts and parts[0] == "archive":
        return "archive/ is non-operative and is never edited"
    if rel.name == "COMPANY_SCOREBOARD.csv" or rel.name == "latest_run.txt":
        return "%s is written only by scripts/finalize_run.py" % rel.name
    if len(parts) >= 5 and parts[0] == "research" and parts[1] == "companies" and parts[3] == "runs":
        run = ROOT.joinpath(*parts[:5])
        try:
            status = json.loads((run / "run_manifest.json").read_text(encoding="utf-8")).get("status")
        except (OSError, ValueError):
            status = None
        if status in FINAL:
            return ("run %s is finished (%s): a previous run is never overwritten (CLAUDE.md rule 5); make a new one with "
                    "new_run.py --refresh or --deepen" % (parts[4], status))
        if parts[5:] == ("cio", "final_report.md") and (run / "cio" / "final_report.md").exists() and \
                (run / "synthesis" / "sections").is_dir():
            return ("cio/final_report.md is assembled from cio/sections/ and synthesis/sections/: edit the section and run "
                    "python3 scripts/synthesis.py assemble %s" % run.relative_to(ROOT))
    return ""


def decide(event: dict) -> str:
    tool = event.get("tool_name") or ""
    inp = event.get("tool_input") or {}
    if tool in WRITE_TOOLS:
        return reason_for(inp.get("file_path") or inp.get("notebook_path") or "")
    if tool == "Bash":
        for path in shell_targets(inp.get("command") or ""):
            why = reason_for(path)
            if why:
                return why
    return ""


def shell_targets(cmd: str) -> list:
    """The paths a shell command writes: a redirect's target; every file of rm, tee, truncate, sed -i and perl -i; the
    destination of cp; both ends of mv (moving a file out changes where it was). Reading a protected file is fine."""
    import shlex
    out = [m.group("path") for m in REDIRECT.finditer(cmd)]
    for part in re.split(r"&&|\|\||[;|\n]", cmd):
        try:
            words = shlex.split(part)
        except ValueError:
            words = part.split()
        while words and re.fullmatch(r"\w+=\S*|sudo|command|exec", words[0]):
            words = words[1:]
        if not words:
            continue
        prog, args = Path(words[0]).name, [w for w in words[1:] if not w.startswith("-")]
        inplace = any(re.fullmatch(r"-[a-zA-Z]*i\S*", w) for w in words[1:])
        if prog in ("rm", "tee", "truncate", "unlink", "shred") or (prog in ("sed", "perl") and inplace):
            out += args
        elif prog == "cp" and args:
            out.append(args[-1])
        elif prog == "mv":
            out += args
    return out


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": "guard.py: " + reason}}))


def main() -> int:
    try:
        why = decide(json.loads(sys.stdin.read() or "{}"))
    except Exception as exc:                          # fail closed
        deny("the guard could not check this call (%s); it is denied rather than let through" % exc)
        return 0
    if why:
        deny(why)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
