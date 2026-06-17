#!/usr/bin/env python3
"""
apr_hcd.py — reproduce the HCD APR permit-derived tables (A / A2 / B) to the OFFICIAL
HCD column schema, from a v2 database. The Q1 deliverable + the Q2 test harness.

HARNESS CONTRACT: the ONLY input is a v2 db path (+ a per-city config). Reads v2 +
housing_rules ONLY — never berkeley.db, never the CKAN mirror (the mirror is the
COLUMN-SCHEMA target, validated against, never a data source). Run it on canonical-v2
or a Q2-rebuilt-v2 for a comparable APR.

A2 is the core: the HCD "Annual Building Activity" matrix — per project, the income-tier
(Acutely-low → Above-mod) x DR/NDR (deed-restricted / non) x milestone (Entitlement / BP /
CO) cells, populated for the milestone(s) the project reached in the report year.

HONEST DATA STATE (measured 2026-06-16, surfaced not hidden):
  - DR/NDR restriction detail covers 0% of completions (the ~1,416 restriction-detailed
    units are on pipeline projects) -> completion affordable units default to NDR, flagged
    "restriction detail absent in v2" (the unknown-with-provenance rule).
  - income-tier coverage ~36% of completed units; the rest are total_units-only (the CO-only
    ADU cohort) -> uncategorized units default to ABOVE_MOD, flagged.
  - ACUTELY_LOW: v2 has ELI (extremely-low), not the 2025+ acutely-low sub-tier -> 0/blank.
  - FIN_ASSIST_NAME + some demo detail: absent in v2 -> blank-with-provenance.
The STRUCTURE matches HCD exactly; the cells carry what v2 actually knows.
"""
import sqlite3, argparse, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from housing_rules import to_canonical_apn  # noqa (kept for harness symmetry / future PRIOR_APN normalize)

STUB_CO_DATE = '2024-01-01'

# ---- per-CITY config (NOT hardcoded into the form — the form/columns are statewide) ----
BERKELEY = {
    'JURIS_NAME': 'Berkeley', 'CNTY_NAME': 'Alameda', 'assessing_county': 'Alameda',
    'rhna': {'very_low': 1786, 'low': 1028, 'moderate': 1452, 'above_moderate': 4668, 'total': 8934},
    'cycle6_projection_start': '2022-06-30',   # first-BP >= this = 6th-cycle credit
}
# OAKLAND = {... same form, different rhna allocations + names ...}  # the per-city swap

# v2 income tier -> HCD tier key. (ACUTELY_LOW has no v2 source -> always 0.)
TIER_MAP = [('eli_units', 'EXTREMELY_LOW'), ('vli_units', 'VLOW'),
            ('li_units', 'LOW'), ('mod_units', 'MOD')]   # ABOVE_MOD handled separately (market_units + uncategorized)
HCD_TIERS = ['ACUTELY_LOW', 'EXTREMELY_LOW', 'VLOW', 'LOW', 'MOD']   # DR/NDR each; ABOVE_MOD single


def _year(d):
    return d[:4] if d and len(d) >= 4 and d > '2000' and d != STUB_CO_DATE else None


def _project_dr_split(conn, pid):
    """restriction detail per (tier, DR/NDR) from unit_program_affordability, where present.
    Returns {tier: {'DR': n, 'NDR': n}} or {} if the project has no restriction detail."""
    rows = conn.execute("""
        SELECT ic.code AS tier, rt.code AS restr, SUM(upa.unit_count) AS u
        FROM unit_program_affordability upa
        JOIN unit_program up ON up.id = upa.unit_program_id
        JOIN project_versions pv ON pv.id = up.project_version_id
        JOIN vocabulary_income_categories ic ON ic.id = upa.income_category_id
        JOIN vocabulary_restriction_types rt ON rt.id = upa.restriction_type_id
        WHERE pv.project_id = ? AND pv.is_current = 1
        GROUP BY ic.code, rt.code""", (pid,)).fetchall()
    out = {}
    for tier, restr, u in rows:
        dr = 'NDR' if restr == 'none' else 'DR'
        key = {'ELI': 'EXTREMELY_LOW', 'VLI': 'VLOW', 'LI': 'LOW', 'MOD': 'MOD',
               'ABOVE_MOD': 'ABOVE_MOD'}.get(tier, tier)
        out.setdefault(key, {'DR': 0, 'NDR': 0})[dr] += (u or 0)
    return out


