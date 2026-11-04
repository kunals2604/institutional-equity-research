#!/usr/bin/env python3
"""Triage: one company, one session, a tear sheet that says KILL or CONTINUE. The cheap tier before a full run.

  python3 scripts/triage.py prepare SYMBOL [--exchange NSE] [--date YYYY-MM-DD] [--company "Name"]
  python3 scripts/agent_driver.py triage DIR          # the triage agent writes DIR/TEAR_SHEET.md (one paid session)
  python3 scripts/triage.py check DIR                 # the agent runs this until it passes
  python3 scripts/triage.py record DIR                # appends the decision to research/funnel/triage/TRIAGE_LOG.csv

`prepare` builds research/funnel/triage/<SYMBOL>/<id>/: a manifest, the warehouse's facts and prices as known on the date
(corpus/facts/, as a run gets them), and PACK.md, which a script fills with the company's last five fiscal years, its
price record, its scan row when a scan of that date exists, survivor-biased base rates and anything the warehouse
rejected as filed. The agent reads the pack, searches the web for what the numbers cannot show (governance, regulators,
litigation, the business), and writes the tear sheet.

A triage is not research and not a verdict. KILL means "not worth a full run now", with the reason; CONTINUE means "a
full run should answer these questions first". It lives outside runs/, never touches the scoreboard or the decision
record, and a later full run does not read it: the run's specialists start independent.
"""

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import base_rates as br  # noqa: E402
import research_lib as rl  # noqa: E402
import warehouse as wh  # noqa: E402

HOME = rl.ROOT / "research" / "funnel" / "triage"
SHEET = "TEAR_SHEET.md"
DECISIONS = ("KILL", "CONTINUE")
SECTIONS = ("What the company does", "The numbers", "Red flags", "What would have to be true", "Why", "Sources opened")
MAX_WORDS = 1500
PACK_METRICS = ("revenue", "interest_income", "pat_attributable", "cfo", "total_equity", "total_debt", "advances", "gnpa",
                "shares_outstanding")
NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def prepare(con, symbol: str, day: str, exchange: str = "NSE", company: str = "", home: Path = None) -> Path:
    symbol = symbol.strip().upper()
    sec = con.execute("SELECT name, isin FROM securities WHERE exchange = ? AND symbol = ?", (exchange, symbol)).fetchone()
    company = company or (sec[0] if sec and sec[0] else symbol)       # NSE's 2020-2024 format carries no names
    tid = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = (home or HOME) / symbol / tid
    d.mkdir(parents=True)
    juris = "US" if exchange == "US" else "IN"
    rl.write_json(d / rl.RUN_MANIFEST, {"run_id": tid, "kind": "triage", "ticker": symbol, "exchange": exchange, "jurisdiction": juris,
                                        "company": company, "isin": sec[1] if sec and sec[1] else "unknown",
                                        "research_cutoff": day, "status": "triage", "replay": False,
                                        "methodology_version": rl.methodology_version(), "model": {"effort_override": None}})
    wh.materialise(con, d)
    (d / "PACK.md").write_text(pack_text(con, symbol, day, exchange, company), encoding="utf-8")
    return d


def pack_text(con, symbol: str, day: str, exchange: str, company: str) -> str:
    lines = ["# Triage pack — %s (%s, %s), as known on %s" % (company, symbol, exchange, day), "",
             "Built by `scripts/triage.py prepare` from the warehouse: exchange results as filed and the verified facts of "
             "earlier finished runs. Cite a figure from here as `PACK`; anything else needs the URL you opened.", ""]
    years = set()
    data = {m: br.series(con, m, day).get(wh.key(symbol, "US" if exchange == "US" else "IN"), {}) for m in PACK_METRICS}
    for s in data.values():
        years |= set(s)
    years = sorted(years)[-5:]
    if years:
        lines += ["## The last five fiscal years (%s unless stated; consolidated where filed)" % (
                      "USD million" if exchange == "US" else "INR crore"), "",
                  "| Metric | %s |" % " | ".join("FY%d" % y for y in years), "|---|%s" % ("---|" * len(years))]
        for m in PACK_METRICS:
            if data[m]:
                lines.append("| %s | %s |" % (m, " | ".join(_num(data[m].get(y), m) for y in years)))
        lines.append("")
    else:
        lines += ["No results for this company in the warehouse: run `warehouse.py crawl-xbrl` for it first, or triage "
                  "from the web alone and say so.", ""]
    import scan
    series = scan.prices(con, exchange, day).get(symbol, [])
    pm = scan.price_measures(series, day)
    if pm:
        lines += ["## Price on %s" % day, "", "- Close: %s" % _num(pm.get("close")),
                  "- One-year return: %s" % _pct(pm.get("return_1y")), "- Worst fall from a high within the year: %s" % _pct(pm.get("max_drawdown_1y")),
                  "- Median daily traded value, last 60 sessions: INR %s" % _num(pm.get("median_traded_inr_60d")), ""]
    row = scan_row(symbol, day, exchange)
    if row:
        lines += ["## Its row in the scan of %s" % day, "",
                  "Rank score %s; earnings yield %s; ROE %s; growth (3y) %s; flags: %s." % (
                      row.get("rank_score") or "n/a", row.get("earnings_yield") or "n/a", row.get("roe") or "n/a",
                      row.get("growth_3y") or "n/a", row.get("flags") or "none"), ""]
    g = br.cagr(con, "revenue", 5, 0.15, day)
    r = br.dist(con, "roe", "FY%d" % (years[-1] if years else int(day[:4])), day)
    lines += ["## Base rates (outside view)", "",
              "- Of %d companies with five years of revenue, %s compounded at 15 %% a year or more." % (
                  g["companies"], _pct(g["share_at_or_above"])),
              "- Return on equity across %d companies: %s." % (r["companies"], ", ".join(
                  "%s %s" % (k, _pct(v)) for k, v in r["distribution"].items() if k != "n") or "too few to say"),
              "- %s" % br.CAVEAT, ""]
    rejected = con.execute("SELECT metric, period, value, reason FROM rejected WHERE ticker = ?",
                           (wh.key(symbol, "US" if exchange == "US" else "IN"),)).fetchall()
    if rejected:
        lines += ["## Values the warehouse rejected as filed", ""] + ["- %s %s: %s (%s)" % r for r in rejected] + [""]
    return "\n".join(lines)


