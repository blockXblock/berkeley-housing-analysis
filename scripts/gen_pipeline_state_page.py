#!/usr/bin/env python3
"""Generate docs/pipeline-state.html — THE PIPELINE-STATE VIEW.

Every tracked (non-UC) project binned by FURTHEST HARD EVIDENCE into five states:
  1 applied, not yet entitled          (anchor: filed_date = MIN application)
  2 entitled, no building permit       (the waiting room; anchor: entitled_date)
  3 BP issued, no construction activity(the stalled shelf; anchor: bp_issued_date)
  4 under construction                 (activity = construction_start/topped_out event,
                                        or current status under_construction — noted)
  5 complete                           (anchor: co_issued_date, verdict-driven)
Withdrawn (status withdrawn, no BP/CO) shown as the voluntary-exit footnote.

ANCHOR: the >=50u subset of these bins must equal JN-K's audited funnel figures
(completion_anatomy_baseline_* latest) — mismatch halts generation.

MACHINERY: re-run after any v2 change, then commit docs/pipeline-state.html.
Run: /opt/miniconda3/envs/jupyter_env/bin/python scripts/gen_pipeline_state_page.py
"""
import glob
import json
import os
import sqlite3
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = date.today()

v2 = sqlite3.connect(f"file:{os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')}?mode=ro", uri=True)
uc = {r[0] for r in v2.execute("""SELECT project_id FROM project_classifications pc
    JOIN vocabulary_classification_types v ON pc.classification_type_id=v.id WHERE v.code='uc_project'""")}
activity = {r[0] for r in v2.execute("""SELECT DISTINCT project_id FROM project_events e
    JOIN vocabulary_event_types t ON t.id=e.event_type_id
    WHERE t.code IN ('construction_start_observed','topped_out')""")}
# INSPECTION OVERLAY (2026-07-14 harvest of all 23 primary permits in states 3/4):
# dated inspection evidence outranks events/status for the building-vs-idle split.
INSPECT = json.load(open(os.path.join(ROOT, 'data/processed/inspection_activity_2026-07-14.json')))
insp = {int(k): v for k, v in INSPECT['projects'].items()}

def d10(s):
    s = str(s or '')[:10]
    try: return date.fromisoformat(s)
    except ValueError: return None

STATES = {i: [] for i in range(1, 6)}
withdrawn, unstated = [], 0
for pid, addr, u, f, e, bp, co, status in v2.execute("""SELECT project_id, address_display,
        total_units, filed_date, entitled_date, bp_issued_date, co_issued_date, status_code
        FROM v_projects_flat"""):
    if pid in uc: continue
    u = u or 0
    f, e, bp, co = d10(f), d10(e), d10(bp), d10(co)
    row = dict(pid=pid, addr=(addr or '').title(), u=u, status=status)
    iv = insp.get(pid)
    row['last_insp'] = iv['last'] if iv else None
    if co: STATES[5].append(row | dict(anchor=co))
    elif bp and iv:   # inspection evidence wins where we have it
        STATES[4 if iv['verdict'] == 'active' else 3].append(row | dict(anchor=bp))
    elif bp and (pid in activity or status == 'under_construction'):
        STATES[4].append(row | dict(anchor=bp))
    elif bp: STATES[3].append(row | dict(anchor=bp))
    elif status == 'withdrawn': withdrawn.append(row)
    elif e: STATES[2].append(row | dict(anchor=e))
    elif f or status in ('in_review', 'pre_application'):
        STATES[1].append(row | dict(anchor=f))
    else: unstated += 1

# ---- ANCHOR to JN-K's audited majors funnel ----
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
for k, (got, want) in checks.items():
    assert got == want, f'ANCHOR FAIL {k}: page derives {got}, JN-K baseline says {want} — diagnose before publishing'
print('anchor PASS vs', bl['as_of'], '| states:',
      {i: (len(STATES[i]), sum(r['u'] for r in STATES[i])) for i in STATES}, '| withdrawn', len(withdrawn))

# ---- render ----
NAMES = {1: 'Applied — not yet entitled', 2: 'Entitled — waiting for a building permit',
         3: 'Permit issued — no construction activity', 4: 'Under construction', 5: 'Complete'}
