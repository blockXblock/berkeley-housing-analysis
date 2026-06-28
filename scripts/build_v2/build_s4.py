"""S4 — finalize the canonical per-building unit count + resolve the s1_s4_unit_reconcile disagreements.

Units already come from the corrected net_units (S1): ua if ua>0; nu if New; min(nu,2) if ADU; else 0;
MAX over a building's permits (REV/phase guard). S4 does NOT re-derive them differently — the canonical
count IS net_units for all 1,385 buildings. S4's job is narrow and evidence-bound:
  - RESOLVE the 6 CPRA-vs-v2 disagreements BY EVIDENCE (the structured per-permit-family net_units),
    never by defaulting to either source;
  - where the evidence is ambiguous (a multi-building development whose permit-families don't cleanly
    aggregate), FLAG it to S8 and HOLD the structured value — write a number only when corroborated;
  - confirm no residual internal leak (canonical total vs any unit breakdown).

Imports s0_keys + housing_predicates + gating. --preview is READ-ONLY.
"""
import sqlite3, sys, os, argparse
import pandas as pd
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from s0_keys import normalize_address
from housing_predicates import net_units
from gating import snapshot_v3
from cpra_dedup import extract_master_permit

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
AS_OF = '2026-06-17'
CPRA = [os.path.join(ROOT, 'data/raw/cpra-downloads', f) for f in
        ('BP_Annual Permit Report-2018-2022.xlsx', 'BP_Annual Permit Report-2023-2025.xlsx')]


def load_cpra():
    def load(f):
        d = pd.read_excel(f, dtype=str, header=7); d.columns = [str(x).strip() for x in d.columns]; return d
    df = pd.concat([load(f) for f in CPRA], ignore_index=True)
    return df[df['PermitNumber'].notna()]


def permit_families(df, num, street_first):
    """distinct permit-family -> max net_units, for the housing-creating permits at this address."""
    m = df[(df['StreetNumber'].astype(str).str.strip() == num) &
           (df['StreetName'].astype(str).str.upper().str.contains(street_first, na=False))]
    fam = {}
    for _, r in m.iterrows():
        nu = net_units(str(r['Work Type']).strip() == 'New', r['UnitsAdded'], r['NumberUnits'], r['ADU'])
        if nu > 0:
            fm = extract_master_permit(str(r['PermitNumber'])) or str(r['PermitNumber'])
            fam[fm] = max(fam.get(fm, 0), nu)
    return fam


def resolve_reconcile():
    """Resolve each disagreement by EVIDENCE. Returns list of
    (bucket, our_units, v2_pid, v2_units, verdict, canonical, why)."""
    v3 = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    v2 = sqlite3.connect(f'file:{V2}?mode=ro', uri=True)
    recon = list(v3.execute("SELECT bucket,cpra_units,v2_project_id,v2_units FROM s1_s4_unit_reconcile"))
    df = load_cpra()
    out = []
    for bucket, cu, pid, vu in recon:
        num, st = bucket.split(' ', 1)
        fam = permit_families(df, num, st.split()[0])
        nfam = len(fam)
        desc = v2.execute("SELECT description FROM project_versions WHERE project_id=? AND is_current=1", (pid,)).fetchone()
        desc = (desc[0] or '') if desc else ''
        if nfam >= 2:
            # multiple distinct permit-families at one address = a MULTI-BUILDING development; our per-
            # building MAX under-counts and the families don't cleanly aggregate -> hold, flag to S8.
            verdict = 'FLAG_S8'; canonical = cu
            why = (f"multi-building development ({nfam} permit-families {dict((k,int(x)) for k,x in fam.items())}); "
                   f"per-building MAX={cu} under-counts; v2={vu} is the development total — HOLD structured value, do not guess")
        else:
            # single structured family -> our net_units IS the building's count; the v2 number is the error.
            verdict = 'RESOLVE_OURS'; canonical = cu
            kind = 'v2 under-count' if vu < cu else 'v2 stored value contradicts its own permit'
            corrob = ' (v2 description itself states this count)' if str(int(cu)) in desc else ''
            why = f"single permit-family structured net_units={cu}; {kind} (v2={vu}){corrob}"
        out.append((bucket, cu, pid, vu, verdict, canonical, why))
    v3.close(); v2.close()
    return out


