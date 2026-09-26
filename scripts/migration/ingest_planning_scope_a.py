#!/usr/bin/env python3
"""ingest_planning_scope_a.py — filing, acceptance and entitlement dates onto projects v2 HAS.

SCOPE A, gated by John 2026-09-25: "get the date filed for all our projects, which is ingest 1."
Events only. No project is created, no unit count is touched, no completion date moves.

WHY IT MATTERS MOST AT THE ENTITLEMENT RUNG. v2 holds entitlement events for 59 projects, and 30 of
the 43 completed multi-unit non-exempt projects lack one -- more than lack a building permit. This
is the ingest that closes that.

WHAT THE SOURCE CAN AND CANNOT SAY. The Accela Planning LIST view carries `Date` (filed), a CURRENT
`Status`, and `capdetail_href`. It has NO transition dates. So a record tells us the project was
filed on a date and where it stands NOW -- not when it moved. Accordingly:
  * `application_submitted` is dated at `Date`, which is a real observation.
  * `entitlement_approved` / `application_complete` are written with **event_date = NULL**.
    ⚠ The first draft dated them at the FILING date as a placeholder. That was wrong and would have
    been silently wrong: `v_projects_flat.entitled_date` is MAX(event_date) over entitlement events
    with NO is_inferred filter, so every one of those 376 placeholders would have set an entitlement
    date EARLIER than the approval actually happened. A NULL date is ignored by MAX, so the event
    asserts the STATE -- this project was approved -- without corrupting any date aggregation. The
    filing date is carried separately and truthfully by `application_submitted`.
The real transition dates are on the CapDetail pages: 14,936 Planning capIDs held, ~95 visited.

Dedupe: an event is skipped when the same project already carries one of that type citing the same
record number, so re-running adds nothing.

Usage:  python scripts/migration/ingest_planning_scope_a.py [--commit]
"""
import argparse
import collections
import datetime
import glob
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "databases/berkeley_housing_v2.db"
EV_SUBMITTED, EV_COMPLETE, EV_ENTITLED = 2, 3, 9
CONF_HIGH, CONF_MED = 1, 2
OBSERVED_BY = "accela_planning_list_ingest@2026-09-25"
SOURCE_URL = "Accela Planning list view (harvester sweep)"

DEV = re.compile(r"^(ZP|PLN|DRS|DRC|LM|ZCBP)", re.I)
HOUSING = re.compile(
    r"(\b(dwelling|adu|jadu|duplex|triplex|fourplex|apartment|residence|residential|"
    r"middle housing|sb ?9|sb ?330|sb ?35|sb ?684|ab ?2011|town ?home|housing|single.family|"
    r"infill|live.?work)\b|\d+\s*[-\s]?\s*units?\b)", re.I)
ACCEPTED = re.compile(r"application complete|under review|in review|pending final action", re.I)
ENTITLED = re.compile(r"^approved", re.I)


def iso(m):
    x = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", (m or "").strip())
    return f"{x.group(3)}-{int(x.group(1)):02d}-{int(x.group(2)):02d}" if x else ""


