"""S1 — CPRA spine ingest (status-keyed CREATE-vs-ATTACH) into v3.

Reads: CPRA corpus + v3.s0_key_index (the S0 existing-project match index). Imports s0_keys
(the single canon — never reimplements) + cpra_dedup.extract_master_permit.
S1 writes project rows into v3; this module's --preview is READ-ONLY (no write).

Spine rule (inversion of match-or-drop):
- Universe = residential by STRUCTURED column (OccType R-1/2/3 or SubType Residential|Mixed Use)
  AND Work Type='New'. Trade/alteration/non-residential excluded by Work Type, never by prose.
- Group rows into BUILDINGS by clean address key (number, street, type) via s0_keys — the
  type-wildcard relation. Units = MAX(UnitsAdded else NumberUnits) across the building's rows
  (REV/phase guard: MAX, never SUM — phase permits each carry the whole-building count).
- CREATE-vs-ATTACH: ATTACH if the building hits an existing v2 project in the S0 index by
  permit-family OR canon-APN OR address-match; else CREATE.
"""
import sqlite3, sys, os, argparse, re
from collections import defaultdict
import pandas as pd
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from s0_keys import normalize_address, AddressKey, canonicalize_apn
from housing_predicates import is_housing, net_units    # the shared housing predicates (single source)
from gating import snapshot_v3                           # the SHARED snapshot helper (refuses to clobber)
from cpra_dedup import extract_master_permit

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
CPRA = [os.path.join(ROOT, 'data/raw/cpra-downloads', f) for f in
        ('BP_Annual Permit Report-2018-2022.xlsx', 'BP_Annual Permit Report-2023-2025.xlsx')]

def fnum(x):
    try: return float(str(x).replace(',', ''))
    except Exception: return 0.0

# is_housing + net_units now live in housing_predicates (imported above) — single source, no drift.

def load_cpra():
    def load(f):
        d = pd.read_excel(f, dtype=str, header=7); d.columns = [str(x).strip() for x in d.columns]; return d
    df = pd.concat([load(f) for f in CPRA], ignore_index=True)
    return df[df['PermitNumber'].notna()].copy()

def load_s0_index():
    """Existing v2 projects keyed three ways (from v3.s0_key_index)."""
    c = sqlite3.connect(f'file:{V3}?mode=ro', uri=True); c.row_factory = sqlite3.Row
    by_family, by_apn, by_bucket = defaultdict(set), defaultdict(set), defaultdict(list)
    protected = set()
    for a, b in c.execute("SELECT project_id_a, project_id_b FROM s0_protected_pairs"):
        protected.add(a); protected.add(b)
    n = 0
    for r in c.execute("SELECT * FROM s0_key_index"):
        pid = r['project_id']; n += 1
        for f in (r['permit_families'] or '').split('|'):
            if f: by_family[f].add(pid)
        for ap in (r['canon_apns'] or '').split('|'):
            if ap: by_apn[ap].add(pid)
        ak = AddressKey(r['number'], r['street'], r['stype'], r['raw_address'])
        by_bucket[ak.bucket].append((pid, ak))
    c.close()
    return by_family, by_apn, by_bucket, protected, n

