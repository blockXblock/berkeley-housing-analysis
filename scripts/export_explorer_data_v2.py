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
DB_PATH = BASE_DIR / 'databases' / 'berkeley_housing_v2.db'
OUTPUT_PATH = BASE_DIR / 'docs' / 'explorer_data_v2_working.js'

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
    """Get all projects from v2 database with derived fields from joined tables"""
    cursor = conn.cursor()

    # Main query: one row per project with current_version fields joined
    cursor.execute('''
        SELECT
            p.id,
            p.canonical_address,
            p.latitude,
            p.longitude,
            pv.total_units,
            pv.height_stories,
            pv.height_feet,
            pv.description,
            vst.code as stage_code
        FROM projects p
        LEFT JOIN project_versions pv ON pv.id = p.current_version_id
        LEFT JOIN vocabulary_stage_types vst ON vst.id = p.current_stage_type_id
        ORDER BY pv.total_units DESC
    ''')

    projects = []
    for row in cursor.fetchall():
        pid = row[0]
        units = row[4] or 0

        # Per-project subqueries for joined data

        # APN from primary parcel
        apn_cur = conn.cursor()
        apn_cur.execute('''
            SELECT pc.apn FROM parcels pc
            JOIN project_parcels pp ON pp.parcel_id = pc.id
            WHERE pp.project_id = ? AND pp.is_primary = 1
            LIMIT 1
        ''', (pid,))
        apn_row = apn_cur.fetchone()
        apn = apn_row[0] if apn_row else None

        # Owner, developer, architect from project_participants
        roles = {}
        role_cur = conn.cursor()
        role_cur.execute('''
            SELECT vrt.code, o.name
            FROM project_participants pp
            JOIN vocabulary_role_types vrt ON vrt.id = pp.role_type_id
            LEFT JOIN organizations o ON o.id = pp.organization_id
            WHERE pp.project_id = ?
              AND vrt.code IN ('developer_of_record', 'architect_design', 'owner_current')
        ''', (pid,))
        for role_code, org_name in role_cur.fetchall():
            if org_name:
                roles[role_code] = org_name

        # Classification flags
        flags = set()
        class_cur = conn.cursor()
        class_cur.execute('''
            SELECT vct.code
            FROM project_classifications pc
            JOIN vocabulary_classification_types vct ON vct.id = pc.classification_type_id
            WHERE pc.project_id = ?
        ''', (pid,))
        for (code,) in class_cur.fetchall():
            flags.add(code)

        # VLI units from unit_program_affordability
        vli_cur = conn.cursor()
        vli_cur.execute('''
            SELECT SUM(upa.unit_count)
            FROM unit_program_affordability upa
            JOIN unit_program up ON up.id = upa.unit_program_id
            JOIN project_versions pv ON pv.id = up.project_version_id
            JOIN vocabulary_income_categories vic ON vic.id = upa.income_category_id
            WHERE pv.project_id = ? AND pv.is_current = 1
              AND vic.code = 'VLI'
        ''', (pid,))
        vli_row = vli_cur.fetchone()
        vli_units = vli_row[0] if vli_row and vli_row[0] else 0

        # Key event dates (MAX event_date per event_type)
        event_cur = conn.cursor()
        event_cur.execute('''
            SELECT vet.code, MAX(pe.event_date)
            FROM project_events pe
            JOIN vocabulary_event_types vet ON vet.id = pe.event_type_id
            WHERE pe.project_id = ?
              AND vet.code IN (
                'application_submitted',
                'application_complete',
                'entitlement_approved',
                'building_permit_issued',
                'co_issued',
                'construction_start_observed',
                'demo_permit_issued'
              )
            GROUP BY vet.code
        ''', (pid,))
        event_dates = dict(event_cur.fetchall())

        # Permits list (comma-separated like v1)
        permit_cur = conn.cursor()
        permit_cur.execute('''
            SELECT GROUP_CONCAT(permit_number, ','), COUNT(*)
            FROM permits
            WHERE project_id = ?
        ''', (pid,))
        permit_row = permit_cur.fetchone()
        permits_str = permit_row[0] if permit_row[0] else ''
        num_permits = permit_row[1] or 0

        # Total fees aggregated
        fee_cur = conn.cursor()
        fee_cur.execute('''
            SELECT SUM(amount) FROM fees WHERE project_id = ?
        ''', (pid,))
        fee_row = fee_cur.fetchone()
        total_fees = fee_row[0] if fee_row and fee_row[0] else 0

        # Derived fields
        filed = event_dates.get('application_submitted')
        entitled = event_dates.get('entitlement_approved')
        bp_issued = event_dates.get('building_permit_issued')
        co_date = validate_co_date(event_dates.get('co_issued'))
        construction_start = event_dates.get('construction_start_observed')
        demolition_permit_date = event_dates.get('demo_permit_issued')

        # Processing days: filed to entitled
        processing_days = None
        if filed and entitled:
            try:
                from datetime import date
                f = date.fromisoformat(filed)
                e = date.fromisoformat(entitled)
                processing_days = (e - f).days
            except (ValueError, TypeError):
                pass

        # Map v2 stage code to v1-compatible status string
        stage_code = row[8]
        status_map = {
            'pre_application': 'Pre-Application',
            'in_review': 'Under Review',
            'entitled': 'Entitled',
            'permitted': 'Building Permits Filed',
            'under_construction': 'Under Construction',
            'completed': 'Completed',
            'stalled': 'Stalled',
            'withdrawn': 'Withdrawn'
        }
        status = status_map.get(stage_code, stage_code or 'Unknown')

        # Build output dict matching v1 shape
        projects.append({
            "id": pid,
            "address": row[1],
            "apn": apn,
            "owner": roles.get('owner_current'),
            "units": units,
            "new_units": units,
            "old_units": 0,
            "status": status,
            "year": filed[:4] if filed else None,
            "permits": permits_str,
            "description": row[7],
            "num_permits": num_permits,
            "project_size": "Large" if units >= 50 else "Medium" if units >= 10 else "Small",
            "latitude": row[2],
            "longitude": row[3],
            "unit_category": None,
            "tenure": None,
            "vli_units": vli_units,
            "density_bonus": 'density_bonus' in flags,
            "density_bonus_pct": None,
            "sb330": 'sb330_protected' in flags,
            "sb35": ('sb35_eligible' in flags or 'sb35_approved' in flags),
            "ab2011": ('ab2011_eligible' in flags or 'ab2011_approved' in flags),
            "app_filed": filed,
            "app_complete": event_dates.get('application_complete'),
            "entitled": entitled,
            "bp_issued": bp_issued,
            "co_date": co_date,
            "construction_start": construction_start,
            "construction_status": None,
            "estimated_completion": None,
            "accela_status": status,
            "accela_status_date": None,
            "processing_days": processing_days,
            "height_stories": row[5],
            "height_feet": row[6],
            "app_packet_mb": 0,
            "total_fees": total_fees,
            "fee_per_unit": (total_fees / units) if units > 0 else 0,
            "fee_count": 0,
            "permit_type": "Unknown",
            "construction_data_reliability": "Unknown",
            "is_uc_project": 'uc_project' in flags,
            "is_stalled": stage_code == 'stalled',
            "developer": roles.get('developer_of_record'),
            "architect": roles.get('architect_design'),
            "field_survey_date": None,
            "field_survey_notes": None,
            "demolition_permit_date": demolition_permit_date,
            "demolition_start_date": None,
            "pipeline_stage": stage_code,
            "construction_substage": None
        })

    return projects

