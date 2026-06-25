"""Permanent regression gate for S9 (the A2 scorecard vs the city's submitted APR). S9's job is a
LIKE-FOR-LIKE CO-completions comparison + three distinct outputs; the load-bearing checks:
  - SCORECARD: v3 CO total == 4310 (s7_cycle co_issued, 2018-2025); city total is the mirror's
    table_a2 CO income-cols (read-only); net surfaced, never tuned toward.
  - COLLAPSE CLASSIFICATION: 36 collapse developments, classified by the city's CO-grain into
    CITY-GRANULAR / CITY-COLLAPSED / REPORTED-NO-CO / ABSENT (sums to 36). breakout devs ==
    CITY-GRANULAR; coverage_gap rows == ABSENT (truly absent, not merely no-CO); caveats == 36.
  - HONESTY: breakout rows are AGREEMENT-WITH-ORACLE (corroboration), the collapse caveats are
    'known-collapsed pending S1.5' (divergence partly our artifact) — labels present.
  - WIRING: static bindings to s0_keys + housing_predicates + gating + housing_rules + cpra_dedup;
    CALL-SPY that normalize_address, net_units AND housing_rules.cycle_for_date are actually INVOKED
    by gather() (the S7 orphan lesson: imported-but-uncalled is still an orphan).
  - mirror oracle-only (read-only) · s0_-s8_ untouched (s7_cycle 2236, s8_reconciliation 90).
Run: python scripts/build_v2/test_s9_gate.py
"""
import sys, os, sqlite3
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s9, s0_keys, gating, housing_predicates, cpra_dedup
import housing_rules as hr
from build_s9 import V3, MIRROR

FAILS = []
def check(c, m):
    if not c: FAILS.append(m)

# ---- STATIC WIRING ----
check(build_s9.normalize_address is s0_keys.normalize_address, "WIRING: normalize_address != s0_keys.normalize_address")
check(build_s9.snapshot_v3 is gating.snapshot_v3, "WIRING: snapshot_v3 != gating.snapshot_v3")
check(build_s9.housing_predicates is housing_predicates, "WIRING: housing_predicates module not bound")
check(build_s9.net_units is housing_predicates.net_units, "WIRING: net_units != housing_predicates.net_units")
check(build_s9.extract_master_permit is cpra_dedup.extract_master_permit, "WIRING: extract_master_permit != cpra_dedup")
check(build_s9.hr is hr, "WIRING: hr is not the housing_rules module")

# ---- CALL-SPY: normalize_address + net_units + cycle_for_date actually invoked by gather() ----
calls = Counter()
_on, _onet, _oc = s0_keys.normalize_address, housing_predicates.net_units, hr.cycle_for_date
def _sn(*a, **k): calls['normalize_address'] += 1; return _on(*a, **k)
def _snet(*a, **k): calls['net_units'] += 1; return _onet(*a, **k)
def _sc(*a, **k): calls['cycle_for_date'] += 1; return _oc(*a, **k)
s0_keys.normalize_address = _sn; build_s9.normalize_address = _sn
housing_predicates.net_units = _snet; build_s9.net_units = _snet
hr.cycle_for_date = _sc
try:
    g = build_s9.gather()
finally:
    s0_keys.normalize_address = _on; build_s9.normalize_address = _on
    housing_predicates.net_units = _onet; build_s9.net_units = _onet
    hr.cycle_for_date = _oc
check(calls['normalize_address'] > 0, "WIRING: s0_keys.normalize_address never CALLED by gather() (orphan)")
check(calls['net_units'] > 0, "WIRING: housing_predicates.net_units never CALLED by gather() (orphan)")
check(calls['cycle_for_date'] > 0, "WIRING: housing_rules.cycle_for_date never CALLED by gather() (orphan)")

cls = g['cls']
# ---- SCORECARD ----
check(g['v3_total'] == 4310, f"v3 CO total {g['v3_total']} != 4310")
check(len(g['scorecard']) == 8, f"scorecard years {len(g['scorecard'])} != 8 (2018-2025)")
check(g['city_total'] > 0, f"city CO total {g['city_total']} == 0 (mirror not read / YEAR-type bug)")

# ---- COLLAPSE CLASSIFICATION ----
check(g['collapse_n'] == 36, f"collapse developments {g['collapse_n']} != 36")
check(sum(cls.values()) == g['collapse_n'], f"classification {dict(cls)} does not sum to {g['collapse_n']}")
check(len(set(r[0] for r in g['breakout'])) == cls['CITY-GRANULAR'],
      f"breakout devs {len(set(r[0] for r in g['breakout']))} != CITY-GRANULAR {cls['CITY-GRANULAR']}")
check(len(g['coverage']) == cls['ABSENT'], f"coverage_gap {len(g['coverage'])} != ABSENT {cls['ABSENT']}")
check(len(g['pending']) == cls['REPORTED-NO-CO'], f"reported_pending {len(g['pending'])} != REPORTED-NO-CO {cls['REPORTED-NO-CO']}")
check(cls['CITY-GRANULAR'] + cls['CITY-COLLAPSED'] + cls['REPORTED-NO-CO'] + cls['ABSENT'] == 36,
      f"four-way classification does not sum to 36: {dict(cls)}")
check(len(g['caveat']) == g['collapse_n'], f"identity_caveat {len(g['caveat'])} != collapse_n {g['collapse_n']}")
check(cls['CITY-GRANULAR'] > 0, "no CITY-GRANULAR devs — S9 cannot check S1.5 at all (suspicious)")

# ---- HONESTY LABELS ----
check(all('agreement_with_oracle' in r[5] for r in g['breakout']),
      "breakout rows must be labeled agreement_with_oracle (corroboration, not independent proof)")
check(any('pending S1.5' in c[5] for c in g['caveat']), "caveats must flag 'pending S1.5'")

# ---- mirror oracle-only readable; s0-s8 untouched ----
con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
check(con.execute("SELECT COUNT(*) FROM s7_cycle").fetchone()[0] == 2236, "s7_cycle != 2236 (S9 must not touch s0-s8)")
check(con.execute("SELECT COUNT(*) FROM s8_reconciliation").fetchone()[0] == 90, "s8_reconciliation != 90 (S9 must not touch s8)")
# if persisted, the tables match gather()
have = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='s9_scorecard'").fetchone()
if have:
    check(con.execute("SELECT CAST(SUM(v3_co_units) AS INT) FROM s9_scorecard").fetchone()[0] == 4310,
          "persisted s9_scorecard v3 total != 4310")
    check(con.execute("SELECT COUNT(DISTINCT development) FROM s9_city_building_breakout").fetchone()[0] == cls['CITY-GRANULAR'],
          "persisted breakout devs != CITY-GRANULAR")
con.close()

if __name__ == "__main__":
    if FAILS:
        print(f"S9 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S9 GATE: PASS — scorecard v3 4310 vs city {g['city_total']} (net {g['v3_total']-g['city_total']:+}) · "
          f"collapse 36 = granular {cls['CITY-GRANULAR']} + collapsed {cls['CITY-COLLAPSED']} + "
          f"reported-no-CO {cls['REPORTED-NO-CO']} + absent {cls['ABSENT']} · breakout devs == granular · "
          f"coverage == absent · caveats 36 · wired+CALLED (normalize {calls['normalize_address']}x · "
          f"net_units {calls['net_units']}x · cycle_for_date {calls['cycle_for_date']}x) · s0-s8 intact")