def build_spine():
    df = load_cpra()
    # HOUSING predicate (tightened, false-negative-safe): a residential OCCUPANCY class (R-1/R-2/R-3,
    # incl R-2.1/R-3.1 care/supervised) OR any dwelling units added. The units clause is ESSENTIAL and
    # not redundant: ADUs are coded 'U' (accessory) and mixed-use towers can carry an 'A'/'B' ground-
    # floor OccType, yet both are real housing (3000 San Pablo 78u coded A-2; ~14 U-coded ADUs w/ units).
    # Pure 0-unit non-housing (garages, restaurants, mercantile) is excluded; the old SubType-only
    # predicate let a New garage in as a 0u building.
    df['ua'] = df['UnitsAdded'].map(fnum); df['nu'] = df['NumberUnits'].map(fnum)
    df['resi'] = [is_housing(o, u, n, a) for o, u, n, a in
                  zip(df['OccType'], df['UnitsAdded'], df['NumberUnits'], df['ADU'])]
    df['isnew'] = df['Work Type'].astype(str).str.strip() == 'New'
    # group ALL residential rows by building (so phased close-in permits join their building);
    # spine membership + units are decided per BUILDING, not per row. Units use the Q3 corrected
    # net_units rule (recovers ADU dwellings coded with NumberUnits; excludes existing-stock alterations).
    resi = df[df['resi']].copy().rename(columns={
        'Finaled Status': 'FinaledStatus', 'Finaled Date': 'FinaledDate', 'Parcel Number': 'ParcelNumber'})
    bld = defaultdict(lambda: {'units': 0.0, 'has_new': False, 'fams': set(),
                               'apns': set(), 'finaled': set(), 'permits': set(), 'addrkey': None, 'rows': []})
    for r in resi.itertuples(index=False):
        st = r.StreetType
        st = '' if (st is None or str(st).strip().lower() == 'nan') else str(st)   # nan-guard
        raw = f"{r.StreetNumber} {r.StreetName} {st}".strip()
        k = normalize_address(raw)
        if not k.number: continue
        b = bld[(k.number, k.street, k.stype)]; b['addrkey'] = k
        pn = str(r.PermitNumber); b['permits'].add(pn)
        nu_row = net_units(r.isnew, r.ua, r.nu, r.ADU)   # raw ADU -> is_adu inside
        b['units'] = max(b['units'], nu_row)             # MAX (REV/phase guard)
        if r.isnew:
            b['has_new'] = True
        fam = extract_master_permit(pn)
        if fam: b['fams'].add(fam)
        ca = canonicalize_apn(str(r.ParcelNumber))
        if ca: b['apns'].add(ca)
        fdate = str(r.FinaledDate)[:10] if (str(r.FinaledStatus).strip().lower() == 'finaled' and str(r.FinaledDate) != 'nan') else None
        if fdate: b['finaled'].add(fdate)
        b['rows'].append((pn, ca, nu_row, bool(r.isnew), fdate, str(r.WorkDescription)))   # per-permit detail for the multi-building split
    # spine = a building with any New permit OR any net-new dwelling units (Q3 corrected signal)
    spine = {gk: b for gk, b in bld.items() if b['has_new'] or b['units'] > 0}
    # S9 multi-building split rule is implemented + validated below (split_multibuilding) BUT NOT WIRED:
    # S2-S8 key buildings by (number,street,stype) — two buildings at one address COLLIDE in their
    # smap dict (build_s2.load_spine L79), so they re-merge downstream. Wiring this requires re-keying
    # S2-S8 to per-building identity first. Held for that architecture change (see docs/audit).
    # spine = split_multibuilding(spine)
    excluded = df[~df['resi']]
    return spine, resi, excluded, df


# --- S9 multi-building split (root-cause fix for the address-grouping-ignores-APN collapse) ---
# A building keyed by ONE address but spanning >=2 APNs that EACH carry a real-build permit with DISTINCT
# unit counts AND DISTINCT CO years is two+ distinct buildings (the two-COs=two-buildings rule, applied
# PER-APN — which the address-only grouping skips). Validated: splits exactly 2352 Shattuck (North 135u@2022
# + South 69u@2023), exonerates all 59 other multi-APN buildings (sub-parcel / solar / condo / phased /
# demo-rebuild). Blind spot (flagged): two IDENTICAL buildings (same count) would not split — 0 such cases now.
_RB_EXCL = re.compile(r'\b(solar|PV|panel|condo|kitchen|water heater|oven|EV char|seismic|retrofit|remodel|temp power|demolish|interior|alteration)\b', re.I)
_RB_INCL = re.compile(r'\b(new construction|new \d|\d+ ?(unit|story|stories)|apartment|dwelling|residential|mixed use|building [a-d])\b', re.I)


def _is_realbuild(isnew, nu_row, desc):
    """A genuine new-building permit (NEW + >=2 units + construction prose), excluding solar/condo/alteration."""
    return bool(isnew) and nu_row >= 2 and not _RB_EXCL.search(desc or '') and bool(_RB_INCL.search(desc or ''))


