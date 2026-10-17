#!/usr/bin/env python3
"""ICIL preferential share swap (Q1FY2027). Inputs: Q1FY2027 results note 3 (FIL-C063), CIO-C002 share count, CIO-C001 price."""
new_sh=146_761_335; price=1923.0; consid_mn=282_222; aa_sh=595_204_251; excess_mn=232_602
fp_shares=6_240_504_481  # CIO-C002 (24-Jul-2026, already includes allotment if completed in Q1FY27)
cmp_=1778.70             # CIO-C001
print(f"Swap ratio: {new_sh/aa_sh:.4f} BAL shares per Airtel Africa share")
print(f"Implied price per Airtel Africa share: INR {consid_mn*1e6/aa_sh:,.1f}")
print(f"NCI carrying value derecognised (consideration - excess): INR {consid_mn-excess_mn:,} mn; consideration/NCI book = {consid_mn/(consid_mn-excess_mn):.1f}x")
print(f"New shares as % of fully paid shares at 24-Jul-2026: {new_sh/fp_shares*100:.2f}%")
print(f"Value of issued shares at CIO-C001 price: INR {new_sh*cmp_/1e7:,.0f} crore vs INR {consid_mn/10:,.0f} crore at issue price")
print(f"Issue price premium to CIO-C001 (12-Oct-2026): {(price/cmp_-1)*100:.1f}%")
