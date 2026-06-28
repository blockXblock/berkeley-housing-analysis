"""Permanent regression gate for S3 (stage derived from events) — FAILS if derivation / the two-
findings separation / wiring drifts. Asserts:
  - 0 ASSERTED stages (every non-pipeline stage justified by an event; pipeline = honest floor);
  - co_issued <-> completed is 1:1; Tier-1 completions at 'completed';
  - the v1 stage disagreements (Finding A) are captured for S8;
  - Finding A (stage over-assertion) and Finding B (the 757 entitlement-EVENT gap) stay DISTINCT —
    most v1-entitled+ projects derive completed/permitted (event-backed), so 757 != the ~33;
  - WIRING (fails-if-not-called): S3 uses s0_keys + gating, never a reimplementation.
Run: python scripts/build_v2/test_s3_gate.py
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s3, s0_keys, gating
from build_s3 import derive_all, v1_stages, reconcile_vs_v1, normalize_address, RANK, V2

FAILS = []
def check(c, m):
    if not c: FAILS.append(m)

# ---- WIRING guards ----
check(build_s3.normalize_address is s0_keys.normalize_address, "WIRING: build_s3.normalize_address != s0_keys.normalize_address")
check(build_s3.snapshot_v3 is gating.snapshot_v3, "WIRING: build_s3.snapshot_v3 != gating.snapshot_v3 (snapshot helper drift)")

rows, ev = derive_all()
v1 = v1_stages()
findings = reconcile_vs_v1(rows, v1)

# ---- 0 asserted stages: every non-pipeline stage names a justifying event ----
asserted = [bid for bid, r in rows.items() if r['stage'] != 'pipeline' and not r['justified_by']]
check(len(asserted) == 0, f"{len(asserted)} asserted stages (non-pipeline with no justifying event)")
# pipeline buildings must genuinely have no event
check(all(not ev.get(bid) for bid, r in rows.items() if r['stage'] == 'pipeline'), "a pipeline building has events (should derive higher)")

# ---- co_issued <-> completed is 1:1 ----
co = {bid for bid in rows if 'co_issued' in ev.get(bid, set())}
comp = {bid for bid, r in rows.items() if r['stage'] == 'completed'}
check(co == comp, "co_issued set != completed set (a completion not event-justified, or vice versa)")

# ---- Tier-1 at completed ----
bybucket = {r['bucket']: r for r in rows.values()}
TIER1 = ["2001 Fourth St","1950 Addison St","1900 Walnut St","2503 Haste St","1808 University Ave",
         "2747 San Pablo Ave","0 San Pablo Ave","2740 San Pablo Ave","2556 Telegraph Ave","2013 Second St"]
nt = sum(1 for a in TIER1 for k in [normalize_address(a)] if bybucket.get(f"{k.number} {k.street}".strip(), {}).get('stage') == 'completed')
check(nt == 10, f"Tier-1 at completed {nt}/10")

# ---- Finding A captured + has the v1=completed->pipeline cases ----
check(len(findings) >= 1 and all(len(f) == 5 for f in findings), "stage disagreements malformed")
comp_pipe = [f for f in findings if f[2] == 'completed' and f[3] == 'pipeline']
check(len(comp_pipe) >= 1, "expected v1=completed but events=pipeline findings (v2 completions we can't corroborate)")

# ---- Finding A vs Finding B kept DISTINCT (the conflation guard) ----
v2 = sqlite3.connect(f'file:{V2}?mode=ro', uri=True)
has_ent = {r[0] for r in v2.execute("SELECT DISTINCT pe.project_id FROM project_events pe "
          "JOIN vocabulary_event_types vt ON vt.id=pe.event_type_id WHERE vt.code='entitlement_approved'")}
v2.close()
a757 = {pid for pid, s in v1.items() if RANK.get(s, 0) >= 2 and pid not in has_ent}
pid2der = {}
for bid, r in rows.items():
    for pid in r['v2_ids']: pid2der.setdefault(pid, set()).update([r['stage']])
backed = sum(1 for p in a757 if pid2der.get(p, set()) & {'completed', 'permitted'})
check(len(a757) > 100, f"the 757 entitlement-event gap should be large, got {len(a757)}")
check(backed > len(findings) * 5, "Finding B (757 entitlement gap) must be far larger than Finding A (stage disagreements) and mostly event-backed — they are NOT the same finding")

if __name__ == "__main__":
    if FAILS:
        print(f"S3 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S3 GATE: PASS — 0 asserted stages · co<->completed 1:1 · Tier-1 {nt}/10 · "
          f"{len(findings)} stage-disagreements (A) incl {len(comp_pipe)} completed->pipeline · "
          f"{len(a757)} entitlement-gap (B, {backed} event-backed) kept DISTINCT · wiring intact")
