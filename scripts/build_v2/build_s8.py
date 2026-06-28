"""S8 — reconciliation matrix. SYNTHESIS, not re-derivation: gather every flagged finding the build
stages already produced into ONE durable, auditable artifact (`s8_reconciliation`). Each gathered row
traces to an existing `_reconcile`/`_overlap`/`_review` source row (basis COPIED, not recomputed); the
synthesized rows (multi-building pattern, UC measurement-basis, the soft scope items, the v2 cross-check)
are documented sourced facts / comparisons, clearly typed.

CORE DISCIPLINE: finding_types stay DISTINCT (date / stage / unit / apn / xaddr / multi_building /
measurement_basis / rhna_scope / entitlement_gap / crosscheck) — NEVER flattened into one bucket. The
gate's exact-count assertions (3 date / 33 stage / 6 unit / 13 apn / 22 xaddr / 1 multi-building / 4 UC)
are the key check: an off-by-N means a finding was dropped or double-gathered, and gathering all of them
is the matrix's whole job.

The cross-check substrate is the LIVE `berkeley_housing_v2.db` (sha d6a1a960…), opened READ-ONLY — it is
the comparison target, never written. s0–s7 untouched. Imports s0_keys + housing_predicates + gating +
housing_rules (housing_rules.cycle_for_date + s0_keys.normalize_address are genuinely CALLED — the date
reconciles get a cycle-shift annotation, the xaddr finds get an address-proximity annotation; the wiring
guard spies that they are invoked, not just imported. housing_predicates is bound for single-source
consistency but net_units is deliberately NOT called — S8 GATHERS units from s4, it does not re-derive them).
--preview is READ-ONLY.
"""
import sqlite3, sys, os, argparse
from collections import Counter
from datetime import date
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import s0_keys
from s0_keys import normalize_address
import housing_predicates  # single-source predicate module; net_units NOT called by design (gather, not re-derive)
from gating import snapshot_v3
import housing_rules as hr

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')  # READ-ONLY cross-check substrate
AS_OF = '2026-06-17'

# UC measurement-basis (4 residences, uc_project classification type 6). SOURCED facts from the read-only
# investigation: bed figures from project descriptions (UC), proj170 units from Anchor House FAQ (v2 doc
# 2178). NONE are in the v3 CPRA spine -> 0 v3 units at-risk; this documents the v2-vs-v3 difference and
# guards the ad hoc bed->unit numbers (550/750/556) from ever being asserted.
#   (proj, name, address, beds, beds_src, units, units_src_or_None, disposition)
UC_RESIDENCES = [
    (170, 'Anchor House', '1950 Oxford', 772, 'UC / Anchor House FAQ (v2 doc 2178)', 244,
     'Anchor House FAQ (v2 doc 2178)', 'sourced_both'),
    (165, 'Bancroft-Fulton', '2200 Bancroft', 1625, 'project description (UC)', None, None, 'pending_uc_conversion'),
    (171, 'Channing-Bowditch', '2400 Bowditch', 1500, 'project description (UC)', None, None, 'pending_uc_conversion'),
    (177, "People's Park", '2556 Haste', 1113, 'project description (UC)', None, None, 'pending_uc_conversion'),
]


def _ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)


