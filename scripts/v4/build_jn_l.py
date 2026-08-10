"""Build JN-L_fiscal_flows.ipynb — the fiscal-flows JN: new property tax from housing COs,
city revenue flows (property / sales / transfer taxes, developer + in-lieu fees), and the
sources of funds behind Berkeley housing projects. DERIVED from v2 + the Feb-2026 Alameda
assessor (berkeley.db), gated against an EXTERNAL TIMESTAMPED BASELINE
(data/baselines/fiscal_flows_baseline_*.json) — never hardcoded constants in the logic.

House pattern (build_jn_e): this generator BOTH (a) derives + gates the hard figures live and
(b) emits the annotated notebook whose cells re-derive everything. Legitimate change = append a
NEW timestamped baseline (EVIDENCE-append-only), never a hand-edit of a magic number.

City-budget figures (FY27 GF revenue mix, department spend, the 32.57% AB-8 city share) are an
EXTERNAL-FACTS layer recorded in the baseline WITH provenance URLs — context we compare against,
never something we derive from primary sources here. CKAN is not involved anywhere in this JN.

Run:
  python scripts/v4/build_jn_l.py                   # derive, gate vs newest baseline, emit notebook
  python scripts/v4/build_jn_l.py --write-baseline  # first run / legitimate change: append new baseline
  python scripts/v4/build_jn_l.py --baseline PATH   # gate vs a specific baseline
"""
import os, sys, json, glob, sqlite3, argparse, hashlib, statistics
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
ASSESSOR = os.path.join(ROOT, 'databases', 'berkeley.db')
NB_OUT = os.path.join(ROOT, 'notebooks', 'v4', 'JN-L_fiscal_flows.ipynb')
BASELINE_GLOB = os.path.join(ROOT, 'data', 'baselines', 'fiscal_flows_baseline_*.json')
BASELINE_DATE = '2026-08-10'

ADU_BLOCK = (185, 899)  # CO-only import cohort id block (CLAUDE.md structural fact)


def ro(p):
    return sqlite3.connect(f'file:{p}?mode=ro', uri=True)


def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


def assessor_lookup():
    """berkeley.db parcels keyed by Option-B canonical APN (book(3)-page(4)-parcel(3)-sub(2)).
    Multiple rows per APN (condo sub-parcels) are summed."""
    look = {}
    with ro(ASSESSOR) as a:
        for book, page, parcel, sub, land, imps, tnv in a.execute(
                "SELECT BOOK, PAGE, PARCEL, SUB_PARCEL, Land, Imps, TotalNetValue FROM parcels"):
            if not book or not page or not parcel:
                continue
            sub = sub if sub not in (None, '', ' ') else '0'
            key = (f"{str(book).strip().zfill(3)}-{str(page).strip().zfill(4)}-"
                   f"{str(parcel).strip().zfill(3)}-{str(sub).strip().zfill(2)}")
            l, i, t = land or 0, imps or 0, tnv or 0
            if key in look:
                o = look[key]
                look[key] = (o[0] + l, o[1] + i, o[2] + t)
            else:
                look[key] = (l, i, t)
    return look


