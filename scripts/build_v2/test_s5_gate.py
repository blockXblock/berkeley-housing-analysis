"""Permanent regression gate for S5 (affordability) — FAILS if the fabrication-laundering trap, the
market-by-subtraction bug, or the wiring re-appears. Asserts:
  - NO fabricated/stub tiers PRESENT: every non-needs_acquisition tier row has a real source doc + basis=cited;
  - NO market-by-subtraction: no ABOVE_MOD row without a source doc (above-mod is only ever source-stated);
  - the 9 genuinely-cited (typed DBE/AHA docs) fold at confidence=high, reconciling to planned totals;
  - proj8/15/35 MOD tiers present (the 2-bucket model couldn't hold them);
  - below-market gaps -> needs_acquisition (flagged with units, NOT zeroed); tier-sum reconciles per-population;
  - unit totals unchanged; WIRING (fails-if-not-called): S5 uses s0_keys + gating.
Run: python scripts/build_v2/test_s5_gate.py
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import build_s5, s0_keys, gating
from build_s5 import genuine_cited, V3

FAILS = []
def check(c, m):
    if not c: FAILS.append(m)

# ---- WIRING ----
check(build_s5.normalize_address is s0_keys.normalize_address, "WIRING: build_s5.normalize_address != s0_keys.normalize_address")
check(build_s5.snapshot_v3 is gating.snapshot_v3, "WIRING: build_s5.snapshot_v3 != gating.snapshot_v3")

# ---- genuine cited keyed on DOC TYPE (not NULL-check): exactly the 9, each reconciling to planned ----
cited = genuine_cited()
check(set(cited) == {7, 8, 10, 13, 15, 17, 35, 36, 119}, f"genuine cited must be the 9 typed-doc projects, got {sorted(cited)}")
for pid, info in cited.items():
    check(sum(info['tiers'].values()) == info['planned'], f"proj{pid} cited tier-sum {sum(info['tiers'].values())} != planned {info['planned']}")
check({8, 15, 35} <= {p for p, i in cited.items() if 'MOD' in i['tiers']}, "proj8/15/35 MOD tiers missing (structural fix not demonstrated)")

con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
# ---- the fabrication-laundering guard: NO real INCOME-tier row from a stub/null doc.
#      (market_rate_no_obligation / needs_acquisition are classifications, not asserted income tiers.) ----
bad = con.execute("SELECT COUNT(*) FROM s5_affordability WHERE income_tier IN ('ELI','VLI','LI','MOD','ABOVE_MOD') AND (source_document_id IS NULL OR basis<>'cited')").fetchone()[0]
check(bad == 0, f"{bad} INCOME-tier rows from a stub/null doc — the 704 fakes must carry NO value forward")
# ---- no market-by-subtraction: every ABOVE_MOD is source-stated ----
amsub = con.execute("SELECT COUNT(*) FROM s5_affordability WHERE income_tier='ABOVE_MOD' AND source_document_id IS NULL").fetchone()[0]
check(amsub == 0, f"{amsub} ABOVE_MOD rows with no source doc (market = units - vli fabrication)")
# ---- the 9 fold at high confidence with a source doc ----
hc = con.execute("SELECT COUNT(DISTINCT v2_project_ref) FROM s5_affordability WHERE basis='cited' AND confidence='high' AND source_document_id IS NOT NULL").fetchone()[0]
check(hc == 9, f"genuinely-cited high-confidence projects folded = {hc}, expected 9")
# ---- gaps -> needs_acquisition, FLAGGED with the unknown unit count (not zeroed). A building with 0
#      units in s4_units (no structured count) legitimately has a 0 gap; the bug we guard is a building
#      that HAS units whose gap was zeroed instead of flagged. ----
na0 = con.execute("""SELECT COUNT(*) FROM s5_affordability a JOIN s4_units s ON s.building_id=a.building_id
    WHERE a.income_tier='needs_acquisition' AND a.unit_count<=0 AND s.units>0""").fetchone()[0]
check(na0 == 0, f"{na0} needs_acquisition gaps ZEROED on buildings that have units (must flag the unknown count)")
nbuilt = con.execute("SELECT COUNT(DISTINCT building_id) FROM s5_affordability WHERE population='built'").fetchone()[0]
check(nbuilt == 1385, f"built-spine buildings covered = {nbuilt}, expected 1385")

# ---- obligation reclassification (BMC 23.328 proxy): market_rate_no_obligation is PROXY-DERIVED, 1-2u ONLY ----
mkt_bad = con.execute("SELECT COUNT(*) FROM s5_affordability WHERE income_tier='market_rate_no_obligation' AND (confidence='high' OR basis NOT LIKE 'derived%')").fetchone()[0]
check(mkt_bad == 0, f"{mkt_bad} market_rate_no_obligation rows wrongly high-conf / not basis=derived (it's a PROXY, not a doc-cited fact)")
over = con.execute("""SELECT COUNT(*) FROM s5_affordability a JOIN s4_units s ON s.building_id=a.building_id
    WHERE a.income_tier='market_rate_no_obligation' AND (s.units<1 OR s.units>2)""").fetchone()[0]
check(over == 0, f"{over} market_rate buildings outside the 1-2u rule (under-include guard: only clearly-sub-threshold reclassify)")
held_wrong = con.execute("""SELECT COUNT(*) FROM s5_affordability a JOIN s4_units s ON s.building_id=a.building_id
    WHERE a.population='built' AND (s.units>=5 OR s.units IN (3,4) OR s.units=0) AND a.income_tier<>'needs_acquisition'""").fetchone()[0]
check(held_wrong == 0, f"{held_wrong} obligated(>=5u)/marginal(3-4u)/0u-unknown buildings NOT held as needs_acquisition (the dangerous under-include direction)")
# ---- leak: tier-sum == reconcile_total per population (built->s4_units, pipeline->planned) ----
leak = con.execute("""SELECT COUNT(*) FROM (SELECT population, COALESCE(building_id,v2_project_ref) g,
    SUM(unit_count) s, MAX(reconcile_total) rt FROM s5_affordability GROUP BY population, g HAVING s<>rt)""").fetchone()[0]
check(leak == 0, f"{leak} groups where tier-sum != reconcile_total (silent affordability leak)")
# ---- unit totals unchanged ----
t1 = con.execute("""SELECT CAST(SUM(units) AS INT) FROM s4_units WHERE bucket IN
    ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO',
     '0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND')""").fetchone()[0]
check(t1 == 568, f"Tier-1 units {t1} != 568 (S5 must not touch unit counts)")
con.close()

if __name__ == "__main__":
    if FAILS:
        print(f"S5 GATE: FAIL ({len(FAILS)})")
        for f in FAILS: print("  XXX", f)
        sys.exit(1)
    print(f"S5 GATE: PASS — 0 fabricated/stub tiers present · 0 market-by-subtraction · 9 cited folded high-conf "
          f"(MOD 8/15/35) · {nbuilt} built->needs_acquisition flagged · 0 leak · Tier-1 568 · wiring intact")
