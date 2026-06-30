"""Build JN-D_bijection_viz.ipynb — the VIZ COMPANION to the build_jn_d.py ADU-bijection engine.

NON-DESTRUCTIVE: does not touch the engine. The engine does the heavy GIS-oracle bijection and writes its
CSV output + asserts the EXP anchors. This companion RE-DERIVES the cheap headline counts (HCD anchor /
matched / missing) live from v4+HCD, GATES them against the engine's EXP anchors (parsed from build_jn_d.py —
one source of truth), and renders the approved viz. Because both read the same anchors, the two can't disagree;
if the live re-derivation != EXP, the companion HALTs (it has drifted from the engine — investigate).

Run: python scripts/v4/build_jn_d_viz.py
"""
import os, re, sqlite3, sys
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
V4   = os.path.join(ROOT, 'databases', 'berkeley_housing_v4.db')
HCD  = os.path.join(ROOT, 'databases', 'hcd_apr_mirror_2026-06-17_fresh.db')
ENGINE = os.path.join(ROOT, 'scripts', 'v4', 'build_jn_d.py')
CSV  = os.path.join(ROOT, 'scratch', '2026-06-26', 'jn_d_out', 'jn_d_bijection_oracled.csv')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-D_bijection_viz.ipynb')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from housing_rules import to_canonical_apn
def C(r):
    try: return to_canonical_apn(r, 'Alameda') or None
    except Exception: return None
def ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)

def parse_exp():
    s = open(ENGINE).read(); blk = s[s.index('EXP = dict('): s.index('EXP = dict(') + 700]
    return {k: int(v) for k, v in re.findall(r'(\w+)\s*=\s*(\d+)', blk)}

def derive():
    EXP = parse_exp()
    hc = ro(HCD); v4 = ro(V4)
    hcd_apns = {C(r[0]) for r in hc.execute("SELECT APN FROM table_a2 WHERE upper(coalesce(UNIT_CAT,''))='ADU'") if C(r[0])}
    v4_apns  = {C(r[0]) for r in v4.execute("SELECT DISTINCT raw_apn FROM events") if C(r[0])}
    matched  = hcd_apns & v4_apns
    live = dict(hcd_anchor=len(hcd_apns), match_any_role=len(matched), missing=len(hcd_apns) - len(matched))
    # GATE: live re-derivation must equal the engine's asserted anchors
    fails = [f"{k}: live {live[k]} != EXP {EXP[k]}" for k in live if live[k] != EXP.get(k)]
    if fails:
        raise AssertionError("JN-D viz companion DRIFTED from the engine — HALT:\n  " + "\n  ".join(fails))
    return EXP, live

cells = []
def md(t): cells.append(new_markdown_cell(t.strip("\n")))
def code(s): cells.append(new_code_cell(s.strip("\n")))

EXP, live = derive()  # build-time gate (proves the companion agrees with the engine before emitting)

md("""
# JN-D — ADU bijection: VIZ COMPANION

**What this is.** The **visualization companion** to the `build_jn_d.py` ADU-bijection **engine**. Separation
of concerns: the **engine** does the heavy GIS-oracle triangulation (Imps / footprints / address-points) and
asserts its `EXP` anchors; **this companion** re-derives the *cheap* headline counts (HCD anchor / matched /
missing) live from v4+HCD and **gates them against those same EXP anchors** — so the engine and the picture
**cannot disagree**. If the live re-derivation ≠ EXP, the companion HALTs (it drifted; investigate).

**Derive-from-data + gate:** the headline (842/839/3) is re-derived live and asserted == the engine's EXP;
the finer figures (regr_adu_only, hardened_new_unit, the band, finaled split) are the engine's **asserted
constants** (parsed from `build_jn_d.py`'s EXP — one source of truth), and the per-row bucket *texture* is read
from the engine's output CSV with provenance.
""")

md("""
## §1 — Setup + the gate (companion ≡ engine)
""")
code("""
import os, re, sqlite3, sys
import plotly.graph_objects as go
ROOT=os.path.expanduser('~/berkeley-data')
V4=os.path.join(ROOT,'databases','berkeley_housing_v4.db'); HCD=os.path.join(ROOT,'databases','hcd_apr_mirror_2026-06-17_fresh.db')
sys.path.insert(0,os.path.join(ROOT,'scripts')); from housing_rules import to_canonical_apn
def C(r):
    try: return to_canonical_apn(r,'Alameda') or None
    except Exception: return None
def ro(p): return sqlite3.connect(f'file:{p}?mode=ro',uri=True)
# EXP anchors parsed from the engine (one source of truth)
_s=open(os.path.join(ROOT,'scripts','v4','build_jn_d.py')).read(); _b=_s[_s.index('EXP = dict('):_s.index('EXP = dict(')+700]
EXP={k:int(v) for k,v in re.findall(r'(\\w+)\\s*=\\s*(\\d+)',_b)}
# live re-derivation (cheap, no GIS engine)
hcd={C(r[0]) for r in ro(HCD).execute("SELECT APN FROM table_a2 WHERE upper(coalesce(UNIT_CAT,''))='ADU'") if C(r[0])}
v4a={C(r[0]) for r in ro(V4).execute("SELECT DISTINCT raw_apn FROM events") if C(r[0])}
matched=hcd & v4a
live=dict(hcd_anchor=len(hcd), match_any_role=len(matched), missing=len(hcd)-len(matched))
for k in live:
    assert live[k]==EXP[k], f'COMPANION DRIFT: {k} live {live[k]} != engine EXP {EXP[k]}'
print('GATE PASS — companion re-derivation == engine EXP:', live)
""")
md("""
**Gate.** The three headline counts are re-derived from v4+HCD and **asserted == the engine's EXP**. A
mismatch HALTs — meaning the companion's cheap path diverged from the engine's; that's a real finding to
investigate, not something to paper over.
""")

