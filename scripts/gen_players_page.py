#!/usr/bin/env python3
"""Generate docs/players.html — THE PLAYERS VIEW (phase 1).

READS v4 SINCE 2026-10-02: databases/berkeley_housing_v4.db, read-only (mode=ro). Projects (address, units, stage)
come from the Explorer exporter's own projection (scripts/export_explorer_data_v4.get_projects over v_projects), so a
player's pipeline mix uses the same stages as the Explorer and the Pipeline State page. Players come from the serving
view v_project_people:
  developer  <- roles developer (CTCAC list) and plans_developer (plans' title blocks) ONLY — an owner is never
                relabelled a developer
  architect  <- plans_architect
  applicant  <- applicant (Planning log) and plans_applicant
  owner      <- v_projects.owner_current (the Explorer's owner); organisation owners drawn as nodes
(Before 2026-10-02 it read v2's curated organizations x project_participants.)

NAMES (John, 2026-10-02: owner names are public record -- "show names"): every developer, architect and applicant is a
node, firm or person. Owner nodes are organisations only -- this page's layout choice since v2 (who builds, not every
household); individual owners are named in the Explorer and the database.

Node size = units; edge weight = shared projects. An edge = co-occurrence on a project, not contract knowledge;
investors and construction lenders are NOT yet in the record (County Recorder deeds of trust + SOS filings).

MACHINERY: re-run after any v4 rebuild, commit docs/players.html.
Run: .venv/bin/python scripts/gen_players_page.py [--out DIR]
     (--out or env SITE_OUT: write DIR/players.html instead of docs/players.html)
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from export_explorer_data_v4 import DB_PATH, get_projects   # noqa: E402  the Explorer's own v4 projection
from housing_rules.owner_name import is_organisation          # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.environ.get('SITE_OUT') or os.path.join(ROOT, 'docs'),
                help='directory to write players.html into (default docs/)')
ARGS = ap.parse_args()

TODAY = date.today()
v4 = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

# ---- project states: the Explorer's stages, named as the Pipeline State page groups them ----
STAGE_NAME = {'Under Review': 'applied', 'Pre-Application': 'applied', 'Entitled': 'waiting',
              'Entitled but Inactive': 'waiting', 'Permitted but Inactive': 'permit-idle',
              'Under Construction': 'building', 'Completed': 'complete', 'Withdrawn': 'withdrawn',
              'Denied': 'denied', 'Expired': 'expired'}
proj = {}
for p in get_projects(v4):
    st = STAGE_NAME.get(p['status']) or ('waiting' if p['entitled'] else 'applied')  # Building Permits Filed
    proj[p['id']] = dict(addr=(p['address'] or '').title(), u=p['units'] or 0, state=st, owner=p['owner'])

# ---- players ----
ROLE = {'developer': 'developer', 'plans_developer': 'developer', 'plans_architect': 'architect',
        'applicant': 'applicant', 'plans_applicant': 'applicant'}
FIRM = re.compile(r"\b(ARCHITECTS?|ARCHITECTURE|STUDIO|DESIGN|CORPORATION|DEVELOPMENT|HOUSING|INTERESTS)\b")


def nkey(name):
    """One node per firm however the records punctuate it ('STACKHOUSE | DE LA PEÑA ...' == 'Stackhouse De La Peña ...')."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w&]+", " ", name.upper())).strip()


def names_a_person(name):
    """A joint title like 'KEY ROUTE PARTNERS LLC & PAULINO EDWARD ETAL' passes is_organisation on its LLC, yet names
    a person. Any '&'/','-separated part of two or more words that is not itself a firm is read as a person."""
    joined = re.sub(r",\s*(LLC|L\.L\.C|INC|LP|L\.P|LTD|CORP)\b", r" \1", name, flags=re.I)   # 'X Ave, LLC' is one name
    parts = [x.strip() for x in re.split(r"[&,]", joined) if x.strip()]
    return len(parts) > 1 and any(len(nkey(x).split()) >= 2 and not is_organisation(x) and not FIRM.search(x.upper())
                                  for x in parts)


def nameable(name, roles):
    """Names are public record and shown (John, 2026-10-02: "show names"): every developer, architect and applicant
    is a node. OWNER nodes keep this page's design from before the v4 cutover (the v2 page also drew organisation
    owners only, so the graph shows who builds rather than every household) -- a layout choice, not masking."""
    if set(roles) - {'owner'}:
        return True
    return is_organisation(name)


def drop_person_prefix(name):
    """'Ali Kia, Spirit Residential Group, LLC' -> 'Spirit Residential Group, LLC': a record that names the person
    filing on a firm's behalf keeps the firm, never the person."""
    head, _, rest = name.partition(',')
    if (len(nkey(rest).split()) >= 2 and not nameable(head, {'applicant'})   # 'X Ave, LLC' is one firm name
            and nameable(rest.strip(), {'applicant'})):
        return rest.strip()
    return name


