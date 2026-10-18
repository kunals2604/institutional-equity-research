#!/usr/bin/env python3
"""Deterministic aids for the independent auditor (.claude/agents/auditor.md) and for the CIO's own QC.

  python3 scripts/audit_tools.py tieout RUN_DIR [--report cio/final_report.md] [--out RUN_DIR/audit/tieout.csv]
  python3 scripts/audit_tools.py sample RUN_DIR [--n 30] [--seed <RUN_ID>] [--out RUN_DIR/audit/sample.csv]

tieout   For every sentence or table row of the report that cites FACT / CALCULATION / ESTIMATE claim IDs with a
         numeric ledger value, check that at least one number in that sentence or row equals one of the cited values
         (allowing for rounding and the usual unit shifts: ratio ↔ %, crore ↔ lakh crore / thousand crore), or that a
         cited value lies inside a stated range ("1,306–1,509"). Status per row:
           match         a number equals a cited claim's value;
           other_claim   no cited value matches, but a number equals the value of a claim the row does NOT cite
                         (an incomplete citation: cite that claim too);
           mismatch      no ledger value in the run matches: a derived or unsupported number to examine by hand.
         The tool screens; it does not judge: a flagged row can be a different period or a presentation choice.
sample   A reproducible, stratified sample of claims to re-verify against their sources: every claim cited in the
         decision sections (dashboard, thesis, scorecards, triggers, verdict), plus a seeded draw weighted toward
         tiers 4-7, single-source claims and quantitative claims, with at least one claim from every author. Each row
         carries the source, locator and the local file to open (from source_retrievals.csv or the corpus catalog).

Both write only the --out file (default under RUN_DIR/audit/). Exit: 0 ok, 1 tie-out mismatches found, 2 usage.
"""

import argparse
import csv
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

DECISION_SECTIONS = ("Decision Dashboard", "Executive Investment Thesis", "Business Quality Scorecard",
                     "Investment Attractiveness Scorecard", "Position-Risk Profile and Decision Triggers", "Final Verdict",
                     "Key Debates and Variant Perception", "Confidence Assessment")
NUM_RE = re.compile(r"(?<![A-Za-z0-9.])[-−–]?\(?\d[\d,]*(?:\.\d+)?\)?(?:\s?%|\s?x\b)?")
TAG_CITE_RE = re.compile(r"\[(FACT|CALCULATION|ESTIMATE|MANAGEMENT STATEMENT)\s*[:|]\s*([^\]]+)\]")


def ledger_index(run_dir: Path) -> Dict[str, dict]:
    out = {}
    for lp in rl.run_ledger_paths(run_dir):
        _, rows = rl.read_csv(lp)
        for r in rows:
            out[r["claim_id"]] = r
    return out


def to_float(s: str) -> Optional[float]:
    t = s.strip().replace("−", "-").replace("–", "-").replace(",", "").replace("%", "").replace("x", "").strip()
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def decimals(s: str) -> int:
    m = re.search(r"\.(\d+)", s)
    return len(m.group(1)) if m else 0


def candidates(v: float, unit: str) -> List[float]:
    out = {v, -v}
    for k in (100.0, 0.01, 0.001, 1e-5, 1000.0, 1e-7, 1e7 / 1e9):
        out.add(v * k)
    return [c for c in out if c == c]


def matches(token: str, value: float, unit: str) -> bool:
    n = to_float(token)
    if n is None:
        return False
    tol_abs = 0.5 * 10 ** (-decimals(token)) if decimals(token) else 0.5
    for c in candidates(value, unit):
        if abs(n - c) <= max(tol_abs, 0.006 * abs(c)):
            return True
    return False


RANGE_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:–|-|to)\s*(\d[\d,]*(?:\.\d+)?)")


def in_stated_range(seg: str, value: float) -> bool:
    for a, b in RANGE_RE.findall(seg):
        lo, hi = to_float(a), to_float(b)
        if lo is not None and hi is not None and lo < hi and lo <= value <= hi:
            return True
    return False


