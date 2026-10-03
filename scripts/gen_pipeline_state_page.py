#!/usr/bin/env python3
"""Generate docs/pipeline-state.html — THE PIPELINE-STATE VIEW.

READS v4 SINCE 2026-10-02: databases/berkeley_housing_v4.db, read-only (mode=ro), through the Explorer exporter's
own projection (scripts/export_explorer_data_v4.get_projects, which reads v4's serving view v_projects). The page's
five states are the Explorer's stage labels grouped, so the two pages always agree; no field is re-derived here.
(Before 2026-10-02 it read v2's v_projects_flat + project_events + two July 2026 overlays keyed on v2 project ids.)

Every tracked (non-UC) project, by its Explorer stage:
  1 applied, not yet entitled        Under Review, Pre-Application            (anchor: filed date)
  2 entitled, no building permit     Entitled, Entitled but Inactive          (anchor: entitled date)
  3 BP issued, no construction       Permitted, Not Started (no inspection yet) + Permitted but Inactive (>24 months)
  4 under construction               Under Construction (inspected in the last 6 months) + Construction Quiet (inspected
                                     before, not since) -- the Explorer's split of 2026-10-03, by the City's inspections
  5 complete                         Completed: every building finaled         (anchor: last building's CO)
  'Building Permits Filed' (a permit applied for, none issued) goes to 2 if entitled, else 1.
  Exits (footnote): Withdrawn, Denied, Expired.
Evidence column: states 3/4 = the latest inspection in v4's events; state 2 = BMC 23.404.060 lapse tier from the
entitled date, plus the building-permit applications cited by the 2026-07-14 waiting-room overlay
(data/processed/waiting_room_lapse_2026-07-14.json), matched by ADDRESS and re-checked against v4's own listing of
that record (its current status) — never by the overlay's v2 project ids.

ANCHOR: the >=50u subset is compared with JN-K's majors funnel (completion_anatomy_baseline_* latest). That baseline
was built from v2; until a v4 JN-K baseline exists, a mismatch HALTS unless --accept-anchor-drift is given, and the
page then does not claim the gate passed.

MACHINERY: re-run after any v4 rebuild, then commit docs/pipeline-state.html.
Run: .venv/bin/python scripts/gen_pipeline_state_page.py [--out DIR] [--accept-anchor-drift]
     (--out or env SITE_OUT: write DIR/pipeline-state.html instead of docs/pipeline-state.html)
"""
import argparse
import glob
import json
import os
import sqlite3
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from export_explorer_data_v4 import DB_PATH, get_projects   # noqa: E402  the Explorer's own v4 projection
from housing_rules.address import normalize_address          # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.environ.get('SITE_OUT') or os.path.join(ROOT, 'docs'),
                help='directory to write pipeline-state.html into (default docs/)')
ap.add_argument('--accept-anchor-drift', action='store_true',
                help='proceed when the >=50u subset differs from the (v2-built) JN-K baseline')
ARGS = ap.parse_args()

TODAY = date.today()
v4 = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
PROJECTS = get_projects(v4)
# latest inspection per project: v4's own inspection events on the project's buildings
last_insp = dict(v4.execute("""SELECT json_extract(p.notes, '$.project_key'), MAX(e.event_date) FROM projects p
    JOIN project_structures ps USING(project_id) JOIN structure_events se USING(structure_id)
    JOIN events e USING(event_id) WHERE e.event_type_code = 'inspection' GROUP BY 1"""))


def listed_status(record):
    """The record's status as v4's latest Accela listing states it (None if v4 does not list it)."""
    r = v4.execute("""SELECT json_extract(raw_payload, '$.Status') FROM events WHERE source_record_key = ?
                      AND event_type_code = 'accela_listed' ORDER BY event_date DESC LIMIT 1""", (record,)).fetchone()
    return r[0] if r else None


def d10(s):
    s = str(s or '')[:10]
    try: return date.fromisoformat(s)
    except ValueError: return None


def akey(a):
    try:
        h, s = normalize_address(a)
        return (h, s) if h and s else None
    except Exception:
        return None


