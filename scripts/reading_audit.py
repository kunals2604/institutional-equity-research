#!/usr/bin/env python3
"""Reading audit: what each agent actually read, on which model and effort — measured from its transcript.

  python3 scripts/reading_audit.py session                       # model and effort of this Claude Code session (Stage 0)
  python3 scripts/reading_audit.py run RUN_DIR [--transcripts DIR] [--waive "<reason>"]   # Stage 4

Why. In run BHARTIARTL 20261012T132311Z the reports said "annual reports read" while the ten agents together had seen
11–17 % of each report's text, and every agent ran at effort *high* while the owner believed *max*. Self-reported
coverage and configuration are not evidence. Claude Code keeps each agent's transcript on this machine
(~/.claude/projects/<project>/<session>/subagents/agent-*.jsonl, with a .meta.json naming the agent type); this
script reads them and checks, independently of what any agent wrote:

  * every agent of the run ran on the model and effort pinned for it (`methodology/MODEL_POLICY.md`, or the run's
    recorded `--effort` override) — the CIO's own session included;
  * every reader and critical-reader received every line of every chunk file it was assigned (through Read, or the
    same lines through a shell command) and opened every VIEW REQUIRED page of the PDF;
  * every specialist read every dossier of its reading pack (≥ 95 % of the dossier's lines reached its context, over
    all of its sessions);
  * independence: no specialist touched another specialist's work (report, ledger, follow-ups, workpapers, calc and
    scratch files), the CIO's, the auditor's or the QC files, the engine's records, another run, the archive, the
    scoreboard or an agent transcript — in any tool call, or in a search result that printed their content — and the
    engine's fingerprints show no specialist changed a file it does not own.

The run's agents are found by the run ID in their launch description (the CIO puts it there) or in their first
prompt; agents run by `agent_driver.py` are headless sessions whose ids their records hold (readers on their launch in
corpus/reading/launches.json, every other agent on its job in engine/jobs.json). A document reused from an earlier run is checked from that run's passed audit and the SHA-256 of the copied files. An
agent that ran above its pinned effort is a warning, below it an error. If no transcript can be found (another
machine, a changed transcript format), the result is NOT_MEASURABLE:
`validate_run.py --stage final` then fails unless the CIO records a waiver with the reason (`--waive`).
Writes RUN_DIR/qc/reading_audit.json and RUN_DIR/qc/READING_AUDIT.md. Exit: 0 PASS (or waived), 1 FAIL or not
measurable, 2 usage.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

DOSSIER_MIN_SHARE = 0.95
READ_PREFIX_RE = re.compile(r"^\s*(\d+)\t")


def transcripts_dir(arg: Optional[str] = None) -> Path:
    if arg:
        return Path(arg).expanduser()
    if os.environ.get("CLAUDE_TRANSCRIPTS_DIR"):
        return Path(os.environ["CLAUDE_TRANSCRIPTS_DIR"]).expanduser()
    slug = re.sub(r"[^A-Za-z0-9-]", "-", str(rl.ROOT.resolve()))
    return Path.home() / ".claude" / "projects" / slug


def family(model_id: str) -> str:
    m = (model_id or "").lower()
    for f in ("opus", "sonnet", "haiku", "fable"):
        if f in m:
            return f
    return m or "unknown"


def load_lines(path: Path) -> List[dict]:
    out = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def tool_events(entries: List[dict]) -> List[Tuple[dict, str]]:
    """[(tool_use block, result text)] in order."""
    uses, out = {}, []
    for d in entries:
        msg = d.get("message") or {}
        if d.get("type") == "assistant":
            for b in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    uses[b["id"]] = b
        elif d.get("type") == "user" and isinstance(msg.get("content"), list):
            for b in msg["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = b.get("content")
                    text = c if isinstance(c, str) else "\n".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
                    u = uses.get(b.get("tool_use_id"))
                    if u:
                        out.append((u, text))
    return out


def profile(entries: List[dict]) -> dict:
    models, efforts, calls, limits = Counter(), Counter(), set(), 0
    first = last = ""
    for d in entries:
        ts = d.get("timestamp", "")
        first = first or ts
        last = ts or last
        if d.get("effort"):
            efforts[str(d["effort"])] += 1
        msg = d.get("message") or {}
        if d.get("type") == "assistant":
            mod = msg.get("model", "")
            if mod == "<synthetic>":
                text = " ".join(b.get("text", "") for b in msg.get("content", []) if isinstance(b, dict))
                limits += "limit" in text.lower()
            elif mod:
                models[mod] += 1
                if msg.get("id"):
                    calls.add(msg["id"])
    return {"models": dict(models), "efforts": dict(efforts), "api_calls": len(calls), "first": first, "last": last,
            "usage_limit_stops": limits}


def first_prompt(entries: List[dict]) -> str:
    for d in entries:
        if d.get("type") == "user":
            c = (d.get("message") or {}).get("content")
            return c if isinstance(c, str) else " ".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
    return ""


def find_agents(tdir: Path, run_id: str) -> List[dict]:
    out = []
    for meta in sorted(tdir.glob("*/subagents/*.meta.json")):
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
        except ValueError:
            continue
        jl = meta.with_name(meta.name.replace(".meta.json", ".jsonl"))
        if not jl.exists():
            continue
        desc = m.get("description", "")
        if run_id not in desc:
            with jl.open(encoding="utf-8", errors="replace") as f:
                head = f.read(20000)
            if run_id not in head:
                continue
        out.append({"type": m.get("agentType", ""), "description": desc, "path": jl})
    return out


def find_main_sessions(tdir: Path, run_id: str) -> List[Path]:
    out = []
    for jl in sorted(tdir.glob("*.jsonl")):
        with jl.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if run_id in line:
                    out.append(jl)
                    break
    return out


EFFORT_RANK = {"low": 0, "medium": 1, "high": 2, "xhigh": 3, "max": 4}


def headless_sessions(run_dir: Path, tdir: Path) -> List[dict]:
    """Sessions run by agent_driver.py, from its records: readers on their launches (launches.json), every other agent
    on its job (engine/jobs.json). One entry per session id (a follow-up may continue an earlier session), typed by
    the agent, described as a subagent launch is ("<agent> <run id> <launch or job id>")."""
    run_id = rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id", run_dir.name)
    out, seen = [], set()
    records = []
    path = run_dir / "corpus" / "reading" / "launches.json"
    if path.exists():
        records += rl.load_json(path).get("launches", [])
    jobs = run_dir / "engine" / "jobs.json"
    if jobs.exists():
        records += rl.load_json(jobs).get("jobs", [])
    for l in records:
        for s in l.get("sessions", []):
            jl = tdir / ("%s.jsonl" % s["session_id"])
            if jl.exists() and s["session_id"] not in seen:
                seen.add(s["session_id"])
                out.append({"type": l["agent"], "description": "%s %s %s" % (l["agent"], run_id, l["id"]), "path": jl,
                            "session_id": s["session_id"], "headless": True, "job": l["id"]})
    return out


def independence_patterns(me: str, run_id: str) -> Tuple[re.Pattern, re.Pattern]:
    """(what a specialist's tool calls must not name, what its tool results must not print as content)."""
    others = "|".join(re.escape(o) for o in sorted(rl.SPECIALISTS, key=len, reverse=True) if o != me)
    files = (r"specialists/(?:%s)(?:\.md|_ledger|_followup|_workpapers)|calc/(?:%s)_|_cache/scratch/(?:%s)/"
             % (others, others, others))
    calls = re.compile(r"(?:%s)|(?:runs/[\w.-]+|\$\{?\w+\}?|RUN_DIR)/(?:cio|audit|qc|engine)/|_cache/engine/|"
                       r"COMPANY_SCOREBOARD|latest_run\.txt|(?<![\w.])archive/|\.claude/projects/|"
                       r"runs/(?!%s\b)\d{8}T\d{6}Z" % (files, re.escape(run_id)))
    content = re.compile(r"(?:%s)[^\s:]*:" % files)
    return calls, content


HEREDOC_TO_FILE_RE = re.compile(r"(?:cat|tee)\s+[^\n]*?<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\1\b", re.S)
TOOL_RESULTS_RE = re.compile(r"tool-results/([\w.-]+)")
PATH_FIELDS = ("file_path", "path", "pattern", "notebook_path")


def independence_breaches(me: str, run_id: str, events: List[Tuple[dict, str]]) -> List[str]:
    """Contacts of a specialist's tool calls with what it must not see. Read/Grep/Glob paths and shell commands are
    checked (text a command writes into a file through a heredoc is content, not a read, and is left out); Write and
    Edit only by the file they write; a search result that prints another specialist's file with its content counts.
    A persisted tool output (~/.claude/projects/.../tool-results/) is the session's own when one of its tool results
    announced it."""
    calls, content = independence_patterns(me, run_id)
    own = set()
    for _, text in events:
        own.update(TOOL_RESULTS_RE.findall(text or ""))
    out = []
    for u, text in events:
        name = u.get("name") or ""
        inp = u.get("input") or {}
        if name in ("WebSearch", "WebFetch"):
            continue
        if name == "Bash":
            blob = HEREDOC_TO_FILE_RE.sub(" ", str(inp.get("command", "")))
        else:
            blob = " ".join(str(inp[k]) for k in PATH_FIELDS if isinstance(inp.get(k), str))
        for m in calls.finditer(blob):
            if m.group(0) == ".claude/projects/":
                tr = TOOL_RESULTS_RE.search(blob[m.end():m.end() + 300])
                if tr and tr.group(1) in own:
                    continue
            out.append("%s call names %r: %s" % (name, m.group(0), blob[:160]))
            break
        else:
            m = content.search(text or "") if name in ("Bash", "Grep") else None
            if m:
                out.append("%s result printed %r (another specialist's work)" % (name, m.group(0)))
    return out


def expected_for(agent_type: str, override: Optional[str], pol: dict) -> Tuple[str, str]:
    spec = pol["agents"].get(agent_type, {})
    model, effort = spec.get("model", ""), spec.get("effort", "")
    if override and model == "opus" and agent_type != "cio":
        effort = override
    return model, effort


def lines_seen_in_reads(events: List[Tuple[dict, str]], target: str) -> Set[int]:
    """Line numbers of `target` returned by Read calls (the result lines carry their numbers)."""
    seen = set()
    for u, text in events:
        if u.get("name") != "Read":
            continue
        fp = str((u.get("input") or {}).get("file_path", ""))
        if not same_file(fp, target):
            continue
        for ln in text.split("\n"):
            m = READ_PREFIX_RE.match(ln)
            if m:
                seen.add(int(m.group(1)))
    return seen


def other_tool_text(events: List[Tuple[dict, str]]) -> Set[str]:
    out = set()
    for u, text in events:
        if u.get("name") in ("Bash",):
            for ln in text.split("\n"):
                t = ln.strip()
                if t:
                    out.add(t)
    return out


def same_file(a: str, b: str) -> bool:
    """True when two spellings name the same file (absolute vs repository-relative)."""
    if not a or not b:
        return False
    a, b = a.replace("\\", "/"), b.replace("\\", "/")
    return a == b or a.endswith("/" + b.lstrip("./")) or b.endswith("/" + a.lstrip("./"))


RENDER_RE = re.compile(r"_cache/reading/render/(?P<doc>[^/]+?)-p(?P<page>\d+)-\d+dpi[^/]*\.png$")


def pages_viewed(events: List[Tuple[dict, str]], pdf: str, doc_key: str = "") -> Set[int]:
    """Pages opened on the rendered page: a Read of the PDF with `pages`, or a Read of a `reading.py render` image of
    the same document (RUN_DIR/_cache/reading/render/<doc>-p<page>-<dpi>dpi....png)."""
    got = set()
    for u, _ in events:
        if u.get("name") != "Read":
            continue
        inp = u.get("input") or {}
        fp = str(inp.get("file_path", ""))
        m = RENDER_RE.search(fp.replace("\\", "/"))
        if m and doc_key and m.group("doc") == doc_key:
            got.add(int(m.group("page")))
            continue
        if not fp.lower().endswith(".pdf") or not same_file(fp, pdf):
            continue
        spec = str(inp.get("pages") or "")
        for part in re.split(r"\s*,\s*", spec):
            m = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", part)
            if m:
                a = int(m.group(1))
                b = int(m.group(2) or a)
                got.update(range(a, b + 1))
    return got


def prompt_text(entries: List[dict]) -> str:
    """Every text the session was given in its user messages (a one-shot reader receives its chunk this way)."""
    out = []
    for d in entries:
        if d.get("type") != "user":
            continue
        c = (d.get("message") or {}).get("content")
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, list):
            out += [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
    return "\n".join(out)


PROMPT_PAGE_RE = re.compile(r"\[VIEW REQUIRED page (\d+) of ([^,\]]+), rendered\]")


def file_coverage(events: List[Tuple[dict, str]], path: Path, display: str, prompt: str = "") -> Tuple[int, int, List[int]]:
    """(non-blank lines seen, non-blank lines in file, first missing line numbers)."""
    lines = path.read_text(encoding="utf-8").split("\n")
    via_read = lines_seen_in_reads(events, display) | lines_seen_in_reads(events, str(path))
    shell = other_tool_text(events) | {x.strip() for x in prompt.split("\n") if x.strip()}
    total = seen = 0
    missing = []
    for i, ln in enumerate(lines, 1):
        if not ln.strip():
            continue
        total += 1
        if i in via_read or ln.strip() in shell:
            seen += 1
        elif len(missing) < 10:
            missing.append(i)
    return seen, total, missing


def session(args) -> int:
    tdir = transcripts_dir(args.transcripts)
    mains = sorted(tdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True) if tdir.exists() else []
    if not mains:
        print("NOT MEASURABLE: no session transcripts under %s" % tdir)
        return 1
    entries = load_lines(mains[0])[-600:]
    prof = profile(entries)
    eff = [d.get("effort") for d in entries if d.get("effort")]
    model = next((d["message"]["model"] for d in reversed(entries) if d.get("type") == "assistant"
                  and (d.get("message") or {}).get("model") not in (None, "", "<synthetic>")), "unknown")
    effort = eff[-1] if eff else "unknown"
    pol = rl.model_policy()["agents"]["cio"]
    ok = family(model) == pol["model"] and effort == pol["effort"]
    print("session %s: model %s, effort %s -> %s (policy: CIO on %s at %s)" % (
        mains[0].stem, model, effort, "OK" if ok else "NOT AS PINNED", pol["model"], pol["effort"]))
    if not ok:
        print("Tell the owner before research starts: switch the session to %s at %s effort in the model picker, "
              "or confirm the run should proceed as it is (record the answer in the manifest notes)."
              % (pol["model"].capitalize(), pol["effort"]))
    return 0 if ok else 1


def run_audit(run_dir: Path, tdir: Path, waive: str = "") -> dict:
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    run_id = m.get("run_id", run_dir.name)
    override = (m.get("model") or {}).get("effort_override") or None
    pol = rl.model_policy()
    res = {"run_id": run_id, "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
           "transcripts": str(tdir), "status": "", "errors": [], "warnings": [], "agents": [], "readers": [],
           "specialists": [], "cio": {}, "waiver": waive or ""}
    agents = find_agents(tdir, run_id) if tdir.exists() else []
    heads = headless_sessions(run_dir, tdir) if tdir.exists() else []
    head_ids = {h["session_id"] for h in heads}
    agents += heads
    mains = [jl for jl in (find_main_sessions(tdir, run_id) if tdir.exists() else []) if jl.stem not in head_ids]
    reading_plan = rl.load_json(run_dir / "corpus" / "reading" / "plan.json") if (run_dir / "corpus" / "reading" / "plan.json").exists() else {}
    reused_chunks = [c for c in reading_plan.get("chunks", []) if c.get("reused")]
    if not agents and not mains and not reused_chunks:
        res["status"] = "NOT_MEASURABLE"
        res["errors"].append("no transcripts for run %s under %s" % (run_id, tdir))
        return res
    # Models and efforts -----------------------------------------------------------------------------------
    for a in agents:
        entries = load_lines(a["path"])
        prof = profile(entries)
        want_model, want_effort = expected_for(a["type"], override, pol)
        fams = {family(x) for x in prof["models"]}
        efforts = set(prof["efforts"])
        row = {"agent": a["type"], "description": a["description"], "transcript": str(a["path"]), **prof,
               "expected_model": want_model, "expected_effort": want_effort}
        if want_model and fams and fams != {want_model}:
            res["errors"].append("%s (%s) ran on %s, pinned %s" % (a["type"], a["description"], sorted(fams), want_model))
        if want_effort:
            below = sorted(e for e in efforts if EFFORT_RANK.get(e, -1) < EFFORT_RANK.get(want_effort, 0))
            above = sorted(e for e in efforts if EFFORT_RANK.get(e, -1) > EFFORT_RANK.get(want_effort, 0))
            if not efforts:
                res["warnings"].append("%s (%s): the transcript records no effort; expected %s" % (a["type"], a["description"], want_effort))
            elif below:
                res["errors"].append("%s (%s) ran at effort %s, pinned %s" % (a["type"], a["description"], sorted(efforts), want_effort))
            elif above:
                res["warnings"].append("%s (%s) ran at effort %s, above its pinned %s" % (
                    a["type"], a["description"], sorted(efforts), want_effort))
        res["agents"].append(row)
        a["entries"] = entries
    t0 = str(m.get("started_at") or "")[:19]
    t1 = str(m.get("completed_at") or "9999")[:19]
    for jl in mains:                          # only the part of the session that ran this run
        prof = profile([d for d in load_lines(jl) if not d.get("timestamp") or t0 <= d["timestamp"][:19] <= t1])
        res["cio"][jl.stem] = prof
        want = pol["agents"]["cio"]
        if prof["models"] and {family(x) for x in prof["models"]} != {want["model"]}:
            res["warnings"].append("CIO session %s ran on %s (policy: %s)" % (jl.stem, sorted(prof["models"]), want["model"]))
        if prof["efforts"] and set(prof["efforts"]) != {want["effort"]}:
            res["warnings"].append("CIO session %s ran at effort %s (policy: %s)" % (jl.stem, sorted(prof["efforts"]), want["effort"]))
    # Readers: every chunk the record depends on was received in full, with its VIEW REQUIRED pages, by an agent ----
    import reading as rd  # noqa: E402  (the plan's rules: which roles each chunk needs)
    reading = run_dir / "corpus" / "reading"
    launches = {l["id"]: l for l in rl.load_json(reading / "launches.json").get("launches", [])} if (reading / "launches.json").exists() else {}
    cache = run_dir / "_cache" / "reading"
    complete: Dict[Tuple[str, str], dict] = {}
    best: Dict[Tuple[str, str], dict] = {}
    seen_launches = set()
    for a in agents:
        if a["type"] not in set(rd.ROLE_AGENT.values()):
            continue
        lid = next((tok for tok in a["description"].split() if re.fullmatch(r"L\d{3,}", tok)), "")
        launch = launches.get(lid)
        if not launch:
            res["errors"].append("%s (%s): no launch id that matches corpus/reading/launches.json" % (a["type"], a["description"]))
            continue
        seen_launches.add(lid)
        if launch.get("superseded_at"):
            res["readers"].append({"agent": a["type"], "launch": lid, "role": launch["role"], "chunks": launch["chunks"],
                                   "superseded": launch["superseded_at"], "reason": launch.get("superseded_reason", "")})
            res["warnings"].append("%s %s: superseded by a new plan (%s); its work is in %s" % (
                a["type"], lid, launch.get("superseded_reason", ""), launch.get("superseded_to", "")))
            continue
        events = tool_events(a["entries"])
        prompt = prompt_text(a["entries"])
        for cid in launch["chunks"]:
            if launch["role"] == "resolved":
                target = reading / "disagreements" / ("%s.json" % cid)
                seen, total, missing = file_coverage(events, target, str(target), prompt) if target.exists() else (0, 0, [])
                view_missing = []
            else:
                store_path = cache / "chunks" / ("%s.json" % cid)
                if not store_path.exists():
                    res["errors"].append("%s %s: chunk %s has no cached file to compare against" % (a["type"], lid, cid))
                    continue
                store = json.loads(store_path.read_text(encoding="utf-8"))
                chunk_file = cache / "chunks" / ("%s.md" % cid)
                seen, total, missing = file_coverage(events, chunk_file, store.get("file", ""), prompt)
                need = set(store.get("visual_pages", [])) | set(store.get("verify_pages", [])) | set(store.get("image_pages", []))
                shown = {int(pg) for pg, doc in PROMPT_PAGE_RE.findall(prompt) if doc == store.get("doc")}
                view_missing = sorted(need - pages_viewed(events, store.get("pdf", ""), store.get("doc", "")) - shown)
            row = {"agent": a["type"], "launch": lid, "role": launch["role"], "chunk": cid, "lines_seen": seen,
                   "lines_total": total, "first_missing_lines": missing, "view_pages_missing": view_missing,
                   "outcome": launch.get("outcome", ""), "session": a.get("session_id", "")}
            res["readers"].append(row)
            key = (cid, launch["role"])
            ok = bool(total) and seen >= total and not view_missing
            if ok:
                complete[key] = row
            elif key not in best or seen > best[key]["lines_seen"]:
                best[key] = row
    for lid, l in launches.items():
        if lid not in seen_launches and not l.get("superseded_at"):
            res["warnings"].append("launch %s (%s %s): no transcript of its agent was found" % (lid, l["role"], ", ".join(l["chunks"])))
        if l.get("outcome") in ("abandoned", "failed"):
            res["warnings"].append("launch %s (%s %s) was closed %s (%s); its chunks were issued again" % (
                lid, l["role"], ", ".join(l["chunks"]), l["outcome"], l.get("note", "")))
    pol = rd.run_policy(run_dir)
    for key, b in sorted(best.items()):               # an incomplete read is an error unless the chunk was read again
        if key in complete or launches.get(b["launch"], {}).get("outcome") in ("abandoned", "failed"):
            continue
        if b["lines_total"] and b["lines_seen"] < b["lines_total"]:
            res["errors"].append("%s %s did not receive every line of %s: %d of %d (first missing %s)" % (
                b["agent"], b["launch"], b["chunk"], b["lines_seen"], b["lines_total"], b["first_missing_lines"][:5]))
        if b["view_pages_missing"]:
            res["errors"].append("%s %s did not open VIEW REQUIRED pages %s of %s" % (
                b["agent"], b["launch"], b["view_pages_missing"], b["chunk"]))
    for c in reading_plan.get("chunks", []):          # every extraction in the record came from an agent's read
        if c.get("reused"):
            continue
        for role in rd.ROLES:
            key = (c["id"], role)
            if rd.extraction_path(run_dir, c["id"], role).exists() and key not in complete and key not in best:
                res["errors"].append("%s %s: no transcript shows an agent reading %s" % (rd.ROLE_AGENT[role], role, c["id"]))
    # Reused documents: the earlier run's audit passed them and the copies are the same bytes ----------------------
    res["reused"] = []
    for c in reused_chunks:
        r = c["reused"]
        prior = run_dir.parent / r["run"]
        audited = rd.audited_reads(prior) if prior.exists() else set()
        need = set(rd.required_roles(c, pol))
        if any(f.startswith("corpus/reading/extractions/") and f.endswith(".resolved.jsonl") for f in r.get("files", {})):
            need.add("resolved")
        bad = [f for f, sha in r.get("files", {}).items()
               if not (run_dir / f).exists() or rd.file_sha256(run_dir / f) != sha]
        missing_audit = sorted(role for role in need if (c["id"], role) not in audited)
        ok = not bad and not missing_audit
        res["reused"].append({"chunk": c["id"], "from_run": r["run"], "roles": sorted(need), "verified": ok})
        if bad:
            res["errors"].append("reused chunk %s: copied file(s) changed since the copy: %s" % (c["id"], ", ".join(bad)))
        if missing_audit:
            res["errors"].append("reused chunk %s: run %s's reading audit does not show a complete read for %s" % (
                c["id"], r["run"], ", ".join(missing_audit)))
    # Specialists: their reading pack, over all of their sessions ---------------------------------------------
    packs = run_dir / "corpus" / "dossiers" / "packs"
    by_specialist: Dict[str, List[Tuple[dict, str]]] = defaultdict(list)
    for a in agents:
        if a["type"] in rl.SPECIALISTS:
            by_specialist[a["type"]] += tool_events(a["entries"])
    for name, events in sorted(by_specialist.items()):
        pack = packs / ("%s.md" % name)
        if not pack.exists():
            continue
        for rel in re.findall(r"`(corpus/dossiers/[\w.-]+\.md)`", pack.read_text(encoding="utf-8")):
            path = run_dir / rel
            if not path.exists():
                continue
            seen, total, missing = file_coverage(events, path, rel)
            share = seen / total if total else 1.0
            res["specialists"].append({"agent": name, "dossier": rel, "lines_seen": seen, "lines_total": total,
                                       "share": round(share, 3)})
            if share < DOSSIER_MIN_SHARE:
                res["errors"].append("%s read %.0f%% of %s (its reading pack requires all of it)" % (name, 100 * share, rel))
    # Independence: no specialist touched another's work, the CIO's or the auditor's -----------------------------
    res["independence"] = []
    jobs_path = run_dir / "engine" / "jobs.json"
    job_stage = {j["id"]: str(j.get("stage", "")) for j in (rl.load_json(jobs_path).get("jobs", []) if jobs_path.exists() else [])}
    for a in agents:
        if a["type"] not in rl.SPECIALISTS:
            continue
        stage = job_stage.get(a.get("job", ""), "")
        if a.get("headless") and not (stage.startswith("1") or stage.startswith("2")):
            continue                      # Stage 3 cross-examination may see peers' work (cio.md Stage 3)
        found = independence_breaches(a["type"], run_id, tool_events(a["entries"]))
        mixed = not a.get("headless") and any(
            d.get("type") == "user" and isinstance((d.get("message") or {}).get("content"), str)
            and "follow-up" in d["message"]["content"].lower() for d in a["entries"][1:])
        res["independence"].append({"agent": a["type"], "description": a["description"], "breaches": len(found)})
        for b in found[:5]:
            # a subagent resumed for a Stage-3 follow-up shares one transcript with its initial work: a warning
            (res["warnings"] if mixed else res["errors"]).append("INDEPENDENCE %s (%s): %s" % (a["type"], a["description"], b))
    for j in (rl.load_json(jobs_path).get("jobs", []) if jobs_path.exists() else []):
        if j.get("integrity"):
            res["errors"].append("INDEPENDENCE %s %s changed files it does not own: %s" % (
                j["agent"], j["id"], ", ".join(j["integrity"][:8])))
    res["status"] = "PASS" if not res["errors"] else "FAIL"
    return res


def write(run_dir: Path, res: dict) -> None:
    (run_dir / rl.READING_AUDIT).parent.mkdir(parents=True, exist_ok=True)
    rl.write_json(run_dir / rl.READING_AUDIT, res)
    lines = ["# Reading audit — run %s" % res["run_id"], "",
             "Generated by `scripts/reading_audit.py run` from the agents' own transcripts (%s); do not edit." % res["transcripts"], "",
             "**Status: %s**%s" % (res["status"], " — waived: %s" % res["waiver"] if res.get("waiver") else ""), ""]
    if res["errors"]:
        lines += ["## Errors", ""] + ["- %s" % e for e in res["errors"]] + [""]
    if res["warnings"]:
        lines += ["## Warnings", ""] + ["- %s" % w for w in res["warnings"]] + [""]
    lines += ["## Agents: model and effort", "", "| Agent | Launch | Models | Efforts | Expected | API calls | Usage-limit stops |",
              "|---|---|---|---|---|---|---|"]
    for a in res["agents"]:
        lines.append("| %s | %s | %s | %s | %s · %s | %d | %d |" % (
            a["agent"], a["description"], ", ".join(sorted(a["models"])) or "-", ", ".join(sorted(a["efforts"])) or "-",
            a["expected_model"] or "-", a["expected_effort"] or "-", a["api_calls"], a["usage_limit_stops"]))
    for sid, prof in res.get("cio", {}).items():
        cio = rl.model_policy()["agents"]["cio"]
        lines.append("| cio (session %s) | main | %s | %s | %s · %s | %d | %d |" % (
            sid[:8], ", ".join(sorted(prof["models"])) or "-", ", ".join(sorted(prof["efforts"])) or "-",
            cio["model"], cio["effort"], prof["api_calls"], prof["usage_limit_stops"]))
    if res["readers"]:
        lines += ["", "## Readers: lines received and pages viewed", "", "| Launch | Role | Chunk | Lines received | VIEW REQUIRED pages not opened |",
                  "|---|---|---|---|---|"]
        lines += ["| %s | %s | %s | %d / %d | %s |" % (r["launch"], r["role"], r["chunk"], r["lines_seen"], r["lines_total"],
                                                    ", ".join(map(str, r["view_pages_missing"])) or "-")
                  for r in res["readers"] if "chunk" in r]
    if res.get("reused"):
        lines += ["", "## Reused from earlier runs", "", "| Chunk | Read in run | Roles | Verified |", "|---|---|---|---|"]
        lines += ["| %s | %s | %s | %s |" % (r["chunk"], r["from_run"], ", ".join(r["roles"]), "yes" if r["verified"] else "NO")
                  for r in res["reused"]]
    if res.get("independence"):
        lines += ["", "## Specialists: independence", "", "| Specialist | Session | Contacts with other agents' work |",
                  "|---|---|---|"]
        lines += ["| %s | %s | %s |" % (r["agent"], r["description"], r["breaches"] or "none") for r in res["independence"]]
    if res["specialists"]:
        lines += ["", "## Specialists: reading pack", "", "| Specialist | Dossier | Lines read |", "|---|---|---|"]
        lines += ["| %s | `%s` | %d / %d (%.0f%%) |" % (s["agent"], s["dossier"], s["lines_seen"], s["lines_total"], 100 * s["share"])
                  for s in res["specialists"]]
    (run_dir / "qc" / "READING_AUDIT.md").parent.mkdir(parents=True, exist_ok=True)
    (run_dir / "qc" / "READING_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("session")
    s.add_argument("--transcripts")
    r = sub.add_parser("run")
    r.add_argument("run_dir")
    r.add_argument("--transcripts")
    r.add_argument("--waive", default="")
    a = ap.parse_args(argv)
    if a.cmd == "session":
        return session(a)
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    res = run_audit(run_dir, transcripts_dir(a.transcripts), a.waive)
    write(run_dir, res)
    print("reading audit %s: %d agents, %d reader chunks, %d specialist dossiers; %d errors, %d warnings -> %s" % (
        res["status"], len(res["agents"]), len(res["readers"]), len(res["specialists"]), len(res["errors"]),
        len(res["warnings"]), run_dir / "qc" / "READING_AUDIT.md"))
    for e in res["errors"][:20]:
        print("  ERROR: %s" % e)
    if res["status"] == "PASS" or (res["status"] == "NOT_MEASURABLE" and res.get("waiver")):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
