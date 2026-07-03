"""Business-license snapshot watcher — the churn instrument for JN-Business-Health.

The city's open-data Business Licenses dataset (data.cityofberkeley.info, Socrata `rwnf-bu3w`)
is a POINT-IN-TIME roll of active licenses with NO date fields — so openings/closings/churn are
only observable as DIFFS BETWEEN DATED SNAPSHOTS. Every month without a snapshot is churn lost
forever; this module makes taking one a single command.

Pattern: oracle_watch.py (JN-G). Dated APPEND-ONLY snapshots in data/license_snapshots/; a run
pulls the live roll, snapshots it, diffs unique recordids vs the newest prior snapshot
(openings / closings / moved), and appends to data/audit/license_watch_log.csv.

Seed baseline: licenses_2025-11-15.csv (the Nov-2025 pull that also lives in berkeley.db.licenses).
Cadence: monthly (scheduled task); running more often is harmless (append-only, identical re-runs no-op).

⚠ ROLL SEMANTICS (calibrated 2026-07-03 on the first diff): recordids are STABLE business identities,
but PRESENCE in the roll = "license currently valid at pull time" — a business mid-renewal-lapse
drops out and reappears (AMOEBA MUSIC BL-000229 was absent from the entire Nov-2025 roll while
plainly operating). So a one-interval 'closed' is a SUSPECT, not a closure: the Nov->Jul diff shows
~1.8k opened / ~1.8k closed, dominated by renewal-cycle flicker. A CONFIRMED closure = absent for
K consecutive monthly snapshots (K>=3 spans any renewal grace window) — that persistence rule lives
in the JN analysis layer; this watcher stays mechanical and just records what the city said when.

Run:  /opt/miniconda3/envs/jupyter_env/bin/python scripts/v4/license_watch.py
"""
import csv
import glob
import io
import json
import os
import urllib.request
from datetime import date

import pandas as pd

ROOT = os.path.expanduser('~/berkeley-data')
SNAP_DIR = os.path.join(ROOT, 'data', 'license_snapshots')
LOG = os.path.join(ROOT, 'data', 'audit', 'license_watch_log.csv')
SODA = 'https://data.cityofberkeley.info/resource/rwnf-bu3w.json'
FIELDS = ['apn', 'recordid', 'busdesc', 'b1_per_sub_type', 'dba', 'naics', 'tax_code',
          'employee_num', 'bus_own_type', 'b1_business_name', 'b1_address1', 'b1_city',
          'b1_state', 'b1_zip', 'b1_contact_type', 'b1_full_address', 'b1_situs_city',
          'b1_situs_state', 'b1_situs_zip']


def pull_live(timeout=120, page=50000):
    """Fetch the full live roll (paginated SODA; $order for deterministic paging).
    Returns a DataFrame with FIELDS columns. Raises on failure — caller decides fallback."""
    rows, offset = [], 0
    while True:
        url = f'{SODA}?$limit={page}&$offset={offset}&$order=recordid'
        with urllib.request.urlopen(url, timeout=timeout) as r:
            recs = json.loads(r.read())
        rows.extend(recs)
        if len(recs) < page:
            break
        offset += page
    df = pd.DataFrame(rows)
    for c in FIELDS:                       # stable column set even if the portal omits empties
        if c not in df.columns:
            df[c] = None
    df = df[FIELDS]
    assert len(df) > 5000, f'suspiciously few licenses ({len(df)}) — endpoint or dataset drift?'
    return df


def snapshot(df, as_of=None):
    """Dated append-only snapshot (refuses to overwrite a same-day file with different content)."""
    as_of = as_of or date.today().isoformat()
    os.makedirs(SNAP_DIR, exist_ok=True)
    path = os.path.join(SNAP_DIR, f'licenses_{as_of}.csv')
    buf = io.StringIO(); df.to_csv(buf, index=False)
    if os.path.exists(path):
        if open(path).read() == buf.getvalue():
            return path
        raise FileExistsError(f'{path} exists with different content — snapshots are append-only')
    with open(path, 'w') as f:
        f.write(buf.getvalue())
    return path


def prior_snapshot(before=None):
    """Newest snapshot path strictly before `before` (date-iso), or None."""
    snaps = sorted(glob.glob(os.path.join(SNAP_DIR, 'licenses_*.csv')))
    if before:
        snaps = [s for s in snaps if s < os.path.join(SNAP_DIR, f'licenses_{before}.csv')]
    return snaps[-1] if snaps else None


def diff_snapshots(old_df, new_df):
    """Churn diff on unique recordid: openings (new ids), closings (gone ids), moved (same id,
    changed situs street address). Duplicate recordids within a snapshot are collapsed (first kept)."""
    o = old_df.drop_duplicates('recordid').set_index('recordid')
    n = new_df.drop_duplicates('recordid').set_index('recordid')
    opened = n.loc[sorted(set(n.index) - set(o.index))].reset_index()
    closed = o.loc[sorted(set(o.index) - set(n.index))].reset_index()
    common = sorted(set(o.index) & set(n.index))
    oa = o.loc[common, 'b1_full_address'].astype(str).str.strip().str.upper()
    na = n.loc[common, 'b1_full_address'].astype(str).str.strip().str.upper()
    moved_ids = oa[oa != na].index
    moved = pd.DataFrame({'recordid': moved_ids,
                          'old_address': oa[moved_ids], 'new_address': na[moved_ids],
                          'dba': n.loc[moved_ids, 'dba']}).reset_index(drop=True)
    return {'opened': opened, 'closed': closed, 'moved': moved}


def log_run(as_of, mode, rows, uniq, d):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    row = dict(run_date=as_of, mode=mode, rows=rows, unique_ids=uniq,
               opened=len(d['opened']) if d else '', closed=len(d['closed']) if d else '',
               moved=len(d['moved']) if d else '')
    exists = os.path.exists(LOG)
    with open(LOG, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            w.writeheader()
        w.writerow(row)
    return row


def run(as_of=None):
    """One watch cycle: pull -> snapshot -> diff vs prior -> log. Returns (snapshot_path, diff)."""
    as_of = as_of or date.today().isoformat()
    live = pull_live()
    path = snapshot(live, as_of=as_of)
    prior = prior_snapshot(before=as_of)
    d = None
    if prior:
        old = pd.read_csv(prior, dtype=str)
        d = diff_snapshots(old, live)
        print(f'{os.path.basename(prior)} -> {os.path.basename(path)}: '
              f'+{len(d["opened"])} opened  -{len(d["closed"])} closed  ~{len(d["moved"])} moved')
        for name in ('opened', 'closed'):
            for _, r in d[name].head(6).iterrows():
                print(f'  {name.upper():6} {r.recordid}  {str(r.dba)[:34]:34} {str(r.b1_full_address)[:34]}')
    else:
        print(f'first snapshot {os.path.basename(path)} — the diff begins next run')
    row = log_run(as_of, 'live', len(live), live['recordid'].nunique(), d)
    print('logged:', row)
    return path, d


if __name__ == '__main__':
    run()