# ============================================================ DERIVATIONS (the live truth)
def derive():
    d = {}
    look = assessor_lookup()
    lo, hi = ADU_BLOCK
    with ro(V2) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT f.project_id, f.total_units, f.co_issued_date,
                   GROUP_CONCAT(pa.apn_normalized) AS apns
            FROM v_projects_flat f
            LEFT JOIN project_parcels pp ON pp.project_id = f.project_id
            LEFT JOIN parcels pa ON pa.id = pp.parcel_id
            WHERE f.co_issued_date IS NOT NULL
            GROUP BY f.project_id""").fetchall()

        d['completed_projects'] = len(rows)
        d['completed_units'] = sum(r['total_units'] or 0 for r in rows)

        matched = 0
        tracked_imps = 0.0
        tracked_units = 0
        per_year = {}          # co_year -> [tracked_units, tracked_imps]
        bench = []             # (imps_per_unit, project_id) for tracked >=100u
        for r in rows:
            land = imps = 0.0
            hit = False
            for apn in set((r['apns'] or '').split(',')):
                if apn and apn in look:
                    l, i, _t = look[apn]
                    land += l; imps += i; hit = True
            if hit:
                matched += 1
            is_adu_block = lo <= r['project_id'] <= hi
            if not is_adu_block:
                u = r['total_units'] or 0
                tracked_imps += imps
                tracked_units += u
                yr = r['co_issued_date'][:4]
                per_year.setdefault(yr, [0, 0.0])
                per_year[yr][0] += u
                per_year[yr][1] += imps
                if u >= 100 and imps > 0:
                    bench.append((imps / u, r['project_id']))
        d['assessor_matched'] = matched
        d['tracked_units'] = tracked_units
        d['tracked_imps_m'] = round(tracked_imps / 1e6, 1)
        d['tracked_per_year'] = {y: [v[0], round(v[1] / 1e6, 1)] for y, v in sorted(per_year.items())}
        best = max(bench) if bench else (0, None)
        d['benchmark_per_unit_k'] = round(best[0] / 1e3)     # $K per unit, most-enrolled large project
        d['benchmark_project_id'] = best[1]

        # ADU / small-infill: CO-only block, 1-2 units, with declared permit valuation
        vals = [row[0] for row in c.execute("""
            SELECT SUM(pe.valuation) FROM v_projects_flat p
            JOIN permits pe ON pe.project_id = p.project_id
            WHERE p.co_issued_date IS NOT NULL AND p.project_id BETWEEN ? AND ?
              AND p.total_units <= 2 AND pe.valuation > 0
            GROUP BY p.project_id""", (lo, hi))]
        d['adu_small_n'] = len(vals)
        d['adu_small_median_valuation'] = round(statistics.median(vals)) if vals else 0
        d['adu_small_sum_m'] = round(sum(vals) / 1e6, 1)
        d['cohort_valuation_sum_m'] = round((c.execute("""
            SELECT COALESCE(SUM(pe.valuation),0) FROM v_projects_flat p
            JOIN permits pe ON pe.project_id = p.project_id
            WHERE p.co_issued_date IS NOT NULL AND p.project_id BETWEEN ? AND ?
              AND pe.valuation > 0""", (lo, hi)).fetchone()[0]) / 1e6, 1)

        # developer-fee empirical layer (thin: Accela aggregates)
        d['fees_total_m'] = round((c.execute(
            "SELECT COALESCE(SUM(amount),0) FROM fees").fetchone()[0]) / 1e6, 1)
        d['fees_projects'] = c.execute(
            "SELECT COUNT(DISTINCT project_id) FROM fees").fetchone()[0]

        # funding-mechanism empirical layer (thin: restriction/income coverage)
        d['vli_completed_units'] = c.execute("""
            SELECT COALESCE(SUM(ua.unit_count),0)
            FROM unit_program_affordability ua
            JOIN unit_program up ON up.id = ua.unit_program_id
            JOIN project_versions pv ON pv.id = up.project_version_id
            JOIN v_projects_flat f ON f.project_id = pv.project_id AND f.current_version_id = pv.id
            JOIN vocabulary_income_categories ic ON ic.id = ua.income_category_id
            WHERE f.co_issued_date IS NOT NULL AND ic.code = 'VLI'""").fetchone()[0]
        d['density_bonus_units'] = c.execute("""
            SELECT COALESCE(SUM(ua.unit_count),0)
            FROM unit_program_affordability ua
            JOIN vocabulary_restriction_types rt ON rt.id = ua.restriction_type_id
            WHERE rt.code = 'density_bonus'""").fetchone()[0]
    return d, file_sha(V2), file_sha(ASSESSOR)


# ============================================================ BASELINE (external, timestamped)
HARD_KEYS = {
    'completed_projects': 'a CO added/retracted in v2 (new CPRA ingest, merge/retire)',
    'completed_units': 'unit-count correction on a completed project',
    'assessor_matched': 'assessor refresh (re-plats resolve or appear) or APN fix in v2',
    'adu_small_n': 'CO-only cohort ingest/merge, or a valuation newly recorded',
    'adu_small_median_valuation': 'valuation corrections in the CO-only cohort',
    'vli_completed_units': 'affordability rows added/corrected on completed projects',
    'density_bonus_units': 'restriction-type labeling progress',
    'fees_projects': 'fee ingestion progress (Accela harvest)',
}
ROUNDED_KEYS = {
    'tracked_imps_m': 'County reassessment posts (EXPECTED to rise: 1-2yr lag on 2024-26 COs)',
    'adu_small_sum_m': 'valuation corrections',
    'cohort_valuation_sum_m': 'valuation corrections',
    'benchmark_per_unit_k': 'a larger project becomes fully enrolled (benchmark ratchets up)',
    'fees_total_m': 'fee ingestion progress',
}

EXTERNAL_FACTS = {
    'city_share_of_1pct': {
        'value': 0.3257,
        'source': 'City of Berkeley revenue memo (AB-8 share): https://berkeleyca.gov/sites/default/files/legislative-body-meeting-attachments/Item%202%20Revenue%20and%20Transfers%20In%20FY%202021%20vs%20FY%202020%20Comparison.pdf'},
    'allocation_approx': {
        'value': {'city': 0.3257, 'schools_incl_eraf': 0.45, 'county': 0.15, 'special_districts': 0.0743},
        'source': 'City 32.57% exact (above); schools/county/special APPROXIMATE from AB-8 structure, Alameda Auditor-Controller glossary https://auditor.alamedacountyca.gov/tax-glossary/'},
    'ad_valorem_total_rate': {
        'value': 0.0125,
        'source': 'approx total ad-valorem (1% base + voter debt levies ~0.23% city FY26 + school debt); matches v2 v_projects_flat est_annual_tax convention'},
    'city_debt_levy_rate': {
        'value': 0.002323,
        'source': 'FY2026 City of Berkeley voter-approved ad-valorem debt rate 0.2323%, Dec-2-2025 staff report https://berkeleyca.gov/sites/default/files/documents/2025-12-02%20Special%20Item%2002%20Discussion%20Regarding%20Potential%20Ballot.pdf'},
    'gf_revenues_fy27_m': {
        'value': {'property_tax': 103.9, 'transfer_taxes': 34.6, 'business_license': 25.0,
                  'sales_and_soda': 20.5, 'utility_users': 18.75, 'other': 112.15, 'total': 314.9},
        'source': 'PROPOSED FY27 GF revenues, May-14-2026 budget presentation slide 25 https://berkeleyca.gov/sites/default/files/legislative-body-meeting-attachments/5.14.26%20Item2%20FY%2027%20-%20FY%2028%20PROPOSED%20BIENNIAL%20BUDGET%20-%20Presentation.pdf'},
    'gf_spend_fy27_m': {
        'value': {'Police': 101.1, 'Fire': 52.0, 'Non-Departmental': 49.6, 'HHCS': 34.1,
                  'City Manager': 13.9, 'Parks Rec Waterfront': 12.2, 'All other': 51.0, 'total': 313.9},
        'source': 'PROPOSED FY27 GF spend by department, May-14-2026 presentation slide 26 (same URL)'},
    'measure_o': {
        'value': {'bond_m': 135, 'allocated_with_p_m': 238.1, 'units_supported': 1421},
        'source': '2018 Measure O affordable-housing GO bond + Measure P transfer tax; Dec-2-2025 staff report (URL above)'},
}
ESTIMATION_PARAMS = {
    'note': 'assumptions for the full-enrollment estimate — parameters, not measurements',
    'enrolled_at_cost_floor': 'declared permit valuation is the FLOOR of what the assessor enrolls',
    'benchmark_rule': 'max Imps/unit among tracked completed projects >=100 units (least-lagged = most-enrolled; lag only understates)',
}


def newest_baseline():
    files = sorted(glob.glob(BASELINE_GLOB))
    if not files:
        raise FileNotFoundError(f'no baseline matching {BASELINE_GLOB} — run with --write-baseline first')
    return files[-1]


def write_baseline(derived, v2s, ass):
    path = os.path.join(ROOT, 'data', 'baselines', f'fiscal_flows_baseline_{BASELINE_DATE}.json')
    if os.path.exists(path):
        raise FileExistsError(f'{path} exists — baselines are append-only; pick a new date suffix')
    base = {
        'as_of': BASELINE_DATE,
        'v2_sha': v2s, 'assessor_sha': ass,
        'assessor_note': 'berkeley.db = Feb-2026 Alameda Open Data pull (2026-06-16 refresh)',
        'hard_gated': {k: {'value': derived[k], 'what_would_change_it': w} for k, w in HARD_KEYS.items()},
        'rounded_gated': {k: {'value': derived[k], 'what_would_change_it': w} for k, w in ROUNDED_KEYS.items()},
        'derived_context': {'tracked_units': derived['tracked_units'],
                            'tracked_per_year': derived['tracked_per_year'],
                            'benchmark_project_id': derived['benchmark_project_id']},
        'external_facts': EXTERNAL_FACTS,
        'estimation_params': ESTIMATION_PARAMS,
    }
    with open(path, 'w') as f:
        json.dump(base, f, indent=2)
    print(f'[JN-L] baseline WRITTEN: {os.path.relpath(path, ROOT)}')
    return path


def gate(baseline_path=None):
    baseline_path = baseline_path or newest_baseline()
    base = json.load(open(baseline_path))
    derived, v2s, ass = derive()
    print(f"[JN-L gate] baseline: {os.path.relpath(baseline_path, ROOT)}  (as_of {base['as_of']})")
    for label, now, pin in (('v2', v2s, base['v2_sha']), ('assessor', ass, base['assessor_sha'])):
        print(f"[JN-L gate] {label} sha derived={now} baseline={pin}  {'MATCH' if now == pin else 'DRIFT'}")
    failures = []
    for section in ('hard_gated', 'rounded_gated'):
        for key, spec in base[section].items():
            exp, got = spec['value'], derived[key]
            ok = (got == exp)
            print(f"   {key:28} derived={got:<10} baseline={exp:<10} {'OK' if ok else 'FAIL'}")
            if not ok:
                failures.append(
                    f"   *** {key}: DERIVED {got} != BASELINE {exp}\n"
                    f"       likely cause: {spec['what_would_change_it']}\n"
                    f"       legitimate change => append a NEW timestamped baseline (do NOT edit values).")
    if failures:
        raise AssertionError('JN-L GATE HALT — derived != baseline:\n' + '\n'.join(failures))
    print('[JN-L gate] PASS — all gated figures match the baseline.')
    return derived, base


# ============================================================ NOTEBOOK
cells = []
def md(t): cells.append(new_markdown_cell(t.strip('\n')))
def code(s): cells.append(new_code_cell(s.strip('\n')))


def build_notebook():
    cells.clear()
    md("""
