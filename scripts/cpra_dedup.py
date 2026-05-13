#!/usr/bin/env python3
"""
CPRA Permit Deduplication Script

Deduplicates CPRA (California Public Records Act) permit data by grouping
sub-permits with their master permits. Each master permit generates multiple
sub-permits (revisions -REV, deferred submittals -DEF) that carry duplicated
unit counts.

Usage:
    from cpra_dedup import dedupe_permits, load_cpra

    cpra = load_cpra('/path/to/BP_Annual Permit Report.xlsx')
    deduped = dedupe_permits(cpra, output_path='/path/to/output.csv')

Or from command line:
    python cpra_dedup.py input.xlsx output.csv
"""

import pandas as pd
import re
import sys
from pathlib import Path


def normalize_apn(apn):
    """Remove all non-digit characters from APN for consistent matching."""
    if pd.isna(apn):
        return ""
    return re.sub(r'[^\d]', '', str(apn))


def extract_master_permit(permit_number):
    """
    Extract master permit number by removing -REV, -DEF, -ADD suffixes.

    Examples:
        B2024-01924-REV05 -> B2024-01924
        B2024-01924-DEF01 -> B2024-01924
        B2024-01924 -> B2024-01924
    """
    match = re.match(r'^([A-Z]\d{4}-\d{5})(?:-[A-Z]+\d*)?$', str(permit_number))
    if match:
        return match.group(1)
    return permit_number


def is_sub_permit(permit_number):
    """Check if permit is a sub-permit (has -REV, -DEF, -ADD suffix)."""
    return bool(re.search(r'-(?:REV|DEF|ADD)\d*$', str(permit_number)))


def load_cpra(input_path):
    """
    Load CPRA Excel file and add derived columns.

    Args:
        input_path: Path to CPRA Excel file (header at row 8, data starts row 9)

    Returns:
        DataFrame with cleaned data and derived columns:
        - norm_apn: Normalized APN (digits only)
        - master_permit: Master permit number (suffix removed)
        - is_sub_permit: Boolean flag for sub-permits
        - IssueYear: Year extracted from Issuance Date
    """
    df = pd.read_excel(input_path, header=7)

    # Clean and derive columns
    df['PermitNumber'] = df['PermitNumber'].astype(str).str.strip()
    df['UnitsAdded'] = pd.to_numeric(df['UnitsAdded'], errors='coerce').fillna(0)
    df['IssueYear'] = pd.to_datetime(df['Issuance Date'], errors='coerce').dt.year
    df['SubmitDate'] = pd.to_datetime(df['Submittal Date'], errors='coerce')
    df['norm_apn'] = df['Parcel Number'].apply(normalize_apn)
    df['master_permit'] = df['PermitNumber'].apply(extract_master_permit)
    df['is_sub_permit'] = df['PermitNumber'].apply(is_sub_permit)

    return df


def dedupe_permits(df, filter_func=None, output_path=None):
    """
    Deduplicate permits by grouping on (APN, master_permit).

    For each group, uses the master permit's data (the permit without a suffix,
    or the earliest if all have suffixes). Sub-permit unit counts are ignored.

    Args:
        df: DataFrame from load_cpra()
        filter_func: Optional function(df) -> boolean Series to filter rows
        output_path: Optional path to save CSV output

    Returns:
        DataFrame with one row per project containing:
        - apn, master_permit, permit_count, units_added
        - issue_year, issue_date, work_type, sub_type, occ_type
        - description, address, adu_flag, detached

    Example filter_func for R-2 permits with units:
        lambda df: (df['OccType'].str.contains('R-2', na=False) &
                    (df['UnitsAdded'] > 0) &
                    df['IssueYear'].isin([2023, 2024, 2025]))
    """
    work_df = df.copy()

    if filter_func is not None:
        work_df = work_df[filter_func(work_df)].copy()

    # Group by APN and master permit
    groups = work_df.groupby(['norm_apn', 'master_permit'])

    results = []
    for (apn, master), group in groups:
        # Find the master permit row (no suffix, or earliest if all have suffixes)
        master_rows = group[~group['is_sub_permit']]
        if len(master_rows) > 0:
            main_row = master_rows.iloc[0]
        else:
            # All are sub-permits - use earliest by submit date
            main_row = group.sort_values('SubmitDate').iloc[0]

        # Build address string
        addr_parts = []
        if pd.notna(main_row.get('StreetNumber')):
            addr_parts.append(str(main_row['StreetNumber']).strip())
        if pd.notna(main_row.get('StreetName')):
            addr_parts.append(str(main_row['StreetName']).strip())
        if pd.notna(main_row.get('StreetType')):
            addr_parts.append(str(main_row['StreetType']).strip())

        results.append({
            'apn': apn,
            'master_permit': master,
            'permit_count': len(group),
            'units_added': main_row['UnitsAdded'],
            'issue_year': main_row['IssueYear'],
            'issue_date': main_row.get('Issuance Date'),
            'finaled_date': main_row.get('Finaled Date'),
            'submit_date': main_row.get('SubmitDate'),
            'work_type': main_row.get('Work Type'),
            'sub_type': main_row.get('SubType'),
            'occ_type': main_row.get('OccType'),
            'description': main_row.get('WorkDescription'),
            'address': ' '.join(addr_parts),
            'adu_flag': main_row.get('ADU'),
            'detached': main_row.get('Detached'),
            'job_valuation': main_row.get('JobValuation')
        })

    result_df = pd.DataFrame(results)

    if output_path:
        result_df.to_csv(output_path, index=False)
        print(f"Saved {len(result_df)} deduplicated records to {output_path}")

    return result_df


