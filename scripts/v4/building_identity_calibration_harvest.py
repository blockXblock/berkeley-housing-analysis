"""CALIBRATION HARVEST v3 — adds BASE-FAMILY COLLAPSE on top of v2's evidence-positive grouping.
-REV/-DEF children are REVISIONS of the base permit (link_role=revision), EXCLUDED from representative
selection + the tie rule. DATA PRESERVED: if a revision carries a unit-count the base lacks, it is re-homed
(building uc = family max), never dropped. Re-run, compare to v2 (372-tie). Read-only; scratch CSV."""
import sqlite3, os, sys, re
import pandas as pd
from collections import defaultdict
ROOT=os.path.expanduser('~/berkeley-data'); OUT=os.path.join(ROOT,'scratch','2026-06-29')
def ro(p): return sqlite3.connect(f'file:{p}?mode=ro',uri=True)
sys.path.insert(0,os.path.join(ROOT,'scripts'))
from housing_rules import to_canonical_apn
def C(r):
    try: return to_canonical_apn(r,'Alameda') or None
    except Exception: return None
con=ro(os.path.join(ROOT,'databases','berkeley_housing_v4.db'))

SITEWORK=re.compile(r'foundation|podium|grading|shoring|excavation',re.I)
ANCIL=re.compile(r'\bsolar\b|\bpv\b|\bmeter\b|service upgrade|\breroof\b|re-?roof|water heater|furnace|panel upgrade',re.I)
XREF=re.compile(r'\bB20\d{2}-\d{4,5}\b'); PHASE=re.compile(r'\bphase\s+(?:[ivx]+|\d+)\b',re.I)
LABEL=re.compile(r'\bbuilding\s+([A-Z]|\d+)\b(?!\s+(?:elements|maintenance|permit|department))|\b(north|south|east|west)\s+building\b',re.I)
MULTIFAM=re.compile(r'apartment|multi-?family|mixed[\s-]?use|-story|dwelling units|group living|congregate|live-?work|townhome|residential building|residential development',re.I)
EXCL=re.compile(r'\b(?:except|excluding|other than)\b[^.]*',re.I)
REFGOV=re.compile(r'(?:foundation|podium|grading|shoring|excavation)[^.]*?\b(?:under|by|per|permit)\b[^.]*?B20\d{2}-\d{4,5}',re.I)
def clean_role(wd): return REFGOV.sub(' ',EXCL.sub(' ',wd or ''))
def role(wd):
    s=clean_role(wd)
    if ANCIL.search(s) and not re.search(r'\bnew\b.{0,15}\b(adu|dwelling|unit|building|residence)\b',s,re.I): return 'ancillary'
    if SITEWORK.search(s): return 'sitework'
    return 'completion'
def label(wd):
    m=LABEL.search(wd or ''); return ((m.group(1) or m.group(2)).upper()) if m else None
def ucount(wd):
    s=wd or ''; n=[int(x) for x in re.findall(r'(\d{1,4})\s*-?\s*(?:dwelling|sleeping|live[\s/-]*work|residential|rental)?\s*-?\s*units?\b',s,re.I)]
    base=max(n) if n else None
    if re.search(r'\b(?:one|1)\b[^.]{0,20}manager',s,re.I): base=(base or 0)+1
    if base is None and re.search(r'single family residence|\bsfr\b|single-family',s,re.I): base=1
    return base
def basekey(sk): return re.sub(r'-(REV|DEF)\d+$','',sk,flags=re.I)
def is_rev(sk): return sk!=basekey(sk)

ev=pd.read_sql("""SELECT e.source_record_key skey,e.raw_apn,e.event_type_code etc,c.housing_role hr,
   json_extract(e.raw_payload,'$.WorkDescription') wd FROM events e LEFT JOIN event_classifications c ON c.event_id=e.event_id""",con)
ev['apn']=ev['raw_apn'].map(C)
def agg(g):
    fin=g[g.etc=='permit_finaled']; rep=fin.iloc[0] if len(fin) else g.iloc[0]
    return pd.Series(dict(apn=next((x for x in g.apn if x),None),hr=rep.hr,wd=next((x for x in g.wd if x),'')))
perm=ev.groupby('skey').apply(agg,include_groups=False).reset_index()
fy=pd.read_sql("SELECT source_record_key skey,CAST(strftime('%Y',MIN(event_date)) AS INT) fy FROM events WHERE event_type_code='permit_finaled' GROUP BY 1",con)
perm=perm.merge(fy,on='skey',how='left')
perm['uc']=perm.wd.map(ucount); perm['role']=perm.wd.map(role); perm['lab']=perm.wd.map(label)
perm['has_xref']=perm.wd.map(lambda s:bool(XREF.search(s or ''))); perm['has_phase']=perm.wd.map(lambda s:bool(PHASE.search(s or '')))
perm['mf']=perm.wd.map(lambda s:bool(MULTIFAM.search(s or ''))); perm['base']=perm.skey.map(basekey)
perm['bs']=perm.apply(lambda r:(r.role!='ancillary') and (r.mf or (r.uc or 0)>=2 or r.has_phase),axis=1)
P=perm.set_index('skey')

