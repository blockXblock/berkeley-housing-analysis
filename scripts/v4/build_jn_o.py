"""Build notebooks/v4/JN-O_pencil_out.ipynb -- do Berkeley's stalled entitlements pencil, and how tall would a building on
an Elmwood site have to be to pencil?

John, 2026-10-25 (pencil-out Phase B, after Phase A docs/audit/2026-10-25_pencil_out_phase_a_inputs.md and the harvest):
  - per project in the explorer's "Entitled 3+ yrs, inactive" stage: NOI -> total development cost -> yield on cost ->
    residual land value at low/base/high, against its land basis; verdict pencils / marginal / does_not /
    insufficient_data; RECORD vs ASSUMPTION on every input; which assumption flips each verdict
  - the Elmwood sites (7-Eleven, Five Little Monkeys, Wells Fargo lot, post office): the height at which a building
    pencils; then every parcel in Berkeley (§8, the citywide pass) and every parcel inside its zoning envelope (§9):
    python scripts/v4/pencil_out.py --citywide --zoned  (one run writes both: citywide_zoned_<date>.csv)

Machinery: scripts/v4/pencil_out.py (on scripts/v4/proforma_projects.py, JN-Feasibility Part 2). Assumptions:
data/assumptions/pencil_out_<date>.yaml. Gate: data/baselines/pencil_out_baseline_<date>.json (first run writes it;
a reviewed change APPENDS one with JN_WRITE_BASELINE=1). Results: data/derived/pencil_out/results_<date>.json.

  .venv/bin/python scripts/v4/build_jn_o.py            # write the notebook
  .venv/bin/jupyter nbconvert --to notebook --execute notebooks/v4/JN-O_pencil_out.ipynb --output /tmp/x.ipynb
"""
import os

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

nb = new_notebook()
C = []


def md(s): C.append(new_markdown_cell(s.strip()))
def code(s): C.append(new_code_cell(s.strip()))


md(r"""
# JN-O — Does it pencil? Berkeley's stalled entitlements, and how tall an Elmwood building would have to be

**Two questions (John, 2026-10-25).**
1. **The stalled projects.** For each project in the explorer's *"Entitled 3+ yrs, inactive"* stage: does it pencil at
   its approved size? *Do these projects stall because they don't pencil, or for other reasons?*
2. **The Elmwood sites.** For the 7-Eleven, the Five Little Monkeys / Nabolom building, the Wells Fargo parking lot and
   the post office: *how high must each building be to have enough units to pencil?* Later, every potential building
   site in Berkeley, so the site model here is generic: give it a lot size and what stands on the lot.

**The decision rule** is JN-Feasibility's (Part 1, Step 4b), never `profit > 0`: a building pencils when its **yield on
cost** (stabilized NOI ÷ total development cost) reaches the **exit cap rate plus a spread**. Equivalently, its
**residual land value** (what the finished building is worth at that hurdle, less every cost except land) is at least its
**land basis**. For an Elmwood site the land basis is the **higher** of market land value and the value of the business
already there (John: *"Both, take the higher"*), because an owner doesn't sell below what the current use is worth.

**Every input is labeled.** **RECORD** = from the City's or the assessor's records (ZAB staff reports, Accela plan sets,
the Rent Board registry, the assessment roll). **ASSUMPTION** = from one versioned file,
`data/assumptions/pencil_out_2026-10-25.yaml`, where each value has a low/base/high, a source and a date. Nothing in this
notebook is a typed-in market number. A project missing a core RECORD input is **`insufficient_data`**; gaps are never
filled with guesses.

**Verdicts are four-valued:** `pencils` (clears the hurdle even with every assumption at its unfavorable end) ·
`marginal` (clears it only in the base or the favorable case) · `does_not` (fails even when every assumption breaks
favorably at once) · `insufficient_data`.

> ⚠️ **What this is not.** A model of *a* developer, not *the* developer: no project's actual pro forma, loan or land deal
> is known. The verdicts say whether the **public-record facts plus sourced market assumptions** support building, which
> is exactly the question of whether stalling is explained by the numbers.
""")

md(r"""
## Data lineage — sources → inputs → verdict

```mermaid
graph LR
  EXP[docs/explorer_data.js<br/>stage 'Entitled but Inactive'] --> COH[cohort: 5+ units]
  V4[(v4 v_projects)] --> COH
  COH --> SUP[superseded / built / conversion<br/>excluded]
  SR[ZAB staff reports<br/>data/raw/zab/staff_reports] --> REC[RECORD inputs CSV<br/>units · floor area · mix · affordable]
  PS[Accela plan sets<br/>harvester 2026-10-25] --> REC
  RB[Rent Board registry<br/>lease-up rents · Part 2a] --> RENT[market rents by bedroom]
  LS[leasing sites · Part 2f] --> RENT
  ASR[(assessor roll<br/>berkeley.db + v4)] --> LAND[land basis]
  YAML[[assumptions YAML<br/>low · base · high · source]] --> PF
  REC --> PF[pencil_out.py<br/>NOI → TDC → YoC → RLV]
  RENT --> PF
  LAND --> PF
  SITES[Elmwood parcels<br/>lot · building sqft] --> HT[break-even height search]
  YAML --> HT
  RENT --> HT
  PF --> V[verdicts + sensitivity]
  HT --> E[height curves]
  ZL[City zoning layer<br/>+ fire hazard zones 2025] --> ZJ[parcel → district]
  ZS[[zoning standards YAML<br/>BMC sections cited]] --> ENV[envelope: stories · FAR · density]
  ZJ --> ENV
  ENV --> HT
  V --> GATE[baseline gate]
  E --> GATE
  V --> OUT[(results JSON)]
  E --> OUT
  V --> BANDS[band chart §4/§6<br/>pencil_out_bands_date.svg]
  E --> BANDS
```
""")

code(r"""
import sys, json, re, csv, collections, sqlite3
from pathlib import Path
ROOT = Path.cwd().resolve()
while not (ROOT / 'scripts' / 'v4').exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / 'scripts' / 'v4')); sys.path.insert(0, str(ROOT / 'scripts'))
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pencil_out as po
A = po.A
print('assumptions file:', po.ASSUMPTIONS_FILE.relative_to(ROOT), '| version', A['version'], '| prices in', A['price_year'])
""")

# ------------------------------------------------------------------------------------------------ §1 the cohort
md(r"""
## §1 — The cohort: who is "Entitled 3+ yrs, inactive"?

📝 **Plan.** Use the explorer's own definition, not a new one. `scripts/export_explorer_data_v4.py` (lines 127–131) sets
the stage **Entitled but Inactive** when v4's status is `entitled`, the approval is more than 1,095 days old, and nothing
has been recorded on any of the project's records for 1,095 days. The home page labels it *"Entitled 3+ yrs, inactive"*.
The cut moves with the export date, so this reads the **published** export. A pro forma only means something for
buildings of **5 or more units**.

Before any finance, the Phase A audit found entitlements in this stage that are **not stalled**: a later project on the
same address went ahead, or the "units" are a conversion. Those are derived here, not typed in: another v4 project at the
same street address with a **later** approval or a building permit, and descriptions that convert space without new
construction.
""")
code(r"""
s = open(ROOT / 'docs' / 'explorer_data.js').read()
EXP = json.loads(s[s.index('{'):s.rindex('}') + 1])
stage = [p for p in EXP['projects'] if p.get('status') == 'Entitled but Inactive']
big = [p for p in stage if (p['units'] or 0) >= 5]
print(f"export {EXP['meta']['generated'][:10]}: {len(stage)} projects / {sum(p['units'] or 0 for p in stage):,} units "
      f"in the stage; {len(big)} with 5+ units / {sum(p['units'] for p in big):,} units")

def same_address(a, b):
    m = re.match(r'(\d+)\s+(\w+)', a or ''); n = re.match(r'(\d+)\s+(\w+)', b or '')
    return bool(m and n and m.groups() == n.groups())
GONE = {'Withdrawn', 'Denied', 'Expired'}
rows = []
for p in sorted(big, key=lambda p: -p['units']):
    # a LATER project on the same parcel or street address that went ahead or holds a later approval
    later = [q for q in EXP['projects'] if q['id'] != p['id'] and q['status'] not in GONE
             and ((p['apn'] and q.get('apn') == p['apn']) or same_address(q['address'], p['address']))
             and (q.get('bp_issued') or (q.get('entitled') or '') > (p.get('entitled') or ''))]
    conversion = bool(re.search(r'\bconvert', p['description'] or '', re.I)) and not re.search(r'\bconstruct', p['description'] or '', re.I)
    why = (f"superseded: {later[0]['id']} {later[0]['address']} ({later[0]['units']} units, {later[0]['status']})" if later
           else 'conversion of existing space' if conversion else '')
    rows.append(dict(anchor=p['id'], address=p['address'], units=p['units'], entitled=p['entitled'], excluded=why))
COH = pd.DataFrame(rows)
EXCLUDED = COH[COH.excluded != '']
IN_SCOPE = COH[COH.excluded == '']
print(f"\nnot stalled ({len(EXCLUDED)} projects, {EXCLUDED.units.sum()} units):")
print(EXCLUDED.to_string(index=False))
""")
md(r"""
📝 **Found.** The "inactive" stage carries entitlements that a later project on the same address replaced or built.
That's an identity error in the build (the successor is not linked to the entitlement it replaced), to be fixed in the
projects stage of the v4 chain rebuild, not here. These are excluded from the finance question. Two more need human
checks before they could be evaluated (Phase A §2): **824 University** (the parcel carries large existing improvements) and
**1155 Hearst** (a 2025 ZAB action that may be a minutes-parse misattribution).
""")

