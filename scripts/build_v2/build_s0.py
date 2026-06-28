"""S0 — stage the CLEAN-KEY INDEX into a fresh berkeley_housing_v3.db.

S0 writes ONLY key-index infrastructure (building -> clean_address / canon_APN / permit_family,
protected-distinct pairs, S8-review buckets). NO project rows — those are S1.

Idempotent: re-running DROPs+rebuilds the S0 tables; same inputs -> same result.
Reads: live v2 (mode=ro) + CPRA corpus. Writes: v3 only. Live v2 is never opened for write.
Imports s0_keys (the single canon) — never reimplements key logic (anti-drift).

  python scripts/build_v2/build_s0.py --preview      # read-only, prints the plan
  python scripts/build_v2/build_s0.py --write        # creates/refreshes v3 S0 tables + fingerprint
"""
import sqlite3, sys, os, argparse, hashlib
from collections import defaultdict
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from s0_keys import normalize_address, disambiguate_distinct, canonicalize_apn
from cpra_dedup import extract_master_permit

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
CPRA = [os.path.join(ROOT, 'data/raw/cpra-downloads', f) for f in
        ('BP_Annual Permit Report-2018-2022.xlsx', 'BP_Annual Permit Report-2023-2025.xlsx')]
AS_OF = '2026-06-17'

def build_index():
    """Derive S0 structures in memory from v2 (cross-check/ATTACH universe) + CPRA corpus."""
    c = sqlite3.connect(f'file:{V2}?mode=ro', uri=True); c.row_factory = sqlite3.Row
    def co_of(pid):
        r = c.execute("SELECT MIN(event_date) FROM project_events pe JOIN vocabulary_event_types vt "
                      "ON vt.id=pe.event_type_id WHERE pe.project_id=? AND vt.code='co_issued'", (pid,)).fetchone()
        return r[0] if r else None
    def fams(pid):
        return sorted({extract_master_permit(p[0]) for p in
                       c.execute("SELECT permit_number FROM permits WHERE project_id=? AND permit_number IS NOT NULL", (pid,))
                       if extract_master_permit(p[0])})
    def apns(pid):
        out = set()
        for a in c.execute("SELECT k.apn FROM project_parcels pp JOIN parcels k ON k.id=pp.parcel_id WHERE pp.project_id=?", (pid,)):
            if a[0]:
                out.add(canonicalize_apn(a[0]))
        return sorted(x for x in out if x)

    rows = []
    for p in c.execute("SELECT id, canonical_address FROM projects WHERE merged_into_id IS NULL ORDER BY id"):
        k = normalize_address(p['canonical_address'])
        fam = fams(p['id']); ap = apns(p['id'])
        has_co = c.execute("SELECT co_issued_date FROM v_projects_flat WHERE project_id=?", (p['id'],)).fetchone()
        completed_no_permit = 1 if (has_co and has_co[0] and not fam) else 0
        rows.append(dict(project_id=p['id'], number=k.number, street=k.street, stype=k.stype,
                         bucket=f"{k.number} {k.street}".strip(), canon_apns='|'.join(ap),
                         permit_families='|'.join(fam), has_permit_family=int(bool(fam)),
                         has_apn=int(bool(ap)), completed_no_permit=completed_no_permit,
                         raw_address=p['canonical_address']))

    # protected-distinct pairs: same matching key, distinct (permit-family + CO)
    keys = {r['project_id']: normalize_address(r['raw_address']) for r in rows}
    recs = {r['project_id']: {'families': set(r['permit_families'].split('|')) if r['permit_families'] else set(),
                              'co': co_of(r['project_id'])} for r in rows}
    buck = defaultdict(list)
    for r in rows: buck[keys[r['project_id']].bucket].append(r['project_id'])
    protected = []  # list of (group_id, [pid_a, pid_b], shared_bucket)
    gid = 0
    for bk, ids in buck.items():
        if len(ids) < 2 or not bk[0]: continue
        for i in range(len(ids)):
            for j in range(i+1, len(ids)):
                a, b = ids[i], ids[j]
                if keys[a].matches(keys[b]) and disambiguate_distinct(recs[a], recs[b]):
                    gid += 1
                    protected.append((gid, a, b, f"{keys[a].number} {keys[a].street}".strip(),
                                      co_of(a), co_of(b)))

    # S8-review buckets: CPRA corpus number+street with >=2 DIFFERENT present types
    import pandas as pd
    def load(f):
        d = pd.read_excel(f, dtype=str, header=7); d.columns = [str(x).strip() for x in d.columns]; return d
    df = pd.concat([load(f) for f in CPRA], ignore_index=True)
    df = df[df['StreetNumber'].notna() & df['StreetName'].notna()]
    a = (df['StreetNumber'].astype(str).str.strip() + ' ' + df['StreetName'].astype(str).str.strip()
         + ' ' + df['StreetType'].fillna('').astype(str).str.strip()).str.strip().unique()
    cb = defaultdict(set)
    for s in a:
        k = normalize_address(s)
        if k.number: cb[k.bucket].add(k.stype)
    s8 = [(f"{bk[0]} {bk[1]}".strip(), '|'.join(sorted(t for t in ts if t)))
          for bk, ts in cb.items() if len({t for t in ts if t}) >= 2]
    c.close()
    return rows, protected, s8

