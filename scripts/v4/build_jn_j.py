"""Build JN-J_entitled_unbuilt.ipynb — where housing dies (the attrition / entitled-but-unbuilt JN).

The question JN-I set up: cities take credit at approval, residents get homes at completion —
how much approved/permitted housing never arrives, and at which gate does it die? Three sources,
three gates: the v4 event stream (units + dates: ISSUED -> FINALED cohort survival, units-weighted);
the Accela harvest universe 2015-2026 (application-stage outcomes incl. the Closed-Expired
abandonment class and planning-stage denials/withdrawals); the assessor's Imps as the built-signal
corroborator for the named stalled register.

House pattern: markdown(assumption+plan) -> code -> markdown(found+verify); derive-and-compare to
data/baselines/entitled_unbuilt_baseline_<date>.json; plotly viz with mislead-guards; assumptions
ledger. Read-only everywhere; writes only its baseline on first run.

Run:  /opt/miniconda3/envs/jupyter_env/bin/python scripts/v4/build_jn_j.py
"""
import os

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-J_entitled_unbuilt.ipynb')

cells = []
def md(t): cells.append(new_markdown_cell(t.strip('\n')))
def code(s): cells.append(new_code_cell(s.strip('\n')))

md(r"""
# JN-J — Entitled but Unbuilt (where housing dies)

**The question.** The public argument about housing is fought over *approvals*; households live in
*completions*. Between the two sit three gates where projects die quietly: the planning counter
(withdrawn/denied), the building-permit counter (applications that expire unissued), and the
construction site (permits issued but never finaled). This notebook measures the attrition at each
gate — units-weighted where units exist — and names the largest casualties.

**Sources & roles.** (1) v4 events + `housing_rules.permit_role` — the deep, dated, unit-carrying
feed for issued→finaled survival; (2) the Accela harvest universe (82k records 2015–2026, both
modules) — application-stage outcomes the feed never contained; (3) the Alameda assessor's `Imps`
— the independent built-signal for corroborating the stalled register. No oracle input anywhere.

**Honesty rails:**
1. **`Closed Expired` ≠ unbuilt.** A completion permit can expire with the building standing and
   occupied — the Den taught us this (the never-final convention). Expired-status counts are an
   ABANDONMENT-CLASS ceiling; individual verdicts need corroboration.
2. **Right-censoring.** Recent cohorts haven't had time to finish; survival headlines use cohorts
   old enough that "not finaled" means something (issued ≤2022, ≥3.5 years of runway).
3. **`Imps=$0` on a finaled permit = reassessment lag, not unbuilt** (the standing rule) — the
   corroborator only strengthens verdicts on NON-finaled permits, never overrides a city final.
""")

