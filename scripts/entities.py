#!/usr/bin/env python3
"""The entity graph (methodology 3.1.0): every company and person the reading recorded, across all years read.

Built by `reading.py dossiers` from the reconciled items (no model call): one record per entity — every name it was
printed under, its CIN where printed, and every role and flow by fiscal year (related party and relationship,
subsidiary or associate and holding, related-party transactions and balances, loans, guarantees and investments,
borrowings and charges, litigation, board and pay, auditors, ratings, CARO remarks), each cited to its document,
passage and page. Writes `corpus/dossiers/entities.md` (must-read for filings, management and special-situations)
and `corpus/reading/entities.json`.

Names are merged only when they are the same after normalization (case, punctuation, "Private Limited" / "Pvt. Ltd."
/ "(P) Ltd", "Limited" / "Ltd", "&" / "and", "M/s", honorifics, role notes such as "(Subsidiary)"), when they share a
CIN, or when a filing says one was formerly the other. Names that are merely close are listed as "possibly the same
entity — confirm", never merged: a wrong merge would invent a relationship.

Flags are leads for the specialists, not conclusions: an entity that first appears or disappears in a year, a
relationship that changes (subsidiary to associate ...), a related-party counterparty that is not in that year's
list of related parties, a loan or guarantee to an entity with no disclosed relationship, an entity named in the
historian's events.

Why (2026-10-23): party names were free text; "XYZ Pvt Ltd" and "XYZ Private Limited" were separate histories, and
three specialists each built the group and related-party map by hand from the dossiers.
"""

import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

CIN_RE = re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")
FORMERLY_RE = re.compile(r"\((?:formerly|earlier)(?: known as)?[:\s]+([^)]+)\)", re.I)
ROLE_NOTE_RE = re.compile(r"\((?:[^)]*\b(?:subsidiary|subsidiaries|associate|joint venture|jv|parent|holding company|"
                          r"kmp|director|relative|promoter|fellow|step[- ]down|wholly[- ]owned|w\.?e\.?f\.?|cin|s\.? ?no)\b"
                          r"[^)]*)\)", re.I)
HONORIFIC_RE = re.compile(r"^(?:mr|mrs|ms|miss|dr|shri|smt|sri|prof|late)\.?\s+", re.I)

# item type -> [(field holding an entity, kind of appearance)]
ENTITY_FIELDS = {
    "related_party": [("name", "related party")],
    "rpt_transaction": [("party", "related-party transaction")],
    "rpt_balance": [("party", "related-party balance")],
    "rpt_approval": [("party", "related-party approval")],
    "loan_guarantee_investment_186": [("counterparty", "loan, guarantee or investment (s.186)")],
    "guarantee": [("beneficiary", "guarantee given")],
    "borrowing": [("lender_or_holder", "lender or holder")],
    "charge_or_pledge": [("holder", "charge or pledge holder")],
    "legal_or_regulatory_matter": [("counterparty", "litigation or regulatory matter")],
    "subsidiary_or_associate": [("name", "group entity")],
    "subsidiary_financials": [("name", "group entity financials")],
    "business_combination": [("target", "acquired")],
    "disposal_or_deconsolidation": [("asset_or_entity", "disposed or deconsolidated")],
    "board_member": [("name", "director")],
    "board_change": [("name", "board change")],
    "remuneration": [("name", "remuneration")],
    "audit_opinion": [("auditor_firm", "auditor")],
    "auditor_signoff": [("firm", "auditor")],
    "auditor_change": [("from_firm", "auditor replaced"), ("to_firm", "auditor appointed")],
    "credit_rating": [("agency", "rating agency")],
    "caro_clause": [("report", "CARO remark")],
    "penalty_or_noncompliance": [("authority", "penalty or non-compliance (authority)")],
}
RELATIONSHIP_KINDS = (("joint venture", "joint venture"), ("associate", "associate"), ("fellow subsidiary", "fellow subsidiary"),
                      ("step-down", "subsidiary"), ("subsidiar", "subsidiary"), ("holding", "holding company"),
                      ("parent", "holding company"), ("promoter", "promoter group"), ("key management", "KMP"),
                      ("kmp", "KMP"), ("relative", "relative of KMP"), ("significant influence", "significant influence"),
                      ("trust", "trust"), ("director", "director"))
RELATED_TYPES = ("related_party", "subsidiary_or_associate")
FLOW_TYPES = ("rpt_transaction", "rpt_balance", "rpt_approval")
LENDING_TYPES = ("loan_guarantee_investment_186", "guarantee")
NEAR = 0.9