def preview(rows, protected, s8):
    print("=== S0 PREVIEW — clean-key index to be written into v3 (NO project rows; that is S1) ===")
    print(f"  source: {os.path.basename(V2)} (mode=ro) + CPRA corpus")
    print(f"  s0_key_index rows (existing v2 projects, the ATTACH/cross-check universe): {len(rows)}")
    print(f"    - with permit_family key: {sum(r['has_permit_family'] for r in rows)}")
    print(f"    - with canon_APN key:     {sum(r['has_apn'] for r in rows)}")
    print(f"    - completed-but-no-permit (S6 flag): {sum(r['completed_no_permit'] for r in rows)} "
          f"-> {[r['project_id'] for r in rows if r['completed_no_permit']]}")
    print(f"  s0_protected_pairs (matching key, kept DISTINCT via disambiguator): {len(protected)}")
    for g, a, b, bk, ca, cb in protected:
        print(f"    group {g}: proj{a}/proj{b}  bucket '{bk}'  CO {ca}/{cb}  (distinct permit-family + CO)")
    print(f"  s0_s8_review_buckets (CPRA different-present-type, flag for S8 — NOT merged): {len(s8)}")
    for bk, ts in s8: print(f"    '{bk}': present types {ts}")
    print("  (live v2 untouched; nothing written in --preview)")

def write(rows, protected, s8):
    fresh = not os.path.exists(V3)
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s0_key_index;
      DROP TABLE IF EXISTS s0_protected_pairs;
      DROP TABLE IF EXISTS s0_s8_review_buckets;
      DROP TABLE IF EXISTS s0_meta;
      CREATE TABLE s0_key_index(project_id INTEGER PRIMARY KEY, number TEXT, street TEXT, stype TEXT,
        bucket TEXT, canon_apns TEXT, permit_families TEXT, has_permit_family INT, has_apn INT,
        completed_no_permit INT, raw_address TEXT);
      CREATE INDEX ix_s0_bucket ON s0_key_index(bucket);
      CREATE TABLE s0_protected_pairs(group_id INT, project_id_a INT, project_id_b INT,
        shared_bucket TEXT, co_a TEXT, co_b TEXT);
      CREATE TABLE s0_s8_review_buckets(bucket TEXT PRIMARY KEY, present_types TEXT, reason TEXT, source TEXT);
      CREATE TABLE s0_meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    con.executemany("INSERT INTO s0_key_index VALUES(:project_id,:number,:street,:stype,:bucket,"
                    ":canon_apns,:permit_families,:has_permit_family,:has_apn,:completed_no_permit,:raw_address)", rows)
    con.executemany("INSERT INTO s0_protected_pairs VALUES(?,?,?,?,?,?)", protected)
    con.executemany("INSERT INTO s0_s8_review_buckets VALUES(?,?,'different_present_types','CPRA_corpus')", s8)
    for k, v in [('stage', 'S0'), ('as_of', AS_OF), ('source_v2', os.path.basename(V2)),
                 ('key_module', 's0_keys.py'), ('key_index_rows', str(len(rows))),
                 ('protected_pairs', str(len(protected))), ('s8_review_buckets', str(len(s8)))]:
        con.execute("INSERT INTO s0_meta VALUES(?,?)", (k, v))
    con.commit(); con.close()
    return fresh

def fingerprint():
    con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ('s0_key_index', 's0_protected_pairs', 's0_s8_review_buckets', 's0_meta')}
    h = hashlib.sha256()
    for r in con.execute("SELECT project_id,bucket,stype,canon_apns,permit_families FROM s0_key_index ORDER BY project_id"):
        h.update(str(tuple(r)).encode())
    con.close()
    print("=== S0 FINGERPRINT (fresh connection read-back) ===")
    print(f"  integrity_check: {ok}")
    print(f"  row counts: {counts}")
    print(f"  key_index content sha256: {h.hexdigest()[:16]}")
    return ok, counts

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true')
    args = ap.parse_args()
    rows, protected, s8 = build_index()
    if args.write:
        v2_size = os.path.getsize(V2)
        fresh = write(rows, protected, s8)
        print(f"=== S0 WRITE -> {V3} ({'created fresh' if fresh else 'refreshed (idempotent)'}) ===")
        fingerprint()
        assert os.path.getsize(V2) == v2_size, "LIVE V2 SIZE CHANGED — abort"
        print(f"  live v2 untouched: size {v2_size} bytes unchanged (opened mode=ro only)")
    else:
        preview(rows, protected, s8)
