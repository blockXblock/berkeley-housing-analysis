"""Build JN-F_corrections.ipynb — the CORRECTIONS stage between JN-C (classify) and JN-E (reconcile).

House pattern: markdown-in-source; the notebook IMPORTS every method from scripts/v4/stage_methods.py
(aa6ded0 lift discipline) and READS every target list from corrections/v4/ (universal METHOD ×
Berkeley CALIBRATION). Target PARAMETERIZED (env JN_F_DB_PATH; default = the JN-A throwaway);
LIVE-DB REFUSAL guard. Gate: derived CO/BP vs the newest timestamped reconciliation baseline —
never hardcoded; HELD items are ENCODED as hold-not-apply asserts.

Run:  python scripts/v4/build_jn_f.py     # emits the notebook (no DB access at build time)
"""
import os

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-F_corrections.ipynb')

cells = []
def md(t): cells.append(new_markdown_cell(t.strip('\n')))
def code(s): cells.append(new_code_cell(s.strip('\n')))

md(r"""
# JN-F — Corrections (the calibrated writes that take 3,066 → 3,676)

**What this is.** The base classification (JN-C) lands at CO 3,066 — correct method, but the raw
descriptions hide counts (C2), phase buildings double-count (C3/C-multifamily), and the file overlap
double-counts finaled events (dedup47). Historically these corrections were **gated one-shot writes**
to the live DB (`scratch/2026-06-2{8,9}/*_write.py`, audits `docs/audit/2026-06-2{8,9}_*`) — the
pipeline result was reproducible only by trusting that history. **This stage re-expresses each one as
a universal METHOD (imported from `scripts/v4/stage_methods.py`) reading its Berkeley CALIBRATION
(`corrections/v4/`)** — so a from-raw rebuild reproduces the corrected state mechanically.

**Validated 2026-07-02** (`scratch/2026-07-02/rebuild_from_raw_driver.py`): raw → JN-A → JN-B → JN-C
→ THIS lands **CO 3,676 / BP 3,945 / events == live / per-permit completion set == live, 0 diffs**.

**Order (one true coupling).** `dedup47 → C2(T1+T2) → C3-Shattuck → C3-tail → C-multifamily`;
only **C-multifamily AFTER C2** is load-bearing (the B2021-04949 → B2021-02423 flag re-home).
""")

md(r"""
## §1 — Target guard + the correction ledger starts
Same target discipline as JN-A/B/C (`JN_F_DB_PATH`, default = the throwaway; live REFUSED — the live
DB already carries these corrections; re-running is idempotent-by-WHERE but discipline is discipline).
The `ledger` records CO after every step — the waterfall and the gate both derive from it.
""")
code(r"""
import os, sys, sqlite3, json
from pathlib import Path
REPO  = Path.home() / "berkeley-data"
_LIVE = REPO / "databases" / "berkeley_housing_v4.db"
DB_PATH = Path(os.environ.get("JN_F_DB_PATH") or os.environ.get("PIPELINE_DB_PATH")
               or str(REPO / "scratch" / "jn_a_throwaway" / "berkeley_housing_v4.db"))
if DB_PATH.resolve() == _LIVE.resolve() and os.environ.get("JN_F_ALLOW_LIVE") != "1":
    raise SystemExit(f"REFUSED: {DB_PATH} is the LIVE corrected DB (already corrected). "
                     f"Point JN_F_DB_PATH at a rebuild.")
assert DB_PATH.exists(), f"{DB_PATH} missing — run JN-A → JN-B → JN-C first."
sys.path.insert(0, str(REPO / "scripts" / "v4"))
import stage_methods as M
con = sqlite3.connect(DB_PATH)
n_class = con.execute("SELECT COUNT(*) FROM event_classifications").fetchone()[0]
assert n_class > 0, "no classifications — run JN-C before JN-F"
ledger = [("after JN-C (base classification)", M.co_total(con))]
print("target:", DB_PATH)
print(f"CO (2018-2025) at entry: {ledger[0][1]:,}")
""")

