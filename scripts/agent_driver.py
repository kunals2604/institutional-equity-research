#!/usr/bin/env python3
"""The execution engine: runs the system's agents as headless Claude Code sessions, outside the CIO's context.

  python3 scripts/agent_driver.py reading     RUN_DIR [--parallel N] [--bakeoff] [--max-launches N]   # Stage 0b
  python3 scripts/agent_driver.py librarian   RUN_DIR --message-file F                                # Stage 0
  python3 scripts/agent_driver.py specialists RUN_DIR [--only a,b] [--parallel N]                     # Stage 1
  python3 scripts/agent_driver.py verify      RUN_DIR [--only a,b]                                    # the verifier
  python3 scripts/agent_driver.py followup    RUN_DIR AGENT --message-file F --purpose "<why>" [--stage 2|3|4] [--output REL]
  python3 scripts/agent_driver.py audit       RUN_DIR --message-file F                                # Stage 4
  python3 scripts/agent_driver.py prompt      RUN_DIR SPECIALIST    # the filled Stage-1 brief (for the Agent-tool fallback)
  python3 scripts/agent_driver.py show        RUN_DIR [--last N]    # every session: time, tokens, cost, usage used
  python3 scripts/agent_driver.py usage       [--probe]             # the account's five-hour and weekly utilization
  python3 scripts/agent_driver.py probe                             # configuration check of one specialist, no research
  python3 scripts/agent_driver.py cli                               # the claude binary it would use
Common options of the commands that run agents: --timeout-min, --max-wait-hours, --weekly-ceiling, --parallel-ceiling,
--context-limit, --segment-turns, --claude, --dry-run.

Why. Measured on this machine (2026-10-19): a five-hour usage window holds about $28 of API-equivalent work. An agent
launched through the Agent tool costs CIO turns that each re-read the CIO's whole context, and a subagent's prompt
cache lives five minutes, so a specialist rewrote its 450k-token context into the cache 5-6 times (a third of its
cost), while each of its 100-145 calls re-read a context that grew to 355-505k tokens. Here every agent is its own
headless session (`claude -p --agent <name>`): no CIO turns, a one-hour cache, and a context that never grows past
--context-limit, because a long agent is handed over to a fresh session that continues from its own files.

The engine changes how an agent runs, never what it does or what it sees:
  * Independence (the owner's rule: the specialists are separate heads of an institutional fund). Each agent runs in
    its own session with its own definition, prompt and pinned model and effort (`methodology/MODEL_POLICY.md`). No
    context is shared or merged. Shared inputs are facts gathered once (document map, structured filings, reading
    dossiers, downloaded documents), never another agent's work. A specialist's permission profile denies reading
    any other specialist's files, cio/, audit/, qc/, the engine's records, other runs, archive/, the scoreboard and
    agent transcripts, and lets it write only its own files. Because a shell can bypass a read rule, the engine also
    fingerprints every file the agent must not touch before and after each segment (`integrity` on the job), and
    `reading_audit.py` scans every specialist transcript for any contact with another specialist's work.
  * Depth. Nothing is shortened. A segment ends after --segment-turns turns only so the engine can look at the
    context size: below --context-limit the same session simply continues; above it the agent is asked to finish
    its current method step and write everything to disk (progress.md: steps done, exact next step, open threads),
    then a fresh session continues from those files. The completion check is the same validator the CIO runs.
  * Usage. Every session streams the account's utilization (`rate_limit_event`: five-hour and weekly windows). A
    usage limit is waited out and the same session resumed. No segment starts while the weekly window is above
    --weekly-ceiling (a reserve for the owner's own use). With --parallel N, another session starts only while the
    five-hour window is below --parallel-ceiling, so parallel sessions do not all stop half-done at the same limit.
    `show` reports the measured cost of a window from the sessions' cost and utilization.

Records: reader sessions on their launches (corpus/reading/launches.json); every other job in RUN_DIR/engine/jobs.json
(model, effort, sessions, segments, cost, utilization before and after, outcome, integrity) and engine/ENGINE.md.
`reading_audit.py` checks every headless session from these records exactly as it checks a subagent. One engine per
run (a lock); stop it at any time and run it again: it resumes the open sessions. On macOS it keeps the machine awake
(caffeinate) while it runs.

Exit: 0 everything asked for passed its check; 1 something failed or a usage window resets later than
--max-wait-hours (run it again after the reset); 2 usage.
"""

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reading  # noqa: E402
import research_lib as rl  # noqa: E402

# Sessions -------------------------------------------------------------------------------------------------------
FIX_ROUNDS = 2                 # readers: resumes with the check's errors before a launch is closed as failed
FIX_ROUNDS_REPORT = 3          # specialists, follow-ups, auditor: resumes with the validator's errors
RESUME_TRIES = 2               # resumes after a crash or timeout before a session is given up
RESTARTS = 1                   # readers: fresh restarts of the same chunks before they are skipped
CONTINUATIONS = 12             # fresh sessions one assignment may use (a guard against a loop, not a depth limit)
SEGMENT_TURNS = 25             # long agents: turns per segment, after which the engine looks at the context
CHECKPOINT_TURNS = 30          # turns allowed to finish the current step and write the checkpoint
CONTEXT_LIMIT = 250000         # above this a long agent continues in a fresh session (average context about half)
LIMIT_SLACK_S = 90             # wait this long past a usage limit's reset time
LIMIT_FALLBACK_S = 15 * 60     # when the reset time cannot be read, try again after this long
WEEKLY_CEILING = 0.95          # no segment starts above this share of the weekly window (the owner's reserve)
PARALLEL_CEILING = 0.60        # with --parallel, another session starts only below this share of the five-hour window
USAGE_STALE_S = 15 * 60        # utilization older than this is refreshed with a one-line probe before a new session
POLL_S = 5
LIMIT_RE = re.compile(r"(session|usage|weekly|daily|rate|5-hour|five.hour) limit|hit your limit|limit reached|"
                      r"usage_limit", re.I)
