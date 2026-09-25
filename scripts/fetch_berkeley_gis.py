#!/usr/bin/env python3
"""Fetch City of Berkeley GIS layers from the ArcGIS ONLINE org.

WHY THIS EXISTS. Berkeley publishes GIS on TWO endpoints and they hold different things:

  gis.cityofberkeley.info/arcgis/rest/services   -- on-prem, 504 layers, swept 2026-08-30
                                                    (data/raw/infrastructure/berkeley_arcgis_inventory_2026-08-30.json)
  services1.arcgis.com/IYiCpZoSIq9lAxi8          -- ArcGIS Online org, 470 services, NOT swept until 2026-09-24

The on-prem sweep found no street-enclosed block polygons -- only Census blocks, parcels and street
LINES. The block polygons are on the Online org, filed as 'sde_prod_DBO_Right_Of_Way', whose attributes
say ZONDIST/UNKNOWN and whose geometry is 1,197 disconnected polygons of median 3.04 acres holding a
median 25 parcels each. It is the blocks. The name misdirects; searching 'block' returns BlocksCoB,
which is only Census TIGER 2020 republished.

Pages past maxRecordCount (2000) -- Street_Centerline is 3,831 features and a single request
silently truncates.

Usage: .venv/bin/python scripts/fetch_berkeley_gis.py
"""
import json, os, time, urllib.parse, urllib.request

BASE = "https://services1.arcgis.com/IYiCpZoSIq9lAxi8/arcgis/rest/services"
OUT  = "data/raw/berkeley_gis"
UA   = {"User-Agent": "berkeleybuild-research/1.0 (+https://berkeleybuild.com)"}
LAYERS = {
    "city_blocks":        "sde_prod_DBO_Right_Of_Way",   # <- the real blocks, misnamed
    "census_blocks_2020": "BlocksCoB",                    # Census TIGER, for comparison
    "street_centerline":  "Street_Centerline",
    "street_intersection":"StreetIntersection",
}

def fetch_all(service):
    feats, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            "where": "1=1", "outFields": "*", "outSR": "4326", "f": "geojson",
            "resultOffset": offset, "resultRecordCount": 2000,
        })
        url = f"{BASE}/{service}/FeatureServer/0/query?{q}"
        d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())
        got = d.get("features", [])
        feats.extend(got)
        if len(got) < 2000:
            return feats, d
        offset += 2000
        time.sleep(0.8)

def main():
    os.makedirs(OUT, exist_ok=True)
    for name, service in LAYERS.items():
        feats, last = fetch_all(service)
        fc = {"type": "FeatureCollection", "crs": last.get("crs"), "features": feats}
        p = f"{OUT}/{name}.geojson"
        json.dump(fc, open(p, "w"))
        print(f"  {name:22} {len(feats):>6,} features  {os.path.getsize(p)/1048576:>6.1f} MB  <- {service}")

if __name__ == "__main__":
    main()