# JN-L — Fiscal Flows: what new housing pays the city, and what the city's money flows look like

**The question (John, 2026-08-09):** how much new property tax does a housing CO generate? How much do
ADUs generate? How is the property-tax dollar split between Berkeley, Alameda County, and the State —
and how do the city's revenue streams (property / sales / transfer taxes, developer + in-lieu fees) flow?
And what funds actually built Berkeley's housing projects?

**Every quantitative figure here is DERIVED** from two primary stores and asserted against an external
timestamped baseline (`data/baselines/fiscal_flows_baseline_*.json`):
- `berkeley_housing_v2.db` — the CPRA-derived serving DB (completions, parcels, permits, fees, affordability)
- `berkeley.db` — the Feb-2026 Alameda assessor pull (Land / Imps assessed values)

**External-facts layer.** City budget-document figures (the FY27 GF revenue mix, the 32.57% AB-8 city
share, Measure O) are recorded IN THE BASELINE with provenance URLs and rendered as *context* — we never
derive our numbers from them. CKAN appears nowhere in this notebook.

**Standing caveats (read before trusting any figure):**
1. **Reassessment lag** — the County enrolls new construction 1–2 years after CO; every "enrolled" figure
   for 2024–2026 completions is a KNOWN UNDERSTATEMENT (this is measured in §3, not assumed).
