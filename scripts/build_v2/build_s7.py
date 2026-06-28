"""S7 — cycle-scope. Tags each dated milestone event with WHICH RHNA cycle / APR reporting window it
falls in. The corrected design handles THREE INDEPENDENT date concepts that the naive cycle_for_date
conflates, and RE-WIRES the orphaned housing_rules module (the anti-drift discipline — the rebuild must
not re-orphan its own single-sourced policy classifiers).

THREE DATE CONCEPTS, per event (a BP event and a CO event are tagged separately — projection status is
PER-EVENT, used by different APR tables, the D5/D6 bp_in_projection_period + co_in_projection_period
precedent):
  reporting_year       = calendar year of the event date (APR Table A / A2 by-year).
  calendar_cycle       = 5th/6th by the 2023-01-31 boundary  -> housing_rules.cycle_for_date.
  in_projection_period = the narrow 2022-06-30..2023-01-30 bridge window (bool) -> housing_rules.is_projection_period.
  rhna_credit_cycle    = which 8-year allocation the unit's RHNA credit counts toward. BUILDING-LEVEL,
                         from the FIRST building permit (credit is earned at BP issuance, NOT CO):
                         6th iff first-BP >= 2022-06-30 (no upper cap) -> housing_rules.rhna_credit_cycle.
                         NULL for the CO-only-no-BP buildings (credit not derivable; flagged).

NON-CONFLATION (CLAUDE.md:179): in_projection_period (narrow window) is NOT the credit filter, and the
credit boundary 2022-06-30 (PROJECTION_PERIODS) is NOT cycle_for_date's 2023-01-31 (RHNA_CYCLES). All three
stay distinct columns. is_first_bp marks the single credit-bearing BP row so a Table-B sum never double-counts.

Imports s0_keys + housing_predicates + gating + housing_rules (all three cycle functions WIRED, guarded).
--preview is READ-ONLY.
"""
import sqlite3, sys, os, argparse
from collections import defaultdict, Counter
from datetime import date
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from s0_keys import normalize_address
import housing_predicates  # noqa: F401 (shared-module wiring; net_units single-source)
from gating import snapshot_v3
import housing_rules as hr  # the orphaned module being RE-WIRED — call via hr.* so the wiring guard sees it

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
AS_OF = '2026-06-17'

# city-reported 6th-cycle RHNA figures (BP-credit basis), for the S9 validation cross-check (NOT a target
# to tune toward — the memo isn't on disk to quote; these are John's figures from the CM memo / city APR).
CITY_RHNA_6TH = {2024: 492, 2025: 503}


def _yr(d): return int(d[:4])


def derive_cycle():
    """One row per s2_events BP/CO event (is_inferred=0). Returns tuples:
       (building_id, event_type, event_date, reporting_year, calendar_cycle,
        in_projection_period, rhna_credit_cycle, is_first_bp, units, basis)."""
    c = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    units = {bid: int(u) for bid, u in c.execute("SELECT building_id,units FROM s4_units")}
    events = list(c.execute(
        "SELECT building_id,event_type,event_date,source_permit FROM s2_events "
        "WHERE event_type IN ('building_permit_issued','co_issued') AND is_inferred=0 "
        "ORDER BY building_id,event_date"))
    c.close()

    # FIRST-BP per building = MIN(building_permit_issued) — the RHNA-credit-bearing milestone.
    # (In v3 each building has <=1 BP event, but MIN keeps the rule correct if that changes.)
    first_bp = {}
    for bid, et, ed, _ in events:
        if et == 'building_permit_issued' and ed:
            if bid not in first_bp or ed < first_bp[bid]:
                first_bp[bid] = ed
    # building-level RHNA credit cycle (WIRED: hr.rhna_credit_cycle). NULL when no BP.
    credit = {bid: hr.rhna_credit_cycle(date.fromisoformat(ed)) for bid, ed in first_bp.items()}

    rows = []
    for bid, et, ed, sp in events:
        d = date.fromisoformat(ed) if ed else None
        # calendar_cycle — guard the (currently impossible) out-of-range date rather than crash.
        try:
            cal = hr.cycle_for_date(d)            # WIRED
        except ValueError:
            cal = None
        inproj = 1 if hr.is_projection_period(d) else 0   # WIRED
        cc = credit.get(bid)                              # building-level; None for CO-only-no-BP
        is_first_bp = 1 if (et == 'building_permit_issued' and first_bp.get(bid) == ed) else 0
        basis = (f"s2_events {et} is_inferred=0 (permit {sp or '?'}); calendar_cycle via "
                 f"housing_rules.cycle_for_date; in_projection_period via is_projection_period; "
                 f"rhna_credit_cycle via rhna_credit_cycle(first-BP>=2022-06-30)"
                 + ("" if cc is not None else "; CO-only building, no BP -> rhna_credit_cycle NULL (flagged)"))
        rows.append((bid, et, ed, _yr(ed), cal, inproj, cc, is_first_bp, units.get(bid, 0), basis))
    return rows


