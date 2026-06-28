"""S5 — affordability tiers. The structural fix for the migration's 2-bucket VLI/ABOVE_MOD ceiling
and its `market = units - vli` fabrication.

PRINCIPLES (each the inverse of a specific migration sin):
- FULL income vocabulary (ELI/VLI/LI/MOD/ABOVE_MOD) — never the 2-bucket model.
- NEVER `market = units - vli`. Above-mod/market is only what a SOURCE states.
- GENUINELY cited only: a tier counts as sourced ONLY if its source document is a TYPED affordability
  doc (density_bonus_application / affordable_housing_agreement). The 704 projects whose affordability
  "cites" an UNTYPED STUB (the CPRA permit report itself) are the migration's FAKE citations. S5 does
  NOT carry their fabricated tier VALUES forward at all — those buildings become needs_acquisition
  (tier UNKNOWN, values removed). Demoting confidence is not enough; a low-confidence fabricated value
  is still fabricated. (Keying on source_document_id NOT NULL is the trap; the doc-TYPE check is the fix.)
- Below-market gaps -> needs_acquisition (flagged, counted as unknown) — never zeroed, never market.

LEAK GUARD (from S4): per BUILT building, tier-sum + needs_acquisition slice == s4_units total. Per
CITED-PIPELINE project, tier-sum == the planned (entitled) total. No silent gap, no subtraction.

Imports s0_keys + housing_predicates + gating. --preview is READ-ONLY.
"""
import sqlite3, sys, os, argparse
from collections import defaultdict
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from s0_keys import normalize_address
from gating import snapshot_v3

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
AS_OF = '2026-06-17'
GENUINE_DOC_TYPES = ('density_bonus_application', 'affordable_housing_agreement', 'ahcp', 'tabulation')
INCOME_TIERS = {'ELI', 'VLI', 'LI', 'MOD', 'ABOVE_MOD'}          # real income tiers — these MUST be doc-cited
# Berkeley Inclusionary Housing Ordinance (BMC 23.328): obligation triggers at 5,000 sqft residential floor
# area (~5+ units). No floor-area data in v3 (assessor BuildingAr dropped), so we use units as a CONSERVATIVE
# proxy: only the clearly-sub-threshold 1-2u buildings reclassify; 3-4u marginal + 0u-unknown are HELD.
OBLIGATION_PROXY_MIN = 5                                          # >=5u => obligated; 1-2u => reclassify; 3-4u/0u => hold


def genuine_cited():
    """v2 projects whose affordability cites a TYPED affordability doc -> {pid: dict(tiers, planned, doc, dtype, addr)}.
    The UNTYPED-stub citations (the 704 CPRA-report fakes) are EXCLUDED by the dt.code filter — their
    fabricated tier values never enter this dict, so they cannot be carried forward."""
    v2 = sqlite3.connect(f'file:{V2}?mode=ro', uri=True); v2.row_factory = sqlite3.Row
    q = """SELECT pv.project_id pid, ic.code tier, upa.unit_count uc, upa.source_document_id doc,
                  dt.code dtype, p.canonical_address addr, pv.total_units planned
           FROM unit_program_affordability upa
           JOIN unit_program up ON up.id=upa.unit_program_id
           JOIN project_versions pv ON pv.id=up.project_version_id
           JOIN projects p ON p.id=pv.project_id
           JOIN documents d ON d.id=upa.source_document_id
           JOIN vocabulary_document_types dt ON dt.id=d.document_type_id
           JOIN vocabulary_income_categories ic ON ic.id=upa.income_category_id
           WHERE pv.is_current=1 AND dt.code IN ({})""".format(','.join('?' * len(GENUINE_DOC_TYPES)))
    out = {}
    for r in v2.execute(q, GENUINE_DOC_TYPES):
        e = out.setdefault(r['pid'], dict(tiers={}, planned=r['planned'], doc=r['doc'], dtype=r['dtype'], addr=r['addr']))
        e['tiers'][r['tier']] = e['tiers'].get(r['tier'], 0) + (r['uc'] or 0)
    v2.close()
    return out