def canonical(name: str) -> str:
    """The merge key of a name (see the module docstring)."""
    s = str(name or "")
    s = FORMERLY_RE.sub(" ", s)
    s = CIN_RE.sub(" ", s)
    s = ROLE_NOTE_RE.sub(" ", s)
    s = s.strip().strip(",;:").strip()
    s = HONORIFIC_RE.sub("", s)
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\bm/s\.?\s*|\bmessrs\.?\s*", " ", s)
    s = re.sub(r"\(\s*p\s*\)", " pvt ", s)
    s = re.sub(r"\bprivate\b|\bpvt\b\.?", " pvt ", s)
    s = re.sub(r"\blimited\b|\bltd\b\.?", " ltd ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"^the ", "", s)


def relationship_kind(text: str) -> str:
    t = str(text or "").lower()
    return next((k for w, k in RELATIONSHIP_KINDS if w in t), "other" if t.strip() else "")


class EntityGraph:
    def __init__(self):
        self.entities: Dict[str, dict] = {}
        self.alias: Dict[str, str] = {}          # merged key -> surviving key
        self.related_by_fy: Dict[int, set] = defaultdict(set)
        self.fys = set()

    def key_of(self, k: str) -> str:
        while k in self.alias:
            k = self.alias[k]
        return k

    def merge(self, a: str, b: str) -> str:
        a, b = self.key_of(a), self.key_of(b)
        if a == b:
            return a
        keep, drop = sorted((a, b), key=lambda k: -len(self.entities.get(k, {}).get("appearances", [])))
        src = self.entities.pop(drop, None)
        if src:
            e = self.entities.setdefault(keep, {"names": Counter(), "cins": set(), "appearances": []})
            e["names"].update(src["names"])
            e["cins"] |= src["cins"]
            e["appearances"] += src["appearances"]
        self.alias[drop] = keep
        return keep

    def add(self, it: dict, doc: str, doc_label: str, fy: int) -> None:
        fields = it.get("fields") or {}
        quote = str(it.get("quote") or "")
        for fld, kind in ENTITY_FIELDS.get(it.get("type"), ()):
            raw = str(fields.get(fld) or "").strip()
            if not raw or len(raw) < 3:
                continue
            k = canonical(raw)
            if len(k) < 3:
                continue
            k = self.key_of(k)
            e = self.entities.setdefault(k, {"names": Counter(), "cins": set(), "appearances": []})
            e["names"][re.sub(r"\s+", " ", raw)] += 1
            cins = set(CIN_RE.findall(raw)) | (set(CIN_RE.findall(quote)) if len(CIN_RE.findall(quote)) == 1 else set())
            e["cins"] |= cins
            rel = fields.get("relationship") or fields.get("category") or fields.get("role") or ""
            app = {"fy": fy, "type": it.get("type"), "kind": kind, "relationship": str(rel),
                   "rel_kind": relationship_kind(rel) if it.get("type") in RELATED_TYPES else "",
                   "detail": "; ".join("%s: %s" % (f, v) for f, v in fields.items() if f != fld and str(v).strip())[:220],
                   "doc": doc, "doc_label": doc_label, "unit": it.get("unit"), "page": it.get("page")}
            e["appearances"].append(app)
            self.fys.add(fy)
            if it.get("type") in RELATED_TYPES:
                self.related_by_fy[fy].add(k)
            m = FORMERLY_RE.search(raw)
            if m:                                  # the filing says it is the same entity
                old = canonical(m.group(1))
                if len(old) >= 3:
                    if old in self.entities or old in self.alias:
                        k = self.merge(k, old)
                    else:
                        self.alias[old] = k

    def finish(self) -> None:
        """Merge entities that share a CIN; resolve related-party sets to surviving keys."""
        by_cin = defaultdict(list)
        for k, e in list(self.entities.items()):
            for c in e["cins"]:
                by_cin[c].append(k)
        for c, ks in by_cin.items():
            base = ks[0]
            for k in ks[1:]:
                if k in self.entities or k in self.alias:
                    base = self.merge(base, k)
        self.related_by_fy = {fy: {self.key_of(k) for k in ks} for fy, ks in self.related_by_fy.items()}

    def near_matches(self) -> List[Tuple[str, str, float]]:
        keys = sorted(self.entities)
        out = []
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if a[:3] != b[:3] or abs(len(a) - len(b)) > 12:
                    continue
                r = SequenceMatcher(None, a, b).ratio()
                if r >= NEAR:
                    out.append((a, b, round(r, 3)))
        return out[:200]

    def flags(self, events: Optional[List[dict]] = None) -> List[Tuple[str, str]]:
        """[(entity key, lead)]"""
        out = []
        lo, hi = (min(self.fys), max(self.fys)) if self.fys else (0, 0)
        listed_fys = {fy for fy, ks in self.related_by_fy.items() if ks}
        for k, e in self.entities.items():
            apps = e["appearances"]
            rel = [a for a in apps if a["type"] in RELATED_TYPES]
            if rel:
                fys = sorted({a["fy"] for a in rel})
                if fys[0] > lo:
                    out.append((k, "first listed as a related party or group entity in FY%d" % fys[0]))
                if fys[-1] < hi:
                    out.append((k, "last listed as a related party or group entity in FY%d" % fys[-1]))
                kinds = {}
                for a in sorted(rel, key=lambda a: a["fy"]):
                    if a["rel_kind"] and a["rel_kind"] != "other":
                        kinds.setdefault(a["fy"], set()).add(a["rel_kind"])
                seq = [(fy, "/".join(sorted(v))) for fy, v in sorted(kinds.items())]
                for (f1, k1), (f2, k2) in zip(seq, seq[1:]):
                    if k1 != k2:
                        out.append((k, "relationship changes from %s (FY%d) to %s (FY%d)" % (k1, f1, k2, f2)))
            for a in apps:
                if a["type"] in FLOW_TYPES and a["fy"] in listed_fys and k not in self.related_by_fy.get(a["fy"], set()):
                    out.append((k, "%s in FY%d, but not in that year's list of related parties read" % (a["kind"], a["fy"])))
                    break
            if any(a["type"] in LENDING_TYPES for a in apps) and not rel and not any(a["type"] in FLOW_TYPES for a in apps):
                out.append((k, "loan, guarantee or investment to an entity with no disclosed relationship"))
        for ev in events or []:
            for name in re.split(r"\s*;\s*", ev.get("entities") or ""):
                c = canonical(name)
                if c and self.key_of(c) in self.entities:
                    out.append((self.key_of(c), "named in event %s (%s): %s" % (ev.get("event_id"), ev.get("date"),
                                                                                (ev.get("event") or "")[:120])))
        return out

    def display(self, k: str) -> str:
        return self.entities[k]["names"].most_common(1)[0][0] if self.entities[k]["names"] else k

    def to_json(self) -> dict:
        return {"entities": {k: {"names": dict(e["names"]), "cins": sorted(e["cins"]), "appearances": e["appearances"]}
                             for k, e in self.entities.items()}, "aliases": self.alias}

    def markdown(self, run_id: str, head: str, events: Optional[List[dict]] = None) -> str:
        flags = self.flags(events)
        near = self.near_matches()
        by = defaultdict(list)
        for k, f in flags:
            by[k].append(f)
        order = sorted(self.entities, key=lambda k: (-len({a["fy"] for a in self.entities[k]["appearances"]}),
                                                     -len(self.entities[k]["appearances"]), self.display(k).lower()))
        lines = ["# Entity graph — run %s" % run_id, "", head, "",
                 "Every company and person the reading recorded, merged across years only when the name is the same "
                 "after normalization, the CIN is the same, or a filing says one was formerly the other. Flags and near "
                 "matches are leads to check on the page, not conclusions.", "",
                 "%d entities; %d flags; %d pairs possibly the same entity." % (len(self.entities), len(flags), len(near)), "",
                 "## Flags (%d)" % len(flags), ""]
        lines += ["- **%s**: %s" % (self.display(k), f) for k, f in sorted(flags, key=lambda x: self.display(x[0]).lower())]
        lines += ["", "## Possibly the same entity — confirm on the page (%d)" % len(near), ""]
        lines += ["- %s / %s (similarity %.2f)" % (self.display(a), self.display(b), r) for a, b, r in near]
        lines += ["", "## Entities (%d), the most years first" % len(self.entities), ""]
        for k in order:
            e = self.entities[k]
            names = [n for n, _ in e["names"].most_common()]
            lines += ["### %s" % names[0], ""]
            meta = []
            if len(names) > 1:
                meta.append("also printed as: %s" % "; ".join(names[1:6]))
            if e["cins"]:
                meta.append("CIN %s" % ", ".join(sorted(e["cins"])))
            aka = sorted(a for a, b in self.alias.items() if self.key_of(b) == k and a not in (canonical(n) for n in names))
            if aka:
                meta.append("formerly: %s" % "; ".join(aka[:4]))
            if by.get(k):
                meta.append("flags: %s" % " · ".join(by[k]))
            lines += ["- %s" % m for m in meta]
            for a in sorted(e["appearances"], key=lambda a: (-a["fy"], a["kind"])):
                lines.append("- FY%d · %s%s%s `[%s %s p.%s]`" % (
                    a["fy"], a["kind"], " (%s)" % a["relationship"] if a["relationship"] else "",
                    " · %s" % a["detail"] if a["detail"] else "", a["doc"], a["unit"], a["page"]))
            lines.append("")
        return "\n".join(lines) + "\n"