def split_multibuilding(spine):
    out = {}
    for gk, b in spine.items():
        apn_u, apn_y = defaultdict(int), defaultdict(set)
        for (pn, ca, nu_row, isnew, fdate, desc) in b['rows']:
            if ca and _is_realbuild(isnew, nu_row, desc):
                apn_u[ca] = max(apn_u[ca], nu_row)
                if fdate: apn_y[ca].add(fdate[:4])
        rb = {a: u for a, u in apn_u.items() if u >= 2}
        distinct_units = len(set(rb.values())) > 1
        distinct_years = len({min(apn_y[a]) for a in rb if apn_y[a]}) > 1
        if len(rb) >= 2 and distinct_units and distinct_years:
            big = max(rb, key=rb.get)   # orphan rows (APN not a real-build APN) attach to the largest sub-building
            for apn in rb:
                sub = {'units': 0.0, 'has_new': False, 'fams': set(), 'apns': {apn},
                       'finaled': set(), 'permits': set(), 'addrkey': b['addrkey'], 'rows': []}
                for row in b['rows']:
                    home = row[1] if row[1] in rb else big
                    if home != apn: continue
                    sub['permits'].add(row[0]); sub['units'] = max(sub['units'], row[2])
                    if row[3]: sub['has_new'] = True
                    if row[4]: sub['finaled'].add(row[4])
                    fam = extract_master_permit(row[0])
                    if fam: sub['fams'].add(fam)
                    sub['rows'].append(row)
                out[(gk[0], gk[1], gk[2], apn)] = sub
        else:
            out[gk] = b
    return out

def classify(bld, by_family, by_apn, by_bucket):
    """ATTACH only on STRONG identity: permit-family (the existing project literally holds this
    master permit) OR address-key match. APN is CORROBORATING ONLY — an APN hit with no
    family/address match (a different-address project sharing a parcel, e.g. a CPRA permit
    recorded against a sibling/mis-entered APN) does NOT auto-ATTACH. Such a building stays
    CREATE, flagged apn_overlap_review. Never merge across addresses on a pooled/shared APN."""
    create, attach = [], []
    for gk, b in bld.items():
        fam_hit = set()
        for f in b['fams']:
            fam_hit |= by_family.get(f, set())
        addr_hit = set()
        for pid, ak in by_bucket.get(b['addrkey'].bucket, []):
            if b['addrkey'].matches(ak): addr_hit.add(pid)
        apn_hit = set()
        for ap in b['apns']:
            apn_hit |= by_apn.get(ap, set())
        strong = fam_hit | addr_hit
        rec = dict(gk=gk, units=b['units'], fams='|'.join(sorted(b['fams'])),
                   apns='|'.join(sorted(b['apns'])), permits=sorted(b['permits']),
                   n_finaled=len(b['finaled']),
                   hit=sorted(strong), via=('family' if fam_hit else 'address') if strong else None,
                   apn_overlap=sorted(apn_hit - strong))   # corroboration / review flag only
        (attach if strong else create).append(rec)
    return create, attach

TIER1 = [("2001 Fourth St", 152), ("1950 Addison St", 107), ("1900 Walnut St", 65),
         ("2503 Haste St", 55), ("1808 University Ave", 44), ("2747 San Pablo Ave", 41),
         ("0 San Pablo Ave", 40), ("2740 San Pablo Ave", 23), ("2556 Telegraph Ave", 22),
         ("2013 Second St", 19)]

def tier1_check(create):
    """-> list of (address, expected_units, found_units_or_None, ok)."""
    cset = {(r['gk'][0], r['gk'][1]): r for r in create}
    out = []
    for addr, exp in TIER1:
        k = normalize_address(addr); m = cset.get((k.number, k.street))
        out.append((addr, exp, int(m['units']) if m else None, bool(m and abs(m['units'] - exp) < 1)))
    return out

