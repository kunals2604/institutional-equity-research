#!/usr/bin/env python3
"""Filings forensic arithmetic (INR million unless stated). Inputs: specialists/filings_workpapers/*.csv and FY2026 AR figures (ledger FIL-C0xx)."""
import csv, os
B=os.path.dirname(os.path.abspath(__file__)); W=os.path.join(B,"..","specialists","filings_workpapers")
ex={r["fy"]:r for r in csv.DictReader(open(os.path.join(W,"exceptional_pat_history.csv")))}
cfo={r["fy"]:float(r["cfo_consolidated_inr_mn"]) for r in csv.DictReader(open(os.path.join(W,"cfo_history.csv")))}
cl=list(csv.DictReader(open(os.path.join(W,"contingent_liabilities.csv"))))
print("== Exceptional items and PAT, FY2017-FY2026 (charge positive) ==")
tot_ex=0; tot_pat=0; tot_cfo=0; n_charge=0
for fy in sorted(ex):
    e=float(ex[fy]["exceptional_charge_as_presented_inr_mn"]); p=float(ex[fy]["profit_for_year_incl_nci_inr_mn"])
    tot_ex+=e; tot_pat+=p; tot_cfo+=cfo[fy]; n_charge+= e>0
    print(f"{fy}: exceptional {e:>10,.0f}  PAT {p:>10,.0f}  CFO {cfo[fy]:>11,.0f}")
print(f"Cumulative FY2017-FY2026: net exceptional charge {tot_ex:,.0f}; PAT {tot_pat:,.0f}; CFO {tot_cfo:,.0f}; years with net charge {n_charge}/10")
print(f"Cumulative net exceptional charge / cumulative PAT = {tot_ex/tot_pat:.2f}")
print(f"Cumulative CFO / cumulative PAT = {tot_cfo/tot_pat:.1f}x")
print("== Contingent liabilities (table) as % of equity attributable to owners ==")
for r in cl:
    t=float(r["cl_table_total_inr_mn"]); eq=float(r["equity_attrib_owners_inr_mn"]); j=float(r["share_jv_assoc_cl_inr_mn"])
    print(f"{r['period_end']}: CL {t:>9,.0f} ({t/eq*100:5.1f}% of equity); incl JV share {(t+j)/eq*100:5.1f}%; DoT/regulatory {float(r['dot_regulatory_inr_mn'])/t*100:5.1f}% of CL")
# FY2026 extended exposure: table CL + DoT items disclosed outside the table
otsc_bal=66065; isp=48619; cl26=191842; eq26=1490566
ext=cl26+otsc_bal+isp
print(f"FY2026 CL incl. OTSC balance and ISP licence fee disclosed outside table: {ext:,.0f} = {ext/eq26*100:.1f}% of equity (note: ISP amount may overlap the DoT line; upper bound)")
# FY2026 cash conversion with financing-classified operating-type outflows
c=1222296; capex=451756+15386; spectrum=8546; lease=67197; interest=148876; agr=54272
fcf_reported=c-capex-spectrum
adj=fcf_reported-lease-interest-agr
print(f"FY2026 CFO {c:,.0f}; CFO - capex(PPE+intangibles) - spectrum = {fcf_reported:,.0f}; less lease {lease:,}, interest {interest:,}, AGR principal {agr:,} = {adj:,.0f}")
print(f"Share of financing-classified operating-type outflows in CFO: {(lease+interest+agr)/c*100:.1f}%")
# OTSC: provision interest vs principal
print(f"OTSC: interest accrued to FY2026 {121377:,} vs principal charged {18075:,} -> ratio {121377/18075:.1f}x; total provided {121377+18075:,}")
# FY2025-26 tax credits relative to attributable PAT
print(f"FY2026 DTL reversal credit 30,952 = {30952/266952*100:.1f}% of attributable PAT 266,952")
print(f"FY2025 DTA recognition credit 85,732 = {85732/335561*100:.1f}% of attributable PAT 335,561; Indus FV gain 107,025 = {107025/335561*100:.1f}%")
# AGR provision composition
agr_prov=347042; ttsl=166725; tel=24886
print(f"AGR sub-judice provision {agr_prov:,}: indemnified (TTSL/TTML+Telenor) {ttsl+tel:,} = {(ttsl+tel)/agr_prov*100:.1f}%; remainder {agr_prov-ttsl-tel:,}")
# unit conversion helper
for k,v in {"CL FY2026":cl26,"AGR provision":agr_prov,"Deferred payment liabs":906430,"Disputed payables":245350,"Mobile money cash":132061,"Indus goodwill":208593,"Dixon purchases":26358,"Dividend to BTL":37737}.items():
    print(f"{k}: INR {v/10:,.0f} crore")
print(f"FY2026 CL + OTSC balance only (ISP assumed inside DoT line): {(cl26+otsc_bal):,.0f} = {(cl26+otsc_bal)/eq26*100:.1f}% of equity")