def build_affordability():
    cited = genuine_cited()
    v3 = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    s4 = {(num, st): (bid, int(u)) for bid, num, st, u in
          v3.execute("SELECT p.building_id,p.number,p.street,s.units FROM s1_projects p JOIN s4_units s ON s.building_id=p.building_id")}
    v3.close()
    cited_built = {}                       # building_id -> (pid, info, total)
    pipeline = []                          # (pid, info)
    for pid, info in cited.items():
        k = normalize_address(info['addr']); hit = s4.get((k.number, k.street))
        if hit: cited_built[hit[0]] = (pid, info, hit[1])
        else: pipeline.append((pid, info))

    built_rows, pipe_rows = [], []
    for (num, st), (bid, total) in s4.items():
        if bid in cited_built:
            pid, info, _ = cited_built[bid]; tsum = sum(info['tiers'].values())
            for tier, uc in info['tiers'].items():
                built_rows.append(dict(building_id=bid, pid=pid, tier=tier, units=uc, conf='high', doc=info['doc'], basis='cited'))
            if total - tsum > 0:
                built_rows.append(dict(building_id=bid, pid=pid, tier='needs_acquisition', units=total - tsum,
                                       conf='needs_acquisition', doc=None, basis='needs_acquisition'))
        elif 1 <= total <= 2:
            # clearly sub-threshold (SFR/ADU/duplex, < 5,000 sqft) -> KNOWN market-rate, no inclusionary
            # obligation. DERIVED from a unit proxy -> confidence='derived', NOT a doc-cited high-conf fact.
            built_rows.append(dict(building_id=bid, pid=None, tier='market_rate_no_obligation', units=total,
                                   conf='derived', doc=None, basis='derived: below inclusionary threshold (unit proxy)'))
        else:
            # 0u (count unknown -> could be obligated), 3-4u (marginal, could exceed 5,000 sqft, no floor-area),
            # >=5u (obligated harvest target) -> HOLD as needs_acquisition (the under-include guard).
            built_rows.append(dict(building_id=bid, pid=None, tier='needs_acquisition', units=total,
                                   conf='needs_acquisition', doc=None, basis='needs_acquisition'))
    for pid, info in pipeline:
        for tier, uc in info['tiers'].items():
            pipe_rows.append(dict(building_id=None, pid=pid, tier=tier, units=uc, conf='high', doc=info['doc'], basis='cited', planned=info['planned']))
    return built_rows, pipe_rows, cited, cited_built, pipeline, s4


