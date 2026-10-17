"""CIO audit: recompute 90-session ADTV (close x volume) to 12-Oct-2026 from Yahoo daily data (tier 5)."""
import json, datetime, sys, os
p = os.path.join(os.path.dirname(__file__), "yahoo_6m_daily.json")
d = json.load(open(p))["chart"]["result"][0]
q = d["indicators"]["quote"][0]
rows = [(datetime.datetime.utcfromtimestamp(t).date(), c, v) for t, c, v in zip(d["timestamp"], q["close"], q["volume"]) if c and v]
rows = [r for r in rows if str(r[0]) <= "2026-10-12"][-90:]
tv = [c * v / 1e7 for _, c, v in rows]
print("sessions=%d from=%s to=%s" % (len(rows), rows[0][0], rows[-1][0]))
print("adtv_90_inr_cr=%.1f median=%.1f" % (sum(tv) / len(tv), sorted(tv)[len(tv) // 2]))
print("days_to_exit_ref_position=%.4f" % (5000000 / 1e7 / (0.2 * sum(tv) / len(tv))))