# Variables that tie a process to the Claude Code session that started it (the engine usually runs inside the CIO's
# session): a child must not inherit them. CLAUDE_EFFORT would even override the pinned --effort.
KEEP_ENV = {"CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY", "CLAUDE_CODE_OAUTH_TOKEN",
            "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "CLAUDE_CONFIG_DIR"}
DROP_ENV = {"CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT", "CLAUDE_AGENT_SDK_VERSION"}
DENY_SECRETS = ["Read(~/.ssh/**)", "Read(~/.aws/**)", "Read(~/.config/**)", "Read(~/.gnupg/**)", "Read(~/.netrc)",
                "Read(~/.claude.json)", "Read(~/Library/Keychains/**)"]
# Other agents' sessions. (Not the whole projects folder: an agent reads back its own large tool outputs, which Claude
# Code keeps in ~/.claude/projects/<project>/<session>/tool-results/; the audit checks they are its own.)
DENY_TRANSCRIPTS = ["Read(~/.claude/projects/*/*.jsonl)", "Read(~/.claude/projects/*/*/subagents/**)"]
CIO_ONLY_SCRIPTS = ("git_publish.py", "finalize_run.py", "scoreboard.py", "manifest.py", "build_scorecard.py",
                    "merge_ledgers.py", "agent_driver.py", "reading_audit.py", "new_run.py")
SPECIALIST_ORDER = ("financials", "filings", "industry", "scuttlebutt", "moat", "management", "concalls", "valuation",
                    "special-situations", "bear-case")
SPECIALIST_PROMPT = rl.ROOT / "templates" / "specialist_prompt.md"

READER_RESUME_MSG = ("You were interrupted (a usage limit, an error or a timeout). Continue your launch exactly where you "
                     "stopped: run the check command of each chunk in your launch file to see what is done, keep the parts "
                     "you have written, write the rest, and run the check until it prints PASS. Then give your one-line "
                     "result.")
READER_FIX_MSG = ("The reading check still fails:\n%s\nFix every error in the part file it names (Edit tool), re-run the "
                  "check until it prints PASS, then give your one-line result.")
RESUME_MSG = ("You were interrupted (a usage limit, an error or a timeout). Continue exactly where you stopped, at the "
              "full standard of your definition: keep everything already written, check %s, and continue from the step "
              "in progress.")
CONTINUE_MSG = "Continue your assignment exactly where you are, at the full standard of your definition."
CHECKPOINT_MSG = ("The engine will continue your assignment in a fresh session: this session's context has passed "
                  "{limit:,} tokens, and every further turn would re-read all of it. Finish the step you are in (do not "
                  "start another), then make sure everything is on disk: the report sections and ledger rows so far, "
                  "your workpapers, and {progress} with the steps done, the exact next step, the open threads, the "
                  "sources still to read and anything else the next session needs to continue at full depth. Then reply "
                  "with one line: CHECKPOINTED.")
CONTINUATION_NOTE = ("\n\nCONTINUATION (session {k} of this assignment). An earlier session of yours carried out the work "
                     "recorded in {progress} and handed over because its context had grown large; nothing was lost, the "
                     "work is on disk. Before anything else, re-read {progress}, your research plan, your report draft "
                     "and ledger, and the workpapers and sources your remaining steps use. Then continue from the next "
                     "unfinished step at the full standard of your Method. Do not redo completed steps, and do not "
                     "shorten, sample or summarize anything because of the hand-over.")
REPORT_FIX_MSG = ("Your work does not pass its checks yet (the report validator and the verification of your work against "
                  "what your sessions read and opened):\n%s\nFix every item (report, ledger, checklist, sources), re-run "
                  "the validator until it passes, then give your return message.")
POLISH_MSG = ("Your report passes. The verification of your work also found these issues; fix each one now (it is "
              "checked again):\n%s\nThen give your return message.")
VERIFY_ROUNDS = 2              # times a specialist is sent the verifier's discrepancies before they go to the CIO


# --------------------------------------------------------------------------------------------------------------
# The CLI
# --------------------------------------------------------------------------------------------------------------

def find_claude(explicit: Optional[str] = None) -> Optional[str]:
    """The claude binary: --claude, $CLAUDE_BIN, PATH, ~/.claude/local, or the newest one an editor extension ships."""
    for c in (explicit, os.environ.get("CLAUDE_BIN"), shutil.which("claude"), str(Path.home() / ".claude" / "local" / "claude")):
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return c
    found = []
    for base in (".vscode/extensions", ".vscode-insiders/extensions", ".cursor/extensions", ".windsurf/extensions"):
        found += [p for p in (Path.home() / base).glob("anthropic.claude-code-*/resources/native-binary/claude")
                  if os.access(str(p), os.X_OK)]

    def version(p: Path) -> Tuple[int, ...]:
        m = re.search(r"claude-code-(\d+)\.(\d+)\.(\d+)", str(p))
        return tuple(int(x) for x in m.groups()) if m else (0,)
    return str(max(found, key=version)) if found else None


def claude_version(claude: str) -> str:
    try:
        return subprocess.run([claude, "--version"], capture_output=True, text=True, timeout=60,
                              env=child_env()).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def child_env() -> Dict[str, str]:
    env = {}
    for k, v in os.environ.items():
        if k in KEEP_ENV or not (k in DROP_ENV or k.startswith("CLAUDE_CODE_")):
            env[k] = v
    return env


def outside(path: Path, roots: List[Path]) -> bool:
    p = path.resolve()
    for r in roots:
        try:
            p.relative_to(r.resolve())
            return False
        except ValueError:
            continue
    return True


def abs_rule(tool: str, path: Path, suffix: str = "") -> str:
    """A permission rule on an absolute path (`Write(//Users/...)`)."""
    return "%s(/%s%s)" % (tool, path.resolve(), suffix)


def agent_tools(agent: str) -> List[str]:
    """The tools an agent's definition grants (its frontmatter), so a headless session has exactly those."""
    text = (rl.AGENTS_DIR / ("%s.md" % agent)).read_text(encoding="utf-8")
    m = re.search(r"^tools:\s*(.+)$", text, re.M)
    return [t.strip() for t in m.group(1).split(",")] if m else ["Read", "Write", "Edit", "Bash"]


def agent_skills(agent: str) -> List[str]:
    """The skills an agent's definition preloads (`skills:` in its frontmatter)."""
    text = (rl.AGENTS_DIR / ("%s.md" % agent)).read_text(encoding="utf-8")
    m = re.search(r"^skills:\s*\n((?:\s+-\s*\S+\s*\n)+)", text, re.M)
    return re.findall(r"-\s*(\S+)", m.group(1)) if m else []


def skills_prompt(agent: str, out_dir: Path) -> Optional[Path]:
    """Claude Code preloads an agent's `skills:` only into a subagent, never into a headless main session (measured
    2026-10-19: the probe answered PRELOADED=N), so the engine appends them to the session's system prompt itself:
    the specialists and the auditor work under the investment constitution exactly as they would as subagents."""
    skills = agent_skills(agent)
    if not skills:
        return None
    parts = ["The following skills are preloaded into your context (they are part of your instructions):", ""]
    for s in skills:
        path = rl.ROOT / ".claude" / "skills" / s / "SKILL.md"
        body = path.read_text(encoding="utf-8")
        body = re.sub(r"\A---\n.*?\n---\n", "", body, flags=re.S)
        parts += ["<skill name=\"%s\">" % s, body.strip(), "</skill>", ""]
    out = out_dir / ("%s.md" % agent)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(parts)
    if not out.exists() or out.read_text(encoding="utf-8") != text:
        out.write_text(text, encoding="utf-8")
    return out


def library_dir() -> Optional[Path]:
    cfg = rl.ROOT / "config" / "data_sources.json"
    try:
        p = Path(json.loads(cfg.read_text(encoding="utf-8")).get("filingforge_library", "")).expanduser()
    except (OSError, ValueError):
        return None
    return p if str(p) not in ("", ".") and p.is_dir() else None


# --------------------------------------------------------------------------------------------------------------
# Assignments: what one agent is asked to do, with its permission profile and its completion check
# --------------------------------------------------------------------------------------------------------------

@dataclasses.dataclass
class Assignment:
    kind: str                       # reader | specialist | followup | auditor | librarian | probe
    agent: str
    model: str
    effort: str
    prompt: str
    label: str                      # the launch or job id
    tools: List[str]
    allowed: List[str]
    denied: List[str]
    dirs: List[Path]
    check: Callable[[], List[str]]  # [] when the work passes
    long: bool = False              # segments, checkpoints and fresh continuations
    progress: str = ""              # the agent's checkpoint file (long agents)
    resume_msg: str = ""
    fix_msg: str = ""
    fix_rounds: int = FIX_ROUNDS_REPORT
    chunks: Tuple[str, ...] = ()
    role: str = ""                  # readers: critical | reader | resolved
    owned: Tuple[str, ...] = ()     # glob patterns (relative to RUN_DIR) of the files the agent may write
    guarded: bool = False           # fingerprint everything else around each segment
    record: str = "job"             # job (engine/jobs.json) | launch (corpus/reading/launches.json)
    stage: str = ""
    purpose: str = ""
    outcome: str = ""
    polish: Optional[Callable[[], List[str]]] = None   # issues worth one fix round that do not block the check
    subject: str = ""               # the verifier: the specialist it checks


def run_paths(run_dir: Path) -> List[Path]:
    """The extra directories a session needs: the run (when outside the repository) and the FilingForge library."""
    dirs = []
    if outside(run_dir, [rl.ROOT]):
        dirs.append(run_dir.resolve())
    lib = library_dir()
    if lib and outside(lib, [rl.ROOT] + dirs):
        dirs.append(lib.resolve())
    return dirs


def other_runs(run_dir: Path) -> List[Path]:
    base = rl.ROOT / "research" / "companies"
    me = run_dir.resolve()
    return [d for d in sorted(base.glob("*/runs/*")) if d.is_dir() and d.resolve() != me]


def specialist_owned(name: str) -> Tuple[str, ...]:
    return ("specialists/%s.md" % name, "specialists/%s_ledger.csv" % name, "specialists/%s_followup_*" % name,
            "specialists/%s_workpapers/**" % name, "calc/%s_*" % name, "_cache/scratch/%s/**" % name)


def independence_denies(run_dir: Path, me: str, review: bool = False) -> List[str]:
    """What a specialist must not read: the other specialists' work, the CIO's and the auditor's, the engine's records
    (they hold every specialist's return message), other runs, the archive, the scoreboard and agent transcripts.
    `review` (a Stage-3 follow-up: cross-examination after the independent work is filed) lifts only the first."""
    out = []
    for other in rl.SPECIALISTS:
        if other == me or review:
            continue
        for pat in specialist_owned(other):
            out.append(abs_rule("Read", run_dir, "/" + pat))
    for d in ("cio", "audit", "qc", "engine", "_cache/engine"):
        out.append(abs_rule("Read", run_dir, "/%s/**" % d))
    for d in other_runs(run_dir):
        out.append(abs_rule("Read", d, "/**"))
    out += [abs_rule("Read", rl.ROOT, "/archive/**"), abs_rule("Read", rl.ROOT, "/docs/**"),
            abs_rule("Read", rl.ROOT, "/COMPANY_SCOREBOARD.csv"), abs_rule("Read", rl.ROOT, "/research/companies/*/latest_run.txt")]
    return out + DENY_TRANSCRIPTS + DENY_SECRETS


def shell_denies() -> List[str]:
    return ["Bash(git:*)"] + ["Bash(python3 scripts/%s:*)" % s for s in CIO_ONLY_SCRIPTS]


def run_command(cmd: List[str]) -> Tuple[int, str]:
    r = subprocess.run(cmd, cwd=str(rl.ROOT), capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


def validator_errors(cmd: List[str]) -> List[str]:
    rc, out = run_command(cmd)
    if rc == 0:
        return []
    errs = [ln.strip() for ln in out.splitlines() if "ERROR" in ln.upper() or ln.strip().startswith("- ")]
    return errs[:40] or [out.strip()[-2000:] or "the validator exited %d" % rc]


def reader_assignment(run_dir: Path, act: dict) -> Assignment:
    """A reading launch: read, write parts, run the check. Writes only into the parts directories; the shell only for
    `reading.py check` and `render`; nothing else of the run, no web."""
    parts = (run_dir / reading.CACHE / "parts").resolve()
    parts.mkdir(parents=True, exist_ok=True)
    dirs = [run_dir.resolve()] if outside(run_dir, [rl.ROOT]) else []
    p = reading.load_json(run_dir / reading.READING / "plan.json", {"chunks": []})
    for c in p["chunks"]:
        if c["id"] in act["chunks"] and c.get("pdf"):
            d = reading.pdf_path(c["pdf"]).parent
            if outside(d, [rl.ROOT] + dirs) and d not in dirs:
                dirs.append(d)
    lid = act["launch"]
    others = [r for r in ("critical", "reader") if r != act["role"]] if act["role"] != "resolved" else []
    four_eyes = []                    # the two reads of a double-read chunk stay independent until they are compared
    for r in others:
        four_eyes += [abs_rule("Read", parts, "/*.%s/**" % r),
                      abs_rule("Read", run_dir / reading.READING / "extractions", "/*.%s.jsonl" % r)]
    if others:
        four_eyes += [abs_rule("Read", run_dir / reading.READING / "disagreements", "/**"),
                      abs_rule("Read", run_dir / reading.DOSSIERS, "/**")]

    def check() -> List[str]:
        errs = []
        for cid in act["chunks"]:
            res = reading.check(run_dir, cid, act["role"])
            if not res.ok:
                errs += ["%s: %s" % (cid, e) for e in res.errors[:25]]
        return errs
    return Assignment(kind="reader", agent=act["agent"], model=act["model"], effort=act["effort"], prompt=act["prompt"],
                      label=lid, tools=["Read", "Write", "Edit", "Bash"],
                      allowed=["Read", abs_rule("Write", parts, "/**"), abs_rule("Edit", parts, "/**"),
                               "Bash(python3 scripts/reading.py check:*)", "Bash(python3 scripts/reading.py render:*)"],
                      denied=four_eyes + DENY_SECRETS + DENY_TRANSCRIPTS, dirs=dirs, check=check, resume_msg=READER_RESUME_MSG,
                      fix_msg=READER_FIX_MSG, fix_rounds=FIX_ROUNDS, chunks=tuple(act["chunks"]), role=act["role"],
                      record="launch",
                      stage="0b", purpose="%s %s" % (act["role"], ", ".join(act["chunks"])))


def specialist_prompt(run_dir: Path, name: str) -> str:
    """The Stage-1 prompt: templates/specialist_prompt.md filled with the run's identity block (engine/identity.md,
    written once by the CIO) and the specialist's name. One template, so no specialist gets a different brief."""
    ident = run_dir / "engine" / "identity.md"
    if not ident.exists():
        raise SystemExit("write the identity block to %s first (cio.md Stage 1)" % ident)
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    sme = str(m.get("listing_segment") or "") == "sme"
    text = SPECIALIST_PROMPT.read_text(encoding="utf-8")
    text = text.split("<!-- PROMPT:BEGIN -->", 1)[1].split("<!-- PROMPT:END -->", 1)[0].strip("\n")
    return (text.replace("{{NAME}}", name).replace("{{RUN_ID}}", m.get("run_id", run_dir.name))
            .replace("{{RUN_DIR}}", reading.rel_run(run_dir)).replace("{{IDENTITY}}", ident.read_text(encoding="utf-8").strip())
            .replace("{{SME}}", "SME ENHANCED SCRUTINY is ON: add the section `SME Enhanced Scrutiny` defined in your "
                                "agent definition." if sme else "")
            .replace("{{LESSONS}}", lessons(name)))


def lessons(name: str) -> str:
    """What verification found in this agent's earlier runs (process lessons only; verify.py lessons)."""
    import verify
    return verify.lessons_text(name)


def report_check(run_dir: Path, report: str, kind: str, ledger: str = "") -> Callable[[], List[str]]:
    def check() -> List[str]:
        if not (run_dir / report).exists():
            return ["%s does not exist yet" % report]
        cmd = [sys.executable, "scripts/validate_report.py", str(run_dir / report), "--kind", kind]
        if ledger:
            cmd += ["--ledger", str(run_dir / ledger)]
        if kind == "audit":
            cmd += ["--run", str(run_dir)]
        return validator_errors(cmd)
    return check


def specialist_assignment(run_dir: Path, name: str, prompt: str, stage: str = "1", purpose: str = "initial investigation",
                          output: str = "") -> Assignment:
    model, effort = reading.pinned(run_dir, name)
    owned = specialist_owned(name)
    scratch = run_dir / "_cache" / "scratch" / name
    scratch.mkdir(parents=True, exist_ok=True)
    allowed = ["Read", "Bash", "WebSearch", "WebFetch"]
    for pat in owned:
        allowed += [abs_rule("Write", run_dir, "/" + pat), abs_rule("Edit", run_dir, "/" + pat)]
    if output:
        kind, report, ledger = "followup", output, output[:-3] + "_ledger.csv"
    else:
        kind, report, ledger = "specialist", "specialists/%s.md" % name, "specialists/%s_ledger.csv" % name
    progress = "%s/specialists/%s_workpapers/progress.md" % (reading.rel_run(run_dir), name)
    report = report_check(run_dir, report, kind, ledger)

    def check() -> List[str]:                  # the validator, then the verification of the work itself (Tier A)
        errs = report()
        if errs:
            return errs
        import verify
        return verify.fix_message(verify.specialist(run_dir, name), ("blocking",), tier_b=False)

    def polish() -> List[str]:
        import verify
        return verify.fix_message(verify.specialist(run_dir, name), ("major",), tier_b=False)
    return Assignment(kind="specialist" if not output else "followup", agent=name, model=model, effort=effort,
                      prompt=prompt, label="", tools=agent_tools(name), allowed=allowed,
                      denied=independence_denies(run_dir, name, review=str(stage).startswith("3")) + shell_denies(),
                      dirs=run_paths(run_dir),
                      check=check, polish=polish, long=True, progress=progress,
                      resume_msg=RESUME_MSG % progress, fix_msg=REPORT_FIX_MSG, owned=owned, guarded=True,
                      stage=stage, purpose=purpose)


def auditor_assignment(run_dir: Path, prompt: str, stage: str = "4", purpose: str = "independent audit of the draft",
                       output: str = "") -> Assignment:
    model, effort = reading.pinned(run_dir, rl.AUDITOR)
    allowed = ["Read", "Bash", "WebSearch", "WebFetch", abs_rule("Write", run_dir, "/audit/**"),
               abs_rule("Edit", run_dir, "/audit/**")]
    denied = [abs_rule("Read", d, "/**") for d in other_runs(run_dir)] + [
        abs_rule("Read", rl.ROOT, "/archive/**"), abs_rule("Read", run_dir, "/engine/**"),
        abs_rule("Read", run_dir, "/_cache/engine/**")] + DENY_TRANSCRIPTS + DENY_SECRETS + shell_denies()
    if output:
        def check() -> List[str]:
            return [] if (run_dir / output).exists() and (run_dir / output).stat().st_size else ["%s was not written" % output]
    else:
        check = report_check(run_dir, rl.AUDIT_REPORT, "audit")
    progress = "%s/audit/progress.md" % reading.rel_run(run_dir)
    return Assignment(kind="auditor", agent=rl.AUDITOR, model=model, effort=effort, prompt=prompt, label="",
                      tools=agent_tools(rl.AUDITOR), allowed=allowed, denied=denied, dirs=run_paths(run_dir), check=check,
                      long=True, progress=progress, resume_msg=RESUME_MSG % progress, fix_msg=REPORT_FIX_MSG,
                      owned=("audit/**",), stage=stage, purpose=purpose)


def verifier_assignment(run_dir: Path, name: str, prompt: str) -> Assignment:
    """The verifier re-checks one specialist's claim sample at the sources: it may read that specialist's files and the
    sources, never another specialist's work, the CIO's or the auditor's; it writes only its results file."""
    model, effort = reading.pinned(run_dir, "verifier")
    out = run_dir / "qc" / "verification" / ("%s_claims.csv" % name)
    out.parent.mkdir(parents=True, exist_ok=True)
    denied = [r for r in independence_denies(run_dir, name) if "/qc/" not in r] + [
        abs_rule("Read", run_dir, "/qc/verification/%s.json" % o) for o in rl.SPECIALISTS if o != name] + shell_denies()

    def check() -> List[str]:
        import verify
        return verify.claims_result(run_dir, name, write=False)[1]
    progress = "%s/qc/verification/%s_claims.csv" % (reading.rel_run(run_dir), name)
    return Assignment(kind="verifier", agent="verifier", model=model, effort=effort, prompt=prompt, label="",
                      tools=agent_tools("verifier"), allowed=["Read", "Bash", "WebFetch", abs_rule("Write", out),
                                                             abs_rule("Edit", out)],
                      denied=denied, dirs=run_paths(run_dir), check=check, resume_msg=RESUME_MSG % progress,
                      fix_msg=("The verification file is not complete yet:\n%s\nFix every item, re-run `python3 "
                               "scripts/verify.py claims RUN_DIR " + name + "` until it reports no errors, then give "
                               "your one-line result."), stage="1-verify", purpose="re-check %s's claims" % name,
                      subject=name)


def librarian_assignment(run_dir: Path, prompt: str) -> Assignment:
    model, effort = reading.pinned(run_dir, "librarian")
    log = run_dir / "corpus" / "librarian_log.md"
    allowed = ["Read", "WebSearch", "WebFetch", abs_rule("Write", log), abs_rule("Edit", log)] + [
        "Bash(python3 scripts/%s:*)" % s for s in ("fetch_source.py", "document_map.py", "exchange_index.py", "doc_text.py")]

    def check() -> List[str]:
        return [] if log.exists() else ["corpus/librarian_log.md was not written"]
    return Assignment(kind="librarian", agent="librarian", model=model, effort=effort, prompt=prompt, label="",
                      tools=agent_tools("librarian"), allowed=allowed,
                      denied=DENY_TRANSCRIPTS + DENY_SECRETS + shell_denies(), dirs=run_paths(run_dir), check=check,
                      resume_msg=RESUME_MSG % "corpus/librarian_log.md", fix_msg=REPORT_FIX_MSG, stage="0",
                      purpose="find the documents the map lacks")


# --------------------------------------------------------------------------------------------------------------
# Transcripts
# --------------------------------------------------------------------------------------------------------------

def transcripts_dir() -> Path:
    import reading_audit
    return reading_audit.transcripts_dir()


def tail_lines(path: Path, n: int = 300) -> List[str]:
    if not path.exists():
        return []
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 400000))
        return f.read().decode("utf-8", "replace").splitlines()[-n:]


