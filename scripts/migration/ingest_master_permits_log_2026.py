#!/usr/bin/env python3
"""ingest_master_permits_log_2026.py — the entitlement-intake side of the 2026 CPRA production.

WHAT THIS FILE IS, AND IS NOT. `2026 Master Permits Log.xlsx` has 9 sheets and 589 rows, and its
headers promise New Units / Demolished Units / Total Units / BMR by tier / Density Bonus / SB 9
streamlining plus the entitlement dates. **Every one of those columns is 100% empty** — the city
exported the template without filling it. Measured, not assumed; see
docs/audit/2026-09-25_cpra_2026_ingest_preview.md. What survives is application intake: number,
type, site address, applicant, res/comm flag, description, date received.

WHY NO PROJECTS ARE CREATED FROM IT. 514 rows carry a usable number + address, and 381 of those
match no existing project. Creating them would add 381 rows to a housing pipeline database when
only ~114 descriptions mention housing at all — the rest are sign permits, driveway gates, hot
tubs, garage replacements and home occupations. The `Res./Comm/ MU/Public` column does not help:
it is a ZONE flag, so a hot tub in a residential zone reads "Residential". The one column that
would have told us whether a unit is proposed, `New Units (Y/N)`, is the empty one. So this ingest
**creates no projects and no permits**. It does two safe things instead:

  1. `application_submitted` events on projects we can already identify, and ONLY where the
     application plausibly belongs to that project — a ZP/PLN record whose description carries
     housing language. A sign-permit application attached to a housing project would land a bogus
     application event, and `v_projects_flat.filed_date` is MIN(application_submitted), so a bad
     event can move a published date.
  2. `planning_queue_2026`, a reference table holding all 514 rows verbatim, so the planning queue
     is visible and queryable without touching the project graph.

Snapshot: keep_snapshot_2026-09-25_pre-masterlog-ingest.db
Dry-run by default; the write is one transaction that verifies its deltas and rolls back on any
mismatch.

Usage:  python scripts/migration/ingest_master_permits_log_2026.py [--commit]
"""
import argparse
import collections
import datetime
import re
import sqlite3
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
ML = ROOT / "data/raw/cpra-downloads/2026 Master Permits Log.xlsx"
V2 = ROOT / "databases/berkeley_housing_v2.db"
SOURCE_URL = "CPRA: 2026 Master Permits Log.xlsx"
OBSERVED_BY = "cpra_master_permits_log_2026_ingest"
EV_APPLICATION_SUBMITTED = 2
CONF_HIGH = 1

# Widened 2026-09-25 after a spot check on 2455 Telegraph (the Amoeba Records site): an 8-storey,
# 68-unit, 7-VLI application read is_housing=0 because the first version of this pattern demanded
# the words "dwelling"/"apartment"/"housing" and the description says "68 units". That one word
# suppressed the application_submitted event that would have corrected the project's filed_date.
# The narrow rule flagged 112 of 514 rows; this one flags 161. It now also catches bare unit counts,
# office-to-residential conversions, SB 330, and plain "residential ... addition".
HOUSING = re.compile(
    r"\b(dwelling|adu|jadu|duplex|triplex|fourplex|apartment|residence|residential|"
    r"middle housing|sb ?9|sb ?330|town ?home|housing|\d+\s*units?\b|units?\s*\()", re.I)
ENTITLEMENT_PREFIX = re.compile(r"^(ZP|PLN)", re.I)


def norm(a: str) -> str:
    a = re.sub(r",.*$", "", str(a or "").upper())
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", a).split())


def iso(x):
    if isinstance(x, datetime.datetime):
        return x.date().isoformat()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})$", str(x or "").strip())
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else None


