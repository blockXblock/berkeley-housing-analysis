#!/usr/bin/env python3
"""
Accela Data Collection Workflow

Generates search URLs and parses Processing Status text from Berkeley's Accela system.

Usage:
    python accela_workflow.py generate    # Generate URLs for all projects
    python accela_workflow.py parse FILE  # Parse copied Processing Status text
    python accela_workflow.py save --db PATH --permit NUM --address ADDR --file FILE
    python accela_workflow.py save_batch --db PATH --dir DIRECTORY
"""

import argparse
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


def strip_markdown(text: str) -> str:
    """
    Strip markdown formatting from text.
    Removes **, *, →, ✅, ⚠️, bullet points, numbered list prefixes, etc.
    """
    if not text:
        return ''

    # Remove common emoji/symbols
    text = re.sub(r'[✅⚠️❌📝🔴🟢🟡●◆▶►→←↓↑]', '', text)

    # Remove markdown bold/italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*(.+?)\*', r'\1', text)      # *italic*
    text = re.sub(r'__(.+?)__', r'\1', text)      # __bold__
    text = re.sub(r'_(.+?)_', r'\1', text)        # _italic_

    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)

    # Remove numbered list prefixes (1. 2. etc)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove bullet points
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)

    # Clean up em-dashes used as placeholders
    text = text.replace('—', '-').replace('–', '-')

    return text.strip()


def parse_processing_status(text: str) -> list:
    """
    Parse the Processing Status text copied from Accela.

    Supports multiple input formats:

    1. Original Accela text format:
        Complete  Collapse      Issuance
        Due on 06/02/2025, assigned to TBD
        Marked as Issued on 06/02/2025 by Chandra Vogt

    2. Markdown table with stage headers:
        **Completeness Review:**
        | Due Date | Assigned | Action | Date Marked | By |
        |---|---|---|---|---|
        | 07/05/2024 | Waqar Shah | Incomplete Pending Applicant | 07/03/2024 | — |

    3. Markdown table with stage column:
        | Stage | Due Date | Assigned | Action | Date Marked | By | Comment |
        |---|---|---|---|---|---|---|
        | Completeness Review | 11/03/2023 | Claudia Garcia | Application Complete | 03/29/2024 | — | — |

    4. Markdown bullet/arrow format:
        **1. Completeness Review** ✅
        - Due 01/19/2024, assigned Niloufar → **Resubmittal Pending Staff** on 12/20/2023 by Name
        - Due 05/17/2024 → Marked **Application Complete** on 05/17/2024 by Name

    5. Pipe-delimited format (Claude sidebar markdown):
        === PROCESSING STATUS ===

        Completeness Review (Active):
          Due: 10/12/2024 | Assigned: Sharon Gong | Action: Resubmittal Pending Staff | Date Marked: 09/17/2024 | By: Claudia Garcia

    6. Entry-based format:
        === PROCESSING STATUS ===
        Completeness Review (complete):
          Entry 1: Due 10/08/2023 | Assigned TBD | Marked as Application Complete | on 09/12/2023
          Entry 2: Due 08/01/2023 | Assigned Shane Fields | Marked as Incomplete | on 07/28/2023 | by Sharon Gong

    7. Building Permit List format:
        06/27/2024
        B2024-03190
        Building Permit
        Closed Expired
        2530 BANCROFT Way, BERKELEY CA 94704

    8. Stage line format:
        Stage: Completeness Review Marked as Incomplete Pending Applicant on 06/13/2024 by Sharon Gong

    9. Numbered stage format:
        1. Completeness Review [COMPLETE]
           - Due: 07/11/2024 | Assigned to: TBD | Marked as: Application Complete | On: 08/07/2025 | By: Boshi Fu

    Returns list of milestone events.
    """
    events = []

    lines = text.strip().split('\n')

    # Detect format by looking for indicators
    # Check for Stage line format (Format 8) - has "Stage: ... Marked as ... on"
    has_stage_line_format = any(
        re.match(r'^Stage:\s*.+\s+Marked as\s+.+\s+on\s+', line.strip())
        for line in lines
    )

    # Check for numbered stage format (Format 9) - has "1. Stage Name [STATUS]" followed by "- Due:"
    # Pattern: numbered line like "1. Completeness Review [COMPLETE]"
    # followed by bullet lines like "- Due: DATE | Assigned to: NAME | Marked as: ACTION"
    has_numbered_stage_format = False
    for i, line in enumerate(lines):
        # Check for numbered stage header: "1. Name [STATUS]" or "Stage 1: Name [STATUS]"
        if re.match(r'^(?:Stage\s+)?\d+[.:\s]+\s*[A-Za-z]', line.strip()):
            # Look for bullet event lines following
            for j in range(i + 1, min(i + 5, len(lines))):
                if re.match(r'^\s*-\s*Due:?\s*\d{2}/\d{2}/\d{4}.*\|.*Marked', lines[j]):
                    has_numbered_stage_format = True
                    break
        if has_numbered_stage_format:
            break

    # Check for Entry-based format (Format 6) - has "Entry N:" and "Marked as"
    has_entry_format = any(
        re.search(r'Entry \d+:', line) and 'Marked as' in line
        for line in lines
    )

    # Check for bracketed status format (Format 10) - has "[COMPLETE] Stage Name" or "[ACTIVE] Stage Name"
    # followed by "- Due DATE, assigned to NAME | Marked as:"
    has_bracketed_status_format = False
    for i, line in enumerate(lines):
        if re.match(r'^\[(?:COMPLETE|ACTIVE)\]\s+[A-Za-z]', line.strip()):
            # Look for bullet event lines following
            for j in range(i + 1, min(i + 5, len(lines))):
                if re.match(r'^\s*-\s*Due\s+\d{2}/\d{2}/\d{4}.*\|\s*Marked\s+as:', lines[j]):
                    has_bracketed_status_format = True
                    break
        if has_bracketed_status_format:
            break

    # Check for event-numbered format (Format 11) - has "Stage: Name [STATUS]" with "Event N: Due on"
    has_event_numbered_format = any(
        re.search(r'Event\s+\d+:\s*Due\s+on', line) and ('Marked as' in line or '—' in line)
        for line in lines
    )

    # Check for Building Permit List format (Format 7) - has permit number pattern and "Permit" type
    has_building_permit_list = False
    for i, line in enumerate(lines):
        if re.match(r'^[A-Z]\d{4}-\d+$', line.strip()):  # e.g., B2024-03190
            # Check if next lines have permit type info
            if i + 2 < len(lines) and 'Permit' in lines[i + 1]:
                has_building_permit_list = True
                break

    # Check for pipe-delimited format (Format 5) - has "Due:" and "|" with "Action:"
    has_pipe_delimited = any(
        'Due:' in line and '|' in line and 'Action:' in line
        for line in lines
    )

    # Check for arrow format first (more specific)
    has_arrow = any('→' in line or '->' in line for line in lines)
    has_bullet_arrow = has_arrow and any(
        line.strip().startswith('-') and ('Due' in line) and ('→' in line or '->' in line)
        for line in lines
    )

    # Check for table format - look for table rows with multiple columns
    # in the Processing Status section
    has_processing_table = False
    in_processing = False
    for line in lines:
        if 'Processing Status' in line:
            in_processing = True
        elif in_processing:
            # Check if this looks like a table data row (has | and date pattern)
            if '|' in line and re.search(r'\d{2}/\d{2}/\d{4}', line):
                # Make sure it's not a separator row and not pipe-delimited format
                if not re.match(r'^[\s|:-]+$', line.strip()) and 'Due:' not in line:
                    has_processing_table = True
                    break
            # Stop if we hit another section
            if line.strip().startswith('###') or line.strip().startswith('**Fees'):
                break

    if has_stage_line_format:
        # Parse Stage line format (Format 8)
        events = parse_stage_line_status(lines)
    elif has_numbered_stage_format:
        # Parse numbered stage format (Format 9)
        events = parse_numbered_stage_status(lines)
    elif has_bracketed_status_format:
        # Parse bracketed status format (Format 10)
        events = parse_bracketed_status_format(lines)
    elif has_event_numbered_format:
        # Parse event-numbered format (Format 11)
        events = parse_event_numbered_status(lines)
    elif has_entry_format:
        # Parse Entry-based format (Format 6)
        events = parse_entry_based_status(lines)
    elif has_building_permit_list:
        # Parse Building Permit List format (Format 7)
        events = parse_building_permit_list(lines)
    elif has_pipe_delimited:
        # Parse pipe-delimited format (Format 5)
        events = parse_pipe_delimited_status(lines)
    elif has_bullet_arrow:
        # Parse bullet/arrow format (don't strip markdown yet - we need the ** for stage detection)
        events = parse_bullet_arrow_status(lines)
    elif has_processing_table:
        # Parse markdown table format
        # Pre-process: strip markdown formatting
        text_clean = strip_markdown(text)
        lines_clean = text_clean.strip().split('\n')
        events = parse_markdown_table_status(lines_clean)
    elif has_arrow:
        # Has arrows but not bullets - try bullet arrow parser anyway
        events = parse_bullet_arrow_status(lines)
    else:
        # Parse original Accela text format
        text_clean = strip_markdown(text)
        lines_clean = text_clean.strip().split('\n')
        events = parse_original_accela_status(lines_clean)

    return events


