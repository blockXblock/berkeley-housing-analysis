#!/usr/bin/env python3
"""
Valuation distribution analysis across classifier buckets
=========================================================
Analyzes permit valuation as a potential classification signal by
examining the distribution across completes, ambiguous, and
does_not_complete buckets.

Read-only. Does NOT modify any files or database.
"""

import sqlite3
import sys
from pathlib import Path
from statistics import median, quantiles

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
from permit_role_classifier import classify_permit_for_completion

OUTPUT_FILE = Path(__file__).parent / 'valuation_distribution.txt'
DB_PATH = Path(__file__).parent.parent.parent / 'databases' / 'berkeley_housing_v2.db'


def get_percentiles(values):
    """Return min, 25%, median, 75%, max for a list of numeric values."""
    if not values:
        return None, None, None, None, None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0], sorted_vals[0], sorted_vals[0], sorted_vals[0], sorted_vals[0]
    if n == 2:
        return sorted_vals[0], sorted_vals[0], (sorted_vals[0] + sorted_vals[1]) / 2, sorted_vals[1], sorted_vals[1]

    q = quantiles(sorted_vals, n=4) if n >= 4 else [sorted_vals[0], median(sorted_vals), sorted_vals[-1]]
    return (
        sorted_vals[0],
        q[0] if len(q) >= 3 else sorted_vals[0],
        median(sorted_vals),
        q[2] if len(q) >= 3 else sorted_vals[-1],
        sorted_vals[-1]
    )


