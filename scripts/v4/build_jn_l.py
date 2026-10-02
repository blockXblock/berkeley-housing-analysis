"""Build JN-L_fiscal_flows.ipynb — the fiscal-flows JN: new property tax from housing COs,
city revenue flows (property / sales / transfer taxes, developer + in-lieu fees), and the
sources of funds behind Berkeley housing projects. DERIVED from the canonical v4 database
(databases/berkeley_housing_v4.db, read-only: its serving view v_projects + the assessor values it
carries), gated against an EXTERNAL TIMESTAMPED BASELINE
(data/baselines/fiscal_flows_baseline_*.json, v4-era files tagged "db": "v4") — never hardcoded
constants in the logic.

RE-POINTED FROM v2 ON 2026-10-02. The v2-era baselines (2026-08-10 .. 2026-09-04) describe a
different database: v2's id-block ADU cohort, its v1-era one-number fee table ($14.1M, 57 projects)
and its affordability vocabulary. They are NEVER edited; the generator prints a v2 -> v4 crosswalk
against the newest of them and gates only against a v4-era baseline. Until one is appended (John's
call: --write-baseline), the gate HALTS with the proposal printed.

House pattern (build_jn_e): this generator BOTH (a) derives + gates the hard figures live and
(b) emits the annotated notebook whose cells re-derive everything. Legitimate change = append a
NEW timestamped baseline (EVIDENCE-append-only), never a hand-edit of a magic number.

City-budget figures (FY27 GF revenue mix, department spend, the 32.57% AB-8 city share) are an
EXTERNAL-FACTS layer recorded in the baseline WITH provenance URLs — context we compare against,
never something we derive from primary sources here. CKAN is not involved anywhere in this JN.

Run:
  python scripts/v4/build_jn_l.py                   # derive, gate vs newest v4-era baseline, emit notebook
  python scripts/v4/build_jn_l.py --write-baseline  # legitimate change / first v4 run: append new baseline
  python scripts/v4/build_jn_l.py --baseline PATH   # gate vs a specific baseline
Env (scratch runs): JN_BASELINE_DIR (read/write baselines there), JN_NB_DIR (notebook output dir).
"""
import os, sys, json, glob, sqlite3, argparse, hashlib, statistics, datetime
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = os.path.expanduser('~/berkeley-data')
V4 = os.path.join(ROOT, 'databases', 'berkeley_housing_v4.db')
NB_OUT = os.path.join(os.environ.get('JN_NB_DIR') or os.path.join(ROOT, 'notebooks', 'v4'), 'JN-L_fiscal_flows.ipynb')
LEGACY_DIR = os.path.join(ROOT, 'data', 'baselines')            # the v2-era baselines live here, read-only
BASELINE_DIR = os.environ.get('JN_BASELINE_DIR') or LEGACY_DIR
BASELINE_PATTERN = 'fiscal_flows_baseline_*.json'
BASELINE_DATE = datetime.date.today().isoformat()
# Per-permit fee snapshot (AgencyCounter total_fee), DATED + frozen (append-on-change); produced by
# scripts/harvest_permit_fees.py. Its project_id/units/status_label columns were copied from v2 at
# harvest time and are NOT used here; only permit, address, record_type, description, total_fee.
FEES_SNAPSHOT_GLOB = os.path.join(ROOT, 'data', 'reference', 'permit_fees_*.csv')

# One query, used by the generator AND embedded verbatim in the notebook (no parallel copy).
# imps / n_av = the Alameda assessor values v4 itself carries (assessed_values, ingested from
# databases/berkeley.db:parcels -- see v4 `sources` kind 'assessor' for the checksum and as-of).
COMPLETED_SQL = """
SELECT p.project_id, p.project_key, p.units_built_or_permitted AS units, p.adu_units,
       p.co_issued_date, p.rhna_excluded, p.construction_valuation AS valuation,
       p.fees_paid, p.fees_outstanding, p.planning_fees_paid, p.vli_units,
       (SELECT SUM(a.improvements) FROM project_parcels pp JOIN assessed_values a USING(parcel_id)
         WHERE pp.project_id = p.project_id) AS imps,
       (SELECT COUNT(*) FROM project_parcels pp JOIN assessed_values a USING(parcel_id)
         WHERE pp.project_id = p.project_id) AS n_av
FROM v_projects p WHERE p.co_issued_date IS NOT NULL"""
SMALL_MAX_UNITS = 2      # <=2 units: parcel Imps is dominated by the pre-existing house -> use declared valuation


def ro(p):
    return sqlite3.connect(f'file:{p}?mode=ro', uri=True)


def itemized_fees():
    """Aggregate the newest per-permit fee snapshot (AgencyCounter total_fee) into gated figures.
    A 'new-construction BP' = record_type 'Building Permit' whose description does NOT start
    'Demolition'."""
    import csv as _csv
    paths = sorted(glob.glob(FEES_SNAPSHOT_GLOB))
    if not paths:
        return None
    rows = list(_csv.DictReader(open(paths[-1])))
    def fee(r):
        try:
            return float(r.get('total_fee') or 0)
        except ValueError:
            return 0.0
    fees = [fee(r) for r in rows if fee(r) > 0]
    newbuild = [fee(r) for r in rows if r.get('record_type') == 'Building Permit'
                and not (r.get('description') or '').lstrip().startswith('Demolition')]
    return {
        'itemized_fee_snapshot': os.path.basename(paths[-1]),
        'itemized_fee_permits': len(fees),
        'itemized_fee_addresses': len({(r.get('address') or '').strip().upper() for r in rows if fee(r) > 0}),
        'itemized_fee_total_k': round(sum(fees) / 1e3),
        'itemized_bp_max_k': round(max(newbuild) / 1e3) if newbuild else 0,
    }


def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


def assessor_source(c):
    r = c.execute("""SELECT source_id, source_asof, retrieved_at, substr(checksum,1,16) FROM sources
                     WHERE source_kind = 'assessor' ORDER BY retrieved_at DESC LIMIT 1""").fetchone()
    return dict(source_id=r[0], as_of=r[1], retrieved_at=r[2], checksum16=r[3]) if r else None


def funding_rows(c):
    """The funding ledger v4 carries on projects (notes.funding; ledger rows from Council resolutions,
    CTCAC, HCD awards). One award can be keyed to more than one project -> dedup on funding_id."""
    out = {}
    for key, status, f in c.execute("SELECT project_key, status, funding FROM v_projects WHERE funding IS NOT NULL"):
        for x in json.loads(f):
            fid = x.get('funding_id') or f'{key}:{len(out)}'
            try:
                amt = float(x.get('amount_usd') or 0)
            except ValueError:
                amt = 0.0
            out.setdefault(fid, dict(funder=x.get('funder'), program=x.get('program'), amount=amt,
                                     status=x.get('status'), projects=set()))['projects'].add(key)
    return out


