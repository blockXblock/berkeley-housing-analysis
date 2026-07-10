"""Build JN-K_completion_anatomy.ipynb — the completed-housing anatomy JN.

Consolidates the 2026-07-09 deck derivations into the durable, re-runnable home
(scratch/2026-07-09/* was the sketch; this is the record): WHERE the 4,229 completed
units 2018-2025 stand (corridor/fabric), what SIZE built them (<=4u vs >4u), the STAGE
CLOCK on major projects (intake -> consideration -> waiting -> construction, incl. the
deemed-complete milestone), the MAJOR-PIPELINE funnel (denied: 0), and the 2025 ours|city
CO adjudication (+108, every row named).

House pattern (JN-E exemplar): markdown(assumption+plan) -> code -> markdown(found+verify);
derive-and-compare to data/baselines/completion_anatomy_baseline_<date>.json; viz with
mislead-guards; assumptions ledger. Read-only everywhere; writes only its baseline.

Run:  /opt/miniconda3/envs/jupyter_env/bin/python scripts/v4/build_jn_k.py
"""
import os

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-K_completion_anatomy.ipynb')

cells = []
def md(t): cells.append(new_markdown_cell(t.strip('\n')))
def code(s): cells.append(new_code_cell(s.strip('\n')))

md(r"""
# JN-K — Completion Anatomy (where, what size, and how long)

**The question.** JN-E established *how many* homes were completed (4,229, 2018–2025, audited
against the city's filing). This notebook dissects that count along the axes the policy debate
actually argues about: **where** the homes stand (commercial corridors vs neighborhood fabric),
**what size** of building delivered them, **how long** each stage of the process took for major
projects (including the deemed-complete milestone that starts the statutory clock), and **how
the count reconciles** with the city's filing in the one year they diverge (2025).

**Sources & roles.** (1) v4 events + `event_classifications` — the audited CO count, with
location from the feed's OWN StreetName/StreetNumber fields (845/845 permits carry them);
(2) v2 serving DB — major-project stage dates (`filed/application_complete/entitled/BP/CO`);
(3) HCD mirror — the reconcile-TARGET in §5 only, never an input.

**Honesty rails:**
1. **Count = v4, geometry = v2 — never swap.** The 2026-07-09 lesson: a v2 project-level
   shortcut (3,693u) silently dropped ~750 fabric units and inflated the corridor share to
   55%; the fine-grained count says 47.7%. Every count here derives from v4.
2. **Corridor = street-name proxy.** The 14 named arterials include residential stretches of
   long streets and EXCLUDE downtown side-street towers (Kittredge, Berkeley Way, Milvia…) —
   it measures arterial frontage, not building scale. §3's size split is the scale story.
3. **Stage durations are elapsed calendar time**, including lawful tolling (resubmittals,
   CEQA) — screens, not violation counts.
4. **Status codes drift; events are evidence.** A status-withdrawn project with an ISSUED
   building permit stays in the under-construction bucket (flagged to the stalled register).
5. **UC in beds, never units** (Anchor House = 772 beds, self-permitted outside the city feed).
""")

