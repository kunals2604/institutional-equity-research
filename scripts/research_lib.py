"""Shared, deterministic helpers for the equity research system.

Canonical vocabularies (layer names, epistemic tags, verdicts, scoring
weights, required sections, ledger columns) are NOT defined here. They are
parsed from marked blocks in the governing markdown so the documents remain
the single source of truth:

    .claude/skills/investment-constitution/SKILL.md   layers, tags, fit scale
    methodology/SCORING.md                           weights, gates, verdicts
    methodology/EVIDENCE_STANDARDS.md                ledger columns, phrases
    methodology/REPORT_CONTRACTS.md                  common report sections
    methodology/METRIC_DEFINITIONS.md                metric keys
    methodology/RESEARCH_PLAYBOOK.md                 historical depth minimums
    .claude/agents/<name>.md                         domain / final sections

Standard library only; Python 3.9 compatible.
"""

import csv
import datetime as dt
import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
CONSTITUTION = ROOT / ".claude" / "skills" / "investment-constitution" / "SKILL.md"
SCORING = ROOT / "methodology" / "SCORING.md"
EVIDENCE = ROOT / "methodology" / "EVIDENCE_STANDARDS.md"
CONTRACTS = ROOT / "methodology" / "REPORT_CONTRACTS.md"
METRICS = ROOT / "methodology" / "METRIC_DEFINITIONS.md"
PLAYBOOK = ROOT / "methodology" / "RESEARCH_PLAYBOOK.md"
AGENTS_DIR = ROOT / ".claude" / "agents"
SCOREBOARD = ROOT / "COMPANY_SCOREBOARD.csv"
INVESTMENT_POLICY = ROOT / "config" / "investment_policy.json"
PROBABILITY_BANDS = ("remote", "low", "moderate", "elevated", "high")

# Run layout (see methodology/REPORT_CONTRACTS.md).
RUN_MANIFEST = "run_manifest.json"
QC_RECORD = "cio/quality_control.md"
LATEST_POINTER = "latest_run.txt"
RUN_ID_RE = re.compile(r"\d{8}T\d{6}Z")
FINAL_LAYER_SECTION = "Four Independent Layer Assessments"
LAYER_BLOCK_FIELDS = (
    "Central question", "Strongest supporting evidence", "Strongest contrary evidence",
    "Business economics", "Valuation methodology", "Base rates", "Bear / base / bull",
    "Risks and thesis-breakers", "Current-price assessment", "What would change the conclusion",
)
FINAL_VERDICT_FIELDS = ("Business quality", "Layer fit", "Current valuation", "Expected return",
                        "Downside risk", "Evidence confidence", "Verdict")
FIT_CONF_RE = re.compile(r"Layer-fit confidence:\**\s*\**\s*(High|Medium|Low)")

# Agent registry: name -> claim-ID prefix. Agent files must exist for each.
# Stage-1 specialists (independent research). `scuttlebutt` joined in methodology 2.4.0.
SPECIALISTS: Dict[str, str] = {
    "financials": "FIN",
    "filings": "FIL",
    "management": "MGT",
    "industry": "IND",
    "moat": "MOAT",
    "concalls": "CON",
    "valuation": "VAL",
    "bear-case": "BEAR",
    "special-situations": "SPS",
    "scuttlebutt": "SCU",
}
SPECIALIST_SINCE: Dict[str, tuple] = {"scuttlebutt": (2, 4, 0)}
CIO_PREFIX = "CIO"
# Independent research auditor (Stage 4, methodology 2.4.0): audits the CIO's draft, never researches the company.
AUDITOR = "auditor"
AUDITOR_PREFIX = "AUD"
# Workers (methodology 3.1.0): they acquire and read documents for everyone (Stage 0) or re-check claims at their
# sources (the verifier, after each specialist); they hold no views, write no claim ledger and never score. Their model
# and effort are pinned by methodology/MODEL_POLICY.md.
WORKERS = ("reader", "critical-reader", "scanner", "librarian", "verifier", "historian")
ALL_PREFIXES = set(SPECIALISTS.values()) | {CIO_PREFIX, AUDITOR_PREFIX}
AGENT_NAMES = set(SPECIALISTS) | {"cio", AUDITOR} | set(WORKERS)

CLAIM_ID_RE = re.compile(r"\b(?:%s)-C\d{3,}\b" % "|".join(sorted(ALL_PREFIXES, key=len, reverse=True)))
TAG_RE = re.compile(
    r"\[(FACT|MANAGEMENT STATEMENT|CALCULATION|ESTIMATE|INFERENCE|JUDGMENT)"
    r"(?:\s*[:|]\s*([^\]]*))?\]"
)
TAGS_REQUIRING_IDS = ("FACT", "MANAGEMENT STATEMENT", "CALCULATION", "ESTIMATE")
NONCANONICAL_TAGS = ("MANAGEMENT CLAIM", "ASSUMPTION", "OPINION", "VERIFIED", "ANALYST ESTIMATE")
PLAUSIBILITY_VALUES = ("raises", "lowers", "no change", "insufficient evidence")
CROSSWALK_FIELDS = (
    "Relevant evidence", "Supports", "Weakens", "Domain implications",
    "Missing information", "Plausibility effect",
)
FIT_SCORE_RE = re.compile(r"Layer-fit score:\**\s*\**\s*(\d{1,3})\s*/\s*100")


