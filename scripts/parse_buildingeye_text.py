#!/usr/bin/env python3
"""
Parse BuildingEye copy-pasted popup text into structured CSV.

Usage:
    python parse_buildingeye_text.py input.txt output.csv

Input format (from BuildingEye popup):
    2555 COLLEGE AVE, BERKELEY, CA 94704
    Permit Number:
    B2024-05972
    Permit Type:
    Electrical Permit
    Received Date:
    Dec 18, 2024
    Description:
    Install 16 KW PV solar panels...
    Status:
    Jul 22, 2025 - Finaled
    More details
"""

import re
import csv
import sys
from pathlib import Path
from datetime import datetime


def parse_date(date_str: str) -> str:
    """Convert 'Dec 18, 2024' to '2024-12-18' ISO format."""
    if not date_str:
        return ''
    try:
        # Try "Mon DD, YYYY" format
        dt = datetime.strptime(date_str.strip(), '%b %d, %Y')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Try "Month DD, YYYY" format
            dt = datetime.strptime(date_str.strip(), '%B %d, %Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return date_str  # Return original if parsing fails


def extract_status_date(status_str: str) -> tuple:
    """
    Extract date and status from 'Jul 22, 2025 - Finaled'.
    Returns (date, status_text).
    """
    if not status_str:
        return ('', '')

    # Pattern: "Mon DD, YYYY - Status"
    match = re.match(r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s*-\s*(.+)', status_str.strip())
    if match:
        date_str = parse_date(match.group(1))
        status_text = match.group(2).strip()
        return (date_str, status_text)

    return ('', status_str.strip())


def parse_buildingeye_text(text: str) -> list:
    """
    Parse BuildingEye popup text into list of permit dictionaries.
    """
    permits = []

    # Split by "More details" which ends each permit entry
    entries = re.split(r'More details\s*', text, flags=re.IGNORECASE)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        permit = {
            'address': '',
            'permit_number': '',
            'permit_type': '',
            'received_date': '',
            'description': '',
            'status_date': '',
            'status': ''
        }

        lines = [l.strip() for l in entry.split('\n') if l.strip()]

        if not lines:
            continue

        # First line is usually the address (contains BERKELEY, CA)
        i = 0
        if 'BERKELEY' in lines[0].upper() or re.match(r'^\d+\s+', lines[0]):
            permit['address'] = lines[0]
            i = 1

        # Parse key-value pairs
        while i < len(lines):
            line = lines[i]

            if line.lower().startswith('permit number'):
                # Next line is the value
                if i + 1 < len(lines) and not ':' in lines[i + 1]:
                    permit['permit_number'] = lines[i + 1]
                    i += 2
                elif ':' in line:
                    permit['permit_number'] = line.split(':', 1)[1].strip()
                    i += 1
                else:
                    i += 1

            elif line.lower().startswith('permit type'):
                if i + 1 < len(lines) and not lines[i + 1].lower().startswith(('permit', 'received', 'description', 'status')):
                    permit['permit_type'] = lines[i + 1]
                    i += 2
                elif ':' in line:
                    permit['permit_type'] = line.split(':', 1)[1].strip()
                    i += 1
                else:
                    i += 1

            elif line.lower().startswith('received date'):
                if i + 1 < len(lines) and not lines[i + 1].lower().startswith(('permit', 'received', 'description', 'status')):
                    permit['received_date'] = parse_date(lines[i + 1])
                    i += 2
                elif ':' in line:
                    permit['received_date'] = parse_date(line.split(':', 1)[1].strip())
                    i += 1
                else:
                    i += 1

            elif line.lower().startswith('description'):
                # Description may span multiple lines until next field
                desc_parts = []
                if ':' in line:
                    desc_parts.append(line.split(':', 1)[1].strip())
                i += 1
                while i < len(lines) and not lines[i].lower().startswith(('permit', 'received', 'description', 'status')):
                    desc_parts.append(lines[i])
                    i += 1
                permit['description'] = ' '.join(desc_parts)

            elif line.lower().startswith('status'):
                if i + 1 < len(lines) and not lines[i + 1].lower().startswith(('permit', 'received', 'description', 'status', 'more')):
                    status_date, status_text = extract_status_date(lines[i + 1])
                    permit['status_date'] = status_date
                    permit['status'] = status_text
                    i += 2
                elif ':' in line:
                    status_date, status_text = extract_status_date(line.split(':', 1)[1].strip())
                    permit['status_date'] = status_date
                    permit['status'] = status_text
                    i += 1
                else:
                    i += 1
            else:
                i += 1

        # Only add if we have at least a permit number
        if permit['permit_number']:
            permits.append(permit)

    return permits


def write_csv(permits: list, output_path: Path):
    """Write permits to CSV file."""
    if not permits:
        print("No permits to write")
        return

    fieldnames = ['address', 'permit_number', 'permit_type', 'received_date',
                  'description', 'status_date', 'status']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(permits)

    print(f"Wrote {len(permits)} permits to {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_buildingeye_text.py input.txt [output.csv]")
        print("\nOr run interactively:")
        print("  python parse_buildingeye_text.py --demo")
        sys.exit(1)

    if sys.argv[1] == '--demo':
        # Demo with sample data
        sample = """
2555 COLLEGE AVE, BERKELEY, CA 94704
Permit Number:
B2024-05972
Permit Type:
Electrical Permit
Received Date:
Dec 18, 2024
Description:
Install 16 KW PV solar panels (40 modules) on the roof with two (2) Batteries.
Status:
Jul 22, 2025 - Finaled
More details
2555 COLLEGE AVE, BERKELEY, CA 94704
Permit Number:
B2023-02975
Permit Type:
Building Permit
Received Date:
Jun 09, 2023
Description:
Construction of a 9,815 SF, four story 11-unit + attached ADU multifamily residential building.
Status:
Jul 25, 2025 - Finaled
More details
"""
        permits = parse_buildingeye_text(sample)
        print(f"Parsed {len(permits)} permits:")
        for p in permits:
            print(f"  {p['permit_number']}: {p['address'][:30]}... ({p['status']})")
        return

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_suffix('.csv')

    print(f"Reading: {input_path}")
    text = input_path.read_text(encoding='utf-8')

    permits = parse_buildingeye_text(text)
    print(f"Parsed {len(permits)} permits")

    write_csv(permits, output_path)


if __name__ == '__main__':
    main()
