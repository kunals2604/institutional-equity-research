"""Management specialist: capital-allocation, dilution and promoter-flow arithmetic (indicative).
Inputs are ledger claims (MGT-C0xx, CIO-C001..C003). Run: python3 calc/management_capital_allocation.py"""
from datetime import date
cr = 1e7  # INR per crore
# --- share counts (MGT-C012, MGT-C022, CIO-C002, MGT-C007/C008)
sh_2011 = 3_797_530_096; sh_2016 = 3_997_400_102; sh_now = 6_240_504_481  # fully paid, 24-Jul-2026 (CIO-C002)
# --- prices (MGT-C037, CIO-C001)
p_2011, p_2016, p_now = 357.40, 350.80, 1778.70
d_2011, d_2016, d_now = date(2011,3,31), date(2016,3,31), date(2026,10,12)
yrs16 = (d_now-d_2016).days/365.25; yrs11 = (d_now-d_2011).days/365.25
mcap16 = p_2016*sh_2016/cr; mcap11 = p_2011*sh_2011/cr; mcap_now = p_now*sh_now/cr
print(f"Market cap 31-Mar-2011 Rs cr: {mcap11:,.0f}; 31-Mar-2016: {mcap16:,.0f}; 12-Oct-2026: {mcap_now:,.0f}")
print(f"Share count growth 2016->2026: {sh_now/sh_2016-1:.1%} (CAGR {((sh_now/sh_2016)**(1/yrs16)-1):.2%}); 2011->2026: {sh_now/sh_2011-1:.1%}")
print(f"Price CAGR (unadjusted, ex-dividends) 2016->2026 over {yrs16:.2f}y: {((p_now/p_2016)**(1/yrs16)-1):.2%}; 2011->2026 over {yrs11:.2f}y: {((p_now/p_2011)**(1/yrs11)-1):.2%}")
print(f"Market-cap CAGR 2016->2026: {((mcap_now/mcap16)**(1/yrs16)-1):.2%}")
# --- equity issued FY2017-FY2027 (Rs crore)
eq = {
 "Rights 2019 @220 (MGT-C033)": 1_133_591_075*220/cr,
 "QIP Jan-2020 @445 (MGT-C034)": 323_595_505*445/cr,
 "FCCB US$1bn (converted to equity by Feb-2025; Rs 71,017 mn at issue) (MGT-C034)": 7101.7,
 "Warburg/Bharti Telemedia swap @600, non-cash (MGT-C035)": 36_469_913*600/cr,
 "Rights 2021 application money @133.75 (MGT-C041)": 392_287_662*133.75/cr,
 "Rights 2021 first & final call (MGT-C020)": 15695.98,
 "Google preferential @734 (MGT-C036)": 71_176_839*734/cr,
 "ICIL swap @1,923 for 16.31% Airtel Africa, non-cash (MGT-C006)": 146_761_335*1923/cr,
}
tot_eq = sum(eq.values())
for k,v in eq.items(): print(f"  {k}: {v:,.0f}")
print(f"Total equity issued FY2017-FY2027 (cash + non-cash) Rs cr: {tot_eq:,.0f}; of which cash: {tot_eq-eq['Warburg/Bharti Telemedia swap @600, non-cash (MGT-C035)']-eq['ICIL swap @1,923 for 16.31% Airtel Africa, non-cash (MGT-C006)']:,.0f}")
# --- consolidated net income attributable FY2017-FY2026 (Rs mn) (MGT-C038, MGT-C039)
ni = {2017:37997,2018:10990,2019:4095,2020:-321832,2021:-150835,2022:42549,2023:83459,2024:74670,2025:335561,2026:266952}
cum_ni = sum(ni.values())/10
# --- dividends declared per share (MGT-C040) x approx fully paid shares (ESTIMATE)
dps = {2017:1.0,2018:2.5,2019:2.5,2020:2.0,2021:0.0,2022:3.0,2023:4.0,2024:8.0,2025:16.0,2026:24.0}
sh_approx = {2017:3.997e9,2018:3.997e9,2019:3.997e9,2020:5.455e9,2021:5.494e9,2022:5.588e9,2023:5.656e9,2024:5.700e9,2025:5.702e9,2026:6.094e9}
divs = sum(dps[y]*sh_approx[y] for y in dps)/cr
print(f"Cumulative consolidated net income FY2017-FY2026 Rs cr: {cum_ni:,.0f}")
print(f"Cumulative dividends declared FY2017-FY2026 (ESTIMATE, DPS x approx shares) Rs cr: {divs:,.0f}")
ret = cum_ni - divs
print(f"Cumulative retained earnings (approx) Rs cr: {ret:,.0f}")
dm = mcap_now - mcap16
print(f"Change in market cap Mar-2016 -> 12-Oct-2026 Rs cr: {dm:,.0f}; less equity issued: {dm-tot_eq:,.0f}")
print("Value per rupee retained: " + ("not meaningful (retained earnings <= ~0)" if ret <= 0.05*abs(dm) else f"{(dm-tot_eq)/ret:.1f}x"))
# --- promoter flows (shareholding patterns; MGT-C011, MGT-C024, MGT-C008)
prom = {"Dec-2024":3_233_696_431,"Mar-2025":3_194_629_531,"Jun-2025":3_123_629_531,"Sep-2025":3_063_629_531,"Dec-2025":2_978_329_531,"Jun-2026":3_125_090_866}
print(f"Promoter group net shares sold Dec-2024 -> Dec-2025: {prom['Dec-2024']-prom['Dec-2025']:,} ({(prom['Dec-2024']-prom['Dec-2025'])/prom['Dec-2024']:.1%} of their holding)")
print(f"ICIL swap allotment as % of post-issue shares: {146_761_335/6_241_154_316:.2%}")
# implied value of Airtel Africa stake acquired
print(f"Implied consideration for 16.31% Airtel Africa: Rs cr {146_761_335*1923/cr:,.0f}; per AAF share Rs {146_761_335*1923/595_204_251:,.1f}")
# promoter share of 2019 rights
print(f"Promoter shares Mar-2019 -> Jun-2019 increase: {3_217_581_205-2_683_781_555:,}; entitlement at 19:67: {2_683_781_555*19/67:,.0f}; take-up vs entitlement {(3_217_581_205-2_683_781_555)/(2_683_781_555*19/67):.1%}")
# --- per-share book value and EPS (MGT-C061)
bv16, bv26, eps16, eps26 = 167.03, 244.6, 15.21, 46.0
print(f"BVPS CAGR FY2016-FY2026 (10y): {((bv26/bv16)**0.1-1):.2%}; EPS CAGR FY2016-FY2026 (10y, bases differ): {((eps26/eps16)**0.1-1):.2%}")
print(f"Independent directors share of board at 31-Mar-2026: {6/12:.0%}")
