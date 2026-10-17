"""Event-window price reactions and ICIL-swap economics (special-situations). Reads cached Yahoo JSON (tier 5)."""
import json, datetime, glob, sys
C = "research/companies/BHARTIARTL/runs/20261012T132311Z/_cache/special-situations/"
def load(pat):
    f = glob.glob(C + pat)[0]
    d = json.load(open(f))["chart"]["result"][0]
    out = {}
    for t, c in zip(d["timestamp"], d["indicators"]["quote"][0]["close"]):
        if c is not None:
            out[datetime.datetime.utcfromtimestamp(t + 19800).date()] = c
    return out
air = load("*BHARTIARTL-NS-since-2000.json"); nif = load("*5ENSEI-since-2000.json")
aaf = load("*AAF-L-since-IPO.json"); fx = load("*GBPINR-1y.json")
days = sorted(set(air) & set(nif))
def idx(d):
    for i, x in enumerate(days):
        if x >= d: return i
def win(d, pre=1, post=1):
    i = idx(d); a, b = days[i-pre], days[min(i+post, len(days)-1)]
    ra = air[b]/air[a]-1; rn = nif[b]/nif[a]-1
    return a, b, ra, rn, ra-rn
E = [("2019-10-24","SC AGR judgment"),
     ("2021-04-14","Telecom demerger scheme approved (later withdrawn)"),("2021-08-30","Rights issue INR 21,000cr announced (board 29-Aug-2021, Sunday)"),
     ("2021-11-22","Prepaid tariff hike 20-25% announced"),("2022-01-28","Google USD 1bn partnership"),
     ("2024-06-28","Tariff hike 10-21% announced"),("2024-11-19","Indus becomes subsidiary"),
     ("2025-12-18","Final call on partly paid shares approved"),("2026-03-30","Nxtra USD 1bn raise"),
     ("2026-05-13","Q4FY26 results + ICIL swap board approval"),("2026-09-23","Airtel Money ITF"),
     ("2026-10-01","Airtel Money priced GBP1.96"),("2026-10-09","Airtel Money conditional dealings")]
print("event | window | Airtel | Nifty | excess  (close t-1 to close t+1; t+5 in brackets)")
for d, name in E:
    d0 = datetime.date.fromisoformat(d)
    a, b, ra, rn, ex = win(d0, 1, 1)
    _, b5, ra5, rn5, ex5 = win(d0, 1, 5)
    print("%s %s | %s..%s | %+.1f%% | %+.1f%% | %+.1f%%  [t+5 excess %+.1f%%]" % (d, name, a, b, 100*ra, 100*rn, 100*ex, 100*ex5))
last = days[-1]
print("last date", last, "Airtel close", air[last])
for d in ("2025-12-31","2026-03-31","2026-05-12","2026-05-13","2026-06-30"):
    d0 = datetime.date.fromisoformat(d); i = idx(d0); print("Airtel close", days[i], air[days[i]])
hi_d = max((x for x in days if x >= datetime.date(2025,10,12)), key=lambda x: air[x])
print("52w high", hi_d, air[hi_d], "drawdown to last %.1f%%" % (100*(air[last]/air[hi_d]-1)))
lo_d = min((x for x in days if x >= datetime.date(2025,10,12)), key=lambda x: air[x]); print("52w low", lo_d, air[lo_d])
y1 = days[idx(datetime.date(2025,10,13))]
print("1y change Airtel %+.1f%% Nifty %+.1f%%" % (100*(air[last]/air[y1]-1), 100*(nif[last]/nif[y1]-1)))
# ICIL swap economics
aday = sorted(x for x in aaf if x <= datetime.date(2026,5,12))[-1]
fday = sorted(x for x in fx if x <= datetime.date(2026,5,12))[-1]
sh_new, px_issue, aaf_sh = 146_761_335, 1923.0, 595_204_251
paid_inr_per_aaf = sh_new*px_issue/aaf_sh
print("ICIL: INR paid per AAF share %.1f; = %.1fp at GBPINR %.2f (%s)" % (paid_inr_per_aaf, 100*paid_inr_per_aaf/fx[fday], fx[fday], fday))
print("AAF close %s: %.1fp ; premium/(discount) of swap value to AAF market %+.1f%%" % (aday, aaf[aday], 100*((paid_inr_per_aaf/fx[fday])/(aaf[aday]/100)-1)))
print("Airtel close %s INR %.1f; issue price premium/(discount) to market %+.1f%%" % (days[idx(datetime.date(2026,5,12))-0], air[sorted(x for x in air if x<=datetime.date(2026,5,12))[-1]], 100*(px_issue/air[sorted(x for x in air if x<=datetime.date(2026,5,12))[-1]]-1)))
aaf_last = sorted(aaf)[-1]; fx_last = sorted(fx)[-1]
print("Mark-to-market %s: Airtel shares given %.0f cr vs AAF shares received %.0f cr" % (aaf_last, sh_new*air[last]/1e7, aaf_sh*aaf[aaf_last]/100*fx[fx_last]/1e7))
print("AAF since 2026-05-12: %+.1f%%; Airtel since 2026-05-12: %+.1f%%" % (100*(aaf[aaf_last]/aaf[aday]-1), 100*(air[last]/air[sorted(x for x in air if x<=datetime.date(2026,5,12))[-1]]-1)))
