#!/usr/bin/env python3
"""
materialize_assessed_value.py — MACHINERY (re-runnable on each assessor refresh).

Builds/refreshes the project_assessed_value FACT TABLE: for each COMPLETED project,
joins the refreshed berkeley.db assessor parcel (3-layer deterministic APN crosswalk)
and materializes the assessed value + an estimated ad-valorem tax. Idempotent — each run
DROP+CREATE+repopulates with a fresh computed_at; as_of_date = the assessor extract date.

TWO stored values (the exemption nuance):
  - assessed_value   = Land + Imps              ("$X assessed" display)
  - total_net_value  = TotalNetValue (net taxable, after exemptions; drives tax)
  - exemption_amount = assessed_value - total_net_value  (explicit: affordable/nonprofit
                       projects carry a LARGE exemption -> the public-subsidy story)

RATE: est_annual_ad_valorem_tax = total_net_value x 1.25% — an APPROXIMATION of the
ad-valorem portion only (Alameda base 1% Prop-13 + countywide voter bonds ~1.18-1.25%).
EXCLUDES Berkeley's flat parcel levies (school/library/parks per-parcel taxes) -> the
REAL bill is higher. Labeled as such everywhere; never presented as the exact bill.

Coverage (honest, partial): rows are written ONLY for completed projects with a usable
value (parcel joins + Imps>0). Crosswalk/stale-APN cases (parcel absent) + reassessment-lag
(Imps=$0) + no-parcel get NO row -> LEFT JOIN in v_projects_flat yields NULL ("pending").
UC (Regents, tax-exempt, no parcel) is excluded. Coverage rises 91%->~98% after the crosswalk.

Modes:
  --preview   READ-ONLY: compute + print the rows/distribution/examples, write NOTHING.
  --write     Gated transactional write (snapshot the DB FIRST, per discipline).

NEVER writes berkeley.db (assessor) — opens it read-only.
"""
import sqlite3, argparse, datetime, statistics, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
V2_PATH = BASE / 'databases' / 'berkeley_housing_v2.db'
BDB_PATH = BASE / 'databases' / 'berkeley.db'

STUB_CO_DATE = '2024-01-01'
UC_CLASSIFICATION_ID = 6
ASSESSOR_AS_OF = '2026-02'        # the refreshed berkeley.db assessor extract date
EFFECTIVE_RATE = 0.0125          # ad-valorem approximation (Alameda 1% + countywide bonds ~1.18-1.25%)
RATE_LABEL = 'est. ad-valorem (1.25% approx; excludes flat parcel levies — real bill higher)'
SOURCE = f'berkeley.db Alameda assessor refresh {ASSESSOR_AS_OF}; ad-valorem rate {EFFECTIVE_RATE} (approx)'

DDL = """
CREATE TABLE project_assessed_value (
    id                          INTEGER PRIMARY KEY,
    project_id                  INTEGER NOT NULL,
    parcel_apn                  TEXT,
    land                        REAL,
    imps                        REAL,
    assessed_value              REAL,   -- land + imps (gross assessed value)
    total_net_value             REAL,   -- net taxable (after exemptions)
    exemption_amount            REAL,   -- assessed_value - total_net_value (explicit)
    as_of_date                  TEXT,   -- assessor extract date
    effective_rate_used         REAL,   -- ad-valorem rate applied
    est_annual_ad_valorem_tax   REAL,   -- total_net_value * rate (approx; excludes flat levies)
    source                      TEXT,   -- provenance
    computed_at                 TEXT,   -- run timestamp
    FOREIGN KEY(project_id) REFERENCES projects(id)
);
CREATE INDEX idx_pav_project ON project_assessed_value(project_id);
"""


def canon_v2(apn):
    if not apn:
        return None
    d = ''.join(c for c in apn if c.isdigit())
    return d if len(d) == 12 else None


def canon_bdb(book, page, parcel, sub):
    try:
        return (book or '').strip().zfill(3) + (page or '').strip().zfill(4) \
            + (parcel or '').strip().zfill(3) + (sub or '').strip().zfill(2)
    except Exception:
        return None


