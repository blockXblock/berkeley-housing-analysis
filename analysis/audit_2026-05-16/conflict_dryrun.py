#!/usr/bin/env python3
"""
Conflict dry-run: check which descriptions match BOTH completes-class
and candidate does-not-complete patterns.

This is a one-off audit script. Does NOT modify permit_role_classifier.py.
"""

import sqlite3
import csv
import re
import sys
sys.path.insert(0, 'scripts')

# Import existing patterns from classifier (read-only)
from permit_role_classifier import COMPLETES_PROJECT_PATTERNS

# Extract just the pattern strings (classifier stores as (pattern, label) tuples)
EXISTING_COMPLETES_PATTERNS = [p[0] if isinstance(p, tuple) else p for p in COMPLETES_PROJECT_PATTERNS]

# Candidate additions (NOT committed to classifier yet)
CANDIDATE_COMPLETES_UNIT_HYPHEN = r'\d+[- ]?units?\b'

CANDIDATE_DOES_NOT_COMPLETE = [
    r'\bremodel\b',
    r'\bsiding\b',
    r'\bwindow\b',
    r'\bshoring\b',
    r'\bexcavation\b',
    r'\bgrading\b',
    r'\binsulation\b',
    r'\bdrywall\b',
    r'\bmural\b',
    r'\bLED screen\b',
    r'\bexterior sign\b',
    r'demolish.*(building|apartment|residence)',
]


def find_matches(text, patterns):
    """Return list of pattern strings that match the text."""
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    for p in patterns:
        if re.search(p, text_lower, re.IGNORECASE):
            matched.append(p)
    return matched


def main():
    conn = sqlite3.connect('databases/berkeley_housing_v2.db')
    cur = conn.cursor()

    # All patterns that indicate "completes project"
    all_completes_patterns = EXISTING_COMPLETES_PATTERNS + [CANDIDATE_COMPLETES_UNIT_HYPHEN]

    conflicts = []
    pattern_conflict_counts = {p: 0 for p in CANDIDATE_DOES_NOT_COMPLETE}

    # Check all permits
    permits = cur.execute("""
        SELECT pm.id, pm.description, pm.project_id, pr.canonical_address
        FROM permits pm
        LEFT JOIN projects pr ON pr.id = pm.project_id
    """).fetchall()

    for permit_id, description, project_id, project_address in permits:
        if not description:
            continue
        completes_matches = find_matches(description, all_completes_patterns)
        does_not_matches = find_matches(description, CANDIDATE_DOES_NOT_COMPLETE)

        if completes_matches and does_not_matches:
            conflicts.append({
                'source_table': 'permits',
                'source_id': permit_id,
                'description': description,
                'matched_completes_patterns': '; '.join(completes_matches),
                'matched_does_not_complete_patterns': '; '.join(does_not_matches),
                'project_id': project_id,
                'project_address': project_address,
            })
            for p in does_not_matches:
                pattern_conflict_counts[p] += 1

    # Check all CO event summaries
    events = cur.execute("""
        SELECT pe.id, pe.summary, pe.project_id, pr.canonical_address
        FROM project_events pe
        JOIN vocabulary_event_types vet ON vet.id = pe.event_type_id
        LEFT JOIN projects pr ON pr.id = pe.project_id
        WHERE vet.code = 'co_issued'
    """).fetchall()

    for event_id, summary, project_id, project_address in events:
        if not summary:
            continue
        completes_matches = find_matches(summary, all_completes_patterns)
        does_not_matches = find_matches(summary, CANDIDATE_DOES_NOT_COMPLETE)

        if completes_matches and does_not_matches:
            conflicts.append({
                'source_table': 'events',
                'source_id': event_id,
                'description': summary,
                'matched_completes_patterns': '; '.join(completes_matches),
                'matched_does_not_complete_patterns': '; '.join(does_not_matches),
                'project_id': project_id,
                'project_address': project_address,
            })
            for p in does_not_matches:
                pattern_conflict_counts[p] += 1

    # Write CSV
    with open('analysis/audit_2026-05-16/conflict_cases.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'source_table', 'source_id', 'description',
            'matched_completes_patterns', 'matched_does_not_complete_patterns',
            'project_id', 'project_address'
        ])
        writer.writeheader()
        writer.writerows(conflicts)

    print(f"Step 5: conflict_cases.csv written with {len(conflicts)} rows")
    print()
    print("Pattern conflict breakdown (does-not-complete patterns triggering conflicts):")
    for p, count in sorted(pattern_conflict_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {count:3d}  {p}")

    conn.close()
    return len(conflicts), pattern_conflict_counts


if __name__ == '__main__':
    main()