def read():
    wb = openpyxl.load_workbook(ML, read_only=True)
    out = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        hi = next((i for i, r in enumerate(rows) if sum(1 for x in r if x) >= 5), 0)
        hdr = [str(h).replace("\n", " ").strip() if h else "" for h in rows[hi]]
        for r in rows[hi + 1:]:
            if not any(x for x in r):
                continue
            d = {hdr[i]: v for i, v in enumerate(r) if i < len(hdr) and hdr[i]}
            numr = d.get("Application Number") or d.get("Project Number")
            addr = d.get("Site Address")
            if not (numr and addr):
                continue
            out.append({
                "sheet": ws.title.strip(), "number": str(numr).strip(), "address": str(addr).strip(),
                "app_type": str(d.get("Application  Type") or d.get("Project Type") or "").strip(),
                "applicant": str(d.get("Applicant") or "").strip(),
                "use_flag": str(d.get("Res./Comm/ MU/Public") or "").strip(),
                "description": str(d.get("Description") or d.get("Project Description") or "").strip(),
                "date_received": iso(d.get("Date Received")),
                "status": str(d.get("Status") or d.get("Application Status") or "").strip(),
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--db", default=str(V2), help="target database (default: the live v2)")
    args = ap.parse_args()
    recs = read()
    db = sqlite3.connect(args.db)
    db.execute("PRAGMA foreign_keys=ON")

    exact, loose = {}, {}
    for pid, a in db.execute("""SELECT id, canonical_address FROM projects
                                WHERE canonical_address IS NOT NULL AND merged_into_id IS NULL"""):
        n = norm(a)
        exact[n] = pid
        p = n.split()
        if p and p[0].isdigit() and len(p) > 1:
            loose.setdefault((p[0], p[1]), pid)

    def match(a):
        n = norm(a)
        p = n.split()
        if n in exact:
            return exact[n]
        if p and p[0].isdigit() and len(p) > 1:
            return loose.get((p[0], p[1]))
        return None

    for r in recs:
        r["project_id"] = match(r["address"])
        r["is_housing"] = bool(HOUSING.search(r["description"]))

    evented = [r for r in recs
               if r["project_id"] and r["is_housing"] and r["date_received"]
               and ENTITLEMENT_PREFIX.match(r["number"])]
    # never double-post the same application onto the same project
    existing = {(pid, ev) for pid, ev in db.execute(
        "SELECT project_id, summary FROM project_events WHERE summary IS NOT NULL")}
    evented = [r for r in evented if (r["project_id"], f"Application {r['number']} received") not in existing]

    print(f"rows with number + address       {len(recs)}")
    print(f"  match an existing project      {sum(1 for r in recs if r['project_id'])}")
    print(f"  housing language in description{sum(1 for r in recs if r['is_housing']):>4}")
    print(f"application_submitted events     {len(evented)}  (matched AND housing AND ZP/PLN AND dated)")
    print(f"planning_queue_2026 rows         {len(recs)}")
    print("projects created                 0   (by design - see module docstring)")
    print("permits created                  0")
    if not args.commit:
        print("\nDRY RUN — nothing written.")
        return 0

    now = datetime.datetime.now().isoformat(timespec="seconds")
    before = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("project_events", "projects", "permits")}
    try:
        db.execute("BEGIN")
        db.execute("""CREATE TABLE IF NOT EXISTS planning_queue_2026 (
            id INTEGER PRIMARY KEY, sheet TEXT, number TEXT, app_type TEXT, address TEXT,
            applicant TEXT, use_flag TEXT, description TEXT, date_received TEXT, status TEXT,
            project_id INTEGER REFERENCES projects(id), is_housing INTEGER NOT NULL,
            source_url TEXT, ingested_at TEXT)""")
        db.execute("DELETE FROM planning_queue_2026")
        for r in recs:
            db.execute("""INSERT INTO planning_queue_2026 (sheet, number, app_type, address,
                applicant, use_flag, description, date_received, status, project_id, is_housing,
                source_url, ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (r["sheet"], r["number"], r["app_type"], r["address"], r["applicant"],
                 r["use_flag"], r["description"], r["date_received"], r["status"],
                 r["project_id"], 1 if r["is_housing"] else 0, SOURCE_URL, now))
        made = 0
        for r in evented:
            db.execute("""INSERT INTO project_events (project_id, event_type_id, event_date,
                event_date_precision, summary, details, confidence_type_id, is_inferred,
                source_type, source_url, observed_by, observed_at, created_at)
                VALUES (?,?,?, 'exact', ?,?,?,0,'document',?,?,?,?)""",
                (r["project_id"], EV_APPLICATION_SUBMITTED, r["date_received"],
                 f"Application {r['number']} received", r["description"][:500], CONF_HIGH,
                 SOURCE_URL, OBSERVED_BY, now, now))
            made += 1
        after = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in before}
        problems = []
        if after["project_events"] - before["project_events"] != made:
            problems.append("project_events delta mismatch")
        for t in ("projects", "permits"):
            if after[t] != before[t]:
                problems.append(f"{t} changed - this ingest must not touch it")
        q = db.execute("SELECT COUNT(*) FROM planning_queue_2026").fetchone()[0]
        if q != len(recs):
            problems.append(f"planning_queue_2026 has {q}, expected {len(recs)}")
        if problems:
            db.execute("ROLLBACK")
            print("\nROLLED BACK — verification failed:")
            for p in problems:
                print("   " + p)
            return 1
        db.execute("COMMIT")
        print(f"\nCOMMITTED  events +{made}  planning_queue_2026 {q} rows  "
              f"projects/permits unchanged")
    except Exception:
        db.execute("ROLLBACK")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