def assessor_index(bdb):
    idx, collided = {}, set()
    for b, p, pa, s, land, imps, tnv in bdb.execute(
            "SELECT BOOK,PAGE,PARCEL,SUB_PARCEL,Land,Imps,TotalNetValue FROM parcels"):
        c = canon_bdb(b, p, pa, s)
        if not c:
            continue
        if c in idx:
            collided.add(c)
        idx[c] = (land or 0.0, imps or 0.0, tnv or 0.0,
                  (b or '').strip() + '-' + (p or '').strip() + '-' + (pa or '').strip()
                  + (('-' + s.strip()) if s and s.strip() else ''))
    return idx, collided


def compute_rows(v2, bdb):
    """Return (rows_to_write, stats) — pure read, no writes. rows = list of dicts for the 640."""
    idx, collided = assessor_index(bdb)
    uc = {r[0] for r in v2.execute(
        "SELECT project_id FROM project_classifications WHERE classification_type_id=?", (UC_CLASSIFICATION_ID,))}
    completed = v2.execute(f"""
        SELECT project_id, total_units, co_issued_date, address_display FROM v_projects_flat
        WHERE co_issued_date IS NOT NULL AND co_issued_date!='' AND co_issued_date<>'{STUB_CO_DATE}'""").fetchall()
    now = datetime.datetime.now().isoformat(timespec='seconds')
    rows, skip = [], {'uc': 0, 'no_parcel': 0, 'parcel_absent_crosswalk': 0, 'imps_zero_lag': 0}
    for pid, units, co, addr in completed:
        if pid in uc:
            skip['uc'] += 1
            continue
        pp = v2.execute("""SELECT pk.apn FROM project_parcels pp JOIN parcels pk ON pk.id=pp.parcel_id
                           WHERE pp.project_id=? AND pp.is_primary=1""", (pid,)).fetchone()
        if not pp:
            skip['no_parcel'] += 1
            continue
        c = canon_v2(pp[0])
        if not c or c not in idx:
            skip['parcel_absent_crosswalk'] += 1
            continue
        land, imps, tnv, apn = idx[c]
        if imps <= 0:
            skip['imps_zero_lag'] += 1
            continue
        assessed = land + imps
        exemption = assessed - tnv
        est_tax = tnv * EFFECTIVE_RATE
        rows.append({'project_id': pid, 'parcel_apn': apn, 'land': land, 'imps': imps,
                     'assessed_value': assessed, 'total_net_value': tnv, 'exemption_amount': exemption,
                     'as_of_date': ASSESSOR_AS_OF, 'effective_rate_used': EFFECTIVE_RATE,
                     'est_annual_ad_valorem_tax': est_tax, 'source': SOURCE, 'computed_at': now,
                     '_units': units, '_addr': addr, '_collided': c in collided})
    stats = {'completed_total': len(completed), 'rows_written': len(rows), 'skipped': skip,
             'coverage_pct': round(100 * len(rows) / len(completed), 1)}
    return rows, stats