def limit_reset(result: Optional[dict], transcript: Path, since: float) -> Optional[float]:
    """The epoch time a usage limit resets, if this attempt stopped on one; None otherwise (an attempt that ended
    without error never did, whatever earlier attempts left in the transcript)."""
    if result is not None and not result.get("is_error"):
        return None
    if result is not None and result.get("subtype") in ("error_max_turns", "error_max_budget_usd"):
        return None
    hit = bool(result and LIMIT_RE.search(str(result.get("result") or "")))
    reset = None
    for line in tail_lines(transcript):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        ts = o.get("timestamp") or ""
        try:
            when = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() if ts else since
        except ValueError:
            when = since
        if when < since - 1:
            continue
        if o.get("apiError") == "usage_limit_reached" or (o.get("error") == "rate_limit" and o.get("isApiErrorMessage")):
            hit = True
        for q in (o.get("quotaLimits") or {}, ((o.get("apiErrorParams") or {}).get("rate_limit_info") or {})):
            if q.get("resetsAt") and q.get("status") == "rejected":
                reset = float(q["resetsAt"])
    if not hit:
        return None
    return reset if reset else time.time() + LIMIT_FALLBACK_S      # a reset time already past: resume at once


def transcript_usage(path: Path) -> dict:
    """Tokens, API turns, peak context and minutes of a session transcript (each API message counted once)."""
    tot, seen, turns, peak, first, last = Counter(), set(), 0, 0, "", ""
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            ts = o.get("timestamp") or ""
            if ts:
                first = first or ts
                last = ts
            m = o.get("message") or {}
            if o.get("type") != "assistant" or m.get("model") in (None, "<synthetic>") or m.get("id") in seen:
                continue
            seen.add(m.get("id"))
            u = m.get("usage") or {}
            turns += 1
            for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"):
                tot[k] += u.get(k, 0) or 0
            peak = max(peak, context_of(u))
    minutes = 0.0
    try:
        minutes = (dt.datetime.fromisoformat(last.replace("Z", "+00:00")) -
                   dt.datetime.fromisoformat(first.replace("Z", "+00:00"))).total_seconds() / 60
    except ValueError:
        pass
    return {"api_turns": turns, "peak_context": peak, "minutes_first_to_last": round(minutes, 1),
            "input": tot["input_tokens"], "cache_write": tot["cache_creation_input_tokens"],
            "cache_read": tot["cache_read_input_tokens"], "output": tot["output_tokens"],
            "processed": sum(tot.values())}


def context_of(usage: dict) -> int:
    return sum((usage.get(k, 0) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))


def last_context(transcript: Path) -> int:
    """The context of the session's latest API call, in tokens."""
    for line in reversed(tail_lines(transcript, 400)):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        m = o.get("message") or {}
        if o.get("type") == "assistant" and m.get("model") not in (None, "<synthetic>") and m.get("usage"):
            return context_of(m["usage"])
    return 0


# --------------------------------------------------------------------------------------------------------------
# Usage windows
# --------------------------------------------------------------------------------------------------------------

def windows_of(info: dict) -> Dict[str, dict]:
    """{"five_hour": {"utilization", "resetsAt"}, "seven_day": {...}} from a rate_limit_info."""
    out = {}
    for k, v in ((info or {}).get("unifiedWindows") or {}).items():
        if isinstance(v, dict) and v.get("utilization") is not None:
            out[k] = {"utilization": float(v["utilization"]), "resetsAt": v.get("resetsAt")}
    t = (info or {}).get("rateLimitType")
    if t in ("five_hour", "seven_day") and t not in out and (info or {}).get("utilization") is not None:
        out[t] = {"utilization": float(info["utilization"]), "resetsAt": info.get("resetsAt")}
    return out


