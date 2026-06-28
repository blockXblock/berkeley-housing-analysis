"""Permanent regression gate for S8 (reconciliation matrix). The matrix's whole job is to GATHER ALL
flagged findings, distinctly — so the load-bearing checks are the EXACT-COUNT assertions: an off-by-N
means a finding was dropped or double-gathered. Asserts:
  - EXACT-COUNT vs LIVE source tables: date_reconcile==s2_date_reconcile(3) · stage_reconcile==
    s3_stage_reconcile(33) · unit_reconcile==s4_unit_reconcile_resolved(6) · apn_overlap==s1_apn_overlap(13)
    · xaddr_review==s1_xaddr_review(22). Re-queries the sources so a future source change is caught.
  - synthesized counts: multi_building_development==1 · measurement_basis==4 · rhna_scope_question==1 ·
    entitlement_date_gap==1.
  - DISTINCT finding_types (>=8) — never flattened into one bucket.
  - pending_uc_conversion is a DISTINCT disposition (3 UC beds-only rows) — NOT needs_acquisition (0); the
    one sourced UC residence (proj170) is sourced_both.
  - WIRING: static bindings to s0_keys + housing_predicates + gating + housing_rules; and a CALL-SPY that
    housing_rules.cycle_for_date AND s0_keys.normalize_address are actually INVOKED by gather() (the S7
    re-orphaning lesson: an imported-but-uncalled function is still an orphan).
  - nothing re-derived (gathered counts equal source counts) · s0_-s7_ untouched (Tier-1 568).
Run: python scripts/build_v2/test_s8_gate.py
"""
import sys, os, sqlite3
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s8, s0_keys, gating, housing_predicates
import housing_rules as hr
from build_s8 import V3, SOURCE_COUNTS, SYNTH_COUNTS

FAILS = []
def check(c, m):
    if not c: FAILS.append(m)

# ---- STATIC WIRING ----
check(build_s8.normalize_address is s0_keys.normalize_address, "WIRING: build_s8.normalize_address != s0_keys.normalize_address")
check(build_s8.snapshot_v3 is gating.snapshot_v3, "WIRING: build_s8.snapshot_v3 != gating.snapshot_v3")
check(build_s8.housing_predicates is housing_predicates, "WIRING: build_s8.housing_predicates != housing_predicates")
check(build_s8.hr is hr, "WIRING: build_s8.hr is not the housing_rules module")

# ---- CALL-SPY WIRING: cycle_for_date (hr) + normalize_address (s0_keys) actually invoked by gather() ----
calls = Counter()
_oc, _on = hr.cycle_for_date, s0_keys.normalize_address
def _spy_c(*a, **k): calls['cycle_for_date'] += 1; return _oc(*a, **k)
def _spy_n(*a, **k): calls['normalize_address'] += 1; return _on(*a, **k)
hr.cycle_for_date = _spy_c
s0_keys.normalize_address = _spy_n
build_s8.normalize_address = _spy_n   # gather() calls the name imported into build_s8
try:
    rows = build_s8.gather()
finally:
    hr.cycle_for_date = _oc
    s0_keys.normalize_address = _on
    build_s8.normalize_address = _on
check(calls['cycle_for_date'] > 0, "WIRING: housing_rules.cycle_for_date never CALLED by gather() (orphaned)")
check(calls['normalize_address'] > 0, "WIRING: s0_keys.normalize_address never CALLED by gather() (orphaned)")

bt = Counter(r[0] for r in rows)

# ---- EXACT-COUNT vs LIVE source tables (the drop/double-gather lock) ----
con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
for ft, (src, expect) in SOURCE_COUNTS.items():
    live = con.execute(f"SELECT COUNT(*) FROM {src}").fetchone()[0]
    check(bt.get(ft, 0) == live == expect, f"{ft}: gathered {bt.get(ft,0)} != source {src} {live} (expect {expect})")
for ft, expect in SYNTH_COUNTS.items():
    check(bt.get(ft, 0) == expect, f"{ft}: {bt.get(ft,0)} != {expect}")

# ---- DISTINCT finding_types, not flattened ----
check(len(bt) >= 8, f"only {len(bt)} finding_types — distinctions flattened into fewer buckets")

# ---- pending_uc_conversion DISTINCT from needs_acquisition ----
uc = [r for r in rows if r[0] == 'measurement_basis']
pend = [r for r in uc if r[7] == 'pending_uc_conversion']
both = [r for r in uc if r[7] == 'sourced_both']
nacq = [r for r in rows if r[7] == 'needs_acquisition']
check(len(uc) == 4, f"measurement_basis {len(uc)} != 4")
check(len(pend) == 3, f"pending_uc_conversion {len(pend)} != 3 (the UC beds-only residences)")
check(len(both) == 1, f"sourced_both {len(both)} != 1 (proj170 Anchor House)")
check(len(nacq) == 0, f"{len(nacq)} rows used needs_acquisition — UC beds-only must be the DISTINCT pending_uc_conversion")

# ---- if persisted, the table matches; facts unchanged; s0-s7 untouched ----
have = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='s8_reconciliation'").fetchone()
if have:
    db_n = con.execute("SELECT COUNT(*) FROM s8_reconciliation").fetchone()[0]
    check(db_n == len(rows), f"persisted s8_reconciliation {db_n} != gather() {len(rows)} (stale table)")
    db_pend = con.execute("SELECT COUNT(*) FROM s8_reconciliation WHERE disposition='pending_uc_conversion'").fetchone()[0]
    check(db_pend == 3, f"persisted pending_uc_conversion {db_pend} != 3")
t1 = con.execute("""SELECT CAST(SUM(units) AS INT) FROM s4_units WHERE bucket IN
    ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO',
     '0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND')""").fetchone()[0]
check(t1 == 568, f"Tier-1 units {t1} != 568 (S8 must not change any value)")
# s7 still intact (prior stage untouched)
s7 = con.execute("SELECT COUNT(*) FROM s7_cycle").fetchone()[0]
check(s7 == 2236, f"s7_cycle {s7} != 2236 (S8 must not touch s0-s7)")
con.close()

if __name__ == "__main__":
    if FAILS:
        print(f"S8 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S8 GATE: PASS — exact-count locked (date 3 · stage 33 · unit 6 · apn 13 · xaddr 22 = source tables) · "
          f"synth (multi_building 1 · UC measurement_basis 4 · rhna_scope 1 · entitlement_gap 1) · {len(bt)} distinct types · "
          f"pending_uc_conversion 3 != needs_acquisition 0 · wired+CALLED (cycle_for_date {calls['cycle_for_date']}x · "
          f"normalize_address {calls['normalize_address']}x) · Tier-1 568 · s0-s7 intact")
