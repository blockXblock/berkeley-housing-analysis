#!/usr/bin/env python3
"""
Accela Data Collection Workflow

Generates search URLs and parses Processing Status text from Berkeley's Accela system.

Usage:
    python accela_workflow.py generate    # Generate URLs for all projects
    python accela_workflow.py parse FILE  # Parse copied Processing Status text
"""

import sqlite3
import csv
import re
import sys
import urllib.parse
from pathlib import Path
from datetime import datetime


# Paths
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / 'databases/berkeley_housing_analysis.db'
OUTPUT_DIR = ROOT / 'data/outputs'


def generate_accela_urls():
    """
    Generate Accela search URLs for all projects.
    Creates a checklist CSV and HTML file for data collection.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, address_display, net_units, permits, status
        FROM projects
        ORDER BY net_units DESC
    """)

    projects = cursor.fetchall()
    conn.close()

    # Generate URLs and checklist
    checklist = []

    for project_id, address, net_units, permits, status in projects:
        # Parse address for Accela search
        # Extract street number and name
        address_clean = address.replace(',', '').strip()

        # Accela search URL - search by address
        # Building permits: https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Building
        search_url = f"https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Building&SearchType=GlobalSearch&QueryText={urllib.parse.quote(address_clean)}"

        # Planning module URL for zoning permits
        # Planning permits: https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Planning
        planning_url = f"https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Planning&SearchType=GlobalSearch&QueryText={urllib.parse.quote(address_clean)}"

        checklist.append({
            'id': project_id,
            'address': address,
            'net_units': int(net_units) if net_units else 0,
            'permits': permits or '',
            'status': status or '',
            'building_url': search_url,
            'planning_url': planning_url,
            'data_collected': '',
            'notes': ''
        })

    # Write CSV checklist
    csv_path = OUTPUT_DIR / 'accela_collection_checklist.csv'
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=checklist[0].keys())
        writer.writeheader()
        writer.writerows(checklist)

    print(f"Created checklist: {csv_path}")
    print(f"Total projects: {len(checklist)}")

    # Write HTML for easy clicking
    html_path = OUTPUT_DIR / 'accela_collection_links.html'

    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Accela Data Collection - Berkeley Housing Projects</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #4CAF50; color: white; position: sticky; top: 0; }
        tr:nth-child(even) { background: #f9f9f9; }
        tr:hover { background: #e8f5e9; }
        a { color: #1565C0; }
        .units { text-align: right; font-weight: bold; }
        .permits { font-size: 0.85em; color: #666; max-width: 200px; }
        input[type="checkbox"] { transform: scale(1.3); }
        .done { background: #c8e6c9 !important; }
        .instructions { background: #fff3e0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .address-cell { cursor: pointer; }
        .address-cell:hover { background: #e3f2fd; }
        .copied { animation: flash 0.3s; }
        @keyframes flash { 0% { background: #4CAF50; } 100% { background: inherit; } }
        .copy-hint { font-size: 0.7em; color: #888; }
    </style>
</head>
<body>
    <h1>Accela Data Collection Workflow</h1>

    <div class="instructions">
        <h3>Instructions:</h3>
        <ol>
            <li><strong>Click the address</strong> to copy it to clipboard</li>
            <li>Click <strong>Building</strong> or <strong>Planning</strong> to open Accela</li>
            <li>Paste address (Cmd+V) into the search box</li>
            <li>Find permits and click to view details</li>
            <li>Click <strong>"Processing Status"</strong> tab</li>
            <li>Select all (Cmd+A) and copy (Cmd+C)</li>
            <li>Check the box when done</li>
        </ol>
        <p><strong>Priority:</strong> Focus on largest projects first (sorted by units)</p>
    </div>

    <table>
        <thead>
            <tr>
                <th>Done</th>
                <th>Units</th>
                <th>Address <span class="copy-hint">(click to copy)</span></th>
                <th>Known Permits</th>
                <th>Building</th>
                <th>Planning</th>
            </tr>
        </thead>
        <tbody>
"""

    for item in checklist:
        # Extract just street number and name for searching (remove Berkeley, CA)
        address_search = item['address'].split(',')[0].strip()
        html_content += f"""            <tr>
                <td><input type="checkbox" onchange="this.parentElement.parentElement.classList.toggle('done')"></td>
                <td class="units">{item['net_units']}</td>
                <td class="address-cell" onclick="copyAddress(this, '{address_search}')" title="Click to copy"><strong>{item['address']}</strong></td>
                <td class="permits">{item['permits']}</td>
                <td><a href="https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Building" target="_blank">Building</a></td>
                <td><a href="https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Planning" target="_blank">Planning</a></td>
            </tr>
"""

    html_content += """        </tbody>
    </table>

    <script>
        // Copy address to clipboard
        function copyAddress(element, address) {
            navigator.clipboard.writeText(address).then(() => {
                element.classList.add('copied');
                setTimeout(() => element.classList.remove('copied'), 300);
            });
        }

        // Save checkbox state to localStorage
        document.querySelectorAll('input[type="checkbox"]').forEach((cb, i) => {
            const key = 'accela_done_' + i;
            cb.checked = localStorage.getItem(key) === 'true';
            if (cb.checked) cb.parentElement.parentElement.classList.add('done');
            cb.addEventListener('change', () => {
                localStorage.setItem(key, cb.checked);
            });
        });
    </script>
</body>
</html>
"""

    with open(html_path, 'w') as f:
        f.write(html_content)

    print(f"Created clickable checklist: {html_path}")
    print(f"\nOpen in browser: file://{html_path.absolute()}")

    return checklist


def parse_processing_status(text: str) -> list:
    """
    Parse the Processing Status text copied from Accela.

    Input format:
        Complete  Collapse      Issuance
        Due on 06/02/2025, assigned to TBD
        Marked as Issued on 06/02/2025 by Chandra Vogt
        Previously Active  Collapse      Inspection
        Due on 06/02/2025, assigned to TBD
        Marked as Finaled on 07/22/2025 by SR

    Returns list of milestone events.
    """
    events = []
    current_stage = None

    lines = text.strip().split('\n')

    # Patterns
    stage_pattern = re.compile(r'(Complete|Previously Active|Collapse|Expand)?\s*(Collapse|Expand)?\s+(.+)')
    marked_pattern = re.compile(r'Marked as (.+?) on (\d{2}/\d{2}/\d{4}) by (.+)')
    due_pattern = re.compile(r'Due on (\d{2}/\d{2}/\d{4}|TBD), assigned to (.+)')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for stage header
        if any(stage in line for stage in ['Submittal', 'Review', 'Distribution', 'Issuance', 'Inspection', 'Comments', 'Resubmittal']):
            # Extract stage name (last word or phrase after Collapse/Expand)
            parts = re.split(r'(Complete|Previously Active|Collapse|Expand)\s*', line)
            stage_name = parts[-1].strip() if parts else line
            current_stage = stage_name
            continue

        # Check for "Marked as" event
        match = marked_pattern.search(line)
        if match:
            action = match.group(1)
            date_str = match.group(2)
            by_whom = match.group(3)

            # Convert MM/DD/YYYY to YYYY-MM-DD
            try:
                dt = datetime.strptime(date_str, '%m/%d/%Y')
                iso_date = dt.strftime('%Y-%m-%d')
            except:
                iso_date = date_str

            events.append({
                'stage': current_stage or 'Unknown',
                'action': action,
                'date': iso_date,
                'by': by_whom
            })

    return events


def extract_key_milestones(events: list) -> dict:
    """
    Extract key milestone dates from parsed events.
    """
    milestones = {
        'first_filed_date': None,
        'zoning_approved_date': None,
        'building_permit_date': None,
        'co_issued_date': None,
        'last_status_date': None,
        'is_completed': False
    }

    for event in events:
        action = event['action'].lower()
        date = event['date']
        stage = (event.get('stage') or '').lower()

        # First filed = earliest date with "plan distribution" or similar
        if 'plan distribution' in action or 'submittal' in stage:
            if not milestones['first_filed_date'] or date < milestones['first_filed_date']:
                milestones['first_filed_date'] = date

        # Zoning approved
        if 'zoning' in stage and 'approved' in action:
            if not milestones['zoning_approved_date']:
                milestones['zoning_approved_date'] = date

        # Building permit issued
        if 'issuance' in stage and 'issued' in action:
            if not milestones['building_permit_date']:
                milestones['building_permit_date'] = date

        # CO / Finaled
        if 'finaled' in action or 'certificate' in action.lower():
            milestones['co_issued_date'] = date
            milestones['is_completed'] = True

        # Track last date
        if not milestones['last_status_date'] or date > milestones['last_status_date']:
            milestones['last_status_date'] = date

    return milestones


def parse_file(filepath: str):
    """Parse a text file containing Accela Processing Status."""
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return

    text = path.read_text()
    events = parse_processing_status(text)
    milestones = extract_key_milestones(events)

    print(f"\nParsed {len(events)} events from {path.name}")
    print("\nKey Events:")
    for event in events[:10]:
        print(f"  {event['date']}: {event['action']} ({event['stage']})")

    if len(events) > 10:
        print(f"  ... and {len(events) - 10} more")

    print("\nExtracted Milestones:")
    for key, value in milestones.items():
        print(f"  {key}: {value}")

    return events, milestones


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python accela_workflow.py generate    # Generate collection URLs")
        print("  python accela_workflow.py parse FILE  # Parse Processing Status text")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'generate':
        generate_accela_urls()

    elif command == 'parse':
        if len(sys.argv) < 3:
            print("Please provide a file to parse")
            sys.exit(1)
        parse_file(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
