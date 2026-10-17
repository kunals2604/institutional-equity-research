"""CIO audit: reconcile shares issued at 31-Mar-2026 (financials FIN-C057) to the 24-Jul-2026 count (CIO-C002)."""
fully_paid_jul24 = 6_240_504_481   # CIO-C002 (after July conversion approval)
partly_paid_jul24 = 649_835        # CIO-C004
icil_swap = 146_761_335            # CIO-C035, issued in Q1FY2027
jul_conversion = 460_833           # converted partly-paid -> fully paid, approved 24-Jul-2026 (CIO-C002 filing)
partly_paid_before_jul = 1_110_668 # outstanding partly paid before July conversion (same filing)
fully_paid_pre_swap = fully_paid_jul24 - icil_swap - jul_conversion
total_issued_mar26_implied = fully_paid_pre_swap + partly_paid_before_jul
print("fully_paid_31mar2026_implied=%d" % fully_paid_pre_swap)
print("total_issued_incl_partly_paid_31mar2026_implied=%d (%.2f crore)" % (total_issued_mar26_implied, total_issued_mar26_implied / 1e7))
print("check partly paid: %d - %d = %d (filing says 649,835)" % (partly_paid_before_jul, jul_conversion, partly_paid_before_jul - jul_conversion))
print("swap_dilution_vs_pre_swap=%.4f" % (icil_swap / (fully_paid_pre_swap + partly_paid_before_jul)))