def is_cand(r): return (r.hr in ('new_unit','ambiguous')) or r.mf or (r.uc or 0)>=2 or r.lab is not None or r.has_phase or r.has_xref
cand=set(perm[perm.apply(is_cand,axis=1)].skey)
for sk in list(cand):
    for ref in XREF.findall(str(P.loc[sk,'wd'] or '')):
        if ref in P.index: cand.add(ref)
pop=set(perm[perm.skey.isin(cand)].skey)

parent={s:s for s in pop}
def find(x):
    while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
    return x
def union(a,b):
    if a in parent and b in parent: parent[find(a)]=find(b)
for base,g in perm[perm.skey.isin(pop)].groupby('base'):
    ks=list(g.skey); [union(ks[0],k) for k in ks[1:]]
for sk in pop:
    for ref in XREF.findall(str(P.loc[sk,'wd'] or '')):
        if ref in parent: union(sk,ref)
for apn,g in perm[perm.skey.isin(pop)].groupby('apn'):
    if apn is None: continue
    for lab,gl in g.groupby(g.lab.fillna('__none__')):
        m=gl.to_dict('records')
        for i in range(len(m)):
            for j in range(i+1,len(m)):
                a,b=m[i],m[j]
                if a['uc'] is not None and a['uc']==b['uc']: union(a['skey'],b['skey'])
                elif a['has_phase'] and b['has_phase'] and a['bs'] and b['bs'] and pd.notna(a['fy']) and pd.notna(b['fy']) and abs(a['fy']-b['fy'])<=2:
                    union(a['skey'],b['skey'])
comp=defaultdict(list)
for s in pop: comp[find(s)].append(s)

def rank(c): return {'high':2,'med':1,'low':0}[c]
rows=[]; dissolved=[]; rehomed=[]; bid=0
def emit(sub,lab,kind):
    global bid; bid+=1; b=f'B3_{bid:04d}'
    g=sub.copy(); g['rev']=g.skey.map(is_rev); apns=set(a for a in g.apn if a)
    nonrev=g[~g.rev]; nonsite_nonrev=nonrev[~nonrev.role.isin(['sitework','ancillary'])]
    if len(g)==1: rep,rc,rs=g.iloc[0].skey,'high','single'
    elif len(nonsite_nonrev)==1: rep,rc,rs=nonsite_nonrev.iloc[0].skey,'high','sole_completion'
    elif len(nonsite_nonrev)>=2: rep,rc,rs=nonsite_nonrev.sort_values(['uc','skey'],ascending=[False,True]).iloc[0].skey,'low','ambiguous_tie'
    elif len(nonrev)>=1: rep,rc,rs=nonrev.sort_values(['uc','skey'],ascending=[False,True]).iloc[0].skey,'med','base_fallback'
    else: rep,rc,rs=g.sort_values(['uc','skey'],ascending=[False,True]).iloc[0].skey,'low','all_revision'
    fam_max=g.uc.dropna().max() if g.uc.notna().any() else None
    base_uc=g.loc[g.skey==rep,'uc'].iloc[0]
    if fam_max is not None and (pd.isna(base_uc) or base_uc<fam_max):
        carrier=g.sort_values('uc',ascending=False).iloc[0]
        if carrier.rev:
            rehomed.append(dict(building=b,base=rep,base_uc=(None if pd.isna(base_uc) else int(base_uc)),carrier=carrier.skey,rehomed_units=int(fam_max)))
    inferred=int(fam_max) if fam_max is not None else None
    if str(lab).startswith('Building '): gc='high'; sig='building_label'
    elif g.rev.any() or g.has_xref.any(): gc='high'; sig='xref/base'
    elif g.uc.notna().any() and len(g)>=2 and g.uc.nunique()<g.uc.notna().sum(): gc='high'; sig='shared_unit_count'
    elif g.has_phase.any() and len(g)>=2: gc='med'; sig='phase+temporal'
    else: gc='high' if kind!='multi' else 'low'; sig=kind
    eff_roles=sorted(set(('revision' if r.rev else r.role) for _,r in g.iterrows()))
    flags=[]
    if kind=='label_singleton': flags.append('labeled_singleton')
    if kind=='housing_singleton': flags.append('housing_singleton_kept')
    if len(apns)>=2: flags.append('cross_apn_same_building')
    if rs=='ambiguous_tie': flags.append('representative_tie')
    if g.rev.any(): flags.append('revision_family')
    if len(g)>=4: flags.append('large_cluster')
    rows.append(dict(building_id=b,apns='|'.join(sorted(apns)),label=lab,n=len(g),signal=sig,
        members='|'.join(sorted(g.skey)),inferred_units=inferred,grouping_confidence=gc,
        representative=rep,representative_confidence=rc,representative_status=rs,
        roles='|'.join(eff_roles),kind=kind,flag_notes=';'.join(flags) or '-',sort_key=rank(gc)*10+rank(rc)))

