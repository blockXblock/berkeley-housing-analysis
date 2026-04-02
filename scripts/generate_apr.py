#!/usr/bin/env python3
"""
Generate APR (Annual Progress Report) Tables

This script generates HCD Annual Progress Report tables by querying the database.
Tables generated:
- Table A: Projects with applications deemed complete in the reporting year
- Table A2: Permitted projects (entitled, BP issued, CO issued in reporting year)
- Table B: Developer/affordability summary
- Summary statistics

Usage:
    python scripts/generate_apr.py --year 2025
    python scripts/generate_apr.py --year 2024 --output data/apr/
"""

import argparse
import sqlite3
import json
import csv
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path('/Users/johngage/berkeley-data')
DB_PATH = BASE_DIR / 'databases' / 'berkeley_housing_analysis.db'

def generate_table_a(conn, year):
    """
    Table A: Projects with applications deemed complete in the reporting year
    HCD definition: Projects where completeness review finished in the year
    """
    cursor = conn.cursor()

    # Projects with app_complete_date in the reporting year
    cursor.execute('''
        SELECT
            id, address, apn, permits, net_units, vli_units, status,
            app_filed_date, app_complete_date, entitled_date,
            density_bonus, sb35_flag, sb330_flag, ab2011_flag,
            developer, architect
        FROM projects
        WHERE app_complete_date LIKE ?
        ORDER BY app_complete_date
    ''', (f'{year}%',))

    columns = ['id', 'address', 'apn', 'permits', 'net_units', 'vli_units', 'status',
               'app_filed_date', 'app_complete_date', 'entitled_date',
               'density_bonus', 'sb35_flag', 'sb330_flag', 'ab2011_flag',
               'developer', 'architect']

    rows = []
    for row in cursor.fetchall():
        rows.append(dict(zip(columns, row)))

    return {
        "title": f"Table A: Applications Deemed Complete in {year}",
        "description": f"Projects with completeness review finished between {year}-01-01 and {year}-12-31",
        "projects": rows,
        "summary": {
            "total_projects": len(rows),
            "total_units": sum(r['net_units'] or 0 for r in rows),
            "vli_units": sum(r['vli_units'] or 0 for r in rows),
            "density_bonus": sum(1 for r in rows if r['density_bonus']),
            "sb35": sum(1 for r in rows if r['sb35_flag']),
            "sb330": sum(1 for r in rows if r['sb330_flag']),
            "ab2011": sum(1 for r in rows if r['ab2011_flag'])
        }
    }

def generate_table_a2(conn, year):
    """
    Table A2: Permitted Projects
    Projects that achieved permits (entitled, BP issued, or CO issued) in the reporting year
    """
    cursor = conn.cursor()

    # Projects with entitled, bp_issued, or co_date in the reporting year
    cursor.execute('''
        SELECT
            id, address, apn, permits, net_units, vli_units, status,
            app_filed_date, app_complete_date, entitled_date, bp_issued_date, co_date,
            density_bonus, sb35_flag, sb330_flag, ab2011_flag,
            developer, architect, construction_status,
            CASE
                WHEN co_date LIKE ? THEN 'CO Issued'
                WHEN bp_issued_date LIKE ? THEN 'BP Issued'
                WHEN entitled_date LIKE ? THEN 'Entitled'
            END as milestone_achieved
        FROM projects
        WHERE entitled_date LIKE ? OR bp_issued_date LIKE ? OR co_date LIKE ?
        ORDER BY
            CASE
                WHEN co_date LIKE ? THEN 1
                WHEN bp_issued_date LIKE ? THEN 2
                WHEN entitled_date LIKE ? THEN 3
            END,
            net_units DESC
    ''', tuple([f'{year}%'] * 9))

    columns = ['id', 'address', 'apn', 'permits', 'net_units', 'vli_units', 'status',
               'app_filed_date', 'app_complete_date', 'entitled_date', 'bp_issued_date', 'co_date',
               'density_bonus', 'sb35_flag', 'sb330_flag', 'ab2011_flag',
               'developer', 'architect', 'construction_status', 'milestone_achieved']

    rows = []
    for row in cursor.fetchall():
        rows.append(dict(zip(columns, row)))

    # Count by milestone
    entitled_count = sum(1 for r in rows if r['milestone_achieved'] == 'Entitled')
    bp_issued_count = sum(1 for r in rows if r['milestone_achieved'] == 'BP Issued')
    co_issued_count = sum(1 for r in rows if r['milestone_achieved'] == 'CO Issued')

    return {
        "title": f"Table A2: Permitted Projects in {year}",
        "description": f"Projects that achieved entitlement, building permit, or certificate of occupancy in {year}",
        "projects": rows,
        "summary": {
            "total_projects": len(rows),
            "total_units": sum(r['net_units'] or 0 for r in rows),
            "vli_units": sum(r['vli_units'] or 0 for r in rows),
            "entitled_in_year": entitled_count,
            "bp_issued_in_year": bp_issued_count,
            "co_issued_in_year": co_issued_count
        }
    }