def segments(text: str):
    """(line number, section, segment text): table rows whole, prose split into sentences."""
    section = ""
    for i, line in enumerate(text.splitlines(), 1):
        h = re.match(r"^##\s+(.*)$", line)
        if h:
            section = h.group(1).strip()
            continue
        if line.strip().startswith("|"):
            yield i, section, line
            continue
        for sent in re.split(r"(?<=[.;])\s+(?=[A-Z\[(])", line):
            if sent.strip():
                yield i, section, sent


def tieout(run_dir: Path, report: Path, out: Path) -> int:
    ledger = ledger_index(run_dir)
    all_values = []
    for cid, r in ledger.items():
        v = to_float(r.get("value") or "") if (r.get("value") or "").strip() else None
        if v is not None:
            all_values.append((cid, v, r.get("unit", "")))
    text = report.read_text(encoding="utf-8")
    rows, n_mis = [], 0
    for line_no, section, seg in segments(text):
        ids = []
        for m in TAG_CITE_RE.finditer(seg):
            ids += [x for x in rl.CLAIM_ID_RE.findall(m.group(2))]
        numeric = []
        for cid in ids:
            r = ledger.get(cid)
            if r and (r.get("value") or "").strip():
                v = to_float(r["value"])
                if v is not None:
                    numeric.append((cid, v, r.get("unit", "")))
        if not numeric:
            continue
        stripped = TAG_CITE_RE.sub(" ", seg)
        stripped = re.sub(r"\b(?:FY|Q[1-4]FY|CY)\s?\d{2,4}\b|\b(?:19|20)\d{2}\b|\b[A-Z]{2,5}-C\d{3,}\b|\bL[1-4]\b|"
                          r"\b(?:IA|BQ|G)\d\b|\bT\d{1,2}\b", " ", stripped)
        tokens = [t.strip() for t in NUM_RE.findall(stripped) if any(ch.isdigit() for ch in t)]
        if not tokens:
            continue
        ok = any(matches(t, v, u) for t in tokens for _, v, u in numeric) or \
            any(in_stated_range(stripped, v) for _, v, _ in numeric)
        other = []
        if not ok:
            for t in tokens:
                other += [c for c, v, u in all_values if c not in ids and matches(t, v, u) and abs(v) >= 1][:3]
        status = "match" if ok else ("other_claim" if other else "mismatch")
        n_mis += 1 if status == "mismatch" else 0
        rows.append({"line": line_no, "section": section, "status": status,
                     "cited": "; ".join("%s=%s %s" % (c, v, u) for c, v, u in numeric), "numbers": " ".join(tokens[:12]),
                     "uncited_matches": " ".join(sorted(set(other))[:6]),
                     "excerpt": re.sub(r"\s+", " ", seg.strip())[:240]})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["line", "section", "status", "cited", "numbers", "uncited_matches", "excerpt"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: ({"mismatch": 0, "other_claim": 1}.get(r["status"], 2), r["line"])))
    n_other = sum(1 for r in rows if r["status"] == "other_claim")
    print("tie-out: %d cited numeric segments: %d match, %d cite incompletely (number is another claim's value), "
          "%d to examine by hand -> %s" % (len(rows), len(rows) - n_mis - n_other, n_other, n_mis, out))
    for r in [x for x in rows if x["status"] == "mismatch"][:25]:
        print("  line %s [%s] cited %s | numbers %s" % (r["line"], r["section"][:30], r["cited"][:70], r["numbers"][:60]))
    return 1 if n_mis else 0


def cached_file(run_dir: Path, source: str, retrievals: Dict[str, str], catalog: Dict[str, str]) -> str:
    if source.startswith("FilingForge:"):
        return catalog.get(source.split(":", 1)[1], "")
    return retrievals.get(source, "")