md(r"""
## §2 — dedup47: duplicate finaled-master collapse (calibration: `dedup47_permits.csv`)
**The error.** 4 permits carry TWO finaled `new_unit` master events (file overlap / within-file dup)
— their units count twice. **The method.** Keep the `MIN(event_id)` copy, demote the duplicate to
`subsidiary/0`. **Premise guard:** each permit must show exactly 2 finaled-masters (or 1, on an
idempotent re-run); anything else HALTS. Note `B2014-05786` is exactly the group JN-B **held** —
this demotion is why.
""")
code(r"""
print(M.apply_dedup47(con))
ledger.append(("dedup47 duplicate finaled-masters", M.co_total(con)))
print(f"CO -> {ledger[-1][1]:,}")
""")

md(r"""
## §3 — C2: the multifamily count-gap recovery (calibration: `c2_count_recovery.csv`)
**The error.** Big multifamily permits classified `new_unit` master but with **NULL `net_units`** —
the structured unit fields were blank, and `net_units` is prose-blind by design. Their counts exist
in the WorkDescription ("...a 152 dwelling unit mixed use building..."). **The method.** Set
`net_units` from the CALIBRATION's curated, noun-anchored recovered counts. **T1** = plain dwelling
counts; **T2** = convention-dependent (live-work / sleeping-room) counts, flagged
`convention_dependent=true` in the basis note. `B2020-03895` stays EXCLUDED (held, per calibration).
**Provenance rule:** every count comes from the permit's own description — never the city APR.
""")
code(r"""
print(M.apply_c2(con))
ledger.append(("C2 count-gap recovery (T1+T2)", M.co_total(con)))
print(f"CO -> {ledger[-1][1]:,}")
""")

md(r"""
## §4 — C3: phantom-master + ADU-tail (calibrations: `c3_shattuck_collapse.csv`, `c3_tail_demote_list.json`)
**Phantom-master (1951 Shattuck).** Two 163-unit permits are ONE 12-story building in two phases —
demote Phase 2 to `subsidiary/0` (count-once). **ADU-tail.** 17 ancillary permits (solar / meter /
panel / service) mis-promoted to `new_unit=1` on ADU parcels — demote each, **PROTECT-asserting the
paired real ADU is still counted** (the shadow-vs-real-pair rule: this stage must never erase a real
building).
""")
code(r"""
print(M.apply_c3_shattuck(con))
ledger.append(("C3 Shattuck phantom-master", M.co_total(con)))
print(f"CO -> {ledger[-1][1]:,}")
print(M.apply_c3_tail(con))
ledger.append(("C3 ADU-tail ancillary demotions", M.co_total(con)))
print(f"CO -> {ledger[-1][1]:,}")
""")

md(r"""
## §5 — C-multifamily: phased-building collapse (calibration: `c_multifamily_collapse.csv`)
**The error (systematic, both directions).** The classifier handles phased multifamily
inconsistently: sometimes BOTH phases → `new_unit` (over-count — fixed here), sometimes the
completion → `ambiguous` (under-count — **HELD**, §6). One rule fixes both: **one building, one
count, at the unit-bearing completion phase.** **Protection guard:** every demote target's own
WorkDescription must read as sitework (foundation/podium/grading) — a completion can never be
demoted by this method. The bump row re-homes the C2-T2 convention flag (40→41 manager unit) —
the reason this stage runs AFTER C2.
""")
code(r"""
print(M.apply_c_multifamily(con))
ledger.append(("C-multifamily phase-collapse", M.co_total(con)))
print(f"CO -> {ledger[-1][1]:,}")
con.commit()
""")

md(r"""
## §5b — Grounded counts: the held-item RESOLUTION path (calibration: `grounded_counts.csv`)
**What this is.** When a held building's count is independently grounded from its OWN documents (the
2026-07-02 harvest: B2021-03302 = 69 from its plan set's Phase-II unit-mix table), the resolution enters
the pipeline HERE — as a ledger row in `corrections/v4/grounded_counts.csv` (permit, count, source
document, corroboration, date) applied by `apply_grounded_counts`. **Never as a one-shot write** (that
would recreate the reproducibility gap) and **never from the city's number** (the ledger's source column
must cite the building's document). The method refuses any permit still listed as held (resolve the hold
in `held_items.json` first — with provenance) and never overwrites an existing count.
""")
code(r"""
print(M.apply_grounded_counts(con))
ledger.append(("grounded counts (harvest resolutions)", M.co_total(con)))
print(f"CO -> {ledger[-1][1]:,}")
con.commit()
""")

