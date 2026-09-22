#!/usr/bin/env python3
"""Rebuild the Datasette databases served at berkeley-housing.fly.dev.

READ-ONLY on the canonical v2 database (opened mode=ro). Writes only into datasette-deploy/.

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
import os, sqlite3, shutil, sys, warnings
warnings.filterwarnings('ignore')

V2   = 'databases/berkeley_housing_v2.db'
OUT  = 'datasette-deploy/berkeley_housing_map.db'
CZU  = 'datasette-deploy/czu.db'
GDB  = 'data/raw/corridors/raimi_corridors.gdb'

# view/table in v2  ->  table name in the served db
EXPORTS = [
    ('v_projects_flat', 'projects'),
    ('project_events',  'project_events'),
    ('permits',         'permits'),
    ('parcels',         'parcels'),
    ('documents',       'documents'),
]

def build_housing():
    src = sqlite3.connect(f'file:{V2}?mode=ro', uri=True)
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

    rows = {}
    for srct, dstt in EXPORTS:
        cur = src.execute(f'select * from "{srct}"')
        cols = [d[0] for d in cur.description]
        dst.execute(f'create table "{dstt}" ({", ".join(chr(34)+c+chr(34) for c in cols)})')
        data = cur.fetchall()
        dst.executemany(f'insert into "{dstt}" values ({",".join("?"*len(cols))})', data)
        rows[dstt] = len(data)
    for idx in ['create index ix_ev_proj on project_events(project_id)',
                'create index ix_pm_proj on permits(project_id)',
                'create index ix_pr_addr on projects(address_normalized)']:
        try: dst.execute(idx)
        except Exception: pass
    dst.commit(); dst.close(); src.close()
    return rows, before

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

def main():
    rows, before = build_housing()
    print("=== berkeley_housing_map.db (rebuilt from v2) ===")
    print(f"  {'table':22}{'was':>9}{'now':>9}   change")
    for t, n in rows.items():
        b = before.get(t)
        d = '(new)' if b is None else f'{n-b:+,}'
        print(f"  {t:22}{(f'{b:,}' if b is not None else '-'):>9}{n:>9,}   {d}")
    for t, b in before.items():
        if t not in rows: print(f"  {t:22}{b:>9,}{'-':>9}   (dropped)")
    czu = build_czu()
    print(f"\n=== czu.db (from the CPRA #26-2367 geodatabase) ===")
    for t, n in czu.items(): print(f"  {t:26}{n:>8,}")
    print(f"\n  sizes: housing {os.path.getsize(OUT)/1048576:.1f} MB · czu {os.path.getsize(CZU)/1048576:.1f} MB")
    print("  NOT deployed. Review, then: cd datasette-deploy && flyctl deploy")

if __name__ == '__main__':
    sys.exit(main())