# ------------------------------------------------------------------------------------------------ §2 the inputs
md(r"""
## §2 — Inputs: what the record holds, and what is assumed

📝 **Plan.** The RECORD inputs were harvested on 2026-10-25: the **ZAB staff reports** for 6 projects (each has a
development-standards table: lot area, gross floor area, units, height; and a project description with the bedroom mix
and the affordable units by tier) and the **Accela plan sets** for 1835 San Pablo, 1200 San Pablo and 1915 Berryman. Every
value carries its file and page in `data/derived/pencil_out/project_inputs_record_2026-10-25.csv`.

**Core inputs** (missing any → `insufficient_data`): units, floor area, the unit mix, stories, lot area. Floor area may be
gross (the staff report) or net (the sum of unit areas on a plan sheet). A floor area flagged PARTIAL on the record doesn't
count.
""")
code(r"""
RECS = po.record_inputs()
in_scope = list(IN_SCOPE.anchor)
cov = []
for a in in_scope:
    r = RECS.get(a, {})
    has = lambda f: 'have' if f in r and 'PARTIAL' not in (r[f].get('note') or '') else ('partial' if f in r else 'missing')
    cov.append(dict(anchor=a, address=COH.set_index('anchor').loc[a, 'address'], units=has('units'),
                    floor_area=('have' if has('gross_floor_area') == 'have' or has('net_unit_area') == 'have'
                                else 'partial' if 'gross_floor_area' in r else 'missing'),
                    unit_mix=has('unit_mix') if 'unit_mix' in r else ('partial' if 'bedrooms' in r else 'missing'),
                    stories=has('stories'), lot=has('lot_area'), affordable=has('affordable')))
COV = pd.DataFrame(cov)
print(COV.to_string(index=False))
""")
md(r"""
📝 **Found.** The staff reports turned *missing* into *have* for six projects. What's still missing is concentrated in
projects heard **before 2022**: their staff reports were on the retired City site, and the plan sets show the units only as
labels on floor plans, which this notebook does not count by hand. The **100%-affordable** senior project (1708 Harmon)
needs a subsidy-gap model, not a market residual, so it's `insufficient_data` for this question by design.

**The assumptions file**, every row with its source (the ASSUMPTION side of the ledger):
""")
code(r"""
def band(e):
    return {k: e.get(k) for k in ('low', 'base', 'high')} if isinstance(e, dict) and 'base' in e else {}
led = []
for k, e in A.items():
    if isinstance(e, dict) and ('source' in e):
        b = band(e)
        led.append(dict(assumption=k, low=b.get('low'), base=b.get('base'), high=b.get('high'),
                        kind=e.get('kind'), as_of=e.get('as_of'), source=str(e.get('source'))[:110]))
ASSUME = pd.DataFrame(led)
pd.set_option('display.max_colwidth', 110)
print(ASSUME.to_string(index=False))
""")

# ------------------------------------------------------------------------------------------------ §3 the pro forma
md(r"""
## §3 — The pro forma, project by project

📝 **Plan.** For each project at its **approved** size, three scenarios (every assumption at its favorable end, at base,
at its unfavorable end):
- **NOI** = market units × Rent Board lease-up rent by bedrooms (RECORD; per-bed rents for 4–5-bedroom group layouts)
  × (1 − vacancy) × (1 − opex) + below-market units at the City's 2025 rents + retail.
- **Total development cost** = hard cost by construction tier (set by stories and height) + soft costs + City fees
  (the legacy per-unit mitigation fee formula, because these projects were vested before 2023-03-31; the 2022 rate, as
  the current one is not published) + construction interest + **land basis**.
- **Land basis**: RECORD when the parcels' last recorded document is a 2018+ transfer (Prop 13 resets assessment at a
  sale); otherwise ASSUMPTION (lot × market $/sqft). Every project's choice is in its ledger.
""")
code(r"""
RES = po.evaluate_stalled()
R = RES['rents']
P = {p['anchor']: p for p in RES['projects']}
out = []
for a in in_scope:
    p = P.get(a)
    if p is None:
        out.append(dict(anchor=a, address=COH.set_index('anchor').loc[a, 'address'], verdict='insufficient_data',
                        why='no RECORD inputs harvested' if a != 'PLN2021-0037' else '100% affordable: subsidy-gap model needed'))
        continue
    if p['verdict'] == 'insufficient_data':
        out.append(dict(anchor=a, address=p['address'], verdict='insufficient_data', why='missing ' + ', '.join(p['missing'])))
        continue
    ac = p['acct']
    out.append(dict(anchor=a, address=p['address'], verdict=p['verdict'], units=p['units'], stories=p['stories'],
                    tier=ac['tier'], yoc=round(p['yoc'] * 100, 2), hurdle=round(ac['hurdle'] * 100, 2),
                    gap_bp=round(p['gap'] * 1e4), gap_fav_bp=round(p['runs']['favorable']['gap'] * 1e4),
                    gap_unf_bp=round(p['runs']['unfavorable']['gap'] * 1e4),
                    rlv_m=round(p['rlv'] / 1e6, 1), land_m=round(p['land_basis'] / 1e6, 1), land=p['land_label'],
                    cost_per_unit_k=round((ac['cost_ex_land'] + p['land_basis']) / p['units'] / 1e3),
                    rent_needed_x=round(p['rent_mult_needed'], 2), why=''))
V = pd.DataFrame(out)
print(f"market rents: {R['lease_ups']} Rent Board lease-ups; per-bed median ${R['per_bed']:,.0f} ({R['per_bed_n']} floor plans)")
print(V.to_string(index=False))
VERDICTS = V.verdict.value_counts().to_dict()
print('\nverdicts:', VERDICTS)
""")
md(r"""
📝 **Found.** Read `gap_bp` (yield on cost minus the hurdle, in basis points, base case) and `rent_needed_x` (how many
times today's lease-up rents the project needs to clear the hurdle with everything else at base). At base, the projects
priced with apartment rents fall short by hundreds of basis points. The `marginal` ones clear only when **every**
assumption breaks favorably **at once**, including BFA24's 5% cap rate. The one that clears at base is a **group-living**
layout (4- and 5-bedroom units) priced at per-bed rents.

⚠️ **What this could mislead about.** (1) Rents are **by bedroom count**, not size: a project of large 2-bedroom units
(1915 Berryman's average 1,190 sqft) is under-rented by the pool, so its gap is overstated. (2) The per-bed rent is the
median 2026 **asking** rent of near-campus buildings, a best case for a building half a mile out. (3) The gross floor
area on a staff report may include garage space, which this model costs at the residential rate (2015 Blake's
underground garage).

**Every input, labeled** (one project shown; the full ledger is in the results file):
""")
code(r"""
LEDGER = pd.DataFrame([row for p in RES['projects'] for row in p['ledger']])
print(LEDGER[LEDGER.anchor == 'ZP2021-0186'][['field', 'value', 'label', 'source']].to_string(index=False))
print('\nlabels across all projects:', LEDGER.label.value_counts().to_dict())
""")

