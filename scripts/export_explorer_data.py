#!/usr/bin/env python3
"""
Export Explorer Data Script - Single Source of Truth

This is the ONLY script that should be used to generate explorer_data.js.
It queries ALL tables in the database to ensure no data is lost:
- projects table → DATA.projects
- permit_events table → DATA.events
- Aggregated fees → DATA.fees
- Staff from permit_events.marked_by → DATA.staff
- Developer/architect aggregation → DATA.players

Usage: python scripts/export_explorer_data.py
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Paths
BASE_DIR = Path('/Users/johngage/berkeley-data')
DB_PATH = BASE_DIR / 'databases' / 'berkeley_housing_analysis.db'
OUTPUT_PATH = BASE_DIR / 'docs' / 'explorer_data.js'

def get_projects(conn):
    """Get all projects from database"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            id, address, apn, permits, net_units, total_units, vli_units, year, status, description,
            density_bonus, density_bonus_pct, sb35_flag, sb330_flag, ab2011_flag,
            height_stories, height_feet, latitude, longitude,
            app_filed_date, app_complete_date, entitled_date, bp_issued_date,
            construction_start_date, co_date, estimated_completion_date,
            construction_status, construction_data_reliability,
            accela_status, accela_status_date, processing_days,
            is_uc_project, is_stalled, developer, architect, owner,
            total_fees, fee_count, unit_category, tenure, project_size, app_packet_mb
        FROM projects
        ORDER BY net_units DESC
    ''')

    columns = [desc[0] for desc in cursor.description]
    projects = []

    for row in cursor.fetchall():
        p = dict(zip(columns, row))
        # Convert to expected format
        projects.append({
            "id": p['id'],
            "address": p['address'],
            "apn": p['apn'],
            "owner": p['owner'],
            "units": p['net_units'] or 0,
            "new_units": p['total_units'] or p['net_units'] or 0,
            "old_units": 0,
            "status": p['status'],
            "year": p['year'],
            "permits": p['permits'],
            "description": p['description'],
            "num_permits": len(p['permits'].split(',')) if p['permits'] else 0,
            "project_size": p['project_size'] or "Unknown",
            "latitude": p['latitude'],
            "longitude": p['longitude'],
            "unit_category": p['unit_category'],
            "tenure": p['tenure'],
            "vli_units": p['vli_units'] or 0,
            "density_bonus": bool(p['density_bonus']),
            "density_bonus_pct": p['density_bonus_pct'],
            "sb330": bool(p['sb330_flag']),
            "sb35": bool(p['sb35_flag']),
            "ab2011": bool(p['ab2011_flag']),
            "app_filed": p['app_filed_date'],
            "app_complete": p['app_complete_date'],
            "entitled": p['entitled_date'],
            "bp_issued": p['bp_issued_date'],
            "co_date": p['co_date'],
            "construction_start": p['construction_start_date'],
            "construction_status": p['construction_status'],
            "estimated_completion": p['estimated_completion_date'],
            "accela_status": p['accela_status'],
            "accela_status_date": p['accela_status_date'],
            "processing_days": p['processing_days'],
            "height_stories": p['height_stories'],
            "height_feet": p['height_feet'],
            "app_packet_mb": p['app_packet_mb'] or 0,
            "total_fees": p['total_fees'] or 0,
            "fee_per_unit": (p['total_fees'] or 0) / (p['net_units'] or 1) if p['net_units'] else 0,
            "fee_count": p['fee_count'] or 0,
            "permit_type": "Unknown",
            "construction_data_reliability": p['construction_data_reliability'] or "Unknown",
            "is_uc_project": bool(p['is_uc_project']),
            "is_stalled": bool(p['is_stalled']),
            "developer": p['developer'],
            "architect": p['architect']
        })

    return projects

def get_events(conn):
    """Get all permit events linked to projects"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            project_id, address, permit_number, stage, action,
            event_date, assigned_to, marked_by, comment, stage_status, permit_type
        FROM permit_events
        WHERE project_id IS NOT NULL
        ORDER BY event_date DESC
    ''')

    events = []
    for row in cursor.fetchall():
        events.append({
            "project_id": row[0],
            "address": row[1],
            "permit": row[2],
            "stage": row[3],
            "type": row[4],  # action -> type for frontend
            "date": row[5],
            "assigned_to": row[6],
            "staff": row[7],  # marked_by -> staff for frontend
            "comment": row[8],
            "status": row[9],
            "permit_type": row[10]
        })

    return events

