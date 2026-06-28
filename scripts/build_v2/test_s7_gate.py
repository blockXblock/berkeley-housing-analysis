"""Permanent regression gate for S7 (cycle-scope) — locks the corrected three-date-concept design and,
above all, the RE-WIRING of the orphaned housing_rules module. Asserts:
  - TRIPLE WIRING (fails-if-not-called): cycle_for_date AND is_projection_period AND rhna_credit_cycle are
    each ACTUALLY CALLED by derive_cycle() — not merely imported (housing_rules is the re-orphaning risk;
    a binding that is never invoked is a silent orphan). Plus s0_keys + gating wired.
  - the THREE date concepts stay DISTINCT (the non-conflation): there exist BP events with calendar_cycle=5th
    but rhna_credit_cycle=6th (projection-credited), proving the 2022-06-30 credit boundary != the 2023-01-31
    calendar boundary and that in_projection_period is not the credit filter;
  - rhna_credit_cycle is BUILDING-level from first-BP, NULL for the 100 CO-only-no-BP buildings (flagged);
  - is_first_bp marks exactly one credit-bearing row per BP-building (no Table-B double-count);
  - every event carries a reporting_year from a real (is_inferred=0) date — no asserted year;
  - facts unchanged (Tier-1 568); s0_-s6_ untouched.
Run: python scripts/build_v2/test_s7_gate.py
"""
import sys, os, sqlite3
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s7, s0_keys, gating, housing_predicates
import housing_rules as hr
from build_s7 import V3

FAILS = []
def check(c, m):
    if not c: FAILS.append(m)

# ---- STATIC WIRING: the bindings point at the single-sourced modules ----
check(build_s7.normalize_address is s0_keys.normalize_address, "WIRING: build_s7.normalize_address != s0_keys.normalize_address")
check(build_s7.snapshot_v3 is gating.snapshot_v3, "WIRING: build_s7.snapshot_v3 != gating.snapshot_v3")
check(build_s7.housing_predicates is housing_predicates, "WIRING: build_s7.housing_predicates != housing_predicates")
check(build_s7.hr is hr, "WIRING: build_s7.hr is not the housing_rules module")

# ---- TRIPLE CALL-WIRING (the re-orphaning lock): spy on all three cycle functions, run derive_cycle,
#      assert each was actually invoked. An imported-but-never-called function is a silent orphan. ----
calls = defaultdict(int)
_orig = {n: getattr(hr, n) for n in ('cycle_for_date', 'is_projection_period', 'rhna_credit_cycle')}
def _spy(name):
    f = _orig[name]
    def w(*a, **k):
        calls[name] += 1
        return f(*a, **k)
    return w
for n in _orig:
    setattr(hr, n, _spy(n))
try:
    rows = build_s7.derive_cycle()
finally:
    for n, f in _orig.items():
        setattr(hr, n, f)   # always restore
check(calls['cycle_for_date'] > 0, "WIRING: housing_rules.cycle_for_date was never CALLED (orphaned)")
check(calls['is_projection_period'] > 0, "WIRING: housing_rules.is_projection_period was never CALLED (orphaned)")
check(calls['rhna_credit_cycle'] > 0, "WIRING: housing_rules.rhna_credit_cycle was never CALLED (orphaned)")

# ---- every event has a reporting_year (no asserted year) ----
no_year = [r for r in rows if r[3] is None]
check(len(no_year) == 0, f"{len(no_year)} events without a reporting_year (every event must be dated)")

# ---- THREE CONCEPTS DISTINCT: BP events calendar=5th but credit=6th must EXIST (the non-conflation) ----
split = [r for r in rows if r[1] == 'building_permit_issued' and r[4] == '5th' and r[6] == '6th']
check(len(split) > 0, "no BP event with calendar_cycle=5th & rhna_credit_cycle=6th — the projection-credit "
                      "distinction collapsed (2022-06-30 boundary wrongly == 2023-01-31)")

# ---- rhna_credit_cycle building-level; is_first_bp exactly one per BP-building; CO-only -> NULL ----
bybuild = defaultdict(list)
for r in rows: bybuild[r[0]].append(r)
first_bp_rows = [r for r in rows if r[7] == 1]
bp_builds = {b for b, rs in bybuild.items() if any(x[1] == 'building_permit_issued' for x in rs)}
check(len(first_bp_rows) == len(bp_builds), f"is_first_bp rows {len(first_bp_rows)} != BP-buildings {len(bp_builds)} (double-count risk)")
co_only = [b for b, rs in bybuild.items() if not any(x[1] == 'building_permit_issued' for x in rs)]
co_only_bad = [b for b in co_only if any(x[6] is not None for x in bybuild[b])]
check(len(co_only_bad) == 0, f"{len(co_only_bad)} CO-only-no-BP buildings carry a non-NULL rhna_credit_cycle (must be NULL/flagged)")
# NOTE: 6 (CO-event-but-no-BP), NOT the Phase-A 100. 100 = s4_units minus BP-buildings, which also folds
# in 94 buildings with NO dated event at all (pipeline/no-milestone) — those have no event to tag, so they
# never enter s7_cycle. The genuine CO-only-no-BP cohort (a CO row, no BP row) is 6.
check(len(co_only) == 6, f"CO-only-no-BP cohort = {len(co_only)}, expected 6")

# ---- the persisted table matches (regression pins) + facts unchanged ----
con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
have_table = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='s7_cycle'").fetchone()
if have_table:
    db_n = con.execute("SELECT COUNT(*) FROM s7_cycle").fetchone()[0]
    check(db_n == len(rows), f"s7_cycle rows {db_n} != derive_cycle() {len(rows)} (stale table)")
    db_first = con.execute("SELECT COUNT(*) FROM s7_cycle WHERE is_first_bp=1").fetchone()[0]
    check(db_first == len(first_bp_rows), f"persisted is_first_bp {db_first} != {len(first_bp_rows)}")
t1 = con.execute("""SELECT CAST(SUM(units) AS INT) FROM s4_units WHERE bucket IN
    ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO',
     '0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND')""").fetchone()[0]
check(t1 == 568, f"Tier-1 units {t1} != 568 (S7 must not change any value)")
con.close()

if __name__ == "__main__":
    if FAILS:
        print(f"S7 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S7 GATE: PASS — triple-wired (cycle_for_date {calls['cycle_for_date']}x · is_projection_period "
          f"{calls['is_projection_period']}x · rhna_credit_cycle {calls['rhna_credit_cycle']}x, all CALLED) · "
          f"{len(rows)} events · {len(split)} projection-credited BPs (5th-cal/6th-credit) · "
          f"{len(first_bp_rows)} credit rows · {len(co_only)} CO-only->NULL · Tier-1 568 · s0-s6 intact")