def parse_stage_line_status(lines: list) -> list:
    """
    Parse Processing Status from Stage line format (Format 8).

    Format:
        PROCESSING STATUS
        Stage: Completeness Review Marked as Incomplete Pending Applicant on 06/13/2024 by Sharon Gong
        Stage: Application Processing Marked as TBD on TBD by TBD (assigned to Singeh Saliki, due 02/15/2025)
        Stage: CEQA Determination (no events recorded)
        Stage: Staff Decision Marked as Approved on 09/11/2025 (due 09/16/2025, assigned to TBD) Comment: Appeal...

    Returns list of event dicts.
    """
    events = []

    # Pattern to match "Stage: <stage> Marked as <action> on <date> [by <person>] [(...)] [Comment: ...]"
    # Date can be MM/DD/YYYY or TBD
    stage_pattern = re.compile(
        r'^Stage:\s*(.+?)\s+Marked as\s+(.+?)\s+on\s+(\d{2}/\d{2}/\d{4}|TBD)'
        r'(?:\s+by\s+([^(]+?))?'  # Optional "by person"
        r'(?:\s*\(([^)]+)\))?'     # Optional parenthetical (assigned to, due, etc.)
        r'(?:\s*Comment:\s*(.+))?$',  # Optional comment
        re.IGNORECASE
    )

    # Pattern for "(no events recorded)" lines - skip these
    no_events_pattern = re.compile(r'^Stage:\s*.+\s*\(no events recorded\)', re.IGNORECASE)

    for line in lines:
        line = line.strip()

        # Skip empty lines and section headers
        if not line or line.upper().startswith('PROCESSING STATUS'):
            continue

        # Skip "(no events recorded)" lines
        if no_events_pattern.match(line):
            continue

        # Try to match stage line
        match = stage_pattern.match(line)
        if match:
            stage = match.group(1).strip()
            action = match.group(2).strip()
            date_str = match.group(3).strip()
            by_person = match.group(4).strip() if match.group(4) else None
            parenthetical = match.group(5) if match.group(5) else ''
            comment = match.group(6).strip() if match.group(6) else None

            # Parse date
            event_date = None
            if date_str and date_str != 'TBD':
                try:
                    dt = datetime.strptime(date_str, '%m/%d/%Y')
                    event_date = dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass

            # Parse parenthetical for assigned_to and due date
            assigned_to = by_person  # Default to "by" person
            if parenthetical:
                # Look for "assigned to X"
                assigned_match = re.search(r'assigned to\s+([^,)]+)', parenthetical, re.IGNORECASE)
                if assigned_match:
                    assigned_to = assigned_match.group(1).strip()

            # Clean up assigned_to
            if assigned_to:
                assigned_to = assigned_to.strip()
                if assigned_to == 'TBD':
                    assigned_to = None

            # Clean up by_person
            if by_person:
                by_person = by_person.strip()
                if by_person == 'TBD':
                    by_person = None

            event = {
                'stage': stage,
                'action': action,
                'date': event_date,
                'assigned_to': assigned_to,
                'marked_by': by_person,
                'comment': comment
            }
            events.append(event)

    return events


def parse_numbered_stage_status(lines: list) -> list:
    """
    Parse Processing Status from numbered stage format (Format 9).

    Format:
        PROCESSING STATUS
        -----------------
        1. Completeness Review [COMPLETE]
           - Due: 07/11/2024 | Assigned to: TBD | Marked as: Application Complete | On: 08/07/2025 | By: Boshi Fu

        Stage 1: Completeness Review [COMPLETE]
          - Due 10/24/2024 | Assigned: TBD | Marked: Incomplete Pending Applicant | On 09/24/2024 | By: Samella Stover

    Returns list of event dicts.
    """
    events = []
    current_stage = None

    # Pattern for stage headers: "1. Stage Name [STATUS]" or "Stage 1: Stage Name [STATUS]"
    stage_header_pattern = re.compile(
        r'^(?:Stage\s+)?(\d+)[.:\s]+\s*([A-Za-z][A-Za-z\s]+?)(?:\s*\[([^\]]+)\])?\s*$',
        re.IGNORECASE
    )

    # Pattern for event lines: "- Due: DATE | Assigned to: NAME | Marked as: ACTION | On: DATE | By: NAME"
    # Handles variations: "Due:" vs "Due", "Assigned to:" vs "Assigned:", "Marked as:" vs "Marked:", etc.
    event_line_pattern = re.compile(
        r'^\s*-\s*Due:?\s*(\d{2}/\d{2}/\d{4}|TBD)\s*\|\s*'
        r'Assigned(?:\s+to)?:?\s*([^|]+?)\s*\|\s*'
        r'Marked(?:\s+as)?:?\s*([^|]+?)\s*\|\s*'
        r'On:?\s*(\d{2}/\d{2}/\d{4}|TBD)\s*'
        r'(?:\|\s*By:?\s*([^|\n]+?))?'
        r'(?:\s*$|\s*\n)',
        re.IGNORECASE
    )

    # Also handle sub-stages with simplified format
    sub_stage_pattern = re.compile(
        r'^\s*-\s*([A-Za-z][^:]+?):\s*Due\s+(\d{2}/\d{2}/\d{4}|TBD)\s*\|\s*'
        r'Marked(?:\s+as)?:?\s*([^|]+?)\s*\|\s*'
        r'On:?\s*(\d{2}/\d{2}/\d{4}|TBD)\s*'
        r'(?:\|\s*By:?\s*([^|\n]+?))?',
        re.IGNORECASE
    )

    for line in lines:
        line_stripped = line.strip()

        # Skip empty lines, section headers, [no entries] lines
        if not line_stripped:
            continue
        if line_stripped.startswith('PROCESSING STATUS') or line_stripped.startswith('---'):
            continue
        if '[no entries]' in line_stripped.lower():
            continue
        if line_stripped.startswith('Sub-stages'):
            continue

        # Check for stage header
        stage_match = stage_header_pattern.match(line_stripped)
        if stage_match:
            current_stage = stage_match.group(2).strip()
            continue

        # Check for event line
        event_match = event_line_pattern.match(line_stripped)
        if event_match and current_stage:
            due_date = event_match.group(1)
            assigned_to = event_match.group(2).strip()
            action = event_match.group(3).strip()
            marked_date = event_match.group(4)
            marked_by = event_match.group(5).strip() if event_match.group(5) else None

            # Parse marked date
            event_date = None
            if marked_date and marked_date != 'TBD':
                try:
                    dt = datetime.strptime(marked_date, '%m/%d/%Y')
                    event_date = dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass

            # Clean up assigned_to and marked_by
            if assigned_to == 'TBD':
                assigned_to = None
            if marked_by == 'TBD':
                marked_by = None

            event = {
                'stage': current_stage,
                'action': action,
                'date': event_date,
                'assigned_to': assigned_to,
                'marked_by': marked_by,
                'comment': None
            }
            events.append(event)
            continue

        # Check for sub-stage line
        sub_match = sub_stage_pattern.match(line_stripped)
        if sub_match:
            sub_stage_name = sub_match.group(1).strip()
            marked_date = sub_match.group(4)
            action = sub_match.group(3).strip()
            marked_by = sub_match.group(5).strip() if sub_match.group(5) else None

            event_date = None
            if marked_date and marked_date != 'TBD':
                try:
                    dt = datetime.strptime(marked_date, '%m/%d/%Y')
                    event_date = dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass

            if marked_by == 'TBD':
                marked_by = None

            event = {
                'stage': f"{current_stage} - {sub_stage_name}" if current_stage else sub_stage_name,
                'action': action,
                'date': event_date,
                'assigned_to': None,
                'marked_by': marked_by,
                'comment': None
            }
            events.append(event)
            continue

        # Check for comment line
        if line_stripped.lower().startswith('comment:') and events:
            comment = line_stripped[8:].strip()
            events[-1]['comment'] = comment

    return events


def parse_bracketed_status_format(lines: list) -> list:
    """
    Parse Processing Status from bracketed status format (Format 10).

    Format:
        [COMPLETE] Completeness Review
          - Due 10/01/2024, assigned to Katrina Lapira | Marked as: Incomplete Pending Applicant | on 07/03/2024 by Katrina Lapira

        [ACTIVE] Application Processing
          - Due 09/05/2024, assigned to TBD | Marked as: Corrections - Pending Applicant | on 10/04/2024 by Katrina Lapira

        Application Processing
          - (no entries)

    Returns list of event dicts.
    """
    events = []
    current_stage = None

    # Pattern for stage headers: "[STATUS] Stage Name" or just "Stage Name"
    stage_header_pattern = re.compile(
        r'^(?:\[([A-Z]+)\]\s+)?([A-Za-z][A-Za-z\s\-]+?)\s*$',
        re.IGNORECASE
    )

    # Pattern for event lines: "- Due DATE, assigned to NAME | Marked as: ACTION | on DATE by NAME"
    event_line_pattern = re.compile(
        r'^\s*-\s*Due\s+(\d{2}/\d{2}/\d{4}|TBD),?\s*assigned\s+to\s+([^|]+?)\s*\|\s*'
        r'Marked\s+as:\s*([^|]+?)\s*\|\s*'
        r'on\s+(\d{2}/\d{2}/\d{4}|TBD)\s*'
        r'(?:by\s+(.+?))?$',
        re.IGNORECASE
    )

    for line in lines:
        line_stripped = line.strip()

        # Skip empty lines, section headers
        if not line_stripped:
            continue
        if line_stripped.startswith('PROCESSING STATUS') or line_stripped.startswith('---'):
            continue
        if '(no entries)' in line_stripped.lower():
            continue

        # Check for stage header
        stage_match = stage_header_pattern.match(line_stripped)
        if stage_match:
            stage_name = stage_match.group(2).strip()
            # Skip if it looks like something else
            if stage_name.lower() not in ['fees', 'attachments', 'conditions']:
                current_stage = stage_name
            continue

        # Check for event line
        event_match = event_line_pattern.match(line_stripped)
        if event_match and current_stage:
            due_date = event_match.group(1)
            assigned_to = event_match.group(2).strip()
            action = event_match.group(3).strip()
            marked_date = event_match.group(4)
            marked_by = event_match.group(5).strip() if event_match.group(5) else None

            # Parse marked date
            event_date = None
            if marked_date and marked_date != 'TBD':
                try:
                    dt = datetime.strptime(marked_date, '%m/%d/%Y')
                    event_date = dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass

            # Clean up assigned_to and marked_by
            if assigned_to == 'TBD':
                assigned_to = None
            if marked_by == 'TBD':
                marked_by = None

            event = {
                'stage': current_stage,
                'action': action,
                'date': event_date,
                'assigned_to': assigned_to,
                'marked_by': marked_by,
                'comment': None
            }
            events.append(event)

    return events


