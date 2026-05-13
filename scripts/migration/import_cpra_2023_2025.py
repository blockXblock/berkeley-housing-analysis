#!/usr/bin/env python3
"""
CPRA 2023-2025 Import Script for Berkeley Housing v2

Imports building permit data from CPRA (California Public Records Act) response
into the v2 database. Based on locked decisions in:
  /Users/johngage/berkeley-data/docs/migration/cpra_import_plan.md (§14, §16)

Key decisions:
  - §14.1b: Master permits only (drop sub-permits)
  - §14.2b: Match existing projects + create new R-2 projects ≥5 units
  - §16: Tightened matching (exact StreetNumber + fuzzy StreetName ≥90%)

Usage:
    python import_cpra_2023_2025.py --dry-run --limit 10
    python import_cpra_2023_2025.py --dry-run
    python import_cpra_2023_2025.py  # Full import

Outputs:
    - Log file: scripts/migration/logs/cpra_import_YYYY-MM-DD.log
    - Summary report: scripts/migration/logs/cpra_import_YYYY-MM-DD_summary.md
"""

import argparse
import logging
import os
import re
import sqlite3
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add parent directory to path for cpra_dedup import
sys.path.insert(0, str(Path(__file__).parent.parent))
from cpra_dedup import load_cpra, dedupe_permits, normalize_apn

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("Warning: rapidfuzz not installed. Install with: pip install rapidfuzz")


# === Configuration ===

CPRA_FILE = Path.home() / "Library/CloudStorage/GoogleDrive-[redacted-email]/My Drive/Corridors/BP-downloads/BP_Annual Permit Report.xlsx"
V2_DB = Path(__file__).parent.parent.parent / "databases/berkeley_housing_v2.db"
LOG_DIR = Path(__file__).parent / "logs"

# Vocabulary IDs from v2 database
VOCAB = {
    'permit_type': {
        'building': 5,
        'demo': 6,
    },
    'event_type': {
        'building_permit_issued': 14,
        'demo_permit_issued': 13,
        'co_issued': 17,
    },
    'permit_status': {
        'issued': 5,
        'finaled': 7,
    }
}

# §16: False positives to skip (inflated unit counts from existing buildings)
SKIP_PERMITS = {'B2025-03731', 'B2024-05284', 'B2024-04593'}

# §17: Projects to exclude from ALL matching (APN and fuzzy)
# Project 93 (1312 ADDISON St): v1 stored wrong APN (056199300100) which actually
# points to 2200 Acton St (unrelated single-family home). Until corrected, exclude
# project 93 from all match types to prevent false-positive permits.
# False positives prevented: B2023-01651, B2024-05921, B2025-00577 (all at 2200 Acton)
EXCLUDE_PROJECTS = {93}

# §16: New R-2 projects to create (verified genuine new construction)
NEW_R2_PROJECTS = [
    {
        'permit_number': 'B2022-05957',
        'address': '2328 CHANNING Way',
        'apn': '055188200900',
        'units': 13,
        'description': 'Construct new (e)(3) 4 story apartment building with 13 dwelling units',
    },
    {
        'permit_number': 'B2025-00168',
        'address': '2330 BLAKE St',
        'apn': '055182301303',
        'units': 6,
        'description': 'ADU new construction - 6 new detached ADUs',
    },
]

# Matching thresholds
FUZZY_THRESHOLD = 90  # Minimum similarity for fuzzy address match

# Validation thresholds (expected counts after import)
# Note: finaled_date counts determined by dry-run analysis of CPRA source data
VALIDATION = {
    'v2_permits_before': 118,
    'v2_permits_after': 239,   # 118 + 121 new permits
    'v2_projects_before': 179,
    'v2_projects_after': 181,  # 179 + 2 new R-2 projects
    'permits_to_insert': 121,  # 118 APN + 1 fuzzy + 2 new R-2 (excludes project 93 entirely)
    'finaled_date_min_ratio': 0.80,  # Post-import count must be >= 80% of pre-computed source count
}


# === Logging Setup ===

