#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-26 ============================
# DO NOT RUN. Original path: scripts/v4/prototype_score_v2_cc.py
# WHY: PROTOTYPE building scorer (June 2026, gitignored, never committed); the v3 variant adds confidence for CKAN presence (oracle used as input). Superseded by the structures stage.
raise SystemExit("SEQUESTERED 2026-09-26 -- see header; original path scripts/v4/prototype_score_v2_cc.py")
# ================================================================================
"""
prototype_score_v2_cc.py — CC's INDEPENDENT implementation of the two-axis ADU/new-housing scorer.

Written from the spec WITHOUT reading scripts/v4/prototype_score_v2.py — the point is two independent
implementations of the same fixed design, to cross-check. Two orthogonal 0..1 confidences per permit:

  new_housing_conf (TRUNK)  — does this produce net-new dwelling(s) of ANY kind?
       interior: role + unit-count / multifamily-new-construction / ADU language. demo/non_housing/sub = low.
       oracle:   assessor Imps only (agree-or-abstain, additive).
  adu_conf (BRANCH)         — given it's housing, is it specifically an ADU?
       interior: ADU/JADU/conversion/legalization language, small size, Detached/R-3. weak-only convert = low.
       oracles:  HCD UNIT_CAT='ADU' + footprint>=2 (both ADU-specific; agree-or-abstain, additive).
       BOUND:    adu_conf <= new_housing_conf.

INVARIANTS: role from housing_rules.permit_role.classify ONLY (oracles never set/flip role); every oracle
is agree-or-abstain and ADDITIVE (none subtract; no footprint dissent); band seeds interior-anchored + printed.
DISCIPLINE: mode=ro on every DB; only write = scratch/2026-06-27/prototype_scores_v2_cc.csv. Nothing committed.
"""
import sqlite3, os, sys, json, re
import pandas as pd

ROOT   = os.path.expanduser('~/berkeley-data')
DBD    = os.path.join(ROOT, 'databases')
V4     = os.path.join(DBD, 'berkeley_housing_v4.db')
HCD    = os.path.join(DBD, 'hcd_apr_mirror_2026-06-17_fresh.db')
ASSESS = os.path.join(DBD, 'berkeley.db')
FPCACHE= os.path.join(ROOT, 'scratch', '2026-06-26', 'jn_d_out', '_oracle_cache', 'footprints.json')
OUT    = os.path.join(ROOT, 'scratch', '2026-06-27', 'prototype_scores_v2_cc.csv')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
def ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)
from scripts.housing_rules.permit_role import classify
from scripts.housing_rules import to_canonical_apn
def C(r):
    try: return to_canonical_apn(r, 'Alameda') or None
    except Exception: return None
def to_int(x):
    try: return int(float(str(x).strip()))
    except Exception: return None

# ---------- vocab (mine) ----------
ADU_STRONG = ['adu','jadu','accessory dwelling','accessory dwelling unit','junior accessory',
              'granny','in-law','secondary dwelling','second unit','second dwelling']
WEAK       = ['convert','conversion','legaliz','address assignment']
MULTIFAM   = ['apartment','multifamily','multi-family','mixed use','mixed-use','dwelling units',
              'residential building','residential development','housing development','group living',
              'story building','-story','sleeping units']
SMALL_HINT = ['adu','jadu','garage','basement','rear','detached','cottage','studio']
UNIT_RE    = re.compile(r'\(?(\d{1,4})\)?\s*(?:new\s+)?(?:dwelling\s+|residential\s+|sleeping\s+)?units?\b', re.I)

def unit_count(ua, wd):
    n = to_int(ua)
    if n and n > 0: return n
    m = UNIT_RE.search(wd or '')
    return int(m.group(1)) if m else None

# ---------- interior tiers (named so seeds derive from them) ----------
# new_housing interior
NH_BIG   = 0.90   # new_unit + multifamily / unit-count>=2 / new-construction
NH_ADU   = 0.85   # new_unit with ADU language (an ADU IS new housing)
NH_NEW   = 0.78   # new_unit, no explicit multifam/ADU prose
NH_ALT_C = 0.55   # alteration/ambiguous WITH unit-creating (ADU/conversion) language
NH_AMB   = 0.45   # ambiguous, desc-corroborated but unconfirmed
NH_LOW   = 0.15   # demolition / non_housing / subsidiary / plain alteration -> not new housing
# adu interior
ADU_STRONGV = 0.85  # explicit ADU/JADU/accessory-dwelling language
ADU_BUMP    = 0.05  # + detached / R-3 / small-size corroboration (capped)
ADU_WEAK    = 0.45  # weak-only convert/address-assignment (no strong ADU term) -> stays LOW (guard)
ADU_NOTADU  = 0.10  # big building / clearly-not-ADU
ADU_NEUTRAL = 0.40  # housing but no ADU signal either way

