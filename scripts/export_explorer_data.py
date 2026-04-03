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
DB_PATH = BASE_DIR / 'data' / 'berkeley_housing_analysis.db'
OUTPUT_PATH = BASE_DIR / 'docs' / 'explorer_data.js'

def validate_co_date(co_date):
    """Validate CO date - reject dates before 2020 as likely fake/placeholder data"""
    if not co_date:
        return None
    try:
        year = int(co_date[:4])
        if year < 2020:
            print(f"  ⚠️ Rejecting invalid CO date (before 2020): {co_date}")
            return None
        return co_date
    except (ValueError, TypeError):
        return None

def get_projects(conn):
    """Get all projects from database"""
    cursor = conn.cursor()
    # Include all columns including UC project flags and construction status
    cursor.execute('''
        SELECT
            id, address_display, units, status, permits, filed, complete, entitled,
            bp_issued, co_date, height_stories, height_feet,
            is_uc_project, construction_status, developer, architect, description,
            latitude, longitude, density_bonus, vli_units, processing_days,
            apn, owner, accela_status, accela_status_date, construction_start,
            estimated_completion, sb35_flag, sb330_flag, ab2011_flag, app_packet_mb
        FROM projects
        ORDER BY units DESC
    ''')

    projects = []

    for row in cursor.fetchall():
        # Validate CO date (reject before 2020)
        co_date = validate_co_date(row[9])

        projects.append({
            "id": row[0],
            "address": row[1],
            "apn": row[22],  # From database
            "owner": row[23],  # From database
            "units": row[2] or 0,
            "new_units": row[2] or 0,
            "old_units": 0,
            "status": row[3],
            "year": row[5][:4] if row[5] else None,  # Extract year from filed date
            "permits": row[4],
            "description": row[16],  # From database
            "num_permits": len(row[4].split(',')) if row[4] else 0,
            "project_size": "Large" if (row[2] or 0) >= 50 else "Medium" if (row[2] or 0) >= 10 else "Small",
            "latitude": row[17],  # From database
            "longitude": row[18],  # From database
            "unit_category": None,
            "tenure": None,
            "vli_units": row[20] or 0,  # From database
            "density_bonus": bool(row[19]),  # From database (1 = True)
            "density_bonus_pct": None,
            "sb330": bool(row[29]),  # From database
            "sb35": bool(row[28]),   # From database
            "ab2011": bool(row[30]), # From database
            "app_filed": row[5],
            "app_complete": row[6],
            "entitled": row[7],
            "bp_issued": row[8],
            "co_date": co_date,
            "construction_start": row[26],  # From database
            "construction_status": row[13],  # From database
            "estimated_completion": row[27],  # From database
            "accela_status": row[24],  # From database
            "accela_status_date": row[25],  # From database
            "processing_days": row[21],  # From database
            "height_stories": row[10],  # From database
            "height_feet": row[11],      # From database
            "app_packet_mb": row[31] or 0,  # From database
            "total_fees": 0,
            "fee_per_unit": 0,
            "fee_count": 0,
            "permit_type": "Unknown",
            "construction_data_reliability": "Unknown",
            "is_uc_project": bool(row[12]),  # From database (1 = True)
            "is_stalled": False,
            "developer": row[14],  # From database
            "architect": row[15]   # From database
        })

    return projects

def get_events(conn):
    """Get ALL permit events from database"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            project_id, address, permit_number, stage, action,
            event_date, assigned_to, marked_by, comment, stage_status, permit_type
        FROM permit_events
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
    """Get fee data from permit_fees table"""
    cursor = conn.cursor()

    # Get totals
    cursor.execute('SELECT SUM(amount), COUNT(*), COUNT(DISTINCT permit_number) FROM permit_fees')
    row = cursor.fetchone()
    total = row[0] or 0
    count = row[1] or 0
    permit_count = row[2] or 0

    # Get linked vs unlinked
    cursor.execute('SELECT SUM(amount) FROM permit_fees WHERE project_id IS NOT NULL')
    linked = cursor.fetchone()[0] or 0
    unlinked = total - linked

    # Get fees by year
    cursor.execute('''
        SELECT SUBSTR(date, 1, 4) as year, SUM(amount)
        FROM permit_fees WHERE date IS NOT NULL
        GROUP BY year ORDER BY year
    ''')
    by_year = {row[0]: row[1] for row in cursor.fetchall()}

    # Get fees by project (top 20)
    cursor.execute('''
        SELECT address, SUM(amount) as total
        FROM permit_fees
        GROUP BY address
        ORDER BY total DESC
        LIMIT 20
    ''')
    by_project = {row[0]: row[1] for row in cursor.fetchall()}

    # Get large individual fees (over $100k)
    cursor.execute('''
        SELECT address, fee_description, amount, date
        FROM permit_fees
        WHERE amount >= 100000
        ORDER BY amount DESC
    ''')
    large_fees = [{"address": row[0], "description": row[1], "amount": row[2], "date": row[3]}
                  for row in cursor.fetchall()]

    # Calculate avg per unit
    total_units = sum(p['units'] for p in projects)
    avg_per_unit = total / total_units if total_units > 0 else 0

    return {
        "total": total,
        "linked": linked,
        "unlinked": unlinked,
        "count": count,
        "permit_count": permit_count,
        "by_year": by_year,
        "by_project": by_project,
        "large_fees": large_fees,
        "avg_per_unit": avg_per_unit
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
            SUBSTR(filed, 1, 7) as month,
            COUNT(*) as applications,
            SUM(units) as units
        FROM projects
        WHERE filed IS NOT NULL
        GROUP BY SUBSTR(filed, 1, 7)
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
        export_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        data = {
            "export_date": export_date,
            "projects": projects,
            "events": events,
            "fees": fees,
            "staff": staff,
            "players": players,
            "timeline": timeline,
            "meta": {
                "generated": datetime.now().isoformat(),
                "export_date": export_date,
                "source": "berkeley_housing_analysis.db",
                "project_count": len(projects),
                "event_count": len(events),
                "total_units": sum(p['units'] for p in projects),
                "total_fees": fees['total'],
                "linked_fees": fees['linked'],
                "unlinked_fees": fees['unlinked']
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