DESC = {
 1: 'In intake or under consideration at the planning counter. The clock that matters here is '
    'deemed-complete → decision (median 410 days for majors).',
 2: 'THE WAITING ROOM. Fully approved and legal to seek a permit — nothing is being built. '
    'Housing dies of waiting here, not denial.',
 3: 'A permit exists but the inspection record shows no recent activity — verified against every '
    'permit\'s full inspection history (harvested 2026-07-14). Two projects have permits and have '
    'NEVER called an inspection.',
 4: 'Dated inspection evidence on the record (last inspection within 6 months — several inspected '
    'this very week). Once building starts, 95% of units reach completion.',
 5: 'Certificate of occupancy issued — keys in doors. The audited count.',
}
COLORS = {1: '#7ec8e3', 2: '#4a6478', 3: '#ff9f7f', 4: '#ffd166', 5: '#8fd694'}
LEVERS = [
 ('Entitlement shot-clock & extension certainty',
  'Entitled approvals quietly age out. A standing extension policy (with a use-it-or-lose-it '
  'horizon) makes the waiting room a queue instead of a shelf.', 2),
 ('Defer city fees to certificate of occupancy',
  'Fees due at permit issuance front-load cost onto the exact moment financing is hardest. '
  'Deferral to CO moves the bill to when the building earns.', 2),
 ('Permit-extension triage on the stalled shelf',
  'Contact every permit older than 18 months with no activity: extend the live ones, retire the '
  'dead ones — the register stops hiding both.', 3),
]

def esc(s): return str(s).replace('&', '&amp;').replace('<', '&lt;')

def state_section(i):
    rows = sorted(STATES[i], key=lambda r: -r['u'])
    units = sum(r['u'] for r in rows)
    trs = []
    for r in rows[:12]:
        yrs = f"{(TODAY - r['anchor']).days / 365:.1f} yrs" if r.get('anchor') else '—'
        anch = r['anchor'].isoformat() if r.get('anchor') else '—'
        li = r.get('last_insp') or ('never' if i in (3, 4) and r.get('last_insp') is None and r['pid'] in insp else '—')
        trs.append(f"<tr><td>{esc(r['addr'])}</td><td class='num'>{r['u']:,}</td>"
                   f"<td>{anch}</td><td class='num'>{yrs}</td><td>{li if i in (3,4) else ''}</td></tr>")
    more = f"<p class='foot'>…and {len(rows)-12} more (shown: largest 12 by units).</p>" if len(rows) > 12 else ''
    return f"""
<section>
  <h2><span style="color:{COLORS[i]}">■</span> {i} · {NAMES[i]}</h2>
  <p class="big">{units:,} units <span style="font-size:1.1rem;color:#9fb8c8">across {len(rows):,} projects</span></p>
  <p>{DESC[i]}</p>
  <table><tr><th>project</th><th>units</th><th>in this state since</th><th>time in state</th><th>last inspection</th></tr>
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
  evidence</b> on its record — dates and events, never status labels alone. The pattern to see:
  Berkeley's pipe doesn't close by denial; it narrows by waiting.</p>
  {flow_svg()}
  <p class="foot">Block width ∝ units. {len(withdrawn)} projects ({sum(r['u'] for r in withdrawn):,} proposed units)
  were withdrawn by their applicants — the only exits are voluntary. UC projects excluded (self-permitted,
  counted in beds).</p>
  {''.join(state_section(i) for i in (2, 3, 1, 4, 5))}
  <h2>The levers — what could move the stalled states</h2>
  <p>The record tells us the <i>exposure</i> — how many units sit in each state and for how long.
  Whether a lever moves them is policy judgment, so every lever wears its tag.</p>
  {lever_html}
  <div class="src">Derived {TODAY.isoformat()} from the canonical v2 database (stage dates: first-application /
  entitlement / first non-subsidiary permit / verdict-driven CO — the MIN-semantics fields corrected 2026-07-10);
  construction activity = the harvested inspection record (all 23 primary permits of states 3/4, full histories,
  2026-07-14 — see data/processed/inspection_activity_2026-07-14.json), falling back to observed-start/topping-out
  events or status only where no inspection data exists; permit evidence = the view's first non-subsidiary permit ONLY — the 2026-07-14 adjudication removed the
  any-permit-event fallback after harvest verification showed the four affected majors' only permit events were
  trades permits (three have never filed a primary building permit; 2138 Kittredge is phased mid-permitting). The ≥50-unit subset is gate-checked against the audited JN-K funnel baseline ({bl['as_of']}) at
  generation time. Coverage: tracked projects (the full permit-level record lives in
  <a href="housing-audit.html">the Audit</a>). Generator: scripts/gen_pipeline_state_page.py — the page regenerates
  from the record; numbers are never hand-edited. <a href="index.html">← berkeleybuild.com</a></div>
</div>
</body>
</html>
"""
out = os.path.join(ROOT, 'docs', 'pipeline-state.html')
open(out, 'w').write(html)
print('wrote', out, f'({len(html)//1024}KB)')
