#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-26 ============================
# DO NOT RUN. Original path: scripts/v4/prototype_score.py
# WHY: PROTOTYPE building scorer (June 2026, gitignored, never committed); the v3 variant adds confidence for CKAN presence (oracle used as input). Superseded by the structures stage.
raise SystemExit("SEQUESTERED 2026-09-26 -- see header; original path scripts/v4/prototype_score.py")
# ================================================================================
"""
prototype_score.py — TWO-TIER CONFIDENCE SCORING (calibration prototype, throwaway instrument)

WHAT THIS IS
  A `score()` wrapper over the CENTRALIZED, COMMITTED classifier (housing_rules.permit_role.classify,
  commit aa6ded0). It does NOT touch classify. It adds the confidence layer designed this session:

    TIER 1 (interior) — classify SETS THE ROLE. An interior_confidence reflects how cleanly the
      description gate fired (strong ADU language high; weak-only convert/address-assignment token low).
    TIER 2 (oracles)  — HCD · Imps · footprint · address-point each vote agree/silent/dissent. Votes
      POOL into a confidence ADJUSTMENT. Two INVARIANTS enforced structurally:
        (I1) an oracle can NEVER set or change the role  (corroborate-never-source / no circularity)
        (I2) oracle SILENCE never lowers confidence       (silence != negative)
      Output carries each oracle's vote DISPLAYED even though pooled for the scalar (orthogonality in
      the record; transparency is the deliverable).

  Output per permit: role · confidence(0-1) · band · interior_confidence · oracle_votes{4} · rationale.
  Band thresholds are SEEDED from the 446 known-good agree-ADUs (not round-number guesses) and printed
  so John can override them. Runs over the 977/584 ADU set; prints boundary cases for calibration.

  DISCIPLINE: read-only on every DB (mode=ro), read-only GIS (cached), only write = one scratch CSV.
  This is a CALIBRATION INSTRUMENT, not a deliverable — it informs the spec; nothing persists to v4.
"""
import sqlite3, os, sys, json
import pandas as pd

ROOT   = os.path.expanduser('~/berkeley-data')
DB_DIR = os.path.join(ROOT, 'databases')
V4     = os.path.join(DB_DIR, 'berkeley_housing_v4.db')
HCD    = os.path.join(DB_DIR, 'hcd_apr_mirror_2026-06-17_fresh.db')
ASSESS = os.path.join(DB_DIR, 'berkeley.db')
OUTDIR = os.path.join(ROOT, 'scratch', '2026-06-27')
JNDOUT = os.path.join(ROOT, 'scratch', '2026-06-26', 'jn_d_out')   # reuse JN-D's footprint cache + bijection
os.makedirs(OUTDIR, exist_ok=True)

def ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)
from scripts.housing_rules.permit_role import classify          # the COMMITTED centralized classifier (aa6ded0)
from scripts.housing_rules import to_canonical_apn
def C(r):
    try: return to_canonical_apn(r, 'Alameda') or None
    except Exception: return None
def num(x):
    try: return int(float(x))
    except Exception: return None

# ----- interior signal vocab (read from the SAME module so it can't drift from classify) -----
from scripts.housing_rules import permit_role as PR
STRONG = ['adu','accessory dwelling','accessory unit','granny','in-law','junior adu','jadu']
WEAK   = ['convert','conversion','legaliz','address assignment']
# interior-confidence tiers, NAMED so the HIGH band seed can be derived FROM them (change 2)
IC_STRONG        = 0.92   # unambiguous ADU language
IC_NEWUNIT_PROSE = 0.75   # new_unit via units/work-type, no explicit ADU prose
IC_WEAK          = 0.55   # weak-only convert/legalize token (the false-positive band)
IC_OTHER         = 0.50   # role set by non-new_unit rules; neutral interior
# positive-only oracle bonuses (change 1): footprint highest (most independent physical signal) but small
# (~1.4x lift, >=2-only), then hcd, then imps. No oracle may subtract.
AGREE_BONUS = {'footprint':0.04, 'hcd':0.03, 'imps':0.02}
def interior_confidence(wd, role):
    """How cleanly did the gate fire? Strong ADU language -> high; weak-only token -> low. (0..1)"""
    s = (wd or '').lower()
    strong = any(k in s for k in STRONG); weak = any(k in s for k in WEAK)
    if role != 'new_unit':                 return IC_OTHER         # role set by other rules; neutral interior
    if strong:                             return IC_STRONG        # unambiguous ADU language
    if weak and not strong:                return IC_WEAK          # weak-only: the false-positive risk band
    return IC_NEWUNIT_PROSE                                        # new_unit via units/work-type, no explicit ADU prose

