#!/usr/bin/env python3
"""
Completes permits full field dump
=================================
Dumps every column of the 9 permits linked to completes_project CO events.

Read-only. Does NOT modify any files or database.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
from permit_role_classifier import classify_permit_for_completion

OUTPUT_FILE = Path(__file__).parent / 'completes_permits_full_fields.txt'
DB_PATH = Path(__file__).parent.parent.parent / 'databases' / 'berkeley_housing_v2.db'


def main():
    conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all CO events with permit descriptions
    co_events = cur.execute("""
        SELECT
            pe.id AS event_id,
            pe.permit_id,
            pm.description AS permit_description,
            pe.summary AS event_summary
        FROM project_events pe
        JOIN vocabulary_event_types vet ON vet.id = pe.event_type_id
        LEFT JOIN permits pm ON pm.id = pe.permit_id
        WHERE vet.code = 'co_issued'
          AND pe.permit_id IS NOT NULL
    """).fetchall()

    # Find completes_project permits
    completes_permit_ids = []
    for row in co_events:
        text = row['permit_description'] or row['event_summary']
        if classify_permit_for_completion(text) == 'completes_project':
            completes_permit_ids.append(row['permit_id'])

    # Get column names for permits and projects
    permit_cols = [row[1] for row in cur.execute("PRAGMA table_info('permits')").fetchall()]
    project_cols = [row[1] for row in cur.execute("PRAGMA table_info('projects')").fetchall()]

    # Get vocabulary lookups
    permit_types = dict(cur.execute("SELECT id, code FROM vocabulary_permit_types").fetchall())
    permit_statuses = dict(cur.execute("SELECT id, code FROM vocabulary_permit_status_types").fetchall())
    stage_types = dict(cur.execute("SELECT id, code FROM vocabulary_stage_types").fetchall())

    lines = []
    lines.append("=" * 80)
    lines.append("COMPLETES_PROJECT PERMITS - FULL FIELD DUMP (CONTROL GROUP)")
    lines.append(f"Total permits: {len(completes_permit_ids)}")
    lines.append("=" * 80)

    for permit_id in completes_permit_ids:
        permit = cur.execute("SELECT * FROM permits WHERE id = ?", (permit_id,)).fetchone()
        if not permit:
            continue

        project_id = permit['project_id']
        project = cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()

        project_address = project['canonical_address'] if project else 'UNKNOWN'

        lines.append("")
        lines.append("=" * 80)
        lines.append(f"=== permit_id {permit_id} ({permit['permit_number']}) | project {project_id} ({project_address}) ===")
        lines.append("=" * 80)

        lines.append("")
        lines.append("--- PERMITS TABLE ---")
        for col in permit_cols:
            val = permit[col]
            extra = ""
            if col == 'permit_type_id' and val:
                extra = f"  ({permit_types.get(val, '?')})"
            elif col == 'permit_status_type_id' and val:
                extra = f"  ({permit_statuses.get(val, '?')})"
            val_str = str(val) if val is not None else 'NULL'
            lines.append(f"  {col:<30} {val_str}{extra}")

        if project:
            lines.append("")
            lines.append("--- PROJECTS TABLE ---")
            for col in project_cols:
                val = project[col]
                extra = ""
                if col == 'current_stage_type_id' and val:
                    extra = f"  ({stage_types.get(val, '?')})"
                val_str = str(val) if val is not None else 'NULL'
                lines.append(f"  {col:<30} {val_str}{extra}")

    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF DUMP")
    lines.append("=" * 80)

    conn.close()

    output_text = '\n'.join(lines)
    with open(OUTPUT_FILE, 'w') as f:
        f.write(output_text)

    print(f"Written {len(completes_permit_ids)} permits to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
