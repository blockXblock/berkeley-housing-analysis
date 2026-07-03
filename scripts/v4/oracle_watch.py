"""Oracle-watch methods — the machinery behind JN-G (the revision watcher).

Watches the city's state filing (CKAN table_a2) for revisions and runs the five mechanical
city-error detectors discovered by the 2026-07-03 no-candidate batch. ORACLE DISCIPLINE: everything
here COMPARES; nothing ever flows into a derived count (the watcher's output is findings, watch-item
status, and dated snapshots — never data).

Importable home (aa6ded0 discipline): JN-G's cells call these; a scheduled job can too.
Snapshots: data/ckan_snapshots/table_a2_<YYYY-MM-DD>.csv (append-only dated files; the diff runs
against the newest prior snapshot). Watch items: corrections/v4/watch_items.json (calibration —
expected upstream changes with their resolution meaning).
"""
import glob
import io
import json
import os
import sqlite3
from datetime import date

import pandas as pd

ROOT = os.path.expanduser('~/berkeley-data')
SNAP_DIR = os.path.join(ROOT, 'data', 'ckan_snapshots')
V4 = os.path.join(ROOT, 'databases', 'berkeley_housing_v4.db')
# the state's live resource (the mirror-era direct-download URL 404s as of 2026-07-03; the
# datastore_search API with a jurisdiction filter is the durable, light path)
CKAN_A2_RESOURCE = 'fe505d9b-8c36-42ba-ba30-08bc4f34e022'
CKAN_A2_API = 'https://data.ca.gov/api/3/action/datastore_search' 
KEY_COLS = ['YEAR', 'APN', 'STREET_ADDRESS', 'JURS_TRACKING_ID']


def _co_cols(df):
    return [c for c in df.columns if c.startswith('CO_') and 'DT' not in c]


def _with_co(df):
    d = df.copy()
    for c in _co_cols(d):
        d[c] = pd.to_numeric(d[c], errors='coerce').fillna(0)
    d['co_units'] = d[_co_cols(df)].sum(axis=1)
    return d


def pull_live_a2(timeout=60, page=5000):
    """Fetch the live CKAN table_a2 for Berkeley (filtered, paginated datastore_search).
    Returns a DataFrame or raises (caller may fall back to the newest snapshot when offline)."""
    import urllib.request
    import urllib.parse
    rows = []
    # the datastore's JURIS_NAME casing has drifted historically ('Berkeley' mirror-era,
    # 'BERKELEY' live 2026-07) — filters are exact-match, so try the known spellings
    for spelling in ('BERKELEY', 'Berkeley'):
        rows, offset = [], 0
        while True:
            q = urllib.parse.urlencode({'resource_id': CKAN_A2_RESOURCE, 'limit': page, 'offset': offset,
                                        'filters': json.dumps({'JURIS_NAME': spelling})})
            with urllib.request.urlopen(f'{CKAN_A2_API}?{q}', timeout=timeout) as r:
                payload = json.loads(r.read())
            assert payload.get('success'), f'CKAN API error: {str(payload)[:200]}'
            recs = payload['result']['records']
            rows.extend(recs)
            if len(recs) < page:
                break
            offset += page
        if rows:
            break
    df = pd.DataFrame(rows)
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    assert len(df) > 500, f'suspiciously few Berkeley rows ({len(df)}) — endpoint or filter drift?'
    return df


def snapshot(df, as_of=None):
    """Write the dated snapshot (append-only: refuses to overwrite an existing date's file with
    DIFFERENT content; identical re-runs are no-ops). Returns the path."""
    as_of = as_of or date.today().isoformat()
    os.makedirs(SNAP_DIR, exist_ok=True)
    path = os.path.join(SNAP_DIR, f'table_a2_{as_of}.csv')
    if os.path.exists(path):
        old = open(path).read()
        buf = io.StringIO(); df.to_csv(buf, index=False)
        if old == buf.getvalue():
            return path
        raise FileExistsError(f'{path} exists with different content — snapshots are append-only; '
                              f'a same-day upstream change deserves its own timestamped name')
    df.to_csv(path, index=False)
    return path


def prior_snapshot(before=None):
    """Newest snapshot path strictly before `before` (a date-iso string), or None."""
    snaps = sorted(glob.glob(os.path.join(SNAP_DIR, 'table_a2_*.csv')))
    if before:
        snaps = [s for s in snaps if s < os.path.join(SNAP_DIR, f'table_a2_{before}.csv')]
    return snaps[-1] if snaps else None


def diff_snapshots(old_df, new_df):
    """Row-level diff on the key columns + CO totals. Returns dict(added, removed, changed) of
    DataFrames — added/removed are full rows; changed carries both sides' CO."""
    o, n = _with_co(old_df), _with_co(new_df)
    for d in (o, n):
        # normalize the key fields: CSV round-trips give 'nan' where API JSON gives 'None' —
        # without this, every null-keyed row false-diffs as added+removed (caught on first run)
        k = d[KEY_COLS].astype(str).apply(lambda col: col.str.strip().str.upper()
                                          .replace({'NAN': '', 'NONE': '', '<NA>': ''}))
        d['_key'] = k.agg('|'.join, axis=1)
    og, ng = o.groupby('_key').co_units.sum(), n.groupby('_key').co_units.sum()
    added = n[~n._key.isin(og.index)]
    removed = o[~o._key.isin(ng.index)]
    common = og.index.intersection(ng.index)
    ch = pd.DataFrame({'old_co': og[common], 'new_co': ng[common]})
    changed = ch[ch.old_co != ch.new_co].reset_index()
    return {'added': added, 'removed': removed, 'changed': changed}


