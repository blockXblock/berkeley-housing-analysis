#!/usr/bin/env python3
"""
build_hcd_mirror.py — pull Berkeley APR data from California HCD's CKAN datastore
into a local SQLite mirror.

Drafted 2026-05-26 to replace the ad-hoc probe with a reproducible script.

Source: California HCD "Housing Element Annual Progress Report (APR) Data by
Jurisdiction and Year" package on data.ca.gov.
  Package ID: 81b0841f-2802-403e-b48e-2ef4b751f77c
  Endpoint:   https://data.ca.gov/api/3/action/datastore_search_sql

The mirror DB (`databases/hcd_apr_mirror.db`) is gitignored — this script is
the canonical method for regenerating it. Run anytime HCD's data updates.

Usage:
  python scripts/build_hcd_mirror.py             # build/refresh mirror
  python scripts/build_hcd_mirror.py --rebuild   # drop and rebuild from scratch
  python scripts/build_hcd_mirror.py --diagnose  # build + run doubling diagnostic
  python scripts/build_hcd_mirror.py --help

Idempotence: each run replaces per-table data atomically (drop + recreate within
a single transaction per table). Running twice produces the same final DB state.
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACKAGE_ID = "81b0841f-2802-403e-b48e-2ef4b751f77c"
BASE_URL = "https://data.ca.gov/api/3/action"

# All 12 APR table resources in the HCD package, as of 2026-05-26.
# (Name, resource_id) — the name becomes the SQLite table name.
RESOURCES = [
    ("table_a",  "c78b769d-cc02-4050-91ef-79ded665b5a8"),
    ("table_a2", "fe505d9b-8c36-42ba-ba30-08bc4f34e022"),
    ("table_c",  "a07dcd90-56bd-4a5e-9ce6-809e1f3fc121"),
    ("table_d",  "37724925-2014-4646-ade8-3ba9f3ff9fb8"),
    ("table_e",  "ec5124e6-a6ce-435d-82b1-0c963aaf15dd"),
    ("table_f",  "d8eb9333-7e85-4007-a96a-1fb06387b2e2"),
    ("table_f2", "16e640ab-c7e1-433c-8e4d-aa5a0a1270d1"),
    ("table_g",  "f68020cc-f245-43e1-a8ec-d7d2d6e42eae"),
    ("table_h",  "8e0e9d86-9a8a-4b3c-8089-8262404d9401"),
    ("table_i",  "575fe458-9e90-4a15-bca6-91e2bbcc463a"),
    ("table_k",  "c1407d6d-adc5-4f32-9cc9-1f022c4e2deb"),
    ("table_l",  "d3cda976-bffc-403d-a693-7eb1873e951a"),
]

# HCD's jurisdiction-field name varies across tables (including a typo in table_i).
# Order matters: try most-common first.
JURIS_FIELD_CANDIDATES = [
    "JURIS_NAME",
    "JURISDICTION",
    "JURISDICTION_NAME",
    "JURS_NAME",
    "JURIS",
    "JURISDICITON",  # HCD's own typo in table_i — yes really
]

JURISDICTION_VALUE = "BERKELEY"

# Indexes to create on table_a2 (Berkeley's main APR table)
INDEX_TABLE = "table_a2"
INDEX_COLUMNS = ["APN", "JURS_TRACKING_ID", "STREET_ADDRESS", "STD_ADDRESS", "YEAR"]

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "databases" / "hcd_apr_mirror.db"
CACHE_DIR = Path(f"/tmp/hcd_pull_{datetime.now().strftime('%Y-%m-%d')}")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_with_retry(method, url, *, max_retries=3, backoff=2.0, **kwargs):
    """GET/POST with simple exponential backoff on 429 / 5xx."""
    for attempt in range(max_retries):
        try:
            r = requests.request(method, url, timeout=kwargs.pop("timeout", 60), **kwargs)
            if r.status_code == 429 or 500 <= r.status_code < 600:
                if attempt < max_retries - 1:
                    sleep_s = backoff ** attempt
                    print(f"    HTTP {r.status_code} — retrying in {sleep_s}s", file=sys.stderr)
                    time.sleep(sleep_s)
                    continue
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                sleep_s = backoff ** attempt
                print(f"    {e} — retrying in {sleep_s}s", file=sys.stderr)
                time.sleep(sleep_s)
                continue
            raise


def probe_schema(resource_id):
    """Fetch field list + total row count for a resource."""
    r = _http_with_retry(
        "GET",
        f"{BASE_URL}/datastore_search",
        params={"resource_id": resource_id, "limit": 1},
        timeout=30,
    )
    return r.json()["result"]


def find_juris_field(field_ids):
    """Return the first jurisdiction-field candidate that exists in the schema."""
    for cand in JURIS_FIELD_CANDIDATES:
        if cand in field_ids:
            return cand
    return None


def pull_berkeley(resource_id, juris_field, cache_path):
    """SQL-query all Berkeley rows for a resource. Cache the raw response."""
    sql = f'SELECT * FROM "{resource_id}" WHERE "{juris_field}" = \'{JURISDICTION_VALUE}\''
    r = _http_with_retry(
        "POST",
        f"{BASE_URL}/datastore_search_sql",
        json={"sql": sql},
        timeout=120,
    )
    payload = r.json()
    if cache_path:
        cache_path.write_text(json.dumps(payload["result"], indent=2, default=str))
    return payload["result"].get("records", [])


# ---------------------------------------------------------------------------
# SQLite mirror builder
# ---------------------------------------------------------------------------

def _ensure_metadata_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS _pull_metadata (
            pulled_at TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            table_name TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            hcd_package_id TEXT NOT NULL,
            hcd_resource_url TEXT NOT NULL,
            schema_json TEXT NOT NULL,
            juris_field TEXT,
            error TEXT
        )
    """)


