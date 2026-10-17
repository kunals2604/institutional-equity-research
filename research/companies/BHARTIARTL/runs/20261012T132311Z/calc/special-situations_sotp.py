"""Listed-holdings look-through and implied India multiple at 12-Oct-2026 (special-situations).
All INR crore unless stated (1 crore = 10 million). Inputs cite ledger IDs."""
CR = 1e7
px_airtel = 1778.70                 # CIO-C001
sh_airtel = 6_240_504_481           # CIO-C002 (fully paid, 24-Jul-2026; partly paid immaterial)
gbpinr = 126.74                     # SPS-C048
# Airtel Africa
aaf_px_gbp = 2.901                  # SPS-C047 (290.1p)
aaf_sh = 3_629_635_395              # SPS-C046
aaf_stake = 0.7911                  # SPS-C037 (30-Jun-2026; buyback continuing)
# Airtel Money
am_mcap_gbp = 5.3e9                 # SPS-C044
aaf_in_am = 0.7785                  # SPS-C043
# Indus
indus_px = 375.65; indus_sh = 2_638_162_757; indus_stake = 0.51256   # SPS-C049, SPS-C051, SPS-C028
# Hexacom
hexa_px = 1521.30; hexa_sh = 500_000_000; hexa_stake = 0.70          # SPS-C049, SPS-C052, SPS-C029
# Nxtra (estimate)
nx_post_usd = 3.1e9; nx_new_usd = 1.0e9; nx_airtel_new_usd = 0.29e9; nx_airtel_pre = 0.7596  # SPS-C041, SPS-C029
usdinr = 94.35                      # IR pack Q1FY2027 RBI reference rate for quarter ended 30-Jun-2026 (SPS-C072)
# India SA (incl. passive infra) Q1FY2027
india_ebitdaal_q = 227_875          # INR mn, SPS-C073
india_nd_exlease = 693_145          # INR mn, SPS-C073

mcap = px_airtel*sh_airtel/CR
aaf_mcap = aaf_px_gbp*aaf_sh*gbpinr/CR
aaf_val = aaf_mcap*aaf_stake
am_mcap = am_mcap_gbp*gbpinr/CR
am_look = am_mcap*aaf_in_am*aaf_stake
indus_mcap = indus_px*indus_sh/CR; indus_val = indus_mcap*indus_stake
hexa_mcap = hexa_px*hexa_sh/CR; hexa_val = hexa_mcap*hexa_stake
nx_pre_usd = nx_post_usd - nx_new_usd
nx_airtel_post = (nx_airtel_pre*nx_pre_usd + nx_airtel_new_usd)/nx_post_usd
nx_val = nx_post_usd*nx_airtel_post*usdinr/CR
ps = lambda x: x*CR/sh_airtel
print("Airtel market cap: %.0f cr (%.1f per share)" % (mcap, px_airtel))
print("Airtel Africa mcap: %.0f cr; Airtel stake value %.0f cr = %.0f/sh = %.1f%% of Airtel mcap" % (aaf_mcap, aaf_val, ps(aaf_val), 100*aaf_val/mcap))
print("Airtel Money IPO mcap: %.0f cr; Airtel look-through (%.2f%%) %.0f cr = %.0f/sh; AM as %% of AAF mcap %.1f%%" % (am_mcap, 100*aaf_in_am*aaf_stake, am_look, ps(am_look), 100*am_mcap/aaf_mcap))
print("AAF ex-Airtel-Money implied equity value: %.0f cr" % (aaf_mcap - am_mcap*aaf_in_am))
print("Indus mcap %.0f cr; Airtel stake %.0f cr = %.0f/sh = %.1f%%" % (indus_mcap, indus_val, ps(indus_val), 100*indus_val/mcap))
print("Hexacom mcap %.0f cr; Airtel stake %.0f cr = %.0f/sh = %.1f%%" % (hexa_mcap, hexa_val, ps(hexa_val), 100*hexa_val/mcap))
listed = aaf_val+indus_val+hexa_val
print("Listed stakes total %.0f cr = %.0f/sh = %.1f%% of Airtel mcap" % (listed, ps(listed), 100*listed/mcap))
print("Nxtra: pre-money est %.2f bn USD; Airtel post-deal stake est %.1f%%; value at deal price %.0f cr = %.0f/sh" % (nx_pre_usd/1e9, 100*nx_airtel_post, nx_val, ps(nx_val)))
# implied India SA EV/EBITDAaL (Indus consolidated at 100%; NCI of Indus and Hexacom at market)
for disc in (0.0, 0.2, 0.3):
    india_eq = mcap - aaf_val*(1-disc)
    ev = india_eq + india_nd_exlease/10 + indus_mcap*(1-indus_stake) + hexa_mcap*(1-hexa_stake)
    ebitdaal = india_ebitdaal_q*4/10
    print("AAF stake discount %2.0f%%: implied India SA equity %.0f cr, EV %.0f cr, EV/annualised EBITDAaL %.1fx" % (100*disc, india_eq, ev, ev/ebitdaal))