def setup_logging(dry_run: bool) -> logging.Logger:
    """Configure logging to file and console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime('%Y-%m-%d')
    suffix = '_dryrun' if dry_run else ''
    log_file = LOG_DIR / f"cpra_import_{date_str}{suffix}.log"

    logger = logging.getLogger('cpra_import')
    logger.setLevel(logging.DEBUG)

    # File handler (detailed)
    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-7s | %(message)s'))
    logger.addHandler(fh)

    # Console handler (info+)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(levelname)-7s | %(message)s'))
    logger.addHandler(ch)

    return logger, log_file


# === Address Normalization ===

def normalize_street_name(name: str) -> str:
    """Normalize street name for fuzzy matching."""
    if pd.isna(name):
        return ""
    name = str(name).upper().strip()
    # Remove common suffixes
    for suffix in ['ST', 'AVE', 'WAY', 'BLVD', 'DR', 'CT', 'PL', 'RD', 'LN']:
        if name.endswith(' ' + suffix):
            name = name[:-len(suffix)-1].strip()
    return name


def normalize_street_number(num) -> str:
    """Normalize street number to string.

    Handles both numeric types (1581.0) and string representations ("1581.0").
    Converts to integer string format ("1581") for consistent comparison.
    """
    if pd.isna(num):
        return ""
    # Convert to string first
    num_str = str(num).strip()
    if not num_str:
        return ""
    # Try to parse as float then convert to int (handles "1581.0" -> "1581")
    try:
        return str(int(float(num_str)))
    except (ValueError, TypeError):
        # If not a valid number, return as-is (e.g., "12A" stays "12A")
        return num_str


def fuzzy_match_address(cpra_addr: dict, v2_addr: str) -> tuple[bool, float]:
    """
    Match CPRA address components against v2 address string.

    §16 Tightened matching:
    - Exact match on StreetNumber
    - Fuzzy match on StreetName (≥90% similarity)

    Returns (is_match, similarity_score)
    """
    if not RAPIDFUZZ_AVAILABLE:
        return False, 0.0

    cpra_num = normalize_street_number(cpra_addr.get('StreetNumber', ''))
    cpra_name = normalize_street_name(cpra_addr.get('StreetName', ''))

    if not cpra_num or not v2_addr:
        return False, 0.0

    v2_upper = v2_addr.upper().strip()

    # Check exact street number match
    # v2 address format: "1234 STREET Name" or "1234 Street Name Ave"
    v2_parts = v2_upper.split()
    if not v2_parts:
        return False, 0.0

    v2_num = v2_parts[0]
    if cpra_num != v2_num:
        return False, 0.0

    # Fuzzy match on street name
    v2_name = normalize_street_name(' '.join(v2_parts[1:]))

    if not cpra_name or not v2_name:
        return False, 0.0

    similarity = fuzz.ratio(cpra_name, v2_name)
    return similarity >= FUZZY_THRESHOLD, similarity


# === Database Operations ===

def get_v2_projects(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load v2 projects with addresses and APNs."""
    query = """
    SELECT
        p.id as project_id,
        p.canonical_name as project_name,
        p.canonical_address as address,
        GROUP_CONCAT(DISTINCT pa.apn) as apns
    FROM projects p
    LEFT JOIN project_parcels pp ON p.id = pp.project_id
    LEFT JOIN parcels pa ON pp.parcel_id = pa.id
    GROUP BY p.id
    """
    df = pd.read_sql_query(query, conn)
    df['norm_apns'] = df['apns'].apply(
        lambda x: set(normalize_apn(a) for a in str(x).split(',') if a and a != 'None') if x else set()
    )
    return df


def get_existing_permits(conn: sqlite3.Connection) -> set:
    """Get set of existing permit numbers in v2."""
    cursor = conn.execute("SELECT permit_number FROM permits WHERE permit_number IS NOT NULL")
    return {row[0] for row in cursor.fetchall()}


