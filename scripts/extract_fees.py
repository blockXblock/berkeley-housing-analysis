#!/usr/bin/env python3
"""
Fee Extraction Script for Berkeley Housing Pipeline
Extracts fee data from Accela text files and inserts into permit_fees table.

Handles multiple formats:
1. Tabular: | Date | Invoice | Amount | rows
2. Line format: 04/26/2022 | Invoice 499818 | $13,055.00
3. Summary: Total Paid: $X or Total Fees: $X (only used if no detailed records)
4. Parenthetical: (Invoice 478368: $750.00 on 10/21/2021)
5. Note format: largest single payment $122,310.00 on 08/25/2021

Separates Planning permits (ZP, PLN, DRCP, DRCF) from Building permits (B).
"""

import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime
import json

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "berkeley_housing.db"
TEXT_FILES_DIR = Path(__file__).parent.parent / "data" / "raw" / "accela_status"

def create_permit_fees_table(conn):
    """Create permit_fees table if it doesn't exist."""
    cursor = conn.cursor()

    # Drop and recreate to add permit_type
    cursor.execute("DROP TABLE IF EXISTS permit_fees")

    cursor.execute("""
        CREATE TABLE permit_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            permit_number TEXT NOT NULL,
            permit_type TEXT NOT NULL DEFAULT 'Unknown',
            address TEXT,
            fee_description TEXT,
            amount REAL NOT NULL,
            fee_date TEXT,
            status TEXT DEFAULT 'paid',
            invoice_number TEXT,
            is_summary INTEGER DEFAULT 0,
            source_file TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Create indexes
    cursor.execute("CREATE INDEX idx_permit_fees_permit ON permit_fees(permit_number)")
    cursor.execute("CREATE INDEX idx_permit_fees_address ON permit_fees(address)")
    cursor.execute("CREATE INDEX idx_permit_fees_type ON permit_fees(permit_type)")
    conn.commit()
    print("✅ permit_fees table created with permit_type column")

def get_permit_type(permit_number):
    """Categorize permit as Planning or Building based on prefix."""
    if not permit_number:
        return 'Unknown'
    permit_number = permit_number.upper()
    if permit_number.startswith('B'):
        return 'Building'
    elif permit_number.startswith(('ZP', 'PLN', 'DRCP', 'DRCF', 'LMSAP', 'ZCBL')):
        return 'Planning'
    elif permit_number.startswith('P') and re.match(r'P\d{4}-', permit_number):
        return 'Planning'
    else:
        return 'Unknown'

def extract_permit_number_from_filename(filename):
    """Extract permit number from filename like ZP2022-0170_3030_TELEGRAPH.txt"""
    match = re.match(r'^([A-Z]+\d{4}-\d{4,5})', filename)
    if match:
        return match.group(1)
    return None

def extract_address_from_filename(filename):
    """Extract address from filename."""
    name = re.sub(r'^[A-Z]+\d{4}-\d{4,5}_?', '', filename)
    name = name.replace('.txt', '')
    name = name.replace('_', ' ')
    return name.strip() if name else None

def parse_fee_amount(amount_str):
    """Parse fee amount from string like $28,950.00 or 28950.00"""
    if not amount_str:
        return None
    cleaned = re.sub(r'[$,]', '', amount_str)
    try:
        return float(cleaned)
    except ValueError:
        return None

def parse_date(date_str):
    """Parse date from various formats."""
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def extract_fees_from_file(filepath):
    """Extract all fee records from a single text file."""
    detailed_fees = []  # Fees with invoice numbers/dates
    summary_fees = []   # Summary totals (fallback)

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"  ⚠️ Error reading {filepath}: {e}")
        return []

    filename = os.path.basename(filepath)
    default_permit = extract_permit_number_from_filename(filename)
    default_address = extract_address_from_filename(filename)

    current_permit = default_permit
    current_address = default_address

    lines = content.split('\n')

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Check for permit number changes
        permit_match = re.search(r'Permit\s*(?:Number|#|No\.?):\s*([A-Z]+\d{4}-\d{4,5})', line, re.IGNORECASE)
        if permit_match:
            current_permit = permit_match.group(1).upper()

        # Check for address
        address_match = re.search(r'Address:\s*(.+?)(?:,\s*BERKELEY|$)', line, re.IGNORECASE)
        if address_match:
            current_address = address_match.group(1).strip()

        # Check for RECORD markers
        record_match = re.search(r'RECORD\s*\d+.*?:\s*([A-Z]+\d{4}-\d{4,5})', line, re.IGNORECASE)
        if record_match:
            current_permit = record_match.group(1).upper()

        # Pattern 1: Tabular format | Date | Invoice | Amount |
        table_match = re.match(r'\|\s*(\d{2}/\d{2}/\d{4})\s*\|\s*(\d{5,6})\s*\|\s*\$?([\d,]+\.?\d*)\s*\|?', line_stripped)
        if table_match:
            fee_date = parse_date(table_match.group(1))
            invoice = table_match.group(2)
            amount = parse_fee_amount(table_match.group(3))
            if amount and amount > 0:
                detailed_fees.append({
                    'permit_number': current_permit or 'UNKNOWN',
                    'permit_type': get_permit_type(current_permit),
                    'address': current_address,
                    'fee_description': None,
                    'amount': amount,
                    'fee_date': fee_date,
                    'status': 'paid',
                    'invoice_number': invoice,
                    'is_summary': 0,
                    'source_file': filename
                })
            continue

        # Pattern 2: Line format MM/DD/YYYY | Invoice XXXXXX | $X,XXX.XX
        line_match = re.match(r'(\d{2}/\d{2}/\d{4})\s*\|\s*Invoice\s*(\d{5,6})\s*\|\s*\$?([\d,]+\.?\d*)', line_stripped)
        if line_match:
            fee_date = parse_date(line_match.group(1))
            invoice = line_match.group(2)
            amount = parse_fee_amount(line_match.group(3))
            if amount and amount > 0:
                detailed_fees.append({
                    'permit_number': current_permit or 'UNKNOWN',
                    'permit_type': get_permit_type(current_permit),
                    'address': current_address,
                    'fee_description': None,
                    'amount': amount,
                    'fee_date': fee_date,
                    'status': 'paid',
                    'invoice_number': invoice,
                    'is_summary': 0,
                    'source_file': filename
                })
            continue

        # Pattern 3: Parenthetical (Invoice 478368: $750.00 on 10/21/2021)
        paren_matches = re.findall(r'\(Invoice\s*(\d{5,6}):\s*\$?([\d,]+\.?\d*)\s*on\s*(\d{2}/\d{2}/\d{4})\)', line, re.IGNORECASE)
        for match in paren_matches:
            invoice = match[0]
            amount = parse_fee_amount(match[1])
            fee_date = parse_date(match[2])
            if amount and amount > 0:
                detailed_fees.append({
                    'permit_number': current_permit or 'UNKNOWN',
                    'permit_type': get_permit_type(current_permit),
                    'address': current_address,
                    'fee_description': None,
                    'amount': amount,
                    'fee_date': fee_date,
                    'status': 'paid',
                    'invoice_number': invoice,
                    'is_summary': 0,
                    'source_file': filename
                })

        # Pattern 4: Summary totals - collect but mark as summary
        total_match = re.search(r'(?:Total\s*(?:Paid|Fees?))[:\s]*\$?([\d,]+\.?\d*)', line, re.IGNORECASE)
        if total_match:
            amount = parse_fee_amount(total_match.group(1))
            if amount and amount > 0:
                summary_fees.append({
                    'permit_number': current_permit or 'UNKNOWN',
                    'permit_type': get_permit_type(current_permit),
                    'address': current_address,
                    'fee_description': 'Total Fees (summary)',
                    'amount': amount,
                    'fee_date': None,
                    'status': 'paid',
                    'invoice_number': None,
                    'is_summary': 1,
                    'source_file': filename
                })

    # Return detailed fees if available, otherwise use summary
    # Group by permit to avoid duplicate summaries
    if detailed_fees:
        return detailed_fees
    elif summary_fees:
        # Deduplicate summary fees by permit_number (take highest amount per permit)
        by_permit = {}
        for fee in summary_fees:
            pn = fee['permit_number']
            if pn not in by_permit or fee['amount'] > by_permit[pn]['amount']:
                by_permit[pn] = fee
        return list(by_permit.values())
    return []

def extract_all_fees():
    """Extract fees from all text files and insert into database."""
    conn = sqlite3.connect(DB_PATH)
    create_permit_fees_table(conn)
    cursor = conn.cursor()

    all_files = list(TEXT_FILES_DIR.rglob("*.txt"))
    print(f"📁 Found {len(all_files)} text files to process")

    total_detailed = 0
    total_summary = 0
    total_amount_detailed = 0.0
    total_amount_summary = 0.0
    projects_with_fees = set()

    for filepath in all_files:
        fees = extract_fees_from_file(filepath)
        for fee in fees:
            cursor.execute("""
                INSERT INTO permit_fees
                (permit_number, permit_type, address, fee_description, amount, fee_date, status, invoice_number, is_summary, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fee['permit_number'],
                fee['permit_type'],
                fee['address'],
                fee['fee_description'],
                fee['amount'],
                fee['fee_date'],
                fee['status'],
                fee['invoice_number'],
                fee['is_summary'],
                fee['source_file']
            ))
            if fee['is_summary']:
                total_summary += 1
                total_amount_summary += fee['amount']
            else:
                total_detailed += 1
                total_amount_detailed += fee['amount']
            projects_with_fees.add(fee['permit_number'])

    conn.commit()

    # Generate summary
    print("\n" + "="*60)
    print("FEE EXTRACTION SUMMARY")
    print("="*60)
    print(f"📊 Detailed fee records: {total_detailed:,} (${total_amount_detailed:,.2f})")
    print(f"📋 Summary fee records: {total_summary:,} (${total_amount_summary:,.2f})")
    print(f"💰 Total (detailed only): ${total_amount_detailed:,.2f}")
    print(f"🏗️  Projects with fee data: {len(projects_with_fees)}")

    # Show by permit type
    print("\n📊 Fees by Permit Type (detailed only):")
    cursor.execute("""
        SELECT permit_type, COUNT(*) as records, SUM(amount) as total
        FROM permit_fees
        WHERE is_summary = 0
        GROUP BY permit_type
        ORDER BY total DESC
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]:12} {row[1]:5} records  ${row[2]:>15,.2f}")

    # Show fees by year (detailed only)
    print("\n📅 Fees by Year (detailed only):")
    cursor.execute("""
        SELECT substr(fee_date, 1, 4) as year, SUM(amount) as total, COUNT(*) as count
        FROM permit_fees
        WHERE fee_date IS NOT NULL AND is_summary = 0
        GROUP BY year
        ORDER BY year DESC
    """)
    yearly_total = 0
    for row in cursor.fetchall():
        print(f"   {row[0]}: ${row[1]:>12,.2f} ({row[2]} records)")
        yearly_total += row[1]
    print(f"   {'TOTAL':4}: ${yearly_total:>12,.2f}")

    # Top 10 by amount (detailed)
    print("\n📈 Top 10 fees by amount (detailed):")
    cursor.execute("""
        SELECT permit_number, permit_type, address, amount, fee_date, invoice_number
        FROM permit_fees
        WHERE is_summary = 0
        ORDER BY amount DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"   ${row[3]:>12,.2f} | {row[1]:8} | {row[0]} | {row[2] or 'N/A'}")

    # Export to JSON for explorer
    print("\n💾 Exporting fee data to JSON...")

    # Build fee data by project (detailed only)
    cursor.execute("""
        SELECT permit_number, permit_type, address, SUM(amount) as total_fees, COUNT(*) as fee_count
        FROM permit_fees
        WHERE is_summary = 0
        GROUP BY permit_number
        ORDER BY total_fees DESC
    """)
    by_project = {}
    for row in cursor.fetchall():
        by_project[row[0]] = {
            'permit_number': row[0],
            'permit_type': row[1],
            'address': row[2],
            'total_fees': row[3],
            'fee_count': row[4]
        }

    # Build fee data by year (detailed only)
    cursor.execute("""
        SELECT substr(fee_date, 1, 4) as year, SUM(amount) as total
        FROM permit_fees
        WHERE fee_date IS NOT NULL AND is_summary = 0
        GROUP BY year
        ORDER BY year
    """)
    by_year = {row[0]: row[1] for row in cursor.fetchall()}

    # By permit type
    cursor.execute("""
        SELECT permit_type, SUM(amount) as total, COUNT(*) as count
        FROM permit_fees
        WHERE is_summary = 0
        GROUP BY permit_type
    """)
    by_type = {row[0]: {'total': row[1], 'count': row[2]} for row in cursor.fetchall()}

    # Large fees (>$50k, detailed only)
    cursor.execute("""
        SELECT permit_number, permit_type, address, amount, fee_date, invoice_number, source_file
        FROM permit_fees
        WHERE amount > 50000 AND is_summary = 0
        ORDER BY amount DESC
    """)
    large_fees = [{
        'permit_number': row[0],
        'permit_type': row[1],
        'address': row[2],
        'amount': row[3],
        'date': row[4],
        'invoice': row[5],
        'source': row[6]
    } for row in cursor.fetchall()]

    # All detailed records
    cursor.execute("""
        SELECT permit_number, permit_type, address, fee_description, amount, fee_date, status, invoice_number, source_file
        FROM permit_fees
        WHERE is_summary = 0
        ORDER BY amount DESC
    """)
    all_records = [{
        'permit_number': row[0],
        'permit_type': row[1],
        'address': row[2],
        'description': row[3],
        'amount': row[4],
        'date': row[5],
        'status': row[6],
        'invoice': row[7],
        'source': row[8]
    } for row in cursor.fetchall()]

    fee_data = {
        'by_project': by_project,
        'by_year': by_year,
        'by_type': by_type,
        'total': total_amount_detailed,
        'record_count': total_detailed,
        'project_count': len([p for p in projects_with_fees if p != 'UNKNOWN']),
        'large_fees': large_fees,
        'all_records': all_records
    }

    output_path = Path(__file__).parent.parent / "data" / "processed" / "project_fees.json"
    with open(output_path, 'w') as f:
        json.dump(fee_data, f, indent=2)
    print(f"✅ Saved fee data to {output_path}")

    conn.close()
    return fee_data

if __name__ == "__main__":
    extract_all_fees()