def usage_log_path() -> Path:
    """Utilization is the account's, not the run's: one log per machine ($EQR_USAGE_LOG overrides it)."""
    return Path(os.environ.get("EQR_USAGE_LOG") or Path.home() / ".claude" / "equity-research-usage.jsonl").expanduser()


def probe_usage(claude: str) -> dict:
    """One tiny Haiku call (no tools, no session kept), for its rate_limit_event."""
    try:
        r = subprocess.run([claude, "-p", "Reply with the single word OK.", "--model", "haiku", "--tools", "",
                            "--strict-mcp-config", "--disable-slash-commands", "--output-format", "stream-json", "--verbose",
                            "--no-session-persistence"], cwd=tempfile.gettempdir(), env=child_env(), capture_output=True,
                           text=True, timeout=120, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return {}
    info = {}
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") == "rate_limit_event":
            info = o.get("rate_limit_info") or {}
    return info


def fmt_windows(w: Dict[str, dict]) -> str:
    parts = []
    for k, name in (("five_hour", "five-hour"), ("seven_day", "weekly")):
        if k in w:
            when = dt.datetime.fromtimestamp(w[k]["resetsAt"]).strftime("%a %H:%M") if w[k].get("resetsAt") else "?"
            parts.append("%s %.0f%% (resets %s)" % (name, 100 * w[k]["utilization"], when))
    return ", ".join(parts) or "not reported"


class LimitStop(Exception):
    pass


# --------------------------------------------------------------------------------------------------------------
# Integrity: what an agent must not touch, fingerprinted around each segment
# --------------------------------------------------------------------------------------------------------------

def owned_by(rel_path: str, patterns) -> bool:
    import fnmatch
    for pat in patterns:
        if pat.endswith("/**"):
            if rel_path.startswith(pat[:-3] + "/"):
                return True
        elif fnmatch.fnmatch(rel_path, pat):
            return True
    return False


def guarded_files(run_dir: Path, a: Assignment, busy_owned=()) -> List[Path]:
    """The files a specialist must not change: every other specialist's work (report, ledger, follow-ups, workpapers,
    calc files) and the facts every agent shares (corpus/, the research brief). Files of an agent that runs at the same
    time are left out (their changes are that agent's). The CIO's own folders are not here: the CIO works while the
    engine runs; reads of them are caught by the permission profile and the transcript audit."""
    pats = [p for other in rl.SPECIALISTS if other != a.agent for p in specialist_owned(other)
            if not p.startswith("_cache/")]
    out = []
    for p in list((run_dir / "specialists").rglob("*")) + list((run_dir / "calc").glob("*")) + \
            list((run_dir / "corpus").rglob("*")) + [run_dir / "research_brief.md"]:
        if not p.is_file():
            continue
        r = str(p.relative_to(run_dir)).replace("\\", "/")
        if r.startswith("corpus/") or r == "research_brief.md" or owned_by(r, pats):
            if not owned_by(r, a.owned) and not any(owned_by(r, o) for o in busy_owned):
                out.append(p)
    return out


def fingerprint(run_dir: Path, a: Assignment, busy_owned=()) -> Dict[str, Tuple[int, int]]:
    """(size, mtime) of each guarded file."""
    out = {}
    for p in guarded_files(run_dir, a, busy_owned):
        st = p.stat()
        out[str(p.relative_to(run_dir)).replace("\\", "/")] = (st.st_size, st.st_mtime_ns)
    return out


def integrity_diff(before: Dict[str, Tuple[int, int]], after: Dict[str, Tuple[int, int]]) -> List[str]:
    changed = [r for r in before if r in after and after[r] != before[r]]
    removed = [r for r in before if r not in after]
    return sorted(changed + removed)


# --------------------------------------------------------------------------------------------------------------
# The engine
# --------------------------------------------------------------------------------------------------------------

class Engine:
    def __init__(self, run_dir: Path, claude: str, opts, log=print):
        self.run_dir = run_dir
        self.claude = claude
        self.o = opts
        self._log = log
        self.lock = threading.RLock()
        self.version = claude_version(claude) if claude else ""
        self.usage: dict = {}
        self.usage_at = 0.0
        self.children = set()
        self.stop = ""                    # why no new segment may start ("" = carry on)
        self.busy: Dict[str, Assignment] = {}
        self.load_last_usage()

    # -- logging and records --------------------------------------------------------------------------------
    def log(self, msg: str) -> None:
        with self.lock:
            self._log(msg)

    def jobs_path(self) -> Path:
        return self.run_dir / "engine" / "jobs.json"

    def jobs(self) -> dict:
        return reading.load_json(self.jobs_path(), {"jobs": []})

    def new_job(self, a: Assignment) -> dict:
        with self.lock:
            data = self.jobs()
            job = {"id": "J%03d" % (len(data["jobs"]) + 1), "kind": a.kind, "agent": a.agent, "stage": a.stage,
                   "purpose": a.purpose, "model": a.model, "effort": a.effort, "issued_at": reading.now_iso(),
                   "status": "running", "prompt_sha256": hashlib.sha256(a.prompt.encode()).hexdigest()[:16],
                   "sessions": []}
            if a.subject:
                job["subject"] = a.subject
            data["jobs"].append(job)
            reading.write_json(self.jobs_path(), data)
            prompt_path(self.run_dir, job["id"]).parent.mkdir(parents=True, exist_ok=True)
            prompt_path(self.run_dir, job["id"]).write_text(a.prompt, encoding="utf-8")
            invocation(self.run_dir, a.agent, a.stage, "%s (%s)" % (a.purpose, job["id"]))
            return job

    def get_record(self, a: Assignment) -> dict:
        with self.lock:
            if a.record == "launch":
                return next(l for l in reading.load_json(reading.launches_path(self.run_dir), {"launches": []})["launches"]
                            if l["id"] == a.label)
            return next(j for j in self.jobs()["jobs"] if j["id"] == a.label)

    def update_record(self, a: Assignment, **fields) -> None:
        with self.lock:
            if a.record == "launch":
                reading.update_launch(self.run_dir, a.label, **fields)
                return
            data = self.jobs()
            for j in data["jobs"]:
                if j["id"] == a.label:
                    j.update(fields)
            reading.write_json(self.jobs_path(), data)

    # -- usage ----------------------------------------------------------------------------------------------
    def load_last_usage(self) -> None:
        for line in tail_lines(usage_log_path(), 50):
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get("at", 0) > self.usage_at:
                self.usage, self.usage_at = o.get("info") or {}, float(o["at"])

    def note_usage(self, info: dict, label: str = "") -> None:
        if not info:
            return
        with self.lock:
            now = time.time()
            self.usage, self.usage_at = info, now
            run = self.run_dir.name if (self.run_dir / rl.RUN_MANIFEST).exists() else ""
            try:
                usage_log_path().parent.mkdir(parents=True, exist_ok=True)
                with usage_log_path().open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"at": now, "run": run, "label": label, "info": info}) + "\n")
            except OSError:
                pass

    def windows(self, refresh: bool = False) -> Dict[str, dict]:
        if refresh and self.claude and time.time() - self.usage_at > USAGE_STALE_S:
            self.note_usage(probe_usage(self.claude), "probe")
        w = windows_of(self.usage)
        for k in list(w):                 # a window whose reset has passed says nothing about now
            if w[k].get("resetsAt") and w[k]["resetsAt"] < time.time():
                w.pop(k)
        return w

    def wait_for_week(self) -> None:
        """Before every segment: the weekly window must be below the ceiling (the owner's reserve)."""
        while True:
            w = self.windows(refresh=False).get("seven_day")
            if not w or w["utilization"] < self.o.weekly_ceiling:
                return
            wait = (w.get("resetsAt") or time.time() + LIMIT_FALLBACK_S) - time.time() + LIMIT_SLACK_S
            when = dt.datetime.fromtimestamp(time.time() + wait).strftime("%Y-%m-%d %H:%M")
            if wait > self.o.max_wait_s:
                self.stop = self.stop or ("the weekly usage window is at %.0f%% (ceiling %.0f%%) until %s" % (
                    100 * w["utilization"], 100 * self.o.weekly_ceiling, when))
                raise LimitStop(self.stop)
            self.log("weekly usage window at %.0f%% (ceiling %.0f%%): waiting until %s" % (
                100 * w["utilization"], 100 * self.o.weekly_ceiling, when))
            time.sleep(max(0.0, wait))
            self.usage_at = 0.0

    def room_for_another(self) -> bool:
        """With sessions already running, another starts only while the five-hour window is below the ceiling."""
        if not self.busy:
            return True
        w = self.windows(refresh=True).get("five_hour")
        return bool(w) and w["utilization"] < self.o.parallel_ceiling

    # -- one segment ----------------------------------------------------------------------------------------
    def command(self, a: Assignment, sid: str, message: str, resume: bool, max_turns: int) -> List[str]:
        cmd = [self.claude, "-p", message]
        cmd += ["--resume", sid] if resume else ["--session-id", sid]
        cmd += ["--agent", a.agent, "--model", a.model, "--effort", a.effort, "--output-format", "stream-json", "--verbose",
                "--tools", ",".join(a.tools), "--strict-mcp-config", "--disable-slash-commands",
                "--permission-mode", "dontAsk", "--allowedTools"] + a.allowed + ["--disallowedTools"] + a.denied
        if max_turns:
            cmd += ["--max-turns", str(max_turns)]
        sp = skills_prompt(a.agent, self.run_dir / "_cache" / "engine" / "system")
        if sp:
            cmd += ["--append-system-prompt-file", str(sp.resolve())]
        for d in a.dirs:
            cmd += ["--add-dir", str(d)]
        return cmd

    def run_process(self, cmd: List[str], out: Path, label: str, on_start=None) -> dict:
        out.parent.mkdir(parents=True, exist_ok=True)
        timed = {"out": False}
        with out.open("w", encoding="utf-8") as fo, Path(str(out) + ".err").open("w", encoding="utf-8") as fe:
            proc = subprocess.Popen(cmd, cwd=str(rl.ROOT), env=child_env(), stdout=subprocess.PIPE, stderr=fe,
                                    stdin=subprocess.DEVNULL, start_new_session=True, text=True, bufsize=1,
                                    encoding="utf-8", errors="replace")
            with self.lock:
                self.children.add(proc)
            if on_start:
                on_start(proc.pid)

            def on_timeout():
                timed["out"] = True
                stop_child(proc)
            timer = threading.Timer(self.o.timeout_s, on_timeout)
            timer.daemon = True
            timer.start()
            result = None
            for line in proc.stdout:
                s = line.strip()
                if not s.startswith("{"):
                    continue
                try:
                    o = json.loads(s)
                except ValueError:
                    continue
                t = o.get("type")
                if t == "rate_limit_event":
                    self.note_usage(o.get("rate_limit_info") or {}, label)
                    fo.write(s + "\n")
                elif t == "result":
                    result = o
                    fo.write(s + "\n")
                elif t == "system" and o.get("subtype") == "init":
                    fo.write(json.dumps({k: o.get(k) for k in ("type", "subtype", "model", "tools", "permissionMode",
                                                               "session_id", "claude_code_version")}) + "\n")
            proc.stdout.close()
            rc = proc.wait()
            timer.cancel()
            with self.lock:
                self.children.discard(proc)
        return {"rc": rc, "timed_out": timed["out"], "result": result, "pid": proc.pid}

    # -- one assignment, to its end ---------------------------------------------------------------------------
    def run(self, a: Assignment) -> str:
        """Run an assignment until its check passes: "pass", "failed" (the check still fails after the fix rounds),
        "abandoned" (a session could not be brought to an end) or "paused" (stopped for a usage window or a signal;
        the next engine run resumes it)."""
        tdir = transcripts_dir()
        rec = self.get_record(a)
        sessions = rec.get("sessions", [])
        logs = self.run_dir / "_cache" / "engine" / "out"
        fixes = resumes = 0
        polished = False
        if sessions and not sessions[-1].get("ended"):
            sess = sessions[-1]
            if alive(sess.get("pid")):
                self.log("%s: the session process %s of an earlier engine still runs; waiting for it to end" % (a.label, sess["pid"]))
                while alive(sess.get("pid")):
                    time.sleep(30)
            kind, message = "resume", a.resume_msg
            self.log("%s: resuming session %s (%s)" % (a.label, sess["session_id"][:8], a.agent))
        else:
            message = a.prompt if not sessions else self.continuation(a, sessions)
            sess = self.new_session(a, sessions, tdir)
            kind = "start"
        while True:
            if self.stop:
                return self.pause(a, sessions, sess)
            try:
                self.wait_for_week()
            except LimitStop:
                return self.pause(a, sessions, sess)
            transcript = Path(sess["transcript"])
            max_turns = 0
            if a.long:
                max_turns = CHECKPOINT_TURNS if kind == "checkpoint" else self.o.segment_turns
            before = fingerprint(self.run_dir, a, self.busy_owned(a)) if a.guarded else {}
            w0 = windows_of(self.usage)
            cmd = self.command(a, sess["session_id"], message, resume=(kind != "start"), max_turns=max_turns)
            started = time.time()

            def on_start(pid):              # recorded, so a later engine waits for an orphaned session instead of racing it
                sess["pid"] = pid
                self.update_record(a, runner="headless", sessions=sessions)
            out = logs / ("%s-%s-%d.jsonl" % (a.label, sess["session_id"][:8], len(sess["attempts"]) + 1))
            got = self.run_process(cmd, out, a.label, on_start)
            sess["pid"] = None
            res = got["result"] or {}
            att = {"kind": kind, "at": dt.datetime.fromtimestamp(started, dt.timezone.utc).replace(microsecond=0).isoformat(),
                   "seconds": round(time.time() - started), "rc": got["rc"], "timed_out": got["timed_out"],
                   "is_error": bool(res.get("is_error")), "subtype": res.get("subtype", ""), "turns": res.get("num_turns"),
                   "result": str(res.get("result") or "")[:300], "cost_usd": res.get("total_cost_usd"),
                   "output": rel_out(out), "context_after": last_context(transcript),
                   "util_before": {k: v["utilization"] for k, v in w0.items()},
                   "util_after": {k: v["utilization"] for k, v in windows_of(self.usage).items()}}
            if a.guarded:
                touched = integrity_diff(before, fingerprint(self.run_dir, a, self.busy_owned(a)))
                if touched:
                    att["integrity"] = touched
                    self.log("%s: INDEPENDENCE: %s changed files it must not touch: %s" % (a.label, a.agent, ", ".join(touched[:8])))
            reset = limit_reset(got["result"], transcript, started)
            if reset:
                att["limit_resets_at"] = dt.datetime.fromtimestamp(reset, dt.timezone.utc).replace(microsecond=0).isoformat()
            sess["attempts"].append(att)
            self.update_record(a, sessions=sessions)
            if self.stop and (got["rc"] != 0 or not got["result"]):
                return self.pause(a, sessions, sess)
            if reset:
                wait = reset - time.time() + LIMIT_SLACK_S
                local = dt.datetime.fromtimestamp(reset).strftime("%Y-%m-%d %H:%M")
                if wait > self.o.max_wait_s:
                    self.stop = self.stop or "a usage limit resets at %s (local), later than --max-wait-hours" % local
                    self.log("%s: usage limit; it resets at %s (local), later than --max-wait-hours. Stopping: run the "
                             "engine again after the reset and it resumes this session." % (a.label, local))
                    return self.pause(a, sessions, sess)
                self.log("%s: usage limit; waiting until %s (local), then resuming the same session" % (a.label, local))
                time.sleep(max(0.0, wait))
                kind, message = "resume", a.resume_msg
                continue
            if res.get("subtype") == "error_max_turns" and got["rc"] in (0, 1) and not got["timed_out"]:
                ctx = att["context_after"]
                if ctx >= self.o.context_limit and kind != "checkpoint":
                    self.log("%s: context %s tokens: asking %s to checkpoint before a fresh session" % (
                        a.label, format(ctx, ","), a.agent))
                    kind, message = "checkpoint", CHECKPOINT_MSG.format(limit=self.o.context_limit, progress=a.progress)
                    continue
                if kind == "checkpoint":
                    self.log("%s: the checkpoint ran out of turns; handing over anyway (the files hold what it wrote)" % a.label)
                    sess, message = self.hand_over(a, sessions, sess, tdir)
                    kind = "start"
                    continue
                kind, message = "continue", CONTINUE_MSG
                continue
            if got["timed_out"] or got["rc"] != 0 or not got["result"] or res.get("is_error"):
                resumes += 1
                self.log("%s: the session ended without finishing (%s); %s" % (
                    a.label, "timed out" if got["timed_out"] else "exit %s: %s" % (got["rc"], att["result"][:120] or "no result"),
                    "resuming it" if resumes <= RESUME_TRIES else "giving it up"))
                if resumes > RESUME_TRIES:
                    self.end_session(sess, transcript)
                    self.close(a, sessions, "abandoned", "the session could not be brought to an end")
                    return "abandoned"
                time.sleep(60 * resumes)
                kind, message = "resume", a.resume_msg
                continue
            errs = a.check()
            if not errs and a.polish and not polished:
                polished = True
                issues = a.polish()
                if issues:
                    self.log("%s: %s passes; sending it %d verification issue(s) to fix once" % (a.label, a.agent, len(issues)))
                    kind, message = "fix", POLISH_MSG % "\n".join(issues[:40])
                    continue
            if not errs:
                self.end_session(sess, transcript)
                self.close(a, sessions, "pass", result=att["result"])
                u = sess["usage"]
                self.log("%s: PASS %s (%s min, %s API turns, %s tokens processed, peak context %s, $%.2f)" % (
                    a.label, a.agent, u.get("minutes_first_to_last"), u.get("api_turns"), format(u.get("processed", 0), ","),
                    format(u.get("peak_context", 0), ","), job_cost(sessions)))
                return "pass"
            if kind == "checkpoint":              # it finished its step and wrote everything: a fresh session goes on
                if len(sessions) > CONTINUATIONS:
                    self.end_session(sess, transcript)
                    self.close(a, sessions, "failed", "more than %d sessions without passing its check" % CONTINUATIONS)
                    return "failed"
                self.log("%s: %s checkpointed at %s tokens; continuing in a fresh session" % (
                    a.label, a.agent, format(att["context_after"], ",")))
                sess, message = self.hand_over(a, sessions, sess, tdir)
                kind = "start"
                continue
            fixes += 1
            self.log("%s: the check fails (%d errors)%s" % (a.label, len(errs), "; resuming the session with them"
                                                             if fixes <= a.fix_rounds else "; closing it as failed"))
            if fixes > a.fix_rounds:
                self.end_session(sess, transcript)
                self.close(a, sessions, "failed", "; ".join(errs[:5]))
                return "failed"
            kind, message = "fix", a.fix_msg % "\n".join(errs[:40])

    def new_session(self, a: Assignment, sessions: List[dict], tdir: Path) -> dict:
        sid = str(uuid.uuid4())
        sess = {"session_id": sid, "runner": "headless", "transcript": str(tdir / ("%s.jsonl" % sid)),
                "started_at": reading.now_iso(), "model": a.model, "effort": a.effort, "claude": self.version,
                "attempts": []}
        sessions.append(sess)
        self.update_record(a, runner="headless", sessions=sessions)
        self.log("%s: %s (%s at %s)%s%s" % (a.label, a.agent, a.model, a.effort,
                                           " on " + ", ".join(a.chunks) if a.chunks else "",
                                           " — session %d" % len(sessions) if len(sessions) > 1 else ""))
        return sess

    def continuation(self, a: Assignment, sessions: List[dict]) -> str:
        return a.prompt + CONTINUATION_NOTE.format(k=len(sessions) + 1, progress=a.progress)

    def hand_over(self, a: Assignment, sessions: List[dict], sess: dict, tdir: Path) -> Tuple[dict, str]:
        self.end_session(sess, Path(sess["transcript"]), "handed over")
        invocation(self.run_dir, a.agent, (a.stage or "1") + "-continue", "fresh session after a checkpoint (%s)" % a.label)
        message = self.continuation(a, sessions)
        return self.new_session(a, sessions, tdir), message

    def end_session(self, sess: dict, transcript: Path, why: str = "") -> None:
        sess["ended"] = reading.now_iso()
        sess["usage"] = transcript_usage(transcript)
        if why:
            sess["ended_because"] = why

    def close(self, a: Assignment, sessions: List[dict], outcome: str, note: str = "", result: str = "") -> None:
        fields = {"sessions": sessions, "closed_at": reading.now_iso(), "outcome": outcome}
        if note:
            fields["note"] = note
        if a.record == "job":
            fields["status"] = outcome
            if result:
                fields["result"] = result
            fields["cost_usd"] = round(job_cost(sessions), 2)
            breaches = sorted({p for s in sessions for at in s.get("attempts", []) for p in at.get("integrity", [])})
            if breaches:
                fields["integrity"] = breaches
        self.update_record(a, **fields)
        a.outcome = outcome

    def pause(self, a: Assignment, sessions: List[dict], sess: dict) -> str:
        self.update_record(a, sessions=sessions, **({"status": "paused"} if a.record == "job" else {}))
        a.outcome = "paused"
        return "paused"

    def busy_owned(self, a: Assignment):
        with self.lock:
            return [b.owned for k, b in self.busy.items() if b is not a and b.owned]

    # -- the scheduler --------------------------------------------------------------------------------------
    def schedule(self, source: Callable[[set], Optional[Assignment]], parallel: int, on_done: Callable[[Assignment, str], None]) -> None:
        """Start assignments from `source` (called with the busy keys; None = nothing to start now, "done" = finished)
        while fewer than `parallel` run and the usage windows allow it; wait for every thread before returning."""
        threads: Dict[threading.Thread, Assignment] = {}
        finished = False
        while True:
            for t in [t for t in threads if not t.is_alive()]:
                a = threads.pop(t)
                with self.lock:
                    self.busy.pop(a.label, None)
                on_done(a, a.outcome or "abandoned")
            if self.stop or finished:
                if not threads:
                    return
                time.sleep(POLL_S)
                continue
            if len(threads) < max(1, parallel) and (not threads or self.room_for_another()):
                with self.lock:
                    a = source(set(self.busy))
                if a == "done":
                    finished = True
                    continue
                if a is not None:
                    with self.lock:
                        self.busy[a.label] = a
                    t = threading.Thread(target=self._run_thread, args=(a,), daemon=True)
                    threads[t] = a
                    t.start()
                    continue
                if not threads:
                    finished = True
                    continue
            time.sleep(POLL_S)

    def _run_thread(self, a: Assignment) -> None:
        try:
            a.outcome = self.run(a)
        except Exception as exc:                      # recorded, never silent: the next run resumes the session
            self.log("%s: engine error: %s" % (a.label, exc))
            a.outcome = a.outcome or "paused"
            self.stop = self.stop or "engine error in %s" % a.label

    def stop_all(self) -> None:
        with self.lock:
            procs = list(self.children)
        for p in procs:
            stop_child(p)


