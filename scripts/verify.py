#!/usr/bin/env python3
"""The verification loop: did each agent do the work its report implies? Fixable findings go back to the agent that
owns them; what it finds is remembered, so the next run's agents are warned and checked harder where they failed.

  python3 scripts/verify.py specialist RUN_DIR NAME                 # Tier A for one specialist -> qc/verification/NAME.json
  python3 scripts/verify.py sample RUN_DIR NAME [--n 8]             # Tier B: the claims the verifier agent re-checks
  python3 scripts/verify.py claims RUN_DIR NAME                     # Tier B: read the verifier's results
  python3 scripts/verify.py run RUN_DIR --stage specialists|final   # the whole research -> qc/VERIFICATION.md
  python3 scripts/verify.py waive RUN_DIR FINDING_ID --reason "<why>"   # the CIO accepts a finding, with the reason
  python3 scripts/verify.py lessons [--agent NAME]                  # what verification found in earlier runs
  python3 scripts/verify.py events RUN_DIR [--years 10]             # the historian's timeline, checked

Why. Run BHARTIARTL 20261012T132311Z passed every validator while its reports implied annual reports had been read
that the agents had seen 11-17 % of. A validator checks the shape of the work; this checks the work against what the
agent actually did, from its own transcripts and the files.

Tier A (scripts, every specialist, the moment its report passes its validator; `agent_driver.py` runs it and resumes
the specialist with every fixable finding until it passes):
  * NUMBER_NOT_SEEN    a FACT or MANAGEMENT STATEMENT value (three or more significant digits) that never appeared in
                       anything the agent read (tool results, its brief): invented, misread, converted without saying
                       so, or computed and mislabelled. Digits are compared without separators, decimal point or
                       leading and trailing zeros, so 1,570,659 (INR mn) and 15.70659 (INR lakh crore) match.
  * SOURCE_NOT_OPENED  a FACT or MANAGEMENT STATEMENT whose cited source the agent never opened (only seen in a dossier,
                       or never retrieved). Blocking above 3 claims or 10 % of the checked claims.
  * PAGE_NOT_OPENED    a FACT citing a page of a document whose page the agent never opened (PDF page, text-layer page,
                       doc_text page/verify).
  * PACK_READ          a must-read dossier of its reading pack not read in full (all of its sessions together).
  * CHECKLIST_EVIDENCE a Method Coverage Checklist row marked Done that points nowhere, or to a claim not in the ledger.
  * INDEPENDENCE / INTEGRITY / MODEL_EFFORT   contact with another specialist's work, a change to a file it does not
                       own, a session below its pinned model or effort: the CIO's to resolve (a re-run), never the agent's.
  * WORKPAPERS         no progress.md or research plan.
Tier B (the `verifier` agent, Opus, a fresh session per specialist): re-opens a sample of the specialist's
decision-critical claims at their sources and records Confirmed / Minor discrepancy / Material discrepancy / Not
verifiable; every material discrepancy and unverifiable claim goes back to the specialist, then is re-checked.
Run level (`run`): every specialist's result, the reading stage and reading audit, and at the final stage the CIO's own
ledger (NUMBER_NOT_SEEN, SOURCE_NOT_OPENED from the CIO's sessions) and the independent audit. `validate_run.py`
requires PASS (an open blocking finding fails it unless the CIO waived it with a reason).

Learning (`lessons`): every run's findings are kept in its qc/verification.json. Before a run, each agent's brief
carries the checks it failed in earlier runs (generic process lessons, never another company's facts or conclusions),
and the verifier samples more of its claims; a check the CIO keeps waiving is listed for the owner to review.

Exit: 0 PASS, 1 findings that block, 2 usage.
"""

import argparse
import csv
import datetime as dt
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claim_graph as cg  # noqa: E402
import reading_audit as ra  # noqa: E402
import research_lib as rl  # noqa: E402

CHECKS = {
    # id: (severity, owner, fixable by the agent, lesson for the agent's next brief)
    "REPORT_CONTRACT": ("blocking", "agent", True, "Run the report validator and fix every error before you return."),
    "NUMBER_NOT_SEEN": ("blocking", "agent", True,
                        "Every FACT or MANAGEMENT STATEMENT value must be copied from a source you opened, as printed; "
                        "a converted or computed value is a CALCULATION with its formula and inputs."),
    "SOURCE_NOT_OPENED": ("blocking", "agent", True,
                          "Open every source you cite for a FACT (the document at the page, the filing, the web page); "
                          "a dossier line is a finding aid, never the source."),
    "PAGE_NOT_OPENED": ("major", "agent", True, "Open the cited page of a document before you cite a fact from it."),
    "PACK_READ": ("blocking", "agent", True, "Read every must-read dossier of your reading pack in full."),
    "CHECKLIST_EVIDENCE": ("major", "agent", True,
                           "Every Done row of the Method Coverage Checklist points to the section and claims that show it."),
    "WORKPAPERS": ("minor", "agent", True, "Keep progress.md and your research plan current."),
    "INDEPENDENCE": ("blocking", "cio", False, "Never open another specialist's work, the CIO's or the auditor's files."),
    "INTEGRITY": ("blocking", "cio", False, "Write only your own files."),
    "MODEL_EFFORT": ("blocking", "cio", False, ""),
    "CLAIM_DISCREPANCY": ("blocking", "agent", True,
                          "The verifier re-opened your claims at their sources and found material discrepancies: copy "
                          "values and wording exactly, with the right period, basis and unit."),
    "CLAIM_UNVERIFIABLE": ("major", "agent", True, "Cite sources precisely enough (document, page, URL) that anyone can "
                                                   "open the exact place."),
    "READING_INCOMPLETE": ("blocking", "cio", False, ""),
    "READING_AUDIT": ("blocking", "cio", False, ""),
    "SPECIALIST_UNVERIFIED": ("blocking", "cio", False, ""),
    "AUDIT_OPEN": ("blocking", "cio", False, ""),
    "EVENTS_NOT_FOUND": ("major", "cio", False, ""),
    "CLAIM_GRAPH": ("blocking", "agent", True, "Every CALCULATION names its input claim IDs in formula_or_inputs, and "
                                                "every claim ID you cite is in your ledger."),
    "DEPENDENT_NOT_REVIEWED": ("blocking", "agent", True,
                               "When a claim of yours is corrected, review every claim built on it and record what you "
                               "did with each (updated, or unaffected and why)."),
    "CIO_CLAIM_GRAPH": ("blocking", "cio", False, ""),
    "CIO_DEPENDENT_NOT_REVIEWED": ("blocking", "cio", False, ""),
}
PROPAGATION_COLUMNS = ("claim", "dependent", "action", "reason")
FACT_TAGS = ("FACT", "MANAGEMENT STATEMENT")
SOURCE_BLOCK = (3, 0.10)       # SOURCE_NOT_OPENED blocks above 3 claims or 10 % of the checked claims
DEFAULT_SAMPLE = 8
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
PDF_PAGE_RE = re.compile(r"\bPDF\s*(?:page|pp?)\.?\s*(\d{1,4})", re.I)
PRINTED_PAGE_RE = re.compile(r"\bprinted\s*(?:page|pp?)\.?\s*(\d{1,4})", re.I)
IMAGE_RE = re.compile(r"\.(png|jpe?g|gif|webp)$", re.I)
VERIFIER_RESULTS = ("Confirmed", "Minor discrepancy", "Material discrepancy", "Not verifiable")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def vdir(run_dir: Path) -> Path:
    return run_dir / "qc" / "verification"