# THE EXPLORER'S STAGES -> THIS PAGE'S STATES (one mapping; the Explorer decides the stage)
STAGE_STATE = {'Under Review': 1, 'Pre-Application': 1, 'Entitled': 2, 'Entitled but Inactive': 2,
               'Permitted, Not Started': 3, 'Permitted but Inactive': 3,
               'Construction Quiet': 4, 'Under Construction': 4, 'Completed': 5}
EXITS = ('Withdrawn', 'Denied', 'Expired')
STATES = {i: [] for i in range(1, 6)}
exits = {x: [] for x in EXITS}
unstated = []
for p in PROJECTS:
    if p['is_uc_project']: continue
    stg = p['status']
    st = STAGE_STATE.get(stg)
    if stg == 'Building Permits Filed':
        st = 2 if p['entitled'] else 1
    row = dict(key=p['id'], addr=(p['address'] or '').title(), u=p['units'] or 0, stage=stg,
               entitled=d10(p['entitled']), last_insp=last_insp.get(p['id']))
    if st is None:
        (exits[stg] if stg in exits else unstated).append(row)
        continue
    anchor = {1: p['app_filed'], 2: p['entitled'], 3: p['bp_issued'], 4: p['bp_issued'], 5: p['co_date']}[st]
    STATES[st].append(row | dict(anchor=d10(anchor)))
withdrawn = exits['Withdrawn']
if unstated:
    print('UNMAPPED Explorer stages (not shown):', {r['stage'] for r in unstated}, len(unstated))

# ---- waiting-room tiers (BMC 23.404.060: lapse-eligible one year after approval unless exercised) ----
LAPSE = json.load(open(os.path.join(ROOT, 'data/processed/waiting_room_lapse_2026-07-14.json')))
overlay = {akey(w['addr']): w for w in LAPSE['projects'] if akey(w['addr'])}
LIVE_DONE = ('Issued', 'Finaled')
for r in STATES[2]:
    w = overlay.get(akey(r['addr']))
    ev = (w or {}).get('evidence')
    now = listed_status(ev['pn']) if ev else None
    if ev and now in LIVE_DONE:
        r['tier'], r['ev'] = 'permitted_unlinked', f"{ev['pn']}, {now} — not yet linked to this project in v4"
    elif ev and now and not now.startswith('Closed'):
        r['tier'], r['ev'] = 'mobilizing', f"{ev['pn']}, {now}"
    elif r['entitled'] and (TODAY - r['entitled']).days >= 365:
        r['tier'] = 'lapse_eligible'
        e = r['entitled']
        r['ev'] = f"since {e.replace(year=e.year + 1, day=min(e.day, 28) if e.month == 2 else e.day)}"
    else:
        r['tier'], r['ev'] = 'fresh', ''
TIER_LABEL = {'mobilizing': 'MOBILIZING — BP application live', 'fresh': 'fresh (<1 yr entitled)',
              'lapse_eligible': 'LAPSE-ELIGIBLE', 'permitted_unlinked': 'permit issued'}
tier_stats = {}
for r in STATES[2]:
    n, u = tier_stats.get(r['tier'], (0, 0))
    tier_stats[r['tier']] = (n + 1, u + r['u'])
def _t(t): return tier_stats.get(t, (0, 0))

# ---- ANCHOR: JN-K's audited majors funnel (a v2-built baseline until a v4 one is written) ----
bl = json.load(open(sorted(glob.glob(os.path.join(ROOT, 'data/baselines/completion_anatomy_baseline_*.json')))[-1]))
fig = bl['figures']
majors = {i: [r for r in STATES[i] if r['u'] >= 50] for i in STATES}
mw = [r for r in withdrawn if r['u'] >= 50]
checks = {
    'majors_completed': (len(majors[5]), fig['majors_completed']),
    'majors_building+stalled': (len(majors[3]) + len(majors[4]), fig['majors_permitted'] - fig['majors_completed']),
    'majors_waiting': (len(majors[2]), fig['majors_entitled'] - fig['majors_permitted']),
    'majors_withdrawn': (len(mw), fig['majors_withdrawn']),
}
drift = {k: v for k, v in checks.items() if v[0] != v[1]}
for k, (got, want) in checks.items():
    print(f"  anchor {k}: page {got}  JN-K {bl['as_of']} {want}{'' if got == want else '   <-- differs'}")