def scan_attaches(attach):
    """Classify ATTACHes via the STRICT address key. Returns (suspects, review, s4_queue).
    - suspects (FAIL): CROSS-address ATTACH where a big building (>=5u) merges into a much smaller
      project (<= max(2, bu/2)) -> permit-mislink risk. (APN-only cross-address can't reach here:
      APN never triggers ATTACH; only permit-family/address do. Family is permit-identity, so a
      cross-address family match is normally benign EXCEPT this big->small signature.)
    - review (info): benign cross-address family match (near-address / consistent units).
    - s4_queue (info): SAME-address ATTACH where CPRA units > v2 units -> v2 undercount, S4 fixes."""
    v2 = sqlite3.connect(f'file:{os.path.join(ROOT, "databases", "berkeley_housing_v2.db")}?mode=ro', uri=True)
    punits = {r[0]: (r[1] or 0) for r in v2.execute("SELECT project_id,total_units FROM v_projects_flat")}
    paddr = {r[0]: r[1] for r in v2.execute("SELECT project_id,address_display FROM v_projects_flat")}
    v2.close()
    suspects, review, s4_queue = [], [], []
    for r in attach:
        bu = r['units']; bbucket = (r['gk'][0], r['gk'][1])
        for pid in r['hit']:
            pu = punits.get(pid, 0); pa = paddr.get(pid)
            pk = normalize_address(pa) if pa else None
            same_addr = pk is not None and (pk.number, pk.street) == bbucket   # STRICT key, no fuzz
            row = (r['gk'], int(bu), pid, pa, int(pu), r['via'])
            if same_addr:
                if bu >= 5 and abs(bu - pu) >= 5: s4_queue.append(row)
            elif bu >= 5 and pu <= max(2, bu / 2):
                suspects.append(row)            # big building into a much smaller different-address project
            else:
                review.append(row)              # benign near-address family match (same permit)
    return suspects, review, s4_queue

AS_OF = '2026-06-17'