def digits(token: str) -> str:
    """A number's significant digits: no separators, no decimal point, no leading or trailing zeros."""
    return re.sub(r"\D", "", token).strip("0")


def digit_set(text: str) -> Set[str]:
    return {digits(t) for t in NUM_RE.findall(text or "") if digits(t)}


# --------------------------------------------------------------------------------------------------------------
# What an agent did: its sessions, what it read, what it opened
# --------------------------------------------------------------------------------------------------------------

def agent_sessions(run_dir: Path, name: str, tdir: Optional[Path] = None) -> List[dict]:
    """Every session of this agent in this run (headless engine sessions and Agent-tool subagents), with entries."""
    tdir = tdir or ra.transcripts_dir()
    run_id = rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id", run_dir.name)
    out = []
    if tdir.exists():
        out += [a for a in ra.headless_sessions(run_dir, tdir) if a["type"] == name]
        out += [a for a in ra.find_agents(tdir, run_id) if a["type"] == name]
    jobs = rl.load_json(run_dir / "engine" / "jobs.json") if (run_dir / "engine" / "jobs.json").exists() else {}
    stage = {j["id"]: str(j.get("stage", "")) for j in jobs.get("jobs", [])}
    for a in out:
        a["entries"] = ra.load_lines(a["path"])
        a["stage"] = stage.get(a.get("job", ""), "")
    return out


class Seen:
    """What a set of sessions saw (tool results and the prompts given to them) and what they opened (tool inputs)."""

    def __init__(self, sessions: List[dict]):
        self.events: List[Tuple[dict, str]] = []
        prompts = []
        for s in sessions:
            self.events += ra.tool_events(s["entries"])
            for d in s["entries"]:
                c = (d.get("message") or {}).get("content")
                if d.get("type") == "user" and isinstance(c, str):
                    prompts.append(c)
        self.digits = digit_set("\n".join(t for _, t in self.events) + "\n" + "\n".join(prompts))
        self.inputs = [(u.get("name") or "", json.dumps(u.get("input") or {}, ensure_ascii=False)) for u, _ in self.events]
        self.inputs_low = [(n, s.lower()) for n, s in self.inputs]

    def opened(self, keys: Iterable[str]) -> bool:
        keys = [k.lower() for k in keys if k and len(k) >= 6]
        return any(k in s for _, s in self.inputs_low for k in keys)

    def touching(self, keys: Iterable[str]):
        keys = [k.lower() for k in keys if k and len(k) >= 6]
        for u, text in self.events:
            inp = json.dumps(u.get("input") or {}, ensure_ascii=False).lower()
            if any(k in inp for k in keys):
                yield u, text, inp

    def viewed(self, keys: Iterable[str]) -> bool:
        """The agent looked at the document as an image (a PDF page view, a rendered page): no text to check against."""
        return any(u.get("name") == "Read" and ((u.get("input") or {}).get("pages") or
                                                IMAGE_RE.search(str((u.get("input") or {}).get("file_path", ""))))
                   for u, _, _ in self.touching(keys))

    def anchored(self, keys: Iterable[str]) -> bool:
        """The agent opened the document in a page-anchored form (PDF pages, the text layer, doc_text)."""
        return any((u.get("input") or {}).get("pages") or "<<<PAGE " in (text or "") or "doc_text.py" in inp
                   for u, text, inp in self.touching(keys))

    def page_opened(self, keys: Iterable[str], pdf_page: int = 0, printed: int = 0) -> bool:
        for u, text, inp in self.touching(keys):
            pages = str((u.get("input") or {}).get("pages") or "")
            for part in re.split(r"\s*,\s*", pages):
                m = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", part)
                if m and pdf_page and int(m.group(1)) <= pdf_page <= int(m.group(2) or m.group(1)):
                    return True
            if pdf_page and re.search(r"<<<PAGE %d[/ |]" % pdf_page, text or ""):
                return True
            if printed and re.search(r"<<<PAGE \d+[^>\n]*printed [^>|\n]*\b%d\b" % printed, text or ""):
                return True
            if pdf_page and u.get("name") == "Bash" and re.search(r"doc_text\.py\s+(?:page|verify)\b[^\n]*\s%d\b" % pdf_page, inp):
                return True
        return False


def source_keys(run_dir: Path) -> Dict[str, Set[str]]:
    """Every spelling of every document the run holds, keyed by each spelling: URLs (with and without the scheme),
    cached and local paths, their file names, FilingForge ids and the text layer's folder; so a citation of any one of
    them is matched by an opening of any other."""
    groups: List[Set[str]] = []
    mp = run_dir / "corpus" / "document_map.csv"
    if mp.exists():
        with mp.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                g = {r.get("primary_url", ""), r.get("local_path", ""), r.get("local_doc_id", ""),
                     r.get("cached_path", ""), r.get("text_path", "")} | set((r.get("alt_urls") or "").split())
                groups.append(g)
    rt = run_dir / "source_retrievals.csv"
    if rt.exists():
        with rt.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("local_path"):
                    groups.append({r.get("url", ""), r.get("final_url", ""), r.get("local_path", "")})
    for meta in (run_dir / "_cache" / "text").glob("*/meta.json"):
        try:
            src = json.loads(meta.read_text(encoding="utf-8")).get("source", "")
        except ValueError:
            continue
        groups.append({src, str(meta.parent), meta.parent.name})
    out: Dict[str, Set[str]] = defaultdict(set)
    for g in groups:
        spell = set()
        for s in g:
            s = (s or "").strip()
            if not s:
                continue
            spell.add(s)
            spell.add(re.sub(r"^https?://", "", s).rstrip("/"))
            if "/" in s:
                spell.add(s.rstrip("/").rsplit("/", 1)[-1])
        spell = {x for x in spell if len(x) >= 6}
        for s in spell:
            out[s] |= spell
    return out


def claim_keys(row: dict, keys: Dict[str, Set[str]]) -> Set[str]:
    src = (row.get("source_url_or_id") or "").strip()
    if not src:
        return set()
    src = re.sub(r"^FilingForge:", "", src)
    base = {src, re.sub(r"^https?://", "", src).rstrip("/")}
    if "/" in src:
        base.add(src.rstrip("/").rsplit("/", 1)[-1])
    out = set(base)
    for b in base:
        out |= keys.get(b, set())
    return {x for x in out if len(x) >= 6}