def _drop_table_if_exists(con, table_name):
    con.execute(f'DROP TABLE IF EXISTS "{table_name}"')


def _drop_indexes_for(con, table_name):
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
        (table_name,),
    ).fetchall()
    for (idx,) in rows:
        if not idx.startswith("sqlite_"):
            con.execute(f'DROP INDEX IF EXISTS "{idx}"')


def _create_indexes_on_table_a2(con):
    cols = {r[1] for r in con.execute('PRAGMA table_info(table_a2)').fetchall()}
    for col in INDEX_COLUMNS:
        if col in cols:
            con.execute(
                f'CREATE INDEX IF NOT EXISTS "idx_a2_{col.lower()}" '
                f'ON "table_a2"("{col}")'
            )


def build_mirror(rebuild=False):
    """Pull all 12 APR resources and build the mirror DB.

    Args:
        rebuild: if True, delete the entire DB file before building. Otherwise
                 per-table drop+recreate happens within the script.

    Returns:
        dict mapping table_name -> {row_count, error, juris_field}
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if rebuild and DB_PATH.exists():
        print(f"--rebuild: deleting existing {DB_PATH}")
        DB_PATH.unlink()

    con = sqlite3.connect(str(DB_PATH))
    _ensure_metadata_table(con)
    now = datetime.now(timezone.utc).isoformat()
    summary = {}

    for name, rid in RESOURCES:
        print(f"\n--- {name} ({rid}) ---")
        cache_schema = CACHE_DIR / f"schema_{name}.json"
        cache_pull   = CACHE_DIR / f"berkeley_{name}.json"
        error = None
        records = []
        fields = []
        juris_field = None

        try:
            schema = probe_schema(rid)
            cache_schema.write_text(json.dumps(schema, indent=2, default=str))
            fields = schema.get("fields", [])
            field_ids = [f["id"] for f in fields]
            juris_field = find_juris_field(field_ids)
            print(f"  total rows in resource: {schema.get('total')}")
            print(f"  juris field: {juris_field}")
            if juris_field:
                records = pull_berkeley(rid, juris_field, cache_pull)
                print(f"  Berkeley rows: {len(records)}")
            else:
                error = "no jurisdiction field found in schema"
                print(f"  SKIP: {error}")
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            print(f"  ERROR: {error}")

        # Build/refresh per-table data
        with con:
            _drop_indexes_for(con, name)
            _drop_table_if_exists(con, name)
            if records and fields:
                field_ids = [
                    f["id"] for f in fields
                    if f["id"] != "_id" and not f["id"].startswith("_")
                ]
                # CKAN sometimes includes _full_text — exclude
                field_ids = [c for c in field_ids if c != "_full_text"]
                col_defs = ", ".join(f'"{c}" TEXT' for c in field_ids)
                con.execute(f'CREATE TABLE "{name}" ({col_defs})')
                placeholders = ", ".join("?" for _ in field_ids)
                stmt = f'INSERT INTO "{name}" VALUES ({placeholders})'
                rows = [
                    tuple(
                        str(rec.get(c)) if rec.get(c) is not None else None
                        for c in field_ids
                    )
                    for rec in records
                ]
                con.executemany(stmt, rows)
            # Replace the metadata row for this table
            con.execute(
                "DELETE FROM _pull_metadata WHERE table_name = ?",
                (name,),
            )
            con.execute(
                """
                INSERT INTO _pull_metadata
                (pulled_at, resource_id, table_name, row_count, hcd_package_id,
                 hcd_resource_url, schema_json, juris_field, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    rid,
                    name,
                    len(records),
                    PACKAGE_ID,
                    (
                        f"https://data.ca.gov/dataset/{PACKAGE_ID}/"
                        f"resource/{rid}/download/{name}.csv"
                    ),
                    json.dumps(fields, default=str),
                    juris_field,
                    error,
                ),
            )

        summary[name] = {
            "row_count": len(records),
            "juris_field": juris_field,
            "error": error,
        }
        time.sleep(0.5)  # polite pacing between resources

    # Indexes on table_a2 (the main APR table)
    if con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (INDEX_TABLE,),
    ).fetchone():
        with con:
            _create_indexes_on_table_a2(con)

    con.close()
    return summary


