#!/usr/bin/env python3
"""
Generate project_master_list.csv and scraping_queue.csv from FINAL.csv.

Analyzes data completeness for each project and identifies what's missing.
"""

import csv
import sqlite3
import re
from pathlib import Path
from datetime import datetime


def normalize_address(addr):
    """Normalize address for matching."""
    if not addr:
        return ''
    addr = ' '.join(addr.upper().split())
    addr = re.sub(r',?\s*(BERKELEY|CA|94\d{3}).*$', '', addr, re.I)
    return addr.strip()


def check_txt_files(address, permits, base_dir):
    """Check if zoning and building txt files exist for this project."""
    has_zoning = False
    has_building = False

    addr_parts = normalize_address(address).split()
    if not addr_parts:
        return has_zoning, has_building

    street_num = addr_parts[0]
    street_name = addr_parts[1] if len(addr_parts) > 1 else ''

    # Check zoning files (in base dir)
    for txt_file in base_dir.glob('*.txt'):
        name = txt_file.stem.upper()
        # Check if permit matches
        if permits:
            for permit in permits.split(','):
                permit = permit.strip()
                if permit and permit in name:
                    # Verify it's not a stub
                    try:
                        content = txt_file.read_text()[:200]
                        if not content.strip().startswith('pbpaste') and len(content.strip()) > 50:
                            has_zoning = True
                            break
                    except:
                        pass
        # Check if address matches
        if street_num in name and street_name and street_name[:4] in name:
            try:
                content = txt_file.read_text()[:200]
                if not content.strip().startswith('pbpaste') and len(content.strip()) > 50:
                    has_zoning = True
            except:
                pass

    # Check building files (in building/ subdir)
    building_dir = base_dir / 'building'
    if building_dir.exists():
        for txt_file in building_dir.glob('*.txt'):
            name = txt_file.stem.upper()
            if street_num in name and (not street_name or street_name[:4] in name):
                try:
                    content = txt_file.read_text()[:200]
                    if not content.strip().startswith('pbpaste') and len(content.strip()) > 50:
                        has_building = True
                        break
                except:
                    pass

    return has_zoning, has_building