# ============================================================ DERIVATIONS (the live truth)
def derive():
    d = {}
    with ro(V4) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(COMPLETED_SQL).fetchall()
        d['completed_projects'] = len(rows)
        d['completed_units'] = sum(r['units'] or 0 for r in rows)
        d['assessor_matched'] = sum(1 for r in rows if r['n_av'])
        tracked_imps = 0.0; tracked_units = 0; per_year = {}; bench = []; vals = []
        for r in rows:
            u = r['units'] or 0
            if r['rhna_excluded']:
                continue                      # UC / outside city permitting: Regents land, not on the tax roll
            if u <= SMALL_MAX_UNITS:
                if (r['valuation'] or 0) > 0:
                    vals.append(r['valuation'])
                continue
            imps = r['imps'] or 0.0
            tracked_imps += imps; tracked_units += u
            yr = r['co_issued_date'][:4]
            per_year.setdefault(yr, [0, 0.0]); per_year[yr][0] += u; per_year[yr][1] += imps
            if u >= 100 and imps > 0:
                bench.append((imps / u, r['project_key']))
        d['tracked_units'] = tracked_units
        d['tracked_imps_m'] = round(tracked_imps / 1e6, 1)
        d['tracked_per_year'] = {y: [v[0], round(v[1] / 1e6, 1)] for y, v in sorted(per_year.items())}
        best = max(bench) if bench else (0, None)
        d['benchmark_per_unit_k'] = round(best[0] / 1e3)
        d['benchmark_project_key'] = best[1]
        d['adu_small_n'] = len(vals)
        d['adu_small_median_valuation'] = round(statistics.median(vals)) if vals else 0
        d['adu_small_sum_m'] = round(sum(vals) / 1e6, 1)
        d['adu_flag_units_completed'] = sum(r['adu_units'] or 0 for r in rows)

        # the City's own Fees-tab totals (building permits) and Planning-record fees, as of retrieval
        f = c.execute("""SELECT COUNT(fees_paid), COALESCE(SUM(fees_paid),0), COALESCE(SUM(fees_outstanding),0),
                                COUNT(planning_fees_paid), COALESCE(SUM(planning_fees_paid),0) FROM v_projects""").fetchone()
        d['bp_fee_projects'] = f[0]
        d['bp_fees_paid_m'] = round(f[1] / 1e6, 1)
        d['bp_fees_outstanding_k'] = round(f[2] / 1e3)
        d['planning_fee_projects'] = f[3]
        d['planning_fees_paid_m'] = round(f[4] / 1e6, 1)
        d['bp_fees_paid_completed_m'] = round(sum(r['fees_paid'] or 0 for r in rows) / 1e6, 1)

        # funding-mechanism layer
        d['vli_completed_units'] = sum(r['vli_units'] or 0 for r in rows)
        d['density_bonus_projects'] = c.execute(
            "SELECT COUNT(*) FROM v_projects WHERE pathways LIKE '%density_bonus%'").fetchone()[0]
        fr = funding_rows(c)
        d['funding_awards'] = len(fr)
        d['funding_projects'] = len(set().union(*[x['projects'] for x in fr.values()])) if fr else 0
        d['funding_total_m'] = round(sum(x['amount'] for x in fr.values()) / 1e6, 1)
        src = assessor_source(c)

        itf = itemized_fees()
        if itf:
            d.update(itf)
    return d, file_sha(V4), (src or {}).get('checksum16')


# ============================================================ BASELINE (external, timestamped)
HARD_KEYS = {
    'completed_projects': 'a building finaled / a CO ruling in the v4 build (projects stage)',
    'completed_units': 'unit-count ruling or reading ruling on a completed building',
    'assessor_matched': 'assessor re-ingest into v4 (re-plats resolve or appear) or a parcel-link change',
    'adu_small_n': 'a small (<=2u) completion added, or a permit valuation newly recorded',
    'adu_small_median_valuation': 'valuation corrections in the small cohort',
    'adu_flag_units_completed': 'CPRA ADU field on a newly finaled master permit',
    'vli_completed_units': 'affordability evidence added on completed projects',
    'density_bonus_projects': 'pathway evidence added (Planning records)',
    'bp_fee_projects': 'a Fees-tab re-harvest (CapDetail) of master permits',
    'planning_fee_projects': 'a Fees-tab re-harvest of Planning records',
    'funding_awards': 'a funding-ledger row added/keyed',
    'funding_projects': 'a funding-ledger row keyed to a project',
    'itemized_fee_permits': 'a NEW dated permit_fees_*.csv snapshot (re-harvest) -> append a new baseline',
    'itemized_fee_addresses': 'a NEW dated permit_fees_*.csv snapshot (re-harvest) -> append a new baseline',
}
ROUNDED_KEYS = {
    'tracked_imps_m': 'County reassessment posts re-ingested into v4 (EXPECTED to rise: 1-2yr lag)',
    'adu_small_sum_m': 'valuation corrections',
    'benchmark_per_unit_k': 'a larger project becomes fully enrolled (benchmark ratchets up)',
    'bp_fees_paid_m': 'a Fees-tab re-harvest (the totals are as of retrieval and only grow)',
    'bp_fees_outstanding_k': 'a Fees-tab re-harvest (balances paid down / new invoices)',
    'bp_fees_paid_completed_m': 'a Fees-tab re-harvest or a building finaled',
    'planning_fees_paid_m': 'a Planning Fees-tab re-harvest',
    'funding_total_m': 'a funding-ledger amount added/corrected',
    'itemized_fee_total_k': 'a NEW dated permit_fees snapshot (re-harvest) -> append a new baseline',
    'itemized_bp_max_k': 'a larger new-construction BP fee appears in a re-harvest -> append a new baseline',
}
# v2-era key -> v4 key with the SAME question behind it (for the crosswalk only; never gated across)
CROSSWALK = {
    'completed_projects': 'completed_projects', 'completed_units': 'completed_units',
    'assessor_matched': 'assessor_matched', 'adu_small_n': 'adu_small_n',
    'adu_small_median_valuation': 'adu_small_median_valuation', 'vli_completed_units': 'vli_completed_units',
    'density_bonus_units': 'density_bonus_projects', 'fees_projects': 'bp_fee_projects',
    'fees_total_m': 'bp_fees_paid_m', 'tracked_imps_m': 'tracked_imps_m', 'adu_small_sum_m': 'adu_small_sum_m',
    'benchmark_per_unit_k': 'benchmark_per_unit_k', 'itemized_fee_permits': 'itemized_fee_permits',
    'itemized_fee_projects': 'itemized_fee_addresses', 'itemized_fee_total_k': 'itemized_fee_total_k',
    'itemized_bp_max_k': 'itemized_bp_max_k',
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
        'source': 'approx total ad-valorem (1% base + voter debt levies ~0.23% city FY26 + school debt); the same 1.25% v4 v_projects.est_annual_tax_1pct_rule uses'},
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
    'small_cohort_rule': f'completed projects with <= {SMALL_MAX_UNITS} units use declared JobValuation, not parcel Imps (the pre-existing house dominates the parcel)',
}