def _affordability_cells(conn, row):
    """Per-project tier x DR/NDR. Tier counts from v_projects_flat (the fuller signal);
    DR/NDR from restriction detail where present, else affordable->NDR (flagged). Uncategorized
    (total - sum tiers) -> ABOVE_MOD. Returns ({tier: {'DR','NDR'}}, above_mod_int, prov_flags)."""
    detail = _project_dr_split(conn, row['project_id'])
    cells = {t: {'DR': 0, 'NDR': 0} for t in HCD_TIERS}
    flags = []
    tier_sum = 0
    for col, hcd in TIER_MAP:
        n = row[col] or 0
        tier_sum += n
        if n == 0:
            continue
        if hcd in detail and (detail[hcd]['DR'] + detail[hcd]['NDR']) > 0:
            cells[hcd] = detail[hcd]
        else:
            cells[hcd]['NDR'] = n          # no restriction detail -> NDR, flagged
            flags.append(f'{hcd}:NDR-default(no restriction detail)')
    above = row['market_units'] or 0
    uncategorized = (row['total_units'] or 0) - tier_sum - above
    if uncategorized > 0:
        above += uncategorized
        flags.append(f'ABOVE_MOD+{uncategorized}(uncategorized total_units)')
    return cells, above, flags


def _apn_and_prior(conn, pid):
    """(current APN, prior APN) for a project's primary parcel. SCHEMA-TOLERANT (the harness runs on
    any v2): current APN prefers the stored apn_normalized (B form), else canonicalizes parcels.apn;
    prior APN from parcel_lineage if that table exists, else None. So a pre-parcel-identity-MVP v2
    still produces the APR (PRIOR_APN blank) — only the MVP columns degrade, not the whole table."""
    p = conn.execute("""SELECT pk.id, pk.apn FROM project_parcels pp JOIN parcels pk ON pk.id=pp.parcel_id
                        WHERE pp.project_id=? AND pp.is_primary=1 LIMIT 1""", (pid,)).fetchone()
    if not p:
        return None, None
    parcel_id, raw = p[0], p[1]
    try:
        row = conn.execute("SELECT apn_normalized FROM parcels WHERE id=?", (parcel_id,)).fetchone()
        cur = row[0] if (row and row[0]) else to_canonical_apn(raw, 'Alameda')
    except sqlite3.OperationalError:
        cur = to_canonical_apn(raw, 'Alameda')
    try:
        pr = conn.execute("""SELECT parent_apn_raw FROM parcel_lineage
            WHERE child_parcel_id=? AND status IN ('candidate','confirmed') LIMIT 1""", (parcel_id,)).fetchone()
        prior = pr[0] if pr else None
    except sqlite3.OperationalError:
        prior = None
    return cur, prior


# HCD's OWN column names are inconsistent: the EXTREMELY_LOW NDR variant drops "LOW"
# (EXTREMELY_INCOME_NDR) while the DR variant keeps it (EXTREMELY_LOW_INCOME_DR). Match verbatim.
_NDR_NAME = {'EXTREMELY_LOW': 'EXTREMELY_INCOME_NDR'}


def _milestone_block(prefix, cells, above, present):
    """Emit the HCD milestone columns for one milestone (ENT/BP/CO). present=False -> all 0."""
    out = {}
    for t in HCD_TIERS:
        out[f'{prefix}{t}_INCOME_DR'] = cells[t]['DR'] if present else 0
        out[f'{prefix}{_NDR_NAME.get(t, t + "_INCOME_NDR")}'] = cells[t]['NDR'] if present else 0
    out[f'{prefix}ABOVE_MOD_INCOME'] = above if present else 0
    return out