md(r"""
## §6 — HELD, encoded (hold-not-apply — the deliberate non-corrections)
- **The held under-side registry is `corrections/v4/held_items.json`** (the assert derives from it —
  originally +147; B2021-03302/69 RESOLVED 2026-07-02 via grounded_counts; **+78 remains**):
  `B2018-03422`/55 — a **convention conflict** (the building's own record: 0 dwelling units, 254-bed
  group living; the city's 55 matches nothing — John's GLA-convention call); `B2016-05139`/23 — **no
  digital documents** in Accela (post-retry). **Oracle-is-never-source**: the assert below FAILS the
  notebook if a held permit slips into the counted set without moving through the resolution path.
- **C1 "584 relabel" — PHANTOM, never applied**: re-running the committed classifier on its own
  output found confirmations, not gaps; applying it would DOUBLE-COUNT (~457 already in the base).
  Encoded here as considered-and-rejected so no future session re-derives it as a TODO.
- **B2020-03895** (excluded from C2) · **JN-B tier-2/3 holds** (dedup side) — same principle.
""")
code(r"""
print(M.assert_held(con))
print("HELD asserts PASS — the +147 stays held; C1-phantom stays never-applied.")
""")

md(r"""
## §7 — GATE: derived vs the external timestamped baseline
Derived CO (headline grain, `net_units>0`, no year filter) and permit-level BP vs
`data/baselines/reconciliation_baseline_*.json` (newest). **Mismatch ⇒ DIAGNOSE + HALT** (value,
sha, likely cause). Legitimate change ⇒ **append a NEW timestamped baseline**, never edit.
""")
code(r"""
import glob
BASE = json.load(open(sorted(glob.glob(str(REPO / "data" / "baselines" / "reconciliation_baseline_*.json")))[-1]))
got = {"co_completions": M.co_all_positive(con), "bp_issued": M.bp_permit_level(con)}
fails = []
for k, v in got.items():
    exp = BASE["hard_gated"][k]["value"]
    print(f"  {k:16} derived={v:<7,} baseline={exp:<7,} {'OK' if v == exp else 'FAIL'}")
    if v != exp:
        fails.append(f"{k}: derived {v} != baseline {exp}; cause: {BASE['hard_gated'][k].get('what_would_change_it','?')}; "
                     f"append a NEW timestamped baseline, never edit this one.")
assert not fails, "JN-F GATE HALT:\n" + "\n".join(fails)
print(f"GATE PASS — the rebuild reproduces the {BASE['as_of']} baseline from raw.")
""")

md(r"""
### §7b — Structural gate vs the live DB (when present)
The baseline gates TOTALS; totals can coincide while structure diverges (e.g. a wrongly-collapsed
held pair is CO-neutral). When the live corrected DB is on this machine, also require **event-count
equality and per-permit counted-completion set equality** — the bijection-grade check. Skipped
cleanly where the live DB is absent (student machines): the baseline gate above still holds.
""")
code(r"""
if _LIVE.exists() and DB_PATH.resolve() != _LIVE.resolve():
    live = sqlite3.connect(f"file:{_LIVE}?mode=ro", uri=True)
    ev_r, ev_l = M.event_count(con), M.event_count(live)
    q = ("SELECT e.source_record_key, c.net_units FROM events e "
         "JOIN event_classifications c ON c.event_id=e.event_id "
         "WHERE e.event_type_code='permit_finaled' AND c.housing_role='new_unit' AND c.is_master=1 "
         "AND COALESCE(c.net_units,0)>0")
    ours, theirs = set(con.execute(q).fetchall()), set(live.execute(q).fetchall())
    print(f"events: rebuild={ev_r:,} live={ev_l:,}  |  completion-set: rebuild-only={len(ours-theirs)} live-only={len(theirs-ours)}")
    for s in sorted(ours - theirs)[:10]: print("   REBUILD-ONLY", s)
    for s in sorted(theirs - ours)[:10]: print("   LIVE-ONLY   ", s)
    assert ev_r == ev_l and ours == theirs, "STRUCTURAL GATE HALT: totals may match but the rebuild diverges from live"
    print("STRUCTURAL GATE PASS — event count and counted-completion set are identical to live.")
    live.close()
else:
    print("live DB not present (or IS the target) — structural gate skipped; baseline gate stands.")
con.close()
""")

