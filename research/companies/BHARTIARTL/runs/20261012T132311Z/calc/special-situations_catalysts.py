"""Illustrative per-share effects of catalysts (special-situations). ESTIMATES, not forecasts. INR crore."""
sh = 6_240_504_481                      # CIO-C002
mob_rev_q = 299_289/10                  # SPS-C085 Mobile Services India Q1FY2027 revenue, INR cr
ps = lambda x: x*1e7/sh
print("Tariff repair: incremental annual EBITDA and value per share")
for uplift in (0.05, 0.10, 0.15):
    for flow in (0.80, 0.90):           # flow-through after licence fee/SUC (~8% of AGR), churn and down-trading
        d_ebitda = mob_rev_q*4*uplift*flow
        for mult in (8.0, 10.0):
            print("ARPU +%2.0f%% | flow %.0f%% | dEBITDA %.0f cr | at %.0fx: %.0f cr = INR %.0f/sh" % (100*uplift, 100*flow, d_ebitda, mult, d_ebitda*mult, ps(d_ebitda*mult)))
aaf_val = 105_574                       # SPS-C075
print("Airtel Africa stake re-rating +/-20%%: INR %.0f/sh" % ps(aaf_val*0.2))
print("Holding discount 20%%/30%% on AAF stake: INR %.0f / %.0f per sh" % (ps(aaf_val*0.2), ps(aaf_val*0.3)))
am_look = 41_369                        # SPS-C076
print("Airtel Money look-through +/-25%%: INR %.0f/sh" % ps(am_look*0.25))
print("Nxtra stake at deal mark (SPS-C077): INR %.0f/sh" % ps(17_786))
dps = 24.0; px = 1778.70
print("FY2026 DPS yield at CIO-C001: %.2f%%; FY2025 DPS 16 -> FY2026 24: %+.0f%%" % (100*dps/px, 100*(24/16-1)))
print("Q4FY2026 regulatory levies charge 31,607 mn = INR %.1f/sh" % ps(3160.7))
# Additional derived ratios cited in the report
aaf_mcap = 133_452; usdinr = 94.35      # sotp.out; SPS-C072
bb = 110e6*usdinr/1e7
print("AAF USD110m buyback tranche = %.0f cr = %.2f%% of AAF mcap; Airtel stake 79.11%% -> approx %.2f%% if all cancelled" % (bb, 100*bb/aaf_mcap, 100*0.7911/(1-bb/aaf_mcap)))
print("Value of +1pp AAF stake: INR %.1f/sh" % ps(aaf_mcap*0.01))
print("Non-listed (India ex listed stakes) share of Airtel mcap: %.1f%%" % (100*(1-209_615/1_109_999)))
print("ICIL new shares as %% of post-issue fully paid count (CIO-C002): %.2f%%" % (100*146_761_335/sh))