def match_permit_to_project(permit_row: pd.Series, v2_projects: pd.DataFrame, logger: logging.Logger) -> int | None:
    """
    Match a CPRA permit to a v2 project.

    Matching strategy (per §16):
    1. Exact APN match
    2. Fuzzy address match (exact StreetNumber + fuzzy StreetName ≥90%)

    §17: Excluded projects are skipped for ALL match types (APN and fuzzy).

    Returns project_id or None
    """
    cpra_apn = normalize_apn(permit_row.get('apn', ''))

    # Try exact APN match first
    if cpra_apn:
        for _, proj in v2_projects.iterrows():
            if cpra_apn in proj['norm_apns']:
                project_id = proj['project_id']
                # §17: Skip excluded projects for APN matching
                if project_id in EXCLUDE_PROJECTS:
                    logger.info(f"  SKIP: Would match project {project_id} via APN but project {project_id} excluded (manual investigation pending)")
                    continue
                logger.debug(f"  APN match: {cpra_apn} -> project {project_id}")
                return project_id

    # Try fuzzy address match
    cpra_addr = {
        'StreetNumber': permit_row.get('address', '').split()[0] if permit_row.get('address') else '',
        'StreetName': ' '.join(permit_row.get('address', '').split()[1:]) if permit_row.get('address') else '',
    }

    best_match = None
    best_score = 0

    for _, proj in v2_projects.iterrows():
        project_id = proj['project_id']
        is_match, score = fuzzy_match_address(cpra_addr, proj['address'])

        if is_match:
            # §17: Skip excluded projects for fuzzy matching
            if project_id in EXCLUDE_PROJECTS:
                logger.info(f"  SKIP: Would match project {project_id} via fuzzy but project {project_id} excluded (manual investigation pending)")
                continue

            if score > best_score:
                best_match = project_id
                best_score = score

    if best_match:
        logger.debug(f"  Address match: {permit_row.get('address')} -> project {best_match} (score: {best_score})")

    return best_match


def determine_permit_type(permit_row: pd.Series) -> str:
    """Determine if permit is building or demo based on work type/description."""
    work_type = str(permit_row.get('work_type', '')).upper()
    description = str(permit_row.get('description', '')).upper()

    demo_keywords = ['DEMOLITION', 'DEMO', 'DEMOLISH', 'RAZE']

    if any(kw in work_type for kw in demo_keywords) or any(kw in description for kw in demo_keywords):
        return 'demo'
    return 'building'


def insert_permit(conn: sqlite3.Connection, project_id: int, permit_row: pd.Series,
                  dry_run: bool, logger: logging.Logger) -> int | None:
    """
    Insert a permit into v2 database.

    Returns permit_id or None if skipped/dry-run.
    """
    permit_number = permit_row.get('master_permit')
    permit_type = determine_permit_type(permit_row)
    permit_type_id = VOCAB['permit_type'][permit_type]

    # Determine status
    finaled_date = permit_row.get('finaled_date') or permit_row.get('Finaled Date')
    if pd.notna(finaled_date):
        status_id = VOCAB['permit_status']['finaled']
    else:
        status_id = VOCAB['permit_status']['issued']

    # Parse dates
    issued_date = permit_row.get('issue_date')
    if pd.notna(issued_date):
        issued_date = pd.to_datetime(issued_date).strftime('%Y-%m-%d')
    else:
        issued_date = None

    if pd.notna(finaled_date):
        finaled_date = pd.to_datetime(finaled_date).strftime('%Y-%m-%d')
    else:
        finaled_date = None

    valuation = permit_row.get('job_valuation')
    if pd.isna(valuation):
        valuation = None

    description = permit_row.get('description', '')
    if pd.isna(description):
        description = None

    logger.info(f"  INSERT permit: {permit_number} -> project {project_id} (type={permit_type})")

    if dry_run:
        return None

    cursor = conn.execute("""
        INSERT OR IGNORE INTO permits
        (project_id, source_system, permit_number, permit_type_id,
         permit_status_type_id, issued_date, finaled_date, valuation, description)
        VALUES (?, 'cpra', ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, permit_number, permit_type_id, status_id,
          issued_date, finaled_date, valuation, description))

    if cursor.rowcount == 0:
        logger.debug(f"  Permit {permit_number} already exists (skipped)")
        return None

    return cursor.lastrowid


def insert_permit_event(conn: sqlite3.Connection, project_id: int, permit_id: int | None,
                        event_type: str, event_date: str, permit_number: str,
                        dry_run: bool, logger: logging.Logger) -> int | None:
    """Insert a project event for the permit."""
    event_type_id = VOCAB['event_type'][event_type]

    summary = f"{event_type.replace('_', ' ').title()}: {permit_number}"

    logger.info(f"  INSERT event: {event_type} on {event_date}")

    if dry_run:
        return None

    cursor = conn.execute("""
        INSERT INTO project_events
        (project_id, event_type_id, event_date, permit_id, summary, is_inferred)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (project_id, event_type_id, event_date, permit_id, summary))

    return cursor.lastrowid