def generate_table_b(conn, year):
    """
    Table B: Developer Summary
    Units permitted by developer with affordability breakdown
    """
    cursor = conn.cursor()

    # Developer summary for projects with BP issued or CO in the year
    cursor.execute('''
        SELECT
            COALESCE(developer, 'Unknown/Individual') as developer_name,
            COUNT(*) as project_count,
            SUM(net_units) as total_units,
            SUM(COALESCE(vli_units, 0)) as vli_units,
            SUM(CASE WHEN density_bonus = 1 THEN 1 ELSE 0 END) as density_bonus_projects
        FROM projects
        WHERE bp_issued_date LIKE ? OR co_date LIKE ?
        GROUP BY COALESCE(developer, 'Unknown/Individual')
        ORDER BY total_units DESC
    ''', (f'{year}%', f'{year}%'))

    rows = []
    for row in cursor.fetchall():
        rows.append({
            "developer": row[0],
            "project_count": row[1],
            "total_units": row[2] or 0,
            "vli_units": row[3] or 0,
            "market_rate_units": (row[2] or 0) - (row[3] or 0),
            "density_bonus_projects": row[4] or 0
        })

    return {
        "title": f"Table B: Developer Summary for {year}",
        "description": f"Units permitted by developer for projects with BP issued or CO in {year}",
        "developers": rows,
        "summary": {
            "total_developers": len([r for r in rows if r['developer'] != 'Unknown/Individual']),
            "total_projects": sum(r['project_count'] for r in rows),
            "total_units": sum(r['total_units'] for r in rows),
            "total_vli": sum(r['vli_units'] for r in rows)
        }
    }

def generate_rhna_progress(conn, year):
    """
    RHNA Progress Summary
    Compare progress against RHNA allocation
    """
    cursor = conn.cursor()

    # Berkeley's 6th Cycle RHNA allocation (2023-2031)
    rhna_allocation = {
        "very_low": 2446,
        "low": 1408,
        "moderate": 1416,
        "above_moderate": 3664,
        "total": 8934
    }

    # Count units by affordability level for all years up to reporting year
    cursor.execute('''
        SELECT
            SUM(CASE WHEN bp_issued_date IS NOT NULL OR co_date IS NOT NULL THEN net_units ELSE 0 END) as total_permitted,
            SUM(CASE WHEN bp_issued_date IS NOT NULL OR co_date IS NOT NULL THEN COALESCE(vli_units, 0) ELSE 0 END) as vli_permitted,
            SUM(CASE WHEN co_date IS NOT NULL THEN net_units ELSE 0 END) as total_completed,
            SUM(CASE WHEN co_date IS NOT NULL THEN COALESCE(vli_units, 0) ELSE 0 END) as vli_completed
        FROM projects
        WHERE bp_issued_date <= ? OR co_date <= ?
    ''', (f'{year}-12-31', f'{year}-12-31'))

    row = cursor.fetchone()

    return {
        "title": f"RHNA Progress Through {year}",
        "allocation": rhna_allocation,
        "progress": {
            "total_permitted": row[0] or 0,
            "vli_permitted": row[1] or 0,
            "total_completed": row[2] or 0,
            "vli_completed": row[3] or 0,
            "percent_of_goal": ((row[0] or 0) / rhna_allocation['total'] * 100) if rhna_allocation['total'] > 0 else 0
        }
    }