2. **Declared permit valuations understate** — the assessor enrolls market value of new construction;
   declared construction cost is a floor (proj136: declared $50M, enrolled $70.4M).
3. **44 completed projects don't match the assessor** — mostly known re-plat/stale-APN cases
   (the CLAUDE.md standing guard); their value is EXCLUDED, another understatement.
""")

    md("""
## §1 — Setup: read-only connections, sha pins, the assessor lookup
**Where from.** v2 opened read-only; the assessor keyed by Option-B canonical APN
(`book(3)-page(4)-parcel(3)-sub(2)`), condo sub-parcels summed per APN. **Verifiability:** both file
shas are pinned in the baseline — a drifted sha means you are estimating from a different world and the
gate (§10) will say so.
""")
    code("""
import os, sqlite3, json, glob, hashlib, statistics
import pandas as pd
ROOT = os.path.expanduser('~/berkeley-data')
V2 = os.path.join(ROOT, 'databases', 'berkeley_housing_v2.db')
ASSESSOR = os.path.join(ROOT, 'databases', 'berkeley.db')
ADU_LO, ADU_HI = 185, 899   # CO-only import cohort id block (CLAUDE.md structural fact)

def ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)
def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()[:16]

BASE = json.load(open(sorted(glob.glob(os.path.join(ROOT, 'data', 'baselines', 'fiscal_flows_baseline_*.json')))[-1]))
print('baseline as_of:', BASE['as_of'])
for label, path, pin in (('v2', V2, BASE['v2_sha']), ('assessor', ASSESSOR, BASE['assessor_sha'])):
    now = file_sha(path)
    print(f"{label} sha now={now} baseline={pin} {'MATCH' if now == pin else 'DRIFT — figures may differ from baseline'}")

look = {}
with ro(ASSESSOR) as a:
    for book, page, parcel, sub, land, imps, tnv in a.execute(
            'SELECT BOOK, PAGE, PARCEL, SUB_PARCEL, Land, Imps, TotalNetValue FROM parcels'):
        if not book or not page or not parcel: continue
        sub = sub if sub not in (None, '', ' ') else '0'
        key = (str(book).strip().zfill(3) + '-' + str(page).strip().zfill(4) + '-'
               + str(parcel).strip().zfill(3) + '-' + str(sub).strip().zfill(2))
        l, i, t = land or 0, imps or 0, tnv or 0
        if key in look:
            o = look[key]; look[key] = (o[0]+l, o[1]+i, o[2]+t)
        else:
            look[key] = (l, i, t)
print(f'assessor lookup: {len(look):,} canonical APNs')
""")

    md("""
## §2 — The completed-housing universe and its two cohorts
**Assumption + plan.** Everything with a CO in `v_projects_flat` (the verdict-driven completion signal —
NOT `status_code`). Split by the id-block heuristic: ids 185–899 = the CO-only import cohort (mostly
ADU/small infill, ingested from finaled CPRA records); everything else = tracked development projects.
**Why the split matters fiscally:** for a tracked project the parcel's improvements ARE (mostly) the new
building; for an ADU the parcel's improvements are DOMINATED by the pre-existing house that was already
taxed — using parcel Imps for ADUs would massively overstate the new-tax increment.
""")
    code("""
with ro(V2) as c:
    c.row_factory = sqlite3.Row
    rows = c.execute('''
        SELECT f.project_id, f.total_units, f.co_issued_date,
               GROUP_CONCAT(pa.apn_normalized) AS apns
        FROM v_projects_flat f
        LEFT JOIN project_parcels pp ON pp.project_id = f.project_id
        LEFT JOIN parcels pa ON pa.id = pp.parcel_id
        WHERE f.co_issued_date IS NOT NULL
        GROUP BY f.project_id''').fetchall()

completed_projects = len(rows)
completed_units = sum(r['total_units'] or 0 for r in rows)
matched = 0
tracked_imps = 0.0; tracked_units = 0
per_year = {}; bench = []
for r in rows:
    imps = 0.0; hit = False
    for apn in set((r['apns'] or '').split(',')):
        if apn and apn in look:
            imps += look[apn][1]; hit = True
    if hit: matched += 1
    if not (ADU_LO <= r['project_id'] <= ADU_HI):
        u = r['total_units'] or 0
        tracked_imps += imps; tracked_units += u
        yr = r['co_issued_date'][:4]
        per_year.setdefault(yr, [0, 0.0]); per_year[yr][0] += u; per_year[yr][1] += imps
        if u >= 100 and imps > 0: bench.append((imps/u, r['project_id']))