# ------------------------------------------------------------------------------------------------ §4 band chart
md(r"""
## §4 — How far each project is from penciling

📝 **Before.** One horizontal band per project, on one axis: **how many times today's lease-up rents** the building
needs to clear the hurdle at its approved size. The band runs from the **favorable** case (every other assumption at its
helpful end) to the **unfavorable** case, with a dot at the **base** case. The shaded column is the rent assumption's own
band (`market_rent_multiplier` in the assumptions file): what new buildings may actually rent for, relative to today's
lease-ups. The geometry **is** the verdict rule:

- the band lies entirely right of the shaded column → **does not pencil**, even with everything favorable;
- the dot is left of 1.0×, or the favorable end is inside the column → **marginal**;
- the unfavorable end is left of the column → **pencils**, even with everything unfavorable.

Projects without enough RECORD inputs keep a gray row, so half the cohort isn't silently dropped.
""")
code(r"""
RB = A['market_rent_multiplier']          # ASSUMPTION: today's rents could be RB['low']..RB['high'] x the lease-up pool
VCOL = {'pencils': '#0ca30c', 'marginal': '#fab219', 'does_not': '#d03b3b', 'insufficient_data': '#b4b2a9'}
VLAB = {'pencils': 'pencils', 'marginal': 'marginal', 'does_not': 'does not pencil', 'insufficient_data': 'not enough record'}

def band_verdict(fav, base, unf):
    # rent needed <= the scenario's own rent assumption  <=>  residual land value >= land basis
    return 'pencils' if unf <= RB['low'] else 'marginal' if (base <= RB['base'] or fav <= RB['high']) else 'does_not'

def band_chart(groups, title):
    # groups: [(header, [dict(label, verdict, fav, base, unf, why)])]; rows with verdict insufficient_data have no numbers
    order, fig, seen = [], go.Figure(), set()
    for header, rows in groups:
        order.append(f'<b>{header}</b>')
        for r in rows:
            order.append(r['label'])
            c = VCOL[r['verdict']]
            if r['verdict'] == 'insufficient_data':
                fig.add_annotation(x=RB['high'], y=r['label'], text=r['why'], showarrow=False, xanchor='left',
                                   font=dict(size=11, color='#52514e'))
                continue
            show = r['verdict'] not in seen
            seen.add(r['verdict'])
            fig.add_trace(go.Scatter(x=[r['fav'], r['unf']], y=[r['label']] * 2, mode='lines', line=dict(width=10, color=c),
                                     opacity=0.55, legendgroup=r['verdict'], name=VLAB[r['verdict']], showlegend=show,
                                     hoverinfo='skip'))
            fig.add_trace(go.Scatter(x=[r['base']], y=[r['label']], mode='markers', legendgroup=r['verdict'], showlegend=False,
                                     marker=dict(size=12, color=c, line=dict(width=2, color='#fcfcfb')),
                                     customdata=[[r['fav'], r['unf'], VLAB[r['verdict']]]],
                                     hovertemplate='%{y}<br>base ×%{x:.2f} (favorable ×%{customdata[0]:.2f}, '
                                                   'unfavorable ×%{customdata[1]:.2f})<br>%{customdata[2]}<extra></extra>'))
            fig.add_annotation(x=r['unf'], y=r['label'], text=VLAB[r['verdict']], showarrow=False, xanchor='left', xshift=8,
                               font=dict(size=11, color='#52514e'))
    fig.add_vrect(x0=RB['low'], x1=RB['high'], fillcolor='#e8eef6', line_width=0, layer='below')
    fig.add_vline(x=RB['base'], line_color='#52514e', line_width=1.5,
                  annotation_text=f"today's lease-up rents (shaded: ×{RB['low']:.2f}–×{RB['high']:.2f})",
                  annotation_position='top', annotation_font=dict(size=11, color='#52514e'))
    xmax = max([r['unf'] for _, rows in groups for r in rows if r['unf'] is not None] + [RB['high']])
    fig.update_yaxes(categoryorder='array', categoryarray=order[::-1], showgrid=False)
    fig.update_xaxes(range=[0, xmax * 1.25], dtick=0.5, ticksuffix='×', gridcolor='#ececea', zeroline=False,
                     title="rent needed to pencil, as a multiple of today's lease-up rents")
    fig.update_layout(title=title, template='plotly_white', plot_bgcolor='#fcfcfb', paper_bgcolor='#fcfcfb',
                      height=140 + 34 * len(order), width=1000, margin=dict(l=230, r=40, t=80, b=60),
                      legend=dict(orientation='h', y=-0.12, x=0), font=dict(family='Helvetica, Arial, sans-serif'))
    return fig

ev = [p for p in RES['projects'] if p.get('verdict') not in (None, 'insufficient_data')]
STALLED_BANDS = []
for p in ev:
    n = {sc: p['runs'][sc]['rent_mult_needed'] for sc in po.SCENARIOS}
    v = band_verdict(n['favorable'], n['base'], n['unfavorable'])
    assert v == p['verdict'], (p['anchor'], v, p['verdict'])    # the chart's geometry must reproduce the model's verdict
    STALLED_BANDS.append(dict(label=f"{p['address'].title()} · {p['stories']} st, {p['units']}u", verdict=v,
                              fav=n['favorable'], base=n['base'], unf=n['unfavorable'], why=''))
STALLED_BANDS.sort(key=lambda r: r['base'])
for r in V[V.verdict == 'insufficient_data'].itertuples():
    STALLED_BANDS.append(dict(label=r.address.title(), verdict='insufficient_data', fav=None, base=None, unf=None,
                              why=r.why))
fig = band_chart([('Stalled entitlements (approved size, legacy fee)', STALLED_BANDS)],
                 'Stalled projects: rent needed to pencil (favorable ▸ base ● ▸ unfavorable)')
fig.show()
print(pd.DataFrame(STALLED_BANDS)[['label', 'verdict', 'fav', 'base', 'unf']].round(2).to_string(index=False))
""")
md(r"""
📝 **After — what this chart could MISLEAD about.** (1) The band ends are **joint** extremes: every assumption at one end
at once, which is less likely than any single move (§5 shows them one at a time). (2) The favorable end excludes the rent
assumption itself; the shaded column carries it, so read a band's left end against the column's right edge, not against
1.0×. (3) The rent pool is by bedroom count, not size, and a group-living layout is priced per bed, its best case
(see §3). (4) The dollar view, residual land value against land basis, is in the §3 table (`rlv_m`, `land_m`); this chart
restates the same test in rent terms. (5) A gray row is a **gap in the record**, not a verdict.
""")