md(r"""
## §1 — The deep feed: housing masters with units and dates
📝 **Plan:** same universe construction as JN-I (v4 events → per-permit frame, roles from the
imported classifier, base permits only), keeping issued/finaled dates and units.
""")
code(r'''
import os, sys, json, glob, sqlite3, subprocess
import pandas as pd
ROOT = os.path.expanduser('~/berkeley-data')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'build_v2'))
from housing_rules import permit_role
from cpra_dedup import extract_master_permit

V4 = os.path.join(ROOT, 'databases', 'berkeley_housing_v4.db')
con = sqlite3.connect(f'file:{V4}?mode=ro', uri=True)
dates = pd.read_sql("""
    SELECT source_record_key pn, event_type_code et, MIN(substr(event_date,1,10)) d
    FROM events WHERE event_type_code IN ('permit_issued','permit_finaled')
    GROUP BY source_record_key, event_type_code""", con)
wide = dates.pivot(index='pn', columns='et', values='d').reset_index()
for c in ('permit_issued', 'permit_finaled'):
    wide[c] = pd.to_datetime(wide.get(c), errors='coerce')
pay = pd.read_sql("""
    SELECT source_record_key pn,
           json_extract(raw_payload,'$."Work Type"')     wt,
           json_extract(raw_payload,'$.WorkDescription') descr,
           json_extract(raw_payload,'$.ADU')             adu,
           json_extract(raw_payload,'$.OccType')         occ,
           json_extract(raw_payload,'$.UnitsAdded')      ua,
           json_extract(raw_payload,'$.UnitsRemoved')    ur,
           json_extract(raw_payload,'$."Parcel Number"') apn,
           json_extract(raw_payload,'$.StreetNumber')    snum,
           json_extract(raw_payload,'$.StreetName')      sname,
           json_extract(raw_payload,'$."Finaled Status"') fstatus
    FROM events WHERE event_type_code='permit_submitted'
    GROUP BY source_record_key""", con)
df = wide.merge(pay, on='pn', how='right')
roles = df.apply(lambda r: permit_role.classify(r.wt, r.descr, r.adu, r.occ, r.ua, r.ur, r.pn), axis=1)
df['role'] = [x[0] for x in roles]; df['is_master'] = [x[1] for x in roles]
df['units'] = [permit_role.net_units(r.ua, r.ur, role) for r, role in zip(df.itertuples(index=False), df['role'])]
df['is_base'] = df.pn.map(lambda p: extract_master_permit(str(p)) == str(p))
housing = df[df.is_base & (df.role == 'new_unit') & df.is_master & (df.units > 0)].copy()
housing['iy'] = housing.permit_issued.dt.year
print(f'housing new-unit masters with units: {len(housing):,} '
      f'({int(housing.units.sum()):,} units) | classifier {permit_role.classifier_hash()}')
''')

md(r"""
## §2 — Gate 3: issued → finaled, cohort survival (units-weighted)
📝 **Plan:** for each issuance-year cohort, what share of *units* reached a final? Cohorts ≤2022
are the headline (≥3.5 years of runway — rail #2); younger cohorts shown as censored context.
""")
code(r"""
h = housing[housing.iy.between(2015, 2025)]
coh = h.groupby('iy').agg(projects=('pn','size'), units=('units','sum'),
                          finaled_units=('units', lambda s: s[h.loc[s.index, 'permit_finaled'].notna()].sum()))
coh['survival'] = (coh.finaled_units / coh.units).round(2)
print(coh.astype({'units':int,'finaled_units':int}).to_string())
mature = coh.loc[coh.index <= 2022]
lost = int(mature.units.sum() - mature.finaled_units.sum())
print(f'\nmature cohorts (issued 2015-2022): {int(mature.units.sum()):,} units issued, '
      f'{int(mature.finaled_units.sum()):,} finaled -> {lost:,} units ({1 - mature.finaled_units.sum()/mature.units.sum():.0%}) not finaled after >=3.5 years')
""")
code(r"""
import plotly.graph_objects as go
fig = go.Figure()
fig.add_bar(x=coh.index, y=coh.units, name='units permitted', marker_color='#90a4ae')
fig.add_bar(x=coh.index, y=coh.finaled_units, name='units finaled (by now)', marker_color='#1565c0')
fig.add_scatter(x=coh.index, y=(coh.survival*100), name='survival %', yaxis='y2',
                mode='lines+markers', line=dict(color='#ffa000'))
fig.update_layout(title='Issued→finaled survival by issuance cohort (units) — right edge is CENSORED',
                  barmode='overlay', yaxis_title='units',
                  yaxis2=dict(overlaying='y', side='right', title='survival %', range=[0,105]), height=430)
fig.show()
""")
md(r"""
📝 **Mislead-guards:** the right edge is censoring, not collapse (rail #2 — 2023–2025 cohorts are
still building); and "not finaled" bundles genuinely-unbuilt with built-but-never-finaled (rail #1)
— the register below separates them with the assessor.
""")