def dedupe_r2_permits(df, years=None):
    """
    Convenience function to deduplicate R-2 (multi-unit) permits with units.

    Args:
        df: DataFrame from load_cpra()
        years: List of years to include (default: [2023, 2024, 2025])

    Returns:
        Deduplicated DataFrame of R-2 projects
    """
    if years is None:
        years = [2023, 2024, 2025]

    filter_func = lambda d: (
        d['OccType'].str.contains('R-2', na=False, case=False) &
        (d['UnitsAdded'] > 0) &
        d['IssueYear'].isin(years)
    )

    return dedupe_permits(df, filter_func)


def dedupe_adu_permits(df, years=None, construction_only=True):
    """
    Convenience function to deduplicate ADU permits.

    Args:
        df: DataFrame from load_cpra()
        years: List of years to include (default: [2023, 2024, 2025])
        construction_only: If True, filter to likely construction permits

    Returns:
        Deduplicated DataFrame of ADU projects
    """
    if years is None:
        years = [2023, 2024, 2025]

    def is_adu(row):
        adu_col = str(row.get('ADU', '')).upper().strip() in ['YES', 'Y', 'TRUE', '1']
        desc = str(row.get('WorkDescription', '')).upper()
        desc_match = any(kw in desc for kw in ['ADU', 'JADU', 'ACCESSORY DWELLING'])
        return adu_col or desc_match

    def is_construction(desc):
        if pd.isna(desc):
            return True  # Include if no description
        desc_upper = str(desc).upper()
        constr = ['NEW ADU', 'NEW DETACHED', 'NEW ATTACHED', 'CONSTRUCT',
                  'BUILD', 'CONVERT', 'CONVERSION', 'LEGALIZE', 'ADDITION',
                  'ACCESSORY DWELLING UNIT', 'NEW JUNIOR', 'NEW JADU',
                  'GARAGE TO ADU', 'BASEMENT ADU', 'SQ FT ADU', 'SF ADU']
        mep = ['ELECTRICAL', 'PANEL UPGRADE', 'SERVICE UPGRADE', 'PLUMBING',
               'WATER HEATER', 'FURNACE', 'HVAC', 'MINI-SPLIT', 'SOLAR', 'EV CHARGER']

        has_constr = any(kw in desc_upper for kw in constr)
        is_mep_only = any(kw in desc_upper for kw in mep) and not has_constr
        return has_constr or not is_mep_only

    # Apply ADU filter
    adu_mask = df.apply(is_adu, axis=1)
    year_mask = df['IssueYear'].isin(years)

    if construction_only:
        constr_mask = df['WorkDescription'].apply(is_construction)
        filter_func = lambda d: adu_mask & year_mask & constr_mask & ~d['is_sub_permit']
    else:
        filter_func = lambda d: adu_mask & year_mask

    return dedupe_permits(df, filter_func)


def main():
    """Command-line interface."""
    if len(sys.argv) < 2:
        print("Usage: python cpra_dedup.py <input.xlsx> [output.csv]")
        print()
        print("Deduplicates CPRA permit data by grouping sub-permits with masters.")
        print("If output.csv is not specified, prints summary statistics.")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Loading {input_path}...")
    df = load_cpra(input_path)
    print(f"Loaded {len(df)} permits")
    print(f"  Sub-permits: {df['is_sub_permit'].sum()}")
    print(f"  Master/standalone: {(~df['is_sub_permit']).sum()}")
    print()

    if output_path:
        # Full deduplication
        deduped = dedupe_permits(df, output_path=output_path)
    else:
        # Summary statistics
        print("=== R-2 Multi-Unit Projects (2023-2025) ===")
        r2 = dedupe_r2_permits(df)
        for year in [2023, 2024, 2025]:
            year_data = r2[r2['issue_year'] == year]
            print(f"{year}: {len(year_data)} projects, {int(year_data['units_added'].sum())} units")

        print()
        print("=== ADU Projects (2023-2025) ===")
        adu = dedupe_adu_permits(df)
        for year in [2023, 2024, 2025]:
            year_data = adu[adu['issue_year'] == year]
            print(f"{year}: {len(year_data)} projects, {int(year_data['units_added'].sum())} units")


if __name__ == '__main__':
    main()