# ------------------------------------------------------------------------------------------------ §5 sensitivity
md(r"""
## §5 — Sensitivity: which assumption could flip each verdict?

📝 **Plan.** One assumption at a time to each end of its sourced band (all others at base). A flip is a change in
whether the project clears the hurdle. Then the **flip points**: the single value that would make it clear: the rent
multiplier, the exit cap rate, or the hard-cost multiplier.
""")
code(r"""
SENS = {p['anchor']: po.sensitivity_stalled(p['anchor'], R) for p in ev}
flip_rows, tor = [], []
for a, s_ in SENS.items():
    fl = [r['assumption'] for r in s_['rows'] if r['flips']]
    fp = s_['flip_points']
    flip_rows.append(dict(anchor=a, address=P[a]['address'], base_gap_bp=round(s_['base_gap'] * 1e4),
                          single_flips=', '.join(fl) or 'none', rent_needed_x=round(fp['rent_mult'], 2),
                          exit_cap_needed=round(fp['exit_cap'] * 100, 2),
                          hard_cost_needed_x=round(fp['hard_mult'], 2) if fp['hard_mult'] else None))
    for r in s_['rows'][:6]:
        tor.append(dict(address=P[a]['address'], assumption=r['assumption'], fav=r['favorable_gap'] * 1e4,
                        unf=r['unfavorable_gap'] * 1e4, base=s_['base_gap'] * 1e4))
FLIPS = pd.DataFrame(flip_rows)
print(FLIPS.to_string(index=False))
FLIPPERS = [a for a, s_ in SENS.items() if any(r['flips'] for r in s_['rows'])]
TOP = collections.Counter(s_['rows'][0]['assumption'] for s_ in SENS.values())
print('\nprojects with a single-assumption flip:', FLIPPERS or 'none', '| largest swing, by project count:', dict(TOP))
""")
md(r"""
📝 **Before.** A tornado per project: the six assumptions that move its gap most, each bar from its favorable to its
unfavorable end, centered on the base gap. Zero is the hurdle.
""")
code(r"""
T = pd.DataFrame(tor)
addrs = list(dict.fromkeys(T.address))
fig = make_subplots(rows=len(addrs), cols=1, subplot_titles=addrs, vertical_spacing=0.05)
for i, ad in enumerate(addrs, 1):
    t = T[T.address == ad].iloc[::-1]
    fig.add_trace(go.Bar(y=t.assumption, x=t.fav - t.unf, base=t.unf, orientation='h', marker_color='#7f9fc7',
                         showlegend=False, hovertemplate='%{y}: %{base:.0f} → %{x:.0f} bp'), row=i, col=1)
    fig.add_vline(x=0, line_color='#c0504d', line_width=1.5, row=i, col=1)
    fig.add_vline(x=t.base.iloc[0], line_color='#444', line_dash='dot', row=i, col=1)
fig.update_layout(height=230 * len(addrs), template='plotly_white',
                  title='Gap to the hurdle (bp): one assumption at a time, favorable → unfavorable end; red = hurdle, dotted = base')
fig.show()
""")
md(r"""
📝 **After — what this could MISLEAD about.** The band ends are the sources' ranges, not probabilities: a short bar can
mean a tightly sourced value **or** a thinly sourced one with no range given (marked `low: null` in the file). The
flip points answer *how far* one thing would have to move; in practice rents, costs and cap rates move together.

**Found (§3–§5 together).** No single sourced assumption flips a verdict. **Cap rate, hard cost and rent** move every
project most, in that order for most. The flip points are far outside the sourced bands: rents well above today's
lease-ups, exit cap rates below 2019's, or hard costs cut by about half. **So, to John's question: the numbers alone
explain the stalling.** At today's costs and rates these approvals don't pencil, consistent with JN-Feasibility Part 2h
(approvals of 2017–21 penciled at approval and broke on costs and rates since). The one that pencils at base is the
exception that needs its own explanation (it's a by-the-bed layout; ownership, financing, or the per-bed rent being a
best case).
""")

# ------------------------------------------------------------------------------------------------ §6 Elmwood
md(r"""
## §6 — The Elmwood sites: how tall must a building be to pencil?

📝 **Plan.** Each site (RECORD: lot from the assessor polygon, the existing building's taxable sqft, assessed values),
a building of 2 to 12 stories: a 15-ft ground floor (retail + lobby) and 10-ft residential floors; lot coverage, floor
efficiency and unit sizes from the assumptions file; units over the **Rent Board bedroom mix**. Height sets the
construction tier (Type V wood to 4 stories / 70 ft; Type V over a concrete podium to 6 / 75 ft; Type III over podium to
8 / 85 ft; Type I concrete or steel above), and the tier sets cost per sqft and months to build.

Two affordability scenarios (John): **in-lieu**, all units market-rate plus Berkeley's in-lieu fee on residential floor
area; **on-site**, 20% of units below market (half very-low-income, half low-income), the City's on-site alternative,
which also earns a state density bonus.

A height pencils when residential land value ≥ land basis = **max(market land, existing-use value)**.
""")
code(r"""
SITES = po.elmwood_sites()
S0 = po.scenario('base')
srows = []
for s_ in SITES:
    lb = po.land_basis(s_, S0)
    srows.append(dict(site=s_['name'], lot_sf=round(s_['lot_sf']), existing_bldg_sf=round(s_['existing_retail_sf']),
                      assessed_land=round(s_['assessed_land']), market_land_m=round(lb['market'] / 1e6, 2),
                      existing_use_m=round(lb['euv'] / 1e6, 2), basis_m=round(lb['basis'] / 1e6, 2), binding=lb['binding']))
print(pd.DataFrame(srows).to_string(index=False))
RUN = po.run_sites(SITES)
BE = pd.DataFrame([dict(site=r['name'], fee_mode=r['fee_mode'], scenario=r['scenario'],
                        break_even_stories=r['break_even_stories']) for r in RUN['results']])
print('\nlowest height that pencils (None = no height from 2 to 12 stories):')
print(BE.pivot_table(index=['site', 'fee_mode'], columns='scenario', values='break_even_stories', aggfunc='first',
                     dropna=False)[list(po.SCENARIOS)].to_string())
""")
md(r"""
📝 **Found.** The assessed land values (Prop 13) are a fraction of either basis: the 7-Eleven parcel's land was last
reassessed in 1976. For the two retail buildings the **existing use** binds: a buyer must pay at least what the shops are
worth as shops. For the parking lot and the post office pair, market land binds. The existing-use value rests on the
**thinnest** assumption in the file (a single undated College Ave retail listing), so read it with its band.
""")
md(r"""
📝 **Before.** For each site and height, **how many times today's lease-up rents** the building would need to pencil
(base case, in-lieu fee). Below 1.0 would pencil at today's rents. Shading marks the construction tiers.
""")
code(r"""
fig = go.Figure()
tier_spans = collections.OrderedDict()
for r in RUN['results']:
    if r['fee_mode'] != 'in_lieu' or r['scenario'] != 'base':
        continue
    xs = [x['stories'] for x in r['rows']]
    fig.add_trace(go.Scatter(x=xs, y=[x['rent_mult_needed'] for x in r['rows']], mode='lines+markers', name=r['name'],
                             customdata=[[x['units'], x['tier'], x['height_ft']] for x in r['rows']],
                             hovertemplate='%{x} stories (%{customdata[2]:.0f} ft, %{customdata[0]} units, %{customdata[1]}): ×%{y:.2f}'))
    for x in r['rows']:
        tier_spans.setdefault(x['tier'], [x['stories'], x['stories']])[1] = x['stories']
shade = ['#f4f4f4', '#e8eef6', '#f4f4f4', '#e8eef6']
for i, (t, (a0, a1)) in enumerate(tier_spans.items()):
    fig.add_vrect(x0=a0 - 0.5, x1=a1 + 0.5, fillcolor=shade[i % 4], line_width=0, layer='below',
                  annotation_text=t, annotation_position='top left', annotation_font_size=10)
fig.add_hline(y=1.0, line_color='#c0504d', annotation_text="today's lease-up rents", annotation_position='bottom right')
fig.update_layout(title='Elmwood sites: rent multiple needed to pencil, by height (base case, in-lieu fee)',
                  xaxis_title='stories', yaxis_title='× today\'s lease-up rents', template='plotly_white', height=520,
                  legend=dict(orientation='h', y=-0.2))
fig.show()
BEST = {}
for r in RUN['results']:
    best = min(r['rows'], key=lambda x: x['rent_mult_needed'])
    BEST[(r['site'], r['fee_mode'], r['scenario'])] = dict(stories=best['stories'], tier=best['tier'],
                                                         rent_needed=best['rent_mult_needed'], units=best['units'])
print(pd.DataFrame([dict(site=k[0], fee_mode=k[1], best_stories=v['stories'], units=v['units'], tier=v['tier'],
                         rent_needed_x=round(v['rent_needed'], 2))
                    for k, v in BEST.items() if k[2] == 'base']).to_string(index=False))
""")
md(r"""
📝 **After — what this chart could MISLEAD about.** (1) The y-axis is a **multiple**, so a curve that looks flat at
×2 is still a building needing double today's rents. (2) Each jump sits where the **construction tier** changes; the size
of the jump comes from BFA24's three prototype costs ($360 → $449 → $547 per sqft), the least certain step in the file.
(3) The units are what fits the envelope, not what Berkeley's zoning or the 2026 Elmwood proposal (4–5 stories, a
hypothetical 7) allows.

**Found.** The answer to *"how high must it be?"* is that, at today's rents, costs and cap rates, **no height pencils on
any of the four sites**, under either affordability scenario. Taller is not the lever it seems: within a tier each added
floor spreads the land over more units and the rent needed falls, but at each tier boundary the cost per sqft jumps and
the need rises. **The most efficient height on every site is the top of the podium tier, 6 stories (about 65 ft).** Going
to 7–8 stories costs more per unit than it adds, and above 85 ft concrete construction is worse still. What would have to
change is in the rent multiple at that best height: rents roughly double, or an equivalent cut in cost or cap rate. The
one combination that pencils is the **Wells Fargo parking lot** with every assumption favorable: no business to buy out.
""")