raw = []   # (key, display name, role, project)
for k, role, name in v4.execute(f"""SELECT DISTINCT project_key, role, TRIM(name) FROM v_project_people
                                    WHERE role IN ({','.join('?' * len(ROLE))}) AND TRIM(COALESCE(name, '')) != ''""",
                                tuple(ROLE)):
    if k in proj:
        raw.append((nkey(name), name, ROLE[role], k))
for k, p in proj.items():
    if p['owner']:
        raw.append((nkey(p['owner']), p['owner'], 'owner', k))
# distinct private-individual owners (named nowhere on this page; counted for the note below)
n_individual_owners = len({o for (o,) in v4.execute("SELECT DISTINCT owner_current FROM v_projects WHERE owner_current > ''")
                           if not is_organisation(o)})

players, spellings = {}, defaultdict(Counter)   # key -> {roles, projects:set}
for key, name, role, k in raw:
    pl = players.setdefault(key, dict(roles=set(), projects=set()))
    pl['roles'].add(role); pl['projects'].add(k)
    spellings[key][name] += 1

# Decide which players are NODES here, before edges are built, so a line never connects to one the page does not draw.
_excluded = {kk for kk, p in players.items() if not nameable(spellings[kk].most_common(1)[0][0], p['roles'])}
n_excluded_prof = sum(1 for kk in _excluded if players[kk]['roles'] - {'owner'})
n_individual_owners += len(_excluded) - n_excluded_prof    # joint titles naming a person (names_a_person)
players = {spellings[kk].most_common(1)[0][0]: p for kk, p in players.items() if kk not in _excluded}

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

ROLE_COLOR = {'developer': '#ffd166', 'architect': '#7ec8e3', 'owner': '#9d8fd8', 'applicant': '#9fb8c8'}
def color(roles):
    for r in ('developer', 'architect', 'owner', 'applicant'):
        if r in roles: return ROLE_COLOR[r]
    return '#9fb8c8'