def parse_event_numbered_status(lines: list) -> list:
    """
    Parse Processing Status from event-numbered format (Format 11).

    Format:
        Stage: Completeness Review [COMPLETE]
          Event 1: Due on 12/26/2025, assigned to TBD — Marked as Incomplete Pending Applicant on 11/26/2025 by Karen Hernandez-Gonzalez
          Event 2: Due on 01/13/2026, assigned to TBD — Marked as Resubmittal Pending Staff on 12/14/2025 by Karen Hernandez-Gonzalez

        Stage: Application Processing [ACTIVE]
          Event 1: Due on 03/06/2026, assigned to TBD — Marked as Corrections - Pending Applicant on 02/06/2026 by Victoria Schlepp

    Returns list of event dicts.
    """
    events = []
    current_stage = None

    # Pattern for stage headers: "Stage: Name [STATUS]"
    stage_header_pattern = re.compile(
        r'^Stage:\s*([A-Za-z][A-Za-z\s\-]+?)(?:\s*\[([A-Z]+)\])?\s*$',
        re.IGNORECASE
    )

    # Pattern for event lines: "Event N: Due on DATE, assigned to NAME — Marked as ACTION on DATE by NAME"
    # Uses em-dash (—) or regular dash (-)
    event_line_pattern = re.compile(
        r'^\s*Event\s+\d+:\s*Due\s+on\s+(\d{2}/\d{2}/\d{4}|TBD),?\s*'
        r'assigned\s+to\s+([^—\-]+?)\s*[—\-]\s*'
        r'Marked\s+as\s+(.+?)\s+on\s+(\d{2}/\d{2}/\d{4}|TBD)\s*'
        r'(?:by\s+(.+?))?$',
        re.IGNORECASE
    )

    for line in lines:
        line_stripped = line.strip()

        # Skip empty lines, section headers
        if not line_stripped:
            continue
        if 'PROCESSING STATUS' in line_stripped or line_stripped.startswith('---'):
            continue

        # Check for stage header
        stage_match = stage_header_pattern.match(line_stripped)
        if stage_match:
            current_stage = stage_match.group(1).strip()
            continue

        # Check for event line
        event_match = event_line_pattern.match(line_stripped)
        if event_match and current_stage:
            due_date = event_match.group(1)
            assigned_to = event_match.group(2).strip()
            action = event_match.group(3).strip()
            marked_date = event_match.group(4)
            marked_by = event_match.group(5).strip() if event_match.group(5) else None

            # Parse marked date
            event_date = None
            if marked_date and marked_date != 'TBD':
                try:
                    dt = datetime.strptime(marked_date, '%m/%d/%Y')
                    event_date = dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass

            # Clean up assigned_to and marked_by
            if assigned_to == 'TBD':
                assigned_to = None
            if marked_by == 'TBD':
                marked_by = None

            event = {
                'stage': current_stage,
                'action': action,
                'date': event_date,
                'assigned_to': assigned_to,
                'marked_by': marked_by,
                'comment': None
            }
            events.append(event)

    return events


def parse_entry_based_status(lines: list) -> list:
    """
    Parse Processing Status from Entry-based format (Format 6).

    Format:
        === PROCESSING STATUS ===
        Completeness Review (complete):
          Entry 1: Due 10/08/2023 | Assigned TBD | Marked as Application Complete | on 09/12/2023
          Entry 2: Due 08/01/2023 | Assigned Shane Fields | Marked as Incomplete Pending Applicant | on 07/28/2023 | by Sharon Gong

        Staff Decision (complete):
          Entry 1: Due 06/06/2024 | Assigned TBD | Marked as Approved | on 05/30/2024
          Comment: Appeal period: 6/6/24-6/20/24
    """
    events = []
    current_stage = None
    current_stage_status = None

    # Pattern for stage headers: "Stage Name (status):" or "Stage Name:"
    stage_header_pattern = re.compile(
        r'^([A-Za-z][A-Za-z\s]+?)\s*(?:\(([^)]+)\))?\s*:\s*(?:not yet started)?$'
    )

    # Pattern for Entry-based event lines
    # Entry 1: Due 10/08/2023 | Assigned TBD | Marked as Application Complete | on 09/12/2023
    # Entry 2: Due 08/01/2023 | Assigned Shane Fields | Marked as Incomplete Pending Applicant | on 07/28/2023 | by Sharon Gong
    entry_pattern = re.compile(
        r'Entry \d+:\s*Due\s+(\d{2}/\d{2}/\d{4}|TBD)\s*\|\s*'
        r'Assigned\s+([^|]+?)\s*\|\s*'
        r'Marked as\s+([^|]+?)\s*\|\s*'
        r'on\s+(\d{2}/\d{2}/\d{4}|TBD)'
        r'(?:\s*\|\s*by\s+(.+?))?$',
        re.IGNORECASE
    )

    # Known stage names
    stage_names = [
        'Completeness Review', 'Application Processing', 'CEQA Determination',
        'Staff Decision', 'Staff Report', 'Appeal', 'Hearing Notice', 'Public Hearing',
        'Public Notification', 'Mailed Project Notices', 'Posted Project Notices',
        'Notice of Decision', 'Case Closed', 'Submittal', 'Distribution',
        'Issuance', 'Inspection', 'Resubmittal', 'Comments Review'
    ]

    for line in lines:
        line_stripped = line.strip()

        # Skip empty lines and section headers
        if not line_stripped or line_stripped.startswith('==='):
            continue

        # Skip "not yet started" lines
        if 'not yet started' in line_stripped.lower():
            continue

        # Skip comment lines
        if line_stripped.startswith('Comment:'):
            continue

        # Check for stage header
        stage_match = stage_header_pattern.match(line_stripped)
        if stage_match:
            potential_stage = stage_match.group(1).strip()
            stage_status = stage_match.group(2)  # e.g., "complete", "active"

            # Verify it's a known stage or contains a stage keyword
            if any(s.lower() in potential_stage.lower() for s in stage_names):
                current_stage = potential_stage
                current_stage_status = stage_status.capitalize() if stage_status else 'Unknown'
            continue

        # Check for Entry line
        entry_match = entry_pattern.search(line_stripped)
        if entry_match:
            due_date = entry_match.group(1)
            assigned_to = entry_match.group(2).strip()
            action = entry_match.group(3).strip()
            date_marked = entry_match.group(4)
            by_whom = entry_match.group(5).strip() if entry_match.group(5) else None

            # Skip entries with TBD dates or actions
            if date_marked == 'TBD' or action == 'TBD':
                continue

            # Clean up assigned_to
            if assigned_to in ['TBD', '']:
                assigned_to = 'TBD'

            # Convert date to ISO format
            try:
                dt = datetime.strptime(date_marked, '%m/%d/%Y')
                iso_date = dt.strftime('%Y-%m-%d')
            except:
                iso_date = date_marked

            events.append({
                'stage': current_stage or 'Unknown',
                'action': action,
                'date': iso_date,
                'by': by_whom or 'Unknown',
                'stage_status': current_stage_status or 'Unknown',
                'assigned_to': assigned_to
            })

    return events


def parse_building_permit_list(lines: list) -> list:
    """
    Parse Building Permit List format (Format 7).

    Format:
        06/27/2024
        B2024-03190
        Building Permit
        Closed Expired
        2530 BANCROFT Way, BERKELEY CA 94704
        Pay Fees Due
        Phase 1: Ground Improvements...

        05/23/2024
        B2024-02577
        Demolition Building Permit
        Closed Expired
        ...
    """
    events = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for date line (MM/DD/YYYY)
        date_match = re.match(r'^(\d{2}/\d{2}/\d{4})$', line)
        if date_match:
            date_str = date_match.group(1)

            # Next line should be permit number
            if i + 1 < len(lines):
                permit_number = lines[i + 1].strip()

                # Next line should be permit type
                permit_type = lines[i + 2].strip() if i + 2 < len(lines) else 'Unknown'

                # Next line should be status
                status = lines[i + 3].strip() if i + 3 < len(lines) else 'Unknown'

                # Convert date to ISO format
                try:
                    dt = datetime.strptime(date_str, '%m/%d/%Y')
                    iso_date = dt.strftime('%Y-%m-%d')
                except:
                    iso_date = date_str

                events.append({
                    'stage': permit_type,
                    'action': status,
                    'date': iso_date,
                    'by': 'System',
                    'stage_status': 'Complete' if 'Closed' in status else 'Active',
                    'assigned_to': None,
                    'permit_number': permit_number
                })

                i += 4  # Skip the lines we just processed
                continue

        i += 1

    return events


def parse_building_permit_file(text: str) -> dict:
    """
    Parse a Building Permit file from the building/ directory.

    These files contain building permit search results with formats:

    1. Detailed permit blocks:
        ADDRESS: 1899 OXFORD ST, Berkeley CA 94709

        BUILDING PERMITS FOUND: 1

        --- PERMIT 1 ---
        Permit #: B2026-00973
        Type: Building Permit (Demolition)
        Status: Corrections List Issued
        Date: 2026 (filed 03/10/2026 per fee payment)
        Description: Demolish 2-story multi-family building (5,104sf).

    2. Compact list format:
        Full permit list:
          B2012-02615 | 07/02/2012 | Building Permit | Closed Expired | Description

    Returns dict with:
        - address: string
        - permits: list of permit dicts with keys:
            permit_number, permit_type, status, date, description, job_value, finaled_date
    """
    lines = text.strip().split('\n')
    result = {
        'address': None,
        'permits': [],
        'permit_count': 0
    }

    # Extract address
    for line in lines:
        if line.startswith('ADDRESS:'):
            addr = line.replace('ADDRESS:', '').strip()
            # Remove city/state/zip
            addr = re.sub(r',?\s*(Berkeley|CA|94\d{3}).*$', '', addr, flags=re.IGNORECASE)
            result['address'] = addr.strip()
            break

    # Extract permit count
    for line in lines:
        match = re.search(r'BUILDING PERMITS FOUND:\s*(\d+)', line)
        if match:
            result['permit_count'] = int(match.group(1))
            break

    # Parse detailed permit blocks (--- PERMIT N ---)
    current_permit = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Start of permit block
        if re.match(r'^---\s*PERMIT\s+\d+\s*---', line):
            if current_permit and current_permit.get('permit_number'):
                result['permits'].append(current_permit)
            current_permit = {
                'permit_number': None,
                'permit_type': None,
                'status': None,
                'date': None,
                'finaled_date': None,
                'description': None,
                'job_value': None,
                'owner': None,
                'applicant': None
            }
            i += 1
            continue

        # Parse permit fields
        if current_permit is not None:
            if line.startswith('Permit #:'):
                current_permit['permit_number'] = line.replace('Permit #:', '').strip()
            elif line.startswith('Type:'):
                current_permit['permit_type'] = line.replace('Type:', '').strip()
            elif line.startswith('Status:'):
                current_permit['status'] = line.replace('Status:', '').strip()
            elif line.startswith('Date:'):
                date_str = line.replace('Date:', '').strip()
                # Try to extract ISO date
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_str)
                if date_match:
                    try:
                        dt = datetime.strptime(date_match.group(1), '%m/%d/%Y')
                        current_permit['date'] = dt.strftime('%Y-%m-%d')
                    except:
                        current_permit['date'] = date_str
                else:
                    current_permit['date'] = date_str
            elif line.startswith('Description:'):
                current_permit['description'] = line.replace('Description:', '').strip()
            elif line.startswith('Job Value:'):
                current_permit['job_value'] = line.replace('Job Value:', '').strip()
            elif line.startswith('Owner:'):
                current_permit['owner'] = line.replace('Owner:', '').strip()
            elif line.startswith('Applicant:'):
                current_permit['applicant'] = line.replace('Applicant:', '').strip()

        i += 1

    # Don't forget last permit
    if current_permit and current_permit.get('permit_number'):
        result['permits'].append(current_permit)

    # Parse compact list format (B2012-02615 | 07/02/2012 | Building Permit | Closed Expired | Desc)
    for line in lines:
        # Match: permit_num | date | type | status | description
        match = re.match(
            r'^\s*([A-Z]\d{4}-\d+(?:-REV\d+)?)\s*\|\s*'
            r'(\d{2}/\d{2}/\d{4})\s*\|\s*'
            r'([^|]+)\s*\|\s*'
            r'([^|]+)\s*\|\s*'
            r'(.*)$',
            line.strip()
        )
        if match:
            permit_num = match.group(1).strip()
            # Check if we already have this permit from detailed block
            existing = [p for p in result['permits'] if p.get('permit_number') == permit_num]
            if not existing:
                try:
                    dt = datetime.strptime(match.group(2).strip(), '%m/%d/%Y')
                    date_iso = dt.strftime('%Y-%m-%d')
                except:
                    date_iso = match.group(2).strip()

                result['permits'].append({
                    'permit_number': permit_num,
                    'permit_type': match.group(3).strip(),
                    'status': match.group(4).strip(),
                    'date': date_iso,
                    'finaled_date': None,
                    'description': match.group(5).strip(),
                    'job_value': None,
                    'owner': None,
                    'applicant': None
                })

    # Extract finaled dates from Processing Status section
    for i, line in enumerate(lines):
        if 'Finaled' in line and 'Permit #' not in line:
            # Look for date in this line or nearby
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
            if date_match:
                try:
                    dt = datetime.strptime(date_match.group(1), '%m/%d/%Y')
                    finaled_date = dt.strftime('%Y-%m-%d')
                    # Apply to permits with "Finaled" status
                    for permit in result['permits']:
                        if permit['status'] and 'Finaled' in permit['status']:
                            permit['finaled_date'] = finaled_date
                except:
                    pass

    return result