md(r"""
📝 **Before.** The Elmwood sites on §4's axis, each at its **most efficient height** (the base case's lowest rent need,
in-lieu fee), plus a second row where the favorable case's best height differs, under the stalled projects. Same bands, same verdict rule. This chart is also written as an SVG file for
the site or slides: `data/derived/pencil_out/pencil_out_bands_<date>.svg`.
""")
code(r"""
from datetime import date
SITE_BANDS = []
for site in dict.fromkeys(r['site'] for r in RUN['results']):
    run = {r['scenario']: r for r in RUN['results'] if r['site'] == site and r['fee_mode'] == 'in_lieu'}
    nm = re.search(r'\(([^)]*)\)', run['base']['name'])                 # '2887 College Ave (7-Eleven)' -> '7-Eleven'
    # the base case's best height; and the favorable case's, when it differs (a cheaper tier can pencil lower)
    for sc_best in dict.fromkeys((BEST[(site, 'in_lieu', 'base')]['stories'], BEST[(site, 'in_lieu', 'favorable')]['stories'])):
        n = {sc: next(x['rent_mult_needed'] for x in run[sc]['rows'] if x['stories'] == sc_best) for sc in po.SCENARIOS}
        u = next(x['units'] for x in run['base']['rows'] if x['stories'] == sc_best)
        SITE_BANDS.append(dict(label=f"{nm.group(1) if nm else run['base']['name']} · {sc_best} st, {u}u",
                               verdict=band_verdict(n['favorable'], n['base'], n['unfavorable']),
                               fav=n['favorable'], base=n['base'], unf=n['unfavorable'], why=''))
SITE_BANDS.sort(key=lambda r: r['base'])
fig = band_chart([('Stalled entitlements (approved size, legacy fee)', STALLED_BANDS),
                  ('Elmwood sites (hypothetical, best height, in-lieu fee)', SITE_BANDS)],
                 'Does it pencil? Rent needed, as a multiple of today\'s lease-up rents')
fig.show()
SVG = ROOT / 'data' / 'derived' / 'pencil_out' / f'pencil_out_bands_{date.today().isoformat()}.svg'
fig.write_image(str(SVG))
print('wrote', SVG.relative_to(ROOT))
print(pd.DataFrame(SITE_BANDS)[['label', 'verdict', 'fav', 'base', 'unf']].round(2).to_string(index=False))
""")
md(r"""
📝 **After — what this could MISLEAD about.** (1) The stalled projects are at their **approved** size and pay the
**legacy** fee; the Elmwood sites are at a **modeled** height and pay today's in-lieu fee, so the two groups share an axis,
not a cost basis. (2) Each site's band is drawn at a fixed height (the base case's best, and the favorable case's best when it
differs), so a site can carry two rows with different verdicts: a lower wood building can pencil in the favorable case
while the taller podium building does not. (3) The SVG is a static copy: no hover, and it is
regenerated, never edited, when the notebook runs.
""")

