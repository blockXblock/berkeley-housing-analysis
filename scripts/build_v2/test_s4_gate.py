"""Permanent regression gate for S4 (finalize units + resolve reconcile) — FAILS if the resolution
logic / canonical units / wiring drifts. Asserts:
  - the 6 reconcile disagreements are each RESOLVE_OURS (by evidence) or FLAG_S8 (held) — NONE guessed;
  - the 5 resolved land on their evidenced values (170/14/13/17/6); 2352 Shattuck is FLAGged, held at 135;
  - canonical units == net_units for every building (S4 re-derives nothing); 0 internal leak; Tier-1 568;
  - WIRING (fails-if-not-called): S4 uses s0_keys + housing_predicates + gating, never a reimplementation.
Run: python scripts/build_v2/test_s4_gate.py
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s4, s0_keys, housing_predicates, gating
from build_s4 import resolve_reconcile, normalize_address, V3

FAILS = []
def check(c, m):
    if not c: FAILS.append(m)

# ---- WIRING guards ----
check(build_s4.net_units is housing_predicates.net_units, "WIRING: build_s4.net_units != housing_predicates.net_units")
check(build_s4.normalize_address is s0_keys.normalize_address, "WIRING: build_s4.normalize_address != s0_keys.normalize_address")
check(build_s4.snapshot_v3 is gating.snapshot_v3, "WIRING: build_s4.snapshot_v3 != gating.snapshot_v3")

# ---- the 6 reconcile resolutions: evidence-or-flag, none guessed ----
resolved = resolve_reconcile()
check(len(resolved) == 6, f"expected 6 reconcile rows, got {len(resolved)}")
for bucket, cu, pid, vu, verdict, canon, why in resolved:
    check(verdict in ('RESOLVE_OURS', 'FLAG_S8'), f"{bucket}: verdict must be resolve-or-flag, not a guess")
    check(canon == cu, f"{bucket}: canonical must HOLD the structured value (write only what's corroborated), not a guessed compromise")
    check(bool(why), f"{bucket}: every resolution must cite its evidence")
rmap = {r[0]: r for r in resolved}
EXPECT = {'1500 SAN PABLO': 170, '739 CHANNING': 14, '2328 CHANNING': 13, '2317 CHANNING': 17, '2330 BLAKE': 6}
for b, u in EXPECT.items():
    check(b in rmap and rmap[b][5] == u and rmap[b][4] == 'RESOLVE_OURS', f"{b} must resolve by evidence to {u}")
check('2352 SHATTUCK' in rmap and rmap['2352 SHATTUCK'][4] == 'FLAG_S8' and rmap['2352 SHATTUCK'][5] == 135,
      "2352 Shattuck (Logan Park multi-building) must be FLAGGED to S8 and held at 135 — not guessed to 237")

# ---- canonical == net_units (0 leak); Tier-1 568 ----
con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
leak = con.execute("SELECT COUNT(*) FROM s4_units s JOIN s1_projects p ON p.building_id=s.building_id WHERE s.units<>p.units").fetchone()[0]
check(leak == 0, f"{leak} buildings where canonical != net_units (S4 must re-derive nothing)")
t1 = con.execute("""SELECT CAST(SUM(units) AS INT) FROM s4_units WHERE bucket IN
    ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO',
     '0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND')""").fetchone()[0]
check(t1 == 568, f"Tier-1 units {t1} != 568")
nrows = con.execute("SELECT COUNT(*) FROM s4_units").fetchone()[0]
check(nrows == 1385, f"s4_units rows {nrows} != 1385")
con.close()

if __name__ == "__main__":
    if FAILS:
        print(f"S4 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S4 GATE: PASS — 6 reconcile (5 resolved-by-evidence 170/14/13/17/6, 1 FLAG-S8 held@135, none guessed) · "
          f"canonical==net_units (0 leak) · Tier-1 568 · 1385 rows · wiring intact")
