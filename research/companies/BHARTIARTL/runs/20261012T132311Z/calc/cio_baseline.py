"""CIO independent baseline (Stage 1 wait): headline consolidated figures from filings, INR million -> INR crore.
Sources: FY2026/FY2025 from Q4FY2026 results filing (FilingForge:b5c6beda..., Section 7.1);
FY2024/FY2023 from Q4FY2024 results filing (FilingForge:4f6dbf86..., Section 7.1);
FY2017 from Annual Report 2016-17 consolidated statements (FilingForge:AR-532454-2017)."""
data_mn = {  # revenue, pat, pat_attr, equity_attr, borrow_noncurrent, borrow_current, cfo
 "FY2026": (2109728, 338228, 266952, 1490566, 1645845, 308272, 1222296),
 "FY2025": (1729852, 374813, 335561, 1136719, 1605339, 531082, 983322),
 "FY2024": (1499824,  85580,  74670,  820188, 1848897, 307026, 788982),
 "FY2023": (1391448, 122874,  83459,  775629, 2023981, 236222, 653246),
 "FY2017": ( 954683,  42414,  37998,  674563,  896373, 129442, 292309),
}
names = ["revenue","pat","pat_attributable","total_equity","borrowings_noncurrent","borrowings_current","cfo"]
for fy, v in data_mn.items():
    cr = [x / 10 for x in v]
    out = dict(zip(names, cr)); out["borrowings_as_reported"] = cr[4] + cr[5]
    out["cfo_to_pat"] = v[6] / v[1]
    print(fy, " ".join("%s=%.1f" % (k, out[k]) if k != "cfo_to_pat" else "%s=%.2f" % (k, out[k]) for k in out))
# growth FY2017 -> FY2026 (9 years), revenue CAGR
print("cagr_revenue_9y_FY2017_FY2026=%.4f" % ((data_mn["FY2026"][0] / data_mn["FY2017"][0]) ** (1/9) - 1))
print("revenue_growth_FY2026=%.4f" % (data_mn["FY2026"][0] / data_mn["FY2025"][0] - 1))
