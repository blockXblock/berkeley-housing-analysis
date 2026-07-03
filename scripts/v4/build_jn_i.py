"""Build JN-I_permit_timelines.ipynb — how long Berkeley takes (the timelines / statutory-clock JN).

The question: how long does each stage of housing production take — application -> issuance ->
final — for whom, trending which way, and how does elapsed time compare to the state's statutory
clocks? Everything derives from the v4 event stream (permit_submitted / permit_issued /
permit_finaled are first-class events); roles from housing_rules.permit_role (aa6ded0 discipline:
IMPORT, never re-define). Read-only on the DB; writes only its baseline (first run) and nothing else.

House pattern: markdown(assumption+plan) -> code -> markdown(found+verify); derive-and-compare to an
external timestamped baseline (data/baselines/timelines_baseline_<date>.json, carrying v4 sha +
classifier hash) — NEVER hardcoded answers in logic; plotly viz with text-sandwich mislead-guards.

Run:  /opt/miniconda3/envs/jupyter_env/bin/python scripts/v4/build_jn_i.py   # emits the notebook
"""
import os

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-I_permit_timelines.ipynb')

cells = []
def md(t): cells.append(new_markdown_cell(t.strip('\n')))
def code(s): cells.append(new_code_cell(s.strip('\n')))

md(r"""
# JN-I — Permit Timelines (how long Berkeley takes)

**The question.** Between a builder deciding to build and a household moving in sit three dated
gates the city controls or records: **application submitted → permit issued → construction finaled**.
This notebook measures the waits — for all permits, for housing, for ADUs — trends them by year,
screens them against the state's statutory clocks, and names the longest waits. The reconciliation
(JN-E, the Audit page) established *what* got built; this establishes *how long it took*.

**Sources & roles.** Everything derives from the v4 event stream (`permit_submitted` /
`permit_issued` / `permit_finaled`) — the same CPRA-fed store the audit runs on. Roles come from
`housing_rules.permit_role` (imported, never re-typed). No oracle input anywhere: these are pure
primary-source measurements.

**Honesty rails (read before quoting any number):**
1. **The feed is survivors-only.** It contains permits that *were issued* (99% have an issuance
   date). Applications still waiting, withdrawn, or denied are invisible — so every wait measured
   here is a **lower bound on the true experience** of applying.
2. **Elapsed ≠ statutory clock.** We measure gross calendar days between dated events. The legal
   clocks (e.g. the 60-day ADU rule) run on *complete* applications and pause for applicant-side
   revision time, which this feed does not record. A long elapsed time is a **screening signal —
   an upper bound on city-attributable time — never a violation count.**
3. **Construction durations are right-censored.** `issue→final` exists only for finaled permits;
   recent cohorts are incomplete and will look artificially fast.
""")