def _num(v, metric: str = "") -> str:
    if v is None:
        return ""
    if metric == "shares_outstanding":
        return "{:,.0f}".format(v)
    return "{:,.2f}".format(v) if abs(v) < 1e6 else "{:,.0f}".format(v)


def _pct(v) -> str:
    return "n/a" if v is None else "%.1f%%" % (v * 100)


def scan_row(symbol: str, day: str, exchange: str) -> Optional[dict]:
    import scan
    path = scan.OUT / ("%s_%s.csv" % (day, exchange))
    if not path.exists():
        return None
    with path.open(encoding="utf-8", newline="") as f:
        return next((r for r in csv.DictReader(f) if r["symbol"] == symbol), None)


def sections(text: str) -> Dict[str, str]:
    out, name = {}, None
    for line in text.splitlines():
        m = re.match(r"##\s+(.+?)\s*$", line)
        if m:
            name = next((s for s in SECTIONS + ("If CONTINUE",) if m.group(1).lower().startswith(s.lower())), m.group(1))
            out[name] = ""
        elif name:
            out[name] += line + "\n"
    return out


def decision(text: str) -> str:
    m = re.search(r"^Decision:\s*\**\s*(KILL|CONTINUE)\b", text, re.M)
    return m.group(1) if m else ""


def errors(d: Path) -> List[str]:
    p = d / SHEET
    if not p.exists():
        return ["%s does not exist yet" % SHEET]
    text = p.read_text(encoding="utf-8")
    errs = []
    dec = decision(text)
    if not dec:
        errs.append("state the decision on its own line: `Decision: KILL` or `Decision: CONTINUE`")
    sec = sections(text)
    errs += ["add the section `## %s`" % s for s in SECTIONS if s not in sec]
    words = len(text.split())
    if words > MAX_WORDS:
        errs.append("%d words: a tear sheet is at most %d" % (words, MAX_WORDS))
    if dec == "CONTINUE":
        qs = [l for l in sec.get("If CONTINUE", "").splitlines() if re.match(r"\s*\d+[.)]\s", l)]
        if not 3 <= len(qs) <= 5 or not all(q.rstrip().endswith("?") for q in qs):
            errs.append("a CONTINUE needs `## If CONTINUE: what the full run must answer first` with 3 to 5 numbered questions")
    if dec and not sec.get("Why", "").strip():
        errs.append("say why, under `## Why`")
    pack = (d / "PACK.md").read_text(encoding="utf-8") if (d / "PACK.md").exists() else ""
    facts = (d / "corpus" / "facts" / "facts.csv").read_text(encoding="utf-8") if (d / "corpus" / "facts" / "facts.csv").exists() else ""
    import verify
    known = verify.exact_set(pack + facts)
    for line in sec.get("The numbers", "").splitlines():
        if "http" in line:
            continue
        for n in NUMBER_RE.findall(line):
            if len(re.sub(r"\D", "", n)) >= 3 and not verify.exact_set(n) <= known:
                errs.append("`%s` is in neither the pack nor a cited URL on its line: %s" % (n, line.strip()[:100]))
    urls = set(re.findall(r"https?://[^\s)>\]]+", text))
    listed = set(re.findall(r"https?://[^\s)>\]]+", sec.get("Sources opened", "")))
    if urls - listed:
        errs.append("list every URL you cite under `## Sources opened`: %s" % ", ".join(sorted(urls - listed)[:5]))
    return errs


LOG_COLUMNS = ["symbol", "exchange", "as_of", "decision", "why", "dir", "recorded_at"]


def record(d: Path, home: Path = None) -> dict:
    errs = errors(d)
    if errs:
        raise SystemExit("the tear sheet does not pass its check:\n- " + "\n- ".join(errs))
    m = rl.load_json(d / rl.RUN_MANIFEST)
    text = (d / SHEET).read_text(encoding="utf-8")
    why = next((l.strip("-* ").strip() for l in sections(text)["Why"].splitlines() if l.strip()), "")
    row = {"symbol": m["ticker"], "exchange": m["exchange"], "as_of": m["research_cutoff"], "decision": decision(text),
           "why": why[:300], "dir": str(d.relative_to(rl.ROOT)) if str(d).startswith(str(rl.ROOT)) else str(d),
           "recorded_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()}
    log = (home or HOME) / "TRIAGE_LOG.csv"
    log.parent.mkdir(parents=True, exist_ok=True)
    new = not log.exists()
    with log.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("symbol")
    p.add_argument("--exchange", default="NSE")
    p.add_argument("--date", default=None)
    p.add_argument("--company", default="")
    for name in ("check", "record"):
        sub.add_parser(name).add_argument("dir")
    a = ap.parse_args(argv)
    if a.cmd == "prepare":
        print(prepare(wh.connect(), a.symbol, a.date or dt.date.today().isoformat(), a.exchange, a.company))
        return 0
    d = Path(a.dir)
    if a.cmd == "check":
        errs = errors(d)
        print("\n".join("- " + e for e in errs) if errs else "PASS: %s" % decision((d / SHEET).read_text(encoding="utf-8")))
        return 1 if errs else 0
    print(record(d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