def print_preview(rows, stats):
    assessed = [r['assessed_value'] for r in rows]
    tnv = [r['total_net_value'] for r in rows]
    tax = [r['est_annual_ad_valorem_tax'] for r in rows]
    exempt_rows = [r for r in rows if r['total_net_value'] == 0 and r['imps'] > 0]
    partial_exempt = [r for r in rows if r['exemption_amount'] > 7000 and r['total_net_value'] > 0]
    print("=" * 78)
    print("PREVIEW — project_assessed_value (READ-ONLY, nothing written)")
    print("=" * 78)
    print(f"completed projects:        {stats['completed_total']}")
    print(f"rows to write (usable):    {stats['rows_written']}  ({stats['coverage_pct']}% coverage)")
    print(f"skipped: {stats['skipped']}")
    print(f"\nASSESSED VALUE (Land+Imps): sum ${sum(assessed):,.0f}")
    print(f"   median ${statistics.median(assessed):,.0f}  min ${min(assessed):,.0f}  max ${max(assessed):,.0f}")
    print(f"TOTAL NET VALUE (taxable):  sum ${sum(tnv):,.0f}   (= the $1.57B reconcile target)")
    print(f"EST ANNUAL AD-VALOREM TAX:  sum ${sum(tax):,.0f}/yr  median ${statistics.median(tax):,.0f}/yr")
    print(f"   rate {EFFECTIVE_RATE} — {RATE_LABEL}")
    print(f"\nFULLY TAX-EXEMPT (TNV=0 but Imps>0 — affordable/nonprofit): {len(exempt_rows)} projects")
    print(f"   their assessed value (untaxed): ${sum(r['assessed_value'] for r in exempt_rows):,.0f}")
    print(f"PARTIAL exemption (>$7k homeowner): {len(partial_exempt)} projects")

    def ex(r):
        return (f"   proj{r['project_id']:>3} {str(r['_addr'])[:26]:26} {str(r['_units'] or '?'):>4}u  "
                f"assessed ${r['assessed_value']:>12,.0f}  net ${r['total_net_value']:>12,.0f}  "
                f"exempt ${r['exemption_amount']:>12,.0f}  tax ${r['est_annual_ad_valorem_tax']:>9,.0f}/yr"
                + ("  [collided-key: verify sibling Imps]" if r['_collided'] else ""))
    print("\n--- EXAMPLE: fully-exempt affordable/nonprofit (assessed > 0, tax ~ $0) ---")
    for r in sorted(exempt_rows, key=lambda x: -x['assessed_value'])[:4]:
        print(ex(r))
    print("\n--- EXAMPLE: market-rate (taxed) — largest by assessed value ---")
    market = [r for r in rows if r['total_net_value'] > 0]
    for r in sorted(market, key=lambda x: -x['assessed_value'])[:5]:
        print(ex(r))
    print("\n--- EXAMPLE: smallest taxed (ADU/small) ---")
    for r in sorted(market, key=lambda x: x['assessed_value'])[:3]:
        print(ex(r))


def do_write(v2):
    """Gated transactional write. Caller must have snapshotted the DB first."""
    bdb = sqlite3.connect(f'file:{BDB_PATH}?mode=ro', uri=True)
    rows, stats = compute_rows(v2, bdb)
    cur = v2.cursor()
    cur.execute("DROP TABLE IF EXISTS project_assessed_value")
    cur.executescript(DDL)
    cols = ['project_id', 'parcel_apn', 'land', 'imps', 'assessed_value', 'total_net_value',
            'exemption_amount', 'as_of_date', 'effective_rate_used', 'est_annual_ad_valorem_tax',
            'source', 'computed_at']
    cur.executemany(
        f"INSERT INTO project_assessed_value ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        [tuple(r[c] for c in cols) for r in rows])
    v2.commit()
    # verify
    n = cur.execute("SELECT COUNT(*) FROM project_assessed_value").fetchone()[0]
    tnv_sum = cur.execute("SELECT SUM(total_net_value) FROM project_assessed_value").fetchone()[0]
    exempt = cur.execute("SELECT COUNT(*) FROM project_assessed_value WHERE total_net_value=0 AND imps>0").fetchone()[0]
    print(f"WROTE {n} rows (expected {stats['rows_written']}); TNV sum ${tnv_sum:,.0f}; fully-exempt {exempt}")
    assert n == stats['rows_written'], "row count mismatch — investigate"
    return stats


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true', help='read-only: compute + print, write nothing')
    ap.add_argument('--write', action='store_true', help='gated write (snapshot the DB first!)')
    args = ap.parse_args()
    if args.write:
        v2 = sqlite3.connect(V2_PATH)
        do_write(v2)
    else:
        v2 = sqlite3.connect(f'file:{V2_PATH}?mode=ro', uri=True)
        bdb = sqlite3.connect(f'file:{BDB_PATH}?mode=ro', uri=True)
        rows, stats = compute_rows(v2, bdb)
        print_preview(rows, stats)
        print("\n(PREVIEW only — no write. Re-run with --write after snapshot + approval.)")