print(f'completed: {completed_projects} projects / {completed_units:,} units (COs 2018–2026)')
print(f'assessor-matched: {matched} of {completed_projects} ({completed_projects-matched} unmatched = re-plat/stale-APN, EXCLUDED)')
print(f'tracked cohort: {tracked_units:,} units; enrolled improvements ${tracked_imps/1e6:.1f}M')
""")
    md("""
**Found + verify.** The unmatched remainder is the standing stale-APN class (e.g. re-platted Acheson) —
excluded, so totals lean conservative. The gate (§10) pins the project/unit/match counts.
""")

    md("""
## §3 — Enrolled value vs. the lag: what the assessor has actually posted
**Assumption + plan.** Sum enrolled improvement value (`Imps`) for tracked projects by CO year, compute
$/unit, and compare against the *benchmark*: the max Imps/unit among large (≥100-unit) completed
projects — the least-lagged large building is the best proxy for what full enrollment looks like
(lag only ever understates; it never overstates).

📝 **What to read from the chart:** enrolled $/unit collapses for recent CO years — that is the
County's reassessment lag made visible, not a collapse in building value.
""")
    code("""
import plotly.graph_objects as go
bench_per_unit, bench_pid = max(bench)
py = pd.DataFrame([(y, v[0], v[1]/1e6, (v[1]/v[0]/1e3 if v[0] else 0)) for y, v in sorted(per_year.items())],
                  columns=['co_year', 'units', 'enrolled_imps_M', 'enrolled_k_per_unit'])
fig = go.Figure()
fig.add_bar(x=py.co_year, y=py.enrolled_k_per_unit, name='enrolled $K/unit (derived)', marker_color='#7ec8e3')
fig.add_scatter(x=py.co_year, y=[bench_per_unit/1e3]*len(py), mode='lines', name=f'benchmark ${bench_per_unit/1e3:.0f}K/unit (proj{bench_pid}, fully enrolled)',
                line=dict(color='#ffd166', dash='dash'))
fig.update_layout(template='plotly_dark', height=380,
                  title='Tracked completions: enrolled assessed $/unit by CO year vs full-enrollment benchmark (derived §3)',
                  yaxis_title='$K per unit')
fig.show()
print(py.to_string(index=False))
print(f'benchmark: proj{bench_pid} at ${bench_per_unit:,.0f}/unit')
""")
    md("""
📝 **What this chart could mislead about.** (1) The benchmark is ONE building — unit mix, parking, and
construction vintage vary; treat it as a central estimate, not a law. (2) Early years (2021–22) sit low
partly from older, cheaper construction and condo-APN linkage gaps — not purely lag. (3) The y-axis is
$/unit, not total value: 2024's bar is small per-unit but 1,258 units wide.
""")

    md("""