def checkable_source(src: str) -> bool:
    """A source a session could have opened: a URL, a file, a FilingForge id; not a claim id or a prose label."""
    s = (src or "").strip()
    return bool(re.match(r"^(https?://|/|FilingForge:|_cache/|corpus/|[\w.-]+\.(pdf|html?|csv|json|xml|xlsx|txt|md)$)", s)
                or re.fullmatch(r"[0-9a-f-]{20,}", s))


# --------------------------------------------------------------------------------------------------------------
# Tier A: one specialist
# --------------------------------------------------------------------------------------------------------------

def ledgers_of(run_dir: Path, name: str) -> List[Path]:
    sp = run_dir / "specialists"
    return [p for p in [sp / ("%s_ledger.csv" % name)] + sorted(sp.glob("%s_followup_*_ledger.csv" % name)) if p.exists()]


def ledger_rows(paths: List[Path]) -> List[dict]:
    rows = []
    for p in paths:
        with p.open(encoding="utf-8", newline="") as f:
            rows += [dict(r, _file=p.name) for r in csv.DictReader(f)]
    return rows


def finding(check: str, agent: str, detail: str, fix: str = "", claims: List[str] = ()) -> dict:
    sev, owner, fixable, _ = CHECKS[check]
    return {"check": check, "severity": sev, "owner": owner, "fixable": fixable, "agent": agent, "detail": detail,
            "fix": fix, "claims": list(claims)[:60]}


def claim_checks(rows: List[dict], seen: Seen, keys: Dict[str, Set[str]], agent: str) -> List[dict]:
    """NUMBER_NOT_SEEN, SOURCE_NOT_OPENED and PAGE_NOT_OPENED over a ledger's FACT and MANAGEMENT STATEMENT claims."""
    out = []
    not_seen, unopened, unpaged, checked = [], [], [], 0
    visual = []
    for r in rows:
        if (r.get("tag") or "").strip().upper() not in FACT_TAGS:
            continue
        cid = r.get("claim_id", "")
        src = r.get("source_url_or_id") or ""
        ck = claim_keys(r, keys) if checkable_source(src) else set()
        v = digits(r.get("value") or "")
        if len(v) >= 3 and v not in seen.digits:
            if ck and seen.viewed(ck):
                visual.append(cid)                 # read off a page image: the verifier re-checks it first
            else:
                not_seen.append("%s (value %s)" % (cid, r.get("value")))
        if not ck:
            continue
        checked += 1
        if not seen.opened(ck):
            unopened.append("%s (%s)" % (cid, src[:90]))
            continue
        loc = r.get("locator") or ""
        mp, mq = PDF_PAGE_RE.search(loc), PRINTED_PAGE_RE.search(loc)
        if (mp or mq) and seen.anchored(ck):
            if not seen.page_opened(ck, int(mp.group(1)) if mp else 0, int(mq.group(1)) if mq else 0):
                unpaged.append("%s (%s, %s)" % (cid, src.rsplit("/", 1)[-1][:60], loc[:40]))
    if not_seen:
        out.append(finding("NUMBER_NOT_SEEN", agent, "%d value(s) never appeared in anything this agent read" % len(not_seen),
                           "For each: open the source at the cited place and copy the value as printed; if you converted "
                           "or rounded it, record the printed value (and the conversion as a CALCULATION); if you computed "
                           "it, tag it CALCULATION with formula_or_inputs; if you cannot find it, remove the claim.",
                           not_seen))
    if unopened:
        f = finding("SOURCE_NOT_OPENED", agent, "%d of %d FACT claims cite a source this agent never opened" % (
            len(unopened), checked), "Open each cited source at the cited place, confirm the claim, and correct or "
                                     "remove what it does not say.", unopened)
        if len(unopened) <= max(SOURCE_BLOCK[0], SOURCE_BLOCK[1] * checked):
            f["severity"] = "major"
        out.append(f)
    if visual:
        f = finding("PAGE_NOT_OPENED", agent, "%d value(s) read off page images (no text to check): the verifier "
                    "re-checks them first" % len(visual), "", visual)
        f.update(check="VISUAL_ONLY", severity="info", fixable=False)
        out.append(f)
    if unpaged:
        out.append(finding("PAGE_NOT_OPENED", agent, "%d claim(s) cite a page this agent never opened" % len(unpaged),
                           "Open each cited page (Read the PDF with pages, or doc_text.py page) and confirm the claim.",
                           unpaged))
    return out


def checklist_findings(run_dir: Path, name: str, ids: Set[str]) -> List[dict]:
    rep = run_dir / "specialists" / ("%s.md" % name)
    if not rep.exists():
        return []
    body = rl.section(rep.read_text(encoding="utf-8"), rl.CHECKLIST_SECTION) or ""
    rows = [l.strip() for l in body.splitlines() if l.strip().startswith("|") and not re.match(r"^\|\s*:?-{2,}", l.strip())]
    bad = []
    for r in rows[1:]:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if len(cells) < 4 or not re.search(r"\bdone\b", cells[2].lower()):
            continue
        where = cells[3]
        cited = set(rl.CLAIM_ID_RE.findall(where))
        if where in ("", "-", "—") or (cited and not cited <= ids):
            bad.append("step %s: %r" % (cells[0], where[:60] or "(empty)"))
    if not bad:
        return []
    return [finding("CHECKLIST_EVIDENCE", name, "%d Done row(s) point nowhere or to claims not in the ledger" % len(bad),
                    "Fill 'Where in this report' with the section and the claim IDs that show the step was done; if it "
                    "was not done in full, mark it Partial and say what was tried.", bad)]