def build_table_a2(conn, year, cfg):
    """HCD Table A2 (Annual Building Activity) — the matrix, per project, for `year`."""
    y = str(year)
    rows = conn.execute(f"""
        SELECT project_id, name, address_display, address_normalized, latitude, longitude,
               total_units, market_units, eli_units, vli_units, li_units, mod_units,
               entitled_date, bp_issued_date, co_issued_date
        FROM v_projects_flat
        WHERE (substr(entitled_date,1,4)=? OR substr(bp_issued_date,1,4)=?
               OR (substr(co_issued_date,1,4)=? AND co_issued_date<>'{STUB_CO_DATE}'))
          AND project_id NOT IN (SELECT pc.project_id FROM project_classifications pc
              JOIN vocabulary_classification_types vct ON vct.id=pc.classification_type_id WHERE vct.code='uc_project')
        ORDER BY project_id""", (y, y, y)).fetchall()
    out = []
    prov = []
    for r in rows:
        cells, above, flags = _affordability_cells(conn, r)
        ent = _year(r['entitled_date']) == y
        bp = _year(r['bp_issued_date']) == y
        co = _year(r['co_issued_date']) == y
        cur_apn, prior = _apn_and_prior(conn, r['project_id'])
        rec = {
            'JURIS_NAME': cfg['JURIS_NAME'], 'CNTY_NAME': cfg['CNTY_NAME'], 'YEAR': year,
            'PRIOR_APN': prior, 'APN': cur_apn,
            'STREET_ADDRESS': r['address_display'], 'PROJECT_NAME': r['name'],
            'JURS_TRACKING_ID': f"proj{r['project_id']}", 'UNIT_CAT': None, 'TENURE': None,
        }
        rec.update(_milestone_block('', cells, above, ent))                 # entitlement block
        rec['ENT_APPROVE_DT1'] = r['entitled_date'] if ent else None
        rec['NO_ENTITLEMENTS'] = 0 if ent else 1
        rec.update(_milestone_block('BP_', cells, above, bp))               # building-permit block
        rec['BP_ISSUE_DT1'] = r['bp_issued_date'] if bp else None
        rec['NO_BUILDING_PERMITS'] = 0 if bp else 1
        rec.update(_milestone_block('CO_', cells, above, co))               # certificate-of-occupancy block
        rec['CO_ISSUE_DT1'] = r['co_issued_date'] if co else None
        # program sub-fields: derive where v2 has it, else blank-with-provenance
        rec['NO_OTHER_FORMS_OF_READINESS'] = 0 if co else 1
        rec['EXTR_LOW_INCOME_UNITS'] = r['eli_units'] or 0
        rec['APPROVE_SB35'] = 'Y' if conn.execute("SELECT 1 FROM project_classifications pc JOIN vocabulary_classification_types v ON v.id=pc.classification_type_id WHERE pc.project_id=? AND v.code IN ('sb35_eligible','sb35_approved') LIMIT 1", (r['project_id'],)).fetchone() else 'N'
        rec['HISTORIC_SITES'] = None       # blank-with-provenance (not tracked in v2)
        rec['INFILL_UNITS'] = None         # blank-with-provenance
        rec['FIN_ASSIST_NAME'] = None      # blank-with-provenance (financial-assistance program not in v2)
        rec['DR_TYPE'] = None              # blank-with-provenance (restriction type detail absent for completions)
        rec['NO_FA_DR'] = None             # blank-with-provenance
        rec['TERM_AFF_DR'] = None          # blank-with-provenance (restriction_term_years 0% on completions)
        rec['DEM_DES_UNITS'] = None        # blank-with-provenance (demo unit detail not modelled)
        rec['DEM_OR_DES_UNITS'] = None
        rec['DEM_DES_UNITS_OWN_RENT'] = None
        rec['DENSITY_BONUS_TOTAL'] = None  # blank-with-provenance (density-bonus DETAIL not in v2; only the flag)
        rec['DENSITY_BONUS_NUMBER_OTHER_INCENTIVES'] = None
        rec['DENSITY_BONUS_INCENTIVES'] = None
        rec['DENSITY_BONUS_RECEIVE_REDUCTION'] = None
        rec['NOTES'] = '; '.join(flags) if flags else None   # provenance flags surface here
        rec['LATITUDE'] = r['latitude']
        rec['LONGITUDE'] = r['longitude']
        rec['STD_ADDRESS'] = r['address_normalized']
        rec['SCORE'] = None                # HCD internal scoring (not ours to produce)
        out.append(rec)
        if flags:
            prov.append({'project_id': r['project_id'], 'flags': flags})
    return out, prov


def build_table_a(conn, year, cfg):
    """HCD Table A (entitlements/applications) — application+entitlement matrix subset."""
    y = str(year)
    rows = conn.execute("""
        SELECT project_id, name, address_display, total_units, market_units,
               eli_units, vli_units, li_units, mod_units, filed_date, entitled_date
        FROM v_projects_flat
        WHERE (substr(filed_date,1,4)=? OR substr(entitled_date,1,4)=?)
          AND project_id NOT IN (SELECT pc.project_id FROM project_classifications pc
              JOIN vocabulary_classification_types vct ON vct.id=pc.classification_type_id WHERE vct.code='uc_project')
        ORDER BY project_id""", (y, y)).fetchall()
    out = []
    for r in rows:
        cells, above, _ = _affordability_cells(conn, r)
        cur_apn, prior = _apn_and_prior(conn, r['project_id'])
        rec = {'JURIS_NAME': cfg['JURIS_NAME'], 'CNTY_NAME': cfg['CNTY_NAME'], 'YEAR': year,
               'PRIOR_APN': prior, 'APN': cur_apn, 'STREET_ADDRESS': r['address_display'],
               'PROJECT_NAME': r['name'], 'JURS_TRACKING_ID': f"proj{r['project_id']}",
               'UNIT_CAT': None, 'TENURE': None, 'APP_SUBMIT_DT': r['filed_date']}
        rec.update(_milestone_block('', cells, above, True))
        rec['TOT_APPROVED_UNITS'] = r['total_units'] if _year(r['entitled_date']) == y else 0
        rec['TOT_PROPOSED_UNITS'] = r['total_units']
        out.append(rec)
    return out


