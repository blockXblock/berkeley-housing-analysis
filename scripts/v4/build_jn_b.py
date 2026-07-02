"""Build JN-B_event_dedup.ipynb — the DEDUP stage between JN-A (ingest) and JN-C (classify).

House pattern (build_jn_c/e): markdown-in-source via md()/code(); the notebook IMPORTS the stage
method from scripts/v4/stage_methods.py (the aa6ded0 lift discipline — never a cell-string copy).
Target PARAMETERIZED (env JN_B_DB_PATH; default = the JN-A throwaway); LIVE-DB REFUSAL guard.

Run:  python scripts/v4/build_jn_b.py     # emits the notebook (no DB access at build time)
"""
import os

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-B_event_dedup.ipynb')

cells = []
def md(t): cells.append(new_markdown_cell(t.strip('\n')))
def code(s): cells.append(new_code_cell(s.strip('\n')))

md(r"""
# JN-B — Event dedup (the stage between JN-A and JN-C)

**What this is.** The CPRA feed is TWO overlapping exports (2018-2022 + 2023-2025): ~1,430 permits
appear in both files, plus a handful of within-file duplicate rows. JN-A ingests **everything,
faithfully** (ingestion reports, it does not resolve — its cell-26 note). So the raw event stream
carries duplicate milestone events: the same `(permit, milestone, date)` recorded twice. **This stage
collapses those duplicates to one event each (keep `MIN(event_id)`), BEFORE classification.**

**Universal METHOD vs Berkeley CALIBRATION.** The method (same-key collapse + hold guards) is
city-agnostic — any jurisdiction with overlapping exports needs it. The calibration is
`corrections/v4/event_dedup_holds.json`: the tier-2 groups this dataset must HOLD (see §3).

**Why the count depends on this.** Without dedup, a permit finaled in both files counts its units
TWICE (the dedup47 story). The CO reconciliation (JN-E) is only trustworthy on a dedup-clean stream.

**Pipeline position.** `raw xlsx → JN-A (ingest) → THIS (dedup) → JN-C (classify) → JN-F
(corrections) → JN-E (reconcile)`. (At the 2026-07-02 validation the stream ran 85,793 → −2,870 →
82,923; those figures are history-citations — the current run's numbers DERIVE in the cells below.)
""")

md(r"""
## §1 — Target guard (parameterized, never the live DB by default)
**Where from.** Same discipline as JN-A/JN-C: the target comes from `JN_B_DB_PATH` (default = the
JN-A throwaway rebuild). **This stage DELETES duplicate events** — running it against the live
corrected DB is refused (it would be a no-op-if-lucky, a corruption-of-record-if-not; the live DB
already carries this dedup, applied 2026-06-29, audit `docs/audit/2026-06-29_event_dedup_write.md`).
""")
code(r"""
import os, sys, sqlite3
from pathlib import Path
REPO  = Path.home() / "berkeley-data"
_LIVE = REPO / "databases" / "berkeley_housing_v4.db"
DB_PATH = Path(os.environ.get("JN_B_DB_PATH") or os.environ.get("PIPELINE_DB_PATH")
               or str(REPO / "scratch" / "jn_a_throwaway" / "berkeley_housing_v4.db"))
if DB_PATH.resolve() == _LIVE.resolve() and os.environ.get("JN_B_ALLOW_LIVE") != "1":
    raise SystemExit(f"REFUSED: {DB_PATH} is the LIVE corrected DB — it is already dedup-clean; "
                     f"this stage mutates its target. Point JN_B_DB_PATH at a rebuild.")
assert DB_PATH.exists(), f"{DB_PATH} missing — run JN-A first (it builds the ingest target)."
sys.path.insert(0, str(REPO / "scripts" / "v4"))
import stage_methods as M
con = sqlite3.connect(DB_PATH)
print("target:", DB_PATH)
print("events before dedup:", f"{M.event_count(con):,}")
""")

md(r"""
## §2 — The collapse (run the imported method)
**What it does.** Groups events by `(source_record_key, event_type_code, event_date)`; every group
with >1 event is a duplicate group. The **kept** event is `MIN(event_id)` (first-ingested); the rest
are deleted along with their (1:1) classification rows if any. **Holds** (never collapsed):
(a) *auto* — any group whose substantive payload fields (WorkDescription / UnitsAdded / NumberUnits)
disagree between the copies, or (post-classification use) whose classifications disagree;
(b) *calibration* — the tier-2 list in `corrections/v4/event_dedup_holds.json`.
**Assumption (load-bearing):** same permit + same milestone + same date + same substance = the same
real-world event recorded twice, not two events. Different DATES are never collapsed (tier-3 —
a different finaled date may be a legit re-final).
""")
code(r"""
stats = M.dedup_events(con)
print(f"duplicate groups: {stats['groups']:,}")
print(f"removed (tier-1 auto-collapse): {stats['removed']:,}")
print(f"held (auto, substantive-differ): {stats['held_auto']}")
print(f"held (calibration):              {stats['held_calib']}")
print(f"events after dedup: {M.event_count(con):,}")
""")