md(r"""
## §1 — The universe: the audited CO count, located
📝 **Plan:** derive the finaled new-unit master permits (JN-E's exact derivation) 2018–2025 with
net units and the feed's street fields; **anchor** the total to the LATEST reconciliation
baseline's `co_completions` (invariant: JN-K dissects exactly the audited number, no more, no less).
""")
code(r'''
import os, json, glob, re, sqlite3, subprocess
from collections import defaultdict
from datetime import date
import pandas as pd

ROOT = os.path.expanduser('~/berkeley-data')
V4 = os.path.join(ROOT, 'databases', 'berkeley_housing_v4.db')
con = sqlite3.connect(f'file:{V4}?mode=ro', uri=True)

rows = []
for pn, d, u, payload in con.execute("""
    SELECT e.source_record_key, e.event_date, c.net_units, e.raw_payload
    FROM events e JOIN event_classifications c ON e.event_id = c.event_id
    WHERE e.event_type_code='permit_finaled' AND c.housing_role='new_unit'
      AND c.is_master=1 AND c.net_units>0
      AND substr(e.event_date,1,4) BETWEEN '2018' AND '2025'"""):
    p = json.loads(payload)
    rows.append(dict(pn=pn, year=int(d[:4]), units=u,
                     street=(p.get('StreetName') or '').strip().upper(),
                     number=(p.get('StreetNumber') or '').strip(),
                     apn=(p.get('Parcel Number') or '').strip()))
co = pd.DataFrame(rows)

recon = sorted(glob.glob(os.path.join(ROOT, 'data', 'baselines', 'reconciliation_baseline_*.json')))[-1]
anchor = json.load(open(recon))['hard_gated']['co_completions']['value']
assert int(co.units.sum()) == anchor, (
    f'ANCHOR FAIL: derived {co.units.sum()} vs {anchor} in {os.path.basename(recon)} — '
    'JN-E moved the audited count; re-derive/diagnose BEFORE trusting any split below')
print(f'{len(co):,} permits, {co.units.sum():,} units — anchored to {os.path.basename(recon)}')
print(f'street-field coverage: {(co.street != "").mean():.0%} (the feed locates itself)')
''')
md("📝 **Found/verify:** the total matches the audited `co_completions` exactly and 100% of the "
   "permits carry street fields — no fallback joins, no unlocated tail.")

md(r"""
## §2 — WHERE: corridor vs neighborhood fabric
📝 **Plan:** classify each permit by street name against the 14 named arterials (incl. the
`M L KING JR` spelling that cost the Day-3 overlay 84 units). ⚠ Mislead-guard: this is arterial
FRONTAGE — see rail 2; the headline is "48% from 11% of permits", not "the towers are all on corridors".
""")
code(r'''
CORR = {'SHATTUCK','SAN PABLO','UNIVERSITY','TELEGRAPH','ADELINE','COLLEGE','SOLANO','GILMAN',
        'HOPKINS','DWIGHT','ASHBY','EUCLID','HEARST','M L KING JR','MARTIN LUTHER KING'}
co['corridor'] = co.street.isin(CORR)
g = co.groupby('corridor').agg(units=('units','sum'), permits=('pn','count'))
per_corr = co[co.corridor].groupby('street').units.sum().sort_values(ascending=False)
print(g.to_string())
print(f"\ncorridor share: {g.loc[True,'units']/co.units.sum():.1%} of units "
      f"from {g.loc[True,'permits']/len(co):.1%} of permits")
print('\ntop corridors:\n' + per_corr.head(6).to_string())
''')

md(r"""
## §3 — WHAT SIZE: the metronome and the towers
📝 **Plan:** the same universe split at 4 units, plus the corridor×size cross-tab that shows why
the two splits differ (large buildings on non-arterial downtown side streets).
""")
code(r'''
co['large'] = co.units > 4
sz = co.groupby('large').agg(units=('units','sum'), permits=('pn','count'))
xt = co.groupby(['corridor','large']).units.sum().unstack(fill_value=0)
yearly = co.groupby(['year','large']).units.sum().unstack(fill_value=0)
print(sz.to_string()); print()
print('units cross-tab (corridor x large):'); print(xt.to_string())
small_rng = (int(yearly[False].min()), int(yearly[False].max()))
print(f"\nthe metronome: small-stream range {small_rng[0]}-{small_rng[1]} u/yr; "
      f"tower stream swings {yearly[True].max()/yearly[True].min():.1f}x")
''')
code(r'''
import plotly.graph_objects as go
fig = go.Figure()
fig.add_bar(x=yearly.index, y=yearly[False], name='1-4 units (small stream)', marker_color='#7ec8e3')
fig.add_bar(x=yearly.index, y=yearly[True], name='5+ units (towers)', marker_color='#ffd166')
fig.update_layout(barmode='stack', title='Completed units by CO year and building size (derived §3)',
                  template='plotly_dark', height=380)
fig.show()
''')
md("📝 **Mislead-guard:** stacking implies the streams are additive competitors — they are "
   "different *processes* (ministerial vs discretionary). The chart must not be read as "
   "'small could replace large': 80% of the units are in the gold.")

