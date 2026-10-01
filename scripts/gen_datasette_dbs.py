#!/usr/bin/env python3
"""Rebuild the Datasette databases served at berkeley-housing.fly.dev.

READ-ONLY on the canonical v4 database (opened mode=ro; re-pointed from v2 2026-10-01). Writes only into
datasette-deploy/. Reads v4's SERVING VIEWS (build_views.py) -- never re-derives a field -- and applies the
publishing rule (organisations named, private individuals not) as each row is copied.

WHY THIS EXISTS. The deployed databases were hand-built in Feb/Mar 2026 and there was no
generator, so they silently went stale: the live instance serves 163 projects while v2 has
909, and datasette-deploy/README.md claims 115 -- three different numbers, none current.
Anyone following the Datasette link from README.md, docs/start-here.md or PRESENTER_NOTES.md
has been shown a fifth of the pipeline, dated March, with nothing saying so.

FILENAME IS DELIBERATE. berkeley_housing_map.db keeps its name even though it now holds the
whole pipeline: the published links are /berkeley_housing_map/... and breaking them is worse
than an imprecise name.

Usage: .venv/bin/python scripts/gen_datasette_dbs.py
"""
import json, os, sqlite3, shutil, sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, 'scripts')
from housing_rules.owner_name import is_organisation   # the publishing rule's organisation test

V4   = 'databases/berkeley_housing_v4.db'       # 2026-10-01: re-pointed from v2 (cutover phase 6, step 2)
OUT  = 'datasette-deploy/berkeley_housing_map.db'
CZU  = 'datasette-deploy/czu.db'
GDB  = 'data/raw/corridors/raimi_corridors.gdb'

# PUBLISHING RULE (John, 2026-10-01): full data stays in v4; a PUBLIC page names organisations and shows a private
# individual as "individual owner" (owners) or "individual" (applicants -- a homeowner's name on an ADU application ties
# a person to a home just as an owner listing does). City staff, inspectors and licensed contractors act in a public or
# licensed capacity and are named. Rent Board tenancy dates are published as the YEAR.
OWNER_ROLES = {'owner_of_record', 'record_owner', 'permit_owner', 'rental_owner', 'rental_owner_business',
               'rental_operator', 'plans_owner', 'tax_credit_owner'}
APPLICANT_ROLES = {'applicant', 'plans_applicant'}


def mask(name, label):
    return name if not name or is_organisation(name) else label


# served table -> (SQL over v4, {column: transform})
EXPORTS = {
    'projects': ("SELECT * FROM v_projects",
                 {'owner_current': lambda v: mask(v, 'individual owner'),
                  'planning_applicant': lambda v: mask(v, 'individual')}),
    'timeline': ("SELECT * FROM v_project_timeline", {}),
    'people': ("SELECT project_key, role, name, source, record, note FROM v_project_people", None),   # row-wise mask
    'businesses': ("SELECT * FROM v_project_businesses", None),
    'city_records': ("SELECT * FROM v_project_records_listed", {}),
    'adu_rent_board': ("SELECT * FROM v_adu_rent_board", {'tenancy_start': lambda v: v[:4] if v else v}),
    'permits': ("""SELECT json_extract(p.notes, '$.project_key') AS project_key, e.source_record_key AS permit,
                          se.role_in_structure AS role, MIN(CASE WHEN e.event_type_code = 'permit_submitted' THEN e.event_date END) AS submitted,
                          MIN(CASE WHEN e.event_type_code = 'permit_issued' THEN e.event_date END) AS issued,
                          MAX(CASE WHEN e.event_type_code IN ('permit_finaled', 'permit_completed') THEN e.event_date END) AS finaled,
                          MAX(c.housing_role) AS housing_role, MAX(c.net_units) AS net_units, MAX(e.raw_description) AS description
                   FROM projects p JOIN project_structures ps USING(project_id) JOIN structure_events se USING(structure_id)
                   JOIN events e USING(event_id) LEFT JOIN event_classifications c USING(event_id)
                   WHERE e.event_type_code LIKE 'permit_%' AND se.role_in_structure IN ('master', 'phase', 'attached')
                   GROUP BY 1, 2, 3""", {}),
    'parcels': ("""SELECT json_extract(p.notes, '$.project_key') AS project_key, pi.apn_normalized AS apn,
                          av.land, av.improvements, av.total_net_value, av.est_annual_tax, av.as_of_date
                   FROM projects p JOIN project_parcels pp USING(project_id)
                   JOIN parcel_identifiers pi ON pi.parcel_id = pp.parcel_id AND pi.is_current = 1
                   LEFT JOIN assessed_values av ON av.parcel_id = pp.parcel_id AND av.valid_to IS NULL""", {}),
    'documents': ("""SELECT DISTINCT json_extract(p.notes, '$.project_key') AS project_key, d.record_key, d.title, d.doc_type,
                            d.doc_date, d.store_url, d.sha256, d.page_count
                     FROM projects p JOIN project_records pr USING(project_id) JOIN documents d ON d.record_key = pr.record_key""", {}),
}