md(r"""
## §3 — The stalled register, named and corroborated
📝 **Plan:** housing masters ≥10 units, issued ≥2015, never finaled — joined to the assessor's
current `Imps` at the parcel prefix. `Imps` high ⇒ likely BUILT-not-finaled (paperwork debt);
`Imps` ≈ 0 and issued years ago ⇒ the genuine unbuilt/stalled candidates (Latham class).
""")
code(r'''
bk = sqlite3.connect(f"file:{os.path.join(ROOT,'databases','berkeley.db')}?mode=ro", uri=True)
par = pd.read_sql("""SELECT printf('%03d%04d%03d%02d', CAST(BOOK AS INT), CAST(PAGE AS INT),
                     CAST(PARCEL AS INT), COALESCE(CAST(SUB_PARCEL AS INT),0)) k,
                     CAST(Imps AS REAL) imps FROM parcels""", bk)
p10 = par.assign(p=par.k.str[:10]).groupby('p').imps.sum()
reg = housing[(housing.units >= 10) & housing.permit_issued.notna() & housing.permit_finaled.isna()].copy()
reg['p10'] = reg.apn.astype(str).str.replace(r'\D', '', regex=True).str.zfill(12).str[:10]
reg['imps'] = reg.p10.map(p10)
reg['yrs_since_issue'] = (pd.Timestamp('2026-07-04') - reg.permit_issued).dt.days / 365.25
reg = reg.sort_values('units', ascending=False)
print(f'never-finaled housing masters >=10u: {len(reg)} projects, {int(reg.units.sum()):,} units')
for _, r in reg.head(15).iterrows():
    sig = 'BUILT? (Imps high)' if (r.imps or 0) > 1e6 else ('unbuilt candidate' if r.yrs_since_issue > 3 else 'in construction window')
    print(f"  {r.pn}  {str(r.snum):>5} {str(r.sname)[:16]:16} {int(r.units):>3}u issued {r.permit_issued.date()} "
          f"({r.yrs_since_issue:.1f}y)  Imps ${(r.imps or 0)/1e6:6.1f}M  {sig}")
''')
md(r"""
📝 **Found/verify:** three classes separate cleanly — high-`Imps` rows are likely *built with
paperwork debt* (adjudicate via the never-final convention before counting either way); old
low-`Imps` rows are the genuine stalled/unbuilt candidates; young rows are simply in their
construction window. Every "unbuilt candidate" deserves a document/field check before publication
— this register is a QUEUE, not a verdict list (rails #1 and #3).
""")

md(r"""
## §4 — Gates 1–2: application-stage attrition (the harvest universe)
📝 **Plan:** outcomes by CURRENT status for (a) building applications (the Closed-Expired
abandonment ceiling) and (b) planning applications (withdrawn/denied at the first gate) — by
filed year, from the 2015–2026 harvest. Statuses are current-state, so old cohorts read as
near-final outcomes; recent years include in-flight records.
""")
code(r"""
def load_module(mod):
    rows = []
    for fp in glob.glob(os.path.join(ROOT, 'data', 'raw', 'accela', 'date_range', f'{mod}_*.jsonl')):
        for l in open(fp):
            rows.append(json.loads(l))
    d = pd.DataFrame(rows)
    pn = d['Permit Number'] if 'Permit Number' in d.columns else pd.Series(index=d.index, dtype=object)
    rn = d['Record Number'] if 'Record Number' in d.columns else pd.Series(index=d.index, dtype=object)
    d['rid'] = pn.where(pn.notna(), rn)
    d = d[d.rid.notna() & (d.rid != '')].drop_duplicates('rid')
    d['y'] = d['Date'].str[6:10]
    return d
b = load_module('Building'); p = load_module('Planning')
bb = b[b.rid.str.match(r'^B\d{4}-\d{4,5}$', na=False) & b.y.between('2015', '2025')]
print('=== Building applications: outcome shares by filed year (current status)')
out = pd.crosstab(bb.y, bb.Status.map(lambda s: s if s in ('Finaled','Issued','Closed Expired') else 'other'), normalize='index').round(2)
print(out.to_string())
ce = bb[bb.Status == 'Closed Expired']
print(f'Closed-Expired building applications 2015-2025: {len(ce):,} (the abandonment-class ceiling — rail #1)')
pp = p[p.y.between('2015', '2025')]
st = pp.Status.fillna('')
died = st.isin(['Withdrawn', 'Denied'])
print(f'\n=== Planning applications 2015-2025: {len(pp):,}; withdrawn {int(st.eq("Withdrawn").sum()):,} '
      f'+ denied {int(st.eq("Denied").sum()):,} = {died.mean():.1%} die at the first gate '
      f'(approved-family statuses: {int(st.str.startswith("Approved").sum()):,})')
""")

