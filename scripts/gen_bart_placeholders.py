#!/usr/bin/env python3
"""gen_bart_placeholders.py — best-approximation placeholder buildings for the two BART joint-
development sites, so the KML tours can show roughly what will be built. Refine as full plans land.

BART sites are agency joint-developments (bart_project classification) with MULTIPLE buildings, not one
structure with a city 1.E. Building counts + heights come from the architect teams (recorded in
data/reference/bart_developments.csv):
  North Berkeley BART (proj1, 1750 Sacramento) — David Baker Architects, 13 buildings, 3-8 stories
    (Accela PLN2024-0010 master plan)
  Ashby BART West Lot (proj151) — PYATOK / DIALOG / Yes Community Architects, 5 buildings, 6-8 stories
    (July 2026 open-house; not yet in Accela)

This lays each site's buildings out on the REAL site parcel(s) (from taxparcels) as a simple packed grid
of rectangular footprints, sized by units, extruded to stories x 3.5 m (matching v2's 28 m = 8-story
convention). Output: kml/geometry/bart_placeholders.kml (extruded) + data/reference/bart_developments.csv.
Placeholder only — orientation/placement is approximate; the geometry session refines + integrates to tours.

Run: /opt/miniconda3/envs/jupyter_env/bin/python scripts/gen_bart_placeholders.py
"""
import geopandas as gpd, pandas as pd, math, warnings
from shapely.geometry import Point, Polygon, box
from shapely.affinity import rotate
import shapely.ops, pyproj
warnings.filterwarnings("ignore")

M_PER_STORY = 3.5
FT = 0.3048  # 1 ft in m; EPSG:2227 is US-feet

# building program per site: (name, stories, approx_units) — footprint derived from units/stories
BUILDINGS = {
    "North Berkeley BART": {
        "proj": 1, "addr": "1750 Sacramento St", "architect": "David Baker Architects",
        "parcels": ["58-2147-18-5", "58-2146-16-5"],  # the two ~2.5ac station lots (straddle Sacramento)
        "buildings": [
            ("Bridge 1", 8, 90), ("Bridge 2", 8, 90), ("Avalon", 8, 120), ("EBALDC", 6, 70),
            ("Insight", 6, 70), ("Bridge 2 Walk-up A", 3, 15), ("Bridge 2 Walk-up B", 3, 15),
            ("Bridge 2 Walk-up C", 3, 15), ("Avalon Walk-up A", 3, 12), ("Avalon Walk-up B", 3, 12),
            ("Avalon Walk-up C", 3, 12), ("Avalon Walk-up D", 3, 12), ("Avalon Walk-up E", 3, 12),
        ],
    },
    "Ashby BART": {
        "proj": 151, "addr": "Ashby BART West Lot (MLK/Adeline/Ashby)", "architect": "PYATOK / DIALOG / Yes Community Architects",
        "parcels": ["53-1597-39-4"],  # the 4.46-ac triangular West Lot
        "buildings": [
            ("Adeline Tower", 8, 150), ("Building B", 7, 130), ("MLK Building C", 6, 115),
            ("MLK Building D", 6, 115), ("MLK Building E", 6, 108),
        ],
    },
}


def footprint_sf(units, stories):
    # rough: ~1000 gsf/unit spread over the floors, ~85% efficiency -> footprint
    return max(2500, round(units * 1000 / stories / 0.85))


def pack(site_poly_ft, specs):
    """Place len(specs) rectangles inside site_poly_ft (a shapely poly in feet). Grid over the bbox,
    keep cells whose center is inside the site, largest buildings first into the roomiest cells."""
    minx, miny, maxx, maxy = site_poly_ft.bounds
    n = len(specs)
    cols = math.ceil(math.sqrt(n * (maxx - minx) / max(1, (maxy - miny))))
    rows = math.ceil(n / cols)
    cw, ch = (maxx - minx) / cols, (maxy - miny) / rows
    cells = []
    for r in range(rows):
        for c in range(cols):
            cx, cy = minx + (c + 0.5) * cw, miny + (r + 0.5) * ch
            if site_poly_ft.contains(Point(cx, cy)):
                cells.append((cx, cy))
    # if the polygon is skinny and too few cells landed inside, fall back to bbox grid
    if len(cells) < n:
        cells = [(minx + (c + 0.5) * cw, miny + (r + 0.5) * ch) for r in range(rows) for c in range(cols)]
    out = []
    for (name, stories, units), (cx, cy) in zip(specs, cells[:n]):
        side = math.sqrt(footprint_sf(units, stories))  # feet
        side = min(side, cw * 0.8, ch * 0.8)  # keep inside its cell
        rect = box(cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
        rect = rect.intersection(site_poly_ft) if not site_poly_ft.contains(rect) else rect
        if rect.area < 500:  # clipped away — keep the un-clipped rect so a building always shows
            rect = box(cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
        out.append((name, stories, units, rect))
    return out


def main():
    tp = gpd.read_file("data/raw/berkeley_taxparcels_2026-08-12.geojson")
    to_ft = pyproj.Transformer.from_crs(4326, 2227, always_xy=True).transform
    to_ll = pyproj.Transformer.from_crs(2227, 4326, always_xy=True).transform

    rows, placemarks = [], []
    for site, cfg in BUILDINGS.items():
        parc = tp[tp.APN.isin(cfg["parcels"])]
        site_ll = parc.geometry.union_all()
        site_ft = shapely.ops.transform(to_ft, site_ll)
        placed = pack(site_ft, cfg["buildings"])
        for name, stories, units, rect_ft in placed:
            rect_ll = shapely.ops.transform(to_ll, rect_ft)
            h = round(stories * M_PER_STORY, 1)
            fp = round(shapely.ops.transform(to_ft, rect_ll).area)
            rows.append({"site": site, "project_id": cfg["proj"], "building": name, "stories": stories,
                         "height_m": h, "approx_footprint_sf": fp, "approx_units": units,
                         "architect": cfg["architect"], "site_address": cfg["addr"],
                         "status": "placeholder_estimate", "source": "architect team / press (2026)"})
            coords = " ".join(f"{x:.6f},{y:.6f},{h}" for x, y in rect_ll.exterior.coords)
            placemarks.append(f"""  <Placemark>
    <name>{site}: {name} ({stories} st)</name>
    <description>Placeholder estimate — {units} units approx, {stories} stories, {cfg['architect']}. Refine when full plans land.</description>
    <styleUrl>#bart</styleUrl>
    <Polygon><extrude>1</extrude><altitudeMode>relativeToGround</altitudeMode>
      <outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs>
    </Polygon>
  </Placemark>""")

    pd.DataFrame(rows).to_csv("data/reference/bart_developments.csv", index=False)

    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>BART joint-development placeholders (best approximation)</name>
  <Style id="bart"><LineStyle><color>ff0066cc</color><width>1.5</width></LineStyle>
    <PolyStyle><color>993399ff</color></PolyStyle></Style>
{chr(10).join(placemarks)}
</Document>
</kml>
"""
    open("kml/geometry/bart_placeholders.kml", "w").write(kml)
    print(f"wrote data/reference/bart_developments.csv ({len(rows)} buildings)")
    print(f"wrote kml/geometry/bart_placeholders.kml ({len(placemarks)} extruded placeholders)")
    print(pd.DataFrame(rows).groupby("site").agg(buildings=("building", "count"),
          stories_min=("stories", "min"), stories_max=("stories", "max")).to_string())


if __name__ == "__main__":
    main()
