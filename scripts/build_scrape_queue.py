#!/usr/bin/env python3
"""
Build the scrape queue for the inspection orchestrator.

Reads v2 database (read-only) to find all in-scope B-permits,
classifies them by URL availability, and populates cic_recon_queue.db.

Usage:
    python3 build_scrape_queue.py

The script is idempotent: re-running adds only new permits.
"""

import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Default paths
DEFAULT_V2_DB = os.environ.get(
    "BERKELEY_V2_DB",
    str(Path.home() / "berkeley-data" / "databases" / "berkeley_housing_v2.db")
)
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

# Query to find in-scope B-permits from v2
V2_QUERY = """
SELECT
    p.id AS permit_id,
    p.permit_number,
    p.project_id,
    pr.canonical_address AS project_address,
    p.source_url,
    p.source_permit_id AS capid_triplet
FROM permits p
JOIN projects pr ON p.project_id = pr.id
JOIN vocabulary_stage_types vst ON pr.current_stage_type_id = vst.id
WHERE vst.code IN ('completed', 'under_construction')
  AND p.permit_number LIKE 'B%'
ORDER BY p.permit_number;
"""


def main():
    parser = argparse.ArgumentParser(
        description="Build scrape queue from v2 in-scope B-permits"
    )
    parser.add_argument(
        "--v2-db",
        default=DEFAULT_V2_DB,
        help=f"Path to v2 database (default: $BERKELEY_V2_DB or {DEFAULT_V2_DB})"
    )
    parser.add_argument(
        "--queue-db",
        default=DEFAULT_QUEUE_DB,
        help=f"Path to queue database (default: {DEFAULT_QUEUE_DB})"
    )
    args = parser.parse_args()

    v2_db_path = Path(args.v2_db)
    queue_db_path = Path(args.queue_db)

    print("=" * 60)
    print("Build Scrape Queue for Inspection Orchestrator")
    print("=" * 60)
    print()

    # Check v2 exists
    if not v2_db_path.exists():
        print(f"ERROR: v2 database not found at: {v2_db_path}")
        raise SystemExit(1)

    print(f"v2 database: {v2_db_path}")
    print(f"Queue database: {queue_db_path}")
    print()

    # Connect to v2 (read-only)
    v2_uri = f"file:{v2_db_path}?mode=ro"
    v2_conn = sqlite3.connect(v2_uri, uri=True)
    v2_conn.row_factory = sqlite3.Row

    # Query v2 for in-scope B-permits
    print("[1] Querying v2 for in-scope B-permits...")
    cursor = v2_conn.execute(V2_QUERY)
    permits = cursor.fetchall()
    v2_conn.close()

    print(f"    Found {len(permits)} B-permits in scope")

    # Sanity checks
    if len(permits) == 0:
        print("ERROR: Query returned 0 rows — something is wrong with v2 or query")
        raise SystemExit(1)

    if len(permits) < 80 or len(permits) > 100:
        print(f"    *** FLAG: Row count {len(permits)} outside expected range 80-100 ***")

    # Connect to queue database (create if needed)
    print("\n[2] Setting up queue database...")
    queue_conn = sqlite3.connect(queue_db_path)
    queue_conn.row_factory = sqlite3.Row

    # Create schema
    queue_conn.executescript(SCHEMA_SQL)
    queue_conn.commit()
    print("    Schema ready")

    # Classify and insert permits
    print("\n[3] Inserting permits into queue...")
    now = datetime.now().isoformat()
    inserted = 0
    skipped = 0
    pending_count = 0
    pending_url_discovery_count = 0

    for permit in permits:
        permit_id = permit["permit_id"]
        permit_number = permit["permit_number"]
        project_id = permit["project_id"]
        project_address = permit["project_address"]
        source_url = permit["source_url"]
        capid_triplet = permit["capid_triplet"]

        # Classify: has Accela URL?
        if source_url and "aca-prod.accela.com" in source_url:
            status = "pending"
            url = source_url
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
    pending_rows = queue_conn.execute(
        "SELECT * FROM scrape_queue WHERE status = 'pending'"
    ).fetchall()
    print(f"\nRows with status='pending' ({len(pending_rows)} total):")
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

    # Flag if count doesn't match expected
    expected_total = 91
    if total != expected_total:
        print(f"\n*** FLAG: Total rows ({total}) != expected ({expected_total}) ***")

    queue_conn.close()

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
