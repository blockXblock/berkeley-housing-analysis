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

Run:  .venv/bin/python scripts/v4/build_jn_k.py
"""
import os

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
NB_OUT = os.path.join(os.environ.get('JN_NB_DIR') or os.path.join(ROOT, 'notebooks', 'v4'), 'JN-K_completion_anatomy.ipynb')

cells = []
def md(t): cells.append(new_markdown_cell(t.strip('\n')))
def code(s): cells.append(new_code_cell(s.strip('\n')))

md(r"""
# JN-K — Completion Anatomy (where, what size, and how long)

**The question.** JN-E established *how many* homes were completed (2018–2025, audited
against the city's filing). This notebook dissects that count along the axes the policy debate
actually argues about: **where** the homes stand (commercial corridors vs neighborhood fabric),
**what size** of building delivered them, **how long** each stage of the process took for major
projects (including the deemed-complete milestone that starts the statutory clock), and **how
the count reconciles** with the city's filing in the one year they diverge (2025).

**Sources & roles.** (1) v4 events + `event_classifications` — the audited CO count, with
location from the feed's OWN StreetName/StreetNumber fields (845/845 permits carry them);
(2) v4 serving view `v_projects` — major-project stage dates (`filed / accepted / entitled / bp_issued /
co_issued`), each SELECTED from the project's anchor application, never aggregated across records
(re-pointed from v2 on 2026-10-02);
(3) HCD mirror — the reconcile-TARGET in §5 only, never an input.

**Honesty rails:**
1. **Count = permit-level, never project-level.** The 2026-07-09 lesson: a v2 project-level
   shortcut (3,693u) silently dropped ~750 fabric units and inflated the corridor share to
   55%; the fine-grained count says 47.7%. Every count in §1–§3 derives from v4 finaled
   master permits; `v_projects` supplies only the major-project stage clock in §4.
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
# Since JN-E 2026-09-26b, co_completions is the WHOLE feed (finals through the 2026-07-07 production),
# not 2018-2025. Anchor the same population, then window it -- same derivation, no extra filter.
feed_total = con.execute("""SELECT COALESCE(SUM(c.net_units),0) FROM events e
    JOIN event_classifications c ON e.event_id = c.event_id
    WHERE e.event_type_code='permit_finaled' AND c.housing_role='new_unit'
      AND c.is_master=1 AND c.net_units>0""").fetchone()[0]
assert int(feed_total) == anchor, (
    f'ANCHOR FAIL: derived feed total {feed_total} vs {anchor} in {os.path.basename(recon)} — '
    'JN-E moved the audited count; re-derive/diagnose BEFORE trusting any split below')
print(f'feed total {feed_total:,} units == {os.path.basename(recon)} co_completions; '
      f'window 2018-2025: {len(co):,} permits, {co.units.sum():,} units (the rest are 2026 finals)')
print(f'street-field coverage: {(co.street != "").mean():.0%} (the feed locates itself)')
''')
md("📝 **Found/verify:** the feed total matches the audited `co_completions` exactly; the 2018–2025 "
   "window is that population minus 2026 finals, and 100% of the permits carry street fields — no "
   "fallback joins, no unlocated tail.")

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
## §4 — HOW LONG: the stage clock on major projects (v4 `v_projects`, ≥50u)
📝 **Plan:** v4's `accepted_date` is the deemed-complete milestone — the Completeness Review
*accepted* row in the anchor application's own CapDetail PROCESSING STATUS
(`housing_rules.planning_record.milestones`), SELECTED from the primary record, never a MIN/MAX
over the project's records (CLAUDE.md, rung 3). For majors: median intake (filed→accepted) vs
consideration (accepted→entitled); then the funnel of ALL non-UC majors by furthest hard evidence
(rail 4: events outrank status — v4's `bp_issued_date`/`co_issued_date` come from the buildings'
master-permit events, not a status code).

**Source change (2026-10-02).** Until v2's retirement this section read v2's `v_projects_flat`
(`MIN(application_complete)` over all project events, `total_units`, the `uc_project` flag). v4 differs
in three legitimate ways, so the §4 figures MOVE and are re-baselined, not compared as drift:
(a) one row per *application-anchored* project (a withdrawn filing and its re-filing are two rows);
(b) a major = ≥50 units by the built/permitted count, else the application's proposed count;
(c) UC and other outside-city-permitting rows are dropped by `rhna_excluded`, and DENIED is now a
derived status, not a constant.
""")
code(r'''
def cl(s, allow_ph=False):
    if not s: return None
    try: d = date.fromisoformat(str(s)[:10])
    except ValueError: return None
    return None if (not allow_ph and d.month == 1 and d.day == 1) else d
majors = []
for key, u, pu, rx, f, ac, e, bp, cod, status in con.execute("""SELECT project_key,
        units_built_or_permitted, proposed_units, rhna_excluded, filed_date, accepted_date,
        entitled_date, bp_issued_date, co_issued_date, status FROM v_projects
        WHERE anchor_role IN ('primary_application', 'pre_application', 'outside_city_permitting')"""):
    units = max(int(u or 0), int(pu or 0))
    if units < 50:
        continue
    majors.append(dict(pid=key, u=units, uc=bool(rx), status=status, f=cl(f), ac=cl(ac),
                       e=cl(e), bp=cl(bp, True), co=cl(cod, True)))
intake = [(m['ac']-m['f']).days for m in majors
          if m['f'] and m['ac'] and m['ac'] >= m['f']]
consider = [(m['e']-m['ac']).days for m in majors if m['ac'] and m['e'] and m['e'] >= m['ac']]
import statistics as st
print(f'deemed-complete coverage: {sum(1 for m in majors if m["ac"])}/{len(majors)} majors')
print(f'intake  (filed->accepted):    n={len(intake)}, median {st.median(intake):.0f}d')
print(f'consideration (accepted->entitled): n={len(consider)}, median {st.median(consider):.0f}d')

nonuc = [m for m in majors if not m['uc']]
wd  = [m for m in nonuc if m['status'] in ('withdrawn', 'void') and not m['bp'] and not m['co']]
dn  = [m for m in nonuc if m['status'] == 'denied' and not m['bp'] and not m['co']]
rest = [m for m in nonuc if m not in wd and m not in dn]
fa = [m for m in rest if m['co']]; fb = [m for m in rest if m['bp'] and not m['co']]
fc = [m for m in rest if m['e'] and not m['bp'] and not m['co']]
fpre = [m for m in rest if not m['e'] and not m['bp'] and not m['co']]
print(f'\nfunnel (non-UC majors): {len(nonuc)} applications -> {len(fa)+len(fb)+len(fc)} entitled '
      f'-> {len(fa)+len(fb)} permitted -> {len(fa)} completed | withdrawn/void {len(wd)}, denied {len(dn)}, '
      f'still pre-entitlement {len(fpre)}')
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
md("📝 **Mislead-guard:** the funnel narrows mostly by WAITING — read the printed withdrawn/void and "
   "denied counts above before reading any band as refusal. The lower bands are not losses — they are "
   "projects still in a stage. A funnel chart visually implies leakage; the annotation must carry "
   "'still in process'. v4 counts applications, so a site that re-filed appears once per filing.")

md(r"""
## §5 — The one divergent year: 2025 ours|city, every row named
📝 **Plan:** address-level adjudication of our 2025 count vs the city's (oracle = compare-target
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
md("📝 **Found/verify (as of the 2026-07-15 baseline: +108; re-read the printed decomposition above for the live figure):** "
   "the gap was two group-living completions (80u) + a small-completion tail. "
   "3030 Telegraph is NOT a factor — its CO is 2026 on both sides.")

md(r"""
## §6 — Data lineage
""")
code(r"""
from IPython.display import Markdown, display
display(Markdown('''```mermaid
graph LR
  E[(v4 events + classifications\nfinaled new-unit masters)] --> U[§1 located universe 2018-2025]
  R[(reconciliation baseline\nJN-E co_completions)] -->|ANCHOR| U
  U --> W[§2 corridor/fabric]
  U --> S[§3 size split]
  V[(v4 v_projects majors ≥50u\nfiled/accepted/entitled/BP/CO)] --> T[§4 stage clock + funnel]
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
  'majors_withdrawn': len(wd), 'majors_denied': len(dn),
  'ac_majors_covered': sum(1 for m in majors if m['ac']),
  'median_intake_days': int(st.median(intake)), 'median_consideration_days': int(st.median(consider)),
  'gap2025_total': gap['ours'] - gap['city'], 'gap2025_ours_only': gap['ours_only'],
}
sha = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'],
                     capture_output=True, text=True).stdout.strip()
import hashlib
_h = hashlib.sha256()
with open(V4, 'rb') as _f:
    for _b in iter(lambda: _f.read(1 << 20), b''): _h.update(_b)
v4_file_sha = _h.hexdigest()[:16]
# §4's source moved v2 -> v4 on 2026-10-02. Baselines written before then carry v2-derived values for
# these keys; comparing them would report a SOURCE change as drift. They are shown as a crosswalk and
# gated only against a baseline tagged majors_source = 'v4_v_projects'.
MOVED = {k for k in figures if k.startswith(('majors_', 'ac_majors', 'median_'))}
BL_DIR = os.environ.get('JN_BASELINE_DIR') or os.path.join(ROOT, 'data', 'baselines')
snaps = sorted(glob.glob(os.path.join(BL_DIR, 'completion_anatomy_baseline_*.json')))
if not snaps:
    raise AssertionError(f'no completion_anatomy baseline in {BL_DIR}')
bl = json.load(open(snaps[-1]))
v4_era = bl.get('majors_source') == 'v4_v_projects'
keys = list(figures) if v4_era else [k for k in figures if k not in MOVED]
diffs = {k: (figures[k], bl['figures'].get(k)) for k in keys if bl['figures'].get(k) != figures[k]}
print(f"gating vs {os.path.basename(snaps[-1])} ({'v4-era: all keys' if v4_era else 'v2-era: stable keys only'}; "
      f"baseline git {bl.get('v4_sha')}, now git {sha}, v4 file {v4_file_sha})")
if not v4_era:
    print('§4 keys changed SOURCE (v2 -> v4) -- crosswalk, NOT a drift check:')
    for k in sorted(MOVED):
        print(f'  {k:28} v2-era {bl["figures"].get(k)!s:>6}  ->  v4 {figures[k]}')
if diffs:
    print('BASELINE MISMATCH:')
    for k, (now, was) in diffs.items():
        print(f'  {k}: computed {now} vs baseline {was}')
    if os.environ.get('JN_WRITE_BASELINE') != '1':
        raise AssertionError('diagnose above; a legitimate change APPENDS a new timestamped baseline '
                             '(re-run with JN_WRITE_BASELINE=1 -- John\'s call)')
    print('JN_WRITE_BASELINE=1: the differences above are a reviewed change; appending a new baseline below.')
    v4_era = False      # fall through to the append
if v4_era:
    print(f'BASELINE GATE PASS vs {os.path.basename(snaps[-1])}')
else:
    print(f'stable keys PASS ({len(keys)}).')
    proposal = {'as_of': date.today().isoformat(), 'v4_sha': sha, 'v4_file_sha': v4_file_sha,
                'majors_source': 'v4_v_projects', 'anchor': os.path.basename(recon),
                'supersedes_for_moved_keys': os.path.basename(snaps[-1]),
                'provenance': 'JN-K re-pointed to v4 (2026-10-02): §1-§3/§5 v4 events, §4 v4 v_projects majors',
                'figures': figures}
    if os.environ.get('JN_WRITE_BASELINE') == '1':
        out_p = os.path.join(BL_DIR, f'completion_anatomy_baseline_{date.today().isoformat()}_v4.json')
        assert not os.path.exists(out_p), f'{out_p} exists -- baselines are append-only'
        json.dump(proposal, open(out_p, 'w'), indent=1)
        print('APPENDED v4-era baseline:', out_p)
    else:
        print('PARTIAL GATE: §4 is UNGATED until a v4-era baseline is appended '
              '(re-run with JN_WRITE_BASELINE=1 -- John\'s call).')
for k, v in figures.items():
    print(f'  {k:28} {v}')
''')

md(r"""
## Assumptions ledger
| assumption | what BREAKS if violated |
|---|---|
| count = permit-level v4 events, never project-level (rail 1) | project-level counting silently drops the fabric tail and inflates corridor share (the 55% error) |
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
