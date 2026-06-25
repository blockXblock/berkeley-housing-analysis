"""S9 — the A2 SCORECARD: v3's cycle-scoped completions vs the city's SUBMITTED APR (the reconcile-target).

The 10th gated stage on the finished S0-S8 DAG. Compares LIKE-FOR-LIKE only: CO completions by
s7_cycle.reporting_year against table_a2's CO income columns by YEAR, in the FRESH deduped oracle
mirror (hcd_apr_mirror_2026-06-17_fresh.db — NOT the stale mirror with the CY2025 double-submission).
The mirror is ORACLE / reconcile-target ONLY, opened READ-ONLY; using it as a data source would be
circular (the cardinal sin). NEVER compares v2's 16,808 Sigma-units to v3's 5,705 (different populations).

THREE DISTINCT OUTPUTS (not one scorecard):
  1. s9_scorecard            — CO completions by reporting_year: v3 vs city + delta + net (the payoff).
  2. s9_city_building_breakout — the ANSWER KEY for S1.5: for the 19 collapse developments the city
     reports PER-BUILDING, the city's per-building CO rows (addr/APN/year/units). AGREEMENT-WITH-ORACLE
     (corroboration — the granularity originates in the city's own staff files; NOT independent proof).
  3. s9_coverage_gap         — the 14 collapse developments the city's APR OMITS entirely (small-lot
     multi-SFD / cottage-court clusters), sized in our spine units: a city-coverage finding in its own right.
Plus s9_identity_caveat — the collapse cases are STILL collapsed in v3 (S1.5 not built): each flagged
"known-collapsed, pending S1.5", showing BOTH our collapsed number AND (for the 19) the city's per-building
figures, so the divergence is labeled PARTLY-OUR-ARTIFACT, not a clean city-vs-us difference.

Imports s0_keys + housing_predicates + gating + housing_rules + cpra_dedup (all genuinely CALLED — the
collapse set is derived from the raw CPRA feed exactly as build_s1 does; reporting_year via housing_rules).
--preview is READ-ONLY. Surfaces city-number differences; NEVER tunes toward them.
"""
import sqlite3, sys, os, argparse, glob, hashlib
from collections import defaultdict, Counter
from datetime import date
import pandas as pd
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import s0_keys
from s0_keys import normalize_address
import housing_predicates
from housing_predicates import is_housing, net_units
from gating import snapshot_v3
import housing_rules as hr
from cpra_dedup import extract_master_permit

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
MIRROR = os.path.join(ROOT, 'databases', 'hcd_apr_mirror_2026-06-17_fresh.db')  # FRESH deduped oracle, READ-ONLY
CPRA = [f for f in glob.glob(os.path.join(ROOT, 'data/raw/cpra-downloads', 'BP_Annual Permit Report-*.xlsx'))]
AS_OF = '2026-06-17'
YEARS = list(range(2018, 2026))

CO_COLS = ['CO_ACUTELY_LOW_INCOME_DR', 'CO_ACUTELY_LOW_INCOME_NDR', 'CO_EXTREMELY_LOW_INCOME_DR',
           'CO_EXTREMELY_INCOME_NDR', 'CO_VLOW_INCOME_DR', 'CO_VLOW_INCOME_NDR', 'CO_LOW_INCOME_DR',
           'CO_LOW_INCOME_NDR', 'CO_MOD_INCOME_DR', 'CO_MOD_INCOME_NDR', 'CO_ABOVE_MOD_INCOME']
CO_SUM = '+'.join(f"CAST(NULLIF({c},'') AS INT)" for c in CO_COLS)

# 3 developments the CITY ALSO collapsed (1 mirror row) -> S9 cannot externally check S1.5 there.
CITY_COLLAPSED = {('1136', 'KEITH'), ('1310', 'PARKER'), ('2587', 'TELEGRAPH')}


def _ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)


def _load_feed():
    def load(f):
        d = pd.read_excel(f, dtype=str, header=7); d.columns = [str(x).strip() for x in d.columns]; return d
    df = pd.concat([load(f) for f in CPRA], ignore_index=True)
    return df[df['PermitNumber'].notna()].copy()


def _bk(addr):
    """mirror free-text street address -> (number, STREET) base key via the shared key."""
    k = normalize_address(str(addr or ''))
    return (k.number, k.street) if k.number else None


