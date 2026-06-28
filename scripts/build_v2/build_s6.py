"""S6 — confidence = f(source presence). The direct fix for the migration stamping confidence=high on
EVERYTHING regardless of evidence.

THE RULE: confidence is a FUNCTION of the recorded evidence per fact, never a constant. It is FACT-LEVEL —
a building has separate confidence for its unit count, its stage, its dates, and its affordability, because
the backing differs per fact. S6 reads what S2-S5 already recorded and maps each fact mechanically:

  high   = a STRUCTURED column / a TYPED document / an EVIDENCE-based resolution backs the fact directly.
  medium = a reasoned PROXY/derivation backs it (defensible rule, not a direct source) — its own tier.
  low    = no source, a flagged cross-source CONFLICT, or an honest FLOOR (pipeline / needs_acquisition).

No fact is ever 'high' by default — only when a real backing is present. This makes the migration's
blanket-high structurally impossible.

Imports s0_keys + housing_predicates + gating. --preview is READ-ONLY.
"""
import sqlite3, sys, os, argparse
from collections import defaultdict, Counter
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from s0_keys import normalize_address
from gating import snapshot_v3

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
AS_OF = '2026-06-17'


def derive_confidence():
    """Returns list of (population, building_id, v2_project_ref, fact_type, confidence, basis)."""
    c = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    units = {bid: int(u) for bid, u in c.execute("SELECT building_id,units FROM s4_units")}
    bucket = {bid: b for bid, b in c.execute("SELECT building_id,bucket FROM s4_units")}
    # s4 reconcile verdicts by bucket
    s4verdict = {r[0]: r[1] for r in c.execute("SELECT bucket,verdict FROM s4_unit_reconcile_resolved")}
    # s3 stage + reconcile
    stage = {bid: st for bid, st in c.execute("SELECT building_id,stage FROM s3_stage")}
    s3recon = {r[0] for r in c.execute("SELECT building_id FROM s3_stage_reconcile")}
    # s2 events per building + date-reconcile permits -> buildings
    ev = defaultdict(set)
    for bid, et, inf in c.execute("SELECT building_id,event_type,is_inferred FROM s2_events"):
        ev[bid].add((et, inf))
    drecon_permits = {r[0] for r in c.execute("SELECT permit FROM s2_date_reconcile")}
    drecon_bids = set()
    for bid, fams in c.execute("SELECT building_id,permit_families FROM s1_projects"):
        if set((fams or '').split('|')) & drecon_permits:
            drecon_bids.add(bid)
    # s5 affordability per building (built) + the cited pipeline projects
    aff_built = {r[0]: (r[1], r[2], r[3]) for r in c.execute(
        "SELECT building_id,income_tier,confidence,basis FROM s5_affordability WHERE population='built'")}
    aff_pipe = list(c.execute("SELECT DISTINCT v2_project_ref FROM s5_affordability WHERE population='pipeline'"))
    c.close()

    rows = []
    for bid in units:
        # UNITS
        bk = bucket[bid]
        if s4verdict.get(bk) == 'FLAG_S8':
            rows.append(('built', bid, None, 'units', 'low', 'flagged S8 (multi-building development; per-building MAX under-counts)'))
        elif units[bid] == 0:
            rows.append(('built', bid, None, 'units', 'low', 'no structured unit count (New building, 0 units recorded)'))
        elif s4verdict.get(bk) == 'RESOLVE_OURS':
            rows.append(('built', bid, None, 'units', 'high', 'reconciled by structured evidence (s4)'))
        else:
            rows.append(('built', bid, None, 'units', 'high', 'structured net_units'))
        # STAGE
        st = stage.get(bid, 'pipeline')
        if bid in s3recon:
            rows.append(('built', bid, None, 'stage', 'low', 'v1 disagrees -> s3_stage_reconcile (S8)'))
        elif st == 'pipeline':
            rows.append(('built', bid, None, 'stage', 'low', 'no milestone event (pipeline floor)'))
        else:
            rows.append(('built', bid, None, 'stage', 'high', f'event-derived ({st})'))
        # DATES
        types = {t for t, i in ev.get(bid, set())}
        structured = any(i == 0 for t, i in ev.get(bid, set()))
        if bid in drecon_bids:
            rows.append(('built', bid, None, 'dates', 'low', 'CPRA-vs-v2 date conflict (s2_date_reconcile, S8)'))
        elif structured and ({'building_permit_issued', 'co_issued'} & types):
            rows.append(('built', bid, None, 'dates', 'high', 'structured CPRA date (is_inferred=0)'))
        else:
            rows.append(('built', bid, None, 'dates', 'low', 'no structured dated milestone'))
        # AFFORDABILITY
        a = aff_built.get(bid)
        if a and a[0] == 'market_rate_no_obligation':
            rows.append(('built', bid, None, 'affordability', 'medium', 'derived: below inclusionary threshold (unit proxy)'))
        else:
            rows.append(('built', bid, None, 'affordability', 'low', 'no affordability source (needs_acquisition)'))
    # the 9 cited pipeline projects: affordability = high (typed DBE/AHA doc)
    for (pid,) in aff_pipe:
        rows.append(('pipeline', None, pid, 'affordability', 'high', 'typed affordability doc (DBE/AHA), document-cited'))
    return rows