def get_event_counts(db_path):
    """Get event counts per project from database."""
    event_counts = {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("""
            SELECT project_id, COUNT(*) as cnt
            FROM permit_events
            WHERE project_id IS NOT NULL
            GROUP BY project_id
        """)
        for row in cursor:
            event_counts[row[0]] = row[1]
        conn.close()
    except:
        pass
    return event_counts


def calculate_completeness(row, has_zoning, has_building, event_count):
    """Calculate data completeness score (0-100)."""
    score = 0
    max_score = 100

    # Core fields (40 points)
    if row.get('address_display'):
        score += 5
    if row.get('permits') and row.get('permits') != 'TBD':
        score += 10
    if row.get('net_units'):
        score += 5
    if row.get('status'):
        score += 5
    if row.get('description'):
        score += 5
    if row.get('owner'):
        score += 5
    if row.get('apn'):
        score += 5

    # Timeline fields (20 points)
    if row.get('app_filed_date'):
        score += 5
    if row.get('app_complete_date'):
        score += 5
    if row.get('entitled_date'):
        score += 5
    if row.get('bp_issued_date') or row.get('co_date'):
        score += 5

    # Scraped data (40 points)
    if has_zoning:
        score += 15
    if has_building:
        score += 10
    if event_count > 0:
        score += 10
    if event_count >= 5:
        score += 5  # Bonus for good event coverage

    return min(score, max_score)


def determine_missing(row, has_zoning, has_building, event_count):
    """Determine what data is missing for this project."""
    missing = []

    if row.get('permits') == 'TBD' or not row.get('permits'):
        missing.append('permit_discovery')
    if not has_zoning:
        missing.append('zoning_events')
    if not has_building:
        missing.append('building_permits')
    if event_count == 0:
        missing.append('processing_status')

    # Assume fees and attachments are missing if no zoning file
    if not has_zoning:
        missing.append('fees')
        missing.append('attachments')

    return ', '.join(missing) if missing else 'complete'


def determine_priority(units, completeness, status):
    """Determine collection priority."""
    units = float(units) if units else 0

    if units >= 100 and completeness < 30:
        return 'Critical'
    elif units >= 50 and completeness < 40:
        return 'High'
    elif units >= 20 and completeness < 50:
        return 'Medium'
    else:
        return 'Low'


def get_search_term(address, permits):
    """Generate Accela search term."""
    if permits and permits != 'TBD':
        # Use first permit number
        first_permit = permits.split(',')[0].strip()
        return first_permit
    else:
        # Use address
        return normalize_address(address)


def main():
    # Paths
    final_csv = Path('data/processed/housing_projects_FINAL.csv')
    master_csv = Path('data/processed/project_master_list.csv')
    queue_csv = Path('data/processed/scraping_queue.csv')
    accela_dir = Path('data/raw/accela_status')
    db_path = Path('data/berkeley_housing_analysis.db')

    # Load event counts
    event_counts = get_event_counts(str(db_path))

    # Read FINAL.csv
    with open(final_csv, 'r') as f:
        reader = csv.DictReader(f)
        projects = list(reader)

    print(f"Processing {len(projects)} projects...")

    # Analyze each project
    master_rows = []
    queue_rows = []

    for row in projects:
        project_id = int(row['id'])
        address = row.get('address_display', '')
        permits = row.get('permits', '')
        units = row.get('net_units', '0')
        status = row.get('status', '')
        construction_status = row.get('construction_status', '')

        # Check for txt files
        has_zoning, has_building = check_txt_files(address, permits, accela_dir)

        # Get event count
        event_count = event_counts.get(project_id, 0)
        has_events = event_count > 0

        # Calculate completeness
        completeness = calculate_completeness(row, has_zoning, has_building, event_count)

        # Determine what's missing
        missing = determine_missing(row, has_zoning, has_building, event_count)

        # Master list row
        master_row = {
            'id': project_id,
            'address': address,
            'permit_number': permits,
            'units': units,
            'status': status,
            'construction_status': construction_status,
            'has_zoning_txt': has_zoning,
            'has_building_txt': has_building,
            'has_events': has_events,
            'event_count': event_count,
            'has_fees': has_zoning,  # Assume fees come with zoning file
            'has_attachments': has_zoning,  # Assume attachments come with zoning file
            'data_completeness_score': completeness,
            'what_is_missing': missing
        }
        master_rows.append(master_row)

        # Queue row (if incomplete)
        if completeness < 50:
            try:
                unit_val = float(units) if units else 0
            except:
                unit_val = 0

            queue_row = {
                'address': address,
                'permit_number': permits,
                'units': unit_val,
                'what_is_missing': missing,
                'accela_search_term': get_search_term(address, permits),
                'priority': determine_priority(units, completeness, status),
                'completeness_score': completeness
            }
            queue_rows.append(queue_row)

    # Sort master list by completeness ascending
    master_rows.sort(key=lambda x: x['data_completeness_score'])

    # Sort queue by units descending
    queue_rows.sort(key=lambda x: (-x['units'], x['priority']))

    # Write master list
    master_fields = ['id', 'address', 'permit_number', 'units', 'status', 'construction_status',
                     'has_zoning_txt', 'has_building_txt', 'has_events', 'event_count',
                     'has_fees', 'has_attachments', 'data_completeness_score', 'what_is_missing']

    with open(master_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=master_fields)
        writer.writeheader()
        writer.writerows(master_rows)

    print(f"Wrote {len(master_rows)} projects to {master_csv}")

    # Write queue
    queue_fields = ['address', 'permit_number', 'units', 'what_is_missing',
                    'accela_search_term', 'priority', 'completeness_score']

    with open(queue_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=queue_fields)
        writer.writeheader()
        writer.writerows(queue_rows)

    print(f"Wrote {len(queue_rows)} incomplete projects to {queue_csv}")

    # Summary
    print("\n" + "="*60)
    print("COMPLETENESS SUMMARY")
    print("="*60)

    brackets = [(0, 25), (25, 50), (50, 75), (75, 100)]
    for low, high in brackets:
        count = len([r for r in master_rows if low <= r['data_completeness_score'] < high])
        print(f"  {low}-{high}%: {count} projects")

    complete = len([r for r in master_rows if r['data_completeness_score'] == 100])
    print(f"  100%: {complete} projects")

    print(f"\nPriority breakdown in queue:")
    for priority in ['Critical', 'High', 'Medium', 'Low']:
        count = len([r for r in queue_rows if r['priority'] == priority])
        print(f"  {priority}: {count}")


if __name__ == '__main__':
    main()