def get_fees(conn, projects):
    """Aggregate fee data from permit_fees table (includes ALL fees, linked and unlinked)"""
    cursor = conn.cursor()

    # Get TOTAL fees from permit_fees table (all $14.1M)
    cursor.execute("SELECT SUM(amount), COUNT(*) FROM permit_fees")
    row = cursor.fetchone()
    total_fees = row[0] or 0
    total_count = row[1] or 0

    # Get fees linked to projects
    cursor.execute("SELECT SUM(amount), COUNT(DISTINCT project_id) FROM permit_fees WHERE project_id IS NOT NULL")
    row = cursor.fetchone()
    linked_fees = row[0] or 0
    projects_with_fees_count = row[1] or 0

    # Fees NOT linked to projects (building permits we haven't matched yet)
    unlinked_fees = total_fees - linked_fees

    # Group by year (from projects that have fees)
    by_year = defaultdict(float)
    for p in projects:
        if p['total_fees'] > 0 and p['year']:
            by_year[str(int(p['year']))] += p['total_fees']

    # Group by project (for linked fees)
    by_project = {}
    for p in projects:
        if p['total_fees'] > 0:
            by_project[p['address']] = {
                "total_fees": p['total_fees'],
                "fee_count": p['fee_count'],
                "units": p['units']
            }

    # Also add unlinked permits to by_project
    cursor.execute('''
        SELECT permit_number, amount
        FROM permit_fees
        WHERE project_id IS NULL AND amount > 10000
        ORDER BY amount DESC
    ''')
    for row in cursor.fetchall():
        by_project[f"Permit: {row[0]}"] = {
            "total_fees": row[1],
            "fee_count": 1,
            "units": 0
        }

    # Large fees (over $50k) - include both project-linked and permit-only
    cursor.execute('''
        SELECT
            COALESCE(p.address, 'Permit: ' || pf.permit_number) as name,
            pf.amount,
            COALESCE(p.net_units, 0) as units
        FROM permit_fees pf
        LEFT JOIN projects p ON pf.project_id = p.id
        WHERE pf.amount >= 50000
        ORDER BY pf.amount DESC
        LIMIT 15
    ''')
    large_fees = [
        {"address": row[0], "total_fees": row[1], "units": row[2]}
        for row in cursor.fetchall()
    ]

    # Calculate average per unit for linked projects
    projects_with_fees = [p for p in projects if p['total_fees'] > 0]
    total_units_with_fees = sum(p['units'] for p in projects_with_fees) if projects_with_fees else 1

    return {
        "total": total_fees,
        "linked": linked_fees,
        "unlinked": unlinked_fees,
        "count": projects_with_fees_count,
        "permit_count": total_count,
        "by_year": dict(by_year),
        "by_project": by_project,
        "large_fees": large_fees,
        "avg_per_unit": linked_fees / total_units_with_fees if total_units_with_fees > 0 else 0
    }

