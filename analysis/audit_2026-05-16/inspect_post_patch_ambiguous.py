#!/usr/bin/env python3
"""
Inspection script: Post-patch ambiguous CO events
=================================================
Read-only inspection of CO events after the leading-word precedence
refactor (commit e9de43c). Outputs a CSV of ambiguous events for
calibrating next pattern additions.

Does NOT modify any files or database. Does NOT commit.
"""

import csv
import sqlite3
import sys
from collections import Counter
from pathlib import Path

# Add scripts/ to path for classifier import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from permit_role_classifier import classify_permit_for_completion

# Output paths
OUTPUT_DIR = Path(__file__).parent
CSV_OUTPUT = OUTPUT_DIR / 'post_patch_ambiguous_events.csv'


def main():
    db_path = Path(__file__).parent.parent.parent / 'databases' / 'berkeley_housing_v2.db'

    # Open read-only
    conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Query all CO events with permit and project info
    rows = cur.execute("""
        SELECT
            pe.id           AS event_id,
            pe.event_date,
            pe.permit_id,
            pe.summary      AS event_summary,
            pm.permit_number,
            vpt.code        AS permit_type,
            pm.description  AS permit_description,
            pe.project_id,
            proj.canonical_address AS project_address
        FROM project_events pe
        JOIN vocabulary_event_types vet ON vet.id = pe.event_type_id
        LEFT JOIN permits pm ON pm.id = pe.permit_id
        LEFT JOIN vocabulary_permit_types vpt ON vpt.id = pm.permit_type_id
        LEFT JOIN projects proj ON proj.id = pe.project_id
        WHERE vet.code = 'co_issued'
        ORDER BY pe.project_id, pe.event_date
    """).fetchall()

    # Buckets
    completes = []
    does_not_complete = []
    ambiguous_with_permit = []
    no_permit_link = []

    for row in rows:
        event_id = row['event_id']
        permit_id = row['permit_id']
        permit_description = row['permit_description']
        event_summary = row['event_summary']

        # Determine source text
        if permit_id is None:
            no_permit_link.append(dict(row))
            continue

        # Prefer permit description, fallback to event summary
        if permit_description:
            source_text = permit_description
            source_used = 'permit_description'
        elif event_summary:
            source_text = event_summary
            source_used = 'event_summary'
        else:
            source_text = None
            source_used = 'none'

        # Classify
        classification = classify_permit_for_completion(source_text)

        record = {
            'event_id': event_id,
            'project_id': row['project_id'],
            'project_address': row['project_address'],
            'event_date': row['event_date'],
            'permit_id': permit_id,
            'permit_number': row['permit_number'],
            'permit_type': row['permit_type'],
            'source_used': source_used,
            'description_text': source_text,
            'classification': classification,
        }

        if classification == 'completes_project':
            completes.append(record)
        elif classification == 'does_not_complete_project':
            does_not_complete.append(record)
        else:  # ambiguous
            ambiguous_with_permit.append(record)

    conn.close()

    # Write CSV of ambiguous events
    csv_columns = [
        'event_id', 'project_id', 'project_address', 'event_date',
        'permit_id', 'permit_number', 'permit_type', 'source_used',
        'description_text'
    ]

    with open(CSV_OUTPUT, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction='ignore')
        writer.writeheader()
        for record in ambiguous_with_permit:
            writer.writerow(record)

    # Print summary
    print("=" * 60)
    print("POST-PATCH CO EVENT CLASSIFICATION (commit e9de43c)")
    print("=" * 60)
    print()
    print("BUCKET COUNTS:")
    print(f"  completes_project:         {len(completes):3d}")
    print(f"  does_not_complete_project: {len(does_not_complete):3d}")
    print(f"  ambiguous (with permit):   {len(ambiguous_with_permit):3d}")
    print(f"  no_permit_link:            {len(no_permit_link):3d}")
    print(f"  ----------------------------")
    print(f"  TOTAL CO EVENTS:           {len(completes) + len(does_not_complete) + len(ambiguous_with_permit) + len(no_permit_link):3d}")
    print()

    # First-word frequency in ambiguous bucket
    print("FIRST-WORD FREQUENCY (ambiguous bucket):")
    first_words = Counter()
    for record in ambiguous_with_permit:
        text = record['description_text']
        if text:
            # Get first word, lowercased
            first_word = text.strip().split()[0].lower() if text.strip() else '(empty)'
            first_words[first_word] += 1
        else:
            first_words['(no_text)'] += 1

    for word, count in first_words.most_common():
        print(f"  {word:30s} {count:3d}")

    print()
    print(f"CSV written to: {CSV_OUTPUT}")
    print()
    print("CONFIRMATION: No files modified, no commits, no DB writes.")


if __name__ == '__main__':
    main()
