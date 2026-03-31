#!/usr/bin/env python3
"""
Fee Extraction Script for Berkeley Housing Pipeline
Extracts fee data from Accela text files and inserts into permit_fees table.

Handles multiple formats:
1. Tabular: | Date | Invoice | Amount | rows
2. Line format: 04/26/2022 | Invoice 499818 | $13,055.00
3. Summary: Total Paid: $X or Total Fees: $X
4. Parenthetical: (Invoice 478368: $750.00 on 10/21/2021)
5. Note format: largest single payment $122,310.00 on 08/25/2021
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permit_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            permit_number TEXT NOT NULL,
            address TEXT,
            fee_description TEXT,
            amount REAL NOT NULL,
            fee_date TEXT,
            status TEXT DEFAULT 'paid',
            invoice_number TEXT,
            source_file TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Create index for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_permit_fees_permit
        ON permit_fees(permit_number)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_permit_fees_address
        ON permit_fees(address)
    """)
    conn.commit()
    print("✅ permit_fees table created/verified")

def extract_permit_number_from_filename(filename):
    """Extract permit number from filename like ZP2022-0170_3030_TELEGRAPH.txt"""
    # Pattern: permit number at start (ZP2022-0170, B2023-06416, PLN2021-0054, etc.)
    match = re.match(r'^([A-Z]+\d{4}-\d{4,5})', filename)
    if match:
        return match.group(1)
    return None

def extract_address_from_filename(filename):
    """Extract address from filename."""
    # Remove permit number prefix if present
    name = re.sub(r'^[A-Z]+\d{4}-\d{4,5}_?', '', filename)
    # Remove .txt extension
    name = name.replace('.txt', '')
    # Convert underscores to spaces
    name = name.replace('_', ' ')
    return name.strip() if name else None

