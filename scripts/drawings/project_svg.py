#!/usr/bin/env python3
"""project_svg.py — one SVG per housing project: its journey from application to move-in, every element a link.

What a drawing shows (all read from live v4, never typed):
  * header: name, address, status (in the site's stage colors), units/beds, buildings, approval pathway;
  * the PROJECT LANE: the planning record's milestones (filed, application complete, entitled) and the first
    building permit, with the time between them colored by stage, ending at the last completion or at today;
  * one BUILDING LANE per building: its first building permit to its final (certificate of occupancy), with units;
  * funding: each award on the project's funding ledger, with funder, program and amount.
Every milestone and bar links to the City's own record page (Accela CapDetail, from the date-range sweep files), and
carries a <title> tooltip with the record number and date. Nothing is drawn for a date v4 does not have: a missing
milestone is a gap, labeled, never interpolated.

Run:  .venv/bin/python scripts/drawings/project_svg.py --keys ZP2018-0137 UP2010-0078 ... [--out scratch/2026-10-01_svg]
"""
import argparse, datetime as dt, glob, hashlib, html, json, os, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V4 = os.path.join(ROOT, 'databases', 'berkeley_housing_v4.db')
ACCELA = 'https://aca-prod.accela.com'
TODAY = dt.date.today()

# the site's stage colors (docs/svg/stage_legend.svg, scripts/site_meta.py STAGES)
STAGE = {'pre_application': ('#7a7a7a', 'pre-application'), 'in_review': ('#b8860b', 'under review'),
         'entitled': ('#ff8000', 'approved, no building permit yet'), 'permitted': ('#00b8cc', 'permitted, not yet started'),
         'under_construction': ('#2962ff', 'under construction'), 'completed': ('#00a844', 'completed and occupiable'),
         'withdrawn': ('#a0aec0', 'withdrawn'), 'denied': ('#a0aec0', 'denied'), 'void': ('#a0aec0', 'void'),
         'stale': ('#a0aec0', 'no recent activity')}
INK, MUTED, LINE, BG = '#1a365d', '#4a5568', '#e2e8f0', '#ffffff'
PATHWAY = {'density_bonus': 'state density bonus', 'sb35_streamlined': 'SB 35 streamlined', 'ab2011': 'AB 2011',
           'sb423_streamlined': 'SB 423 streamlined', 'ministerial': 'ministerial'}

esc = lambda s: html.escape(str(s), quote=True)


def capdetail_index():
    """record number -> CapDetail URL, from every date-range sweep file (Building and Planning)."""
    idx = {}
    for f in glob.glob(os.path.join(ROOT, 'data', 'raw', 'accela', 'date_range', '*.jsonl')):
        for line in open(f):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            k = r.get('Permit Number') or r.get('Record Number')
            h = r.get('capdetail_href')
            if k and h and k not in idx:
                idx[k] = ACCELA + h
    return idx


def project(con, key):
    con.row_factory = sqlite3.Row
    p = dict(con.execute('SELECT * FROM v_projects WHERE project_key = ?', (key,)).fetchone())
    tl = [dict(r) for r in con.execute('SELECT * FROM v_project_timeline WHERE project_key = ? ORDER BY event_date', (key,))]
    bld = [dict(r) for r in con.execute('''
        SELECT ps.structure_id,
          (SELECT SUM(unit_count) FROM units u WHERE u.structure_id = ps.structure_id) AS units,
          (SELECT MIN(e.event_date) FROM structure_events se JOIN events e ON e.event_id = se.event_id
             WHERE se.structure_id = ps.structure_id AND e.event_type_code = 'permit_issued'
               AND se.role_in_structure IN ('master', 'phase')) AS first_bp,
          (SELECT MAX(e.event_date) FROM structure_events se JOIN events e ON e.event_id = se.event_id
             WHERE se.structure_id = ps.structure_id AND e.event_type_code = 'permit_finaled'
               AND se.role_in_structure = 'master') AS finaled,
          (SELECT e.source_record_key FROM structure_events se JOIN events e ON e.event_id = se.event_id
             WHERE se.structure_id = ps.structure_id AND se.role_in_structure = 'master' LIMIT 1) AS master,
          (SELECT e.raw_address FROM structure_events se JOIN events e ON e.event_id = se.event_id
             WHERE se.structure_id = ps.structure_id AND se.role_in_structure = 'master' LIMIT 1) AS address
        FROM project_structures ps JOIN v_projects p ON p.project_id = ps.project_id
        WHERE p.project_key = ? ORDER BY first_bp, structure_id''', (key,))]
    return p, tl, bld


