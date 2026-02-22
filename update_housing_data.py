#!/usr/bin/env python3
"""
Berkeley Housing Data Update Script
====================================
Updates the housing projects database with new permit data from City of Berkeley.

Usage:
    python update_housing_data.py /path/to/new_permits.xlsx

Or import and use programmatically:
    from update_housing_data import update_housing_database
    update_housing_database('/path/to/new_permits.xlsx')
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import sys
import re
from pathlib import Path
from datetime import datetime

# Find project root
def find_project_root():
    current = Path(__file__).parent
    for path in [current] + list(current.parents):
        if (path / '00_config').exists() and (path / 'modules').exists():
            return path
    return current

ROOT = find_project_root()

# Paths
EXISTING_DATA = ROOT / 'data/processed/housing_projects_FINAL.csv'
LOOKUP_TABLE = ROOT / 'data/reference/alameda_lookup_complete.csv'
DATABASE_PATH = ROOT / 'databases/berkeley_housing_analysis.db'
BACKUP_DIR = ROOT / 'data/backups'

# Housing keywords to filter permits
HOUSING_KEYWORDS = [
    'dwelling', 'unit', 'units', 'residential', 'housing', 'apartment',
    'ADU', 'SB330', 'SB 330', 'AB2011', 'AB 2011', 'multi-family',
    'multifamily', 'duplex', 'triplex', 'fourplex', 'mixed-use',
    'density bonus', 'affordable'
]

def load_existing_data():
    """Load existing housing projects database."""
    print(f"\n📂 Loading existing data from {EXISTING_DATA}")
    df = pd.read_csv(EXISTING_DATA)
    print(f"   Found {len(df)} existing projects")

    # Extract all permit numbers (handle comma-separated)
    existing_permits = set()
    for permits in df['permits'].dropna():
        for p in str(permits).split(','):
            existing_permits.add(p.strip())
    print(f"   Tracking {len(existing_permits)} permit numbers")

    return df, existing_permits

def load_new_permits(excel_path):
    """Load new permits from Excel file."""
    print(f"\n📂 Loading new permits from {excel_path}")

    # Read Excel, skip header rows
    df = pd.read_excel(excel_path, header=None, skiprows=2)
    df.columns = ['Permit Number', 'Description', 'Address', 'Record Status']

    # Remove any header rows that got included
    df = df[df['Permit Number'] != 'Permit Number']
    df = df.dropna(subset=['Permit Number'])

    print(f"   Found {len(df)} total permits")
    return df

def filter_housing_permits(df):
    """Filter for housing-related permits."""
    print(f"\n🏠 Filtering for housing-related permits...")

    pattern = '|'.join(HOUSING_KEYWORDS)
    mask = df['Description'].str.contains(pattern, case=False, na=False)
    housing_df = df[mask].copy()

    print(f"   Found {len(housing_df)} housing-related permits")
    return housing_df

def find_new_permits(housing_df, existing_permits):
    """Identify permits not already in database."""
    print(f"\n🔍 Identifying new permits...")

    housing_df['is_new'] = ~housing_df['Permit Number'].isin(existing_permits)
    new_permits = housing_df[housing_df['is_new']].copy()

    print(f"   Already tracked: {len(housing_df) - len(new_permits)}")
    print(f"   NEW permits: {len(new_permits)}")

    return new_permits

def load_geocoding_lookup():
    """Load the Alameda County address lookup table."""
    print(f"\n📍 Loading geocoding lookup table...")
    lookup = pd.read_csv(LOOKUP_TABLE, low_memory=False)
    print(f"   Loaded {len(lookup):,} addresses")
    return lookup

def normalize_address(addr):
    """Normalize address for matching."""
    if pd.isna(addr):
        return ''

    addr = str(addr).upper().strip()

    # Standardize street types
    replacements = {
        ' AVENUE': ' AV',
        ' AVE': ' AV',
        ' STREET': ' ST',
        ' ROAD': ' RD',
        ' BOULEVARD': ' BLVD',
        ' DRIVE': ' DR',
        ' COURT': ' CT',
        ' PLACE': ' PL',
        ' LANE': ' LN',
        ' CIRCLE': ' CIR',
        ' TERRACE': ' TER',
    }

    for old, new in replacements.items():
        addr = addr.replace(old, new)

    # Remove unit/apt designations
    addr = re.sub(r'\s+(APT|UNIT|#|STE)\s*\w*$', '', addr)

    return addr

def geocode_addresses(new_permits, lookup):
    """Geocode new addresses using lookup table."""
    print(f"\n📍 Geocoding {len(new_permits)} addresses...")

    # Normalize addresses
    new_permits['address_norm'] = new_permits['Address'].apply(normalize_address)

    # Create normalized lookup
    lookup['lookup_norm'] = lookup['normalized_address'].apply(normalize_address)

    # Create lookup dictionary (use first match for each normalized address)
    lookup_dedup = lookup.drop_duplicates(subset='lookup_norm')
    geo_dict = lookup_dedup.set_index('lookup_norm')[['latitude', 'longitude']].to_dict('index')

    # Match addresses
    matched = 0
    unmatched = []

    for idx, row in new_permits.iterrows():
        addr_norm = row['address_norm']

        if addr_norm in geo_dict:
            new_permits.loc[idx, 'latitude'] = geo_dict[addr_norm]['latitude']
            new_permits.loc[idx, 'longitude'] = geo_dict[addr_norm]['longitude']
            matched += 1
        else:
            # Try fuzzy matching - extract street number and name
            parts = addr_norm.split()
            if len(parts) >= 2:
                street_num = parts[0]
                street_name = parts[1]

                # Find addresses with same number and partial street name match
                for lookup_addr, coords in geo_dict.items():
                    if lookup_addr.startswith(street_num + ' ') and street_name[:4] in lookup_addr:
                        new_permits.loc[idx, 'latitude'] = coords['latitude']
                        new_permits.loc[idx, 'longitude'] = coords['longitude']
                        matched += 1
                        break
                else:
                    unmatched.append(row['Address'])
            else:
                unmatched.append(row['Address'])

    print(f"   ✅ Geocoded: {matched}")
    print(f"   ❌ Unmatched: {len(unmatched)}")

    if unmatched:
        print(f"\n   Addresses needing manual geocoding:")
        for addr in unmatched:
            print(f"      - {addr}")

    return new_permits

def extract_unit_count(description):
    """Extract unit count from project description."""
    if pd.isna(description):
        return None

    desc = str(description).lower()

    # Common patterns - order matters, more specific first
    patterns = [
        r'(\d+)-unit\s+housing',           # "45-unit housing"
        r'(\d+)\s*-\s*unit',                # "45-unit" or "45 - unit"
        r'(\d+)\s+units?\b',                # "45 units" or "68 units"
        r'(\d+)\s+dwelling\s+units?',       # "257 dwelling units"
        r'total\s+(?:of\s+)?(\d+)\s+units?',# "total of 45 units"
        r'(\d+)\s+(?:new\s+)?(?:residential\s+)?(?:dwelling|apartment|home)s?',
        r'unit\s+count\s+(?:from\s+\d+\s+)?to\s+(\d+)',  # "unit count from 66 to 73"
        r'increase.*?to\s+(\d+)\s+units?',  # "increase...to 73 units"
    ]

    for pattern in patterns:
        match = re.search(pattern, desc)
        if match:
            count = int(match.group(1))
            if count > 0 and count < 2000:  # Sanity check
                return count

    # Check for ADU/garage conversion (usually 1 unit)
    if 'adu' in desc or 'accessory dwelling' in desc or 'garage conversion' in desc:
        return 1

    # Check for single-family modifications (usually 0 net new)
    if ('single-family' in desc or 'single family' in desc) and ('addition' in desc or 'remodel' in desc):
        return 0

    # Residential additions without unit mentions are usually 0 net new
    if 'residential addition' in desc and 'unit' not in desc:
        return 0

    return None

def extract_year(permit_number):
    """Extract year from permit number."""
    match = re.search(r'(20\d{2})', str(permit_number))
    if match:
        return int(match.group(1))
    return datetime.now().year

def categorize_project_size(units):
    """Categorize project by size."""
    if pd.isna(units) or units == 0:
        return 'Unknown'
    elif units <= 5:
        return 'Small (1-5)'
    elif units <= 20:
        return 'Medium (6-20)'
    elif units <= 50:
        return 'Large (21-50)'
    elif units <= 100:
        return 'Very Large (51-100)'
    else:
        return 'Mega (100+)'

def create_slug(address):
    """Create URL-friendly slug from address."""
    if pd.isna(address):
        return ''
    slug = str(address).lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug

def prepare_new_records(new_permits, next_id):
    """Prepare new records in the format of existing database."""
    print(f"\n📝 Preparing {len(new_permits)} new records...")

    records = []
    for idx, row in new_permits.iterrows():
        units = extract_unit_count(row['Description'])
        year = extract_year(row['Permit Number'])

        record = {
            'id': next_id,
            'address_display': row['Address'],
            'apn': None,
            'owner': None,
            'net_units': units if units else 0,
            'new_units': units if units else 0,
            'old_units': 0,
            'year': year,
            'permits': row['Permit Number'],
            'description': row['Description'],
            'status': row['Record Status'],
            'num_permits': 1,
            'project_size_category': categorize_project_size(units),
            'slug': create_slug(row['Address']),
            'address_norm': row['address_norm'],
            'latitude': row.get('latitude'),
            'longitude': row.get('longitude'),
        }
        records.append(record)
        next_id += 1

    return pd.DataFrame(records)

def update_existing_statuses(existing_df, all_permits_df):
    """Update status of existing projects from new data."""
    print(f"\n🔄 Updating statuses of existing projects...")

    # Create status lookup from new data
    status_lookup = dict(zip(all_permits_df['Permit Number'], all_permits_df['Record Status']))

    updated_count = 0
    for idx, row in existing_df.iterrows():
        permits = str(row['permits']).split(',')
        for permit in permits:
            permit = permit.strip()
            if permit in status_lookup:
                new_status = status_lookup[permit]
                if row['status'] != new_status:
                    existing_df.loc[idx, 'status'] = new_status
                    updated_count += 1
                    break

    print(f"   Updated {updated_count} project statuses")
    return existing_df

def backup_existing_data():
    """Create backup of existing data."""
    print(f"\n💾 Creating backup...")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    backup_path = BACKUP_DIR / f'housing_projects_FINAL_{timestamp}.csv'

    if EXISTING_DATA.exists():
        import shutil
        shutil.copy(EXISTING_DATA, backup_path)
        print(f"   Backup saved to: {backup_path}")

    return backup_path

def save_updated_data(merged_df):
    """Save updated data to CSV and database."""
    print(f"\n💾 Saving updated data...")

    # Save CSV
    merged_df.to_csv(EXISTING_DATA, index=False)
    print(f"   ✅ CSV saved: {EXISTING_DATA}")

    # Update SQLite database
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)

    merged_df.to_sql('projects', conn, if_exists='replace', index=False)

    # Create indexes
    cursor = conn.cursor()
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_year ON projects(year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_units ON projects(net_units)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coords ON projects(latitude, longitude)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON projects(status)')
    conn.commit()
    conn.close()

    print(f"   ✅ Database updated: {DATABASE_PATH}")

def print_summary(existing_count, new_count, merged_df):
    """Print summary of updates."""
    print(f"\n" + "="*70)
    print(f"📊 UPDATE SUMMARY")
    print(f"="*70)
    print(f"   Previous projects: {existing_count}")
    print(f"   New projects added: {new_count}")
    print(f"   Total projects now: {len(merged_df)}")
    print(f"   Total units: {merged_df['net_units'].sum():,.0f}")

    print(f"\n   Projects by status:")
    status_counts = merged_df['status'].value_counts()
    for status, count in status_counts.items():
        print(f"      {status}: {count}")

    print(f"\n   Projects by year:")
    year_counts = merged_df.groupby('year')['net_units'].agg(['count', 'sum'])
    for year, row in year_counts.iterrows():
        print(f"      {int(year)}: {int(row['count'])} projects, {int(row['sum'])} units")

    geocoded = merged_df['latitude'].notna().sum()
    print(f"\n   Geocoding: {geocoded}/{len(merged_df)} ({geocoded/len(merged_df)*100:.1f}%)")

    print(f"\n" + "="*70)

def update_housing_database(excel_path, dry_run=False):
    """
    Main function to update housing database with new permit data.

    Args:
        excel_path: Path to Excel file with new permit data
        dry_run: If True, show what would be done without saving
    """
    print(f"\n{'='*70}")
    print(f"🏗️  BERKELEY HOUSING DATA UPDATE")
    print(f"{'='*70}")
    print(f"   Input file: {excel_path}")
    print(f"   Dry run: {dry_run}")

    # Load data
    existing_df, existing_permits = load_existing_data()
    new_df = load_new_permits(excel_path)

    # Filter and find new permits
    housing_df = filter_housing_permits(new_df)
    new_permits = find_new_permits(housing_df, existing_permits)

    if len(new_permits) == 0:
        print(f"\n✅ No new housing permits to add. Database is up to date.")
        return existing_df

    # Geocode new addresses
    lookup = load_geocoding_lookup()
    new_permits = geocode_addresses(new_permits, lookup)

    # Prepare new records
    next_id = existing_df['id'].max() + 1
    new_records = prepare_new_records(new_permits, next_id)

    # Update existing statuses
    existing_df = update_existing_statuses(existing_df, new_df)

    # Merge data
    merged_df = pd.concat([existing_df, new_records], ignore_index=True)

    # Print summary
    print_summary(len(existing_df), len(new_records), merged_df)

    if dry_run:
        print(f"\n🔍 DRY RUN - No changes saved")
        print(f"\n   New records that would be added:")
        print(new_records[['address_display', 'permits', 'net_units', 'status']].to_string())
    else:
        # Backup and save
        backup_existing_data()
        save_updated_data(merged_df)
        print(f"\n✅ Update complete!")

    return merged_df

def main():
    """Command-line interface."""
    if len(sys.argv) < 2:
        print(__doc__)
        print(f"\nError: Please provide path to Excel file")
        print(f"Usage: python {sys.argv[0]} /path/to/permits.xlsx [--dry-run]")
        sys.exit(1)

    excel_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    if not os.path.exists(excel_path):
        print(f"Error: File not found: {excel_path}")
        sys.exit(1)

    update_housing_database(excel_path, dry_run=dry_run)

if __name__ == '__main__':
    main()