def write_s1(create, attach, suspects, review, s4_queue):
    """Persist the S1 spine into v3 (s1_* tables only; s0_* untouched). Idempotent: DROP+rebuild."""
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s1_projects;
      DROP TABLE IF EXISTS s1_apn_overlap;
      DROP TABLE IF EXISTS s1_s4_unit_reconcile;
      DROP TABLE IF EXISTS s1_xaddr_review;
      DROP TABLE IF EXISTS s1_meta;
      CREATE TABLE s1_projects(building_id INTEGER PRIMARY KEY, decision TEXT, v2_project_ids TEXT,
        number TEXT, street TEXT, stype TEXT, bucket TEXT, units REAL, permit_families TEXT,
        canon_apns TEXT, n_finaled INT, via TEXT);
      CREATE INDEX ix_s1_bucket ON s1_projects(bucket);
      CREATE INDEX ix_s1_decision ON s1_projects(decision);
      CREATE TABLE s1_apn_overlap(building_id INT, v2_project_id INT);
      CREATE TABLE s1_s4_unit_reconcile(bucket TEXT, cpra_units INT, v2_project_id INT, v2_units INT);
      CREATE TABLE s1_xaddr_review(bucket TEXT, cpra_units INT, v2_project_id INT, v2_addr TEXT, v2_units INT, via TEXT);
      CREATE TABLE s1_meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    rows, overlaps = [], []
    bid = 0
    for decision, recs in (('CREATE', create), ('ATTACH', attach)):
        for r in recs:
            bid += 1; gk = r['gk']
            rows.append((bid, decision, '|'.join(map(str, r['hit'])), gk[0], gk[1], gk[2],
                         f"{gk[0]} {gk[1]}".strip(), r['units'], r['fams'], r.get('apns', ''),
                         r['n_finaled'], r['via']))
            for pid in r.get('apn_overlap', []):
                overlaps.append((bid, pid))
    con.executemany("INSERT INTO s1_projects VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.executemany("INSERT INTO s1_apn_overlap VALUES(?,?)", overlaps)
    con.executemany("INSERT INTO s1_s4_unit_reconcile VALUES(?,?,?,?)",
                    [(f"{g[0]} {g[1]}".strip(), bu, pid, pu) for g, bu, pid, pa, pu, via in s4_queue])
    con.executemany("INSERT INTO s1_xaddr_review VALUES(?,?,?,?,?,?)",
                    [(f"{g[0]} {g[1]}".strip(), bu, pid, pa, pu, via) for g, bu, pid, pa, pu, via in review])
    meta = [('stage', 'S1'), ('as_of', AS_OF), ('create', str(len(create))), ('attach', str(len(attach))),
            ('create_units', str(int(sum(r['units'] for r in create)))),
            ('apn_overlap', str(len(overlaps))), ('s4_reconcile', str(len(s4_queue))),
            ('xaddr_review', str(len(review))), ('key_module', 's0_keys.py')]
    con.executemany("INSERT INTO s1_meta VALUES(?,?)", meta)
    con.commit(); con.close()
    return bid, len(overlaps)

def fingerprint_s1():
    con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
              ('s0_key_index', 's1_projects', 's1_apn_overlap', 's1_s4_unit_reconcile', 's1_xaddr_review', 's1_meta')}
    cre = con.execute("SELECT COUNT(*), CAST(COALESCE(SUM(units),0) AS INT) FROM s1_projects WHERE decision='CREATE'").fetchone()
    att = con.execute("SELECT COUNT(*) FROM s1_projects WHERE decision='ATTACH'").fetchone()[0]
    # Tier-1 present check from the persisted table
    t1 = con.execute("""SELECT COUNT(*), CAST(SUM(units) AS INT) FROM s1_projects WHERE decision='CREATE' AND bucket IN
        ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO',
         '0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND')""").fetchone()
    con.close()
    print("=== S1 FINGERPRINT (fresh connection) ===")
    print(f"  integrity_check: {ok}")
    print(f"  CREATE: {cre[0]} buildings / {cre[1]} units   ATTACH: {att}   (spine {cre[0]+att})")
    print(f"  Tier-1 in s1_projects as CREATE: {t1[0]}/10 buildings / {t1[1]}u")
    print(f"  table counts: {counts}")
    return ok, cre, att, t1

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true'); ap.add_argument('--no-snapshot', action='store_true')
    args = ap.parse_args()
    by_family, by_apn, by_bucket, protected, n_idx = load_s0_index()
    spine, resi, excluded, df = build_spine()
    create, attach = classify(spine, by_family, by_apn, by_bucket)
    cu = sum(r['units'] for r in create); au = sum(r['units'] for r in attach)
    FAIL = []

    print("=== S1 PREVIEW — CPRA spine ingest (read-only; no write) ===")
    print(f"  S0 index loaded: {n_idx} existing v2 projects (3-way: family/APN/address)")

    print(f"\n  [4] RESIDENTIAL FILTER (structured columns, never prose):")
    print(f"      CPRA rows {len(df):,}  |  residential rows {len(resi):,}  |  non-residential (excluded) {len(excluded):,}")
    print(f"      -> NEW/unit-adding residential BUILDINGS (spine): {len(spine)}")
    nonnew = resi[~resi['isnew']]
    print(f"      residential non-New rows (alterations etc., not spine-creating): {len(nonnew):,}")
    print(f"      their Work-Type mix (confirm trade/alteration stays out): {dict(nonnew['Work Type'].astype(str).value_counts().head(5))}")

    print(f"\n  [1] CREATE vs ATTACH:")
    apn_flag = [r for r in create if r['apn_overlap']]
    print(f"      CREATE (net-new v3 projects): {len(create)} buildings / {int(cu)} units "
          f"(incl {len(apn_flag)} flagged apn_overlap_review)")
    print(f"      ATTACH (to existing v2 via family/address): {len(attach)} buildings / {int(au)} units")
    print(f"        via permit-family: {sum(1 for r in attach if r['via']=='family')}  via address: {sum(1 for r in attach if r['via']=='address')}")

    # BLAST-RADIUS via the shared scan (same definition test_s1_gate uses -> no drift)
    suspects, review, s4_queue = scan_attaches(attach)
    print(f"\n  [BLAST RADIUS] CROSS-address big->small ATTACHes (mislink risk): {len(suspects)}")
    for gk, bu, pid, pa, pu, via in suspects[:20]:
        print(f"      !! {gk[0]} {gk[1]} {bu}u -> proj{pid} '{pa}' {pu}u  via={via}")
    if suspects: FAIL.append(f"{len(suspects)} cross-address big->small false-ATTACH")
    print(f"  cross-address benign family matches (near-address, same permit -> review): {len(review)}")
    print(f"  [S4 reconcile queue] same-address ATTACHes, CPRA units > v2 units (v2 undercount): {len(s4_queue)}")
    for gk, bu, pid, pa, pu, via in s4_queue[:10]:
        print(f"      {gk[0]} {gk[1]} CPRA {bu}u vs v2 proj{pid} {pu}u")
    if apn_flag:
        print(f"\n  [apn_overlap review queue] {len(apn_flag)} CREATE buildings carry a different-address APN overlap:")
        for r in apn_flag[:10]:
            print(f"      {r['gk'][0]} {r['gk'][1]} {int(r['units'])}u  apn-overlaps proj {r['apn_overlap']} (kept CREATE, flagged)")

    print(f"\n  [2] ~568u TIER-1 material completions present as CREATE:")
    tot = 0
    for addr, exp, found, ok in tier1_check(create):
        if not ok: FAIL.append(f"Tier-1 {addr}: {'absent from CREATE' if found is None else str(found)+'u != '+str(exp)}")
        tot += (found or 0)
        print(f"      {addr:22} expect {exp:>3}u: {'CREATE '+str(found)+'u OK' if ok else ('FAIL '+(str(found)+'u' if found is not None else 'ABSENT'))}")
    print(f"      Tier-1 CREATE total: {int(tot)}u  (target ~568)")

    print(f"\n  [6] 2503 HASTE phase-triple-count guard:")
    cset = {(r['gk'][0], r['gk'][1]): r for r in create}
    hk = normalize_address("2503 Haste St"); h = cset.get((hk.number, hk.street))
    if h:
        masters = sorted({p for p in h['permits'] if '-REV' not in p and '-DEF' not in p})
        ok = abs(h['units']-55) < 1
        if not ok: FAIL.append("2503 Haste != 55u")
        print(f"      ONE building: {int(h['units'])}u  (masters {masters}; 3x55 SUM avoided -> {'OK' if ok else 'FAIL'})")

    print(f"\n  [3] NO FALSE DUPS against S0 key:")
    false_create = []
    for r in create:
        for pid, ak in by_bucket.get((r['gk'][0], r['gk'][1]), []):
            if normalize_address(' '.join(filter(None, r['gk']))).matches(ak):
                false_create.append((r['gk'], pid))
    print(f"      CREATE buildings that ALSO match an existing project (should be 0): {len(false_create)}")
    if false_create: FAIL.append(f"{len(false_create)} false CREATE(s) that should be ATTACH"); print(f"        {false_create[:5]}")
    prot_in_attach = [r for r in attach if set(r['hit']) & protected]
    print(f"      ATTACH hits touching a protected-pair project: {len(prot_in_attach)} (write resolves via disambiguator)")
    print(f"      protected projects: {sorted(protected)}")

    print(f"\n  [5] REV-trap sample (units from master row, never summed):")
    revs = [r for r in (create+attach) if any('-REV' in p or '-DEF' in p for p in r['permits']) and r['units'] > 0][:3]
    for r in revs:
        print(f"      {r['gk'][0]} {r['gk'][1]}: units={int(r['units'])} (MAX UnitsAdded) across {len(r['permits'])} rows incl REV/DEF -> not summed")

    print(f"\n  === S1 ACCEPTANCE GATE: {'PASS' if not FAIL else 'FAIL'} ===")
    for f in FAIL: print("    XXX", f)
    if args.write:
        if FAIL:
            print("\n  WRITE ABORTED — acceptance gate failed."); sys.exit(1)
        v2_path = os.path.join(ROOT, "databases", "berkeley_housing_v2.db")
        import hashlib
        v2_before = hashlib.sha256(open(v2_path, 'rb').read()).hexdigest()
        if args.no_snapshot:
            print("\n  (--no-snapshot: idempotency re-run, NOT snapshotting — must not clobber the rollback point)")
        else:
            snap, created = snapshot_v3('s1-rerun')
            print(f"\n  snapshot: {os.path.basename(snap)} ({'created' if created else 'preserved existing — NOT clobbered'})")
        n, n_ov = write_s1(create, attach, suspects, review, s4_queue)
        print(f"  S1 WRITE -> {os.path.basename(V3)}: {n} s1_projects rows ({n_ov} apn_overlap)")
        fingerprint_s1()
        v2_after = hashlib.sha256(open(v2_path, 'rb').read()).hexdigest()
        print(f"  live v2 untouched: sha256 {'UNCHANGED' if v2_before==v2_after else 'CHANGED ✗✗'} ({v2_before[:16]})")