def write_s7(rows):
    """Persist s7_cycle into v3 (s0_-s6_ untouched). Idempotent."""
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s7_cycle;
      DROP TABLE IF EXISTS s7_meta;
      CREATE TABLE s7_cycle(
        id INTEGER PRIMARY KEY, building_id INT, event_type TEXT, event_date TEXT,
        reporting_year INT, calendar_cycle TEXT, in_projection_period INT,
        rhna_credit_cycle TEXT, is_first_bp INT, units INT, basis TEXT);
      CREATE INDEX ix_s7_bid ON s7_cycle(building_id);
      CREATE INDEX ix_s7_year ON s7_cycle(event_type, reporting_year);
      CREATE INDEX ix_s7_credit ON s7_cycle(rhna_credit_cycle, is_first_bp);
      CREATE TABLE s7_meta(key TEXT, value TEXT);
    """)
    con.executemany("INSERT INTO s7_cycle(building_id,event_type,event_date,reporting_year,calendar_cycle,"
                    "in_projection_period,rhna_credit_cycle,is_first_bp,units,basis) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
    meta = [('stage', 'S7'), ('as_of', AS_OF), ('events', str(len(rows))),
            ('rule', 'three date concepts per event: reporting_year / calendar_cycle (2023-01-31) / '
                     'in_projection_period (2022-06-30..2023-01-30) / rhna_credit_cycle (first-BP>=2022-06-30)'),
            ('wired', 'housing_rules.cycle_for_date + is_projection_period + rhna_credit_cycle'),
            ('key_module', 's0_keys.py + housing_predicates.py + gating.py + housing_rules')]
    con.executemany("INSERT INTO s7_meta VALUES(?,?)", meta)
    con.commit(); con.close()
    return len(rows)


def _credit_cumulative():
    """Cumulative 6th-cycle RHNA credit (BP-based, is_first_bp rows) by year — for the S9 cross-check."""
    con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    by = con.execute("SELECT reporting_year,COUNT(*),CAST(SUM(units) AS INT) FROM s7_cycle "
                     "WHERE is_first_bp=1 AND rhna_credit_cycle='6th' GROUP BY reporting_year ORDER BY 1").fetchall()
    con.close()
    cum_b = cum_u = 0; out = []
    for yr, nb, nu in by:
        cum_b += nb; cum_u += (nu or 0); out.append((yr, nb, nu or 0, cum_b, cum_u))
    return out


def fingerprint_s7():
    con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    n = con.execute("SELECT COUNT(*) FROM s7_cycle").fetchone()[0]
    by_type = dict(con.execute("SELECT event_type,COUNT(*) FROM s7_cycle GROUP BY event_type"))
    no_year = con.execute("SELECT COUNT(*) FROM s7_cycle WHERE reporting_year IS NULL").fetchone()[0]
    no_cal = con.execute("SELECT COUNT(*) FROM s7_cycle WHERE calendar_cycle IS NULL").fetchone()[0]
    first_bp = con.execute("SELECT COUNT(*) FROM s7_cycle WHERE is_first_bp=1").fetchone()[0]
    co_only_null = con.execute("SELECT COUNT(DISTINCT building_id) FROM s7_cycle WHERE building_id IN "
        "(SELECT building_id FROM s7_cycle GROUP BY building_id HAVING SUM(is_first_bp)=0) "
        "AND rhna_credit_cycle IS NULL").fetchone()[0]
    cred = dict(con.execute("SELECT rhna_credit_cycle,COUNT(*) FROM s7_cycle WHERE is_first_bp=1 GROUP BY 1"))
    t1 = con.execute("""SELECT CAST(SUM(units) AS INT) FROM s4_units WHERE bucket IN
        ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO',
         '0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND')""").fetchone()[0]
    con.close()
    print("=== S7 FINGERPRINT (fresh connection) ===")
    print(f"  integrity: {ok}  | s7_cycle events: {n}  ({by_type})")
    print(f"  events with NO reporting_year (must be 0 — every event is dated): {no_year}")
    print(f"  events with NO calendar_cycle (out-of-cycle-range; expect 0): {no_cal}")
    print(f"  is_first_bp credit-bearing rows: {first_bp}  | credit-cycle of those: {cred}")
    print(f"  CO-only-no-BP buildings with rhna_credit_cycle NULL (flagged, expected 6; the 94 no-event "
          f"pipeline buildings are not tagged — no event to tag): {co_only_null}")
    print(f"  S9 cross-check — cumulative 6th-cycle BP credit by year (city: {CITY_RHNA_6TH}):")
    for yr, nb, nu, cb, cu in _credit_cumulative():
        tag = f"  <-- city {CITY_RHNA_6TH[yr]}" if yr in CITY_RHNA_6TH else ""
        print(f"      {yr}: +{nb}bldg/+{nu}u  cumulative {cb}bldg/{cu}u{tag}")
    print(f"  facts unchanged: Tier-1 units {t1} (expect 568)")
    return ok, n, no_year


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true'); ap.add_argument('--no-snapshot', action='store_true')
    args = ap.parse_args()

    rows = derive_cycle()
    FAIL = []
    print("=== S7 PREVIEW — cycle-scope (read-only; no write) ===")
    print(f"  events tagged: {len(rows)}  (one row per s2_events BP/CO milestone; both event types)")

    bt = Counter(r[1] for r in rows)
    print(f"\n  [1] event coverage: {dict(bt)}  (BP + CO, the per-event projection-status design)")

    # [2] every event has a reporting_year from a real date (no asserted year)
    no_year = [r for r in rows if r[3] is None]
    no_cal = [r for r in rows if r[4] is None]
    print(f"\n  [2] every event a reporting_year from its is_inferred=0 date (no asserted year): "
          f"missing={len(no_year)}; calendar_cycle out-of-range={len(no_cal)}")
    if no_year: FAIL.append(f"{len(no_year)} events without a reporting_year")

    # [3] THREE DATE CONCEPTS kept distinct — show the canonical 2022-06-30..2023-01-30 disagreement
    print(f"\n  [3] three date concepts (kept distinct — the non-conflation):")
    cal = Counter(r[4] for r in rows)
    proj = sum(r[5] for r in rows)
    print(f"      calendar_cycle (2023-01-31 boundary): {dict(cal)}")
    print(f"      in_projection_period=1 (narrow 2022-06-30..2023-01-30 window): {proj} events")
    # the discriminating set: calendar=5th but credited 6th (a 2022-06-30..2023-01-30 BP)
    split = [r for r in rows if r[1] == 'building_permit_issued' and r[4] == '5th' and r[6] == '6th']
    print(f"      BP events calendar_cycle=5th BUT rhna_credit_cycle=6th (projection-credited): {len(split)} "
          f"(e.g. {[(r[0], r[2]) for r in split[:3]]})")

    # [4] rhna_credit_cycle building-level (first-BP), NULL for CO-only-no-BP, is_first_bp marks credit row
    bybuild = defaultdict(list)
    for r in rows: bybuild[r[0]].append(r)
    co_only = [b for b, rs in bybuild.items() if not any(x[1] == 'building_permit_issued' for x in rs)]
    co_only_null = [b for b in co_only if all(x[6] is None for x in bybuild[b])]
    first_bp_rows = [r for r in rows if r[7] == 1]
    bp_builds = {b for b, rs in bybuild.items() if any(x[1] == 'building_permit_issued' for x in rs)}
    cred = Counter(r[6] for r in first_bp_rows)
    print(f"\n  [4] rhna_credit_cycle (BUILDING-level, from first-BP>=2022-06-30):")
    print(f"      is_first_bp credit-bearing rows: {len(first_bp_rows)} (== buildings with a BP: {len(bp_builds)}); "
          f"credit-cycle split {dict(cred)}")
    print(f"      CO-only-no-BP buildings: {len(co_only)} -> rhna_credit_cycle NULL (credit not derivable, flagged): {len(co_only_null)}")
    if len(first_bp_rows) != len(bp_builds): FAIL.append("is_first_bp not exactly one per BP-building (double-count risk)")
    if len(co_only_null) != len(co_only): FAIL.append("a CO-only building got a non-NULL credit cycle")

    # [5] S9 cross-check vs the city's BP-credit figure — SURFACE the difference, do NOT force a match
    print(f"\n  [5] S9 cross-check — cumulative 6th-cycle BP credit (is_first_bp, credit=6th) vs city {CITY_RHNA_6TH}:")
    cumb = cumu = 0
    by = Counter(); byu = Counter()
    for r in first_bp_rows:
        if r[6] == '6th': by[r[3]] += 1; byu[r[3]] += r[8]
    for yr in sorted(by):
        cumb += by[yr]; cumu += byu[yr]
        tag = f"   city {CITY_RHNA_6TH[yr]}" if yr in CITY_RHNA_6TH else ""
        print(f"      {yr}: +{by[yr]}bldg/+{byu[yr]}u  cumulative {cumb}bldg/{cumu}u{tag}")
    print(f"      NOTE: BP is the correct milestone (was CO). Magnitude does NOT reconcile to 492/503 -> a")
    print(f"      SCOPE/population question (annual-vs-cumulative / affordable-only / coverage universe) -> S8/S9.")
    print(f"      Per discipline: the validation SURFACES the difference; it does not tune our number to the city's.")

    print(f"\n  [6] facts unchanged — S7 adds a cycle-scope layer, never changes a value; s0_-s6_ untouched (read-only).")
    print(f"\n  === S7 ACCEPTANCE GATE: {'PASS' if not FAIL else 'FAIL'} ===")
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
            snap, created = snapshot_v3('s7')
            print(f"\n  snapshot: {os.path.basename(snap)} ({'created' if created else 'preserved existing — NOT clobbered'})")
        nr = write_s7(rows)
        print(f"  S7 WRITE -> {os.path.basename(V3)}: {nr} s7_cycle events")
        fingerprint_s7()
        v2a = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        print(f"  live v2 untouched: sha256 {'UNCHANGED' if v2b == v2a else 'CHANGED ✗✗'} ({v2b[:16]})")