md(r"""
## §1 — Universe: one row per permit, three dates, a role
📝 **Assumption:** the v4 store carries ~30.8k permits as events, one submitted event each; the
classifier assigns each a housing role. **Plan:** collapse events to a per-permit frame
(MIN date per event type), classify from the submitted event's payload, mark base permits
(`extract_master_permit(pn) == pn`) so subsidiary revisions/deferrals don't double-count waits.
""")
code(r'''
import os, sys, json, sqlite3, subprocess
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
    FROM events WHERE event_type_code IN ('permit_submitted','permit_issued','permit_finaled')
    GROUP BY source_record_key, event_type_code""", con)
wide = dates.pivot(index='pn', columns='et', values='d').reset_index()
for c in ('permit_submitted', 'permit_issued', 'permit_finaled'):
    wide[c] = pd.to_datetime(wide.get(c), errors='coerce')

pay = pd.read_sql("""
    SELECT source_record_key pn,
           json_extract(raw_payload,'$."Work Type"')      wt,
           json_extract(raw_payload,'$.WorkDescription')  descr,
           json_extract(raw_payload,'$.ADU')              adu,
           json_extract(raw_payload,'$.OccType')          occ,
           json_extract(raw_payload,'$.UnitsAdded')       ua,
           json_extract(raw_payload,'$.UnitsRemoved')     ur,
           json_extract(raw_payload,'$.NumberUnits')      nu,
           json_extract(raw_payload,'$.StreetNumber')     snum,
           json_extract(raw_payload,'$.StreetName')       sname
    FROM events WHERE event_type_code='permit_submitted'
    GROUP BY source_record_key""", con)
df = wide.merge(pay, on='pn', how='left')

roles = df.apply(lambda r: permit_role.classify(r.wt, r.descr, r.adu, r.occ, r.ua, r.ur, r.pn), axis=1)
df['role'] = [x[0] for x in roles]; df['is_master'] = [x[1] for x in roles]
df['units'] = [permit_role.net_units(r.ua, r.ur, role) for r, role in zip(df.itertuples(index=False), df['role'])]
df['is_base'] = df.pn.map(lambda p: extract_master_permit(str(p)) == str(p))
df['is_adu'] = df.adu.astype(str).str.strip().str.lower().str.startswith('y')

df['d_review'] = (df.permit_issued - df.permit_submitted).dt.days     # submit -> issue
df['d_build']  = (df.permit_finaled - df.permit_issued).dt.days       # issue -> final
df['d_total']  = (df.permit_finaled - df.permit_submitted).dt.days
df = df[(df.d_review.isna()) | (df.d_review >= 0)]                    # drop clock-impossible rows

base = df[df.is_base]
housing = base[(base.role == 'new_unit') & base.is_master & (base.units > 0)]
adu = base[base.is_adu]
print(f'permits {len(df):,} | base {len(base):,} | housing new-unit masters {len(housing):,} | ADU-flagged base {len(adu):,}')
print(f'classifier: {permit_role.classifier_hash()}')
''')
md(r"""
📝 **Found/verify:** the universe splits into the city's whole caseload (base permits), the
housing-production core (new-unit masters with units), and the ADU stream. Negative-duration rows
(data-entry artifacts) are dropped and counted by their absence from the totals above.
""")

md(r"""
## §2 — The waits: how long each gate takes
📝 **Plan:** for each cohort, the three durations as median / p90 (medians resist outliers; p90 is
the "one in ten wait longer than this" number a permit applicant actually fears).
""")
code(r"""
def stats(g, col):
    s = g[col].dropna()
    return dict(n=int(len(s)), median=float(s.median()) if len(s) else None,
                p90=float(s.quantile(.9)) if len(s) else None)
SEG = {'all base permits': base, 'housing new-unit masters': housing, 'ADU-flagged': adu}
rows = []
for name, g in SEG.items():
    for col, label in (('d_review','submit→issue'), ('d_build','issue→final'), ('d_total','submit→final')):
        st = stats(g, col)
        rows.append({'cohort': name, 'stage': label, **st})
timing = pd.DataFrame(rows)
print(timing.to_string(index=False))
""")
md(r"""
📝 **Found:** read the `submit→issue` rows first — that's the wait the city controls most directly.
The housing-masters row is the story number: half of Berkeley's new-housing permits wait longer
than the median shown, and one in ten wait past the p90. **Mislead-guard:** `issue→final` and
`submit→final` rows only include *finished* projects (right-censoring, rail #3) — quote them as
"among completed projects," never as expectations for a new applicant.
""")

md(r"""
## §3 — Trend: is the wait growing?
📝 **Plan:** submit→issue medians by submittal-year cohort, housing masters vs all base permits.
Recent cohorts are near-complete for this metric (99% of the feed's permits have issuance dates) —
but remember rail #1: still-pending applications never enter the feed at all.
""")
code(r"""
base_y = base.assign(y=base.permit_submitted.dt.year)
trend = (base_y[base_y.y.between(2017, 2025)]
         .groupby('y').d_review.agg(all_median='median', all_p90=lambda s: s.quantile(.9), n='count'))
h_y = housing.assign(y=housing.permit_submitted.dt.year)
trend['housing_median'] = h_y[h_y.y.between(2017, 2025)].groupby('y').d_review.median()
print(trend.round(0).to_string())
""")
code(r"""
import plotly.graph_objects as go
fig = go.Figure()
fig.add_scatter(x=trend.index, y=trend.all_median, name='all base permits — median', mode='lines+markers')
fig.add_scatter(x=trend.index, y=trend.housing_median, name='housing masters — median', mode='lines+markers')
fig.add_scatter(x=trend.index, y=trend.all_p90, name='all base permits — p90', mode='lines+markers', line=dict(dash='dot'))
fig.update_layout(title='Days from application to permit issuance, by submittal year (derived live)',
                  xaxis_title='submittal year', yaxis_title='calendar days', height=420)
fig.show()
""")
md(r"""
📝 **Mislead-guards for the chart above:** (1) the last cohort is the least complete — its slow
applications may still be pending and invisible, so a downtick at the right edge can be survivorship,
not speed; (2) these are calendar days including applicant-side revision time (rail #2); (3) the
housing-masters line rides on far fewer permits per year than the all-permits line — expect noise.
""")

