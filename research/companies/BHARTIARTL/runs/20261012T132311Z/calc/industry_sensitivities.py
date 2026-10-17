#!/usr/bin/env python3
"""Industry specialist: first-order factor sensitivities for Bharti Airtel (FY2026 base).
Inputs (INR mn, Quarterly Report Q4FY2026, IND-C055 / IND-C058):
  India mobile revenue 1,129,954; India mobile EBITDA 680,346; India ex-towers revenue 1,403,734, EBITDA 821,926;
  India incl towers capex 396,539; consolidated revenue 2,109,728, EBITDA 1,212,676; Africa revenue 568,064, EBITDA 280,713.
Assumptions are labelled; outputs are approximate (ESTIMATE where an assumption drives them)."""
mob_rev, mob_ebitda = 1129954, 680346
ind_rev, ind_ebitda = 1403734, 821926
ind_capex = 396539
con_rev, con_ebitda = 2109728, 1212676
afr_rev, afr_ebitda = 568064, 280713
LF = 0.08          # licence fee as % of AGR (DoT licence terms; assumption for flow-through)
SUC = 0.02         # assumed blended spectrum usage charge on incremental AGR (assumption)
out = []
def p(s): print(s); out.append(s)
for hike, sub_loss in [(0.10, 0.0), (0.10, 0.02), (0.15, 0.02), (0.05, 0.0)]:
    d_rev = mob_rev * ((1 + hike) * (1 - sub_loss) - 1)
    d_ebitda = d_rev * (1 - LF - SUC)
    p("Tariff +%d%%, subscriber loss %d%%: mobile revenue %+.0f mn (%+.1f%%), EBITDA %+.0f mn (%+.1f%% of mobile EBITDA, %+.1f%% of consolidated EBITDA)" % (
        hike*100, sub_loss*100, d_rev, 100*d_rev/mob_rev, d_ebitda, 100*d_ebitda/mob_ebitda, 100*d_ebitda/con_ebitda))
for dep in (0.10, 0.25):
    p("African currencies -%d%% vs reporting currency: consolidated revenue %.1f%%, EBITDA %.1f%% (translation only; Africa = %.0f%% of revenue, %.0f%% of EBITDA)" % (
        dep*100, -100*dep*afr_rev/con_rev, -100*dep*afr_ebitda/con_ebitda, 100*afr_rev/con_rev, 100*afr_ebitda/con_ebitda))
for imp in (0.4, 0.6):
    d = ind_capex * imp * 0.10
    p("INR -10%% vs USD with %d%% import content in India capex (assumption): capex +%.0f mn = %.1f%% of India ex-tower EBITDA" % (imp*100, d, 100*d/ind_ebitda))
d = ind_rev * 0.01
p("Licence fee +/-1 pp of AGR on India ex-tower revenue: %.0f mn = %.1f%% of India ex-tower EBITDA" % (d, 100*d/ind_ebitda))
open(__file__.replace('.py', '.out.txt'), 'w').write('\n'.join(out) + '\n')
