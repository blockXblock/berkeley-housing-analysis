#!/usr/bin/env python3
"""
build_parcel_crosswalk.py — PHASE 1 MACHINERY (READ-ONLY, stages a proposal; NEVER writes).

Resolves prior-APN -> current-parcel lineage for the stale_apn class (the re-platting root
cause). Input: data/audit/shake_findings_<date>_full.json stale_apn findings. Output:
data/staging/parcel_crosswalk_<date>.json (the confidence-gated proposal for John review).

Method: 3-layer crosswalk — improved canon (component-pad handles hyphen/short forms) +
EXACT-address-only candidate finding (NEVER nearest-address: the proj136 trap) + book/page
continuity + Imps/scale match. Danger rules baked in: completed+built only (pipeline/too-new
left alone); stored APN is primary (re-point only on converging evidence); multi-parcel splits
(Acheson) flagged MULTI_SPLIT for manual mapping. Confidence: HIGH (exact-addr + single built
parcel + book/page continuity/scale) / MEDIUM (ambiguous: multi-candidate or Imps=0 lag) /
LOW (re-platted w/ address renumber, no exact match) / LEAVE (pipeline) / FALSE_STALE (canon gap).

PHASE 2 (the gated DB write of confirmed-HIGH re-points + the parcel_crosswalk table) is SEPARATE
and waits for John's review of the HIGH set. This script does not write the DB.
"""
import sqlite3, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from housing_rules import to_canonical_apn   # the SINGLE canon function (Option B, per-county)
v2=sqlite3.connect('file:databases/berkeley_housing_v2.db?mode=ro',uri=True); v2.row_factory=sqlite3.Row
bdb=sqlite3.connect('file:databases/berkeley.db?mode=ro',uri=True)
STUB='2024-01-01'; ASOF='2026-02'
def norm_addr(a):
    if not a: return ('','')
    s=a.lower(); s=re.sub(r'\s+berkeley\s*,?\s*(ca\s*)?\d{5}.*$','',s); s=re.sub(r'\s+berkeley\s*$','',s)
    for w,n in {'first':'1st','second':'2nd','third':'3rd','fourth':'4th','fifth':'5th','sixth':'6th','seventh':'7th','eighth':'8th','ninth':'9th','tenth':'10th'}.items(): s=re.sub(r'\b'+w+r'\b',n,s)
    m=re.match(r'\s*(\d+)',s); num=m.group(1) if m else ''
    st=re.sub(r'\b(ave|avenue|st|street|blvd|way|dr|drive|rd|road|ln|lane|ct|court|pl|place|ter)\b','',s)
    st=re.sub(r'[^a-z0-9 ]',' ',st); st=re.sub(r'^\s*\d+\s*','',st).strip(); st=re.sub(r'\s+',' ',st); return (num,st)
by_canon={}; by_addr={}
for apn,b,p,pa,s,imps,use,situs in bdb.execute("SELECT APN,BOOK,PAGE,PARCEL,SUB_PARCEL,Imps,UseCode,SitusAddre FROM parcels"):
    c=to_canonical_apn(apn,'Alameda')   # the single canon (Option B)
    if not c: continue
    rec={'apn':apn,'canon':c,'imps':imps or 0,'use':str(use or ''),'situs':situs}
    by_canon[c]=rec
    na=norm_addr(situs)
    if na[0]: by_addr.setdefault(na,[]).append(rec)
def finaled(pid):
    return v2.execute("SELECT COUNT(*) FROM permits WHERE project_id=? AND completion_verdict='completes' AND finaled_date IS NOT NULL AND finaled_date!=''",(pid,)).fetchone()[0]>0
