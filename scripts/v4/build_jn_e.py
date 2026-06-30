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
## §2 — The headline: CO 3,676 vs city 4,022 (−346)
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
city=int(ta[cc].sum().sum()); print(f'OUR CO={co}  CITY CO={city}  GAP={co-city}')
""")

    md("""
## §3 — The ledger: how 3,066 became 3,676
**Where from.** Each step is a *gated, audited write* to v4 (`docs/audit/2026-06-28..29_*`). The ledger is the
audit trail made runnable — it bridges the original baseline (3,066) to the current derived CO (3,676).
**Verifiability:** the ledger arithmetic is asserted; the per-row provenance points at the audit doc.
""")
    code("""
ledger=[('baseline (pre-corrections)',3066),('C2 multifamily count-gap',+1036),('C3 Shattuck phantom-master',-163),
        ('C3 ADU-tail ancillary',-17),('C-multifamily phase-collapse',-199),('dedup47 duplicate-file-row',-47)]
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
**under** (+147) is held → §7.
""")
    code("""
print('phase OVER corrected (in CO):', BASE['documented_not_gated']['phase_over_corrected']['value'], BASE['documented_not_gated']['phase_over_corrected']['status'])
print('phase UNDER held (NOT in CO):', BASE['documented_not_gated']['phase_under_held']['value'], BASE['documented_not_gated']['phase_under_held']['status'])
""")

    md("""
## §7 — The +147 held under-count (the SHARPEST verifiability cell)  ·  folds `three_multifam_families/siblings.py`
**Where from.** Three multifamily completion permits classified `ambiguous`: B2021-03302 (+69), B2018-03422
(+55), B2016-05139 (+23). **The concern, stated plainly:** *our* WorkDescriptions carry **NO unit count** for
these — so the ONLY source of 69/55/23 is the **city's** filing. **Adopting +147 would be oracle-as-source —
circular — and is forbidden.** Therefore +147 is **HELD-not-verified**. The ONLY way to verify it independently
is the **Accela / architect-plan harvest** (a separate work stream). Until then it does not enter our CO.
""")
    code("""
import re
ev=pd.read_sql("SELECT e.source_record_key sk, json_extract(e.raw_payload,'$.WorkDescription') wd "
  "FROM events e WHERE e.source_record_key IN ('B2021-03302','B2018-03422','B2016-05139')", ro(V4)).drop_duplicates('sk')
for _,r in ev.iterrows():
    has_count = bool(re.search(r'\\d+\\s*(?:dwelling|residential|rental)?\\s*units?', str(r.wd or ''), re.I))
    print(f"  {r.sk}: our-text-has-unit-count={has_count}  | {str(r.wd)[:70]}")
print('=> our text lacks the count; 69/55/23 come ONLY from the city -> HELD-not-verified (+147).')
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
## §12 — Net picture + the building-identity refinement note (HYPOTHETICAL)
**Building-identity** is the multifamily *refinement input* (it groups permits→buildings); the base
reconciliation runs **without** it (current classification). The projection below — "if the +147 were
harvested and the residual adjudicated" — is **HYPOTHETICAL** and is deliberately **NOT written to the
baseline** (it is not a derived current value).
""")
    code("""
print(f'CURRENT (derived):     CO {co} vs city {city} = {co-city}')
print(f'HYPOTHETICAL if +147 harvested: {co}+147 = {co+147} vs {city} = {co+147-city}   # NOT a baseline value')
print('building-identity: refinement input to §6 grouping; base reconciliation does not depend on it.')
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
| **count-once** | one building, one count at completion | phased multifamily **double-counts** (over) or **drops** (under) — the −199/+147 errors |
| **null-not-zero** | a missing count is unknown, not 0 | fabricated below-market units; silent under/over-statement of affordability |
| **hold-don't-adopt** | unreproducible city figures are HELD | adopting the +147 makes the number **unverifiable** (oracle-as-source); the gate can no longer protect it |

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