def specialist(run_dir: Path, name: str, tdir: Optional[Path] = None, write: bool = True) -> dict:
    """Tier A for one specialist; writes qc/verification/<name>.json (keeping its Tier B results and waivers)."""
    sessions = agent_sessions(run_dir, name, tdir)
    rows = ledger_rows(ledgers_of(run_dir, name))
    ids = {r.get("claim_id", "") for r in rows}
    findings: List[dict] = []
    if not sessions:
        findings.append(finding("MODEL_EFFORT", name, "no transcript of this specialist was found: nothing it did can be "
                                                       "verified", "Run it through the engine, or waive with the reason."))
    seen = Seen(sessions)
    findings += claim_checks(rows, seen, source_keys(run_dir), name)
    findings += checklist_findings(run_dir, name, ids)
    old = rl.load_json(vdir(run_dir) / ("%s.json" % name)) if (vdir(run_dir) / ("%s.json" % name)).exists() else {}
    findings += graph_findings(run_dir, name, old.get("corrected", []))
    # its reading pack, over all of its sessions
    pack = run_dir / "corpus" / "dossiers" / "packs" / ("%s.md" % name)
    if pack.exists() and sessions:
        short = []
        for rel in re.findall(r"`(corpus/dossiers/[\w.-]+\.md)`", pack.read_text(encoding="utf-8")):
            path = run_dir / rel
            if path.exists():
                got, total, _ = ra.file_coverage(seen.events, path, rel)
                if total and got / total < ra.DOSSIER_MIN_SHARE:
                    short.append("%s (%d of %d lines)" % (rel, got, total))
        if short:
            findings.append(finding("PACK_READ", name, "%d must-read dossier(s) not read in full" % len(short),
                                    "Read each of these dossiers in full (Read with offset/limit to the last line), then "
                                    "revise your report and ledger where they change anything.", short))
    # independence (Stages 1-2 only), integrity, model and effort
    run_id = rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id", run_dir.name)
    breaches = []
    for s in sessions:
        if s.get("headless") and not (s["stage"].startswith("1") or s["stage"].startswith("2")):
            continue
        breaches += ra.independence_breaches(name, run_id, ra.tool_events(s["entries"]))
    if breaches:
        findings.append(finding("INDEPENDENCE", name, "%d contact(s) with other agents' work" % len(breaches),
                                "The CIO re-runs this specialist from a clean start, or records what it saw and why its "
                                "conclusions stand.", breaches))
    jobs = rl.load_json(run_dir / "engine" / "jobs.json").get("jobs", []) if (run_dir / "engine" / "jobs.json").exists() else []
    touched = sorted({p for j in jobs if j["agent"] == name for p in j.get("integrity", [])})
    if touched:
        findings.append(finding("INTEGRITY", name, "changed files it does not own", "The CIO restores them and re-runs "
                                                                                    "the specialist.", touched))
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    want_model, want_effort = ra.expected_for(name, (m.get("model") or {}).get("effort_override"), rl.model_policy())
    low = []
    for s in sessions:
        prof = ra.profile(s["entries"])
        fams = {ra.family(x) for x in prof["models"]}
        if want_model and fams and fams != {want_model}:
            low.append("%s ran on %s" % (s["description"], sorted(fams)))
        if want_effort and any(ra.EFFORT_RANK.get(e, -1) < ra.EFFORT_RANK.get(want_effort, 0) for e in prof["efforts"]):
            low.append("%s ran at %s" % (s["description"], sorted(prof["efforts"])))
    if low:
        findings.append(finding("MODEL_EFFORT", name, "below its pinned %s at %s" % (want_model, want_effort), "The CIO "
                                "re-runs it on the pinned model and effort, or records the deviation.", low))
    wp = run_dir / "specialists" / ("%s_workpapers" % name)
    if not (wp / "progress.md").exists():
        findings.append(finding("WORKPAPERS", name, "no progress.md", "Write %s_workpapers/progress.md." % name))
    res = merge_record(run_dir, name, findings, len(rows), len(sessions)) if write else {"findings": findings}
    return res


def propagation_path(run_dir: Path, owner: str) -> Path:
    return run_dir / "cio" / "propagation.csv" if owner == "cio" else \
        run_dir / "specialists" / ("%s_workpapers" % owner) / "propagation.csv"


def propagation_rows(run_dir: Path, owner: str) -> Set[Tuple[str, str]]:
    """(claim, dependent) pairs the owner has recorded as reviewed: updated, or unaffected with the reason."""
    path = propagation_path(run_dir, owner)
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as f:
        return {((r.get("claim") or "").strip(), (r.get("dependent") or "").strip()) for r in csv.DictReader(f)
                if (r.get("action") or "").strip().lower() in ("updated", "unaffected") and (r.get("reason") or "").strip()}


def unreviewed(run_dir: Path, g: dict, owner: str, corrected: Iterable[str]) -> List[str]:
    """The owner's claims and scorecard inputs built on corrected claims that it has not recorded as reviewed."""
    done = propagation_rows(run_dir, owner)
    out = []
    for c in sorted(set(corrected)):
        for d in cg.down(g, [c]):
            if g["owners"].get(d) == owner and (d in g["claims"] or d.startswith("scorecard:")) and (c, d) not in done:
                out.append("%s (built on %s)" % (d, c))
    return out


def graph_findings(run_dir: Path, name: str, corrected: Iterable[str]) -> List[dict]:
    """The claim graph for one specialist: its own broken links, and what is built on its corrected claims."""
    g = cg.build(run_dir, write=False)
    out = []
    errs = ["%s cites %s, which no ledger holds" % (m["node"], m["id"]) for m in g["errors"]["missing"]
            if g["owners"].get(m["node"]) == name]
    errs += ["%s names no input claim ID in formula_or_inputs" % c for c in g["errors"]["calculation_without_inputs"]
             if g["claims"][c]["owner"] == name]
    errs += ["cycle: %s" % " -> ".join(c) for c in g["errors"]["cycles"] if g["owners"].get(c[0]) == name]
    if errs:
        out.append(finding("CLAIM_GRAPH", name, "%d broken link(s) between your claims" % len(errs),
                           "Name each CALCULATION's input claim IDs in formula_or_inputs, and cite only claim IDs your "
                           "ledger holds (python3 scripts/claim_graph.py build RUN_DIR lists them).", errs))
    todo = unreviewed(run_dir, g, name, corrected)
    if todo:
        out.append(finding("DEPENDENT_NOT_REVIEWED", name, "%d claim(s) built on corrected claims not yet reviewed" % len(todo),
                           "Review each against the corrected input (recompute it with the scripts where it is a "
                           "calculation), update it or its report lines if it changes, and record each in %s with the "
                           "columns %s (action: updated or unaffected)." % (
                               "specialists/%s_workpapers/propagation.csv" % name, ",".join(PROPAGATION_COLUMNS)), todo))
    return out


def merge_record(run_dir: Path, name: str, findings: List[dict], n_claims: int, n_sessions: int) -> dict:
    """Write the Tier A result, keeping the Tier B results, the remediation rounds and the waivers already recorded."""
    path = vdir(run_dir) / ("%s.json" % name)
    old = rl.load_json(path) if path.exists() else {}
    waived = old.get("waived", {})
    for i, f in enumerate(findings, 1):
        f["id"] = "%s-%s" % (name, f["check"])
        if f["id"] in waived:
            f["waived"] = waived[f["id"]]
    rec = {"agent": name, "checked_at": now(), "claims": n_claims, "sessions": n_sessions, "tier_a": findings,
           "tier_b": old.get("tier_b", {}), "rounds": old.get("rounds", []), "waived": waived,
           "corrected": old.get("corrected", [])}
    rec["status"] = status_of(rec)
    path.parent.mkdir(parents=True, exist_ok=True)
    rl.write_json(path, rec)
    return rec


def open_findings(rec: dict) -> List[dict]:
    out = [f for f in rec.get("tier_a", []) if not f.get("waived")]
    tb = rec.get("tier_b") or {}
    out += [f for f in tb.get("findings", []) if not f.get("waived")]
    return out