d=json.load(open('data/audit/shake_findings_2026-06-16_full.json'))
results=[]
for f in d['findings_by_check']['stale_apn']:
    pid=f['key']; raw=f['evidence'].get('stored_apn'); addr=f['evidence'].get('addr')
    p=v2.execute("SELECT total_units,co_issued_date FROM v_projects_flat WHERE project_id=?",(pid,)).fetchone()
    units=p['total_units'] if p else None; co=p['co_issued_date'] if p else None
    completed=(co and co!=STUB) or finaled(pid)
    R={'project_id':pid,'addr':addr,'stored_apn':raw,'units':units,'completed':bool(completed),'co_date':co}
    if raw and ',' in raw:
        R.update(confidence='MULTI_SPLIT',note='umbrella w/ multiple stored APNs (Acheson) — handle as split'); results.append(R); continue
    ci=to_canonical_apn(raw,'Alameda'); R['canon']=ci
    if ci and ci in by_canon:
        R.update(confidence='FALSE_STALE',note='resolves with component-pad canon — NOT re-platted (detector canon gap)',proposed_apn=by_canon[ci]['apn'],proposed_imps=by_canon[ci]['imps']); results.append(R); continue
    if not completed:
        R.update(confidence='LEAVE',note='pipeline/in-review or stub-only — may be too-new, NOT re-platted; leave'); results.append(R); continue
    na=norm_addr(addr)
    if not na[0] or na[0]=='0':
        R.update(confidence='LOW',note='no resolvable house number ("0 X") — John-verify'); results.append(R); continue
    cands=by_addr.get(na,[]); built=[c for c in cands if c['imps']>0]
    bp='-'.join(ci.split('-')[:2]) if ci else None; bp_cont=[c for c in built if '-'.join(c['canon'].split('-')[:2])==bp]   # book-page (B form)
    ev=[]; 
    if cands: ev.append('exact_address')
    if len(built)==1: ev.append('single_built_parcel')
    if bp_cont: ev.append('book_page_continuity')
    scale_ok=False
    if built and units:
        top=max(built,key=lambda x:x['imps'])
        if top['imps']>=max(150000,units*120000)*0.4: scale_ok=True; ev.append('imps_scale_match')
    if len(built)==1 and cands and (bp_cont or scale_ok): conf='HIGH'; pr=built[0]
    elif built and cands: conf='MEDIUM'; pr=max(built,key=lambda x:x['imps'])
    elif cands and not built: conf='MEDIUM'; pr=cands[0]
    else: conf='LOW'; pr=None
    R.update(confidence=conf,evidence=ev,n_exact_candidates=len(cands),n_built=len(built),
             proposed_apn=(pr['apn'] if pr else None),proposed_canon=(pr['canon'] if pr else None),
             proposed_imps=(pr['imps'] if pr else None),proposed_situs=(pr['situs'] if pr else None),
             proposed_usecode=(pr['use'] if pr else None))
    results.append(R)

# ---- Acheson split (proj178 umbrella) ----
ach=[c for c in (by_canon[k] for k in by_canon) if c['canon'].startswith('057-2046') and c['imps']>0]
ach_b8=[c for c in ach if c['apn'].startswith('57-2046-8') or '2046-8' in c['apn']]
acheson={'umbrella':178,'stored_apns':'57-2046-8-3/8-2/6-0/10-0','current_built_parcels_block_57-2046':
         [{'apn':c['apn'],'imps':c['imps'],'situs':c['situs']} for c in sorted(ach,key=lambda x:-x['imps'])[:8]]}

from collections import Counter
cc=Counter(r['confidence'] for r in results)
print("=== SUMMARY (71) ===",dict(cc))
# coverage impact: HIGH re-points that are completed -> gain assessed value + pass built_vs_vacant + de-list blindspot
high=[r for r in results if r['confidence']=='HIGH']
high_built=[r for r in high if r.get('proposed_imps',0)>0]
print(f"\nCOVERAGE IMPACT (HIGH set, {len(high)}):")
print(f"  -> {len(high_built)} completions gain a current BUILT parcel = +assessed value (91%->{round(100*(640+len(high_built))/703)}% of completed) + pass built_vs_vacant")
bs={f['evidence']['apn'] for f in d['findings_by_check']['block_cohort']}
delisted=[r for r in high if r.get('proposed_apn') in bs]
print(f"  -> {len(delisted)} HIGH proposals are CURRENT blind-spot parcels (de-list on re-point): {[ (r['project_id'],r['proposed_apn']) for r in delisted]}")

out={'generated':'2026-06-16','source':'shake_findings_2026-06-16_full.json stale_apn (71)','as_of':ASOF,
     'method':'3-layer crosswalk: improved canon + EXACT-address-only + book/page continuity + imps/scale. Danger rules: never nearest-address; completed+built only; stored APN primary.',
     'summary':dict(cc),'acheson_split':acheson,'results':results}
import os; os.makedirs('data/staging',exist_ok=True)
json.dump(out,open('data/staging/parcel_crosswalk_2026-06-16.json','w'),indent=1,default=str)
print("\nstaged -> data/staging/parcel_crosswalk_2026-06-16.json")
# print HIGH with situs for eyeball
print("\n=== HIGH re-points (with proposed situs for eyeball) ===")
for r in high:
    print(f"  proj{r['project_id']:>3} '{r['addr']}' {r['units']}u  {r['stored_apn']} -> {r['proposed_apn']} (${r['proposed_imps']:,.0f}) situs='{r['proposed_situs']}'")
