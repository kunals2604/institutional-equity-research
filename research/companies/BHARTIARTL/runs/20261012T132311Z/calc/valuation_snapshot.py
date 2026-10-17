#!/usr/bin/env python3
"""Capital-structure snapshot, TTM metrics, EV variants, current multiples and their percentile in own history.
Run: python3 -I calc/valuation_snapshot.py RUN_DIR  -> calc/valuation_snapshot.json"""
import json, sys
from pathlib import Path
run = Path(sys.argv[1]); I = json.loads((run / "calc/valuation_snapshot_inputs.json").read_text())
o = {}
P = I["price"]
mcap_fp = P * I["shares_fully_paid"] / 1e6                      # INR mn
mcap_pp = (P - I["call_unpaid_per_pp_share"]) * I["shares_partly_paid"] / 1e6
mcap = mcap_fp + mcap_pp
o["market_cap_inr_mn"] = mcap; o["market_cap_fully_paid_inr_mn"] = mcap_fp; o["partly_paid_economic_value_inr_mn"] = mcap_pp
o["shares_economic_equivalent"] = I["shares_fully_paid"] + I["shares_partly_paid"] * (1 - I["call_unpaid_per_pp_share"] / P)
ttm = {k: I["fy26"][k] + I["q1fy27"][k] - I["q1fy26"][k] for k in I["q1fy27"]}
o["ttm_jun26"] = ttm
o["ttm_eps_pre_exc"] = ttm["ni_pre_exc"] * 1e6 / I["shares_fully_paid"]
# NCI at market value
A = I["africa"]; africa_shares = A["icil_swap_shares"] / A["icil_stake_pct"]
africa_mcap = africa_shares * A["price_gbp_pence"] / 100 * A["gbpinr"] / 1e6
nci_africa = africa_mcap * (1 - A["airtel_effective_stake"])
ind = I["indus"]; indus_shares = ind["mcap_inr_crore_screener"] * 1e7 / ind["screener_price"]
indus_mcap = indus_shares * ind["price"] / 1e6; nci_indus = indus_mcap * (1 - ind["airtel_stake"])
hx = I["hexacom"]; hex_mcap = hx["shares"] * hx["price"] / 1e6; nci_hex = hex_mcap * (1 - hx["airtel_stake"])
nci_mkt = nci_africa + nci_indus + nci_hex + I["other_nci_estimate_inr_mn"]
o["listed_subs"] = {"africa_shares_implied": africa_shares, "africa_mcap_inr_mn": africa_mcap, "airtel_africa_stake_value_inr_mn": africa_mcap * A["airtel_effective_stake"],
    "nci_africa_inr_mn": nci_africa, "indus_shares_implied": indus_shares, "indus_mcap_inr_mn": indus_mcap, "airtel_indus_stake_value_inr_mn": indus_mcap * ind["airtel_stake"],
    "nci_indus_inr_mn": nci_indus, "hexacom_mcap_inr_mn": hex_mcap, "airtel_hexacom_stake_value_inr_mn": hex_mcap * hx["airtel_stake"], "nci_hexacom_inr_mn": nci_hex,
    "other_nci_estimate_inr_mn": I["other_nci_estimate_inr_mn"], "nci_market_total_inr_mn": nci_mkt}
ev_company = mcap + I["net_debt_incl_leases_jun26"]
ev_full = ev_company + nci_mkt
ev_full_exlease = mcap + I["net_debt_excl_leases_jun26"] + nci_mkt
o["ev"] = {"company_basis_mcap_plus_net_debt_incl_leases": ev_company, "full_incl_nci_market": ev_full, "full_excl_leases_incl_nci_market": ev_full_exlease,
           "ev_with_nci_at_book": ev_company + I["nci_book_jun26"]}
o["multiples_ttm"] = {
    "ev_ebitda_company_basis": ev_company / ttm["ebitda"], "ev_ebitda_full": ev_full / ttm["ebitda"],
    "ev_ebitdaal_full_excl_leases": ev_full_exlease / ttm["ebitdaal"], "ev_ebit_full": ev_full / ttm["ebit"],
    "ev_sales_full": ev_full / ttm["revenue"], "pe_ttm_pre_exc": mcap / ttm["ni_pre_exc"],
    "pb_parent_equity": mcap / I["equity_parent_jun26"],
    "opfcf_ebitdaal_minus_capex_yield_on_ev_excl_leases": (ttm["ebitdaal"] - ttm["capex"]) / ev_full_exlease,
    "q1fy27_annualised_ev_ebitda_full": ev_full / (4 * I["q1fy27"]["ebitda"]),
    "net_debt_incl_leases_to_ttm_ebitda": I["net_debt_incl_leases_jun26"] / ttm["ebitda"],
    "net_debt_excl_leases_to_ttm_ebitdaal": I["net_debt_excl_leases_jun26"] / ttm["ebitdaal"]}
f10 = I["fy10_inputs"]; px10 = f10["price_adj_yahoo"] / f10["rights_adj_factor"]
mc10 = px10 * f10["shares_mn"]
evh = dict(I["ev_ebitda_history"]); evh["FY2010"] = (mc10 + f10["net_debt"]) / f10["ebitda"]
peh = {k: v for k, v in I["pe_history"].items()}; peh["FY2010"] = mc10 / f10["net_income"]; peh["FY2011"] = I["fy11_inputs"]["mcap_bn"] * 1000 / I["fy11_inputs"]["net_income"]
o["fy2010_unadjusted_price"] = px10; o["fy2010_mcap_inr_mn"] = mc10
def stats(d, cur):
    v = sorted(x for x in d.values() if x is not None)
    n = len(v); med = (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)
    pct = sum(1 for x in v if x < cur) / n
    return {"n": n, "min": v[0], "max": v[-1], "median": med, "mean": sum(v) / n, "current": cur, "percentile_of_current": pct}
o["ev_ebitda_history"] = dict(sorted(evh.items()))
o["ev_ebitda_company_basis_stats"] = stats(evh, o["multiples_ttm"]["ev_ebitda_company_basis"])
pe_mean = {k: v for k, v in peh.items() if v is not None and v < 100}
o["pe_history"] = dict(sorted(peh.items()))
o["pe_stats_excl_loss_and_gt100"] = stats(pe_mean, o["multiples_ttm"]["pe_ttm_pre_exc"])
(run / "calc/valuation_snapshot.json").write_text(json.dumps(o, indent=2))
print(json.dumps(o, indent=2))