md("""
## §2 — VIZ D1: the bijection (HCD-anchored)
**What it shows.** Of the city's **842** ADU APNs (the HCD anchor), how many **WE** match (839) vs miss (3) —
APN grain, all three live-derived + gated. Then the **per-v4-permit-row bucket texture** (the engine's actual
output) showing *how* those APNs are seen in v4.
""")
code("""
# VIZ D1a — APN-grain Sankey (conserved + gated): 842 -> 839 matched + 3 missing
a=EXP['hcd_anchor']; m=EXP['match_any_role']; miss=EXP['missing']
figS=go.Figure(go.Sankey(
  node=dict(label=[f'HCD ADU anchor {a}', f'matched in v4 {m}', f'missing from v4 {miss}'],
            color=['#444','#2ca02c','#d62728'], pad=20, thickness=18),
  link=dict(source=[0,0], target=[1,2], value=[m,miss],
            color=['rgba(44,160,44,0.5)','rgba(214,39,40,0.6)'])))
figS.update_layout(title=f'ADU bijection (APN grain, gated): {a} HCD ADU APNs -> {m} matched + {miss} missing', height=320)
figS.show()

# VIZ D1b — per-permit-row bucket texture (engine output CSV, ROW grain, provenance)
import csv, collections, os
CSV=os.path.join(ROOT,'scratch','2026-06-26','jn_d_out','jn_d_bijection_oracled.csv')
if os.path.exists(CSV):
    bk=collections.Counter(r['bucket'] for r in csv.DictReader(open(CSV)))
    items=sorted(bk.items(), key=lambda x:-x[1])
    figB=go.Figure(go.Bar(x=[v for _,v in items], y=[k for k,_ in items], orientation='h',
                          text=[v for _,v in items], textposition='outside'))
    figB.update_layout(title=f'v4-permit-ROW buckets over the {a} HCD ADU APNs ({sum(bk.values()):,} rows — engine output, row grain)',
                       xaxis_title='v4 permit-rows', height=400)
    figB.show()
    print('bucket texture (row grain, from engine CSV):', dict(items))
else:
    print('engine CSV absent — run build_jn_d.py to regenerate jn_d_bijection_oracled.csv (buckets shown from EXP only)')
""")
md("""
**⚠ viz-verifiability.**
- **HCD is the ANCHOR/enumerator** (the *city's* ADU set). This shows *of the city's ADUs, how many WE match* —
  the **3 missing are OUR coverage gaps to investigate, NOT "the city is wrong"** (oracle-not-source, at the
  bijection layer).
- **Two grains, kept distinct:** the Sankey is **APN grain** (842/839/3, gated to the engine). The bucket bar
  is **v4-permit-ROW grain** (~3,175 rows over the 842 APNs — an APN appears in *multiple* buckets), read from
  the engine's output CSV (provenance). **Don't read the bucket counts as APN counts** — different denominator.
- The named EXP cuts (`regr_adu_only={regr}`, `hardened_new_unit={hard}`) are *derived cuts*, not buckets in
  this bar; the hardened set is in VIZ D2.
""".replace('{regr}', str(EXP.get('regr_adu_only','?'))).replace('{hard}', str(EXP.get('hardened_new_unit','?'))))

md("""
## §3 — VIZ D2: the hardened-new_unit band + finaled split
**What it shows.** The hardened new_unit set isn't a point — it's a **band** (floor ↔ ceiling, dedup-dependent),
split into finaled vs pending. All from the engine's EXP anchors.
""")
code("""
floor=EXP.get('band_floor'); ceil=EXP.get('band_ceiling'); fin=EXP.get('finaled'); nfin=EXP.get('not_finaled')
fig=go.Figure()
fig.add_bar(name='finaled', x=['hardened new_unit'], y=[fin], text=[f'finaled {fin}'], textposition='inside')
fig.add_bar(name='not finaled (pending)', x=['hardened new_unit'], y=[nfin], text=[f'pending {nfin}'], textposition='inside')
# the band drawn as floor/ceiling reference lines (NOT a single point)
fig.add_hline(y=floor, line_dash='dot', annotation_text=f'band floor {floor}', line_color='#888')
fig.add_hline(y=ceil,  line_dash='dot', annotation_text=f'band ceiling {ceil}', line_color='#444')
fig.update_layout(barmode='stack', title=f'hardened new_unit: band {floor}-{ceil} · finaled {fin} + pending {nfin}',
                  yaxis_title='units', height=420)
fig.show()
print(f'band floor={floor} ceiling={ceil}; finaled={fin} not_finaled={nfin} (sum {fin+nfin} == ceiling {ceil})')
""")
md("""
**⚠ mislead-guard.** **531–584 is an uncertainty BAND, not a point** (it moves with dedup). A single bar would
imply false precision — the floor/ceiling reference lines make the range visible. The finaled/pending split
(441/143) sums to the ceiling (584); "pending" are real-but-not-yet-finaled, not absent.
""")

nb = new_notebook(cells=cells, metadata={'kernelspec': {'name':'python3','display_name':'Python 3'}})
os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
with open(NB_OUT, 'w') as f: nbf.write(nb, f)
if __name__ == '__main__':
    print('GATE (build-time) PASS:', live, '== engine EXP subset')
    print(f'emitted: {os.path.relpath(NB_OUT, ROOT)} ({len(cells)} cells)')