def prompt_path(run_dir: Path, job_id: str) -> Path:
    """The prompt a job was given (git-ignored: it can quote the CIO's draft; specialists may not read it)."""
    return run_dir / "_cache" / "engine" / "prompts" / ("%s.md" % job_id)


def options(**kw) -> argparse.Namespace:
    """The engine's options with their defaults (for callers and tests that do not go through the command line)."""
    base = dict(timeout_s=150 * 60, max_wait_s=12 * 3600, weekly_ceiling=WEEKLY_CEILING, parallel_ceiling=PARALLEL_CEILING,
                context_limit=CONTEXT_LIMIT, segment_turns=SEGMENT_TURNS)
    base.update(kw)
    return argparse.Namespace(**base)


def job_cost(sessions: List[dict]) -> float:
    return sum((at.get("cost_usd") or 0.0) for s in sessions for at in s.get("attempts", []))


def stop_child(proc) -> None:
    for sig, wait in ((signal.SIGTERM, 30), (signal.SIGKILL, 10)):
        try:
            os.killpg(proc.pid, sig)
        except OSError:
            return
        try:
            proc.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


def alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def rel_out(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(rl.ROOT.resolve()))
    except ValueError:
        return str(p)


def invocation(run_dir: Path, agent: str, stage: str, purpose: str) -> None:
    """The manifest's record of an agent call (what `manifest.py invocation` writes)."""
    path = run_dir / rl.RUN_MANIFEST
    if not path.exists():
        return
    m = json.loads(path.read_text(encoding="utf-8"))
    if agent == rl.AUDITOR:
        node = m.setdefault("auditor", {"status": "pending", "report": rl.AUDIT_REPORT, "invocations": []})
    elif agent in rl.SPECIALISTS:
        node = m.setdefault("specialists", {}).setdefault(agent, {"status": "pending", "invocations": []})
    else:
        node = m.setdefault("workers", {}).setdefault(agent, {"invocations": []})
    node.setdefault("invocations", []).append({"stage": stage, "purpose": purpose, "runner": "agent_driver",
                                               "at": reading.now_iso()})
    rl.write_json(path, m)


