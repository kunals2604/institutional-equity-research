#!/usr/bin/env python3
"""Deterministic financial metrics from a long-format, source-cited financial history.

  python3 scripts/fin_metrics.py HISTORY.csv --basis consolidated --profile general \
      --out RUN_DIR/calc/financial_metrics.csv [--summary]
  python3 scripts/fin_metrics.py HISTORY.csv --check            # validate the dataset only

HISTORY.csv columns (template: templates/financial_history_template.csv):
  item, period, value, unit, basis, source_tier, source_url_or_id, locator, verified, note
  * item  : a line-item key from methodology/METRIC_DEFINITIONS.md (revenue, pat, cfo, ...)
  * period: FY2025 style (annual)
  * every row carries its source and page/note locator; verified=Y only if read from a tier-1 filing

Formulas follow methodology/METRIC_DEFINITIONS.md exactly; every output row carries
the formula and inputs so it can be cited as CALCULATION. Profiles: general (non-financial
companies) and lender (banks, NBFCs, HFCs). Missing inputs omit a metric; they are
never imputed, except the optional items noted in the formula (treated as 0, and flagged).
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

REQUIRED_COLS = ["item", "period", "value", "unit", "basis", "source_tier", "source_url_or_id", "locator", "verified", "note"]
SHARE_ITEMS = {"shares_basic", "shares_diluted"}
PER_SHARE_ITEMS = {"dps", "price"}
PCT_ITEMS = {"crar", "tier1_ratio", "casa_ratio", "cost_of_funds", "yield_on_advances"}
OPTIONAL_ZERO = {"minority_interest_bs", "lease_liabilities", "current_investments", "acquisitions", "deposits"}
CAGR_ITEMS = {
    "general": ["revenue", "ebitda", "pat_attributable", "cfo", "eps", "bvps", "fcf_per_share", "total_equity", "shares_diluted"],
    "lender": ["advances", "nii", "ppop", "pat_attributable", "eps", "bvps", "total_equity", "shares_diluted"],
}
CAGR_WINDOWS = (3, 5, 10, 15)


class Data:
    def __init__(self, rows: List[Dict[str, str]], basis: str):
        self.v: Dict[Tuple[str, int], float] = {}
        self.unit: Dict[str, str] = {}
        self.basis = basis
        for r in rows:
            self.v[(r["item"], fy(r["period"]))] = float(r["value"])
            self.unit[r["item"]] = r["unit"]
        self.years = sorted({y for (_, y) in self.v})

    def get(self, item: str, y: int, optional_zero: bool = False) -> Optional[float]:
        val = self.v.get((item, y))
        if val is None and optional_zero and item in OPTIONAL_ZERO:
            return 0.0
        return val

    def avg(self, item: str, y: int) -> Tuple[Optional[float], str]:
        cur, prev = self.get(item, y), self.get(item, y - 1)
        if cur is None:
            return None, ""
        if prev is None:
            return cur, " (closing)"
        return (cur + prev) / 2.0, ""


def fy(period: str) -> int:
    m = re.fullmatch(r"FY(\d{4})", period.strip().upper())
    if not m:
        raise ValueError("period %r must look like FY2025" % period)
    return int(m.group(1))


def load(path: Path, basis: Optional[str]) -> Tuple[List[Dict[str, str]], List[str], List[str]]:
    errors, warnings = [], []
    header, rows = rl.read_csv(path)
    missing = [c for c in REQUIRED_COLS if c not in header]
    if missing:
        return [], ["missing columns: %s" % missing], []
    keys = rl.metric_keys()
    seen = {}
    kept = []
    for i, r in enumerate(rows, 2):
        if basis and r["basis"].strip().lower() != basis.lower():
            continue
        where = "row %d (%s %s)" % (i, r.get("item"), r.get("period"))
        item = r["item"].strip()
        if item not in keys:
            errors.append("%s: item not a METRIC_DEFINITIONS key" % where)
        try:
            fy(r["period"])
        except ValueError as exc:
            errors.append("%s: %s" % (where, exc))
            continue
        try:
            float(r["value"].replace(",", ""))
            r["value"] = r["value"].replace(",", "")
        except ValueError:
            errors.append("%s: value %r not numeric" % (where, r["value"]))
            continue
        if not r["source_url_or_id"].strip() or not r["locator"].strip():
            errors.append("%s: every data point needs source_url_or_id and locator" % where)
        if r["source_tier"].strip() not in [str(n) for n in range(1, 8)]:
            errors.append("%s: source_tier must be 1-7" % where)
        if r["verified"].strip().upper() not in ("Y", "N"):
            errors.append("%s: verified must be Y or N" % where)
        elif r["verified"].strip().upper() == "Y" and r["source_tier"].strip() not in ("1", "2"):
            errors.append("%s: verified=Y requires a tier-1/2 source" % where)
        key = (item, r["period"].strip().upper(), r["basis"].strip().lower())
        if key in seen:
            errors.append("%s: duplicate of row %d" % (where, seen[key]))
        seen[key] = i
        r["item"], r["period"] = item, r["period"].strip().upper()
        kept.append(r)
    money_units = {r["unit"].strip() for r in kept
                   if r["item"] not in SHARE_ITEMS | PER_SHARE_ITEMS | PCT_ITEMS}
    if len(money_units) > 1:
        errors.append("monetary items use mixed units %s; convert to one unit" % sorted(money_units))
    bases = {r["basis"].strip().lower() for r in kept}
    if len(bases) > 1:
        errors.append("multiple bases %s; pass --basis" % sorted(bases))
    if kept and not any(r["verified"].strip().upper() == "Y" for r in kept):
        warnings.append("no data point is verified against a tier-1 filing (RESEARCH_PLAYBOOK.md §3)")
    return kept, errors, warnings


def scale_word(unit: str) -> str:
    for w in ("crore", "lakh", "million", "billion", "thousand"):
        if w in unit.lower():
            return w
    return ""


def compute(d: Data, profile: str) -> Tuple[List[dict], List[str]]:
    out: List[dict] = []
    notes: List[str] = []
    money = next((u for i, u in d.unit.items() if i not in SHARE_ITEMS | PER_SHARE_ITEMS | PCT_ITEMS), "")
    share_unit = d.unit.get("shares_diluted") or d.unit.get("shares_basic") or ""
    per_share_ok = bool(share_unit) and scale_word(money) == scale_word(share_unit) and scale_word(money) != ""
    if (d.unit.get("shares_diluted") or d.unit.get("shares_basic")) and not per_share_ok:
        notes.append("per-share metrics skipped: money unit %r and share unit %r must share a scale (e.g. 'INR crore' / 'crore shares')"
                     % (money, share_unit))
    cur = re.sub(r"\s*(crore|lakh|million|billion|thousand)\s*", "", money).strip() or "currency"

    def emit(metric, y, value, unit, formula, inputs):
        if value is None:
            return
        out.append({"metric": metric, "period": "FY%d" % y, "value": round(value, 6), "unit": unit,
                    "formula": formula, "inputs": inputs, "basis": d.basis})

    def div(a, b):
        if a is None or b is None or b == 0:
            return None
        return a / b

    derived: Dict[Tuple[str, int], float] = {}

    def item(name, y, optional_zero=False):
        if (name, y) in derived:
            return derived[(name, y)]
        return d.get(name, y, optional_zero)

    for y in d.years:
        g = lambda n, oz=False: item(n, y, oz)  # noqa: E731
        p = lambda n: item(n, y - 1)  # noqa: E731
        if profile == "general":
            if g("ebitda") is None and None not in (g("revenue"), g("cogs"), g("employee_cost"), g("other_opex")):
                derived[("ebitda", y)] = g("revenue") - g("cogs") - g("employee_cost") - g("other_opex")
                emit("ebitda", y, derived[("ebitda", y)], money, "revenue - cogs - employee_cost - other_opex", "revenue,cogs,employee_cost,other_opex")
            if g("ebit") is None and None not in (g("ebitda"), g("depreciation")):
                derived[("ebit", y)] = g("ebitda") - g("depreciation")
                emit("ebit", y, derived[("ebit", y)], money, "ebitda - depreciation", "ebitda,depreciation")
            if g("revenue") is not None and p("revenue"):
                emit("revenue_growth", y, g("revenue") / p("revenue") - 1, "ratio", "revenue_t / revenue_t-1 - 1", "revenue")
            for m, num in (("ebitda_margin", "ebitda"), ("ebit_margin", "ebit"), ("pat_margin", "pat")):
                emit(m, y, div(g(num), g("revenue")), "ratio", "%s / revenue" % num, "%s,revenue" % num)
            etr = div(g("tax"), g("pbt")) if (g("pbt") or 0) > 0 else None
            emit("effective_tax_rate", y, etr, "ratio", "tax / pbt (pbt > 0 only)", "tax,pbt")
            for yy in (y, y - 1):
                ta, cl = item("total_assets", yy), item("current_liabilities", yy)
                if ta is not None and cl is not None:
                    derived[("capital_employed", yy)] = ta - cl
                parts = [item("total_equity", yy), item("total_debt", yy), item("cash_and_equivalents", yy)]
                if None not in parts:
                    derived[("invested_capital", yy)] = (parts[0] + item("minority_interest_bs", yy, True) + parts[1]
                                                         + item("lease_liabilities", yy, True) - parts[2]
                                                         - item("current_investments", yy, True))
            emit("capital_employed", y, derived.get(("capital_employed", y)), money, "total_assets - current_liabilities", "total_assets,current_liabilities")
            emit("invested_capital", y, derived.get(("invested_capital", y)), money,
                 "total_equity + minority_interest_bs + total_debt + lease_liabilities - cash_and_equivalents - current_investments (optional items missing->0)",
                 "total_equity,minority_interest_bs,total_debt,lease_liabilities,cash_and_equivalents,current_investments")
            ce_now, ce_prev = derived.get(("capital_employed", y)), derived.get(("capital_employed", y - 1))
            ce_avg = (ce_now + ce_prev) / 2 if None not in (ce_now, ce_prev) else ce_now
            emit("roce", y, div(g("ebit"), ce_avg), "ratio", "ebit / average capital_employed" + ("" if ce_prev is not None else " (closing)"), "ebit,capital_employed")
            nopat = g("ebit") * (1 - etr) if (g("ebit") is not None and etr is not None) else None
            if nopat is not None:
                derived[("nopat", y)] = nopat
            emit("nopat", y, nopat, money, "ebit * (1 - effective_tax_rate)", "ebit,effective_tax_rate")
            ic_now, ic_prev = derived.get(("invested_capital", y)), derived.get(("invested_capital", y - 1))
            ic_avg = (ic_now + ic_prev) / 2 if None not in (ic_now, ic_prev) else ic_now
            emit("roic", y, div(nopat, ic_avg) if (ic_avg or 0) > 0 else None, "ratio",
                 "nopat / average invested_capital" + ("" if ic_prev is not None else " (closing)"), "nopat,invested_capital")
            nd = None
            if None not in (g("total_debt"), g("cash_and_equivalents")):
                nd = g("total_debt") - g("cash_and_equivalents") - g("current_investments", True)
                emit("net_debt", y, nd, money, "total_debt - cash_and_equivalents - current_investments", "total_debt,cash_and_equivalents,current_investments")
                emit("net_debt_incl_leases", y, nd + g("lease_liabilities", True), money, "net_debt + lease_liabilities", "net_debt,lease_liabilities")
            emit("net_debt_to_ebitda", y, div(nd, g("ebitda")) if (g("ebitda") or 0) > 0 else None, "x", "net_debt / ebitda", "net_debt,ebitda")
            emit("interest_coverage", y, div(g("ebit"), g("interest_expense")), "x", "ebit / interest_expense", "ebit,interest_expense")
            emit("cfo_to_pat", y, div(g("cfo"), g("pat")) if (g("pat") or 0) > 0 else None, "ratio", "cfo / pat (pat > 0 only)", "cfo,pat")
            emit("cfo_to_ebitda", y, div(g("cfo"), g("ebitda")) if (g("ebitda") or 0) > 0 else None, "ratio", "cfo / ebitda", "cfo,ebitda")
            fcf = g("cfo") - g("capex") if None not in (g("cfo"), g("capex")) else None
            if fcf is not None:
                derived[("fcf", y)] = fcf
            emit("fcf", y, fcf, money, "cfo - capex", "cfo,capex")
            emit("fcf_to_pat", y, div(fcf, g("pat")) if (g("pat") or 0) > 0 else None, "ratio", "fcf / pat (pat > 0 only)", "fcf,pat")
            dso = div(g("trade_receivables"), g("revenue"))
            emit("dso", y, dso * 365 if dso is not None else None, "days", "trade_receivables / revenue * 365", "trade_receivables,revenue")
            base, lbl = (g("cogs"), "cogs") if g("cogs") else (g("revenue"), "revenue (cogs unavailable)")
            dio, dpo = div(g("inventories"), base), div(g("trade_payables"), base)
            emit("dio", y, dio * 365 if dio is not None else None, "days", "inventories / %s * 365" % lbl, "inventories,%s" % lbl.split()[0])
            emit("dpo", y, dpo * 365 if dpo is not None else None, "days", "trade_payables / %s * 365" % lbl, "trade_payables,%s" % lbl.split()[0])
            if None not in (dso, dio, dpo):
                emit("ccc", y, (dso + dio - dpo) * 365, "days", "dso + dio - dpo", "dso,dio,dpo")
            emit("capex_to_revenue", y, div(g("capex"), g("revenue")), "ratio", "capex / revenue", "capex,revenue")
            emit("capex_to_depreciation", y, div(g("capex"), g("depreciation")), "x", "capex / depreciation", "capex,depreciation")
            ta_avg, sfx = d.avg("total_assets", y)
            if None not in (g("pat"), g("cfo"), ta_avg):
                emit("accruals_ratio", y, (g("pat") - g("cfo")) / ta_avg, "ratio", "(pat - cfo) / average total_assets" + sfx, "pat,cfo,total_assets")
            emit("roa", y, div(g("pat"), ta_avg), "ratio", "pat / average total_assets" + sfx, "pat,total_assets")
            if (g("pbt") or 0) > 0:
                emit("other_income_share_pbt", y, div(g("other_income"), g("pbt")), "ratio", "other_income / pbt", "other_income,pbt")
                emit("exceptional_share_pbt", y, div(g("exceptional_items"), g("pbt")), "ratio", "exceptional_items / pbt", "exceptional_items,pbt")
            emit("goodwill_to_equity", y, div(g("goodwill_intangibles"), g("total_equity")), "ratio", "goodwill_intangibles / total_equity", "goodwill_intangibles,total_equity")
            nwc = lambda yy: (None if None in (item("trade_receivables", yy), item("inventories", yy), item("trade_payables", yy))  # noqa: E731
                              else item("trade_receivables", yy) + item("inventories", yy) - item("trade_payables", yy))
            if None not in (g("capex"), g("depreciation"), nwc(y), nwc(y - 1), nopat) and nopat and nopat > 0:
                rr = (g("capex") - g("depreciation") + (nwc(y) - nwc(y - 1)) + g("acquisitions", True)) / nopat
                emit("reinvestment_rate", y, rr, "ratio",
                     "(capex - depreciation + change in (receivables + inventories - payables) + acquisitions) / nopat",
                     "capex,depreciation,trade_receivables,inventories,trade_payables,acquisitions,nopat")
            for n, k in ((3, "incremental_roic_3y"), (5, "incremental_roic_5y")):
                a, b = derived.get(("nopat", y)), derived.get(("nopat", y - n))
                c, e = derived.get(("invested_capital", y - 1)), derived.get(("invested_capital", y - 1 - n))
                if None not in (a, b, c, e) and (c - e) > 0:
                    emit(k, y, (a - b) / (c - e), "ratio",
                         "(nopat_t - nopat_t-%d) / (invested_capital_t-1 - invested_capital_t-%d)" % (n, n + 1), "nopat,invested_capital")
            _piotroski(y, item, emit)
            _beneish(y, item, emit)
        else:  # lender
            if g("nii") is None and None not in (g("interest_income"), g("interest_expense")):
                derived[("nii", y)] = g("interest_income") - g("interest_expense")
                emit("nii", y, derived[("nii", y)], money, "interest_income - interest_expense", "interest_income,interest_expense")
            if g("ppop") is None and None not in (g("nii"), g("fee_income"), g("opex")):
                derived[("ppop", y)] = g("nii") + g("fee_income") - g("opex")
                emit("ppop", y, derived[("ppop", y)], money, "nii + fee_income - opex", "nii,fee_income,opex")
            adv_avg, sa = d.avg("advances", y)
            ta_avg, st = d.avg("total_assets", y)
            eq_avg, se = d.avg("total_equity", y)
            emit("nim", y, div(g("nii"), adv_avg), "ratio", "nii / average advances" + sa, "nii,advances")
            emit("nii_to_avg_assets", y, div(g("nii"), ta_avg), "ratio", "nii / average total_assets" + st, "nii,total_assets")
            if None not in (g("nii"), g("fee_income"), g("opex")):
                emit("cost_to_income", y, div(g("opex"), g("nii") + g("fee_income")), "ratio", "opex / (nii + fee_income)", "opex,nii,fee_income")
            emit("credit_cost", y, div(g("provisions"), adv_avg), "ratio", "provisions / average advances" + sa, "provisions,advances")
            emit("roa", y, div(g("pat"), ta_avg), "ratio", "pat / average total_assets" + st, "pat,total_assets")
            emit("leverage_assets_to_equity", y, div(ta_avg, eq_avg), "x", "average total_assets / average total_equity", "total_assets,total_equity")
            emit("gnpa_ratio", y, div(g("gnpa"), g("advances")), "ratio", "gnpa / advances", "gnpa,advances")
            if None not in (g("nnpa"), g("gnpa"), g("advances")):
                emit("nnpa_ratio", y, div(g("nnpa"), g("advances") - (g("gnpa") - g("nnpa"))), "ratio", "nnpa / (advances - (gnpa - nnpa))", "nnpa,gnpa,advances")
                emit("pcr", y, 1 - div(g("nnpa"), g("gnpa")) if g("gnpa") else None, "ratio", "1 - nnpa / gnpa", "nnpa,gnpa")
            for m, it in (("advances_growth", "advances"), ("borrowings_growth", "borrowings"), ("deposits_growth", "deposits")):
                if g(it) is not None and p(it):
                    emit(m, y, g(it) / p(it) - 1, "ratio", "%s_t / %s_t-1 - 1" % (it, it), it)
            if None not in (g("borrowings"), p("borrowings"), g("interest_expense")):
                funds = (g("borrowings") + g("deposits", True) + p("borrowings") + item("deposits", y - 1, True)) / 2
                emit("cost_of_funds", y, div(g("interest_expense"), funds), "ratio",
                     "interest_expense / average (borrowings + deposits) (deposits missing->0)", "interest_expense,borrowings,deposits")
        # common to both profiles
        pa = g("pat_attributable") if g("pat_attributable") is not None else g("pat")
        eq_avg, se = d.avg("total_equity", y)
        emit("roe", y, div(pa, eq_avg) if (eq_avg or 0) > 0 else None, "ratio",
             ("pat_attributable" if g("pat_attributable") is not None else "pat (pat_attributable unavailable)") + " / average total_equity" + se,
             "pat_attributable,total_equity")
        payout = div(g("dividends_paid"), pa) if (pa or 0) > 0 else None
        emit("payout_ratio", y, payout, "ratio", "dividends_paid / pat_attributable", "dividends_paid,pat_attributable")
        if profile == "lender" and payout is not None and eq_avg:
            roe = div(pa, eq_avg)
            emit("internal_capital_generation", y, roe * (1 - payout) if roe is not None else None, "ratio", "roe * (1 - payout_ratio)", "roe,payout_ratio")
        if per_share_ok:
            sb, sd = g("shares_basic"), g("shares_diluted") or g("shares_basic")
            eps = div(pa, sb)
            if eps is not None:
                derived[("eps", y)] = eps
            emit("eps", y, eps, "%s per share" % cur, "pat_attributable / shares_basic", "pat_attributable,shares_basic")
            bv = div(g("total_equity"), sd)
            if bv is not None:
                derived[("bvps", y)] = bv
            emit("bvps", y, bv, "%s per share" % cur, "total_equity / shares_diluted", "total_equity,shares_diluted")
            if derived.get(("fcf", y)) is not None and sd:
                derived[("fcf_per_share", y)] = derived[("fcf", y)] / sd
                emit("fcf_per_share", y, derived[("fcf_per_share", y)], "%s per share" % cur, "fcf / shares_diluted", "fcf,shares_diluted")
            prev_sd = item("shares_diluted", y - 1) or item("shares_basic", y - 1)
            if sd and prev_sd:
                emit("share_count_change", y, sd / prev_sd - 1, "ratio", "shares_diluted_t / shares_diluted_t-1 - 1", "shares_diluted")

    if d.years:
        last = d.years[-1]
        for it in CAGR_ITEMS[profile]:
            for n in CAGR_WINDOWS:
                a, b = item(it, last), item(it, last - n)
                if a is None or b is None:
                    continue
                if a <= 0 or b <= 0:
                    notes.append("cagr_%s_%dy not computed: non-positive endpoint" % (it, n))
                    continue
                emit("cagr_%s_%dy" % (it, n), last, (a / b) ** (1.0 / n) - 1, "ratio",
                     "(%s_FY%d / %s_FY%d)^(1/%d) - 1" % (it, last, it, last - n, n), it)
    return out, notes


def _piotroski(y, item, emit):
    need = ["pat", "total_assets", "cfo", "total_debt", "current_assets", "current_liabilities", "revenue", "cogs"]
    cur = {n: item(n, y) for n in need}
    prev = {n: item(n, y - 1) for n in need}
    prev2_ta = item("total_assets", y - 2)
    if None in cur.values() or None in prev.values() or prev2_ta is None:
        return
    sh_now = item("shares_diluted", y) or item("shares_basic", y)
    sh_prev = item("shares_diluted", y - 1) or item("shares_basic", y - 1)
    if sh_now is None or sh_prev is None:
        return
    roa, roa_p = cur["pat"] / prev["total_assets"], prev["pat"] / prev2_ta
    gm = lambda d: (d["revenue"] - d["cogs"]) / d["revenue"]  # noqa: E731
    signals = [roa > 0, cur["cfo"] > 0, roa > roa_p, cur["cfo"] > cur["pat"],
               cur["total_debt"] / cur["total_assets"] < prev["total_debt"] / prev["total_assets"],
               cur["current_assets"] / cur["current_liabilities"] > prev["current_assets"] / prev["current_liabilities"],
               sh_now <= sh_prev, gm(cur) > gm(prev),
               cur["revenue"] / prev["total_assets"] > prev["revenue"] / prev2_ta]
    emit("piotroski_f_score", y, float(sum(signals)), "score 0-9",
         "ROA>0, CFO>0, dROA>0, CFO>PAT, dLeverage<0, dCurrentRatio>0, no dilution, dGrossMargin>0, dAssetTurnover>0",
         "pat,total_assets,cfo,total_debt,current_assets,current_liabilities,revenue,cogs,shares")


def _beneish(y, item, emit):
    need = ["trade_receivables", "revenue", "cogs", "current_assets", "net_fixed_assets", "total_assets",
            "depreciation", "employee_cost", "other_opex", "current_liabilities", "total_debt", "pat", "cfo"]
    c = {n: item(n, y) for n in need}
    p = {n: item(n, y - 1) for n in need}
    if None in c.values() or None in p.values():
        return
    try:
        dsri = (c["trade_receivables"] / c["revenue"]) / (p["trade_receivables"] / p["revenue"])
        gmi = ((p["revenue"] - p["cogs"]) / p["revenue"]) / ((c["revenue"] - c["cogs"]) / c["revenue"])
        aqi = (1 - (c["current_assets"] + c["net_fixed_assets"]) / c["total_assets"]) / \
              (1 - (p["current_assets"] + p["net_fixed_assets"]) / p["total_assets"])
        sgi = c["revenue"] / p["revenue"]
        depi = (p["depreciation"] / (p["depreciation"] + p["net_fixed_assets"])) / \
               (c["depreciation"] / (c["depreciation"] + c["net_fixed_assets"]))
        sgai = ((c["employee_cost"] + c["other_opex"]) / c["revenue"]) / ((p["employee_cost"] + p["other_opex"]) / p["revenue"])
        lvgi = ((c["current_liabilities"] + c["total_debt"]) / c["total_assets"]) / \
               ((p["current_liabilities"] + p["total_debt"]) / p["total_assets"])
        tata = (c["pat"] - c["cfo"]) / c["total_assets"]
    except ZeroDivisionError:
        return
    m = (-4.84 + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi
         - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)
    emit("beneish_m_score", y, m, "score",
         "-4.84+0.920*DSRI+0.528*GMI+0.404*AQI+0.892*SGI+0.115*DEPI-0.172*SGAI+4.679*TATA-0.327*LVGI "
         "(SGA ~ employee_cost+other_opex; LVGI uses current_liabilities+total_debt: approximations)",
         "receivables,revenue,cogs,current_assets,net_fixed_assets,total_assets,depreciation,opex,liabilities,pat,cfo")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("history_csv")
    ap.add_argument("--basis", help="filter rows to this basis (consolidated / standalone / segment:...)")
    ap.add_argument("--profile", choices=["general", "lender"], default="general")
    ap.add_argument("--out", help="output CSV (long format)")
    ap.add_argument("--check", action="store_true", help="validate the dataset only")
    ap.add_argument("--summary", action="store_true", help="print a wide summary of key metrics")
    a = ap.parse_args(argv)
    rows, errors, warnings = load(Path(a.history_csv), a.basis)
    for w in warnings:
        print("warn: " + w)
    if errors:
        for e in errors:
            print("ERROR: " + e)
        return 1
    d = Data(rows, (a.basis or (rows[0]["basis"] if rows else "")).lower())
    years = d.years
    print("Dataset OK: %d data points, %d fiscal years (%s..%s), %d verified against tier-1/2."
          % (len(rows), len(years), "FY%d" % years[0] if years else "-", "FY%d" % years[-1] if years else "-",
             sum(1 for r in rows if r["verified"].strip().upper() == "Y")))
    gaps = [y for y in range(years[0], years[-1] + 1) if y not in years] if years else []
    if gaps:
        print("warn: missing fiscal years inside the range: %s" % ", ".join("FY%d" % y for y in gaps))
    mins = rl.depth_minimums().get("financials.fiscal_years", 10)
    if len(years) < mins:
        print("warn: %d fiscal years < Historical Depth Standard (%d); a coverage_exception will be required" % (len(years), mins))
    if a.check:
        return 0
    out, notes = compute(d, a.profile)
    for n in notes:
        print("note: " + n)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["metric", "period", "value", "unit", "basis", "formula", "inputs"])
            w.writeheader()
            w.writerows(out)
        print("Wrote %d metric values to %s" % (len(out), a.out))
    if a.summary or not a.out:
        key = ["revenue_growth", "ebitda_margin", "roce", "roic", "roe", "cfo_to_pat", "fcf", "net_debt_to_ebitda",
               "dso", "eps", "nim", "credit_cost", "gnpa_ratio", "roa", "cost_to_income"]
        by = {(r["metric"], r["period"]): r["value"] for r in out}
        show = [k for k in key if any(m == k for (m, _) in by)]
        cols = ["FY%d" % y for y in years[-12:]]
        print("\n| metric | " + " | ".join(cols) + " |")
        print("|---|" + "---|" * len(cols))
        for k in show:
            print("| %s | %s |" % (k, " | ".join("" if by.get((k, c)) is None else "%.4g" % by[(k, c)] for c in cols)))
        cagr = [r for r in out if r["metric"].startswith("cagr_")]
        if cagr:
            print("\nCAGRs to FY%d: %s" % (years[-1], ", ".join("%s=%.1f%%" % (r["metric"], r["value"] * 100) for r in cagr)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
