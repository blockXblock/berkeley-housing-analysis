#!/usr/bin/env python3
"""Generate docs/players.html — THE PLAYERS VIEW (phase 1).

Who builds Berkeley: developers, architects, owners from v2's curated participants
(organizations + project_participants), linked by shared projects. Node size = units;
edge weight = shared projects. Each player's pipeline mix uses the same evidence
binning as the Pipeline-State view.

PHASE-1 HONESTY (stated on the page): coverage is majors-heavy (the ADU fabric's
hundreds of small builders are not in the record); an edge = co-occurrence on a
project, not contract knowledge; investors and construction lenders are NOT yet in
the record (County Recorder deeds of trust + SOS filings — acquisition queued).

MACHINERY: re-run after v2 changes, commit docs/players.html.
Run: /opt/miniconda3/envs/jupyter_env/bin/python scripts/gen_players_page.py
"""
import json
import os
import sqlite3
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = date.today()
v2 = sqlite3.connect(f"file:{os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')}?mode=ro", uri=True)

# ---- project states (same evidence binning as gen_pipeline_state_page) ----
activity = {r[0] for r in v2.execute("""SELECT DISTINCT project_id FROM project_events e
    JOIN vocabulary_event_types t ON t.id=e.event_type_id
    WHERE t.code IN ('construction_start_observed','topped_out')""")}
bp_any = dict(v2.execute("""SELECT project_id, MIN(substr(event_date,1,10)) FROM project_events e
    JOIN vocabulary_event_types t ON t.id=e.event_type_id
    WHERE t.code='building_permit_issued' GROUP BY project_id"""))
STATE_NAMES = {1: 'applied', 2: 'waiting', 3: 'permit-idle', 4: 'building', 5: 'complete', 0: 'withdrawn'}
proj = {}
for pid, addr, u, e, bp, co, status in v2.execute("""SELECT project_id, address_display, total_units,
        entitled_date, bp_issued_date, co_issued_date, status_code FROM v_projects_flat"""):
    bp = bp or bp_any.get(pid)
    if co: st = 5
    elif bp and (pid in activity or status == 'under_construction'): st = 4
    elif bp: st = 3
    elif status == 'withdrawn': st = 0
    elif e: st = 2
    else: st = 1
    proj[pid] = dict(addr=(addr or '').title(), u=u or 0, state=st)

# ---- players ----
players = {}   # name -> {roles, projects:set}
for name, role, pid in v2.execute("""SELECT o.name, rt.code, pp.project_id
        FROM project_participants pp
        JOIN vocabulary_role_types rt ON rt.id=pp.role_type_id
        JOIN organizations o ON o.id=pp.organization_id"""):
    p = players.setdefault(name, dict(roles=set(), projects=set()))
    p['roles'].add({'developer_of_record': 'developer', 'architect_design': 'architect',
                    'owner_current': 'owner'}.get(role, role))
    p['projects'].add(pid)

by_project = defaultdict(list)
for name, p in players.items():
    for pid in p['projects']:
        by_project[pid].append(name)

edges = defaultdict(lambda: dict(w=0, shared=[]))
for pid, names in by_project.items():
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = sorted((names[i], names[j]))
            e = edges[(a, b)]
            e['w'] += 1
            e['shared'].append(proj[pid]['addr'])

ROLE_COLOR = {'developer': '#ffd166', 'architect': '#7ec8e3', 'owner': '#9d8fd8'}
def color(roles):
    for r in ('developer', 'architect', 'owner'):
        if r in roles: return ROLE_COLOR[r]
    return '#9fb8c8'

nodes = []
for name, p in sorted(players.items(), key=lambda kv: -sum(proj[i]['u'] for i in kv[1]['projects'])):
    units = sum(proj[i]['u'] for i in p['projects'])
    mix = defaultdict(int)
    for i in p['projects']: mix[STATE_NAMES[proj[i]['state']]] += 1
    nodes.append(dict(id=name, roles=sorted(p['roles']), units=units, n=len(p['projects']),
                      color=color(p['roles']), mix=dict(mix),
                      projects=sorted(({'a': proj[i]['addr'], 'u': proj[i]['u'],
                                        's': STATE_NAMES[proj[i]['state']]} for i in p['projects']),
                                      key=lambda d: -d['u'])))
links = [dict(source=a, target=b, w=e['w'], shared=e['shared']) for (a, b), e in edges.items()]
covered = {i for p in players.values() for i in p['projects']}
cov_units = sum(proj[i]['u'] for i in covered)
print(f'players {len(nodes)}, links {len(links)}, projects covered {len(covered)} ({cov_units:,}u)')

