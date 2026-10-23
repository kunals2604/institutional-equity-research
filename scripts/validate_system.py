#!/usr/bin/env python3
"""Static (and optional live) validation of the research system's configuration.

  python3 scripts/validate_system.py                 # static checks, no model calls
  python3 scripts/validate_system.py --live-probe    # + one headless Claude Code delegation probe
  python3 scripts/validate_system.py --json          # machine-readable

Static checks do NOT prove that a research run will succeed; they verify
configuration, contracts and documentation consistency. --live-probe starts a
fresh headless Claude Code session that invokes ONE specialist through the
native Agent tool with a harmless configuration-check prompt (small model cost,
no research, no file writes).
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import scoreboard as sb  # noqa: E402

ROOT = rl.ROOT
# Agent frontmatter keys verified against the Claude Code agent schema (code.claude.com/docs/en/sub-agents,
# checked 2026-10-17: `effort` accepts low | medium | high | xhigh | max and overrides the session effort).
AGENT_KEYS = {"name", "description", "tools", "disallowedTools", "model", "skills", "maxTurns",
              "permissionMode", "color", "memory", "background", "initialPrompt", "hooks",
              "mcpServers", "omitClaudeMd", "autoCompactWindow", "effort", "isolation", "experimental"}
EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}
SKILL_KEYS = {"name", "description", "when_to_use", "argument-hint", "allowed-tools",
              "disable-model-invocation", "model", "user-invocable", "context", "agent", "arguments"}
MODEL_ALIASES = {"opus", "sonnet", "haiku", "fable", "inherit"}
KNOWN_TOOLS = {"Read", "Write", "Edit", "Bash", "WebSearch", "WebFetch", "Agent", "Glob", "Grep",
               "NotebookEdit", "TodoWrite", "Skill", "AskUserQuestion"}
ANTIGRAVITY_PATTERNS = (r"invoke_subagent", r'"Workspace"\s*:', r"\.agents/agents", r"^subagent:\s*(true|false)",
                        r'"TypeName"')
RETIRED_NAMES = (r"LATEST_RUN\.txt", r"qc_record\.md", r"(?<![_\w])manifest\.json", r"update_scoreboard\.py")
SECRET_PATTERNS = (r"ghp_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}", r"sk-ant-[A-Za-z0-9-]{10,}",
                   r"(?i)password\s*[:=]\s*\S+", r"(?i)\btoken\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")
RESEARCH_SKILL_MODES = ("--validate-only", "--dry-run", "--resume", "$ARGUMENTS")


class Report:
    def __init__(self):
        self.checks = []

    def add(self, name, ok, detail=""):
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})

    @property
    def ok(self):
        return all(c["ok"] for c in self.checks)


def parse_yaml_frontmatter(text):
    """Minimal YAML subset parser for frontmatter: scalars and '- item' lists. Returns (dict, errors)."""
    if not text.startswith("---\n"):
        return None, ["no frontmatter"]
    end = text.find("\n---", 4)
    if end == -1:
        return None, ["unterminated frontmatter"]
    data, errors, key = {}, [], None
    for n, line in enumerate(text[4:end].splitlines(), 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if key in data:
                errors.append("line %d: duplicate key %s" % (n, key))
            if val == "":
                data[key] = []
            else:
                if (val[0] in "\"'") and val[-1] != val[0]:
                    errors.append("line %d: unbalanced quotes" % n)
                data[key] = val.strip("\"'")
            continue
        m = re.match(r"^\s+-\s+(.+)$", line)
        if m and key is not None and isinstance(data.get(key), list):
            data[key].append(m.group(1).strip().strip("\"'"))
            continue
        errors.append("line %d: unparseable: %r" % (n, line))
    return data, errors


def operative_markdown():
    files = [ROOT / f for f in ("CLAUDE.md", "README.md", "PROJECT_INSTRUCTIONS.md", "MASTER_RESEARCH_FRAMEWORK.md")]
    files += sorted((ROOT / ".claude").rglob("*.md"))
    files += sorted((ROOT / "methodology").glob("*.md")) + sorted((ROOT / "templates").glob("*.md"))
    files += [p for p in sorted((ROOT / "docs").glob("*.md")) if p.name != "CLAUDE_CODE_MIGRATION_AUDIT.md"]
    return files


def check_agents(rep):
    expected = set(rl.SPECIALISTS) | {"cio", rl.AUDITOR} | set(rl.WORKERS)
    try:
        policy = rl.model_policy()["agents"]
        rep.add("model policy block parses (methodology/MODEL_POLICY.md)", True)
    except (ValueError, OSError) as exc:
        policy = {}
        rep.add("model policy block parses (methodology/MODEL_POLICY.md)", False, str(exc))
    rep.add("model policy covers exactly the agent roster", set(policy) == expected,
            "policy %s vs roster %s" % (sorted(set(policy) - expected), sorted(expected - set(policy))) if set(policy) != expected else "")
    files = sorted(rl.AGENTS_DIR.glob("*.md"))
    names = {}
    for f in files:
        text = f.read_text(encoding="utf-8")
        fm, errs = parse_yaml_frontmatter(text)
        rep.add("frontmatter parses: %s" % f.name, fm is not None and not errs, "; ".join(errs))
        if not fm:
            continue
        unknown = set(fm) - AGENT_KEYS
        rep.add("frontmatter keys supported: %s" % f.name, not unknown, "unknown: %s" % sorted(unknown) if unknown else "")
        name = fm.get("name", "")
        names.setdefault(name, []).append(f.name)
        rep.add("agent name valid and matches file: %s" % f.name,
                re.fullmatch(r"[a-z][a-z0-9-]*", name or "") and name == f.stem, "name=%r" % name)
        model = fm.get("model", "")
        rep.add("model valid (%s): %s" % (model, f.name), model in MODEL_ALIASES or model.startswith("claude-"))
        effort = fm.get("effort", "")
        rep.add("effort valid (%s): %s" % (effort or "unset", f.name), effort in EFFORT_LEVELS)
        want = policy.get(name, {})
        rep.add("model and effort pinned as MODEL_POLICY.md says (%s · %s): %s" % (want.get("model"), want.get("effort"), f.name),
                bool(want) and model == want.get("model") and effort == want.get("effort"),
                "frontmatter %s · %s" % (model or "unset", effort or "unset"))
        tools = [t.strip() for t in fm.get("tools", "").split(",") if t.strip()] if isinstance(fm.get("tools"), str) else fm.get("tools") or []
        unknown_tools = [t for t in tools if t not in KNOWN_TOOLS and not t.startswith("mcp__")]
        rep.add("tool names recognised: %s" % f.name, not unknown_tools, str(unknown_tools) if unknown_tools else "")
        for s in fm.get("skills") or []:
            rep.add("preloaded skill exists (%s): %s" % (s, f.name), (ROOT / ".claude" / "skills" / s / "SKILL.md").exists())
        if name == "cio":
            rep.add("CIO can invoke specialists (Agent tool inherited or listed)", not tools or "Agent" in tools,
                    "tools=%s" % (tools or "inherit"))
            for out in ("final_report.md", "scorecard.json", "quality_control.md", "contradiction_log.md"):
                rep.add("CIO declares output %s" % out, out in text)
        elif name in rl.SPECIALISTS:
            rep.add("specialist cannot spawn agents: %s" % name, tools and "Agent" not in tools, "tools=%s" % tools)
            rep.add("specialist has research tools: %s" % name, {"WebSearch", "WebFetch", "Write"} <= set(tools))
            for out in ("RUN_DIR/specialists/%s.md" % name, "RUN_DIR/specialists/%s_ledger.csv" % name):
                rep.add("specialist declares output path %s" % out, out in text)
            rep.add("specialist declares claim prefix: %s" % name, "`%s`" % rl.SPECIALISTS[name] in text)
            try:
                rep.add("specialist required sections block: %s" % name, len(rl.agent_sections(name)) >= 5)
            except ValueError as exc:
                rep.add("specialist required sections block: %s" % name, False, str(exc))
            rep.add("specialist references all four layers: %s" % name, all(x in text for x in ("L1", "L2", "L3", "L4")))
            rep.add("specialist defines a minimum evidence set: %s" % name, "## Minimum evidence set" in text)
            rep.add("specialist reads the sector playbooks: %s" % name, "SECTOR_PLAYBOOKS.md" in text)
            rep.add("specialist defines SME enhanced scrutiny: %s" % name, "## SME enhanced scrutiny" in text)
            try:
                rep.add("specialist has a numbered Method: %s" % name, len(rl.method_steps(name)) >= 8,
                        "%d steps" % len(rl.method_steps(name)))
            except ValueError as exc:
                rep.add("specialist has a numbered Method: %s" % name, False, str(exc))
        elif name in rl.WORKERS:
            rep.add("worker cannot spawn agents: %s" % name, tools and "Agent" not in tools, "tools=%s" % tools)
            rep.add("worker writes no claim ledger: %s" % name, "_ledger.csv" not in text)
            if name in ("reader", "critical-reader", "scanner"):
                rep.add("reader has no web access: %s" % name, not ({"WebSearch", "WebFetch"} & set(tools)), "tools=%s" % tools)
                rep.add("reader follows the reading schema: %s" % name, "methodology/READING_SCHEMAS.md" in text
                        and "reading.py check" in text.replace("`", ""))
            elif name == "historian":
                rep.add("historian can search the web: %s" % name, {"WebSearch", "WebFetch"} <= set(tools))
                rep.add("historian checks its timeline with verify.py: %s" % name, "verify.py events" in text)
            elif name == "verifier":
                rep.add("verifier can open sources: %s" % name, {"Read", "WebFetch", "Bash"} <= set(tools))
                rep.add("verifier checks its results with verify.py: %s" % name, "verify.py claims" in text)
            else:
                rep.add("librarian can search and fetch: %s" % name, {"WebSearch", "WebFetch", "Bash"} <= set(tools))
                rep.add("librarian registers through the document map: %s" % name, "document_map.py add" in text)
        elif name == rl.AUDITOR:
            rep.add("auditor cannot spawn agents", tools and "Agent" not in tools, "tools=%s" % tools)
            rep.add("auditor declares claim prefix", "`%s`" % rl.AUDITOR_PREFIX in text)
            rep.add("auditor declares output path", "RUN_DIR/%s" % rl.AUDIT_REPORT in text)
            try:
                rep.add("auditor required sections block", len(rl.agent_sections(rl.AUDITOR)) >= 6)
            except ValueError as exc:
                rep.add("auditor required sections block", False, str(exc))
            rep.add("auditor is forbidden from editing other files", "never edit" in text.lower())
    rep.add("exactly the %d expected agents (CIO, %d specialists, auditor, %d workers)" % (
        len(expected), len(rl.SPECIALISTS), len(rl.WORKERS)), set(names) == expected, "found %s" % sorted(names))
    dups = {n: fs for n, fs in names.items() if len(fs) > 1}
    rep.add("agent names unique", not dups, str(dups) if dups else "")
    # Duplicate definitions elsewhere (outside archive / legacy runs).
    stray = []
    for p in ROOT.rglob("*.md"):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith((".claude/agents/", "archive/", "research/", ".git/")):
            continue
        fm, _ = parse_yaml_frontmatter(p.read_text(encoding="utf-8", errors="ignore"))
        if fm and fm.get("name") in expected and ("model" in fm or "tools" in fm):
            stray.append(rel)
    rep.add("no duplicate operative agent definitions in repository", not stray, str(stray) if stray else "")
    user_dir = Path.home() / ".claude" / "agents"
    shadow = sorted(p.name for p in user_dir.glob("*.md") if p.stem in expected) if user_dir.exists() else []
    rep.add("no user-level agents with the same names (~/.claude/agents)", not shadow, str(shadow) if shadow else "")


def check_skills(rep):
    for skill in ("research-company", "investment-constitution"):
        f = ROOT / ".claude" / "skills" / skill / "SKILL.md"
        if not f.exists():
            rep.add("skill exists: %s" % skill, False)
            continue
        text = f.read_text(encoding="utf-8")
        fm, errs = parse_yaml_frontmatter(text)
        rep.add("skill frontmatter parses: %s" % skill, fm is not None and not errs, "; ".join(errs))
        if not fm:
            continue
        unknown = set(fm) - SKILL_KEYS
        rep.add("skill keys supported: %s" % skill, not unknown, str(sorted(unknown)) if unknown else "")
        rep.add("skill name matches directory: %s" % skill, fm.get("name") == skill)
        rep.add("skill has description: %s" % skill, bool(fm.get("description")))
        if skill == "research-company":
            rep.add("research skill has argument-hint", bool(fm.get("argument-hint")))
            rep.add("research skill is user-invoked only", fm.get("disable-model-invocation") == "true")
            missing = [m for m in RESEARCH_SKILL_MODES if m not in text]
            rep.add("research skill implements argument contract and modes", not missing, str(missing) if missing else "")
            ops = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
            undocumented = [m for m in RESEARCH_SKILL_MODES[:3] if m not in ops]
            rep.add("modes documented in docs/OPERATIONS.md", not undocumented, str(undocumented) if undocumented else "")


def check_taxonomy_and_docs(rep):
    layers = rl.canonical_layers()
    rep.add("constitution defines exactly four canonical layers", len(layers) == 4, str(layers))
    rep.add("six canonical epistemic tags", rl.epistemic_tags() == ["FACT", "MANAGEMENT STATEMENT", "CALCULATION",
                                                                     "ESTIMATE", "INFERENCE", "JUDGMENT"])
    for kind in ("BQ", "IA"):
        rep.add("%s weights sum to 100" % kind, sum(w for _, _, w in rl.dimension_weights(kind)) == 100)
    drift, stale, antigravity, retired = [], [], [], []
    ref_re = re.compile(r"(?<![\w/.])((?:scripts|methodology|templates|docs|tests)/[\w.\-/]+\.(?:py|md|json|csv)"
                        r"|\.claude/(?:agents|skills)/[\w.\-/]+\.md)")
    for f in operative_markdown():
        text = f.read_text(encoding="utf-8")
        rel = f.relative_to(ROOT).as_posix()
        res = rl.Result(rel)
        rl.check_layer_names(text, res)
        drift += ["%s: %s" % (rel, m) for m in res.errors + res.warnings]
        for ref in set(ref_re.findall(text)):
            if not (ROOT / ref).exists() and "<" not in ref and "*" not in ref:
                stale.append("%s -> %s" % (rel, ref))
        for pat in ANTIGRAVITY_PATTERNS:
            if re.search(pat, text, re.M):
                antigravity.append("%s: /%s/" % (rel, pat))
        if rel != "docs/FRAMEWORK_CHANGES.md":
            for pat in RETIRED_NAMES:
                if re.search(pat, text):
                    retired.append("%s: /%s/" % (rel, pat))
    rep.add("no conflicting or non-canonical layer definitions in operative files", not drift, "; ".join(drift[:10]))
    rep.add("no stale file references in operative files", not stale, "; ".join(sorted(stale)[:15]))
    rep.add("no Antigravity orchestration in operative files", not antigravity, "; ".join(antigravity))
    rep.add("no retired file names in operative files", not retired, "; ".join(retired))
    ops = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    undocumented = [p.name for p in (ROOT / "scripts").glob("*.py") if p.name != "research_lib.py" and p.name not in ops]
    rep.add("every script documented in docs/OPERATIONS.md", not undocumented, str(undocumented) if undocumented else "")
    contracts = (ROOT / "methodology" / "REPORT_CONTRACTS.md").read_text(encoding="utf-8")
    missing = [x for x in (rl.RUN_MANIFEST, "final_report.md", "scorecard.json", "quality_control.md",
                           rl.LATEST_POINTER, "evidence_ledger.csv", "source_register.csv") if x not in contracts]
    rep.add("run layout in REPORT_CONTRACTS.md matches implementation", not missing, str(missing) if missing else "")


def check_methodology(rep):
    for doc in ("RESEARCH_PLAYBOOK.md", "SOURCE_GUIDE.md", "SECTOR_PLAYBOOKS.md", "METRIC_DEFINITIONS.md",
                "SCORING.md", "EVIDENCE_STANDARDS.md", "INVESTOR_LENSES.md", "REPORT_CONTRACTS.md",
                "READING_SCHEMAS.md", "MODEL_POLICY.md"):
        rep.add("methodology document exists: %s" % doc, (ROOT / "methodology" / doc).exists())
    try:
        sch = rl.reading_schema()
        types, topics, classes = sch["types"], sch["topics"], sch["classes"]
        bad_topic = sorted(t for t, v in types.items() if v.get("topic") not in topics)
        bad_amount = sorted(t for t, v in types.items() if not set(v.get("amounts", [])) <= set(v.get("fields", [])))
        bad_hint = sorted("%s:%s" % (c, h) for c, v in classes.items() for h in v.get("hint", []) if h not in types)
        owners = {o for v in topics.values() for o in v.get("owners", [])}
        rep.add("reading schema parses: %d item types, %d topics, %d section classes" % (len(types), len(topics), len(classes)),
                not (bad_topic or bad_amount or bad_hint), "topic %s amounts %s hints %s" % (bad_topic, bad_amount, bad_hint))
        rep.add("reading schema topics are owned by specialists only", owners <= set(rl.SPECIALISTS), str(sorted(owners - set(rl.SPECIALISTS))))
        rep.add("every specialist owns at least one reading topic", set(rl.SPECIALISTS) <= owners, str(sorted(set(rl.SPECIALISTS) - owners)))
        import reading
        crit = {c for c, v in classes.items() if v.get("critical")}
        rep.add("critical section classes include the auditor's reports, CARO and critical notes",
                {"auditor_report", "caro", "ifc", "notes_critical"} <= crit, str(sorted(crit)))
        missing_cls = sorted({c for c in reading.SECTION_TO_CLASS.values()} - set(classes))
        rep.add("every class the reading planner assigns is defined in the schema", not missing_cls, str(missing_cls))
        cal = rl.model_policy().get("calibration", {})
        rep.add("calibration record: status %s, single-read classes non-critical" % cal.get("status"),
                not (set(cal.get("single_read_classes", [])) & crit), str(cal.get("single_read_classes")))
    except (ValueError, OSError, KeyError) as exc:
        rep.add("reading schema parses (methodology/READING_SCHEMAS.md)", False, repr(exc))
    mins = rl.depth_minimums()
    rep.add("Historical Depth Standard parses (>=10 fiscal years, >=12 quarters)",
            mins.get("financials.fiscal_years", 0) >= 10 and mins.get("concalls.quarters", 0) >= 12, str(mins))
    th = rl.evidence_thresholds()
    rep.add("evidence thresholds parse", {"min_claims_per_specialist", "min_primary_share_overall"} <= set(th), str(th))
    keys = rl.metric_keys()
    rep.add("metric dictionary has >= 100 keys", len(keys) >= 100, "%d keys" % len(keys))
    import fin_metrics
    engine = set(fin_metrics.SHARE_ITEMS | fin_metrics.PER_SHARE_ITEMS | fin_metrics.PCT_ITEMS | fin_metrics.OPTIONAL_ZERO)
    engine |= {"roce", "roic", "roe", "roa", "nopat", "fcf", "dso", "dio", "dpo", "ccc", "nim", "credit_cost", "pcr",
               "beneish_m_score", "piotroski_f_score", "incremental_roic_3y", "incremental_roic_5y", "accruals_ratio"}
    missing = sorted(k for k in engine if k not in keys)
    rep.add("metrics engine outputs are dictionary keys", not missing, str(missing) if missing else "")
    sectors = (ROOT / "methodology" / "SECTOR_PLAYBOOKS.md").read_text(encoding="utf-8")
    n = len(re.findall(r"^## \d+\. ", sectors, re.M))
    rep.add("sector playbooks cover >= 15 sectors", n >= 15, "%d sectors" % n)
    try:
        pol = rl.investment_policy()
        need = {"confirmed_by_user", "hurdle_rate", "investment_horizon_years", "benchmark", "reference_position",
                "liquidity", "risk_limits"}
        rep.add("investment policy (IPS) has required keys", need <= set(pol), str(sorted(need - set(pol))))
        h = pol.get("hurdle_rate")
        rep.add("investment policy hurdle is null (derived per run) or a plausible decimal", h is None or 0 < float(h) < 0.5)
        if not pol.get("confirmed_by_user"):
            rep.add("investment policy confirmed by user", True, "NOT YET CONFIRMED — values are placeholders (warning)")
    except Exception as exc:
        rep.add("investment policy (IPS) parses", False, repr(exc))


def check_contracts(rep):
    rep.add("example scorecard satisfies schema", rl.validate_scorecard(ROOT / "templates" / "scorecard.example.json").ok)
    header, _ = rl.read_csv(rl.SCOREBOARD) if rl.SCOREBOARD.exists() else ([], [])
    rep.add("scoreboard has exactly the required columns", header == sb.COLUMNS, "header=%s" % header)
    rep.add("scoreboard has both score columns",
            {"business_quality_score", "investment_attractiveness_score"} <= set(header))
    errs = sb.validate_file(rl.SCOREBOARD, check_runs=True)
    rep.add("scoreboard rows valid and backed by QC-passed runs", not errs, "; ".join(errs[:5]))
    settings = ROOT / ".claude" / "settings.json"
    try:
        json.loads(settings.read_text(encoding="utf-8"))
        rep.add(".claude/settings.json parses", True)
    except Exception as exc:
        rep.add(".claude/settings.json parses", False, str(exc))
    leaks = []
    for f in [settings, ROOT / "CLAUDE.md"] + sorted((ROOT / ".claude").rglob("*.md")) + sorted((ROOT / "scripts").glob("*.py")):
        for pat in SECRET_PATTERNS:
            if re.search(pat, f.read_text(encoding="utf-8")):
                leaks.append("%s /%s/" % (f.relative_to(ROOT), pat))
    rep.add("no credentials in configuration or scripts", not leaks, "; ".join(leaks))


def check_run_preservation(rep):
    tmp = Path(tempfile.mkdtemp(prefix="eqr-sys-"))
    try:
        new_run = [sys.executable, str(ROOT / "scripts" / "new_run.py"), "--ticker", "PROBECO", "--company", "Probe Co",
                   "--exchange", "NSE", "--segment", "main", "--root", str(tmp)]
        dry = subprocess.run(new_run + ["--dry-run"], capture_output=True, text=True)
        rep.add("dry-run writes nothing", dry.returncode == 0 and not (tmp / "research").exists())
        r1 = subprocess.run(new_run + ["--run-id", "20260101T000000Z"], capture_output=True, text=True)
        marker = tmp / "research/companies/PROBECO/runs/20260101T000000Z/specialists/marker.md"
        if r1.returncode == 0:
            marker.write_text("prior run content", encoding="utf-8")
        r2 = subprocess.run(new_run + ["--run-id", "20260101T000000Z"], capture_output=True, text=True)
        r3 = subprocess.run(new_run, capture_output=True, text=True)
        runs = sorted(p.name for p in (tmp / "research/companies/PROBECO/runs").iterdir()) if r1.returncode == 0 else []
        rep.add("existing run is never overwritten", r1.returncode == 0 and r2.returncode != 0
                and marker.read_text() == "prior run content")
        rep.add("new run gets a distinct sortable UTC run id", r3.returncode == 0 and len(runs) == 2
                and all(rl.RUN_ID_RE.fullmatch(r) for r in runs), str(runs))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_isolation_and_connectors(rep):
    """The engine isolates every agent session, the librarian alone gets the browser, the connector registry is
    well formed; and what is installed on this Mac (reported, never a failure)."""
    import agent_driver as ad
    import browser
    import connectors
    src = (ROOT / "scripts" / "agent_driver.py").read_text(encoding="utf-8")
    rep.add("agent sessions are isolated (project settings only, no hooks, no auto-memory)",
            ad.ISOLATION[:2] == ["--setting-sources", "project"] and ad.ISOLATION_SETTINGS.get("disableAllHooks") is True
            and ad.ISOLATION_SETTINGS.get("autoMemoryEnabled") is False and src.count("+ ISOLATION") >= 4)
    lib_mcp = ad.agent_tools("librarian", mcp=True)
    others = [a for a in rl.AGENT_NAMES if (rl.AGENTS_DIR / ("%s.md" % a)).exists() and a != "librarian"
              and ad.agent_tools(a, mcp=True)]
    rep.add("only the librarian has browser tools, exactly the navigation set", sorted(lib_mcp) == sorted(ad.BROWSER_TOOLS)
            and not others, "others: %s" % others if others else "")
    reg = connectors.registry()
    bad = [r.get("id") for r in reg if r.get("access") not in ("free", "free-key", "manual") or not r.get("agents")
           or (r.get("landing") and not r["landing"].startswith("https://"))]
    rep.add("connector registry well formed (%d sources)" % len(reg), bool(reg) and not bad, ", ".join(map(str, bad)))
    tools = {"Chrome (snapshots, librarian browser)": browser.find_chrome(), "npx (Playwright MCP)": shutil.which("npx"),
             "whisper-cli": shutil.which("whisper-cli"), "ffmpeg": shutil.which("ffmpeg"),
             "whisper model": str(connectors.WHISPER_MODEL) if connectors.WHISPER_MODEL.exists() else None}
    missing = [k for k, v in tools.items() if not v]
    rep.add("local tools for the free connectors", True, ("missing: %s (docs/OPERATIONS.md: install lines)" % ", ".join(missing))
            if missing else "")
    home = Path.home() / ".claude"
    found = []
    try:
        us = json.loads((home / "settings.json").read_text(encoding="utf-8"))
        if us.get("hooks"):
            found.append("user hooks (%s)" % ", ".join(sorted(us["hooks"])))
        plugins = [k for k, v in (us.get("enabledPlugins") or {}).items() if v]
        if plugins:
            found.append("plugins %s" % ", ".join(sorted(plugins)))
    except (OSError, ValueError):
        pass
    if (home / "CLAUDE.md").exists():
        found.append("~/.claude/CLAUDE.md")
    rep.add("user-level add-ons", True, ("present: %s. Agent sessions are isolated from them; the CIO session is not "
                                         "(docs/OPERATIONS.md)" % "; ".join(found)) if found else "")


def find_claude_bin(explicit):
    if explicit:
        return explicit
    found = shutil.which("claude")
    if found:
        return found
    cands = sorted(glob.glob(os.path.expanduser("~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude")))
    return cands[-1] if cands else None


def live_probe(rep, claude_bin, specialist="bear-case"):
    binp = find_claude_bin(claude_bin)
    if not binp:
        rep.add("live probe: Claude Code binary found", False, "pass --claude-bin")
        return
    prompt = ('Wiring probe. Invoke the Agent tool exactly once, in the foreground, with subagent_type "%s" and this prompt: '
              '"CONFIGURATION CHECK ONLY. Do not research, use web tools, write files or run commands. Reply in one line: '
              'PRELOADED=<Y/N>; PREFIX=<your claim-ID prefix>; MODEL=<model id in your system context>; AGENT_TOOL=<Y/N>." '
              'Then print its reply verbatim on a line starting with REPLY:' % specialist)
    try:
        r = subprocess.run([binp, "-p", "--allowedTools", "Agent", "--output-format", "text", prompt],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        rep.add("live probe: specialist invoked via native Agent tool", False, "timeout")
        return
    out = r.stdout
    m = re.search(r"PREFIX=\s*`?([A-Z]+)", out)
    model = re.search(r"MODEL=\s*`?([\w.\-]+)", out)
    ok = bool(m) and m.group(1) == rl.SPECIALISTS[specialist]
    rep.add("live probe: '%s' invoked via native Agent tool and answered" % specialist, ok,
            out.strip().splitlines()[-1][:200] if out.strip() else r.stderr[:200])
    rep.add("live probe: constitution preloaded", "PRELOADED=Y" in out.replace(" ", ""))
    rep.add("live probe: specialist has no Agent tool", "AGENT_TOOL=N" in out.replace(" ", ""))
    rep.add("live probe: model reported", bool(model), model.group(1) if model else "not reported")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--live-probe", action="store_true")
    p.add_argument("--claude-bin")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    rep = Report()
    for fn in (check_agents, check_skills, check_taxonomy_and_docs, check_methodology, check_contracts, check_run_preservation,
               check_isolation_and_connectors):
        try:
            fn(rep)
        except Exception as exc:  # a crashing check is a failing check
            rep.add("%s crashed" % fn.__name__, False, repr(exc))
    if a.live_probe:
        live_probe(rep, a.claude_bin)
    if a.json:
        print(json.dumps({"ok": rep.ok, "checks": rep.checks}, indent=2))
    else:
        for c in rep.checks:
            if not c["ok"] or c["detail"]:
                print("%s  %s%s" % ("PASS" if c["ok"] else "FAIL", c["check"], ("  — " + c["detail"]) if c["detail"] else ""))
        print("\n%d checks, %d failed: %s" % (len(rep.checks), sum(not c["ok"] for c in rep.checks),
                                           "SYSTEM VALID" if rep.ok else "SYSTEM INVALID"))
        print("Note: static checks verify configuration and contracts, not that a research run will succeed."
              + ("" if a.live_probe else " Use --live-probe for a real delegation check."))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
