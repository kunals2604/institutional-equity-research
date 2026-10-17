#!/usr/bin/env python3
"""ARPU step-ups around the three tariff repairs (Airtel India mobile ARPU, Rs/month; IND-C042, corpus 5-quarter trend lines).
Dec-2019 hike: Q3FY20 135 -> Q4FY20 154 (IUC-inclusive; IUC-recast 135.3 in Q4FY20 per KPI Q4FY21 workbook)
Nov-2021 hike: Q2FY22 153 -> Q4FY22 178
Jul-2024 hike: Q1FY25 211 -> Q3FY25 245
Customers (000): Mar-24 352,253 -> Mar-25 361,593 (through the Jul-2024 hike)."""
cases = {"Dec-2019 (pre Q3FY20 -> Q4FY20)": (135, 154), "Nov-2021 (Q2FY22 -> Q4FY22)": (153, 178), "Jul-2024 (Q1FY25 -> Q3FY25)": (211, 245),
         "No-hike drift FY2025Q4 -> FY2026Q4": (245, 257), "No-hike drift Q4FY23 -> Q4FY24": (193, 209)}
out = []
for k, (a, b) in cases.items():
    s = "%s: ARPU %d -> %d = %+.1f%%" % (k, a, b, 100.0 * (b / a - 1)); print(s); out.append(s)
s = "Customers Mar-24 -> Mar-25: %+.1f%%" % (100.0 * (361593 / 352253 - 1)); print(s); out.append(s)
open(__file__.replace('.py', '.out.txt'), 'w').write('\n'.join(out) + '\n')
