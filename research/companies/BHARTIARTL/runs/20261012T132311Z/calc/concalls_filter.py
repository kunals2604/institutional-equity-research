#!/usr/bin/env python3
"""Sentence-level discovery filter over a compact, page-marked transcript.

Prints, with page locators: (Q) every question sentence (analyst-concern tracker), and
(M) every sentence that is forward-looking AND mentions a quantity or a tracked topic.
Discovery aid only: every promise-database row is confirmed against the cited page.
Usage: python3 -I concalls_filter.py COMPACT_FILE [--mode q|m|both]
"""
import re
import sys

FWD = re.compile(r"\b(will|expect\w*|target\w*|guid\w*|aim\w*|aspir\w*|plan\w*|intend\w*|commit\w*|by the end|by end|by (?:march|december|june|september|20\d\d)|next (?:year|quarter|few|\d+|financial|fiscal|couple)|going forward|over the (?:next|coming)|should (?:be|come|go|start|see)|outlook|peak\w*|trajector\w*|in the coming|ambition|roadmap|timeline|going to|on track)\b", re.I)
TOPIC = re.compile(r"(\d|capex|capital expenditure|ARPU|tariff|price increase|price hike|repair|debt|leverage|dividend|5G|4G|homes?\b|broadband|FWA|fibre|fiber|data cent|Nxtra|Africa|Indus|Infratel|margin|EBITDA|free cash|payments bank|DTH|digital TV|enterprise|B2B|spectrum|AGR|rights|IPO|merger|listing|postpaid|smartphone|market share|revenue share|churn|cost|Hexacom|satellite|OneWeb|IoT|cloud|cyber|deleverag|prepay|buyback|payout)", re.I)
BOILER = re.compile(r"forward[- ]looking statements|safe harbor|listen-only|unmute|introduce yourself|next question|Republished with permission", re.I)


def main():
    path = sys.argv[1]
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "both"
    text = open(path, errors="ignore").read()
    qs, ms = [], []
    for m in re.finditer(r"\[p\.(\d+)\]\s(.*?)(?=\n\[p\.\d+\]|\Z)", text, re.S):
        pg, body = int(m.group(1)), m.group(2)
        body = re.sub(r"^Final Transcript .*?(Call|Webinar)\s", "", body)
        for s in re.split(r"(?<=[\.\?!])\s+", body):
            s = s.strip()
            if len(s) < 30 or BOILER.search(s):
                continue
            if s.endswith("?"):
                qs.append("Q p.%d: %s" % (pg, s[:300]))
            elif FWD.search(s) and TOPIC.search(s):
                ms.append("M p.%d: %s" % (pg, s[:600]))
    if mode in ("q", "both"):
        print("#### QUESTIONS")
        print("\n".join(qs))
    if mode in ("m", "both"):
        print("#### FORWARD-LOOKING + TOPIC SENTENCES")
        print("\n".join(ms))


if __name__ == "__main__":
    main()
