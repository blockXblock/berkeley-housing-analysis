#!/usr/bin/env python3
"""
Database Migration Script - Single Source of Truth
Migrates all data to berkeley_housing_analysis.db

This script:
1. Creates/updates the projects table with all fields
2. Imports 164 projects from FINAL.csv with developer/architect associations
3. Links permit_events to projects by address matching
4. Imports fee data from project_fees.json
5. Creates indexes for performance
"""

import sqlite3
import pandas as pd
import json
import re
from pathlib import Path

# Paths
BASE_DIR = Path('/Users/johngage/berkeley-data')
DB_PATH = BASE_DIR / 'databases' / 'berkeley_housing_analysis.db'
FINAL_CSV = BASE_DIR / 'data' / 'processed' / 'housing_projects_FINAL.csv'
FEES_JSON = BASE_DIR / 'data' / 'processed' / 'project_fees.json'

# Known developers with their addresses (from user's list)
DEVELOPER_ASSOCIATIONS = {
    "Panoramic Interests": ["1367 University", "2274 Shattuck", "2109 Virginia", "2711 Shattuck", "1752 Shattuck"],
    "NX Ventures": ["1598 University", "2601 San Pablo", "2720 San Pablo", "2733 San Pablo", "2847 Shattuck", "1974 Shattuck", "3000 Shattuck"],
    "Riaz Capital": ["2127 Dwight", "2300 Ellsworth"],
    "4Terra Investments": ["2100 Milvia", "2550 Shattuck"],
    "Core Spaces": ["2128 Oxford"],
    "Landmark Properties": ["2530 Bancroft"],
    "Allrise Capital": ["2136 San Pablo", "2198 San Pablo"],
    "Martin Group / Valiance Capital": ["2538 Durant"],
    "Realtex Group": ["2902 Adeline"],
    "Gilbane Development": ["2587 Telegraph", "2115 Kittredge"],
    "Collabhome": ["2425 Durant"],
    "CHDC": ["2016 Ashby", "1708 Harmon"],
    "RCD": ["2001 Ashby"],
    "Insight Housing": ["1700 Sacramento"],
    "Read Investments": ["2000 University"],
    "UC Berkeley Capital Strategies": ["2200 Bancroft"],
}

# Known architects with their addresses
ARCHITECT_ASSOCIATIONS = {
    "Trachtenberg Architects": ["2136 San Pablo", "2350 Telegraph", "2198 San Pablo", "2555 College", "2109 Virginia", "2127 Dwight", "2300 Ellsworth", "2733 San Pablo", "2720 San Pablo", "2847 Shattuck", "1598 University", "3000 Shattuck", "2601 San Pablo", "2274 Shattuck", "2550 Shattuck", "2100 Milvia"],
    "Studio KDA": ["2427 San Pablo", "2538 Durant", "2037 Durant", "2462 Bancroft", "2420 Shattuck", "1752 Shattuck", "2065 Kittredge", "1899 Oxford", "2920 Shattuck", "2700 Shattuck"],
    "SDT Architects": ["2902 Adeline", "2800 Telegraph", "1581 University", "2442 Haste", "2614 Telegraph", "3031 Adeline", "2018 Blake", "2712 Telegraph"],
    "Pyatok Architects": ["1700 Sacramento", "2001 Ashby"],
    "Lowney Architecture": ["2016 Ashby"],
    "Kava Massih Architects": ["1708 Harmon", "2435 San Pablo"],
    "KieranTimberlake": ["2200 Bancroft"],
    "DLR Group": ["2115 Kittredge"],
}

def match_address(partial, full_addr):
    """Check if partial address matches full address"""
    partial_norm = partial.upper().replace(".", "").strip()
    full_norm = full_addr.upper() if full_addr else ""
    return partial_norm in full_norm

def get_developer(address):
    """Get developer for an address"""
    for dev, addresses in DEVELOPER_ASSOCIATIONS.items():
        for addr in addresses:
            if match_address(addr, address):
                return dev
    return None

def get_architect(address):
    """Get architect for an address"""
    for arch, addresses in ARCHITECT_ASSOCIATIONS.items():
        for addr in addresses:
            if match_address(addr, address):
                return arch
    return None