# --------------------------------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------------------------------

def lock_path(run_dir: Path) -> Path:
    return run_dir / "_cache" / "engine" / "engine.lock"


class Session:
    """One engine command: the lock, signals, caffeinate."""

    def __init__(self, eng: Engine, what: str):
        self.eng, self.what = eng, what
        self.old = {}
        self.caf = None

    def __enter__(self):
        owner = reading.driver_owner(self.eng.run_dir)
        if owner:
            raise SystemExit("another engine runs for this run (pid %s on %s since %s: %s)" % (
                owner.get("pid"), owner.get("host"), owner.get("started_at"), owner.get("what", "")))
        reading.write_json(lock_path(self.eng.run_dir), {"pid": os.getpid(), "host": socket.gethostname(),
                                                         "started_at": reading.now_iso(), "what": self.what})

        def on_signal(signum, _frame):
            self.eng.stop = self.eng.stop or "stopped by signal %d" % signum
            self.eng.stop_all()
        self.old = {s: signal.signal(s, on_signal) for s in (signal.SIGTERM, signal.SIGINT)}
        if sys.platform == "darwin" and shutil.which("caffeinate") and not os.environ.get("EQR_NO_CAFFEINATE"):
            try:
                self.caf = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())], stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)
            except OSError:
                self.caf = None
        self.eng.log("engine: %s, run %s, %s (%s); usage %s" % (
            self.what, reading.run_id_of(self.eng.run_dir), self.eng.claude, self.eng.version or "?",
            fmt_windows(self.eng.windows(refresh=True))))
        return self

    def __exit__(self, *exc):
        for s, h in self.old.items():
            signal.signal(s, h)
        if self.caf:
            self.caf.terminate()
        if lock_path(self.eng.run_dir).exists():
            lock_path(self.eng.run_dir).unlink()
        write_ledger(self.eng.run_dir)
        return False


def launch_assignment(run_dir: Path, launch: dict) -> dict:
    """The action of a launch still open from an earlier engine run (to resume its session)."""
    rid = reading.run_id_of(run_dir)
    model, effort = reading.pinned(run_dir, launch["agent"])
    path = run_dir / reading.CACHE / "launches" / ("%s.md" % launch["id"])
    role_text = "resolved (adjudicate disagreements A vs B)" if launch["role"] == "resolved" else launch["role"]
    file = reading.repo_path(run_dir, path)
    return {"action": "launch", "agent": launch["agent"], "role": launch["role"], "launch": launch["id"],
            "chunks": launch["chunks"], "model": model, "effort": effort, "file": file,
            "prompt": reading.agent_prompt(run_dir, rid, launch["agent"], role_text, file)}


def cmd_reading(eng: Engine, bakeoff: bool, max_launches: int, parallel: int) -> int:
    run_dir = eng.run_dir
    skip, failed, restarts, n = set(), [], Counter(), {"started": 0}
    resumable = [l for l in reading.load_json(reading.launches_path(run_dir), {"launches": []})["launches"]
                 if l.get("runner") == "headless" and not l.get("closed_at") and not l.get("superseded_at")]

    def source(busy: set):
        if max_launches and n["started"] >= max_launches:
            return "done" if not busy else None
        in_flight = {"%s:%s" % (c, a.role) for a in eng.busy.values() for c in a.chunks}
        while resumable:
            l = resumable.pop(0)
            if not {"%s:%s" % (c, l["role"]) for c in l["chunks"]} & in_flight:
                n["started"] += 1
                return reader_assignment(run_dir, launch_assignment(run_dir, l))
        act = reading.next_action(run_dir, bakeoff, exclude=skip | in_flight)
        if act["action"] == "done":
            if not busy:
                eng.log("done: %s" % act["message"])
            return "done" if not busy else None
        if act["action"] != "launch":
            eng.log(act.get("message", "nothing to launch"))
            eng.stop = eng.stop or act.get("message", "nothing to launch")
            return None
        n["started"] += 1
        return reader_assignment(run_dir, act)

    def on_done(a: Assignment, outcome: str):
        if outcome == "abandoned":
            restarts[a.chunks] += 1
            if restarts[a.chunks] <= RESTARTS:
                eng.log("%s: issuing its chunks afresh (the unfinished parts are set aside)" % a.label)
                return
        if outcome in ("failed", "abandoned"):
            skip.update(a.chunks)
            failed.append((a.label, a.chunks, outcome))
    eng.schedule(source, parallel, on_done)
    if max_launches and n["started"] >= max_launches and not eng.stop:
        eng.log("stopping after %d launch(es) (--max-launches)" % n["started"])
    if failed:
        eng.log("not finished: %s. Read their launch records (corpus/reading/launches.json) and the check output, fix the "
                "cause, then run the engine again." % "; ".join("%s %s (%s)" % (l, ", ".join(c), o) for l, c, o in failed))
        return 1
    if eng.stop:
        eng.log("stopped: %s; run the engine again to resume" % eng.stop)
        return 1
    return 0


def open_job(eng: Engine, agent: str, kind: str) -> Optional[dict]:
    for j in reversed(eng.jobs()["jobs"]):
        if j["agent"] == agent and j["kind"] == kind and j.get("status") in ("running", "paused"):
            return j
    return None


def run_jobs(eng: Engine, items: List[Tuple[Assignment, Optional[dict]]], parallel: int) -> int:
    """Run assignments (each with its open job to resume, or None for a new job) through the scheduler."""
    queue = list(items)
    failed = []

    def source(busy: set):
        if not queue:
            return "done" if not busy else None
        a, job = queue.pop(0)
        a.label = (job or eng.new_job(a))["id"]
        return a

    def on_done(a: Assignment, outcome: str):
        if outcome != "pass":
            failed.append((a.label, a.agent, outcome))
    eng.schedule(source, parallel, on_done)
    for a, _ in items:
        rec = next((j for j in eng.jobs()["jobs"] if j["id"] == a.label), {})
        if rec.get("integrity"):
            eng.log("%s %s: INDEPENDENCE: changed %s; the reading audit fails until the CIO resolves it" % (
                a.label, a.agent, ", ".join(rec["integrity"][:8])))
    if failed:
        eng.log("not passed: %s. Read engine/jobs.json and the validator output; fix the cause and run again." %
                "; ".join("%s %s (%s)" % f for f in failed))
        return 1
    if eng.stop:
        eng.log("stopped: %s; run the engine again to resume" % eng.stop)
        return 1
    return 0


def verifier_job(eng: Engine, name: str) -> Optional[dict]:
    for j in reversed(eng.jobs()["jobs"]):
        if j["agent"] == "verifier" and j.get("subject") == name and j.get("status") in ("running", "paused"):
            return j
    return None


