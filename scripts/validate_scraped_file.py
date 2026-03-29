#!/usr/bin/env python3
"""
Validate a scraped Accela text file.

Checks:
- File has more than 3 lines of real content (not a pbpaste stub)
- Extracts PERMIT and ADDRESS from file contents
- Compares against the filename for mismatches
- Checks that required sections exist: PROCESSING STATUS, FEES, ATTACHMENTS
- Reports what's missing

Usage:
    python scripts/validate_scraped_file.py data/raw/accela_status/ZP2024-0058_2700_SHATTUCK.txt
    python scripts/validate_scraped_file.py --check-all  # Check all files
"""

import sys
import re
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    """Result of validating a scraped file."""
    filepath: str
    is_valid: bool
    is_stub: bool
    is_empty: bool
    line_count: int
    content_permit: Optional[str]
    content_address: Optional[str]
    filename_permit: Optional[str]
    filename_address: Optional[str]
    permit_match: bool
    address_match: bool
    has_processing_status: bool
    has_fees: bool
    has_attachments: bool
    has_attachment_urls: bool
    has_record_info: bool
    has_staff_names: bool
    has_entity_names: bool  # developer/architect/contractor
    attachment_url_count: int
    staff_name_count: int
    warnings: list
    errors: list


def parse_filename(filename: str):
    """Extract permit and address from filename."""
    name = Path(filename).stem
    parts = name.split('_', 1)

    permit = None
    address = None

    if len(parts) >= 1:
        first = parts[0]
        # Check if first part is a permit (has letters and dash)
        if re.search(r'[A-Za-z]', first) and '-' in first:
            permit = first
            if len(parts) > 1:
                address = parts[1].replace('_', ' ')
        elif first.startswith('B_'):
            # Building permit file
            address = name[2:].replace('_', ' ')
        elif first.isdigit():
            # Address-only file
            address = name.replace('_', ' ')
        else:
            address = name.replace('_', ' ')

    return permit, address


def normalize_address(addr: str) -> str:
    """Normalize address for comparison."""
    if not addr:
        return ''
    addr = ' '.join(addr.upper().split())
    # Remove city/state/zip
    addr = re.sub(r',?\s*(BERKELEY|CA|94\d{3}).*$', '', addr, re.I)
    # Remove common suffixes
    addr = re.sub(r'\s+(AVE|AVENUE|ST|STREET|WAY|BLVD|BOULEVARD|RD|ROAD|DR|DRIVE|LN|LANE|CT|COURT|PL|PLACE)\.?\s*$', '', addr, re.I)
    return addr.strip()


def addresses_match(addr1: str, addr2: str) -> bool:
    """Check if two addresses match (normalized)."""
    if not addr1 or not addr2:
        return True  # Can't compare, assume OK

    n1 = normalize_address(addr1)
    n2 = normalize_address(addr2)

    # Extract number and first word
    p1 = n1.split()
    p2 = n2.split()

    if not p1 or not p2:
        return True

    # Compare street number
    if p1[0] != p2[0]:
        return False

    # Compare first word of street name
    if len(p1) > 1 and len(p2) > 1:
        if p1[1][:4] != p2[1][:4]:
            return False

    return True


def validate_file(filepath: str) -> ValidationResult:
    """Validate a scraped Accela text file."""
    path = Path(filepath)

    result = ValidationResult(
        filepath=str(path),
        is_valid=True,
        is_stub=False,
        is_empty=False,
        line_count=0,
        content_permit=None,
        content_address=None,
        filename_permit=None,
        filename_address=None,
        permit_match=True,
        address_match=True,
        has_processing_status=False,
        has_fees=False,
        has_attachments=False,
        has_attachment_urls=False,
        has_record_info=False,
        has_staff_names=False,
        has_entity_names=False,
        attachment_url_count=0,
        staff_name_count=0,
        warnings=[],
        errors=[]
    )

    # Check file exists
    if not path.exists():
        result.is_valid = False
        result.errors.append(f"File not found: {filepath}")
        return result

    # Read file
    try:
        content = path.read_text(errors='replace')
    except Exception as e:
        result.is_valid = False
        result.errors.append(f"Cannot read file: {e}")
        return result

    # Check for empty
    if not content.strip():
        result.is_valid = False
        result.is_empty = True
        result.errors.append("File is empty")
        return result

    # Check for pbpaste stub
    if content.strip().startswith('pbpaste'):
        result.is_valid = False
        result.is_stub = True
        result.errors.append("File is a pbpaste stub (clipboard not captured)")
        return result

    # Count lines
    lines = content.strip().split('\n')
    result.line_count = len([l for l in lines if l.strip()])

    if result.line_count < 3:
        result.is_valid = False
        result.is_stub = True
        result.errors.append(f"File has only {result.line_count} lines (stub)")
        return result

    # Extract from filename
    result.filename_permit, result.filename_address = parse_filename(path.name)

    # Extract from content
    for line in lines[:50]:
        line_stripped = line.strip()

        # ADDRESS
        if line_stripped.startswith('ADDRESS:'):
            addr = line_stripped.replace('ADDRESS:', '').strip()
            addr = re.sub(r',?\s*(BERKELEY|CA|94\d{3}).*$', '', addr, re.I)
            result.content_address = addr.strip()

        # PERMIT
        if line_stripped.startswith('PERMIT:'):
            p = line_stripped.replace('PERMIT:', '').strip()
            if p:
                result.content_permit = p.split()[0]

        # Record ID format
        m = re.match(r'^Record ID:\s*([A-Z0-9-]+)', line_stripped)
        if m and not result.content_permit:
            result.content_permit = m.group(1)

        # PERMIT N: format
        m = re.match(r'^PERMIT \d+:\s*([A-Z0-9-]+)', line_stripped)
        if m and not result.content_permit:
            result.content_permit = m.group(1)

    # Check sections
    content_upper = content.upper()

    if 'PROCESSING STATUS' in content_upper or 'STATUS:' in content_upper:
        result.has_processing_status = True
    else:
        result.warnings.append("Missing PROCESSING STATUS section")

    if 'FEES' in content_upper or 'FEE SUMMARY' in content_upper or 'FEES:' in content_upper:
        result.has_fees = True
    else:
        result.warnings.append("Missing FEES section")

    if 'ATTACHMENTS' in content_upper or 'ATTACHMENT' in content_upper or 'DOCUMENTS' in content_upper:
        result.has_attachments = True
    else:
        result.warnings.append("Missing ATTACHMENTS section")

    if 'RECORD INFO' in content_upper or 'APPLICANT' in content_upper or 'OWNER' in content_upper:
        result.has_record_info = True

    # Check for attachment URLs (https:// or http:// in attachment lines)
    url_pattern = re.compile(r'https?://[^\s\]]+', re.I)
    attachment_urls = url_pattern.findall(content)
    result.attachment_url_count = len(attachment_urls)
    if result.has_attachments and attachment_urls:
        result.has_attachment_urls = True
    elif result.has_attachments:
        result.warnings.append("ATTACHMENTS section exists but no download URLs captured")

    # Check for staff names (By: Name or by Name patterns)
    staff_pattern = re.compile(r'\b[Bb]y[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)', re.M)
    staff_matches = staff_pattern.findall(content)
    result.staff_name_count = len(staff_matches)
    if staff_matches:
        result.has_staff_names = True
    else:
        result.warnings.append("No staff names captured (expected 'By: Name' patterns)")

    # Check for entity names (developer, architect, contractor)
    entity_keywords = ['DEVELOPER', 'ARCHITECT', 'CONTRACTOR', 'APPLICANT', 'OWNER']
    found_entities = [kw for kw in entity_keywords if kw in content_upper]
    if found_entities:
        result.has_entity_names = True

    # Compare permit
    if result.filename_permit and result.content_permit:
        if result.filename_permit != result.content_permit:
            result.permit_match = False
            result.errors.append(f"Permit mismatch: filename={result.filename_permit}, content={result.content_permit}")
            result.is_valid = False

    # Compare address
    if result.filename_address and result.content_address:
        if not addresses_match(result.filename_address, result.content_address):
            result.address_match = False
            result.errors.append(f"Address mismatch: filename={result.filename_address}, content={result.content_address}")
            result.is_valid = False

    return result