table_rows = ''.join(
    f"<tr><td>{n['id']}</td><td>{', '.join(n['roles'])}</td><td class='num'>{n['n']}</td>"
    f"<td class='num'>{n['units']:,}</td><td>{' · '.join(f'{k} {v}' for k, v in sorted(n['mix'].items()))}</td></tr>"
    for n in nodes if n['n'] >= 2)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Players — who builds Berkeley</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; background:#10202b; color:#eef3f6; }}
  .wrap {{ max-width: 56rem; margin: 0 auto; padding: 3rem 1.5rem 4rem; }}
  h1 {{ font-size:2.2rem; margin-bottom:.8rem; color:#fff; }}
  h2 {{ font-size:1.4rem; margin:2.2rem 0 .6rem; color:#7ec8e3; }}
  p {{ font-size:1.02rem; line-height:1.55; max-width:48rem; margin-bottom:.6rem; }}
  .kicker {{ text-transform:uppercase; letter-spacing:.14em; font-size:.85rem; color:#7ec8e3; margin-bottom:.8rem; }}
  .foot {{ font-size:.9rem; color:#9fb8c8; }}
  .src {{ margin-top:3rem; font-size:.82rem; color:#6d8496; border-top:1px solid #24384a; padding-top:1rem; }}
  table {{ border-collapse:collapse; margin:.6rem 0; width:100%; }}
  td, th {{ padding:.32rem .7rem; border-bottom:1px solid #2b4356; font-size:.92rem; text-align:left; }}
  th {{ color:#9fb8c8; font-weight:600; }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  #net {{ width:100%; height:560px; background:#0c1922; border:1px solid #24384a; border-radius:10px; }}
  #panel {{ background:#16283a; border:1px solid #24384a; border-radius:8px; padding: .9rem 1.1rem; min-height:3.5rem; margin-top:.6rem; font-size:.95rem; }}
  .lg {{ font-size:.85rem; color:#9fb8c8; margin:.4rem 0 0; }}
  a {{ color:#7ec8e3; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="kicker">A view of the record · berkeleybuild.com · as of {TODAY.isoformat()}</div>
  <h1>The Players — who builds Berkeley</h1>
  <p>The organizations on the record of Berkeley's major housing projects, joined where they share a
  project. <b>Drag, hover, click.</b> Node size ∝ units across a player's projects; a line means the
  two appear on the same project.</p>
  <p class="lg"><span style="color:#ffd166">●</span> developer &nbsp;
  <span style="color:#7ec8e3">●</span> architect &nbsp; <span style="color:#9d8fd8">●</span> owner
  &nbsp;·&nbsp; {len(nodes)} players · {len(covered)} projects · {cov_units:,} units across their projects, all stages</p>
  <svg id="net"></svg>
  <div id="panel">Click a player to see their projects.</div>

  <h2>The repeat players (2+ projects)</h2>
  <table><tr><th>player</th><th>roles</th><th class="num">projects</th><th class="num">units</th><th>pipeline mix</th></tr>
  {table_rows}</table>

  <h2>What this view does not know yet</h2>
  <p><b>The money is missing.</b> Construction lenders live on deeds of trust at the County
  Recorder; investors in LLC filings with the Secretary of State. Neither is loaded yet — this
  page will say so until they are. Coverage is majors-heavy: the neighborhood fabric's hundreds
  of small builders and homeowners aren't named in the record. And a line between two players
  means they <i>appear on the same project</i> — the record does not know who hired whom.</p>

  <div class="src">Derived {TODAY.isoformat()} from the canonical v2 database (organizations ×
  project_participants: developer-of-record, design architect, current owner; pipeline mix uses the
  same evidence binning as <a href="pipeline-state.html">the Pipeline State</a>). Cross-role
  identities (e.g. a developer that also owns) are one node. Generator: scripts/gen_players_page.py —
  regenerates from the record; never hand-edited. <a href="index.html">← berkeleybuild.com</a></div>
</div>
<script>
const NODES = {json.dumps(nodes)};
const LINKS = {json.dumps(links)};
const svg = document.getElementById('net');
const W = svg.clientWidth || 860, H = 560;
svg.setAttribute('viewBox', `0 0 ${{W}} ${{H}}`);
const N = NODES.map((d,i) => ({{...d,
  x: W/2 + Math.cos(i*2.399) * (120 + (i%7)*28),
  y: H/2 + Math.sin(i*2.399) * (100 + (i%5)*26), vx:0, vy:0,
  r: 5 + Math.sqrt(d.units || 1) * 0.55 }}));
const byId = Object.fromEntries(N.map(d => [d.id, d]));
const L = LINKS.map(l => ({{...l, a: byId[l.source], b: byId[l.target]}}));
function tick(alpha) {{
  for (const l of L) {{
    const dx = l.b.x - l.a.x, dy = l.b.y - l.a.y;
    const dist = Math.max(1, Math.hypot(dx, dy)), want = 90;
    const f = (dist - want) / dist * 0.02 * alpha * (1 + l.w * .3);
    l.a.vx += dx * f; l.a.vy += dy * f; l.b.vx -= dx * f; l.b.vy -= dy * f;
  }}
  for (let i = 0; i < N.length; i++) for (let j = i + 1; j < N.length; j++) {{
    const a = N[i], b = N[j];
    let dx = b.x - a.x, dy = b.y - a.y;
    let d2 = dx*dx + dy*dy || 1;
    if (d2 < 40000) {{ const f = 900 * alpha / d2; const d = Math.sqrt(d2);
      dx /= d; dy /= d; a.vx -= dx * f; a.vy -= dy * f; b.vx += dx * f; b.vy += dy * f; }}
  }}
  for (const n of N) {{
    n.vx += (W/2 - n.x) * 0.002 * alpha; n.vy += (H/2 - n.y) * 0.002 * alpha;
    n.x = Math.max(n.r, Math.min(W - n.r, n.x + n.vx));
    n.y = Math.max(n.r, Math.min(H - n.r, n.y + n.vy));
    n.vx *= .85; n.vy *= .85;
  }}
}}
for (let it = 0; it < 300; it++) tick(1 - it/320);
const NS = 'http://www.w3.org/2000/svg';
for (const l of L) {{
  const e = document.createElementNS(NS, 'line');
  e.setAttribute('stroke', '#33506b'); e.setAttribute('stroke-width', Math.min(4, l.w));
  e.setAttribute('x1', l.a.x); e.setAttribute('y1', l.a.y);
  e.setAttribute('x2', l.b.x); e.setAttribute('y2', l.b.y);
  svg.appendChild(e); l.el = e;
}}
const panel = document.getElementById('panel');
for (const n of N) {{
  const g = document.createElementNS(NS, 'g'); g.style.cursor = 'pointer';
  const c = document.createElementNS(NS, 'circle');
  c.setAttribute('cx', n.x); c.setAttribute('cy', n.y); c.setAttribute('r', n.r);
  c.setAttribute('fill', n.color); c.setAttribute('fill-opacity', '.85');
  c.setAttribute('stroke', '#10202b');
  const t = document.createElementNS(NS, 'text');
  t.setAttribute('x', n.x); t.setAttribute('y', n.y - n.r - 4);
  t.setAttribute('text-anchor', 'middle'); t.setAttribute('font-size', n.units > 300 ? '11' : '9');
  t.setAttribute('fill', '#c8d8e4'); t.textContent = n.id.length > 26 ? n.id.slice(0, 24) + '…' : n.id;
  g.appendChild(c); g.appendChild(t); svg.appendChild(g);
  g.addEventListener('click', () => {{
    panel.innerHTML = `<b style="color:${{n.color}}">${{n.id}}</b> — ${{n.roles.join(', ')}} · ` +
      `${{n.n}} project(s) · ${{n.units.toLocaleString()}} units<br>` +
      n.projects.map(p => `${{p.a}} (${{p.u}}u · ${{p.s}})`).join(' · ');
  }});
  // drag
  let drag = null;
  g.addEventListener('pointerdown', ev => {{ drag = n; ev.preventDefault(); }});
  svg.addEventListener('pointermove', ev => {{
    if (drag !== n) return;
    const pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    n.x = p.x; n.y = p.y;
    c.setAttribute('cx', n.x); c.setAttribute('cy', n.y);
    t.setAttribute('x', n.x); t.setAttribute('y', n.y - n.r - 4);
    for (const l of L) if (l.a === n || l.b === n) {{
      l.el.setAttribute('x1', l.a.x); l.el.setAttribute('y1', l.a.y);
      l.el.setAttribute('x2', l.b.x); l.el.setAttribute('y2', l.b.y);
    }}
  }});
  svg.addEventListener('pointerup', () => {{ drag = null; }});
}}
</script>
</body>
</html>
"""
out = os.path.join(ROOT, 'docs', 'players.html')
open(out, 'w').write(html)
print('wrote', out, f'({len(html)//1024}KB)')
