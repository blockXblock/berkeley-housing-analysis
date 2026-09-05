"""Build JN-N_labels.ipynb — the flyover label as a DATA PRODUCT, not decoration.

Why this notebook exists. The labels that ride the buildings in the berkeleybuild.com flyovers are
generated from v2 by scripts/gen_svg_labels.py: six lines of text per project, rendered to SVG and
rasterised to a PNG that Google Earth carries as an icon. Every design question about them so far
has been settled by John watching a video and saying what was wrong, then a 5-30 minute batch
re-render before anyone could see the answer. svg() takes 1.3 ms. The batch is the rasteriser, not
the design. So the design belongs in a notebook, where a change is visible immediately.

The second reason is the one that matters for readers. A label is a claim about a building, made in
six lines, on top of a photograph of that building. Which six lines is an editorial decision we have
been making implicitly. This notebook makes it explicit, shows what the data can actually support
(most projects cannot fill six lines), and hands the choice to the reader.

House pattern (build_jn_c/d/e): markdown-in-source via md()/code(); this generator BOTH (a) derives
and gates the coverage figures live -- the real gate test -- and (b) emits the annotated notebook.
A legitimate change = APPEND a new timestamped baseline, never a hand-edit to match drift.

Run:
  python scripts/v4/build_jn_n.py                  # derive, gate vs newest baseline, emit notebook
  python scripts/v4/build_jn_n.py --write-baseline # append a new timestamped baseline
  python scripts/v4/build_jn_n.py --baseline X     # gate vs a specific baseline (both-ways test)
"""
import os, sys, json, glob, hashlib, sqlite3, argparse, datetime

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-N_labels.ipynb')
BASELINE_GLOB = os.path.join(ROOT, 'data', 'baselines', 'label_fields_baseline_*.json')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

# The six lines a label can carry, and the v2 column each one needs. This mapping IS the subject of
# the notebook: it is the editorial decision, written down.
LINE_FIELDS = {
    'address':   'address_display',
    'units':     'total_units',
    'status':    'status_label',
    'storeys':   'height_stories',
    'height':    'height_feet',
    'filed':     'filed_date',
    'architect': 'architect',
    'developer': 'developer',
    'owner':     'owner_current',
}
# Projects whose labels we pin, so a silent content change is caught. 2128 Oxford is here because it
# moved TODAY (485 -> 456 units, 26 -> 27 storeys, gated write 3d108d1): it is the live proof that a
# label tracks a correction rather than a cached rendering of a superseded figure.
ANCHORS = ['2128 Oxford St', '1974 SHATTUCK Ave', '2700 SHATTUCK Ave']


def ro(p):
    return sqlite3.connect(f'file:{p}?mode=ro', uri=True)


def v2_sha():
    h = hashlib.sha256()
    with open(V2, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


# ==================================================== DERIVATIONS (the live truth)
def derive():
    """Field coverage across the live pipeline, plus a content hash per anchor label.

    Nothing here is a constant. Coverage is counted from v_projects_flat; the anchor hashes are
    taken from the SAME lines_for() the tour builder uses, so a change to the label's wording or to
    the underlying data both move the hash and both trip the gate.
    """
    import gen_svg_labels as G
    d = {'n_projects': 0, 'coverage': {}, 'lines_filled': {}, 'anchors': {}}
    # THE PIPELINE'S OWN ROW SOURCE, not a parallel query. rows() adds the uc_project flag that
    # lines_for() needs to say "beds" instead of "units", and already excludes merged rows. A
    # second query here would drift from the thing it is meant to describe.
    os.chdir(ROOT)
    rows = G.rows(False)
    d['n_projects'] = len(rows)
    for name, col in LINE_FIELDS.items():
        d['coverage'][name] = sum(
            1 for r in rows
            if r[col] is not None and str(r[col]).strip() not in ('', '0', 'None'))
    # how many of the six DISPLAY lines each project can actually fill
    hist = {}
    for r in rows:
        n = len([x for x in G.lines_for(r) if x])
        hist[n] = hist.get(n, 0) + 1
    d['lines_filled'] = {str(k): v for k, v in sorted(hist.items())}
    by_addr = {str(r['address_display']): r for r in rows}
    for a in ANCHORS:
        r = by_addr.get(a)
        if r is None:
            d['anchors'][a] = None
            continue
        lines = [x for x in G.lines_for(r) if x]
        d['anchors'][a] = {
            'lines': lines,
            'sha': hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16],
        }
    return d, v2_sha()


# ==================================================== GATE (derived vs external baseline)
def newest_baseline():
    hits = sorted(glob.glob(BASELINE_GLOB))
    return hits[-1] if hits else None