def extract_permit_from_content(content):
    """Extract permit number from file content."""
    patterns = [
        r'Permit\s*(?:Number|#|No\.?):\s*([A-Z]+\d{4}-\d{4,5})',
        r'Record\s*(?:Number|#|ID):\s*([A-Z]+\d{4}-\d{4,5})',
        r'^([A-Z]+\d{4}-\d{4,5})\s*$',
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None

def parse_fee_amount(amount_str):
    """Parse fee amount from string like $28,950.00 or 28950.00"""
    if not amount_str:
        return None
    # Remove $ and commas
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
    formats = [
        '%m/%d/%Y',
        '%Y-%m-%d',
        '%m-%d-%Y',
        '%d/%m/%Y',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def extract_fees_from_file(filepath):
    """Extract all fee records from a single text file."""
    fees = []

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"  ⚠️ Error reading {filepath}: {e}")
        return fees

    filename = os.path.basename(filepath)
    default_permit = extract_permit_number_from_filename(filename)
    default_address = extract_address_from_filename(filename)

    # Track current permit number as we parse through records
    current_permit = default_permit
    current_address = default_address

    lines = content.split('\n')
    in_fee_section = False

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

        # Detect fee section start
        if re.match(r'^FEES?:?\s*$', line_stripped, re.IGNORECASE) or 'Fees:' in line:
            in_fee_section = True
            continue

        # Detect fee section end
        if in_fee_section and (
            line_stripped.startswith('ATTACHMENTS') or
            line_stripped.startswith('---') or
            line_stripped.startswith('===') or
            (line_stripped.startswith('RECORD') and 'Fee' not in line_stripped)
        ):
            in_fee_section = False
            continue

        # Pattern 1: Tabular format | Date | Invoice | Amount |
        table_match = re.match(r'\|\s*(\d{2}/\d{2}/\d{4})\s*\|\s*(\d{5,6})\s*\|\s*\$?([\d,]+\.?\d*)\s*\|?', line_stripped)
        if table_match:
            fee_date = parse_date(table_match.group(1))
            invoice = table_match.group(2)
            amount = parse_fee_amount(table_match.group(3))
            if amount and amount > 0:
                fees.append({
                    'permit_number': current_permit or 'UNKNOWN',
                    'address': current_address,
                    'fee_description': None,
                    'amount': amount,
                    'fee_date': fee_date,
                    'status': 'paid',
                    'invoice_number': invoice,
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
                fees.append({
                    'permit_number': current_permit or 'UNKNOWN',
                    'address': current_address,
                    'fee_description': None,
                    'amount': amount,
                    'fee_date': fee_date,
                    'status': 'paid',
                    'invoice_number': invoice,
                    'source_file': filename
                })
            continue

        # Pattern 3: Parenthetical (Invoice 478368: $750.00 on 10/21/2021)
        paren_match = re.search(r'\(Invoice\s*(\d{5,6}):\s*\$?([\d,]+\.?\d*)\s*on\s*(\d{2}/\d{2}/\d{4})\)', line, re.IGNORECASE)
        if paren_match:
            invoice = paren_match.group(1)
            amount = parse_fee_amount(paren_match.group(2))
            fee_date = parse_date(paren_match.group(3))
            if amount and amount > 0:
                fees.append({
                    'permit_number': current_permit or 'UNKNOWN',
                    'address': current_address,
                    'fee_description': None,
                    'amount': amount,
                    'fee_date': fee_date,
                    'status': 'paid',
                    'invoice_number': invoice,
                    'source_file': filename
                })
            continue

        # Pattern 4: Multiple invoice items in one line
        # Invoice 420552: $1,260.00 + $1,800.00 on 12/24/2019; Invoice 416529: $400.00 on 10/08/2019
        multi_match = re.findall(r'Invoice\s*(\d{5,6}):\s*\$?([\d,]+\.?\d*)(?:\s*\+\s*\$?([\d,]+\.?\d*))*\s*on\s*(\d{2}/\d{2}/\d{4})', line, re.IGNORECASE)
        for match in multi_match:
            invoice = match[0]
            fee_date = parse_date(match[3])
            # First amount
            amount1 = parse_fee_amount(match[1])
            if amount1 and amount1 > 0:
                fees.append({
                    'permit_number': current_permit or 'UNKNOWN',
                    'address': current_address,
                    'fee_description': None,
                    'amount': amount1,
                    'fee_date': fee_date,
                    'status': 'paid',
                    'invoice_number': invoice,
                    'source_file': filename
                })
            # Second amount if present
            if match[2]:
                amount2 = parse_fee_amount(match[2])
                if amount2 and amount2 > 0:
                    fees.append({
                        'permit_number': current_permit or 'UNKNOWN',
                        'address': current_address,
                        'fee_description': None,
                        'amount': amount2,
                        'fee_date': fee_date,
                        'status': 'paid',
                        'invoice_number': invoice,
                        'source_file': filename
                    })

        # Pattern 5: Summary totals (capture as summary record if no detail available)
        # Total Paid: $212,874.00 or Total Fees: $500.00 or **Total paid fees: $377,724.51**
        total_match = re.search(r'(?:Total\s*(?:Paid|Fees?))[:\s]*\$?([\d,]+\.?\d*)', line, re.IGNORECASE)
        if total_match and not fees:  # Only use summary if no detailed records found yet for this section
            amount = parse_fee_amount(total_match.group(1))
            if amount and amount > 0:
                # Check if we already have this total in fees
                existing_amounts = sum(f['amount'] for f in fees if f.get('permit_number') == current_permit)
                if abs(existing_amounts - amount) > 1:  # Allow for rounding
                    # This is a summary without line items, add as single record
                    fees.append({
                        'permit_number': current_permit or 'UNKNOWN',
                        'address': current_address,
                        'fee_description': 'Total Fees (summary)',
                        'amount': amount,
                        'fee_date': None,
                        'status': 'paid',
                        'invoice_number': None,
                        'source_file': filename
                    })

        # Pattern 6: "largest single payment $122,310.00 on 08/25/2021"
        largest_match = re.search(r'largest\s+(?:single\s+)?payment\s+\$?([\d,]+\.?\d*)\s+on\s+(\d{2}/\d{2}/\d{4})', line, re.IGNORECASE)
        if largest_match:
            amount = parse_fee_amount(largest_match.group(1))
            fee_date = parse_date(largest_match.group(2))
            if amount and amount > 0:
                fees.append({
                    'permit_number': current_permit or 'UNKNOWN',
                    'address': current_address,
                    'fee_description': 'Large payment (flagged)',
                    'amount': amount,
                    'fee_date': fee_date,
                    'status': 'paid',
                    'invoice_number': None,
                    'source_file': filename
                })

    return fees

def extract_all_fees():
    """Extract fees from all text files and insert into database."""
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    create_permit_fees_table(conn)
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM permit_fees")
    conn.commit()
    print("🗑️  Cleared existing fee data")

    # Find all text files
    all_files = list(TEXT_FILES_DIR.rglob("*.txt"))
    print(f"📁 Found {len(all_files)} text files to process")

    total_fees = 0
    total_amount = 0.0
    projects_with_fees = set()
    all_fee_records = []

    for filepath in all_files:
        fees = extract_fees_from_file(filepath)
        if fees:
            for fee in fees:
                cursor.execute("""
                    INSERT INTO permit_fees
                    (permit_number, address, fee_description, amount, fee_date, status, invoice_number, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fee['permit_number'],
                    fee['address'],
                    fee['fee_description'],
                    fee['amount'],
                    fee['fee_date'],
                    fee['status'],
                    fee['invoice_number'],
                    fee['source_file']
                ))
                total_fees += 1
                total_amount += fee['amount']
                projects_with_fees.add(fee['permit_number'])
                all_fee_records.append(fee)

    conn.commit()

    # Generate summary
    print("\n" + "="*60)
    print("FEE EXTRACTION SUMMARY")
    print("="*60)
    print(f"📊 Total fee records extracted: {total_fees:,}")
    print(f"💰 Total dollar amount: ${total_amount:,.2f}")
    print(f"🏗️  Projects with fee data: {len(projects_with_fees)}")

    # Show top 10 by amount
    print("\n📈 Top 10 fees by amount:")
    cursor.execute("""
        SELECT permit_number, address, amount, fee_date, invoice_number
        FROM permit_fees
        ORDER BY amount DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"   ${row[2]:>12,.2f} | {row[0]} | {row[1] or 'N/A'}")

    # Show fees by year
    print("\n📅 Fees by year:")
    cursor.execute("""
        SELECT substr(fee_date, 1, 4) as year, SUM(amount) as total, COUNT(*) as count
        FROM permit_fees
        WHERE fee_date IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: ${row[1]:,.2f} ({row[2]} records)")

    # Export to JSON for explorer
    print("\n💾 Exporting fee data to JSON...")

    # Build fee data by project
    cursor.execute("""
        SELECT permit_number, address, SUM(amount) as total_fees, COUNT(*) as fee_count
        FROM permit_fees
        GROUP BY permit_number
        ORDER BY total_fees DESC
    """)
    by_project = {}
    for row in cursor.fetchall():
        by_project[row[0]] = {
            'permit_number': row[0],
            'address': row[1],
            'total_fees': row[2],
            'fee_count': row[3]
        }

    # Build fee data by year
    cursor.execute("""
        SELECT substr(fee_date, 1, 4) as year, SUM(amount) as total
        FROM permit_fees
        WHERE fee_date IS NOT NULL
        GROUP BY year
        ORDER BY year
    """)
    by_year = {row[0]: row[1] for row in cursor.fetchall()}

    # Large fees (>$100k)
    cursor.execute("""
        SELECT permit_number, address, amount, fee_date, invoice_number, source_file
        FROM permit_fees
        WHERE amount > 100000
        ORDER BY amount DESC
    """)
    large_fees = [{
        'permit_number': row[0],
        'address': row[1],
        'amount': row[2],
        'date': row[3],
        'invoice': row[4],
        'source': row[5]
    } for row in cursor.fetchall()]

    # All fee records
    cursor.execute("""
        SELECT permit_number, address, fee_description, amount, fee_date, status, invoice_number, source_file
        FROM permit_fees
        ORDER BY amount DESC
    """)
    all_records = [{
        'permit_number': row[0],
        'address': row[1],
        'description': row[2],
        'amount': row[3],
        'date': row[4],
        'status': row[5],
        'invoice': row[6],
        'source': row[7]
    } for row in cursor.fetchall()]

    fee_data = {
        'by_project': by_project,
        'by_year': by_year,
        'total': total_amount,
        'record_count': total_fees,
        'project_count': len(projects_with_fees),
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
