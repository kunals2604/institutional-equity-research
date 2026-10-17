#!/usr/bin/env python3
"""Industry specialist: TRAI access-AGR (revenue) share, wireless subscriber share, CR3 and HHI.
Inputs: specialists/industry_workpapers/trai_access_agr_q4.csv, trai_wireless_subs_march.csv
(transcribed from TRAI Performance Indicator Reports, page-verified in trai_page_verification_log.txt).
HHI uses only providers listed individually; unlisted residual is treated as fragmented (lower bound).
Vodafone + Idea are combined pre-merger (merged Aug-2018) for a like-for-like 'Vodafone Idea' series."""
import csv, os
here = os.path.dirname(os.path.abspath(__file__))
wp = os.path.join(here, '..', 'specialists', 'industry_workpapers')
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
OPS = ['bharti','jio','vodafone_idea','bsnl','mtnl','tata','aircel','rcom','telenor']
def run(name, totcol, out):
    rows = []
    for r in csv.DictReader(open(os.path.join(wp, name))):
        tot = f(r[totcol]); v = {k: f(r.get(k)) for k in OPS}
        if v['vodafone_idea'] is None and (f(r.get('vodafone')) or f(r.get('idea'))):
            v['vodafone_idea'] = (f(r.get('vodafone')) or 0) + (f(r.get('idea')) or 0)
        sh = {k: (100*v[k]/tot if v[k] is not None else None) for k in OPS}
        pos = [max(s, 0) for s in sh.values() if s is not None]
        hhi = sum(s*s for s in pos)
        top3 = sum(sorted(pos, reverse=True)[:3])
        rows.append([r['fy']] + ['%.2f' % sh[k] if sh[k] is not None else '' for k in ['bharti','jio','vodafone_idea','bsnl']] + ['%.1f' % top3, '%.0f' % hhi, '%.2f' % tot])
    with open(os.path.join(here, out), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['fy','bharti_share_pct','jio_share_pct','vodafone_idea_share_pct','bsnl_share_pct','cr3_pct','hhi_listed','total'])
        w.writerows(rows)
    for r in rows: print(name.split('_')[1], *r)
run('trai_access_agr_q4.csv', 'access_total', 'industry_agr_share.out.csv')
run('trai_wireless_subs_march.csv', 'total', 'industry_subs_share.out.csv')
