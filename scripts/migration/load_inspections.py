#!/usr/bin/env python3
"""Layer A — give the Accela inspection records a home in v2. ADDITIVE ONLY.

Designed 2026-05-23 (`notes/2026-05-23_inspection_ingest_design_sketch.md`, "Design complete. Ready for
CC build") and never built; 1,300 harvested JSON files have sat outside the database since. This is that
build, unchanged in intent: ingest the raw inspection rows, provenance preserved, nothing derived.

WHAT IT TOUCHES: creates `inspections` (+ indexes) and inserts rows. It does NOT write to projects,
permits, project_events, or any view, and it does NOT set a completion date anywhere — deriving
`co_issued_date` from an approved `Building 1200 Building Final` is a SEPARATE, ADR-changing step that
needs its own gate. Reversible: `DROP TABLE inspections`.

Keyed on permit_number as the source gives it (the natural key), with project_id resolved where v2 knows
the permit and left NULL where it does not — 564 harvested permits are not tracked by v2, and dropping
them would discard exactly the evidence we went looking for. `inspection_id` is Accela's own id; the
UNIQUE(permit_number, inspection_id) constraint makes re-runs idempotent.

Usage:
  python scripts/migration/load_inspections.py --preview          # read-only counts, writes nothing
  python scripts/migration/load_inspections.py --write            # transactional, verify-or-rollback
"""
import argparse, datetime as dt, json, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / "databases/berkeley_housing_v2.db"
SRC = ROOT / "data/raw/accela_inspections"

SCHEMA = """
CREATE TABLE IF NOT EXISTS inspections (
  id             INTEGER PRIMARY KEY,
  permit_number  TEXT NOT NULL,          -- natural key from Accela; NOT a FK (564 permits are untracked)
  project_id     INTEGER REFERENCES projects(id) ON DELETE SET NULL,   -- NULL when v2 does not track it
  inspection_id  TEXT,                   -- Accela's own inspection id
  type_code      TEXT,                   -- e.g. 'Building 1200 Building Final'
  result         TEXT,                   -- Approved / Partially Approved / Disapproved / Cancelled / ...
  inspection_date TEXT,                  -- ISO8601, converted from the source's MM/DD/YYYY
  inspector      TEXT,
  source_file    TEXT NOT NULL,          -- provenance: which harvest JSON this row came from
  scraped_at     TEXT,                   -- provenance: when that file was harvested
  created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (permit_number, inspection_id)
);
CREATE INDEX IF NOT EXISTS idx_inspections_permit  ON inspections(permit_number);
CREATE INDEX IF NOT EXISTS idx_inspections_project ON inspections(project_id);
CREATE INDEX IF NOT EXISTS idx_inspections_type    ON inspections(type_code);
CREATE INDEX IF NOT EXISTS idx_inspections_date    ON inspections(inspection_date);
"""


def iso(s):
    for f in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(str(s), f).date().isoformat()
        except (ValueError, TypeError):
            continue
    return None


def gather(permit_to_project):
    rows, files, skipped = [], 0, 0
    for f in sorted(SRC.glob("*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            skipped += 1
            continue
        pn = d.get("permit_number")
        if not pn:
            skipped += 1
            continue
        files += 1
        scraped = str(d.get("extraction_timestamp") or "")[:19]
        seen = set()
        for i in (d.get("inspections") or []):
            iid = str(i.get("inspection_id") or "")
            if iid and (pn, iid) in seen:       # same file can repeat a row
                continue
            seen.add((pn, iid))
            rows.append((pn, permit_to_project.get(pn), iid or None,
                         (i.get("type_code") or "").strip() or None,
                         i.get("result") or None, iso(i.get("date")),
                         (i.get("inspector") or "").strip() or None, f.name, scraped))
    return rows, files, skipped


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--preview", action="store_true")
    g.add_argument("--write", action="store_true")
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    p2p = {r[0]: r[1] for r in con.execute(
        "select permit_number, project_id from permits where permit_number is not null")}
    rows, files, skipped = gather(p2p)
    linked = sum(1 for r in rows if r[1])
    finals = [r for r in rows if r[3] == "Building 1200 Building Final"]
    appr = [r for r in finals if r[4] == "Approved"]

    print(f"source: {files} files parsed ({skipped} unreadable/no permit_number)")
    print(f"rows to insert: {len(rows):,}")
    print(f"  linked to a v2 project: {linked:,}   unlinked (v2 does not track the permit): {len(rows)-linked:,}")
    print(f"  'Building 1200 Building Final' rows: {len(finals):,}  of which Approved: {len(appr):,}")
    print(f"  distinct permits: {len({r[0] for r in rows}):,}   distinct type_codes: {len({r[3] for r in rows}):,}")
    print(f"  date range: {min(r[5] for r in rows if r[5])} .. {max(r[5] for r in rows if r[5])}")
    if a.preview:
        print("\nPREVIEW ONLY — nothing written.")
        return

    before = con.execute("select count(*) from permits").fetchone()[0]
    try:
        con.executescript(SCHEMA)
        with con:                                   # one transaction; any exception rolls back
            cur = con.executemany(
                "insert or ignore into inspections "
                "(permit_number, project_id, inspection_id, type_code, result, inspection_date, "
                " inspector, source_file, scraped_at) values (?,?,?,?,?,?,?,?,?)", rows)
            n = con.execute("select count(*) from inspections").fetchone()[0]
            if n == 0:
                raise RuntimeError("verify failed: inspections table is empty after insert")
            after = con.execute("select count(*) from permits").fetchone()[0]
            if after != before:
                raise RuntimeError(f"verify failed: permits count changed {before} -> {after}")
        print(f"\nWROTE {n:,} inspection rows. permits unchanged at {before}.")
    except Exception as e:
        print(f"\nROLLED BACK: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        con.close()

    # fresh-connection fingerprint (CLAUDE.md discipline)
    c2 = sqlite3.connect(DB)
    print("fresh-connection fingerprint:",
          dict(zip(("inspections", "approved_building_finals", "projects", "permits", "projects_with_co"),
                   c2.execute(
                       "select (select count(*) from inspections),"
                       " (select count(*) from inspections where type_code='Building 1200 Building Final'"
                       "   and result='Approved'),"
                       " (select count(*) from projects), (select count(*) from permits),"
                       " (select count(*) from v_projects_flat where co_issued_date is not null)"
                   ).fetchone())))
    c2.close()


if __name__ == "__main__":
    main()
