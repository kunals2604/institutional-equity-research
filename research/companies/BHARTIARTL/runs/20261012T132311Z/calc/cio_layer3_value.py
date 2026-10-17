"""CIO: Layer 3 (cyclical/event) current-price assessment for BHARTIARTL (revised after the Stage-3 adversarial review).
The base case now carries one realised tariff round in year 2 (CIO-C056: INR 1,306-1,509, point 1,378).
Two rounds (years 2 and 5) give a DCF point of INR 1,519 (BEAR-C085). Floor = trough-multiple earnings floor (SPS-C082)."""
price = 1778.70                  # CIO-C001
one_round = (1306.0, 1378.0, 1509.0)   # CIO-C056 lo / point / hi
two_rounds_point = 1519.0        # BEAR-C085
print("one_round_base lo=%.0f point=%.0f hi=%.0f; price premium to point=%.3f" % (one_round[0], one_round[1], one_round[2], price / one_round[1] - 1))
print("two_rounds_point=%.0f; price premium=%.3f" % (two_rounds_point, price / two_rounds_point - 1))
print("floor_trough_multiple=915-1113; stress=685-853 (SPS-C082)")