def get_staff(conn):
    """Get staff activity from permit_events.marked_by"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            marked_by,
            COUNT(*) as actions,
            COUNT(DISTINCT project_id) as projects
        FROM permit_events
        WHERE marked_by IS NOT NULL AND marked_by != ''
        GROUP BY marked_by
        ORDER BY actions DESC
    ''')

    staff = []
    for row in cursor.fetchall():
        if row[0]:  # Skip empty names
            staff.append({
                "name": row[0],
                "actions": row[1],
                "projects": row[2]
            })

    return staff

def get_players(conn, projects):
    """Get developers, architects, and owners from projects"""
    # Aggregate developers
    dev_data = defaultdict(lambda: {"projects": [], "total_units": 0, "total_fees": 0})
    arch_data = defaultdict(lambda: {"projects": [], "total_units": 0, "total_fees": 0})
    owner_data = defaultdict(lambda: {"projects": [], "total_units": 0, "total_fees": 0})

    for p in projects:
        if p['developer']:
            dev_data[p['developer']]["projects"].append(p['address'])
            dev_data[p['developer']]["total_units"] += p['units'] or 0
            dev_data[p['developer']]["total_fees"] += p['total_fees'] or 0

        if p['architect']:
            arch_data[p['architect']]["projects"].append(p['address'])
            arch_data[p['architect']]["total_units"] += p['units'] or 0
            arch_data[p['architect']]["total_fees"] += p['total_fees'] or 0

        if p['owner']:
            owner_data[p['owner']]["projects"].append(p['address'])
            owner_data[p['owner']]["total_units"] += p['units'] or 0
            owner_data[p['owner']]["total_fees"] += p['total_fees'] or 0

    # Convert to sorted lists
    developers = sorted([
        {"name": k, **v} for k, v in dev_data.items()
    ], key=lambda x: x['total_units'], reverse=True)

    architects = sorted([
        {"name": k, **v} for k, v in arch_data.items()
    ], key=lambda x: x['total_units'], reverse=True)

    owners = sorted([
        {"name": k, **v} for k, v in owner_data.items()
    ], key=lambda x: x['total_units'], reverse=True)

    return {
        "developers": developers,
        "architects": architects,
        "owners": owners
    }

def get_timeline(conn):
    """Get timeline data for projects"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            SUBSTR(app_filed_date, 1, 7) as month,
            COUNT(*) as applications,
            SUM(net_units) as units
        FROM projects
        WHERE app_filed_date IS NOT NULL
        GROUP BY SUBSTR(app_filed_date, 1, 7)
        ORDER BY month
    ''')

    return [{"month": row[0], "applications": row[1], "units": row[2] or 0} for row in cursor.fetchall()]

def export_data():
    """Main export function"""
    print("=" * 60)
    print("EXPORT EXPLORER DATA - Single Source of Truth")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    try:
        # Get all data
        print("\nQuerying projects...")
        projects = get_projects(conn)
        print(f"  {len(projects)} projects")

        print("Querying events...")
        events = get_events(conn)
        print(f"  {len(events)} events")

        print("Aggregating fees...")
        fees = get_fees(conn, projects)
        print(f"  ${fees['total']:,.2f} total fees across {fees['count']} projects")

        print("Querying staff...")
        staff = get_staff(conn)
        print(f"  {len(staff)} staff members")

        print("Aggregating players...")
        players = get_players(conn, projects)
        print(f"  {len(players['developers'])} developers, {len(players['architects'])} architects, {len(players['owners'])} owners")

        print("Generating timeline...")
        timeline = get_timeline(conn)
        print(f"  {len(timeline)} months of data")

        # Build DATA object
        data = {
            "projects": projects,
            "events": events,
            "fees": fees,
            "staff": staff,
            "players": players,
            "timeline": timeline,
            "meta": {
                "generated": datetime.now().isoformat(),
                "source": "berkeley_housing_analysis.db",
                "project_count": len(projects),
                "event_count": len(events),
                "total_units": sum(p['units'] for p in projects),
                "total_fees": fees['total']
            }
        }

        # Write JavaScript file
        print(f"\nWriting to {OUTPUT_PATH}...")
        js_content = f'''// Berkeley Housing Pipeline Explorer - Data
// Auto-generated from berkeley_housing_analysis.db
// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
// DO NOT EDIT MANUALLY - Use scripts/export_explorer_data.py to regenerate

const DATA = {json.dumps(data, separators=(',', ':'))};
'''

        with open(OUTPUT_PATH, 'w') as f:
            f.write(js_content)

        print("\n=== Export Summary ===")
        print(f"Projects: {len(projects)}")
        print(f"Events: {len(events)}")
        print(f"Total Units: {sum(p['units'] for p in projects):,.0f}")
        print(f"Total Fees: ${fees['total']:,.2f}")
        print(f"Staff: {len(staff)}")
        print(f"Developers: {len(players['developers'])}")
        print(f"Architects: {len(players['architects'])}")
        print(f"Owners: {len(players['owners'])}")
        print(f"\n✓ Exported to {OUTPUT_PATH}")

    except Exception as e:
        print(f"\n✗ Export failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    export_data()