def get_events(conn):
    """Get ALL events from v2 database with derived display fields.

    Translates v2's normalized project_events into v1-compatible output dict
    so docs/explorer.html doesn't need changes.
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            pe.project_id,
            p.canonical_address,
            COALESCE(pm.permit_number, '') as permit_number,
            vet.code as event_type_code,
            COALESCE(pe.summary, '') as summary,
            pe.event_date,
            pe.observed_by,
            pe.details,
            pe.new_status_code,
            COALESCE(vpt.code, '') as permit_type_code
        FROM project_events pe
        JOIN projects p ON p.id = pe.project_id
        JOIN vocabulary_event_types vet ON vet.id = pe.event_type_id
        LEFT JOIN permits pm ON pm.id = pe.permit_id
        LEFT JOIN vocabulary_permit_types vpt ON vpt.id = pm.permit_type_id
        ORDER BY pe.event_date DESC
    ''')

    events = []
    for row in cursor.fetchall():
        project_id, address, permit, event_type_code, summary, event_date, observed_by, details, new_status, permit_type = row

        # Filter out migration-attributed staff name (synthesized events have no real observer)
        is_migration = (observed_by == 'migration_v1_to_v2_20260507')
        display_staff = None if is_migration else observed_by

        # Map v2 event_type code to a stage label (broader category for grouping/display)
        stage_label_map = {
            'pre_app_meeting': 'Pre-Application',
            'application_submitted': 'Application',
            'application_complete': 'Application',
            'review_started': 'Review',
            'comments_issued': 'Review',
            'revision_submitted': 'Resubmittal',
            'hearing_scheduled': 'Hearing',
            'hearing_held': 'Hearing',
            'entitlement_approved': 'Entitlement',
            'entitlement_denied': 'Entitlement',
            'appeal_filed': 'Appeal',
            'appeal_resolved': 'Appeal',
            'demo_permit_issued': 'Permit',
            'building_permit_issued': 'Permit',
            'construction_start_observed': 'Construction',
            'topped_out': 'Construction',
            'co_issued': 'Completion',
            'permit_expired': 'Permit',
            'project_withdrawn': 'Withdrawal',
            'ownership_changed': 'Ownership',
            'developer_changed': 'Ownership',
            'program_revised': 'Program',
            'status_update': 'Status',
            'observation': 'Note',
        }
        stage = stage_label_map.get(event_type_code, 'Other')

        # type field: use summary if present (Accela detail), else humanized event_type
        # The [v1] prefix marks events synthesized during v1->v2 migration from v1's date columns
        # (filed, entitled, bp_issued, co_date) -- these dates were real but had no Accela detail
        if summary:
            type_label = summary
        else:
            type_label = '[v1] ' + event_type_code.replace('_', ' ').title()

        # comment: combine details and new_status_code if present
        comment_parts = []
        if details:
            comment_parts.append(details)
        if new_status and new_status != summary:
            comment_parts.append(f"Status: {new_status}")
        comment = ' | '.join(comment_parts) if comment_parts else ''

        events.append({
            "project_id": project_id,
            "address": address,
            "permit": permit,
            "stage": stage,
            "type": type_label,
            "date": event_date,
            "assigned_to": None,  # v2 doesn't track assignment separately from observed_by
            "staff": display_staff,
            "comment": comment,
            "status": new_status,
            "permit_type": permit_type
        })

    return events

def get_fees(conn, projects):
    """Get fee data from v2 fees table.

    Translates v2's normalized fees + projects join into v1-compatible
    output dict so docs/explorer.html doesn't need changes.
    """
    cursor = conn.cursor()

    # Totals
    cursor.execute('SELECT SUM(amount), COUNT(*), COUNT(DISTINCT permit_number_text) FROM fees')
    row = cursor.fetchone()
    total = row[0] or 0
    count = row[1] or 0
    permit_count = row[2] or 0

    # Linked vs unlinked (linked = has project_id)
    cursor.execute('SELECT SUM(amount) FROM fees WHERE project_id IS NOT NULL')
    linked = cursor.fetchone()[0] or 0
    unlinked = total - linked

    # Fees by year (from paid_date; many rows have null paid_date)
    cursor.execute('''
        SELECT SUBSTR(paid_date, 1, 4) as year, SUM(amount)
        FROM fees
        WHERE paid_date IS NOT NULL AND paid_date != ''
        GROUP BY year
        ORDER BY year
    ''')
    by_year = {row[0]: row[1] for row in cursor.fetchall()}

    # Fees by project address (top 20). Join through projects table to get canonical_address.
    cursor.execute('''
        SELECT p.canonical_address, SUM(f.amount) as total
        FROM fees f
        JOIN projects p ON p.id = f.project_id
        WHERE f.project_id IS NOT NULL
        GROUP BY p.canonical_address
        ORDER BY total DESC
        LIMIT 20
    ''')
    by_project = {row[0]: row[1] for row in cursor.fetchall()}

    # Large individual fees (>= $100k). Some may not have project_id; show address as null in that case.
    cursor.execute('''
        SELECT
            COALESCE(p.canonical_address, '(unattributed)') as address,
            COALESCE(f.fee_description, '') as description,
            f.amount,
            f.paid_date
        FROM fees f
        LEFT JOIN projects p ON p.id = f.project_id
        WHERE f.amount >= 100000
        ORDER BY f.amount DESC
    ''')
    large_fees = [
        {"address": row[0], "description": row[1], "amount": row[2], "date": row[3]}
        for row in cursor.fetchall()
    ]

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
    """Get staff activity from v2 project_events.observed_by.

    Translates v2's observed_by field into v1-compatible staff list.
    Excludes the migration_v1_to_v2_20260507 tag (synthesized events have no real staff).
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            observed_by,
            COUNT(*) as actions,
            COUNT(DISTINCT project_id) as projects
        FROM project_events
        WHERE observed_by IS NOT NULL
          AND length(observed_by) > 3
          AND observed_by != 'migration_v1_to_v2_20260507'
        GROUP BY observed_by
        ORDER BY actions DESC
    ''')

    staff = []
    for row in cursor.fetchall():
        if row[0]:  # Skip empty names (defense against blank strings that pass length check)
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
    """Get timeline data for projects in v2.

    Replaces v1's `projects.filed` column lookup with a query against
    project_events for application_submitted events. Groups by month.
    Returns the same v1-compatible shape: list of dicts with month, applications, units.
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            SUBSTR(pe.event_date, 1, 7) as month,
            COUNT(DISTINCT pe.project_id) as applications,
            SUM(COALESCE(pv.total_units, 0)) as units
        FROM project_events pe
        JOIN vocabulary_event_types vet ON vet.id = pe.event_type_id
        LEFT JOIN project_versions pv ON pv.id = (
            SELECT id FROM project_versions
            WHERE project_id = pe.project_id AND is_current = 1
            LIMIT 1
        )
        WHERE vet.code = 'application_submitted'
          AND pe.event_date IS NOT NULL
          AND pe.event_date != ''
        GROUP BY SUBSTR(pe.event_date, 1, 7)
        ORDER BY month
    ''')

    return [
        {"month": row[0], "applications": row[1], "units": row[2] or 0}
        for row in cursor.fetchall()
    ]