def build_table_b(conn, cfg):
    """HCD Table B (RHNA progress) — the derived cumulative summary vs the per-city allocation."""
    uc = """project_id NOT IN (SELECT pc.project_id FROM project_classifications pc
            JOIN vocabulary_classification_types vct ON vct.id=pc.classification_type_id WHERE vct.code='uc_project')"""
    # all-time CO units by tier (the completion side of RHNA progress)
    co = conn.execute(f"""SELECT SUM(eli_units+vli_units), SUM(li_units), SUM(mod_units),
        SUM(market_units), SUM(total_units) FROM v_projects_flat
        WHERE co_issued_date>'' AND co_issued_date<>'{STUB_CO_DATE}' AND {uc}""").fetchone()
    alloc = cfg['rhna']
    return {
        'allocation': alloc,
        'completed_by_tier': {'very_low': co[0] or 0, 'low': co[1] or 0, 'moderate': co[2] or 0,
                              'above_moderate': co[3] or 0, 'total_co_units': co[4] or 0},
        'note': 'Table B is HCD-derived (RHNA progress summary), not a raw CKAN table. Completion '
                'side shown; RHNA CREDIT is first-BP >= projection-start (see cumulative_block).',
    }


def cumulative_block(conn, cfg):
    """The headline metrics: 703/702 completions, net-new-CO tiles, all-time CO, RHNA first-BP credit."""
    uc = """project_id NOT IN (SELECT pc.project_id FROM project_classifications pc
            JOIN vocabulary_classification_types vct ON vct.id=pc.classification_type_id WHERE vct.code='uc_project')"""
    comp_all = conn.execute(f"SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date>'' AND co_issued_date<>'{STUB_CO_DATE}'").fetchone()[0]
    comp_uc = conn.execute(f"SELECT COUNT(*) FROM v_projects_flat WHERE co_issued_date>'' AND co_issued_date<>'{STUB_CO_DATE}' AND {uc}").fetchone()[0]
    tiles = {r[0]: r[1] for r in conn.execute(f"""SELECT substr(co_issued_date,1,4), SUM(total_units)
        FROM v_projects_flat WHERE co_issued_date>='2023' AND co_issued_date<>'{STUB_CO_DATE}' AND {uc}
        GROUP BY 1""")}
    alltime_co = conn.execute(f"SELECT SUM(total_units) FROM v_projects_flat WHERE co_issued_date>'' AND co_issued_date<>'{STUB_CO_DATE}' AND {uc}").fetchone()[0]
    # RHNA credit = first-BP (MIN non-subsidiary BP event) >= projection-start, UC-excluded
    rhna = conn.execute(f"""SELECT SUM(vpf.total_units), SUM(COALESCE(vpf.vli_units,0))
        FROM v_projects_flat vpf JOIN (
            SELECT pe.project_id, MIN(pe.event_date) first_bp FROM project_events pe
            JOIN vocabulary_event_types et ON et.id=pe.event_type_id
            WHERE et.code='building_permit_issued' AND NOT EXISTS(
                SELECT 1 FROM project_events cc JOIN vocabulary_event_types ct ON ct.id=cc.event_type_id
                WHERE ct.code='permit_classified_subsidiary' AND cc.permit_id=pe.permit_id)
            GROUP BY pe.project_id) bp ON bp.project_id=vpf.project_id
        WHERE bp.first_bp >= '{cfg['cycle6_projection_start']}' AND vpf.{uc}""").fetchone()
    return {'completions_count': comp_all, 'completions_count_uc_excluded': comp_uc,
            'net_new_co_tiles': tiles, 'all_time_co_units': alltime_co or 0,
            'rhna_6th_cycle_credit_units': rhna[0] or 0, 'rhna_6th_cycle_credit_vli': rhna[1] or 0,
            'rhna_credit_note': 'coverage-limited: tracked-project BPs only (not the full city stream)'}


def main():
    ap = argparse.ArgumentParser(description='HCD APR A/A2/B from a v2 DB (harness: v2-path only).')
    ap.add_argument('--db', required=True, help='v2 database path (the ONLY data input)')
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--city', default='Berkeley')
    a = ap.parse_args()
    cfg = BERKELEY  # per-city config swap point
    conn = sqlite3.connect(f'file:{a.db}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    a2, prov = build_table_a2(conn, a.year, cfg)
    out = {'table_a2': a2, 'table_a': build_table_a(conn, a.year, cfg),
           'table_b': build_table_b(conn, cfg), 'cumulative': cumulative_block(conn, cfg),
           'a2_provenance_flags': prov, 'a2_row_count': len(a2)}
    print(json.dumps(out['cumulative'], indent=2))
    print(f"\nTable A2 rows for {a.year}: {len(a2)} | provenance-flagged: {len(prov)}")
    return out


if __name__ == '__main__':
    main()
