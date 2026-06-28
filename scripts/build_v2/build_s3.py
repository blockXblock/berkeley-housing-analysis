"""S3 — derive each building's STAGE from its events (never from a v1 status string).

================================ WHAT S3 TEACHES ================================
Stage is the migration's original sin: it set a project's lifecycle position from a v1 status STRING
and stamped it `confidence=high`, so 757 projects claimed "entitled+" with no event behind them. S3
inverts that — stage is COMPUTED from the dated events S2 materialized, and a building can only reach
a stage an event justifies. Where there's no event, the honest floor is "pipeline", never an assertion.

  co_issued (evidentiary)        -> completed
  building_permit_issued, no CO  -> permitted   (a BP was issued; we have no construction-start event,
                                                  so 'permitted' is the evidence floor, not under_construction)
  entitlement_approved, no BP    -> entitled
  none of the above              -> pipeline    (the honest floor — no event, no asserted stage)

v1's old status enters ONLY as a CROSS-CHECK (S8): where the derived stage disagrees with v1, we record
the disagreement and trust the EVENTS, never v1. The disagreement set is the proof the migration over-asserted.
================================================================================

Imports the shared address canon from s0_keys (for the Tier-1 lookup). --preview is READ-ONLY.
S3 derives stage from s2_events only; it does not need the housing predicates (no CPRA re-read).
"""
import sqlite3, sys, os, argparse
from collections import defaultdict, Counter
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from s0_keys import normalize_address
from gating import snapshot_v3                          # the SHARED snapshot helper (refuses to clobber)

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
V3 = os.path.join(ROOT, 'databases', 'berkeley_housing_v3.db')
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
AS_OF = '2026-06-17'

# stage ordering for cross-check direction (v2-higher = over-assertion; v2-lower = v2 under-stated)
RANK = {'pipeline': 0, 'pre_application': 0, 'in_review': 1, 'entitled': 2, 'permitted': 3,
        'under_construction': 4, 'completed': 5, 'stalled': 1, 'withdrawn': 1}


def derive_stage(event_types):
    """The ONLY stage rule — computed from events, justified by the event named."""
    if 'co_issued' in event_types:
        return 'completed', 'co_issued'
    if 'building_permit_issued' in event_types:
        return 'permitted', 'building_permit_issued'
    if 'entitlement_approved' in event_types:
        return 'entitled', 'entitlement_approved'
    return 'pipeline', None                          # honest floor: no event, no asserted stage


def derive_all():
    c = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    ev = defaultdict(set)
    for bid, et in c.execute("SELECT building_id, event_type FROM s2_events"):
        ev[bid].add(et)
    rows = {}   # building_id -> dict(stage, justified_by, bucket, v2_ids)
    for bid, bucket, v2ids in c.execute("SELECT building_id, bucket, v2_project_ids FROM s1_projects"):
        st, just = derive_stage(ev.get(bid, set()))
        rows[bid] = dict(stage=st, justified_by=just, bucket=bucket,
                         v2_ids=[int(x) for x in (v2ids or '').split('|') if x])
    c.close()
    return rows, ev


def v1_stages():
    """v1's status, as carried into v2 — the CROSS-CHECK source (never an input to the derivation)."""
    c = sqlite3.connect(f'file:{V2}?mode=ro', uri=True)
    out = {pid: code for pid, code in c.execute(
        "SELECT p.id, vst.code FROM projects p LEFT JOIN vocabulary_stage_types vst "
        "ON vst.id=p.current_stage_type_id WHERE p.merged_into_id IS NULL")}
    c.close()
    return out


def reconcile_vs_v1(rows, v1):
    """For buildings linked to a v2 project, compare derived stage to v1's status. Returns the
    disagreement list (building_id, v2_id, v1_stage, derived_stage, direction)."""
    findings = []
    for bid, r in rows.items():
        for pid in r['v2_ids']:
            v1s = v1.get(pid)
            if v1s is None:
                continue
            d = r['stage']
            if RANK.get(v1s, 0) == RANK.get(d, 0):
                continue                            # same rung -> agree
            direction = 'v1_over_asserts' if RANK.get(v1s, 0) > RANK.get(d, 0) else 'v1_under (events show more)'
            findings.append((bid, pid, v1s, d, direction))
    return findings