def build_housing():
    src = sqlite3.connect(f'file:{V4}?mode=ro', uri=True)
    # Keep the FIRST .prev ever made -- that is the original hand-built February database
    # and the only copy of the baseline. Later runs must not clobber it.
    if os.path.exists(OUT):
        if os.path.exists(OUT + '.prev'):
            os.remove(OUT)
        else:
            shutil.move(OUT, OUT + '.prev')
    dst = sqlite3.connect(OUT)
    before = {}
    if os.path.exists(OUT + '.prev'):
        p = sqlite3.connect(f'file:{OUT}.prev?mode=ro', uri=True)
        for (t,) in p.execute("select name from sqlite_master where type='table'"):
            before[t] = p.execute(f'select count(*) from "{t}"').fetchone()[0]
        p.close()

    rows, masked = {}, {}
    for dstt, (sql, tf) in EXPORTS.items():
        cur = src.execute(sql)
        cols = [d[0] for d in cur.description]
        data, n_mask = [], 0
        for r in cur.fetchall():
            r = list(r)
            if dstt == 'people':
                role, name = r[1], r[2]
                if role in OWNER_ROLES or role in APPLICANT_ROLES:
                    m = mask(name, 'individual owner' if role in OWNER_ROLES else 'individual')
                    n_mask += m != name
                    r[2] = m
            elif dstt == 'businesses':
                i_sub, i_n, i_d = cols.index('sub_type'), cols.index('business_name'), cols.index('dba')
                if r[i_sub] == 'Rental of Real Property':
                    for i in (i_n, i_d):
                        m = mask(r[i], 'individual owner'); n_mask += m != r[i]; r[i] = m
            else:
                for c, f in (tf or {}).items():
                    if c in cols:
                        k = cols.index(c); m = f(r[k]); n_mask += m != r[k]; r[k] = m
            data.append(r)
        dst.execute(f'create table "{dstt}" ({", ".join(chr(34)+c+chr(34) for c in cols)})')
        dst.executemany(f'insert into "{dstt}" values ({",".join("?"*len(cols))})', data)
        rows[dstt], masked[dstt] = len(data), n_mask
    for idx in ['create index ix_tl_proj on timeline(project_key)', 'create index ix_pe_proj on people(project_key)',
                'create index ix_pm_proj on permits(project_key)', 'create index ix_pr_key on projects(project_key)',
                'create index ix_cr_proj on city_records(project_key)', 'create index ix_bz_proj on businesses(project_key)']:
        dst.execute(idx)
    dst.commit(); dst.close(); src.close()
    return rows, before, masked

def build_czu():
    import geopandas as gpd
    layers = {
        'corridor_parcels'        : 'project_area_parcels_data',
        'corridor_dev_potential'  : 'project_area_parcels_dev_potential',
        'corridor_zoning'         : 'project_area_parcels_zoning_gplu',
        'housing_element_sites'   : 'housing_element_sites',
        'opportunity_sites'       : 'Parcels_Opportunity_Sites_OpOnly',
        'zoning_districts'        : 'ZoningDistricts',
    }
    if os.path.exists(CZU): os.remove(CZU)
    con = sqlite3.connect(CZU)
    out = {}
    for name, layer in layers.items():
        df = gpd.read_file(GDB, layer=layer)
        if df.crs and df.crs.to_epsg() != 4326:
            df = df.to_crs(4326)
        # keep a lon/lat so datasette-cluster-map can plot, then drop geometry
        # NAME THESE DISTINCTLY. Several layers already carry Longitude/Latitude (in UTM
        # metres, not degrees), and SQLite column names are case-insensitive -- adding
        # 'longitude' collided with 'Longitude' and aborted the build.
        c = df.geometry.representative_point()
        df = df.drop(columns='geometry')
        df['lon_wgs84'], df['lat_wgs84'] = c.x.values, c.y.values
        df.columns = [str(x) for x in df.columns]
        df.to_sql(name, con, index=False)
        out[name] = len(df)
    con.commit(); con.close()
    return out

