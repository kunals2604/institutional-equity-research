#!/usr/bin/env python3
"""Guidance-accuracy statistics from the concalls promise database (stdlib only).
Usage: python3 -I calc/concalls_stats.py RUN_DIR  -> prints and writes calc/concalls_stats.out
Rules: only rows with stats=Y. 'Resolved' excludes Not yet due / Cannot be determined.
'On-target' = Exceeded + Delivered + Mostly delivered. Capex variance = (actual/guided - 1), signed (+ = overspend).
"""
import csv
import statistics
import sys
from collections import Counter, OrderedDict
from pathlib import Path

GROUP = {
    "capex": "Capex", "guidance policy": "Capex",
    "ARPU": "ARPU/tariff", "tariff": "ARPU/tariff",
    "5G launch": "Network/5G/tech", "5G coverage": "Network/5G/tech", "5G pace": "Network/5G/tech", "spectrum": "Network/5G/tech",
    "VoLTE": "Network/5G/tech", "3G shutdown": "Network/5G/tech", "5G SA/FWA": "Network/5G/tech", "FWA": "Network/5G/tech",
    "network": "Network/5G/tech", "Africa 4G": "Network/5G/tech", "5G timing": "Network/5G/tech",
    "M&A": "Corporate/M&A", "Africa IPO": "Corporate/M&A", "rights issue": "Corporate/M&A", "towers": "Corporate/M&A",
    "leadership": "Corporate/M&A", "cloud": "New ventures", "B2B": "Corporate/M&A", "Africa": "Corporate/M&A",
    "homes": "Homes", "leverage": "Balance sheet/returns", "debt": "Balance sheet/returns", "dividend": "Balance sheet/returns",
    "industry": "Industry calls", "ESG": "New ventures", "postpaid": "ARPU/tariff", "data centres": "New ventures",
    "Africa mobile money": "New ventures", "edge DCs": "New ventures", "promoter": "Balance sheet/returns",
}
CLASSES = ["Exceeded", "Delivered", "Mostly delivered", "Partially delivered", "Delayed", "Missed", "Abandoned/withdrawn",
           "Not yet due", "Cannot be determined"]
ON = {"Exceeded", "Delivered", "Mostly delivered"}


def fy(q):
    return int(q[-4:])


def period(q):
    y = fy(q)
    if y <= 2019:
        return "FY2016-FY2019 (Jio shock)"
    if y <= 2022:
        return "FY2020-FY2022 (repair/COVID)"
    return "FY2023-FY2027 (5G/post-5G)"


def main():
    run = Path(sys.argv[1])
    rows = [r for r in csv.DictReader(open(run / "specialists/concalls_workpapers/promise_database.csv")) if r["stats"] == "Y"]
    out = []
    p = out.append
    p("Rows in stats (stats=Y): %d" % len(rows))
    c = Counter(r["classification"] for r in rows)
    p("Classification counts (all stats rows): " + "; ".join("%s=%d" % (k, c.get(k, 0)) for k in CLASSES))
    res = [r for r in rows if r["resolved"] == "Y"]
    on = sum(1 for r in res if r["classification"] in ON)
    p("Resolved n=%d; on-target (Exceeded+Delivered+Mostly) n=%d (%.0f%%)" % (len(res), on, 100.0 * on / len(res)))
    late = sum(1 for r in res if r["classification"] == "Delayed")
    miss = sum(1 for r in res if r["classification"] in ("Missed", "Abandoned/withdrawn"))
    part = sum(1 for r in res if r["classification"] == "Partially delivered")
    p("Resolved: partially=%d (%.0f%%), delayed=%d (%.0f%%), missed+abandoned=%d (%.0f%%)" % (
        part, 100.0 * part / len(res), late, 100.0 * late / len(res), miss, 100.0 * miss / len(res)))
    p("")
    p("By topic group (resolved): group | n | on-target | partial | delayed | missed/abandoned | on-target %")
    groups = OrderedDict()
    for r in res:
        groups.setdefault(GROUP.get(r["topic"], r["topic"]), []).append(r)
    for g, rs in groups.items():
        o = sum(1 for r in rs if r["classification"] in ON)
        pa = sum(1 for r in rs if r["classification"] == "Partially delivered")
        d = sum(1 for r in rs if r["classification"] == "Delayed")
        m = sum(1 for r in rs if r["classification"] in ("Missed", "Abandoned/withdrawn"))
        p("%s | %d | %d | %d | %d | %d | %.0f%%" % (g, len(rs), o, pa, d, m, 100.0 * o / len(rs)))
    p("")
    p("By period of statement (resolved): period | n | on-target | on-target %")
    per = OrderedDict()
    for r in sorted(res, key=lambda x: fy(x["quarter"])):
        per.setdefault(period(r["quarter"]), []).append(r)
    for k, rs in per.items():
        o = sum(1 for r in rs if r["classification"] in ON)
        p("%s | %d | %d | %.0f%%" % (k, len(rs), o, 100.0 * o / len(rs)))
    p("")
    capex = [r for r in res if r["topic"] == "capex" and r["variance_pct"] and r["variance_basis"].startswith(("vs", "level", "3-year", "FY2024 vs", "direction"))]
    lv = [float(r["variance_pct"]) for r in capex if r["variance_basis"].startswith(("vs", "level", "3-year", "FY2024 vs"))]
    p("Capex level guidance (vs stated level/range): n=%d; variances %% = %s" % (len(lv), ", ".join("%.1f" % v for v in lv)))
    if lv:
        p("  mean %.1f%%; median %.1f%%; overspend count %d of %d" % (statistics.mean(lv), statistics.median(lv), sum(1 for v in lv if v > 0), len(lv)))
    pre = [float(r["variance_pct"]) for r in capex if r["variance_basis"].startswith(("vs", "level", "3-year", "FY2024 vs")) and fy(r["quarter"]) <= 2022]
    post = [float(r["variance_pct"]) for r in capex if r["variance_basis"].startswith(("vs", "level", "3-year", "FY2024 vs")) and fy(r["quarter"]) >= 2023]
    if pre:
        p("  statements FY2016-FY2022: n=%d median %.1f%%" % (len(pre), statistics.median(pre)))
    if post:
        p("  statements FY2023+: n=%d median %.1f%%" % (len(post), statistics.median(post)))
    dirn = [r for r in capex if r["variance_basis"].startswith("direction")]
    p("Capex direction calls ('lower next year'): n=%d; delivered %d; missed %d" % (
        len(dirn), sum(1 for r in dirn if r["classification"] in ON), sum(1 for r in dirn if r["classification"] == "Missed")))
    timing = [r for r in res if r["classification"] in ("Delayed",) or (r["deadline"] and r["classification"] in ON and r["topic"] not in ("capex",))]
    p("")
    p("Timeline-bearing non-capex items resolved: on-time/on-target %d, delayed %d" % (
        sum(1 for r in timing if r["classification"] in ON), sum(1 for r in timing if r["classification"] == "Delayed")))
    nyd = [r["promise_id"] for r in rows if r["classification"] == "Not yet due"]
    cbd = [r["promise_id"] for r in rows if r["classification"] == "Cannot be determined"]
    p("Not yet due: %d (%s); Cannot be determined: %d (%s)" % (len(nyd), ",".join(nyd), len(cbd), ",".join(cbd)))
    txt = "\n".join(out)
    (run / "calc/concalls_stats.out").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
