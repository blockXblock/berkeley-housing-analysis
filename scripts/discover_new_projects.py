#!/usr/bin/env python3
"""
Discover new housing projects not in our database.

Sources:
- SFYimby Berkeley articles (from saved scan file or RSS)
- Corridor scan files (manual observations)
- Accela permit searches

Usage:
    python scripts/discover_new_projects.py data/raw/corridor_scans/sfyimby_scan.txt
    python scripts/discover_new_projects.py --scan-file FILE
    python scripts/discover_new_projects.py --compare-only  # Just compare existing files

Output:
    - Prints new projects not in FINAL.csv
    - Optionally generates data/processed/new_projects_discovered.csv
"""

import csv
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class DiscoveredProject:
    """A project discovered from external sources."""
    address: str
    units: Optional[int]
    source: str
    source_date: Optional[str]
    description: Optional[str]
    developer: Optional[str]
    permit_hint: Optional[str]
    url: Optional[str]
    in_database: bool = False
    matched_id: Optional[int] = None


def normalize_address(addr: str) -> str:
    """Normalize address for comparison."""
    if not addr:
        return ''
    addr = ' '.join(addr.upper().split())
    # Remove city/state/zip
    addr = re.sub(r',?\s*(BERKELEY|CA|94\d{3}).*$', '', addr, re.I)
    # Standardize suffixes
    addr = re.sub(r'\bSTREET\b', 'ST', addr)
    addr = re.sub(r'\bAVENUE\b', 'AVE', addr)
    addr = re.sub(r'\bBOULEVARD\b', 'BLVD', addr)
    addr = re.sub(r'\bDRIVE\b', 'DR', addr)
    addr = re.sub(r'\bROAD\b', 'RD', addr)
    return addr.strip()


def extract_street_key(addr: str) -> str:
    """Extract number + first word for matching."""
    norm = normalize_address(addr)
    parts = norm.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1][:4]}"
    elif parts:
        return parts[0]
    return ''


def load_existing_projects(final_csv: str) -> dict:
    """Load existing projects from FINAL.csv."""
    projects = {}
    with open(final_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            addr = row.get('address_display', '')
            key = extract_street_key(addr)
            projects[key] = {
                'id': row.get('id'),
                'address': addr,
                'units': row.get('net_units'),
                'status': row.get('status'),
                'permits': row.get('permits')
            }
    return projects


def parse_sfyimby_scan(filepath: str) -> List[DiscoveredProject]:
    """
    Parse a SFYimby scan file.

    Expected format (flexible):
    - Lines with addresses and unit counts
    - Format: "ADDRESS - N units" or "N units at ADDRESS"
    - URLs on separate lines
    - Dates in various formats
    """
    projects = []

    with open(filepath, 'r') as f:
        content = f.read()

    # Split into chunks by double newlines or horizontal rules
    chunks = re.split(r'\n{2,}|---+|===+', content)

    current_url = None
    current_date = None

    for chunk in chunks:
        lines = chunk.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for URL
            url_match = re.search(r'https?://[^\s]+', line)
            if url_match:
                current_url = url_match.group(0)
                continue

            # Check for date
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})|(\d{4}-\d{2}-\d{2})', line)
            if date_match:
                current_date = date_match.group(0)

            # Try to extract address and units
            # Pattern 1: "123 Street Name - 50 units"
            match1 = re.search(r'(\d+\s+[A-Za-z][A-Za-z\s]+(?:St|Ave|Way|Blvd|Rd|Dr|Ln|Ct|Pl)?)\s*[-–—]\s*(\d+)\s*(?:units?|apt|dwelling)', line, re.I)

            # Pattern 2: "50 units at 123 Street Name"
            match2 = re.search(r'(\d+)\s*(?:units?|apt|dwelling).*?(?:at|@)\s+(\d+\s+[A-Za-z][A-Za-z\s]+)', line, re.I)

            # Pattern 3: "123 Street Name (50 units)"
            match3 = re.search(r'(\d+\s+[A-Za-z][A-Za-z\s]+)\s*\((\d+)\s*(?:units?|apt|dwelling)?\)', line, re.I)

            # Pattern 4: Just an address with unit count somewhere
            match4 = re.search(r'(\d+\s+(?:N\.?|S\.?|E\.?|W\.?)?\s*[A-Za-z][A-Za-z\s]+(?:Street|Avenue|Way|Boulevard|Road|Drive|Lane|Court|Place|St|Ave|Blvd|Rd|Dr|Ln|Ct|Pl))', line, re.I)
            unit_match = re.search(r'(\d+)\s*(?:units?|homes?|apt|dwelling|residences?)', line, re.I)

            address = None
            units = None

            if match1:
                address = match1.group(1).strip()
                units = int(match1.group(2))
            elif match2:
                units = int(match2.group(1))
                address = match2.group(2).strip()
            elif match3:
                address = match3.group(1).strip()
                units = int(match3.group(2))
            elif match4 and unit_match:
                address = match4.group(1).strip()
                units = int(unit_match.group(1))

            if address:
                # Clean up address
                address = re.sub(r'\s+', ' ', address)
                address = address.title()

                project = DiscoveredProject(
                    address=address,
                    units=units,
                    source='SFYimby',
                    source_date=current_date,
                    description=line[:200] if len(line) > 50 else None,
                    developer=None,
                    permit_hint=None,
                    url=current_url
                )
                projects.append(project)

    return projects