# ============================================================ load the ADU candidate set (977/584)
# reuse JN-D's per-permit evidence so we score the SAME population we already understand
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
# role from the COMMITTED classifier (interior tier sets it)
ev['role'] = ev.apply(lambda r: classify(r['wt'], r['wd'], r['adu'], r['occ'], r['ua'], r['ur'], r['skey'])[0], axis=1)

# the 584/977 ADU population = description-corroborated relabel candidates (same gate JN-D used)
ADU_LANG = STRONG + WEAK + ['accessory','dwelling unit']
ev['desc_adu'] = ev['wd'].map(lambda s: any(k in (s or '').lower() for k in ADU_LANG))
pop = ev[ev['desc_adu']].copy()
print(f'scoring population (desc-corroborated ADU candidates): {len(pop)}  '
      f'(of which classifier new_unit: {int((pop.role=="new_unit").sum())})')

# ============================================================ oracle signals (read-only; pooled, displayed)
# HCD oracle
hcd_apn = set(C(a) for (a,) in ro(HCD).execute(
    "select APN from table_a2 where upper(coalesce(UNIT_CAT,''))='ADU'") if C(a))
# Assessor Imps
imps = {}
for a, v in ro(ASSESS).execute('select APN, Imps from parcels'):
    ca = C(a)
    if ca:
        try: imps[ca] = float(str(v).replace('$','').replace(',',''))
        except Exception: pass
# footprints (reuse JN-D cache if present; else flag unavailable)
fp_count = {}
fp_cache = os.path.join(JNDOUT, '_oracle_cache', 'footprints.json')
if os.path.exists(fp_cache):
    for r in json.load(open(fp_cache)):
        ca = C(r.get('PARCELID'))
        if ca: fp_count[ca] = fp_count.get(ca, 0) + 1
    print(f'[oracle] footprints loaded from JN-D cache: {len(fp_count)} parcels')
else:
    print('[oracle] footprint cache not found — footprint votes = unavailable (run JN-D first to populate)')