## §4 — The ADU increment: declared valuations, not parcel values
**Assumption + plan.** For the CO-only cohort (ids 185–899, ≤2 units, CO'd), the new-tax increment is
the *declared building-permit valuation* (construction cost) — the parcel's Imps would count the main
house that was already taxed. Declared cost is a FLOOR: the assessor enrolls market value of the
addition (proj136 precedent: enrolled 1.4× declared).
""")
    code("""
with ro(V2) as c:
    vals = [v for (v,) in c.execute('''
        SELECT SUM(pe.valuation) FROM v_projects_flat p
        JOIN permits pe ON pe.project_id = p.project_id
        WHERE p.co_issued_date IS NOT NULL AND p.project_id BETWEEN ? AND ?
          AND p.total_units <= 2 AND pe.valuation > 0
        GROUP BY p.project_id''', (ADU_LO, ADU_HI))]
    cohort_val = c.execute('''
        SELECT COALESCE(SUM(pe.valuation),0) FROM v_projects_flat p
        JOIN permits pe ON pe.project_id = p.project_id
        WHERE p.co_issued_date IS NOT NULL AND p.project_id BETWEEN ? AND ?
          AND pe.valuation > 0''', (ADU_LO, ADU_HI)).fetchone()[0]
adu_small_n = len(vals)
adu_small_median = statistics.median(vals)
adu_small_sum = sum(vals)
print(f'ADU/small-infill (<=2u, CO-only cohort, valued): n={adu_small_n}')
print(f'declared valuation: median ${adu_small_median:,.0f}, mean ${adu_small_sum/adu_small_n:,.0f}, sum ${adu_small_sum/1e6:.1f}M')
print(f'whole CO-only cohort (incl. its multi-unit members): ${cohort_val/1e6:.1f}M declared')
""")
    md("""
**Found + verify.** The median declared ADU valuation is the load-bearing per-ADU figure (gated §10).
The cohort id-block heuristic is imperfect — some multi-unit CO-only imports sit in the block — which is
why the ≤2-unit filter defines the ADU subset and the block total is reported separately.
""")

    md("""
## §5 — The tax math: per-unit rules of thumb and the city's slice
**Assumption + plan.** New assessed value × the 1% AB-8 levy × the city's 32.57% share = the General-Fund
increment; the ~0.23% voter-debt levy flows to GO debt-service funds (NOT the GF). Rates and shares come
from the baseline's external-facts layer (with provenance) — the chart/table cells read them, never
literals.
""")
    code("""
ext = BASE['external_facts']
city_share = ext['city_share_of_1pct']['value']
tot_rate  = ext['ad_valorem_total_rate']['value']
mf_av_per_unit = bench_per_unit                       # derived §3
adu_av = adu_small_median                             # derived §4 (declared floor)
rules = pd.DataFrame({
    'new multifamily unit': [mf_av_per_unit, mf_av_per_unit*tot_rate, mf_av_per_unit*0.01*city_share],
    'new ADU (declared floor)': [adu_av, adu_av*tot_rate, adu_av*0.01*city_share]},
    index=['new assessed value ($)', f'total ad-valorem @ {tot_rate:.2%} ($/yr)', 'City GF share ($/yr)'])
print(rules.round(0).to_string())

# Conservative decomposition: multifamily-ish units = all completed units minus the <=2u ADU subset's units.
with ro(V2) as c:
    adu_small_units = c.execute('''SELECT COALESCE(SUM(p.total_units),0) FROM v_projects_flat p
        WHERE p.co_issued_date IS NOT NULL AND p.project_id BETWEEN ? AND ? AND p.total_units <= 2''',
        (ADU_LO, ADU_HI)).fetchone()[0]
mf_units = completed_units - adu_small_units
enrolled_now = tracked_imps + adu_small_sum
full_av = mf_units * mf_av_per_unit + adu_small_sum
print(f'\\nmultifamily-ish units {mf_units:,} × ${mf_av_per_unit/1e3:.0f}K + ADU ${adu_small_sum/1e6:.0f}M declared')
print(f'ENROLLED NOW (floor): ${enrolled_now/1e6:.0f}M → total 1% levy ${enrolled_now*0.01/1e6:.2f}M/yr → City GF ${enrolled_now*0.01*city_share/1e6:.2f}M/yr')
print(f'FULL ENROLLMENT (est): ${full_av/1e9:.2f}B → total 1% levy ${full_av*0.01/1e6:.1f}M/yr → City GF ${full_av*0.01*city_share/1e6:.1f}M/yr')
""")
    md("""
**Found + verify.** Two figures bracket reality: the *enrolled-now floor* (what the County has posted)
and the *full-enrollment estimate* (units × benchmark). The truth converges toward the estimate as the
County works its 1–2-year backlog. **Mislead check:** the estimate multiplies ~3,300 units by ONE
benchmark building's $/unit — a ±15% band is honest; and the ADU term uses declared cost (floor).
""")

    md("""
## §6 — Flow of city revenues (Sankey 1): the FY27 General Fund, external-facts layer
📝 **Before.** This is the *context* diagram — Berkeley's PROPOSED FY27 GF revenue mix flowing into the
GF and out to departments, drawn from the baseline's external-facts (May-14-2026 budget presentation,
provenance in the baseline JSON). Developer fees and in-lieu fees are drawn to their DEDICATED funds —
they never enter the GF, which is exactly why they can't help the $30M operating deficit.
""")
    code("""
rev = ext['gf_revenues_fy27_m']['value']; spend = ext['gf_spend_fy27_m']['value']
labels = ['Property tax (1% share)', 'Transfer taxes', 'Business license', 'Sales + soda tax',
          'Utility users tax', 'Other GF revenue', 'GENERAL FUND',
          'Police', 'Fire', 'Non-Departmental', 'HHCS', 'City Manager', 'Parks Rec Waterfront', 'All other depts',
          'Developer/permit fees', 'In-lieu (inclusionary/HTF) fees', 'Dedicated funds (NOT GF)']
GF = 6
src = [0,1,2,3,4,5, GF,GF,GF,GF,GF,GF,GF, 14,15]
dst = [GF]*6 + [7,8,9,10,11,12,13] + [16,16]
val = [rev['property_tax'], rev['transfer_taxes'], rev['business_license'], rev['sales_and_soda'],
       rev['utility_users'], rev['other'],
       spend['Police'], spend['Fire'], spend['Non-Departmental'], spend['HHCS'],
       spend['City Manager'], spend['Parks Rec Waterfront'], spend['All other'],
       12.9, 3.0]   # fee-stream scale: Accela aggregates (derived, thin) + HTF-order-of-magnitude — see After note
fig = go.Figure(go.Sankey(
    node=dict(label=labels, pad=12, thickness=14,
              color=['#7ec8e3']*6 + ['#ffd166'] + ['#ef8a62']*7 + ['#b3b3ff']*2 + ['#8dd3c7']),
    link=dict(source=src, target=dst, value=val)))
fig.update_layout(template='plotly_dark', height=520,
                  title='Berkeley FY27 General Fund flows ($M, PROPOSED budget — external facts) + fee streams to dedicated funds')
fig.show()
print('GF revenue total $%.1fM / spend total $%.1fM (proposed FY27; source in baseline external_facts)' % (rev['total'], spend['total']))
""")
    md("""
📝 **What this Sankey could mislead about.** (1) These are PROPOSED FY27 figures, not actuals — the
adopted budget differs slightly. (2) The two fee links are drawn at ILLUSTRATIVE scale: our fees table
holds only $12.9M of un-itemized Accela aggregates across 57 projects (derived §8) — Berkeley's actual
annual impact/in-lieu fee flow is NOT materialized in v2, and the link widths must not be read as
measurements. (3) "Non-Departmental" hides debt service, insurance, and transfers — it is not a service.
""")

    md("""