# oracle bonuses (additive, agree-or-abstain)
IMPS_BONUS = 0.07   # new_housing trunk: a real improvement-value bump
HCD_BONUS  = 0.06   # adu branch: HCD says ADU
FP_BONUS   = 0.04   # adu branch: >=2 structures (modest ~1.4x lift, positive-only)

def new_housing_interior(role, wd, uc):
    s = (wd or '').lower()
    strong_adu = any(k in s for k in ADU_STRONG)
    multifam   = any(k in s for k in MULTIFAM) or (uc is not None and uc >= 2)
    if role in ('demolition','non_housing','subsidiary'): return NH_LOW
    if role == 'new_unit':
        if multifam or (uc is not None and uc >= 5): return NH_BIG
        if strong_adu:                               return NH_ADU
        return NH_NEW
    if role == 'ambiguous':
        return NH_ALT_C if strong_adu else NH_AMB
    if role == 'alteration':
        return NH_ALT_C if (strong_adu or any(k in s for k in WEAK)) else NH_LOW
    return NH_AMB

def adu_interior(role, wd, uc, det, occ):
    s = (wd or '').lower()
    strong_adu = any(k in s for k in ADU_STRONG)
    weak       = any(k in s for k in WEAK)
    big        = (uc is not None and uc >= 5) or any(k in s for k in
                 ['apartment','multifamily','multi-family','mixed use','mixed-use','dwelling units','group living'])
    detached   = str(det).lower() == 'yes'
    r3         = str(occ or '').upper().startswith('R-3')
    if big and not strong_adu:           return ADU_NOTADU      # a 39-unit building is not an ADU
    if strong_adu:
        v = ADU_STRONGV + (ADU_BUMP if (detached or r3 or any(k in s for k in SMALL_HINT)) else 0.0)
        return min(v, 0.92)
    if weak and not strong_adu:          return ADU_WEAK        # weak-only convert -> low (false-positive guard)
    return ADU_NEUTRAL

# ============================================================ load population (desc-corroborated ADU candidates)
ev = pd.read_sql("""
  select e.source_record_key skey, e.raw_apn,
         json_extract(e.raw_payload,'$.WorkDescription') wd,
         json_extract(e.raw_payload,'$.Work Type')       wt,
         json_extract(e.raw_payload,'$.ADU')             adu,
         json_extract(e.raw_payload,'$.OccType')         occ,
         json_extract(e.raw_payload,'$.Detached')        det,
         json_extract(e.raw_payload,'$.UnitsAdded')      ua,
         json_extract(e.raw_payload,'$.UnitsRemoved')    ur,
         max(e.event_type_code='permit_finaled')         finaled
  from events e group by e.source_record_key
""", ro(V4))
ev['apn_canon'] = ev['raw_apn'].map(C)
ev['role'] = ev.apply(lambda r: classify(r['wt'], r['wd'], r['adu'], r['occ'], r['ua'], r['ur'], r['skey'])[0], axis=1)
POP_LANG = ADU_STRONG + WEAK + ['accessory','dwelling unit']
ev['desc_adu'] = ev['wd'].map(lambda s: any(k in (s or '').lower() for k in POP_LANG))
pop = ev[ev['desc_adu']].copy()
print(f'population (desc-corroborated ADU candidates): {len(pop)}  (classifier new_unit: {int((pop.role=="new_unit").sum())})')

# ============================================================ oracles (read-only)
hcd_adu = set(C(a) for (a,) in ro(HCD).execute(
    "select APN from table_a2 where upper(coalesce(UNIT_CAT,''))='ADU'") if C(a))
imps = {}
for a, v in ro(ASSESS).execute('select APN, Imps from parcels'):
    ca = C(a)
    if ca:
        try: imps[ca] = float(str(v).replace('$','').replace(',',''))
        except Exception: pass
fp = {}
if os.path.exists(FPCACHE):
    for r in json.load(open(FPCACHE)):
        ca = C(r.get('PARCELID'))
        if ca: fp[ca] = fp.get(ca, 0) + 1
    print(f'[oracle] footprints: {len(fp)} parcels from cache')
else:
    print('[oracle] footprint cache MISSING -> footprint votes abstain')

