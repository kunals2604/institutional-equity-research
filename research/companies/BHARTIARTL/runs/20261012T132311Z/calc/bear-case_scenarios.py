"""Bear-case scenario arithmetic for BHARTIARTL (run 20261012T132311Z).
All INR million unless stated. Inputs cite ledger claim IDs. Run: python3 calc/bear-case_scenarios.py > calc/bear-case_scenarios.out
Assumptions marked ASSUMPTION are analyst choices (ESTIMATE), not facts."""
PRICE = 1778.70                      # CIO-C001
SHARES = 6240.504481                 # million, CIO-C002 (fully paid, Jul-2026)
MCAP = PRICE * SHARES                # INR million
# FY2026 consolidated (BEAR-C001..C005, C051; Q4FY2026 Quarterly Report)
EBITDA26 = 1212676.0                 # KPI EBITDA, excl. other income (BEAR-C002)
OTHER_INC26 = 28173.0
DA26 = 527108.0
FIN26 = 215553.0
ASSOC26 = 3645.0                     # share of profit of associates/JVs (added)
PBT_PRE_EXC26 = 485902.0
TAX_RATE = 113499.0 / 451727.0       # FY2026 tax / PBT
NCI_SHARE26 = 71276.0 / 338228.0     # NCI share of PAT FY2026
NI_PRE_EXC26 = 269042.0              # attributable, before exceptional (BEAR-C003)
NI_Q1FY26 = 59479.0                  # no exceptional in Q1FY26
NI_Q1FY27 = 81674.0 + (3534.0 - 738.0)   # attributable + exceptional net of NCI (BEAR-C004)
AFR_NI26 = 60013.0                   # Africa reported net income (BEAR-C047)
ICIL_STAKE = 0.1631                  # BEAR-C013
NET_DEBT_INCL_LEASES = 1647888.0     # 31-Mar-2026 (BEAR-C005)
BOOK_NCI_POST_SWAP = 469068.0 - (282222.0 - 232602.0)   # Mar-26 NCI less NCI reduction from ICIL swap (BEAR-C013)
CFO26, PPE26, SPEC26, LEASE26, INT26 = 1222296.0, 440076.0, 23932.0, 67197.0, 148876.0   # BEAR-C051
MOB_IND_REV26 = 1129954.0            # BEAR-C049
AFR_EBITDA26 = 280713.0              # Q4FY2026 QR Africa EBITDA (BEAR-C047 source p.34)
DPS = 24.0                           # FY2026 final dividend per share

def p(label, v, fmt="{:,.1f}"):
    print(f"{label}: {fmt.format(v)}")

print("== 1. Market value and trailing multiples")
p("Market cap INR crore", MCAP / 10)
ttm_ni = NI_PRE_EXC26 - NI_Q1FY26 + NI_Q1FY27
icil_uplift = ICIL_STAKE * AFR_NI26 * 0.75   # ASSUMPTION: ~3 quarters not yet in TTM
pf_ni = ttm_ni + icil_uplift
pf_eps = pf_ni / SHARES
p("TTM attributable NI before exceptional (Q2FY26-Q1FY27) INR crore", ttm_ni / 10)
p("Pro-forma TTM NI incl. ICIL uplift INR crore", pf_ni / 10)
p("Pro-forma TTM EPS INR", pf_eps, "{:.1f}")
p("Trailing P/E on pro-forma EPS (x)", PRICE / pf_eps)
ttm_ebitda = EBITDA26 - 281668.0 + (342094.0 - 9066.0)   # Q1FY27 statutory EBITDA less other income
p("Approx TTM EBITDA INR crore", ttm_ebitda / 10)
ev = MCAP + NET_DEBT_INCL_LEASES
p("EV (company convention: mcap + net debt incl leases, no NCI) INR crore", ev / 10)
p("EV/EBITDA TTM (company convention) x", ev / ttm_ebitda)
p("EV/EBITDA TTM incl. book NCI (floor for minority value) x", (ev + BOOK_NCI_POST_SWAP) / ttm_ebitda)
fcfe = CFO26 - PPE26 - SPEC26 - LEASE26 - INT26
p("FY2026 FCF after capex, spectrum, leases, interest INR crore", fcfe / 10)
p("  as % of market cap", 100 * fcfe / MCAP)
p("  after deducting NCI share (approx) as % of mcap", 100 * fcfe * (1 - NCI_SHARE26) / MCAP)

def eps_path(years, g_ebitda, g_da=0.09, g_fin=-0.03, nci=0.18, ebitda_adj=0.0, start=EBITDA26):
    e = start * (1 + g_ebitda) ** years + ebitda_adj
    pbt = e + OTHER_INC26 - DA26 * (1 + g_da) ** years - FIN26 * (1 + g_fin) ** years + ASSOC26
    pat = pbt * (1 - TAX_RATE)
    return e, pat * (1 - nci) / SHARES

print("\n== 2. Expectations gap: consensus FY2028 EPS 82.26 (BEAR-C040)")
check_e, check_eps = eps_path(0, 0.0, nci=NCI_SHARE26)
p("Model check: FY2026 EPS reconstructed (pre-exceptional, FY26 NCI share) INR", check_eps, "{:.1f}")
for g in (0.08, 0.10, 0.12, 0.14):
    e, eps = eps_path(2, g)
    print(f"EBITDA growth {g:.0%}/yr -> FY2028 EBITDA INR crore {e/10:,.0f}, EPS INR {eps:.1f} ({100*(eps/82.26-1):+.0f}% vs consensus)")