# calibrate Imps reference from the 446 known-good agree-ADUs (HCD-confirmed finaled new_unit)
agree = pop[(pop.role=='new_unit') & pop.finaled & pop.apn_canon.isin(hcd_apn)]
agree_imps = sorted(v for v in (imps.get(a) for a in agree.apn_canon) if v and v>0)
IMPS_REF = agree_imps[len(agree_imps)//4] if agree_imps else None    # p25 of known-good
print(f'[calibration] Imps p25 of {len(agree_imps)} known-good ADUs -> IMPS_REF={IMPS_REF}')

def oracle_votes(apn, finaled):
    """Each oracle: 'agree' / 'silent' / 'dissent'. Silence is NEUTRAL (I2)."""
    v = {}
    v['hcd']       = 'agree' if apn in hcd_apn else 'silent'           # concordant; absence = silent (could be under-report)
    im = imps.get(apn)
    v['imps']      = ('agree' if (im and IMPS_REF and im>=IMPS_REF) else 'silent')  # lag -> silent, never dissent
    fc = fp_count.get(apn) if fp_count else None
    # POSITIVE-ONLY (change 1): >=2 structures = agree; 1 / 0 / no-match / no-cache all = abstain (NEVER dissent).
    # Join diagnostic: footprint=1 is 44.6% false on real detached ADUs -> carries no negative information.
    v['footprint'] = 'agree' if (fc is not None and fc >= 2) else 'abstain'
    v['addrpoint'] = 'unavailable'                                    # 404'd this session; slot reserved
    return v

def pool_confidence(interior, votes):
    """
    Two-tier combine. Interior sets the BASELINE; oracles only ADD (change 1: agree-or-abstain — NO oracle
    may subtract). I1: role already fixed by classify upstream; this only returns a number.
    I2: 'silent'/'abstain'/'unavailable' contribute 0 (never lower). Only 'agree' raises.
    """
    conf = interior
    for k, val in votes.items():
        if val == 'agree': conf += AGREE_BONUS.get(k, 0.0)          # only 'agree' adds; everything else = 0
    return max(0.0, min(1.0, conf))

# ============================================================ score the population
rows = []
for _, r in pop.iterrows():
    votes = oracle_votes(r['apn_canon'], r['finaled'])
    ic    = interior_confidence(r['wd'], r['role'])
    conf  = pool_confidence(ic, votes)
    rationale = (f"role={r['role']} via interior; " +
                 ", ".join(f"{k}:{val}" for k,val in votes.items() if val!='unavailable'))
    rows.append(dict(skey=r['skey'], apn=r['apn_canon'], role=r['role'], finaled=bool(r['finaled']),
                     interior_confidence=round(ic,3), confidence=round(conf,3),
                     hcd=votes['hcd'], imps=votes['imps'], footprint=votes['footprint'],
                     wd=(r['wd'] or '')[:80], rationale=rationale))
S = pd.DataFrame(rows)

# ----- band thresholds SEEDED from INTERIOR confidence (change 2), not from HCD-confirmed cases -----
# A strong-interior ADU clears HIGH on DESCRIPTION ALONE (zero oracles); a medium-interior new_unit needs
# ONE primary oracle to cross. HIGH = medium-new_unit baseline + the HCD agree lift.
HI = round(IC_NEWUNIT_PROSE + AGREE_BONUS['hcd'], 2)   # 0.75 + 0.03 = 0.78
LO = 0.60
def band(c): return 'high' if c>=HI else ('medium' if c>=LO else 'low')
S['band'] = S['confidence'].map(band)
print(f'[calibration] band thresholds SEEDED from INTERIOR confidence: HIGH>={HI}  MEDIUM>={LO}')
print(f'              interior tiers: strong={IC_STRONG} clears HIGH UNAIDED · new_unit-prose={IC_NEWUNIT_PROSE} needs +1 oracle · '
      f'weak-only={IC_WEAK} / other-role={IC_OTHER} never reach HIGH')

# ============================================================ calibration readout
print('\n=== confidence distribution ===')
print(S['band'].value_counts().reindex(['high','medium','low']).to_string())
print('\n=== role x band ===')
print(pd.crosstab(S['role'], S['band']).to_string())

def show(title, df):
    print(f'\n--- {title} ---')
    for _, r in df.head(8).iterrows():
        print(f'  {r["confidence"]:.2f} [{r["band"]:6s}] {r["role"]:10s} | hcd:{r["hcd"]:6s} fp:{r["footprint"]:11s} | {r["wd"]}')

# the boundary cases are where calibration succeeds or fails
near_hi = S[(S.confidence>=HI-0.05) & (S.confidence<HI+0.05)].sort_values('confidence')
near_lo = S[(S.confidence>=LO-0.05) & (S.confidence<LO+0.05)].sort_values('confidence')
show(f'AT THE HIGH/MEDIUM BOUNDARY (~{HI}) — should these be high?', near_hi)
show(f'AT THE MEDIUM/LOW BOUNDARY (~{LO}) — should these be low?', near_lo)
# known anchors: do they land where judgment says?
show('weak-only "convert" cases (should be LOW/medium, not high)',
     S[S.wd.str.lower().str.contains('convert') & ~S.wd.str.lower().str.contains('adu|accessory|dwelling')])
print(f'\n[footprint] agree (>=2 structures, positive-only) count: {int((S.footprint=="agree").sum())} of {len(S)}  '
      f'(dissent dropped per join diagnostic)')
show('footprint AGREE (>=2 structures — positive corroboration only; no dissent path)',
     S[S.footprint=='agree'])

S.sort_values(['band','confidence']).to_csv(os.path.join(OUTDIR, 'prototype_scores.csv'), index=False)
print(f'\nwrote {OUTDIR}/prototype_scores.csv  (calibration instrument — nothing persisted to v4)')
print('\nREAD THE BOUNDARY CASES: if a case lands in a band against your judgment, that names a weight or '
      'threshold to tune. The thresholds (HI/LO) and AGREE_BONUS/dissent weights are the knobs.')