md(r"""
## §5 — Data lineage
""")
code(r"""
from IPython.display import Markdown, display
display(Markdown('''```mermaid
graph LR
  E[(v4 events\nissued/finaled + units)] -->|classifier @hash| H[housing masters]
  H --> S2[cohort survival §2]
  H --> S3[stalled register §3]
  A[(assessor Imps)] --> S3
  U[(Accela harvest 82k\n2015-2026 both modules)] --> S4[application attrition §4]
  S2 & S3 & S4 --> B{{baseline gate §6}}
```'''))
""")

md(r"""
## §6 — Baseline gate (derive vs timestamped baseline)
📝 First run writes `data/baselines/entitled_unbuilt_baseline_2026-07-04.json` (v4 sha + classifier
hash); later runs must match or diagnose-and-halt; legitimate change = APPEND a new baseline.
""")
code(r"""
figures = {
  'housing_masters': int(len(housing)),
  'mature_units_issued_2015_2022': int(mature.units.sum()),
  'mature_units_finaled': int(mature.finaled_units.sum()),
  'mature_units_not_finaled': lost,
  'stalled_register_projects_10u': int(len(reg)),
  'stalled_register_units': int(reg.units.sum()),
  'closed_expired_building_apps': int(len(ce)),
  'planning_apps_2015_2025': int(len(pp)),
  'planning_first_gate_death_share': round(float(died.mean()), 4),
}
sha = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
snaps = sorted(glob.glob(os.path.join(ROOT, 'data', 'baselines', 'entitled_unbuilt_baseline_*.json')))
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
    out_p = os.path.join(ROOT, 'data', 'baselines', 'entitled_unbuilt_baseline_2026-07-04.json')
    json.dump({'as_of': '2026-07-04', 'v4_sha': sha, 'classifier': permit_role.classifier_hash(),
               'provenance': 'JN-J first derivation (v4 events + 2015-2026 Accela harvest + assessor)',
               'figures': figures}, open(out_p, 'w'), indent=1)
    print('WROTE first baseline:', out_p)
for k, v in figures.items():
    print(f'  {k:34} {v}')
""")

md(r"""
## Assumptions ledger
| assumption | what BREAKS if violated |
|---|---|
| Closed-Expired ≠ unbuilt (rail 1, the Den) | quoting the abandonment ceiling as an unbuilt count manufactures phantom losses |
| censoring (rail 2) | survival quoted on young cohorts reads normal construction time as death |
| Imps corroborates, never overrides a final (rail 3) | reassessment lag would erase real completions |
| register is a queue, not verdicts | publishing candidates unverified names owners wrongly |
| statuses are CURRENT state | historical funnel shares drift as in-flight records resolve — re-runs against a fresher harvest legitimately move (baseline-append) |
| roles from housing_rules @ classifier_hash | re-typed classifier drifts from the audited record |
""")

nb = new_notebook(cells=cells, metadata={'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}})
os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
with open(NB_OUT, 'w') as f:
    nbf.write(nb, f)
print('wrote', NB_OUT, len(cells), 'cells')
