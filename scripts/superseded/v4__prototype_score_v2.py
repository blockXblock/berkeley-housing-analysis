#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-26 ============================
# DO NOT RUN. Original path: scripts/v4/prototype_score_v2.py
# WHY: PROTOTYPE building scorer (June 2026, gitignored, never committed); the v3 variant adds confidence for CKAN presence (oracle used as input). Superseded by the structures stage.
raise SystemExit("SEQUESTERED 2026-09-26 -- see header; original path scripts/v4/prototype_score_v2.py")
# ================================================================================
"""
prototype_score_v2.py — TWO-AXIS CONFIDENCE (new-housing trunk + ADU-ness branch)

WHY v2
  v1 collapsed two orthogonal questions into one score, so an 83-unit building scored BELOW a 300sf
  ADU (its description has no 'ADU' word, and the ADU-flavored oracles correctly stayed silent — but
  in one score that silence read as 'uncorroborated'). v2 splits them and routes each oracle to the
  axis it actually speaks to.

  TRUNK  new_housing_conf : "does this produce net new dwelling(s), any kind?"
     interior: unit-count language ('83 dwelling units'), multifamily/new-construction, ADU language.
     oracle:   Imps (improvement-value bump corroborates construction of ANY size).
  BRANCH adu_conf : "given it's housing, is it specifically an ADU?"
     interior: ADU/JADU/accessory-dwelling/conversion/legalization, small size, detached/R-3.
     oracle:   HCD UNIT_CAT='ADU' + footprint>=2 (both ADU-specific).
     BOUND:    adu_conf <= new_housing_conf  (can't be a confident ADU while barely housing).

  INVARIANTS (held from v1):
    - role still set by classify (interior only); oracles never set/flip role.
    - oracles agree-or-abstain; NONE subtract (silence != negative; footprint dissent dropped).
    - weak-only convert/address-assignment floor stays low (false-positive guard).

  Read-only (mode=ro) everywhere; only write = scratch CSV. Calibration instrument, not persisted.
"""
import sqlite3, os, sys, re, json
import pandas as pd

ROOT   = os.path.expanduser('~/berkeley-data')
DB_DIR = os.path.join(ROOT, 'databases')
V4     = os.path.join(DB_DIR, 'berkeley_housing_v4.db')
HCD    = os.path.join(DB_DIR, 'hcd_apr_mirror_2026-06-17_fresh.db')
ASSESS = os.path.join(DB_DIR, 'berkeley.db')
OUTDIR = os.path.join(ROOT, 'scratch', '2026-06-27')
JNDOUT = os.path.join(ROOT, 'scratch', '2026-06-26', 'jn_d_out')
os.makedirs(OUTDIR, exist_ok=True)

def ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)
from scripts.housing_rules.permit_role import classify
from scripts.housing_rules import to_canonical_apn
def C(r):
    try: return to_canonical_apn(r, 'Alameda') or None
    except Exception: return None

# ---------------- interior vocab (two distinct axes) ----------------
ADU_STRONG  = ['adu','accessory dwelling','accessory unit','granny','in-law','junior adu','jadu','accessory dwelling unit']
ADU_WEAK    = ['convert','conversion','legaliz','address assignment']        # weak-only stays low (false-pos guard)
MULTIFAM    = ['mixed use','mixed-use','apartment','multifamily','multi-family','multi family',
               'story building','-story','group living','dwelling units','residential building','new residential']
NEWCONSTRUCT= ['new construction','construction of a new','new residential building','new ','construct']
UNIT_COUNT  = re.compile(r'\(?\s*(\d{1,4})\s*\)?\s*(?:dwelling\s+units?|units?|sleeping\s+units?|dwelling)', re.I)

def unit_count(wd):
    m = UNIT_COUNT.search(wd or '')
    try: return int(m.group(1)) if m else None
    except Exception: return None