def parse_building_filename(filename: str) -> str | None:
    """
    Parse address from building permit filename.

    Expected format: B_1899_OXFORD_St.txt or B_2601_SAN_PABLO_Ave.txt
    Returns address string or None if can't parse.
    """
    name = Path(filename).stem  # Remove .txt extension

    if not name.startswith('B_'):
        return None

    # Remove B_ prefix
    addr_part = name[2:]

    # Convert underscores to spaces
    address = addr_part.replace('_', ' ')

    return address


def save_building_permit_events(db_path: str, text_file: str) -> dict:
    """
    Parse Building Permit file and save events to database.

    Unlike Planning permits, Building files contain the address and may have
    multiple permits. We extract all permits and their events.

    Returns dict with counts of inserted/skipped records.
    """
    path = Path(text_file)
    if not path.exists():
        return {'error': f"File not found: {text_file}"}

    text = path.read_text()

    # Check for placeholder/empty files
    if 'pbpaste' in text and len(text) < 200:
        return {'error': "Placeholder file (contains pbpaste command)", 'permits': 0}

    if 'No building permits found' in text:
        return {
            'permits_found': 0,
            'events_inserted': 0,
            'events_skipped': 0,
            'no_permits': True,
            'source_file': str(path)
        }

    # Parse the file
    parsed = parse_building_permit_file(text)

    if not parsed['permits']:
        # Check if explicitly no qualifying permits
        if 'No qualifying permits found' in text or 'RESULT: No qualifying' in text:
            return {
                'permits_found': 0,
                'events_inserted': 0,
                'events_skipped': 0,
                'no_qualifying_permits': True,
                'source_file': str(path)
            }
        return {'error': "No permits parsed from file", 'permits': 0}

    address = parsed['address']

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Look up project_id
    project_id = lookup_project_id(conn, address) if address else None

    # Track results
    results = {
        'source_file': str(path),
        'address': address,
        'project_id': project_id,
        'permits_found': len(parsed['permits']),
        'events_inserted': 0,
        'events_skipped': 0,
        'permits_upserted': 0,
        'warnings': []
    }

    if project_id is None and address:
        results['warnings'].append(f"No project match for address: {address}")

    # Ensure permit_events table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            address TEXT,
            permit_number TEXT,
            stage TEXT,
            action TEXT,
            event_date TEXT,
            assigned_to TEXT,
            marked_by TEXT,
            comment TEXT,
            stage_status TEXT,
            source TEXT DEFAULT 'accela',
            imported_at TEXT DEFAULT (datetime('now')),
            permit_type TEXT,
            UNIQUE(permit_number, stage, action, event_date)
        )
    """)

    # Ensure building_permits table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS building_permits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            permit_number TEXT NOT NULL UNIQUE,
            permit_type TEXT,
            address TEXT,
            status TEXT,
            filed_date TEXT,
            finaled_date TEXT,
            job_value TEXT,
            description TEXT,
            owner TEXT,
            applicant TEXT,
            source TEXT DEFAULT 'accela',
            imported_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Insert each permit
    for permit in parsed['permits']:
        permit_number = permit.get('permit_number')
        if not permit_number:
            continue

        # Insert event for this permit
        try:
            cursor.execute("""
                INSERT INTO permit_events
                (project_id, address, permit_number, stage, action, event_date,
                 assigned_to, marked_by, stage_status, source, permit_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'accela_building', 'Building')
            """, (
                project_id,
                address,
                permit_number,
                permit.get('permit_type', 'Building Permit'),
                permit.get('status'),
                permit.get('date'),
                None,
                None,
                'Finaled' if permit.get('status') and 'Finaled' in permit.get('status') else 'Active'
            ))
            results['events_inserted'] += 1
        except sqlite3.IntegrityError:
            results['events_skipped'] += 1

        # Upsert into building_permits table
        try:
            cursor.execute("""
                INSERT INTO building_permits
                (project_id, permit_number, permit_type, address, status,
                 filed_date, finaled_date, job_value, description, owner, applicant)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(permit_number) DO UPDATE SET
                    project_id = excluded.project_id,
                    status = excluded.status,
                    finaled_date = excluded.finaled_date,
                    job_value = excluded.job_value,
                    description = excluded.description
            """, (
                project_id,
                permit_number,
                permit.get('permit_type'),
                address,
                permit.get('status'),
                permit.get('date'),
                permit.get('finaled_date'),
                permit.get('job_value'),
                permit.get('description'),
                permit.get('owner'),
                permit.get('applicant')
            ))
            results['permits_upserted'] += 1
        except Exception as e:
            results['warnings'].append(f"Error upserting {permit_number}: {e}")

    conn.commit()
    conn.close()

    return results


def parse_pipe_delimited_status(lines: list) -> list:
    """
    Parse Processing Status from pipe-delimited format (Claude sidebar markdown).

    Format:
        === PROCESSING STATUS ===

        Completeness Review (Active):
          Due: 10/12/2024 | Assigned: Sharon Gong | Action: Resubmittal Pending Staff | Date Marked: 09/17/2024 | By: Claudia Garcia
          Due: 10/17/2024 | Assigned: Sharon Gong | Action: Incomplete Pending Applicant | Date Marked: 10/16/2024 | By: Sharon Gong

        Staff Decision:
          Due: -- | Assigned: TBD | Action: -- | Date Marked: -- | By: --
    """
    events = []
    current_stage = None
    current_stage_status = None

    # Pattern for stage headers: "Stage Name (Status):" or "Stage Name:"
    stage_header_pattern = re.compile(
        r'^([A-Za-z][A-Za-z\s]+?)\s*(?:\(([^)]+)\))?\s*:\s*$'
    )

    # Pattern for pipe-delimited event lines
    # Due: 10/12/2024 | Assigned: Sharon Gong | Action: Resubmittal Pending Staff | Date Marked: 09/17/2024 | By: Claudia Garcia
    event_pattern = re.compile(
        r'Due:\s*(\d{2}/\d{2}/\d{4}|--|-|TBD)\s*\|\s*'
        r'Assigned:\s*([^|]+?)\s*\|\s*'
        r'Action:\s*([^|]+?)\s*\|\s*'
        r'Date Marked:\s*(\d{2}/\d{2}/\d{4}|--|-)\s*\|\s*'
        r'By:\s*(.+?)\s*$',
        re.IGNORECASE
    )

    # Known stage names
    stage_names = [
        'Completeness Review', 'Application Processing', 'CEQA Determination',
        'Staff Decision', 'Appeal', 'Hearing Notice', 'Public Hearing',
        'Notice of Decision', 'Case Closed', 'Submittal', 'Distribution',
        'Issuance', 'Inspection', 'Resubmittal', 'Comments Review'
    ]

    for line in lines:
        line_stripped = line.strip()

        # Skip empty lines and section headers
        if not line_stripped or line_stripped.startswith('==='):
            continue

        # Check for stage header
        stage_match = stage_header_pattern.match(line_stripped)
        if stage_match:
            potential_stage = stage_match.group(1).strip()
            stage_status = stage_match.group(2)  # e.g., "Active", "Complete"

            # Verify it's a known stage or contains a stage keyword
            if any(s.lower() in potential_stage.lower() for s in stage_names):
                current_stage = potential_stage
                current_stage_status = stage_status or 'Unknown'
            continue

        # Check for event line
        event_match = event_pattern.search(line_stripped)
        if event_match:
            due_date = event_match.group(1)
            assigned_to = event_match.group(2).strip()
            action = event_match.group(3).strip()
            date_marked = event_match.group(4)
            by_whom = event_match.group(5).strip()

            # Skip entries with no meaningful data
            if action in ['--', '-', ''] or date_marked in ['--', '-', '']:
                continue

            # Clean up assigned_to
            if assigned_to in ['--', '-', 'TBD', '']:
                assigned_to = 'TBD'

            # Clean up by_whom
            if by_whom in ['--', '-', '']:
                by_whom = None

            # Convert date to ISO format
            try:
                dt = datetime.strptime(date_marked, '%m/%d/%Y')
                iso_date = dt.strftime('%Y-%m-%d')
            except:
                iso_date = date_marked

            events.append({
                'stage': current_stage or 'Unknown',
                'action': action,
                'date': iso_date,
                'by': by_whom or 'Unknown',
                'stage_status': current_stage_status or 'Unknown',
                'assigned_to': assigned_to
            })

    return events


def parse_bullet_arrow_status(lines: list) -> list:
    """
    Parse Processing Status from bullet/arrow markdown format.

    Format:
        **1. Completeness Review** ✅
        - Due 01/19/2024, assigned Niloufar → **Resubmittal Pending Staff** on 12/20/2023 by Name
        - Due 05/17/2024 → **Application Complete** on 05/17/2024 by Name
        - Due 05/17/2024 → Marked **Categorically Exempt** on 06/16/2025

    Also handles:
        **2. CEQA Determination** ✅ (Complete) — assigned to TBD
        - Due 05/24/2024 → Marked **Approved** on 09/25/2024 by MJ
    """
    events = []
    current_stage = None

    # Event line patterns - handle various formats:
    # - Due 01/19/2024, assigned Name → **Action** on 12/20/2023 by Name
    # - Due 05/17/2024 → **Action** on 05/17/2024 by Name
    # - Due 05/17/2024 → Marked **Action** on 05/17/2024 by Name
    # - Due 05/17/2024 → Marked **Action** on 05/17/2024
    event_pattern = re.compile(
        r'Due\s+(\d{2}/\d{2}/\d{4})(?:,?\s*assigned\s+([^→\-]+?))?'
        r'\s*[→\->]+\s*'
        r'(?:Marked\s+)?'
        r'\*?\*?([A-Za-z][A-Za-z\s\-]+?)\*?\*?'
        r'\s+on\s+(\d{2}/\d{2}/\d{4})'
        r'(?:\s+by\s+(.+))?',
        re.IGNORECASE
    )

    # Stage header pattern - matches lines like:
    # **1. Completeness Review** ✅
    # **2. CEQA Determination** ✅ (Complete) — assigned to TBD
    stage_header_pattern = re.compile(
        r'^\*\*\s*(?:\d+\.\s*)?([A-Za-z][A-Za-z\s]+?)\s*\*\*',
        re.IGNORECASE
    )

    # Known stage names for fallback matching
    stage_names = [
        'Completeness Review', 'Application Processing', 'CEQA Determination',
        'Staff Decision', 'Appeal', 'Hearing Notice', 'Public Hearing',
        'Notice of Decision', 'Case Closed', 'Submittal', 'Distribution',
        'Issuance', 'Inspection'
    ]

    for line in lines:
        line_stripped = line.strip()

        # Skip empty lines
        if not line_stripped:
            continue

        # First, check if this is an event line (has Due and →)
        # Process event lines BEFORE checking for stage headers
        if ('→' in line_stripped or '->' in line_stripped) and 'Due' in line_stripped:
            # Normalize arrow
            line_norm = line_stripped.replace('->', '→')

            match = event_pattern.search(line_norm)
            if match:
                due_date = match.group(1)
                assigned_to = match.group(2).strip() if match.group(2) else None
                action = match.group(3).strip() if match.group(3) else None
                date_marked = match.group(4)
                by_whom = match.group(5).strip() if match.group(5) else None

                # Clean up assigned_to
                if assigned_to:
                    assigned_to = assigned_to.strip(' ,')
                    if assigned_to in ['-', '—', 'TBD']:
                        assigned_to = 'TBD'

                # Clean up by_whom
                if by_whom:
                    by_whom = by_whom.strip(' ,*')
                    if by_whom in ['-', '—', '']:
                        by_whom = None

                # Clean up action - remove any remaining markdown
                if action:
                    action = action.strip('* ')

                # Skip if no meaningful action
                if not action or action in ['-', '—', 'No data', 'No data recorded']:
                    continue

                # Convert date to ISO format
                try:
                    dt = datetime.strptime(date_marked, '%m/%d/%Y')
                    iso_date = dt.strftime('%Y-%m-%d')
                except:
                    iso_date = date_marked

                events.append({
                    'stage': current_stage or 'Unknown',
                    'action': action,
                    'date': iso_date,
                    'by': by_whom or 'Unknown',
                    'stage_status': 'Complete',
                    'assigned_to': assigned_to
                })
            continue  # Don't process this line as a stage header

        # Check for stage header - only if line starts with ** and contains a stage name
        stage_match = stage_header_pattern.match(line_stripped)
        if stage_match:
            potential_stage = stage_match.group(1).strip()
            # Verify it's a known stage
            for stage in stage_names:
                if stage.lower() in potential_stage.lower():
                    current_stage = stage
                    break
            continue

        # Fallback: check for stage names in lines that look like headers (no Due, no →)
        if '→' not in line_stripped and 'Due' not in line_stripped:
            for stage in stage_names:
                if stage.lower() in line_stripped.lower():
                    # Make sure this looks like a header, not content
                    if line_stripped.startswith('**') or line_stripped.startswith('#'):
                        current_stage = stage
                        break

    return events


def parse_markdown_table_status(lines: list) -> list:
    """
    Parse Processing Status from markdown table format.
    Handles both stage-header format and stage-column format.
    """
    events = []
    current_stage = None
    in_processing_section = False

    # Known stage names for detection
    stage_names = [
        'Completeness Review', 'Application Processing', 'CEQA Determination',
        'Staff Decision', 'Appeal', 'Hearing Notice', 'Public Hearing',
        'Notice of Decision', 'Case Closed', 'Submittal', 'Distribution',
        'Issuance', 'Inspection', 'Resubmittal', 'Comments Review'
    ]

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check for "Processing Status" section header
        if 'Processing Status' in line:
            in_processing_section = True
            i += 1
            continue

        # Check for stage header (e.g., "Completeness Review:" or "**Completeness Review:**")
        stage_header_match = re.match(r'^([A-Za-z][A-Za-z\s]+?):\s*$', line)
        if stage_header_match:
            potential_stage = stage_header_match.group(1).strip()
            if any(s.lower() in potential_stage.lower() for s in stage_names):
                current_stage = potential_stage
            i += 1
            continue

        # Check for table row (contains |)
        if '|' in line:
            # Skip separator rows (|---|---|)
            if re.match(r'^[\s|:-]+$', line):
                i += 1
                continue

            # Parse table row
            cells = [c.strip() for c in line.split('|')]
            cells = [c for c in cells if c]  # Remove empty cells from leading/trailing |

            if not cells:
                i += 1
                continue

            # Check if this is a header row
            header_keywords = ['Due Date', 'Assigned', 'Action', 'Date Marked', 'Stage', 'By', 'Comment']
            is_header = any(kw in ' '.join(cells) for kw in header_keywords)

            if is_header:
                # Determine column positions based on header
                # We'll parse the column layout for subsequent rows
                i += 1
                continue

            # Parse data row - try to detect format
            event = parse_table_row(cells, current_stage, stage_names)
            if event:
                events.append(event)

        i += 1

    return events


def parse_table_row(cells: list, current_stage: str, stage_names: list) -> dict | None:
    """
    Parse a single table row into an event.

    Handles formats:
    - [Due Date, Assigned, Action, Date Marked, By] (5 cells, stage from header)
    - [Due Date, Assigned, Action, Date Marked, By, Comment] (6 cells, stage from header)
    - [Stage, Due Date, Assigned, Action, Date Marked, By] (6 cells, stage in row)
    - [Stage, Due Date, Assigned, Action, Date Marked, By, Comment] (7 cells, stage in row)
    """
    if len(cells) < 4:
        return None

    stage = current_stage
    due_date = None
    assigned_to = None
    action = None
    date_marked = None
    by_whom = None
    comment = None

    # Date pattern
    date_pattern = r'\d{2}/\d{2}/\d{4}'

    # Determine format based on cells
    # If first cell looks like a stage name, it's the stage-column format
    first_cell = cells[0]
    if any(s.lower() in first_cell.lower() for s in stage_names):
        # Stage is in first column
        stage = first_cell
        cells = cells[1:]  # Shift cells

    # Now cells should be: [Due Date, Assigned, Action, Date Marked, By, ?Comment]
    if len(cells) >= 5:
        due_date = cells[0] if re.search(date_pattern, cells[0]) else None
        assigned_to = cells[1] if cells[1] and cells[1] != '-' else None
        action = cells[2] if cells[2] and cells[2] != '-' else None
        date_marked = cells[3] if re.search(date_pattern, cells[3]) else None
        by_whom = cells[4] if cells[4] and cells[4] != '-' else None
        if len(cells) >= 6:
            comment = cells[5] if cells[5] and cells[5] != '-' else None

    # Skip rows with no action or date
    if not action or action == '-':
        return None
    if not date_marked:
        return None

    # Convert date to ISO format
    try:
        dt = datetime.strptime(date_marked, '%m/%d/%Y')
        iso_date = dt.strftime('%Y-%m-%d')
    except:
        iso_date = date_marked

    return {
        'stage': stage or 'Unknown',
        'action': action,
        'date': iso_date,
        'by': by_whom or 'Unknown',
        'stage_status': 'Complete',  # Default for markdown format
        'assigned_to': assigned_to,
        'comment': comment
    }


def parse_original_accela_status(lines: list) -> list:
    """
    Parse Processing Status from original Accela text format.

    Format:
        Complete  Collapse      Issuance
        Due on 06/02/2025, assigned to TBD
        Marked as Issued on 06/02/2025 by Chandra Vogt
    """
    events = []
    current_stage = None
    current_status = None
    assigned_to = None

    # Patterns
    marked_pattern = re.compile(r'Marked (?:as )?(.+?) on (\d{2}/\d{2}/\d{4}) by (.+)', re.IGNORECASE)
    due_pattern = re.compile(r'Due (?:on )?(\d{2}/\d{2}/\d{4}|TBD),?\s*assigned to (.+)', re.IGNORECASE)

    # Stage keywords
    stage_keywords = [
        'Submittal', 'Review', 'Distribution', 'Issuance', 'Inspection',
        'Comments', 'Resubmittal', 'CEQA', 'Appeal', 'Hearing', 'Decision',
        'Closed', 'Processing'
    ]

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for stage header
        if any(stage in line for stage in stage_keywords):
            # Extract stage name (last word or phrase after Collapse/Expand)
            parts = re.split(r'(Complete|Previously Active|Collapse|Expand)\s*', line)
            stage_name = parts[-1].strip() if parts else line

            # Clean up stage name
            stage_name = re.sub(r'^[\s:]+|[\s:]+$', '', stage_name)
            if stage_name:
                current_stage = stage_name

            # Capture stage status (Complete, Previously Active, etc.)
            if 'Complete' in line:
                current_status = 'Complete'
            elif 'Previously Active' in line:
                current_status = 'Previously Active'
            else:
                current_status = 'Active'
            continue

        # Check for "Due on" to capture assigned_to
        due_match = due_pattern.search(line)
        if due_match:
            assigned_to = due_match.group(2)

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
                'by': by_whom,
                'stage_status': current_status or 'Unknown',
                'assigned_to': assigned_to
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
        action = (event.get('action') or '').lower()
        date = event.get('date')
        stage = (event.get('stage') or '').lower()

        # Skip events with no date
        if not date:
            continue

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


# =============================================================================
# NEW: Database save functions
# =============================================================================

def detect_permit_type(permit_number: str) -> str:
    """
    Detect permit type from permit number prefix.

    ZP, PLN = Planning
    B, BP = Building
    """
    if not permit_number:
        return 'Unknown'

    permit_upper = permit_number.upper().strip()

    if permit_upper.startswith('ZP') or permit_upper.startswith('PLN'):
        return 'Planning'
    elif permit_upper.startswith('B') or permit_upper.startswith('BP'):
        return 'Building'
    elif permit_upper.startswith('DEM') or permit_upper.startswith('DP'):
        return 'Demolition'
    else:
        return 'Other'


def normalize_address(address: str) -> str:
    """Normalize address for matching."""
    if not address:
        return ''

    # Uppercase, remove extra spaces
    addr = ' '.join(address.upper().split())

    # Remove common suffixes
    addr = re.sub(r',?\s*(BERKELEY|CA|94\d{3}).*$', '', addr, flags=re.IGNORECASE)

    # Standardize street types
    replacements = [
        (r'\bSTREET\b', 'ST'),
        (r'\bAVENUE\b', 'AVE'),
        (r'\bBOULEVARD\b', 'BLVD'),
        (r'\bDRIVE\b', 'DR'),
        (r'\bROAD\b', 'RD'),
        (r'\bLANE\b', 'LN'),
        (r'\bCOURT\b', 'CT'),
        (r'\bPLACE\b', 'PL'),
        (r'\bWAY\b', 'WY'),
    ]
    for pattern, repl in replacements:
        addr = re.sub(pattern, repl, addr)

    return addr.strip()


def lookup_project_id(conn: sqlite3.Connection, address: str) -> int | None:
    """
    Look up project_id by matching address against projects table.
    Returns project_id or None if no match.
    """
    cursor = conn.cursor()

    # Normalize the input address
    addr_norm = normalize_address(address)

    # Extract street number and name for matching
    parts = addr_norm.split()
    if not parts:
        return None

    # Handle address ranges like "2113-15"
    street_num = parts[0].split('-')[0] if parts else ''
    street_name = parts[1] if len(parts) > 1 else ''

    # Skip if "street number" is not numeric (e.g., "PERMITS")
    if not street_num.isdigit():
        return None

    # Get all projects and compare normalized addresses
    cursor.execute("SELECT DISTINCT id, address_display FROM projects")
    results = cursor.fetchall()

    # First pass: exact normalized match
    for project_id, addr in results:
        if normalize_address(addr) == addr_norm:
            return project_id

    # Second pass: match on street number + street name
    for project_id, addr in results:
        addr_upper = addr.upper()
        if street_num in addr_upper and street_name in addr_upper:
            return project_id

    # Third pass: fuzzy match on street number only (for address ranges)
    for project_id, addr in results:
        addr_norm_db = normalize_address(addr)
        addr_parts = addr_norm_db.split()
        if addr_parts and addr_parts[0].split('-')[0] == street_num:
            # Check if street names are similar
            if len(parts) > 1 and len(addr_parts) > 1:
                if parts[1][:4] == addr_parts[1][:4]:  # Compare first 4 chars of street name
                    return project_id

    # Fourth pass: for address ranges like "2113-15", try matching the second number
    if '-' in parts[0]:
        range_parts = parts[0].split('-')
        if len(range_parts) == 2:
            # Try to reconstruct the full second address (e.g., "2113-15" -> "2115")
            base = range_parts[0]
            suffix = range_parts[1]
            if len(suffix) < len(base):
                alt_num = base[:-len(suffix)] + suffix
                for project_id, addr in results:
                    addr_norm_db = normalize_address(addr)
                    addr_parts = addr_norm_db.split()
                    if addr_parts and addr_parts[0] == alt_num:
                        if len(parts) > 1 and len(addr_parts) > 1:
                            if parts[1][:4] == addr_parts[1][:4]:
                                return project_id

    return None


def save_permit_events(db_path: str, permit_number: str, address: str, text_file: str) -> dict:
    """
    Parse Accela text file and save events to database.

    Returns dict with counts of inserted/skipped records.
    """
    path = Path(text_file)
    if not path.exists():
        return {'error': f"File not found: {text_file}"}

    # Parse the text file
    text = path.read_text()

    # If no permit number provided (address-only file), extract from content
    if permit_number is None:
        # Look for permit patterns like "1. DRCF2024-0004 |" or "PERMIT: ZP2022-0099"
        permit_matches = re.findall(r'(?:^\d+\.\s+|PERMIT:\s*)([A-Z]{2,}[0-9]{4}-[0-9]+)', text, re.MULTILINE)
        if permit_matches:
            # Use the first permit found (usually the most recent/primary)
            permit_number = permit_matches[0]

    # Check if file explicitly indicates no processing status records
    text_lower = text.lower()
    has_no_records = (
        'no records found' in text_lower or
        'no processing status records' in text_lower or
        '(no processing status records found)' in text_lower
    )

    events = parse_processing_status(text)
    milestones = extract_key_milestones(events)

    if not events:
        if has_no_records:
            # This is a valid permit with no processing history - not an error
            return {
                'permit_number': permit_number,
                'address': address,
                'events_parsed': 0,
                'events_inserted': 0,
                'events_skipped': 0,
                'no_processing_status': True
            }
        return {'error': "No events parsed from file", 'events': 0}

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Look up project_id
    project_id = lookup_project_id(conn, address)

    # Detect permit type
    permit_type = detect_permit_type(permit_number)

    # Get earliest event date for filed_date (filter out None dates)
    valid_dates = [e['date'] for e in events if e.get('date')]
    filed_date = min(valid_dates) if valid_dates else None

    # Track results
    results = {
        'permit_number': permit_number,
        'address': address,
        'project_id': project_id,
        'permit_type': permit_type,
        'events_parsed': len(events),
        'events_inserted': 0,
        'events_skipped': 0,
        'permit_upserted': False,
        'warnings': []
    }

    if project_id is None:
        results['warnings'].append(f"No project match for address: {address}")

    # Ensure permit_events table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            address TEXT,
            permit_number TEXT,
            stage TEXT,
            action TEXT,
            event_date TEXT,
            assigned_to TEXT,
            marked_by TEXT,
            comment TEXT,
            stage_status TEXT,
            source TEXT DEFAULT 'accela',
            imported_at TEXT DEFAULT (datetime('now')),
            permit_type TEXT,
            UNIQUE(permit_number, stage, action, event_date)
        )
    """)

    # Insert events (skip duplicates)
    for event in events:
        try:
            cursor.execute("""
                INSERT INTO permit_events
                (project_id, address, permit_number, stage, action, event_date,
                 assigned_to, marked_by, stage_status, source, permit_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'accela', ?)
            """, (
                project_id,
                address,
                permit_number,
                event.get('stage'),
                event.get('action'),
                event.get('date'),
                event.get('assigned_to'),
                event.get('by'),
                event.get('stage_status'),
                permit_type
            ))
            results['events_inserted'] += 1
        except sqlite3.IntegrityError:
            # Duplicate - skip
            results['events_skipped'] += 1

    # Ensure project_permits table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_permits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            permit_number TEXT NOT NULL UNIQUE,
            permit_type TEXT,
            permit_module TEXT,
            address TEXT,
            filed_date TEXT,
            status TEXT,
            status_date TEXT,
            is_primary INTEGER DEFAULT 0,
            source TEXT DEFAULT 'accela',
            imported_at TEXT DEFAULT (datetime('now')),
            permit_year INTEGER,
            permit_sequence INTEGER,
            permit_prefix TEXT
        )
    """)

    # Determine status from milestones
    if milestones['is_completed']:
        status = 'Completed'
    elif milestones['building_permit_date']:
        status = 'Under Construction'
    elif milestones['zoning_approved_date']:
        status = 'Approved'
    else:
        status = 'In Review'

    # Upsert project_permits
    try:
        cursor.execute("""
            INSERT INTO project_permits
            (project_id, permit_number, permit_type, address, filed_date, status, status_date, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'accela')
            ON CONFLICT(permit_number) DO UPDATE SET
                filed_date = COALESCE(excluded.filed_date, filed_date),
                status = excluded.status,
                status_date = excluded.status_date,
                imported_at = datetime('now')
        """, (
            project_id,
            permit_number,
            permit_type,
            address,
            filed_date,
            status,
            milestones['last_status_date']
        ))
        results['permit_upserted'] = True
    except Exception as e:
        results['warnings'].append(f"Failed to upsert project_permits: {e}")

    conn.commit()
    conn.close()

    return results


def save_command(args):
    """
    Handle the 'save' command.

    Usage: python accela_workflow.py save --db PATH --permit NUM --address ADDR --file FILE
    """
    results = save_permit_events(args.db, args.permit, args.address, args.file)

    if 'error' in results:
        print(f"ERROR: {results['error']}")
        return 1

    print(f"\n{'='*60}")
    print(f"SAVE RESULTS: {results['permit_number']}")
    print(f"{'='*60}")
    print(f"Address:        {results['address']}")
    print(f"Project ID:     {results['project_id'] or 'NOT FOUND'}")
    print(f"Permit Type:    {results['permit_type']}")
    print(f"Events Parsed:  {results['events_parsed']}")
    print(f"Events Inserted:{results['events_inserted']}")
    print(f"Events Skipped: {results['events_skipped']} (duplicates)")
    print(f"Permit Upserted:{results['permit_upserted']}")

    if results['warnings']:
        print(f"\nWarnings:")
        for w in results['warnings']:
            print(f"  - {w}")

    print(f"{'='*60}\n")

    return 0


def extract_address_from_file(filepath: str) -> str | None:
    """
    Extract address from file content (ADDRESS: line).
    Used for address-only files without permit prefix in filename.
    """
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line.startswith('ADDRESS:'):
                    # Extract address, remove city/state/zip
                    addr = line.replace('ADDRESS:', '').strip()
                    addr = re.sub(r',?\s*(BERKELEY|CA|94\d{3}).*$', '', addr, flags=re.IGNORECASE)
                    return addr.strip()
    except Exception:
        pass
    return None


def parse_filename(filename: str) -> tuple[str, str] | None:
    """
    Parse permit number and address from filename.

    Expected formats:
    - ZP2024-0058_2700_SHATTUCK.txt -> (ZP2024-0058, 2700 SHATTUCK)
    - 1598_UNIVERSITY.txt -> (None, 1598 UNIVERSITY)  # address-only file

    Returns (permit_number, address) or None if can't parse.
    permit_number may be None for address-only files.
    """
    name = Path(filename).stem  # Remove .txt extension

    # Try to split on first underscore
    parts = name.split('_', 1)
    if len(parts) < 2:
        return None

    first_part = parts[0]

    # Check if first part is a permit number (has letters or dashes) vs street number (digits only)
    # Permit numbers: ZP2024-0058, PLN2024-0011, B2025-05534, DRCF2024-0004
    # Street numbers: 1598, 1701, 2555
    is_permit_number = bool(re.search(r'[A-Za-z-]', first_part))

    if is_permit_number:
        permit_number = first_part
        # Convert remaining underscores to spaces for address
        address = parts[1].replace('_', ' ')
    else:
        # First part is a street number - whole filename is an address
        permit_number = None
        address = name.replace('_', ' ')

    return permit_number, address


def save_batch_command(args):
    """
    Handle the 'save_batch' command.

    Usage: python accela_workflow.py save_batch --db PATH --dir DIRECTORY

    Processes all .txt files in DIRECTORY with names like:
    ZP2024-0058_2700_SHATTUCK.txt
    """
    dir_path = Path(args.dir)
    if not dir_path.exists():
        print(f"ERROR: Directory not found: {args.dir}")
        return 1

    # Find all .txt files
    txt_files = list(dir_path.glob('*.txt'))

    if not txt_files:
        print(f"No .txt files found in {args.dir}")
        return 1

    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING: {len(txt_files)} files")
    print(f"Database: {args.db}")
    print(f"{'='*60}\n")

    # Track totals
    totals = {
        'files_processed': 0,
        'files_skipped': 0,
        'events_inserted': 0,
        'events_skipped': 0,
        'permits_upserted': 0,
        'warnings': []
    }

    for txt_file in sorted(txt_files):
        filename = txt_file.name

        # Check if this is a Building permit file (starts with B_)
        if filename.startswith('B_'):
            # Process as Building permit file
            results = save_building_permit_events(args.db, str(txt_file))

            if 'error' in results:
                print(f"ERROR: {filename}: {results['error']}")
                totals['files_skipped'] += 1
                continue

            # Handle files with no permits or no qualifying permits
            if results.get('no_permits') or results.get('no_qualifying_permits'):
                print(f"NO PERMITS: {filename} (no qualifying building permits)")
                totals['files_processed'] += 1
                continue

            # Print progress
            address = results.get('address', 'Unknown')
            status = "OK" if results.get('project_id') else "NO PROJECT MATCH"
            print(f"{status}: [BUILDING] {address} "
                  f"({results['permits_found']} permits, {results['events_inserted']} events inserted)")

            # Update totals
            totals['files_processed'] += 1
            totals['events_inserted'] += results.get('events_inserted', 0)
            totals['events_skipped'] += results.get('events_skipped', 0)
            totals['permits_upserted'] += results.get('permits_upserted', 0)
            totals['warnings'].extend(results.get('warnings', []))
            continue

        # Otherwise, process as Planning permit file
        parsed = parse_filename(filename)

        if parsed is None:
            print(f"SKIP: {filename} (can't parse filename)")
            totals['files_skipped'] += 1
            totals['warnings'].append(f"Can't parse filename: {filename}")
            continue

        permit_number, address = parsed

        # For address-only files (no permit in filename), extract address from file content
        if permit_number is None:
            file_address = extract_address_from_file(str(txt_file))
            if file_address:
                address = file_address

        # Process file
        results = save_permit_events(args.db, permit_number, address, str(txt_file))

        if 'error' in results:
            print(f"ERROR: {filename}: {results['error']}")
            totals['files_skipped'] += 1
            continue

        # Handle permits with no processing status (valid, not an error)
        if results.get('no_processing_status'):
            print(f"NO STATUS: {permit_number} @ {address} (no processing status records)")
            totals['files_processed'] += 1
            continue

        # Print progress
        status = "OK" if results['project_id'] else "NO PROJECT MATCH"
        print(f"{status}: {permit_number} @ {address} "
              f"({results['events_inserted']} inserted, {results['events_skipped']} skipped)")

        # Update totals
        totals['files_processed'] += 1
        totals['events_inserted'] += results['events_inserted']
        totals['events_skipped'] += results['events_skipped']
        if results['permit_upserted']:
            totals['permits_upserted'] += 1
        totals['warnings'].extend(results['warnings'])

    # Print summary
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"Files Processed:  {totals['files_processed']}")
    print(f"Files Skipped:    {totals['files_skipped']}")
    print(f"Events Inserted:  {totals['events_inserted']}")
    print(f"Events Skipped:   {totals['events_skipped']} (duplicates)")
    print(f"Permits Upserted: {totals['permits_upserted']}")

    if totals['warnings']:
        print(f"\nWarnings ({len(totals['warnings'])}):")
        for w in totals['warnings'][:10]:
            print(f"  - {w}")
        if len(totals['warnings']) > 10:
            print(f"  ... and {len(totals['warnings']) - 10} more")

    print(f"{'='*60}\n")

    return 0


# =============================================================================
# NEW: Discover command - systematic permit range exploration
# =============================================================================

def generate_accela_permit_url(permit_number: str) -> str:
    """
    Generate direct Accela URL for a specific permit number.

    The Accela system uses a global search that can find permits by number.
    """
    base_url = "https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx"
    params = {
        'module': 'Planning',
        'SearchType': 'GlobalSearch',
        'QueryText': permit_number
    }
    return f"{base_url}?module=Planning&SearchType=GlobalSearch&QueryText={urllib.parse.quote(permit_number)}"


def find_permit_gaps(year: int, db_path: str = None) -> dict:
    """
    Find gaps in the permit sequence for a given year.

    Reads all ZP{year}-XXXX permits from:
    1. The database (permit_events, project_permits tables)
    2. The housing_projects_FINAL.csv file

    Returns dict with:
    - found_permits: set of permit numbers found
    - found_sequences: set of sequence numbers (integers)
    - max_sequence: highest sequence number found
    - gaps: list of missing sequence numbers
    """
    db_path = db_path or DB_PATH
    prefix = f"ZP{year}-"

    found_permits = set()
    found_sequences = set()

    # 1. Check permit_events table
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT permit_number FROM permit_events
            WHERE permit_number LIKE ?
        """, (f"{prefix}%",))

        for (permit,) in cursor.fetchall():
            found_permits.add(permit)
            # Extract sequence number
            match = re.search(rf'{prefix}(\d+)', permit)
            if match:
                found_sequences.add(int(match.group(1)))

        # 2. Check project_permits table if it exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='project_permits'
        """)
        if cursor.fetchone():
            cursor.execute("""
                SELECT DISTINCT permit_number FROM project_permits
                WHERE permit_number LIKE ?
            """, (f"{prefix}%",))

            for (permit,) in cursor.fetchall():
                found_permits.add(permit)
                match = re.search(rf'{prefix}(\d+)', permit)
                if match:
                    found_sequences.add(int(match.group(1)))

        conn.close()
    except Exception as e:
        print(f"Warning: Could not read database: {e}")

    # 3. Check housing_projects_FINAL.csv
    csv_path = ROOT / 'data/processed/housing_projects_FINAL.csv'
    if csv_path.exists():
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    permits = row.get('permits', '')
                    for permit in permits.split(','):
                        permit = permit.strip()
                        if permit.startswith(prefix):
                            found_permits.add(permit)
                            match = re.search(rf'{prefix}(\d+)', permit)
                            if match:
                                found_sequences.add(int(match.group(1)))
        except Exception as e:
            print(f"Warning: Could not read CSV: {e}")

    # 4. Check city APR reference data
    apr_path = ROOT / 'data/reference/city_apr_2024_table_a.csv'
    if apr_path.exists() and year == 2024:
        try:
            with open(apr_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    permit = row.get('JURS_TRACKING_ID', '').strip()
                    if permit.startswith(prefix):
                        found_permits.add(permit)
                        match = re.search(rf'{prefix}(\d+)', permit)
                        if match:
                            found_sequences.add(int(match.group(1)))
        except Exception as e:
            print(f"Warning: Could not read APR CSV: {e}")

    # Calculate gaps
    if found_sequences:
        max_seq = max(found_sequences)
        all_possible = set(range(1, max_seq + 1))
        gaps = sorted(all_possible - found_sequences)
    else:
        max_seq = 0
        gaps = []

    return {
        'year': year,
        'prefix': prefix,
        'found_permits': found_permits,
        'found_sequences': found_sequences,
        'max_sequence': max_seq,
        'gaps': gaps
    }


def generate_discover_html(year: int, start: int, end: int, known_permits: set = None) -> str:
    """
    Generate HTML file with clickable links for a range of permit numbers.

    Args:
        year: Permit year (e.g., 2024)
        start: Starting sequence number
        end: Ending sequence number
        known_permits: Optional set of permit numbers we already have data for

    Returns path to generated HTML file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    prefix = f"ZP{year}-"
    known_permits = known_permits or set()
    known_sequences = set()

    # Extract sequences from known permits
    for permit in known_permits:
        match = re.search(rf'{prefix}(\d+)', permit)
        if match:
            known_sequences.add(int(match.group(1)))

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Accela Permit Discovery - ZP{year}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 20px;
            max-width: 1200px;
        }}
        h1 {{ color: #1565C0; }}
        .stats {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .stats span {{
            display: inline-block;
            margin-right: 30px;
            font-weight: bold;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 8px;
        }}
        .permit {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            text-align: center;
            transition: all 0.2s;
        }}
        .permit a {{
            text-decoration: none;
            color: #1565C0;
            font-family: monospace;
            font-size: 14px;
        }}
        .permit:hover {{
            background: #e3f2fd;
            border-color: #1565C0;
        }}
        .permit.known {{
            background: #c8e6c9;
            border-color: #4CAF50;
        }}
        .permit.known a {{ color: #2E7D32; }}
        .permit.checked {{
            background: #fff3e0;
            border-color: #FF9800;
        }}
        .permit.not-found {{
            background: #ffebee;
            border-color: #f44336;
            opacity: 0.6;
        }}
        .legend {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-box {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
            border: 1px solid #999;
        }}
        .instructions {{
            background: #fff3e0;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .filter-bar {{
            margin-bottom: 15px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 5px;
        }}
        .filter-bar label {{ margin-right: 15px; }}
        button {{
            padding: 8px 16px;
            margin-right: 10px;
            cursor: pointer;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
        }}
        button:hover {{ background: #e3f2fd; }}
    </style>
</head>
<body>
    <h1>Accela Permit Discovery: ZP{year}</h1>

    <div class="stats">
        <span>Range: {prefix}{start:04d} - {prefix}{end:04d}</span>
        <span>Total: {end - start + 1} permits</span>
        <span>Known: {len([s for s in range(start, end+1) if s in known_sequences])}</span>
        <span>To Check: {len([s for s in range(start, end+1) if s not in known_sequences])}</span>
    </div>

    <div class="instructions">
        <strong>Instructions:</strong>
        <ol>
            <li>Click a permit number to search in Accela</li>
            <li>If the permit exists, collect the data</li>
            <li>Right-click and mark as "checked" or "not found"</li>
            <li>Green = already in our database, White = needs checking</li>
        </ol>
    </div>

    <div class="legend">
        <div class="legend-item">
            <div class="legend-box" style="background: #c8e6c9;"></div>
            <span>Known (in database)</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background: white;"></div>
            <span>Unchecked</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background: #fff3e0;"></div>
            <span>Checked (has data)</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background: #ffebee;"></div>
            <span>Not Found</span>
        </div>
    </div>

    <div class="filter-bar">
        <button onclick="showAll()">Show All</button>
        <button onclick="showUnchecked()">Show Unchecked Only</button>
        <button onclick="showGaps()">Show Gaps Only</button>
        <button onclick="clearMarks()">Clear All Marks</button>
    </div>

    <div class="grid">
"""

    # Generate permit links
    for seq in range(start, end + 1):
        permit = f"{prefix}{seq:04d}"
        url = generate_accela_permit_url(permit)

        css_class = "permit"
        if seq in known_sequences:
            css_class += " known"

        html_content += f"""        <div class="{css_class}" id="p{seq}" oncontextmenu="markPermit(event, {seq})">
            <a href="{url}" target="_blank">{permit}</a>
        </div>
"""

    html_content += f"""    </div>

    <script>
        const knownSequences = new Set({list(known_sequences)});

        // Load saved state from localStorage
        function loadState() {{
            const state = JSON.parse(localStorage.getItem('discover_{year}') || '{{}}');
            for (const [seq, status] of Object.entries(state)) {{
                const el = document.getElementById('p' + seq);
                if (el && !el.classList.contains('known')) {{
                    el.classList.add(status);
                }}
            }}
        }}

        // Save state
        function saveState(seq, status) {{
            const state = JSON.parse(localStorage.getItem('discover_{year}') || '{{}}');
            if (status) {{
                state[seq] = status;
            }} else {{
                delete state[seq];
            }}
            localStorage.setItem('discover_{year}', JSON.stringify(state));
        }}

        // Mark permit on right-click
        function markPermit(event, seq) {{
            event.preventDefault();
            const el = document.getElementById('p' + seq);
            if (el.classList.contains('known')) return;

            if (el.classList.contains('checked')) {{
                el.classList.remove('checked');
                el.classList.add('not-found');
                saveState(seq, 'not-found');
            }} else if (el.classList.contains('not-found')) {{
                el.classList.remove('not-found');
                saveState(seq, null);
            }} else {{
                el.classList.add('checked');
                saveState(seq, 'checked');
            }}
        }}

        // Filter functions
        function showAll() {{
            document.querySelectorAll('.permit').forEach(el => el.style.display = '');
        }}

        function showUnchecked() {{
            document.querySelectorAll('.permit').forEach(el => {{
                const isUnchecked = !el.classList.contains('known') &&
                                   !el.classList.contains('checked') &&
                                   !el.classList.contains('not-found');
                el.style.display = isUnchecked ? '' : 'none';
            }});
        }}

        function showGaps() {{
            document.querySelectorAll('.permit').forEach(el => {{
                const isGap = !el.classList.contains('known');
                el.style.display = isGap ? '' : 'none';
            }});
        }}

        function clearMarks() {{
            if (confirm('Clear all marks? This cannot be undone.')) {{
                localStorage.removeItem('discover_{year}');
                document.querySelectorAll('.permit').forEach(el => {{
                    el.classList.remove('checked', 'not-found');
                }});
            }}
        }}

        // Initialize
        loadState();
    </script>
</body>
</html>
"""

    html_path = OUTPUT_DIR / f'accela_discover_{year}.html'
    with open(html_path, 'w') as f:
        f.write(html_content)

    return str(html_path)


def discover_command(args):
    """
    Handle the 'discover' command.

    Modes:
    1. Range mode: --year 2024 --range 1 200
       Generates HTML with links for ZP2024-0001 through ZP2024-0200

    2. Gap finder mode: --year 2024 --find-gaps
       Reads existing permits and identifies missing sequence numbers
    """
    year = args.year

    # First, find what we already have
    gap_info = find_permit_gaps(year, str(DB_PATH))

    print(f"\n{'='*60}")
    print(f"PERMIT DISCOVERY: ZP{year}")
    print(f"{'='*60}")
    print(f"Permits found in database: {len(gap_info['found_permits'])}")
    print(f"Sequence numbers found:    {len(gap_info['found_sequences'])}")
    print(f"Highest sequence:          {gap_info['max_sequence']}")

    if args.find_gaps:
        # Gap finder mode
        gaps = gap_info['gaps']
        print(f"\n{'='*60}")
        print(f"GAP ANALYSIS")
        print(f"{'='*60}")
        print(f"Missing sequence numbers:  {len(gaps)}")

        if gaps:
            # Group consecutive gaps for readability
            ranges = []
            start = gaps[0]
            prev = gaps[0]

            for g in gaps[1:] + [None]:
                if g is None or g != prev + 1:
                    if start == prev:
                        ranges.append(f"ZP{year}-{start:04d}")
                    else:
                        ranges.append(f"ZP{year}-{start:04d} to ZP{year}-{prev:04d}")
                    if g is not None:
                        start = g
                prev = g if g is not None else prev

            print(f"\nMissing ranges:")
            for r in ranges[:20]:
                print(f"  {r}")
            if len(ranges) > 20:
                print(f"  ... and {len(ranges) - 20} more ranges")

            print(f"\nAll missing permit numbers ({len(gaps)}):")
            for i, g in enumerate(gaps):
                if i < 50:
                    print(f"  ZP{year}-{g:04d}")
                elif i == 50:
                    print(f"  ... and {len(gaps) - 50} more")
                    break
        else:
            print("No gaps found - sequence is complete!")

        # Generate HTML for gaps only
        if gaps and not args.range:
            # Create HTML showing just the gaps
            html_path = generate_discover_html(
                year,
                min(gaps),
                max(gaps),
                gap_info['found_permits']
            )
            print(f"\nGenerated HTML for gaps: {html_path}")
            print(f"Open in browser: file://{Path(html_path).absolute()}")

    if args.range:
        # Range mode
        start, end = args.range
        print(f"\n{'='*60}")
        print(f"GENERATING RANGE: ZP{year}-{start:04d} to ZP{year}-{end:04d}")
        print(f"{'='*60}")

        html_path = generate_discover_html(
            year,
            start,
            end,
            gap_info['found_permits']
        )

        # Count how many in range are already known
        known_in_range = len([s for s in range(start, end+1) if s in gap_info['found_sequences']])
        unknown_in_range = (end - start + 1) - known_in_range

        print(f"Total permits in range:    {end - start + 1}")
        print(f"Already known:             {known_in_range}")
        print(f"Need to check:             {unknown_in_range}")
        print(f"\nGenerated HTML: {html_path}")
        print(f"Open in browser: file://{Path(html_path).absolute()}")

    if not args.find_gaps and not args.range:
        print("\nNo action specified. Use --range START END or --find-gaps")
        print("\nExamples:")
        print(f"  python accela_workflow.py discover --year {year} --range 1 200")
        print(f"  python accela_workflow.py discover --year {year} --find-gaps")
        print(f"  python accela_workflow.py discover --year {year} --find-gaps --range 1 200")

    print(f"{'='*60}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Accela Data Collection Workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python accela_workflow.py generate
  python accela_workflow.py parse processing_status.txt
  python accela_workflow.py save --db databases/berkeley_housing_analysis.db \\
      --permit ZP2024-0058 --address "2700 SHATTUCK Ave" --file zp2024-0058.txt
  python accela_workflow.py save_batch --db databases/berkeley_housing_analysis.db \\
      --dir data/raw/accela_exports/

  # Discover permits in a range:
  python accela_workflow.py discover --year 2024 --range 1 200

  # Find gaps in existing permit sequence:
  python accela_workflow.py discover --year 2024 --find-gaps

  # Both: find gaps and generate HTML for full range:
  python accela_workflow.py discover --year 2024 --find-gaps --range 1 200
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # generate command
    subparsers.add_parser('generate', help='Generate Accela collection URLs')

    # parse command
    parse_parser = subparsers.add_parser('parse', help='Parse Processing Status text file')
    parse_parser.add_argument('file', help='Text file containing Processing Status')

    # save command
    save_parser = subparsers.add_parser('save', help='Parse and save events to database')
    save_parser.add_argument('--db', required=True, help='Path to SQLite database')
    save_parser.add_argument('--permit', required=True, help='Permit number (e.g., ZP2024-0058)')
    save_parser.add_argument('--address', required=True, help='Project address')
    save_parser.add_argument('--file', required=True, help='Text file with Processing Status')

    # save_batch command
    batch_parser = subparsers.add_parser('save_batch', help='Batch process multiple text files')
    batch_parser.add_argument('--db', required=True, help='Path to SQLite database')
    batch_parser.add_argument('--dir', required=True,
                              help='Directory with .txt files named like ZP2024-0058_2700_SHATTUCK.txt')

    # discover command
    discover_parser = subparsers.add_parser('discover', help='Discover permits in a range or find gaps')
    discover_parser.add_argument('--year', type=int, required=True,
                                 help='Permit year (e.g., 2024)')
    discover_parser.add_argument('--range', type=int, nargs=2, metavar=('START', 'END'),
                                 help='Generate URLs for permit range (e.g., --range 1 200)')
    discover_parser.add_argument('--find-gaps', action='store_true',
                                 help='Find missing permit numbers in sequence')

    # Parse arguments
    args = parser.parse_args()

    if args.command is None:
        # Backwards compatibility: check sys.argv for old-style commands
        if len(sys.argv) >= 2:
            old_cmd = sys.argv[1]
            if old_cmd == 'generate':
                generate_accela_urls()
                return
            elif old_cmd == 'parse' and len(sys.argv) >= 3:
                parse_file(sys.argv[2])
                return

        parser.print_help()
        sys.exit(1)

    if args.command == 'generate':
        generate_accela_urls()

    elif args.command == 'parse':
        parse_file(args.file)

    elif args.command == 'save':
        sys.exit(save_command(args))

    elif args.command == 'save_batch':
        sys.exit(save_batch_command(args))

    elif args.command == 'discover':
        sys.exit(discover_command(args))


if __name__ == '__main__':
    main()