def gather():
    v3 = _ro(V3); mir = _ro(MIRROR)

    # ---- OUTPUT 1 inputs: CO completions by reporting_year ----
    v3_year = dict(v3.execute(
        "SELECT reporting_year, CAST(SUM(units) AS INT) FROM s7_cycle "
        "WHERE event_type='co_issued' AND reporting_year BETWEEN 2018 AND 2025 GROUP BY reporting_year"))
    v3_bldg = dict(v3.execute(
        "SELECT reporting_year, COUNT(*) FROM s7_cycle "
        "WHERE event_type='co_issued' AND reporting_year BETWEEN 2018 AND 2025 GROUP BY reporting_year"))
    city_year = dict(mir.execute(
        f"SELECT CAST(YEAR AS INT), SUM({CO_SUM}) FROM table_a2 WHERE CO_ISSUE_DT1<>'' "
        f"AND CAST(YEAR AS INT) BETWEEN 2018 AND 2025 GROUP BY CAST(YEAR AS INT)"))
    scorecard = []
    for y in YEARS:
        vv = v3_year.get(y, 0) or 0; cc = city_year.get(y, 0) or 0
        cyc = hr.cycle_for_date(date(y, 7, 1))   # RHNA calendar cycle the reporting_year sits in (genuine hr call)
        scorecard.append((y, vv, cc, vv - cc, v3_bldg.get(y, 0),
                          f'CO completions: v3 reporting_year vs city table_a2 CO income-cols (like-for-like); {cyc} cycle'))

    # ---- derive the collapse set from the raw feed (≥2 New housing-creating master permits) ----
    df = _load_feed()
    df['isnew'] = df['Work Type'].astype(str).str.strip() == 'New'
    df = df[[is_housing(o, u, n, a) for o, u, n, a in zip(df['OccType'], df['UnitsAdded'], df['NumberUnits'], df['ADU'])]].copy()
    df['ak'] = df.apply(lambda r: (lambda k: (k.number, k.street) if k.number else None)(
        normalize_address(f"{r['StreetNumber']} {r['StreetName']} "
                          f"{'' if str(r['StreetType']).strip().lower()=='nan' else r['StreetType']}".strip())), axis=1)
    df['master'] = df['PermitNumber'].map(lambda p: extract_master_permit(str(p)))
    df['nu'] = [net_units(n, ua, num, a) for n, ua, num, a in zip(df['isnew'], df['UnitsAdded'], df['NumberUnits'], df['ADU'])]
    collapse = sorted([k for k, g in df.groupby('ak')
                       if k is not None and len(set(g[(g['isnew']) & (g['nu'] > 0)]['master'])) >= 2])

    # our spine units + CO reporting_year per collapse dev (from v3)
    spine = {}
    for num, street, units, bid in v3.execute("SELECT number,street,units,building_id FROM s1_projects"):
        spine.setdefault((num, street), {'units': 0.0, 'bid': None})
        spine[(num, street)]['units'] += (units or 0); spine[(num, street)]['bid'] = bid
    co_year_by_bldg = dict(v3.execute("SELECT building_id, MAX(reporting_year) FROM s7_cycle WHERE event_type='co_issued' GROUP BY building_id"))

    # ---- mirror grain per collapse dev: count CO-bearing rows + harvest per-building breakout ----
    breakout = []      # OUTPUT 2: per-building city rows (CITY-GRANULAR — the answer key)
    coverage = []      # OUTPUT 3: TRULY absent devs (no mirror row at all — the real coverage gap)
    pending = []       # the three-valued middle: city lists it (entitled/permitted) but no CO row yet
    caveat = []        # identity caveats (all 36)
    cls = Counter()
    # index mirror rows by base key — TWO views: ALL milestones (presence) and CO-bearing (completions)
    mir_all = defaultdict(list); mir_co = defaultdict(list)
    for (a,) in mir.execute("SELECT STREET_ADDRESS FROM table_a2").fetchall():
        k = _bk(a)
        if k: mir_all[k].append(a)
    # CO-bearing rows only (a real completion: has a CO issue date)
    for (a, apn, y, co, dt) in mir.execute(
            f"SELECT STREET_ADDRESS, APN, YEAR, ({CO_SUM}) co, CO_ISSUE_DT1 FROM table_a2 WHERE CO_ISSUE_DT1<>''").fetchall():
        k = _bk(a)
        if k: mir_co[k].append((a, apn, y, co))
    for (num, street) in collapse:
        co_rows = [h for h in mir_co.get((num, street), []) if (h[3] or 0) > 0]
        present = (num, street) in mir_all
        dev = f"{num} {street}"
        our_u = int(spine.get((num, street), {}).get('units', 0) or 0)
        our_co_year = co_year_by_bldg.get(spine.get((num, street), {}).get('bid'))
        if not present:
            cls['ABSENT'] += 1
            coverage.append((dev, our_u, 'city APR omits this development entirely (small-lot multi-SFD / cottage-court)',
                             'city_coverage_gap'))
            caveat.append((dev, our_u, our_co_year, 'absent', '', 'no external check (city did not report it at all)'))
        elif len(co_rows) >= 2 and (num, street) not in CITY_COLLAPSED:
            cls['CITY-GRANULAR'] += 1
            for (a, apn, y, co) in sorted(co_rows, key=lambda r: r[2]):
                breakout.append((dev, str(a), str(apn), int(y), int(co or 0),
                                 'agreement_with_oracle: city per-building CO row (corroboration, NOT independent proof)'))
            citybps = '; '.join(f"{int(co)}u@{y}" for (a, apn, y, co) in sorted(co_rows, key=lambda r: r[2]))
            caveat.append((dev, our_u, our_co_year, 'city-granular', f"city per-building: {citybps}",
                           'known-collapsed pending S1.5 — divergence PARTLY OUR ARTIFACT; check split vs city breakout'))
        elif len(co_rows) == 1:
            cls['CITY-COLLAPSED'] += 1
            caveat.append((dev, our_u, our_co_year, 'city-collapsed', 'city: 1 CO row',
                           'no external check (city also collapsed to one CO row)'))
        else:  # present but NO CO row yet (entitlement/BP only) — a three-valued middle state
            cls['REPORTED-NO-CO'] += 1
            pending.append((dev, our_u, 'city reports the development (entitled/permitted) but has no CO row yet',
                            'city_reported_pending'))
            caveat.append((dev, our_u, our_co_year, 'reported-no-CO', 'city: listed, no CO row yet',
                           'city-reported, not-yet-finaled (NOT present-complete, NOT a coverage gap)'))

    v3.close(); mir.close()
    return {'scorecard': scorecard, 'breakout': breakout, 'coverage': coverage, 'pending': pending,
            'caveat': caveat, 'collapse_n': len(collapse), 'cls': cls,
            'v3_total': sum(r[1] for r in scorecard), 'city_total': sum(r[2] for r in scorecard)}


