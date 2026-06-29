"""PROTOTYPE building-identity layer v2 — 3 fixes applied. Read-only on v4; scratch CSVs only.
FIX1 clause/reference-aware roles · FIX2 per-dimension confidence · FIX3 ambiguous-tie representative."""
import sqlite3, os, sys, re
import pandas as pd
ROOT=os.path.expanduser('~/berkeley-data'); OUT=os.path.join(ROOT,'scratch','2026-06-29')
def ro(p): return sqlite3.connect(f'file:{p}?mode=ro',uri=True)
sys.path.insert(0,os.path.join(ROOT,'scripts'))
from housing_rules import to_canonical_apn
def C(r):
    try: return to_canonical_apn(r,'Alameda') or None
    except Exception: return None
con=ro(os.path.join(ROOT,'databases','berkeley_housing_v4.db'))

PERMITS=['B2019-05608','B2021-04893','B2021-05812','B2022-01111','B2019-01150','B2019-01950',
         'B2021-02423','B2021-04949','B2019-02824','B2019-02831','B2018-01346','B2018-01347','B2018-01348']
GROUNDTRUTH={'057-2046-001-00':(1,163),'057-2025-013-00':(1,81),'055-1819-001-02':(1,78),
  '056-1928-019-00':(1,41),'056-1945-007-04':(2,8),'052-1516-024-00':(3,3)}

rows=[]
for p in PERMITS:
    r=con.execute("""SELECT DISTINCT e.raw_apn, json_extract(e.raw_payload,'$.WorkDescription')
        FROM events e WHERE e.source_record_key=?""",(p,)).fetchone()
    rows.append(dict(permit=p, apn=C(r[0]), wd=r[1] or ''))
P=pd.DataFrame(rows)

SITEWORK=re.compile(r'foundation|podium|grading|shoring|excavation',re.I)
ANCIL=re.compile(r'\bsolar\b|\bpv\b|\bmeter\b|service upgrade',re.I)
XREF=re.compile(r'\bB20\d{2}-\d{4,5}\b')
PHASE=re.compile(r'\bphase\s+(?:[ivx]+|\d+)\b',re.I)
LABEL=re.compile(r'\bbuilding\s+([A-Z]|\d+)\b(?!\s+(?:elements|maintenance))|\b(north|south|east|west)\s+building\b',re.I)
# FIX 1: strip keywords governed by an exclusion clause OR attributed to ANOTHER permit (cross-ref)
EXCL=re.compile(r'\b(?:except|excluding|other than)\b[^.]*', re.I)
REFGOV=re.compile(r'(?:foundation|podium|grading|shoring|excavation)[^.]*?\b(?:under|by|per|permit)\b[^.]*?B20\d{2}-\d{4,5}', re.I)
def clean_for_role(wd):
    s=wd or ''
    s=EXCL.sub(' ', s)      # drop "...except foundation, podium, underground..."
    s=REFGOV.sub(' ', s)    # drop "Foundation under B2021-04949" (foundation is another permit)
    return s

def primary_label(wd):
    m=LABEL.search(wd or '')
    return ((m.group(1) or m.group(2)).upper()) if m else None
def unit_count(wd):
    s=wd or ''
    nums=[int(x) for x in re.findall(r'(\d{1,4})\s*-?\s*(?:dwelling|sleeping|live[\s/-]*work|residential|rental)?\s*-?\s*units?\b',s,re.I)]
    base=max(nums) if nums else None
    if re.search(r'\b(?:one|1)\b[^.]{0,20}manager', s, re.I): base=(base or 0)+1
    if base is None and re.search(r'single family residence|\bsfr\b|single-family', s, re.I): base=1
    m=re.search(r'\band\s+(\d+)\s+townhomes?\b',s,re.I)
    if m and base: base+=int(m.group(1))
    return base
def role(wd):
    s=clean_for_role(wd)
    if ANCIL.search(s) and not re.search(r'\bnew\b.{0,20}\b(adu|dwelling|unit)\b',s,re.I): return 'ancillary'
    if SITEWORK.search(s): return 'sitework'
    return 'completion'

P['label']=P['wd'].map(primary_label); P['uc']=P['wd'].map(unit_count); P['role']=P['wd'].map(role)
P['has_xref']=P['wd'].map(lambda s: bool(XREF.search(s or ''))); P['has_phase']=P['wd'].map(lambda s: bool(PHASE.search(s or '')))