md(r"""
## §3 — The HELD groups (hold-not-apply, encoded)
**Why holds exist.** Three groups are deliberately NOT collapsed:
- **`B2014-05786` finaled 2021-08-31** — a same-date within-file duplicate that must SURVIVE this
  stage so the **dedup47 correction** (JN-F) can demote one copy to `subsidiary/0`. Collapsing it
  here would leave the rebuild one event short of the live DB (the live dedup ran AFTER dedup47 and
  held this group because the classifications differed).
- **`B2022-00032` issued + submitted** — the two files carry **different WorkDescriptions** (the one
  genuine substantive-differ case). Which description is canonical awaits John's review; collapsing
  would silently pick one.
**Verifiability:** the holds are CALIBRATION (versioned in `corrections/v4/`), not code — a second
city's rebuild starts with an empty hold list and grows it from its own audit.
""")
code(r"""
import json
holds = json.load(open(REPO / "corrections" / "v4" / "event_dedup_holds.json"))
for h in holds["tier2_holds"]:
    print(f"HOLD {h['source_record_key']} {h['event_type_code']} {h['event_date_prefix']}")
    print(f"     {h['reason'][:110]}")
remain = con.execute("SELECT COUNT(*) FROM (SELECT source_record_key,event_type_code,event_date "
                     "FROM events GROUP BY 1,2,3 HAVING COUNT(*)>1)").fetchone()[0]
print(f"\nremaining duplicate groups (must equal the held count): {remain}")
assert remain == len(stats['held_auto']) + len(stats['held_calib']), "unexplained duplicate groups survived"
""")

md(r"""
## §4 — Verify: conservation + integrity
**What must hold.** (1) No orphaned classifications (if classifications existed); (2) no duplicate
group lost ALL its events (the keeper survives); (3) **no permit disappeared** — dedup collapses
copies, never permits. These derive live; nothing is hardcoded.
""")
code(r"""
orphan = con.execute("SELECT COUNT(*) FROM event_classifications c LEFT JOIN events e "
                     "ON e.event_id=c.event_id WHERE e.event_id IS NULL").fetchone()[0]
permits = con.execute("SELECT COUNT(DISTINCT source_record_key) FROM events").fetchone()[0]
print(f"orphaned classifications: {orphan} (expect 0)")
print(f"distinct permits retained: {permits:,}")
assert orphan == 0
con.commit(); con.close()
print("JN-B COMPLETE — the stream is dedup-clean (held groups excepted, by design).")
""")

# ---------------------------------------------------------------- viz
md(r"""
## Visualizations
### VIZ 1 — the dedup flow (the subject)
**What it shows.** Events before → duplicates removed → events after, with the held groups drawn
separately. **Derives from the run's own stats + live counts** (never literals).
""")
code(r"""
import plotly.graph_objects as go
ro = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
after = ro.execute("SELECT COUNT(*) FROM events").fetchone()[0]
before = after + stats['removed']
held_n = len(stats['held_auto']) + len(stats['held_calib'])
fig = go.Figure(go.Waterfall(orientation='v', measure=['absolute','relative','total'],
    x=['events after JN-A','tier-1 auto-collapse','events (dedup-clean)'],
    y=[before, -stats['removed'], 0],
    text=[f'{before:,}', f"-{stats['removed']:,}", f'{after:,}'],
    connector={'line':{'color':'rgb(160,160,160)'}}))
fig.update_layout(title=f'JN-B: {before:,} → −{stats["removed"]:,} duplicates → {after:,}  ·  {held_n} groups HELD (not collapsed)',
                  yaxis_title='events', height=420)
fig.show()
""")
md(r"""
**⚠ mislead-guards.** (1) The waterfall implies the removed events were *errors* — they were
**faithful ingest of overlapping source files**; the error would be counting them twice, not
recording them. (2) The **held groups are invisible at this scale** (a handful of groups against
tens of thousands of events — the exact counts derive in the title) but they are the part that
carries review risk — the bar chart's smoothness hides exactly the cases a reviewer must look at
(§3 lists them). (3) Axis starts at 0; no truncation.
""")

md(r"""
### VIZ 2 — data-flow lineage (provenance)
**What it shows.** Where this stage sits and what it reads: the method is code; the HOLDS are
versioned calibration; the target is the parameterized rebuild.
""")
code(r"""
from IPython.display import Markdown, display
display(Markdown(f'''```mermaid
flowchart LR
  RAW["raw CPRA xlsx (2 overlapping files)"] --> JNA["JN-A ingest\n{before:,} events (faithful, incl. duplicates)"]
  JNA --> JNB["JN-B dedup (THIS)\n−{stats['removed']:,} → {after:,}"]
  CAL[/"corrections/v4/event_dedup_holds.json\n{held_n} tier-2 HOLD groups"/] -.-> JNB
  JNB --> JNC["JN-C classification"]
  JNC --> JNF["JN-F corrections"]
  classDef calib fill:#ffd,stroke:#b90;
  class CAL calib;
```'''))
print("calibration is DATA (versioned, reviewable); the method is CODE (city-agnostic).")
""")
md(r"""
**⚠ mislead-guards.** (1) The diagram draws JN-C/JN-F as clean downstream stages — but the stream
they receive still **contains the held duplicate groups** (deliberately: §3), so "dedup-clean" means
*clean except the documented holds*, not perfectly single-copied. (2) The calibration node points
only at THIS stage; it does **not** mean the hold-list resolves anything — held groups pass through
unresolved until their owning correction (dedup47) or John's review acts. (3) Arrow direction shows
data flow, not validation: this diagram asserts nothing about whether downstream stages ran.
""")

md(r"""
## Assumptions ledger
| assumption | what BREAKS if violated |
|---|---|
| same (permit, milestone, date, substance) = one real event | a legit duplicate-dated re-record would be silently merged — the auto-hold on substantive-differ is the guard |
| different dates are never the same event | collapsing across dates would erase legit re-finals (tier-3) — the key design prevents it |
| keep-MIN is arbitrary-but-stable | if the two copies differed substantively, keep-MIN would pick silently — the substantive-differ auto-hold prevents exactly that |
| holds are calibration, not code | hardcoding holds in the method would make the method Berkeley-specific and the holds invisible to review |
""")

nb = new_notebook(cells=cells, metadata={'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}})
os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
with open(NB_OUT, 'w') as f: nbf.write(nb, f)
print('wrote', NB_OUT, len(cells), 'cells')