if drift and not ARGS.accept_anchor_drift:
    raise SystemExit(f"ANCHOR FAIL vs JN-K {bl['as_of']} (a v2-built baseline): {drift} — diagnose, or rerun with "
                     "--accept-anchor-drift once John has accepted the v4 figures")
anchor_passed = not drift
print('anchor', 'PASS' if anchor_passed else 'DRIFT ACCEPTED', 'vs', bl['as_of'], '| states:',
      {i: (len(STATES[i]), sum(r['u'] for r in STATES[i])) for i in STATES},
      '| exits', {x: len(v) for x, v in exits.items()})

# ---- render ----
n4 = len(STATES[4])
recent = sum(1 for r in STATES[4] if r['last_insp'] and (TODAY - d10(r['last_insp'])).days <= 183)
older = sum(1 for r in STATES[4] if r['last_insp'] and (TODAY - d10(r['last_insp'])).days > 183)
none4 = n4 - recent - older
NAMES = {1: 'Applied — not yet entitled', 2: 'Entitled — waiting for a building permit',
         3: 'Permit issued — no construction activity', 4: 'Under construction', 5: 'Complete'}
DESC = {
 1: 'In intake or under consideration at the planning counter. The clock that matters here is '
    'deemed-complete → decision.',
 2: ('THE WAITING ROOM. Fully approved and legal to seek a permit — nothing is being built. '
     'Housing dies of waiting here, not denial. Under BMC 23.404.060 a permit becomes '
     'LAPSE-ELIGIBLE one year after approval unless exercised (a filed building-permit '
     'application protects; the declaration is discretionary). The tiers, from the record: '
     f"{_t('mobilizing')[0]} projects ({_t('mobilizing')[1]:,} units) are MOBILIZING with live permit applications; "
     f"{_t('fresh')[0]} ({_t('fresh')[1]:,}) are fresh; {_t('lapse_eligible')[0]} projects "
     f"({_t('lapse_eligible')[1]:,} units) are ALREADY LAPSE-ELIGIBLE — the city has declared none of them lapsed. "
     f"({_t('permitted_unlinked')[0]} more show an issued permit not yet linked to the project in our record — "
     'data queue.)'),
 3: 'A building permit was issued more than two years ago and the record shows no inspection ever called '
    f'on it. {len(STATES[3])} projects sit here.',
 4: f'A building permit is issued and the work is being inspected. Of these {n4} projects, {recent} had an '
    f'inspection in the last six months, {older} were last inspected more than six months ago, and {none4} '
    'have a permit issued within the last two years and no inspection yet. The last column gives the latest '
    'inspection on the record.',
 5: 'Every building finaled — certificate of occupancy issued, keys in doors.',
}
COLORS = {1: '#7ec8e3', 2: '#4a6478', 3: '#ff9f7f', 4: '#ffd166', 5: '#8fd694'}
LEVERS = [
 ('Entitlement shot-clock & extension certainty',
  f"Entitled approvals quietly age out: {_t('lapse_eligible')[1]:,} units are already lapse-eligible under "
  'BMC 23.404.060 and none has been declared lapsed. A standing extension policy with a use-it-or-lose-it horizon '
  'makes the waiting room a queue instead of a shelf.', 2),
 ('Defer city fees to certificate of occupancy',
  'Fees due at permit issuance front-load cost onto the exact moment financing is hardest. '
  'Deferral to CO moves the bill to when the building earns.', 2),
 ('Permit-extension triage on the stalled shelf',
  'Contact every permit older than 18 months with no activity: extend the live ones, retire the '
  'dead ones — the register stops hiding both.', 3),
]

def esc(s): return str(s).replace('&', '&amp;').replace('<', '&lt;')

SECTION_CAP = {}   # None = show ALL rows. Every state defaults to the 12 largest.