# ---------------------------------------------------------------------------
# CY 2025 doubling diagnostic
# ---------------------------------------------------------------------------

def diagnose_cy2025_doubling(db_path=None):
    """Compute the doubling diagnostic against table_a2.

    Returns a structured dict:
        {
            "per_year_counts": {year: total_rows},
            "ratios": {year: {"total": N, "distinct_combos": M, "ratio": float}},
            "dup_clusters_cy2025": [{"apn", "street_address", "n", "distinct_tracking_ids"}],
            "schema_diff_sample": {"apn", "n_copies", "identical_cols", "differing_cols": [...]},
            "verdict": "doubling confirmed" or "no doubling",
        }
    """
    db_path = db_path or DB_PATH
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = con.cursor()
    report = {}

    cur.execute("SELECT YEAR, COUNT(*) FROM table_a2 GROUP BY YEAR ORDER BY YEAR")
    per_year = {r[0]: r[1] for r in cur.fetchall()}
    report["per_year_counts"] = per_year

    ratios = {}
    for year, total in per_year.items():
        cur.execute(
            "SELECT COUNT(DISTINCT APN || STREET_ADDRESS) FROM table_a2 WHERE YEAR=?",
            (year,),
        )
        distinct = cur.fetchone()[0]
        ratios[year] = {
            "total": total,
            "distinct_combos": distinct,
            "ratio": (total / distinct) if distinct else 0,
        }
    report["ratios"] = ratios

    # Duplicate clusters in CY 2025
    cur.execute("""
        SELECT APN, STREET_ADDRESS, COUNT(*) AS n,
               COUNT(DISTINCT JURS_TRACKING_ID) AS distinct_tracking
        FROM table_a2 WHERE YEAR='2025'
        GROUP BY APN, STREET_ADDRESS
        HAVING COUNT(*) > 1
        ORDER BY n DESC
    """)
    dup_clusters = [
        {
            "apn": r[0],
            "street_address": r[1],
            "n_rows": r[2],
            "distinct_tracking_ids": r[3],
        }
        for r in cur.fetchall()
    ]
    report["dup_clusters_cy2025"] = dup_clusters

    # Field-level diff on the largest duplicate cluster
    schema_diff_sample = None
    if dup_clusters:
        top = dup_clusters[0]
        cur.execute(
            'SELECT * FROM table_a2 WHERE YEAR="2025" AND APN=? AND STREET_ADDRESS=?',
            (top["apn"], top["street_address"]),
        )
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description]
        identical, differing = [], []
        for ci, col in enumerate(col_names):
            vals = {r[ci] for r in rows}
            (identical if len(vals) == 1 else differing).append(col)
        schema_diff_sample = {
            "apn": top["apn"],
            "street_address": top["street_address"],
            "n_copies": len(rows),
            "identical_cols": len(identical),
            "differing_cols": differing,
        }
    report["schema_diff_sample"] = schema_diff_sample

    # Verdict
    cy25 = ratios.get("2025") or {}
    report["verdict"] = (
        "doubling confirmed in CY 2025 — ratio > 1.5"
        if cy25.get("ratio", 0) > 1.5
        else "no doubling detected"
    )

    # Total CY 2025 duplicate-row count
    total_2025 = per_year.get("2025", 0)
    distinct_2025 = ratios.get("2025", {}).get("distinct_combos", 0)
    cur.execute("""
        SELECT SUM(n - 1) FROM (
            SELECT COUNT(*) AS n FROM table_a2 WHERE YEAR='2025'
            GROUP BY APN, STREET_ADDRESS, JURS_TRACKING_ID
            HAVING COUNT(*) > 1
        )
    """)
    excess_2025 = cur.fetchone()[0] or 0
    report["excess_duplicate_rows_cy2025"] = excess_2025

    con.close()
    return report


