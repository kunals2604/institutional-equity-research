"""Batch PDF-page locator for special-situations corpus citations (wraps scripts/corpus.py locate)."""
import subprocess, sys
R="research/companies/BHARTIARTL/runs/20261012T132311Z"
L="/Users/kunalsingla/Documents/FilingForgeLibrary/BHARTIARTL/"
D={"A25":"annual-reports/2025/2025-07-16_Annual_report_FY_2024-25__ef981e1b-4d0f-478c-ae63-5e3f2ca4316f.md",
"A23":"annual-reports/2023/2023-08-02_Annual_report_FY_2022-23__80756f27-cb0a-4847-9f7b-019ba8be2275.md",
"A22":"annual-reports/2022/2022-07-21_Annual_report_FY_2021-22__1c7c2552-7d96-4a40-ae4b-afed2435fdcf.md",
"A21":"annual-reports/2021/2021-08-09_Annual_report_FY_2020-21__3e7fff81-d3bf-4662-8dd5-8c18db7db532.md",
"A20":"annual-reports/2020/2020-07-27_Annual_report_FY_2019-20__49889f5f-b097-41be-8be7-8bad6d949760.md",
"A19":"annual-reports/2019/2019-07-21_Annual_report__e52e5a27-cfee-4e32-aac2-04337c03baeb.md",
"A17":"annual-reports/2017/2017-08-14_Annual_report__AR-532454-2017.md",
"Q127":"quarterly/2026/2026-08-04_Financial_results__3a61007b-6d5a-449e-be4d-84dca645422b.md",
"Q426":"quarterly/2026/2026-05-13_Financial_results__b5c6beda-7ade-4dd3-ad4f-bff5e5efe4c1.md",
"Q326":"quarterly/2026/2026-02-05_Financial_results_Quarter_and_9M_ended_2025-12-31__e22c482b-a125-447f-9fa2-d3a66803763d.md",
"T127":"concalls/2026/2026-08-10_Concall_transcript__a46861ad-47c4-4fb1-9001-f56835e1a897.md"}
Q=[l.split("|",1) for l in sys.stdin.read().strip().splitlines()]
for k,txt in Q:
    out=subprocess.run(["python3","scripts/corpus.py","locate","--run",R,L+D[k],txt],capture_output=True,text=True).stdout.strip().splitlines()
    print(k,"|",txt[:50],"|",out[-1] if out else "?")