def verify_specialist(eng: Engine, name: str) -> str:
    """Tier B for one specialist: the verifier re-checks a sample of its claims at the sources; every material
    discrepancy and unverifiable claim goes back to the specialist, and the verifier re-checks the corrected claims (at
    most VERIFY_ROUNDS times). What is still open is left in qc/verification/<name>.json for the CIO."""
    import verify
    run_dir = eng.run_dir
    rid = reading.run_id_of(run_dir)
    rec = rl.load_json(verify.vdir(run_dir) / ("%s.json" % name)) if (verify.vdir(run_dir) / ("%s.json" % name)).exists() else {}
    if (rec.get("tier_b") or {}).get("results") and not [f for f in rec["tier_b"].get("findings", []) if not f.get("waived")]:
        eng.log("%s: its claims were already re-checked; nothing open" % name)
        return "pass"
    if not (verify.vdir(run_dir) / ("%s_sample.csv" % name)).exists():
        verify.sample(run_dir, name)
    rel = reading.rel_run(run_dir)
    base = ("You are the VERIFIER for run %s, checking the %s specialist. RUN_DIR: %s\nRe-check every claim in "
            "%s/qc/verification/%s_sample.csv at its source, per your definition, and write %s/qc/verification/%s_claims.csv. "
            "Then run python3 scripts/verify.py claims %s %s until it reports no errors." % (
                rid, name, rel, rel, name, rel, name, rel, name))
    message = base
    for rnd in range(VERIFY_ROUNDS + 1):
        a = verifier_assignment(run_dir, name, message)
        if run_jobs(eng, [(a, verifier_job(eng, name))], 1) != 0:
            return "failed"
        tb, errs = verify.claims_result(run_dir, name)
        open_ = [f for f in tb.get("findings", []) if not f.get("waived")]
        eng.log("%s: verifier re-check %s" % (name, ", ".join("%s %d" % kv for kv in sorted((tb.get("results") or {}).items()))))
        if not open_:
            return "pass"
        if rnd == VERIFY_ROUNDS:
            eng.log("%s: %d verifier finding(s) still open after %d rounds: for the CIO (qc/verification/%s.json)" % (
                name, len(open_), VERIFY_ROUNDS, name))
            return "findings"
        verify.note_round(run_dir, name, "sent %s to the specialist" % ", ".join(f["check"] for f in open_))
        lines = verify.fix_message({"tier_a": [], "tier_b": tb}, ("blocking", "major"))
        fix = specialist_assignment(run_dir, name, specialist_prompt(run_dir, name), stage="1-verify",
                                    purpose="correct the claims the verifier found at variance with their sources")
        fix, job = resume_or_fresh(eng, fix, "The verifier re-opened a sample of your claims at their sources:\n%s\n"
                                   "Correct each claim to what the source says, as printed (value, unit, period, basis), "
                                   "and every claim, table or conclusion built on it; re-run the validator; then give your "
                                   "return message." % "\n".join(lines))
        if run_jobs(eng, [(fix, job)], 1) != 0:
            return "failed"
        verify.refresh_sample(run_dir, name)
        ids = [c.split(":", 1)[0].strip() for f in open_ for c in f["claims"]]
        message = ("RE-CHECK: the %s specialist corrected these claims: %s. Re-read their current ledger rows (the sample "
                   "file is refreshed), open each source again and update those rows in your results file; then run "
                   "python3 scripts/verify.py claims %s %s until it reports no errors." % (name, ", ".join(ids), rel, name))
    return "findings"


def cmd_verify(eng: Engine, only: List[str]) -> int:
    """Tier B for specialists whose reports exist (the engine runs it after each specialist; this re-runs it)."""
    bad = []
    for name in [n for n in SPECIALIST_ORDER if not only or n in only]:
        if not (eng.run_dir / "specialists" / ("%s.md" % name)).exists():
            continue
        if verify_specialist(eng, name) != "pass":
            bad.append(name)
    if bad:
        eng.log("verification left findings for the CIO: %s (qc/verification/)" % ", ".join(bad))
        return 1
    return 0


def cmd_specialists(eng: Engine, only: List[str], parallel: int, verify_claims: bool = True) -> int:
    run_dir = eng.run_dir
    names = [n for n in SPECIALIST_ORDER if not only or n in only]
    unknown = [n for n in only if n not in rl.SPECIALISTS]
    if unknown:
        raise SystemExit("not specialists: %s" % ", ".join(unknown))
    items = []
    for name in names:
        job = open_job(eng, name, "specialist")
        a = specialist_assignment(run_dir, name, specialist_prompt(run_dir, name))
        if not job and not a.check():
            eng.log("%s: its report already passes the validator; not run again" % name)
            continue
        earlier = [j for j in eng.jobs()["jobs"] if j["agent"] == name and j["kind"] == "specialist"]
        if not job and earlier:             # a closed job that did not pass: carry on from its files, never from zero
            a.prompt += CONTINUATION_NOTE.format(k=sum(len(j.get("sessions", [])) for j in earlier) + 1, progress=a.progress)
            a.purpose = "continue after %s (%s)" % (earlier[-1]["id"], earlier[-1].get("status", ""))
        items.append((a, job))
    if not items:
        eng.log("every specialist's report passes the validator")
        return cmd_verify(eng, only) if verify_claims else 0
    rc = 0
    if parallel <= 1:                  # one at a time: each specialist is verified before the next starts
        for item in items:
            if run_jobs(eng, [item], 1) != 0:
                rc = 1
                if eng.stop:
                    return 1
                continue
            if verify_claims and verify_specialist(eng, item[0].agent) != "pass":
                rc = 1
            if eng.stop:
                return 1
        return rc
    rc = run_jobs(eng, items, parallel)
    if verify_claims and not eng.stop:
        rc = cmd_verify(eng, [a.agent for a, _ in items]) or rc
    return rc


def resume_or_fresh(eng: Engine, a: Assignment, message: str) -> Tuple[Assignment, Optional[dict]]:
    """A follow-up continues the agent's latest session when its context is still small (the CIO's SendMessage), and
    otherwise starts a fresh session on the agent's prompt plus the follow-up. A Stage-3 follow-up of a specialist
    always starts fresh: its session may see peers' work, the independent sessions never do."""
    for j in reversed(eng.jobs()["jobs"] if not (a.agent in rl.SPECIALISTS and str(a.stage).startswith("3")) else []):
        if j["agent"] != a.agent or not j.get("sessions"):
            continue
        if a.agent in rl.SPECIALISTS and str(j.get("stage", "")).startswith("3"):
            break                         # never carry a cross-examination session into independent work
        last = j["sessions"][-1]
        if last_context(Path(last["transcript"])) < eng.o.context_limit:
            a.prompt = message
            job = eng.new_job(a)
            a.label = job["id"]
            sess = dict(last, attempts=[], ended=None, usage=None, continued_from=j["id"], started_at=reading.now_iso())
            sess.pop("ended_because", None)
            eng.update_record(a, sessions=[sess])
            a.resume_msg = message
            return a, eng.get_record(a)
        break
    base = a.prompt
    for j in reversed(eng.jobs()["jobs"]):             # the agent's own last prompt (the auditor's is not a template)
        if j["agent"] == a.agent and prompt_path(eng.run_dir, j["id"]).exists():
            base = prompt_path(eng.run_dir, j["id"]).read_text(encoding="utf-8")
            base = re.split(r"\n\n(?:FOLLOW-UP|CONTINUATION) \(", base, 1)[0]
            break
    a.prompt = (base + "\n\nFOLLOW-UP (" + a.purpose + "). Your earlier work is on disk: read your report, ledger and "
                "progress file first. Then:\n" + message)
    return a, None


def cmd_followup(eng: Engine, agent: str, message: str, purpose: str, stage: str, output: str) -> int:
    run_dir = eng.run_dir
    if agent in rl.SPECIALISTS:
        a = specialist_assignment(run_dir, agent, specialist_prompt(run_dir, agent), stage=stage, purpose=purpose,
                                  output=output)
    elif agent == rl.AUDITOR:
        a = auditor_assignment(run_dir, "", stage=stage, purpose=purpose, output=output)
    else:
        raise SystemExit("follow-ups go to a specialist or the auditor, not %s" % agent)
    a, job = resume_or_fresh(eng, a, message)
    return run_jobs(eng, [(a, job)], 1)