def parse_corridor_scan(filepath: str) -> List[DiscoveredProject]:
    """
    Parse a corridor scan file (manual observations).

    Expected format:
    ADDRESS | UNITS | NOTES
    or simple list of addresses
    """
    projects = []

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Try pipe-delimited format
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                address = parts[0] if parts else None
                units = None
                description = None

                if len(parts) > 1:
                    try:
                        units = int(parts[1])
                    except:
                        description = parts[1]

                if len(parts) > 2:
                    description = parts[2]
            else:
                # Simple address line
                address = line
                units = None
                description = None

                # Try to extract units
                unit_match = re.search(r'(\d+)\s*(?:units?|apt)', line, re.I)
                if unit_match:
                    units = int(unit_match.group(1))
                    address = re.sub(r'\s*-?\s*\d+\s*(?:units?|apt).*$', '', line, flags=re.I)

            if address:
                project = DiscoveredProject(
                    address=address.strip(),
                    units=units,
                    source='Corridor Scan',
                    source_date=datetime.now().strftime('%Y-%m-%d'),
                    description=description,
                    developer=None,
                    permit_hint=None,
                    url=None
                )
                projects.append(project)

    return projects


def compare_with_database(discovered: List[DiscoveredProject], existing: dict) -> List[DiscoveredProject]:
    """Compare discovered projects with existing database."""
    for project in discovered:
        key = extract_street_key(project.address)

        if key in existing:
            project.in_database = True
            project.matched_id = existing[key]['id']
        else:
            # Try fuzzy match
            norm_addr = normalize_address(project.address)
            for db_key, db_proj in existing.items():
                db_norm = normalize_address(db_proj['address'])
                # Check if street numbers match and first few chars of street name
                norm_parts = norm_addr.split()
                db_parts = db_norm.split()
                if norm_parts and db_parts:
                    if norm_parts[0] == db_parts[0]:  # Same street number
                        if len(norm_parts) > 1 and len(db_parts) > 1:
                            if norm_parts[1][:3] == db_parts[1][:3]:  # Similar street name
                                project.in_database = True
                                project.matched_id = db_proj['id']
                                break

    return discovered


def main():
    parser = argparse.ArgumentParser(description='Discover new housing projects')
    parser.add_argument('scan_file', nargs='?', help='Path to scan file to process')
    parser.add_argument('--scan-file', dest='scan_file_arg', help='Path to scan file')
    parser.add_argument('--compare-only', action='store_true', help='Only compare existing discovered files')
    parser.add_argument('--output', '-o', help='Output CSV path')
    parser.add_argument('--show-all', action='store_true', help='Show all projects including matches')

    args = parser.parse_args()

    # Paths
    final_csv = Path('data/processed/housing_projects_FINAL.csv')
    scan_dir = Path('data/raw/corridor_scans')
    output_csv = Path(args.output) if args.output else Path('data/processed/new_projects_discovered.csv')

    # Load existing projects
    print("Loading existing projects from FINAL.csv...")
    existing = load_existing_projects(str(final_csv))
    print(f"  Found {len(existing)} existing projects")

    # Determine input file
    scan_file = args.scan_file or args.scan_file_arg

    all_discovered = []

    if scan_file:
        # Process single file
        filepath = Path(scan_file)
        if not filepath.exists():
            print(f"Error: File not found: {scan_file}")
            sys.exit(1)

        print(f"\nProcessing: {filepath}")

        if 'sfyimby' in filepath.name.lower():
            projects = parse_sfyimby_scan(str(filepath))
        else:
            projects = parse_corridor_scan(str(filepath))

        all_discovered.extend(projects)

    elif args.compare_only:
        # Process all files in scan directory
        if scan_dir.exists():
            for scan_file in scan_dir.glob('*.txt'):
                print(f"\nProcessing: {scan_file.name}")
                if 'sfyimby' in scan_file.name.lower():
                    projects = parse_sfyimby_scan(str(scan_file))
                else:
                    projects = parse_corridor_scan(str(scan_file))
                all_discovered.extend(projects)

    else:
        print("Usage: python discover_new_projects.py SCAN_FILE")
        print("   or: python discover_new_projects.py --compare-only")
        sys.exit(1)

    # Compare with database
    print(f"\nComparing {len(all_discovered)} discovered projects with database...")
    all_discovered = compare_with_database(all_discovered, existing)

    # Report results
    new_projects = [p for p in all_discovered if not p.in_database]
    matched_projects = [p for p in all_discovered if p.in_database]

    print("\n" + "="*70)
    print("DISCOVERY RESULTS")
    print("="*70)

    print(f"\nTotal discovered: {len(all_discovered)}")
    print(f"Already in database: {len(matched_projects)}")
    print(f"NEW (not in database): {len(new_projects)}")

    if new_projects:
        print("\n" + "-"*70)
        print("NEW PROJECTS NOT IN DATABASE:")
        print("-"*70)

        # Sort by units descending
        new_projects.sort(key=lambda x: x.units or 0, reverse=True)

        for p in new_projects:
            units_str = f"{p.units} units" if p.units else "? units"
            print(f"\n  {p.address}")
            print(f"    Units: {units_str}")
            print(f"    Source: {p.source}")
            if p.source_date:
                print(f"    Date: {p.source_date}")
            if p.url:
                print(f"    URL: {p.url}")

    if args.show_all and matched_projects:
        print("\n" + "-"*70)
        print("ALREADY IN DATABASE:")
        print("-"*70)

        for p in matched_projects:
            print(f"  {p.address} -> Project ID {p.matched_id}")

    # Write output CSV
    if new_projects:
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        with open(output_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['address', 'units', 'source', 'source_date', 'description', 'url', 'action_needed'])

            for p in new_projects:
                action = "Add to FINAL.csv, search Accela for permits"
                writer.writerow([
                    p.address,
                    p.units or '',
                    p.source,
                    p.source_date or '',
                    p.description or '',
                    p.url or '',
                    action
                ])

        print(f"\n\nNew projects written to: {output_csv}")

    return 0 if not new_projects else 1


if __name__ == '__main__':
    sys.exit(main())
