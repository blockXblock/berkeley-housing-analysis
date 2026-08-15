#!/usr/bin/env python3
"""build_parcel_facts.py — consolidate the per-parcel facts our map popups need into ONE queryable DB.

Owner names, build-date corrections, and the use-bucket crosswalk currently live in loose CSVs that each
map generator re-joins ad hoc. This INGESTS them — together with the assessor's assessed values, address,
lat/lon, and last-recorded-document date — into databases/parcel_facts.db as a single `parcel_facts` table
keyed by canonical APN. That table is what map popups draw from, so a dot shows owner + use + assessed value
+ build year INLINE (the county assessor/tax record at propinfo.acgov.org can NOT be deep-linked and hides
owner names — see notes/2026-08-14_bond_maps_handoff.md §3), and the same table is Datasette-servable.

READ-ONLY on all sources. Writes a NEW db file — does NOT mutate berkeley.db or the canonical v2 DB.
STILL OWED (separate harvest): propinfo.acgov.org 35-yr assessed-value history + parent/child parcel lineage.

Run: python scripts/build_parcel_facts.py   # (re)builds databases/parcel_facts.db
"""
import sqlite3, sys, warnings
import pandas as pd, geopandas as gpd
warnings.filterwarnings("ignore"); sys.path.insert(0, "scripts")
from housing_rules import to_canonical_apn
from gen_ownership_map import owner_type            # DRY: the one owner-type classifier

OWNTYPE = {0: "individual", 1: "investor", 2: "trust", 3: "institutional"}
OUT = "databases/parcel_facts.db"

def bucket(uc):                                       # two-level use crosswalk (UseCode is a weak raw signal)
    p = (str(uc).lstrip("0")[:1] or "0")
    return {"1": "residential_sf", "2": "residential_small", "3": "commercial", "4": "industrial",
            "6": "institutional", "7": "residential_multi_or_condo", "9": "misc"}.get(p, "other")

def canon(a):
    try: return to_canonical_apn(a, "alameda") if pd.notna(a) else None
    except Exception: return None

def main():
    # 1) assessor core: address, assessed $, use, lat/lon, last-recorded-document date
    db = sqlite3.connect("databases/berkeley.db")
    a = pd.read_sql("SELECT APN,SitusStree,SitusStr_1,Latitude,Longitude,Land,Imps,TotalNetValue,"
                    "UseCode,LatestDocumentDate FROM parcels", db)
    for c in ["Latitude", "Longitude", "Land", "Imps", "TotalNetValue"]:
        a[c] = pd.to_numeric(a[c], errors="coerce")
    a["capn"] = a.APN.map(canon)
    a["address"] = (a.SitusStree.fillna("").astype(str).str.strip() + " "
                    + a.SitusStr_1.fillna("").astype(str).str.strip()).str.strip()
    a["use_bucket"] = a.UseCode.map(bucket)
    a["doc_year"] = pd.to_datetime(a.LatestDocumentDate, errors="coerce").dt.year

    # 2) units + assessor YearBuilt from parcel geometry file
    tp = gpd.read_file("data/raw/berkeley_taxparcels_2026-08-12.geojson")[["APN", "Units", "YearBuilt"]]
    tp["capn"] = tp.APN.map(canon)
    tp["Units"] = pd.to_numeric(tp.Units, errors="coerce")
    tp["YearBuilt"] = pd.to_numeric(tp.YearBuilt, errors="coerce")
    tp = tp.dropna(subset=["capn"]).drop_duplicates("capn")[["capn", "Units", "YearBuilt"]]

    # 3) owner name + type
    ow = pd.read_csv("data/reference/berkeley_parcel_owners_2026-08-13.csv")
    ow["capn"] = ow.APN.map(canon)
    ow["owner_type"] = ow.OwnersName.map(lambda n: OWNTYPE[owner_type(n)])
    ow = (ow.dropna(subset=["capn"]).drop_duplicates("capn")[["capn", "OwnersName", "owner_type"]]
            .rename(columns={"OwnersName": "owner_name"}))

    # 4) City-landmark true build-year override (assessor mis-dates ~70% of landmarks)
    lm = pd.read_csv("data/reference/berkeley_landmark_build_dates.csv")
    lm = (lm[lm.apn.notna() & lm.name_year.notna()].drop_duplicates("apn")
            .rename(columns={"apn": "capn", "name_year": "lm_year"})[["capn", "lm_year"]])

    f = (a.dropna(subset=["capn"]).drop_duplicates("capn")
           .merge(tp, on="capn", how="left").merge(ow, on="capn", how="left").merge(lm, on="capn", how="left"))
    f["build_year"] = f.lm_year.fillna(f.YearBuilt)
    f["build_year_source"] = f.lm_year.notna().map({True: "landmark", False: "assessor"})

    out = (f[["capn", "APN", "address", "Latitude", "Longitude", "owner_name", "owner_type", "UseCode",
              "use_bucket", "Units", "build_year", "build_year_source", "Land", "Imps", "TotalNetValue",
              "LatestDocumentDate", "doc_year"]]
           .rename(columns={"APN": "apn_raw", "Latitude": "lat", "Longitude": "lon", "UseCode": "use_code",
                            "Units": "units", "Land": "assessed_land", "Imps": "assessed_imps",
                            "TotalNetValue": "assessed_total", "LatestDocumentDate": "last_recorded_doc",
                            "doc_year": "last_recorded_doc_year"}))

    con = sqlite3.connect(OUT)                        # NEW db file
    out.to_sql("parcel_facts", con, if_exists="replace", index=False)
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_capn ON parcel_facts(capn)")
    con.commit()

    n = con.execute("SELECT COUNT(*) FROM parcel_facts").fetchone()[0]
    print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
    print(f"parcel_facts rows: {n:,}")
    for col in ["owner_name", "owner_type", "build_year", "assessed_total", "use_bucket", "address"]:
        nn = con.execute(f"SELECT COUNT({col}) FROM parcel_facts").fetchone()[0]
        print(f"  {col}: {nn:,} non-null ({100*nn//n}%)")
    print("landmark-corrected build years:",
          con.execute("SELECT COUNT(*) FROM parcel_facts WHERE build_year_source='landmark'").fetchone()[0])
    r = con.execute("SELECT address,owner_name,owner_type,use_bucket,build_year,build_year_source,"
                    "assessed_total,last_recorded_doc_year FROM parcel_facts WHERE address LIKE '2811 BENVENUE%'").fetchone()
    print("verify 2811 Benvenue:", r)
    con.close()
    print(f"wrote {OUT}")

if __name__ == "__main__":
    main()
