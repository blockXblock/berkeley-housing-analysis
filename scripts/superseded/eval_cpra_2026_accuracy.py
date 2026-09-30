#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-29 ============================
# DO NOT RUN. Original path: scripts/eval_cpra_2026_accuracy.py
# WHY: One-time evaluation of the 2026 CPRA v2 ingest, itself sequestered 2026-09-28.
raise SystemExit('SEQUESTERED 2026-09-29 -- see header; original path scripts/eval_cpra_2026_accuracy.py')
# ================================================================================
"""eval_cpra_2026_accuracy.py — did the 2026 CPRA ingest make v2 more accurate?

Measures v2's completion coverage against the HCD APR mirror, which is the **VERIFICATION TARGET
and never a data source** (CLAUDE.md rule 1). Nothing here feeds a classification or a derivation;
the oracle is only ever the thing we score ourselves against, because "the city's APR agrees with
us" would be circular if it had been an input.

Compares the pre-ingest snapshot with the live database, so the delta is attributable:
  before: databases/keep_snapshot_2026-09-25_pre-cpra-2026-ingest.db
  after : databases/berkeley_housing_v2.db
Oracle  : databases/hcd_apr_mirror.db, table_a2 (pulled 2026-05-26, covers through 2025)

Recall is measured on APNs, canonicalised through housing_rules.to_canonical_apn on both sides --
the assessor and the APR write APNs differently, and a bare strip-non-digits comparison is the
890/892-false-dead trap.

UC IS EXCLUDED, and leaving it out was a real error in the first version of this script. UC projects
sit in the total pipeline but are EXEMPT from city permitting and therefore from RHNA/APR counting
(CLAUDE.md; Anchor House FAQ, v2 documents id 2178). The first run scored 2024 at 1,466 units
against the oracle's 708 -- 207% -- and reported it as an unexplained discrepancy. It was not a
discrepancy: proj170, 1950 Oxford (Anchor House), carries 772 beds with a CO of 2024-08-21, and the
APR rightly omits it. Excluding UC the same way `generate_apr_v2.py` does gives 694 against 708.
The 2024 completion reconciliation was settled in 2026-06 at CY2024=709 / CY2025=532 / CY2026=216.
Filter on the uc_project CLASSIFICATION, never a hardcoded id.

The APR covers through 2025, so 2026 cannot be scored against it. That is stated, not papered over.

Read-only on every database.
"""
import collections
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from housing_rules import to_canonical_apn      # noqa: E402

BEFORE = ROOT / "databases/keep_snapshot_2026-09-25_pre-cpra-2026-ingest.db"
AFTER = ROOT / "databases/berkeley_housing_v2.db"
ORACLE = ROOT / "databases/hcd_apr_mirror.db"


UC_EXCLUDE = """project_id NOT IN (
    SELECT pc.project_id FROM project_classifications pc
    JOIN vocabulary_classification_types vct ON vct.id = pc.classification_type_id
    WHERE vct.code = 'uc_project')"""


def ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def canon(a):
    try:
        return to_canonical_apn(a, "alameda")
    except Exception:
        return None


def n(x):
    try:
        return int(float(x))
    except Exception:
        return 0


def ours(db, year):
    """APNs with a CO in `year`, and the unit total."""
    q = f"""SELECT DISTINCT pa.apn_normalized
            FROM v_projects_flat f
            JOIN project_parcels pp ON pp.project_id = f.project_id
            JOIN parcels pa ON pa.id = pp.parcel_id
            WHERE f.co_issued_date LIKE ? AND pa.apn_normalized IS NOT NULL
              AND f.{UC_EXCLUDE}"""
    apns = set()
    for (apn,) in db.execute(q, (f"{year}%",)):
        c = canon(apn)
        if c:
            apns.add(c)
    units = db.execute(
        f"""SELECT IFNULL(SUM(total_units),0) FROM v_projects_flat
            WHERE co_issued_date LIKE ? AND {UC_EXCLUDE}""", (f"{year}%",)).fetchone()[0]
    return apns, units


