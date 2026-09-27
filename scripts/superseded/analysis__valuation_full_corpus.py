#!/usr/bin/env python3
"""
Valuation distribution across FULL permit corpus (all 240 permits)
===================================================================
Evaluates the $500K threshold across all permits, not just the 55
with evidentiary CO events. Identifies edge cases where valuation
alone is insufficient.

Read-only. Does NOT modify any files or database.
"""

import csv
import sqlite3
import sys
from pathlib import Path
from statistics import median, quantiles

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
from permit_role_classifier import classify_permit_for_completion

OUTPUT_DIR = Path(__file__).parent
CSV_OUTPUT = OUTPUT_DIR / 'valuation_full_corpus_all.csv'
BY_CLASSIFIER_OUTPUT = OUTPUT_DIR / 'valuation_full_corpus_by_classifier.txt'
THRESHOLD_OUTPUT = OUTPUT_DIR / 'valuation_threshold_sweep_full_corpus.txt'
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

    # Get vocabulary lookups
    permit_types = dict(cur.execute("SELECT id, code FROM vocabulary_permit_types").fetchall())
    permit_statuses = dict(cur.execute("SELECT id, code FROM vocabulary_permit_status_types").fetchall())

    # Get all permits with project info
    permits = cur.execute("""
        SELECT p.id AS permit_id, p.permit_number, p.permit_type_id,
               p.permit_status_type_id, p.valuation, p.source_system,
               p.description, p.project_id, proj.canonical_address AS project_address
        FROM permits p
        LEFT JOIN projects proj ON proj.id = p.project_id
        ORDER BY p.valuation DESC NULLS LAST
    """).fetchall()

    # Classify each permit
    all_permits = []
    for p in permits:
        desc = p['description']
        classifier_vote = classify_permit_for_completion(desc)
        permit_type_name = permit_types.get(p['permit_type_id'], 'unknown')

        all_permits.append({
            'permit_id': p['permit_id'],
            'permit_number': p['permit_number'],
            'permit_type_id': p['permit_type_id'],
            'permit_type_name': permit_type_name,
            'permit_status_type_id': p['permit_status_type_id'],
            'valuation': p['valuation'],
            'source_system': p['source_system'],
            'description': desc,
            'description_short': (desc[:80] if desc else ''),
            'project_id': p['project_id'],
            'project_address': p['project_address'],
            'classifier_vote': classifier_vote,
        })

    conn.close()

    # =========================================================================
    # OUTPUT 1: CSV of all 240 permits
    # =========================================================================
    csv_columns = [
        'permit_id', 'permit_number', 'permit_type_name', 'valuation',
        'source_system', 'classifier_vote', 'project_id', 'project_address',
        'description_short'
    ]
    with open(CSV_OUTPUT, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction='ignore')
        writer.writeheader()
        for p in all_permits:
            writer.writerow(p)

    # =========================================================================
    # OUTPUT 2: By classifier vote
    # =========================================================================
    buckets = {
        'completes_project': [],
        'ambiguous': [],
        'does_not_complete_project': [],
    }
    for p in all_permits:
        buckets[p['classifier_vote']].append(p)

    lines = []
    lines.append("=" * 100)
    lines.append("VALUATION DISTRIBUTION BY CLASSIFIER VOTE (ALL 240 PERMITS)")
    lines.append("=" * 100)
    lines.append("")
    lines.append(f"Total permits: {len(all_permits)}")
    for vote, items in buckets.items():
        lines.append(f"  {vote}: {len(items)}")
    lines.append("")

    for vote in ['completes_project', 'does_not_complete_project', 'ambiguous']:
        items = buckets[vote]
        # Sort by valuation desc
        items_sorted = sorted(items, key=lambda x: (x['valuation'] is None, -(x['valuation'] or 0)))

        lines.append("=" * 100)
        lines.append(f"=== {vote.upper()} ({len(items)} permits) ===")
        lines.append("=" * 100)
        lines.append("")

        # Header
        lines.append(f"{'id':<6} | {'permit_number':<14} | {'valuation':>14} | {'type':<16} | {'source':<8} | description (80 chars)")
        lines.append("-" * 140)

        valuations = []
        zero_count = 0
        null_count = 0

        for p in items_sorted:
            val = p['valuation']
            if val is None:
                null_count += 1
                val_str = 'NULL'
            else:
                valuations.append(val)
                if val == 0:
                    zero_count += 1
                val_str = f"${val:,.0f}"

            lines.append(f"{p['permit_id']:<6} | {p['permit_number'] or 'NULL':<14} | {val_str:>14} | {p['permit_type_name']:<16} | {p['source_system']:<8} | {p['description_short']}")

        lines.append("")
        lines.append("Summary stats:")
        lines.append(f"  count:          {len(items)}")
        if valuations:
            min_v, p25, med, p75, max_v = get_percentiles(valuations)
            lines.append(f"  valuation min:    ${min_v:,.0f}")
            lines.append(f"  valuation 25%:    ${p25:,.0f}")
            lines.append(f"  valuation median: ${med:,.0f}")
            lines.append(f"  valuation 75%:    ${p75:,.0f}")
            lines.append(f"  valuation max:    ${max_v:,.0f}")
        else:
            lines.append(f"  valuation:        (no numeric values)")
        lines.append(f"  valuation == 0:   {zero_count} ({100*zero_count/len(items):.1f}%)")
        lines.append(f"  valuation NULL:   {null_count} ({100*null_count/len(items):.1f}%)")
        lines.append("")

    with open(BY_CLASSIFIER_OUTPUT, 'w') as f:
        f.write('\n'.join(lines))

    # =========================================================================
    # OUTPUT 3: Threshold sweep + risk zones
    # =========================================================================
    tlines = []
    tlines.append("=" * 100)
    tlines.append("VALUATION THRESHOLD SWEEP (ALL 240 PERMITS)")
    tlines.append("=" * 100)
    tlines.append("")

    thresholds = [50000, 100000, 250000, 500000, 1000000, 2000000, 5000000]

    for threshold in thresholds:
        above = [p for p in all_permits if p['valuation'] is not None and p['valuation'] >= threshold]
        completes_above = [p for p in above if p['classifier_vote'] == 'completes_project']
        ambiguous_above = [p for p in above if p['classifier_vote'] == 'ambiguous']
        does_not_above = [p for p in above if p['classifier_vote'] == 'does_not_complete_project']

        tlines.append(f"Threshold ${threshold:,}:")
        tlines.append(f"  permits >= threshold: {len(above)} of {len(all_permits)}")
        tlines.append(f"    - classifier_vote = completes_project:         {len(completes_above)}")
        tlines.append(f"    - classifier_vote = ambiguous:                 {len(ambiguous_above)}")
        tlines.append(f"    - classifier_vote = does_not_complete_project: {len(does_not_above)}")
        tlines.append("")

    # Risk zone: $100K - $500K
    tlines.append("=" * 100)
    tlines.append("RISK ZONE: Permits with valuation between $100K and $500K")
    tlines.append("(Valuation alone is ambiguous; classifier must do real work)")
    tlines.append("=" * 100)
    tlines.append("")

    risk_zone = [p for p in all_permits
                 if p['valuation'] is not None and 100000 <= p['valuation'] < 500000]
    risk_zone_sorted = sorted(risk_zone, key=lambda x: -x['valuation'])

    tlines.append(f"{'id':<6} | {'valuation':>12} | {'classifier_vote':<28} | {'type':<16} | description (80 chars)")
    tlines.append("-" * 140)
    for p in risk_zone_sorted:
        tlines.append(f"{p['permit_id']:<6} | ${p['valuation']:>10,.0f} | {p['classifier_vote']:<28} | {p['permit_type_name']:<16} | {p['description_short']}")

    tlines.append("")
    tlines.append(f"Risk zone count: {len(risk_zone)}")
    by_vote = {}
    for p in risk_zone:
        by_vote[p['classifier_vote']] = by_vote.get(p['classifier_vote'], 0) + 1
    for vote, cnt in sorted(by_vote.items()):
        tlines.append(f"  {vote}: {cnt}")
    tlines.append("")

    # Critical: completes with valuation < $500K
    tlines.append("=" * 100)
    tlines.append("CRITICAL: Permits with classifier_vote = 'completes_project' but valuation < $500K")
    tlines.append("(These would be MISCLASSIFIED by a pure $500K-threshold rule)")
    tlines.append("=" * 100)
    tlines.append("")

    completes_low = [p for p in all_permits
                     if p['classifier_vote'] == 'completes_project'
                     and (p['valuation'] is None or p['valuation'] < 500000)]
    completes_low_sorted = sorted(completes_low, key=lambda x: (x['valuation'] is None, -(x['valuation'] or 0)))

    if completes_low_sorted:
        tlines.append(f"{'id':<6} | {'permit_number':<14} | {'valuation':>12} | {'type':<16} | {'address':<30} | description")
        tlines.append("-" * 160)
        for p in completes_low_sorted:
            val_str = f"${p['valuation']:,.0f}" if p['valuation'] is not None else 'NULL'
            addr = (p['project_address'] or '')[:30]
            desc = p['description_short']
            tlines.append(f"{p['permit_id']:<6} | {p['permit_number'] or 'NULL':<14} | {val_str:>12} | {p['permit_type_name']:<16} | {addr:<30} | {desc}")
        tlines.append("")
        tlines.append(f"Total: {len(completes_low_sorted)} permits would be misclassified by $500K threshold alone")
    else:
        tlines.append("None found. $500K threshold would correctly classify all completes_project permits.")
    tlines.append("")

    # High-value non-completes
    tlines.append("=" * 100)
    tlines.append("ANOMALY: Permits with valuation >= $500K but classifier_vote != 'completes_project'")
    tlines.append("(Valuation says 'major construction' but classifier disagrees)")
    tlines.append("=" * 100)
    tlines.append("")

    high_val_non_completes = [p for p in all_permits
                              if p['valuation'] is not None and p['valuation'] >= 500000
                              and p['classifier_vote'] != 'completes_project']
    high_val_sorted = sorted(high_val_non_completes, key=lambda x: -x['valuation'])

    if high_val_sorted:
        tlines.append(f"{'id':<6} | {'permit_number':<14} | {'valuation':>12} | {'classifier_vote':<28} | {'type':<16} | description")
        tlines.append("-" * 160)
        for p in high_val_sorted:
            desc = p['description_short']
            tlines.append(f"{p['permit_id']:<6} | {p['permit_number'] or 'NULL':<14} | ${p['valuation']:>10,.0f} | {p['classifier_vote']:<28} | {p['permit_type_name']:<16} | {desc}")
        tlines.append("")
        tlines.append(f"Total: {len(high_val_sorted)} permits have high valuation but classifier says non-completes")
    else:
        tlines.append("None found. All permits >= $500K are classified as completes_project.")
    tlines.append("")

    tlines.append("=" * 100)
    tlines.append("END OF THRESHOLD ANALYSIS")
    tlines.append("=" * 100)

    with open(THRESHOLD_OUTPUT, 'w') as f:
        f.write('\n'.join(tlines))

    print(f"Written {len(all_permits)} permits to: {CSV_OUTPUT}")
    print(f"Written by-classifier breakdown to: {BY_CLASSIFIER_OUTPUT}")
    print(f"Written threshold sweep to: {THRESHOLD_OUTPUT}")


if __name__ == '__main__':
    main()