def write_s3(rows, findings):
    """Persist s3_stage + s3_stage_reconcile into v3 (s0_/s1_/s2_ untouched). Idempotent: DROP+rebuild."""
    con = sqlite3.connect(V3)
    con.executescript("""
      DROP TABLE IF EXISTS s3_stage;
      DROP TABLE IF EXISTS s3_stage_reconcile;
      DROP TABLE IF EXISTS s3_meta;
      CREATE TABLE s3_stage(building_id INTEGER PRIMARY KEY, stage TEXT, justified_by TEXT, bucket TEXT);
      CREATE INDEX ix_s3_stage ON s3_stage(stage);
      CREATE TABLE s3_stage_reconcile(building_id INT, v2_project_id INT, v1_stage TEXT, derived_stage TEXT, direction TEXT);
      CREATE TABLE s3_meta(key TEXT, value TEXT);
    """)
    con.executemany("INSERT INTO s3_stage VALUES(?,?,?,?)",
                    [(bid, r['stage'], r['justified_by'], r['bucket']) for bid, r in rows.items()])
    con.executemany("INSERT INTO s3_stage_reconcile VALUES(?,?,?,?,?)", findings)
    dist = Counter(r['stage'] for r in rows.values())
    meta = [('stage', 'S3'), ('as_of', AS_OF), ('buildings', str(len(rows))),
            ('completed', str(dist['completed'])), ('permitted', str(dist['permitted'])),
            ('entitled', str(dist['entitled'])), ('pipeline', str(dist['pipeline'])),
            ('asserted_stages', '0'), ('stage_disagreements', str(len(findings))),
            ('key_module', 's0_keys.py + housing_predicates.py + gating.py')]
    con.executemany("INSERT INTO s3_meta VALUES(?,?)", meta)
    con.commit(); con.close()
    return len(rows), len(findings)