# ---------------------------------------------------------------- the five detectors
# Each returns a DataFrame of suspect rows. Validation anchors (the documented instances each
# MUST find when run over the 2026-06-17 mirror-era data) are noted per detector.
def detect_duplicate_rows(df):
    """(1) Full-row duplicates — the CY2025 double-submission class."""
    d = _with_co(df)
    cols = [c for c in d.columns if not c.startswith('_') and c != 'co_units']
    dup = d[d.duplicated(subset=cols, keep=False) & (d.co_units > 0)]
    return dup.sort_values(KEY_COLS)


def detect_cross_cy_recredit(df):
    """(2) Same tracking id with CO units in 2+ years — anchor: B2022-02049 (CY2023+CY2024)."""
    d = _with_co(df)
    d = d[(d.co_units > 0) & d.JURS_TRACKING_ID.astype(str).str.match(r'^B\d{4}-\d{4,5}')]
    g = d.groupby('JURS_TRACKING_ID').YEAR.nunique()
    return d[d.JURS_TRACKING_ID.isin(g[g > 1].index)].sort_values(['JURS_TRACKING_ID', 'YEAR'])


def detect_approval_as_co(df):
    """(3) Planning-record tracking id (ZP/UP/DR/AP/LM) on a CO-credited row — anchor: ZP2019-0022."""
    d = _with_co(df)
    return d[(d.co_units > 0) &
             d.JURS_TRACKING_ID.astype(str).str.match(r'^(ZP|UP|DR|AP|LM)\d{4}-\d+')]


def detect_co_at_issuance(df, v4_path=V4):
    """(4) CO date == the tracked permit's ISSUANCE date in the permit record, where a distinct
    later final exists — anchor: B2019-03765 (CY2020 'CO' 2020-01-28 = issuance)."""
    d = _with_co(df)
    d = d[(d.co_units > 0) & d.JURS_TRACKING_ID.astype(str).str.match(r'^B\d{4}-\d{4,5}$')]
    con = sqlite3.connect(f'file:{v4_path}?mode=ro', uri=True)
    dates = {}
    for sk in d.JURS_TRACKING_ID.unique():
        rows = dict(con.execute("""SELECT event_type_code, MIN(substr(event_date,1,10)) FROM events
            WHERE source_record_key=? AND event_type_code IN ('permit_issued','permit_finaled')
            GROUP BY event_type_code""", (sk,)).fetchall())
        dates[sk] = rows
    hits = []
    for _, r in d.iterrows():
        info = dates.get(r.JURS_TRACKING_ID, {})
        iss, fin = info.get('permit_issued'), info.get('permit_finaled')
        co = str(r.get('CO_ISSUE_DT1') or '')[:10]
        if iss and co == iss and fin and fin != iss:
            hits.append(r)
    return pd.DataFrame(hits)


def detect_meter_recredit(df, v4_path=V4):
    """(5) CO-credited tracking permit whose OWN description is utility/meter work referencing
    another permit — anchor: B2024-04912 ('add 2 new meters for ADUs... REF B2024-00819')."""
    import re
    d = _with_co(df)
    d = d[(d.co_units > 0) & d.JURS_TRACKING_ID.astype(str).str.match(r'^B\d{4}-\d{4,5}$')]
    con = sqlite3.connect(f'file:{v4_path}?mode=ro', uri=True)
    pat = re.compile(r'\b(meter|amp service|panel upgrade|service upgrade)\b.*\b(REF|reference|B\d{4}-\d{4,5})', re.I | re.S)
    hits = []
    for _, r in d.iterrows():
        wd = con.execute("SELECT json_extract(raw_payload,'$.WorkDescription') FROM events "
                         "WHERE source_record_key=? LIMIT 1", (r.JURS_TRACKING_ID,)).fetchone()
        if wd and wd[0] and pat.search(str(wd[0])):
            hits.append(r)
    return pd.DataFrame(hits)


def run_all_detectors(df, v4_path=V4):
    """All five, returned as {name: DataFrame}."""
    return {
        'duplicate_rows': detect_duplicate_rows(df),
        'cross_cy_recredit': detect_cross_cy_recredit(df),
        'approval_as_co': detect_approval_as_co(df),
        'co_at_issuance': detect_co_at_issuance(df, v4_path),
        'meter_recredit': detect_meter_recredit(df, v4_path),
    }


def check_watch_items(df, watch_path=os.path.join(ROOT, 'corrections', 'v4', 'watch_items.json')):
    """Evaluate the calibration watch-items against the current filing. Each item defines a
    match (APN prefix / tracking / address substring + co_units>0 in a YEAR range) and what its
    appearance MEANS. Returns [(item, fired?, matching_rows_count)]."""
    items = json.load(open(watch_path))['items']
    d = _with_co(df)
    out = []
    for it in items:
        m = d
        if it.get('apn_contains'):
            m = m[m.APN.astype(str).str.replace(r'[ -]', '', regex=True)
                   .str.contains(it['apn_contains'].replace('-', '').replace(' ', ''))]
        if it.get('tracking'):
            m = m[m.JURS_TRACKING_ID.astype(str) == it['tracking']]
        if it.get('address_contains'):
            m = m[m.STREET_ADDRESS.astype(str).str.upper().str.contains(it['address_contains'].upper())]
        m = m[m.co_units > 0]
        if it.get('year_min'):
            m = m[m.YEAR.astype(int) >= int(it['year_min'])]
        out.append((it, len(m) > 0, len(m)))
    return out