def sample(run_dir: Path, n: int, seed: str, out: Path) -> int:
    ledger = ledger_index(run_dir)
    report = run_dir / "cio" / "final_report.md"
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    critical: Set[str] = set()
    for s in DECISION_SECTIONS:
        critical |= set(rl.CLAIM_ID_RE.findall(rl.section(text, s) or ""))
    critical &= set(ledger)
    retrievals, catalog = {}, {}
    log = run_dir / "source_retrievals.csv"
    if log.exists():
        _, rows = rl.read_csv(log)
        for r in rows:
            if str(r.get("http_status")) == "200" and not r.get("error") and r.get("local_path"):
                retrievals.setdefault(r["url"], r["local_path"])
    cat = run_dir / "corpus" / "catalog.csv"
    if cat.exists():
        _, rows = rl.read_csv(cat)
        for r in rows:
            catalog[r.get("doc_id", "")] = r.get("pdf_path") or r.get("md_path") or ""
    rng = random.Random(seed)
    pool = [cid for cid in sorted(ledger) if cid not in critical]

    def weight(cid):
        r = ledger[cid]
        w = 1.0
        try:
            if int(r.get("source_tier") or 0) >= 4:
                w *= 3
        except ValueError:
            pass
        if not (r.get("corroborated_by") or "").strip():
            w *= 1.5
        if (r.get("value") or "").strip():
            w *= 1.5
        return w
    chosen: List[str] = []
    authors = sorted({ledger[c].get("author", "") for c in pool})
    for a in authors:                                # at least one claim per author
        cands = [c for c in pool if ledger[c].get("author") == a and c not in chosen]
        if cands:
            chosen.append(rng.choices(cands, weights=[weight(c) for c in cands])[0])
    remaining = [c for c in pool if c not in chosen]
    while len(chosen) < n and remaining:
        pick = rng.choices(remaining, weights=[weight(c) for c in remaining])[0]
        chosen.append(pick)
        remaining.remove(pick)
    rows = []
    for cid in sorted(critical) + chosen:
        r = ledger[cid]
        rows.append({"claim_id": cid, "reason": "decision-critical" if cid in critical else "sampled",
                     "author": r.get("author", ""), "tag": r.get("tag", ""), "claim": r.get("claim", "")[:200],
                     "value": r.get("value", ""), "unit": r.get("unit", ""), "period": r.get("period", ""),
                     "source_url_or_id": r.get("source_url_or_id", ""), "locator": r.get("locator", ""),
                     "tier": r.get("source_tier", ""), "local_file": cached_file(run_dir, r.get("source_url_or_id", ""), retrievals, catalog),
                     "result": "", "notes": ""})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["claim_id"])
        w.writeheader()
        w.writerows(rows)
    print("sample: %d decision-critical + %d sampled claims (seed %s) -> %s" % (len(critical), len(chosen), seed, out))
    print("Fill `result` with Confirmed | Minor discrepancy | Material discrepancy | Not verifiable after opening each source.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tieout")
    t.add_argument("run_dir")
    t.add_argument("--report", help="default: RUN_DIR/cio/final_report.md")
    t.add_argument("--out", help="default: RUN_DIR/audit/tieout.csv")
    s = sub.add_parser("sample")
    s.add_argument("run_dir")
    s.add_argument("--n", type=int, default=30, help="sampled claims in addition to the decision-critical ones")
    s.add_argument("--seed", help="default: the run ID (reproducible)")
    s.add_argument("--out", help="default: RUN_DIR/audit/sample.csv")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if a.cmd == "tieout":
        report = Path(a.report) if a.report else run_dir / "cio" / "final_report.md"
        if not report.exists():
            ap.error("report not found: %s" % report)
        return tieout(run_dir, report, Path(a.out) if a.out else run_dir / "audit" / "tieout.csv")
    seed = a.seed or rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id", "seed")
    return sample(run_dir, a.n, seed, Path(a.out) if a.out else run_dir / "audit" / "sample.csv")


if __name__ == "__main__":
    sys.exit(main())
