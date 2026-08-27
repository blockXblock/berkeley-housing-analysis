#!/usr/bin/env python3
"""resolve_placeholders.py — batch-resolve the migration-placeholder buildings (geometry still at the
~10.5 m / 3-storey default) using the proj135 method, generalized: best-available HEIGHT + real FOOTPRINT.

HEIGHT, in priority order (most authoritative first):
  1. a PASS stated height from the harvested 1.E forms (data/reference/stated_heights.csv)
  2. the building-permit DESCRIPTION story count — "(5) floors over (2) floors" = 7, "12 story",
     "levels 2-12" = 12, "N-story"
FOOTPRINT:
  the assessor parcel via situs address -> APN -> berkeley.db the_geom (following re-platted APNs;
  Imps>0 confirms it is built). Falls back to the current placeholder geometry if no situs match.

Output: data/reference/placeholder_corrections.csv (+ per-project geojson in the same dir) for the
geometry session to promote into geometry.kml. Read-only on v2; writes only to data/reference/.
Run: /opt/miniconda3/envs/jupyter_env/bin/python scripts/resolve_placeholders.py
"""
import sqlite3, re, json, os
import pandas as pd
from shapely import wkt
from shapely.geometry import shape
import shapely.ops, pyproj

TO_FT = pyproj.Transformer.from_crs(4326, 2227, always_xy=True).transform
M_PER_STORY = 3.5
OUTDIR = "data/reference/placeholder_geojson"


def stories_from_desc(desc):
    d = str(desc or "")
    # "(5) floors ... over (2) floors [+ basement]" -> sum
    m = re.search(r"\(?(\d+)\)?\s*floors?.*?over.*?\(?(\d+)\)?\s*floors?", d, re.I)
    if m:
        return int(m.group(1)) + int(m.group(2))
    # "levels 2-12" -> top level
    m = re.search(r"levels?\s*\d+\s*[-–]\s*(\d+)", d, re.I)
    if m:
        return int(m.group(1))
    # "12 story" / "12-story" / "(12) story"
    m = re.search(r"\(?(\d+)\)?\s*[-\s]?stor(?:y|ies)", d, re.I)
    if m and int(m.group(1)) <= 60:
        return int(m.group(1))
    return None


def main():
    v2 = sqlite3.connect("databases/berkeley_housing_v2.db")
    b = sqlite3.connect("databases/berkeley.db")

    pg = pd.read_sql("SELECT project_id, height_meters, geojson FROM project_geometries WHERE geojson LIKE '%Polygon%'", v2)
    ph = pg[(pg.height_meters >= 9) & (pg.height_meters <= 11)].drop_duplicates("project_id")
    flat = pd.read_sql("SELECT project_id, address_display, total_units FROM v_projects_flat", v2).set_index("project_id")
    perms = pd.read_sql("SELECT project_id, permit_number, valuation, description FROM permits", v2)
    stated = pd.read_csv("data/reference/stated_heights.csv")
    stated_pass = stated[stated.verdict == "PASS"].set_index("project_id")

    os.makedirs(OUTDIR, exist_ok=True)
    out = []
    for pid in ph.project_id:
        addr = flat.address_display.get(pid, "")
        units = flat.total_units.get(pid, None)
        # ---- HEIGHT ----
        stories = height_src = None
        if pid in stated_pass.index:
            stories = int(stated_pass.stories_proposed.get(pid)); height_src = "1.E stated"
        if stories is None:
            pp = perms[perms.project_id == pid].sort_values("valuation", ascending=False, na_position="last")
            for _, r in pp.iterrows():
                s = stories_from_desc(r.description)
                if s:
                    stories = s; height_src = f"BP {r.permit_number} desc"; break
        # ---- FOOTPRINT ----  primary: the project's stored APN -> assessor geom (handles corner
        # lots / re-plats where situs address != project address); fallback: situs-address match.
        fp_sf = fp_geojson = fp_src = None
        row = None
        apn = v2.execute("""SELECT p.apn_normalized FROM parcels p JOIN project_parcels pp
                            ON pp.parcel_id=p.id WHERE pp.project_id=? AND p.apn_normalized IS NOT NULL
                            ORDER BY pp.is_primary DESC LIMIT 1""", (pid,)).fetchone()
        if apn and apn[0]:
            segs = [s.lstrip("0") or "0" for s in apn[0].split("-")]           # 057-2046-001-00 -> 57 2046 1 0
            for cand in {"-".join(segs[:3]), "-".join(segs), "-".join(segs[:4])}:
                row = b.execute("SELECT APN, the_geom, Imps FROM parcels WHERE APN=?", (cand,)).fetchone()
                if row and row[1]:
                    break
        if not (row and row[1]):  # situs fallback
            m = re.match(r"\s*(\d+)\s+(.+?)\s*(?:St|Ave|Way|Blvd|Dr|Rd|Ln|Ct|Pl|Ter|Sq|Cir)?\s*$", str(addr), re.I)
            if m:
                row = b.execute("SELECT APN, the_geom, Imps FROM parcels WHERE SitusStree=? AND UPPER(SitusStr_1) LIKE ?",
                                (m.group(1), f"{m.group(2).upper().strip()}%")).fetchone()
        if row and row[1]:
            g = wkt.loads(row[1]); poly = g.geoms[0] if g.geom_type == "MultiPolygon" else g
            fp_sf = round(shapely.ops.transform(TO_FT, poly).area)
            fp_geojson = {"type": "Polygon", "coordinates": [[list(c) for c in poly.exterior.coords]]}
            fp_src = f"assessor {row[0]}" + (f" Imps=${int(row[2]):,}" if row[2] else "")
        # sanity: floor-area per unit if both known
        spu = round(fp_sf * stories / units) if (fp_sf and stories and units and units > 0) else None
        rec = {"project_id": pid, "address": addr, "units": units, "stories": stories,
               "height_m": round(stories * M_PER_STORY, 1) if stories else None,
               "footprint_sf": fp_sf, "sf_per_unit": spu, "height_source": height_src,
               "footprint_source": fp_src,
               "status": "resolved" if (stories and fp_sf) else "partial" if (stories or fp_sf) else "unresolved"}
        out.append(rec)
        if fp_geojson and stories:
            json.dump({**rec, "geojson": fp_geojson}, open(f"{OUTDIR}/proj{pid}.json", "w"))

    df = pd.DataFrame(out).sort_values(["status", "units"], ascending=[True, False])
    df.to_csv("data/reference/placeholder_corrections.csv", index=False)
    from collections import Counter
    print(f"placeholders: {len(df)} -> data/reference/placeholder_corrections.csv")
    print("status:", dict(Counter(df.status)))
    print("height sources:", dict(Counter(df.height_source.dropna())))
    print("\nRESOLVED (height + footprint), top by units:")
    for _, r in df[df.status == "resolved"].sort_values("units", ascending=False).head(25).iterrows():
        print(f"  proj{int(r.project_id):<4} {str(r.address)[:20]:20} {r.stories}st {r.footprint_sf}sf "
              f"{r.sf_per_unit}sf/u  [{r.height_source}]")


if __name__ == "__main__":
    main()