## §7 — Where a new-housing property-tax dollar goes (Sankey 2): the derived increment
📝 **Before.** The §5 full-enrollment estimate flowing through the AB-8 split (city share exact at
32.57%; schools/county/special approximate — flagged in the baseline). The State's box is drawn at ZERO
by construction: property tax never leaves the county; ERAF's school dollars *relieve* the State's
Prop-98 obligation instead.
""")
    code("""
alloc = ext['allocation_approx']['value']
levy = full_av * 0.01 / 1e6          # $M/yr at full enrollment (derived §5)
debt = full_av * ext['city_debt_levy_rate']['value'] / 1e6
mf_share  = (mf_units * mf_av_per_unit) / full_av
labels2 = [f'New multifamily AV (~{mf_units:,}u)', f'New ADU AV ({adu_small_n} ADUs, declared)',
           '1% AB-8 levy', 'City of Berkeley GF (32.57%)', 'Schools + ERAF (~45%)',
           'Alameda County (~15%)', 'Special districts (~7%)', 'Voter debt levies (GO bonds)',
           'State of California ($0 direct)']
src2 = [0, 1, 2, 2, 2, 2, 0, 1]
dst2 = [2, 2, 3, 4, 5, 6, 7, 7]
val2 = [levy*mf_share, levy*(1-mf_share),
        levy*alloc['city'], levy*alloc['schools_incl_eraf'], levy*alloc['county'], levy*alloc['special_districts'],
        debt*mf_share, debt*(1-mf_share)]
fig = go.Figure(go.Sankey(
    node=dict(label=labels2, pad=12, thickness=14,
              color=['#7ec8e3', '#8dd3c7', '#ffd166', '#ef8a62', '#b3b3ff', '#b3b3ff', '#b3b3ff', '#cccccc', '#555555']),
    link=dict(source=src2, target=dst2, value=val2)))