def gather():
    """Gather all findings into matrix tuples:
       (finding_type, subject, v3_value, other_value, other_source, disagreement, magnitude, disposition, basis)."""
    v3 = _ro(V3); v2 = _ro(V2)
    rows = []

    # --- date_reconcile (s2_date_reconcile, live count) — CALLS hr.cycle_for_date to annotate cycle-shift ---
    for permit, field, cpra, v2d in v3.execute("SELECT permit,field,cpra_date,v2_date FROM s2_date_reconcile"):
        gap = abs((date.fromisoformat(v2d) - date.fromisoformat(cpra)).days)
        cc_c, cc_v = hr.cycle_for_date(date.fromisoformat(cpra)), hr.cycle_for_date(date.fromisoformat(v2d))
        yr_shift = cpra[:4] != v2d[:4]
        cyc_shift = cc_c != cc_v
        mag = f"{gap}d; reporting-year {cpra[:4]}->{v2d[:4]}" + (f"; CALENDAR_CYCLE {cc_c}->{cc_v}" if cyc_shift else "")
        disp = "resolved_ours_evidence" + ("|s9_year_watch" if yr_shift else "")
        rows.append(('date_reconcile', permit, f"CPRA {cpra} (is_inferred=0)", f"v2 {v2d}", 'v2',
                     f"{field} date disagreement", mag, disp,
                     "v3 uses the CPRA structured finaled date (is_inferred=0); v2 later/likely re-recorded -> "
                     "S9 year-watch (the year shift moves the completion's APR table-A year / cycle)"))

    # --- stage_reconcile (s3_stage_reconcile, live count) — held, never auto-resolved ---
    for bid, pid, v1s, ds, direction in v3.execute(
            "SELECT building_id,v2_project_id,v1_stage,derived_stage,direction FROM s3_stage_reconcile"):
        rows.append(('stage_reconcile', f"building {bid} / proj{pid}", ds, v1s, 'v1',
                     f"v1 stage '{v1s}' vs event-derived '{ds}'", direction, 'held_flagged',
                     "event-derived stage (s3, 0 asserted) vs v1's asserted stage; held for S8/S9, not auto-resolved"))

    # --- unit_reconcile (s4_unit_reconcile_resolved, live count) — 5 resolved + 1 FLAG_S8 ---
    for bucket, ours, pid, v2u, verdict, canon, evidence in v3.execute(
            "SELECT bucket,our_units,v2_project_id,v2_units,verdict,canonical,evidence FROM s4_unit_reconcile_resolved"):
        disp = 'resolved_ours_evidence' if verdict == 'RESOLVE_OURS' else 'held_flagged'
        rows.append(('unit_reconcile', f"{bucket} / proj{pid}", f"{ours:.0f}", f"{v2u:.0f}", 'v2',
                     f"unit count {ours:.0f} vs v2 {v2u:.0f}", f"{ours - v2u:+.0f}u", disp, evidence))

    # --- apn_overlap (s1_apn_overlap, live count) — kept CREATE, flagged ---
    for bid, pid in v3.execute("SELECT building_id,v2_project_id FROM s1_apn_overlap"):
        rows.append(('apn_overlap', f"building {bid} / proj{pid}", "kept CREATE", f"shares parcel w/ proj{pid}", 'v2',
                     "CREATE building shares a different-address parcel with another project", None, 'held_flagged',
                     "kept as a CREATE (distinct address); apn overlap flagged for review, NOT merged"))

    # --- xaddr_review (s1_xaddr_review, live count) — CALLS normalize_address to annotate proximity ---
    for bucket, cu, pid, v2addr, v2u, via in v3.execute(
            "SELECT bucket,cpra_units,v2_project_id,v2_addr,v2_units,via FROM s1_xaddr_review"):
        same = normalize_address(bucket) == normalize_address(v2addr)
        rows.append(('xaddr_review', f"{bucket} / proj{pid}", f"{bucket} ({cu}u)", f"{v2addr} ({v2u}u)", 'v2',
                     f"near-address family match ({via})", f"normalized-equal={same}", 'benign_match',
                     "benign near-address family match; buildings kept distinct (not a merge)"))

    # --- multi_building_development (synthesized: the s4 FLAG_S8 subject as a reusable PATTERN) ---
    for bucket, ours, v2u, evidence in v3.execute(
            "SELECT bucket,our_units,v2_units,evidence FROM s4_unit_reconcile_resolved WHERE verdict='FLAG_S8'"):
        rows.append(('multi_building_development', f"{bucket} / proj179 (Logan Park)",
                     f"per-building MAX {ours:.0f}", f"development total {v2u:.0f}", 'v2',
                     "development spans multiple permit-families; per-building MAX under-counts the development total",
                     f"{ours:.0f} vs {v2u:.0f} ({v2u - ours:+.0f})", 'category_pattern',
                     evidence + " | PATTERN: count a multi-permit development at development scope; a v3 scan "
                     "for v2_total>1.3x per-building MAX found exactly 1 member (this one)"))

    # --- measurement_basis (4 UC residences; sourced facts, 0 in v3 spine) ---
    for proj, name, addr, beds, beds_src, units, units_src, disp in UC_RESIDENCES:
        if units is not None:
            uval = f"units={units} (sourced)"
            basis = (f"units={units} apartments SOURCED ({units_src}); beds={beds} SOURCED ({beds_src}); "
                     f"each measure labeled by basis; the 772 beds-as-units NEVER carried")
        else:
            uval = "units=NULL (pending_uc_conversion)"
            basis = (f"beds={beds} SOURCED ({beds_src}); units=NULL, unit_basis=pending_uc_conversion "
                     f"(size KNOWN in beds; only UC's authoritative bed->unit conversion is missing — "
                     f"DISTINCT from needs_acquisition); the ad hoc unit number is REJECTED")
        rows.append(('measurement_basis', f"proj{proj} {name} ({addr})", "0 (not in CPRA spine)",
                     "v2 carried bed-derived units", 'v2',
                     "beds-vs-units measurement basis (UC student housing, exempt from CPRA)",
                     f"beds={beds}; {uval}", disp, basis))

    # --- rhna_scope_question (soft, text-only — Table B absent from the mirror) ---
    rows.append(('rhna_scope_question', "6th-cycle RHNA progress (BP-credit)",
                 "cumulative 421bldg/1,792u (CY2024); 648bldg/2,419u (CY2025)", "city 492 / 503", 'city',
                 "BP-credit magnitude does not reconcile to the city's reported figure",
                 "1,792u vs 492; 2,419u vs 503", 'scope_question_s9',
                 "BP is the correct milestone (S7 fix; was CO); Table B is ABSENT from the CKAN mirror so this is "
                 "soft/text-only; scope axes (annual-vs-cumulative / affordable-only / coverage universe) -> S9, do NOT force"))

    # --- entitlement_date_gap (soft pointer — DISTINCT from the 33 stage reconciles; NOT 757 rows) ---
    rows.append(('entitlement_date_gap', "discretionary entitlement DATES (acquisition queue)",
                 "spine lacks dated entitlement events", "—", 'v3',
                 "the entitlement-DATE gap (S3 finding) is a missing-DATES/acquisition issue, DISTINCT from "
                 "stage over-assertion (the 33)", "soft (1 pointer row, not row-materialized)", 'scope_question',
                 "the .txt corpus does not cover the CPRA spine -> acquire entitlement dates; kept as its own "
                 "finding_type so it is never conflated with the 33 stage_reconcile rows"))

    # --- crosscheck_summary (v2-vs-v3 headline; computed comparison, clearly typed; v2 READ-ONLY) ---
    o2 = lambda s: (v2.execute(s).fetchone() or [None])[0]
    o3 = lambda s: (v3.execute(s).fetchone() or [None])[0]
    v2_proj = o2("SELECT COUNT(*) FROM v_projects_flat")
    v2_co = o2("SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date IS NOT NULL")
    v2_u = o2("SELECT CAST(SUM(total_units) AS INT) FROM v_projects_flat")
    v3_b = o3("SELECT COUNT(*) FROM s1_projects")
    v3_co = o3("SELECT COUNT(*) FROM s3_stage WHERE stage='completed'")
    v3_u = o3("SELECT CAST(SUM(units) AS INT) FROM s4_units")
    v3_cited = o3("SELECT COUNT(DISTINCT v2_project_ref) FROM s5_affordability WHERE population='pipeline'")
    v3_unbacked = o3("SELECT COUNT(*) FROM s6_confidence WHERE confidence='high' AND basis NOT LIKE '%structured%' "
                     "AND basis NOT LIKE '%event-derived%' AND basis NOT LIKE '%typed%' AND basis NOT LIKE '%reconciled%'")
    uc_v2_units = 2628  # 550+772+750+556 (the v2 UC bed-derived 'units'); all excluded from v3
    cc = [
        ("projects/buildings", f"{v3_b}", f"{v2_proj}", "per-building granularity + ADU-tail recovery", 'population_difference'),
        ("completions", f"{v3_co}", f"{v2_co}", "completions RECOVERED (265 ADUs, 154 completed)", 'completions_recovered'),
        ("Σ units", f"{v3_u}", f"{v2_u}", "DIFFERENT POPULATIONS: v2 includes pipeline towers + UC beds; v3 is the "
         "built/permitted spine net_units — compare like-for-like in S9, never these two totals", 'population_difference'),
        ("affordability cited", f"{v3_cited} real", f"704 stub-cited", "v2 fabrication STRIPPED (9 typed-doc citations stand)", 'fabrication_stripped'),
        ("confidence high-without-backing", f"{v3_unbacked}", "blanket-high", "confidence EARNED per fact (migration's blanket-high impossible)", 'confidence_earned'),
        ("UC bed-unit basis", "0 in spine", f"{uc_v2_units} v2 bed-derived units", "measurement-basis bucket: v3 excludes all 4 UC residences", 'measurement_basis'),
    ]
    for metric, v3v, v2v, story, disp in cc:
        rows.append(('crosscheck_summary', metric, v3v, v2v, 'v2', story, None, disp,
                     "v2-vs-v3 headline comparison (berkeley_housing_v2.db read-only, sha d6a1a960)"))

    v3.close(); v2.close()
    return rows


