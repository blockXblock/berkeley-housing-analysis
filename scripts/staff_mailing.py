#!/usr/bin/env python3
"""
Staff Mailing List Manager

Manage the staff_mailing table for Berkeley city staff outreach.

Usage:
    python scripts/staff_mailing.py list [--all|--active|--trial]
    python scripts/staff_mailing.py verify EMAIL
    python scripts/staff_mailing.py activate EMAIL
    python scripts/staff_mailing.py deactivate EMAIL
    python scripts/staff_mailing.py export [--active-only]
    python scripts/staff_mailing.py add NAME EMAIL [--verified]
"""

import sqlite3
import argparse
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'outreach' / 'outreach.db'

def get_conn():
    return sqlite3.connect(DB_PATH)

def list_staff(filter_type='all'):
    conn = get_conn()
    cursor = conn.cursor()

    if filter_type == 'active':
        cursor.execute('''
            SELECT name, email, role, verified, active
            FROM staff_mailing WHERE active=1 ORDER BY name
        ''')
        print("=== ACTIVE STAFF (will receive mail) ===\n")
    elif filter_type == 'trial':
        cursor.execute('''
            SELECT name, email, role, verified, active
            FROM staff_mailing WHERE verified=0 ORDER BY name
        ''')
        print("=== TRIAL/UNVERIFIED STAFF ===\n")
    else:
        cursor.execute('''
            SELECT name, email, role, verified, active
            FROM staff_mailing ORDER BY active DESC, verified DESC, name
        ''')
        print("=== ALL STAFF ===\n")

    rows = cursor.fetchall()
    for name, email, role, verified, active in rows:
        status = "✓" if active else "○"
        v_mark = "[verified]" if verified else "[trial]"
        role_str = f" ({role})" if role else ""
        print(f"  {status} {name}{role_str}")
        print(f"      {email} {v_mark}")

    print(f"\nTotal: {len(rows)}")
    conn.close()

def verify_email(email):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE staff_mailing
        SET verified=1, active=1, verified_at=?
        WHERE email=?
    ''', (datetime.now().isoformat(), email))

    if cursor.rowcount:
        print(f"✓ Verified and activated: {email}")
    else:
        print(f"✗ Email not found: {email}")

    conn.commit()
    conn.close()

def set_active(email, active):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('UPDATE staff_mailing SET active=? WHERE email=?', (active, email))

    if cursor.rowcount:
        status = "activated" if active else "deactivated"
        print(f"✓ {status.capitalize()}: {email}")
    else:
        print(f"✗ Email not found: {email}")

    conn.commit()
    conn.close()

def export_emails(active_only=True):
    conn = get_conn()
    cursor = conn.cursor()

    if active_only:
        cursor.execute('SELECT name, email FROM staff_mailing WHERE active=1 ORDER BY name')
    else:
        cursor.execute('SELECT name, email FROM staff_mailing ORDER BY name')

    rows = cursor.fetchall()

    # Print in format suitable for email clients
    print("# Copy/paste for email To: field:")
    print(", ".join([f'"{name}" <{email}>' for name, email in rows]))

    print(f"\n# {len(rows)} recipients")
    conn.close()

def add_staff(name, email, verified=False):
    conn = get_conn()
    cursor = conn.cursor()

    domain = email.split('@')[1] if '@' in email else None
    active = 1 if verified else 0

    try:
        cursor.execute('''
            INSERT INTO staff_mailing (name, email, email_domain, source, verified, active)
            VALUES (?, ?, ?, 'manual', ?, ?)
        ''', (name, email, domain, int(verified), active))
        status = "verified" if verified else "trial"
        print(f"✓ Added ({status}): {name} <{email}>")
    except sqlite3.IntegrityError:
        print(f"✗ Email already exists: {email}")

    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='Staff Mailing List Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # list command
    list_parser = subparsers.add_parser('list', help='List staff')
    list_parser.add_argument('--all', action='store_true', help='Show all staff')
    list_parser.add_argument('--active', action='store_true', help='Show only active staff')
    list_parser.add_argument('--trial', action='store_true', help='Show only trial/unverified')

    # verify command
    verify_parser = subparsers.add_parser('verify', help='Verify and activate an email')
    verify_parser.add_argument('email', help='Email to verify')

    # activate command
    activate_parser = subparsers.add_parser('activate', help='Activate an email')
    activate_parser.add_argument('email', help='Email to activate')

    # deactivate command
    deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate an email')
    deactivate_parser.add_argument('email', help='Email to deactivate')

    # export command
    export_parser = subparsers.add_parser('export', help='Export emails for mailing')
    export_parser.add_argument('--all', action='store_true', help='Export all, not just active')

    # add command
    add_parser = subparsers.add_parser('add', help='Add new staff')
    add_parser.add_argument('name', help='Staff name')
    add_parser.add_argument('email', help='Email address')
    add_parser.add_argument('--verified', action='store_true', help='Mark as verified')

    args = parser.parse_args()

    if args.command == 'list':
        if args.active:
            list_staff('active')
        elif args.trial:
            list_staff('trial')
        else:
            list_staff('all')
    elif args.command == 'verify':
        verify_email(args.email)
    elif args.command == 'activate':
        set_active(args.email, 1)
    elif args.command == 'deactivate':
        set_active(args.email, 0)
    elif args.command == 'export':
        export_emails(active_only=not args.all)
    elif args.command == 'add':
        add_staff(args.name, args.email, args.verified)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