def write_s9(g):
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s9_scorecard; DROP TABLE IF EXISTS s9_city_building_breakout;
      DROP TABLE IF EXISTS s9_coverage_gap; DROP TABLE IF EXISTS s9_city_reported_pending;
      DROP TABLE IF EXISTS s9_identity_caveat; DROP TABLE IF EXISTS s9_meta;
      CREATE TABLE s9_scorecard(reporting_year INT PRIMARY KEY, v3_co_units INT, city_co_units INT,
        delta INT, v3_co_buildings INT, note TEXT);
      CREATE TABLE s9_city_building_breakout(id INTEGER PRIMARY KEY, development TEXT, city_address TEXT,
        city_apn TEXT, reporting_year INT, co_units INT, basis TEXT);
      CREATE TABLE s9_coverage_gap(id INTEGER PRIMARY KEY, development TEXT, our_spine_units INT,
        finding TEXT, finding_type TEXT);
      CREATE TABLE s9_city_reported_pending(id INTEGER PRIMARY KEY, development TEXT, our_spine_units INT,
        finding TEXT, finding_type TEXT);
      CREATE TABLE s9_identity_caveat(id INTEGER PRIMARY KEY, development TEXT, v3_collapsed_units INT,
        v3_co_year INT, city_grain TEXT, city_per_building TEXT, status TEXT);
      CREATE TABLE s9_meta(key TEXT, value TEXT);
      CREATE INDEX ix_s9_bo_dev ON s9_city_building_breakout(development);
    """)
    con.executemany("INSERT INTO s9_scorecard VALUES(?,?,?,?,?,?)", g['scorecard'])
    con.executemany("INSERT INTO s9_city_building_breakout(development,city_address,city_apn,reporting_year,co_units,basis) "
                    "VALUES(?,?,?,?,?,?)", g['breakout'])
    con.executemany("INSERT INTO s9_coverage_gap(development,our_spine_units,finding,finding_type) VALUES(?,?,?,?)", g['coverage'])
    con.executemany("INSERT INTO s9_city_reported_pending(development,our_spine_units,finding,finding_type) VALUES(?,?,?,?)", g['pending'])
    con.executemany("INSERT INTO s9_identity_caveat(development,v3_collapsed_units,v3_co_year,city_grain,city_per_building,status) "
                    "VALUES(?,?,?,?,?,?)", g['caveat'])
    meta = [('stage', 'S9'), ('as_of', AS_OF), ('oracle', 'hcd_apr_mirror_2026-06-17_fresh.db (READ-ONLY, deduped)'),
            ('v3_co_total', str(g['v3_total'])), ('city_co_total', str(g['city_total'])),
            ('net', str(g['v3_total'] - g['city_total'])), ('collapse_devs', str(g['collapse_n'])),
            ('city_granular', str(g['cls']['CITY-GRANULAR'])), ('city_collapsed', str(g['cls']['CITY-COLLAPSED'])),
            ('city_reported_pending', str(g['cls']['REPORTED-NO-CO'])), ('city_absent', str(g['cls']['ABSENT'])),
            ('rule', 'CO<->CO by reporting_year; mirror oracle-only; never tune to city; collapse cases flagged pending S1.5'),
            ('key_module', 's0_keys + housing_predicates + gating + housing_rules + cpra_dedup')]
    con.executemany("INSERT INTO s9_meta VALUES(?,?)", meta)
    con.commit(); con.close()


def fingerprint_s9():
    con = _ro(V3)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    sc = con.execute("SELECT COUNT(*) FROM s9_scorecard").fetchone()[0]
    bo = con.execute("SELECT COUNT(DISTINCT development) FROM s9_city_building_breakout").fetchone()[0]
    cg = con.execute("SELECT COUNT(*) FROM s9_coverage_gap").fetchone()[0]
    pn = con.execute("SELECT COUNT(*) FROM s9_city_reported_pending").fetchone()[0]
    cv = con.execute("SELECT COUNT(*) FROM s9_identity_caveat").fetchone()[0]
    net = con.execute("SELECT SUM(v3_co_units)-SUM(city_co_units) FROM s9_scorecard").fetchone()[0]
    s7 = con.execute("SELECT COUNT(*) FROM s7_cycle").fetchone()[0]
    con.close()
    print("=== S9 FINGERPRINT (fresh connection) ===")
    print(f"  integrity: {ok} | scorecard yrs: {sc} | breakout devs: {bo} | coverage_gap: {cg} | reported_pending: {pn} | identity_caveat: {cv}")
    print(f"  net CO (v3-city): {net:+} | s7_cycle intact: {s7==2236}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true')
    ap.add_argument('--no-snapshot', action='store_true')
    args = ap.parse_args()
    g = gather(); FAIL = []
    sc, bo, cg, cv = g['scorecard'], g['breakout'], g['coverage'], g['caveat']
    print("=== S9 PREVIEW — A2 scorecard vs the city's submitted APR (read-only; no write) ===")
    print(f"\n  [OUTPUT 1] CO completions by reporting_year (v3 vs city, like-for-like):")
    print(f"      {'year':6}{'v3_units':>10}{'city_units':>12}{'delta':>8}{'v3_bldgs':>10}")
    for y, vv, cc, d, nb, _ in sc:
        print(f"      {y:<6}{vv:>10}{cc:>12}{d:>+8}{nb:>10}")
    print(f"      {'TOTAL':6}{g['v3_total']:>10}{g['city_total']:>12}{g['v3_total']-g['city_total']:>+8}")
    print(f"      net = {g['v3_total']-g['city_total']:+} (v3 {g['v3_total']} vs city {g['city_total']}; "
          f"completion count is extract-dated — surface, do NOT tune)")

    print(f"\n  [collapse classification] {g['collapse_n']} developments fold >=2 New master permits:")
    print(f"      CITY-GRANULAR {g['cls']['CITY-GRANULAR']} (S9 can check S1.5) · "
          f"CITY-COLLAPSED {g['cls']['CITY-COLLAPSED']} (1 CO row, no check) · "
          f"REPORTED-NO-CO {g['cls']['REPORTED-NO-CO']} (listed, no completion yet) · "
          f"ABSENT {g['cls']['ABSENT']} (true coverage gap)")

    print(f"\n  [OUTPUT 2] s9_city_building_breakout — ANSWER KEY for S1.5 ({len(bo)} per-building rows, "
          f"{len(set(r[0] for r in bo))} devs). AGREEMENT-WITH-ORACLE (corroboration, not independent proof):")
    for dev in list(dict.fromkeys(r[0] for r in bo))[:6]:
        rs = [r for r in bo if r[0] == dev]
        print(f"      {dev:16} -> " + "; ".join(f"{r[4]}u@{r[3]}" for r in rs))

    pn = g['pending']
    print(f"\n  [OUTPUT 3] s9_coverage_gap — TRUE gaps: city OMITS these {len(cg)} entirely "
          f"(units-at-stake = {sum(r[1] for r in cg)} spine units):")
    for dev, u, _, _ in sorted(cg, key=lambda r: -r[1])[:10]:
        print(f"      {dev:16} {u:>4}u")
    print(f"\n  [OUTPUT 4] s9_city_reported_pending — city lists it, no CO row yet (three-valued middle): "
          f"{len(pn)} devs, {sum(r[1] for r in pn)} spine units. sample:")
    for dev, u, _, _ in sorted(pn, key=lambda r: -r[1])[:8]:
        print(f"      {dev:16} {u:>4}u")

    print(f"\n  [identity caveats] {len(cv)} collapse devs flagged (known-collapsed pending S1.5). sample:")
    for dev, u, yr, grain, cpb, status in [c for c in cv if c[3] == 'city-granular'][:3]:
        print(f"      {dev}: v3 collapsed {u}u@{yr} | {cpb} | {status}")

    # ---- ACCEPTANCE GATE ----
    print(f"\n  === S9 ACCEPTANCE GATE ===")
    if g['v3_total'] != 4310: FAIL.append(f"v3 CO total {g['v3_total']} != 4310")
    if g['collapse_n'] != 36: FAIL.append(f"collapse devs {g['collapse_n']} != 36")
    if sum(g['cls'].values()) != g['collapse_n']:
        FAIL.append("classification does not sum to collapse_n")
    if len(set(r[0] for r in bo)) != g['cls']['CITY-GRANULAR']:
        FAIL.append(f"breakout devs {len(set(r[0] for r in bo))} != CITY-GRANULAR {g['cls']['CITY-GRANULAR']}")
    if len(cg) != g['cls']['ABSENT']: FAIL.append(f"coverage_gap {len(cg)} != ABSENT {g['cls']['ABSENT']}")
    if len(pn) != g['cls']['REPORTED-NO-CO']: FAIL.append(f"reported_pending {len(pn)} != REPORTED-NO-CO {g['cls']['REPORTED-NO-CO']}")
    if len(cv) != g['collapse_n']: FAIL.append(f"identity_caveat {len(cv)} != collapse_n {g['collapse_n']}")
    print(f"      v3 CO total 4310 · collapse 36 · granular/collapsed/absent sum · breakout==granular · "
          f"coverage==absent · caveats==36  -> {'PASS' if not FAIL else 'FAIL'}")
    for f in FAIL: print("      XXX", f)
    print(f"\n  mirror oracle-only (read-only) · CPRA feed read-only · s0_-s8_ untouched · collapse flagged pending S1.5.")

    if args.write:
        if FAIL:
            print("\n  WRITE ABORTED — acceptance gate failed."); sys.exit(1)
        mb = hashlib.sha256(open(MIRROR, 'rb').read()).hexdigest()
        if args.no_snapshot:
            print("\n  (--no-snapshot: idempotency re-run — not snapshotting; must not clobber the rollback point)")
        else:
            snap, created = snapshot_v3('s9')
            print(f"\n  snapshot: {os.path.basename(snap)} ({'created' if created else 'preserved existing — NOT clobbered'})")
        write_s9(g)
        print(f"  S9 WRITE -> {os.path.basename(V3)}: scorecard {len(sc)} · breakout {len(bo)} · coverage_gap {len(cg)} · caveats {len(cv)}")
        fingerprint_s9()
        ma = hashlib.sha256(open(MIRROR, 'rb').read()).hexdigest()
        print(f"  oracle mirror untouched: sha256 {'UNCHANGED' if mb == ma else 'CHANGED XX'} ({mb[:16]})")
