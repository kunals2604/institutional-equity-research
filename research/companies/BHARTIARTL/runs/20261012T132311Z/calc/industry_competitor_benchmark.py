#!/usr/bin/env python3
"""Competitor benchmark ratios from specialists/industry_workpapers/competitor_benchmark.csv (inputs cited there)."""
import csv, os
here = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(here, '..', 'specialists', 'industry_workpapers', 'competitor_benchmark.csv'))))
out = []
for r in rows:
    f = lambda k: float(r[k]) if r[k] else None
    rev, rev0, eb = f('fy2026_revenue_inr_cr'), f('fy2025_revenue_inr_cr'), f('fy2026_ebitda_inr_cr')
    s = "%s: revenue growth %s | EBITDA margin %s | share change FY16->FY26 %s pp" % (
        r['operator'], ('%.1f%%' % (100 * (rev / rev0 - 1))) if rev and rev0 else 'n/a', ('%.1f%%' % (100 * eb / rev)) if rev and eb else 'n/a',
        '%+.1f' % (float(r['trai_access_agr_share_q4fy26_pct']) - float(r['trai_access_agr_share_q4fy16_pct'])))
    print(s); out.append(s)
open(__file__.replace('.py', '.out.txt'), 'w').write('\n'.join(out) + '\n')
