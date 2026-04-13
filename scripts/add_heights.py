#!/usr/bin/env python3
"""
Add heights to projects missing height_stories using three methods:
1. Parse descriptions for patterns like "X-story", "X story", etc.
2. Parse scraped text files in data/raw/accela_status/
3. Estimate from units for remaining projects
"""

import sqlite3
import re
import os
from pathlib import Path
from collections import defaultdict

DB_PATH = Path('/Users/johngage/berkeley-data/databases/berkeley_housing_analysis.db')
ACCELA_DIR = Path('/Users/johngage/berkeley-data/data/raw/accela_status')

# Height extraction pattern - matches "X-story", "X story", "X stories", "X floors", "X-Story"
HEIGHT_PATTERN = re.compile(r'\b(\d{1,2})[\s-]?(?:stor(?:y|ies)|floor(?:s)?)\b', re.IGNORECASE)

def extract_height_from_text(text):
    """Extract height from text using regex pattern"""
    if not text:
        return None
    matches = HEIGHT_PATTERN.findall(text)
    if matches:
        # Return the largest match (most likely the building height)
        return max(int(m) for m in matches)
    return None

def estimate_height_from_units(units):
    """Estimate building height based on unit count"""
    if units is None or units <= 0:
        return 3
    elif units <= 4:
        return 3
    elif units <= 19:
        return 4
    elif units <= 49:
        return 5
    elif units <= 99:
        return 7
    elif units <= 199:
        return 10
    elif units <= 399:
        return 15
    else:
        return 20

def normalize_address(addr):
    """Normalize address for matching"""
    if not addr:
        return ""
    # Convert to uppercase, remove extra spaces
    addr = addr.upper().strip()
    # Remove common suffixes
    addr = re.sub(r'\b(AVE|AVENUE|ST|STREET|WAY|BLVD|BOULEVARD|DR|DRIVE|CT|COURT|PL|PLACE)\b', '', addr)
    # Remove non-alphanumeric except spaces
    addr = re.sub(r'[^A-Z0-9\s]', '', addr)
    # Collapse whitespace
    addr = re.sub(r'\s+', ' ', addr).strip()
    return addr

def parse_accela_files():
    """Parse all Accela text files and extract heights by address"""
    heights_from_files = {}

    if not ACCELA_DIR.exists():
        print(f"  ⚠️ Directory not found: {ACCELA_DIR}")
        return heights_from_files

    # Walk through all subdirectories
    for root, dirs, files in os.walk(ACCELA_DIR):
        for filename in files:
            if not filename.endswith('.txt'):
                continue

            filepath = Path(root) / filename
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Extract height from content
                height = extract_height_from_text(content)
                if height:
                    # Try to extract address from filename
                    # Patterns: B_2128_Oxford_St.txt, FULL_1698_UNIVERSITY.txt, etc.
                    name = filename.replace('.txt', '')
                    # Remove prefixes
                    name = re.sub(r'^(B_|FULL_|ZP\d+-\d+_)', '', name)
                    # Convert underscores to spaces
                    addr_from_file = name.replace('_', ' ')
                    normalized = normalize_address(addr_from_file)

                    if normalized and len(normalized) > 3:
                        heights_from_files[normalized] = height

            except Exception as e:
                print(f"  ⚠️ Error reading {filepath}: {e}")

    return heights_from_files

def main():
    print("=" * 60)
    print("ADD HEIGHTS TO PROJECTS")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get projects missing height_stories
    cursor.execute('''
        SELECT id, address_display, description, units, height_stories
        FROM projects
        WHERE height_stories IS NULL OR height_stories = 0
    ''')
    missing = cursor.fetchall()
    print(f"\nProjects missing height_stories: {len(missing)}")

    # Track results by method
    results = {
        'description': [],
        'accela_files': [],
        'estimated': []
    }

    # Method 1: Parse descriptions
    print("\n--- Method 1: Parse descriptions ---")
    description_heights = {}
    for project_id, address, description, units, current_height in missing:
        height = extract_height_from_text(description)
        if height:
            description_heights[project_id] = (address, height)

    print(f"  Found heights in descriptions: {len(description_heights)}")
    for project_id, (address, height) in description_heights.items():
        print(f"    {address}: {height} stories")
        cursor.execute('UPDATE projects SET height_stories = ? WHERE id = ?', (height, project_id))
        results['description'].append((address, height))

    # Method 2: Parse Accela files
    print("\n--- Method 2: Parse Accela files ---")
    file_heights = parse_accela_files()
    print(f"  Heights extracted from files: {len(file_heights)}")

    # Get remaining projects missing heights
    cursor.execute('''
        SELECT id, address_display, units
        FROM projects
        WHERE height_stories IS NULL OR height_stories = 0
    ''')
    still_missing = cursor.fetchall()

    matched_from_files = 0
    for project_id, address, units in still_missing:
        normalized_addr = normalize_address(address)
        # Check for matches in file heights
        for file_addr, height in file_heights.items():
            # Check if file address is contained in project address or vice versa
            if file_addr in normalized_addr or normalized_addr in file_addr:
                print(f"    {address}: {height} stories (from file)")
                cursor.execute('UPDATE projects SET height_stories = ? WHERE id = ?', (height, project_id))
                results['accela_files'].append((address, height))
                matched_from_files += 1
                break

    print(f"  Matched from Accela files: {matched_from_files}")

    # Method 3: Estimate from units
    print("\n--- Method 3: Estimate from units ---")
    cursor.execute('''
        SELECT id, address_display, units
        FROM projects
        WHERE height_stories IS NULL OR height_stories = 0
    ''')
    final_missing = cursor.fetchall()
    print(f"  Projects still missing heights: {len(final_missing)}")

    for project_id, address, units in final_missing:
        height = estimate_height_from_units(units)
        print(f"    {address} ({units} units): estimated {height} stories")
        cursor.execute('''
            UPDATE projects
            SET height_stories = ?, construction_data_reliability = 'estimated_height'
            WHERE id = ?
        ''', (height, project_id))
        results['estimated'].append((address, height, units))

    # Additional UC project height_feet updates
    print("\n--- UC Project height_feet updates ---")
    cursor.execute("UPDATE projects SET height_feet = 253 WHERE address_display = '2200 BANCROFT Way'")
    print(f"  2200 BANCROFT Way: height_feet = 253")
    cursor.execute("UPDATE projects SET height_feet = 154 WHERE address_display = '1950 OXFORD St'")
    print(f"  1950 OXFORD St: height_feet = 154")

    conn.commit()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Heights from descriptions: {len(results['description'])}")
    print(f"  Heights from Accela files: {len(results['accela_files'])}")
    print(f"  Heights estimated from units: {len(results['estimated'])}")
    print(f"  Total heights added: {len(results['description']) + len(results['accela_files']) + len(results['estimated'])}")

    # Verify
    cursor.execute('SELECT COUNT(*) FROM projects WHERE height_stories IS NULL OR height_stories = 0')
    remaining = cursor.fetchone()[0]
    print(f"\n  Projects still missing heights: {remaining}")

    cursor.execute('SELECT COUNT(*) FROM projects WHERE construction_data_reliability = "estimated_height"')
    estimated = cursor.fetchone()[0]
    print(f"  Projects marked as estimated_height: {estimated}")

    conn.close()
    print("\n✓ Height updates complete")

if __name__ == '__main__':
    main()
