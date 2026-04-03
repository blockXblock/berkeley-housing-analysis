#!/usr/bin/env python3
"""
Outreach Contact Management

Manage contacts, mailing lists, and outreach campaigns for Berkeley Civic Action.

Usage:
    python scripts/manage_outreach.py list [--category CATEGORY]
    python scripts/manage_outreach.py send --template NAME [--category CATEGORY] [--dry-run]
    python scripts/manage_outreach.py log --contact-id ID --channel CHANNEL --status STATUS [--subject SUBJECT]
    python scripts/manage_outreach.py import-mailchimp FILE.csv
    python scripts/manage_outreach.py export [--category CATEGORY] [--output FILE.csv]
    python scripts/manage_outreach.py templates
    python scripts/manage_outreach.py add --name NAME --email EMAIL --category CATEGORY [--org ORG] [--role ROLE]
"""

import argparse
import sqlite3
import csv
import sys
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / 'data' / 'outreach' / 'outreach.db'

def get_connection():
    """Get database connection"""
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def list_contacts(category=None):
    """List all contacts, optionally filtered by category"""
    conn = get_connection()
    cursor = conn.cursor()

    if category:
        cursor.execute('''
            SELECT id, name, organization, role, email, category, subcategory
            FROM contacts
            WHERE category = ?
            ORDER BY name
        ''', (category,))
    else:
        cursor.execute('''
            SELECT id, name, organization, role, email, category, subcategory
            FROM contacts
            ORDER BY category, name
        ''')

    rows = cursor.fetchall()

    if not rows:
        print("No contacts found.")
        return

    current_category = None
    for row in rows:
        id_, name, org, role, email, cat, subcat = row

        if cat != current_category:
            print(f"\n{'='*60}")
            print(f"  {cat}")
            print(f"{'='*60}")
            current_category = cat

        email_str = f"<{email}>" if email else "(no email)"
        subcat_str = f"[{subcat}]" if subcat else ""
        print(f"  {id_:3d}. {name}")
        print(f"       {org or ''} - {role or ''} {subcat_str}")
        print(f"       {email_str}")

    # Summary
    cursor.execute('SELECT category, COUNT(*) FROM contacts GROUP BY category ORDER BY COUNT(*) DESC')
    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    for cat, count in cursor.fetchall():
        print(f"  {cat}: {count}")

    cursor.execute('SELECT COUNT(*) FROM contacts')
    total = cursor.fetchone()[0]
    print(f"  --------")
    print(f"  Total: {total}")

    conn.close()