buildings=[]; links=[]; log=[]; bid=0; RULE='proto-v2-2026-06-29'
def add_building(g, label, group_conf, method):
    global bid; bid+=1; b=f'BLD{bid:03d}'
    nonsite=g[~g.role.isin(['sitework','ancillary'])]
    # FIX 3: representative selection + per-dimension representative confidence
    if len(g)==1:
        rep=g.iloc[0].permit; rep_conf='high'; rep_status='single'
    elif len(nonsite)==1:
        rep=nonsite.iloc[0].permit; rep_conf='high'; rep_status='sole_completion'
    elif len(nonsite)>=2:
        rep=nonsite.sort_values(['uc','permit'],ascending=[False,True]).iloc[0].permit; rep_conf='low'; rep_status='ambiguous_tie'
        log.append(dict(building_id=b, action='representative_ambiguous_tie', apn=g.apn.iloc[0],
            candidates='|'.join(sorted(nonsite.permit)), chosen=rep, note='≥2 non-sitework phases tie; pointer is revisable', rule=RULE))
    else:  # all sitework/ancillary -> fallback
        rep=g.sort_values(['uc','permit'],ascending=[False,True]).iloc[0].permit; rep_conf='med'; rep_status='fallback_no_completion'
    buildings.append(dict(building_id=b, apn=g.apn.iloc[0], label=label,
        inferred_unit_count=int(g.uc.dropna().max()), grouping_confidence=group_conf,
        representative_permit_id=rep, representative_confidence=rep_conf, representative_status=rep_status,
        status='active', note=('co_located_distinct' if label.startswith('Building ') else '')))
    for _,r in g.iterrows():
        # FIX 2: role_confidence per link
        if r.role in ('sitework','ancillary'): rconf='high'
        elif len(nonsite)==1: rconf='high'
        else: rconf='med'   # completion among ties / by-default
        links.append(dict(permit_id=r.permit, building_id=b, link_role=r.role, role_confidence=rconf,
            grouping_confidence=group_conf, method=method,
            evidence=(f'xref {XREF.findall(r.wd or "")[:1]}' if r.has_xref else ('phase-lang' if r.has_phase else ('label '+str(r.label) if r.label else 'same APN'))),
            rule_version=RULE))
    log.append(dict(building_id=b, action='group', apn=g.apn.iloc[0], candidates='|'.join(g.permit), chosen=rep, note=label, rule=RULE))

for apn,g in P.groupby('apn'):
    labels=set(g.label.dropna())
    if len(labels)>=2:   # over-merge guard: distinct labels -> distinct buildings
        for lab in sorted(labels):
            add_building(g[g.label==lab].copy(), f'Building {lab}', 'high', 'building_label')
    else:
        method = 'explicit_xref' if g.has_xref.any() else ('phase_lang' if g.has_phase.any() else 'apn_cluster')
        gconf = 'high' if method in ('explicit_xref','phase_lang') else 'low'
        add_building(g.copy(), '(single)', gconf, method)

B=pd.DataFrame(buildings); L=pd.DataFrame(links); LG=pd.DataFrame(log)
B.to_csv(OUT+'/proto_buildings.csv',index=False); L.to_csv(OUT+'/proto_permit_building.csv',index=False); LG.to_csv(OUT+'/proto_grouping_log.csv',index=False)

print('='*96); print('PROTOTYPE v2 (3 fixes) — re-run vs groundtruth'); print('='*96)
print('\n=== permit_building links (role + per-dim confidence) ===')
for _,r in L.sort_values('building_id').iterrows():
    print(f'  {r.permit_id} -> {r.building_id} [{r.link_role:10}] role_conf={r.role_confidence:4} group_conf={r.grouping_confidence:4} {r.method:14} | {r.evidence}')
print('\n=== buildings (grouping vs representative confidence) ===')
for _,r in B.iterrows():
    print(f'  {r.building_id} apn={r.apn} {r.label:12} units={r.inferred_unit_count:>3} | grouping={r.grouping_confidence:4} representative={r.representative_confidence:4} ({r.representative_status}) rep={r.representative_permit_id}')

print('\n=== REGRESSION: per-case vs groundtruth (counts must be unchanged) ===')
allok=True
for apn,(gt_n,gt_u) in GROUNDTRUTH.items():
    bs=B[B.apn==apn]; n=len(bs); u=int(bs.inferred_unit_count.sum()); ok=(n==gt_n and u==gt_u); allok&=ok
    print(f'  {apn}: {n} bldg / {u} units  vs {gt_n}/{gt_u}  {"✓" if ok else "✗"}')
print('\n=== FIX CHECKS ===')
c2=B[B.apn=='057-2025-013-00'].iloc[0]
print(f'  FIX1 case2 representative = {c2.representative_permit_id} (expect B2022-01111 completion, NOT podium B2021-05812) -> {"✓" if c2.representative_permit_id=="B2022-01111" else "✗"}')
c4=B[B.apn=='056-1928-019-00'].iloc[0]
print(f'  FIX1 case4 representative = {c4.representative_permit_id} (expect B2021-02423 completion) -> {"✓" if c4.representative_permit_id=="B2021-02423" else "✗"}; B2021-04949 role={L[(L.permit_id=="B2021-04949")].link_role.iloc[0]} (expect sitework)')
sh=B[B.apn=='057-2046-001-00'].iloc[0]
print(f'  FIX3 Shattuck representative_status={sh.representative_status} conf={sh.representative_confidence} (expect ambiguous_tie/low) -> {"✓" if sh.representative_status=="ambiguous_tie" and sh.representative_confidence=="low" else "✗"}')
print(f'    tie candidates logged: {list(LG[(LG.building_id==sh.building_id)&(LG.action=="representative_ambiguous_tie")].candidates)}')
print(f'\n=== TIERED COUNT ===')
print(f'  buildings: {len(B)} (groundtruth 9)  ·  units: {int(B.inferred_unit_count.sum())}')
print(f'  grouping_confidence: {B.grouping_confidence.value_counts().to_dict()}')
print(f'  representative_confidence: {B.representative_confidence.value_counts().to_dict()}')
print(f'\nRESULT: {"9/9 GROUNDTRUTH HELD ✓" if allok and len(B)==9 else "REGRESSION ✗"}')
print('wrote proto_buildings/permit_building/grouping_log .csv (scratch, uncommitted). v4 untouched.')
