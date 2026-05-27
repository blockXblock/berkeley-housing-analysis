#!/usr/bin/env python3
"""
Ambiguous permits full field dump
=================================
Dumps every column of the 21 permits linked to ambiguous CO events,
plus their linked project rows.

Read-only. Does NOT modify any files or database.
"""

import csv
import sqlite3
from pathlib import Path

INPUT_CSV = Path(__file__).parent / 'post_patch_ambiguous_events.csv'
OUTPUT_FILE = Path(__file__).parent / 'ambiguous_permits_full_fields.txt'
DB_PATH = Path(__file__).parent.parent.parent / 'databases' / 'berkeley_housing_v2.db'


def main():
    # Read permit_ids from the ambiguous events CSV
    with open(INPUT_CSV, 'r') as f:
        reader = csv.DictReader(f)
        permit_ids = [int(row['permit_id']) for row in reader]

    conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get column names for permits and projects
    permit_cols = [row[1] for row in cur.execute("PRAGMA table_info('permits')").fetchall()]
    project_cols = [row[1] for row in cur.execute("PRAGMA table_info('projects')").fetchall()]

    # Get vocabulary lookups for human-readable output
    permit_types = dict(cur.execute("SELECT id, code FROM vocabulary_permit_types").fetchall())
    permit_statuses = dict(cur.execute("SELECT id, code FROM vocabulary_permit_status_types").fetchall())
    stage_types = dict(cur.execute("SELECT id, code FROM vocabulary_stage_types").fetchall())

    lines = []
    lines.append("=" * 80)
    lines.append("AMBIGUOUS PERMITS - FULL FIELD DUMP")
    lines.append(f"Total permits: {len(permit_ids)}")
    lines.append("=" * 80)

    for permit_id in permit_ids:
        # Get permit row
        permit = cur.execute(
            f"SELECT * FROM permits WHERE id = ?", (permit_id,)
        ).fetchone()

        if not permit:
            lines.append(f"\n=== permit_id {permit_id} NOT FOUND ===")
            continue

        project_id = permit['project_id']

        # Get project row
        project = cur.execute(
            f"SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()

        permit_type_code = permit_types.get(permit['permit_type_id'], 'NULL')
        permit_status_code = permit_statuses.get(permit['permit_status_type_id'], 'NULL')
        project_address = project['canonical_address'] if project else 'UNKNOWN'

        lines.append("")
        lines.append("=" * 80)
        lines.append(f"=== permit_id {permit_id} ({permit['permit_number']}) | project {project_id} ({project_address}) ===")
        lines.append("=" * 80)

        lines.append("")
        lines.append("--- PERMITS TABLE ---")
        for col in permit_cols:
            val = permit[col]
            # Add human-readable lookup for FK columns
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

    print(f"Written {len(permit_ids)} permits to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