md(r"""
## §4 — HOW LONG: the stage clock on major projects (v2, ≥50u)
📝 **Plan:** v2 carries the deemed-complete milestone (`application_complete`, scraped from
city-portal detail pages — 159 events / 68 projects). For majors: median intake (filed→complete)
vs consideration (complete→entitled); then the funnel of ALL non-UC majors by furthest hard
evidence (rail 4: events outrank status).
""")
code(r'''
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
v2 = sqlite3.connect(f'file:{V2}?mode=ro', uri=True)
def cl(s, allow_ph=False):
    if not s: return None
    try: d = date.fromisoformat(str(s)[:10])
    except ValueError: return None
    return None if (not allow_ph and d.month == 1 and d.day == 1) else d
uc = {r[0] for r in v2.execute("""SELECT project_id FROM project_classifications pc
    JOIN vocabulary_classification_types v ON pc.classification_type_id=v.id WHERE v.code='uc_project'""")}
ac_map = dict(v2.execute("""SELECT project_id, MIN(substr(event_date,1,10)) FROM project_events
    WHERE event_type_id=(SELECT id FROM vocabulary_event_types WHERE code='application_complete')
    GROUP BY project_id"""))
majors = []
for pid, u, f, e, bp, cod, status in v2.execute("""SELECT project_id, total_units, filed_date,
        entitled_date, bp_issued_date, co_issued_date, status_code FROM v_projects_flat
        WHERE total_units >= 50"""):
    bpm = v2.execute("""SELECT MIN(substr(pe.event_date,1,10)) FROM project_events pe
        JOIN vocabulary_event_types v ON pe.event_type_id=v.id
        WHERE pe.project_id=? AND v.code='building_permit_issued'""", (pid,)).fetchone()[0]
    majors.append(dict(pid=pid, u=u, uc=pid in uc, status=status, f=cl(f), ac=cl(ac_map.get(pid)),
                       e=cl(e), bp=cl(bpm or bp) or cl(bpm or bp, True), co=cl(cod, True)))
intake = [(m['ac']-m['f']).days for m in majors
          if m['f'] and m['ac'] and m['ac'] >= m['f']]
consider = [(m['e']-m['ac']).days for m in majors if m['ac'] and m['e'] and m['e'] >= m['ac']]
import statistics as st
print(f'deemed-complete coverage: {sum(1 for m in majors if m["ac"])}/{len(majors)} majors')
print(f'intake  (filed->complete):    n={len(intake)}, median {st.median(intake):.0f}d')
print(f'consideration (complete->entitled): n={len(consider)}, median {st.median(consider):.0f}d')

nonuc = [m for m in majors if not m['uc']]
wd  = [m for m in nonuc if m['status'] == 'withdrawn' and not m['bp'] and not m['co']]
rest = [m for m in nonuc if m not in wd]
fa = [m for m in rest if m['co']]; fb = [m for m in rest if m['bp'] and not m['co']]
fc = [m for m in rest if m['e'] and not m['bp'] and not m['co']]
fpre = [m for m in rest if not m['e'] and not m['bp'] and not m['co']]
print(f'\nfunnel (non-UC majors): {len(nonuc)} applications -> {len(fa)+len(fb)+len(fc)} entitled '
      f'-> {len(fa)+len(fb)} permitted -> {len(fa)} completed | withdrawn {len(wd)}, denied 0')
''')
code(r'''
fig = go.Figure(go.Funnel(
    y=['applications', 'entitled', 'building permit', 'completed'],
    x=[len(nonuc), len(fa)+len(fb)+len(fc), len(fa)+len(fb), len(fa)],
    marker=dict(color=['#7ec8e3', '#ff9f7f', '#4a6478', '#8fd694'])))
fig.update_layout(title='Major (≥50u) applications by furthest hard evidence (derived §4)',
                  template='plotly_dark', height=380)
fig.show()
''')
md("📝 **Mislead-guard:** the funnel narrows by WAITING, not refusal (denied = 0; one voluntary "
   "withdrawal). The lower bands are not losses — they are projects still in a stage. A funnel "
   "chart visually implies leakage; the annotation must carry 'still in process'.")