md(r"""
## §4 — The statutory-clock screen (ADU 60-day rule)
📝 **Assumption:** state law (Gov. Code §66317) requires action on a *complete* ADU application
within 60 days. **Plan:** measure the share of ADU-flagged base permits whose gross submit→issue
elapsed time exceeds 60 / 120 / 180 days. **This is a screen, not a verdict** (rail #2): elapsed
time includes applicant revision rounds the statute nets out. What the screen CAN say: every permit
under 60 days gross is clock-compliant beyond argument, and the size of the >180-day tail bounds
how much process time exists to explain.
""")
code(r"""
a = adu.dropna(subset=['d_review'])
screen = {f'>{k}d': (float((a.d_review > k).mean()), int((a.d_review > k).sum())) for k in (60, 120, 180, 365)}
print(f'ADU base permits with both dates: {len(a):,};  median {a.d_review.median():.0f}d  p90 {a.d_review.quantile(.9):.0f}d')
for k, (share, n) in screen.items():
    print(f'  gross elapsed {k:>5}: {share:5.1%}  ({n:,} permits)')
""")
md(r"""
📝 **Found/verify:** the fraction of ADU permits that clear even the *gross* 60-day bar is the
lead statistic — gross elapsed is an upper bound on city time, so the under-60 share is a **floor**
on compliance and the over-180 share is the tail that demands explanation (either heavy applicant
revision loops or a slow counter — the feed cannot distinguish; a records request for
complete-application dates would).
""")

md(r"""
## §5 — The longest waits, named
📝 **Plan:** the ten longest submit→issue waits among housing new-unit masters — with address,
units, and days. These are the anchor anecdotes; each deserves a document pull before publication
(the wait may be applicant-driven — rail #2 applies to every row).
""")
code(r"""
top = (housing.dropna(subset=['d_review']).nlargest(10, 'd_review')
       [['pn', 'snum', 'sname', 'units', 'd_review', 'permit_submitted', 'permit_issued']])
top = top.assign(years=(top.d_review / 365.25).round(1),
                 permit_submitted=top.permit_submitted.dt.date, permit_issued=top.permit_issued.dt.date)
print(top.to_string(index=False))
""")

md(r"""
## §6 — Construction time (issue→final), by project size
📝 **Plan:** among *finaled* housing masters (censoring rail #3), how long construction takes by
size class — the number that turns "the city permitted it" into "someone lives there."
""")
code(r"""
fin = housing.dropna(subset=['d_build'])
fin = fin[fin.d_build >= 0]
size = pd.cut(fin.units, [0, 1, 4, 19, 99, 100000],
              labels=['1', '2-4', '5-19', '20-99', '100+'])
build = fin.groupby(size, observed=True).d_build.agg(n='count', median='median',
                                                     p90=lambda s: s.quantile(.9)).round(0)
print(build.to_string())
""")
code(r"""
import plotly.graph_objects as go
fig = go.Figure(go.Bar(x=build.index.astype(str), y=build['median'], name='median',
                       text=build['median'], textposition='outside'))
fig.add_scatter(x=build.index.astype(str), y=build['p90'], name='p90', mode='markers',
                marker=dict(size=11, symbol='diamond'))
fig.update_layout(title='Construction days (issue→final) by project size — finaled housing masters only',
                  xaxis_title='units in project', yaxis_title='calendar days', height=400)
fig.show()
""")
md(r"""
📝 **Mislead-guard:** finaled-only (censoring) — stalled and abandoned projects are absent, so
every bar is optimistic; and `final` is an inspection milestone, not move-in day.
""")