# ---------------------------------------------------------------- viz
md(r"""
## Visualizations
### VIZ 1 — the correction waterfall (the subject)
**What it shows.** CO after each correction step — **derived from this run's `ledger`**, never typed.
The chart changes when the calibration changes.
""")
code(r"""
import plotly.graph_objects as go
labels = [ledger[0][0]] + [name for name, _ in ledger[1:]] + ["= CO (corrected)"]
deltas = [ledger[0][1]] + [ledger[i][1] - ledger[i-1][1] for i in range(1, len(ledger))] + [0]
measure = ["absolute"] + ["relative"] * (len(ledger) - 1) + ["total"]
fig = go.Figure(go.Waterfall(orientation="v", measure=measure, x=labels, y=deltas,
    text=[f"{d:+,}" if m == "relative" else f"{ledger[-1][1]:,}" if m == "total" else f"{d:,}"
          for d, m in zip(deltas, measure)],
    connector={"line": {"color": "rgb(160,160,160)"}}))
fig.update_layout(title=f"JN-F: {ledger[0][1]:,} → {ledger[-1][1]:,} through the calibrated corrections",
                  yaxis_title="CO units (2018-2025)", height=460)
fig.show()
""")
md(r"""
**⚠ mislead-guards.** (1) The big upward C2 bar (whatever this run derives it to be — +1,036 at the
2026-07-02 validation) is **recovery of counts already present in the permits' own text** — not new
discovery, and NOT adopted from the city. (2) The downward bars remove **our own double-counts** —
they are not concessions to the city's number. (3) The held under-count (+147 at validation) is
**absent from this chart on purpose** (it is not a correction until independently grounded) —
a reader summing the bars to "the true count" would miss that the honest figure carries a known,
held, un-adopted under-side.
""")

md(r"""
### VIZ 2 — data-flow lineage: methods × calibrations (provenance)
**What it shows.** Each correction = one universal method (code) reading one calibration file
(versioned data). The city's APR appears NOWHERE in this diagram — that absence is the circularity
guard.
""")
code(r"""
from IPython.display import Markdown, display
steps = "\n".join(
    f'  C{i}[/"{f}"/] -.-> F{i}["{m}"] --> DB' for i, (f, m) in enumerate([
        ("dedup47_permits.csv", "apply_dedup47"),
        ("c2_count_recovery.csv", "apply_c2 (T1+T2)"),
        ("c3_shattuck_collapse.csv", "apply_c3_shattuck"),
        ("c3_tail_demote_list.json", "apply_c3_tail"),
        ("c_multifamily_collapse.csv", "apply_c_multifamily"),
    ]))
display(Markdown(f'''```mermaid
flowchart LR
  JNC["JN-C classified stream\n(CO {ledger[0][1]:,})"] --> DB[("rebuild DB\nCO {ledger[-1][1]:,}")]
{steps}
  DB --> JNE["JN-E reconciliation"]
  classDef calib fill:#ffd,stroke:#b90;
  class C0,C1,C2,C3,C4 calib;
```'''))
print("every arrow into DB is a method reading a VERSIONED calibration — none reads the city APR.")
""")
md(r"""
**⚠ mislead-guards.** (1) The diagram shows only the **APPLIED** corrections — the held +147, the
rejected C1-phantom, and the excluded B2020-03895 are **absent from the picture entirely**, which
is exactly the held-vs-counted mislead the viz convention warns about; §6 is the authoritative
held-side record. (2) Every calibration arrow looks equal-weight; the CO deltas they carry differ
by two orders of magnitude (the waterfall above is the magnitude view). (3) The absence of a CKAN
node is the point, but absence can't be *seen* — the §7 gate and the assumptions ledger are what
actually enforce oracle-not-source.
""")

md(r"""
## Assumptions ledger
| assumption | what BREAKS if violated |
|---|---|
| oracle-not-source | any count adopted from the city APR makes JN-E circular — the +147 hold exists because of this |
| count-once (completion phase) | phased buildings double-count (the −199) or drop (the held +147) |
| calibration is data, methods are code | inlining permit lists back into scripts recreates the endangered-inputs problem `corrections/v4/` was built to end |
| premise guards before every write | a drifted upstream state (e.g. dedup didn't run) would silently corrupt counts — guards HALT instead |
| protect the real pair | an ancillary demotion that hits a real ADU/building erases real housing — the C3-tail keep-assert and the sitework regex are the guards |
""")

nb = new_notebook(cells=cells, metadata={'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}})
os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
with open(NB_OUT, 'w') as f: nbf.write(nb, f)
print('wrote', NB_OUT, len(cells), 'cells')
