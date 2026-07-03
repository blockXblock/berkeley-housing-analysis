"""Build JN-G_revision_watcher.ipynb — the oracle revision watcher (the audit's standing sentry).

House pattern: markdown-in-source; the notebook IMPORTS scripts/v4/oracle_watch.py (never re-types
the detectors); watch items are CALIBRATION (corrections/v4/watch_items.json). Each run: pull the
live state filing → dated append-only snapshot → diff vs the prior snapshot → run the five
city-error detectors (anchor-validated) → evaluate watch items → append the run to the watch log.
ORACLE DISCIPLINE THROUGHOUT: findings trigger adjudication, never adoption.

Run:  python scripts/v4/build_jn_g.py     # emits the notebook (no network at build time)
"""
import os

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-G_revision_watcher.ipynb')

cells = []
def md(t): cells.append(new_markdown_cell(t.strip('\n')))
def code(s): cells.append(new_code_cell(s.strip('\n')))

md(r"""
# JN-G — The Revision Watcher

**What this is.** The reconciliation (JN-E, the Audit page) compares our permit-derived record against
the city's filing — but the city's filing MOVES: rows appear (the missing 2435-San-Pablo certificate,
one day), get revised (the CY2025 double-submission cleanup), or get re-credited (the five error
classes). This notebook is the standing sentry: **each run snapshots the live state filing, diffs it
against the last snapshot, runs the five mechanical error-detectors, and checks the calibrated watch
items.** It converts "the city changed its numbers" from something we discover months later into
something dated and logged the week it happens.

**Oracle discipline (the invariant):** everything here COMPARES. A fired detector or watch item
triggers ADJUDICATION (a human, the ledger, a baseline append) — never automatic adoption. The
snapshots are evidence of what the city said WHEN; they never flow into a derived count.

**Provenance of the detectors:** each encodes a city-error class discovered and receipted in the
2026-07-03 no-candidate batch (`docs/audit/2026-07-03_no_candidate_batch.md`), and each is
anchor-validated below against the documented instance it must find.
""")

md(r"""
## §1 — Acquire: live pull → dated append-only snapshot
Pulls Berkeley's `table_a2` from the state's live endpoint. Offline (or endpoint-down) runs fall
back to the newest snapshot with a loud notice — a watcher that silently reuses stale data is worse
than one that says so. Snapshots are APPEND-ONLY (a same-day upstream change refuses to overwrite).
""")
code(r"""
import os, sys, json
from datetime import date
sys.path.insert(0, os.path.join(os.path.expanduser('~'), 'berkeley-data', 'scripts', 'v4'))
import oracle_watch as W
import pandas as pd
today = date.today().isoformat()
try:
    live = W.pull_live_a2()
    snap_path = W.snapshot(live, as_of=today)
    print(f'LIVE pull OK: {len(live):,} Berkeley rows -> {os.path.relpath(snap_path, os.path.expanduser("~/berkeley-data"))}')
    LIVE_MODE = True
except Exception as e:
    prior = W.prior_snapshot()
    assert prior, f'offline AND no snapshot exists — cannot watch: {e}'
    live = pd.read_csv(prior, low_memory=False)
    snap_path = prior
    LIVE_MODE = False
    print(f'*** OFFLINE ({str(e)[:60]}) — falling back to newest snapshot {os.path.basename(prior)}; '
          f'diff + detectors run on STALE data ***')
""")

md(r"""
## §2 — The revision diff (what changed since last watch)
Row-level diff on `(YEAR, APN, address, tracking-id)` keys with CO totals: rows ADDED (a new filing —
e.g. a late certificate), REMOVED (a cleanup — e.g. the double-submission dedup), or CHANGED (a
revised count). **Each is a dated finding about the city's record**, the raw material of the Audit
page's findings log. First-ever run has no prior snapshot and says so.
""")
code(r"""
prior = W.prior_snapshot(before=today)
if prior:
    old = pd.read_csv(prior, low_memory=False)
    d = W.diff_snapshots(old, live)
    print(f'vs {os.path.basename(prior)}:  ADDED {len(d["added"])}  REMOVED {len(d["removed"])}  CHANGED {len(d["changed"])}')
    for name in ('added','removed'):
        for _, r in W._with_co(d[name]).head(8).iterrows() if len(d[name]) else []:
            print(f'  {name.upper():7} {r.YEAR} {str(r.APN)[:14]:14} {str(r.STREET_ADDRESS)[:28]:28} CO={int(r.co_units)}')
    for _, r in d['changed'].head(8).iterrows() if len(d['changed']) else []:
        print(f'  CHANGED {r._key[:60]}  CO {int(r.old_co)} -> {int(r.new_co)}')
else:
    d = None
    print('first run — no prior snapshot; the diff begins next run')
""")