# Imps reference = p25 of known-good ADUs (HCD-confirmed finaled new_unit) — "a real improvement bump"
known = pop[(pop.role=='new_unit') & pop.finaled & pop.apn_canon.isin(hcd_adu)]
kimps = sorted(v for v in (imps.get(a) for a in known.apn_canon) if v and v > 0)
IMPS_REF = kimps[len(kimps)//4] if kimps else None
print(f'[calibration] IMPS_REF (p25 of {len(kimps)} known-good ADUs) = {IMPS_REF}')

# ============================================================ band seeds (interior-anchored)
NH_HI, NH_LO   = 0.80, 0.50   # strong new-housing interior (NH_ADU 0.85 / NH_BIG 0.90) clears HIGH unaided
ADU_HI, ADU_LO = 0.80, 0.45   # strong-ADU interior (0.85) clears HIGH unaided
print(f'[seeds] new_housing: HIGH>={NH_HI} MED>={NH_LO}  (strong interior {NH_ADU}/{NH_BIG} clears HIGH unaided)')
print(f'[seeds] adu        : HIGH>={ADU_HI} MED>={ADU_LO}  (strong-ADU interior {ADU_STRONGV} clears HIGH unaided)')
def nh_band(c):  return 'high' if c>=NH_HI  else ('medium' if c>=NH_LO  else 'low')
def adu_band(c): return 'high' if c>=ADU_HI else ('medium' if c>=ADU_LO else 'low')

# ============================================================ score
rows = []
for _, r in pop.iterrows():
    apn = r['apn_canon']; wd = r['wd'] or ''; uc = unit_count(r['ua'], wd)
    im = imps.get(apn); fc = fp.get(apn) if fp else None
    imps_vote = 'agree' if (im is not None and IMPS_REF and im >= IMPS_REF) else 'abstain'
    hcd_vote  = 'agree' if apn in hcd_adu else 'abstain'
    fp_vote   = 'agree' if (fc is not None and fc >= 2) else 'abstain'
    # TRUNK
    nh = new_housing_interior(r['role'], wd, uc)
    if imps_vote == 'agree': nh += IMPS_BONUS
    nh = max(0.0, min(1.0, nh))
    # BRANCH
    ad = adu_interior(r['role'], wd, uc, r['det'], r['occ'])
    if hcd_vote == 'agree': ad += HCD_BONUS
    if fp_vote  == 'agree': ad += FP_BONUS
    ad = max(0.0, min(1.0, ad))
    ad = min(ad, nh)                      # BOUND: adu_conf <= new_housing_conf
    rows.append(dict(skey=r['skey'], apn=apn, role=r['role'], finaled=bool(r['finaled']), units=uc,
                     new_housing_conf=round(nh,3), new_housing_band=nh_band(nh),
                     adu_conf=round(ad,3), adu_band=adu_band(ad),
                     imps=imps_vote, hcd=hcd_vote, footprint=fp_vote, wd=wd[:80]))
S = pd.DataFrame(rows)

# ============================================================ readouts
print('\n=== new_housing band distribution ===')
print(S['new_housing_band'].value_counts().reindex(['high','medium','low']).to_string())
print('\n=== adu band distribution ===')
print(S['adu_band'].value_counts().reindex(['high','medium','low']).to_string())
print('\n=== 2x2 crosstab: new_housing (rows) x adu (cols) ===')
ct = pd.crosstab(S['new_housing_band'], S['adu_band']).reindex(index=['high','medium','low'], columns=['high','medium','low']).fillna(0).astype(int)
print(ct.to_string())

def show(title, df, n=8):
    print(f'\n--- {title} ---')
    for _, r in df.head(n).iterrows():
        print(f'  NH {r["new_housing_conf"]:.2f}[{r["new_housing_band"]:6}] ADU {r["adu_conf"]:.2f}[{r["adu_band"]:6}] '
              f'{r["role"]:10} u={str(r["units"]):>4} | imps:{r["imps"]:6} hcd:{r["hcd"]:6} fp:{r["footprint"]:6} | {r["wd"]}')

show('BIG BUILDINGS (units>=5) — expect HIGH new_housing / LOW adu', S[S.units.fillna(0)>=5].sort_values('units', ascending=False))
show('STRONG-ADU cases — expect HIGH / HIGH', S[S.wd.str.lower().str.contains('adu|accessory dwelling|jadu', na=False) & ~S.wd.str.lower().str.contains('not an adu', na=False)])
show('WEAK-ONLY convert (no strong ADU term) — expect LOW adu',
     S[S.wd.str.lower().str.contains('convert', na=False) & ~S.wd.str.lower().str.contains('adu|accessory|jadu|granny|in-law', na=False)])

# the bound forbids high-adu / low-new_housing
corner = S[(S.adu_band=='high') & (S.new_housing_band=='low')]
print(f'\n[BOUND CHECK] high-adu / low-new_housing corner (must be EMPTY): {len(corner)} rows '
      f'-> {"EMPTY ✓" if len(corner)==0 else "VIOLATION ✗"}')

S.sort_values(['new_housing_band','adu_band','new_housing_conf']).to_csv(OUT, index=False)
print(f'\nwrote {OUT}  ({len(S)} rows; read-only calibration instrument, nothing persisted)')