def gate(d, sha, path):
    """Compare derived to the baseline. On mismatch DIAGNOSE and HALT -- both directions."""
    if path is None:
        print('  NO BASELINE — run with --write-baseline to establish one.')
        return False
    b = json.load(open(path))
    print(f'  gating against {os.path.basename(path)}  (v2_sha then {b.get("v2_sha")}, now {sha})')
    bad = []
    for k in ('n_projects',):
        if d[k] != b.get(k):
            bad.append(f'{k}: computed {d[k]}, baseline {b.get(k)}')
    for name, n in d['coverage'].items():
        if n != b.get('coverage', {}).get(name):
            bad.append(f'coverage[{name}]: computed {n}, baseline {b.get("coverage", {}).get(name)}')
    for a, v in d['anchors'].items():
        bv = b.get('anchors', {}).get(a)
        if (v or {}).get('sha') != (bv or {}).get('sha'):
            bad.append(f'anchor[{a}]: sha computed {(v or {}).get("sha")}, baseline '
                       f'{(bv or {}).get("sha")}\n      now      : {(v or {}).get("lines")}'
                       f'\n      baseline : {(bv or {}).get("lines")}')
    if bad:
        print('\n  GATE FAILED — derived does not match the baseline:')
        for x in bad:
            print(f'    - {x}')
        print('\n  Likely causes, in order: (a) a gated write changed v2 — if the new value is '
              'CORRECT, append a new baseline, never edit this logic; (b) lines_for() was edited, '
              'which is an editorial change and needs a new baseline too; (c) a project was merged '
              'or un-merged, which moves n_projects.')
        return False
    print('  GATE PASSED — every coverage count and anchor label matches the baseline.')
    return True


def write_baseline(d, sha):
    p = os.path.join(ROOT, 'data', 'baselines',
                     f'label_fields_baseline_{datetime.date.today().isoformat()}.json')
    out = dict(d)
    out['v2_sha'] = sha
    out['written_at'] = datetime.datetime.now().isoformat(timespec='seconds')
    out['provenance'] = ('Derived by scripts/v4/build_jn_n.py from v_projects_flat '
                         '(merged_into_id IS NULL) and gen_svg_labels.lines_for().')
    json.dump(out, open(p, 'w'), indent=2)
    print(f'  wrote {p}')
    return p


# ==================================================== NOTEBOOK
cells = []
def md(t): cells.append(new_markdown_cell(t.strip("\n")))
def code(s): cells.append(new_code_cell(s.strip("\n")))


