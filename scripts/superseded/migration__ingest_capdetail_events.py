#!/usr/bin/env python3
"""ingest_capdetail_events.py -- write rung 3 (application ACCEPTED) into v2 from the CapDetail
harvest. PREVIEW BY DEFAULT; --commit is gated on John's go-ahead and on him unlocking the DB.

WHAT IT WRITES, AND WHAT IT DELIBERATELY DOES NOT.
One `application_complete` event (vocabulary_event_types id 3, which already exists -- no schema
change) per project, for the acceptance of that project's PRIMARY APPLICATION only, selected by
capdetail_select.select_rung3.

It does NOT write the companion reviews (design review, landmarks, appeal), even though each is a
real dated city action with a real Completeness Review. Writing them as `application_complete` would
recreate the exact defect this work exists to remove: several same-type events per project, forcing
whoever reads them to aggregate, and an aggregate promotes one record's action to speak for the
project (export_explorer_data_v2.py takes MAX, which on 2449 Dwight would make a 2026 design-review
check the project's 2022 acceptance). The companion reviews stay in the harvest evidence file, which
is their honest home until there is a structure that can hold them without being mistaken for rung 3.
See docs/methodology/identity_is_the_product.md.

EVERY ROW CARRIES ITS IDENTITY -- the record number in `summary`, the CapDetail URL in `source_url`,
and the task / city-set due date / signer in `details`. That is the whole point: a date whose referent
is recoverable never needs an aggregate to stand in for it.

DISCIPLINE (CLAUDE.md): snapshot -> read-only preview -> STOP for John -> transactional write with
per-row rowcount==1 and verify-or-rollback -> fresh-connection fingerprint. Idempotent: a row whose
(project_id, type, date, record) is already present is skipped, so a re-run is a no-op.

  .venv/bin/python scripts/migration/ingest_capdetail_events.py                # preview
  .venv/bin/python scripts/migration/ingest_capdetail_events.py --commit       # only after go-ahead
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from capdetail_select import EV_APP_COMPLETE, load_rows, select_rung3   # noqa: E402

V2 = ROOT / "databases/berkeley_housing_v2.db"
HARVEST = ROOT / "scratch/2026-09-26_capdetail"
BASE_URL = "https://aca-prod.accela.com"
OBSERVED_BY = "capdetail_harvest@2026-09-26"
CONF_HIGH = 1


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def build_plan(db) -> list[dict]:
    src = sorted(glob.glob(str(HARVEST / "capdetail_reparsed_*.jsonl")))
    if not src:
        raise SystemExit(f"no reparsed harvest in {HARVEST} -- run reparse_capdetail.py first")
    sel = select_rung3(load_rows(src[-1]), db)
    have = {(pid, d, s or "") for pid, d, s in db.execute(
        "SELECT project_id, event_date, summary FROM project_events "
        f"WHERE event_type_id={EV_APP_COMPLETE}")}
    plan = []
    for pid, (rec, task) in sorted(sel["selected"].items()):
        summary = f"Application {rec['record']} deemed complete"
        if (pid, task["status_date"], summary) in have:
            continue                            # idempotent
        details = (f"{task['task']} marked '{task['status']}'"
                   f" on {task['status_date']}"
                   + (f" by {task['status_by']}" if task.get("status_by") else "")
                   + (f"; city due date {task['due_date']}" if task.get("due_date") else "")
                   + f"; record type {rec.get('record_type')}")
        plan.append({
            "project_id": pid, "event_date": task["status_date"], "summary": summary,
            "details": details, "source_url": BASE_URL + rec["href"], "record": rec["record"],
        })
    return plan, sel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true",
                    help="write. Requires John's go-ahead AND an unlocked DB.")
    args = ap.parse_args()

    db = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    plan, sel = build_plan(db)
    db.close()

    print(f"harvest selection: {len(sel['selected'])} projects with an identified primary "
          f"application ({len(sel['chains'])} of them a modification CHAIN resolved to its root) · "
          f"{len(sel['no_primary'])} with no primary (unknown with provenance) · "
          f"{len(sel['ambiguous'])} ambiguous")
    if sel["conflated"]:
        print(f"\n⚠ {len(sel['conflated'])} CONFLATED projects -- separate applications sharing one")
        print("  address, so v2 has stitched a single timeline from different buildings. NOT written")
        print("  and NOT merged; this is a data finding for John:")
        for pid, recs, filed in sel["conflated"][:10]:
            print(f"    proj{pid:<5} unrelated primaries={recs}  v2 filed_date={filed}")
    print(f"rows to INSERT into project_events (type {EV_APP_COMPLETE} application_complete): "
          f"{len(plan)}\n")
    for r in plan[:25]:
        print(f"  proj{r['project_id']:<5} {r['event_date']}  {r['summary']}")
        print(f"        {r['details'][:110]}")
    if len(plan) > 25:
        print(f"  ... and {len(plan)-25} more")

    if not args.commit:
        print("\nPREVIEW ONLY -- nothing written. Re-run with --commit after John's go-ahead.")
        return 0
    if not plan:
        print("\nnothing to write.")
        return 0

    # ---- gated write ----
    snap = ROOT / f"databases/keep_snapshot_{time.strftime('%Y-%m-%d')}_pre-capdetail_rung3.db"
    if not snap.exists():
        shutil.copy2(V2, snap)
    print(f"\nsnapshot {snap.name} ({snap.stat().st_size:,} bytes, sha {sha(snap)})")
    w = sqlite3.connect(V2)
    if w.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit("integrity_check failed on the live DB -- aborting")
    w.execute("PRAGMA foreign_keys=ON")
    before = w.execute("SELECT COUNT(*) FROM project_events WHERE observed_by=?",
                       (OBSERVED_BY,)).fetchone()[0]
    n = 0
    try:
        w.execute("BEGIN")
        for r in plan:
            cur = w.execute(
                "INSERT INTO project_events (project_id,event_type_id,event_date,"
                "event_date_precision,summary,details,confidence_type_id,is_inferred,"
                "source_type,source_url,observed_by,observed_at) "
                "VALUES (?,?,?,'exact',?,?,?,0,'city_portal',?,?,?)",
                (r["project_id"], EV_APP_COMPLETE, r["event_date"], r["summary"], r["details"],
                 CONF_HIGH, r["source_url"], OBSERVED_BY,
                 time.strftime("%Y-%m-%dT%H:%M:%S")))
            if cur.rowcount != 1:
                raise RuntimeError(f"rowcount {cur.rowcount} for proj{r['project_id']}")
            n += 1
        # VERIFY THE DELTA, NOT THE TOTAL. Counting every row this observer has ever written
        # and comparing it to THIS run's insert count is only true on a first run: the rung-3
        # ingest passed at 287==287 and then rolled back a legitimate 2-row incremental run
        # because 289 != 2. Same error as the 2026-09-26 verifier that failed on 25 pre-existing
        # rows: a check anchored to a running total, not to what this transaction did.
        got = w.execute("SELECT COUNT(*) FROM project_events WHERE observed_by=?",
                        (OBSERVED_BY,)).fetchone()[0]
        if got != before + n:
            raise RuntimeError(f"verify failed: {before} before + {n} inserted != {got} present")
        w.commit()
        print(f"committed {n} events")
    except Exception as e:
        w.rollback()
        print(f"ROLLED BACK: {e}")
        return 1
    finally:
        w.close()
    fresh = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    print("fresh-connection fingerprint: "
          f"{fresh.execute('SELECT COUNT(*) FROM project_events WHERE observed_by=?', (OBSERVED_BY,)).fetchone()[0]}"
          f" rows by {OBSERVED_BY}; integrity "
          f"{fresh.execute('PRAGMA integrity_check').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