fig.update_layout(template='plotly_dark', height=460,
                  title=f'Annual property tax from housing CO\\'d 2018–2026 at FULL enrollment (est ${levy:.1f}M/yr levy + ${debt:.1f}M/yr debt levies)')
fig.show()
print(f"City GF increment at full enrollment: ${levy*alloc['city']:.1f}M/yr — vs the ~$30M structural deficit")
""")
    md("""
📝 **What this Sankey could mislead about.** (1) DO NOT compare its widths to Sankey 1 visually — this
whole diagram (~$15M/yr) is ≈5% of the GF diagram above; eight years of housing production covers about
one-seventh of one year's deficit. (2) It shows the FULL-ENROLLMENT estimate, not current cash — today's
enrolled floor is roughly a third of it. (3) The schools/county/special split is approximate (baseline
flags it); only the 32.57% city share is document-exact. (4) The State box at $0 is *direct* incidence —
via ERAF the State budget benefits indirectly.
""")

    md("""
## §8 — Sources of funds that BUILT the housing (what v2 can and cannot say)
**Assumption + plan.** Derive the thin-but-real layers: (a) the fee record (Accela aggregates), (b)
affordability restriction/income coverage on completed units (TCAC/HCD/inclusionary/density-bonus are
funding *mechanisms*). Where v2 is silent, record **unknown with provenance** and show the external-facts
layer (Measure O / Measure P) — never fill from an oracle.
""")
    code("""
with ro(V2) as c:
    fee_rows = c.execute('''SELECT COALESCE(vc.code,'unknown'), COUNT(*), COALESCE(SUM(f.amount),0)
        FROM fees f LEFT JOIN vocabulary_fee_categories vc ON vc.id=f.fee_category_id
        GROUP BY vc.code ORDER BY 3 DESC''').fetchall()
    fees_total = sum(r[2] for r in fee_rows)
    fees_projects = c.execute('SELECT COUNT(DISTINCT project_id) FROM fees').fetchone()[0]
    vli = c.execute('''SELECT COALESCE(SUM(ua.unit_count),0)
        FROM unit_program_affordability ua
        JOIN unit_program up ON up.id=ua.unit_program_id
        JOIN project_versions pv ON pv.id=up.project_version_id
        JOIN v_projects_flat f ON f.project_id=pv.project_id AND f.current_version_id=pv.id
        JOIN vocabulary_income_categories ic ON ic.id=ua.income_category_id
        WHERE f.co_issued_date IS NOT NULL AND ic.code='VLI' ''').fetchone()[0]
    db_units = c.execute('''SELECT COALESCE(SUM(ua.unit_count),0)
        FROM unit_program_affordability ua
        JOIN vocabulary_restriction_types rt ON rt.id=ua.restriction_type_id
        WHERE rt.code='density_bonus' ''').fetchone()[0]
print('FEE RECORD (derived — the honest, thin layer):')
for code_, n, amt in fee_rows:
    print(f'   {code_:26} n={n:<5} ${amt:,.0f}')
print(f'   TOTAL ${fees_total/1e6:.1f}M across {fees_projects} projects — Accela "total paid" aggregates;')
print('   itemized impact / Housing-Trust / inclusionary in-lieu fees: NOT MATERIALIZED in v2 (data gap).')
print()
print('FUNDING-MECHANISM RECORD on completed units (derived):')
print(f'   VLI-restricted completed units: {vli}')
print(f'   density-bonus units (all stages): {db_units}')
print('   restriction-type coverage is mostly unlabeled — unknown WITH provenance, never filled from CKAN.')
print()
mo = ext['measure_o']['value']
print('EXTERNAL-FACTS layer (provenance in baseline):')
print(f"   Measure O (2018): ${mo['bond_m']}M GO bond; with Measure P transfer-tax ~${mo['allocated_with_p_m']}M")
print(f"   allocated, supporting {mo['units_supported']:,}+ affordable units (city staff report, Dec 2025).")
print('   Mechanism vocabulary v2 DOES model (restriction types): TCAC/LIHTC, HCD agreement,')
print('   inclusionary condition, density bonus, deed restriction — labeling is the queued work.')
""")
    md("""
**Found + verify.** The deliverable of this section is the *shape of the gap*: Berkeley's affordable
projects are financed by stacked sources (Measure O bond + Measure P transfer tax through the Housing
Trust Fund, LIHTC equity, state HCD programs) — v2 models the *mechanisms* (restriction vocabulary) but
the per-project funding-stack amounts are un-ingested. Filling that (HTF award lists, TCAC allocation
records — both public) is the natural next ingestion, and would turn Sankey 1's illustrative fee links
into measurements.
""")

    md("""
## §9 — Data lineage: how every figure in this JN was produced
```mermaid
flowchart LR
    A[CPRA permit xlsx 2018-2025] --> V2[(berkeley_housing_v2.db)]
    B[Alameda Open Data parcels Feb-2026] --> ASS[(berkeley.db assessor)]
    V2 -->|v_projects_flat COs| S2[§2 cohorts 704 proj / 4,465u]
    ASS -->|Option-B canonical APN join| S2
    S2 --> S3[§3 enrolled Imps + benchmark $/unit]
    V2 -->|permit valuations| S4[§4 ADU declared values]
    S3 --> S5[§5 tax math]
    S4 --> S5
    X[City budget docs = EXTERNAL FACTS w/ provenance] -.-> S6[§6 GF Sankey]
    X -.-> S7[§7 allocation Sankey]
    S5 --> S7
    V2 -->|fees + affordability| S8[§8 funding sources]
    BL[(fiscal_flows_baseline_*.json)] ==>|gate §10| S2
    BL ==> S3
    BL ==> S4
```
Solid arrows = derivation from primary stores. Dotted = external-facts context (never derived-from).
Double arrows = the baseline gate. CKAN does not appear — nothing here touches the oracle.
""")

    md("""
## §10 — THE GATE: derived == external timestamped baseline, or HALT with a diagnosis
**Why.** A notebook that hardcodes its answers has the answer key baked in. Every load-bearing figure
above is re-derived here and asserted against the newest `fiscal_flows_baseline_*.json`. A legitimate
change (County posts reassessments, a new CPRA ingest) re-passes by APPENDING a new timestamped
baseline — never by editing a number. Expected-to-move figures carry their own cause in
`what_would_change_it` (e.g. `tracked_imps_m` is EXPECTED to rise as the lag clears).
""")
    code("""
derived_now = {
    'completed_projects': completed_projects,
    'completed_units': completed_units,
    'assessor_matched': matched,
    'adu_small_n': adu_small_n,
    'adu_small_median_valuation': round(adu_small_median),
    'vli_completed_units': vli,
    'density_bonus_units': db_units,
    'fees_projects': fees_projects,
    'tracked_imps_m': round(tracked_imps/1e6, 1),
    'adu_small_sum_m': round(adu_small_sum/1e6, 1),
    'cohort_valuation_sum_m': round(cohort_val/1e6, 1),
    'benchmark_per_unit_k': round(bench_per_unit/1e3),
    'fees_total_m': round(fees_total/1e6, 1),
}
failures = []
for section in ('hard_gated', 'rounded_gated'):
    for key, spec in BASE[section].items():
        exp, got = spec['value'], derived_now[key]
        ok = (got == exp)
        print(f"   {key:28} derived={got:<10} baseline={exp:<10} {'OK' if ok else 'FAIL'}")
        if not ok:
            failures.append(f"{key}: derived {got} != baseline {exp} — likely: {spec['what_would_change_it']}")
assert not failures, ('JN-L GATE HALT — derived != baseline:\\n' + '\\n'.join(failures)
                      + '\\nLegitimate change => append a NEW timestamped baseline; never edit a value.')
print('\\nJN-L GATE PASS — all gated figures match', BASE['as_of'])
""")

    nb = new_notebook(cells=cells, metadata={
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'}})
    with open(NB_OUT, 'w') as f:
        nbf.write(nb, f)
    print(f'[JN-L] notebook written: {os.path.relpath(NB_OUT, ROOT)}  ({len(cells)} cells)')


# ============================================================ MAIN
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--write-baseline', action='store_true')
    ap.add_argument('--baseline')
    args = ap.parse_args()
    if args.write_baseline:
        derived, v2s, ass = derive()
        write_baseline(derived, v2s, ass)
    gate(args.baseline)
    build_notebook()
