#!/usr/bin/env python3
"""Revenue-recognition screens FY2025-FY2026 (consolidated, INR mn). Inputs FY2026 AR CFS (FIL-C004, FIL-C068)."""
rev={"FY2025":1729852,"FY2026":2109728}
tr={"FY2025":74557+2131,"FY2026":79776+2544}   # current + non-current trade receivables
unb={"FY2025":37277,"FY2026":44947}
dr={"FY2025":97729+35185,"FY2026":109487+40185}
for y in rev:
    print(f"{y}: DSO (closing, incl. non-current) {tr[y]/rev[y]*365:.1f} days; unbilled/revenue {unb[y]/rev[y]*100:.2f}%; deferred revenue/revenue {dr[y]/rev[y]*100:.2f}%")
g=lambda d:(d['FY2026']/d['FY2025']-1)*100
print(f"Growth FY2026: revenue {g(rev):.1f}%; receivables {g(tr):.1f}%; unbilled {g(unb):.1f}%; deferred revenue {g(dr):.1f}%")
print(f"Bad-debt provision FY2026 3,586 = {3586/rev['FY2026']*100:.2f}% of revenue")