def state_section(i):
    rows = sorted(STATES[i], key=lambda r: -r['u'])
    units = sum(r['u'] for r in rows)
    cap = SECTION_CAP.get(i, 12)
    shown = rows if cap is None else rows[:cap]
    trs = []
    for r in shown:
        yrs = f"{(TODAY - r['anchor']).days / 365:.1f} yrs" if r.get('anchor') else '—'
        anch = r['anchor'].isoformat() if r.get('anchor') else '—'
        if i == 2:
            extra = TIER_LABEL.get(r['tier'], '') + (f" ({r['ev']})" if r.get('ev') else '')
        elif i in (3, 4):
            extra = f"last inspection {r['last_insp']}" if r['last_insp'] else 'no inspection on record'
        elif i == 1:
            extra = r['stage']
        else:
            extra = ''
        trs.append(f"<tr><td>{esc(r['addr'])}</td><td class='num'>{r['u']:,}</td>"
                   f"<td>{anch}</td><td class='num'>{yrs}</td><td>{esc(extra)}</td></tr>")
    more = (f"<p class='foot'>Showing the {cap} largest by units — {len(rows):,} projects total in this state.</p>"
            if (cap is not None and len(rows) > cap) else '')
    return f"""
<section>
  <h2><span style="color:{COLORS[i]}">■</span> {i} · {NAMES[i]}</h2>
  <p class="big">{units:,} units <span style="font-size:1.1rem;color:#9fb8c8">across {len(rows):,} projects</span></p>
  <p>{DESC[i]}</p>
  <table><tr><th>project</th><th>units</th><th>in this state since</th><th>time in state</th><th>status evidence</th></tr>
  {''.join(trs)}</table>
  {more}
</section>"""

def flow_svg():
    total_u = sum(sum(r['u'] for r in STATES[i]) for i in STATES)
    parts, x = [], 20
    W = 660
    for i in range(1, 6):
        u = sum(r['u'] for r in STATES[i])
        w = max(28, u / total_u * (W - 5 * 8))
        parts.append(f'<rect x="{x:.0f}" y="30" width="{w:.0f}" height="54" rx="6" fill="{COLORS[i]}" opacity="0.9"/>')
        parts.append(f'<text x="{x + w/2:.0f}" y="57" fill="#10202b" font-size="15" font-weight="800" text-anchor="middle" font-family="inherit">{u:,}</text>')
        parts.append(f'<text x="{x + w/2:.0f}" y="74" fill="#10202b" font-size="10" text-anchor="middle" font-family="inherit">{len(STATES[i])} projects</text>')
        parts.append(f'<text x="{x + w/2:.0f}" y="104" fill="#9fb8c8" font-size="11" text-anchor="middle" font-family="inherit">{i}</text>')
        x += w + 8
    return (f'<svg viewBox="0 0 700 116" xmlns="http://www.w3.org/2000/svg" style="max-width:46rem; width:100%;" role="img" '
            f'aria-label="Units by pipeline state">{"".join(parts)}</svg>')

lever_html = ''.join(f"""
  <div class="lever"><h3>{esc(t)} <span class="tag modeled">modeled</span></h3>
  <p>{esc(body)} <b>Exposure: {sum(r['u'] for r in STATES[st]):,} units now in state {st}.</b></p></div>"""
  for t, body, st in LEVERS)

def _n(x): return f"{len(exits[x])} ({sum(r['u'] for r in exits[x]):,} proposed units)"
exit_line = (f"Exits: {_n('Withdrawn')} withdrawn by their applicants; {_n('Denied')} denied; "
             f"{_n('Expired')} expired or voided.")