# ------------------------------------------------------------------------------------------------ §8 citywide
md(r"""
## §8 — Citywide: the same break-even search on every parcel

📝 **Plan (John, 2026-10-25: "run the citywide break-even pass").** The §6 site model on every Berkeley assessor parcel
with a usable lot. Three inputs that §6 took per site become **per parcel and RECORD-derived**:
- **Rents by neighborhood.** A rent index from the Rent Board's unit records: tenancies started 2023+ in **Fully
  Covered** (pre-1980) units, where vacancy decontrol resets the starting rent to market. Each rent is divided by the
  citywide median for its bedroom count; a neighborhood's median ratio multiplies the new-construction lease-up pool,
  shrunk toward 1.0 where it has few tenancies.
- **Existing-use value.** Building sqft × the median price per building sqft of same-kind parcels (residential /
  non-residential) whose last recorded document is 2024+ (Prop 13 resets assessment at a sale), by neighborhood where it
  has 25+ such sales, else citywide; the quartiles are the band. A vacant lot's existing use is 0.
- **Universe.** Every assessor parcel. **Excluded and counted:** condominium units (use 73xx) and lots under 2,500 sqft.
  **Tagged, not dropped:** tax-exempt parcels (UC, City, churches, nonprofits), City landmarks, and parcels with
  registered rental units (demolishing them brings replacement and relocation duties this model does not price).

The run is machinery (`python scripts/v4/pencil_out.py --citywide --zoned`, ~30 minutes) writing
`data/derived/pencil_out/citywide_zoned_<date>.csv` + `.meta.json` (this section's columns and §9's zoned `z_*` columns),
stamped with the hashes of the assumptions file, v4, the assessor roll and the zoning inputs. This cell **refuses** a
file whose stamps don't match today's inputs.
""")
code(r"""
import glob, hashlib
cw_files = sorted(glob.glob(str(ROOT / 'data' / 'derived' / 'pencil_out' / 'citywide_zoned_*.meta.json')))
CWM = json.load(open(cw_files[-1]))
now = dict(assumptions_sha=po._sha16(po.ASSUMPTIONS_FILE), v4_file_sha=po._sha16(po.pp.V4), assessor_sha=po._sha16(po.pp.ASSESSOR),
           zoning_standards_sha=po._sha16(po.ZONING_STANDARDS), zoning_districts_sha=po._sha16(po.ZONING_DISTRICTS))
stale = {k: (CWM[k], v) for k, v in now.items() if CWM[k] != v}
if stale:
    raise AssertionError(f"citywide file {Path(cw_files[-1]).name} is STALE {stale} -- re-run "
                         "`python scripts/v4/pencil_out.py --citywide --zoned`")
CW = pd.read_csv(cw_files[-1].replace('.meta.json', '.csv'))
print(f"{Path(cw_files[-1]).name}: {len(CW):,} parcels; excluded {CWM['excluded']}; inputs match today's files")
print(f"rent index: {CWM['rent_index']['tenancies']:,} market tenancies (2023+)")
RI = pd.DataFrame([dict(neighborhood=k, factor=round(v['factor'], 3), raw=round(v['raw'], 3), tenancies=v['n'])
                   for k, v in CWM['rent_index']['by_neighborhood'].items()]).sort_values('factor', ascending=False)
print(RI.to_string(index=False))
""")
md(r"""
📝 **Found.** Relative rents for old stock vary within about ±15% across most of the city (hill and campus-adjacent
neighborhoods high, South and Southwest Berkeley low). That spread is small next to the gaps §6 found: location cannot
by itself close a building that needs about twice today's rents.
""")
code(r"""
TAGS = lambda d: ('exempt' if d.exempt else 'landmark' if d.landmark else 'existing rentals' if d.rental_units else 'clear')
CW['tag'] = CW.apply(TAGS, axis=1)
def count(col): return int(CW[col].notna().sum())
summ = (CW.groupby('bucket').agg(parcels=('key', 'size'),
         pencils_base_in_lieu=('in_lieu_base_break_even', lambda s: int(s.notna().sum())),
         pencils_base_on_site=('on_site_base_break_even', lambda s: int(s.notna().sum())),
         pencils_favorable_in_lieu=('in_lieu_favorable_break_even', lambda s: int(s.notna().sum())),
         pencils_favorable_on_site=('on_site_favorable_break_even', lambda s: int(s.notna().sum())),
         median_rent_needed=('in_lieu_base_rent_needed', 'median'),
         p10_rent_needed=('in_lieu_base_rent_needed', lambda s: s.quantile(0.10)))
        .sort_values('parcels', ascending=False))
summ.loc['ALL'] = [len(CW), count('in_lieu_base_break_even'), count('on_site_base_break_even'),
                   count('in_lieu_favorable_break_even'), count('on_site_favorable_break_even'),
                   CW.in_lieu_base_rent_needed.median(), CW.in_lieu_base_rent_needed.quantile(0.10)]
print(summ.round(2).to_string())
print('\nbest height (base, in-lieu):', CW.in_lieu_base_best_stories.value_counts().sort_index().to_dict())
print('land basis set by (base):', CW.in_lieu_base_binding.value_counts().to_dict())
""")
md(r"""
📝 **Before.** The distribution of **how many times today's local rents** each parcel's best building would need, by
kind of parcel (base case, in-lieu fee). 1.0 = pencils at today's rents.
""")
code(r"""
order = ['vacant_or_misc', 'commercial', 'industrial', 'misc', 'institutional', 'public_or_common',
         'residential_5plus', 'residential_2_4', 'single_family']
fig = go.Figure()
for b in [o for o in order if o in set(CW.bucket)]:
    v = CW.loc[CW.bucket == b, 'in_lieu_base_rent_needed'].clip(upper=6)
    fig.add_trace(go.Box(x=v, name=f"{b} ({len(v):,})", boxpoints=False, orientation='h'))
fig.add_vline(x=1.0, line_color='#c0504d', annotation_text="today's local rents")
fig.update_layout(title='Every Berkeley parcel: rent multiple its best building needs to pencil (base, in-lieu; clipped at 6)',
                  xaxis_title="× today's local rents", template='plotly_white', height=480, showlegend=False)
fig.show()
""")
md(r"""
📝 **After — what this could MISLEAD about.** (1) Values are clipped at 6× so the boxes are readable. (2) The kinds
differ less than the boxes' spread suggests: across the city the need sits in a narrow band, and **single-family lots
have the lowest median**, because their land basis is mostly market land and many sit in the higher-rent neighborhoods.
(3) The **existing-use values lean low**: a 2024+ recorded document is not always a sale, and a stale assessment
understates the price, which makes development look **easier** than it is. (4) Every parcel gets the same envelope
(ground-floor retail, 75% upper coverage) and the same costs; **zoning, slope, fire zones and setbacks are not modeled
here** (§9 adds zoning and fire zones), so a hillside single-family lot is priced as if it could carry a 6-story building.
""")
md(r"""
📝 **Before.** The map: each parcel colored by the rent multiple its best building needs (base, in-lieu). Darker = closer
to penciling.
""")
code(r"""
m = CW.dropna(subset=['lat', 'lon']).copy()
m['need'] = m.in_lieu_base_rent_needed.clip(upper=4)
fig = go.Figure(go.Scattermap(lat=m.lat, lon=m.lon, mode='markers',
    marker=dict(size=4, color=m.need, colorscale='Viridis_r', cmin=1.5, cmax=4, colorbar=dict(title='× rents')),
    text=m.name + ' · ' + m.bucket + ' · best ' + m.in_lieu_base_best_stories.astype(str) + ' stories',
    hovertemplate='%{text}<br>needs ×%{marker.color:.2f} today\'s local rents<extra></extra>'))
fig.update_layout(map=dict(style='open-street-map', center=dict(lat=37.87, lon=-122.27), zoom=12.2), height=650,
                  margin=dict(l=0, r=0, t=40, b=0),
                  title='Rent multiple needed to pencil, best height, base case (clipped 1.5–4)')
fig.show()
""")
md(r"""
📝 **After — what this could MISLEAD about.** The color scale starts at 1.5×, not 1.0×, because no parcel reaches 1.0 at
base; a reader should not take the darkest dots as "pencils". The **ranking** follows the rent index (darkest in the hills
and near campus) and ignores zoning, slope and fire zones, so dark hillside dots are not buildable sites.

**The parcels that pencil in any scenario** (the favorable case: every assumption at its helpful end), with their tags:
""")
code(r"""
fav = CW[CW.in_lieu_favorable_break_even.notna() | CW.on_site_favorable_break_even.notna()].copy()
cols = ['name', 'neighborhood', 'bucket', 'lot_sf', 'building_sf', 'tag', 'in_lieu_favorable_break_even',
        'on_site_favorable_break_even', 'in_lieu_base_rent_needed', 'in_lieu_base_best_stories', 'in_lieu_base_best_units']
print(f"{len(fav):,} parcels pencil in the favorable case; by kind:", fav.bucket.value_counts().to_dict(),
      '| by tag:', fav.tag.value_counts().to_dict())
print(fav.sort_values('in_lieu_base_rent_needed')[cols].head(25).to_string(index=False))
""")
md(r"""
📝 **Found — citywide.** Three results, from the most to the least robust.
1. **At base, no parcel in Berkeley pencils at any height from 2 to 12 stories,** under either affordability scenario,
   and none does in the unfavorable case. This holds before land is even paid for on most parcels.
2. **The rent needed sits in a narrow band everywhere** (see the table: medians about 1.9–2.2× today's local rents, by
   kind of parcel), and **the best height is the top of the podium tier (6 stories) on nearly every parcel.** Location
   moves the need by the rent index's roughly ±15%; lot size and what stands on the lot move it a little more. Nothing
   moves it near 1.0.
3. **In the favorable case about half the parcels pencil, and that number should not be read as "potential sites".**
   Most are single-family lots in the higher-rent hill and north-side neighborhoods, and the lowest needs of all are on
   Panoramic Hill, the neighborhood with the highest rent index and among the least buildable land in the city. The model
   ignores **zoning, slope and fire zones** in this section, so it prices every lot as if a 6-story building were allowed, and the
   favorable case stacks every helpful assumption at once (5% cap rate, low costs, +10% rents, corridor land at
   $149/sqft).

**So the citywide answer to "how tall must it be?" matches Elmwood's:** at today's rents, costs and rates, no height
pencils anywhere; height is not the binding constraint, the rent-to-cost ratio is, and taller (past the podium tier) makes
it worse. §9 cuts the favorable-case set to what each parcel's zoning actually allows.
""")
# ------------------------------------------------------------------------------------------------ §9 zoned
md(r"""
## §9 — Zoned: the same search inside each parcel's zoning envelope

📝 **Plan (John, 2026-10-25: "build the zoning lookup table and rerun the citywide pass").** §8 let every parcel build
any height. Here each parcel stops at what its zoning allows.
- **District** — the City's zoning layer (`Portal_Planning/MapServer/7`, 42 district polygons), joined by the point in
  polygon of each parcel's assessor coordinates.
- **Envelope** — `data/reference/berkeley_zoning_standards_2026-10-25.yaml`, one row per district with its BMC section
  and the copy it was read from (RECORD): maximum height and stories, FAR and density caps, lot coverage, and whether
  the ground floor is homes (residential districts and residential-only envelopes) or the model's retail + lobby.
  Use-permit height increases are recorded there but **not used**: this is the standard envelope.
- **Two scenarios, as before.** *In-lieu fee*: the standard envelope. *On-site affordable*: the state density bonus for
  10% very-low-income units (32.5%, Gov. Code 65915(f)) added as stories and as a multiple of the FAR and density caps,
  or the district's **own** bonus where it allows more (the Adeline Corridor's tier 2 for 14% affordable).
- **Not permitted** — districts where multi-unit housing is not allowed (manufacturing, MU-LI, ES-R, green space,
  unclassified/UC land, and the specific-plan and research districts whose standards were not read) leave the zoned
  universe and are counted. **Fire hazard zones** (the City's 2025 Very High and High maps) are **tagged**, not excluded.
""")
code(r"""
ZST, BONUS = po.zoning_standards()
CW['residential_ok'] = CW.district.map(lambda d: bool(ZST.get(d, {}).get('residential')) if isinstance(d, str) else False)
ZU = CW[CW.residential_ok].copy()
print(f"zoned universe: {len(ZU):,} of {len(CW):,} parcels in districts that permit multi-unit housing")
print('not permitted / no district:', CW[~CW.residential_ok].district.fillna('(no district)').value_counts().to_dict())
print('fire hazard zone (2025):', CW.fire_zone.fillna('none').value_counts().to_dict())
""")
code(r"""
def zsumm(df):
    g = df.groupby('district')
    out = g.agg(parcels=('key', 'size'), allowed_in_lieu=('z_in_lieu_allowed_stories', 'first'),
                allowed_on_site=('z_on_site_allowed_stories', 'first'),
                pencils_base=('z_in_lieu_base_break_even', lambda s: int(s.notna().sum())),
                pencils_fav_in_lieu=('z_in_lieu_favorable_break_even', lambda s: int(s.notna().sum())),
                pencils_fav_on_site=('z_on_site_favorable_break_even', lambda s: int(s.notna().sum())),
                need_unzoned=('in_lieu_base_rent_needed', 'median'), need_zoned=('z_in_lieu_base_rent_needed', 'median'),
                need_zoned_on_site=('z_on_site_base_rent_needed', 'median'))
    return out.sort_values('parcels', ascending=False)
ZS = zsumm(ZU)
zcount = lambda col, df=ZU: int(df[col].notna().sum())
print(ZS.round(2).to_string())
print(f"\nALL zoned: pencils base in-lieu {zcount('z_in_lieu_base_break_even')}, base on-site {zcount('z_on_site_base_break_even')}, "
      f"favorable in-lieu {zcount('z_in_lieu_favorable_break_even')}, favorable on-site {zcount('z_on_site_favorable_break_even')}; "
      f"median need {ZU.z_in_lieu_base_rent_needed.median():.2f}x zoned vs {ZU.in_lieu_base_rent_needed.median():.2f}x unzoned")
""")
md(r"""
📝 **Before.** For each district, the median rent multiple a parcel's best building needs: **unzoned** (§8, any height)
against **zoned** (its envelope), in-lieu fee, base case. The gap between the two markers is what the zoning envelope
costs. Bubble size = parcels.
""")
code(r"""
zs = ZS[ZS.parcels >= 20].sort_values('need_zoned')
fig = go.Figure()
for _, r in zs.iterrows():
    fig.add_trace(go.Scatter(x=[r.need_unzoned, r.need_zoned], y=[r.name, r.name], mode='lines',
                             line=dict(color='#bbbbbb', width=2), showlegend=False, hoverinfo='skip'))
fig.add_trace(go.Scatter(x=zs.need_unzoned, y=zs.index, mode='markers', name='unzoned (§8)',
                         marker=dict(color='#8da0cb', size=9)))
fig.add_trace(go.Scatter(x=zs.need_zoned, y=zs.index, mode='markers', name='inside the zoning envelope',
                         marker=dict(color='#d95f02', size=(zs.parcels ** 0.5).clip(6, 30)),
                         text=[f"{p:,} parcels · {int(a)} stories allowed" for p, a in zip(zs.parcels, zs.allowed_in_lieu)],
                         hovertemplate='%{y}: needs ×%{x:.2f} · %{text}<extra></extra>'))
fig.add_vline(x=1.0, line_color='#c0504d', annotation_text="today's local rents")
fig.update_layout(title='Median rent multiple needed to pencil, by zoning district (base, in-lieu)',
                  xaxis_title="× today's local rents", template='plotly_white', height=640)
fig.show()
""")
md(r"""
📝 **After — what this could MISLEAD about.** (1) Medians hide the spread inside a district; a district's best parcels
are in the table below. (2) Where the layer has no sub-area boundary the **lower** envelope is used (R-3 outside the
Southside Plan, C-U Avenue not Node, C-SA outside Subarea One, C-AC's Adeline subareas), so those districts are
understated. (3) R-4 comes from a 2025 consultant report, not the code. (4) Use-permit heights (downtown 75 ft, R-5
65 ft) are not used.

**Where the zoning allows the most, and what pencils there** (favorable case, either scenario):
""")
code(r"""
zf = ZU[ZU.z_in_lieu_favorable_break_even.notna() | ZU.z_on_site_favorable_break_even.notna()].copy()
zf['tag'] = zf.apply(TAGS, axis=1)
print(f"{len(zf):,} parcels pencil inside their envelope in the favorable case; by district:",
      zf.district.value_counts().to_dict())
print('  by fire zone:', zf.fire_zone.fillna('none').value_counts().to_dict(), '| by tag:', zf.tag.value_counts().to_dict())
cols = ['name', 'district', 'neighborhood', 'lot_sf', 'tag', 'fire_zone', 'z_in_lieu_allowed_stories',
        'z_in_lieu_favorable_break_even', 'z_on_site_favorable_break_even', 'z_in_lieu_base_rent_needed', 'z_in_lieu_base_best_units']
print(zf.sort_values('z_in_lieu_base_rent_needed')[cols].head(25).to_string(index=False))
""")
md(r"""
📝 **Before.** The map of the zoned universe: each parcel colored by the rent multiple its best **permitted** building
needs (base, in-lieu). Grey = multi-unit housing not permitted.
""")
code(r"""
m = CW.dropna(subset=['lat', 'lon']).copy()
no = m[~m.residential_ok]
ok = m[m.residential_ok].copy()
ok['need'] = ok.z_in_lieu_base_rent_needed.clip(upper=4)
fig = go.Figure()
fig.add_trace(go.Scattermap(lat=no.lat, lon=no.lon, mode='markers', marker=dict(size=3, color='#cccccc'),
                            name='not permitted', hoverinfo='skip'))
fig.add_trace(go.Scattermap(lat=ok.lat, lon=ok.lon, mode='markers', name='zoned universe',
    marker=dict(size=4, color=ok.need, colorscale='Viridis_r', cmin=1.5, cmax=4, colorbar=dict(title='× rents')),
    text=ok.name + ' · ' + ok.district + ' · ' + ok.z_in_lieu_allowed_stories.astype('Int64').astype(str) + ' stories allowed',
    hovertemplate='%{text}<br>needs ×%{marker.color:.2f} today\'s local rents<extra></extra>'))
fig.update_layout(map=dict(style='open-street-map', center=dict(lat=37.87, lon=-122.27), zoom=12.2), height=650,
                  margin=dict(l=0, r=0, t=40, b=0),
                  title='Inside the zoning envelope: rent multiple needed to pencil (base, in-lieu; clipped 1.5–4)')
fig.show()
""")
md(r"""
📝 **After — what this could MISLEAD about.** The scale starts at 1.5×, so the darkest dots are the closest, not "pencils".
A parcel inside a fire hazard zone is shown like any other; the table above carries the tag.
""")
md(r"""
📝 **Found — zoned.** Four results.
1. **Still nothing pencils at base, in any district, under either scenario.** Zoning makes the gap wider, not narrower:
   the median parcel's best permitted building needs about **2.2× today's local rents**, against about 1.9× when any
   height was allowed (§8). Across most of the city the envelope is **3 stories** (the Middle Housing districts R-1,
   R-2, R-2A and their hillside versions hold three quarters of the zoned universe), below the 6-story podium building
   §8 found to be the cheapest per unit of rent.
2. **Where zoning allows height, it isn't what binds.** In the Southside districts (R-SMU, C-T up to 85 ft; R-S 55 ft)
   the envelope reaches or passes the 6-story optimum, and the need there is the same as unzoned, about 2×. Height was
   never the constraint in those places; the rent-to-cost ratio is.
3. **The density bonus helps only where the base envelope is tiny.** In most districts the on-site scenario needs
   **more** rent than paying the in-lieu fee, even with the bonus story: the 20% affordable units cost more than the
   extra market units earn. It needs less only where the base envelope is very small: Solano (2 stories), the West
   Berkeley MU-R (FAR 1.5 and a density cap), and the Adeline Corridor, where the City's own tier-2 bonus (14%
   affordable → 5 stories) beats the state bonus. That answers the earlier question with this model's numbers:
   zoning low and letting the bonus do the work produces a building only where the bonus envelope pencils, and at
   today's rents none does.
4. **The favorable-case set shrinks from about half the city to about 2,100 parcels**, and its character doesn't change:
   mostly single-family and 2–4-unit lots in R-1, R-2 and R-1H, where a 3-story Middle Housing building of a handful of
   units would pencil only with every assumption at its helpful end. **Roughly 4 in 10 of them sit in a 2025 High or
   Very High fire hazard zone.** Corridor commercial parcels almost vanish from the set: their 2–3 story envelopes
   (C-E, C-NS, C-SO, C-U Avenue, C-AC tier 1) need 2.3–3.9× rents.

**So, "how tall must it be, and is that allowed?"** The cheapest building per unit of rent is the 6-story podium
building; most of Berkeley allows 3 stories, and the places that allow 6+ (Southside, downtown at 60 ft) still need
about twice today's rents. Neither upzoning nor the bonus closes that gap alone; it moves only with rents, costs, rates
or subsidy.

**What the table can't see yet** (each would raise some districts' envelopes): the Southside, C-U node, C-SA Subarea One
and Adeline South Shattuck boundaries; use-permit heights; the state laws that override local height on qualifying
sites (AB 2011 on commercial corridors, SB 79 near transit, SB 35/423); and the R-4 section, read from a secondary source.
""")