def _load(p):
    return json.load(open(p))


def newest_baseline(v4_only=True, d=None):
    files = sorted(glob.glob(os.path.join(d or BASELINE_DIR, BASELINE_PATTERN)))
    files = [f for f in files if (_load(f).get('db') == 'v4') == v4_only]
    return files[-1] if files else None


def write_baseline(derived, v4s, ass):
    path = os.path.join(BASELINE_DIR, f'fiscal_flows_baseline_{BASELINE_DATE}_v4.json')
    if os.path.exists(path):
        raise FileExistsError(f'{path} exists — baselines are append-only; pick a new date suffix')
    legacy = newest_baseline(v4_only=False, d=LEGACY_DIR)
    base = {
        'as_of': BASELINE_DATE, 'db': 'v4',
        'v4_sha': v4s, 'assessor_checksum16': ass,
        'supersedes_v2_era': os.path.basename(legacy) if legacy else None,
        'note': ('first v4-era baseline: JN-L re-pointed from v2 to databases/berkeley_housing_v4.db (2026-10-02). '
                 'Fee layer = the City\'s own CapDetail Fees-tab TOTALS per master/phase permit and per Planning '
                 'record, as of retrieval (not itemized); the small cohort = completed projects with <=2 units '
                 '(replaces v2\'s id-block heuristic); assessor values = the snapshot v4 carries.'),
        'hard_gated': {k: {'value': derived[k], 'what_would_change_it': w} for k, w in HARD_KEYS.items() if k in derived},
        'rounded_gated': {k: {'value': derived[k], 'what_would_change_it': w} for k, w in ROUNDED_KEYS.items() if k in derived},
        'derived_context': {'tracked_units': derived['tracked_units'],
                            'tracked_per_year': derived['tracked_per_year'],
                            'benchmark_project_key': derived['benchmark_project_key'],
                            'itemized_fee_snapshot': derived.get('itemized_fee_snapshot')},
        'external_facts': EXTERNAL_FACTS,
        'estimation_params': ESTIMATION_PARAMS,
    }
    with open(path, 'w') as f:
        json.dump(base, f, indent=2)
    print(f'[JN-L] baseline WRITTEN: {path}')
    return path


def crosswalk(derived):
    """v2-era figure -> v4 figure for the same question. INFORMATIONAL: a different database, so a
    difference here is a source change, not drift, and is never gated."""
    legacy = newest_baseline(v4_only=False, d=LEGACY_DIR)
    if not legacy:
        return
    b = _load(legacy)
    old = {k: v['value'] for sec in ('hard_gated', 'rounded_gated') for k, v in b.get(sec, {}).items()}
    print(f'[JN-L crosswalk] v2-era {os.path.basename(legacy)} -> v4 (not a gate):')
    for k2, k4 in CROSSWALK.items():
        print(f'   {k2:28} {old.get(k2)!s:>10}  ->  {k4:28} {derived.get(k4)!s:>10}')


def gate(baseline_path=None):
    derived, v4s, ass = derive()
    crosswalk(derived)
    baseline_path = baseline_path or newest_baseline()
    if not baseline_path:
        print('[JN-L gate] NO v4-era baseline in', BASELINE_DIR, '— derived figures:')
        for k in list(HARD_KEYS) + list(ROUNDED_KEYS):
            print(f'   {k:28} {derived.get(k)}')
        raise AssertionError('JN-L GATE HALT — no v4-era baseline. Review the figures + crosswalk above; '
                             'append one with --write-baseline (John\'s call).')
    base = _load(baseline_path)
    print(f"[JN-L gate] baseline: {baseline_path}  (as_of {base['as_of']})")
    for label, now, pin in (('v4', v4s, base.get('v4_sha')), ('assessor', ass, base.get('assessor_checksum16'))):
        print(f"[JN-L gate] {label} sha derived={now} baseline={pin}  {'MATCH' if now == pin else 'DRIFT'}")
    failures = []
    for section in ('hard_gated', 'rounded_gated'):
        for key, spec in base[section].items():
            exp, got = spec['value'], derived.get(key)
            ok = (got == exp)
            print(f"   {key:28} derived={got!s:<10} baseline={exp!s:<10} {'OK' if ok else 'FAIL'}")
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