def new_housing_interior(wd, role):
    """TRUNK interior confidence: is this net new housing of ANY kind? (0..1)"""
    s = (wd or '').lower()
    n = unit_count(wd)
    if role in ('demolition','non_housing','subsidiary'):    return 0.30   # role says not-housing-production
    if n and n >= 5:                                         return 0.95   # explicit multi-unit count = unambiguous
    if any(k in s for k in MULTIFAM):                        return 0.88   # multifamily/midrise language
    if any(k in s for k in ADU_STRONG):                     return 0.90   # an ADU IS new housing
    if n and n >= 1:                                        return 0.82   # explicit small unit count
    if role == 'new_unit':                                  return 0.72   # classifier says new_unit, generic prose
    if any(k in s for k in ADU_WEAK):                       return 0.50   # weak-only conversion language
    return 0.45

def adu_interior(wd, occ, det):
    """BRANCH interior confidence: is it specifically an ADU? (0..1)"""
    s = (wd or '').lower()
    strong = any(k in s for k in ADU_STRONG)
    weak   = any(k in s for k in ADU_WEAK)
    small  = bool(re.search(r'\b\d{2,3}\s*(?:sq\.?\s*ft|sf|square)', s)) and not (unit_count(wd) or 0) >= 5
    if strong and (small or str(det).lower()=='yes' or str(occ).upper().startswith('R-3')):
        return 0.92                                                       # strong ADU + a corroborating form signal
    if strong:                                                           return 0.85
    if weak and not strong:                                              return 0.45   # weak-only: not confidently ADU
    return 0.10                                                          # no ADU signal -> low ADU-ness (e.g. the 83-unit bldg)

# ---------------- load population (same desc-corroborated ADU candidate set as v1, for comparability) ----------------
ev = pd.read_sql("""
  select e.source_record_key skey, e.raw_apn,
         json_extract(e.raw_payload,'$.WorkDescription') wd,
         json_extract(e.raw_payload,'$.Work Type') wt, json_extract(e.raw_payload,'$.ADU') adu,
         json_extract(e.raw_payload,'$.OccType') occ, json_extract(e.raw_payload,'$.Detached') det,
         json_extract(e.raw_payload,'$.UnitsAdded') ua, json_extract(e.raw_payload,'$.UnitsRemoved') ur,
         max(e.event_type_code='permit_finaled') finaled
  from events e group by e.source_record_key
""", ro(V4))
ev['apn_canon'] = ev['raw_apn'].map(C)
ev['role'] = ev.apply(lambda r: classify(r['wt'], r['wd'], r['adu'], r['occ'], r['ua'], r['ur'], r['skey'])[0], axis=1)
ADU_LANG = ADU_STRONG + ADU_WEAK + ['accessory','dwelling unit']
pop = ev[ev['wd'].map(lambda s: any(k in (s or '').lower() for k in ADU_LANG))].copy()
print(f'population: {len(pop)}  (classifier new_unit: {int((pop.role=="new_unit").sum())})')

# ---------------- oracles (per-axis attachment) ----------------
hcd_apn = set(C(a) for (a,) in ro(HCD).execute("select APN from table_a2 where upper(coalesce(UNIT_CAT,''))='ADU'") if C(a))
imps = {}
for a, v in ro(ASSESS).execute('select APN, Imps from parcels'):
    ca = C(a)
    if ca:
        try: imps[ca] = float(str(v).replace('$','').replace(',',''))
        except Exception: pass
fp_count = {}
fp_cache = os.path.join(JNDOUT, '_oracle_cache', 'footprints.json')
if os.path.exists(fp_cache):
    for r in json.load(open(fp_cache)):
        ca = C(r.get('PARCELID'))
        if ca: fp_count[ca] = fp_count.get(ca, 0) + 1
print(f'[oracles] hcd_adu_apns={len(hcd_apn)} · imps={len(imps)} · footprint_parcels={len(fp_count)}')

