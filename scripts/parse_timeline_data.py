#!/usr/bin/env python3
"""
Comprehensive Timeline Data Parser

Extracts ALL timeline data from Accela status text files:
- Workflow stages and transitions
- Dates and staff names
- Correction cycles
- Fee payments

Imports into:
- permit_events table (workflow events)
- projects table (bp_filed_date, bp_issued_date, co_date)
- permit_fees table (fee payments)
"""

import os
import re
import sqlite3
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# Paths
BASE_DIR = Path('/Users/johngage/berkeley-data')
DB_PATH = BASE_DIR / 'data' / 'berkeley_housing_analysis.db'
ACCELA_DIR = BASE_DIR / 'data' / 'raw' / 'accela_status'

# Patterns
PERMIT_PATTERN = re.compile(r'B20[0-9]{2}-[0-9]{5}')
DATE_PATTERN = re.compile(r'(\d{1,2}/\d{1,2}/\d{4})')
STAGE_PATTERN = re.compile(r'(Due\s+\d{1,2}/\d{1,2}/\d{4}|Due\s+TBD)\s*--\s*Marked\s+([A-Za-z\s\-/]+)\s+on\s+(\d{1,2}/\d{1,2}/\d{4})\s+by\s+([A-Za-z\s\.]+?)(?:\s*\(|$|\n)')
FEE_PATTERN = re.compile(r'\$([0-9,]+\.?\d*)')
WORKFLOW_STAGES = [
    'Application Submittal', 'Plan Distribution', 'Resubmittal', 'Resubmittal-Revision',
    'Building and Safety Review', 'Fire Review', 'Public Works Review', 'Zoning Review',
    'Corrections', 'Ready to Issue', 'Ready To Issue', 'Issuance', 'Issued',
    'Inspection', 'Final Inspection', 'Finaled', 'Certificate of Occupancy',
    'Plan Check', 'Route', 'Documents Uploaded', 'Auto-Closed', 'Approved',
    'Approved w/Conditions', 'Denied', 'Expired', 'Withdrawn'
]

def parse_date(date_str):
    """Parse MM/DD/YYYY to YYYY-MM-DD"""
    if not date_str or date_str == 'TBD':
        return None
    try:
        dt = datetime.strptime(date_str.strip(), '%m/%d/%Y')
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def extract_address_from_filename(filename):
    """Extract address from filename like ZP2024-0070_2442_HASTE_St.txt"""
    # Try pattern: permit_number_street_type.txt
    match = re.search(r'(\d+)[_\s]+([A-Z]+)[_\s]+([A-Za-z]+)\.txt', filename, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2)} {match.group(3)}"

    # Try pattern: B_address.txt
    match = re.search(r'B_(\d+)[_\s]+([A-Z]+)', filename, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2)}"

    return None

