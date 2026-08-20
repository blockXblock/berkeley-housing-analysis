#!/usr/bin/env python3
"""harvest_tabulation_footprints.py — authoritative footprint/lot-coverage layer from architect Tabulation Forms.

The City "Tabulation Form 1.E" that architects file with each project is a STRUCTURED form whose text is
machine-readable: Lot Area, Lot Coverage (%), Building Footprint, Gross Floor Area, and dwelling-unit counts.
This harvests every Tabulation Form in v2 (documents.r2_url), parses the PROPOSED figures, derives the
authoritative building footprint (explicit value, else Lot Area x Coverage), and cross-checks it against our
hand-traced skyline footprints (kml/geometry/geometry.kml) — flagging traces that are oversized/undersized.

Output: data/reference/tabulation_footprints.csv  + a validation table to stdout.
Usage: python scripts/harvest_tabulation_footprints.py
"""
import sqlite3, subprocess, re, os, warnings
import pandas as pd

os.makedirs("scratch/2026-08-16/tab", exist_ok=True)

def numbers(line):
    return [int(x.replace(",", "")) for x in re.findall(r"[\d,]{2,}", line)]

def field(txt, label, pct=False):
    m = re.search(label + r"[^\n]*", txt, re.I)
    if not m: return None
    line = m.group(0)
    vals = [int(x) for x in re.findall(r"(\d{1,3})\s*%", line)] if pct else numbers(line)
    if not vals: return None
    # columns are [existing, proposed, required/allowed] -> take PROPOSED (2nd of 3, else the last present)
    return vals[1] if len(vals) >= 3 else vals[-1]

def main():
    v2 = sqlite3.connect("databases/berkeley_housing_v2.db")
    forms = pd.read_sql("SELECT id,project_id,title,r2_url FROM documents "
                        "WHERE (title LIKE '%Tabulation%' OR title LIKE '%1.E%') AND r2_url IS NOT NULL", v2)
    proj = pd.read_sql("SELECT project_id, address_display AS address FROM v_projects_flat", v2)
    addr = dict(zip(proj.project_id, proj.address))

    rows = []
    for _, f in forms.iterrows():
        dst = f"scratch/2026-08-16/tab/tab_{f.project_id}.pdf"
        if not os.path.exists(dst):
            subprocess.run(["curl", "-s", "--max-time", "60", "-o", dst, f.r2_url])
        try:
            txt = subprocess.run(["pdftotext", "-layout", dst, "-"], capture_output=True, text=True).stdout
        except Exception:
            txt = ""
        lot = field(txt, r"Lot Area")
        cov = field(txt, r"Lot Coverage", pct=True)
        units = field(txt, r"Number of Dwelling Units")
        fp_explicit = field(txt, r"Building Footprint")
        footprint = fp_explicit or (round(lot * cov / 100) if lot and cov else None)
        rows.append({"project_id": f.project_id, "address": addr.get(f.project_id, ""),
                     "lot_area_sf": lot, "coverage_pct": cov, "units": units,
                     "footprint_sf": footprint, "footprint_source": "explicit" if fp_explicit else "lot*coverage"})
    df = pd.DataFrame(rows)

    # cross-check vs hand-traced skyline footprints
    import geopandas as gpd
    from shapely.geometry import Polygon
    t = open("kml/geometry/geometry.kml").read()
    geo = {}
    for pm in re.findall(r"<Placemark>.*?</Placemark>", t, re.S):
        nm = re.search(r"<name>([^<]*)</name>", pm); poly = re.search(r"<Polygon>.*?</Polygon>", pm, re.S)
        if not (nm and poly): continue
        cs = re.search(r"<coordinates>(.*?)</coordinates>", poly.group(0), re.S).group(1).split()
        pts = [tuple(map(float, c.split(",")))[:2] for c in cs if c.strip()]
        if len(pts) >= 4:
            a = gpd.GeoSeries([Polygon(pts)], crs=4326).to_crs(2227).area.iloc[0]
            geo[nm.group(1)] = round(a)
    def match_geo(address):
        if not address: return None, None
        key = re.match(r"\d+\s+\w+", str(address))
        key = key.group(0) if key else str(address)[:10]
        for name, a in geo.items():
            if key.upper() in name.upper(): return name[:38], a
        return None, None
    df[["geo_name", "geo_footprint_sf"]] = df.address.apply(lambda a: pd.Series(match_geo(a)))
    df["ratio"] = (df.geo_footprint_sf / df.footprint_sf).round(2)
    df["FLAG"] = df.ratio.apply(lambda r: "" if pd.isna(r) else ("OVERSIZED" if r > 1.15 else "UNDERSIZED" if r < 0.85 else "ok"))

    os.makedirs("data/reference", exist_ok=True)
    df.to_csv("data/reference/tabulation_footprints.csv", index=False)
    print(f"harvested {len(df)} tabulation forms -> data/reference/tabulation_footprints.csv\n")
    print(df[["project_id", "address", "lot_area_sf", "coverage_pct", "units", "footprint_sf",
              "geo_footprint_sf", "ratio", "FLAG"]].to_string(index=False))

if __name__ == "__main__":
    main()