def generate_adu_summary(year, adu_count=0):
    """
    ADU/JADU Summary with ABAG 30/30/30/10 affordability split
    ABAG methodology assumes:
    - 30% Very Low Income
    - 30% Low Income
    - 30% Moderate Income
    - 10% Above Moderate Income
    """
    # Apply ABAG 30/30/30/10 split
    vli = round(adu_count * 0.30)
    low = round(adu_count * 0.30)
    mod = round(adu_count * 0.30)
    above_mod = adu_count - vli - low - mod  # Remainder

    return {
        "title": f"ADU/JADU Summary for {year}",
        "description": "ADU permits issued with ABAG 30/30/30/10 affordability split",
        "total_adus": adu_count,
        "affordability_split": {
            "very_low_income": vli,
            "low_income": low,
            "moderate_income": mod,
            "above_moderate_income": above_mod
        },
        "methodology": "ABAG 30/30/30/10 affordability assumption for unpermitted ADUs"
    }

def generate_stalled_projects(conn):
    """
    Stalled Projects Analysis
    Projects that haven't progressed in 12+ months
    """
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            id, address, net_units, status, developer,
            app_complete_date, entitled_date, bp_issued_date,
            accela_status_date
        FROM projects
        WHERE is_stalled = 1
        ORDER BY net_units DESC
    ''')

    columns = ['id', 'address', 'net_units', 'status', 'developer',
               'app_complete_date', 'entitled_date', 'bp_issued_date', 'accela_status_date']

    rows = []
    for row in cursor.fetchall():
        rows.append(dict(zip(columns, row)))

    return {
        "title": "Stalled Projects",
        "description": "Projects flagged as stalled (entitled 12+ months without BP, or in review 12+ months)",
        "projects": rows,
        "summary": {
            "total_stalled": len(rows),
            "total_units_at_risk": sum(r['net_units'] or 0 for r in rows)
        }
    }

def write_csv(data, output_path, filename):
    """Write data to CSV file"""
    filepath = output_path / filename
    projects = data.get('projects') or data.get('developers', [])

    if not projects:
        return

    with open(filepath, 'w', newline='') as f:
        if projects:
            writer = csv.DictWriter(f, fieldnames=projects[0].keys())
            writer.writeheader()
            writer.writerows(projects)

    print(f"  Written: {filepath}")

def main():
    parser = argparse.ArgumentParser(description='Generate APR tables')
    parser.add_argument('--year', type=int, required=True, help='Reporting year (e.g., 2025)')
    parser.add_argument('--output', type=str, default='data/apr/', help='Output directory')
    parser.add_argument('--format', choices=['json', 'csv', 'both'], default='both', help='Output format')
    parser.add_argument('--adus', type=int, default=0, help='Number of ADU/JADU permits issued in year')
    args = parser.parse_args()

    year = args.year
    output_path = BASE_DIR / args.output / str(year)
    output_path.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"GENERATE APR TABLES - {year}")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    try:
        # Generate all tables
        print(f"\nGenerating Table A (Applications Deemed Complete in {year})...")
        table_a = generate_table_a(conn, year)
        print(f"  {table_a['summary']['total_projects']} projects, {table_a['summary']['total_units']} units")

        print(f"\nGenerating Table A2 (Permitted Projects in {year})...")
        table_a2 = generate_table_a2(conn, year)
        print(f"  {table_a2['summary']['total_projects']} projects, {table_a2['summary']['total_units']} units")
        print(f"  Entitled: {table_a2['summary']['entitled_in_year']}, BP Issued: {table_a2['summary']['bp_issued_in_year']}, CO Issued: {table_a2['summary']['co_issued_in_year']}")

        print(f"\nGenerating Table B (Developer Summary for {year})...")
        table_b = generate_table_b(conn, year)
        print(f"  {table_b['summary']['total_developers']} developers, {table_b['summary']['total_units']} units")

        print(f"\nGenerating RHNA Progress through {year}...")
        rhna = generate_rhna_progress(conn, year)
        print(f"  {rhna['progress']['total_permitted']} permitted, {rhna['progress']['percent_of_goal']:.1f}% of RHNA goal")

        print("\nGenerating Stalled Projects Report...")
        stalled = generate_stalled_projects(conn)
        print(f"  {stalled['summary']['total_stalled']} stalled, {stalled['summary']['total_units_at_risk']} units at risk")

        print(f"\nGenerating ADU Summary (ABAG 30/30/30/10 split)...")
        adu_summary = generate_adu_summary(year, args.adus)
        if args.adus > 0:
            print(f"  {adu_summary['total_adus']} ADUs: VLI={adu_summary['affordability_split']['very_low_income']}, Low={adu_summary['affordability_split']['low_income']}, Mod={adu_summary['affordability_split']['moderate_income']}, Above={adu_summary['affordability_split']['above_moderate_income']}")
        else:
            print("  No ADU count provided (use --adus N to specify)")

        # Combine all data
        apr_data = {
            "year": year,
            "generated": datetime.now().isoformat(),
            "table_a": table_a,
            "table_a2": table_a2,
            "table_b": table_b,
            "adu_summary": adu_summary,
            "rhna_progress": rhna,
            "stalled_projects": stalled
        }

        # Write outputs
        print(f"\nWriting outputs to {output_path}...")

        if args.format in ['json', 'both']:
            json_path = output_path / f'apr_{year}.json'
            with open(json_path, 'w') as f:
                json.dump(apr_data, f, indent=2)
            print(f"  Written: {json_path}")

        if args.format in ['csv', 'both']:
            write_csv(table_a, output_path, f'table_a_{year}.csv')
            write_csv(table_a2, output_path, f'table_a2_{year}.csv')
            write_csv(table_b, output_path, f'table_b_{year}.csv')
            write_csv(stalled, output_path, f'stalled_{year}.csv')

        # Print summary
        print("\n" + "=" * 60)
        print(f"APR {year} SUMMARY")
        print("=" * 60)
        print(f"\nTable A (Applications Complete): {table_a['summary']['total_projects']} projects, {table_a['summary']['total_units']} units")
        print(f"Table A2 (Permitted): {table_a2['summary']['total_projects']} projects, {table_a2['summary']['total_units']} units")
        print(f"  - Entitled in {year}: {table_a2['summary']['entitled_in_year']}")
        print(f"  - BP Issued in {year}: {table_a2['summary']['bp_issued_in_year']}")
        print(f"  - CO Issued in {year}: {table_a2['summary']['co_issued_in_year']}")
        if adu_summary['total_adus'] > 0:
            print(f"\nADU/JADU Permits: {adu_summary['total_adus']} units (ABAG 30/30/30/10 split)")
            split = adu_summary['affordability_split']
            print(f"  - Very Low: {split['very_low_income']}, Low: {split['low_income']}, Mod: {split['moderate_income']}, Above Mod: {split['above_moderate_income']}")
        print(f"\nTable B (By Developer): {table_b['summary']['total_developers']} known developers")
        print(f"RHNA Progress: {rhna['progress']['percent_of_goal']:.1f}% of 8,934 unit goal")
        print(f"Stalled: {stalled['summary']['total_stalled']} projects ({stalled['summary']['total_units_at_risk']} units)")

        print(f"\n✓ APR {year} generated successfully!")

    except Exception as e:
        print(f"\n✗ Generation failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
