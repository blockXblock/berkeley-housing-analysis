#!/usr/bin/env python3
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
    q = """SELECT DISTINCT pa.apn_normalized, f.total_units
           FROM v_projects_flat f
           JOIN project_parcels pp ON pp.project_id = f.project_id
           JOIN parcels pa ON pa.id = pp.parcel_id
           WHERE f.co_issued_date LIKE ? AND pa.apn_normalized IS NOT NULL"""
    apns, units = set(), 0
    for apn, u in db.execute(q, (f"{year}%",)):
        c = canon(apn)
        if c:
            apns.add(c)
    units = db.execute("SELECT IFNULL(SUM(total_units),0) FROM v_projects_flat WHERE co_issued_date LIKE ?",
                       (f"{year}%",)).fetchone()[0]
    return apns, units


def oracle(year):
    db = ro(ORACLE)
    apns, units = set(), 0
    for row in db.execute("""SELECT APN, CO_ISSUE_DT1, YEAR,
                CO_ACUTELY_LOW_INCOME_DR, CO_ACUTELY_LOW_INCOME_NDR, CO_EXTREMELY_LOW_INCOME_DR,
                CO_EXTREMELY_INCOME_NDR, CO_VLOW_INCOME_DR, CO_VLOW_INCOME_NDR, CO_LOW_INCOME_DR,
                CO_LOW_INCOME_NDR, CO_MOD_INCOME_DR, CO_MOD_INCOME_NDR, CO_ABOVE_MOD_INCOME
                FROM table_a2"""):
        apn, dt, yr = row[0], str(row[1] or ""), str(row[2] or "")
        y = dt[:4] if dt[:4].isdigit() else yr[:4]
        if y != str(year):
            continue
        u = sum(n(x) for x in row[3:])
        if u <= 0 and not dt:
            continue
        units += u
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
        r = db.execute("""SELECT COUNT(*), IFNULL(SUM(total_units),0) FROM v_projects_flat
                          WHERE co_issued_date LIKE '2026%'""").fetchone()
        print(f"         {label}: {r[0]:>4} projects, {r[1]:>4} units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
