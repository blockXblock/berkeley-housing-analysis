"""Permanent regression gate for S2 (dated milestone events) — FAILS if derivation / provenance /
wiring drifts. Runs the real S2 assembly and asserts the acceptance gate:
  - every event traces to a real SOURCE;
  - HONEST is_inferred: BP/CO = 0 (structured CPRA columns), entitlement = 1 (parsed text, NO date);
  - the CPRA-vs-v2 finaled-date disagreements are CAPTURED for S8 (persisted, not silently tolerated);
  - Tier-1 completions are CO-dated; no orphan events;
  - WIRING (fails-if-not-called): S2 uses s0_keys + housing_predicates, never a reimplementation.
Run: python scripts/build_v2/test_s2_gate.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s2, s0_keys, housing_predicates
from build_s2 import assemble, normalize_address

FAILS = []
def check(c, m):
    if not c: FAILS.append(m)

# ---- WIRING guards: S2 must use the shared canon, never an inline copy ----
check(build_s2.normalize_address is s0_keys.normalize_address, "WIRING: build_s2.normalize_address != s0_keys.normalize_address")
check(build_s2.net_units is housing_predicates.net_units, "WIRING: build_s2.net_units != housing_predicates.net_units")
check(build_s2.is_housing is housing_predicates.is_housing, "WIRING: build_s2.is_housing != housing_predicates.is_housing")
check(housing_predicates.is_adu is s0_keys.is_adu, "WIRING: housing_predicates.is_adu != s0_keys.is_adu")

events, ent, findings, iss_a, fin_a, smap = assemble()
spine_ids = set(smap.values())

# ---- every event traces to a real source ----
check(all(e[5] for e in events), "every event must carry a source")

# ---- honest is_inferred per event type (the heart of S2: provenance per source, not blanket 0) ----
for e in events:
    et, date, inf = e[2], e[3], e[4]
    if et in ('building_permit_issued', 'co_issued'):
        check(inf == 0 and bool(date), f"{et} must be is_inferred=0 with a structured date")
    elif et == 'entitlement_approved':
        check(inf == 1 and date is None, "entitlement_approved must be is_inferred=1 with NO asserted date (flag, don't fill)")

# ---- CPRA-vs-v2 finaled-date disagreements captured for S8 (persisted, not tolerated) ----
check(len(findings) >= 3, f"expected the >=3 CPRA-vs-v2 date findings, got {len(findings)}")
check(all(len(f) == 4 for f in findings), "each finding = (permit, field, cpra_date, v2_date)")

# ---- Tier-1 completions are CO-dated ----
co_bids = {e[0] for e in events if e[2] == 'co_issued'}
TIER1 = ["2001 Fourth St", "1950 Addison St", "1900 Walnut St", "2503 Haste St", "1808 University Ave",
         "2747 San Pablo Ave", "0 San Pablo Ave", "2740 San Pablo Ave", "2556 Telegraph Ave", "2013 Second St"]
nt = 0
for addr in TIER1:
    k = normalize_address(addr); bid = smap.get((k.number, k.street, k.stype))
    if bid in co_bids: nt += 1
    else: FAILS.append(f"Tier-1 {addr}: no co_issued event")
check(nt == 10, f"Tier-1 CO-dated {nt}/10")

# ---- no orphan events ----
check(all(e[0] in spine_ids for e in events), "no orphan events (building_id off the spine)")

if __name__ == "__main__":
    if FAILS:
        print(f"S2 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S2 GATE: PASS — {len(events)} events (BP/CO is_inferred=0 structured, entitlement=1 none-asserted) · "
          f"{len(findings)} S8 date-findings · Tier-1 {nt}/10 CO-dated · 0 orphans · wiring intact")
