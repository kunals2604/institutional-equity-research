#!/usr/bin/env python3
"""Build compact, page-marked transcript texts for the concalls specialist.

Inputs: pdftotext -layout outputs (form-feed page breaks) in _cache/concalls/txt/
and corpus page files (=== PAGE n ===) in _cache/corpus/.
Output: _cache/concalls/compact/<QxFYyyyy>.txt with [p.N] markers and collapsed whitespace,
plus calc/concalls_transcript_index.csv (quarter, call date text, source file, pages).
Usage: python3 -I concalls_compact.py RUN_DIR
"""
import csv
import re
import sys
from pathlib import Path

MONTH_Q = {"june": 1, "september": 2, "december": 3, "march": 4}


def quarter_label(text):
    m = re.search(r"(first|second|third|fourth|Q[1-4])\s+(?:quarter\s+)?(?:&\s+full\s+year\s+|and\s+(?:9M|full\s+year)\s+)?(?:ended|FY)\s*,?\s*(?:on\s+)?(March|June|September|December)?\s*(\d{1,2})?(?:st|th|nd|rd)?,?\s*(\d{4})",
                  text, re.I)
    m2 = re.search(r"(?:quarter|Q[1-4])[^.]{0,40}?ended\s+(?:on\s+)?(March|June|September|December)\s+\d{1,2}(?:st|th|nd|rd)?,?\s+(\d{4})", text, re.I)
    if m2:
        mon, yr = m2.group(1).lower(), int(m2.group(2))
        q = MONTH_Q[mon]
        fy = yr + 1 if mon != "march" else yr
        return "Q%dFY%d" % (q, fy)
    m3 = re.search(r"(First|Second|Third|Fourth) Quarter FY\s?(\d{4})", text, re.I)
    if m3:
        q = {"first": 1, "second": 2, "third": 3, "fourth": 4}[m3.group(1).lower()]
        return "Q%dFY%s" % (q, m3.group(2))
    m4 = re.search(r"Fourth Quarter and Full Year FY\s?(\d{4})", text, re.I)
    if m4:
        return "Q4FY%s" % m4.group(1)
    return None


def compact_pages(pages):
    out = []
    for i, p in enumerate(pages, 1):
        lines = []
        for ln in p.splitlines():
            s = re.sub(r"\s+", " ", ln).strip()
            if not s:
                continue
            if re.match(r"^(Page \d+ of \d+|\d+)$", s):
                continue
            lines.append(s)
        out.append("[p.%d] " % i + " ".join(lines))
    return "\n".join(out)


def main():
    run = Path(sys.argv[1])
    src_txt = run / "_cache/concalls/txt"
    corp = run / "_cache/corpus"
    outd = run / "_cache/concalls/compact"
    outd.mkdir(parents=True, exist_ok=True)
    rows = []
    items = []
    for f in sorted(src_txt.glob("*.txt")):
        pages = f.read_text(errors="ignore").split("\f")
        items.append(("web", f, [p for p in pages]))
    for f in sorted(corp.glob("*Concall_transcript*.pages.txt")):
        raw = f.read_text(errors="ignore")
        pages = re.split(r"=== PAGE \d+ ===", raw)[1:]
        items.append(("corpus", f, pages))
    for kind, f, pages in items:
        head = " ".join(re.sub(r"\s+", " ", p) for p in pages[:3])
        q = quarter_label(head) or "UNKNOWN"
        call = re.search(r"(?:held on|dated|Call dated|Earnings Call held on)\s+([A-Z][a-z]+ \d{1,2},? \d{4})", head)
        dest = outd / ("%s__%s.txt" % (q, kind))
        if dest.exists() and kind == "corpus":
            dest = outd / ("%s__%s_b.txt" % (q, kind))
        dest.write_text(compact_pages(pages))
        rows.append([q, kind, call.group(1) if call else "", f.name, len(pages), dest.name])
    with open(run / "calc/concalls_transcript_index.csv", "w", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["quarter", "channel", "call_date_text", "source_file", "pages", "compact_file"])
        for r in sorted(rows):
            w.writerow(r)
    for r in sorted(rows):
        print(r)


if __name__ == "__main__":
    main()