def main():
    conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all CO events with permit info
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
    """).fetchall()

    # Bucket permit_ids by classification
    completes_permit_ids = []
    ambiguous_permit_ids = []
    does_not_complete_permit_ids = []
    no_permit_link_count = 0

    for row in co_events:
        permit_id = row['permit_id']
        if permit_id is None:
            no_permit_link_count += 1
            continue

        text = row['permit_description'] or row['event_summary']
        classification = classify_permit_for_completion(text)

        if classification == 'completes_project':
            completes_permit_ids.append(permit_id)
        elif classification == 'ambiguous':
            ambiguous_permit_ids.append(permit_id)
        else:  # does_not_complete_project
            does_not_complete_permit_ids.append(permit_id)

    # Get vocabulary lookups
    permit_types = dict(cur.execute("SELECT id, code FROM vocabulary_permit_types").fetchall())

    lines = []
    lines.append("=" * 80)
    lines.append("VALUATION DISTRIBUTION ANALYSIS")
    lines.append("Post-e9de43c classifier buckets")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"CO events total: {len(co_events)}")
    lines.append(f"  completes_project:         {len(completes_permit_ids)}")
    lines.append(f"  ambiguous:                 {len(ambiguous_permit_ids)}")
    lines.append(f"  does_not_complete_project: {len(does_not_complete_permit_ids)}")
    lines.append(f"  no_permit_link:            {no_permit_link_count}")
    lines.append("")

    buckets = [
        ('completes_project', completes_permit_ids),
        ('ambiguous', ambiguous_permit_ids),
        ('does_not_complete_project', does_not_complete_permit_ids),
    ]

    all_bucket_data = {}

    for bucket_name, permit_ids in buckets:
        if not permit_ids:
            continue

        # Query permits with project info
        placeholders = ','.join('?' * len(permit_ids))
        permits = cur.execute(f"""
            SELECT p.id, p.permit_number, p.permit_type_id,
                   p.permit_status_type_id, p.valuation, p.source_system,
                   p.description, p.project_id, proj.canonical_address AS address
            FROM permits p
            LEFT JOIN projects proj ON proj.id = p.project_id
            WHERE p.id IN ({placeholders})
            ORDER BY p.valuation DESC NULLS LAST
        """, permit_ids).fetchall()

        all_bucket_data[bucket_name] = permits

        lines.append("=" * 80)
        lines.append(f"=== BUCKET: {bucket_name} ({len(permits)} permits) ===")
        lines.append("=" * 80)
        lines.append("")

        # Table header
        lines.append(f"{'permit_id':<10} | {'permit_number':<14} | {'valuation':>14} | {'source':<8} | {'type':<16} | description (first 50 chars)")
        lines.append("-" * 130)

        valuations = []
        zero_count = 0
        null_count = 0
        source_counts = {}

        for p in permits:
            val = p['valuation']
            if val is None:
                null_count += 1
                val_str = 'NULL'
            else:
                valuations.append(val)
                if val == 0:
                    zero_count += 1
                val_str = f"${val:,.0f}"

            src = p['source_system'] or 'NULL'
            source_counts[src] = source_counts.get(src, 0) + 1

            type_code = permit_types.get(p['permit_type_id'], 'NULL')
            desc = (p['description'] or '')[:50]

            lines.append(f"{p['id']:<10} | {p['permit_number'] or 'NULL':<14} | {val_str:>14} | {src:<8} | {type_code:<16} | {desc}")

        lines.append("")
        lines.append("Summary stats for this bucket:")

        if valuations:
            min_v, p25, med, p75, max_v = get_percentiles(valuations)
            lines.append(f"  count:            {len(permits)}")
            lines.append(f"  valuation min:    ${min_v:,.0f}")
            lines.append(f"  valuation 25%:    ${p25:,.0f}")
            lines.append(f"  valuation median: ${med:,.0f}")
            lines.append(f"  valuation 75%:    ${p75:,.0f}")
            lines.append(f"  valuation max:    ${max_v:,.0f}")
        else:
            lines.append(f"  count:            {len(permits)}")
            lines.append(f"  valuation:        (no numeric values)")

        lines.append(f"  valuation == 0:   {zero_count} permits ({100*zero_count/len(permits):.1f}%)")
        lines.append(f"  valuation NULL:   {null_count} permits ({100*null_count/len(permits):.1f}%)")
        lines.append("")
        lines.append("  source_system breakdown:")
        for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
            lines.append(f"    {src}: {cnt}")
        lines.append("")

    # Cross-bucket comparison
    lines.append("=" * 80)
    lines.append("=== CROSS-BUCKET COMPARISON ===")
    lines.append("=" * 80)
    lines.append("")

    # Threshold sweep
    thresholds = [50000, 100000, 250000, 500000, 1000000, 2000000, 5000000]

    def count_above_threshold(permits, threshold):
        return sum(1 for p in permits if p['valuation'] is not None and p['valuation'] >= threshold)

    lines.append("Threshold sweep: at each candidate threshold, how cleanly")
    lines.append("does valuation separate completes from non-completes?")
    lines.append("")

    for threshold in thresholds:
        lines.append(f"Threshold ${threshold:,}:")
        for bucket_name, permits in all_bucket_data.items():
            above = count_above_threshold(permits, threshold)
            total = len(permits)
            pct = 100 * above / total if total else 0
            lines.append(f"  {bucket_name}: {above} of {total} ({pct:.1f}%)")
        lines.append("")

    # Overlap analysis
    lines.append("-" * 80)
    lines.append("Overlap analysis:")
    lines.append("")

    # Get valuations for each bucket
    completes_vals = [(p['id'], p['permit_number'], p['valuation'], p['description'][:40] if p['description'] else '')
                      for p in all_bucket_data.get('completes_project', [])
                      if p['valuation'] is not None]
    ambiguous_vals = [(p['id'], p['permit_number'], p['valuation'], p['description'][:40] if p['description'] else '')
                      for p in all_bucket_data.get('ambiguous', [])
                      if p['valuation'] is not None]
    does_not_vals = [(p['id'], p['permit_number'], p['valuation'], p['description'][:40] if p['description'] else '')
                     for p in all_bucket_data.get('does_not_complete_project', [])
                     if p['valuation'] is not None]

    if completes_vals:
        min_completes_val = min(v[2] for v in completes_vals)
        lines.append(f"Lowest completes valuation: ${min_completes_val:,.0f}")
        lines.append("")

        # Find ambiguous/does_not_complete permits >= min_completes
        overlapping_ambiguous = [v for v in ambiguous_vals if v[2] >= min_completes_val]
        overlapping_does_not = [v for v in does_not_vals if v[2] >= min_completes_val]

        if overlapping_ambiguous or overlapping_does_not:
            lines.append(f"Non-completes with valuation >= ${min_completes_val:,}:")
            for pid, pnum, val, desc in sorted(overlapping_ambiguous + overlapping_does_not, key=lambda x: -x[2]):
                bucket = 'ambiguous' if (pid, pnum, val, desc) in overlapping_ambiguous else 'does_not_complete'
                lines.append(f"  {bucket}: {pnum} (${val:,.0f}) - {desc}")
            lines.append("")
        else:
            lines.append(f"No ambiguous or does_not_complete permits with valuation >= ${min_completes_val:,}")
            lines.append("")

    if does_not_vals:
        max_does_not_val = max(v[2] for v in does_not_vals)
        lines.append(f"Highest does_not_complete valuation: ${max_does_not_val:,.0f}")
        lines.append("")

        # Find completes permits < max_does_not
        overlapping_completes = [v for v in completes_vals if v[2] < max_does_not_val]

        if overlapping_completes:
            lines.append(f"Completes with valuation < ${max_does_not_val:,}:")
            for pid, pnum, val, desc in sorted(overlapping_completes, key=lambda x: x[2]):
                lines.append(f"  completes: {pnum} (${val:,.0f}) - {desc}")
            lines.append("")
        else:
            lines.append(f"No completes permits with valuation < ${max_does_not_val:,}")
            lines.append("")

    lines.append("=" * 80)
    lines.append("END OF ANALYSIS")
    lines.append("=" * 80)

    conn.close()

    output_text = '\n'.join(lines)
    with open(OUTPUT_FILE, 'w') as f:
        f.write(output_text)

    print(output_text)
    print(f"\nWritten to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
