"""CIO preflight: market cap from CIO-C001 (price) and CIO-C002/C004 (share counts)."""
price = 1778.70                      # CIO-C001, NSE bhavcopy close 12-Oct-2026
fully_paid = 6_240_504_481           # CIO-C002, Airtel filing 24-Jul-2026
partly_paid = 649_835                # CIO-C004, paid-up INR 1.25 of INR 5 face; call INR 401.25 unpaid
mcap_fp = price * fully_paid / 1e7   # INR crore
# economic value of partly paid: price less unpaid call
mcap_pp = (price - 401.25) * partly_paid / 1e7
print("market_cap_fully_paid_inr_cr=%.2f" % mcap_fp)
print("partly_paid_economic_value_inr_cr=%.2f" % mcap_pp)
print("market_cap_total_inr_cr=%.2f" % (mcap_fp + mcap_pp))
