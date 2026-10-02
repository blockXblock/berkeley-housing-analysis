#!/usr/bin/env python3
"""audit_footprint_vs_parcel_docs.py — for skyline footprints that EXCEED their parcel, do we hold the
architect-plan / tabulation PDFs that carry the true building measurements?

A hand-traced building footprint (kml/geometry/geometry.kml) legitimately exceeds a SINGLE parcel when the
project assembles / crosses lot lines — but then the authoritative footprint lives in the architect's site
plan, not the assessor parcel. This audits each tower footprint against the parcels it overlaps and reports,
for the ones that exceed their lot(s), whether v2 (documents) holds the source PDFs to verify the number.

Two flags:
  - CROSSES LINES : footprint spans >1 parcel (nparc>1) — normal for an assemblage; needs plans to confirm.
  - EXCEEDS LOTS  : footprint area > the UNION of the parcels it sits on (ratio>1.05) — exceeds even the
                    assembled lots (crosses into street/ROW, or the trace is oversized).
Read-only. Output: a coverage table to stdout + data/reference/footprint_vs_parcel_doc_audit.csv.
"""
import geopandas as gpd, pandas as pd, sqlite3, re, warnings
from shapely.geometry import Polygon
warnings.filterwarnings("ignore")

def main():
    # 1) footprints
    t = open("kml/geometry/geometry.kml").read()
    rows = []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", t, re.S):
        nm = re.search(r"<name>([^<]*)</name>", pm); poly = re.search(r"<Polygon>.*?</Polygon>", pm, re.S)
        if not (nm and poly): continue
        cs = re.search(r"<coordinates>(.*?)</coordinates>", poly.group(0), re.S).group(1).split()
        pts = [tuple(map(float, c.split(",")))[:2] for c in cs if c.strip()]
        if len(pts) >= 4:
            rows.append({"name": nm.group(1), "geometry": Polygon(pts)})
    fp = gpd.GeoDataFrame(rows, crs=4326).to_crs(2227)

    # 2) parcels + ratio
    tp = gpd.read_file("data/raw/berkeley_taxparcels_2026-08-12.geojson")[["APN", "geometry"]].to_crs(2227)
    sidx = tp.sindex
    out = []
    for _, r in fp.iterrows():
        g = r.geometry; A = g.area
        cand = list(sidx.query(g, predicate="intersects"))
        parea = tp.iloc[cand].geometry.union_all().area if cand else None
        out.append({"name": r["name"], "fp_sqft": round(A),
                    "parcel_sqft": round(parea) if parea else None,
                    "ratio": round(A / parea, 2) if parea else None, "nparc": len(cand)})
    d = pd.DataFrame(out)

    # 3) match to v2 project by leading "NNNN STREET" and count source docs
    v2 = sqlite3.connect("databases/berkeley_housing_v2.db")
    proj = pd.read_sql("SELECT project_id, UPPER(address_display) AS addr FROM v_projects_flat", v2)
    docs = pd.read_sql("SELECT project_id, title, r2_url FROM documents", v2)
    def key(s):
        m = re.match(r"\s*(\d+)\s+([A-Za-z]+)", str(s)); return f"{m.group(1)} {m.group(2).upper()}" if m else None
    proj["key"] = proj.addr.map(key)
    p_by_key = proj.dropna(subset=["key"]).drop_duplicates("key").set_index("key").project_id.to_dict()

    def docs_for(pid):
        if pid is None: return 0, 0, 0
        sub = docs[docs.project_id == pid]
        plans = sub[sub.r2_url.fillna("").str.contains("architect_plans", case=False) |
                    sub.title.fillna("").str.contains(r"plan set|plans|drawing", case=False, regex=True)]
        tab = sub[sub.title.fillna("").str.contains(r"tabulation|1\.E", case=False, regex=True)]
        return len(plans), len(tab), int(sub.r2_url.notna().sum())

    d["project_id"] = d.name.map(lambda n: p_by_key.get(key(n)))
    d[["plans", "tabulation", "r2_docs"]] = d.project_id.apply(lambda p: pd.Series(docs_for(p)))
    d["CROSSES_LINES"] = d.nparc > 1
    d["EXCEEDS_LOTS"] = (d.ratio.notna()) & (d.ratio > 1.05)
    d["has_measure_doc"] = (d.plans > 0) | (d.tabulation > 0)

    d.to_csv("data/reference/footprint_vs_parcel_doc_audit.csv", index=False)
    flagged = d[d.CROSSES_LINES | d.EXCEEDS_LOTS].sort_values("ratio", ascending=False)
    print(f"footprints audited: {len(d)}  |  matched to a v2 project: {int(d.project_id.notna().sum())}\n")
    print(f"=== EXCEEDS LOTS (footprint > union of its parcels, ratio>1.05): {int(d.EXCEEDS_LOTS.sum())} ===")
    print(d[d.EXCEEDS_LOTS][["name", "fp_sqft", "parcel_sqft", "ratio", "nparc", "plans", "tabulation", "has_measure_doc"]].to_string(index=False))
    print(f"\n=== CROSSES LINES (spans >1 parcel — assemblage): {int(d.CROSSES_LINES.sum())} ===")
    print(d[d.CROSSES_LINES][["name", "nparc", "ratio", "plans", "tabulation", "has_measure_doc"]].sort_values("nparc", ascending=False).head(25).to_string(index=False))
    miss = flagged[(flagged.project_id.notna()) & (~flagged.has_measure_doc)]
    print(f"\n=== COVERAGE: of {len(flagged)} flagged footprints, {int(flagged.has_measure_doc.sum())} have a plan/tabulation doc; "
          f"{int(flagged.project_id.isna().sum())} unmatched to a project; {len(miss)} matched-but-NO source doc (need harvest):")
    print(miss[["name", "ratio", "nparc"]].to_string(index=False) if len(miss) else "  (none matched-but-missing)")

if __name__ == "__main__":
    main()
