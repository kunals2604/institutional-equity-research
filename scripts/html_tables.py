#!/usr/bin/env python3
"""Extract HTML tables deterministically into CSV files (no model in the loop).

  python3 scripts/html_tables.py RUN_DIR/_cache/financials/....html --out-dir RUN_DIR/specialists/financials_workpapers/tables
  python3 scripts/html_tables.py page.html --match "Profit & Loss" --list

Each table becomes table_<n>.csv (cells are whitespace-normalized text;
colspan cells are repeated). --match keeps only tables whose text contains the
string (case-insensitive). --list prints an index without writing files.
"""

import argparse
import csv
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: List[List[List[str]]] = []
        self.stack: List[List[List[str]]] = []
        self.row: Optional[List[str]] = None
        self.cell: Optional[List[str]] = None
        self.colspan = 1

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.stack.append([])
        elif tag == "tr" and self.stack:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
            span = dict(attrs).get("colspan") or "1"
            self.colspan = int(span) if span.isdigit() else 1
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            text = re.sub(r"\s+", " ", "".join(self.cell)).strip()
            self.row.extend([text] * max(1, min(self.colspan, 50)))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.stack:
            if any(c for c in self.row):
                self.stack[-1].append(self.row)
            self.row = None
        elif tag == "table" and self.stack:
            t = self.stack.pop()
            if t:
                self.tables.append(t)

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def extract(html: str) -> List[List[List[str]]]:
    p = TableParser()
    p.feed(html)
    return p.tables


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html_file")
    ap.add_argument("--out-dir")
    ap.add_argument("--match")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    raw = Path(a.html_file).read_bytes()
    html = raw.decode("utf-8", errors="replace")
    tables = extract(html)
    if a.match:
        needle = a.match.lower()
        tables = [t for t in tables if needle in " ".join(" ".join(r) for r in t).lower()]
    if not tables:
        print("No tables found%s." % (" matching %r" % a.match if a.match else ""))
        return 1
    out = Path(a.out_dir) if a.out_dir else None
    if out and not a.list:
        out.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(tables, 1):
        width = max(len(r) for r in t)
        first = " | ".join(t[0])[:110]
        print("table_%d: %d rows x %d cols — %s" % (i, len(t), width, first))
        if out and not a.list:
            with (out / ("table_%d.csv" % i)).open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([r + [""] * (width - len(r)) for r in t])
    if out and not a.list:
        print("Wrote %d CSV file(s) to %s" % (len(tables), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
