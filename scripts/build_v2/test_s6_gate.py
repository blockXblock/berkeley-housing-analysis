"""Permanent regression gate for S6 (confidence = f(source presence)) — the KEY lock against the
migration's original sin (confidence=high stamped on everything). Asserts:
  - 0 facts at confidence=high WITHOUT a real backing (structured column / evidence resolution / typed
    doc / dated event) — the migration-bug lock;
  - confidence is FACT-LEVEL, not a blanket constant (varies per building; >=2 tiers in use);
  - the per-fact distribution is consistent with what S2-S5 recorded;
  - market_rate_no_obligation -> a distinct MIDDLE (medium) tier, neither high nor low;
  - facts unchanged; WIRING (fails-if-not-called): S6 uses s0_keys + gating.
Run: python scripts/build_v2/test_s6_gate.py
"""
import sys, os, sqlite3
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s6, s0_keys, gating
from build_s6 import derive_confidence, V3

FAILS = []
def check(c, m):
    if not c: FAILS.append(m)

# ---- WIRING ----
check(build_s6.normalize_address is s0_keys.normalize_address, "WIRING: build_s6.normalize_address != s0_keys.normalize_address")
check(build_s6.snapshot_v3 is gating.snapshot_v3, "WIRING: build_s6.snapshot_v3 != gating.snapshot_v3")

rows = derive_confidence()

# ---- THE MIGRATION-BUG LOCK: 0 high facts without a real backing ----
HIGH_OK = ('structured net_units', 'reconciled by structured evidence (s4)', 'typed affordability doc (DBE/AHA), document-cited')
def backed(b): return b in HIGH_OK or b.startswith('event-derived') or b.startswith('structured CPRA date')
unbacked = [r for r in rows if r[4] == 'high' and not backed(r[5])]
check(len(unbacked) == 0, f"{len(unbacked)} high facts WITHOUT a real backing — the migration's blanket-high must be impossible")

# ---- fact-level, not a blanket constant ----
tiers = set(r[4] for r in rows)
check(tiers == {'high', 'medium', 'low'}, f"expected three tiers high/medium/low, got {sorted(tiers)}")
perb = defaultdict(set)
for r in rows:
    if r[1] is not None: perb[r[1]].add(r[4])
varies = sum(1 for s in perb.values() if len(s) > 1)
check(varies > 1000, f"confidence barely varies ({varies}) — must be fact-level, not constant")

# ---- per-fact distribution consistent with S2-S5 (deterministic regression pins) ----
bf = defaultdict(Counter)
for r in rows: bf[r[3]][r[4]] += 1
check(bf['units']['high'] == 1303 and bf['units']['low'] == 82, f"units dist drifted: {dict(bf['units'])}")
check(bf['stage']['high'] == 1274 and bf['stage']['low'] == 111, f"stage dist drifted: {dict(bf['stage'])}")
check(bf['dates']['high'] == 1288 and bf['dates']['low'] == 97, f"dates dist drifted: {dict(bf['dates'])}")
check(bf['affordability']['high'] == 9 and bf['affordability']['medium'] == 1219 and bf['affordability']['low'] == 166,
      f"affordability dist drifted: {dict(bf['affordability'])}")

# ---- market_rate_no_obligation is the MIDDLE (medium) tier, distinct from high and low ----
check(bf['affordability']['medium'] == 1219, "market_rate must map to a distinct 'medium' tier (not high, not low)")

# ---- facts unchanged ----
con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
t1 = con.execute("""SELECT CAST(SUM(units) AS INT) FROM s4_units WHERE bucket IN
    ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO',
     '0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND')""").fetchone()[0]
check(t1 == 568, f"Tier-1 units {t1} != 568 (S6 must not change any value)")
con.close()

if __name__ == "__main__":
    if FAILS:
        print(f"S6 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S6 GATE: PASS — 0 high-without-backing (migration-bug locked) · fact-level ({varies}/1385 vary) · "
          f"units 1303/82 · stage 1274/111 · dates 1288/97 · affordability 9/1219/166 · market_rate=medium · wiring intact")