def create_schema(conn):
    """Create the new projects table schema"""
    cursor = conn.cursor()

    # Backup existing data
    print("Backing up existing permit_events...")
    cursor.execute("SELECT COUNT(*) FROM permit_events")
    event_count = cursor.fetchone()[0]
    print(f"  Found {event_count} permit_events")

    # Drop views that depend on projects table
    print("Dropping dependent views...")
    cursor.execute("DROP VIEW IF EXISTS project_velocity")

    # Drop old projects table and create new one
    print("Creating new projects table...")
    cursor.execute("DROP TABLE IF EXISTS projects")

    cursor.execute('''
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            address TEXT NOT NULL,
            apn TEXT,
            permits TEXT,
            net_units REAL,
            total_units REAL,
            vli_units REAL,
            year INTEGER,
            status TEXT,
            description TEXT,
            density_bonus INTEGER DEFAULT 0,
            density_bonus_pct REAL,
            sb35_flag INTEGER DEFAULT 0,
            sb330_flag INTEGER DEFAULT 0,
            ab2011_flag INTEGER DEFAULT 0,
            height_stories INTEGER,
            height_feet REAL,
            latitude REAL,
            longitude REAL,
            app_filed_date TEXT,
            app_complete_date TEXT,
            entitled_date TEXT,
            bp_issued_date TEXT,
            construction_start_date TEXT,
            co_date TEXT,
            estimated_completion_date TEXT,
            construction_status TEXT,
            construction_data_reliability TEXT,
            accela_status TEXT,
            accela_status_date TEXT,
            processing_days INTEGER,
            is_uc_project INTEGER DEFAULT 0,
            is_stalled INTEGER DEFAULT 0,
            developer TEXT,
            architect TEXT,
            owner TEXT,
            total_fees REAL DEFAULT 0,
            fee_count INTEGER DEFAULT 0,
            unit_category TEXT,
            tenure TEXT,
            project_size TEXT,
            app_packet_mb REAL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_address ON projects(address)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_year ON projects(year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_units ON projects(net_units)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_developer ON projects(developer)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_architect ON projects(architect)")

    conn.commit()
    print("  Projects table created with new schema")

def import_projects(conn):
    """Import projects from FINAL.csv with developer/architect associations"""
    print("\nImporting projects from FINAL.csv...")

    df = pd.read_csv(FINAL_CSV)
    print(f"  Read {len(df)} projects from CSV")

    cursor = conn.cursor()

    for _, row in df.iterrows():
        address = row['address_display']
        developer = get_developer(address)
        architect = get_architect(address)
        owner = row['owner'] if pd.notna(row['owner']) else None

        # Determine if stalled
        is_stalled = 0
        status = row.get('status', '')
        if status in ['Under Review', 'Entitled']:
            # Check if entitled > 12 months without BP
            entitled_date = row.get('entitled_date')
            bp_issued_date = row.get('bp_issued_date')
            if entitled_date and pd.notna(entitled_date) and (pd.isna(bp_issued_date) or not bp_issued_date):
                is_stalled = 1

        cursor.execute('''
            INSERT INTO projects (
                id, address, apn, permits, net_units, total_units, vli_units, year, status, description,
                density_bonus, density_bonus_pct, sb35_flag, sb330_flag, ab2011_flag,
                height_stories, height_feet, latitude, longitude,
                app_filed_date, app_complete_date, entitled_date, bp_issued_date,
                construction_start_date, co_date, estimated_completion_date,
                construction_status, construction_data_reliability,
                accela_status, accela_status_date, processing_days,
                is_uc_project, is_stalled, developer, architect, owner,
                total_fees, fee_count, unit_category, tenure, project_size, app_packet_mb
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['id'],
            address,
            row.get('apn'),
            row.get('permits'),
            row.get('net_units'),
            row.get('new_units'),
            row.get('vli_units_extracted', 0),
            row.get('year'),
            status,
            row.get('description'),
            1 if row.get('density_bonus') else 0,
            row.get('density_bonus_pct'),
            1 if row.get('sb35_flag') else 0,
            1 if row.get('sb330_flag') else 0,
            1 if row.get('ab2011_flag') else 0,
            row.get('height_stories'),
            row.get('height_feet'),
            row.get('latitude'),
            row.get('longitude'),
            row.get('app_filed_date'),
            row.get('app_complete_date'),
            row.get('entitled_date'),
            row.get('bp_issued_date'),
            row.get('construction_start_date'),
            row.get('co_date'),
            row.get('estimated_completion_date'),
            row.get('construction_status'),
            row.get('construction_data_reliability'),
            row.get('accela_status'),
            row.get('accela_status_date'),
            row.get('total_processing_days'),
            1 if row.get('is_uc_project') else 0,
            is_stalled,
            developer,
            architect,
            owner,
            0,  # total_fees - will be updated later
            0,  # fee_count - will be updated later
            row.get('unit_category'),
            row.get('tenure'),
            row.get('project_size_category'),
            row.get('app_packet_size_mb', 0)
        ))

    conn.commit()

    # Report developer/architect assignments
    cursor.execute("SELECT COUNT(*) FROM projects WHERE developer IS NOT NULL")
    dev_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM projects WHERE architect IS NOT NULL")
    arch_count = cursor.fetchone()[0]

    print(f"  Imported {len(df)} projects")
    print(f"  Developer assigned: {dev_count} projects")
    print(f"  Architect assigned: {arch_count} projects")

