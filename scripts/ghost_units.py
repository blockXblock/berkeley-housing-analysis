#!/usr/bin/env python3
"""ghost_units.py — inventory Berkeley's "ghost" dwelling units and label which system misses each.

Principle (from the Benvenue investigation): the city assigns an official ADDRESS to a dwelling unit even
when it was never permitted or licensed. So the RPP address layer (secondary-unit addresses: fractional
"½", letter "A"/"B", "Rear", "Cottage") is the master inventory of units-on-the-ground — including
unpermitted backyard conversions like 2811½ Benvenue that permits, business licenses, and the Rent Board
miss. Cross-referencing that inventory against each other system tells you WHICH system missed each unit.

Signals (per parcel):
  - secondary-unit addresses ... data/reference/berkeley_secondary_unit_addresses.geojson (RPP, dedup'd)
  - assessor units ............. scratch/2026-08-12/taxparcels.geojson (`Units`, `UseCode`)
  - business-license units ..... berkeley.db `licenses` "RES. RENTAL - N UNITS"
  - rent-board units ........... berkeley.db `rent_control` (PARTIAL registry; the Rent Board CPRA closes it)

Classes (for a parcel carrying >=1 secondary-unit address):
  - assessor_undercount ... assessor says <=1 unit -> the assessor genuinely missed the secondary unit(s).
  - assessed_multiunit .... assessor already counts >=2 -> the unit is assessed but may be unpermitted /
                            unlicensed / unregistered (the 2811½ class — visible to the assessor, not to
                            the permit/license systems).

Usage: python scripts/ghost_units.py
"""
import sqlite3, re, sys, warnings
import pandas as pd, geopandas as gpd
warnings.filterwarnings("ignore"); sys.path.insert(0, "scripts")
from housing_rules import to_canonical_apn

SEC = "data/reference/berkeley_secondary_unit_addresses.geojson"
TP  = "scratch/2026-08-12/taxparcels.geojson"
NBH = "data/reference/berkeley_neighborhoods.geojson"

def canon(a):
    try: return to_canonical_apn(a, "alameda")
    except Exception: return None

def _lic_units(s):
    m = re.search(r"(\d+)\s*UNIT", str(s).upper())
    return int(m.group(1)) if m else 1

def main():
    # 1) RPP secondary-unit addresses -> parcel (spatial), dedup by address
    sec = gpd.read_file(SEC).drop_duplicates("FullAddres")
    tp = gpd.read_file(TP)[["APN", "Units", "UseCode", "geometry"]]
    tp["Units"] = pd.to_numeric(tp["Units"], errors="coerce")
    tp = tp.rename(columns={"Units": "assessor_units", "UseCode": "assessor_uc"})
    nbh = gpd.read_file(NBH).to_crs(4326)
    elpoly = nbh[nbh.Name.astype(str).str.contains("lmwood", case=False)].dissolve().geometry.iloc[0]
    j = gpd.sjoin(sec, tp, predicate="within", how="inner")
    j["elmwood"] = j.geometry.within(elpoly)
    j["capn"] = j["APN"].map(canon)

    # per-parcel rollup
    P = j.groupby("capn").agg(
        n_secondary=("FullAddres", "nunique"),
        assessor_units=("assessor_units", "max"),
        assessor_uc=("assessor_uc", "first"),
        elmwood=("elmwood", "any"),
        addrs=("FullAddres", lambda s: "; ".join(sorted(set(s))[:4])),
    ).reset_index()

    # 2) attach license / rent-board unit counts
    db = sqlite3.connect("databases/berkeley.db")
    lic = pd.read_sql("SELECT apn, busdesc FROM licenses WHERE b1_per_sub_type='Rental of Real Property'", db)
    lic["capn"] = lic["apn"].map(canon); lic["lic_units"] = lic["busdesc"].map(_lic_units)
    P = P.merge(lic.groupby("capn")["lic_units"].max().reset_index(), on="capn", how="left")
    rc = pd.read_sql('SELECT APN, Number_of_total_units_on_the_pr AS rb FROM rent_control', db)
    rc["capn"] = rc["APN"].map(canon); rc["rb"] = pd.to_numeric(rc["rb"], errors="coerce")
    P = P.merge(rc.groupby("capn")["rb"].max().reset_index(), on="capn", how="left")

    # 3) classify
    P["cls"] = P["assessor_units"].apply(lambda u: "assessor_undercount" if (pd.isna(u) or u <= 1) else "assessed_multiunit")
    P["registered_rental"] = P[["lic_units", "rb"]].notna().any(axis=1)

    def rpt(mask, name):
        d = P[mask]
        print(f"\n=== {name} — {len(d)} parcels carry a secondary-unit address ({int(d.n_secondary.sum())} such addresses) ===")
        print(d.cls.value_counts().to_string())
        print(f"  of the assessed_multiunit, registered as a rental (license/rent-board): "
              f"{int(P[mask & (P.cls=='assessed_multiunit')].registered_rental.sum())}")
    rpt(P.elmwood, "ELMWOOD DISTRICT")
    rpt(P.capn.notna(), "ALL BERKELEY")

    c = canon("53-1695-26")
    r = P[P.capn == c]
    if len(r):
        print(f"\nCALIBRATION 2811 Benvenue ({c}): class={r.cls.iloc[0]}, assessor_units={r.assessor_units.iloc[0]}, "
              f"secondary_addrs=[{r.addrs.iloc[0]}], registered_rental={bool(r.registered_rental.iloc[0])}")
    P.sort_values(["elmwood", "n_secondary"], ascending=False).to_csv("scratch/2026-08-12/ghost_units.csv", index=False)
    print("\nwrote scratch/2026-08-12/ghost_units.csv (per-parcel ghost inventory)")

if __name__ == "__main__":
    main()
