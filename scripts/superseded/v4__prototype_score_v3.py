#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-26 ============================
# DO NOT RUN. Original path: scripts/v4/prototype_score_v3.py
# WHY: PROTOTYPE building scorer (June 2026, gitignored, never committed); the v3 variant adds confidence for CKAN presence (oracle used as input). Superseded by the structures stage.
raise SystemExit("SEQUESTERED 2026-09-26 -- see header; original path scripts/v4/prototype_score_v3.py")
# ================================================================================
"""
prototype_score_v3.py — RECONCILED two-axis scorer (merge of prototype_score_v2.py [JN] + _v2_cc.py [CC]).

The two v2 implementations agreed at rho=0.90 (adu) / 0.85 (new_housing) on raw scoring — the
architecture is validated. They diverged only on policy knobs, now DECIDED:

  D1  KEEP AN EXPLICIT MEDIUM BAND on both axes (uncertainty surfaced = harvest queue). Per-axis
      interior-anchored thresholds (CC's banding; not JN's bimodal). Strong interior reaches HIGH unaided.
  D2  WEAK-ONLY CONVERTS FLOOR TO LOW on adu_conf (strictly below the medium floor) — false-positive guard.
  D3  PRE-2017 statutory ADU terms count as strong-ADU ONLY behind a CREATING-CONTEXT guard (a creation
      verb new/add/construct/create/build/conver* within ~40 chars of the term). Bare existing-unit refs
      ('repairs to stairs to 2nd unit') do NOT promote.
  D4  UNCHANGED regressions: strong-ADU+new_unit -> high/high; big buildings (units>=20) -> ~23 low-adu /
      1 high-adu; bound adu_conf <= new_housing_conf -> forbidden corner (high-adu/low-new-housing) EMPTY.

INVARIANTS: role from housing_rules.permit_role.classify ONLY (oracles never set/flip role); oracles
agree-or-abstain, none subtract (no footprint dissent); per-axis attachment (Imps->trunk; HCD+footprint->branch).
DISCIPLINE: mode=ro on every DB; only write = scratch/2026-06-27/prototype_scores_v3.csv. Nothing committed.
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

# ---------------- vocab ----------------
ADU_STRONG  = ['adu','accessory dwelling','accessory unit','granny','in-law','junior adu','jadu','accessory dwelling unit']
ADU_WEAK    = ['convert','conversion','legaliz','address assignment']     # weak-only -> LOW (D2)
SOFT_ADU    = ['accessory','cottage','carriage house','garden cottage']   # accessory-ish but not a clean ADU token -> MEDIUM
MULTIFAM    = ['mixed use','mixed-use','apartment','multifamily','multi-family','multi family',
               'story building','-story','group living','dwelling units','residential building','new residential']
# D3 — pre-2017 statutory terms + creating-context guard
PRE2017     = ['second unit','secondary unit','secondary dwelling','2nd unit','secondary residential unit']
UNIT_COUNT  = re.compile(r'\(?\s*(\d{1,4})\s*\)?\s*(?:dwelling\s+units?|units?|sleeping\s+units?|dwelling)', re.I)
# D3 guard: the creation verb must GOVERN the unit phrase (not merely sit nearby — 'new fixtures' must not
# promote 'existing 2nd unit'). Forward: verb ...<=4 tokens... (second/2nd) (unit/dwelling/residential).
# Reverse: the unit phrase ...<=3 tokens... a creation/conversion verb (catches 'SECONDARY UNIT CONVERSION').
CREATE_FWD = re.compile(r'\b(?:new|add(?:ing)?|construct\w*|creat\w*|build\w*|convert\w*)\b(?:\s+\S+){0,6}\s+(?:second(?:ary)?|2nd)\s+(?:unit|dwelling|residential)')
CREATE_REV = re.compile(r'(?:second(?:ary)?|2nd)\s+(?:unit|dwelling|residential)\b(?:\s+\S+){0,3}\s+\b(?:conversion|convert\w*|creat\w*|construct\w*|add(?:ed|ition)?|built)\b')

def unit_count(wd):
    m = UNIT_COUNT.search(wd or '')
    try: return int(m.group(1)) if m else None
    except Exception: return None

def creating_pre2017(s):
    """D3 guard: a pre-2017 statutory term counts as strong-ADU ONLY in a unit-creation context."""
    return bool(CREATE_FWD.search(s) or CREATE_REV.search(s))

def is_strong_adu(s):
    return any(k in s for k in ADU_STRONG) or creating_pre2017(s)

def new_housing_interior(wd, role):
    """TRUNK: net new housing of ANY kind? (0..1)"""
    s = (wd or '').lower(); n = unit_count(wd)
    if role in ('demolition','non_housing','subsidiary'): return 0.30
    if n and n >= 5:                                      return 0.95
    if any(k in s for k in MULTIFAM):                     return 0.88
    if is_strong_adu(s):                                  return 0.90   # an ADU IS new housing (incl guarded pre-2017)
    if n and n >= 1:                                      return 0.82
    if role == 'new_unit':                               return 0.72
    if any(k in s for k in ADU_WEAK):                    return 0.50
    return 0.45

def adu_interior(wd, occ, det):
    """BRANCH: specifically an ADU? (0..1)  Order: strong > big-guard > soft(MEDIUM) > weak(LOW) > none(LOW)."""
    s = (wd or '').lower()
    strong = is_strong_adu(s)
    big    = (unit_count(wd) or 0) >= 5 or any(k in s for k in MULTIFAM)
    if strong:                                                          # strong wins even on a big parcel (the 1 high)
        small = bool(re.search(r'\b\d{2,3}\s*(?:sq\.?\s*ft|sf|square)', s)) and not big
        if small or str(det).lower()=='yes' or str(occ).upper().startswith('R-3'): return 0.92
        return 0.85
    if big:                                                  return 0.10   # big & not strong -> the 23 low-adu
    if any(k in s for k in SOFT_ADU):                        return 0.62   # uncertain ADU -> MEDIUM (harvest queue)
    if any(k in s for k in ADU_WEAK):                        return 0.40   # weak-only -> LOW (D2, strictly < ADU_LO)
    return 0.10

# ---------------- population (same desc-corroborated ADU candidate set, for comparability) ----------------
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

# ---------------- oracles (per-axis) ----------------
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
print(f'[oracles] hcd_adu={len(hcd_apn)} · imps={len(imps)} · footprint_parcels={len(fp_count)}')
agree_imps = sorted(v for v in (imps.get(a) for a in
              pop.loc[(pop.role=='new_unit') & pop.finaled & pop.apn_canon.isin(hcd_apn),'apn_canon']) if v and v>0)
IMPS_REF = agree_imps[len(agree_imps)//4] if agree_imps else None
print(f'[calibration] IMPS_REF (p25 known-good) = {IMPS_REF}')

# ---------------- band seeds (D1: interior-anchored, medium preserved) ----------------
NH_HI, NH_LO   = 0.80, 0.50   # strong new-housing interior (0.88/0.90/0.95) clears HIGH unaided; medium = generic/weak
ADU_HI, ADU_LO = 0.80, 0.55   # strong-ADU interior (0.85/0.92) clears HIGH unaided; weak(0.40)<LO -> low; soft(0.62)=medium
print(f'[seeds] new_housing HIGH>={NH_HI} MED>={NH_LO}  ·  adu HIGH>={ADU_HI} MED>={ADU_LO}  (interior-anchored; strong clears HIGH unaided)')
def nh_band(c):  return 'high' if c>=NH_HI  else ('medium' if c>=NH_LO  else 'low')
def adu_band(c): return 'high' if c>=ADU_HI else ('medium' if c>=ADU_LO else 'low')

# ---------------- score ----------------
def score_row(r):
    apn = r['apn_canon']
    nh_i = new_housing_interior(r['wd'], r['role'])
    im = imps.get(apn); imps_vote = 'agree' if (im and IMPS_REF and im >= IMPS_REF) else 'abstain'
    nh = min(1.0, nh_i + (0.05 if imps_vote=='agree' else 0.0))
    adu_i = adu_interior(r['wd'], r['occ'], r['det'])
    hcd_vote = 'agree' if apn in hcd_apn else 'abstain'
    fc = fp_count.get(apn) if fp_count else None
    fp_vote = 'agree' if (fc and fc >= 2) else 'abstain'
    adu = adu_i + (0.04 if hcd_vote=='agree' else 0.0) + (0.04 if fp_vote=='agree' else 0.0)
    adu = max(0.0, min(min(adu, nh), 1.0))                              # BOUND + clamp
    return pd.Series(dict(role=r['role'], finaled=bool(r['finaled']), units=unit_count(r['wd']),
        new_housing_conf=round(nh,3), nh_band=nh_band(nh), adu_conf=round(adu,3), adu_band=adu_band(adu),
        nh_interior=round(nh_i,3), adu_interior=round(adu_i,3),
        imps=imps_vote, hcd=hcd_vote, footprint=fp_vote, wd=(r['wd'] or '')[:90]))
S = pd.concat([pop[['skey','apn_canon']].reset_index(drop=True),
               pop.apply(score_row, axis=1).reset_index(drop=True)], axis=1)

# ---------------- report ----------------
print('\n=== NEW-HOUSING band ===\n' + S['nh_band'].value_counts().reindex(['high','medium','low']).to_string())
print('\n=== ADU band ===\n'         + S['adu_band'].value_counts().reindex(['high','medium','low']).to_string())
print('\n=== 2x2 (new_housing rows x adu cols) ===')
print(pd.crosstab(S['nh_band'], S['adu_band']).reindex(index=['high','medium','low'], columns=['high','medium','low']).fillna(0).astype(int).to_string())

print('\n--- D1 CONFIRM: populated medium band on BOTH axes ---')
print(f'  new_housing medium = {(S.nh_band=="medium").sum()} ; adu medium = {(S.adu_band=="medium").sum()}')

print('\n--- D2 CONFIRM: weak-only convert anchors must be LOW adu ---')
anchors = S[S.wd.str.contains('4-PLEX TO DUPLEX|convert closet|CRAWLAPACE|crawlspace|STORAGE TO CREATE A KITCHEN|Convert Closet', case=False, na=False)
            & ~S.wd.str.lower().str.contains('adu|accessory|jadu|granny|in-law')]
for _, r in anchors.head(12).iterrows():
    print(f'  adu={r["adu_conf"]:.2f} [{r["adu_band"]:6}] | {r["wd"][:72]}')

print('\n--- D3 CONFIRM: pre-2017 statutory permits — promoted (strong) vs stayed ---')
# use FULL WorkDescription (S.wd is truncated to 90 for display; the guard must see the whole text)
Sf = S.merge(pop[['skey','wd']].rename(columns={'wd':'wd_full'}), on='skey', how='left')
pre = Sf[Sf.wd_full.str.lower().str.contains('|'.join(re.escape(t) for t in PRE2017), na=False)].copy()
pre['promoted'] = pre['wd_full'].map(lambda s: is_strong_adu((s or '').lower()))
print(f'  pre-2017-term permits in population: {len(pre)}  ·  promoted(strong): {int(pre.promoted.sum())}  ·  stayed: {int((~pre.promoted).sum())}')
for _, r in pre.sort_values('promoted', ascending=False).iterrows():
    tag = 'PROMOTE' if r['promoted'] else 'stay   '
    print(f'  [{tag}] adu={r["adu_conf"]:.2f}[{r["adu_band"]:6}] nh={r["new_housing_conf"]:.2f}[{r["nh_band"]:6}] {r["role"]:10} | {str(r["wd_full"])[:80]}')
# DIRECT guard test on the gap-report examples (existing-unit refs are NOT in the population — prove the
# guard rejects them anyway; creating-context refs promote).
print('  guard unit-test (creating_pre2017 should be True only for creation-context):')
for s, exp in [("make repairs to existing deck and stairs to 2nd unit", False),
               ("remodel existing 2nd unit bathroom at 2nd floor with new fixtures", False),
               ("construction of a new secondary dwelling unit. aup obtained", True),
               ("convert basement to second unit and remodel upper unit", True),
               ("secondary unit conversion & remodel of an existing garage in rear yard", True)]:
    got = creating_pre2017(s)
    print(f'    [{"ok" if got==exp else "**FAIL"}] guard={got!s:5} expect={exp!s:5} | {s[:60]}')

print('\n--- D4 REGRESSION ---')
strong658 = S[(S.role=='new_unit') & S.wd.str.lower().str.contains('adu|accessory dwelling|jadu', na=False)]
hh = ((strong658.nh_band=='high') & (strong658.adu_band=='high')).sum()
print(f'  strong-ADU + new_unit: {len(strong658)} permits, high/high = {hh}  ({"OK" if hh==len(strong658) else "DRIFT"})')
big = S[S.units.fillna(0) >= 20]
print(f'  big buildings (units>=20): {len(big)} · adu band = {big.adu_band.value_counts().to_dict()}')
corner = S[(S.adu_band=='high') & (S.nh_band=='low')]
print(f'  forbidden corner (high-adu/low-new-housing): {len(corner)} -> {"EMPTY ✓" if len(corner)==0 else "VIOLATION ✗"}')

S.sort_values(['nh_band','adu_band','new_housing_conf']).to_csv(os.path.join(OUTDIR,'prototype_scores_v3.csv'), index=False)
print(f'\nwrote {OUTDIR}/prototype_scores_v3.csv  ({len(S)} rows; read-only, nothing persisted)')