nodes = []
for name, p in sorted(players.items(), key=lambda kv: -sum(proj[i]['u'] for i in kv[1]['projects'])):
    units = sum(proj[i]['u'] for i in p['projects'])
    mix = defaultdict(int)
    for i in p['projects']: mix[proj[i]['state']] += 1
    nodes.append(dict(id=name, roles=sorted(p['roles']), units=units, n=len(p['projects']),
                      color=color(p['roles']), mix=dict(mix),
                      projects=sorted(({'a': proj[i]['addr'], 'u': proj[i]['u'],
                                        's': proj[i]['state']} for i in p['projects']),
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
  #net {{ display:block; width:96vw; margin-left:calc(50% - 48vw); height:72vh; min-height:560px;
         background:#0c1922; border:1px solid #24384a; border-radius:10px; touch-action:none; }}
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
  project. <b>Pinch or ⌘-scroll (or the buttons) to zoom · drag the background to pan · drag nodes · click for details.</b> Node size ∝ units across a player's projects; a line means the
  two appear on the same project.</p>
  <p class="lg"><span style="color:#ffd166">●</span> developer &nbsp;
  <span style="color:#7ec8e3">●</span> architect &nbsp; <span style="color:#9d8fd8">●</span> owner
  &nbsp; <span style="color:#9fb8c8">●</span> applicant
  &nbsp;·&nbsp; {len(nodes)} players · {len(covered)} projects · {cov_units:,} units across their projects, all stages</p>
  <div style="position:relative;">
    <svg id="net"></svg>
    <div style="position:absolute; top:.6rem; right:calc(50% - 48vw + .8rem); display:flex; gap:.35rem;">
      <button id="zin"  style="width:2rem;height:2rem;border-radius:6px;border:1px solid #33506b;background:#16283a;color:#eef3f6;font-size:1.1rem;cursor:pointer;">+</button>
      <button id="zout" style="width:2rem;height:2rem;border-radius:6px;border:1px solid #33506b;background:#16283a;color:#eef3f6;font-size:1.1rem;cursor:pointer;">−</button>
      <button id="zreset" style="height:2rem;padding:0 .5rem;border-radius:6px;border:1px solid #33506b;background:#16283a;color:#9fb8c8;font-size:.8rem;cursor:pointer;">reset</button>
    </div>
  </div>
  <div id="panel">Click a player to see their projects.</div>

  <h2>The repeat players (2+ projects)</h2>
  <table><tr><th>player</th><th>roles</th><th class="num">projects</th><th class="num">units</th><th>pipeline mix</th></tr>
  {table_rows}</table>

  <h2>Players Notes — the stories behind the record</h2>
  <p>This network shows who appears on the record; the <a href="players-notes/">Players Notes
  series</a> tells their stories. <b>Note № 1: <a href="players-notes/roots-and-reckoning/">Roots
  &amp; Reckoning</a></b> — Indian-origin families shaping Berkeley, from the city's 1916 invention
  of exclusionary zoning to the rise and fall of Lakireddy Bali Reddy, once Berkeley's largest
  private landlord. An interactive, fully sourced timeline.</p>

  <h2>What this view does not know yet</h2>
  <p><b>The money is missing.</b> Construction lenders live on deeds of trust at the County
  Recorder; investors in LLC filings with the Secretary of State. Neither is loaded yet — this
  page will say so until they are. Coverage is majors-heavy: the neighborhood fabric's hundreds
  of small builders and homeowners aren't named in the record.</p>
  <p><b>Who appears here.</b> Everyone named on the record in a professional role — developer, architect,
  applicant, firm or person — plus owners that are <i>organizations</i>. The {n_individual_owners:,} individual
  owners (including family trusts) are named in the Explorer and the database rather than drawn here, so the
  graph shows who builds rather than every household that holds title.
  Their parcels are shown, as title records, on
  <a href="maps/berkeley_ownership.html">the ownership map</a>. And a line between two players
  means they <i>appear on the same project</i> — the record does not know who hired whom.</p>

  <div class="src">Derived {TODAY.isoformat()} from the canonical v4 database (the people named on each
  project's records: developers from the state's tax-credit list and the plans' title blocks, architects from the
  plans, applicants from the Planning log and the plans, current owners of record; pipeline mix uses the same
  stages as <a href="explorer.html">the Explorer</a> and <a href="pipeline-state.html">the Pipeline State</a>).
  Spellings of one firm are one node. Cross-role
  identities (e.g. a developer that also owns) are one node. Generator: scripts/gen_players_page.py —
  regenerates from the record; never hand-edited. <a href="index.html">← berkeleybuild.com</a></div>
</div>
<script>
const NODES = {json.dumps(nodes)};
const LINKS = {json.dumps(links)};
const svg = document.getElementById('net');
const W = svg.clientWidth || 860, H = svg.clientHeight || 620;
const vb = {{x: 0, y: 0, w: W, h: H}};
function setVB() {{ svg.setAttribute('viewBox', `${{vb.x}} ${{vb.y}} ${{vb.w}} ${{vb.h}}`); }}
setVB();
function zoomAt(cx, cy, k) {{
  if (vb.w * k < W/8 || vb.w * k > W*2.5) return;
  const pt = svg.createSVGPoint(); pt.x = cx; pt.y = cy;
  const p = pt.matrixTransform(svg.getScreenCTM().inverse());
  vb.x = p.x - (p.x - vb.x) * k; vb.y = p.y - (p.y - vb.y) * k;
  vb.w *= k; vb.h *= k; setVB();
}}
svg.addEventListener('wheel', ev => {{
  if (!(ev.ctrlKey || ev.metaKey)) return;   // plain scroll = page scroll; pinch / cmd+scroll = zoom
  ev.preventDefault();
  zoomAt(ev.clientX, ev.clientY, ev.deltaY > 0 ? 1.15 : 1/1.15);
}}, {{passive: false}});
for (const [id, k] of [['zin', 1/1.3], ['zout', 1.3], ['zreset', 0]]) {{
  document.getElementById(id).addEventListener('click', () => {{
    if (!k) {{ vb.x = 0; vb.y = 0; vb.w = W; vb.h = H; setVB(); return; }}
    const r = svg.getBoundingClientRect();
    zoomAt(r.x + r.width/2, r.y + r.height/2, k);
  }});
}}
let pan = null;
svg.addEventListener('pointerdown', ev => {{
  if (ev.target === svg) {{ pan = {{x: ev.clientX, y: ev.clientY}}; svg.setPointerCapture(ev.pointerId); }}
}});
svg.addEventListener('pointermove', ev => {{
  if (!pan) return;
  const sx = vb.w / svg.clientWidth;
  vb.x -= (ev.clientX - pan.x) * sx; vb.y -= (ev.clientY - pan.y) * sx;
  pan = {{x: ev.clientX, y: ev.clientY}}; setVB();
}});
svg.addEventListener('pointerup', () => {{ pan = null; }});
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
os.makedirs(ARGS.out, exist_ok=True)
out = os.path.join(ARGS.out, 'players.html')

# Re-stamp the site_meta block. A generator that writes a whole fresh page silently
# STRIPS the <!-- BEGIN site_meta --> block (description, canonical, Open Graph,
# favicon) that scripts/site_meta.py puts in, and site_meta's own main() sys.exits on a
# missing Pillow before it can put it back. block() has no image dependency, so call it
# here and the page is never served without its identity. (2026-09-07)
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('site_meta', os.path.join(ROOT, 'scripts', 'site_meta.py'))
    site_meta = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(site_meta)
    html = html.replace('</head>', site_meta.block('players.html') + '</head>', 1)
except Exception as e:                                  # never block the page on metadata
    print(f'  WARNING: site_meta block not applied ({e})')

open(out, 'w').write(html)
print('wrote', out, f'({len(html)//1024}KB)')
print(f'  left out: {n_individual_owners} individual/family-trust owner(s), {n_excluded_prof} individual(s) in a '
      f'professional role; {len(nodes)} players shown')