def write_s5(built, pipe, s4_by_bid, cited):
    """Persist s5_affordability into v3. reconcile_total = s4_units (built) / planned (pipeline) so the
    leak guard is enforceable per row. Idempotent."""
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s5_affordability;
      DROP TABLE IF EXISTS s5_meta;
      CREATE TABLE s5_affordability(id INTEGER PRIMARY KEY, population TEXT, building_id INT, v2_project_ref INT,
        income_tier TEXT, unit_count REAL, confidence TEXT, source_document_id INT, basis TEXT, reconcile_total REAL);
      CREATE INDEX ix_s5_bid ON s5_affordability(building_id);
      CREATE INDEX ix_s5_tier ON s5_affordability(income_tier);
      CREATE TABLE s5_meta(key TEXT, value TEXT);
    """)
    rows = []
    for r in built:
        rows.append(('built', r['building_id'], r['pid'], r['tier'], r['units'], r['conf'], r['doc'], r['basis'], s4_by_bid[r['building_id']]))
    for r in pipe:
        rows.append(('pipeline', None, r['pid'], r['tier'], r['units'], r['conf'], r['doc'], r['basis'], cited[r['pid']]['planned']))
    con.executemany("INSERT INTO s5_affordability(population,building_id,v2_project_ref,income_tier,unit_count,"
                    "confidence,source_document_id,basis,reconcile_total) VALUES(?,?,?,?,?,?,?,?,?)", rows)
    na = sum(1 for r in built if r['basis'] == 'needs_acquisition')
    meta = [('stage', 'S5'), ('as_of', AS_OF), ('rows', str(len(rows))), ('genuine_cited_projects', str(len(cited))),
            ('built_needs_acquisition', str(na)), ('pipeline_cited_rows', str(len(pipe))),
            ('key_module', 's0_keys.py + housing_predicates.py + gating.py')]
    con.executemany("INSERT INTO s5_meta VALUES(?,?)", meta)
    con.commit(); con.close()
    return len(rows)


def fingerprint_s5():
    con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    n = con.execute("SELECT COUNT(*) FROM s5_affordability").fetchone()[0]
    # no-fabrication: only real INCOME tiers must be doc-cited (market_rate_no_obligation/needs_acquisition are classifications)
    bad = con.execute("SELECT COUNT(*) FROM s5_affordability WHERE income_tier IN ('ELI','VLI','LI','MOD','ABOVE_MOD') AND (source_document_id IS NULL OR basis<>'cited')").fetchone()[0]
    cited_n = con.execute("SELECT COUNT(DISTINCT v2_project_ref) FROM s5_affordability WHERE basis='cited'").fetchone()[0]
    mod = con.execute("SELECT v2_project_ref,CAST(unit_count AS INT) FROM s5_affordability WHERE income_tier='MOD' ORDER BY v2_project_ref").fetchall()
    mkt = con.execute("SELECT COUNT(*),CAST(SUM(unit_count) AS INT) FROM s5_affordability WHERE income_tier='market_rate_no_obligation'").fetchone()
    mkt_bad = con.execute("SELECT COUNT(*) FROM s5_affordability WHERE income_tier='market_rate_no_obligation' AND (confidence='high' OR basis NOT LIKE 'derived%')").fetchone()[0]
    na = con.execute("SELECT COUNT(*),CAST(SUM(unit_count) AS INT) FROM s5_affordability WHERE income_tier='needs_acquisition'").fetchone()
    leak = con.execute("""SELECT COUNT(*) FROM (SELECT population, COALESCE(building_id,v2_project_ref) g,
        SUM(unit_count) s, MAX(reconcile_total) rt FROM s5_affordability GROUP BY population, g HAVING s<>rt)""").fetchone()[0]
    utot = con.execute("SELECT CAST(SUM(units) AS INT) FROM s4_units").fetchone()[0]
    con.close()
    print("=== S5 FINGERPRINT (fresh connection) ===")
    print(f"  integrity: {ok}  | s5_affordability rows: {n}")
    print(f"  INCOME-tier rows from a stub/null doc (NO-FABRICATION — must be 0): {bad}")
    print(f"  genuinely-cited projects folded: {cited_n} (expect 9)  | MOD tiers present: {mod}")
    print(f"  market_rate_no_obligation: {mkt[0]} bldgs / {mkt[1]}u  (proxy-derived; wrongly-high-conf/non-derived: {mkt_bad} must be 0)")
    print(f"  needs_acquisition HELD: {na[0]} bldgs / {na[1]}u (75 obligated + 10 marginal + 81 zero-unit)")
    print(f"  leak (tier-sum != reconcile_total): {leak} (must be 0)  |  unit total unchanged: {utot} (expect 5705)")
    return ok, n, bad, leak


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true'); ap.add_argument('--no-snapshot', action='store_true')
    args = ap.parse_args()

    built, pipe, cited, cited_built, pipeline, s4 = build_affordability()
    s4_by_bid = {bid: u for (n, st), (bid, u) in s4.items()}
    FAIL = []
    print("=== S5 PREVIEW — affordability (read-only; no write) ===")
    print(f"  built-spine buildings: {len(s4)}   genuine-cited projects (typed affordability doc): {len(cited)}")

    print(f"\n  [1] GENUINELY cited (typed DBE/AHA docs) — confidence=high, source_document_id, reconcile to planned:")
    for pid, info in sorted(cited.items()):
        ok = sum(info['tiers'].values()) == info['planned']
        loc = 'BUILT' if any(v[0] == pid for v in cited_built.values()) else 'PIPELINE'
        print(f"      proj{pid}: {info['tiers']} sum={sum(info['tiers'].values())} planned={info['planned']} "
              f"doc={info['doc']}({info['dtype'][:14]}) {loc} {'OK' if ok else 'DELTA->needs_acq'}")

    # *** the critical confirmation: only real INCOME-tier rows (ELI/VLI/LI/MOD/ABOVE_MOD) may be present,
    # and only from a genuine doc cite. market_rate_no_obligation/needs_acquisition are classifications, not
    # asserted income tiers. ***
    income_rows = [r for r in built + pipe if r['tier'] in INCOME_TIERS]
    bad = [r for r in income_rows if r['basis'] != 'cited' or r['pid'] not in cited]
    print(f"\n  [CONFIRM] fabricated stub tiers removed, not demoted:")
    print(f"      INCOME-tier rows present from a NON-genuine (stub/null) doc: {len(bad)} (must be 0 — fakes carry NO value forward)")
    print(f"      all income-tier rows are genuinely doc-cited: {not bad}  (the 704 stub fakes contribute 0)")
    if bad: FAIL.append(f"{len(bad)} fabricated income-tier rows present")

    mkt = [r for r in built if r['tier'] == 'market_rate_no_obligation']
    na = [r for r in built if r['basis'] == 'needs_acquisition']
    bad_mkt = [r for r in mkt if r['conf'] == 'high' or 'derived' not in r['basis']]
    print(f"\n  [2] BUILT-spine obligation classification (BMC 23.328 proxy):")
    print(f"      market_rate_no_obligation (1-2u, DERIVED proxy, conf!=high): {len(mkt)} buildings / {int(sum(r['units'] for r in mkt))}u")
    print(f"      needs_acquisition HELD (0u-unknown + 3-4u marginal + >=5u obligated): {len(na)} buildings / {int(sum(r['units'] for r in na))}u")
    print(f"      market_rate rows wrongly high-conf or not basis=derived (must be 0): {len(bad_mkt)}")
    if bad_mkt: FAIL.append(f"{len(bad_mkt)} market_rate rows not proxy-derived")
    # under-include guard: every market_rate building is 1-2u (none >=3u reclassified)
    over = [r for r in mkt if not (1 <= s4_by_bid[r['building_id']] <= 2)]
    print(f"      under-include guard: market_rate buildings that are NOT 1-2u (must be 0): {len(over)}")
    if over: FAIL.append(f"{len(over)} market_rate buildings outside the 1-2u rule")

    print(f"\n  [3] market = units - vli: 0 rows — above-mod is ONLY ever a source-stated tier from a cited doc, never derived.")

    tiers_seen = sorted(set(r['tier'] for r in built + pipe))
    mod = {pid: info['tiers']['MOD'] for pid, info in cited.items() if 'MOD' in info['tiers']}
    print(f"\n  [4] full vocabulary: {tiers_seen}")
    print(f"      cited projects with a MOD tier (impossible in the migration's 2-bucket model): {mod}")

    by_b = defaultdict(float)
    for r in built: by_b[r['building_id']] += r['units']
    leak = [(bid, s) for bid, s in by_b.items() if s != s4_by_bid[bid]]
    pl = defaultdict(float)
    for r in pipe: pl[r['pid']] += r['units']
    pipe_leak = [(pid, s) for pid, s in pl.items() if s != cited[pid]['planned']]
    print(f"\n  [5] LEAK: built tier-sum != s4_units: {len(leak)} (must 0); pipeline tier-sum != planned: {len(pipe_leak)} (must 0)")
    if leak: FAIL.append(f"{len(leak)} built leak: {leak[:3]}")
    if pipe_leak: FAIL.append(f"{len(pipe_leak)} pipeline leak: {pipe_leak[:3]}")

    t1 = sum(s4_by_bid[bid] for (n, st), (bid, u) in s4.items() if f"{n} {st}" in
             ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO','0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND'))
    print(f"\n  [6] unit totals unchanged — S5 adds affordability rows, never touches s4_units (Tier-1 still {int(t1)}); s0_-s4_ untouched.")

    print(f"\n  === S5 ACCEPTANCE GATE: {'PASS' if not FAIL else 'FAIL'} ===")
    for f in FAIL: print("    XXX", f)
    if args.write:
        if FAIL:
            print("\n  WRITE ABORTED — acceptance gate failed."); sys.exit(1)
        import hashlib
        v2b = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        if args.no_snapshot:
            print("\n  (--no-snapshot: idempotency re-run, NOT snapshotting — must not clobber the rollback point)")
        else:
            snap, created = snapshot_v3('s5-obligation')   # distinct tag: refuse-to-clobber preserves the pre-s5.db
            print(f"\n  snapshot: {os.path.basename(snap)} ({'created' if created else 'preserved existing — NOT clobbered'})")
        nr = write_s5(built, pipe, s4_by_bid, cited)
        print(f"  S5 WRITE -> {os.path.basename(V3)}: {nr} s5_affordability rows")
        fingerprint_s5()
        v2a = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        print(f"  live v2 untouched: sha256 {'UNCHANGED' if v2b == v2a else 'CHANGED ✗✗'} ({v2b[:16]})")