# ------------------------------------------------------------------------------------------------ §7 results + gate
md(r"""
## §7 — Results file and gate

📝 The derived results (every verdict, ledger row, sensitivity row and height row) go to
`data/derived/pencil_out/results_<date>.json`. The headline figures are gated against
`data/baselines/pencil_out_baseline_<date>.json`: **structural** figures (cohort counts, record coverage) are stable for a
given export and harvest; **calibration** figures (verdicts, gaps, break-even heights) move when the assumptions file
changes. A reviewed change **appends** a baseline (`JN_WRITE_BASELINE=1`), never an edit.
""")
code(r"""
import os, glob, hashlib, subprocess
from datetime import date
FIG = {
    'stage_projects': len(stage), 'stage_units': int(sum(p['units'] or 0 for p in stage)),
    'cohort_5plus': len(big), 'cohort_5plus_units': int(sum(p['units'] for p in big)),
    'excluded_not_stalled': len(EXCLUDED), 'excluded_units': int(EXCLUDED.units.sum()),
    'in_scope': len(IN_SCOPE), 'record_rows': int(len(LEDGER[LEDGER.label == 'RECORD'])),
    'verdict_pencils': VERDICTS.get('pencils', 0), 'verdict_marginal': VERDICTS.get('marginal', 0),
    'verdict_does_not': VERDICTS.get('does_not', 0), 'verdict_insufficient': VERDICTS.get('insufficient_data', 0),
    'single_assumption_flips': len(FLIPPERS),
    'median_gap_bp': int(V.gap_bp.dropna().median()) if V.gap_bp.notna().any() else None,
    'elmwood_best_stories_base': sorted({v['stories'] for k, v in BEST.items() if k[2] == 'base'}),
    'lease_ups': R['lease_ups'],
    'citywide_parcels': int(len(CW)), 'citywide_excluded': CWM['excluded'],
    'citywide_pencils_base_in_lieu': count('in_lieu_base_break_even'), 'citywide_pencils_base_on_site': count('on_site_base_break_even'),
    'citywide_pencils_favorable_in_lieu': count('in_lieu_favorable_break_even'),
    'citywide_pencils_favorable_on_site': count('on_site_favorable_break_even'),
    'citywide_median_rent_needed': round(float(CW.in_lieu_base_rent_needed.median()), 3),
    'citywide_best_stories_mode': int(CW.in_lieu_base_best_stories.mode()[0]),
    'zoned_universe': int(len(ZU)), 'zoned_not_permitted': int((~CW.residential_ok).sum()),
    'zoned_pencils_base_in_lieu': zcount('z_in_lieu_base_break_even'), 'zoned_pencils_base_on_site': zcount('z_on_site_base_break_even'),
    'zoned_pencils_favorable_in_lieu': zcount('z_in_lieu_favorable_break_even'),
    'zoned_pencils_favorable_on_site': zcount('z_on_site_favorable_break_even'),
    'zoned_median_rent_needed': round(float(ZU.z_in_lieu_base_rent_needed.median()), 3),
    'zoned_median_rent_needed_on_site': round(float(ZU.z_on_site_base_rent_needed.median()), 3),
    'fire_zone_parcels': CW.fire_zone.fillna('none').value_counts().to_dict(),
}
FIG['elmwood_break_even_base'] = {r['site'] + '|' + r['fee_mode']: r['break_even_stories']
                                  for r in RUN['results'] if r['scenario'] == 'base'}
h = hashlib.sha256()
with open(po.pp.V4, 'rb') as f_:
    for b_ in iter(lambda: f_.read(1 << 20), b''): h.update(b_)
meta = {'as_of': date.today().isoformat(), 'v4_file_sha': h.hexdigest()[:16],
        'assumptions': po.ASSUMPTIONS_FILE.name, 'record_inputs': po.RECORD_INPUTS.name,
        'zoning_standards': po.ZONING_STANDARDS.name,
        'export_generated': EXP['meta']['generated'],
        'git': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip(),
        'figures': FIG}
# the results file
res_dir = ROOT / 'data' / 'derived' / 'pencil_out'
results = dict(meta=meta, cohort=COH.to_dict('records'), coverage=COV.to_dict('records'), verdicts=V.to_dict('records'),
               ledger=LEDGER.to_dict('records'), flips=FLIPS.to_dict('records'),
               sensitivity={a: s_['rows'] for a, s_ in SENS.items()},
               citywide_file=Path(cw_files[-1]).name, elmwood_sites=srows, elmwood=[dict(site=r['site'], fee_mode=r['fee_mode'], scenario=r['scenario'],
                                                  break_even_stories=r['break_even_stories'], land=r['land'], rows=r['rows'])
                                             for r in RUN['results']])
out_p = res_dir / f"results_{date.today().isoformat()}.json"
json.dump(results, open(out_p, 'w'), indent=1, default=float)
print('wrote', out_p.relative_to(ROOT))
# the gate
BL_DIR = os.environ.get('JN_BASELINE_DIR') or str(ROOT / 'data' / 'baselines')
snaps = sorted(glob.glob(os.path.join(BL_DIR, 'pencil_out_baseline_*.json')))
if not snaps or os.environ.get('JN_WRITE_BASELINE') == '1':
    nm = f"pencil_out_baseline_{date.today().isoformat()}"
    bp = next(os.path.join(BL_DIR, f'{nm}{x}.json') for x in ['', *'bcdefgh'] if not os.path.exists(os.path.join(BL_DIR, f'{nm}{x}.json')))
    json.dump(meta, open(bp, 'w'), indent=1)
    print('WROTE baseline', bp)
else:
    bl = json.load(open(snaps[-1]))
    diffs = {k: (FIG[k], bl['figures'].get(k)) for k in FIG if bl['figures'].get(k) != FIG[k]}
    if diffs:
        for k, (now, was) in diffs.items():
            print(f'  {k}: computed {now} vs baseline {was}')
        raise AssertionError(f"BASELINE MISMATCH vs {os.path.basename(snaps[-1])} (assumptions then {bl.get('assumptions')}, "
                             f"now {meta['assumptions']}; v4 then {bl.get('v4_file_sha')}, now {meta['v4_file_sha']}; export then "
                             f"{bl.get('export_generated')}, now {meta['export_generated']}) -- diagnose; a legitimate change "
                             f"APPENDS a baseline (JN_WRITE_BASELINE=1)")
    print(f'BASELINE GATE PASS vs {os.path.basename(snaps[-1])}')
for k, v in FIG.items():
    print(f'  {k:28} {v}')
""")