agree_imps = sorted(v for v in (imps.get(a) for a in pop.loc[(pop.role=='new_unit') & pop.finaled & pop.apn_canon.isin(hcd_apn),'apn_canon']) if v and v>0)
IMPS_REF = agree_imps[len(agree_imps)//4] if agree_imps else None
print(f'[calibration] IMPS_REF (p25 known-good) = {IMPS_REF}')

def score_row(r):
    apn = r['apn_canon']
    # TRUNK: new-housing, Imps oracle only
    nh_i = new_housing_interior(r['wd'], r['role'])
    im   = imps.get(apn)
    imps_vote = 'agree' if (im and IMPS_REF and im >= IMPS_REF) else 'abstain'
    nh = min(1.0, nh_i + (0.05 if imps_vote=='agree' else 0.0))
    # BRANCH: ADU-ness, HCD + footprint oracles, bounded by trunk
    adu_i = adu_interior(r['wd'], r['occ'], r['det'])
    hcd_vote = 'agree' if apn in hcd_apn else 'abstain'
    fc = fp_count.get(apn) if fp_count else None
    fp_vote = 'agree' if (fc and fc >= 2) else 'abstain'         # positive-only (dissent dropped)
    adu = adu_i + (0.04 if hcd_vote=='agree' else 0.0) + (0.04 if fp_vote=='agree' else 0.0)
    adu = min(adu, nh)                                            # BOUND: can't be a stronger ADU than it is housing
    adu = max(0.0, min(1.0, adu))
    return pd.Series(dict(
        role=r['role'], finaled=bool(r['finaled']), units=unit_count(r['wd']),
        new_housing_conf=round(nh,3), adu_conf=round(adu,3),
        nh_interior=round(nh_i,3), adu_interior=round(adu_i,3),
        imps=imps_vote, hcd=hcd_vote, footprint=fp_vote,
        wd=(r['wd'] or '')[:78]))
S = pd.concat([pop[['skey','apn_canon']].reset_index(drop=True),
               pop.apply(score_row, axis=1).reset_index(drop=True)], axis=1)

def band(c, hi=0.78, lo=0.60): return 'high' if c>=hi else ('medium' if c>=lo else 'low')
S['nh_band']  = S['new_housing_conf'].map(band)
S['adu_band'] = S['adu_conf'].map(band)

# ---------------- calibration readout ----------------
print('\n=== NEW-HOUSING band ===\n' + S['nh_band'].value_counts().reindex(['high','medium','low']).to_string())
print('\n=== ADU-ness band ===\n'    + S['adu_band'].value_counts().reindex(['high','medium','low']).to_string())
print('\n=== the 2x2 (where the two axes diverge) ===')
print(pd.crosstab(S['nh_band'], S['adu_band'], rownames=['new_housing'], colnames=['adu']).to_string())

def show(title, df, n=8):
    print(f'\n--- {title} ---')
    for _, r in df.head(n).iterrows():
        print(f'  nh={r["new_housing_conf"]:.2f} adu={r["adu_conf"]:.2f} [{r["role"]:10s}] '
              f'im:{r["imps"]:6s} hcd:{r["hcd"]:6s} fp:{r["footprint"]:6s} | {r["wd"]}')

# the cases v1 got wrong: big buildings should now be HIGH new-housing, LOW adu
show('BIG BUILDINGS (unit-count >=5) — expect HIGH new_housing, LOW adu',
     S[S.units.fillna(0)>=5].sort_values('new_housing_conf', ascending=False))
# real ADUs: expect HIGH on both
show('STRONG ADU language — expect HIGH on both axes',
     S[S.wd.str.lower().str.contains('adu|accessory dwelling|jadu')].sort_values('adu_conf', ascending=False))
# weak-only: expect LOW adu (false-positive guard)
show('weak-only convert — expect LOW adu',
     S[S.wd.str.lower().str.contains('convert') & ~S.wd.str.lower().str.contains('adu|accessory|dwelling|jadu')])

S.sort_values(['adu_band','adu_conf'], ascending=[True,False]).to_csv(os.path.join(OUTDIR,'prototype_scores_v2.csv'), index=False)
print(f'\nwrote {OUTDIR}/prototype_scores_v2.csv')
print('READ: the 2x2 is the payoff — high-new-housing/low-adu = big buildings (correct); high/high = real ADUs; '
      'low/low = trade permits. If the diagonal is clean and big buildings left the low-new-housing corner, the split works.')