def fingerprint_s3():
    con = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    dist = dict(con.execute("SELECT stage,COUNT(*) FROM s3_stage GROUP BY stage"))
    asserted = con.execute("SELECT COUNT(*) FROM s3_stage WHERE stage<>'pipeline' AND justified_by IS NULL").fetchone()[0]
    nrec = con.execute("SELECT COUNT(*) FROM s3_stage_reconcile").fetchone()[0]
    comp_pipe = con.execute("SELECT COUNT(*) FROM s3_stage_reconcile WHERE v1_stage='completed' AND derived_stage='pipeline'").fetchone()[0]
    # co_issued <-> completed 1:1
    co = {r[0] for r in con.execute("SELECT building_id FROM s2_events WHERE event_type='co_issued'")}
    comp = {r[0] for r in con.execute("SELECT building_id FROM s3_stage WHERE stage='completed'")}
    con.close()
    print("=== S3 FINGERPRINT (fresh connection) ===")
    print(f"  integrity: {ok}  | distribution: {dist}")
    print(f"  asserted stages (non-pipeline w/ no justifying event): {asserted} (must be 0)")
    print(f"  co_issued <-> completed 1:1: {co == comp}  ({len(comp)})")
    print(f"  s3_stage_reconcile (S8): {nrec}  incl. {comp_pipe} v1=completed->pipeline")
    return ok, dist, asserted, nrec

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--write', action='store_true'); ap.add_argument('--no-snapshot', action='store_true')
    args = ap.parse_args()

    rows, ev = derive_all()
    v1 = v1_stages()
    findings = reconcile_vs_v1(rows, v1)
    FAIL = []

    print("=== S3 PREVIEW — stage derived from events (read-only; no write) ===")
    print(f"  buildings: {len(rows)}   (stage computed from s2_events; v1 status used only as cross-check)")

    dist = Counter(r['stage'] for r in rows.values())
    print(f"\n  [1] stage distribution (pure event-derivation):")
    for st in ('completed', 'permitted', 'entitled', 'pipeline'):
        print(f"      {st:16} {dist.get(st,0)}")

    # [2] every non-pipeline stage has a justifying event; pipeline = no events (honest floor)
    asserted = [bid for bid, r in rows.items() if r['stage'] != 'pipeline' and not r['justified_by']]
    pipeline_with_events = [bid for bid, r in rows.items() if r['stage'] == 'pipeline' and ev.get(bid)]
    print(f"\n  [2] traceability: stages with NO justifying event (asserted): {len(asserted)} (must be 0)")
    print(f"      pipeline-floor buildings (no event at all): {dist.get('pipeline',0)}  | pipeline-but-has-events (bug?): {len(pipeline_with_events)}")
    if asserted: FAIL.append(f"{len(asserted)} asserted stages")
    if pipeline_with_events: FAIL.append(f"{len(pipeline_with_events)} pipeline buildings that have events")

    # [3] Tier-1 + the 265 recovered ADUs -> completed
    TIER1 = ["2001 Fourth St","1950 Addison St","1900 Walnut St","2503 Haste St","1808 University Ave",
             "2747 San Pablo Ave","0 San Pablo Ave","2740 San Pablo Ave","2556 Telegraph Ave","2013 Second St"]
    bybucket = {r['bucket']: r for r in rows.values()}
    co_bids = {bid for bid in rows if 'co_issued' in ev.get(bid, set())}
    completed_bids = {bid for bid, r in rows.items() if r['stage'] == 'completed'}
    print(f"\n  [3] co_issued <-> completed is 1:1 (every completion event-justified): {co_bids == completed_bids} ({len(completed_bids)})")
    if co_bids != completed_bids: FAIL.append("co_issued set != completed set")
    t1ok = sum(1 for a in TIER1 for k in [normalize_address(a)] if bybucket.get(f"{k.number} {k.street}".strip(), {}).get('stage') == 'completed')
    print(f"      Tier-1 completions at 'completed': {t1ok}/10")
    if t1ok != 10: FAIL.append(f"Tier-1 only {t1ok}/10 at completed")
    # recovered ADUs staged BY EVIDENCE — finaled->completed, BP-only->permitted, no-date->pipeline (not all forced complete)
    c = sqlite3.connect(f'file:{V3}?mode=ro', uri=True)
    adu = [bid for (bid,) in c.execute("SELECT building_id FROM s1_projects WHERE units<=2 AND via IS NULL")]
    c.close()
    print(f"      recovered small/ADU CREATE buildings ({len(adu)}) staged by evidence: {dict(Counter(rows[b]['stage'] for b in adu))}")

    # [4] v1 CROSS-CHECK — TWO DISTINCT findings, do not conflate:
    over = [f for f in findings if f[4] == 'v1_over_asserts']
    under = [f for f in findings if f[4].startswith('v1_under')]
    comp_pipe = [f for f in over if f[2] == 'completed' and f[3] == 'pipeline']
    print(f"\n  [4] v1 cross-check -> s3_stage_reconcile (S8 queue); v1 NEVER trusted:")
    print(f"      FINDING A (stage-label over-assertion): {len(findings)} stage disagreements ({len(over)} v1-over, {len(under)} v1-under).")
    print(f"        incl. {len(comp_pipe)} where v1='completed' but events give 'pipeline' (v2 completions we can't corroborate):")
    for f in comp_pipe[:5]:
        print(f"          proj{f[1]} ({rows[f[0]]['bucket']}): v1=completed -> events=pipeline")
    # FINDING B: the migration's '757 entitled+ with no entitlement event' — reframed against the events.
    v2 = sqlite3.connect(f'file:{V2}?mode=ro', uri=True)
    has_ent = {r[0] for r in v2.execute("SELECT DISTINCT pe.project_id FROM project_events pe "
              "JOIN vocabulary_event_types vt ON vt.id=pe.event_type_id WHERE vt.code='entitlement_approved'")}
    v2.close()
    a757 = {pid for pid, s in v1.items() if RANK.get(s, 0) >= 2 and pid not in has_ent}
    pid2der = defaultdict(set)
    for bid, r in rows.items():
        for pid in r['v2_ids']: pid2der[pid].add(r['stage'])
    backed = sum(1 for p in a757 if pid2der.get(p, set()) & {'completed', 'permitted'})
    notbuilt = sum(1 for p in a757 if p not in pid2der)
    unsup = len(a757) - backed - notbuilt
    print(f"      FINDING B (entitlement-EVENT gap, SEPARATE — the S2 acquisition queue): {len(a757)} v1-entitled+ lack an")
    print(f"        entitlement event. Re-derived from events: {backed} are event-backed at permitted/completed (v1")
    print(f"        under-stated), {notbuilt} entitled-not-yet-in-spine, only {unsup} unsupported by any event.")
    print(f"      -> 757 = missing entitlement DATES (acquisition); the stage-label over-assertion is the {len(findings)} above. Distinct.")

    # [5] entitlement-gap nuance: BP/CO present but no entitlement -> permitted/completed (NOT mis-flagged)
    bp_or_co_no_ent = [bid for bid in rows if ('building_permit_issued' in ev.get(bid,set()) or 'co_issued' in ev.get(bid,set())) and 'entitlement_approved' not in ev.get(bid,set())]
    mis = [bid for bid in bp_or_co_no_ent if rows[bid]['stage'] not in ('permitted','completed')]
    print(f"\n  [5] entitlement-gap nuance: buildings with BP/CO but no entitlement event: {len(bp_or_co_no_ent)}")
    print(f"      of those, mis-staged (NOT permitted/completed): {len(mis)} (must be 0 — entitlement absence is the S2 gap, not an S3 stage)")
    if mis: FAIL.append(f"{len(mis)} entitlement-gap buildings mis-staged")

    print(f"\n  [6] s0_/s1_/s2_ tables UNTOUCHED (preview is read-only).")
    print(f"\n  === S3 ACCEPTANCE GATE: {'PASS' if not FAIL else 'FAIL'} ===")
    for f in FAIL:
        print("    XXX", f)
    if args.write:
        if FAIL:
            print("\n  WRITE ABORTED — acceptance gate failed."); sys.exit(1)
        import hashlib
        v2b = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        if args.no_snapshot:
            print("\n  (--no-snapshot: idempotency re-run, NOT snapshotting — must not clobber the rollback point)")
        else:
            snap, created = snapshot_v3('s3')
            print(f"\n  snapshot: {os.path.basename(snap)} ({'created' if created else 'preserved existing — NOT clobbered'})")
        nb, nf = write_s3(rows, findings)
        print(f"  S3 WRITE -> {os.path.basename(V3)}: {nb} s3_stage, {nf} s3_stage_reconcile")
        fingerprint_s3()
        v2a = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
        print(f"  live v2 untouched: sha256 {'UNCHANGED' if v2b == v2a else 'CHANGED ✗✗'} ({v2b[:16]})")