**Every quantitative figure here is DERIVED** from the canonical database, opened read-only, and
asserted against an external timestamped baseline (`data/baselines/fiscal_flows_baseline_*_v4.json`):
- `berkeley_housing_v4.db` — the serving view `v_projects` (completions, units, permit valuations, the
  City's own Fees-tab totals, affordability evidence, the funding ledger) and the Alameda assessor values
  v4 carries (`assessed_values`, provenance in its `sources` table).

**Re-pointed from v2 on 2026-10-02.** Earlier runs read `berkeley_housing_v2.db`, whose fee layer was a
single v1-era "total paid" figure for 57 projects ($14.1M). v4 holds **the City's own CapDetail Fees-tab
totals** for every harvested master building permit and for the projects' Planning records — a far
wider layer, but **TOTALS, not itemized**: we can say what was paid on a permit, not what each fee was
for (impact fee vs plan check vs in-lieu). §8 says so where it matters. v2-era baselines are kept
unedited; §10 gates against a v4-era baseline only.

**External-facts layer.** City budget-document figures (the FY27 GF revenue mix, the 32.57% AB-8 city
share, Measure O) are recorded IN THE BASELINE with provenance URLs and rendered as *context* — we never
derive our numbers from them. CKAN appears nowhere in this notebook.

**Standing caveats (read before trusting any figure):**
1. **Reassessment lag** — the County enrolls new construction 1–2 years after CO; every "enrolled" figure
   for 2024–2026 completions is a KNOWN UNDERSTATEMENT (this is measured in §3, not assumed).
2. **Declared permit valuations understate** — the assessor enrolls market value of new construction;
   declared construction cost is a floor.
3. **Completed projects with no assessor row** are counted in §2 and their value EXCLUDED — another
   understatement (re-platted / too-new parcels; the CLAUDE.md standing guard).
""")

    md("""
## §1 — Setup: read-only connection, sha pins, the baseline
**Where from.** v4 opened read-only (`mode=ro`). The assessor values are the snapshot v4 ingested; its
`sources` row carries the as-of date and a content checksum, which the baseline pins alongside the v4
file sha — a drifted pin means you are estimating from a different world and the gate (§10) will say so.
""")
    code("""
import os, sys, sqlite3, json, glob, hashlib, statistics
import pandas as pd
import plotly.io as pio
pio.renderers.default = 'notebook_connected'   # so plotly figures survive nbconvert-to-HTML export
ROOT = os.path.expanduser('~/berkeley-data')
V4 = os.path.join(ROOT, 'databases', 'berkeley_housing_v4.db')
SMALL_MAX_UNITS = """ + str(SMALL_MAX_UNITS) + """   # <=2 units: declared valuation, not parcel Imps (§4)
COMPLETED_SQL = '''""" + COMPLETED_SQL + """'''

def ro(p): return sqlite3.connect(f'file:{p}?mode=ro', uri=True)
def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()[:16]

if not os.path.exists(V4):
    print("=" * 74)
    print("JN-L is an INVESTIGATION notebook: it derives everything live from the")
    print("project's local database, which is not distributed publicly:")
    print("   missing:", V4)
    print()
    print("On Colab/GitHub this notebook is READ-ONLY — reopen the link (without")
    print("running) to see the saved charts and prose.")
    print("For a notebook that RUNS anywhere, start with curriculum module FIN1:")
    print("https://colab.research.google.com/drive/1tc0oJSf4b5Iv2rNkLz3nAIk947W7LUvA")
    print("=" * 74)
    raise SystemExit("JN-L: local database required — stopping cleanly (not an error).")

BL_DIR = os.environ.get('JN_BASELINE_DIR') or os.path.join(ROOT, 'data', 'baselines')
_all = sorted(glob.glob(os.path.join(BL_DIR, 'fiscal_flows_baseline_*.json')))
_v4 = [f for f in _all if json.load(open(f)).get('db') == 'v4']
BASE = json.load(open(_v4[-1])) if _v4 else None
# external facts are the same document-sourced layer in every baseline; read the newest available
EXT_SRC = json.load(open((_v4 or _all)[-1]))
ext = EXT_SRC['external_facts']
con = ro(V4)
src = con.execute('''SELECT source_id, source_asof, retrieved_at, substr(checksum,1,16) FROM sources
                     WHERE source_kind='assessor' ORDER BY retrieved_at DESC LIMIT 1''').fetchone()
v4_now = file_sha(V4)
print('v4-era baseline:', os.path.basename(_v4[-1]) if _v4 else 'NONE YET (§10 will halt)')
if BASE:
    print(f"v4 sha now={v4_now} baseline={BASE['v4_sha']} {'MATCH' if v4_now == BASE['v4_sha'] else 'DRIFT — figures may differ'}")
    print(f"assessor checksum now={src[3]} baseline={BASE['assessor_checksum16']} "
          f"{'MATCH' if src[3] == BASE['assessor_checksum16'] else 'DRIFT'}")
print(f'assessor values in v4: source {src[0]}, as-of {src[1]}, ingested {src[2][:10]}')
""")

    md("""
## §2 — The completed-housing universe and its cohorts
**Assumption + plan.** Every project with a `co_issued_date` in `v_projects` (all of its buildings
finaled — v4's completion signal, built from the buildings' master-permit events). Three cohorts:
**UC / outside city permitting** (`rhna_excluded`: Regents land, off the tax roll — no city property-tax
increment); **small** (≤2 units — ADUs and small infill); **tracked** (≥3 units).
**Why the split matters fiscally:** for a tracked project the parcel's improvements ARE (mostly) the new
building; for an ADU the parcel's improvements are DOMINATED by the pre-existing house that was already
taxed — using parcel Imps for ADUs would massively overstate the new-tax increment.
**Change from v2:** v2 split by an id-block heuristic (ids 185–899 = the CO-only import cohort); v4 has
no such block, so the split is by the units the buildings actually carry.
""")
    code("""
con.row_factory = sqlite3.Row
rows = con.execute(COMPLETED_SQL).fetchall()
completed_projects = len(rows)
completed_units = sum(r['units'] or 0 for r in rows)
matched = sum(1 for r in rows if r['n_av'])
uc = [r for r in rows if r['rhna_excluded']]
small = [r for r in rows if not r['rhna_excluded'] and (r['units'] or 0) <= SMALL_MAX_UNITS]
tracked = [r for r in rows if not r['rhna_excluded'] and (r['units'] or 0) > SMALL_MAX_UNITS]
tracked_imps = 0.0; tracked_units = 0; per_year = {}; bench = []
for r in tracked:
    u = r['units'] or 0; imps = r['imps'] or 0.0
    tracked_imps += imps; tracked_units += u
    yr = r['co_issued_date'][:4]
    per_year.setdefault(yr, [0, 0.0]); per_year[yr][0] += u; per_year[yr][1] += imps
    if u >= 100 and imps > 0: bench.append((imps/u, r['project_key']))
co_years = sorted(r['co_issued_date'][:4] for r in rows)
print(f'completed: {completed_projects} projects / {completed_units:,} units (COs {co_years[0]}–{co_years[-1]})')
print(f'cohorts: UC/outside-city {len(uc)} | small (<={SMALL_MAX_UNITS}u) {len(small)} | tracked (>={SMALL_MAX_UNITS+1}u) {len(tracked)}')
print(f'assessor-linked: {matched} of {completed_projects} ({completed_projects-matched} with no assessor row = re-plat/stale-APN/too-new, EXCLUDED)')
print(f'tracked cohort: {tracked_units:,} units; enrolled improvements ${tracked_imps/1e6:.1f}M')
""")
    md("""
**Found + verify.** The unlinked remainder is the standing stale-APN class — excluded, so totals lean
conservative. The gate (§10) pins the project/unit/link counts. Note that v4 counts projects as
*application-anchored or building-anchored* units of work: a lot with a house and a later ADU on separate
permits can be two completed projects sharing a parcel — the parcel's Imps then count once per project
in the tracked sum only if both are ≥3 units (rare).
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
bench_per_unit, bench_key = max(bench)
py = pd.DataFrame([(y, v[0], v[1]/1e6, (v[1]/v[0]/1e3 if v[0] else 0)) for y, v in sorted(per_year.items())],
                  columns=['co_year', 'units', 'enrolled_imps_M', 'enrolled_k_per_unit'])
fig = go.Figure()
fig.add_bar(x=py.co_year, y=py.enrolled_k_per_unit, name='enrolled $K/unit (derived)', marker_color='#7ec8e3')
fig.add_scatter(x=py.co_year, y=[bench_per_unit/1e3]*len(py), mode='lines',
                name=f'benchmark ${bench_per_unit/1e3:.0f}K/unit ({bench_key}, most enrolled)',
                line=dict(color='#ffd166', dash='dash'))
fig.update_layout(template='plotly_dark', height=380,
                  title='Tracked completions: enrolled assessed $/unit by CO year vs full-enrollment benchmark (derived §3)',
                  yaxis_title='$K per unit')
fig.show()
print(py.to_string(index=False))
print(f'benchmark: {bench_key} at ${bench_per_unit:,.0f}/unit')
_bn = sorted(v for v, _ in bench)
print(f'context (not gated): {len(_bn)} tracked >=100u projects with Imps; median ${statistics.median(_bn):,.0f}/unit, '
      f'max/median {max(_bn)/statistics.median(_bn):.1f}x')
""")
    md("""
📝 **What this chart could mislead about.** (1) The benchmark is ONE building — unit mix, parking, and
construction vintage vary; treat it as a central estimate, not a law. (2) Early years sit low partly from
older, cheaper construction and condo-APN linkage gaps — not purely lag. (3) The y-axis is $/unit, not
total value: read the printed `units` column for each bar's width in homes. (4) **The max-rule is
sensitive to what a "unit" is.** v4 links far more completed projects to their parcels than v2 did, and
the most-enrolled large building is now a student building whose units hold several beds each — a high
$/unit that is real for that building but not typical. The printed median is the robustness check; a
change of rule (median, or $/sq ft) is a methodology decision, not drift (open for John, 2026-10-02).
""")

    md("""
## §4 — The ADU / small-infill increment: declared valuations, not parcel values
**Assumption + plan.** For completed small projects (≤2 units, not UC), the new-tax increment is the
*declared building-permit valuation* (`construction_valuation` = the master permits' CPRA `JobValuation`)
— the parcel's Imps would count the main house that was already taxed. Declared cost is a FLOOR: the
assessor enrolls market value of the addition. Separately, the CPRA permit's own **ADU** field gives the
count of ADU units among all completions.
""")
    code("""
vals = [r['valuation'] for r in small if (r['valuation'] or 0) > 0]
adu_small_n = len(vals)
adu_small_median = statistics.median(vals)
adu_small_sum = sum(vals)
adu_flag_units = sum(r['adu_units'] or 0 for r in rows)
print(f'small (<={SMALL_MAX_UNITS}u) completions with a declared valuation: n={adu_small_n} of {len(small)}')
print(f'declared valuation: median ${adu_small_median:,.0f}, mean ${adu_small_sum/adu_small_n:,.0f}, sum ${adu_small_sum/1e6:.1f}M')
print(f'ADU units among ALL completions (CPRA ADU field on the master permit): {adu_flag_units:,}')
""")
    md("""
**Found + verify.** The median declared small-project valuation is the load-bearing per-ADU figure
(gated §10). A ≤2-unit project is not always an ADU (a new single-family house or duplex qualifies too),
which is why the ADU-field count is printed separately rather than used as the cohort.
""")

    md("""
## §5 — The tax math: per-unit rules of thumb and the city's slice
**Assumption + plan.** New assessed value × the 1% AB-8 levy × the city's 32.57% share = the General-Fund
increment; the ~0.23% voter-debt levy flows to GO debt-service funds (NOT the GF). Rates and shares come
from the baseline's external-facts layer (with provenance) — the cells read them, never literals.
""")
    code("""
city_share = ext['city_share_of_1pct']['value']
tot_rate  = ext['ad_valorem_total_rate']['value']
mf_av_per_unit = bench_per_unit                       # derived §3
adu_av = adu_small_median                             # derived §4 (declared floor)
rules = pd.DataFrame({
    'new multifamily unit': [mf_av_per_unit, mf_av_per_unit*tot_rate, mf_av_per_unit*0.01*city_share],
    'new ADU (declared floor)': [adu_av, adu_av*tot_rate, adu_av*0.01*city_share]},
    index=['new assessed value ($)', f'total ad-valorem @ {tot_rate:.2%} ($/yr)', 'City GF share ($/yr)'])
print(rules.round(0).to_string())

small_units = sum(r['units'] or 0 for r in small)
mf_units = tracked_units
enrolled_now = tracked_imps + adu_small_sum
full_av = mf_units * mf_av_per_unit + adu_small_sum
print(f'\\ntracked units {mf_units:,} × ${mf_av_per_unit/1e3:.0f}K + small-cohort ${adu_small_sum/1e6:.0f}M declared ({small_units:,} units)')
print(f'ENROLLED NOW (floor): ${enrolled_now/1e6:.0f}M → total 1% levy ${enrolled_now*0.01/1e6:.2f}M/yr → City GF ${enrolled_now*0.01*city_share/1e6:.2f}M/yr')
print(f'FULL ENROLLMENT (est): ${full_av/1e9:.2f}B → total 1% levy ${full_av*0.01/1e6:.1f}M/yr → City GF ${full_av*0.01*city_share/1e6:.1f}M/yr')
""")
    md("""
**Found + verify.** Two figures bracket reality: the *enrolled-now floor* (what the County has posted)
and the *full-enrollment estimate* (units × benchmark). The truth converges toward the estimate as the
County works its 1–2-year backlog. **Mislead check:** the estimate multiplies the tracked units by ONE
benchmark building's $/unit — a ±15% band is honest; and the small-cohort term uses declared cost (floor).
""")

    md("""
## §6 — Flow of city revenues (Sankey 1): the FY27 General Fund, external-facts layer
📝 **Before.** This is the *context* diagram — Berkeley's PROPOSED FY27 GF revenue mix flowing into the
GF and out to departments, drawn from the baseline's external-facts (May-14-2026 budget presentation,
provenance in the baseline JSON). Permit fees are drawn to DEDICATED funds — they never enter the GF,
which is exactly why they can't help the $30M operating deficit. The fee link is DERIVED: the average
annual building-permit fees paid on projects whose first BP was issued 2018–2025 (v4 Fees-tab totals).
""")
    code("""
fee_by_bp_year = con.execute('''SELECT substr(bp_issued_date,1,4) y, SUM(fees_paid) FROM v_projects
    WHERE fees_paid IS NOT NULL AND substr(bp_issued_date,1,4) BETWEEN '2018' AND '2025' GROUP BY 1''').fetchall()
bp_fee_per_year_m = sum(v for _, v in fee_by_bp_year) / 8 / 1e6
rev = ext['gf_revenues_fy27_m']['value']; spend = ext['gf_spend_fy27_m']['value']
labels = ['Property tax (1% share)', 'Transfer taxes', 'Business license', 'Sales + soda tax',
          'Utility users tax', 'Other GF revenue', 'GENERAL FUND',
          'Police', 'Fire', 'Non-Departmental', 'HHCS', 'City Manager', 'Parks Rec Waterfront', 'All other depts',
          'Building-permit fees on housing (avg/yr, derived)', 'Dedicated funds (NOT GF)']
GF = 6
src_ = [0,1,2,3,4,5, GF,GF,GF,GF,GF,GF,GF, 14]
dst = [GF]*6 + [7,8,9,10,11,12,13] + [15]
val = [rev['property_tax'], rev['transfer_taxes'], rev['business_license'], rev['sales_and_soda'],
       rev['utility_users'], rev['other'],
       spend['Police'], spend['Fire'], spend['Non-Departmental'], spend['HHCS'],
       spend['City Manager'], spend['Parks Rec Waterfront'], spend['All other'],
       bp_fee_per_year_m]
fig = go.Figure(go.Sankey(
    node=dict(label=labels, pad=12, thickness=14,
              color=['#7ec8e3']*6 + ['#ffd166'] + ['#ef8a62']*7 + ['#b3b3ff'] + ['#8dd3c7']),
    link=dict(source=src_, target=dst, value=val)))
fig.update_layout(template='plotly_dark', height=520,
                  title='Berkeley FY27 General Fund flows ($M, PROPOSED budget — external facts) + housing BP fees to dedicated funds')
fig.show()
print('GF revenue total $%.1fM / spend total $%.1fM (proposed FY27; source in baseline external_facts)' % (rev['total'], spend['total']))
print(f'housing building-permit fees: ${bp_fee_per_year_m:.1f}M/yr average over BP years 2018-2025 (v4 Fees-tab totals)')
print('in-lieu / Housing Trust Fund / inclusionary fees: NOT MEASURED in v4 -- no link drawn (unknown with provenance)')
""")
    md("""
📝 **What this Sankey could mislead about.** (1) These are PROPOSED FY27 figures, not actuals. (2) The fee
link is an 8-year *average* of totals paid as of retrieval, assigned to the project's first-BP year — fees
are paid over a permit's life, so it is a scale, not a cash-flow year. (3) In-lieu / impact fees are
**absent, not zero**: the Fees tab gives totals per permit, not fee types, so we cannot separate an
impact fee from plan-check — the diagram must not be read as "no in-lieu money". (4) "Non-Departmental"
hides debt service, insurance, and transfers — it is not a service.
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
labels2 = [f'New multifamily AV (~{mf_units:,}u)', f'New small/ADU AV ({adu_small_n} projects, declared)',
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
                  title=f'Annual property tax from housing completed {co_years[0][:4]}–{co_years[-1][:4]} at FULL enrollment (est ${levy:.1f}M/yr levy + ${debt:.1f}M/yr debt levies)')
fig.show()
print(f"City GF increment at full enrollment: ${levy*alloc['city']:.1f}M/yr — vs the ~$30M structural deficit")
""")
    md("""
📝 **What this Sankey could mislead about.** (1) DO NOT compare its widths to Sankey 1 visually — this
whole diagram is a small fraction of the GF diagram above. (2) It shows the FULL-ENROLLMENT estimate, not
current cash — today's enrolled floor (§5) is well below it. (3) The schools/county/special split is
approximate (baseline flags it); only the 32.57% city share is document-exact. (4) The State box at $0 is
*direct* incidence — via ERAF the State budget benefits indirectly.
""")

    md("""
## §8 — Fees paid, and the sources of funds that BUILT the housing (what v4 can and cannot say)
**Assumption + plan.** Three layers, each named for what it is:
(a) **building-permit fees** — the City's own CapDetail *Fees tab* total for each master/phase permit
of a project's buildings, summed per project, **as of retrieval** (`fees_paid`, `fees_outstanding`,
`fees_as_of`); (b) **Planning fees** — the same, on the project's Planning records
(`planning_fees_paid`); (c) the **funding ledger** v4 keys to projects (Council resolutions, CTCAC and
HCD awards) and affordability evidence on completed units.
**What this layer is NOT:** itemized. The Fees tab shows totals and the first page of invoices; it does
not tell an impact fee from plan check, and in-lieu / Housing Trust Fund payments that are not invoiced
on a permit are not in it. Where v4 is silent the answer is **unknown with provenance** — never filled
from an oracle.
""")
    code("""