def print_result(result: ValidationResult, verbose: bool = True):
    """Print validation result."""
    status = "VALID" if result.is_valid else "INVALID"
    icon = "✓" if result.is_valid else "✗"

    print(f"\n{icon} {status}: {result.filepath}")
    print("-" * 60)

    if result.is_empty:
        print("  Status: EMPTY FILE")
        return

    if result.is_stub:
        print("  Status: STUB (pbpaste or <3 lines)")
        return

    print(f"  Lines: {result.line_count}")
    print(f"  Filename permit:  {result.filename_permit or '(none)'}")
    print(f"  Content permit:   {result.content_permit or '(none)'}")
    print(f"  Filename address: {result.filename_address or '(none)'}")
    print(f"  Content address:  {result.content_address or '(none)'}")

    print(f"\n  Sections found:")
    print(f"    Processing Status: {'✓' if result.has_processing_status else '✗'}")
    print(f"    Staff names:       {'✓' if result.has_staff_names else '✗'} ({result.staff_name_count} found)")
    print(f"    Fees:              {'✓' if result.has_fees else '✗'}")
    print(f"    Attachments:       {'✓' if result.has_attachments else '✗'}")
    print(f"    Attachment URLs:   {'✓' if result.has_attachment_urls else '✗'} ({result.attachment_url_count} URLs)")
    print(f"    Entity names:      {'✓' if result.has_entity_names else '✗'}")
    print(f"    Record Info:       {'✓' if result.has_record_info else '✗'}")

    if result.errors:
        print(f"\n  ERRORS:")
        for err in result.errors:
            print(f"    ✗ {err}")

    if verbose and result.warnings:
        print(f"\n  WARNINGS:")
        for warn in result.warnings:
            print(f"    ⚠ {warn}")


def main():
    parser = argparse.ArgumentParser(description='Validate scraped Accela text files')
    parser.add_argument('filepath', nargs='?', help='Path to file to validate')
    parser.add_argument('--check-all', action='store_true', help='Check all files in accela_status/')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode (exit code only)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if args.check_all:
        # Check all files
        base_dir = Path('data/raw/accela_status')
        files = list(base_dir.rglob('*.txt'))

        valid = 0
        invalid = 0

        for f in sorted(files):
            result = validate_file(str(f))
            if result.is_valid:
                valid += 1
            else:
                invalid += 1
                if not args.quiet:
                    print_result(result, verbose=False)

        print(f"\n{'='*60}")
        print(f"SUMMARY: {valid} valid, {invalid} invalid out of {len(files)} files")
        sys.exit(0 if invalid == 0 else 1)

    elif args.filepath:
        result = validate_file(args.filepath)

        if args.json:
            import json
            print(json.dumps({
                'valid': result.is_valid,
                'stub': result.is_stub,
                'empty': result.is_empty,
                'lines': result.line_count,
                'permit_match': result.permit_match,
                'address_match': result.address_match,
                'has_processing_status': result.has_processing_status,
                'has_fees': result.has_fees,
                'has_attachments': result.has_attachments,
                'errors': result.errors,
                'warnings': result.warnings
            }, indent=2))
        elif not args.quiet:
            print_result(result)

        sys.exit(0 if result.is_valid else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