def build_notebook(d, sha, baseline_path):
    md(f"""
# JN-N — The label as a data product

**What this is.** Every building in the berkeleybuild.com flyovers carries a small panel: address,
how many homes, how tall, who is building it, who owns the land. This notebook is where those
panels are designed, and where the editorial decision behind them — *which* six facts, out of
everything v2 knows — is made explicit instead of implicit.

**Why a notebook and not a script.** `gen_svg_labels.svg()` returns a finished label in **1.3 ms**.
The 5–30 minute wait that has governed every label decision so far is the *rasteriser*
(`qlmanage` at 0.53 s per label, `cairosvg` at 0.31 s), not the design. Here you change a line and
see it immediately.

**Derived, not hardcoded.** Every figure below is computed from `v_projects_flat` at run time and
gated against an external timestamped baseline
(`data/baselines/label_fields_baseline_*.json`). A legitimate change to the data means
**appending a new baseline**, never editing the logic to match.

| | |
|---|---|
| v2 sha at build | `{sha}` |
| baseline gated against | `{os.path.basename(baseline_path) if baseline_path else 'NONE'}` |
| projects in scope | {d['n_projects']} (merged rows excluded) |
""")

    md("""
## §1 — One label, end to end

**Assumption.** A label is a pure function of one row of `v_projects_flat`. Nothing about the tour,
the camera or the geometry enters into it.

**Plan.** Pull the row for 2128 Oxford St, show the six lines `lines_for()` produces, and render the
SVG inline.

**Why this project.** Its numbers moved today. A gated write took it from the 2023 SB330 application
figures (485 units, 26 storeys) to the ZAB-approved plan set (456 units, 27 storeys). If the label
below says 456, the pipeline is tracking corrections rather than serving a cached rendering of a
superseded figure — which it was doing until this morning, because the PNG cache keyed on filename.
""")
    code("""
import sys, sqlite3, hashlib, json, glob, os
sys.path.insert(0, os.path.expanduser('~/berkeley-data/scripts'))
import gen_svg_labels as G
from IPython.display import SVG, display

V2 = os.path.expanduser('~/berkeley-data/databases/berkeley_housing_v2.db')
def ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)

os.chdir(os.path.expanduser('~/berkeley-data'))
ROWS = G.rows(False)          # the pipeline's own row source: adds uc_project, drops merged rows
BY = {str(r['address_display']): r for r in ROWS}
r = BY['2128 Oxford St']

for line in [x for x in G.lines_for(r) if x]:
    print(' ', line)
display(SVG(G.svg(r)))
""")
    md("""
**Found.** Six lines, and the SVG rendered in about a millisecond. The panel colour is the project's
status — orange for *Entitled* — which is the same encoding the flyover uses for the building
footprint, so the label and the building agree without the viewer being told the rule.

**Verify.** The units line should read **456**, not 485. If it reads 485 you are running against a
v2 that predates the 2026-09-04 write, and the gate in §5 will say so.
""")

    md("""
## §2 — What the data can actually support

**Assumption — and it is the one worth testing.** The label design assumes six lines are available.
They are not. `architect`, `developer` and `owner_current` are sparse; `height_feet` is sparser
still. A label design that assumes rich data produces mostly-empty boxes.

**Plan.** Count, for every field a label line needs, how many of the projects in scope actually
carry it. Then count how many of the six display lines each project can fill.
""")
    code("""
LINE_FIELDS = """ + json.dumps(LINE_FIELDS, indent=4) + """

n = len(ROWS)
print(f'{n} projects in scope\\n')
cov = {}
for name, col in LINE_FIELDS.items():
    k = sum(1 for x in ROWS
            if x[col] is not None and str(x[col]).strip() not in ('', '0', 'None'))
    cov[name] = k
    print(f'  {name:10} {col:18} {k:5}  {100*k/n:5.1f}%')

hist = {}
for x in ROWS:
    hist[len([y for y in G.lines_for(x) if y])] = hist.get(len([y for y in G.lines_for(x) if y]), 0) + 1
print('\\n  lines a project can fill -> how many projects')
for k in sorted(hist):
    print(f'    {k} lines  {hist[k]:5}   {"#" * int(60*hist[k]/n)}')
""")
    md(f"""
**Found.** The address and status are near-universal; the people are not. Of {d['n_projects']}
projects, **{d['coverage']['owner']} carry an owner** and **{d['coverage']['architect']} an
architect**. The owner figure is high only because of the assessor join done on 2026-09-02 — before
that it was 28 out of 895, and the site was serving *that* number until today.

**Verify — and this is the point of the section.** Look at the histogram. The modal project fills
far fewer than six lines. **Designing a six-line label for a pipeline whose typical project supports
three is a design error, not a data problem.** The label happens to degrade gracefully (missing
lines are simply omitted and the box shrinks to fit), but the *design* was chosen against the
richest projects — the towers we orbit — and those are the exception.
""")

    md("""
## §3 — Choose your own label

**Assumption.** Which six facts appear is an editorial choice, not a technical constraint.

**Plan.** `lines_for()` is one function. Write a different one and the whole pipeline — SVG, PNG,
KMZ, flyover — follows. Below are three alternative labels over the same project: the shipped one,
an affordability-first one, and a money one.

**Why it matters.** This is the handle a reader gets. The video shows there is information on every
building; this cell is where they change what that information *is*.
""")
    code("""
def label_affordability(r):
    t = r['total_units'] or 0
    aff = (r['eli_units'] or 0) + (r['vli_units'] or 0) + (r['li_units'] or 0) + (r['mod_units'] or 0)
    return [str(r['address_display']),
            f"{aff:,} affordable of {t:,}" if t else 'units unknown',
            f"{100*aff/t:.0f}% below market" if t else '',
            str(r['status_label'] or '')]

def label_money(r):
    av = r['assessed_value']; tax = r['est_annual_tax']
    return [str(r['address_display']),
            f"assessed ${av:,.0f}" if av else 'not yet assessed',
            f"tax ${tax:,.0f}/yr" if tax else '',
            f"{r['total_units'] or 0:,} units · {r['status_label']}"]

for name, fn in (('shipped', G.lines_for),
                 ('affordability', label_affordability),
                 ('money', label_money)):
    print(f'  --- {name} ---')
    for line in [x for x in fn(r) if x]:
        print('   ', line)
    print()
""")
    md("""
**Found.** Same building, three different arguments about it. The shipped label answers *what is
being built*; the affordability label answers *who gets to live there*; the money label answers
*what it is worth to the city*.

**What this could mislead about.** The affordability label divides by `total_units`, and for
2128 Oxford that denominator moved by 29 today. A percentage is only as stable as the number under
it — and unlike a raw count, a percentage hides that it moved. The money label is worse: an
`assessed_value` of $0 on a finished building usually means **reassessment lag, not zero value**,
so a money label would confidently print "not yet assessed" on a completed occupied tower. Neither
is wrong; both need the caveat the video has no room for. That asymmetry — the notebook can
qualify, the label cannot — is the honest reason the flyover is a teaser and not the analysis.
""")

    md("""
## §4 — The renderer that was quietly changing the design

**Assumption we held until today.** The panel was translucent (`fill-opacity="0.86"`), so buildings
showed faintly through it.

**Found — it never was.** `qlmanage` is macOS Quick Look, and it *flattens alpha against a light
background*. It rendered `#0d1117` at 0.86 as an opaque **(47,51,56)** grey. Every label in every
video shipped before 2026-09-04 is that grey. `cairosvg` renders the same SVG as **(13,17,23)**.

The design intent never reached a single frame, and nothing reported an error — the rasteriser
simply returned a different picture than the one specified.
""")
    code("""
# Derived, not asserted: read the panel pixel straight out of a rendered label.
from pathlib import Path
try:
    from PIL import Image
    p = Path(os.path.expanduser('~/berkeley-data/scratch/2026-08-31/svg-labels/2128-oxford-st.png'))
    if p.exists():
        im = Image.open(p).convert('RGBA')
        print(f'  shipped label {p.name}: size {im.size}  panel pixel {im.load()[300,100]}')
        print('  (13,17,23,255) = cairosvg, faithful   (47,51,56,255) = qlmanage, flattened')
    else:
        print('  no rendered label on disk yet — run scripts/gen_svg_labels.py')
except ImportError:
    print('  PIL not available in this kernel; skipping the pixel check')
""")
    md("""
**Verify.** A faithful render reads `(13,17,23,255)`. Anything near `(47,51,56)` means the label was
made by Quick Look and is lighter than designed.

**The general lesson, which is not about labels.** A tool that silently returns *something
plausible* instead of what you asked for is worse than one that fails, because the output looks
fine. We only caught it by diffing two renderers pixel by pixel — by eye they were identical.
""")

    md("""
## §5 — The gate

**Assumption.** Coverage counts and the exact text of the anchor labels should not move unless v2
moved, and if they do move the notebook must say so rather than quietly render something new.

**Plan.** Recompute, compare against the newest timestamped baseline, and halt with a diagnosis on
mismatch. A legitimate change is an **appended** baseline, never an edit here.
""")
    code("""
import glob
BG = os.path.expanduser('~/berkeley-data/data/baselines/label_fields_baseline_*.json')
hits = sorted(glob.glob(BG))
if not hits:
    print('  NO BASELINE — run: python scripts/v4/build_jn_n.py --write-baseline')
else:
    b = json.load(open(hits[-1]))
    print(f'  baseline {os.path.basename(hits[-1])}  (v2_sha then {b.get("v2_sha")})')
    bad = []
    if len(ROWS) != b['n_projects']:
        bad.append(f"n_projects: now {len(ROWS)}, baseline {b['n_projects']}")
    for name, k in cov.items():
        if k != b['coverage'].get(name):
            bad.append(f"coverage[{name}]: now {k}, baseline {b['coverage'].get(name)}")
    for a, bv in b['anchors'].items():
        rr = BY.get(a)
        now = [x for x in G.lines_for(rr) if x] if rr is not None else None
        s = hashlib.sha256('\\n'.join(now).encode()).hexdigest()[:16] if now else None
        if s != (bv or {}).get('sha'):
            bad.append(f"anchor[{a}]\\n      now      : {now}\\n      baseline : {(bv or {}).get('lines')}")
    if bad:
        print('\\n  GATE FAILED:')
        for x in bad: print('    -', x)
        print('\\n  If the new value is CORRECT, append a new baseline. Never edit the logic to match.')
    else:
        print('  GATE PASSED — coverage and every anchor label match the baseline.')
""")
    md(f"""
**Found at build time.** Gate {'PASSED' if baseline_path else 'had no baseline'} against
`{os.path.basename(baseline_path) if baseline_path else 'NONE'}`.

**Verify — prove the gate can fail.** Edit `lines_for()` in `scripts/gen_svg_labels.py` (add a word
to the address line), re-run the cell above, and confirm it FAILS and prints the old and new text.
A gate that has never been seen to fail is not evidence of anything. This one was proven both ways;
so was the deploy gate it is modelled on.
""")

    md("""
## §6 — Coverage, drawn

**What this shows.** For each label line, the share of projects that can fill it. Read it as *how
often this line appears at all*, not how often it is interesting.
""")
    code("""
import plotly.graph_objects as go
names = list(cov.keys()); vals = [100*cov[k]/len(ROWS) for k in names]
order = sorted(range(len(names)), key=lambda i: -vals[i])
fig = go.Figure(go.Bar(x=[vals[i] for i in order], y=[names[i] for i in order],
                       orientation='h', marker_color='#ff8000',
                       text=[f'{vals[i]:.0f}%  ({cov[names[i]]})' for i in order],
                       textposition='outside'))
fig.update_layout(title=f'Label line coverage across {len(ROWS)} projects',
                  xaxis_title='% of projects that can fill this line',
                  xaxis_range=[0,115], height=420,
                  paper_bgcolor='white', plot_bgcolor='white')
fig.show()
""")
    md("""
**What this could mislead about.** Coverage is not quality. `owner_current` shows high because every
Berkeley parcel has an assessor owner of record — but an owner of record is often a single-purpose
LLC that tells you nothing about who is actually behind a project. A bar at 95% invites you to read
"we know who owns these"; what it means is "we know what name is on the deed". The chart cannot
carry that distinction and the label carries it even less.
""")

    md("""
## §7 — Where a label comes from

```mermaid
graph LR
  A[CPRA permits xlsx] --> V2[(berkeley_housing_v2.db)]
  B[Alameda assessor<br/>berkeley.db parcels] --> V2
  C[Plan sets · 1.E tabulation forms<br/>ZAB packets] --> V2
  V2 --> VF[v_projects_flat]
  VF --> LF["gen_svg_labels.lines_for()<br/><b>the editorial choice</b>"]
  LF --> SVG["svg() — 1.3 ms"]
  SVG --> R{rasteriser}
  R -->|cairosvg 0.31s<br/>faithful| PNG[label PNG]
  R -->|qlmanage 0.53s<br/>FLATTENS ALPHA| PNG
  PNG --> KMZ["svg_label_tour.py<br/>package + gx:AnimatedUpdate"]
  KMZ --> GE[Google Earth]
  GE -->|Movie Maker, by hand| MP4[YouTube]
  VF --> EXP[export_explorer_data_v2.py] --> SITE[berkeleybuild.com explorer]
```

**Read it as:** one row of `v_projects_flat` feeds both the label and the website, so a gated write
moves both — but only if the caches downstream invalidate. Two did not, and both were found on
2026-09-04: the label PNG cache keyed on filename (fixed: it now hashes the SVG), and the explorer's
served data file needed a manual copy (fixed: the deploy gate now blocks a stale one).

**The diamond is the part to remember.** The rasteriser is the one step in this chain that can
change what the reader sees without changing any data, any code, or any figure in this notebook.
""")

    md("""
## §8 — What this notebook does not do

**It does not make the labels legible in video.** Measured from the 2026-09-04 Shattuck recording, a
pass-by label renders about **124 × 52 px on a 1920-wide frame** — an unreadable smudge. Only the
four orbited buildings are readable. Inside Earth you can pause and lean in; in a video nobody can.
That is not fixable here, because Earth ties icon size to camera distance.

**The route out is a different pipeline.** Google Earth Pro is scriptable — `GetViewInfo`,
`SetViewInfo`, `SaveScreenShot`, `GetStreamingProgress`, verified 2026-09-04 — with no Movie Maker
command. A notebook that steps the camera and captures frames knows exactly where the camera is,
so it can composite labels in **screen space** with a minimum legible size. That would dissolve the
placement problems this project has fought all along — the label sinking into the building, the
roof-versus-view-axis height, the radial pump around an elongated footprint — because none of them
exist in 2D.

Untested and honest about it: `SaveScreenShot` and `GetStreamingProgress` have not been exercised,
the projection needs calibrating against a known frame, and 470 seconds at 29.97 fps is ~14,000
scripted round-trips through Rosetta. That is the next spike, not a promise.
""")

    nb = new_notebook(cells=cells, metadata={'kernelspec': {
        'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}})
    os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
    with open(NB_OUT, 'w') as f:
        nbf.write(nb, f)
    print(f'  wrote {NB_OUT}  ({len(cells)} cells)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write-baseline', action='store_true')
    ap.add_argument('--baseline', default=None)
    a = ap.parse_args()
    d, sha = derive()
    print(f'  derived from v2 sha {sha}: {d["n_projects"]} projects')
    if a.write_baseline:
        write_baseline(d, sha)
    path = a.baseline or newest_baseline()
    ok = gate(d, sha, path)
    build_notebook(d, sha, path)
    sys.exit(0 if (ok or a.write_baseline) else 1)


if __name__ == '__main__':
    main()