lo, hi = 0.0, 0.5
for _ in range(60):
    mid = (lo + hi) / 2
    if eps_path(2, mid)[1] < 82.26: lo = mid
    else: hi = mid
p("EBITDA CAGR FY2026-FY2028 needed to reach consensus FY2028 EPS (D&A +9%/yr, finance -3%/yr, NCI 18%) %", 100 * mid)

print("\n== 3. Three-year scenarios (horizon ~FY2029; value = FY2029 EPS x exit P/E + cumulative dividends)")
mob29 = MOB_IND_REV26 * 1.07 ** 3      # ASSUMPTION: 7%/yr mobile revenue growth without repair
afr29 = AFR_EBITDA26 * 1.10 ** 3
scen = [
 ("BASE-like (repair arrives, 13% EBITDA CAGR, P/E 28x)", dict(g_ebitda=0.13), 28, 3 * 28.0),
 ("B1 No tariff repair + capex super-cycle (9% EBITDA, D&A +11%/yr, P/E 22x)", dict(g_ebitda=0.09, g_da=0.11), 22, 3 * 26.0),
 ("B2 Competitive reset: B1 + India mobile ARPU -10% by FY2029 (100% flow-through), P/E 18x", dict(g_ebitda=0.09, g_da=0.11, ebitda_adj=-0.10 * mob29), 18, 3 * 24.0),
 ("B3 Correlated: B2 + Africa INR EBITDA -30% (FX) + finance cost flat, P/E 16x", dict(g_ebitda=0.09, g_da=0.11, g_fin=0.0, ebitda_adj=-0.10 * mob29 - 0.30 * afr29 * 0.79), 16, 3 * 20.0),
]
for name, kw, pe, divs in scen:
    e, eps = eps_path(3, **kw)
    v = eps * pe + divs
    irr = (v / PRICE) ** (1 / 3) - 1
    print(f"{name}\n   FY2029 EBITDA INR crore {e/10:,.0f}; EPS {eps:.1f}; value+divs INR {v:,.0f}; vs price {100*(v/PRICE-1):+.0f}%; 3y IRR {100*irr:+.1f}%")

print("\n== 4. Severe 2016-2019 replay on EV basis (company convention)")
for drop, mult, nd in ((0.20, 8.0, 2000000.0), (0.15, 8.9, 1900000.0), (0.10, 7.75, 1800000.0)):
    e = EBITDA26 * (1 - drop)
    eq = e * mult - nd
    print(f"EBITDA -{drop:.0%} vs FY2026 ({e/10:,.0f} cr) x {mult}x - net debt incl leases {nd/10:,.0f} cr -> INR {eq/SHARES:,.0f}/share ({100*(eq/SHARES/PRICE-1):+.0f}%)")
hist = {"FY2016": (34168, 6077), "FY2019": (26294, 410)}   # BEAR-C016, BEAR-C019 (INR crore)
p("History: EBITDA change FY2016->FY2019 %", 100 * (hist["FY2019"][0] / hist["FY2016"][0] - 1))
p("History: net income change FY2016->FY2019 %", 100 * (hist["FY2019"][1] / hist["FY2016"][1] - 1))
p("History: revenue change FY2016->FY2019 % (96,532 -> 80,780)", 100 * (80780 / 96532 - 1))

print("\n== 5. Dilution and quasi-debt")
p("Share count change FY2019 (3,998m) -> Jul-2026 %", 100 * (SHARES / (1999.0 * 10 / 5) - 1))
unindemnified_agr = 347042.0 - 166725.0 - 24886.0     # BEAR-C027
contingent = 191842.0; otsc = 66065.0                  # BEAR-C028, BEAR-C029
p("Unindemnified sub-judice AGR provision (outside net debt) INR crore", unindemnified_agr / 10)
p("  per share INR", unindemnified_agr / SHARES)
p("Contingent liabilities + OTSC balance, 50% crystallisation, per share INR", 0.5 * (contingent + otsc) / SHARES)
p("  as % of price", 100 * 0.5 * (contingent + otsc) / SHARES / PRICE)
nbfc_airtel = 200000.0 * 0.70                          # BEAR-C012
p("Airtel share of NBFC capital INR crore", nbfc_airtel / 10)
p("  per share INR", nbfc_airtel / SHARES)

print("\n== 6. Mobile India pre-tax return on cumulative (gross) investment, Q4FY2026 annualised")
p("EBIT x4 / cumulative investment %", 100 * 93219.0 * 4 / 3792545.0)

print("\n== 7. Sensitivity: 10% India mobile ARPU change at FY2029")
d_ebitda = 0.10 * mob29
d_eps = d_ebitda * (1 - TAX_RATE) * (1 - 0.18) / SHARES
p("EBITDA change INR crore", d_ebitda / 10)
p("EPS change INR", d_eps, "{:.1f}")
p("Value change at 18x INR", d_eps * 18, "{:.0f}")
p("Value change at 22x INR", d_eps * 22, "{:.0f}")

print("\n== 8. Indicator current values")
p("FY2026 capex / revenue % (475,218 / 2,109,728)", 100 * 475218.0 / 2109728.0)
p("Q4FY2026 capex / revenue % (160,656 / 553,832)", 100 * 160656.0 / 553832.0)
