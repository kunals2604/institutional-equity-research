"""Downside-floor arithmetic (special-situations). INR crore. Not a valuation: a stress floor using historical trough multiples.
India SA EBITDAaL (incl. Indus at 100%) Q1FY2027 annualised; NCI of Indus/Hexacom deducted at market; Airtel Africa stake at market and stressed."""
sh = 6_240_504_481                       # CIO-C002
india_ebitdaal = 227_875*4/10            # SPS-C073 (INR mn -> cr)
india_nd = 693_145/10                    # SPS-C073 net debt ex leases
indus_nci = 99_103*(1-0.51256)           # SPS-C072/SPS-C049 (Indus mcap from sotp.out)
hexa_nci = 76_065*0.30                   # Hexacom mcap from sotp.out
aaf_stake_mkt = 105_574                  # sotp.out
px = 1778.70
print("India SA annualised EBITDAaL %.0f cr; net debt ex leases %.0f cr" % (india_ebitdaal, india_nd))
for mult in (6.65, 8.0, 10.0):
    for ebit_cut in (0.0, 0.15):
        for aaf_haircut in (0.0, 0.5):
            eq = india_ebitdaal*(1-ebit_cut)*mult - india_nd - indus_nci - hexa_nci + aaf_stake_mkt*(1-aaf_haircut)
            print("mult %.2fx | EBITDAaL cut %2.0f%% | AAF haircut %2.0f%% -> equity %.0f cr = INR %.0f/sh (%+.0f%% vs price)" % (mult, 100*ebit_cut, 100*aaf_haircut, eq, eq*1e7/sh, 100*(eq*1e7/sh/px-1)))
# implied multiple at current price (AAF at market)
ev = px*sh/1e7 - aaf_stake_mkt + india_nd + indus_nci + hexa_nci
print("Implied India SA EV/EBITDAaL at current price (AAF at market): %.1fx" % (ev/india_ebitdaal))
print("India net debt ex leases per share: INR %.0f; listed stakes per share 336 vs price %.1f%%" % (india_nd*1e7/sh, 100*336/px))