def create_new_project(conn: sqlite3.Connection, project_info: dict,
                       dry_run: bool, logger: logging.Logger) -> int | None:
    """Create a new project for an unmatched R-2 permit."""
    address = project_info['address']

    logger.info(f"  CREATE project: {address} ({project_info['units']} units)")

    if dry_run:
        return None

    cursor = conn.execute("""
        INSERT INTO projects (canonical_name, canonical_address, city_id)
        VALUES (?, ?, 1)
    """, (address, address))

    project_id = cursor.lastrowid

    # Create parcel if APN provided
    apn = project_info.get('apn')
    if apn:
        # Check if parcel exists
        existing = conn.execute(
            "SELECT id FROM parcels WHERE apn = ?", (apn,)
        ).fetchone()

        if existing:
            parcel_id = existing[0]
        else:
            cursor = conn.execute(
                "INSERT INTO parcels (apn, city_id) VALUES (?, 1)", (apn,)
            )
            parcel_id = cursor.lastrowid

        # Link parcel to project
        conn.execute(
            "INSERT OR IGNORE INTO project_parcels (project_id, parcel_id) VALUES (?, ?)",
            (project_id, parcel_id)
        )

    return project_id


def validate_import(conn: sqlite3.Connection, stats: dict, logger: logging.Logger) -> tuple[bool, str]:
    """
    Validate import results before committing.

    Returns (is_valid, error_message). If is_valid is True, error_message is empty.
    """
    errors = []

    # Check permit count
    cursor = conn.execute("SELECT COUNT(*) FROM permits")
    permit_count = cursor.fetchone()[0]
    expected_permits = VALIDATION['v2_permits_after']
    if permit_count != expected_permits:
        errors.append(f"Permit count mismatch: expected {expected_permits}, got {permit_count}")

    # Check project count
    cursor = conn.execute("SELECT COUNT(*) FROM projects")
    project_count = cursor.fetchone()[0]
    expected_projects = VALIDATION['v2_projects_after']
    if project_count != expected_projects:
        errors.append(f"Project count mismatch: expected {expected_projects}, got {project_count}")

    # Check FK integrity
    cursor = conn.execute("PRAGMA foreign_key_check")
    fk_errors = cursor.fetchall()
    if fk_errors:
        errors.append(f"FK integrity violations: {len(fk_errors)} errors")
        for err in fk_errors[:5]:  # Log first 5
            logger.error(f"  FK error: {err}")

    # Check no NULL project_ids in permits (except for orphaned permits)
    cursor = conn.execute("""
        SELECT COUNT(*) FROM permits
        WHERE project_id IS NULL AND source_system = 'cpra'
    """)
    null_projects = cursor.fetchone()[0]
    if null_projects > 0:
        errors.append(f"CPRA permits with NULL project_id: {null_projects}")

    # Check no duplicate permit_numbers
    cursor = conn.execute("""
        SELECT permit_number, COUNT(*) as cnt FROM permits
        GROUP BY permit_number HAVING cnt > 1
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        errors.append(f"Duplicate permit numbers: {[d[0] for d in duplicates[:5]]}")

    # Validate finaled_date counts against pre-computed source count
    # Post-import count must be >= 80% of pre-computed source count
    cursor = conn.execute("""
        SELECT COUNT(*) FROM permits
        WHERE source_system = 'cpra' AND finaled_date IS NOT NULL
    """)
    db_finaled_count = cursor.fetchone()[0]
    source_finaled_count = stats.get('source_finaled_count', 0)
    tracked_finaled_count = stats.get('permits_with_finaled_date', 0)
    min_ratio = VALIDATION.get('finaled_date_min_ratio', 0.80)

    logger.info(f"  finaled_date validation:")
    logger.info(f"    Pre-computed source count: {source_finaled_count}")
    logger.info(f"    Tracked during import:     {tracked_finaled_count}")
    logger.info(f"    Actual in DB:              {db_finaled_count}")

    if source_finaled_count > 0:
        actual_ratio = db_finaled_count / source_finaled_count
        if actual_ratio < min_ratio:
            errors.append(
                f"finaled_date completeness failed: {db_finaled_count}/{source_finaled_count} "
                f"({actual_ratio:.0%}) < {min_ratio:.0%} threshold"
            )
            logger.error(f"    FAIL: {actual_ratio:.0%} < {min_ratio:.0%} threshold")
        else:
            logger.info(f"    PASS: {actual_ratio:.0%} >= {min_ratio:.0%} threshold")

    # Validate co_issued event counts against pre-computed source count
    # (one co_issued event expected per finaled permit)
    cursor = conn.execute("""
        SELECT COUNT(*) FROM project_events
        WHERE event_type_id = ?
        AND permit_id IN (SELECT id FROM permits WHERE source_system = 'cpra')
    """, (VOCAB['event_type']['co_issued'],))
    db_co_issued_count = cursor.fetchone()[0]
    tracked_co_issued_count = stats.get('co_issued_events', 0)

    logger.info(f"  co_issued event validation:")
    logger.info(f"    Expected (= source finaled): {source_finaled_count}")
    logger.info(f"    Tracked during import:       {tracked_co_issued_count}")
    logger.info(f"    Actual in DB:                {db_co_issued_count}")

    if source_finaled_count > 0:
        actual_ratio = db_co_issued_count / source_finaled_count
        if actual_ratio < min_ratio:
            errors.append(
                f"co_issued event completeness failed: {db_co_issued_count}/{source_finaled_count} "
                f"({actual_ratio:.0%}) < {min_ratio:.0%} threshold"
            )
            logger.error(f"    FAIL: {actual_ratio:.0%} < {min_ratio:.0%} threshold")
        else:
            logger.info(f"    PASS: {actual_ratio:.0%} >= {min_ratio:.0%} threshold")

    if errors:
        return False, "; ".join(errors)
    return True, ""


# === Main Import Logic ===

def run_import(dry_run: bool = True, limit: int | None = None) -> dict:
    """
    Run the CPRA import process.

    Returns summary statistics dict.
    """
    logger, log_file = setup_logging(dry_run)

    mode = "DRY-RUN" if dry_run else "LIVE"
    logger.info(f"=== CPRA Import Started ({mode}) ===")
    logger.info(f"CPRA file: {CPRA_FILE}")
    logger.info(f"V2 database: {V2_DB}")
    if limit:
        logger.info(f"Limit: {limit} permits")

    # Load CPRA data
    logger.info("Loading CPRA data...")
    cpra_raw = load_cpra(CPRA_FILE)
    logger.info(f"  Loaded {len(cpra_raw)} raw permits")

    # Deduplicate to master permits only (§14.1b)
    logger.info("Deduplicating to master permits...")
    cpra = dedupe_permits(cpra_raw)
    logger.info(f"  {len(cpra)} master permits after deduplication")

    # Filter to 2023-2025
    cpra = cpra[cpra['issue_year'].isin([2023, 2024, 2025])].copy()
    logger.info(f"  {len(cpra)} permits in 2023-2025")

    # Remove false positives (§16)
    before_skip = len(cpra)
    cpra = cpra[~cpra['master_permit'].isin(SKIP_PERMITS)]
    skipped = before_skip - len(cpra)
    if skipped > 0:
        logger.info(f"  Skipped {skipped} false positive permits: {SKIP_PERMITS}")

    # Apply limit if specified
    if limit:
        cpra = cpra.head(limit)
        logger.info(f"  Limited to {len(cpra)} permits for testing")

    # Connect to v2
    logger.info("Connecting to v2 database...")
    conn = sqlite3.connect(V2_DB)
    conn.execute("PRAGMA foreign_keys = ON")

    # Load v2 projects (before transaction - read-only)
    v2_projects = get_v2_projects(conn)
    logger.info(f"  Loaded {len(v2_projects)} v2 projects")

    # Get existing permits (before transaction - read-only)
    existing_permits = get_existing_permits(conn)
    logger.info(f"  Found {len(existing_permits)} existing permits in v2")

    # Statistics
    stats = {
        'total_cpra_permits': len(cpra),
        'already_exist': 0,
        'matched': 0,
        'matched_inserted': 0,
        'unmatched': 0,
        'new_projects_created': 0,
        'events_created': 0,
        'co_issued_events': 0,
        'permits_with_finaled_date': 0,
        'errors': 0,
    }

    # Pre-compute expected finaled_date count from CPRA source
    # This counts permits in our import scope that have finaled_date populated
    logger.info("")
    logger.info("=== Pre-Computing Source Counts ===")

    # Count finaled_date in permits that will be matched (not in existing, will match a project)
    source_finaled_count = 0
    for _, permit in cpra.iterrows():
        permit_number = permit['master_permit']
        if permit_number in existing_permits:
            continue
        # Check if this permit will be matched
        project_id = match_permit_to_project(permit, v2_projects, logging.getLogger('cpra_import_precompute'))
        if project_id:
            if pd.notna(permit.get('finaled_date')):
                source_finaled_count += 1

    # Also count new R-2 projects with finaled_date
    for proj_info in NEW_R2_PROJECTS:
        permit_number = proj_info['permit_number']
        if permit_number not in existing_permits:
            permit_row = cpra_raw[cpra_raw['PermitNumber'] == permit_number]
            if len(permit_row) > 0:
                if pd.notna(permit_row.iloc[0].get('Finaled Date')):
                    source_finaled_count += 1

    stats['source_finaled_count'] = source_finaled_count
    logger.info(f"  Source permits with Finaled Date (in import scope): {source_finaled_count}")

    # Begin transaction (single-transaction mode)
    logger.info("")
    if dry_run:
        logger.info("=== DRY-RUN MODE (no database changes) ===")
    else:
        logger.info("=== Beginning transaction (single-transaction mode) ===")
        conn.execute("BEGIN TRANSACTION")

    try:
        # Process permits
        logger.info("")
        logger.info("=== Processing Permits ===")

        for idx, (_, permit) in enumerate(cpra.iterrows()):
            permit_number = permit['master_permit']
            address = permit.get('address', 'Unknown')

            logger.info(f"[{idx+1}/{len(cpra)}] {permit_number} @ {address}")

            # Skip if already exists
            if permit_number in existing_permits:
                logger.info(f"  SKIP: Already exists in v2")
                stats['already_exist'] += 1
                continue

            # Try to match to v2 project
            project_id = match_permit_to_project(permit, v2_projects, logger)

            if project_id:
                stats['matched'] += 1

                # Insert permit
                permit_id = insert_permit(conn, project_id, permit, dry_run, logger)
                if permit_id or dry_run:
                    stats['matched_inserted'] += 1

                # Insert issued event
                issued_date = permit.get('issue_date')
                if pd.notna(issued_date):
                    issued_str = pd.to_datetime(issued_date).strftime('%Y-%m-%d')
                    permit_type = determine_permit_type(permit)
                    event_type = f'{permit_type}_permit_issued'
                    insert_permit_event(conn, project_id, permit_id, event_type,
                                        issued_str, permit_number, dry_run, logger)
                    stats['events_created'] += 1

                # Insert CO event if finaled
                finaled_date = permit.get('finaled_date')
                if pd.notna(finaled_date):
                    finaled_str = pd.to_datetime(finaled_date).strftime('%Y-%m-%d')
                    insert_permit_event(conn, project_id, permit_id, 'co_issued',
                                        finaled_str, permit_number, dry_run, logger)
                    stats['events_created'] += 1
                    stats['co_issued_events'] += 1
                    stats['permits_with_finaled_date'] += 1
            else:
                stats['unmatched'] += 1
                logger.info(f"  NO MATCH: Permit not linked to any v2 project")

            # Progress logging every 100 permits
            if (idx + 1) % 100 == 0:
                logger.info(f"  Progress: {idx + 1}/{len(cpra)} permits processed...")

        # Create new R-2 projects (§16)
        logger.info("")
        logger.info("=== Creating New R-2 Projects ===")

        for proj_info in NEW_R2_PROJECTS:
            permit_number = proj_info['permit_number']

            # Skip if already processed above or exists
            if permit_number in existing_permits:
                logger.info(f"SKIP {permit_number}: Already exists")
                continue

            logger.info(f"Creating project for {permit_number}")

            project_id = create_new_project(conn, proj_info, dry_run, logger)

            if project_id or dry_run:
                stats['new_projects_created'] += 1

                # Find the permit in CPRA data to get dates
                permit_row = cpra_raw[cpra_raw['PermitNumber'] == permit_number]
                if len(permit_row) > 0:
                    permit_data = permit_row.iloc[0]

                    # Parse dates
                    issued_date = permit_data.get('Issuance Date')
                    if pd.notna(issued_date):
                        issued_str = pd.to_datetime(issued_date).strftime('%Y-%m-%d')
                    else:
                        issued_str = None

                    finaled_date = permit_data.get('Finaled Date')
                    if pd.notna(finaled_date):
                        finaled_str = pd.to_datetime(finaled_date).strftime('%Y-%m-%d')
                        status_id = VOCAB['permit_status']['finaled']
                    else:
                        finaled_str = None
                        status_id = VOCAB['permit_status']['issued']

                    # Create permit record
                    permit_id = None
                    if not dry_run and project_id:
                        cursor = conn.execute("""
                            INSERT OR IGNORE INTO permits
                            (project_id, source_system, permit_number, permit_type_id,
                             permit_status_type_id, issued_date, finaled_date, description)
                            VALUES (?, 'cpra', ?, ?, ?, ?, ?, ?)
                        """, (project_id, permit_number, VOCAB['permit_type']['building'],
                              status_id, issued_str, finaled_str, proj_info['description']))
                        permit_id = cursor.lastrowid

                    logger.info(f"  INSERT permit: {permit_number}")
                    stats['matched_inserted'] += 1

                    # Insert issued event
                    if issued_str:
                        insert_permit_event(conn, project_id, permit_id, 'building_permit_issued',
                                            issued_str, permit_number, dry_run, logger)
                        stats['events_created'] += 1

                    # Insert CO event if finaled
                    if finaled_str:
                        insert_permit_event(conn, project_id, permit_id, 'co_issued',
                                            finaled_str, permit_number, dry_run, logger)
                        stats['events_created'] += 1
                        stats['co_issued_events'] += 1
                        stats['permits_with_finaled_date'] += 1

        # Validation and commit/rollback
        logger.info("")
        logger.info("=== Validation ===")

        if dry_run:
            # Log validation metrics even in dry-run mode
            source_finaled = stats.get('source_finaled_count', 0)
            tracked_finaled = stats.get('permits_with_finaled_date', 0)
            tracked_co_issued = stats.get('co_issued_events', 0)
            min_ratio = VALIDATION.get('finaled_date_min_ratio', 0.80)

            logger.info(f"  finaled_date validation (dry-run):")
            logger.info(f"    Pre-computed source count: {source_finaled}")
            logger.info(f"    Tracked during import:     {tracked_finaled}")
            if source_finaled > 0:
                ratio = tracked_finaled / source_finaled
                status = "PASS" if ratio >= min_ratio else "FAIL"
                logger.info(f"    Ratio: {ratio:.0%} (threshold: {min_ratio:.0%}) -> {status}")

            logger.info(f"  co_issued event validation (dry-run):")
            logger.info(f"    Expected (= source finaled): {source_finaled}")
            logger.info(f"    Tracked during import:       {tracked_co_issued}")
            if source_finaled > 0:
                ratio = tracked_co_issued / source_finaled
                status = "PASS" if ratio >= min_ratio else "FAIL"
                logger.info(f"    Ratio: {ratio:.0%} (threshold: {min_ratio:.0%}) -> {status}")

            logger.info("Validation passed. Would COMMIT (dry-run).")
        else:
            is_valid, error_msg = validate_import(conn, stats, logger)
            if is_valid:
                conn.commit()
                logger.info("Validation passed. COMMITTED.")
            else:
                conn.rollback()
                logger.error(f"Validation failed: {error_msg}. ROLLED BACK.")
                stats['errors'] += 1
                conn.close()
                return stats

    except Exception as e:
        # Rollback on any exception
        logger.error("")
        logger.error("=== EXCEPTION DURING IMPORT ===")
        logger.error(f"Exception: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        if not dry_run:
            conn.rollback()
            logger.error("ROLLED BACK.")
        stats['errors'] += 1
        conn.close()
        return stats

    conn.close()

    # Summary
    logger.info("")
    logger.info("=== Import Summary ===")
    logger.info(f"Total CPRA permits processed: {stats['total_cpra_permits']}")
    logger.info(f"Already exist in v2:          {stats['already_exist']}")
    logger.info(f"Matched to v2 projects:       {stats['matched']}")
    logger.info(f"Permits inserted:             {stats['matched_inserted']}")
    logger.info(f"  - with finaled_date:        {stats['permits_with_finaled_date']}")
    logger.info(f"Unmatched (no v2 project):    {stats['unmatched']}")
    logger.info(f"New projects created:         {stats['new_projects_created']}")
    logger.info(f"Events created:               {stats['events_created']}")
    logger.info(f"  - co_issued events:         {stats['co_issued_events']}")
    logger.info(f"Errors:                       {stats['errors']}")
    logger.info("")
    logger.info(f"Log file: {log_file}")

    # Write summary markdown
    summary_file = log_file.with_suffix('.md').with_stem(log_file.stem + '_summary')
    write_summary_report(summary_file, stats, dry_run)
    logger.info(f"Summary:  {summary_file}")

    return stats


def write_summary_report(path: Path, stats: dict, dry_run: bool):
    """Write markdown summary report."""
    mode = "DRY-RUN" if dry_run else "LIVE"

    content = f"""# CPRA Import Summary ({mode})

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Statistics

| Metric | Count |
|--------|-------|
| Total CPRA permits processed | {stats['total_cpra_permits']} |
| Already exist in v2 | {stats['already_exist']} |
| Matched to v2 projects | {stats['matched']} |
| Permits inserted | {stats['matched_inserted']} |
| - with finaled_date | {stats['permits_with_finaled_date']} |
| Unmatched (no v2 project) | {stats['unmatched']} |
| New projects created | {stats['new_projects_created']} |
| Events created | {stats['events_created']} |
| - co_issued events | {stats['co_issued_events']} |
| Errors | {stats['errors']} |

## Configuration

- Matching strategy: Exact APN OR (exact StreetNumber + fuzzy StreetName ≥90%)
- Skip permits: {', '.join(SKIP_PERMITS)}
- New R-2 projects: {len(NEW_R2_PROJECTS)}

## New R-2 Projects

| Permit | Address | Units |
|--------|---------|-------|
"""

    for proj in NEW_R2_PROJECTS:
        content += f"| {proj['permit_number']} | {proj['address']} | {proj['units']} |\n"

    with open(path, 'w') as f:
        f.write(content)


# === CLI ===

def main():
    parser = argparse.ArgumentParser(
        description='Import CPRA 2023-2025 building permits into v2 database'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate import without making changes')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of permits to process (for testing)')

    args = parser.parse_args()

    if not CPRA_FILE.exists():
        print(f"Error: CPRA file not found: {CPRA_FILE}")
        sys.exit(1)

    if not V2_DB.exists():
        print(f"Error: V2 database not found: {V2_DB}")
        sys.exit(1)

    if not RAPIDFUZZ_AVAILABLE:
        print("Error: rapidfuzz is required. Install with: pip install rapidfuzz")
        sys.exit(1)

    stats = run_import(dry_run=args.dry_run, limit=args.limit)

    if stats['errors'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
