#!/usr/bin/env python3
"""fix_autoclosed_mapping.py — 'Auto-Closed' is not a withdrawal.

THE BUG. `scripts/migration/migrate_v1_to_v2.py` line 257 maps Accela's workflow action
'auto-closed' onto the `project_withdrawn` event:

        'auto-closed': 'project_withdrawn',

Accela emits "Auto-Closed" when it closes a workflow task — in every case here paired with a
"Documents Uploaded" status update. It is an administrative close of a RECORD, not an applicant
abandoning a project. The neighbouring line already gets this right for a similar case:
'categorically exempt': 'status_update', with the comment "CEQA, not modeled".

THE DAMAGE. **All 64 `project_withdrawn` events in v2 read "Auto-Closed".** Not one is a genuine
withdrawal. They sit on 7 projects totalling 412 units, and four of those are displayed as
**withdrawn** on berkeleybuild.com:

    2902 ADELINE St     54u   14 auto-closed   inspected 2026-09-22
    2127 DWIGHT Way     58u   12 auto-closed
    2587 TELEGRAPH Ave  52u   11 auto-closed   confirmed under construction by John; leasing
                                               office approved 2025-06, blade-sign permit
                                               2026-09-01, no BP finaled
    2016 ASHBY Ave      50u    7 auto-closed   inspected 2026-09-16

**214 units shown as dead that are not.**

THE FIX, and why it is a re-classification rather than an edit of evidence. The OBSERVATION —
"Accela recorded Auto-Closed on this date" — is correct and is preserved untouched in `summary`,
`event_date` and `observed_by`. What was wrong is the INTERPRETATION of that observation as a
withdrawal. Re-typing the event to `status_update` corrects the interpretation and leaves the
evidence intact, which is the distinction ADR-002 draws between the append-only EVIDENCE layer and
the classification above it.

After this, v2 holds **zero** `project_withdrawn` events — correct, because it never had a real one.
A genuine withdrawal would come from an Accela status of 'Withdrawn', which is in the vocabulary
list and has never appeared in this data.

Stage is NOT changed here. That follows from `preview_stage_from_events.py` as its own gated write.

Usage:  python scripts/migration/fix_autoclosed_mapping.py [--commit]
"""
import argparse
import datetime
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "databases/berkeley_housing_v2.db"
EV_WITHDRAWN = 19
EV_STATUS_UPDATE = 23


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--db", default=str(V2))
    args = ap.parse_args()
    db = sqlite3.connect(args.db)
    db.execute("PRAGMA foreign_keys=ON")

    total = db.execute("SELECT COUNT(*) FROM project_events WHERE event_type_id=?",
                       (EV_WITHDRAWN,)).fetchone()[0]
    autoc = db.execute("""SELECT COUNT(*) FROM project_events
                          WHERE event_type_id=? AND IFNULL(summary,'') LIKE '%Auto-Closed%'""",
                       (EV_WITHDRAWN,)).fetchone()[0]
    other = total - autoc
    print("Auto-Closed -> project_withdrawn mis-mapping")
    print(f"  project_withdrawn events total      {total}")
    print(f"  ...summarised 'Auto-Closed'         {autoc}")
    print(f"  ...anything else (a REAL withdrawal) {other}   <- left untouched\n")
    rows = list(db.execute("""SELECT e.project_id, f.address_display, f.total_units, f.status_code,
                                     COUNT(*) n, MAX(e.event_date)
                              FROM project_events e JOIN v_projects_flat f ON f.project_id=e.project_id
                              WHERE e.event_type_id=? AND IFNULL(e.summary,'') LIKE '%Auto-Closed%'
                              GROUP BY e.project_id ORDER BY f.total_units DESC""", (EV_WITHDRAWN,)))
    print("  affected projects:")
    for pid, ad, u, st, n, last in rows:
        flag = "  <-- shown WITHDRAWN" if st == "withdrawn" else ""
        print(f"    proj{pid:<5} {str(ad)[:26]:<26} {str(u):>4}u  {n:>3} events  last {last}  stage={st}{flag}")
    units = sum(u or 0 for _, _, u, st, _, _ in rows if st == "withdrawn")
    print(f"\n  units currently displayed as withdrawn because of this: {units}")
    if not args.commit:
        print("\nDRY RUN — nothing written.")
        return 0

    now = datetime.datetime.now().isoformat(timespec="seconds")
    before_w = total
    before_s = db.execute("SELECT COUNT(*) FROM project_events WHERE event_type_id=?",
                          (EV_STATUS_UPDATE,)).fetchone()[0]
    before_all = db.execute("SELECT COUNT(*) FROM project_events").fetchone()[0]
    try:
        db.execute("BEGIN")
        cur = db.execute("""UPDATE project_events SET event_type_id=?
                            WHERE event_type_id=? AND IFNULL(summary,'') LIKE '%Auto-Closed%'""",
                         (EV_STATUS_UPDATE, EV_WITHDRAWN))
        moved = cur.rowcount
        after_w = db.execute("SELECT COUNT(*) FROM project_events WHERE event_type_id=?",
                             (EV_WITHDRAWN,)).fetchone()[0]
        after_s = db.execute("SELECT COUNT(*) FROM project_events WHERE event_type_id=?",
                             (EV_STATUS_UPDATE,)).fetchone()[0]
        after_all = db.execute("SELECT COUNT(*) FROM project_events").fetchone()[0]
        problems = []
        if moved != autoc:
            problems.append(f"updated {moved}, expected {autoc}")
        if after_w != before_w - autoc:
            problems.append("project_withdrawn count wrong after update")
        if after_s != before_s + autoc:
            problems.append("status_update count wrong after update")
        if after_all != before_all:
            problems.append("total event count changed — this must only re-type, never add or drop")
        if problems:
            db.execute("ROLLBACK")
            print("\nROLLED BACK:")
            for p in problems:
                print("   " + p)
            return 1
        db.execute("COMMIT")
        print(f"\nCOMMITTED  re-typed {moved}  project_withdrawn {before_w}->{after_w}  "
              f"status_update {before_s}->{after_s}  total unchanged at {after_all}")
    except Exception:
        db.execute("ROLLBACK")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