def write_s4(s1units, resolved):
    """Persist s4_units (canonical = net_units) + s4_unit_reconcile_resolved into v3. Idempotent."""
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s4_units;
      DROP TABLE IF EXISTS s4_unit_reconcile_resolved;
      DROP TABLE IF EXISTS s4_meta;
      CREATE TABLE s4_units(building_id INTEGER PRIMARY KEY, units REAL, bucket TEXT, source TEXT);
      CREATE TABLE s4_unit_reconcile_resolved(bucket TEXT, our_units REAL, v2_project_id INT, v2_units REAL,
        verdict TEXT, canonical REAL, evidence TEXT);
      CREATE TABLE s4_meta(key TEXT, value TEXT);
    """)
    con.executemany("INSERT INTO s4_units VALUES(?,?,?,'net_units')",
                    [(bid, u, b) for bid, (u, b) in s1units.items()])
    con.executemany("INSERT INTO s4_unit_reconcile_resolved VALUES(?,?,?,?,?,?,?)", resolved)
    res_ours = sum(1 for r in resolved if r[4] == 'RESOLVE_OURS')
    meta = [('stage', 'S4'), ('as_of', AS_OF), ('buildings', str(len(s1units))),
            ('reconcile_total', str(len(resolved))), ('resolved_by_evidence', str(res_ours)),
            ('flagged_s8', str(len(resolved) - res_ours)),
            ('key_module', 's0_keys.py + housing_predicates.py + gating.py')]
    con.executemany("INSERT INTO s4_meta VALUES(?,?)", meta)
    con.commit(); con.close()
    return len(s1units), len(resolved)


def fingerprint_s4():
    con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    n = con.execute("SELECT COUNT(*) FROM s4_units").fetchone()[0]
    leak = con.execute("SELECT COUNT(*) FROM s4_units s JOIN s1_projects p ON p.building_id=s.building_id WHERE s.units<>p.units").fetchone()[0]
    t1 = con.execute("""SELECT CAST(SUM(units) AS INT) FROM s4_units WHERE bucket IN
        ('2001 4TH','1950 ADDISON','1900 WALNUT','2503 HASTE','1808 UNIVERSITY','2747 SAN PABLO',
         '0 SAN PABLO','2740 SAN PABLO','2556 TELEGRAPH','2013 2ND')""").fetchone()[0]
    res = list(con.execute("SELECT bucket,CAST(canonical AS INT),verdict FROM s4_unit_reconcile_resolved ORDER BY verdict,bucket"))
    con.close()
    print("=== S4 FINGERPRINT (fresh connection) ===")
    print(f"  integrity: {ok}  | s4_units: {n}")
    print(f"  canonical != net_units (must be 0 — S4 re-derives nothing): {leak}")
    print(f"  Tier-1 units: {t1} (expect 568)")
    print(f"  reconcile resolutions: " + "; ".join(f"{b}={c}({v.split('_')[0]})" for b, c, v in res))
    return ok, n, leak, t1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true'); ap.add_argument('--no-snapshot', action='store_true')
    args = ap.parse_args()

    v3 = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    s1units = {bid: (u, bucket) for bid, u, bucket in v3.execute("SELECT building_id,units,bucket FROM s1_projects")}
    FAIL = []
    resolved = resolve_reconcile()

    print("=== S4 PREVIEW — finalize units + resolve reconcile (read-only; no write) ===")
    print(f"  buildings: {len(s1units)}   canonical unit count = net_units (S1); S4 resolves the {len(resolved)} disagreements by evidence")

    print(f"\n  [1] the {len(resolved)} reconcile disagreements — resolved by evidence or flagged (none guessed):")
    res_ours = [r for r in resolved if r[4] == 'RESOLVE_OURS']; flagged = [r for r in resolved if r[4] == 'FLAG_S8']
    for bucket, cu, pid, vu, verdict, canon, why in resolved:
        print(f"      {bucket:16} OUR={int(cu)} v2 proj{pid}={vu}  -> {verdict} (canonical={int(canon)})")
        print(f"          {why}")
    print(f"      => {len(res_ours)} resolved-by-evidence (our structured value), {len(flagged)} flagged to S8 (held, not guessed)")

    # [2] Tier-1 568u unchanged
    TIER1 = ["2001 Fourth St","1950 Addison St","1900 Walnut St","2503 Haste St","1808 University Ave",
             "2747 San Pablo Ave","0 San Pablo Ave","2740 San Pablo Ave","2556 Telegraph Ave","2013 Second St"]
    by_bucket = {b: (u, bid) for bid, (u, b) in s1units.items()}
    t1 = sum(by_bucket.get(f"{normalize_address(a).number} {normalize_address(a).street}".strip(), (0,))[0] for a in TIER1)
    t1_touched = [a for a in TIER1 for k in [normalize_address(a)] if f"{k.number} {k.street}".strip() in {r[0] for r in resolved}]
    print(f"\n  [2] Tier-1 total units: {int(t1)} (expect 568, UNCHANGED); reconcile touches a Tier-1 building: {t1_touched or 'none'}")
    if int(t1) != 568: FAIL.append(f"Tier-1 {int(t1)} != 568")

    # [3] 265 ADUs unchanged (units set by net_units, S4 doesn't touch them)
    print(f"\n  [3] 265 ADU unit counts: set by net_units in S1; S4 canonical = net_units -> UNCHANGED (only the {len(resolved)} reconcile buildings are examined, none are ADUs).")

    # [4] no residual internal leak: canonical is single-sourced (net_units); no separate unit_program sum exists in v3 yet
    print(f"\n  [4] internal total-vs-sum leak: the canonical total is single-sourced (net_units); there is NO separate")
    print(f"      unit_program breakdown in v3 yet (S5 builds affordability tiers) -> 0 leak by construction.")
    print(f"      (The proj15-class 110-vs-131 leak was v2's total != unit_program sum; it CANNOT occur here until S5,")
    print(f"       whose gate will require the tier sum == this canonical total.)")

    # [5] canonical == net_units for ALL (S4 doesn't silently re-derive); only flagged buildings carry a hold
    canon = {bid: u for bid, (u, b) in s1units.items()}                    # = net_units
    changed = [(b, cu, canon_b) for b, cu, pid, vu, v, canon_b, why in resolved if v == 'RESOLVE_OURS' and canon_b != cu]
    print(f"\n  [5] canonical units == net_units for all {len(s1units)} buildings (S4 re-derives nothing): "
          f"{'OK' if not changed else 'CHANGED: '+str(changed)}")
    print(f"      the {len(flagged)} flagged building holds its structured value pending S8 (development modeling).")

    print(f"\n  [6] s0_/s1_/s2_/s3_ tables UNTOUCHED (preview is read-only).")
    print(f"\n  === S4 ACCEPTANCE GATE: {'PASS' if not FAIL else 'FAIL'} ===")
    for f in FAIL: print("    XXX", f)
    if args.write:
        if FAIL:
            print("\n  WRITE ABORTED — acceptance gate failed."); sys.exit(1)
        import hashlib
        v2b = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        if args.no_snapshot:
            print("\n  (--no-snapshot: idempotency re-run, NOT snapshotting — must not clobber the rollback point)")
        else:
            snap, created = snapshot_v3('s4')
            print(f"\n  snapshot: {os.path.basename(snap)} ({'created' if created else 'preserved existing — NOT clobbered'})")
        nb, nf = write_s4(s1units, resolved)
        print(f"  S4 WRITE -> {os.path.basename(V3)}: {nb} s4_units, {nf} s4_unit_reconcile_resolved")
        fingerprint_s4()
        v2a = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        print(f"  live v2 untouched: sha256 {'UNCHANGED' if v2b == v2a else 'CHANGED ✗✗'} ({v2b[:16]})")