# the gathered finding_types whose count MUST equal their live source table exactly (drop/double-gather lock)
SOURCE_COUNTS = {
    'date_reconcile': ('s2_date_reconcile', 3),
    'stage_reconcile': ('s3_stage_reconcile', 33),
    'unit_reconcile': ('s4_unit_reconcile_resolved', 6),
    'apn_overlap': ('s1_apn_overlap', 13),
    'xaddr_review': ('s1_xaddr_review', 22),
}
SYNTH_COUNTS = {'multi_building_development': 1, 'measurement_basis': 4,
                'rhna_scope_question': 1, 'entitlement_date_gap': 1}


def write_s8(rows):
    """Persist s8_reconciliation into v3 (s0_-s7_ untouched). Idempotent."""
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s8_reconciliation;
      DROP TABLE IF EXISTS s8_meta;
      CREATE TABLE s8_reconciliation(
        finding_id INTEGER PRIMARY KEY, finding_type TEXT, subject TEXT, v3_value TEXT,
        other_value TEXT, other_source TEXT, disagreement TEXT, magnitude TEXT,
        disposition TEXT, basis TEXT);
      CREATE INDEX ix_s8_type ON s8_reconciliation(finding_type);
      CREATE INDEX ix_s8_disp ON s8_reconciliation(disposition);
      CREATE TABLE s8_meta(key TEXT, value TEXT);
    """)
    con.executemany("INSERT INTO s8_reconciliation(finding_type,subject,v3_value,other_value,other_source,"
                    "disagreement,magnitude,disposition,basis) VALUES(?,?,?,?,?,?,?,?,?)", rows)
    meta = [('stage', 'S8'), ('as_of', AS_OF), ('findings', str(len(rows))),
            ('rule', 'gather flagged findings into one matrix; finding_types DISTINCT; nothing re-derived'),
            ('crosscheck', 'berkeley_housing_v2.db sha d6a1a960 (READ-ONLY)'),
            ('key_module', 's0_keys.py + housing_predicates.py + gating.py + housing_rules')]
    con.executemany("INSERT INTO s8_meta VALUES(?,?)", meta)
    con.commit(); con.close()
    return len(rows)


def fingerprint_s8():
    con = _ro(V3)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    n = con.execute("SELECT COUNT(*) FROM s8_reconciliation").fetchone()[0]
    by_type = dict(con.execute("SELECT finding_type,COUNT(*) FROM s8_reconciliation GROUP BY 1"))
    # exact-count check vs live source tables
    drift = []
    for ft, (src, _) in SOURCE_COUNTS.items():
        live = con.execute(f"SELECT COUNT(*) FROM {src}").fetchone()[0]
        got = by_type.get(ft, 0)
        if got != live: drift.append(f"{ft}: gathered {got} != source {src} {live}")
    pending = con.execute("SELECT COUNT(*) FROM s8_reconciliation WHERE disposition='pending_uc_conversion'").fetchone()[0]
    needsacq = con.execute("SELECT COUNT(*) FROM s8_reconciliation WHERE disposition='needs_acquisition'").fetchone()[0]
    types = con.execute("SELECT COUNT(DISTINCT finding_type) FROM s8_reconciliation").fetchone()[0]
    con.close()
    print("=== S8 FINGERPRINT (fresh connection) ===")
    print(f"  integrity: {ok}  | s8_reconciliation findings: {n}  | distinct finding_types: {types}")
    print(f"  per-type counts: {by_type}")
    print(f"  exact-count vs live source tables: {'ALL MATCH' if not drift else 'DRIFT -> ' + '; '.join(drift)}")
    print(f"  pending_uc_conversion: {pending} (the 3 UC beds-only) | needs_acquisition: {needsacq} (must be 0 — distinct disposition)")
    return ok, n, drift


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true'); ap.add_argument('--no-snapshot', action='store_true')
    args = ap.parse_args()

    rows = gather()
    FAIL = []
    bt = Counter(r[0] for r in rows)
    print("=== S8 PREVIEW — reconciliation matrix (read-only; no write) ===")
    print(f"  findings gathered: {len(rows)}  | distinct finding_types: {len(bt)}")

    print(f"\n  [1] per finding_type (DISTINCT — never one bucket):")
    for ft in ('date_reconcile', 'stage_reconcile', 'unit_reconcile', 'apn_overlap', 'xaddr_review',
               'multi_building_development', 'measurement_basis', 'rhna_scope_question',
               'entitlement_date_gap', 'crosscheck_summary'):
        print(f"      {ft:28} {bt.get(ft, 0)}")

    # [2] THE KEY GATE — gathered counts == live source-table counts (drop/double-gather)
    print(f"\n  [2] EXACT-COUNT vs live source tables (off-by-N = a finding dropped or double-gathered):")
    v3 = _ro(V3)
    for ft, (src, expect) in SOURCE_COUNTS.items():
        live = v3.execute(f"SELECT COUNT(*) FROM {src}").fetchone()[0]
        got = bt.get(ft, 0)
        ok = (got == live == expect)
        print(f"      {ft:28} gathered {got} == {src} {live} (expect {expect}) {'OK' if ok else 'XXX'}")
        if not ok: FAIL.append(f"{ft} gathered {got} != source {live}/{expect}")
    for ft, expect in SYNTH_COUNTS.items():
        got = bt.get(ft, 0)
        print(f"      {ft:28} {got} (expect {expect}) {'OK' if got == expect else 'XXX'}")
        if got != expect: FAIL.append(f"{ft} {got} != {expect}")
    v3.close()

    # [3] pending_uc_conversion DISTINCT from needs_acquisition
    uc = [r for r in rows if r[0] == 'measurement_basis']
    pend = [r for r in uc if r[7] == 'pending_uc_conversion']
    both = [r for r in uc if r[7] == 'sourced_both']
    nacq = [r for r in rows if r[7] == 'needs_acquisition']
    print(f"\n  [3] UC measurement_basis: {len(uc)} (proj170 sourced_both={len(both)}; pending_uc_conversion={len(pend)})")
    print(f"      pending_uc_conversion is DISTINCT from needs_acquisition (needs_acquisition rows here: {len(nacq)} — must be 0)")
    if len(uc) != 4: FAIL.append(f"UC measurement_basis {len(uc)} != 4")
    if len(pend) != 3: FAIL.append(f"pending_uc_conversion {len(pend)} != 3")
    if len(both) != 1: FAIL.append(f"sourced_both {len(both)} != 1")
    if nacq: FAIL.append(f"{len(nacq)} rows used needs_acquisition (must be the distinct pending_uc_conversion)")

    # [4] distinctions preserved
    print(f"\n  [4] distinctions preserved: date(3) vs stage(33) vs unit(6) vs apn(13) vs xaddr(22) vs "
          f"multi_building(1) vs measurement_basis(4) — {len(bt)} distinct types, not flattened")
    if len(bt) < 8: FAIL.append(f"only {len(bt)} finding_types — distinctions flattened")

    # [5] sample rows per type
    print(f"\n  [5] sample finding rows (one per type):")
    seen = set()
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            print(f"      [{r[0]}] {r[1]} | v3={r[2]} vs {r[4]}={r[3]} | {r[8]}")

    print(f"\n  [6] nothing re-derived (basis copied from source rows) · v2 read-only (sha d6a1a960) · s0_-s7_ untouched.")
    print(f"\n  === S8 ACCEPTANCE GATE: {'PASS' if not FAIL else 'FAIL'} ===")
    for f in FAIL: print("    XXX", f)

    if args.write:
        if FAIL:
            print("\n  WRITE ABORTED — acceptance gate failed."); sys.exit(1)
        import hashlib
        v2b = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        if args.no_snapshot:
            print("\n  (--no-snapshot: idempotency re-run, NOT snapshotting — must not clobber the rollback point)")
        else:
            snap, created = snapshot_v3('s8')
            print(f"\n  snapshot: {os.path.basename(snap)} ({'created' if created else 'preserved existing — NOT clobbered'})")
        nr = write_s8(rows)
        print(f"  S8 WRITE -> {os.path.basename(V3)}: {nr} s8_reconciliation findings")
        fingerprint_s8()
        v2a = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        print(f"  live v2 untouched: sha256 {'UNCHANGED' if v2b == v2a else 'CHANGED XX'} ({v2b[:16]})")