md(r"""
## §7 — Data lineage
📝 What feeds what: raw CPRA xlsx → JN-A ingestion → v4 `events` (submitted/issued/finaled) →
this notebook's per-permit frame → the figures above and the baseline gate below.
""")
code(r"""
from IPython.display import Markdown, display
display(Markdown('''```mermaid
graph LR
  X[CPRA BP xlsx 2018-2025] -->|JN-A ingest| E[(v4 events\nsubmitted/issued/finaled)]
  E -->|MIN date per type per permit| P[per-permit frame]
  R[housing_rules.permit_role] -->|classify + net_units| P
  P --> S2[waits by cohort §2]
  P --> S3[trend §3]
  P --> S4[ADU 60-day screen §4]
  P --> S5[named outliers §5]
  P --> S6[construction time §6]
  S2 & S3 & S4 --> B{{baseline gate §8}}
```'''))
""")

md(r"""
## §8 — Baseline gate (derive vs the timestamped baseline — never hardcode)
📝 **Plan:** the key figures derive above; here they are compared to the newest
`data/baselines/timelines_baseline_*.json`. First run WRITES the baseline (with the v4 sha +
classifier hash); later runs must match or **diagnose and halt**. A legitimate change (new data,
corrected classifier) re-passes by APPENDING a new timestamped baseline — never by editing one.
""")
code(r"""
import glob
figures = {
    'n_base_permits': int(len(base)),
    'n_housing_masters': int(len(housing)),
    'n_adu_base': int(len(adu)),
    'review_median_all': float(base.d_review.median()),
    'review_p90_all': float(base.d_review.quantile(.9)),
    'review_median_housing': float(housing.d_review.median()),
    'review_p90_housing': float(housing.d_review.quantile(.9)),
    'adu_review_median': float(adu.d_review.median()),
    'adu_share_over_60d': round(float((adu.d_review.dropna() > 60).mean()), 4),
}
sha = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'],
                     capture_output=True, text=True).stdout.strip()
snaps = sorted(glob.glob(os.path.join(ROOT, 'data', 'baselines', 'timelines_baseline_*.json')))
if snaps:
    bl = json.load(open(snaps[-1]))
    diffs = {k: (v, bl['figures'].get(k)) for k, v in figures.items() if bl['figures'].get(k) != v}
    if diffs:
        print(f"BASELINE MISMATCH vs {os.path.basename(snaps[-1])} (baseline sha {bl['v4_sha']}, now {sha}):")
        for k, (now, was) in diffs.items():
            print(f'  {k}: computed {now}  vs baseline {was}')
        raise AssertionError('diagnose above; a legitimate change APPENDS a new timestamped baseline')
    print(f'BASELINE GATE PASS vs {os.path.basename(snaps[-1])}')
else:
    out = os.path.join(ROOT, 'data', 'baselines', 'timelines_baseline_2026-07-03.json')
    json.dump({'as_of': '2026-07-03', 'v4_sha': sha, 'classifier': permit_role.classifier_hash(),
               'provenance': 'JN-I first derivation from v4 events (permit_submitted/issued/finaled)',
               'figures': figures}, open(out, 'w'), indent=1)
    print('WROTE first baseline:', out)
for k, v in figures.items():
    print(f'  {k:24} {v}')
""")

md(r"""
## Assumptions ledger
| assumption | what BREAKS if violated |
|---|---|
| survivors-only feed (rail 1) | quoting these waits as the applicant experience understates it — pending/withdrawn applications are invisible |
| elapsed ≠ statutory clock (rail 2) | calling a >60d ADU permit a "violation" — applicant revision time is inside our number; it is a screen |
| right-censoring (rail 3) | construction durations quoted as expectations — stalled projects are absent |
| base permits only | mixing revisions/deferrals back in would double-count waits per project |
| roles from housing_rules @ classifier_hash | a re-typed classifier would silently drift from the audited record |
| baseline append-only | editing a baseline hides real drift; a legit change appends a new dated file |
""")

nb = new_notebook(cells=cells, metadata={'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}})
os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
with open(NB_OUT, 'w') as f:
    nbf.write(nb, f)
print('wrote', NB_OUT, len(cells), 'cells')