def send_emails(template_name, category=None, dry_run=True):
    """Generate personalized emails from template"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get template
    cursor.execute('SELECT subject, body FROM message_templates WHERE name = ?', (template_name,))
    result = cursor.fetchone()
    if not result:
        print(f"Error: Template '{template_name}' not found.")
        cursor.execute('SELECT name FROM message_templates')
        templates = [r[0] for r in cursor.fetchall()]
        print(f"Available templates: {', '.join(templates)}")
        conn.close()
        return

    subject, body = result

    # Get contacts with email addresses
    if category:
        cursor.execute('''
            SELECT id, name, email, organization, category
            FROM contacts
            WHERE email IS NOT NULL AND email != '' AND category = ?
            ORDER BY name
        ''', (category,))
    else:
        cursor.execute('''
            SELECT id, name, email, organization, category
            FROM contacts
            WHERE email IS NOT NULL AND email != ''
            ORDER BY category, name
        ''')

    contacts = cursor.fetchall()

    if not contacts:
        print("No contacts with email addresses found.")
        conn.close()
        return

    print(f"{'='*60}")
    print(f"  Template: {template_name}")
    print(f"  Subject: {subject}")
    print(f"  Recipients: {len(contacts)}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    for id_, name, email, org, cat in contacts:
        # Personalize
        personalized_body = body.replace('[Name]', name.split()[0] if name else 'Hello')

        print(f"To: {name} <{email}>")
        print(f"Category: {cat}")
        print(f"Subject: {subject}")
        print(f"---")
        print(personalized_body[:200] + "..." if len(personalized_body) > 200 else personalized_body)
        print(f"\n{'─'*40}\n")

        if not dry_run:
            # Log the outreach
            cursor.execute('''
                INSERT INTO outreach_log (contact_id, channel, subject, message_template, status)
                VALUES (?, 'email', ?, ?, 'scheduled')
            ''', (id_, subject, template_name))

    if not dry_run:
        conn.commit()
        print(f"\nLogged {len(contacts)} emails as 'scheduled'")
    else:
        print(f"\nDRY RUN complete. Use --no-dry-run to log emails.")

    conn.close()

def log_outreach(contact_id, channel, status, subject=None, notes=None):
    """Log an outreach interaction"""
    conn = get_connection()
    cursor = conn.cursor()

    # Verify contact exists
    cursor.execute('SELECT name, email FROM contacts WHERE id = ?', (contact_id,))
    contact = cursor.fetchone()
    if not contact:
        print(f"Error: Contact ID {contact_id} not found.")
        conn.close()
        return

    cursor.execute('''
        INSERT INTO outreach_log (contact_id, channel, subject, status, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (contact_id, channel, subject, status, notes))

    conn.commit()
    print(f"Logged {channel} to {contact[0]} ({contact[1]}) - Status: {status}")
    conn.close()

def import_mailchimp(filepath):
    """Import contacts from Mailchimp CSV export"""
    conn = get_connection()
    cursor = conn.cursor()

    if not Path(filepath).exists():
        print(f"Error: File not found: {filepath}")
        return

    imported = 0
    skipped = 0

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            email = row.get('Email Address', row.get('email', '')).strip()
            if not email:
                skipped += 1
                continue

            # Check if exists
            cursor.execute('SELECT id FROM contacts WHERE email = ?', (email,))
            if cursor.fetchone():
                skipped += 1
                continue

            # Extract name
            first_name = row.get('First Name', row.get('first_name', '')).strip()
            last_name = row.get('Last Name', row.get('last_name', '')).strip()
            name = f"{first_name} {last_name}".strip() or email.split('@')[0]

            # Insert
            cursor.execute('''
                INSERT INTO contacts (name, email, category, source)
                VALUES (?, ?, 'Mailchimp', 'Mailchimp import')
            ''', (name, email))

            contact_id = cursor.lastrowid

            # Add to mailing list
            cursor.execute('''
                INSERT INTO mailing_lists (contact_id, list_name, subscribed_date, status, source)
                VALUES (?, 'Mailchimp Import', date('now'), 'active', ?)
            ''', (contact_id, filepath))

            imported += 1

    conn.commit()
    print(f"Imported: {imported} contacts")
    print(f"Skipped (duplicate/empty): {skipped}")
    conn.close()

def export_contacts(category=None, output=None):
    """Export contacts to CSV"""
    conn = get_connection()
    cursor = conn.cursor()

    if category:
        cursor.execute('''
            SELECT name, organization, role, email, phone, category, subcategory, notes
            FROM contacts
            WHERE category = ?
            ORDER BY name
        ''', (category,))
    else:
        cursor.execute('''
            SELECT name, organization, role, email, phone, category, subcategory, notes
            FROM contacts
            ORDER BY category, name
        ''')

    rows = cursor.fetchall()
    columns = ['name', 'organization', 'role', 'email', 'phone', 'category', 'subcategory', 'notes']

    if output:
        with open(output, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        print(f"Exported {len(rows)} contacts to {output}")
    else:
        # Print to stdout
        writer = csv.writer(sys.stdout)
        writer.writerow(columns)
        writer.writerows(rows)

    conn.close()

def list_templates():
    """List available message templates"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id, name, subject, category, created_date FROM message_templates')

    print(f"\n{'='*60}")
    print("  Message Templates")
    print(f"{'='*60}")

    for id_, name, subject, category, created in cursor.fetchall():
        print(f"\n  {id_}. {name}")
        print(f"     Subject: {subject}")
        print(f"     Category: {category or 'General'}")
        print(f"     Created: {created}")

    conn.close()

