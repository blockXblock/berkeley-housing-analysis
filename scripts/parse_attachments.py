#!/usr/bin/env python3
"""
Parse ATTACHMENTS sections from accela_status text files
and insert into project_documents table.
"""

import sqlite3
import re
import os
from pathlib import Path

DB_PATH = Path('/Users/johngage/berkeley-data/data/berkeley_housing_analysis.db')
ACCELA_DIR = Path('/Users/johngage/berkeley-data/data/raw/accela_status')

def extract_address_from_filename(filename):
    """Extract address from filename like ZP2024-0126_2298_DURANT_Ave.txt"""
    # Remove permit number prefix and extension
    name = filename.replace('.txt', '')
    parts = name.split('_')

    # Skip permit number (first part if it contains letters and numbers)
    start_idx = 0
    if parts and re.match(r'^[A-Z]+\d+', parts[0]):
        start_idx = 1

    # Reconstruct address
    addr_parts = parts[start_idx:]
    if len(addr_parts) >= 2:
        # Format: number + street name
        number = addr_parts[0]
        street = ' '.join(addr_parts[1:]).replace('_', ' ')
        return f"{number} {street}".upper()
    return None

def find_project_id(conn, address):
    """Find project_id by matching address"""
    if not address:
        return None

    cursor = conn.cursor()
    # Try exact match first
    cursor.execute("SELECT id FROM projects WHERE UPPER(address_display) LIKE ?", (f"%{address}%",))
    row = cursor.fetchone()
    if row:
        return row[0]

    # Try number + first word of street
    parts = address.split()
    if len(parts) >= 2:
        pattern = f"{parts[0]} {parts[1]}%"
        cursor.execute("SELECT id FROM projects WHERE UPPER(address_display) LIKE ?", (pattern,))
        row = cursor.fetchone()
        if row:
            return row[0]

    return None

def parse_attachment_line(line):
    """Parse an attachment line and return dict with filename, size, date"""
    # Remove leading number and dot: "1. " or "  1.  "
    line = re.sub(r'^\s*\d+\.\s*', '', line).strip()

    # Try pipe separator: "filename.pdf | size | date"
    if '|' in line:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 3:
            return {
                'filename': parts[0],
                'size': parts[1],
                'date': parts[2]
            }
        elif len(parts) == 2:
            return {
                'filename': parts[0],
                'size': parts[1],
                'date': None
            }

    # Try dash separator: "filename.pdf - size - date"
    dash_match = re.match(r'(.+\.pdf)\s*-\s*([0-9.,]+\s*[KMGT]?B)\s*-\s*(\d{2}/\d{2}/\d{4})', line, re.I)
    if dash_match:
        return {
            'filename': dash_match.group(1).strip(),
            'size': dash_match.group(2).strip(),
            'date': dash_match.group(3).strip()
        }

    # Try just filename with size
    size_match = re.match(r'(.+\.pdf)\s*[-|]\s*([0-9.,]+\s*[KMGT]?B)', line, re.I)
    if size_match:
        return {
            'filename': size_match.group(1).strip(),
            'size': size_match.group(2).strip(),
            'date': None
        }

    # Just filename
    if '.pdf' in line.lower():
        return {
            'filename': line.split()[0] if ' ' in line else line,
            'size': None,
            'date': None
        }

    return None

def parse_file(filepath):
    """Parse a single accela_status file for attachments"""
    attachments = []
    in_attachments = False

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.rstrip()

            # Detect start of ATTACHMENTS section
            if 'ATTACHMENTS' in line.upper():
                in_attachments = True
                continue

            # End of attachments section (empty line or new section header)
            if in_attachments:
                if line.strip() == '' or (line.strip() and not line.strip()[0].isdigit() and not line.startswith(' ')):
                    # Check if it's a continuation or end
                    if not any(c.isdigit() for c in line[:5] if c):
                        if not '.pdf' in line.lower():
                            in_attachments = False
                            continue

                # Parse attachment line
                if '.pdf' in line.lower() or re.match(r'^\s*\d+\.', line):
                    attachment = parse_attachment_line(line)
                    if attachment and attachment.get('filename'):
                        attachments.append(attachment)

    return attachments

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clear existing city_attachment entries
    cursor.execute("DELETE FROM project_documents WHERE document_type = 'city_attachment'")

    total_inserted = 0
    files_processed = 0

    for filepath in ACCELA_DIR.glob('*.txt'):
        filename = filepath.name
        address = extract_address_from_filename(filename)
        project_id = find_project_id(conn, address)

        attachments = parse_file(filepath)

        if attachments:
            files_processed += 1
            print(f"\n{filename}: {len(attachments)} attachments")
            if project_id:
                print(f"  -> Linked to project_id {project_id} ({address})")
            else:
                print(f"  -> No project match for: {address}")

            for att in attachments:
                # Generate title from filename
                title = att['filename'].replace('.pdf', '').replace('_', ' ')
                # Clean up date format
                notes = f"Size: {att['size']}" if att['size'] else None

                cursor.execute('''
                    INSERT INTO project_documents
                    (project_id, title, filename, document_type, source, notes)
                    VALUES (?, ?, ?, 'city_attachment', ?, ?)
                ''', (project_id, title, att['filename'], filename, notes))
                total_inserted += 1

    conn.commit()

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Files processed: {files_processed}")
    print(f"Documents inserted: {total_inserted}")

    # Show stats
    cursor.execute("SELECT COUNT(*) FROM project_documents WHERE project_id IS NOT NULL")
    linked = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM project_documents WHERE project_id IS NULL")
    unlinked = cursor.fetchone()[0]
    print(f"Linked to projects: {linked}")
    print(f"Unlinked: {unlinked}")

    conn.close()

if __name__ == '__main__':
    main()