md(r"""
## §5 — The one divergent year: 2025 ours|city, every row named
📝 **Plan:** address-level adjudication of our 600 vs the city's 492 (oracle = compare-target
ONLY). ⚠ The two large ours-only completions are GROUP LIVING — sleeping units are arguably not
APR dwelling units, so the city's omission may be definitional, not error. We say "omits," never "wrong."
""")
code(r'''
MIR = sorted(glob.glob(os.path.join(ROOT, 'databases', 'hcd_apr_mirror*fresh.db')))[-1]
mir = sqlite3.connect(f'file:{MIR}?mode=ro', uri=True)
cols = [d[1] for d in mir.execute('PRAGMA table_info(table_a2)')]
tier = [c for c in cols if c.upper().startswith('CO_') and
        ('INCOME' in c.upper() or c.upper().endswith(('_DR', '_NDR')))]
assert len(tier) == 11, f'expected the 11 CO tier columns, got {len(tier)}'
q = (f"SELECT STREET_ADDRESS, ({'+'.join(f'COALESCE(CAST({c} AS INT),0)' for c in tier)}) co "
     "FROM table_a2 WHERE YEAR='2025' AND JURIS_NAME LIKE 'BERKELEY%'")
city = [(a or '', c) for a, c in mir.execute(q) if c and c > 0]
def norm(a):
    a = re.sub(r'[^A-Z0-9 ]', ' ', str(a).upper())
    a = re.sub(r'\b(AVENUE|AVE|STREET|ST|WAY|BLVD|ROAD|RD|DRIVE|DR|LANE|LN|CT|COURT|PL|PLACE)\b', '', a)
    return re.sub(r'\s+', ' ', a.replace('MARTIN LUTHER KING JR', 'M L KING JR')).strip()
ours25 = co[co.year == 2025]
on, cn = defaultdict(int), defaultdict(int)
for _, r in ours25.iterrows(): on[norm(f"{r.number} {r.street}")] += r.units
for a, c in city: cn[norm(a)] += c
oo = {a: u for a, u in on.items() if a not in cn}
oc = {a: u for a, u in cn.items() if a not in on}
bd = {a: on[a]-cn[a] for a in on if a in cn and on[a] != cn[a]}
gap = dict(ours=int(ours25.units.sum()), city=sum(c for _, c in city),
           ours_only=sum(oo.values()), city_only=sum(oc.values()), row_diffs=sum(bd.values()))
assert gap['ours'] - gap['city'] == gap['ours_only'] - gap['city_only'] + gap['row_diffs'], 'decomposition must sum'
print(f"ours {gap['ours']} - city {gap['city']} = +{gap['ours']-gap['city']}  "
      f"(= +{gap['ours_only']} ours-only - {gap['city_only']} city-only + {gap['row_diffs']} row-diffs)")
print('largest ours-only rows:')
for a, u in sorted(oo.items(), key=lambda x: -x[1])[:4]:
    print(f'  {u:4d}u {a}')
''')
md("📝 **Found/verify:** +108 = two group-living completions (80u) + a small-completion tail. "
   "3030 Telegraph is NOT a factor — its CO is 2026 on both sides.")

md(r"""
## §6 — Data lineage
""")
code(r"""
from IPython.display import Markdown, display
display(Markdown('''```mermaid
graph LR
  E[(v4 events + classifications\nfinaled new-unit masters)] --> U[§1 located universe 4,229u]
  R[(reconciliation baseline\nJN-E co_completions)] -->|ANCHOR| U
  U --> W[§2 corridor/fabric]
  U --> S[§3 size split]
  V[(v2 majors ≥50u\nfiled/complete/entitled/BP/CO)] --> T[§4 stage clock + funnel]
  M[(HCD mirror A2 2025\nORACLE - compare only)] --> G[§5 gap adjudication]
  U --> G
  W & S & T & G --> B{{baseline gate §7}}
```'''))
""")