fees_df = pd.read_sql('''SELECT project_key, name, status, units_built_or_permitted units, bp_issued_date,
                                fees_paid, fees_outstanding, fees_as_of, planning_fees_paid FROM v_projects''', con)
by_status = (fees_df.groupby('status')
             .agg(projects_with_bp_fees=('fees_paid', 'count'), bp_fees_paid=('fees_paid', 'sum'),
                  projects_with_planning_fees=('planning_fees_paid', 'count'), planning_fees_paid=('planning_fees_paid', 'sum'))
             .sort_values('bp_fees_paid', ascending=False))
bp_fee_projects = int(fees_df.fees_paid.notna().sum())
bp_fees_paid = float(fees_df.fees_paid.sum())
bp_fees_outstanding = float(fees_df.fees_outstanding.sum())
planning_fee_projects = int(fees_df.planning_fees_paid.notna().sum())
planning_fees_paid = float(fees_df.planning_fees_paid.sum())
bp_fees_paid_completed = sum(r['fees_paid'] or 0 for r in rows)
print('FEE RECORD — the City\\'s own Fees-tab TOTALS (not itemized), as of', fees_df.fees_as_of.max())
print(f'   building permits: ${bp_fees_paid/1e6:.1f}M paid across {bp_fee_projects} projects '
      f'(${bp_fees_outstanding:,.0f} outstanding); completed projects ${bp_fees_paid_completed/1e6:.1f}M')
print(f'   Planning records: ${planning_fees_paid/1e6:.1f}M paid across {planning_fee_projects} projects')
print(by_status.round(0).to_string())
per_unit = fees_df[(fees_df.units >= 5) & fees_df.fees_paid.notna()].assign(per_unit=lambda d: d.fees_paid / d.units)
print(f'\\n   BP fees per unit, 5+ unit projects with fees (n={len(per_unit)}): median ${per_unit.per_unit.median():,.0f}, '
      f'IQR ${per_unit.per_unit.quantile(.25):,.0f}–${per_unit.per_unit.quantile(.75):,.0f}')
print('   largest:')
for _, r in fees_df.sort_values('fees_paid', ascending=False).head(8).iterrows():
    print(f"     {r.project_key:14} {str(r['name'])[:34]:34} {int(r.units or 0):>4}u  ${r.fees_paid:>12,.0f}")

vli = sum(r['vli_units'] or 0 for r in rows)
db_projects = con.execute("SELECT COUNT(*) FROM v_projects WHERE pathways LIKE '%density_bonus%'").fetchone()[0]
awards = {}
for key, status, f in con.execute('SELECT project_key, status, funding FROM v_projects WHERE funding IS NOT NULL'):
    for x in json.loads(f):
        fid = x.get('funding_id') or f'{key}:{len(awards)}'
        try: amt = float(x.get('amount_usd') or 0)
        except ValueError: amt = 0.0
        awards.setdefault(fid, dict(funder=x.get('funder'), program=x.get('program'), amount=amt, projects=set()))['projects'].add(key)
funding_projects = len(set().union(*[a['projects'] for a in awards.values()])) if awards else 0
funding_total = sum(a['amount'] for a in awards.values())
print('\\nFUNDING LEDGER keyed to projects (deduplicated on funding_id):')
fund = (pd.DataFrame([dict(funder=a['funder'], amount=a['amount']) for a in awards.values()])
        .groupby('funder').amount.agg(['count', 'sum']).sort_values('sum', ascending=False))
for k, r in fund.iterrows():
    print(f"   {k[:60]:60} {int(r['count']):>3} awards  ${r['sum']:>14,.0f}")
print(f'   TOTAL ${funding_total/1e6:.1f}M across {len(awards)} awards on {funding_projects} projects')
print()
print('AFFORDABILITY / MECHANISM evidence:')
print(f'   VLI units on completed projects (affordability evidence): {vli}')
print(f'   projects using the State Density Bonus (pathways, all stages): {db_projects}')
mo = ext['measure_o']['value']
print('\\nEXTERNAL-FACTS layer (provenance in baseline):')
print(f"   Measure O (2018): ${mo['bond_m']}M GO bond; with Measure P transfer-tax ~${mo['allocated_with_p_m']}M")
print(f"   allocated, supporting {mo['units_supported']:,}+ affordable units (city staff report, Dec 2025).")
""")
    md("""
**Found + verify.** The fee layer is now City-recorded rather than v1-era: Fees-tab totals on hundreds of
projects instead of one number on 57. Two cautions travel with it: totals are **as of retrieval** (a
permit still open will keep accruing), and they are **not itemized** — "paid" mixes plan-check,
permit, and any impact fees invoiced on that permit. The funding ledger covers the subsidized projects
the City and State document (Measure O / Housing Trust Fund, LIHTC, AHSC, NPLH); market-rate equity and
construction debt are not public records, so the stack is complete only for the affordable projects.
**Publishing rule:** funders printed here are public agencies and programs; no private individual is named.
""")

    md("""
## §8b — The per-permit fee snapshot (AgencyCounter `total_fee`)
**Assumption + plan.** A **dated, frozen AgencyCounter snapshot** (`data/reference/permit_fees_*.csv`,
harvested by `scripts/harvest_permit_fees.py`) carries `total_fee` PER PERMIT, including permits that are
still *under review* — fees assessed before issuance, which §8's Fees-tab totals (issued master permits)
do not yet hold. **What to read:** the fiscal engine is the **new-construction Building Permit fee**, and
it scales with project size. The big BP fee is charged around issuance, so the large-project
**application collapse (JN-J §4b) is a leading indicator of a coming decline in this fee stream**.
The snapshot's own `project_id`/`units`/`status_label` columns were copied from v2 at harvest time and
are not used here.
""")
    code("""
snap = sorted(glob.glob(os.path.join(ROOT, 'data', 'reference', 'permit_fees_*.csv')))[-1]
fees = pd.read_csv(snap)
fees = fees[fees.total_fee > 0].copy()

def fee_class(r):
    d = str(r.description or '').lstrip()
    if r.record_type == 'Building Permit' and not d.startswith('Demolition'):
        return 'New-construction BP'
    if d.startswith('Demolition') or 'Demolition' in str(r.record_type):
        return 'Demolition'
    return 'Other (mech/elec/plumb/misc)'
fees['klass'] = fees.apply(fee_class, axis=1)

by_class = fees.groupby('klass').total_fee.agg(['count', 'sum']).sort_values('sum', ascending=False)
nb_sum = float(fees.loc[fees.klass == 'New-construction BP', 'total_fee'].sum())
print(f'PER-PERMIT FEE SNAPSHOT  <-  {os.path.basename(snap)}  (frozen, gated in §10)')
print(f'  {len(fees)} fee-bearing permits at {fees.address.str.strip().str.upper().nunique()} addresses  |  total ${fees.total_fee.sum():,.0f}')
print(f'  new-construction BP fees carry ${nb_sum:,.0f} = {nb_sum/fees.total_fee.sum()*100:.0f}% of the snapshot total')
print()
for k, r in by_class.iterrows():
    print(f'   {k:34} {int(r["count"]):>3} permits   ${r["sum"]:>12,.0f}')

COLOR = {'New-construction BP': '#b5371f', 'Demolition': '#c9975a', 'Other (mech/elec/plumb/misc)': '#9aa0a6'}
top = fees.sort_values('total_fee', ascending=False).head(15).iloc[::-1]
label = [f"{a[:20]} · {p}" for a, p in zip(top.address, top.permit)]
fig = go.Figure(go.Bar(
    x=top.total_fee, y=label, orientation='h',
    marker_color=[COLOR[k] for k in top.klass],
    text=[f'${v/1e3:.0f}K' for v in top.total_fee], textposition='outside',
    customdata=top[['klass', 'permit_status']].values,
    hovertemplate='%{y}<br>$%{x:,.0f}<br>%{customdata[0]} · %{customdata[1]}<extra></extra>'))
fig.update_layout(
    title=f'Per-permit city fees — top 15 charges  ({os.path.basename(snap)})',
    xaxis_title='total fee charged ($)', height=520,
    margin=dict(l=8, r=60, t=54, b=40), plot_bgcolor='white',
    annotations=[dict(x=0.98, y=0.06, xref='paper', yref='paper', showarrow=False, align='right',
                      font=dict(size=11, color='#6b6b6b'),
                      text='red = new-construction BP (scales with size) · tan = demolition · grey = other trades')])
fig.show()
""")
    md("""
📝 **What this snapshot could mislead about.** (1) **`total_fee` is populated on only a MINORITY of
AgencyCounter records** — mostly active/recent permits — so it is a slice, **complementary to** §8's
Fees-tab totals and **not to be summed with them** (an issued permit can appear in both). (2) These are
amounts **charged on the permit record, not a cash-flow ledger**. (3) The chart is **truncated to the top
15**. (4) **No party names** — this layer carries no payer identity; the payer → city network needs the
CapDetail contacts v4 holds (`v_project_people`), names as the records give them.
(5) The snapshot is **dated and frozen**; a re-harvest writes a NEW dated file and appends a NEW baseline.
""")

    md("""
## §9 — Data lineage: how every figure in this JN was produced
```mermaid
flowchart LR
    A[CPRA permit productions 2026-07-07] --> V4[(berkeley_housing_v4.db)]
    C[Accela CapDetail Fees tab\\nmaster permits + Planning records] --> V4
    B[Alameda assessor parcels\\nvia databases/berkeley.db] --> V4
    L[funding ledger\\nCouncil / CTCAC / HCD awards] --> V4
    V4 -->|v_projects completions| S2[§2 cohorts]
    V4 -->|assessed_values via project_parcels| S2
    S2 --> S3[§3 enrolled Imps + benchmark $/unit]
    V4 -->|construction_valuation| S4[§4 small-cohort declared values]
    S3 --> S5[§5 tax math]
    S4 --> S5
    X[City budget docs = EXTERNAL FACTS w/ provenance] -.-> S6[§6 GF Sankey]
    V4 -->|fees_paid by first-BP year| S6
    X -.-> S7[§7 allocation Sankey]
    S5 --> S7
    V4 -->|fees + funding + affordability| S8[§8 fees + funding sources]
    FEE[permit_fees_*.csv AgencyCounter snapshot] --> S8B[§8b per-permit fees]
    BL[(fiscal_flows_baseline_*_v4.json)] ==>|gate §10| S2
    BL ==> S8
    BL ==> S8B
    BL ==> S3
    BL ==> S4
```
Solid arrows = derivation from primary stores. Dotted = external-facts context (never derived-from).
Double arrows = the baseline gate. CKAN does not appear — nothing here touches the oracle.
""")

    md("""
## §10 — THE GATE: derived == external timestamped baseline, or HALT with a diagnosis
**Why.** A notebook that hardcodes its answers has the answer key baked in. Every load-bearing figure
above is re-derived here and asserted against the newest **v4-era** `fiscal_flows_baseline_*.json`. A
legitimate change (County posts reassessments, a Fees-tab re-harvest, a new ruling) re-passes by
APPENDING a new timestamped baseline — never by editing a number. The v2-era baselines are a different
database and are never compared here; the generator prints the v2 → v4 crosswalk.
""")
    code("""
derived_now = {
    'completed_projects': completed_projects,
    'completed_units': completed_units,
    'assessor_matched': matched,
    'adu_small_n': adu_small_n,
    'adu_small_median_valuation': round(adu_small_median),
    'adu_flag_units_completed': adu_flag_units,
    'vli_completed_units': vli,
    'density_bonus_projects': db_projects,
    'bp_fee_projects': bp_fee_projects,
    'planning_fee_projects': planning_fee_projects,
    'funding_awards': len(awards),
    'funding_projects': funding_projects,
    'tracked_imps_m': round(tracked_imps/1e6, 1),
    'adu_small_sum_m': round(adu_small_sum/1e6, 1),
    'benchmark_per_unit_k': round(bench_per_unit/1e3),
    'bp_fees_paid_m': round(bp_fees_paid/1e6, 1),
    'bp_fees_outstanding_k': round(bp_fees_outstanding/1e3),
    'bp_fees_paid_completed_m': round(bp_fees_paid_completed/1e6, 1),
    'planning_fees_paid_m': round(planning_fees_paid/1e6, 1),
    'funding_total_m': round(funding_total/1e6, 1),
    'itemized_fee_permits': int((fees.total_fee > 0).sum()),
    'itemized_fee_addresses': int(fees.address.str.strip().str.upper().nunique()),
    'itemized_fee_total_k': round(float(fees.total_fee.sum())/1e3),
    'itemized_bp_max_k': round(float(fees.loc[fees.klass == 'New-construction BP', 'total_fee'].max())/1e3),
}
assert BASE is not None, ('JN-L GATE HALT — no v4-era fiscal_flows baseline in ' + BL_DIR +
                          '. Review the figures above; append one with build_jn_l.py --write-baseline (John\\'s call).')
failures = []
for section in ('hard_gated', 'rounded_gated'):
    for key, spec in BASE[section].items():
        exp, got = spec['value'], derived_now.get(key)
        ok = (got == exp)
        print(f"   {key:28} derived={got!s:<10} baseline={exp!s:<10} {'OK' if ok else 'FAIL'}")
        if not ok:
            failures.append(f"{key}: derived {got} != baseline {exp} — likely: {spec['what_would_change_it']}")
assert not failures, ('JN-L GATE HALT — derived != baseline:\\n' + '\\n'.join(failures)
                      + '\\nLegitimate change => append a NEW timestamped baseline; never edit a value.')
print('\\nJN-L GATE PASS — all gated figures match', BASE['as_of'], '(v4-era)')
""")

    nb = new_notebook(cells=cells, metadata={
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'}})
    os.makedirs(os.path.dirname(NB_OUT), exist_ok=True)
    with open(NB_OUT, 'w') as f:
        nbf.write(nb, f)
    print(f'[JN-L] notebook written: {NB_OUT}  ({len(cells)} cells)')


# ============================================================ MAIN
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--write-baseline', action='store_true')
    ap.add_argument('--baseline')
    args = ap.parse_args()
    if args.write_baseline:
        derived, v4s, ass = derive()
        write_baseline(derived, v4s, ass)
    gate(args.baseline)
    build_notebook()