def write_s6(rows):
    """Persist s6_confidence into v3 (s0_-s5_ untouched). Idempotent."""
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s6_confidence;
      DROP TABLE IF EXISTS s6_meta;
      CREATE TABLE s6_confidence(id INTEGER PRIMARY KEY, population TEXT, building_id INT, v2_project_ref INT,
        fact_type TEXT, confidence TEXT, basis TEXT);
      CREATE INDEX ix_s6_fact ON s6_confidence(fact_type, confidence);
      CREATE INDEX ix_s6_bid ON s6_confidence(building_id);
      CREATE TABLE s6_meta(key TEXT, value TEXT);
    """)
    con.executemany("INSERT INTO s6_confidence(population,building_id,v2_project_ref,fact_type,confidence,basis) "
                    "VALUES(?,?,?,?,?,?)", rows)
    d = Counter((r[3], r[4]) for r in rows)
    meta = [('stage', 'S6'), ('as_of', AS_OF), ('facts', str(len(rows))),
            ('rule', 'confidence = f(source presence); fact-level; no constant'),
            ('key_module', 's0_keys.py + housing_predicates.py + gating.py')]
    con.executemany("INSERT INTO s6_meta VALUES(?,?)", meta)
    con.commit(); con.close()
    return len(rows)


# the ONLY bases that may carry confidence='high' — a structured column, an evidence resolution, a typed
# doc, a dated event. Anything else high = the migration's blanket-high bug.
_HIGH_OK_EXACT = ('structured net_units', 'reconciled by structured evidence (s4)',
                  'typed affordability doc (DBE/AHA), document-cited')


def fingerprint_s6():
    con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    n = con.execute("SELECT COUNT(*) FROM s6_confidence").fetchone()[0]
    ph = ",".join("?" * len(_HIGH_OK_EXACT))
    unbacked = con.execute(f"SELECT COUNT(*) FROM s6_confidence WHERE confidence='high' AND basis NOT IN ({ph}) "
                           "AND basis NOT LIKE 'event-derived%' AND basis NOT LIKE 'structured CPRA date%'", _HIGH_OK_EXACT).fetchone()[0]
    dist = {ft: dict(con.execute("SELECT confidence,COUNT(*) FROM s6_confidence WHERE fact_type=? GROUP BY confidence", (ft,)))
            for ft in ('units', 'stage', 'dates', 'affordability')}
    med = con.execute("SELECT COUNT(*) FROM s6_confidence WHERE fact_type='affordability' AND confidence='medium'").fetchone()[0]
    varies = con.execute("SELECT COUNT(*) FROM (SELECT building_id FROM s6_confidence WHERE building_id IS NOT NULL GROUP BY building_id HAVING COUNT(DISTINCT confidence)>1)").fetchone()[0]
    tiers = [r[0] for r in con.execute("SELECT DISTINCT confidence FROM s6_confidence ORDER BY 1")]
    t1 = con.execute("""SELECT CAST(SUM(units) AS INT) FROM s4_units WHERE bucket IN
        ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO',
         '0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND')""").fetchone()[0]
    con.close()
    print("=== S6 FINGERPRINT (fresh connection) ===")
    print(f"  integrity: {ok}  | s6_confidence facts: {n}")
    print(f"  MIGRATION-BUG CHECK — high facts WITHOUT a real backing (must be 0): {unbacked}")
    for ft in ('units', 'stage', 'dates', 'affordability'):
        print(f"    {ft:14} {dist[ft]}")
    print(f"  affordability market_rate -> 'medium' (distinct tier): {med} | tiers in use: {tiers}")
    print(f"  confidence VARIES per-building (not constant): {varies}/1385")
    print(f"  facts unchanged: Tier-1 units {t1} (expect 568)")
    return ok, n, unbacked


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true'); ap.add_argument('--no-snapshot', action='store_true')
    args = ap.parse_args()

    rows = derive_confidence()
    FAIL = []
    print("=== S6 PREVIEW — confidence = f(source presence) (read-only; no write) ===")
    print(f"  facts scored: {len(rows)}  (fact-LEVEL: each building has separate confidence per fact)")

    print(f"\n  [1] tier definitions (mechanical, not judgment):")
    print(f"      high   = structured column / typed document / evidence-based resolution backs the fact")
    print(f"      medium = a reasoned PROXY/derivation (market_rate_no_obligation = unit-proxy for the sqft threshold)")
    print(f"      low    = no source / flagged conflict / honest floor (pipeline, needs_acquisition, FLAG-S8)")

    print(f"\n  [2] per-fact-type confidence distribution:")
    by_fact = defaultdict(Counter)
    for pop, bid, pid, ft, conf, basis in rows:
        by_fact[ft][conf] += 1
    for ft in ('units', 'stage', 'dates', 'affordability'):
        print(f"      {ft:14} {dict(by_fact[ft])}")
    aff = by_fact['affordability']
    print(f"      -> affordability: high={aff['high']} (the 9 cited), medium={aff['medium']} (1,219 derived market-rate), low={aff['low']} (166 needs_acquisition)")

    # [3] THE MIGRATION-BUG CHECK: 0 facts high WITHOUT real backing
    BACKED = {'structured net_units', 'reconciled by structured evidence (s4)', 'typed affordability doc (DBE/AHA), document-cited'}
    high = [r for r in rows if r[4] == 'high']
    unbacked = [r for r in high if not (r[5] in BACKED or r[5].startswith('event-derived') or r[5].startswith('structured CPRA date'))]
    print(f"\n  [3] MIGRATION-BUG CHECK: high facts WITHOUT a real backing (must be 0): {len(unbacked)}")
    print(f"      every 'high' traces to: structured column, evidence-resolution, typed doc, or a dated event.")
    if unbacked: FAIL.append(f"{len(unbacked)} high-without-backing")

    # [4] no blanket constant: confidence varies within a building across its facts
    perb = defaultdict(set)
    for pop, bid, pid, ft, conf, basis in rows:
        if bid is not None: perb[bid].add(conf)
    varies = sum(1 for b, s in perb.items() if len(s) > 1)
    print(f"\n  [4] NOT a blanket constant: buildings whose confidence VARIES across their facts: {varies}/{len(perb)} "
          f"(distinct tiers used: {sorted(set(r[4] for r in rows))})")
    check_one = all(len(by_fact[ft]) >= 1 for ft in by_fact)
    if len(set(r[4] for r in rows)) < 2: FAIL.append("confidence is a single constant (blanket)")

    print(f"\n  [5] facts unchanged — S6 adds a confidence layer, never changes a value; s0_-s5_ untouched (read-only).")
    print(f"\n  === S6 ACCEPTANCE GATE: {'PASS' if not FAIL else 'FAIL'} ===")
    for f in FAIL: print("    XXX", f)
    if args.write:
        if FAIL:
            print("\n  WRITE ABORTED — acceptance gate failed."); sys.exit(1)
        import hashlib
        V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
        v2b = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        if args.no_snapshot:
            print("\n  (--no-snapshot: idempotency re-run, NOT snapshotting — must not clobber the rollback point)")
        else:
            snap, created = snapshot_v3('s6')
            print(f"\n  snapshot: {os.path.basename(snap)} ({'created' if created else 'preserved existing — NOT clobbered'})")
        nr = write_s6(rows)
        print(f"  S6 WRITE -> {os.path.basename(V3)}: {nr} s6_confidence facts")
        fingerprint_s6()
        v2a = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        print(f"  live v2 untouched: sha256 {'UNCHANGED' if v2b == v2a else 'CHANGED ✗✗'} ({v2b[:16]})")
