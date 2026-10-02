#!/usr/bin/env python3
"""derive_inspection_events.py — turn 47,413 inspection rows into stage-transition events.

WHY. v2's stage vocabulary encodes the whole sequence John describes, but the transition DATA is
sparse: of 1,099 projects only 17 carry the full chain application -> entitlement -> BP -> CO, and
`construction_start_observed` covers just 18 projects. Two event types sit at zero rows despite the
evidence being on disk since 2026-05: `first_inspection_observed` and `final_inspection_passed`.
`load_inspections.py` deliberately loaded the raw rows and wrote nothing derived, leaving this as a
separate gated step. This is that step.

WHAT IT DOES, and does NOT.
  * `first_inspection_observed` — ONE per project, dated at its earliest CONDUCTED inspection.
    Semantics: construction observably started. Linked to the permit that carried that inspection.
  * `final_inspection_passed` — ONE per permit holding an APPROVED `Building 1200 Building Final`.
    Semantics: that permit's work passed its final.
  * It does NOT touch completion dates. Deriving `co_issued_date` from a Building Final is a
    SEPARATE, ADR-changing step (ADR-001/002) and is deliberately excluded.
  * It does NOT change `current_stage_type_id` unless --with-stage is passed, and that is reported
    separately so the stage move can be gated on its own.

CONDUCTED vs NOT. An inspection with result Cancelled / Site Cancellation / Rescheduled was never
performed -- nobody attended -- so it is NOT evidence that construction started. Only Approved,
Partially Approved, Approved with Conditions, Disapproved, Approve and Partial count: a DISAPPROVED
inspection still means an inspector stood on the site.

Append-only and idempotent: an event is skipped if one of the same type already exists for that
project/permit, so re-running adds nothing.

Usage:  python scripts/migration/derive_inspection_events.py [--commit] [--with-stage]
"""
import argparse
import collections
import datetime
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "databases/berkeley_housing_v2.db"

EV_FIRST_INSPECTION = 28        # first_inspection_observed
EV_FINAL_PASSED = 29            # final_inspection_passed
STAGE_UNDER_CONSTRUCTION = 5
STAGE_PERMITTED = 4
CONF_HIGH = 1
OBSERVED_BY = "derive_inspection_events@2026-09-25"
SOURCE_URL = "Accela inspection records (harvester) -> v2.inspections"

CONDUCTED = ("Approved", "Partially Approved", "Approved with Conditions",
             "Disapproved", "Approve", "Partial")
