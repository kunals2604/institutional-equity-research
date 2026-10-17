# Valuation research plan — BHARTIARTL, run 20261012T132311Z

Cutoff 2026-10-12. Price CIO-C001 = INR 1,778.70 (NSE close 12-Oct-2026).

## Decision questions (agent definition)
1. Verified price, basic/diluted shares, market cap, net debt (with/without leases; deferred spectrum + AGR), EV.
2. Liquidity: 90-day ADTV, free float, F&O/index membership, surveillance; FPI/DII 12 quarters.
3. 15-20 years: annual price, TSR vs Nifty 500 TRI, max drawdowns (causes, recovery), P/E and EV/EBITDA ranges + current percentile.
4. Method selection per plausible layer (L1 long-duration DCF/owner earnings; L2 scenario DCF; L3 normalized/SOTP; L4 outcome tree for adjacencies).
5. Reverse DCF (growth, margin), compared with 10-y history and base rates.
6. Bear/base/bull 5-year horizon values, probabilities with basis, E[IRR], asymmetry, MoS.
7. Drivers, sensitivity, price ladder ±40%.

## Data series and sources
| Series | Years | Source (tier) |
|---|---|---|
| Daily price history BHARTIARTL.NS | 2002-2026 | Yahoo chart API (5), spot-verified vs NSE bhavcopy (1) |
| Nifty 500 / Nifty 50 TRI | 2006-2026 | niftyindices.com (5) or Yahoo index (5) |
| Annual consolidated financials (rev, EBITDA, PAT, net debt, shares) | FY2006-FY2026 | Annual reports / results (1) via corpus + IR; aggregator (5) for older years |
| Q1FY2027 / Q4FY2026 results | latest | corpus (1) |
| Shareholding pattern 12 quarters | Sep-2023..Sep-2026 | BSE / IR (1), aggregator (5) |
| 10-y G-Sec yield | Oct-2026 | RBI/FBIL/CCIL or market data |
| ERP India | 2026 | Damodaran (5) |
| Beta | 2-5y weekly regression vs Nifty 50 | computed from price data |
| Listed subsidiaries market caps (Airtel Africa, Indus, Hexacom) | Oct-2026 | exchange data |
| Peers multiples (Jio/RIL, Vi, Indus, global) | 2026 | filings / aggregators |

## Calc files
calc/valuation_wacc_inputs.json -> valuation_wacc.json
calc/valuation_dcf_inputs*.json -> valuation_dcf*.json
calc/valuation_reverse_*.json
calc/valuation_scenarios.json -> valuation_scenario_irr.json, valuation_price_ladder.json
calc/valuation_decompose_inputs.json -> valuation_decompose.json
calc/valuation_price_history.py (TSR, drawdowns, multiples, beta, ADTV)
