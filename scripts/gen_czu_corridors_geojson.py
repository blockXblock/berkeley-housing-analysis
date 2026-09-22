#!/usr/bin/env python3
"""CZU corridor parcels -> web-ready GeoJSON.

Reads the Raimi + Associates file geodatabase obtained under CPRA #26-2367 and writes a
single reprojected GeoJSON for the MapLibre maps in docs/maps/.

WHY EACH STEP:
  - reproject: the .gdb is EPSG:32610 (UTM 10N) + NAVD88. Web maps need EPSG:4326 lon/lat.
  - force_2d:  the source carries Z; MapLibre chokes on 3D coordinates in GeoJSON.
  - dedupe:    the attribute join is many-to-one on APN (the corridor table has repeated
               APNs for multi-address parcels). Joining naively turned 335 parcels into 339.
               Keep the first attribute row per parcel.

  development_potential IS NOT DECODED. The .gdb carries a 9-value grade (1A..5) on 186 of
  335 parcels with NO legend, and it is absent from both the Existing Conditions report and
  the 2026-05-06 Planning Commission item. Do NOT render it as an ordered scale until the
  City supplies the data dictionary. It ships as an opaque label.

Usage: .venv/bin/python scripts/gen_czu_corridors_geojson.py
"""
import os, sys, warnings
warnings.filterwarnings('ignore')
import geopandas as gpd

GDB = 'data/raw/corridors/raimi_corridors.gdb'
OUT = 'data/derived/czu_corridor_parcels.geojson'

def key(s): return s.astype(str).str.replace(r'[^0-9A-Za-z]', '', regex=True)

def main():
    dp = gpd.read_file(GDB, layer='project_area_parcels_dev_potential')
    at = gpd.read_file(GDB, layer='project_area_parcels_data')
    n_in = len(dp)

    dp['APNk'] = key(dp['APN']); at['APNk'] = key(at['APN'])
    cols = ['APNk','SitusAddre','OwnersName','UseCode','Units','YearBuilt','Stories','BuildingAr','Land','Imps']
    at = at[cols].drop_duplicates(subset='APNk', keep='first')   # <- the 335 vs 339 fix
    m = dp.merge(at, on='APNk', how='left')
    assert len(m) == n_in, f"join changed row count: {n_in} -> {len(m)}"

    m = m.to_crs(4326)
    m['geometry'] = m.geometry.force_2d()
    m = m.drop(columns=['APNk','Shape_Length','Shape_Area'], errors='ignore')

    os.makedirs('data/derived', exist_ok=True)
    if os.path.exists(OUT): os.remove(OUT)
    m.to_file(OUT, driver='GeoJSON')

    graded = m['development_potential'].notna().sum()
    print(f"{OUT}: {len(m)} parcels, {os.path.getsize(OUT)/1024:.0f} KB")
    print(f"  corridors: {dict(m['Corridor'].value_counts())}")
    print(f"  graded (development_potential present): {graded}/{len(m)}")
    for c, g in m.groupby('Corridor'):
        print(f"    {c:16} {len(g):4} parcels, {g['development_potential'].notna().sum():4} graded"
              f"  ({g['development_potential'].notna().mean()*100:.0f}%)")
    print(f"  bounds: {[round(x,4) for x in m.total_bounds]}")

if __name__ == '__main__':
    sys.exit(main())
