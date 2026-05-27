#!/usr/bin/env python3
"""
Schema inventory: Structured fields in v2 database
===================================================
Read-only inspection of permits, project_events, projects, and related
vocabulary tables to understand what classification fields exist beyond
description text.

Does NOT modify any files or database. Does NOT commit.
"""

import sqlite3
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / 'schema_inventory.txt'
DB_PATH = Path(__file__).parent.parent.parent / 'databases' / 'berkeley_housing_v2.db'


def main():
    conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    cur = conn.cursor()

    lines = []
    lines.append("=" * 70)
    lines.append("V2 DATABASE SCHEMA INVENTORY")
    lines.append("=" * 70)
    lines.append("")

    # a) Full schema of permits table
    lines.append("=" * 70)
    lines.append("A) PERMITS TABLE SCHEMA")
    lines.append("=" * 70)
    cols = cur.execute("PRAGMA table_info('permits')").fetchall()
    lines.append(f"{'cid':<4} {'name':<30} {'type':<15} {'notnull':<8} {'dflt_value':<20} {'pk'}")
    lines.append("-" * 90)
    for row in cols:
        cid, name, typ, notnull, dflt, pk = row
        lines.append(f"{cid:<4} {name:<30} {typ or '':<15} {notnull:<8} {str(dflt) if dflt else '':<20} {pk}")
    lines.append("")

    # b) Related tables
    lines.append("=" * 70)
    lines.append("B) RELATED TABLE SCHEMAS")
    lines.append("=" * 70)

    # Get all table names
    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t[0] for t in tables]

    # Tables to inspect
    inspect_tables = ['project_events', 'projects']
    # Add tables containing 'permit', 'vocabulary', or 'type' in name
    for t in table_names:
        tl = t.lower()
        if 'permit' in tl or 'vocabulary' in tl or 'type' in tl:
            if t not in inspect_tables:
                inspect_tables.append(t)

    for table in sorted(inspect_tables):
        lines.append("")
        lines.append(f"--- {table} ---")
        cols = cur.execute(f"PRAGMA table_info('{table}')").fetchall()
        lines.append(f"{'cid':<4} {'name':<35} {'type':<15} {'notnull':<8} {'dflt_value':<20} {'pk'}")
        lines.append("-" * 95)
        for row in cols:
            cid, name, typ, notnull, dflt, pk = row
            lines.append(f"{cid:<4} {name:<35} {typ or '':<15} {notnull:<8} {str(dflt) if dflt else '':<20} {pk}")

    lines.append("")

    # c) Foreign key relationships
    lines.append("=" * 70)
    lines.append("C) FOREIGN KEY RELATIONSHIPS")
    lines.append("=" * 70)

    for table in ['permits', 'project_events', 'projects']:
        lines.append("")
        lines.append(f"--- {table} foreign keys ---")
        fks = cur.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
        if fks:
            lines.append(f"{'id':<4} {'seq':<4} {'table':<30} {'from':<25} {'to':<25} {'on_update':<12} {'on_delete'}")
            lines.append("-" * 110)
            for fk in fks:
                lines.append(f"{fk[0]:<4} {fk[1]:<4} {fk[2]:<30} {fk[3]:<25} {fk[4]:<25} {fk[5]:<12} {fk[6]}")
        else:
            lines.append("(no foreign keys)")

    lines.append("")

    # d) Distinct values for classification-like columns on permits
    lines.append("=" * 70)
    lines.append("D) PERMITS: DISTINCT VALUES FOR CLASSIFICATION COLUMNS")
    lines.append("=" * 70)

    # Get permits column names
    permit_cols = [row[1] for row in cur.execute("PRAGMA table_info('permits')").fetchall()]

    # Columns that look like classification/category
    classification_keywords = ['type', 'status', 'class', 'category', 'scope', 'kind', 'source']
    for col in permit_cols:
        col_lower = col.lower()
        if any(kw in col_lower for kw in classification_keywords):
            lines.append("")
            lines.append(f"--- permits.{col} ---")
            try:
                values = cur.execute(f"SELECT {col}, COUNT(*) FROM permits GROUP BY {col} ORDER BY 2 DESC").fetchall()
                for val, cnt in values:
                    lines.append(f"  {str(val):<50} {cnt:>5}")
            except Exception as e:
                lines.append(f"  ERROR: {e}")

    lines.append("")

    # e) Distinct values for classification-like columns on project_events
    lines.append("=" * 70)
    lines.append("E) PROJECT_EVENTS: DISTINCT VALUES FOR CLASSIFICATION COLUMNS")
    lines.append("=" * 70)

    pe_cols = [row[1] for row in cur.execute("PRAGMA table_info('project_events')").fetchall()]

    for col in pe_cols:
        col_lower = col.lower()
        if any(kw in col_lower for kw in classification_keywords):
            lines.append("")
            lines.append(f"--- project_events.{col} ---")
            try:
                values = cur.execute(f"SELECT {col}, COUNT(*) FROM project_events GROUP BY {col} ORDER BY 2 DESC").fetchall()
                for val, cnt in values:
                    lines.append(f"  {str(val):<50} {cnt:>5}")
            except Exception as e:
                lines.append(f"  ERROR: {e}")

    lines.append("")

    # f) Sample 5 random permits rows
    lines.append("=" * 70)
    lines.append("F) SAMPLE 5 PERMITS ROWS (ALL COLUMNS)")
    lines.append("=" * 70)

    sample = cur.execute("SELECT * FROM permits ORDER BY RANDOM() LIMIT 5").fetchall()
    col_names = [desc[0] for desc in cur.description]

    for i, row in enumerate(sample):
        lines.append("")
        lines.append(f"--- Sample permit {i+1} ---")
        for col, val in zip(col_names, row):
            val_str = str(val) if val is not None else 'NULL'
            if len(val_str) > 80:
                val_str = val_str[:77] + '...'
            lines.append(f"  {col:<30} {val_str}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF SCHEMA INVENTORY")
    lines.append("=" * 70)

    conn.close()

    # Write output
    output_text = '\n'.join(lines)
    with open(OUTPUT_FILE, 'w') as f:
        f.write(output_text)

    print(output_text)
    print(f"\nWritten to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
