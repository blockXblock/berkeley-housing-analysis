#!/usr/bin/env python3
"""
build_jn_d.py — JN-D ENGINE: v4↔HCD ADU bijection, hardened, with independent oracles.

WHAT THIS IS
  The consolidated, gated, RE-RUNNABLE engine behind the JN-D build notebook. It runs the full
  verified arc from this session as one pipeline:
      bijection (HCD-anchored, 6 buckets)  ->  704 'under_other_role' split (3-axis)
      ->  hardening (the SETTLED JN-C classifier, not keywords)  ->  dedup + unit band
  and carries THREE independent oracles as columns on every HCD-ADU row:
      HCD (concordant) · Assessor Imps (independent admin) · Berkeley footprints (independent physical)
      + Address Points (independent admin, self-discovering join format)

DISCIPLINE
  - READ-ONLY on every database (mode=ro). Read-only on the GIS endpoints. The ONLY writes are
    output CSVs under OUTDIR. It STOPS at the relabel-queue CSV — it does NOT write event_classifications.
    The reversible relabel is a separate gated step, by design (it is the first thing that mutates v4).
  - LOOK, don't assume: footprint join format is confirmed (space-form PARCELID -> to_canonical_apn).
    Address-Points APN format was NOT confirmed this session, so it is DISCOVERED here (try formats on a
    known parcel, use what resolves) or flagged-null — never guessed.
  - VERIFIED-NUMBER GATES: the load-bearing counts from the piecewise runs are asserted and HALT on
    mismatch. If the consolidation drifts from the verified runs, this stops rather than ships a wrong number.
  - Numbers that are city/run-specific are EXPECTATIONS held as checks (warn), not structure imposed.

  CC: confirm the four path vars + the JN-C classifier callable name (printed below) before trusting output.
"""
import sqlite3, os, sys, re, json, time, urllib.request, urllib.parse
import pandas as pd

# ============================================================ CELL 1 — CONFIG (intent, not structure)
ROOT   = os.path.expanduser('~/berkeley-data')                 # CC: confirm
DB_DIR = os.path.join(ROOT, 'databases')
V4     = os.path.join(DB_DIR, 'berkeley_housing_v4.db')
HCD    = os.path.join(DB_DIR, 'hcd_apr_mirror_2026-06-17_fresh.db')   # deduped oracle
ASSESS = os.path.join(DB_DIR, 'berkeley.db')                          # Alameda assessor (Imps)
OUTDIR = os.path.join(ROOT, 'scratch', '2026-06-26', 'jn_d_out')      # CSV-only outputs (scratch until gated)
CACHE  = os.path.join(OUTDIR, '_oracle_cache')
os.makedirs(OUTDIR, exist_ok=True); os.makedirs(CACHE, exist_ok=True)

# independent-physical oracle: Berkeley building footprints (confirmed live this session)
GIS_FOOTPRINTS = ('https://gis.cityofberkeley.info/arcgis/rest/services/'
                  'Planning/Building_Safety/MapServer/7/query')
# independent-admin oracle: Alameda address points (format self-discovered below)
GIS_ADDRPOINTS = ('https://services5.arcgis.com/ROBnTHSNjoZ2Wm1P/arcgis/rest/services/'
                  'Address_Points/FeatureServer/0/query')   # CC: confirm service name if it 404s

# EXPECTATIONS held strictly as checks (from the verified piecewise runs) — gates that HALT are marked (HARD)
EXP = dict(hcd_anchor=842,            # (HARD) HCD ADU canonical APNs
           regr_adu_only=649,         # (HARD) ADU-flagged-only APN intersection
           match_any_role=839,        # (HARD) HCD APNs with any v4 permit
           missing=3,                  # v4-missing-entirely
           hardened_new_unit=584,     # (HARD) of the 977 keyword candidates, settled-classifier new_unit
           band_floor=531, band_ceiling=584,   # (HARD) unit band after dedup
           finaled=441, not_finaled=143,        # finaled/pending split of the 584
           known_footprint_parcel='060-2417-056-00', known_footprint_count=3)  # GIS sanity

def ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import housing_rules
def C(raw):
    try: return housing_rules.to_canonical_apn(raw, 'Alameda') or None
    except Exception: return None
def num(x):
    try: return int(float(x))
    except Exception: return None
def jv(x):
    try: return float(str(x).replace('$','').replace(',','').strip())
    except Exception: return None

print('=== JN-D ENGINE — config ===')
for k,v in [('ROOT',ROOT),('V4',V4),('HCD',HCD),('ASSESS',ASSESS),('OUTDIR',OUTDIR)]:
    print(f'  {k:7s} {v}   exists={os.path.exists(v) if k not in ("OUTDIR",) else True}')

# ============================================================ CELL 2 — small GIS helper (read-only, cached)
def _gis_get(url, params, cache_name, page=2000):
    """Paginated read-only ArcGIS query -> list of attribute dicts. Cached to disk; network errors non-fatal."""
    cache = os.path.join(CACHE, cache_name)
    if os.path.exists(cache):
        return json.load(open(cache))
    out, offset = [], 0
    try:
        while True:
            q = dict(params); q.update(resultOffset=offset, resultRecordCount=page, f='json')
            req = urllib.request.Request(url + '?' + urllib.parse.urlencode(q),
                                         headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            feats = d.get('features', [])
            out += [f['attributes'] for f in feats]
            if len(feats) < page or not d.get('exceededTransferLimit', False):
                if len(feats) < page: break
            offset += page
            if offset > 200000: break   # safety
            time.sleep(0.2)
        json.dump(out, open(cache, 'w'))
        return out
    except Exception as e:
        print(f'  ⚠ GIS oracle unavailable ({cache_name}): {e} — column will be flagged unavailable, core bijection still runs')
        return None

# ============================================================ CELL 3 — HCD ADU oracle (anchor = 842)
hc = ro(HCD)
a2cols = [c[1] for c in hc.execute('pragma table_info(table_a2)')]
ucol = next((c for c in a2cols if 'unit' in c.lower() and 'cat' not in c.lower() and 'tot' in c.lower()), None)
sel = 'APN, STD_ADDRESS, YEAR' + (f', "{ucol}"' if ucol else '')
hcd = pd.read_sql(f"select {sel} from table_a2 where upper(coalesce(UNIT_CAT,''))='ADU'", hc)
hcd['apn_canon'] = hcd['APN'].map(C)
hcd_noncanon = int(hcd['apn_canon'].isna().sum())
hcd = hcd.dropna(subset=['apn_canon'])
hcd_g = (hcd.groupby('apn_canon')
            .agg(hcd_addresses=('STD_ADDRESS', lambda s: ' | '.join(sorted({str(x) for x in s if str(x).strip()}))),
                 hcd_years=('YEAR', lambda s: ','.join(sorted({str(int(x)) for x in s if pd.notna(x)}))),
                 hcd_adu_rows=('APN', 'size')).reset_index())
HCD_APN = set(hcd_g['apn_canon']); NHCD = len(HCD_APN)
print(f'\n[oracle 1/HCD] ADU canonical APNs (anchor): {NHCD}  (non-canon dropped {hcd_noncanon})')
assert NHCD == EXP['hcd_anchor'], f'(HARD) HCD anchor drift: {NHCD} != {EXP["hcd_anchor"]}'

# ============================================================ CELL 4 — v4 permit-grain evidence
ev = pd.read_sql("""
  select e.source_record_key skey, e.raw_apn,
         json_extract(e.raw_payload,'$.WorkDescription') wd,
         json_extract(e.raw_payload,'$.Work Type')       wt,
         json_extract(e.raw_payload,'$.ADU')             adu,
         json_extract(e.raw_payload,'$.OccType')         occ,
         json_extract(e.raw_payload,'$.Detached')        det,
         json_extract(e.raw_payload,'$.UnitsAdded')      ua,
         json_extract(e.raw_payload,'$.UnitsRemoved')    ur,
         json_extract(e.raw_payload,'$.JobValuation')    jval,
         e.event_type_code etc, e.event_date occ_at,     -- events date column is event_date (verified pragma)
         ec.housing_role role
  from events e left join event_classifications ec on ec.event_id = e.event_id
""", ro(V4))
ev['adu_yes'] = ev['adu'].eq('Yes')
ev['finaled'] = ev['etc'].eq('permit_finaled')
ev['apn_canon'] = ev['raw_apn'].map(C)
ev['jval_n'] = ev['jval'].map(jv)

def collapse_permit(g):
    apns  = [a for a in (C(x) for x in g['raw_apn'].dropna().unique()) if a]
    roles = [r for r in g['role'].dropna().unique()]
    fy = g.loc[g['finaled'], 'occ_at'].dropna()
    return pd.Series({
        'apn_canon': apns[0] if apns else None,
        'apn_multi': len(set(apns)) > 1,
        'role': roles[0] if len(roles) == 1 else ('MIXED:'+'/'.join(sorted(roles)) if roles else None),
        'adu_yes': bool(g['adu_yes'].any()),
        'finaled': bool(g['finaled'].any()),
        'fin_year': (str(fy.min())[:4] if len(fy) else None),
        'v4_units': num(g['ua'].dropna().iloc[0]) if g['ua'].dropna().size else None,
        'jval_n': (g['jval_n'].dropna().iloc[0] if g['jval_n'].dropna().size else None),
        'wd': (g['wd'].dropna().iloc[0] if g['wd'].dropna().size else ''),
        'wt': (g['wt'].dropna().iloc[0] if g['wt'].dropna().size else ''),
        'occ': (g['occ'].dropna().iloc[0] if g['occ'].dropna().size else ''),
        'det': (g['det'].dropna().iloc[0] if g['det'].dropna().size else ''),
        'adu_raw': (g['adu'].dropna().iloc[0] if g['adu'].dropna().size else None),  # raw ADU flag for classify
        'ur': (g['ur'].dropna().iloc[0] if g['ur'].dropna().size else None)})        # UnitsRemoved for classify
perm = ev.groupby('skey').apply(collapse_permit, include_groups=False).reset_index()
print(f'[v4] permits: {len(perm)}   ADU=Yes permits: {int(perm.adu_yes.sum())}')

# ============================================================ CELL 5 — Assessor Imps oracle (independent admin)
ac = [c[1] for c in ro(ASSESS).execute('pragma table_info(parcels)')]
acol = 'APN'  if 'APN'  in ac else next((c for c in ac if 'apn'  in c.lower()), None)
icol = 'Imps' if 'Imps' in ac else next((c for c in ac if c.lower() in ('imps','improvements','improvement_value')), None)
imps = {}
if icol:
    for a, v in ro(ASSESS).execute(f'select "{acol}","{icol}" from parcels'):
        ca = C(a)
        if ca:
            try: imps[ca] = float(str(v).replace('$','').replace(',',''))
            except Exception: pass
print(f'[oracle 2/Assessor] Imps populated for {len(imps)} canonical APNs (col={icol})')

# ============================================================ CELL 6 — Berkeley footprints (independent physical)
fp_rows = _gis_get(GIS_FOOTPRINTS, dict(where='1=1', outFields='PARCELID', returnGeometry='false'),
                   'footprints.json')
fp_count = {}
if fp_rows is not None:
    for r in fp_rows:
        ca = C(r.get('PARCELID'))
        if ca: fp_count[ca] = fp_count.get(ca, 0) + 1
    sanity = fp_count.get(EXP['known_footprint_parcel'])
    print(f'[oracle 3/footprints] {len(fp_rows)} outlines over {len(fp_count)} parcels; '
          f'sanity {EXP["known_footprint_parcel"]} -> {sanity} (expect {EXP["known_footprint_count"]})')
    if sanity != EXP['known_footprint_count']:
        print('  ⚠ footprint sanity mismatch — check PARCELID canonicalization before trusting this column')
else:
    print('[oracle 3/footprints] UNAVAILABLE — column flagged')

# ============================================================ CELL 7 — Address Points (self-discovering join format)
def discover_addrpoint_format():
    """LOOK don't assume: find which APN string format the address-point layer joins on, using one known parcel."""
    probe_canon = EXP['known_footprint_parcel']                 # 060-2417-056-00
    raw_space   = probe_canon.replace('-', ' ')[:3] + ' ' + probe_canon.replace('-', '')[3:]  # best-effort space form
    candidates = [probe_canon, probe_canon.replace('-', ''), raw_space, raw_space.replace(' ', '')]
    for fmt in candidates:
        rows = _gis_get(GIS_ADDRPOINTS, dict(where=f"APN='{fmt}'", outFields='APN', returnGeometry='false'),
                        f'addr_probe_{abs(hash(fmt))%9999}.json', page=50)
        if rows:
            print(f'[oracle 4/addrpoints] join format resolved: APN like {fmt!r} ({len(rows)} pts on probe parcel)')
            return fmt, True
    print('[oracle 4/addrpoints] could NOT resolve APN format on the probe parcel — column flagged null (not guessed)')
    return None, False

ap_count = {}
ap_fmt, ap_ok = discover_addrpoint_format()
if ap_ok:
    # pull address points for our HCD-ADU APNs in batches, in the resolved format
    def to_fmt(canon):
        return {'060-2417-056-00': canon,
                '0602417056 00': canon.replace('-', '')}.get('x', None) or (
                canon if '-' in ap_fmt else canon.replace('-', ''))
    apns = sorted(HCD_APN)
    for i in range(0, len(apns), 100):
        batch = apns[i:i+100]
        inlist = ','.join("'" + (a if '-' in ap_fmt else a.replace('-','')) + "'" for a in batch)
        rows = _gis_get(GIS_ADDRPOINTS, dict(where=f'APN IN ({inlist})', outFields='APN', returnGeometry='false'),
                        f'addr_batch_{i}.json')
        if rows:
            for r in rows:
                ca = C(r.get('APN'))
                if ca: ap_count[ca] = ap_count.get(ca, 0) + 1
    print(f'[oracle 4/addrpoints] address-point counts for {len(ap_count)} of {NHCD} HCD-ADU APNs')

# ============================================================ CELL 8 — bijection (HCD-anchored, exploded, 6 buckets)
m = hcd_g.merge(perm, on='apn_canon', how='left')

# regression: ADU-flagged-only intersection must still be 649 (HARD)
v4_adu_apn = set(perm.loc[perm.adu_yes & perm.apn_canon.notna(), 'apn_canon'])
inter_adu  = len(v4_adu_apn & HCD_APN)
assert inter_adu == EXP['regr_adu_only'], f'(HARD) regression drift: {inter_adu} != {EXP["regr_adu_only"]}'

def bucket(r):
    if pd.isna(r['skey']):                 return 'v4_missing_entirely'
    role, adu, fin = r['role'], r['adu_yes'], r['finaled']
    if adu:
        if role == 'new_unit':  return 'agree' if fin else 'v4_new_not_finaled'
        if role == 'ambiguous': return 'v4_ambiguous_finaled' if fin else 'v4_ambiguous_pending'
        return 'v4_adu_flag_nonhousing_role'
    return 'v4_under_other_role'
m['bucket'] = m.apply(bucket, axis=1)

# attach the oracle columns on every HCD-ADU row
m['oracle_imps']        = m['apn_canon'].map(imps.get)
m['oracle_footprints']  = m['apn_canon'].map(lambda a: fp_count.get(a)) if fp_rows is not None else 'unavailable'
m['oracle_addrpoints']  = m['apn_canon'].map(lambda a: ap_count.get(a)) if ap_ok else 'unavailable'

# conservation gates
apns_with_permit = set(m.loc[m.skey.notna(), 'apn_canon'])
apns_missing     = set(m.loc[m.bucket == 'v4_missing_entirely', 'apn_canon'])
assert apns_with_permit | apns_missing == HCD_APN, 'APN partition leak'
assert not (apns_with_permit & apns_missing),       'APN in both matched and missing'
assert set(m['apn_canon']) == HCD_APN,              'HCD APN lost from output'
assert len(apns_with_permit) == EXP['match_any_role'], \
    f'(HARD) match drift: {len(apns_with_permit)} != {EXP["match_any_role"]}'
print(f'\n[bijection] match {len(apns_with_permit)}/{NHCD} = {len(apns_with_permit)/NHCD:.1%} · '
      f'missing {len(apns_missing)} · ADU-flagged-only {inter_adu}')

# inverse finding (NOT in the HCD-anchored CSV; tightest scope: confident new_unit + finaled + ADU not in HCD)
inv = perm[(perm.role=='new_unit') & perm.finaled & perm.adu_yes &
           perm.apn_canon.notna() & ~perm.apn_canon.isin(HCD_APN)]

# ============================================================ CELL 9 — calibrate valuation on the 446 agree-ADUs
agree_apns = set(m.loc[m.bucket=='agree', 'apn_canon'])
cal = perm[perm.apn_canon.isin(agree_apns) & perm.finaled]
def band(vals):
    v = sorted(x for x in vals if x and x > 0); n = len(v)
    if not n: return None
    q = lambda p: v[min(n-1, int(p*n))]
    return dict(n=n, p10=q(.10), p25=q(.25), median=q(.5), p75=q(.75), p90=q(.90))
jv_band   = band(cal['jval_n']); imps_band = band(cal['apn_canon'].map(imps.get))
JV_FLOOR  = jv_band['p10']   if jv_band   else None     # soft positive tiebreaker (low value does NOT exclude)
IMPS_REF  = imps_band['p25'] if imps_band else None
print(f'[calibration] JobValuation {jv_band}\n              Imps         {imps_band}\n'
      f'              soft JV_FLOOR={JV_FLOOR}  IMPS_REF={IMPS_REF}  (positive tiebreakers; description gates)')

# ============================================================ CELL 10 — split the 704 under_other_role (3-axis)
ADU_LANG = ['adu','accessory dwelling','accessory unit','granny','in-law','junior adu','jadu',
            'convert','conversion','legaliz','address assignment']
def desc_corrob(wd): s=(wd or '').lower(); return any(k in s for k in ADU_LANG)
u704_apns = set(m.loc[m.bucket=='v4_under_other_role', 'apn_canon'])
cand = perm[perm.apn_canon.isin(u704_apns)].copy()
cand['imps'] = cand['apn_canon'].map(imps.get)
def tier(r):
    if desc_corrob(r['wd']):                                   return 'relabel_candidate'
    terse = (not (r['wd'] or '').strip()) or len((r['wd'] or '').split()) <= 3
    form  = (str(r['det']).lower()=='yes') or str(r['occ']).upper().startswith('R-3') \
            or (r['jval_n'] and JV_FLOOR and r['jval_n']>=JV_FLOOR) \
            or (r['imps'] and IMPS_REF and r['imps']>=IMPS_REF)
    if terse and form: return 'harvest_terse_but_form_supports'
    if terse:          return 'harvest_terse'
    return 'genuine_other_permit'
cand['tier'] = cand.apply(tier, axis=1)
print('\n[704 split] (per permit)\n' + cand['tier'].value_counts().to_string())

# ============================================================ CELL 11 — HARDEN: settled JN-C classifier (977 -> 584)
classify_fn = housing_rules.classify   # the lifted, importable v4 classifier (housing_rules.permit_role)
print('\n[harden] JN-C classifier ->', classify_fn.__module__ + '.' + classify_fn.__name__)
rc = cand[cand.tier=='relabel_candidate'].copy()
def jnc(r):
    try:
        # real signature: classify(work_type, description, adu_flag, occtype, units_added, units_removed, permit)->tuple
        return classify_fn(r['wt'], r['wd'], r['adu_raw'], r['occ'], r['v4_units'], r['ur'], r['skey'])[0]
    except Exception as e:
        return f'ERR:{e}'
if classify_fn:
    rc['jnc_role'] = rc.apply(jnc, axis=1)
    print('[harden] settled-classifier verdict on the relabel_candidates:\n' + rc['jnc_role'].value_counts().to_string())
    hardened = rc[rc['jnc_role']=='new_unit'].copy()
    assert len(hardened) == EXP['hardened_new_unit'], \
        f'(HARD) hardened new_unit drift: {len(hardened)} != {EXP["hardened_new_unit"]}'
else:
    hardened = rc.iloc[0:0].copy()
    print('  ⚠ classifier not found — hardening skipped; CANNOT gate 584. Fix the callable name and re-run.')

# ============================================================ CELL 12 — dedup + unit band + finaled split
h = hardened.drop_duplicates(subset=['skey']).copy()
def fam(s): mt = re.match(r'([A-Za-z]+\d{4}-\d+)', str(s)); return mt.group(1) if mt else str(s)
h['fam'] = h['skey'].map(fam)
apn_counts = h.groupby('apn_canon')['skey'].nunique()
multi  = apn_counts[apn_counts > 1]; clean = apn_counts[apn_counts == 1]
band_ceiling = len(h); band_floor = len(clean) + len(multi)
finaled     = h[h['finaled']]; not_finaled = h[~h['finaled']]
print(f'\n[dedup/band] {len(h)} permits · clean-single-APN {len(clean)} · multi-permit-APN {len(multi)} (-> #3 review)')
print(f'             UNIT BAND  floor {band_floor}  ..  ceiling {band_ceiling}')
print(f'             finaled {len(finaled)} (completed) · not-finaled {len(not_finaled)} (permitted-not-complete)')
if classify_fn:
    assert band_ceiling == EXP['band_ceiling'], f'(HARD) ceiling drift {band_ceiling} != {EXP["band_ceiling"]}'
    assert band_floor   == EXP['band_floor'],   f'(HARD) floor drift {band_floor} != {EXP["band_floor"]}'
print('[dedup/band] completed-ADU by finaled year:\n' +
      finaled.groupby('fin_year')['skey'].nunique().to_string())

# ============================================================ CELL 13 — write CSV outputs (STOP at queue; no DB write)
m.sort_values(['bucket','apn_canon']).to_csv(os.path.join(OUTDIR, 'jn_d_bijection_oracled.csv'), index=False)
cand.sort_values(['tier','apn_canon']).to_csv(os.path.join(OUTDIR, 'jn_d_704_split.csv'), index=False)
if classify_fn:
    h['relabel_target'] = 'new_unit'
    h['needs_3_review'] = h['apn_canon'].isin(set(multi.index))
    h.sort_values(['needs_3_review','apn_canon']).to_csv(os.path.join(OUTDIR, 'jn_d_relabel_queue.csv'), index=False)
inv.to_csv(os.path.join(OUTDIR, 'jn_d_inverse.csv'), index=False)
print(f'\nwrote CSVs -> {OUTDIR}  (relabel queue is a QUEUE; no event_classifications written — that is a separate gated step)')

# ============================================================ CELL 14 — headline
print('\n================= JN-D HEADLINE =================')
print(f'HCD ADU oracle (anchor)         : {NHCD}')
print(f'v4 coverage (any role)          : {len(apns_with_permit)} = {len(apns_with_permit)/NHCD:.1%}  (gap is FLAGGING not coverage)')
print(f'genuinely missing from v4       : {len(apns_missing)}')
print(f'recall blind-spot, hardened     : {len(hardened) if classify_fn else "n/a"} permits -> band {band_floor}..{band_ceiling} units')
print(f'  of which completed (finaled)  : {len(finaled) if classify_fn else "n/a"}')
print(f'harvest residue (needs Accela)  : {int((cand.tier.isin(["harvest_terse","harvest_terse_but_form_supports"])).sum())} permits')
print(f'inverse (v4 has, HCD lacks)     : {inv.apn_canon.nunique()} APNs / {len(inv)} permits')
print('oracles carried per HCD-ADU row : HCD · Assessor Imps · Berkeley footprints · Address Points')
print('STOP — read-only complete; nothing committed; relabel deferred to its own gated step.')