md(r"""
## §3 — The five error-detectors (anchor-validated)
Mechanical tells, each born from a receipted finding: **(1) duplicate full rows** (the CY2025
double-submission class); **(2) cross-year re-credit** (same permit's units CO'd in two years —
B2022-02049); **(3) a Planning approval credited as a CO** (ZP2019-0022); **(4) "CO" dated at the
permit's ISSUANCE** (B2019-03765); **(5) a utility/meter permit re-crediting the units it serves**
(B2024-04912). The anchor asserts guarantee the detectors still catch their documented instances —
a watcher whose detectors silently rot is a false comfort. **A hit = an adjudication queue entry,
not an auto-correction.**
""")
code(r"""
res = W.run_all_detectors(live)
for name, df_ in res.items():
    ids = sorted(set(df_.JURS_TRACKING_ID.astype(str)))[:8] if len(df_) and 'JURS_TRACKING_ID' in df_ else []
    print(f'{name:20} {len(df_):>3} rows  {ids}')
# anchor validation (on any dataset containing the documented years)
years = set(live.YEAR.astype(str))
if {'2020','2021','2023','2024','2025'} <= years:
    hits = lambda k: set(res[k].JURS_TRACKING_ID.astype(str)) if len(res[k]) else set()
    assert 'B2022-02049' in hits('cross_cy_recredit'), 'ANCHOR MISS: cross-CY (B2022-02049)'
    assert 'ZP2019-0022' in hits('approval_as_co'), 'ANCHOR MISS: approval-as-CO (ZP2019-0022)'
    assert 'B2019-03765' in hits('co_at_issuance'), 'ANCHOR MISS: CO-at-issuance (B2019-03765)'
    assert 'B2024-04912' in hits('meter_recredit'), 'ANCHOR MISS: meter re-credit (B2024-04912)'
    print('anchor validation: all documented instances found')
""")

md(r"""
## §4 — Watch items (the calibrated expectations)
`corrections/v4/watch_items.json` — upstream changes we EXPECT, each with what its appearance MEANS.
The first two: the 2435-San-Pablo certificate the city omitted from CY2025 (its arrival converges the
adjudicated totals by ~41), and the Den's CKAN row (a completeness repair). **A fired item is moved
to `resolved` with provenance after adjudication — calibration, never code.**
""")
code(r"""
watch = W.check_watch_items(live)
for it, fired, n in watch:
    print(f'{"🔔 FIRED" if fired else "  quiet"}  {it["id"]:28} ({n} matching rows)')
    if fired:
        print(f'         expect: {it["expect"][:90]}')
        print(f'         meaning: {it["meaning"][:90]}')
""")

md(r"""
## §5 — The watch log (append-only run record)
Every run appends one row: date, mode, row count, diff sizes, detector totals, fired watch items.
The log IS the "we check weekly" claim made auditable.
""")
code(r"""
import csv
LOG = os.path.join(os.path.expanduser('~'), 'berkeley-data', 'data', 'audit', 'revision_watch_log.csv')
row = dict(run_date=today, mode='live' if LIVE_MODE else 'offline-stale', rows=len(live),
           added=len(d['added']) if d else '', removed=len(d['removed']) if d else '',
           changed=len(d['changed']) if d else '',
           detector_hits=sum(len(v) for v in res.values()),
           fired='|'.join(it['id'] for it, f, _ in watch if f) or 'none')
exists = os.path.exists(LOG)
with open(LOG, 'a', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(row.keys()))
    if not exists: w.writeheader()
    w.writerow(row)
print('logged:', row)
""")

md(r"""
## Visualization — detector hits (derived from this run)
📝 **What it shows:** rows flagged per detector in the CURRENT filing. Derived from `res`, never typed.
""")
code(r"""
import plotly.graph_objects as go
names, counts = list(res.keys()), [len(v) for v in res.values()]
fig = go.Figure(go.Bar(x=names, y=counts, text=counts, textposition='outside'))
fig.update_layout(title=f'JN-G detector hits — {today} ({ "live" if LIVE_MODE else "STALE-OFFLINE"} data, {len(live):,} rows)',
                  yaxis_title='flagged rows', height=380)
fig.show()
""")
md(r"""
**⚠ mislead-guards.** (1) A flagged row is a SUSPECT, not a verdict — several documented hits are
already adjudicated and inside the reconciliation's named divergences; the queue-worthy set is
flags MINUS the already-adjudicated (cross-reference `docs/audit/2026-07-03_no_candidate_batch.md`).
(2) Zero hits on `duplicate_rows` reflects the post-cleanup filing — the class is historical, not
impossible. (3) Counts are ROWS, not units.
""")

md(r"""
## Assumptions ledger
| assumption | what BREAKS if violated |
|---|---|
| oracle-not-source | a fired finding auto-applied would make the count circular — everything here queues adjudication |
| snapshots append-only | overwriting a snapshot destroys the evidence of what the city said when — the watcher's whole point |
| anchors stay found | a detector that stops catching its documented instance has rotted; the assert makes rot loud |
| offline is loud | silently watching stale data manufactures false "no changes this week" findings |
""")

nb = new_notebook(cells=cells, metadata={'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}})
os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
with open(NB_OUT, 'w') as f:
    nbf.write(nb, f)
print('wrote', NB_OUT, len(cells), 'cells')