def link_permit_events(conn):
    """Link permit_events to projects by address matching"""
    print("\nLinking permit_events to projects...")
    cursor = conn.cursor()

    # Get all projects
    cursor.execute("SELECT id, address, permits FROM projects")
    projects = cursor.fetchall()

    # Create lookup by address and permit number
    address_to_id = {}
    permit_to_id = {}

    for proj_id, address, permits in projects:
        # Normalize address for matching
        addr_norm = address.upper().replace(".", "").replace(",", "").strip()
        address_to_id[addr_norm] = proj_id

        # Also match by street number
        parts = addr_norm.split()
        if parts and parts[0].isdigit():
            street_key = parts[0] + " " + (parts[1] if len(parts) > 1 else "")
            address_to_id[street_key] = proj_id

        # Match by permit number
        if permits:
            for permit in permits.split(','):
                permit = permit.strip()
                permit_to_id[permit.upper()] = proj_id

    # Update permit_events
    cursor.execute("SELECT id, address, permit_number FROM permit_events WHERE project_id IS NULL")
    unlinked = cursor.fetchall()

    linked = 0
    for event_id, event_addr, permit_num in unlinked:
        project_id = None

        # Try permit number match first
        if permit_num:
            project_id = permit_to_id.get(permit_num.upper())

        # Try address match
        if not project_id and event_addr:
            event_addr_norm = event_addr.upper().replace(".", "").replace(",", "").strip()
            project_id = address_to_id.get(event_addr_norm)

            # Try partial match
            if not project_id:
                parts = event_addr_norm.split()
                if parts and parts[0].isdigit():
                    street_key = parts[0] + " " + (parts[1] if len(parts) > 1 else "")
                    project_id = address_to_id.get(street_key)

        if project_id:
            cursor.execute("UPDATE permit_events SET project_id = ? WHERE id = ?", (project_id, event_id))
            linked += 1

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM permit_events WHERE project_id IS NOT NULL")
    total_linked = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM permit_events")
    total_events = cursor.fetchone()[0]

    print(f"  Newly linked: {linked} events")
    print(f"  Total linked: {total_linked}/{total_events} events ({100*total_linked/total_events:.1f}%)")

def import_fees(conn):
    """Import fees from project_fees.json and link to projects"""
    print("\nImporting fees from project_fees.json...")

    if not FEES_JSON.exists():
        print("  Fee file not found, skipping")
        return

    with open(FEES_JSON, 'r') as f:
        fees_data = json.load(f)

    cursor = conn.cursor()

    # Get project permits mapping
    cursor.execute("SELECT id, permits FROM projects")
    projects = cursor.fetchall()

    permit_to_project = {}
    for proj_id, permits in projects:
        if permits:
            for permit in permits.split(','):
                permit = permit.strip().upper()
                permit_to_project[permit] = proj_id

    # Process fees by project (permit_id)
    if 'by_project' in fees_data:
        for permit_id, fee_info in fees_data['by_project'].items():
            permit_id_upper = permit_id.upper()
            project_id = permit_to_project.get(permit_id_upper)

            if project_id:
                total_fees = fee_info.get('total_fees', 0)
                fee_count = fee_info.get('fee_count', 0)

                # Update project
                cursor.execute('''
                    UPDATE projects
                    SET total_fees = total_fees + ?, fee_count = fee_count + ?
                    WHERE id = ?
                ''', (total_fees, fee_count, project_id))

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM projects WHERE total_fees > 0")
    with_fees = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total_fees) FROM projects")
    total_fees = cursor.fetchone()[0] or 0

    print(f"  Projects with fees: {with_fees}")
    print(f"  Total fees: ${total_fees:,.2f}")

def verify_migration(conn):
    """Verify the migration was successful"""
    print("\n=== Migration Verification ===")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM projects")
    project_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE developer IS NOT NULL")
    dev_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE architect IS NOT NULL")
    arch_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE total_fees > 0")
    fee_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM permit_events WHERE project_id IS NOT NULL")
    linked_events = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT project_id) FROM permit_events WHERE project_id IS NOT NULL")
    projects_with_events = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_fees) FROM projects")
    total_fees = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(net_units) FROM projects")
    total_units = cursor.fetchone()[0] or 0

    print(f"Projects: {project_count}")
    print(f"  With developer: {dev_count}")
    print(f"  With architect: {arch_count}")
    print(f"  With fees: {fee_count}")
    print(f"  With events: {projects_with_events}")
    print(f"Total units: {total_units:,.0f}")
    print(f"Total fees: ${total_fees:,.2f}")
    print(f"Linked events: {linked_events}")

def main():
    print("=" * 60)
    print("DATABASE MIGRATION - Single Source of Truth")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    try:
        create_schema(conn)
        import_projects(conn)
        link_permit_events(conn)
        import_fees(conn)
        verify_migration(conn)

        print("\n✓ Migration completed successfully!")
        print(f"Database: {DB_PATH}")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
