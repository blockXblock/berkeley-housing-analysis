#!/usr/bin/env python3
"""ghost_units.py — find parcels renting MORE dwelling units than the assessor records ("ghost units").

Principle (from the Benvenue investigation): building permits and the assessor miss unpermitted / older
conversions, but the city REGULATES RENTALS regardless of permit status — so the rental-regulation datasets
count *actual* units. A parcel where a rental signal exceeds the assessor's unit count is a candidate hidden
unit. This detector uses the data we already hold; the fully-invisible class (a rented unit with NO rental
record at all, e.g. 2811½ Benvenue) is NOT flaggable here and needs the RHSP harvest + full Rent Board registry.

Signals (per parcel, joined on canonical APN):
  - assessor units .............. TaxParcel `Units` (scratch/2026-08-12/taxparcels.geojson)
  - business-license units ...... berkeley.db `licenses` busdesc "RES. RENTAL - N UNITS" / "RENTAL .../N UNITS"
  - rent-board units ............ berkeley.db `rent_control` Number_of_total_units_on_the_pr (PARTIAL: 1,098 rows)
Ghost gap = max(rental signals) - assessor units, where > 0. Plus: SFR-coded (UseCode 1xxx) parcels that
carry ANY rental record = "rented single-family" candidates (conversions).

Usage: python scripts/ghost_units.py
"""
import sqlite3, re, sys, warnings
import pandas as pd, geopandas as gpd
warnings.filterwarnings("ignore"); sys.path.insert(0, "scripts")
from housing_rules import to_canonical_apn

def canon(a):
    try: return to_canonical_apn(a, "alameda")
    except Exception: return None

def _units_from_busdesc(s):
    m = re.search(r"(\d+)\s*UNIT", str(s).upper())
    return int(m.group(1)) if m else (1 if "RENTAL" in str(s).upper() else 0)

def main():
    # 1) assessor units per parcel + Elmwood tag
    tp = gpd.read_file("scratch/2026-08-12/taxparcels.geojson")
    tp["Units"] = pd.to_numeric(tp["Units"], errors="coerce")
    tp["capn"] = tp["APN"].map(canon)
    tp["sfr"] = tp["UseCode"].astype(str).str.startswith("1")
    el = gpd.read_file("data/reference/berkeley_neighborhoods.geojson").to_crs(4326)
    elpoly = el[el["Name"].astype(str).str.contains("lmwood", case=False)].dissolve().geometry.iloc[0]
    tp = tp.to_crs(4326); tp["elmwood"] = tp.geometry.centroid.within(elpoly)
    A = tp[["capn", "Units", "sfr", "elmwood"]].dropna(subset=["capn"]).groupby("capn").agg(
        assessor_units=("Units", "max"), sfr=("sfr", "any"), elmwood=("elmwood", "any")).reset_index()

    db = sqlite3.connect("databases/berkeley.db")
    # 2) business-license rental units per parcel
    lic = pd.read_sql("SELECT apn, busdesc FROM licenses WHERE b1_per_sub_type='Rental of Real Property'", db)
    lic["capn"] = lic["apn"].map(canon); lic["lic_units"] = lic["busdesc"].map(_units_from_busdesc)
    L = lic.dropna(subset=["capn"]).groupby("capn")["lic_units"].max().reset_index()
    # 3) rent-board units per parcel (partial registry)
    rc = pd.read_sql('SELECT APN, Number_of_total_units_on_the_pr AS rb_units FROM rent_control', db)
    rc["capn"] = rc["APN"].map(canon); rc["rb_units"] = pd.to_numeric(rc["rb_units"], errors="coerce")
    R = rc.dropna(subset=["capn"]).groupby("capn")["rb_units"].max().reset_index()

    df = A.merge(L, on="capn", how="left").merge(R, on="capn", how="left")
    df["rental_signal"] = df[["lic_units", "rb_units"]].max(axis=1)
    df["ghost_gap"] = (df["rental_signal"] - df["assessor_units"]).clip(lower=0)
    df["has_rental_record"] = df[["lic_units", "rb_units"]].notna().any(axis=1)

    def report(mask, name):
        d = df[mask]
        ghosts = d[d.ghost_gap > 0]
        sfr_rented = d[d.sfr & d.has_rental_record & (d.assessor_units <= 1)]
        print(f"\n=== {name} ({len(d)} parcels) ===")
        print(f"  ghost-gap parcels (rental signal > assessor units): {len(ghosts)}  (+{int(ghosts.ghost_gap.sum())} units)")
        print(f"  rented single-family (UseCode 1xxx + a rental record, assessor<=1): {len(sfr_rented)} parcels")
    report(df.elmwood, "ELMWOOD DISTRICT")
    report(df.capn.notna(), "ALL BERKELEY")

    # calibration honesty: is 2811.5 Benvenue (053-1695-026) flaggable here?
    c = canon("53-1695-26")
    row = df[df.capn == c]
    print(f"\n2811 Benvenue ({c}): ", end="")
    if len(row): print(f"assessor={row.assessor_units.iloc[0]}, rental_record={bool(row.has_rental_record.iloc[0])}, ghost_gap={row.ghost_gap.iloc[0]}")
    print("  -> NOT flaggable from held data (no license, no rent-board row) — its only signal is the RHSP")
    print("     record in Accela. This class needs the RHSP harvest + full Rent Board registry (the CPRA).")
    df[df.ghost_gap > 0].sort_values("ghost_gap", ascending=False).to_csv("scratch/2026-08-12/ghost_units.csv", index=False)
    print("\nwrote scratch/2026-08-12/ghost_units.csv")

if __name__ == "__main__":
    main()
