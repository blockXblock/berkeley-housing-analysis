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
DB_PATH = BASE_DIR / 'data' / 'berkeley_housing_analysis.db'

def generate_table_a(conn, year):
    """
    Table A: Projects with applications deemed complete in the reporting year
    HCD definition: Projects where completeness review finished in the year
    """
    cursor = conn.cursor()

    # Projects with complete date in the reporting year
    cursor.execute('''
        SELECT
            id, address_display, apn, permits, units, vli_units, status,
            filed, complete, entitled,
            density_bonus, sb35_flag, sb330_flag, ab2011_flag,
            developer, architect
        FROM projects
        WHERE complete LIKE ?
        ORDER BY complete
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
            id, address_display, apn, permits, units, vli_units, status,
            filed, complete, entitled, bp_issued, co_date,
            density_bonus, sb35_flag, sb330_flag, ab2011_flag,
            developer, architect, construction_status,
            CASE
                WHEN co_date LIKE ? THEN 'CO Issued'
                WHEN bp_issued LIKE ? THEN 'BP Issued'
                WHEN entitled LIKE ? THEN 'Entitled'
            END as milestone_achieved
        FROM projects
        WHERE entitled LIKE ? OR bp_issued LIKE ? OR co_date LIKE ?
        ORDER BY
            CASE
                WHEN co_date LIKE ? THEN 1
                WHEN bp_issued LIKE ? THEN 2
                WHEN entitled LIKE ? THEN 3
            END,
            units DESC
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

def generate_table_b(conn, year, adu_count=0):
    """
    Table B: RHNA Progress by Income Level
    Shows permitted units (BP issued only) through the reporting year against RHNA targets
    RHNA credit requires building permit issuance, not just entitlement
    """
    cursor = conn.cursor()

    # Berkeley's 6th Cycle RHNA allocation (2023-2031)
    rhna_targets = {
        "very_low": 1786,
        "low": 1028,
        "moderate": 1452,
        "above_moderate": 4668,
        "total": 8934
    }

    # ADU affordability split (ABAG 30/30/30/10)
    adu_vli = round(adu_count * 0.30)
    adu_low = round(adu_count * 0.30)
    adu_mod = round(adu_count * 0.30)
    adu_above = adu_count - adu_vli - adu_low - adu_mod

    # Get permitted units - ONLY projects with BP issued (RHNA credit requirement)
    cursor.execute('''
        SELECT
            SUM(COALESCE(vli_units, 0)) as vli_units,
            SUM(units) as total_units
        FROM projects
        WHERE bp_issued IS NOT NULL AND bp_issued != ''
    ''')
    row = cursor.fetchone()
    bp_vli = row[0] or 0
    bp_total = row[1] or 0

    # Income breakdown for BP-issued projects:
    # - VLI: actual vli_units from database
    # - Low/Moderate: we have no LI or MOD columns for multifamily, so 0
    # - Above Moderate: total units minus VLI
    # Then add ADUs with ABAG 30/30/30/10 split
    vli_permitted = bp_vli + adu_vli
    low_permitted = adu_low  # No Low Income data from multifamily projects
    mod_permitted = adu_mod  # No Moderate Income data from multifamily projects
    above_mod = (bp_total - bp_vli) + adu_above
    total_permitted = bp_total + adu_count

    income_levels = [
        {
            "income_level": "Very Low",
            "rhna_target": rhna_targets["very_low"],
            "permitted": vli_permitted,
            "percent_of_target": round(vli_permitted / rhna_targets["very_low"] * 100, 1) if rhna_targets["very_low"] > 0 else 0
        },
        {
            "income_level": "Low",
            "rhna_target": rhna_targets["low"],
            "permitted": low_permitted,
            "percent_of_target": round(low_permitted / rhna_targets["low"] * 100, 1) if rhna_targets["low"] > 0 else 0
        },
        {
            "income_level": "Moderate",
            "rhna_target": rhna_targets["moderate"],
            "permitted": mod_permitted,
            "percent_of_target": round(mod_permitted / rhna_targets["moderate"] * 100, 1) if rhna_targets["moderate"] > 0 else 0
        },
        {
            "income_level": "Above Moderate",
            "rhna_target": rhna_targets["above_moderate"],
            "permitted": above_mod,
            "percent_of_target": round(above_mod / rhna_targets["above_moderate"] * 100, 1) if rhna_targets["above_moderate"] > 0 else 0
        },
        {
            "income_level": "Total",
            "rhna_target": rhna_targets["total"],
            "permitted": total_permitted,
            "percent_of_target": round(total_permitted / rhna_targets["total"] * 100, 1) if rhna_targets["total"] > 0 else 0
        }
    ]

    return {
        "title": f"Table B: RHNA Progress by Income Level Through {year}",
        "description": f"Cumulative permitted units through {year} against 6th Cycle RHNA targets (2023-2031)",
        "income_levels": income_levels,
        "summary": {
            "total_permitted": total_permitted,
            "total_rhna": rhna_targets["total"],
            "percent_of_goal": round(total_permitted / rhna_targets["total"] * 100, 1),
            "adu_count": adu_count
        }
    }

def generate_developer_summary(conn, year):
    """
    Supplemental: Developer Summary
    Units permitted (BP issued) by developer with affordability breakdown
    """
    cursor = conn.cursor()

    # Developer summary for projects with BP issued only (RHNA credit)
    cursor.execute('''
        SELECT
            COALESCE(developer, 'Unknown/Individual') as developer_name,
            COUNT(*) as project_count,
            SUM(units) as total_units,
            SUM(COALESCE(vli_units, 0)) as vli_units,
            SUM(CASE WHEN density_bonus = 1 THEN 1 ELSE 0 END) as density_bonus_projects
        FROM projects
        WHERE bp_issued IS NOT NULL AND bp_issued != ''
        GROUP BY COALESCE(developer, 'Unknown/Individual')
        ORDER BY total_units DESC
    ''')

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
        "title": f"Supplemental: Developer Summary Through {year}",
        "description": f"Units permitted by developer for projects with BP issued or CO",
        "developers": rows,
        "summary": {
            "total_developers": len([r for r in rows if r['developer'] != 'Unknown/Individual']),
            "total_projects": sum(r['project_count'] for r in rows),
            "total_units": sum(r['total_units'] for r in rows),
            "total_vli": sum(r['vli_units'] for r in rows)
        }
    }

def generate_rhna_progress(conn, year, adu_count=0):
    """
    RHNA Progress Summary
    RHNA credit requires building permit issuance - NOT just entitlement or pipeline
    Shows both: 1) RHNA credit (BP issued only) 2) Pipeline (all projects)
    """
    cursor = conn.cursor()

    # Berkeley's 6th Cycle RHNA allocation (2023-2031)
    rhna_allocation = {
        "very_low": 1786,
        "low": 1028,
        "moderate": 1452,
        "above_moderate": 4668,
        "total": 8934
    }

    # RHNA CREDIT: Only projects with BP issued (this is what counts for HCD)
    cursor.execute('''
        SELECT
            SUM(units) as total_units,
            SUM(COALESCE(vli_units, 0)) as vli_units
        FROM projects
        WHERE bp_issued IS NOT NULL AND bp_issued != ''
    ''')
    bp_row = cursor.fetchone()
    bp_issued_units = bp_row[0] or 0
    bp_issued_vli = bp_row[1] or 0

    # RHNA credit = BP-issued units + ADUs
    rhna_credit_units = bp_issued_units + adu_count
    rhna_credit_percent = round(rhna_credit_units / rhna_allocation['total'] * 100, 1)

    # PIPELINE: All projects (for context, not RHNA credit)
    cursor.execute('''
        SELECT
            SUM(units) as total_units,
            SUM(COALESCE(vli_units, 0)) as vli_units
        FROM projects
    ''')
    pipeline_row = cursor.fetchone()
    pipeline_units = pipeline_row[0] or 0
    pipeline_vli = pipeline_row[1] or 0

    # Completed units (CO issued)
    cursor.execute('''
        SELECT
            SUM(units) as total_units,
            SUM(COALESCE(vli_units, 0)) as vli_units
        FROM projects
        WHERE co_date IS NOT NULL AND co_date != ''
    ''')
    co_row = cursor.fetchone()
    completed_units = co_row[0] or 0
    completed_vli = co_row[1] or 0

    return {
        "title": f"RHNA Progress Through {year}",
        "description": "RHNA credit requires building permit issuance. Pipeline units shown separately.",
        "allocation": rhna_allocation,
        "rhna_credit": {
            "bp_issued_units": bp_issued_units,
            "adu_units": adu_count,
            "total_credit": rhna_credit_units,
            "vli_units": bp_issued_vli,
            "percent_of_goal": rhna_credit_percent
        },
        "pipeline": {
            "total_units": pipeline_units,
            "vli_units": pipeline_vli,
            "note": "Pipeline units do NOT count toward RHNA until BP is issued"
        },
        "completed": {
            "total_units": completed_units,
            "vli_units": completed_vli
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
    Projects entitled but not yet permitted (potential stalled projects)
    """
    cursor = conn.cursor()

    # Get entitled projects without BP issued
    cursor.execute('''
        SELECT
            id, address_display, units, status, developer,
            complete, entitled, bp_issued,
            accela_status_date
        FROM projects
        WHERE entitled IS NOT NULL AND entitled != ''
          AND (bp_issued IS NULL OR bp_issued = '')
        ORDER BY units DESC
    ''')

    columns = ['id', 'address', 'net_units', 'status', 'developer',
               'app_complete_date', 'entitled_date', 'bp_issued_date', 'accela_status_date']

    rows = []
    for row in cursor.fetchall():
        rows.append(dict(zip(columns, row)))

    return {
        "title": "Stalled Projects",
        "description": "Projects entitled but not yet issued building permits",
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

        print(f"\nGenerating Table B (RHNA Progress by Income Level)...")
        table_b = generate_table_b(conn, year, args.adus)
        print(f"  {table_b['summary']['total_permitted']} units permitted, {table_b['summary']['percent_of_goal']}% of RHNA goal")

        print(f"\nGenerating Developer Summary...")
        developer_summary = generate_developer_summary(conn, year)
        print(f"  {developer_summary['summary']['total_developers']} developers, {developer_summary['summary']['total_units']} units")

        print(f"\nGenerating RHNA Progress through {year}...")
        rhna = generate_rhna_progress(conn, year, args.adus)
        print(f"  RHNA Credit: {rhna['rhna_credit']['total_credit']} units ({rhna['rhna_credit']['percent_of_goal']}% of goal)")
        print(f"  Pipeline (not RHNA credit): {rhna['pipeline']['total_units']} units")

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
            "developer_summary": developer_summary,
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
            # Table B uses income_levels key
            write_csv({"projects": table_b.get('income_levels', [])}, output_path, f'table_b_{year}.csv')
            write_csv(developer_summary, output_path, f'developer_summary_{year}.csv')
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
        print(f"\nTable B (RHNA Progress - BP Issued Only):")
        for level in table_b['income_levels']:
            print(f"  {level['income_level']}: {level['permitted']} / {level['rhna_target']} ({level['percent_of_target']}%)")
        print(f"\nRHNA Credit Summary:")
        print(f"  BP Issued: {rhna['rhna_credit']['bp_issued_units']} units")
        print(f"  ADUs: {rhna['rhna_credit']['adu_units']} units")
        print(f"  Total RHNA Credit: {rhna['rhna_credit']['total_credit']} units = {rhna['rhna_credit']['percent_of_goal']}% of {rhna['allocation']['total']} goal")
        print(f"\nPipeline (NOT RHNA Credit): {rhna['pipeline']['total_units']} units")
        print(f"\nDeveloper Summary: {developer_summary['summary']['total_developers']} known developers")
        print(f"Stalled: {stalled['summary']['total_stalled']} projects ({stalled['summary']['total_units_at_risk']} units)")

        print(f"\n✓ APR {year} generated successfully!")

    except Exception as e:
        print(f"\n✗ Generation failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