def get_documents(conn):
    """Get all project documents from v2 documents table.

    Translates v2's documents table into v1-compatible output dict.
    v2 has richer URL fields (source_url, drive_url, ia_url, r2_url) — we
    pick the best available URL with drive_url preferred (durable, public),
    then source_url, then ia_url, then r2_url.

    v2 document_type is vocabulary FK; resolve to code for v1-compatible display.
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            d.id,
            d.project_id,
            d.title,
            d.title as filename,
            COALESCE(d.drive_url, d.source_url, d.ia_url, d.r2_url) as url,
            COALESCE(vdt.code, 'other') as document_type,
            COALESCE(d.source_system, 'unknown') as source,
            COALESCE(d.fetched_at, d.created_at) as date_added,
            d.notes
        FROM documents d
        LEFT JOIN vocabulary_document_types vdt ON vdt.id = d.document_type_id
        ORDER BY d.project_id, d.created_at DESC
    ''')

    documents = []
    for row in cursor.fetchall():
        documents.append({
            "id": row[0],
            "project_id": row[1],
            "title": row[2],
            "filename": row[3],
            "url": row[4],
            "type": row[5],
            "source": row[6],
            "date_added": row[7],
            "notes": row[8]
        })

    return documents

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

        print("Querying documents...")
        documents = get_documents(conn)
        print(f"  {len(documents)} documents")

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
            "documents": documents,
            "meta": {
                "generated": datetime.now().isoformat(),
                "export_date": export_date,
                "source": "berkeley_housing_v2.db",
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
// Auto-generated from berkeley_housing_v2.db
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
        print(f"Documents: {len(documents)}")
        print(f"\n✓ Exported to {OUTPUT_PATH}")

    except Exception as e:
        print(f"\n✗ Export failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    export_data()