def d(s):
    return dt.date.fromisoformat(s[:10]) if s else None


def svg(p, tl, bld, links, sha):
    W, L, R = 960, 150, 40                      # width, left gutter (lane labels), right margin
    anchor = next((r['record_key'] for r in tl if r['role'] == 'anchor'), p['project_key'])
    ms = [('filed', 'Application filed', d(p['filed_date'])), ('accepted', 'Application complete', d(p['accepted_date'])),
          ('entitled', 'Approved' + (f" ({p['entitled_by']})" if p.get('entitled_by') else ''), d(p['entitled_date'])),
          ('bp', 'First building permit', d(p['bp_issued_date']))]
    done = [d(b['finaled']) for b in bld if b['finaled']]
    dates = [x for _, _, x in ms if x] + [x for b in bld for x in (d(b['first_bp']), d(b['finaled'])) if x]
    y0 = min(dates).year if dates else TODAY.year - 1
    end = TODAY if p['status'] not in ('completed',) or not done else max(done)
    y1 = max(end.year + 1, max(dates).year + 1 if dates else TODAY.year)
    span = (dt.date(y1, 1, 1) - dt.date(y0, 1, 1)).days
    X = lambda day: L + (W - L - R) * (day - dt.date(y0, 1, 1)).days / span
    link = lambda rec: links.get(rec)
    out = []
    a = lambda rec, body, tip: (f'<a href="{esc(link(rec))}" target="_blank" rel="noopener"><title>{esc(tip)}</title>{body}</a>'
                                if link(rec) else f'<g><title>{esc(tip)} (no City link on file)</title>{body}</g>')
    # ---- header
    col, stage_label = STAGE.get(p['status'], ('#a0aec0', p['status']))
    units = p['units_built_or_permitted'] or p['proposed_units'] or 0
    facts = [f"{units:,} units" if units else 'no units recorded',
             f"{len(bld)} building{'s' if len(bld) != 1 else ''}" if bld else 'no building permit yet']
    if p.get('beds'):
        facts.append(f"{p['beds']:,} beds")
    pw = [PATHWAY.get(x, x.replace('_', ' ')) for x in json.loads(p['pathways'] or '[]')]
    if pw:
        facts.append(', '.join(pw))
    title = p['name'] if p['name'] and p['name'] != p['address_display'] else p['address_display']
    out.append(f'<text x="24" y="40" font-size="24" font-weight="700" fill="{INK}">{esc(title)}</text>')
    if title != p['address_display']:
        out.append(f'<text x="24" y="62" font-size="14" fill="{MUTED}">{esc(p["address_display"])}</text>')
    out.append(f'<rect x="{W - R - 230}" y="20" width="230" height="28" rx="14" fill="{col}"/>'
               f'<text x="{W - R - 115}" y="39" font-size="13" font-weight="600" fill="#fff" text-anchor="middle">{esc(stage_label)}</text>')
    out.append(f'<text x="24" y="86" font-size="14" fill="{INK}">{esc(" · ".join(facts))}</text>')
    # ---- axis
    top = 112
    nb = max(len(bld), 1)
    lane_h = 52
    bottom = top + 40 + 30 + lane_h * (1 + nb)
    for y in range(y0, y1 + 1):
        x = X(dt.date(y, 1, 1))
        out.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="{LINE}"/>')
        if y < y1:
            out.append(f'<text x="{X(dt.date(y, 7, 1)):.1f}" y="{top + 14}" font-size="12" fill="{MUTED}" text-anchor="middle">{y}</text>')
    tx = X(TODAY)
    if TODAY.year < y1:
        out.append(f'<line x1="{tx:.1f}" y1="{top + 20}" x2="{tx:.1f}" y2="{bottom}" stroke="#e53e3e" stroke-dasharray="3 3"/>'
                   f'<text x="{tx:.1f}" y="{bottom + 14}" font-size="11" fill="#e53e3e" text-anchor="middle">today</text>')
    # ---- project lane: segments between the milestones v4 has, colored by the stage each one starts
    ly = top + 40
    lane0 = 30                                   # extra room under the planning lane for its labels
    out.append(f'<text x="24" y="{ly + 4}" font-size="13" font-weight="600" fill="{INK}">Planning</text>'
               f'<text x="24" y="{ly + 20}" font-size="11" fill="{MUTED}">{esc(anchor)}</text>')
    seg_stage = {'filed': 'in_review', 'accepted': 'in_review', 'entitled': 'entitled', 'bp': 'under_construction'}
    have = [(k, lab, x) for k, lab, x in ms if x]
    stop = max(done) if done and p['status'] == 'completed' else TODAY
    for i, (k, lab, x) in enumerate(have):
        nxt = have[i + 1][2] if i + 1 < len(have) else stop
        if nxt and nxt > x:
            c = STAGE[seg_stage[k]][0]
            dash = '' if i + 1 < len(have) or p['status'] == 'completed' else ' stroke-dasharray="6 4"'
            out.append(f'<line x1="{X(x):.1f}" y1="{ly}" x2="{X(nxt):.1f}" y2="{ly}" stroke="{c}" stroke-width="10"{dash}>'
                       f'<title>{esc(STAGE[seg_stage[k]][1])}: {x} to {nxt} ({(nxt - x).days:,} days)</title></line>')
    missing = [lab for k, lab, x in ms if not x]
    for k, lab, x in have:
        rec = anchor if k != 'bp' else (bld[0]['master'] if bld else anchor)
        out.append(a(rec, f'<circle cx="{X(x):.1f}" cy="{ly}" r="7" fill="#fff" stroke="{INK}" stroke-width="2.5"/>',
                     f'{lab}: {x} ({rec})'))
    # milestone labels below the lane: each goes in the first row where it overlaps no earlier label
    rows = []
    for k, lab, x in have:
        txt = f'{lab.split(" (")[0]}, {x:%b %Y}'
        w = 5.6 * len(txt)
        cx = min(max(X(x), L - 20 + w / 2), W - R - w / 2)     # never run into the lane-label column
        r = next((i for i, row in enumerate(rows) if all(cx - w / 2 > b + 6 or cx + w / 2 < a_ - 6 for a_, b in row)), len(rows))
        rows.append([]) if r == len(rows) else None
        rows[r].append((cx - w / 2, cx + w / 2))
        out.append(f'<text x="{cx:.1f}" y="{ly + 22 + 12 * r}" font-size="10.5" fill="{MUTED}" text-anchor="middle">{esc(txt)}</text>')
    if missing:
        out.append(f'<text x="{W - R}" y="{ly - 12}" font-size="10.5" fill="#c05621" text-anchor="end">'
                   f'no date in the records: {esc(", ".join(m.lower() for m in missing))}</text>')
    # ---- building lanes
    for i, b in enumerate(bld):
        y = ly + lane0 + lane_h * (i + 1)
        s, f = d(b['first_bp']), d(b['finaled'])
        out.append(f'<text x="24" y="{y + 4}" font-size="13" font-weight="600" fill="{INK}">{esc((b["address"] or "Building").title()[:20])}</text>'
                   f'<text x="24" y="{y + 20}" font-size="11" fill="{MUTED}">{esc(b["master"] or "")} · {b["units"] or 0} units</text>')
        if s:
            e = f or TODAY
            body = (f'<line x1="{X(s):.1f}" y1="{y}" x2="{X(e):.1f}" y2="{y}" stroke="{STAGE["under_construction"][0]}" stroke-width="10"'
                    f'{"" if f else " stroke-dasharray=\"6 4\""}/>')
            out.append(a(b['master'], body, f"{b['master']}: building permit {s}" + (f", final {f}" if f else ', not yet finaled')))
        else:
            out.append(f'<text x="{L}" y="{y + 4}" font-size="11" fill="#c05621">no building-permit issue date in the records</text>')
        if f:
            out.append(a(b['master'], f'<circle cx="{X(f):.1f}" cy="{y}" r="8" fill="{STAGE["completed"][0]}" stroke="#fff" stroke-width="2"/>',
                         f"{b['master']}: final inspection {f}, {b['units']} units"))
            out.append(f'<text x="{X(f):.1f}" y="{y - 11}" font-size="11" fill="{INK}" text-anchor="end">'
                       f'{b["units"] or 0} homes, final {f:%b %Y}</text>')
    if not bld:
        out.append(f'<text x="{L}" y="{ly + lane_h + 12}" font-size="12" fill="{MUTED}">No building permit issued for this project in the records.</text>')
    # ---- funding
    fy = bottom + 34
    fund = json.loads(p['funding'] or '[]')
    if fund:
        tot = sum(float(f.get('amount_usd') or 0) for f in fund)
        out.append(f'<text x="24" y="{fy}" font-size="13" font-weight="600" fill="{INK}">Public funding on record: ${tot:,.0f}</text>')
        for k, f in enumerate(fund[:6]):
            amt = f"${float(f['amount_usd']):,.0f}" if f.get('amount_usd') else 'amount not stated'
            parts = [f.get('funder'), f.get('program'), f.get('instrument'), amt, f.get('action_date')]
            out.append(f'<text x="24" y="{fy + 18 * (k + 1)}" font-size="11.5" fill="{MUTED}">'
                       f'{esc(" · ".join(str(x) for x in parts if x))}</text>')
        if len(fund) > 6:
            out.append(f'<text x="24" y="{fy + 18 * 7}" font-size="11.5" fill="{MUTED}">and {len(fund) - 6} more</text>')
        fy += 18 * (min(len(fund), 6) + 1 + (len(fund) > 6))
    H = fy + 40
    out.append(f'<text x="24" y="{H - 16}" font-size="10.5" fill="{MUTED}">BerkeleyBuild · from the City of Berkeley\'s permit '
               f'and planning records (v4 {sha}) · drawn {TODAY} · click a milestone or bar to open the City\'s record</text>')
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" role="img" '
            f'aria-label="{esc(title)}: {esc(stage_label)}">'
            f'<title>{esc(title)}: {esc(stage_label)}</title><rect width="{W}" height="{H}" fill="{BG}"/>')
    return head + ''.join(x for x in out if x) + '</svg>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keys', nargs='+', required=True)
    ap.add_argument('--out', default=os.path.join(ROOT, 'scratch', 'svg'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    con = sqlite3.connect(f'file:{V4}?mode=ro', uri=True)
    sha = hashlib.sha256(open(V4, 'rb').read()).hexdigest()[:8]
    links = capdetail_index()
    made = []
    for k in a.keys:
        p, tl, bld = project(con, k)
        open(os.path.join(a.out, f'{k}.svg'), 'w').write(svg(p, tl, bld, links, sha))
        recs = {r['record_key'] for r in tl if r['role'] in ('anchor', 'master')}
        made.append((k, p['name'] or p['address_display'], len(bld), sum(r in links for r in recs), len(recs)))
    page = ''.join(f'<h2 style="font:600 15px -apple-system,sans-serif;color:#4a5568;margin:28px 0 6px">{esc(k)} — '
                   f'{esc(n)} · {nb} building(s) · {lk}/{nr} records linked</h2><img src="{esc(k)}.svg" '
                   f'style="max-width:100%;border:1px solid #e2e8f0">' for k, n, nb, lk, nr in made)
    open(os.path.join(a.out, 'index.html'), 'w').write(
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Project drawings test</title><body style="margin:24px;background:#f7fafc">'
        '<p style="font:14px -apple-system,sans-serif;color:#4a5568">Images here do not follow links; open a single '
        'SVG file to click through to the City record.</p>' + page)
    for m in made:
        print(*m)


if __name__ == '__main__':
    main()
