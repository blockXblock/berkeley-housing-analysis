#!/usr/bin/env python3
"""
Build the scrape queue for the inspection orchestrator.

Reads the v4 database (read-only) to find all in-scope B-permits,
classifies them by URL availability, and populates cic_recon_queue.db.

IN SCOPE (v4, re-pointed 2026-10-02 from v2's stage-filtered `permits`): the MASTER and PHASE
permits of v4 structures -- structure_events.role_in_structure IN ('master','phase') joined to
events.source_record_key. The URL is the CapDetail href the City's own Accela list carried
(events of type 'accela_listed', raw_payload.capdetail_href); a permit with no listed href goes
to 'pending_url_discovery'.

QUEUE IDS. v4 has no permit table and its event_ids renumber on every rebuild, so the queue's
`permit_id` is derived from the permit number itself (B2015-00006 -> 201500006): stable across
rebuilds, and disjoint from the small v2 permit ids an older queue may hold. `project_id` is v4's
internal project_id (it renumbers; the public id is v_projects.project_key) and `project_address`
is the project's address_display.

Usage:
    python3 build_scrape_queue.py

The script is idempotent: re-running adds only new permits.
"""

import argparse
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Default paths
DEFAULT_V4_DB = os.environ.get(
    "BERKELEY_V4_DB",
    str(Path.home() / "berkeley-data" / "databases" / "berkeley_housing_v4.db")
)
ACCELA_BASE = "https://aca-prod.accela.com"
V2_ID_CEILING = 100_000_000   # v4-derived permit_ids are >= 2006*100000; anything below is a v2 id
DEFAULT_QUEUE_DB = "/tmp/cic_recon_queue.db"

# Schema for scrape_queue table
# NOTE: `url TEXT` is nullable, deviating from the design sketch which had
# `url TEXT NOT NULL`. This is intentional: rows with status='pending_url_discovery'
# have NULL url because they need URL discovery before they can be scraped.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scrape_queue (
    id INTEGER PRIMARY KEY,
    permit_id INTEGER NOT NULL,
    permit_number TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    project_address TEXT,
    capid_triplet TEXT,
    url TEXT,  -- nullable; rows with status='pending_url_discovery' have NULL
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    error_message TEXT,
    inspections_count INTEGER,
    output_file TEXT,
    created_at TEXT NOT NULL,
    succeeded_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_scrape_queue_status ON scrape_queue(status);
CREATE INDEX IF NOT EXISTS idx_scrape_queue_permit_number ON scrape_queue(permit_number);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scrape_queue_permit_id ON scrape_queue(permit_id);
"""

# In-scope B-permits from v4: the master/phase permits of structures, with the listed CapDetail href
V4_QUERY = """
WITH sp AS (
    SELECT DISTINCT se.structure_id, e.source_record_key AS permit_number
    FROM structure_events se JOIN events e USING (event_id)
    WHERE se.role_in_structure IN ('master', 'phase')
      AND e.source_record_key LIKE 'B%'
),
pp AS (   -- a permit's project; measured 2026-10-02: no master/phase permit spans two projects
    SELECT sp.permit_number, MIN(ps.project_id) AS project_id
    FROM sp LEFT JOIN project_structures ps USING (structure_id)
    GROUP BY sp.permit_number
)
SELECT
    pp.permit_number,
    pp.project_id,
    json_extract(p.notes, '$.address') AS project_address,
    (SELECT json_extract(a.raw_payload, '$.capdetail_href') FROM events a
      WHERE a.event_type_code = 'accela_listed' AND a.source_record_key = pp.permit_number
        AND json_extract(a.raw_payload, '$.capdetail_href') LIKE '%CapDetail.aspx%'
      ORDER BY a.event_id LIMIT 1) AS capdetail_href