def write_ledger(run_dir: Path) -> None:
    """engine/ENGINE.md: every job's sessions, time, tokens, cost and the usage it took."""
    jobs = reading.load_json(run_dir / "engine" / "jobs.json", {"jobs": []})["jobs"]
    if not jobs:
        return
    lines = ["# Engine ledger — run %s" % reading.run_id_of(run_dir), "",
             "Generated by `scripts/agent_driver.py` from engine/jobs.json; do not edit. Reader sessions are on their "
             "launches (corpus/reading/launches.json; `agent_driver.py show`).", "",
             "| Job | Agent | Stage | Purpose | Model · effort | Sessions | Segments | Minutes | Peak context | Cost $ | Outcome | Integrity |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for j in jobs:
        ss = j.get("sessions", [])
        mins = sum((s.get("usage") or {}).get("minutes_first_to_last", 0) or 0 for s in ss)
        peak = max([(s.get("usage") or {}).get("peak_context", 0) or 0 for s in ss] or [0])
        lines.append("| %s | %s | %s | %s | %s · %s | %d | %d | %.0f | %s | %.2f | %s | %s |" % (
            j["id"], j["agent"], j.get("stage", ""), j.get("purpose", "").replace("|", "/"), j["model"], j["effort"], len(ss),
            sum(len(s.get("attempts", [])) for s in ss), mins, format(peak, ","), job_cost(ss),
            j.get("status", ""), "BREACH: " + ", ".join(j["integrity"][:3]) if j.get("integrity") else "clean"))
    path = run_dir / "engine" / "ENGINE.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def window_cost(rows: List[dict]) -> Dict[str, float]:
    """$ per whole window, measured: cost of segments over the utilization they moved (same window, no reset between)."""
    out = {}
    for k in ("five_hour", "seven_day"):
        cost = used = 0.0
        for at in rows:
            b, a = (at.get("util_before") or {}).get(k), (at.get("util_after") or {}).get(k)
            if b is not None and a is not None and a > b and at.get("cost_usd"):
                cost += at["cost_usd"]
                used += a - b
        if used >= 0.02:
            out[k] = cost / used
    return out


def show(run_dir: Path, last: int = 0) -> None:
    p = reading.load_json(run_dir / reading.READING / "plan.json", {"chunks": []})
    est = {c["id"]: c["est_tokens"] for c in p["chunks"]}
    launches = reading.load_json(reading.launches_path(run_dir), {"launches": []})["launches"]
    jobs = reading.load_json(run_dir / "engine" / "jobs.json", {"jobs": []})["jobs"]
    rows = []
    for l in launches:
        rows.append((l["id"], l["agent"], l["role"] + " " + ", ".join(l["chunks"]), format(sum(est.get(c, 0) for c in l["chunks"]), ","),
                     l.get("runner", "agent"), l.get("outcome", "superseded" if l.get("superseded_at") else "-"), l.get("sessions", [])))
    for j in jobs:
        rows.append((j["id"], j["agent"], "%s %s" % (j.get("stage", ""), j.get("purpose", "")), "-", "headless",
                     j.get("status", "-"), j.get("sessions", [])))
    rows = rows[-last:] if last else rows
    print("| Id | Agent | Work | Chunk tokens | Runner | Outcome | Sessions | Minutes | API turns | Processed | Output | Peak context | Cost $ |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    attempts = []
    for rid, agent, work, tok, runner, outcome, sessions in rows:
        u = Counter()
        for s in sessions:
            us = s.get("usage") or (transcript_usage(Path(s["transcript"])) if s.get("transcript") else {})
            for k in ("minutes_first_to_last", "api_turns", "processed", "output"):
                u[k] += us.get(k, 0) or 0
            u["peak"] = max(u["peak"], us.get("peak_context", 0) or 0)
            attempts += s.get("attempts", [])
        print("| %s | %s | %s | %s | %s | %s | %d | %s | %s | %s | %s | %s | %s |" % (
            rid, agent, work[:60], tok, runner, outcome, len(sessions),
            round(u["minutes_first_to_last"], 1) if sessions else "-", u["api_turns"] or "-",
            format(u["processed"], ",") if u["processed"] else "-", format(u["output"], ",") if u["output"] else "-",
            format(u["peak"], ",") if u["peak"] else "-", "%.2f" % job_cost(sessions) if sessions else "-"))
    wc = window_cost(attempts)
    if wc:
        print("\nMeasured from these sessions: one five-hour window ≈ $%s; one weekly window ≈ $%s (API-equivalent)." % (
            "%.0f" % wc["five_hour"] if "five_hour" in wc else "?", "%.0f" % wc["seven_day"] if "seven_day" in wc else "?"))


def probe(eng: Engine) -> int:
    """The headless counterpart of `--validate-only --probe`: one specialist, configuration only, on Haiku."""
    msg = ("CONFIGURATION CHECK ONLY. Do not research, use web tools, write files or run commands. Reply in one line: "
           "PRELOADED=<Y/N: is the investment constitution (its epistemic tags FACT, MANAGEMENT STATEMENT, CALCULATION "
           "and the claim-ID citation syntax) in your context>; PREFIX=<your claim-ID prefix>; "
           "MODEL=<model id in your system context>; AGENT_TOOL=<Y/N>.")
    sp = skills_prompt("bear-case", Path(tempfile.gettempdir()) / "eqr-probe")
    cmd = [eng.claude, "-p", msg, "--agent", "bear-case", "--model", "haiku", "--tools", ",".join(agent_tools("bear-case")),
           "--strict-mcp-config", "--disable-slash-commands", "--permission-mode", "dontAsk", "--output-format", "json",
           "--no-session-persistence", "--append-system-prompt-file", str(sp)]
    r = subprocess.run(cmd, cwd=str(rl.ROOT), env=child_env(), capture_output=True, text=True, timeout=300,
                       stdin=subprocess.DEVNULL)
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("no result: %s" % (r.stderr.strip()[-500:] or r.stdout.strip()[-500:]))
        return 1
    print(o.get("result", ""))
    res = str(o.get("result", ""))
    ok = "PREFIX=BEAR" in res and "AGENT_TOOL=N" in res and "PRELOADED=Y" in res
    print("probe %s (expected PRELOADED=Y, PREFIX=BEAR, AGENT_TOOL=N); cost $%.4f" % ("OK" if ok else "UNEXPECTED",
                                                                                    o.get("total_cost_usd") or 0))
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, timeout_min):
        p.add_argument("run_dir")
        p.add_argument("--timeout-min", type=float, default=timeout_min, help="longest one segment may run before it is resumed")
        p.add_argument("--max-wait-hours", type=float, default=12, help="longest wait for a usage window to reset")
        p.add_argument("--weekly-ceiling", type=float, default=WEEKLY_CEILING,
                       help="no segment starts above this share of the weekly window (default %(default)s)")
        p.add_argument("--parallel-ceiling", type=float, default=PARALLEL_CEILING,
                       help="with --parallel, another session starts only below this share of the five-hour window")
        p.add_argument("--context-limit", type=int, default=CONTEXT_LIMIT,
                       help="long agents continue in a fresh session above this context (tokens)")
        p.add_argument("--segment-turns", type=int, default=SEGMENT_TURNS)
        p.add_argument("--claude", help="the claude binary (default: $CLAUDE_BIN, PATH, or an editor extension's)")
        p.add_argument("--dry-run", action="store_true", help="print the first session's command; run nothing")
    r = sub.add_parser("reading")
    common(r, 150)
    r.add_argument("--bakeoff", action="store_true", help="only the calibration chunks (reading.py bakeoff plan)")
    r.add_argument("--max-launches", type=int, default=0, help="stop after this many launches (0: until done)")
    r.add_argument("--parallel", type=int, default=1)
    lb = sub.add_parser("librarian")
    common(lb, 120)
    lb.add_argument("--message-file", required=True)
    s = sub.add_parser("specialists")
    common(s, 120)
    s.add_argument("--only", default="", help="comma-separated specialists (default: all ten, in cio.md order)")
    s.add_argument("--parallel", type=int, default=1)
    s.add_argument("--no-verify", action="store_true", help="skip the verifier's re-check of each specialist's claims")
    vf = sub.add_parser("verify")
    common(vf, 120)
    vf.add_argument("--only", default="")
    f = sub.add_parser("followup")
    common(f, 120)
    f.add_argument("agent")
    f.add_argument("--message-file", required=True)
    f.add_argument("--purpose", required=True)
    f.add_argument("--stage", default="2")
    f.add_argument("--output", default="", help="the file the follow-up must write (specialists/<name>_followup_<n>.md, "
                                                 "audit/audit_followup_<n>.md); it is validated")
    au = sub.add_parser("audit")
    common(au, 120)
    au.add_argument("--message-file", required=True)
    pp = sub.add_parser("prompt")
    pp.add_argument("run_dir")
    pp.add_argument("specialist", choices=sorted(rl.SPECIALISTS))
    sh = sub.add_parser("show")
    sh.add_argument("run_dir")
    sh.add_argument("--last", type=int, default=0)
    us = sub.add_parser("usage")
    us.add_argument("--probe", action="store_true", help="refresh with a one-line Haiku call")
    us.add_argument("--claude")
    pr = sub.add_parser("probe")
    pr.add_argument("--claude")
    c = sub.add_parser("cli")
    c.add_argument("--claude")
    a = ap.parse_args(argv)
    if a.cmd == "cli":
        claude = find_claude(a.claude)
        print(claude or "not found")
        if claude:
            print(claude_version(claude))
        return 0 if claude else 1
    if a.cmd in ("usage", "probe"):
        claude = find_claude(a.claude)
        if not claude:
            print("no claude binary found (set CLAUDE_BIN or pass --claude)")
            return 1
        eng = Engine(Path("."), claude, argparse.Namespace(), log=print)
        if a.cmd == "probe":
            return probe(eng)
        if a.probe:
            eng.note_usage(probe_usage(claude), "probe")
        print("usage: %s (as of %s)" % (fmt_windows(eng.windows()), dt.datetime.fromtimestamp(eng.usage_at).strftime(
            "%Y-%m-%d %H:%M") if eng.usage_at else "never"))
        return 0
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if a.cmd == "show":
        show(run_dir, a.last)
        return 0
    if a.cmd == "prompt":
        print(specialist_prompt(run_dir, a.specialist))
        return 0
    claude = find_claude(a.claude)
    if not claude:
        print("no claude binary found (set CLAUDE_BIN or pass --claude). Without it, launch the agents through the Agent "
              "tool as cio.md describes (reading.py next for the readers).")
        return 1
    a.timeout_s = a.timeout_min * 60
    a.max_wait_s = a.max_wait_hours * 3600
    logf = run_dir / "_cache" / "engine" / "engine.log"
    logf.parent.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        line = "%s %s" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
        print(line, flush=True)
        with logf.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    eng = Engine(run_dir, claude, a, log=log)
    if a.dry_run:
        return dry_run(eng, a)
    with Session(eng, a.cmd):
        if a.cmd == "reading":
            return cmd_reading(eng, a.bakeoff, a.max_launches, a.parallel)
        if a.cmd == "specialists":
            return cmd_specialists(eng, [x.strip() for x in a.only.split(",") if x.strip()], a.parallel, not a.no_verify)
        if a.cmd == "verify":
            return cmd_verify(eng, [x.strip() for x in a.only.split(",") if x.strip()])
        message = Path(a.message_file).read_text(encoding="utf-8")
        if a.cmd == "followup":
            return cmd_followup(eng, a.agent, message, a.purpose, a.stage, a.output)
        if a.cmd == "audit":
            job = open_job(eng, rl.AUDITOR, "auditor")
            return run_jobs(eng, [(auditor_assignment(run_dir, message), job)], 1)
        if a.cmd == "librarian":
            job = open_job(eng, "librarian", "librarian")
            return run_jobs(eng, [(librarian_assignment(run_dir, message), job)], 1)
    return 2


def dry_run(eng: Engine, a) -> int:
    run_dir = eng.run_dir
    if a.cmd == "reading":
        p = reading.load_json(run_dir / reading.READING / "plan.json")
        if not p:
            print("no plan: run reading.py plan first")
            return 1
        got = reading.plan_next(run_dir, p, rl.model_policy(), a.bakeoff)
        if not got:
            print("nothing to launch: every chunk is read, checked and reconciled")
            return 0
        role, batch = got
        agent = reading.ROLE_AGENT[role]
        model, effort = reading.pinned(run_dir, agent)
        act = {"agent": agent, "model": model, "effort": effort, "chunks": [c["id"] for c in batch], "role": role,
               "launch": "<launch>", "prompt": "<launch prompt>"}
        asg = reader_assignment(run_dir, act)
    elif a.cmd == "specialists":
        name = ([x for x in a.only.split(",") if x] or list(SPECIALIST_ORDER))[0]
        asg = specialist_assignment(run_dir, name, specialist_prompt(run_dir, name))
    elif a.cmd == "audit":
        asg = auditor_assignment(run_dir, "<prompt>")
    elif a.cmd == "librarian":
        asg = librarian_assignment(run_dir, "<prompt>")
    else:
        asg = specialist_assignment(run_dir, a.agent, "<prompt>")
    print("next: %s (%s at %s)%s" % (asg.agent, asg.model, asg.effort, " on " + ", ".join(asg.chunks) if asg.chunks else ""))
    print(" ".join(json.dumps(x) if " " in x else x for x in eng.command(asg, "<session id>", "<prompt>", False,
                                                                       a.segment_turns if asg.long else 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