def add_contact(name, email, category, organization=None, role=None):
    """Add a new contact"""
    conn = get_connection()
    cursor = conn.cursor()

    # Check for duplicate email
    if email:
        cursor.execute('SELECT id, name FROM contacts WHERE email = ?', (email,))
        existing = cursor.fetchone()
        if existing:
            print(f"Error: Email already exists for contact {existing[0]}: {existing[1]}")
            conn.close()
            return

    cursor.execute('''
        INSERT INTO contacts (name, email, category, organization, role)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, email, category, organization, role))

    contact_id = cursor.lastrowid
    conn.commit()
    print(f"Added contact {contact_id}: {name} <{email}> ({category})")
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='Outreach Contact Management')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # list command
    list_parser = subparsers.add_parser('list', help='List contacts')
    list_parser.add_argument('--category', '-c', help='Filter by category')

    # send command
    send_parser = subparsers.add_parser('send', help='Generate emails from template')
    send_parser.add_argument('--template', '-t', required=True, help='Template name')
    send_parser.add_argument('--category', '-c', help='Filter by category')
    send_parser.add_argument('--dry-run', action='store_true', default=True, help='Preview only (default)')
    send_parser.add_argument('--no-dry-run', action='store_true', help='Actually log emails')

    # log command
    log_parser = subparsers.add_parser('log', help='Log outreach interaction')
    log_parser.add_argument('--contact-id', '-i', type=int, required=True, help='Contact ID')
    log_parser.add_argument('--channel', required=True, choices=['email', 'phone', 'meeting', 'event', 'social_media'])
    log_parser.add_argument('--status', required=True, choices=['sent', 'opened', 'replied', 'bounced', 'scheduled'])
    log_parser.add_argument('--subject', '-s', help='Subject/topic')
    log_parser.add_argument('--notes', '-n', help='Notes')

    # import-mailchimp command
    import_parser = subparsers.add_parser('import-mailchimp', help='Import from Mailchimp CSV')
    import_parser.add_argument('file', help='CSV file path')

    # export command
    export_parser = subparsers.add_parser('export', help='Export contacts to CSV')
    export_parser.add_argument('--category', '-c', help='Filter by category')
    export_parser.add_argument('--output', '-o', help='Output file (stdout if not specified)')

    # templates command
    subparsers.add_parser('templates', help='List message templates')

    # add command
    add_parser = subparsers.add_parser('add', help='Add a contact')
    add_parser.add_argument('--name', required=True, help='Contact name')
    add_parser.add_argument('--email', required=True, help='Email address')
    add_parser.add_argument('--category', required=True,
                           choices=['Media', 'Research', 'City Council', 'City Staff', 'Advocacy', 'Real Estate', 'Education', 'Community', 'Mailchimp'])
    add_parser.add_argument('--org', help='Organization')
    add_parser.add_argument('--role', help='Role/title')

    args = parser.parse_args()

    if args.command == 'list':
        list_contacts(args.category)
    elif args.command == 'send':
        dry_run = not args.no_dry_run
        send_emails(args.template, args.category, dry_run)
    elif args.command == 'log':
        log_outreach(args.contact_id, args.channel, args.status, args.subject, args.notes)
    elif args.command == 'import-mailchimp':
        import_mailchimp(args.file)
    elif args.command == 'export':
        export_contacts(args.category, args.output)
    elif args.command == 'templates':
        list_templates()
    elif args.command == 'add':
        add_contact(args.name, args.email, args.category, args.org, args.role)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