def print_diagnostic_report(report):
    print("\n" + "=" * 72)
    print("CY 2025 doubling diagnostic")
    print("=" * 72)
    print("\nPer-year row counts (table_a2, Berkeley):")
    for y, n in sorted(report["per_year_counts"].items()):
        print(f"  YEAR={y}: {n}")
    print("\nPer-year ratio of total rows / distinct (APN+STREET_ADDRESS):")
    for y, info in sorted(report["ratios"].items()):
        marker = "  ← anomalous" if info["ratio"] > 1.5 else ""
        print(
            f"  YEAR={y}: total={info['total']:>4} distinct={info['distinct_combos']:>4} "
            f"ratio={info['ratio']:.2f}{marker}"
        )
    print(f"\nCY 2025 duplicate clusters (groups by APN+STREET_ADDRESS with n>1):"
          f"  {len(report['dup_clusters_cy2025'])}")
    for cluster in report["dup_clusters_cy2025"][:10]:
        print(
            f"  APN={cluster['apn']!r:18} addr={cluster['street_address']!r:38} "
            f"n={cluster['n_rows']}  distinct_tracking={cluster['distinct_tracking_ids']}"
        )
    if report["schema_diff_sample"]:
        s = report["schema_diff_sample"]
        print(
            f"\nField-level diff inside the largest cluster "
            f"({s['n_copies']} copies of APN={s['apn']}):"
        )
        print(f"  {s['identical_cols']} columns identical across all copies")
        print(f"  {len(s['differing_cols'])} columns differ: {s['differing_cols']}")
    print(f"\nExcess duplicate rows in CY 2025 (rows that are exact field-copies of another): "
          f"{report['excess_duplicate_rows_cy2025']}")
    print(f"\nVerdict: {report['verdict']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    global DB_PATH
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--rebuild", action="store_true",
                    help="delete the DB file before building (default: per-table refresh)")
    ap.add_argument("--diagnose", action="store_true",
                    help="run the CY 2025 doubling diagnostic after building")
    ap.add_argument("--db-path", default=None,
                    help="override DB path (default: databases/hcd_apr_mirror.db)")
    args = ap.parse_args()

    if args.db_path:
        DB_PATH = Path(args.db_path)

    print(f"DB path:    {DB_PATH}")
    print(f"Cache dir:  {CACHE_DIR}")
    print(f"Resources:  {len(RESOURCES)}")
    summary = build_mirror(rebuild=args.rebuild)

    print("\n" + "=" * 72)
    print("Build summary")
    print("=" * 72)
    for name, info in summary.items():
        print(f"  {name:<10} rows={info['row_count']:>5}  "
              f"juris={info['juris_field']!r:<22} "
              f"error={info['error'] or ''}")

    if args.diagnose:
        report = diagnose_cy2025_doubling()
        print_diagnostic_report(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