for root,mem in comp.items():
    sub=perm[perm.skey.isin(mem)]
    if len(mem)>=2:
        labs=set(sub.lab.dropna())
        if len(labs)>=2:
            for l in sorted(labs): emit(sub[sub.lab==l],f'Building {l}','multi')
            resid=sub[sub.lab.isna()]
            if len(resid): emit(resid,'(unlabeled-residual)','multi')
        else:
            only=list(labs)[0] if labs else None
            emit(sub,f'Building {only}' if only else '(single)','multi')
    else:
        r=sub.iloc[0]
        if r.lab is not None: emit(sub,f'Building {r.lab}','label_singleton')
        elif r.hr in ('new_unit','ambiguous'): emit(sub,'(housing-singleton)','housing_singleton')
        else: dissolved.append(r.skey)

B=pd.DataFrame(rows).sort_values(['sort_key','n'],ascending=[True,False])
B.to_csv(OUT+'/calibration_harvest_v3.csv',index=False)
B['has_rev']=B.members.map(lambda m: any(is_rev(s) for s in m.split('|')))
multi=B[B.kind=='multi']
V2=dict(buildings=3777,multi=578,tie=372)
print('='*92); print('CALIBRATION HARVEST v3 — base-family collapse — BEFORE/AFTER vs v2'); print('='*92)
print(f"  buildings: v2 {V2['buildings']} -> v3 {len(B)} (multi {len(multi)} + singletons {len(B)-len(multi)})")
tie=int((B.representative_status=='ambiguous_tie').sum())
print(f"  ambiguous_tie: v2 {V2['tie']} -> v3 {tie}   (expect ~53)")
print(f"  representative_status dist: {B.representative_status.value_counts().to_dict()}")
print(f"  REV/DEF-family buildings: {int(B.has_rev.sum())}  · of which still tie: {int(B[B.has_rev & (B.representative_status=='ambiguous_tie')].shape[0])} (expect ~0)")
print(f"  revision-families resolved to base (sole_completion/base_fallback/single): {int(B[B.has_rev & B.representative_status.isin(['sole_completion','base_fallback','single'])].shape[0])}")

print('\n--- REGRESSION GUARD: the 9 known cases ---')
GT={'057-2046-001-00':(1,163),'057-2025-013-00':(1,81),'055-1819-001-02':(1,78),'056-1928-019-00':(1,41),'056-1945-007-04':(2,8),'052-1516-024-00':(3,3)}
ok9=True
for apn,(gn,gu) in GT.items():
    bs=B[B.apns.str.contains(apn,regex=False)]; n=len(bs); u=int(bs.inferred_units.dropna().sum())
    good=(n==gn and u==gu); ok9&=good
    print(f"  {apn}: {n} bldg / {u} units vs {gn}/{gu} {'✓' if good else '✗ BROKEN'}")
print(f"  REGRESSION: {'ALL 9 INTACT ✓' if ok9 else '✗ HALT'}")

print('\n--- DATA-PRESERVATION CHECK (revision-carried counts re-homed, not dropped) ---')
print(f"  re-homed unit-counts (REV/DEF carried a count the base lacked): {len(rehomed)}")
for r in rehomed[:12]: print(f"     {r['building']}: base {r['base']} (uc={r['base_uc']}) <- revision {r['carrier']} carried {r['rehomed_units']} (kept on building)")
loss=0
for _,row in B.iterrows():
    fam=[P.loc[s,'uc'] for s in row.members.split('|')]; fam=[x for x in fam if pd.notna(x)]
    if fam and (row.inferred_units is None or row.inferred_units<max(fam)): loss+=1
print(f"  buildings where a member unit-count exceeds building inferred_units (DROPPED data): {loss} (must be 0)")

print('\n--- HOUSING GUARD ---')
hd=[s for s in dissolved if P.loc[s,'hr'] in ('new_unit','ambiguous')]
print(f"  new_unit/ambiguous dissolved: {len(hd)} (must be 0)")
print('--- 0-ERASURE GUARD ---')
erase=multi[multi.members.map(lambda m: len({label(P.loc[s,'wd']) for s in m.split('|') if label(P.loc[s,'wd'])})>=2)]
print(f"  buildings merging >=2 distinct labels: {len(erase)} (must be 0)")

print('\n--- GENUINE-HARD ADJUDICATION SET ---')
real_tie=multi[(multi.representative_status=='ambiguous_tie')&(multi.inferred_units.notna())]
cx=int(B.flag_notes.str.contains('cross_apn').sum()); lc=int(B.flag_notes.str.contains('large_cluster').sum()); ur=int((B.label=='(unlabeled-residual)').sum())
print(f"  real ambiguous_tie (units present): {len(real_tie)} · cross_apn: {cx} · large_cluster: {lc} · unlabeled-residual: {ur}")
print(f"  => genuine-hard total ≈ {len(real_tie)+cx+lc+ur}")
print('\nwrote calibration_harvest_v3.csv. Read-only; nothing committed.')