class Result:
    """Collects errors and warnings for one check target."""

    def __init__(self, target: str):
        self.target = target
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def extend(self, other: "Result", prefix: str = "") -> None:
        self.errors.extend(prefix + e for e in other.errors)
        self.warnings.extend(prefix + w for w in other.warnings)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {"target": self.target, "ok": self.ok, "errors": self.errors, "warnings": self.warnings}

    def render(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        lines = ["%s  %s  (%d errors, %d warnings)" % (status, self.target, len(self.errors), len(self.warnings))]
        lines += ["  ERROR: " + e for e in self.errors]
        lines += ["  warn:  " + w for w in self.warnings]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parsing canonical blocks from markdown
# ---------------------------------------------------------------------------

def read_block(path: Path, name: str) -> List[str]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<!--\s*%s:BEGIN\s*-->(.*?)<!--\s*%s:END\s*-->" % (name, name), text, re.S)
    if not m:
        raise ValueError("Block %s not found in %s" % (name, path))
    items = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^(?:[-*]|\d+\.)\s+", "", line)
        items.append(line)
    return items


def read_json_block(path: Path, name: str):
    """A JSON value between <!-- NAME:BEGIN --> and <!-- NAME:END --> (an optional ```json fence is ignored)."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<!--\s*%s:BEGIN\s*-->(.*?)<!--\s*%s:END\s*-->" % (name, name), text, re.S)
    if not m:
        raise ValueError("Block %s not found in %s" % (name, path))
    body = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", m.group(1).strip())
    return json.loads(body)


READING_SCHEMAS = ROOT / "methodology" / "READING_SCHEMAS.md"
MODEL_POLICY = ROOT / "methodology" / "MODEL_POLICY.md"


def reading_schema() -> dict:
    return read_json_block(READING_SCHEMAS, "READING_SCHEMA")


def model_policy() -> dict:
    return read_json_block(MODEL_POLICY, "MODEL_POLICY")


def canonical_layers() -> List[str]:
    """Full canonical names, e.g. 'Layer 1 — Bedrock Compounder'."""
    layers = read_block(CONSTITUTION, "CANONICAL_LAYERS")
    if len(layers) != 4:
        raise ValueError("Constitution must define exactly four layers")
    return layers


def layer_short_names() -> Dict[int, str]:
    out = {}
    for full in canonical_layers():
        m = re.match(r"Layer\s+([1-4])\s+—\s+(.+)$", full)
        if not m:
            raise ValueError("Malformed canonical layer line: %r" % full)
        out[int(m.group(1))] = m.group(2).strip()
    return out


def epistemic_tags() -> List[str]:
    return [line.split(" — ")[0].strip() for line in read_block(CONSTITUTION, "EPISTEMIC_TAGS")]


def verdicts() -> List[str]:
    return read_block(SCORING, "VERDICTS")


def valuation_statuses() -> List[str]:
    return read_block(SCORING, "VALUATION_STATUS")


def flagged_phrases() -> List[str]:
    return [p.lower() for p in read_block(EVIDENCE, "FLAGGED_PHRASES")]


def ledger_columns() -> List[str]:
    return read_block(EVIDENCE, "LEDGER_COLUMNS")


def common_head() -> List[str]:
    return read_block(CONTRACTS, "COMMON_SECTIONS_HEAD")


def common_tail() -> List[str]:
    return read_block(CONTRACTS, "COMMON_SECTIONS_TAIL")


def common_sections() -> List[str]:
    return common_head() + common_tail()


def metric_keys() -> Set[str]:
    return {line.split(" — ")[0].strip() for line in read_block(METRICS, "METRIC_KEYS")}


def valid_metric(key: str, keys: Optional[Set[str]] = None) -> bool:
    key = (key or "").strip()
    if key.startswith("other:") and len(key) > 6:
        return True
    if re.fullmatch(r"cagr_[a-z_]+_\d+y", key):
        return True
    return key in (keys if keys is not None else metric_keys())


def _key_values(path: Path, name: str) -> Dict[str, str]:
    out = {}
    for line in read_block(path, name):
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def depth_minimums() -> Dict[str, int]:
    return {k: int(v) for k, v in _key_values(PLAYBOOK, "DEPTH_MINIMUMS").items()}


def evidence_thresholds() -> Dict[str, float]:
    return {k: float(v) for k, v in _key_values(EVIDENCE, "EVIDENCE_THRESHOLDS").items()}


def investment_policy(path: Optional[Path] = None) -> dict:
    return json.loads((path or INVESTMENT_POLICY).read_text(encoding="utf-8"))


# Period counting for the Historical Depth Standard -------------------------

_FY_RE = re.compile(r"\bFY\s?'?(\d{4}|\d{2})\b")
_Q_RE = re.compile(r"\bQ([1-4])\s?FY\s?'?(\d{4}|\d{2})\b")
_QEND_RE = re.compile(r"\b(Mar|Jun|Sep|Dec)[a-z]*[\s'\-]*(\d{4}|\d{2})\b")
_YEAR_RE = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")


def _yr(s: str) -> int:
    y = int(s)
    return y + 2000 if y < 100 else y


def fiscal_years(text: str) -> Set[int]:
    return {_yr(m.group(1)) for m in _FY_RE.finditer(text)}


def quarters(text: str) -> Set[str]:
    out = {"Q%sFY%d" % (m.group(1), _yr(m.group(2))) for m in _Q_RE.finditer(text)}
    out |= {"%s%d" % (m.group(1), _yr(m.group(2))) for m in _QEND_RE.finditer(text)}
    return out


def any_years(text: str) -> Set[int]:
    return fiscal_years(text) | {int(y) for y in _YEAR_RE.findall(text)}


SINCE_RE = re.compile(r"^(.*?)\s*\(since (\d+(?:\.\d+){1,2})\)\s*$")


def agent_sections(agent: str, version: Optional[tuple] = None) -> List[str]:
    """Required H2 sections of an agent's report. A section marked `(since X.Y.Z)` in the agent definition is
    required only of runs produced under methodology X.Y.Z or later; `version=None` returns every section."""
    out = []
    for item in read_block(AGENTS_DIR / ("%s.md" % agent), "REQUIRED_SECTIONS"):
        m = SINCE_RE.match(item)
        if m:
            if version is not None and version < version_tuple(m.group(2)):
                continue
            item = m.group(1)
        out.append(item)
    return out


def round_half_up(x: float) -> int:
    """The single rounding rule for every score in the system (0.5 rounds up; float noise ignored).
    Python's built-in round() is banker's rounding, so 60.5 -> 60; scores must not depend on that."""
    return int(math.floor(float(x) + 0.5 + 1e-9))


CHECKLIST_SECTION = "Method Coverage Checklist"
CHECKLIST_STATUSES = ("done", "partial", "not available", "not applicable")


def method_steps(agent: str) -> List[str]:
    """Top-level numbered steps of the '## Method' section of an agent definition (nested lists ignored)."""
    path = AGENTS_DIR / ("%s.md" % agent)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^## Method\s*$(.*?)(?=^## )", text, re.M | re.S)
    if not m:
        return []
    out = []
    for _, t in re.findall(r"^(\d+)\.\s+(.*)$", m.group(1), re.M):
        b = re.match(r"\*\*(.+?)\*\*", t)
        out.append((b.group(1) if b else t[:60]).strip().rstrip(".:"))
    return out


def check_method_checklist(agent: str, text: str, res: "Result") -> None:
    """Every numbered method step of the agent definition must appear as a row of the Method Coverage Checklist,
    with a status (Done | Partial | Not available | Not applicable); Partial / Not available rows must say what was
    tried and why it fell short. This makes silent omissions impossible."""
    steps = method_steps(agent)
    body = section(text, CHECKLIST_SECTION)
    if body is None or not steps:
        return
    rows = [l.strip() for l in body.splitlines() if l.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|\s*:?-{2,}", r)]
    data = rows[1:] if rows else []
    if len(data) < len(steps):
        res.error("%s: %d rows but the agent definition has %d method steps (one row per step)"
                  % (CHECKLIST_SECTION, len(data), len(steps)))
    for r in data:
        cells = [c.strip() for c in r.strip("|").split("|")]
        low = " ".join(cells).lower()
        status = next((st for st in CHECKLIST_STATUSES if re.search(r"\b%s\b" % st, low)), None)
        if status is None:
            res.error("%s row without a status (Done | Partial | Not available | Not applicable): %s" % (CHECKLIST_SECTION, r[:80]))
        elif status in ("partial", "not available") and (len(cells) < 2 or cells[-1] in ("", "-", "—", "n/a")):
            res.warn("%s: '%s' row must say what was tried and why it fell short (last column)" % (CHECKLIST_SECTION, cells[0][:50]))


def methodology_version() -> str:
    m = re.search(r"<!--\s*METHODOLOGY_VERSION:\s*([\w.\-]+)\s*-->", SCORING.read_text(encoding="utf-8"))
    return m.group(1) if m else "unversioned"


# Contract additions of methodology 2.3.0. Runs recorded under an earlier version are validated without them,
# so a legacy run is judged by the contract it was produced under.
V23 = (2, 3, 0)
V23_FINAL_SECTIONS = ("CIO Independent Analysis", "Confidence Assessment")
V23_CIO_FILES = ("cio/gap_register.md", "cio/cio_analysis.md")
# Contract additions of methodology 2.4.0: the scuttlebutt specialist, the independent audit, the Stage-0
# document map (both evidence channels cross-checked) and SME enhanced-scrutiny sections.
V24 = (2, 4, 0)
V24_FINAL_SECTIONS = ("Ground-Truth Evidence", "Independent Audit and Resolutions")
V24_CIO_FILES = ("cio/audit_resolutions.md", "corpus/DOCUMENT_MAP.md")
AUDIT_REPORT = "audit/audit_report.md"
AUDIT_LEDGER = "audit/auditor_ledger.csv"
SME_SECTION = "SME Enhanced Scrutiny"
# Contract additions of methodology 3.1.0: the Stage-0b reading stage (every in-scope page read once and recorded,
# critical sections read twice), structured exchange filings, pinned models and efforts, and the reading audit.
V31 = (3, 1, 0)
READING_COVERAGE = "corpus/reading/COVERAGE.md"
READING_STATUS = "corpus/reading/status.json"
DOSSIER_INDEX = "corpus/dossiers/INDEX.md"
STRUCTURED_SUMMARY = "corpus/STRUCTURED.md"
READING_AUDIT = "qc/reading_audit.json"
V31_RUN_FILES_SPECIALISTS = (READING_COVERAGE, READING_STATUS, DOSSIER_INDEX, STRUCTURED_SUMMARY)
COVERAGE_BLOCK = "READING_COVERAGE"
# A specialist states what it relied on; the record of what was read is the reading ledger, generated by script.
OVERCLAIM_RE = re.compile(r"\b(read (?:in full|end to end|cover to cover|every page|all pages)|"
                          r"(?:fully|completely|exhaustively) read|read in substance|every page (?:was |has been )?read)\b", re.I)


def version_tuple(v: Optional[str]) -> tuple:
    nums = re.findall(r"\d+", str(v or ""))
    return tuple(int(x) for x in nums[:3]) if nums else (0,)


def is_legacy(run_version: Optional[str]) -> bool:
    """True when a run was produced under a methodology older than 2.3.0."""
    return version_tuple(run_version) < V23


def current_version() -> tuple:
    return version_tuple(methodology_version())


def specialists_for(run_version: Optional[tuple] = None) -> Dict[str, str]:
    """The Stage-1 specialists a run of this methodology version must have (all of them for current runs)."""
    v = run_version or current_version()
    return {n: p for n, p in SPECIALISTS.items() if v >= SPECIALIST_SINCE.get(n, (0,))}


def effective_version(legacy: bool = False, version: Optional[tuple] = None) -> tuple:
    """Version whose contract applies: `legacy=True` means a pre-2.3.0 run (kept for older callers)."""
    if legacy:
        return (2, 2, 0)
    return version or current_version()


def _parse_table_block(path: Path, name: str) -> List[List[str]]:
    rows = []
    for line in read_block(path, name):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or set(cells[0]) <= set("-: ") or cells[0].lower() in ("id", "gate"):
            continue
        rows.append(cells)
    return rows


def dimension_weights(kind: str) -> List[Tuple[str, str, int]]:
    """kind = 'BQ' or 'IA'. Returns (id, name, weight)."""
    rows = _parse_table_block(SCORING, "%s_DIMENSIONS" % kind)
    return [(r[0], r[1], int(r[2])) for r in rows]


def gates(kind: str) -> Dict[str, Tuple[str, Optional[int]]]:
    """Returns gate id -> (trigger text, cap value)."""
    out = {}
    for r in _parse_table_block(SCORING, "%s_GATES" % kind):
        cap = re.search(r"≤\s*(\d+)", r[2])
        out[r[0]] = (r[1], int(cap.group(1)) if cap else None)
    return out


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def parse_front_matter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, v = line.split(":", 1)
            v = v.split(" #")[0].strip().strip('"').strip("'")
            out[k.strip()] = v
    return out


def norm_heading(h: str) -> str:
    h = re.sub(r"^\s*\d+(\.\d+)*[.)]?\s+", "", h)
    h = h.replace("&", "and").replace("–", "-").replace("—", "-")
    h = re.sub(r"[*`]", "", h)
    h = re.sub(r"\s+", " ", h).strip().rstrip(":.").lower()
    return h


def h2_headings(text: str) -> List[str]:
    return [norm_heading(m.group(1)) for m in re.finditer(r"^##\s+(?!#)(.+)$", text, re.M)]


def section(text: str, heading: str) -> Optional[str]:
    target = norm_heading(heading)
    matches = list(re.finditer(r"^##\s+(?!#)(.+)$", text, re.M))
    for i, m in enumerate(matches):
        if norm_heading(m.group(1)) == target:
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            return text[m.end():end]
    return None


def h3_blocks(text: str) -> List[Tuple[str, str]]:
    matches = list(re.finditer(r"^###\s+(?!#)(.+)$", text, re.M))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group(1).strip(), text[m.end():end]))
    return out


def norm_layer(s: str) -> str:
    s = s.replace("–", "—").replace(" - ", " — ")
    s = re.sub(r"[*`]", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Content checks
# ---------------------------------------------------------------------------

_LAYER_KEYWORDS = {
    1: ("compounder", "bedrock"),
    2: ("growth",),
    3: ("cyclical", "event", "deep value", "special situation", "turnaround"),
    4: ("venture", "optionality"),
}
_FORBIDDEN_LABEL_WORDS = ("trap", "commodity", "excessive price", "overvalu", "low-moat", "low moat")
_LAYER_REF_RE = re.compile(
    r"Layer\s*([1-4])\s*\**\s*(?:—|–|-|:|\||│)\s*\**\s*([^\n|│*`]{0,70})", re.I
)


def check_layer_names(text: str, res: Result) -> None:
    """Detect renamed / redefined layers (the TVS-run failure)."""
    short = layer_short_names()
    canon_norm = {n: re.sub(r"[^a-z]", "", short[n].lower()) for n in short}
    for m in _LAYER_REF_RE.finditer(text):
        n = int(m.group(1))
        label = m.group(2)
        label = re.split(r"[:.(;,]| — | - |–", label)[0].strip().lower()
        if not label:
            continue
        compact = re.sub(r"[^a-z]", "", label)
        own = any(k in label for k in _LAYER_KEYWORDS[n])
        other = [k for j, ks in _LAYER_KEYWORDS.items() if j != n for k in ks if k in label]
        bad = [w for w in _FORBIDDEN_LABEL_WORDS if w in label]
        snippet = m.group(0).strip()[:80]
        if bad:
            res.error("Layer %d labelled with non-archetype term %s: %r" % (n, bad, snippet))
        elif other and not own:
            res.error("Layer %d appears to be redefined (uses another layer's archetype %s): %r" % (n, other, snippet))
        elif own and not (canon_norm[n].startswith(compact) or compact.startswith(canon_norm[n])):
            res.warn("Non-standard Layer %d label (canonical: %r): %r" % (n, short[n], snippet))


def find_tags(text: str) -> List[Tuple[int, str, List[str]]]:
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in TAG_RE.finditer(line):
            ids = CLAIM_ID_RE.findall(m.group(2) or "")
            out.append((lineno, m.group(1), ids))
    return out


def check_tags(text: str, res: Result, known_ids: Optional[Set[str]],
               allowed_prefixes: Optional[Set[str]] = None) -> int:
    tags = find_tags(text)
    if not tags:
        res.error("No epistemic tags found")
    for lineno, tag, ids in tags:
        if tag in TAGS_REQUIRING_IDS and not ids:
            res.error("Line %d: [%s] without a claim ID" % (lineno, tag))
        for cid in ids:
            if known_ids is not None and cid not in known_ids:
                res.error("Line %d: claim ID %s not found in ledger(s)" % (lineno, cid))
            if allowed_prefixes is not None and cid.split("-")[0] not in allowed_prefixes:
                res.warn("Line %d: cites another author's claim %s in an initial report" % (lineno, cid))
    for bad in NONCANONICAL_TAGS:
        if re.search(r"\[%s\b" % re.escape(bad), text):
            res.warn("Non-canonical tag [%s] used" % bad)
    return len(tags)


def check_flagged_phrases(text: str, res: Result, strict: bool) -> None:
    for lineno, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        for p in flagged_phrases():
            if p in low:
                quoted = "[management statement" in low
                msg = "Line %d: flagged phrase %r" % (lineno, p)
                if strict and not quoted:
                    res.error(msg)
                else:
                    res.warn(msg)


def check_crosswalk(text: str, res: Result) -> None:
    body = section(text, "Four-Layer Evidence Crosswalk")
    if body is None:
        res.error("Missing section: Four-Layer Evidence Crosswalk")
        return
    blocks = h3_blocks(body)
    heads = [norm_layer(h) for h, _ in blocks]
    expected = canonical_layers()
    positions = []
    for layer in expected:
        if layer not in heads:
            res.error("Crosswalk missing exact heading '### %s'" % layer)
            continue
        positions.append(heads.index(layer))
        content = blocks[heads.index(layer)][1]
        for field in CROSSWALK_FIELDS:
            if not re.search(r"\**%s\**\s*:" % re.escape(field), content, re.I):
                (res.error if field == "Plausibility effect" else res.warn)(
                    "Crosswalk %s: missing field '%s'" % (layer.split(" — ")[0], field))
        m = re.search(r"Plausibility effect\**\s*:\**\s*\**\s*([A-Za-z ]+)", content, re.I)
        if m and not any(m.group(1).strip().lower().startswith(v) for v in PLAUSIBILITY_VALUES):
            res.error("Crosswalk %s: plausibility effect %r not in %s"
                      % (layer.split(" — ")[0], m.group(1).strip(), PLAUSIBILITY_VALUES))
    if positions != sorted(positions):
        res.warn("Crosswalk layers are not in canonical order")


def check_sections(text: str, required: List[str], res: Result) -> None:
    present = h2_headings(text)
    for s in required:
        if norm_heading(s) not in present:
            res.error("Missing section: %s" % s)


# ---------------------------------------------------------------------------
# Ledgers
# ---------------------------------------------------------------------------

def read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        return list(header), [dict(r) for r in reader]


def validate_ledger(path: Path, expected_prefix: Optional[str] = None) -> Tuple[Result, Set[str]]:
    res = Result(str(path))
    ids: Set[str] = set()
    if not path.exists():
        res.error("Ledger missing")
        return res, ids
    try:
        header, rows = read_csv(path)
    except Exception as exc:  # malformed CSV
        res.error("Unreadable CSV: %s" % exc)
        return res, ids
    cols = ledger_columns()
    if header != cols:
        res.error("Header mismatch. Expected: %s" % ",".join(cols))
        return res, ids
    tags = set(epistemic_tags())
    mkeys = metric_keys()
    for i, r in enumerate(rows, 2):
        cid = (r.get("claim_id") or "").strip()
        where = "row %d (%s)" % (i, cid or "no id")
        if not CLAIM_ID_RE.fullmatch(cid):
            res.error("%s: malformed claim_id" % where)
        elif cid in ids:
            res.error("%s: duplicate claim_id" % where)
        else:
            ids.add(cid)
        if expected_prefix and cid and not cid.startswith(expected_prefix + "-"):
            res.error("%s: prefix should be %s" % (where, expected_prefix))
        tag = (r.get("tag") or "").strip()
        if tag not in tags:
            res.error("%s: tag %r not canonical" % (where, tag))
        if not (r.get("claim") or "").strip():
            res.error("%s: empty claim" % where)
        metric = (r.get("metric") or "").strip()
        if (r.get("value") or "").strip() and tag in ("FACT", "CALCULATION", "ESTIMATE"):
            if not metric:
                res.error("%s: quantitative %s requires a metric key (METRIC_DEFINITIONS.md)" % (where, tag))
            elif not valid_metric(metric, mkeys):
                res.error("%s: metric %r not in METRIC_DEFINITIONS.md (use other:<name>)" % (where, metric))
        elif metric and not valid_metric(metric, mkeys):
            res.error("%s: metric %r not in METRIC_DEFINITIONS.md (use other:<name>)" % (where, metric))
        tier = (r.get("source_tier") or "").strip()
        conf = (r.get("confidence") or "").strip()
        prim = (r.get("primary") or "").strip()
        if conf not in ("H", "M", "L"):
            res.error("%s: confidence must be H/M/L" % where)
        has_source = bool((r.get("source_url_or_id") or "").strip())
        locator = (r.get("locator") or "").strip()
        if tag in ("FACT", "MANAGEMENT STATEMENT"):
            if not has_source:
                res.error("%s: %s requires source_url_or_id" % (where, tag))
            if not (r.get("retrieved_date") or "").strip():
                res.error("%s: %s requires retrieved_date" % (where, tag))
            if not locator:
                res.error("%s: %s requires locator (or NOT_LOCATED)" % (where, tag))
            elif locator.upper() == "NOT_LOCATED" and conf == "H":
                res.error("%s: NOT_LOCATED cannot carry confidence H" % where)
        if has_source or tier:
            if tier not in [str(n) for n in range(1, 8)]:
                res.error("%s: source_tier must be 1-7" % where)
            if prim not in ("Y", "N"):
                res.error("%s: primary must be Y/N" % where)
            elif tier in "1234" and tier and prim != "Y":
                res.warn("%s: tier %s source normally primary=Y" % (where, tier))
        if tag == "FACT" and tier in ("6", "7") and not (r.get("corroborated_by") or "").strip():
            res.warn("%s: FACT supported only by tier %s source" % (where, tier))
        if tag == "CALCULATION" and not (r.get("formula_or_inputs") or "").strip():
            res.error("%s: CALCULATION requires formula_or_inputs" % where)
        if tag == "CALCULATION" and not CLAIM_ID_RE.search(r.get("formula_or_inputs") or ""):
            res.warn("%s: CALCULATION inputs do not reference claim IDs" % where)
        if tag == "ESTIMATE" and not ((r.get("formula_or_inputs") or "").strip() or (r.get("notes") or "").strip()):
            res.error("%s: ESTIMATE requires its basis in formula_or_inputs or notes" % where)
    if not rows:
        res.warn("Ledger has no claims")
    return res, ids


def run_ledger_paths(run_dir: Path) -> List[Path]:
    paths = sorted((run_dir / "specialists").glob("*_ledger.csv"))
    cio = run_dir / "cio" / "cio_ledger.csv"
    if cio.exists():
        paths.append(cio)
    paths += sorted((run_dir / "audit").glob("*_ledger.csv"))
    return paths


def prefix_for_ledger(path: Path) -> Optional[str]:
    if path.parent.name == "cio":
        return CIO_PREFIX
    if path.parent.name == "audit":
        return AUDITOR_PREFIX
    stem = path.name[: -len("_ledger.csv")]
    stem = re.sub(r"_followup_\d+$", "", stem)
    return SPECIALISTS.get(stem)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

SPECIALIST_FM = ("specialist", "company", "ticker", "exchange", "run_id", "research_cutoff",
                 "report_status", "model_requested", "independence_attestation")
FINAL_FM = ("company", "ticker", "exchange", "run_id", "as_of_date", "research_cutoff", "price", "price_timestamp",
            "currency", "primary_layer", "secondary_layers", "business_quality",
            "business_quality_confidence", "investment_attractiveness",
            "investment_attractiveness_confidence", "verdict", "valuation_status", "assessment_status",
            "qc_status", "model_effective")


def validate_specialist_report(path: Path, ledger_ids: Optional[Set[str]] = None,
                               expected: Optional[dict] = None, followup: bool = False, legacy: bool = False,
                               version: Optional[tuple] = None, segment: str = "") -> Result:
    """Validate one specialist report against the contract of `version` (the run's methodology version;
    default: current). `segment` is the run's listing segment; `sme` requires the SME Enhanced Scrutiny section."""
    v = effective_version(legacy, version)
    res = Result(str(path))
    if not path.exists():
        res.error("Report missing")
        return res
    text = path.read_text(encoding="utf-8")
    fm = parse_front_matter(text)
    if not fm:
        res.error("Missing YAML front matter")
    for k in SPECIALIST_FM:
        if not fm.get(k):
            res.error("Front matter missing '%s'" % k)
    name = fm.get("specialist", "")
    if name and name not in SPECIALISTS:
        res.error("Unknown specialist %r" % name)
    if expected:
        for k in ("ticker", "run_id"):
            if expected.get(k) and fm.get(k) and fm[k] != expected[k]:
                res.error("Front matter %s=%r does not match run (%r)" % (k, fm[k], expected[k]))
    if fm.get("report_status") == "partial":
        res.warn("Report status is partial")
    if not followup:
        tail = [t for t in common_tail() if not (v < V23 and t == CHECKLIST_SECTION)]
        required = common_head() + (agent_sections(name, v) if name in SPECIALISTS else []) + tail
        if segment.lower() == "sme" and v >= V24:
            required = required + [SME_SECTION]
        check_sections(text, required, res)
        check_crosswalk(text, res)
        check_coverage(name, text, fm, res, v)
        if name in SPECIALISTS and v >= V23:
            check_method_checklist(name, text, res)
    allowed = {SPECIALISTS[name], CIO_PREFIX} if (name in SPECIALISTS and not followup) else None
    if ledger_ids is not None:
        # Specialists may cite the CIO's preflight claims (e.g. price CIO-C001).
        cio_ledger = path.parent.parent / "cio" / "cio_ledger.csv"
        if cio_ledger.exists():
            ledger_ids = set(ledger_ids) | validate_ledger(cio_ledger)[1]
    check_tags(text, res, ledger_ids, allowed)
    check_layer_names(text, res)
    check_flagged_phrases(text, res, strict=False)
    if v >= V31:
        check_no_coverage_claims(text, res)
    reg = section(text, "Source Register")
    if reg is not None and "http" not in reg and not re.search(r"\b(BSE|NSE|ISIN|CIN|filing)\b|FilingForge:", reg, re.I):
        res.warn("Source Register contains no URLs or filing identifiers")
    return res


def check_no_coverage_claims(text: str, res: Result) -> None:
    """Methodology 3.1.0: a report states what it used; what was read is the reading ledger's record
    (corpus/reading/COVERAGE.md), generated by script. Phrases like 'read in full' are rejected."""
    for n, line in enumerate(text.splitlines(), 1):
        m = OVERCLAIM_RE.search(line)
        if m:
            res.error("line %d: '%s' — do not state your own reading coverage; cite corpus/reading/COVERAGE.md "
                      "(the reading ledger) and state the periods and series you used" % (n, m.group(0)))


def coverage_block_of(text: str) -> Optional[str]:
    m = re.search(r"<!--\s*%s:BEGIN\s*-->(.*?)<!--\s*%s:END\s*-->" % (COVERAGE_BLOCK, COVERAGE_BLOCK), text, re.S)
    return m.group(1).strip() if m else None


def check_reading_coverage_block(text: str, run_dir: Path, res: Result) -> None:
    """The final report must carry corpus/reading/COVERAGE.md unchanged between the READING_COVERAGE markers."""
    cov = run_dir / READING_COVERAGE
    block = coverage_block_of(text)
    if block is None:
        res.error("Missing the reading-coverage block (<!-- %s:BEGIN --> ... <!-- %s:END -->) in the final report"
                  % (COVERAGE_BLOCK, COVERAGE_BLOCK))
    elif not cov.exists():
        res.error("%s missing: run reading.py status" % READING_COVERAGE)
    elif re.sub(r"\s+", " ", block) != re.sub(r"\s+", " ", cov.read_text(encoding="utf-8").strip()):
        res.error("The reading-coverage block differs from %s: paste it unchanged (re-run reading.py status first)" % READING_COVERAGE)


# (specialist, section(s), counter, depth key, unit label, error-or-warning, contract version it applies from)
_COVERAGE_RULES = (
    ("financials", ("Historical Financial Summary",), fiscal_years, "financials.fiscal_years", "fiscal years", True, (0,)),
    ("concalls", ("Coverage of Communications", "Promise-to-Delivery Database"), quarters, "concalls.quarters", "quarters", True, (0,)),
    ("valuation", ("Historical and Peer Valuation", "Price History, Drawdowns and TSR"), any_years, "valuation.history_years", "years", True, (0,)),
    ("management", ("Ownership, Pledging and Insider Activity",), quarters, "management.shareholding_quarters", "quarters", False, (0,)),
    ("industry", ("Market Share and Company Position", "Market Size and Reachable Market"), any_years, "industry.history_years", "years", False, (0,)),
    ("filings", ("Filings Reviewed",), fiscal_years, "filings.annual_report_years", "annual-report fiscal years", True, V24),
    ("moat", ("Quantified Advantage Metrics",), any_years, "moat.history_years", "years", False, V24),
    ("special-situations", ("Corporate-Action History",), any_years, "special-situations.history_years", "years", False, V24),
    ("scuttlebutt", ("Independent Operating Data",), any_years, "scuttlebutt.history_years", "years", False, V24),
)


def check_coverage(name: str, text: str, fm: Dict[str, str], res: Result, version: Optional[tuple] = None) -> None:
    """Historical Depth Standard (methodology/RESEARCH_PLAYBOOK.md §2), as it applied to the run's version."""
    mins = depth_minimums()
    v = version or current_version()
    exception = (fm.get("coverage_exception") or "").strip()
    for agent, sections, counter, key, label, hard, since in _COVERAGE_RULES:
        if agent != name or key not in mins or v < since:
            continue
        body = "\n".join(section(text, s) or "" for s in sections)
        n = len(counter(body))
        if n >= mins[key]:
            continue
        msg = "Historical depth: %d %s found in %s; standard requires %d" % (n, label, " / ".join(sections), mins[key])
        if exception:
            res.warn(msg + " (coverage_exception: %s)" % exception[:80])
        elif hard:
            res.error(msg + " (add coverage_exception to front matter if genuinely unavailable)")
        else:
            res.warn(msg)


def final_sections_for(version: tuple) -> List[str]:
    """The CIO final-report sections required for a run of this methodology version."""
    out = []
    for s in agent_sections("cio", version):
        if version < V23 and s in V23_FINAL_SECTIONS:
            continue
        if version < V24 and s in V24_FINAL_SECTIONS:
            continue
        out.append(s)
    return out


def validate_final_report(path: Path, scorecard: Optional[dict], ledger_ids: Optional[Set[str]], legacy: bool = False,
                          version: Optional[tuple] = None, segment: str = "") -> Result:
    res = Result(str(path))
    if not path.exists():
        res.error("Final report missing")
        return res
    text = path.read_text(encoding="utf-8")
    fm = parse_front_matter(text)
    for k in FINAL_FM:
        if not fm.get(k):
            res.error("Front matter missing '%s'" % k)
    v = effective_version(legacy, version)
    required = final_sections_for(v)
    if segment.lower() == "sme" and v >= V24:
        required = required + [SME_SECTION]
    check_sections(text, required, res)
    if v >= V31:
        check_reading_coverage_block(text, path.parent.parent, res)
    insufficient = fm.get("assessment_status") == "insufficient_evidence"
    layers = canonical_layers()
    body = section(text, FINAL_LAYER_SECTION) or ""
    blocks = {norm_layer(h): c for h, c in h3_blocks(body)}
    fits, confs = {}, {}
    for i, layer in enumerate(layers, 1):
        if layer not in blocks:
            res.error("%s missing exact heading '### %s'" % (FINAL_LAYER_SECTION, layer))
            continue
        block = blocks[layer]
        m = FIT_SCORE_RE.search(block)
        if m:
            fits["L%d" % i] = int(m.group(1))
        elif not insufficient:
            res.error("%s: missing 'Layer-fit score: NN/100'" % layer)
        c = FIT_CONF_RE.search(block)
        if c:
            confs["L%d" % i] = c.group(1)
        elif not insufficient:
            res.error("%s: missing 'Layer-fit confidence: High|Medium|Low'" % layer)
        for field in LAYER_BLOCK_FIELDS:
            if not re.search(r"\**%s\**\s*:" % re.escape(field), block, re.I):
                res.warn("%s: missing item '%s'" % (layer.split(" — ")[0], field))
    verdict_body = section(text, "Final Verdict") or ""
    for field in FINAL_VERDICT_FIELDS:
        if not re.search(r"\**%s\**\s*:" % re.escape(field), verdict_body, re.I):
            res.error("Final Verdict must state '%s:'" % field)
    if insufficient:
        for key in ("business_quality", "investment_attractiveness", "verdict"):
            if fm.get(key) and fm[key] != "not issued":
                res.error("Insufficient-evidence report must show %s: not issued" % key)
    else:
        if fm.get("verdict") and fm["verdict"] not in verdicts():
            res.error("Verdict %r not canonical" % fm["verdict"])
        if fm.get("valuation_status") and fm["valuation_status"] not in valuation_statuses():
            res.error("Valuation status %r not canonical" % fm["valuation_status"])
    pl = fm.get("primary_layer", "")
    if pl and pl != "None" and norm_layer(pl) not in layers:
        res.error("primary_layer %r is not a canonical layer name" % pl)
    if scorecard:
        def show(v):
            return "not issued" if v is None else str(v)
        pairs = [
            ("business_quality", show(scorecard.get("business_quality", {}).get("final"))),
            ("investment_attractiveness", show(scorecard.get("investment_attractiveness", {}).get("final"))),
            ("verdict", show(scorecard.get("verdict"))),
            ("assessment_status", scorecard.get("assessment_status")),
            ("qc_status", scorecard.get("qc_status")),
            ("run_id", scorecard.get("run_id")),
            ("ticker", scorecard.get("ticker")),
        ]
        if not insufficient:
            pairs.append(("valuation_status", scorecard.get("valuation_status")))
        for key, sv in pairs:
            if fm.get(key) is not None and sv is not None and str(fm.get(key)) != str(sv):
                res.error("Front matter %s=%r differs from scorecard (%r)" % (key, fm.get(key), sv))
        if pl and norm_layer(pl) != norm_layer(str(scorecard.get("primary_layer"))):
            res.error("primary_layer differs from scorecard")
        for k, v in fits.items():
            sc = scorecard.get("layer_fit", {}).get(k, {}).get("score")
            if sc is not None and int(sc) != v:
                res.error("%s fit %d in report vs %s in scorecard" % (k, v, sc))
        for k, v in confs.items():
            sc = scorecard.get("layer_fit", {}).get(k, {}).get("confidence")
            if sc is not None and sc != v:
                res.error("%s fit confidence %s in report vs %s in scorecard" % (k, v, sc))
    check_tags(text, res, ledger_ids, None)
    check_layer_names(text, res)
    check_flagged_phrases(text, res, strict=True)
    return res


# ---------------------------------------------------------------------------
# Independent audit (methodology 2.4.0; contract in .claude/agents/auditor.md)
# ---------------------------------------------------------------------------

AUDIT_FM = ("auditor", "company", "ticker", "run_id", "audit_opinion", "independence_attestation")
AUDIT_OPINIONS = ("Clean", "Clean with minor findings", "Qualified", "Adverse")
AUDIT_SEVERITIES = ("Critical", "Major", "Minor")
AUDIT_RESOLUTIONS = ("Fixed", "Rebutted", "Accepted limitation")
FINDING_ROW_RE = re.compile(r"^\|\s*(AUD-F\d{2,})\s*\|\s*([A-Za-z]+)\s*\|", re.M)


def audit_findings(text: str) -> List[Tuple[str, str]]:
    """(finding id, severity) rows of the Findings Register table."""
    body = section(text, "Findings Register") or ""
    return [(m.group(1), m.group(2).strip().title()) for m in FINDING_ROW_RE.finditer(body)]


def validate_audit_report(path: Path, ledger_ids: Optional[Set[str]] = None,
                          expected: Optional[dict] = None, version: Optional[tuple] = None) -> Tuple[Result, List[Tuple[str, str]]]:
    """`version` = the run's methodology version (sections marked `(since X)` apply from X); None = the current one."""
    res = Result(str(path))
    if not path.exists():
        res.error("Audit report missing: the CIO must invoke the auditor agent before QC (cio.md Stage 4)")
        return res, []
    text = path.read_text(encoding="utf-8")
    fm = parse_front_matter(text)
    for k in AUDIT_FM:
        if not fm.get(k):
            res.error("Front matter missing '%s'" % k)
    if expected:
        for k in ("ticker", "run_id"):
            if expected.get(k) and fm.get(k) and fm[k] != expected[k]:
                res.error("Front matter %s=%r does not match run (%r)" % (k, fm[k], expected[k]))
    opinion = fm.get("audit_opinion", "")
    if opinion and opinion not in AUDIT_OPINIONS:
        res.error("audit_opinion %r is not one of %s" % (opinion, ", ".join(AUDIT_OPINIONS)))
    check_sections(text, agent_sections(AUDITOR, version or current_version()), res)
    findings = audit_findings(text)
    for fid, sev in findings:
        if sev not in AUDIT_SEVERITIES:
            res.error("%s: severity %r is not Critical | Major | Minor" % (fid, sev))
    n = {s: sum(1 for _, x in findings if x == s) for s in AUDIT_SEVERITIES}
    if n["Critical"] and opinion != "Adverse":
        res.error("%d Critical finding(s) require the opinion 'Adverse' (resolutions are recorded by the CIO)" % n["Critical"])
    elif n["Major"] and opinion in ("Clean", "Clean with minor findings"):
        res.error("%d Major finding(s) are inconsistent with the opinion %r" % (n["Major"], opinion))
    elif n["Minor"] and opinion == "Clean":
        res.warn("Minor findings with a 'Clean' opinion: use 'Clean with minor findings'")
    if not findings and "no findings" not in (section(text, "Findings Register") or "").lower():
        res.warn("Findings Register has no AUD-F## rows and does not state 'No findings'")
    check_tags(text, res, ledger_ids, {AUDITOR_PREFIX, CIO_PREFIX} | set(SPECIALISTS.values()))
    check_layer_names(text, res)
    return res, findings


def check_audit_resolutions(run_dir: Path, findings: List[Tuple[str, str]], res: Result) -> None:
    """Every Critical/Major finding is resolved in cio/audit_resolutions.md; a Critical finding cannot be accepted as a
    limitation and its fix must be confirmed 'Closed' by a re-audit (audit/audit_followup_<n>.md)."""
    path = run_dir / "cio" / "audit_resolutions.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(r"AUD-F\d{2,}", cells[0]):
            rows[cells[0]] = cells
    followups = "\n".join(p.read_text(encoding="utf-8") for p in sorted((run_dir / "audit").glob("audit_followup_*.md")))
    for fid, sev in findings:
        row = rows.get(fid)
        if row is None:
            (res.error if sev in ("Critical", "Major") else res.warn)(
                "%s (%s) has no row in cio/audit_resolutions.md" % (fid, sev))
            continue
        resolution = next((r for r in AUDIT_RESOLUTIONS if any(c.lower() == r.lower() for c in row[1:4])), None)
        if resolution is None:
            res.error("%s: resolution must be one of %s" % (fid, ", ".join(AUDIT_RESOLUTIONS)))
        elif sev == "Critical" and resolution == "Accepted limitation":
            res.error("%s is Critical: it must be fixed or rebutted with evidence, not accepted as a limitation" % fid)
        if sev == "Critical" and not re.search(r"%s[^\n]*\bClosed\b" % re.escape(fid), followups):
            res.error("%s is Critical: a re-audit (audit/audit_followup_<n>.md) must mark it Closed" % fid)


# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------

NOTCH = {"STRONG AVOID": 0, "AVOID": 1, "HOLD / NEUTRAL": 2, "WATCHLIST — WAIT FOR BETTER PRICE": 2,
         "BUY": 3, "SPECULATIVE BUY": 3, "STRONG BUY": 4}


def mapped_verdict(bq: int, ia: int, ia_conf: str, gates_hit: List[str], primary_layer: str) -> str:
    l4 = norm_layer(primary_layer or "") == canonical_layers()[3]
    if "G1" in gates_hit or "G3" in gates_hit or ia < 25:
        return "STRONG AVOID"
    if ia < 45:
        return "AVOID"
    if ia < 65:
        return "WATCHLIST — WAIT FOR BETTER PRICE" if bq >= 70 else "HOLD / NEUTRAL"
    v = "STRONG BUY" if (ia >= 80 and ia_conf in ("High", "Medium")) else "BUY"
    return "SPECULATIVE BUY" if l4 else v


# ---------------------------------------------------------------------------
# Decision engine, methodology 3.0.0 (SCORING.md §§0, 1, 3a-3c, 5)
# ---------------------------------------------------------------------------

V3 = (3, 0, 0)
BUY_CLASS = ("BUY", "STRONG BUY", "SPECULATIVE BUY")


def layer_code(name: Optional[str]) -> str:
    """'Layer 2 — High-Growth Business' -> 'L2'; anything else -> 'None'."""
    layers = canonical_layers()
    n = norm_layer(name or "")
    return "L%d" % (layers.index(n) + 1) if n in layers else "None"


def weight_profiles() -> Dict[str, Dict[str, float]]:
    rows = [r for r in _parse_table_block(SCORING, "WEIGHT_PROFILES") if r and r[0].lower() != "dimension"]
    cols = ["Base", "L1", "L2", "L3", "L4"]
    out: Dict[str, Dict[str, float]] = {c: {} for c in cols}
    for r in rows:
        for c, v in zip(cols, r[1:6]):
            out[c][r[0]] = float(v)
    return out


def confidence_shrink() -> Dict[str, float]:
    out = {}
    for line in read_block(SCORING, "CONFIDENCE_SHRINK"):
        k, _, v = line.partition(":")
        out[k.strip()] = float(v)
    return out


def dimension_owners() -> Dict[str, List[str]]:
    rows = [r for r in _parse_table_block(SCORING, "DIMENSION_OWNERS") if r and r[0].lower() != "dimension"]
    return {r[0]: [x.strip() for x in r[1].split(",") if x.strip()] for r in rows}


MUST_PASS_RE = re.compile(r"^(BQ\d|IA\d)\s*(>=|>|<=|<)\s*(\d+(?:\.\d+)?)$")


def must_pass_rules() -> List[dict]:
    out = []
    for r in _parse_table_block(SCORING, "MUST_PASS"):
        if not r or r[0].lower().startswith("applies"):
            continue
        m = MUST_PASS_RE.match(r[1].strip())
        if not m:
            raise ValueError("MUST_PASS test %r not of the form 'BQ1 >= 60'" % r[1])
        out.append({"applies": [x.strip() for x in r[0].split(",")], "test": r[1].strip(), "dimension": m.group(1),
                    "op": m.group(2), "threshold": float(m.group(3)), "kind": r[2].strip().lower(), "why": r[3] if len(r) > 3 else ""})
    return out


def required_mos_table() -> Dict[str, Dict[str, Optional[float]]]:
    out = {}
    for r in _parse_table_block(SCORING, "REQUIRED_MOS"):
        if not r or r[0].lower() == "layer":
            continue
        out[r[0]] = {lvl: (None if v.strip().lower() == "none" else float(v)) for lvl, v in zip(("High", "Medium", "Low"), r[1:4])}
    return out


def conviction_rules() -> dict:
    out = {}
    for line in read_block(SCORING, "CONVICTION"):
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if "=" in v:
            pairs = [p.strip().split("=") for p in v.split(",")]
            out[k] = [(a.strip(), float(b)) for a, b in pairs]
        else:
            out[k] = float(v)
    return out


def layer_codes_of(sc: dict) -> List[str]:
    codes = [layer_code(sc.get("primary_layer"))]
    if sc.get("hybrid") and sc.get("secondary_layers"):
        sec = layer_code(sc["secondary_layers"][0])
        if sec != "None" and sec not in codes:
            codes.append(sec)
    return codes


def profile_weights(codes: List[str]) -> Tuple[str, Dict[str, float]]:
    prof = weight_profiles()
    keys = [c if c in prof else "Base" for c in codes] or ["Base"]
    keys = ["Base" if k == "None" else k for k in keys]
    dims = prof["Base"].keys()
    weights = {d: sum(prof[k][d] for k in keys) / float(len(keys)) for d in dims}
    return "+".join(keys), weights


def effective_score(score: float, confidence: str, shrink: Optional[Dict[str, float]] = None) -> float:
    k = (shrink or confidence_shrink()).get(confidence, 0.0)
    return float(score) if score <= 50 else 50.0 + (float(score) - 50.0) * k


def required_mos(codes: List[str], ia_confidence: str) -> Tuple[bool, Optional[float]]:
    """(buy permitted at this confidence, required margin of safety). A hybrid takes the stricter layer."""
    table = required_mos_table()
    vals = []
    for c in codes or ["None"]:
        row = table.get(c) or table.get("None")
        vals.append(row.get(ia_confidence))
    if any(v is None for v in vals):
        return False, None
    return True, max(vals)


def conviction(edge: Optional[float], asymmetry: Optional[float], ia_confidence: str, robust: bool) -> Tuple[str, int]:
    rules = conviction_rules()
    pts = 0
    if edge is not None:
        e_pp = edge * 100.0
        for thr, p in sorted(((float(a), b) for a, b in rules["edge_pp"]), reverse=True):
            if e_pp >= thr:
                pts += int(p)
                break
    if asymmetry is not None:
        for thr, p in sorted(((float(a), b) for a, b in rules["asymmetry"]), reverse=True):
            if asymmetry >= thr:
                pts += int(p)
                break
    pts += int(dict(rules["confidence"]).get(ia_confidence, 0))
    pts += int(rules["robust"]) if robust else 0
    level = "High" if pts >= rules["high_at"] else ("Medium" if pts >= rules["medium_at"] else "Low")
    return level, pts


def _cmp(v: float, op: str, t: float) -> bool:
    return {">=": v >= t, ">": v > t, "<=": v <= t, "<": v < t}[op]


def evaluate_v3(sc: dict, ia_override: Optional[Dict[str, int]] = None, metrics_override: Optional[dict] = None) -> dict:
    """Recompute the 3.0.0 decision from a scorecard's judgments. `ia_override` replaces IA dimension scores (the
    price ladder's IA1/IA2/IA4 at another price); `metrics_override` replaces price_metrics at that price."""
    codes = layer_codes_of(sc)
    label, weights = profile_weights(codes)
    _, base_weights = profile_weights(["Base"])
    shrink = confidence_shrink()
    eff: Dict[str, float] = {}
    out = {"weight_profile": label, "weights": weights, "effective": eff}
    implied = set()
    cls = sc.get("classifications") or {}
    for (field, value), gate in _CLASSIFICATION_GATES.items():
        if str(cls.get(field, "")).strip().lower() == value:
            implied.add(gate)
    gates_all = set()
    for kind, key in (("BQ", "business_quality"), ("IA", "investment_attractiveness")):
        block = sc.get(key) or {}
        dims = {d.get("id"): d for d in block.get("dimensions", [])}
        raw = base = 0.0
        for did in [d for d in weights if d.startswith(kind)]:
            d = dims.get(did) or {}
            score = (ia_override or {}).get(did, d.get("score", 0)) if kind == "IA" else d.get("score", 0)
            e = effective_score(float(score), d.get("confidence", "Low"), shrink)
            eff[did] = e
            raw += e * weights[did] / 100.0
            base += e * base_weights[did] / 100.0
        table = gates(kind)
        hit = sorted((set(block.get("gates_triggered") or []) | implied) & set(table))
        caps = [table[g][1] for g in hit if table[g][1] is not None]
        out[kind] = {"weighted_raw": round(raw, 2), "base_profile_raw": round(base, 2), "gates": hit,
                     "final": min([round_half_up(raw)] + caps)}
        gates_all |= set(hit)
    m = dict(sc.get("price_metrics") or {})
    m.update(metrics_override or {})
    ia_conf = (sc.get("investment_attractiveness") or {}).get("confidence", "Low")
    tests = []
    for rule in must_pass_rules():
        if "ALL" not in rule["applies"] and not set(rule["applies"]) & set(codes):
            continue
        v = eff.get(rule["dimension"], 0.0)
        tests.append({"test": rule["test"], "kind": rule["kind"], "effective": round(v, 2),
                      "passed": _cmp(v, rule["op"], rule["threshold"]), "why": rule["why"]})
    permitted, req = required_mos(codes, ia_conf)
    mos = m.get("margin_of_safety")
    e_irr, hurdle = m.get("expected_irr"), m.get("hurdle_rate", sc.get("hurdle_rate"))
    edge = (e_irr - hurdle) if (e_irr is not None and hurdle is not None) else None
    conv, pts = conviction(edge, m.get("asymmetry_ratio"), ia_conf, bool(m.get("robust")))
    bq, ia = out["BQ"]["final"], out["IA"]["final"]
    l4 = codes[0] == "L4"
    biz_fail = [t["test"] for t in tests if t["kind"] == "business" and not t["passed"]]
    price_fail = [t["test"] for t in tests if t["kind"] == "price" and not t["passed"]]
    if "G1" in gates_all or "G3" in gates_all or ia < 25:
        verdict, why = "STRONG AVOID", "gate G1/G3 or IA < 25"
    elif ia < 45:
        verdict, why = "AVOID", "IA 25-44"
    elif ia < 65:
        verdict, why = ("WATCHLIST — WAIT FOR BETTER PRICE", "IA 45-64, BQ >= 70") if bq >= 70 else ("HOLD / NEUTRAL", "IA 45-64")
    elif biz_fail:
        verdict, why = "HOLD / NEUTRAL", "business must-pass failed: %s" % ", ".join(biz_fail)
    elif price_fail:
        verdict, why = "WATCHLIST — WAIT FOR BETTER PRICE", "price must-pass failed: %s" % ", ".join(price_fail)
    elif not permitted:
        verdict, why = "WATCHLIST — WAIT FOR BETTER PRICE", "no buy at %s IA confidence for %s" % (ia_conf, "+".join(codes))
    elif mos is None or mos < req - 1e-9:
        verdict, why = "WATCHLIST — WAIT FOR BETTER PRICE", "margin of safety %s below the required %.0f %%" % (
            "n/a" if mos is None else "%.1f %%" % (mos * 100), req * 100)
    elif l4:
        verdict, why = "SPECULATIVE BUY", "Layer 4 buy"
    elif ia >= 80 and ia_conf in ("High", "Medium") and conv == "High":
        verdict, why = "STRONG BUY", "IA >= 80, confidence %s, conviction High" % ia_conf
    else:
        verdict, why = "BUY", "IA >= 65 and every buy condition met"
    out.update({"layer_codes": codes, "gates": sorted(gates_all), "must_pass": tests,
                "buy_permitted_at_confidence": permitted, "required_margin_of_safety": req,
                "margin_of_safety": mos, "edge": edge, "conviction": conv, "conviction_points": pts,
                "mapped_verdict": verdict, "verdict_path": why})
    return out


def _date(s) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


PREDICTION_COMPARATORS = (">=", "<=", ">", "<", "between", "event")
PREDICTION_SOURCES = ("price", "results_xbrl", "filing", "other")


def _validate_prediction_structure(p: dict, pid, res: Result) -> None:
    """A prediction a script (or the CIO, with evidence) can resolve as hit or miss (SCORING.md §10): what is
    measured, the comparator and threshold, its unit and period, and where the outcome will be read."""
    comp = p.get("comparator")
    if comp not in PREDICTION_COMPARATORS:
        res.error("prediction %s: comparator must be one of %s" % (pid, ", ".join(PREDICTION_COMPARATORS)))
        return
    if p.get("resolution_source") not in PREDICTION_SOURCES:
        res.error("prediction %s: resolution_source must be one of %s" % (pid, ", ".join(PREDICTION_SOURCES)))
    if comp == "event":
        if not (p.get("resolution_rule") or "").strip():
            res.error("prediction %s: an event prediction needs its resolution_rule (what counts as it happening)" % pid)
        return
    th = p.get("threshold")
    if comp == "between":
        if not (isinstance(th, list) and len(th) == 2 and all(isinstance(x, (int, float)) for x in th) and th[0] < th[1]):
            res.error("prediction %s: a between threshold is [low, high]" % pid)
    elif not isinstance(th, (int, float)) or isinstance(th, bool):
        res.error("prediction %s: threshold must be a number" % pid)
    for key in ("metric", "unit", "period"):
        if not str(p.get(key) or "").strip():
            res.error("prediction %s: %s missing" % (pid, key))


def _validate_decision_outputs(sc: dict, res: Result, structured: bool = True) -> None:
    """Coverage, predictions, decision triggers, position risk, review date (SCORING.md §§9-10). `structured`: the
    resolvable form of predictions and the review-date rule (runs from methodology 3.1.0)."""
    asof = _date(sc.get("as_of_date") or sc.get("research_cutoff"))
    mins = depth_minimums()
    cov = sc.get("coverage")
    if not isinstance(cov, dict):
        res.error("coverage block missing (financial_years, transcript_quarters, valuation_history_years)")
    else:
        for key, depth_key in (("financial_years", "financials.fiscal_years"), ("transcript_quarters", "concalls.quarters"),
                               ("valuation_history_years", "valuation.history_years")):
            v = cov.get(key)
            if not isinstance(v, int) or v < 0:
                res.error("coverage.%s must be a non-negative integer" % key)
            elif v < mins.get(depth_key, 0) and not (cov.get("exception") or "").strip():
                res.error("coverage.%s=%d below the depth standard (%d) without coverage.exception" % (key, v, mins[depth_key]))
    preds = sc.get("predictions")
    if not isinstance(preds, list) or not 3 <= len(preds) <= 7:
        res.error("predictions must list 3-7 falsifiable predictions")
    else:
        ids = set()
        for p in preds:
            pid = p.get("id")
            if not pid or pid in ids:
                res.error("prediction ids must be unique and non-empty")
            ids.add(pid)
            if not (p.get("statement") or "").strip():
                res.error("prediction %s: statement missing" % pid)
            prob = p.get("probability")
            if not isinstance(prob, (int, float)) or not 0.05 <= prob <= 0.95:
                res.error("prediction %s: probability must be between 0.05 and 0.95" % pid)
            due = _date(p.get("due"))
            if due is None:
                res.error("prediction %s: due must be YYYY-MM-DD" % pid)
            elif asof and due <= asof:
                res.error("prediction %s: due date must be after the as-of date" % pid)
            if structured:
                _validate_prediction_structure(p, pid, res)
    trig = sc.get("decision_triggers")
    if not isinstance(trig, dict):
        res.error("decision_triggers block missing")
    else:
        for key in ("buy_below", "strong_buy_below", "avoid_above"):
            if key not in trig or not (trig[key] is None or isinstance(trig[key], (int, float))):
                res.error("decision_triggers.%s must be a number or null" % key)
        if not (trig.get("method") or "").strip():
            res.error("decision_triggers.method missing")
    pr = sc.get("position_risk")
    if not isinstance(pr, dict):
        res.error("position_risk block missing")
    else:
        if pr.get("p_permanent_loss_band") not in PROBABILITY_BANDS:
            res.error("position_risk.p_permanent_loss_band must be one of %s" % (PROBABILITY_BANDS,))
        if not isinstance(pr.get("factor_exposures"), list) or not pr.get("factor_exposures"):
            res.error("position_risk.factor_exposures must list at least one driver")
        for key in ("bear_case_loss_pct", "days_to_exit_reference_position", "sizing_ceiling_pct"):
            if key not in pr or not (pr[key] is None or isinstance(pr[key], (int, float))):
                res.error("position_risk.%s must be a number or null" % key)
        if not (pr.get("sizing_basis") or "").strip():
            res.error("position_risk.sizing_basis missing")
    review = _date(sc.get("next_review_due"))
    if review is None:
        res.error("next_review_due must be YYYY-MM-DD")
    elif asof and not asof < review <= asof + dt.timedelta(days=366):
        res.error("next_review_due must fall within 12 months after the as-of date")
    elif structured and isinstance(preds, list) and preds:
        dues = [d for d in (_date(p.get("due")) for p in preds) if d]
        if dues and min(dues) > review:
            res.error("at least one prediction must fall due on or before next_review_due (%s): the review resolves "
                      "it, so the outcome loop learns within the review cycle" % review)


_CLASSIFICATION_GATES = {
    ("reporting_reliability", "highly concerning"): "G1",
    ("reporting_reliability", "material concerns"): "G2",
    ("governance", "compromised"): "G3",
}


def validate_scorecard(path: Path, version: Optional[tuple] = None) -> Result:
    """`version`: the run's methodology version (rules added later are skipped for older runs); None = current."""
    res = Result(str(path))
    try:
        sc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        res.error("Unreadable JSON: %s" % exc)
        return res
    for key in ("run_id", "ticker", "price", "assessment_status", "layer_fit", "primary_layer",
                "business_quality", "investment_attractiveness", "scenarios", "verdict",
                "valuation_status", "qc_status", "classifications", "model"):
        if key not in sc:
            res.error("Missing key '%s'" % key)
    if res.errors:
        return res
    if sc["assessment_status"] not in ("complete", "insufficient_evidence"):
        res.error("assessment_status must be complete or insufficient_evidence")
        return res
    if sc["qc_status"] not in ("PASS", "FAIL", "PENDING"):
        res.error("qc_status must be PASS/FAIL/PENDING")
    if sc["assessment_status"] == "complete":
        own = version or version_tuple(sc.get("methodology_version") or "0.0.0")
        _validate_decision_outputs(sc, res, structured=own >= V31)
    if sc["assessment_status"] == "insufficient_evidence":
        if not (sc.get("insufficient_evidence_reason") or "").strip():
            res.error("insufficient_evidence_reason required")
        for key in ("business_quality", "investment_attractiveness"):
            if (sc.get(key) or {}).get("final") is not None:
                res.error("%s.final must be null when evidence is insufficient (no manufactured scores)" % key)
        if sc.get("verdict") is not None:
            res.error("verdict must be null when evidence is insufficient")
        return res
    layers = canonical_layers()
    fits = {}
    for i in range(1, 5):
        f = sc["layer_fit"].get("L%d" % i, {})
        s = f.get("score")
        if not isinstance(s, int) or not 0 <= s <= 100:
            res.error("layer_fit.L%d.score must be an integer 0-100" % i)
        else:
            fits[i] = s
        if not (f.get("rationale") or "").strip():
            res.error("layer_fit.L%d.rationale missing" % i)
        if f.get("confidence") not in ("High", "Medium", "Low"):
            res.error("layer_fit.L%d.confidence must be High/Medium/Low" % i)
    pl = sc.get("primary_layer") or "None"
    if pl != "None":
        if norm_layer(pl) not in layers:
            res.error("primary_layer %r not canonical" % pl)
        elif fits.get(layers.index(norm_layer(pl)) + 1, 0) < 41:
            res.error("primary layer must have fit >= 41")
    elif fits and max(fits.values()) >= 61:
        res.warn("primary_layer None although a layer has strong fit")
    for s in sc.get("secondary_layers") or []:
        if norm_layer(s) not in layers:
            res.error("secondary layer %r not canonical" % s)
    lpa = sc.get("layer_price_assessments", {})
    for i, f in fits.items():
        if f >= 41 and not (lpa.get("L%d" % i) or {}).get("assessment"):
            res.error("L%d fit %d >= 41 requires layer_price_assessments.L%d.assessment" % (i, f, i))

    implied = set()
    cls = sc.get("classifications") or {}
    for (field, value), gate in _CLASSIFICATION_GATES.items():
        if str(cls.get(field, "")).strip().lower() == value:
            implied.add(gate)

    if version_tuple(sc.get("methodology_version")) >= V3:
        _validate_v3(sc, implied, res)
        _validate_scenarios_and_vocab(sc, res)
        return res

    finals = {}
    for kind, key in (("BQ", "business_quality"), ("IA", "investment_attractiveness")):
        block = sc[key]
        weights = dimension_weights(kind)
        if sum(w for _, _, w in weights) != 100:
            res.error("%s weights in SCORING.md do not sum to 100" % kind)
        dims = {d.get("id"): d for d in block.get("dimensions", [])}
        raw = 0.0
        for did, name, w in weights:
            d = dims.get(did)
            if not d:
                res.error("%s missing dimension %s (%s)" % (key, did, name))
                continue
            s = d.get("score")
            if not isinstance(s, int) or not 0 <= s <= 100:
                res.error("%s.%s score must be integer 0-100" % (key, did))
                continue
            if not (d.get("rationale") or "").strip():
                res.error("%s.%s rationale missing" % (key, did))
            if not d.get("claim_ids"):
                res.warn("%s.%s cites no claim IDs" % (key, did))
            raw += s * w / 100.0
        extra = set(dims) - {d for d, _, _ in weights}
        if extra:
            res.error("%s has unknown dimensions %s" % (key, sorted(extra)))
        if abs(raw - float(block.get("weighted_raw", -1))) > 0.51:
            res.error("%s weighted_raw %.2f but dimensions compute to %.2f" % (key, block.get("weighted_raw", -1), raw))
        hit = set(block.get("gates_triggered") or [])
        gate_table = gates(kind)
        for g in implied & set(gate_table):
            if g not in hit:
                res.error("%s: classification implies gate %s but gates_triggered omits it" % (key, g))
        unknown = hit - set(gate_table)
        if unknown:
            res.error("%s: unknown gates %s" % (key, sorted(unknown)))
        caps = [gate_table[g][1] for g in hit if g in gate_table and gate_table[g][1] is not None]
        expected_final = min([round_half_up(raw)] + caps)
        final = block.get("final")
        if final != expected_final:
            res.error("%s final %r but rounded weighted score with gates = %d" % (key, final, expected_final))
        if block.get("confidence") not in ("High", "Medium", "Low"):
            res.error("%s confidence must be High/Medium/Low" % key)
        if kind == "IA" and "G6" in hit and block.get("confidence") != "Low":
            res.error("Gate G6 requires IA confidence Low")
        for f in ("band", "prevents_higher", "could_lower", "evidence_to_change"):
            if block.get(f) in (None, ""):
                res.error("%s.%s missing" % (key, f))
        finals[kind] = final if isinstance(final, int) else expected_final

    _validate_scenarios_and_vocab(sc, res)
    all_hits = set(sc["business_quality"].get("gates_triggered") or []) | set(sc["investment_attractiveness"].get("gates_triggered") or [])
    if "BQ" in finals and "IA" in finals:
        mv = mapped_verdict(finals["BQ"], finals["IA"], sc["investment_attractiveness"].get("confidence", ""),
                            sorted(all_hits), pl)
        _check_verdict(sc, mv, res)
    return res


def _validate_scenarios_and_vocab(sc: dict, res: Result) -> None:
    scen = sc["scenarios"]
    probs = []
    for name in ("bear", "base", "bull"):
        s = scen.get(name)
        if not s:
            res.error("scenarios.%s missing" % name)
            continue
        probs.append(float(s.get("probability", 0)))
        rng = s.get("value_per_share_range")
        if not (isinstance(rng, list) and len(rng) == 2 and rng[0] <= rng[1]):
            res.error("scenarios.%s.value_per_share_range must be [low, high]" % name)
    if probs and abs(sum(probs) - 1.0) > 0.011:
        res.error("Scenario probabilities sum to %.3f, not 1" % sum(probs))

    if sc["verdict"] not in verdicts():
        res.error("Verdict %r not canonical" % sc["verdict"])
    if sc["valuation_status"] not in valuation_statuses():
        res.error("Valuation status %r not canonical" % sc["valuation_status"])


def _check_verdict(sc: dict, mv: str, res: Result) -> None:
    if sc.get("mapped_verdict") and sc["mapped_verdict"] != mv:
        res.error("mapped_verdict %r but methodology maps to %r" % (sc["mapped_verdict"], mv))
    if sc["verdict"] in NOTCH and sc["verdict"] != mv:
        gap = abs(NOTCH[sc["verdict"]] - NOTCH[mv])
        if not (sc.get("override_reason") or "").strip():
            res.error("Verdict %r differs from mapped %r without override_reason" % (sc["verdict"], mv))
        elif gap > 1:
            res.error("Override moves verdict %d notches (max 1)" % gap)
        elif gap == 0:
            res.warn("Verdict swapped within the same notch; check override_reason")


DRIVER_KEYS = ("driver", "market_implied", "our_view", "claim_ids", "confidence", "value_at_stake", "signpost")


def _validate_v3(sc: dict, implied: set, res: Result) -> None:
    """3.0.0 scorecards: per-dimension confidence, recomputed decision, price metrics, decision drivers."""
    for kind, key in (("BQ", "business_quality"), ("IA", "investment_attractiveness")):
        block = sc[key]
        ids = {d for d in weight_profiles()["Base"] if d.startswith(kind)}
        dims = {d.get("id"): d for d in block.get("dimensions", [])}
        if set(dims) != ids:
            res.error("%s dimensions %s, expected %s" % (key, sorted(dims), sorted(ids)))
        for did, d in dims.items():
            s_ = d.get("score")
            if not isinstance(s_, int) or not 0 <= s_ <= 100:
                res.error("%s.%s score must be integer 0-100" % (key, did))
            if d.get("confidence") not in ("High", "Medium", "Low"):
                res.error("%s.%s confidence must be High/Medium/Low (3.0.0: every dimension carries its own)" % (key, did))
            if not (d.get("rationale") or "").strip():
                res.error("%s.%s rationale missing" % (key, did))
            if not d.get("claim_ids"):
                res.warn("%s.%s cites no claim IDs" % (key, did))
        hit = set(block.get("gates_triggered") or [])
        for g in implied & set(gates(kind)):
            if g not in hit:
                res.error("%s: classification implies gate %s but gates_triggered omits it" % (key, g))
        if block.get("confidence") not in ("High", "Medium", "Low"):
            res.error("%s confidence must be High/Medium/Low" % key)
        for f in ("band", "prevents_higher", "could_lower", "evidence_to_change"):
            if block.get(f) in (None, ""):
                res.error("%s.%s missing" % (key, f))
    if "G6" in set(sc["investment_attractiveness"].get("gates_triggered") or []) and \
            sc["investment_attractiveness"].get("confidence") != "Low":
        res.error("Gate G6 requires IA confidence Low")
    pm = sc.get("price_metrics")
    if not isinstance(pm, dict):
        res.error("price_metrics missing (margin_of_safety, expected_irr, hurdle_rate, asymmetry_ratio, robust)")
        return
    for k in ("margin_of_safety", "expected_irr", "hurdle_rate", "asymmetry_ratio", "robust"):
        if pm.get(k) is None:
            res.error("price_metrics.%s missing" % k)
    if res.errors:
        return
    ev = evaluate_v3(sc)
    for kind, key in (("BQ", "business_quality"), ("IA", "investment_attractiveness")):
        block = sc[key]
        if abs(float(block.get("weighted_raw", -1)) - ev[kind]["weighted_raw"]) > 0.51:
            res.error("%s weighted_raw %s but the %s profile with effective scores gives %.2f" % (
                key, block.get("weighted_raw"), ev["weight_profile"], ev[kind]["weighted_raw"]))
        if block.get("final") != ev[kind]["final"]:
            res.error("%s final %r but the methodology gives %d" % (key, block.get("final"), ev[kind]["final"]))
    dec = sc.get("decision") or {}
    if dec.get("conviction") != ev["conviction"]:
        res.error("decision.conviction %r but the methodology gives %r (%d points)" % (dec.get("conviction"), ev["conviction"], ev["conviction_points"]))
    recorded = {t.get("test"): t.get("passed") for t in dec.get("must_pass") or []}
    for t in ev["must_pass"]:
        if recorded.get(t["test"]) is not t["passed"]:
            res.error("decision.must_pass %s recorded %r but evaluates %r (effective %.1f)" % (t["test"], recorded.get(t["test"]), t["passed"], t["effective"]))
    drivers = sc.get("decision_drivers") or []
    if sc.get("assessment_status") == "complete":
        if len(drivers) < 3:
            res.error("decision_drivers: at least 3 required (SCORING.md §6), found %d" % len(drivers))
        for i, d in enumerate(drivers, 1):
            missing = [k for k in DRIVER_KEYS if d.get(k) in (None, "", [])]
            if missing:
                res.error("decision_drivers[%d] missing %s" % (i, ", ".join(missing)))
    _check_verdict(sc, ev["mapped_verdict"], res)


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