def key(a):
    a = re.sub(r",.*$", "", str(a or "").upper())
    p = re.sub(r"[^A-Z0-9 ]", " ", a).split()
    return (p[0], p[1]) if len(p) > 1 and p[0].isdigit() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    recs = {}
    for fn in glob.glob(str(ROOT / "data/raw/accela/date_range/Planning_*.jsonl")):
        for line in open(fn):
            try:
                d = json.loads(line)
            except Exception:
                continue
            n = str(d.get("Record Number") or "").strip()
            if n and n not in recs:
                recs[n] = d
    db = sqlite3.connect(V2)
    db.execute("PRAGMA foreign_keys=ON")
    addr = collections.defaultdict(set)
    for p, a in db.execute("SELECT project_id,address_display FROM v_projects_flat WHERE address_display IS NOT NULL"):
        k = key(a)
        if k:
            addr[k].add(p)
    existing = {(p, s) for p, s in db.execute(
        "SELECT project_id, summary FROM project_events WHERE summary IS NOT NULL")}

    plan = []
    for n, d in recs.items():
        if not DEV.match(n):
            continue
        blob = " ".join(str(d.get(f, "")) for f in ("Description", "Project Name", "Record Type"))
        if not HOUSING.search(blob):
            continue
        k = key((d.get("_cells") or [""])[-1])
        pids = addr.get(k, set()) if k else set()
        when = iso(d.get("Date", ""))
        if not pids or not when:
            continue
        status = str(d.get("Status") or "")
        desc = str(d.get("Description") or "")[:400]
        for pid in pids:
            plan.append((pid, EV_SUBMITTED, when, f"Application {n} filed", desc, 0, "exact", CONF_HIGH))
            if ENTITLED.match(status):
                plan.append((pid, EV_ENTITLED, None, f"Application {n} approved ({status})", desc, 1, None, CONF_MED))
            elif ACCEPTED.search(status):
                plan.append((pid, EV_COMPLETE, None, f"Application {n} accepted ({status})", desc, 1, None, CONF_MED))
    plan = [x for x in plan if (x[0], x[3]) not in existing]

    by = collections.Counter(x[1] for x in plan)
    names = {EV_SUBMITTED: "application_submitted", EV_COMPLETE: "application_complete",
             EV_ENTITLED: "entitlement_approved"}
    print(f"  events to insert: {len(plan):,}   projects touched: {len({x[0] for x in plan}):,}")
    for t, c in by.most_common():
        inf = "  [is_inferred=1, event_date=NULL - asserts the STATE, not a date]" if t != EV_SUBMITTED else ""
        print(f"    {names[t]:<24} {c:>5}{inf}")
    for t in (EV_SUBMITTED, EV_COMPLETE, EV_ENTITLED):
        before = db.execute("SELECT COUNT(DISTINCT project_id) FROM project_events WHERE event_type_id=?", (t,)).fetchone()[0]
        after = len({x[0] for x in plan if x[1] == t} | {p for (p,) in db.execute(
            "SELECT DISTINCT project_id FROM project_events WHERE event_type_id=?", (t,))})
        print(f"    projects with {names[t]:<22} {before:>4} -> {after:>4}")
    if not args.commit:
        print("\n  DRY RUN — nothing written.")
        return 0

    now = datetime.datetime.now().isoformat(timespec="seconds")
    before_all = db.execute("SELECT COUNT(*) FROM project_events").fetchone()[0]
    before_proj = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    before_perm = db.execute("SELECT COUNT(*) FROM permits").fetchone()[0]
    try:
        db.execute("BEGIN")
        for pid, tid, when, summary, details, inferred, prec, conf in plan:
            db.execute("""INSERT INTO project_events (project_id,event_type_id,event_date,
                event_date_precision,summary,details,confidence_type_id,is_inferred,
                source_type,source_url,observed_by,observed_at,created_at)
                VALUES (?,?,?,?,?,?,?,?, 'city_portal',?,?,?,?)""",
                (pid, tid, when, prec, summary, details, conf, inferred,
                 SOURCE_URL, OBSERVED_BY, now, now))
        after_all = db.execute("SELECT COUNT(*) FROM project_events").fetchone()[0]
        problems = []
        if after_all - before_all != len(plan):
            problems.append("event delta mismatch")
        if db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] != before_proj:
            problems.append("projects changed — this ingest must not create any")
        if db.execute("SELECT COUNT(*) FROM permits").fetchone()[0] != before_perm:
            problems.append("permits changed — this ingest must not touch them")
        bad = db.execute("""SELECT COUNT(*) FROM project_events WHERE observed_by=?
                            AND is_inferred=1 AND event_date IS NOT NULL""", (OBSERVED_BY,)).fetchone()[0]
        if bad:
            problems.append(f"{bad} inferred events carry a date — they would corrupt entitled_date")
        if problems:
            db.execute("ROLLBACK")
            print("\nROLLED BACK:")
            for p in problems:
                print("   " + p)
            return 1
        db.execute("COMMIT")
        print(f"\nCOMMITTED  events {before_all:,} -> {after_all:,}  (+{len(plan):,})")
    except Exception:
        db.execute("ROLLBACK")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