md(r"""
## Assumptions ledger — what BREAKS if each is wrong

| assumption | source quality | what breaks if it is wrong |
|---|---|---|
| market rents = Rent Board lease-ups by bedroom (2022–24) | RECORD, 831 leases | rents by bedroom ignore unit size: large units are under-rented; concessions not in the registry overstate rent |
| per-bed rent = median 2026 asking rent of near-campus buildings | collected, 2026 asks | a best case for a building farther out; group-living verdicts lean favorable |
| hard cost by tier = BFA24's prototype costs (2024 $ × TBD index) | cited, one Berkeley study | the **tier steps** set the best height; Terner 2020's Type I step was far smaller |
| exit cap rate 6.0% (CBRE Oakland, H1 2024 carried) | cited, Oakland not Berkeley; BFA24 and Terner used 5.0% | the single largest swing on every project |
| opex 35% of effective rent | labeled; BFA24 implies 31.6% | unclear whether property tax on the new value is inside BFA24's ratio |
| legacy mitigation fee at the 2022 rate | cited; current rate NOT FOUND | the fee is a few percent of cost; it does not decide any verdict |
| existing-use value from one undated College Ave listing | **thin** | it sets the land basis for the two retail sites; the height result does not depend on it (no height pencils even at market land) |
| lot coverage, ground-floor retail share, floor heights | labeled (checked against staff reports) | the unit count at each height; not the sign of the result |

**Next.** (1) The pre-2022 staff reports (1835 and 1200 San Pablo) via the Wayback Machine would move two projects off
`insufficient_data`. (2) Rents by unit **size** (the registry has bedrooms only; staff reports give sizes) would fix the
large-unit bias. (3) The same `break_even()` runs on any parcel: the citywide pass needs only lot size and what stands on
each lot.
""")

nb["cells"] = C
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
os.makedirs("notebooks/v4", exist_ok=True)
nbf.write(nb, "notebooks/v4/JN-O_pencil_out.ipynb")
print("wrote notebooks/v4/JN-O_pencil_out.ipynb —", len(C), "cells")