def oracle(year):
    """The oracle's own completion rows for `year`, de-duplicated.

    TWO TRAPS IN table_a2, both of which inflated the first version of this script:

    1. **The APR contains exact duplicate rows.** 2001 Ashby appears twice in 2025 with identical
       values (CO 2025-02-24, 1/80/6), and 2000 Dwight twice (CO 2025-06-17, 113). Summing rows
       double-counts them. We de-duplicate on (APN, CO date, unit vector). This is the same class
       of thing as the 2425 Durant cross-year double-count already recorded as a genuine city
       error in the Table A reconciliation.
    2. **A row's YEAR is not its completion year.** 268 rows carry YEAR=2025 with a BLANK
       CO_ISSUE_DT1 -- they are entitlement or building-permit rows, not completions. Falling back
       to YEAR when the CO date is blank pulled them in, which is why 121 of 128 supposedly
       "missing" 2025 APNs had zero units. A completion row must carry a real CO_ISSUE_DT1.
    """
    db = ro(ORACLE)
    seen, apns, units = set(), set(), 0
    for row in db.execute("""SELECT APN, CO_ISSUE_DT1,
                CO_ACUTELY_LOW_INCOME_DR, CO_ACUTELY_LOW_INCOME_NDR, CO_EXTREMELY_LOW_INCOME_DR,
                CO_EXTREMELY_INCOME_NDR, CO_VLOW_INCOME_DR, CO_VLOW_INCOME_NDR, CO_LOW_INCOME_DR,
                CO_LOW_INCOME_NDR, CO_MOD_INCOME_DR, CO_MOD_INCOME_NDR, CO_ABOVE_MOD_INCOME
                FROM table_a2"""):
        apn, dt = row[0], str(row[1] or "")
        if dt[:4] != str(year):          # a real CO date in the year, never the YEAR column
            continue
        key = (str(apn), dt, row[2:])
        if key in seen:                  # the APR's own duplicate rows
            continue
        seen.add(key)
        units += sum(n(x) for x in row[2:])
        c = canon(apn)
        if c:
            apns.add(c)
    return apns, units


def main() -> int:
    global AFTER
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--after", default=str(AFTER), help="database to score (default: live v2)")
    AFTER = Path(ap.parse_args().after)
    print(f"scoring: {AFTER.name}\n")
    print("Accuracy of v2 completions vs the HCD APR oracle (comparison target only)\n")
    for year in (2024, 2025):
        o_apn, o_units = oracle(year)
        rows = []
        for label, path in (("before ingest", BEFORE), ("after ingest ", AFTER)):
            a_apn, a_units = ours(ro(path), year)
            hit = len(a_apn & o_apn)
            rec = hit / len(o_apn) * 100 if o_apn else 0
            prec = hit / len(a_apn) * 100 if a_apn else 0
            rows.append((label, len(a_apn), a_units, hit, rec, prec))
        print(f"  {year} — oracle: {len(o_apn)} APNs, {o_units} units")
        print(f"    {'':<14} {'our APNs':>9} {'our units':>10} {'matched':>8} {'recall':>8} {'precision':>10}")
        for label, na, au, hit, rec, prec in rows:
            print(f"    {label:<14} {na:>9} {au:>10} {hit:>8} {rec:>7.1f}% {prec:>9.1f}%")
        d_rec = rows[1][4] - rows[0][4]
        d_units = rows[1][2] - rows[0][2]
        print(f"    delta: recall {d_rec:+.1f} pts · units {d_units:+} · "
              f"unit coverage {rows[1][2]/o_units*100:.1f}% of oracle\n")

    print("  2026 — the APR mirror was pulled 2026-05-26 and carries no 2026 completions,")
    print("         so 2026 CANNOT be scored against the oracle. v2's own 2026 figures moved")
    a = ro(AFTER); b = ro(BEFORE)
    for label, db in (("before", b), ("after ", a)):
        r = db.execute(f"""SELECT COUNT(*), IFNULL(SUM(total_units),0) FROM v_projects_flat
                           WHERE co_issued_date LIKE '2026%' AND {UC_EXCLUDE}""").fetchone()
        print(f"         {label}: {r[0]:>4} projects, {r[1]:>4} units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