md(r"""
## §7 — Baseline gate (derive vs timestamped baseline)
📝 First run writes `data/baselines/completion_anatomy_baseline_2026-07-09.json`; later runs must
match or diagnose-and-halt; a legitimate change APPENDS a new baseline (evidence-append-only).
""")
code(r'''
figures = {
  'co_units_2018_2025': int(co.units.sum()),
  'co_permits': int(len(co)),
  'corridor_units': int(g.loc[True, 'units']), 'corridor_permits': int(g.loc[True, 'permits']),
  'fabric_units': int(g.loc[False, 'units']), 'fabric_permits': int(g.loc[False, 'permits']),
  'small_units': int(sz.loc[False, 'units']), 'small_permits': int(sz.loc[False, 'permits']),
  'large_units': int(sz.loc[True, 'units']), 'large_permits': int(sz.loc[True, 'permits']),
  'large_units_nonarterial': int(xt.loc[False, True]),
  'majors_nonuc': len(nonuc), 'majors_entitled': len(fa)+len(fb)+len(fc),
  'majors_permitted': len(fa)+len(fb), 'majors_completed': len(fa),
  'majors_withdrawn': len(wd), 'majors_denied': 0,
  'ac_majors_covered': sum(1 for m in majors if m['ac']),
  'median_intake_days': int(st.median(intake)), 'median_consideration_days': int(st.median(consider)),
  'gap2025_total': gap['ours'] - gap['city'], 'gap2025_ours_only': gap['ours_only'],
}
sha = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'],
                     capture_output=True, text=True).stdout.strip()
snaps = sorted(glob.glob(os.path.join(ROOT, 'data', 'baselines', 'completion_anatomy_baseline_*.json')))
if snaps:
    bl = json.load(open(snaps[-1]))
    diffs = {k: (v, bl['figures'].get(k)) for k, v in figures.items() if bl['figures'].get(k) != v}
    if diffs:
        print(f"BASELINE MISMATCH vs {os.path.basename(snaps[-1])} (baseline sha {bl['v4_sha']}, now {sha}):")
        for k, (now, was) in diffs.items():
            print(f'  {k}: computed {now} vs baseline {was}')
        raise AssertionError('diagnose above; a legitimate change APPENDS a new timestamped baseline')
    print(f'BASELINE GATE PASS vs {os.path.basename(snaps[-1])}')
else:
    out_p = os.path.join(ROOT, 'data', 'baselines', 'completion_anatomy_baseline_2026-07-09.json')
    json.dump({'as_of': '2026-07-09', 'v4_sha': sha,
               'anchor': os.path.basename(recon),
               'provenance': 'JN-K first derivation (v4 located universe + v2 majors + A2-2025 compare)',
               'figures': figures}, open(out_p, 'w'), indent=1)
    print('WROTE first baseline:', out_p)
for k, v in figures.items():
    print(f'  {k:28} {v}')
''')

md(r"""
## Assumptions ledger
| assumption | what BREAKS if violated |
|---|---|
| count = v4, geometry = v2 (rail 1) | project-level counting silently drops the fabric tail and inflates corridor share (the 55% error) |
| corridor = street-name frontage proxy (rail 2) | reading it as building-scale conflates §2 with §3; downtown side-street towers vanish |
| durations include lawful tolling (rail 3) | quoting 410d as a violation count overstates; it is a screen |
| events outrank status (rail 4) | status drift fabricates withdrawals of permitted projects (3 such flagged to the stalled register) |
| UC in beds, never units (rail 5) | 772 phantom units reappear in fabric (the Day-3 error) |
| §5 oracle is compare-only | any CKAN-derived figure entering §1-§4 makes the reconciliation circular and void |
| sleeping units may be non-APR by definition | "the city missed 80u" overclaims; we say "omits" |
""")

nb = new_notebook(cells=cells, metadata={'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}})
os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
with open(NB_OUT, 'w') as f:
    nbf.write(nb, f)
print('wrote', NB_OUT, len(cells), 'cells')
