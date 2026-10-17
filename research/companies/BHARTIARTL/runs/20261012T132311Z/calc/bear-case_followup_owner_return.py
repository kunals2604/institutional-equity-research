"""Owner's 5-year return at a constant (or stated) EV/EBITDA, independent of the DCF convergence assumption.
EV here includes minorities at market value (draft DCF input) so the multiple is like-for-like at both ends.
Also: Poisson base rate for tariff rounds. Run: python3 calc/bear-case_followup_owner_return.py > calc/bear-case_followup_owner_return.out"""
import math
PRICE, SH = 1778.70, 6240.504481          # CIO-C001, CIO-C002 (million shares)
MCAP = PRICE * SH                          # INR mn
ND0 = 1572396.0                            # draft DCF net debt incl. leases (calc/valuation_dcf_inputs.json)
MI0 = 1089801.0                            # draft DCF minorities at market value
EBITDA0 = 1264036.0                        # approx TTM EBITDA (BEAR-C054)
EV0 = MCAP + ND0 + MI0
m0 = EV0 / EBITDA0
print(f"EV incl. market minorities INR crore {EV0/10:,.0f}; EV/TTM EBITDA {m0:.2f}x")
DPS0 = 24.0
def irr(cfs):
    lo, hi = -0.9, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        npv = sum(c / (1 + mid) ** t for t, c in enumerate(cfs))
        lo, hi = (mid, hi) if npv > 0 else (lo, mid)
    return mid
print("\nEBITDA CAGR | exit multiple | annual net-debt reduction INR cr | 5y IRR incl. dividends")
for g in (0.08, 0.10, 0.12):
    for mult in (m0, 9.3, 8.2):
        for dred in (0.0, 20000.0):
            e5 = EBITDA0 * (1 + g) ** 5
            nd5 = ND0 - 5 * dred * 10
            mi5 = MI0 * (1 + g) ** 5
            eq5 = mult * e5 - nd5 - mi5
            p5 = eq5 / SH
            divs = [DPS0 * (1 + g) ** t for t in range(1, 6)]
            cfs = [-PRICE] + divs[:-1] + [divs[-1] + p5]
            print(f"{g:.0%} | {mult:.1f}x | {dred:,.0f} | value/share {p5:,.0f}; IRR {irr(cfs):.1%}")
# Tariff-round base rate: rounds Dec-2019, Nov-2021, Jul-2024 (search corroboration in BEAR-C082); window Dec-2019 to Oct-2026
yrs = (2026 + 10/12) - (2019 + 11/12)
lam_per_yr = 3 / yrs
lam5 = lam_per_yr * 5
p0 = math.exp(-lam5); p1 = lam5 * p0
print(f"\nTariff rounds: 3 in {yrs:.1f} years -> {lam_per_yr:.2f}/yr; over 5 years lambda {lam5:.2f}: P(0) {p0:.0%}, P(>=1) {1-p0:.0%}, P(>=2) {1-p0-p1:.0%}")
lam5b = 2 / yrs * 5   # sensitivity: count only two full rounds (treat 2019 as end of the price war)
print(f"Sensitivity (2 rounds in window): lambda {lam5b:.2f}: P(>=1) {1-math.exp(-lam5b):.0%}, P(>=2) {1-math.exp(-lam5b)*(1+lam5b):.0%}")
