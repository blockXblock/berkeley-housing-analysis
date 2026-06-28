"""Permanent regression gate for S1 (CPRA spine ingest) — FAILS if the spine/classify drifts.

Runs the real S1 derivation against live CPRA + v3.s0_key_index and asserts the acceptance gate:
  - 10/10 Tier-1 material completions present as CREATE at 568u
  - 2503 Haste collapsed to ONE 55u building (phase-triple-count guard)
  - 0 CROSS-address false-ATTACHes (the 1808/1812 regression)
  - 1808 University CREATEs (44u) and does NOT ATTACH to proj307 (1812, 2u) on the shared APN
  - same-address unit disagreements route to the S4 queue, not the suspect list
  - WIRING GUARD: S1 imports the key logic from s0_keys (fails-if-not-called / no reimplementation)

Run: python -m scripts.build_v2.test_s1_gate   (or: python scripts/build_v2/test_s1_gate.py)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s1
import s0_keys
from build_s1 import build_spine, classify, load_s0_index, tier1_check, scan_attaches, normalize_address, is_housing, net_units
from s0_keys import is_adu
import numpy as _np

FAILS = []
def check(cond, msg):
    if not cond: FAILS.append(msg)

# ---- WIRING GUARD: S1 must use s0_keys' canon, never a reimplementation ----
check(build_s1.normalize_address is s0_keys.normalize_address,
      "WIRING: build_s1.normalize_address is NOT s0_keys.normalize_address (reimplementation/drift)")
check(build_s1.AddressKey is s0_keys.AddressKey, "WIRING: build_s1.AddressKey is not s0_keys.AddressKey")
check(build_s1.canonicalize_apn is s0_keys.canonicalize_apn,
      "WIRING: build_s1.canonicalize_apn is NOT s0_keys.canonicalize_apn (APN-canon reimplementation/drift)")
import housing_predicates as _hp
check(build_s1.is_housing is _hp.is_housing and build_s1.net_units is _hp.net_units,
      "WIRING: build_s1 must use the shared housing_predicates.is_housing/net_units (no inline copy)")
check(_hp.is_adu is s0_keys.is_adu, "WIRING: housing_predicates must use the shared s0_keys.is_adu")
check(s0_keys.canonicalize_apn('057 201602101') == '057-2016-021-01',
      "WIRING: APN canon format drifted from Option-B dashed")

# ---- housing predicate regression: the false-negatives the guard caught must stay IN; 0-unit
#      non-housing must stay OUT (guards against an OccType-only over-tighten re-appearing) ----
check(is_housing('A-2 Assembly: Food or Drink Consumption', '78', '78', 'No data available'),
      "3000 San Pablo 78u mixed-use (A-2 + units) must be housing")
check(is_housing('U Private Garages, Carports, Sheds, Agricultural, Tanks, Accessory', '2', '2', 'Yes'),
      "U-coded ADU with units must be housing")
check(is_housing('Not Applicable (new)', 'nan', 'nan', 'Yes'),
      "ADU=Yes with no occ/units must be housing")
check(is_housing('R-3 Residential: Dwellings (1 or 2 Units)', 'nan', 'nan', 'No data available'),
      "R-3 dwelling (occupancy only, no unit data) must be housing")
check(not is_housing('U Private Garages, Carports, Sheds, Agricultural, Tanks, Accessory', 'nan', 'nan', 'No data available'),
      "0-unit garage (U, no units, not ADU) must NOT be housing")
check(not is_housing('B Business', '0', '0', 'No data available'), "0-unit commercial must NOT be housing")

# ---- net_units (Q3 unit signal) regression: recover NumberUnits-coded ADUs, cap contamination,
#      exclude existing-stock alterations (the bugs that dropped 265 ADUs / nearly added 4,239u) ----
check(net_units(False, 'nan', '1', 'Yes') == 1, "NumberUnits-coded ADU (1322 Carleton garage->ADU) must count 1")
check(net_units(False, '0', '2', 'Yes') == 2, "duplex ADU via NumberUnits must count 2")
check(net_units(False, '0', '82', 'Yes') == 2, "contaminated ADU nu=82 must CAP to min(nu,2)=2, not 82")
check(net_units(False, '0', '11', 'No data available') == 0, "existing-stock alteration (nu=11) must count 0, NOT add stock")
check(net_units(True, '0', '152', 'No data available') == 152, "New building with units in NumberUnits must count 152")
check(net_units(False, '40', '0', 'No data available') == 40, "explicit UnitsAdded must count as-is")

# ---- is_adu type-variant regression: the silent dead branch (str(numpy.True_)='true'!='yes') ----
check(is_adu(True) and is_adu(_np.bool_(True)) and is_adu('Yes') and is_adu('yes'), "is_adu must be True for bool/np.bool/'Yes'/'yes'")
check(not is_adu(False) and not is_adu(_np.bool_(False)) and not is_adu('No data available') and not is_adu('nan'),
      "is_adu must be False for bool/np.bool False / 'No data available' / 'nan'")

# ---- spine recovery: a NumberUnits-coded ADU is now IN the spine (was silently dropped) ----
_adu_k = normalize_address("1322 Carleton St")
check((_adu_k.number, _adu_k.street, _adu_k.stype) in build_spine()[0],
      "1322 Carleton (garage->ADU, units in NumberUnits) must be recovered into the spine")

# ---- pure-key regression: 1808 != 1812 University (a shared APN must never merge them) ----
check(not normalize_address("1808 University Ave").matches(normalize_address("1812 University Ave")),
      "1808 != 1812 University: different house numbers must never match (shared-APN false-ATTACH guard)")

# ---- run the real S1 derivation ----
by_family, by_apn, by_bucket, protected, n_idx = load_s0_index()
spine, resi, excluded, df = build_spine()
create, attach = classify(spine, by_family, by_apn, by_bucket)
suspects, review, s4_queue = scan_attaches(attach)

# Tier-1: all 10 present as CREATE, total 568u
t1 = tier1_check(create)
for addr, exp, found, ok in t1:
    check(ok, f"Tier-1 {addr}: expected {exp}u, got {found}")
check(sum((f or 0) for _, _, f, _ in t1) == 568, f"Tier-1 total != 568 (got {sum((f or 0) for *_, f, _ in t1)})")

# 2503 Haste: ONE building, 55u (phase-triple-count guard)
hk = normalize_address("2503 Haste St")
haste = {(r['gk'][0], r['gk'][1]): r for r in create}.get((hk.number, hk.street))
check(haste is not None and abs(haste['units'] - 55) < 1, "2503 Haste not a single 55u CREATE")

# 0 cross-address false-ATTACHes
check(len(suspects) == 0, f"{len(suspects)} CROSS-address false-ATTACH(es): {suspects[:3]}")

# 1808 University: CREATE (not ATTACH), flagged apn_overlap with proj307; never attached to 307
k = normalize_address("1808 University Ave")
c_1808 = [r for r in create if (r['gk'][0], r['gk'][1]) == (k.number, k.street)]
a_1808 = [r for r in attach if (r['gk'][0], r['gk'][1]) == (k.number, k.street)]
check(len(c_1808) == 1 and not a_1808, "1808 University must be CREATE, not ATTACH")
check(bool(c_1808) and 307 in c_1808[0]['apn_overlap'],
      "1808 University must carry apn_overlap flag for proj307 (corroborating, not merged)")
# proj307 (1812 University) must never be reached by a CROSS-address ATTACH (the 1808 mislink);
# a SAME-address ATTACH from a real 1812 building is fine.
for r in attach:
    if 307 in r['hit']:
        pk = normalize_address("1812 University Ave")
        check((r['gk'][0], r['gk'][1]) == (pk.number, pk.street),
              f"proj307 received a CROSS-address ATTACH from {r['gk']} (the 1808/1812 false-ATTACH)")

# same-vs-cross criterion: the known same-address undercounts are in the S4 queue, not suspects
s4_buckets = {(g[0], g[1]) for g, *_ in s4_queue}
for addr in ("739 Channing Way", "2328 Channing Way", "2330 Blake St"):
    kk = normalize_address(addr)
    check((kk.number, kk.street) in s4_buckets,
          f"{addr}: same-address undercount must be in S4 queue (not a suspect)")

if __name__ == "__main__":
    if FAILS:
        print(f"S1 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S1 GATE: PASS — 10/10 Tier-1 @568u · Haste 55u · 0 cross-address false-ATTACH · "
          f"1808 CREATEs (apn_overlap 307) · {len(s4_queue)} S4-undercount queued · wiring intact")