FROM pp LEFT JOIN projects p ON p.project_id = pp.project_id
ORDER BY pp.permit_number;
"""


def permit_id_of(permit_number):
    """B2015-00006 -> 201500006: a stable integer id from the permit number itself."""
    m = re.fullmatch(r"B(\d{4})-(\d{5})", permit_number)
    if not m:
        raise ValueError(f"unexpected permit number shape: {permit_number!r}")
    return int(m.group(1)) * 100000 + int(m.group(2))


def url_and_capid(href):
    """Full CapDetail URL and the capID1-capID2-capID3 triplet, from the listed href."""
    if not href:
        return None, None
    url = href if href.startswith("http") else ACCELA_BASE + href
    q = parse_qs(urlparse(url).query)
    parts = [q.get(k, [""])[0] for k in ("capID1", "capID2", "capID3")]
    return url, ("-".join(parts) if all(parts) else None)


def main():
    parser = argparse.ArgumentParser(
        description="Build scrape queue from v4 in-scope B-permits"
    )
    parser.add_argument(
        "--v4-db", "--v2-db",
        dest="v4_db",
        default=DEFAULT_V4_DB,
        help=f"Path to v4 database, opened read-only (default: $BERKELEY_V4_DB or {DEFAULT_V4_DB}); "
             "--v2-db is a retired alias kept so old invocations still parse"
    )
    parser.add_argument(
        "--queue-db",
        default=DEFAULT_QUEUE_DB,
        help=f"Path to queue database (default: {DEFAULT_QUEUE_DB})"
    )
    args = parser.parse_args()

    v4_db_path = Path(args.v4_db)
    queue_db_path = Path(args.queue_db)

    print("=" * 60)
    print("Build Scrape Queue for Inspection Orchestrator")
    print("=" * 60)
    print()

    # Check v4 exists
    if not v4_db_path.exists():
        print(f"ERROR: v4 database not found at: {v4_db_path}")
        raise SystemExit(1)

    print(f"v4 database: {v4_db_path}")
    print(f"Queue database: {queue_db_path}")
    print()

    # Connect to v4 (read-only)
    v4_conn = sqlite3.connect(f"file:{v4_db_path}?mode=ro", uri=True)
    v4_conn.row_factory = sqlite3.Row

    # Query v4 for in-scope B-permits
    print("[1] Querying v4 for in-scope B-permits (master/phase permits of structures)...")
    rows = v4_conn.execute(V4_QUERY).fetchall()
    v4_conn.close()

    # A permit whose structure belongs to no project cannot fill the NOT NULL project_id: report, never invent
    no_project = [r["permit_number"] for r in rows if r["project_id"] is None]
    permits = [r for r in rows if r["project_id"] is not None]
    print(f"    Found {len(rows)} B-permits in scope; {len(no_project)} without a project "
          f"(not queued){': ' + ', '.join(no_project[:5]) if no_project else ''}")

    if len(permits) == 0:
        print("ERROR: Query returned 0 rows — something is wrong with v4 or query")
        raise SystemExit(1)

    # Connect to queue database (create if needed)
    print("\n[2] Setting up queue database...")
    queue_conn = sqlite3.connect(queue_db_path)
    queue_conn.row_factory = sqlite3.Row

    # Create schema
    queue_conn.executescript(SCHEMA_SQL)
    queue_conn.commit()
    print("    Schema ready")

    # Refuse to mix id spaces: an older queue keyed on v2 permit ids would get a second row per permit
    legacy = queue_conn.execute(
        "SELECT COUNT(*) FROM scrape_queue WHERE permit_id < ?", (V2_ID_CEILING,)).fetchone()[0]
    if legacy:
        print(f"ERROR: {queue_db_path} holds {legacy} v2-era rows (v2 permit ids). Point --queue-db "
              "at a fresh file; the v4 queue keys permits by their permit number.")
        raise SystemExit(1)

    # Classify and insert permits
    print("\n[3] Inserting permits into queue...")
    now = datetime.now().isoformat()
    inserted = 0
    skipped = 0
    pending_count = 0
    pending_url_discovery_count = 0

    for permit in permits:
        permit_number = permit["permit_number"]
        permit_id = permit_id_of(permit_number)
        project_id = permit["project_id"]
        project_address = permit["project_address"]
        url, capid_triplet = url_and_capid(permit["capdetail_href"])

        # Classify: has Accela URL?
        if url and "aca-prod.accela.com" in url:
            status = "pending"
            pending_count += 1
        else:
            status = "pending_url_discovery"
            url = None
            pending_url_discovery_count += 1

        # INSERT OR IGNORE (idempotent via unique index on permit_id)
        cursor = queue_conn.execute(
            """
            INSERT OR IGNORE INTO scrape_queue
                (permit_id, permit_number, project_id, project_address,
                 capid_triplet, url, status, attempts, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (permit_id, permit_number, project_id, project_address,
             capid_triplet, url, status, now)
        )
        if cursor.rowcount == 1:
            inserted += 1
        else:
            skipped += 1

    queue_conn.commit()
    print(f"    Inserted: {inserted}, Skipped (already existed): {skipped}")
    print(f"    Classified: {pending_count} pending, {pending_url_discovery_count} pending_url_discovery")

    # Final summary
    print("\n[4] Queue summary...")
    print("-" * 60)

    # Total rows
    total = queue_conn.execute("SELECT COUNT(*) FROM scrape_queue").fetchone()[0]
    print(f"Total rows in scrape_queue: {total}")

    # Count by status
    status_counts = queue_conn.execute(
        "SELECT status, COUNT(*) as cnt FROM scrape_queue GROUP BY status ORDER BY status"
    ).fetchall()
    print("\nCount by status:")
    for row in status_counts:
        print(f"  {row['status']}: {row['cnt']}")

    # The pending row(s)
    n_pending = queue_conn.execute(
        "SELECT COUNT(*) FROM scrape_queue WHERE status = 'pending'").fetchone()[0]
    pending_rows = queue_conn.execute(
        "SELECT * FROM scrape_queue WHERE status = 'pending' LIMIT 3"
    ).fetchall()
    print(f"\nSample rows with status='pending' (3 of {n_pending}):")
    for row in pending_rows:
        print(f"  id={row['id']}, permit_id={row['permit_id']}, "
              f"permit_number={row['permit_number']}, project_id={row['project_id']}, "
              f"project_address={row['project_address']}")
        print(f"    url={row['url'][:70]}..." if row['url'] else "    url=NULL")
        print(f"    capid_triplet={row['capid_triplet']}, status={row['status']}")

    # Sample pending_url_discovery rows
    sample_rows = queue_conn.execute(
        "SELECT * FROM scrape_queue WHERE status = 'pending_url_discovery' LIMIT 3"
    ).fetchall()
    print(f"\nSample rows with status='pending_url_discovery' (3 of many):")
    for row in sample_rows:
        print(f"  id={row['id']}, permit_id={row['permit_id']}, "
              f"permit_number={row['permit_number']}, project_id={row['project_id']}, "
              f"project_address={row['project_address']}")
        print(f"    url={row['url']}, capid_triplet={row['capid_triplet']}, status={row['status']}")

    # Conservation, not a pinned literal (the old "expected 91" moved the moment scope did):
    # every in-scope permit is either newly inserted or already queued, and each is in the queue.
    queued = {r[0] for r in queue_conn.execute("SELECT permit_number FROM scrape_queue")}
    missing = [p["permit_number"] for p in permits if p["permit_number"] not in queued]
    if inserted + skipped != len(permits) or missing:
        print(f"\n*** FLAG: {len(permits)} in scope but inserted+skipped={inserted + skipped}; "
              f"{len(missing)} not in queue: {missing[:5]} ***")
        raise SystemExit(1)
    print(f"\nConservation: all {len(permits)} in-scope permits are in the queue")

    queue_conn.close()

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