PASSED = ("Approved", "Approved with Conditions", "Approve")
BUILDING_FINAL = "BUILDING 1200 BUILDING FINAL"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--with-stage", action="store_true",
                    help="also move 'permitted' projects with a first inspection to under_construction")
    ap.add_argument("--db", default=str(V2))
    args = ap.parse_args()

    db = sqlite3.connect(args.db)
    db.execute("PRAGMA foreign_keys=ON")
    qs = ",".join("?" * len(CONDUCTED))

    # --- first conducted inspection per project ----------------------------------------
    firsts = list(db.execute(f"""
        SELECT i.project_id, MIN(i.inspection_date) AS first_date
        FROM inspections i
        WHERE i.project_id IS NOT NULL AND IFNULL(i.inspection_date,'') <> ''
          AND i.result IN ({qs})
        GROUP BY i.project_id""", CONDUCTED))
    have_first = {p for (p,) in db.execute(
        "SELECT DISTINCT project_id FROM project_events WHERE event_type_id=?", (EV_FIRST_INSPECTION,))}
    firsts = [(p, d) for p, d in firsts if p not in have_first]

    # --- approved Building Final per permit ---------------------------------------------
    pqs = ",".join("?" * len(PASSED))
    finals = list(db.execute(f"""
        SELECT i.project_id, i.permit_number, MIN(i.inspection_date) AS passed_date
        FROM inspections i
        WHERE i.project_id IS NOT NULL AND IFNULL(i.inspection_date,'') <> ''
          AND UPPER(i.type_code) LIKE '{BUILDING_FINAL}%'
          AND i.result IN ({pqs})
        GROUP BY i.project_id, i.permit_number""", PASSED))
    permit_id = {n: i for i, n in db.execute(
        "SELECT id, permit_number FROM permits WHERE permit_number IS NOT NULL")}
    have_final = {(p, pm) for p, pm in db.execute(
        f"""SELECT e.project_id, e.permit_id FROM project_events e WHERE e.event_type_id=?""",
        (EV_FINAL_PASSED,))}
    finals = [(p, n, d) for p, n, d in finals if (p, permit_id.get(n)) not in have_final]

    # permit id for the first-inspection event, where we can find one
    # Explicit window function. A `GROUP BY project_id HAVING MIN(date)` with a bare
    # permit_number happens to return the right row in SQLite, but that is undefined behaviour --
    # HAVING MIN(...) is a truthiness test, not a filter -- so the permit attached to each event
    # would be correct only by accident.
    first_permit = {}
    for p, n in db.execute(f"""
            SELECT project_id, permit_number FROM (
                SELECT i.project_id, i.permit_number,
                       ROW_NUMBER() OVER (PARTITION BY i.project_id
                                          ORDER BY i.inspection_date, i.id) rn
                FROM inspections i
                WHERE i.project_id IS NOT NULL AND IFNULL(i.inspection_date,'') <> ''
                  AND i.result IN ({qs})
            ) WHERE rn = 1""", CONDUCTED):
        first_permit[p] = permit_id.get(n)

    stage_moves = []
    if args.with_stage:
        fp = {p for p, _ in firsts}
        for p, code in db.execute("""SELECT p.id, s.code FROM projects p
                JOIN vocabulary_stage_types s ON s.id = p.current_stage_type_id
                WHERE p.merged_into_id IS NULL"""):
            if p in fp and code == "permitted":
                stage_moves.append(p)

    print("Derive inspection events")
    print(f"  inspections rows linked to a project : "
          f"{db.execute('SELECT COUNT(*) FROM inspections WHERE project_id IS NOT NULL').fetchone()[0]:,}")
    print(f"  first_inspection_observed to insert  : {len(firsts)}   (today: {len(have_first)})")
    print(f"  final_inspection_passed to insert    : {len(finals)}   (today: {len(have_final)})")
    print(f"  ...distinct projects with a final    : {len({p for p,_,_ in finals})}")
    if args.with_stage:
        print(f"  stage 'permitted' -> 'under_construction': {len(stage_moves)}")
    else:
        print("  (stage unchanged; pass --with-stage to move permitted -> under_construction)")

    if firsts:
        yrs = collections.Counter(d[:4] for _, d in firsts)
        print("  first inspections by year: " + " ".join(f"{k}:{v}" for k, v in sorted(yrs.items())))
    if not args.commit:
        print("\nDRY RUN — nothing written.")
        return 0

    now = datetime.datetime.now().isoformat(timespec="seconds")
    before = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("project_events", "projects", "permits", "inspections")}
    made = 0
    try:
        db.execute("BEGIN")
        for p, d in firsts:
            db.execute("""INSERT INTO project_events (project_id, event_type_id, event_date,
                event_date_precision, permit_id, summary, confidence_type_id, is_inferred,
                source_type, source_url, observed_by, observed_at, created_at)
                VALUES (?,?,?, 'exact', ?,?,?,0,'city_portal',?,?,?,?)""",
                (p, EV_FIRST_INSPECTION, d, first_permit.get(p),
                 "First conducted inspection", CONF_HIGH, SOURCE_URL, OBSERVED_BY, now, now))
            made += 1
        for p, n, d in finals:
            db.execute("""INSERT INTO project_events (project_id, event_type_id, event_date,
                event_date_precision, permit_id, summary, confidence_type_id, is_inferred,
                source_type, source_url, observed_by, observed_at, created_at)
                VALUES (?,?,?, 'exact', ?,?,?,0,'city_portal',?,?,?,?)""",
                (p, EV_FINAL_PASSED, d, permit_id.get(n),
                 f"Building Final passed ({n})", CONF_HIGH, SOURCE_URL, OBSERVED_BY, now, now))
            made += 1
        moved = 0
        for p in stage_moves:
            db.execute("UPDATE projects SET current_stage_type_id=?, updated_at=? WHERE id=?",
                       (STAGE_UNDER_CONSTRUCTION, now, p))
            moved += 1

        after = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in before}
        problems = []
        if after["project_events"] - before["project_events"] != made:
            problems.append("project_events delta mismatch")
        for t in ("permits", "inspections"):
            if after[t] != before[t]:
                problems.append(f"{t} changed — this step must not touch it")
        if after["projects"] != before["projects"]:
            problems.append("projects row count changed")
        # no completion date may move: this step must not touch ADR-001 semantics
        if problems:
            db.execute("ROLLBACK")
            print("\nROLLED BACK — verification failed:")
            for x in problems:
                print("   " + x)
            return 1
        db.execute("COMMIT")
        print(f"\nCOMMITTED  events +{made}  stage moves {moved}")
    except Exception:
        db.execute("ROLLBACK")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