gate_line = (f"The ≥50-unit subset is gate-checked against the audited JN-K funnel baseline ({bl['as_of']}) at "
             'generation time.' if anchor_passed else
             f"The JN-K funnel baseline ({bl['as_of']}) predates the v4 database; a v4 baseline is pending.")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Pipeline State — where every Berkeley housing project stands</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; background:#10202b; color:#eef3f6; }}
  .wrap {{ max-width: 52rem; margin: 0 auto; padding: 3rem 1.5rem 4rem; }}
  h1 {{ font-size:2.2rem; line-height:1.15; margin-bottom:.8rem; color:#fff; }}
  h2 {{ font-size:1.5rem; margin:2.4rem 0 .6rem; color:#7ec8e3; }}
  h3 {{ font-size:1.05rem; color:#ffd166; margin-bottom:.3rem; }}
  p {{ font-size:1.05rem; line-height:1.55; max-width:48rem; margin-bottom:.6rem; }}
  .big {{ font-size:2.2rem; font-weight:800; color:#ffd166; }}
  .kicker {{ text-transform:uppercase; letter-spacing:.14em; font-size:.85rem; color:#7ec8e3; margin-bottom:.8rem; }}
  .foot {{ font-size:.9rem; color:#9fb8c8; }}
  .src {{ margin-top:3rem; font-size:.82rem; color:#6d8496; border-top:1px solid #24384a; padding-top:1rem; }}
  table {{ border-collapse:collapse; margin:.6rem 0 .4rem; width:100%; max-width:46rem; }}
  td, th {{ padding:.3rem .8rem; border-bottom:1px solid #2b4356; font-size:.95rem; text-align:left; }}
  th {{ color:#9fb8c8; font-weight:600; }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .lever {{ background:#16283a; border:1px solid #24384a; border-radius:8px; padding:1rem 1.2rem; margin:.7rem 0; }}
  .tag {{ display:inline-block; font-size:.7rem; padding:.1rem .45rem; border-radius:3px; background:#5a4a1a; color:#ffd166; vertical-align:middle; }}
  a {{ color:#7ec8e3; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="kicker">A view of the record · berkeleybuild.com · as of {TODAY.isoformat()}</div>
  <h1>The Pipeline State</h1>
  <p>Where every tracked housing project stands <b>right now</b>, binned by the furthest <b>hard
  evidence</b> on its record — dates, permits and inspections, never status labels alone. The pattern to see:
  Berkeley's pipe doesn't close by denial; it narrows by waiting.</p>
  {flow_svg()}
  <p class="foot">Block width ∝ units. {exit_line} UC projects excluded (self-permitted, counted in beds).</p>
  {''.join(state_section(i) for i in (1, 2, 3, 4, 5))}
  <h2>The levers — what could move the stalled states</h2>
  <p>The record tells us the <i>exposure</i> — how many units sit in each state and for how long.
  Whether a lever moves them is policy judgment, so every lever wears its tag.</p>
  {lever_html}
  <div class="src">Derived {TODAY.isoformat()} from the canonical v4 database (its serving view v_projects, through
  the same projection as <a href="explorer.html">the Explorer</a>, so the two agree: each state is a group of the
  Explorer's stages). Stage dates: first application / entitlement / first building permit / the last building's
  certificate of occupancy. Construction activity = the inspections on the record for the project's buildings; a
  permit issued more than two years ago with no inspection ever is "no construction activity". Waiting-room tiers =
  BMC 23.404.060 one-year lapse-eligibility from the entitlement date, plus the building-permit APPLICATIONS found in
  the 2015-2026 harvest (data/processed/waiting_room_lapse_2026-07-14.json), each re-checked against the City's
  current listing of that record — lapse declaration is discretionary, so 'eligible' is a legal state, not a
  prediction. {gate_line} Coverage: tracked projects (the full permit-level record lives in
  <a href="housing-audit.html">the Audit</a>). Generator: scripts/gen_pipeline_state_page.py — the page regenerates
  from the record; numbers are never hand-edited. <a href="index.html">← berkeleybuild.com</a></div>
</div>
</body>
</html>
"""

# Re-stamp the site_meta block (description, canonical, Open Graph, favicon) that a whole fresh page would strip;
# block() has no image dependency. Never block the page on metadata.
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('site_meta', os.path.join(ROOT, 'scripts', 'site_meta.py'))
    site_meta = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(site_meta)
    html = html.replace('</head>', site_meta.block('pipeline-state.html') + '</head>', 1)
except Exception as e:
    print(f'  WARNING: site_meta block not applied ({e})')

os.makedirs(ARGS.out, exist_ok=True)
out = os.path.join(ARGS.out, 'pipeline-state.html')
open(out, 'w').write(html)
print('wrote', out, f'({len(html)//1024}KB)')
