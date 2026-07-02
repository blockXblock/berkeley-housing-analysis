"""Build JN-E_co_reconciliation.ipynb — the CO reconciliation, DERIVED from v4 + CKAN, gated against an
EXTERNAL TIMESTAMPED BASELINE (data/baselines/reconciliation_baseline_*.json), never hardcoded constants.

House pattern (build_jn_c/d): markdown-in-source via md()/code(); this generator BOTH (a) derives+gates the
4 hard figures live (the real gate test) and (b) emits the annotated notebook. Legitimate change = append a
NEW timestamped baseline (EVIDENCE-append-only), never hand-edit logic to match drift.

Run:
  python scripts/v4/build_jn_e.py                 # derive, gate vs newest baseline, emit notebook
  python scripts/v4/build_jn_e.py --baseline X    # gate vs a specific baseline (used for the both-ways test)
"""
import os, sys, json, glob, sqlite3, argparse
import pandas as pd
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
V4   = os.path.join(ROOT, 'databases', 'berkeley_housing_v4.db')
HCD  = os.path.join(ROOT, 'databases', 'hcd_apr_mirror_2026-06-17_fresh.db')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-E_co_reconciliation.ipynb')
BASELINE_GLOB = os.path.join(ROOT, 'data', 'baselines', 'reconciliation_baseline_*.json')

def ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)
def v4_sha():
    import hashlib
    h = hashlib.sha256()
    with open(V4, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()[:16]

# ============================================================ DERIVATIONS (the live truth)
def derive():
    """Derive the 4 hard figures from v4 + CKAN. Returns a dict of derived values + the v4 sha."""
    d = {}
    with ro(V4) as c:
        d['co_completions'] = c.execute(
            "SELECT COALESCE(SUM(x.net_units),0) FROM events e JOIN event_classifications x ON x.event_id=e.event_id "
            "WHERE e.event_type_code='permit_finaled' AND x.housing_role='new_unit' AND x.is_master=1 "
            "AND COALESCE(x.net_units,0)>0").fetchone()[0]
        # BP: permit-level (distinct source_record_key), NOT event-level
        d['bp_issued'] = c.execute(
            "WITH one AS (SELECT e.source_record_key sk, x.net_units nu, "
            "  ROW_NUMBER() OVER (PARTITION BY e.source_record_key ORDER BY e.event_id) rn "
            "  FROM events e JOIN event_classifications x ON x.event_id=e.event_id "
            "  WHERE e.event_type_code='permit_issued' AND x.housing_role='new_unit' AND x.is_master=1) "
            "SELECT COALESCE(SUM(nu),0) FROM one WHERE rn=1").fetchone()[0]
    ta = pd.read_sql("SELECT * FROM table_a2", ro(HCD))
    co_cols = [col for col in ta.columns if col.startswith('CO_') and 'DT' not in col]
    for col in co_cols: ta[col] = pd.to_numeric(ta[col], errors='coerce').fillna(0)
    d['city_co_total'] = int(ta[co_cols].sum().sum())
    d['co_gap'] = d['co_completions'] - d['city_co_total']
    return d, v4_sha()

# ============================================================ GATE (derived vs external baseline)
def newest_baseline():
    files = sorted(glob.glob(BASELINE_GLOB))
    if not files: raise FileNotFoundError(f'no baseline matching {BASELINE_GLOB}')
    return files[-1]

def gate(baseline_path=None):
    """Compare DERIVED vs BASELINE. HALT with a DIAGNOSTIC on any mismatch (computed vs baseline, sha, cause)."""
    baseline_path = baseline_path or newest_baseline()
    base = json.load(open(baseline_path))
    derived, sha = derive()
    print(f"[JN-E gate] baseline: {os.path.relpath(baseline_path, ROOT)}  (as_of {base['as_of']})")
    print(f"[JN-E gate] v4 sha derived={sha}  baseline={base['v4_sha']}  {'MATCH' if sha==base['v4_sha'] else 'DRIFT'}")
    failures = []
    for key, spec in base['hard_gated'].items():
        exp = spec['value']; got = derived[key]
        ok = (got == exp)
        print(f"   {key:16} derived={got:<7} baseline={exp:<7} {'OK' if ok else 'FAIL'}")
        if not ok:
            failures.append(
                f"   *** {key}: DERIVED {got} != BASELINE {exp}\n"
                f"       v4 sha now {sha} (baseline pinned {base['v4_sha']})\n"
                f"       likely cause: {spec.get('what_would_change_it','?')}\n"
                f"       legitimate change => append a NEW timestamped baseline (do NOT edit this value).")
    if failures:
        raise AssertionError("JN-E GATE HALT — derived != baseline:\n" + "\n".join(failures))
    print("[JN-E gate] PASS — all 4 hard figures match the baseline.")
    return derived, base, sha

# ============================================================ NOTEBOOK (the explained, re-runnable artifact)
cells = []
def md(t): cells.append(new_markdown_cell(t.strip("\n")))
def code(s): cells.append(new_code_cell(s.strip("\n")))

def build_notebook():
    cells.clear()
    md("""
# JN-E — CO Reconciliation (v4 ↔ CKAN), derived & baseline-gated

**What this is.** The Certificate-of-Occupancy reconciliation between our independent reconstruction (v4)
and Berkeley's filed HCD APR (the CKAN mirror) — **every figure DERIVED here**, asserted against an
**external timestamped baseline** (`data/baselines/reconciliation_baseline_*.json`), never hardcoded.

**The text cells are the deliverable.** Each section answers: *where does this data come from* (the flow),
*what transformation happens and what it assumes*, and *what could be wrong* (the verifiability concern).

**Role-discipline contract (the load-bearing invariant).**
DATA FLOW: `raw CPRA xlsx → JN-A events → JN-C classification → gated corrections → THIS reconciliation`.
CKAN **never appears in that chain** — it enters ONLY at the comparison step. **If CKAN ever flows INTO a
derived number, the reconciliation is circular and void.** That single concern governs the whole notebook.
""")

    md("""
## §1 — Setup + the two sources (read-only)
**Where from.** v4 = the end of our derivation chain (raw CPRA → JN-A → JN-C → corrections). CKAN mirror =
the ORACLE (reconcile-target only). **Verifiability:** both opened read-only and the v4 **sha is pinned** —
the baseline is meaningless unless you reconcile the *same* DB. If the sha drifts, the gate flags it.
""")
    code("""
import os, sqlite3, json, glob, hashlib
import pandas as pd
ROOT=os.path.expanduser('~/berkeley-data')
V4=os.path.join(ROOT,'databases','berkeley_housing_v4.db'); HCD=os.path.join(ROOT,'databases','hcd_apr_mirror_2026-06-17_fresh.db')
def ro(p): return sqlite3.connect(f'file:{p}?mode=ro',uri=True)
def v4_sha():
    h=hashlib.sha256()
    with open(V4,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest()[:16]
BASE=json.load(open(sorted(glob.glob(os.path.join(ROOT,'data','baselines','reconciliation_baseline_*.json')))[-1]))
print('v4 sha:', v4_sha(), '| baseline as_of:', BASE['as_of'], '| pinned sha:', BASE['v4_sha'])
print('CONTRACT:', BASE['verifiability_contract']['oracle_not_source'])
""")

    md("""
## §2 — The headline: our CO vs the city's (both derived below; the gate pins the current values)
**Where from.** *Our* CO = finaled `new_unit` master permits with `net_units>0` (the ADR-002 verdict layer,
classified in JN-C, corrected by the gated writes). *City* CO = the sum of all 11 `CO_*` income-tier columns
in `table_a2` (the city's curated unit-creating rollup).
**Transformation & assumption.** We compare a **per-permit verdict count** to a **tier-sum rollup**.
**Verifiability concern (grain comparability):** the two grains are comparable because both are
"net new dwelling units that reached completion in Berkeley" — but the comparison is **fragile** where the
city aggregates differently than we attribute per-permit (phased buildings, ADUs, re-platted parcels). Those
fragilities are exactly what the decomposition (§5–§11) isolates. **City CO is NEVER an input — only the target.**
""")
    code("""
co = ro(V4).execute("SELECT COALESCE(SUM(x.net_units),0) FROM events e JOIN event_classifications x "
  "ON x.event_id=e.event_id WHERE e.event_type_code='permit_finaled' AND x.housing_role='new_unit' "
  "AND x.is_master=1 AND COALESCE(x.net_units,0)>0").fetchone()[0]
ta=pd.read_sql('SELECT * FROM table_a2', ro(HCD)); cc=[c for c in ta.columns if c.startswith('CO_') and 'DT' not in c]
for c in cc: ta[c]=pd.to_numeric(ta[c],errors='coerce').fillna(0)
city=int(ta[cc].sum().sum()); print(f'OUR CO={co}  CITY CO (CKAN)={city}  GAP={co-city}')
adj=BASE.get('documented_not_gated',{}).get('city_co_adjudicated')
if adj: print(f"ADJUDICATED CITY (PDF-CKAN union, per-row): {adj['value']}  ->  ours-vs-adjudicated {co-adj['value']:+d}")
""")

    md("""
## §3 — The ledger: how 3,066 became 3,676
**Where from.** Each step is a *gated, audited write* to v4 (`docs/audit/2026-06-28..29_*`). The ledger is the
audit trail made runnable — it bridges the original baseline (3,066) to the current derived CO (3,676).
**Verifiability:** the ledger arithmetic is asserted; the per-row provenance points at the audit doc.
""")
    code("""
# the ledger DERIVES from the baseline file (2026-07-02 fix: was an inline literal list that broke
# on every legitimate baseline append)
ledger=[(s['label'], s['delta']) for s in BASE['ledger']['steps']]
run=0
for name,d in ledger: run+=d; print(f'  {name:34} {d:+6}  -> {run}')
assert run==co, f'ledger {run} != derived CO {co}'
print('ledger reconciles to derived CO:', run)
""")

    md("""
## §4 — Decomposition framing
The −346 is **not a uniform shortfall** — it is a NET of large offsetting flows. Two directions:
**forward** (city credits, we don't) and **reverse** (we credit, city doesn't). The adjudication rule,
stated once and applied throughout: **the mirror ENUMERATES where we differ; v4 ADJUDICATES each case from
our own evidence. City-silence is never proof.**
""")

    md("""
## §5 — Permit-mismatch noise (~689, net-zero)  ·  folds `reverse_overcount_triage.py`
**Where from.** The reverse triage of our counted completions the city credits under a *different* permit#/ID
on the same parcel. **Transformation:** match our completions to city credits by APN; the matched-but-
different-ID set is noise. **Verifiability concern — the MATCHING:** a "mismatch" could be a *real*
disagreement if the APN/address join is wrong. We size it by APN + magnitude proximity; it is **approximate**,
which is why ~689 is DOCUMENTED in the baseline but **not hard-gated**. It nets to zero because both sides
count the same unit under different identifiers.
""")
    code("""
print('permit-mismatch noise (documented, heuristic):', BASE['documented_not_gated']['permit_mismatch_noise']['value'],
      '-', BASE['documented_not_gated']['permit_mismatch_noise']['sign'])
print('concern:', BASE['documented_not_gated']['permit_mismatch_noise']['verifiability_concern'])
""")

    md("""
## §6 — Phase-handling, both directions  ·  folds `three_multifam_*`, `c_multifamily_collapse_write.py`
**Assumption (load-bearing): count-once — one building, one count, at the unit-bearing completion phase.**
Foundation/podium/superstructure are *phases of one building*; counting each = double. The systematic finding:
the classifier handled phased multifamily **inconsistently** — sometimes both phases→`new_unit` (over),
sometimes the completion→`ambiguous` (under). **Over** (−199) is already corrected (in §3 ledger, in 3,676);
**under** side is HELD → §7 (originally +147; +69 resolved via the 2026-07-02 harvest, +78 remains).
""")
    code("""
print('phase OVER corrected (in CO):', BASE['documented_not_gated']['phase_over_corrected']['value'], BASE['documented_not_gated']['phase_over_corrected']['status'])
print('phase UNDER held (NOT in CO):', BASE['documented_not_gated']['phase_under_held']['value'], BASE['documented_not_gated']['phase_under_held']['status'])
""")

    md("""
## §7 — The held under-count (the SHARPEST verifiability cell)  ·  folds `three_multifam_families/siblings.py` + the 2026-07-02 harvest
**Where from.** Multifamily completion permits classified `ambiguous` whose counts our pipeline could not
independently materialize. **The rule:** a count enters our CO only from the **building's own documents**
(plan set / tabulation) — the city's filing only ENUMERATES which buildings to chase; adopting its number
would be oracle-as-source. **The registry is CALIBRATION** (`corrections/v4/held_items.json`): held items
with reasons, resolved items with document provenance. The 2026-07-02 harvest resolved B2021-03302 (69,
grounded from its plan set's unit-mix table) and re-based the remaining holds: B2018-03422 is a
**convention conflict** (the building's own record says 0 dwelling units / 254-bed group living — the
city's 55 matches nothing), B2016-05139 has **no digital documents**. This cell DERIVES the current
held/resolved state from the registry — it does not hardcode it.
""")
    code("""
import json as _json
_held=_json.load(open(os.path.join(ROOT,'corrections','v4','held_items.json')))
for h in _held['held_147']:
    print(f"  HELD    {h['permit']} (city claims {h['city_count_unadopted']}): {h['reason'][:95]}")
for h in _held.get('resolved',[]):
    print(f"  RESOLVED {h['permit']} ({h['city_count_unadopted']}): {h['resolution'][:95]}")
held_total=sum(h['city_count_unadopted'] for h in _held['held_147'])
print(f'=> still held (city-enumerated, un-adopted): +{held_total}; resolutions enter CO only via '
      f'corrections/v4/grounded_counts.csv with document provenance.')
""")

    md("""
## §8 — ADU recall (~4)  ·  folds `adu_recall_gap_sizing.py`
**Where from.** Manufactured-home / within-existing-home ADUs held `ambiguous`. **null-not-zero:** a missing
count is unknown, never 0. **Verifiability:** a lower bound — the broader `adu_flag`-nonhousing-role bucket is
not fully sized, so ~4 is DOCUMENTED, not gated.
""")
    code("print('ADU recall (documented, lower bound):', BASE['documented_not_gated']['adu_recall']['value'])")

    md("""
## §9 — Dedup (already corrected) — and why the count DEPENDS on it  ·  folds dedup47 + event-dedup
**Where from.** The CPRA two-file overlap (2018-2022 + 2023-2025) made some permits emit duplicate
milestone events. **The CO count's correctness DEPENDS on dedup being complete.** dedup47 removed 4 permits'
duplicate *finaled* events (−47, in §3 ledger); the 2,870-event structural dedup was CO-neutral.
**Verifiability — checked:** below we confirm **0 counted permits with >1 finaled-master event** (the dedup
held), and the event-dedup was proven CO-unchanged in `docs/audit/2026-06-29_event_dedup_write.md`.
""")
    code("""
dups=ro(V4).execute("SELECT COUNT(*) FROM (SELECT e.source_record_key FROM events e JOIN event_classifications x "
  "ON x.event_id=e.event_id WHERE e.event_type_code='permit_finaled' AND x.housing_role='new_unit' AND x.is_master=1 "
  "AND COALESCE(x.net_units,0)>0 GROUP BY e.source_record_key HAVING COUNT(*)>1)").fetchone()[0]
print('counted permits with >1 finaled-master event:', dups, '(expect 0 -> dedup complete, CO is dedup-clean)')
assert dups==0, 'DEDUP INCOMPLETE — CO count is not trustworthy until this is 0'
""")

    md("""
## §10 — The BP side, re-established at permit-level: 3,945 (retires 4,911)
**Where from.** FIRST building-permit issuance, **permit-level** = `COUNT(DISTINCT source_record_key)` over
`permit_issued`/`new_unit`/`master`. **The verifiability lesson (deploy-state-decay):** the prior figure
**4,911 was unverifiable** — it had *no runnable provenance* (ad-hoc prose in PROGRESS) and was **event-inflated**
(the cross-file overlap doubled ~1,430 issued events). **A number you cannot re-derive is a number you cannot
trust.** We retire it: derive at permit-level (3,945; event-level 3,946 — they match now that dedup is done).
**Coverage caveat:** tracked-project BPs only, an internal lower bound (the full-city BP stream is unmodeled).
""")
    code("""
ev_lvl=ro(V4).execute("SELECT COALESCE(SUM(x.net_units),0) FROM events e JOIN event_classifications x "
  "ON x.event_id=e.event_id WHERE e.event_type_code='permit_issued' AND x.housing_role='new_unit' AND x.is_master=1").fetchone()[0]
pm_lvl=ro(V4).execute("WITH one AS (SELECT e.source_record_key sk, x.net_units nu, "
  "ROW_NUMBER() OVER (PARTITION BY e.source_record_key ORDER BY e.event_id) rn FROM events e "
  "JOIN event_classifications x ON x.event_id=e.event_id WHERE e.event_type_code='permit_issued' "
  "AND x.housing_role='new_unit' AND x.is_master=1) SELECT COALESCE(SUM(nu),0) FROM one WHERE rn=1").fetchone()[0]
print(f'BP-issued units: event-level={ev_lvl}  PERMIT-level={pm_lvl}  (retires the un-provenanced 4,911)')
""")

    md("""
## §11 — The ~−150 residual (the open, sensitive direction)  ·  folds `structural_gap_triage.py`
**Where from.** After both directions are corrected, the residual is **genuine real-housing-the-city-counts-
that-we-don't** — the forward triage (COVERAGE / DETECTION / TIMING / POSSIBLE_CITY_OVER).
**Verifiability — the sharpest open concern:** this requires **per-permit INDEPENDENT proof** (e.g. the
39-unit congregate CITY_UNDER candidate), **never CKAN-silence**. It is **not closeable by adoption**; it is
DOCUMENTED (~−150), not gated, and is the standing adjudication queue.
""")
    code("""
print('residual (documented, open):', BASE['documented_not_gated']['residual']['value'], '-', BASE['documented_not_gated']['residual']['status'])
print('concern:', BASE['documented_not_gated']['residual']['verifiability_concern'])
""")

    md("""
## §11b — Window attributions (same-period comparison, derived from calibration)
**The lesson of The Overture (1808-1812 University):** our completion grain is the permit-FINALED date,
which can lag actual occupancy by years (a 2016-built building whose permit closed administratively in
2021). The city credited such buildings in PRE-window APRs, so comparing raw counts misplaces them.
`corrections/v4/window_attributions.json` records each adjudicated case WITH its evidence; this cell
derives the same-period comparison. **The buildings stay fully counted in all-time totals** — this
adjusts the COMPARISON, never the count.
""")
    code("""
WA=json.load(open(os.path.join(ROOT,'corrections','v4','window_attributions.json')))
wa_units=sum(a['units'] for a in WA['attributions'])
for a in WA['attributions']:
    print(f"  {a['permit']} {a['units']}u — {a['building'][:60]}: attributed {a['attributed_completion']}")
print(f"window-adjusted comparison: ({co} − {wa_units}) vs {city} = {co-wa_units-city:+d}   (raw: {co-city:+d})")
""")

    md("""
## §12 — Net picture + the building-identity refinement note (HYPOTHETICAL)
**Building-identity** is the multifamily *refinement input* (it groups permits→buildings); the base
reconciliation runs **without** it (current classification). The projection below — "if the +147 were
harvested and the residual adjudicated" — is **HYPOTHETICAL** and is deliberately **NOT written to the
baseline** (it is not a derived current value).
""")
    code("""
print(f'CURRENT (derived):     CO {co} vs city {city} = {co-city}')
_ht=sum(h['city_count_unadopted'] for h in _held['held_147'])
print(f'HYPOTHETICAL if the remaining +{_ht} held were grounded: {co}+{_ht} = {co+_ht} vs {city} = {co+_ht-city}   # NOT a baseline value')
print('building-identity: refinement input to §6 grouping; base reconciliation does not depend on it.')
""")

    # ============================================================ VISUALIZATIONS (derive from data/baseline, never hardcode)
    md("""
## Visualizations
Per the viz convention: each chart is text-sandwiched, **derives from the data/baseline (never hardcoded
literals)**, and carries a *what-it-could-mislead-about* annotation. (plotly for the quantitative charts +
flow; mermaid for the lineage — graphviz is the richer option when the `dot` binary is installed.)
""")

    # ---- VIZ 1: reconciliation waterfall ----
    md("""
### VIZ 1 — Reconciliation waterfall (the subject)
**What it shows.** How **3,066 → 3,676** through the gated corrections — the offsetting flows made visual.
Read it as: the floor (pre-corrections) plus each audited write, landing on the derived CO.
**Derives from** the baseline `ledger.steps` (not literals) — so the bars track the data.
""")
    code("""
import json, glob, os
import plotly.graph_objects as go
BASE=json.load(open(sorted(glob.glob(os.path.join(ROOT,'data','baselines','reconciliation_baseline_*.json')))[-1]))
steps=BASE['ledger']['steps']
labels=[s['label'] for s in steps]+['= CO (derived)']
deltas=[s['delta'] for s in steps]+[0]
measure=['absolute']+['relative']*(len(steps)-1)+['total']
# DERIVE-CHECK: the ledger must reconcile to the gated co_completions, else the chart would lie
assert sum(s['delta'] for s in steps)==BASE['hard_gated']['co_completions']['value'], 'ledger != CO'
fig=go.Figure(go.Waterfall(orientation='v', measure=measure, x=labels, y=deltas,
    text=[f"{d:+,}" if m!='total' else f"{sum(s['delta'] for s in steps):,}" for d,m in zip(deltas,measure)],
    connector={'line':{'color':'rgb(160,160,160)'}}))
fig.update_layout(title=f"CO reconciliation ledger: 3,066 → {BASE['hard_gated']['co_completions']['value']:,} (derived)",
                  yaxis_title='units', showlegend=False, height=460)
fig.show()
""")
    md("""
**What to read / what it could MISLEAD about.** The −163 (Shattuck) and −199 (C-multifamily) are **our OWN
double-counts removed**, not the city's. ⚠ Mislead-guards: the bars are **net of larger offsetting flows**
(a −199 "phase-collapse" removed ~398 of gross double-count to net −199); and **+1,036 C2 is NOT "we found
1,036 new units"** — it's a **count-gap recovery** (units present in permits but uncounted by the prior
classifier). A waterfall implies clean additive discovery; these are corrections, not discoveries.
""")

    # ---- VIZ 2: gap-decomposition Sankey ----
    md("""
### VIZ 2 — The −346 gap decomposition (the flow)
**What it shows.** The −346 is **not uniform** — it's competing currents. This Sankey splits **city 4,022**
into the part our **3,676** matches plus the directional components (held / residual / ADU / heuristic slop).
**Derives** the magnitudes from the baseline (`hard_gated` + `documented_not_gated`); the slop is computed so
the flows balance to 4,022 exactly (making the heuristic imprecision visible, not hidden).
""")
    code("""
ours=BASE['hard_gated']['co_completions']['value']; city=BASE['hard_gated']['city_co_total']['value']
held=BASE['documented_not_gated']['phase_under_held']['value']
adu=BASE['documented_not_gated']['adu_recall']['value']
resid=abs(BASE['documented_not_gated']['residual']['value'])
slop=city-ours-held-adu-resid          # DERIVED balancer -> flows sum to city exactly; exposes heuristic slop
# nodes: 0 our, 1 city, 2 held, 3 residual, 4 adu, 5 slop
labels=[f'Our CO {ours:,}', f'City CO {city:,}', f'+{held} HELD (not counted, awaiting Accela)',
        f'~{resid} residual (real under)', f'~{adu} ADU recall', f'~{slop} heuristic slop (approx)']
src=[0,2,3,4,5]; tgt=[1,1,1,1,1]; val=[ours,held,resid,adu,slop]
HELD_COLOR='rgba(214,39,40,0.65)'   # distinct: HELD is NOT part of our count
link_color=['rgba(150,150,150,0.45)', HELD_COLOR, 'rgba(255,127,14,0.5)', 'rgba(44,160,44,0.5)', 'rgba(190,190,190,0.35)']
fig=go.Figure(go.Sankey(
    node=dict(label=labels, pad=18, thickness=16,
              color=['#888','#444',HELD_COLOR,'#ff7f0e','#2ca02c','#bbb']),
    link=dict(source=src, target=tgt, value=val, color=link_color)))
fig.update_layout(title=f"Why ours {ours:,} < city {city:,}: the −{city-ours} gap as currents", height=420)
fig.show()
""")
    md("""
**⚠ viz-verifiability (the chart can overstate — guard it).**
- **The held under-count is HELD, not counted** (crimson; +78 as of 2026-07-02 — was +147). It is drawn as a
  *would-fill-the-gap* current, **NOT** a flow into our 3,676 — or the Sankey would imply a count we
  **deliberately did not make** (oracle-not-source: the city enumerated it, we haven't independently grounded it).
- **The ~689 permit-mismatch noise is net-zero** and is **NOT a flow here** — it lives *inside* the matched
  3,676 (both sides count those units under different IDs); showing it as a gap-current would invent a gap.
- **held / residual / ADU / slop are HEURISTIC** (baseline `documented_not_gated`, not gated). The **slop link
  is the derived balancer** — its size IS the imprecision, shown honestly rather than hidden by forcing a tidy sum.
""")

    # ---- VIZ 3: data-flow lineage ----
    md("""
### VIZ 3 — Data-flow lineage (provenance made visible)
**What it shows.** Where every number comes from: raw CPRA → JN-A → JN-C → gated corrections → v4 DB →
JN-E (this reconciliation). **CKAN/mirror is a SEPARATE node that ONLY compares** — an arrow points INTO the
comparison, never back into our derived chain. **Derives** the headline numbers into the node labels from the
baseline. (Rendered as mermaid — GitHub renders it in-notebook; graphviz is the richer option when installed.)
""")
    code("""
from IPython.display import Markdown, display
g=f'''```mermaid
flowchart LR
  RAW["raw CPRA xlsx\\n(2018-2022 + 2023-2025)"] --> JNA["JN-A ingestion\\nevents (deduped)"]
  JNA --> JNC["JN-C classification\\nevent_classifications"]
  JNC --> COR["gated corrections\\nC2/C3/C-multifamily/dedup"]
  COR --> V4[("v4 DB\\nberkeley_housing_v4.db")]
  V4 --> JNE["JN-E reconciliation\\nOur CO = {ours:,} · BP = {BASE['hard_gated']['bp_issued']['value']:,}"]
  JNE --> CMP{{"COMPARISON\\nours {ours:,} vs city {city:,} = {ours-city}"}}
  CKAN[/"CKAN / HCD mirror (ORACLE)\\nCity CO = {city:,}"/] --> CMP
  classDef oracle fill:#fdd,stroke:#c00,stroke-dasharray:5 3;
  class CKAN oracle;
```'''
display(Markdown(g))
print('CKAN -> COMPARISON only; NO arrow runs CKAN -> (RAW|JNA|JNC|COR|V4|JNE). That dead-end IS the circularity guard.')
""")
    md("""
**⚠ the circularity-invariant, made visual.** Every arrow flows **left-to-right into our derived chain
except CKAN's** — CKAN points **only into the COMPARISON node** (dashed red, an oracle sink). **If an arrow
ever ran from CKAN back into RAW/JN-A/JN-C/corrections/v4/JN-E, the reconciliation would be circular and
void.** The diagram's shape *is* the proof that can't happen: the oracle is a dead-end comparison input,
never a source. (This is `verifiability_contract.oracle_not_source` drawn.)
""")

    md("""
## §13 — The gate: derived vs baseline (not hardcoded)
**Design.** The gate compares **DERIVED vs the external timestamped BASELINE file** — never hardcoded
constants. On any mismatch it **DIAGNOSES** (computed value vs baseline value, the v4 sha then-vs-now, the
likely cause from the baseline's `what_would_change_it`) and **HALTs**. **Legitimate change = append a NEW
timestamped baseline** (EVIDENCE-append-only); you NEVER hand-edit a value to make a drifted computation pass.
This is the JN-A anchor-test discipline applied to the reconciliation.
""")
    code("""
sha=v4_sha(); fails=[]
for k,spec in BASE['hard_gated'].items():
    got={'co_completions':co,'city_co_total':city,'co_gap':co-city,'bp_issued':pm_lvl}[k]
    ok=got==spec['value']; print(f"  {k:16} derived={got:<7} baseline={spec['value']:<7} {'OK' if ok else 'FAIL'}")
    if not ok: fails.append(f"{k}: derived {got} != baseline {spec['value']} (sha {sha} vs {BASE['v4_sha']}); cause: {spec['what_would_change_it']}; append a new baseline, don't edit.")
assert not fails, 'JN-E GATE HALT:\\n'+'\\n'.join(fails)
print('GATE PASS — 4 hard figures match', BASE['as_of'], 'baseline.')
""")

    md("""
## §14 — Assumptions ledger = verifiability ledger (the teachable core)
Each assumption, and **what BREAKS if it is violated** (the failure mode) — so a future reader, or a second
city's analyst, knows the stakes:

| assumption | what it means | what BREAKS if violated |
|---|---|---|
| **oracle-not-source** | CKAN enumerates, never derives | the reconciliation is **circular and void** — you'd be "verifying" the city against itself |
| **count-once** | one building, one count at completion | phased multifamily **double-counts** (over) or **drops** (under) — the −199 over / held-under errors |
| **null-not-zero** | a missing count is unknown, not 0 | fabricated below-market units; silent under/over-statement of affordability |
| **hold-don't-adopt** | unreproducible city figures are HELD | adopting a held city figure makes the number **unverifiable** (oracle-as-source); resolution goes through grounded_counts.csv with document provenance |

These four are the lesson: the reconciliation is trustworthy **only** while all four hold. The gate (§13)
enforces the *numbers*; this ledger enforces the *reasoning*.
""")

    nb = new_notebook(cells=cells, metadata={'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}})
    os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
    with open(NB_OUT, 'w') as f: nbf.write(nb, f)
    return NB_OUT

# ============================================================ MAIN
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', default=None, help='specific baseline json (default: newest)')
    ap.add_argument('--no-notebook', action='store_true')
    args = ap.parse_args()
    print('=== JN-E: derive + gate ==='); derived, base, sha = gate(args.baseline)
    if not args.no_notebook:
        out = build_notebook(); print(f'\n=== emitted notebook: {os.path.relpath(out, ROOT)} ({len(cells)} cells) ===')
    print('\nDONE.')