def status_of(rec: dict) -> str:
    return "FAIL" if any(f["severity"] == "blocking" for f in open_findings(rec)) else "PASS"


def fix_message(rec: dict, severities=("blocking",), tier_b: bool = True) -> List[str]:
    """The lines the engine sends back to the agent: each fixable finding, what it covers and how to fix it. The
    specialist's own completion check uses Tier A only (`tier_b=False`): the verifier's findings close by its re-check."""
    out = []
    for f in open_findings(rec if tier_b else dict(rec, tier_b={})):
        if f["fixable"] and f["owner"] == "agent" and f["severity"] in severities:
            out.append("%s (%s): %s. %s Items: %s" % (f["check"], f["severity"], f["detail"], f["fix"],
                                                      "; ".join(f["claims"][:40]) or "-"))
    return out


# --------------------------------------------------------------------------------------------------------------
# Tier B: the verifier agent's sample
# --------------------------------------------------------------------------------------------------------------

def sample(run_dir: Path, name: str, n: int = 0, seed: str = "verifier") -> List[dict]:
    """The claims the verifier re-checks: those the report's conclusion rests on first (claim IDs in its Domain
    Conclusion and summary sections), then numeric FACTs, then the rest, drawn reproducibly; more for an agent whose
    earlier runs had material discrepancies."""
    n = n or DEFAULT_SAMPLE + (4 if lesson_counts().get((name, "CLAIM_DISCREPANCY")) else 0)
    rows = [r for r in ledger_rows(ledgers_of(run_dir, name)) if (r.get("tag") or "").upper() in FACT_TAGS
            and checkable_source(r.get("source_url_or_id") or "")]
    rep = run_dir / "specialists" / ("%s.md" % name)
    text = rep.read_text(encoding="utf-8") if rep.exists() else ""
    key = set()
    for sec in ("Domain Conclusion", "Executive Summary", "Key Findings", "Summary"):
        key |= set(rl.CLAIM_ID_RE.findall(rl.section(text, sec) or ""))
    key |= set(cg.fact_inputs(cg.build(run_dir, write=False), key))    # the facts under the calculations they cite
    rnd = random.Random("%s:%s" % (seed, name))
    first = [r for r in rows if r["claim_id"] in key]
    numeric = [r for r in rows if r["claim_id"] not in key and len(digits(r.get("value") or "")) >= 3]
    rest = [r for r in rows if r["claim_id"] not in key and r not in numeric]
    for lst in (first, numeric, rest):
        rnd.shuffle(lst)
    picked = (first[:max(n // 2, n - len(numeric) - len(rest))] + numeric + rest)[:n]
    picked = (picked + [r for r in first if r not in picked])[:n]
    out = vdir(run_dir) / ("%s_sample.csv" % name)
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["claim_id", "claim", "tag", "value", "unit", "period", "basis", "source_title", "source_url_or_id", "locator"]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in picked:
            w.writerow(r)
    return picked


def verifier_opened(run_dir: Path, name: str, claim_ids: List[str], tdir: Optional[Path] = None) -> List[str]:
    """Verify the verifier: from its own transcripts, each sampled claim's cited source was opened by a verifier session
    of this specialist (a result written without opening the source is not a re-check). Not measurable without the
    transcripts (an Agent-tool run on another machine): nothing is claimed either way."""
    tdir = tdir or ra.transcripts_dir()
    jobs = rl.load_json(run_dir / "engine" / "jobs.json").get("jobs", []) if (run_dir / "engine" / "jobs.json").exists() else []
    mine = {j["id"] for j in jobs if j["agent"] == "verifier" and j.get("subject") == name}
    sessions = [s for s in agent_sessions(run_dir, "verifier", tdir) if not mine or s.get("job") in mine]
    if not sessions:
        return []
    seen, keys = Seen(sessions), source_keys(run_dir)
    rows = {r.get("claim_id"): r for r in ledger_rows(ledgers_of(run_dir, name))}
    out = []
    for c in claim_ids:
        r = rows.get(c)
        if r and checkable_source(r.get("source_url_or_id") or "") and not seen.opened(claim_keys(r, keys)):
            out.append("%s: the verifier never opened its source (%s): open it and re-check the claim" % (
                c, (r.get("source_url_or_id") or "")[:90]))
    return out


EVENT_COLUMNS = ["event_id", "date", "fiscal_year", "category", "event", "entities", "amount", "source_title", "source_url"]
EVENT_CATEGORIES = ("acquisition_or_merger", "divestment_or_demerger", "capital_raise", "capital_return",
                    "leadership_change", "auditor_change", "regulatory_or_legal", "penalty", "fraud_or_investigation",
                    "default_or_restructuring", "credit_rating", "major_contract_or_licence", "operations_incident",
                    "promoter_action", "controversy", "accounting_restatement", "other")


def events_rows(run_dir: Path) -> List[dict]:
    path = run_dir / "corpus" / "events.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def events_errors(run_dir: Path, years: int = 10, tdir: Optional[Path] = None) -> List[str]:
    """The historian's timeline: the columns, a date in the window and a category for every event, the search log, and
    (from its own transcripts) every cited source opened in its session."""
    path = run_dir / "corpus" / "events.csv"
    if not path.exists():
        return ["corpus/events.csv does not exist yet"]
    with path.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        cols, rows = rd.fieldnames or [], list(rd)
    errs = []
    if cols != EVENT_COLUMNS:
        errs.append("events.csv columns must be exactly %s" % ",".join(EVENT_COLUMNS))
    if not (run_dir / "corpus" / "EVENTS.md").exists():
        errs.append("corpus/EVENTS.md (the timeline and the search log) does not exist yet")
    if not rows:
        errs.append("events.csv has no events: record the searches in EVENTS.md and the events they found")
    cutoff = str(rl.load_json(run_dir / rl.RUN_MANIFEST).get("research_cutoff") or now()[:10])
    low = "%04d" % (int(cutoff[:4]) - years - 1)
    sessions = agent_sessions(run_dir, "historian", tdir)
    seen = Seen(sessions) if sessions else None
    ids = Counter(r.get("event_id") for r in rows)
    for r in rows:
        e = r.get("event_id") or "?"
        if ids[e] > 1:
            errs.append("%s: duplicate event_id" % e)
        d = (r.get("date") or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", d):
            errs.append("%s: date %r must be YYYY-MM-DD (or YYYY-MM)" % (e, d))
        elif d > cutoff or d[:4] < low:
            errs.append("%s: date %s is outside the window (%s to %s)" % (e, d, low, cutoff))
        if not re.fullmatch(r"FY\d{4}", (r.get("fiscal_year") or "").strip()):
            errs.append("%s: fiscal_year must look like FY2024" % e)
        if r.get("category") not in EVENT_CATEGORIES:
            errs.append("%s: category %r is not one of %s" % (e, r.get("category"), ", ".join(EVENT_CATEGORIES)))
        if not (r.get("event") or "").strip():
            errs.append("%s: the event is empty" % e)
        url = (r.get("source_url") or "").strip()
        if not re.match(r"^https?://", url):
            errs.append("%s: source_url must be the http(s) address of the source opened" % e)
        elif seen is not None and not seen.opened({url, re.sub(r"^https?://", "", url).rstrip("/")}):
            errs.append("%s: its source was never opened in your session (%s): open it and confirm the event" % (e, url[:90]))
    return errs[:60]


def refresh_sample(run_dir: Path, name: str) -> None:
    """After the specialist corrected claims: the sample keeps its claim IDs with their current ledger rows (a claim the
    specialist removed leaves the sample: it is no longer made)."""
    sp = vdir(run_dir) / ("%s_sample.csv" % name)
    if not sp.exists():
        return
    with sp.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        cols, ids = rd.fieldnames, [r["claim_id"] for r in rd]
    cur = {r["claim_id"]: r for r in ledger_rows(ledgers_of(run_dir, name))}
    with sp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for c in ids:
            if c in cur:
                w.writerow(cur[c])


def claims_result(run_dir: Path, name: str, write: bool = True) -> Tuple[dict, List[str]]:
    """(Tier B record, errors in the verifier's file). Material discrepancies and unverifiable claims become findings."""
    sp = vdir(run_dir) / ("%s_sample.csv" % name)
    cp = vdir(run_dir) / ("%s_claims.csv" % name)
    if not sp.exists():
        return {}, ["no sample: verify.py sample RUN_DIR %s" % name]
    with sp.open(encoding="utf-8", newline="") as f:
        want = [r["claim_id"] for r in csv.DictReader(f)]
    if not cp.exists():
        return {}, ["the verifier has not written %s" % cp.name]
    with cp.open(encoding="utf-8", newline="") as f:
        got = {r.get("claim_id", ""): r for r in csv.DictReader(f)}
    errs = ["%s: no row for %s" % (cp.name, c) for c in want if c not in got]
    errs += ["%s: %s result %r is not one of %s" % (cp.name, c, r.get("result"), ", ".join(VERIFIER_RESULTS))
             for c, r in got.items() if c in want and r.get("result") not in VERIFIER_RESULTS]
    errs += ["%s: %s needs the evidence (what the source says, and where)" % (cp.name, c)
             for c, r in got.items() if c in want and r.get("result") != "Confirmed" and not (r.get("evidence") or "").strip()]
    errs += verifier_opened(run_dir, name, want)
    if errs:
        return {}, errs
    cnt = Counter(got[c]["result"] for c in want)
    mat = ["%s: %s" % (c, (got[c].get("evidence") or "")[:200]) for c in want if got[c]["result"] == "Material discrepancy"]
    unv = ["%s: %s" % (c, (got[c].get("evidence") or "")[:200]) for c in want if got[c]["result"] == "Not verifiable"]
    fs = []
    wrong = [c for c in want if got[c]["result"] == "Material discrepancy"]
    if mat:
        g = cg.build(run_dir, write=False)
        built = [d for d in cg.down(g, wrong) if g["owners"].get(d) == name]
        deps = [d for d in built if d in g["claims"]]
        lines = [d for d in built if d in g["lines"]]
        fs.append(finding("CLAIM_DISCREPANCY", name, "%d of %d re-checked claims materially differ from their sources" % (
            len(mat), len(want)), "Correct each claim to what the source says, as printed; the verifier re-checks them. "
            "Built on them (claim_graph.py down): %s; report lines citing them: %s. Review each built claim and "
            "record it in specialists/%s_workpapers/propagation.csv (%s)." % (
                ", ".join(deps[:40]) or "none", ", ".join(lines[:20]) or "none", name, ",".join(PROPAGATION_COLUMNS)),
            mat))
    if unv:
        fs.append(finding("CLAIM_UNVERIFIABLE", name, "%d re-checked claims could not be located at their sources" % len(unv),
                          "Give each claim a source and locator anyone can open (document, page, URL), or remove it.", unv))
    rec = {"sampled": len(want), "results": dict(cnt), "findings": fs, "checked_at": now()}
    if write:
        path = vdir(run_dir) / ("%s.json" % name)
        full = rl.load_json(path) if path.exists() else {"agent": name, "tier_a": [], "waived": {}, "rounds": []}
        for f in fs:
            f["id"] = "%s-%s" % (name, f["check"])
            if f["id"] in full.get("waived", {}):
                f["waived"] = full["waived"][f["id"]]
        full["tier_b"] = rec
        full["corrected"] = sorted(set(full.get("corrected", [])) | set(wrong))
        full["status"] = status_of(full)
        rl.write_json(path, full)
    return rec, []


def note_round(run_dir: Path, name: str, what: str) -> None:
    path = vdir(run_dir) / ("%s.json" % name)
    rec = rl.load_json(path) if path.exists() else {"agent": name, "tier_a": [], "tier_b": {}, "waived": {}, "rounds": []}
    rec.setdefault("rounds", []).append({"at": now(), "what": what})
    rl.write_json(path, rec)


# --------------------------------------------------------------------------------------------------------------
# The whole research
# --------------------------------------------------------------------------------------------------------------

def cio_findings(run_dir: Path, tdir: Path) -> List[dict]:
    """The CIO's own ledger against what the CIO's sessions read (the main session; only this run's part of it)."""
    led = run_dir / "cio" / "cio_ledger.csv"
    if not led.exists() or not tdir.exists():
        return []
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    run_id = m.get("run_id", run_dir.name)
    head_ids = {h["session_id"] for h in ra.headless_sessions(run_dir, tdir)}
    t0, t1 = str(m.get("started_at") or "")[:19], str(m.get("completed_at") or "9999")[:19]
    sessions = []
    for jl in ra.find_main_sessions(tdir, run_id):
        if jl.stem in head_ids:
            continue
        ents = [d for d in ra.load_lines(jl) if not d.get("timestamp") or t0 <= d["timestamp"][:19] <= t1]
        sessions.append({"entries": ents})
    if not sessions:
        return []
    return claim_checks(ledger_rows([led]), Seen(sessions), source_keys(run_dir), "cio")


def run(run_dir: Path, stage: str, tdir: Optional[Path] = None) -> dict:
    tdir = tdir or ra.transcripts_dir()
    findings, per = [], {}
    st = rl.load_json(run_dir / "corpus" / "reading" / "status.json") if (run_dir / "corpus" / "reading" / "status.json").exists() else {}
    if (run_dir / "corpus" / "reading" / "plan.json").exists() and not st.get("complete"):
        findings.append(finding("READING_INCOMPLETE", "cio", "the reading stage is not complete (reading.py status --strict)",
                                "Finish the reading stage before Stage 1."))
    ev = rl.load_json(run_dir / "corpus" / "reading" / "events_check.json") if (run_dir / "corpus" / "reading" / "events_check.json").exists() else {}
    if ev.get("unmatched"):
        findings.append(finding("EVENTS_NOT_FOUND", "cio", "%d major event(s) from news and the web were not found in the "
                                "reports read (corpus/dossiers/events.md)" % ev["unmatched"],
                                "Put each in the gap register and send it to its owning specialist: confirm it in a primary "
                                "source, and say whether the reading missed it or the company did not disclose it.",
                                ["%s %s" % (r.get("event_id"), (r.get("event") or "")[:80]) for r in ev.get("rows", [])
                                 if r.get("status") == "unmatched"]))
    for name in rl.SPECIALISTS:
        if not (run_dir / "specialists" / ("%s.md" % name)).exists():
            continue
        rec = specialist(run_dir, name, tdir)
        if not rec.get("tier_b") and not rec.get("waived", {}).get("%s-TIER_B" % name):
            rec["tier_a"].append(dict(finding("SPECIALIST_UNVERIFIED", name, "the verifier did not re-check this specialist's "
                                                                              "claims (agent_driver.py verify)",
                                              "Run python3 scripts/agent_driver.py verify RUN_DIR --only %s." % name),
                                      id="%s-TIER_B" % name))
            rec["status"] = status_of(rec)
        per[name] = rec
    if stage == "final":
        if (run_dir / rl.READING_AUDIT).exists():
            aud = rl.load_json(run_dir / rl.READING_AUDIT)
            if aud.get("status") != "PASS" and not aud.get("waiver"):
                findings.append(finding("READING_AUDIT", "cio", "the reading audit is %s" % aud.get("status"),
                                        "Fix every reading-audit error (cio.md Stage 4 step 0)."))
        else:
            findings.append(finding("READING_AUDIT", "cio", "no reading audit", "Run reading_audit.py run RUN_DIR."))
        findings += cio_findings(run_dir, tdir)
        g = cg.build(run_dir)
        errs = ["%s cites %s, which no ledger holds" % (m["node"], m["id"]) for m in g["errors"]["missing"]
                if g["owners"].get(m["node"]) == "cio"]
        errs += ["%s names no input claim ID" % c for c in g["errors"]["calculation_without_inputs"]
                 if g["claims"][c]["owner"] == "cio"] + ["cycle: %s" % " -> ".join(c) for c in g["errors"]["cycles"]]
        if errs:
            findings.append(finding("CIO_CLAIM_GRAPH", "cio", "%d broken link(s) in the CIO's claims, scorecard or report"
                                    % len(errs), "Fix each (python3 scripts/claim_graph.py build RUN_DIR).", errs))
        corrected = sorted({c for n in per for c in rl.load_json(vdir(run_dir) / ("%s.json" % n)).get("corrected", [])
                            if (vdir(run_dir) / ("%s.json" % n)).exists()})
        todo = unreviewed(run_dir, g, "cio", corrected)
        if todo:
            findings.append(finding("CIO_DEPENDENT_NOT_REVIEWED", "cio", "%d CIO claim(s) or scorecard input(s) built on "
                                    "claims the verification corrected" % len(todo),
                                    "Review each against the corrected claim, rebuild the scorecard and ladder where it "
                                    "changes, and record each in cio/propagation.csv (%s)." % ",".join(PROPAGATION_COLUMNS),
                                    todo))
        aud_ledgers = sorted((run_dir / "audit").glob("*_ledger.csv"))
        aud_sessions = agent_sessions(run_dir, rl.AUDITOR, tdir)
        if aud_ledgers and aud_sessions:      # the auditor's own claims, against what its sessions read
            for f in claim_checks(ledger_rows(aud_ledgers), Seen(aud_sessions), source_keys(run_dir), rl.AUDITOR):
                f["owner"] = "auditor"
                findings.append(f)
        ar = run_dir / rl.AUDIT_REPORT
        if ar.exists():
            res = rl.Result("audit")
            rl.check_audit_resolutions(run_dir, rl.audit_findings(ar.read_text(encoding="utf-8")), res)
            if not res.ok:
                findings.append(finding("AUDIT_OPEN", "cio", "; ".join(res.errors[:3]), "Resolve every Critical and Major "
                                                                                          "audit finding (cio.md Stage 4)."))
    waived = rl.load_json(vdir(run_dir) / "run_waivers.json") if (vdir(run_dir) / "run_waivers.json").exists() else {}
    for f in findings:
        if f["agent"] == rl.AUDITOR:
            f["id"] = "auditor-%s" % f["check"]
        else:
            f["id"] = "run-%s" % f["check"] if f["agent"] == "cio" and f["check"] not in (
                "NUMBER_NOT_SEEN", "SOURCE_NOT_OPENED", "PAGE_NOT_OPENED") else "cio-%s" % f["check"]
        if f["id"] in waived:
            f["waived"] = waived[f["id"]]
    blocking = [f for f in findings if f["severity"] == "blocking" and not f.get("waived")]
    failed = [n for n, r in per.items() if r["status"] != "PASS"]
    out = {"run_id": rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id", run_dir.name), "stage": stage, "checked_at": now(),
           "status": "FAIL" if blocking or failed else "PASS", "run_findings": findings,
           "specialists": {n: {"status": r["status"], "claims": r.get("claims", 0), "tier_b": r.get("tier_b", {}).get("results", {}),
                               "rounds": len(r.get("rounds", [])),
                               "findings": [{k: f[k] for k in ("id", "check", "severity", "owner", "detail")} |
                                            {"waived": bool(f.get("waived"))} for f in open_findings(r) + [
                                                f for f in r.get("tier_a", []) if f.get("waived")]]} for n, r in per.items()}}
    rl.write_json(run_dir / "qc" / "verification.json", out)
    write_md(run_dir, out)
    return out


def write_md(run_dir: Path, out: dict) -> None:
    lines = ["# Verification — run %s (%s stage)" % (out["run_id"], out["stage"]), "",
             "Generated by `scripts/verify.py run`; do not edit. Checks the work against what each agent did (its "
             "transcripts and files), not only the shape of its report.", "", "**Status: %s**" % out["status"], "",
             "| Specialist | Status | Claims | Verifier re-check | Remediation rounds | Open findings |", "|---|---|---|---|---|---|"]
    for n, r in out["specialists"].items():
        tb = ", ".join("%s %d" % (k, v) for k, v in sorted(r["tier_b"].items())) or "-"
        opn = "; ".join("%s (%s)" % (f["check"], f["severity"]) for f in r["findings"] if not f["waived"]) or "none"
        lines.append("| %s | %s | %d | %s | %d | %s |" % (n, r["status"], r["claims"], tb, r["rounds"], opn))
    if out["run_findings"]:
        lines += ["", "## Run-level findings", ""] + ["- **%s** (%s, %s)%s: %s" % (
            f["check"], f["severity"], f["owner"], " — waived: %s" % f["waived"]["reason"] if f.get("waived") else "",
            f["detail"]) for f in out["run_findings"]]
    waived = [(n, f) for n, r in out["specialists"].items() for f in r["findings"] if f["waived"]]
    if waived:
        lines += ["", "## Waived by the CIO", ""] + ["- %s %s" % (n, f["id"]) for n, f in waived]
    (run_dir / "qc" / "VERIFICATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def waive(run_dir: Path, fid: str, reason: str) -> None:
    if not reason.strip():
        raise SystemExit("a waiver needs its reason")
    entry = {"reason": reason, "at": now()}
    name = next((s for s in sorted(rl.SPECIALISTS, key=len, reverse=True) if fid.startswith(s + "-")), "")
    if name:
        path = vdir(run_dir) / ("%s.json" % name)
        rec = rl.load_json(path) if path.exists() else {"agent": name, "tier_a": [], "tier_b": {}, "rounds": []}
        rec.setdefault("waived", {})[fid] = entry
        for f in rec.get("tier_a", []) + (rec.get("tier_b") or {}).get("findings", []):
            if f.get("id") == fid:
                f["waived"] = entry
        rec["status"] = status_of(rec)
        rl.write_json(path, rec)
    else:
        path = vdir(run_dir) / "run_waivers.json"
        data = rl.load_json(path) if path.exists() else {}
        data[fid] = entry
        path.parent.mkdir(parents=True, exist_ok=True)
        rl.write_json(path, data)


# --------------------------------------------------------------------------------------------------------------
# Learning across runs
# --------------------------------------------------------------------------------------------------------------

def all_results(root: Optional[Path] = None) -> List[dict]:
    root = root or rl.ROOT / "research" / "companies"
    out = []
    for p in sorted(root.glob("*/runs/*/qc/verification.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return out


def lesson_counts(root: Optional[Path] = None, last: int = 5) -> Dict[Tuple[str, str], int]:
    """(agent, check) -> number of the last `last` verified runs in which the check found something (waived or not)."""
    res = sorted(all_results(root), key=lambda r: r.get("run_id", ""))[-last:]
    if root is None:                   # lessons measured before the loop existed (config/verification_lessons_seed.json)
        seed = rl.ROOT / "config" / "verification_lessons_seed.json"
        if seed.exists():
            data = json.loads(seed.read_text(encoding="utf-8")).get("findings", {})
            res = [{"specialists": {a: {"findings": [{"check": c} for c in cs]} for a, cs in data.items()}}] + res
    cnt: Counter = Counter()
    for r in res:
        hit = set()
        for name, s in r.get("specialists", {}).items():
            for f in s.get("findings", []):
                hit.add((name, f["check"]))
        cnt.update(hit)
    return dict(cnt)


def lessons_text(agent: str, root: Optional[Path] = None) -> str:
    """The process lessons for one agent's brief: the checks its earlier runs failed, with the rule each enforces.
    Generic by construction: no company, fact or conclusion of an earlier run is carried over."""
    cnt = lesson_counts(root)
    mine = sorted(((c, n) for (a, c), n in cnt.items() if a == agent and CHECKS.get(c, ("", "", False, ""))[3]),
                  key=lambda x: -x[1])
    if not mine:
        return ""
    lines = ["LESSONS FROM VERIFICATION OF YOUR EARLIER RUNS (process only; your work is checked for these again):"]
    lines += ["- %s (found in %d of the last verified runs): %s" % (c, n, CHECKS[c][3]) for c, n in mine]
    return "\n".join(lines)


def check_review(root: Optional[Path] = None) -> List[str]:
    """Checks the CIO waived in most of the runs where they fired: candidates for the owner to recalibrate."""
    fired, waived = Counter(), Counter()
    for r in all_results(root):
        for s in r.get("specialists", {}).values():
            for f in s.get("findings", []):
                fired[f["check"]] += 1
                waived[f["check"]] += bool(f.get("waived"))
    return ["%s waived %d of %d times" % (c, waived[c], fired[c]) for c in fired if fired[c] >= 3 and waived[c] / fired[c] > 0.5]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("specialist", "sample", "claims"):
        p = sub.add_parser(c)
        p.add_argument("run_dir")
        p.add_argument("name", choices=sorted(rl.SPECIALISTS))
        if c == "sample":
            p.add_argument("--n", type=int, default=0)
    r = sub.add_parser("run")
    r.add_argument("run_dir")
    r.add_argument("--stage", choices=["specialists", "final"], required=True)
    ev = sub.add_parser("events")
    ev.add_argument("run_dir")
    ev.add_argument("--years", type=int, default=10)
    w = sub.add_parser("waive")
    w.add_argument("run_dir")
    w.add_argument("finding_id")
    w.add_argument("--reason", required=True)
    ls = sub.add_parser("lessons")
    ls.add_argument("--agent", default="")
    a = ap.parse_args(argv)
    if a.cmd == "lessons":
        for name in ([a.agent] if a.agent else sorted(rl.SPECIALISTS)):
            print("%s:\n%s\n" % (name, lessons_text(name) or "  (no findings in earlier runs)"))
        for x in check_review():
            print("REVIEW: %s" % x)
        return 0
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if a.cmd == "specialist":
        rec = specialist(run_dir, a.name)
        for f in open_findings(rec):
            print("%s %s (%s): %s" % (f["severity"].upper(), f["check"], f["owner"], f["detail"]))
        print("%s: %s" % (a.name, rec["status"]))
        return 0 if rec["status"] == "PASS" else 1
    if a.cmd == "sample":
        got = sample(run_dir, a.name, a.n)
        print("%d claims -> %s" % (len(got), vdir(run_dir) / ("%s_sample.csv" % a.name)))
        return 0
    if a.cmd == "claims":
        rec, errs = claims_result(run_dir, a.name)
        for e in errs:
            print("ERROR: %s" % e)
        print(json.dumps(rec.get("results", {})))
        return 1 if errs or any(f["severity"] == "blocking" for f in rec.get("findings", [])) else 0
    if a.cmd == "events":
        errs = events_errors(run_dir, a.years)
        for e in errs:
            print("ERROR: %s" % e)
        print("events: %s (%d events)" % ("FAIL" if errs else "PASS", len(events_rows(run_dir))))
        return 1 if errs else 0
    if a.cmd == "waive":
        waive(run_dir, a.finding_id, a.reason)
        print("waived %s" % a.finding_id)
        return 0
    out = run(run_dir, a.stage)
    print("verification %s (%s stage): %s" % (out["status"], a.stage, run_dir / "qc" / "VERIFICATION.md"))
    for n, s in out["specialists"].items():
        if s["status"] != "PASS":
            print("  %s: %s" % (n, "; ".join(f["check"] for f in s["findings"] if not f["waived"])))
    for f in out["run_findings"]:
        if not f.get("waived"):
            print("  run: %s (%s) %s" % (f["check"], f["severity"], f["detail"]))
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
