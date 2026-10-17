#!/usr/bin/env python3
"""Industry specialist: decompose Airtel's India mobile growth into industry growth and share change,
and into subscriber and ARPU growth. Inputs (page-verified workpapers):
  specialists/industry_workpapers/trai_access_agr_q4.csv   (TRAI, Q4 access AGR by operator; IND-C001..C016)
  specialists/industry_workpapers/airtel_india_mobile_kpis.csv (Airtel Q4 ARPU, customers, annual India mobile revenue)
Method: log-decomposition. ln(Bharti_t/Bharti_0) = ln(Industry_t/Industry_0) + ln(Share_t/Share_0).
Reported revenue growth: ln(Rev_t/Rev_0) vs ln(ARPU_t/ARPU_0) + ln(Customers_t/Customers_0) (Q4 snapshot proxy; residual = mix, timing, non-ARPU revenue, definition changes)."""
import csv, math, os
here = os.path.dirname(os.path.abspath(__file__)); wp = os.path.join(here, '..', 'specialists', 'industry_workpapers')
agr = {r['fy']: r for r in csv.DictReader(open(os.path.join(wp, 'trai_access_agr_q4.csv')))}
kpi = {r['fy']: r for r in csv.DictReader(open(os.path.join(wp, 'airtel_india_mobile_kpis.csv')))}
def cagr(a, b, n): return (b / a) ** (1.0 / n) - 1
out = []
def p(*a):
    s = ' '.join(str(x) for x in a); print(s); out.append(s)
p('== A. TRAI Q4 access AGR: industry vs Bharti share (annualised log contributions)')
for a, b in [('FY2013', 'FY2026'), ('FY2016', 'FY2026'), ('FY2016', 'FY2019'), ('FY2019', 'FY2026'), ('FY2021', 'FY2026'), ('FY2024', 'FY2026')]:
    i0, i1 = float(agr[a]['access_total']), float(agr[b]['access_total'])
    b0, b1 = float(agr[a]['bharti']), float(agr[b]['bharti'])
    n = int(b[2:]) - int(a[2:])
    s0, s1 = b0 / i0, b1 / i1
    p('%s->%s (%dy): industry CAGR %.1f%% | Bharti CAGR %.1f%% | share %.1f%%->%.1f%% | contribution of industry %.1f pp/yr, share %.1f pp/yr (log)' % (
        a, b, n, 100 * cagr(i0, i1, n), 100 * cagr(b0, b1, n), 100 * s0, 100 * s1, 100 * math.log(i1 / i0) / n, 100 * math.log(s1 / s0) / n))
p('== B. Industry access AGR trough: FY2016 Q4 -> FY2018 Q4 change %.1f%%; recovery FY2018->FY2026 CAGR %.1f%%' % (
    100 * (float(agr['FY2018']['access_total']) / float(agr['FY2016']['access_total']) - 1), 100 * cagr(float(agr['FY2018']['access_total']), float(agr['FY2026']['access_total']), 8)))
p('== C. Airtel reported India mobile revenue vs ARPU x customers (Q4 snapshots)')
for a, b in [('FY2016', 'FY2026'), ('FY2019', 'FY2026'), ('FY2021', 'FY2026'), ('FY2024', 'FY2026'), ('FY2014', 'FY2016'), ('FY2016', 'FY2019')]:
    r0, r1 = float(kpi[a]['india_mobile_revenue_rs_mn']), float(kpi[b]['india_mobile_revenue_rs_mn'])
    a0, a1 = float(kpi[a]['q4_arpu_rs']), float(kpi[b]['q4_arpu_rs'])
    c0, c1 = float(kpi[a]['q4_customers_000']), float(kpi[b]['q4_customers_000'])
    n = int(b[2:]) - int(a[2:])
    lr, la, lc = math.log(r1 / r0) / n, math.log(a1 / a0) / n, math.log(c1 / c0) / n
    p('%s->%s: revenue CAGR %.1f%% | ARPU CAGR %.1f%% | customers CAGR %.1f%% | log pp/yr: ARPU %.1f, customers %.1f, residual %.1f' % (
        a, b, 100 * cagr(r0, r1, n), 100 * cagr(a0, a1, n), 100 * cagr(c0, c1, n), 100 * la, 100 * lc, 100 * (lr - la - lc)))
p('== D. Annualised Q4 Bharti TRAI AGR vs reported India mobile revenue (scope check)')
for fy in ['FY2016', 'FY2019', 'FY2021', 'FY2024', 'FY2025', 'FY2026']:
    p('%s: 4 x Q4 TRAI Bharti AGR = Rs %.0f cr; reported India mobile revenue = Rs %.0f cr; ratio %.2f' % (
        fy, 4 * float(agr[fy]['bharti']), float(kpi[fy]['india_mobile_revenue_rs_mn']) / 10, 4 * float(agr[fy]['bharti']) / (float(kpi[fy]['india_mobile_revenue_rs_mn']) / 10)))
open(os.path.join(here, 'industry_growth_decomposition.out.txt'), 'w').write('\n'.join(out) + '\n')