TABLE_DOCS = {
    'projects': ("Projects", "One row per project (v4 v_projects). project_key is the stable public id (anchor Planning "
                 "record, else first master permit). Status, units, tiers, pathways and dates come from sources; see "
                 "the methodology for each.", ["status", "pathways", "rhna_excluded"]),
    'timeline': ("Timeline", "Each project's Planning records and building-permit events, dated as the City recorded them.",
                 ["role", "event_type_code"]),
    'people': ("People and organizations, by role", "Every role from its own record: owner of record (County roll), "
               "permit owner and contractors (building permit pages), architect and engineers (plan title blocks), "
               "property manager and rental owner (Rent Board), developer and general partners (CTCAC), funders "
               "(funding ledger), City reviewers and inspectors. Private individuals are shown as 'individual owner' "
               "or 'individual'.", ["role", "source"]),
    'businesses': ("Licensed businesses at each project", "City business licenses (2025-11-15 export) on a project's "
                   "parcels or addresses. The export lacks some tenants that permits show, so no license does not mean vacant.",
                   ["sub_type", "matched_by"]),
    'city_records': ("City records at each project's buildings", "Every Accela Building and Planning listing at the "
                     "project's building addresses (tenant improvements, business certificates, signs, short-term "
                     "rentals). in_project = 1 when the record is one of the project's own.", ["module", "record_type", "in_project"]),
    'adu_rent_board': ("ADUs in the Rent Board registry", "Each ADU at one of three strengths: board_labelled_adu (the "
                       "Board labels the unit ADU), parcel_registrations (units on the parcel, none labeled ADU), "
                       "no_registration_found (NOT 'not rented'). Tenancy start shown as the year.", ["evidence", "unit_status"]),
    'permits': ("Building permits", "Master, phase and attached permits of each project's buildings, with submitted / "
                "issued / finaled dates and the model-read housing role.", ["role", "housing_role"]),
    'parcels': ("Parcels and assessed values", "Each project's current parcels (County lineage) and the assessor's "
                "current values.", []),
    'documents': ("Documents", "Plan sets, applications and forms held in R2, with SHA-256.", ["doc_type"]),
}


def write_metadata(rows):
    """metadata.json FROM THE BUILD (the hand-written one still said 162 projects). The address-centric database's
    section is carried over unchanged."""
    path = 'datasette-deploy/metadata.json'
    old = json.load(open(path)) if os.path.exists(path) else {}
    meta = {"title": "Berkeley Housing Pipeline Database",
            "description": f"{rows['projects']:,} housing projects rebuilt from primary sources (CPRA permit feeds, City "
                           f"Accela records, Alameda County assessor, Rent Board registry, CTCAC). Regenerated by "
                           f"scripts/gen_datasette_dbs.py from the canonical v4 database.",
            "source": "City of Berkeley (Accela, CPRA productions, Rent Board), Alameda County assessor, CTCAC",
            "source_url": "https://github.com/blockXblock/berkeley-housing-analysis",
            "license": "Public Domain (CC0)",
            "databases": dict(old.get("databases", {}))}
    meta["databases"]["berkeley_housing_map"] = {
        "title": f"Housing Pipeline ({rows['projects']:,} projects)",
        "description": "From the canonical v4 database's serving views. Organizations are named; private individuals "
                       "are not (publishing rule, 2026-10-01).",
        "tables": {t: {"title": f"{title} ({rows[t]:,})", "description": desc, **({"facets": facets} if facets else {})}
                   for t, (title, desc, facets) in TABLE_DOCS.items() if t in rows}}
    meta["databases"]["berkeley_housing_map"]["tables"]["projects"]["plugins"] = {
        "datasette-cluster-map": {"latitude_column": "latitude", "longitude_column": "longitude"}}
    json.dump(meta, open(path, 'w'), indent=2)


def main():
    rows, before, masked = build_housing()
    write_metadata(rows)
    print("=== berkeley_housing_map.db (rebuilt from v4) ===")
    print(f"  {'table':22}{'was':>9}{'now':>9}   change")
    for t, n in rows.items():
        b = before.get(t)
        d = '(new)' if b is None else f'{n-b:+,}'
        print(f"  {t:22}{(f'{b:,}' if b is not None else '-'):>9}{n:>9,}   {d}   (values masked by the publishing rule: {masked[t]:,})")
    for t, b in before.items():
        if t not in rows: print(f"  {t:22}{b:>9,}{'-':>9}   (dropped)")
    czu = build_czu()
    print(f"\n=== czu.db (from the CPRA #26-2367 geodatabase) ===")
    for t, n in czu.items(): print(f"  {t:26}{n:>8,}")
    print(f"\n  sizes: housing {os.path.getsize(OUT)/1048576:.1f} MB · czu {os.path.getsize(CZU)/1048576:.1f} MB")
    print("  NOT deployed. Review, then: cd datasette-deploy && flyctl deploy")

if __name__ == '__main__':
    sys.exit(main())