def extract_address_from_content(content):
    """Extract address from file content"""
    # Look for ADDRESS: line
    match = re.search(r'ADDRESS:\s*(\d+\s+[A-Za-z]+\s+[A-Za-z]+)', content, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Look for address in permit line
    match = re.search(r'Address:\s*(\d+\s+[A-Z]+\s+[A-Z]+)', content, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None

def parse_workflow_events(content, permit_number, address, source_file):
    """Extract all workflow events from content"""
    events = []

    # Pattern 1: "Due ... -- Marked ... on ... by ..." format
    for match in STAGE_PATTERN.finditer(content):
        due_str = match.group(1)
        action = match.group(2).strip()
        event_date = parse_date(match.group(3))
        staff = match.group(4).strip()

        # Clean up staff name
        staff = re.sub(r'\s+', ' ', staff).strip()
        if staff in ['ADM', 'TBD', 'System', '—', '-']:
            staff = None

        # Determine stage from action
        stage = None
        action_lower = action.lower()
        for s in WORKFLOW_STAGES:
            if s.lower() in action_lower:
                stage = s
                break

        if not stage:
            stage = action

        if event_date:
            events.append({
                'permit_number': permit_number,
                'address': address,
                'stage': stage,
                'action': action,
                'event_date': event_date,
                'marked_by': staff,
                'source_file': source_file
            })

    # Pattern 2: Markdown table format
    # Find section headers and their tables
    section_pattern = re.compile(r'\*\*([A-Za-z\s]+):\*\*\s*\n\|[^\n]+\|\s*\n\|[-|\s]+\|\s*\n((?:\|[^\n]+\|\s*\n?)+)', re.MULTILINE)

    for section_match in section_pattern.finditer(content):
        stage = section_match.group(1).strip()
        table_content = section_match.group(2)

        # Parse table rows
        # Format: | Due Date | Assigned | Action | Date Marked | By |
        # or: | Date | Invoice | Amount |
        for line in table_content.split('\n'):
            if not line.strip() or line.strip().startswith('|---'):
                continue

            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 4:
                # Try to parse as workflow row
                due_date = cells[0] if len(cells) > 0 else ''
                assigned = cells[1] if len(cells) > 1 else ''
                action = cells[2] if len(cells) > 2 else ''
                date_marked = cells[3] if len(cells) > 3 else ''
                staff = cells[4] if len(cells) > 4 else ''

                event_date = parse_date(date_marked)
                if event_date and action:
                    if staff in ['—', '-', 'TBD', '']:
                        staff = None

                    events.append({
                        'permit_number': permit_number,
                        'address': address,
                        'stage': stage,
                        'action': action,
                        'event_date': event_date,
                        'marked_by': staff,
                        'source_file': source_file
                    })

    # Pattern 3: Simpler status lines - STATUS: Issued
    status_match = re.search(r'STATUS:\s*(Issued|Finaled|Under Review|Corrections)', content, re.IGNORECASE)
    if status_match:
        status = status_match.group(1)
        date_match = re.search(r'DATE:\s*(\d{1,2}/\d{1,2}/\d{4})', content)
        if date_match:
            event_date = parse_date(date_match.group(1))
            if event_date:
                events.append({
                    'permit_number': permit_number,
                    'address': address,
                    'stage': status,
                    'action': f'Status: {status}',
                    'event_date': event_date,
                    'marked_by': None,
                    'source_file': source_file
                })

    # Extract Date Filed
    filed_match = re.search(r'Date Filed:\s*(\d{1,2}/\d{1,2}/\d{4})', content)
    if filed_match:
        event_date = parse_date(filed_match.group(1))
        if event_date:
            events.append({
                'permit_number': permit_number,
                'address': address,
                'stage': 'Application Filed',
                'action': 'Date Filed',
                'event_date': event_date,
                'marked_by': None,
                'source_file': source_file
            })

    return events

def parse_permit_block(content, source_file):
    """Parse a single permit block and extract all data"""
    results = {
        'permit_number': None,
        'address': None,
        'status': None,
        'date_filed': None,
        'date_issued': None,
        'date_finaled': None,
        'events': [],
        'fees': [],
        'description': None
    }

    # Extract permit number
    permit_match = PERMIT_PATTERN.search(content)
    if permit_match:
        results['permit_number'] = permit_match.group()
    else:
        return None

    # Extract address
    results['address'] = extract_address_from_content(content)

    # Extract status
    status_match = re.search(r'Status:\s*(\w+)', content)
    if status_match:
        results['status'] = status_match.group(1)

    # Extract dates
    filed_match = re.search(r'Date Filed:\s*(\d{1,2}/\d{1,2}/\d{4})', content)
    if filed_match:
        results['date_filed'] = parse_date(filed_match.group(1))

    # Extract description
    desc_match = re.search(r'Description:\s*(.+?)(?:\n[A-Z]|\nApplicant|\nOwner|$)', content, re.DOTALL)
    if desc_match:
        results['description'] = desc_match.group(1).strip()[:500]

    # Extract workflow events
    results['events'] = parse_workflow_events(content, results['permit_number'], results['address'], source_file)

    # Determine issued/finaled dates from events
    for event in results['events']:
        if event['stage'] in ['Issued', 'Issuance', 'Ready to Issue', 'Ready To Issue']:
            if not results['date_issued'] or event['event_date'] > results['date_issued']:
                results['date_issued'] = event['event_date']
        if event['stage'] in ['Finaled', 'Final Inspection', 'Certificate of Occupancy']:
            if not results['date_finaled'] or event['event_date'] > results['date_finaled']:
                results['date_finaled'] = event['event_date']

    # Extract fees - multiple formats

    # Format 1: "FEES:" section with amounts
    fee_section = re.search(r'FEES:(.*?)(?:\n[A-Z]{2,}|\nATTACHMENTS|$)', content, re.DOTALL)
    if fee_section:
        fee_text = fee_section.group(1)
        total_match = re.search(r'Total Paid:\s*\$([0-9,]+\.?\d*)', fee_text)
        if total_match:
            try:
                amount = float(total_match.group(1).replace(',', ''))
                results['fees'].append({
                    'permit_number': results['permit_number'],
                    'amount': amount,
                    'fee_type': 'Total Paid',
                    'payment_date': None
                })
            except:
                pass

    # Format 2: Markdown table "### Fees" section
    fee_table_match = re.search(r'### Fees.*?\*\*Paid.*?\|[^\n]+\|\s*\n\|[-|\s]+\|\s*\n((?:\|[^\n]+\|\s*\n?)+)', content, re.DOTALL)
    if fee_table_match:
        for line in fee_table_match.group(1).split('\n'):
            if not line.strip():
                continue
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 3:
                date_str = cells[0]
                amount_str = cells[2] if len(cells) > 2 else cells[1]
                amount_match = re.search(r'\$([0-9,]+\.?\d*)', amount_str)
                if amount_match:
                    try:
                        amount = float(amount_match.group(1).replace(',', ''))
                        payment_date = parse_date(date_str)
                        results['fees'].append({
                            'permit_number': results['permit_number'],
                            'amount': amount,
                            'fee_type': 'Payment',
                            'payment_date': payment_date
                        })
                    except:
                        pass

    # Format 3: "Total paid fees:" line
    total_match = re.search(r'\*\*Total paid fees:\s*\$([0-9,]+\.?\d*)\*\*', content)
    if total_match:
        try:
            amount = float(total_match.group(1).replace(',', ''))
            results['fees'].append({
                'permit_number': results['permit_number'],
                'amount': amount,
                'fee_type': 'Total Paid',
                'payment_date': None
            })
        except:
            pass

    return results

def parse_file(filepath):
    """Parse a single text file and extract all permit data"""
    filename = os.path.basename(filepath)

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return []

    results = []

    # Get file-level address
    file_address = extract_address_from_filename(filename) or extract_address_from_content(content)

    # Find all building permits in the file
    permits = PERMIT_PATTERN.findall(content)
    permits = list(set(permits))  # Deduplicate

    # For each permit, try to find its block
    for permit in permits:
        permit_idx = content.find(permit)
        if permit_idx == -1:
            continue

        # Extract a block around the permit
        start = max(0, content.rfind('\n---', 0, permit_idx))
        if start == -1 or start < permit_idx - 3000:
            start = max(0, permit_idx - 2000)

        end = content.find('\n---', permit_idx)
        if end == -1 or end > permit_idx + 5000:
            end = min(len(content), permit_idx + 5000)

        block = content[start:end]

        parsed = parse_permit_block(block, filename)
        if parsed and parsed['permit_number']:
            if not parsed['address']:
                parsed['address'] = file_address
            results.append(parsed)

    # Also extract events from the whole file (for ZP files with markdown tables)
    if file_address and ('### Processing Status' in content or '**Completeness Review:**' in content):
        # Extract zoning permit number from filename
        zp_match = re.search(r'(ZP\d{4}-\d{4}|PLN\d{4}-\d{4})', filename)
        zp_permit = zp_match.group(1) if zp_match else None

        events = parse_workflow_events(content, zp_permit, file_address, filename)

        # Extract fees from markdown tables
        fees = []
        fee_table_match = re.search(r'\*\*Paid.*?\|[^\n]+\|\s*\n\|[-|\s]+\|\s*\n((?:\|[^\n]+\|\s*\n?)+)', content, re.DOTALL)
        if fee_table_match:
            for line in fee_table_match.group(1).split('\n'):
                if not line.strip():
                    continue
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if len(cells) >= 3:
                    amount_str = cells[2] if len(cells) > 2 else cells[1]
                    amount_match = re.search(r'\$([0-9,]+\.?\d*)', amount_str)
                    if amount_match:
                        try:
                            amount = float(amount_match.group(1).replace(',', ''))
                            payment_date = parse_date(cells[0])
                            fees.append({
                                'permit_number': zp_permit,
                                'amount': amount,
                                'fee_type': 'Payment',
                                'payment_date': payment_date
                            })
                        except:
                            pass

        if events or fees:
            results.append({
                'permit_number': zp_permit,
                'address': file_address,
                'events': events,
                'fees': fees,
                'date_filed': None,
                'date_issued': None,
                'date_finaled': None
            })

    return results

def main():
    print("=" * 70)
    print("COMPREHENSIVE TIMELINE DATA PARSER")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure permit_events table exists with all columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            permit_number TEXT,
            address TEXT,
            stage TEXT,
            action TEXT,
            event_date TEXT,
            assigned_to TEXT,
            marked_by TEXT,
            comment TEXT,
            stage_status TEXT,
            permit_type TEXT,
            source_file TEXT,
            UNIQUE(permit_number, address, stage, action, event_date)
        )
    ''')

    # Add source_file column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE permit_events ADD COLUMN source_file TEXT")
    except:
        pass

    # Get existing events for deduplication
    cursor.execute("SELECT permit_number, address, stage, action, event_date FROM permit_events")
    existing_events = set()
    for row in cursor.fetchall():
        existing_events.add((row[0], row[1], row[2], row[3], row[4]))

    print(f"Existing events in database: {len(existing_events)}")

    # Get project lookup by address
    cursor.execute("SELECT id, address_display FROM projects")
    project_lookup = {}
    for row in cursor.fetchall():
        addr_norm = row[1].upper().replace(',', '').replace('.', '').strip() if row[1] else ''
        match = re.match(r'(\d+)\s+([A-Z]+)', addr_norm)
        if match:
            key = f"{match.group(1)} {match.group(2)}"
            project_lookup[key] = row[0]

    # Parse all files
    all_files = []
    for root, dirs, files in os.walk(ACCELA_DIR):
        for f in files:
            if f.endswith('.txt'):
                all_files.append(os.path.join(root, f))

    print(f"Files to parse: {len(all_files)}")

    # Statistics
    stats = {
        'files_parsed': 0,
        'permits_found': 0,
        'events_new': 0,
        'events_duplicate': 0,
        'fees_found': 0,
        'projects_updated': set(),
        'bp_filed_updates': 0,
        'bp_issued_updates': 0,
        'co_date_updates': 0
    }

    # Process each file
    for filepath in all_files:
        stats['files_parsed'] += 1
        if stats['files_parsed'] % 20 == 0:
            print(f"  Parsing file {stats['files_parsed']}/{len(all_files)}...")

        results = parse_file(filepath)

        for parsed in results:
            stats['permits_found'] += 1
            permit = parsed.get('permit_number')
            address = parsed.get('address', '').upper() if parsed.get('address') else ''

            # Find project ID
            project_id = None
            addr_match = re.match(r'(\d+)\s+([A-Z]+)', address)
            if addr_match:
                key = f"{addr_match.group(1)} {addr_match.group(2)}"
                project_id = project_lookup.get(key)

            # Insert events
            for event in parsed.get('events', []):
                event_key = (
                    event.get('permit_number'),
                    event.get('address', '').upper() if event.get('address') else '',
                    event.get('stage'),
                    event.get('action'),
                    event.get('event_date')
                )

                if event_key in existing_events:
                    stats['events_duplicate'] += 1
                    continue

                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO permit_events
                        (project_id, permit_number, address, stage, action, event_date, marked_by, source_file)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        project_id,
                        event.get('permit_number'),
                        event.get('address'),
                        event.get('stage'),
                        event.get('action'),
                        event.get('event_date'),
                        event.get('marked_by'),
                        event.get('source_file')
                    ))
                    if cursor.rowcount > 0:
                        stats['events_new'] += 1
                        existing_events.add(event_key)
                except Exception as e:
                    pass

            # Update project dates if we have a project match
            if project_id and permit and permit.startswith('B20'):
                # Update bp_filed_date
                if parsed.get('date_filed'):
                    cursor.execute('''
                        UPDATE projects
                        SET filed = ?
                        WHERE id = ? AND (filed IS NULL OR filed > ?)
                    ''', (parsed['date_filed'], project_id, parsed['date_filed']))
                    if cursor.rowcount > 0:
                        stats['bp_filed_updates'] += 1
                        stats['projects_updated'].add(project_id)

                # Update bp_issued_date
                if parsed.get('date_issued'):
                    cursor.execute('''
                        UPDATE projects
                        SET bp_issued = ?
                        WHERE id = ? AND (bp_issued IS NULL OR bp_issued > ?)
                    ''', (parsed['date_issued'], project_id, parsed['date_issued']))
                    if cursor.rowcount > 0:
                        stats['bp_issued_updates'] += 1
                        stats['projects_updated'].add(project_id)

                # Update co_date
                if parsed.get('date_finaled'):
                    cursor.execute('''
                        UPDATE projects
                        SET co_date = ?
                        WHERE id = ? AND (co_date IS NULL OR co_date > ?)
                    ''', (parsed['date_finaled'], project_id, parsed['date_finaled']))
                    if cursor.rowcount > 0:
                        stats['co_date_updates'] += 1
                        stats['projects_updated'].add(project_id)

            # Process fees
            for fee in parsed.get('fees', []):
                stats['fees_found'] += 1

    conn.commit()

    # Print summary
    print("\n" + "=" * 70)
    print("RECOVERY SUMMARY")
    print("=" * 70)
    print(f"Files parsed: {stats['files_parsed']}")
    print(f"Permits found: {stats['permits_found']}")
    print(f"New events extracted: {stats['events_new']}")
    print(f"Duplicate events skipped: {stats['events_duplicate']}")
    print(f"Fee records found: {stats['fees_found']}")
    print(f"\nProject date updates:")
    print(f"  bp_filed_date updates: {stats['bp_filed_updates']}")
    print(f"  bp_issued_date updates: {stats['bp_issued_updates']}")
    print(f"  co_date updates: {stats['co_date_updates']}")
    print(f"  Projects updated: {len(stats['projects_updated'])}")

    # Show event counts by stage
    print("\n" + "=" * 70)
    print("EVENTS BY STAGE")
    print("=" * 70)
    cursor.execute('''
        SELECT stage, COUNT(*) as cnt
        FROM permit_events
        GROUP BY stage
        ORDER BY cnt DESC
        LIMIT 20
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # Show BP issued by year
    print("\n" + "=" * 70)
    print("BP ISSUED BY YEAR (after updates)")
    print("=" * 70)
    cursor.execute('''
        SELECT SUBSTR(bp_issued, 1, 4) as year, COUNT(*), SUM(units)
        FROM projects
        WHERE bp_issued IS NOT NULL
        GROUP BY SUBSTR(bp_issued, 1, 4)
        ORDER BY year DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} projects, {int(row[2] or 0)} units")

    conn.close()
    print("\n✓ Timeline data parsing complete!")

if __name__ == '__main__':
    main()
