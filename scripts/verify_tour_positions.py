#!/usr/bin/env python3
"""verify_tour_positions.py — is a tour flying to the right places?

Two checks with DIFFERENT failure mechanisms, which is the whole value. Either alone can agree with
a wrong answer; both are unlikely to be wrong in the same direction.

  1. ADMINISTRATIVE — distance from each footprint to the Alameda assessor parcel we claim for it.
     Catches a footprint drawn on the wrong lot. Blind to whether anything is built there.
  2. INDEPENDENT PHYSICAL — distance to the nearest Overture building footprint, and its area.
     Catches a footprint drawn where no building stands. Blind to buildings that do not exist yet
     or post-date the imagery, so a miss here is a QUESTION, never a verdict.

BOTH SIDES OF THE APN JOIN MUST BE CANONICALISED. The first run of this check produced a nearly
empty parcel column because the reference CSV holds 059-2263-032-00 and the assessor holds
59-2263-32. It reported almost nothing and looked like it had passed. That is CLAUDE.md rule 4's
three-layer cross-walk, skipped, producing exactly the false-dead it warns about.

  python3 scripts/verify_tour_positions.py --geom kml/tours/panoramic-kennedy-legacy.kml \
      --refs data/reference/kennedy_panoramic_buildings_2026-09-04.csv
"""
import argparse, csv, math, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_building_loop import buildings
from housing_rules.apn import to_canonical_apn
import gen_svg_labels as G

ASSESSOR = "databases/berkeley.db"
V2 = "databases/berkeley_housing_v2.db"
OVERTURE = "data/raw/overture_buildings_berkeley_2026-08-19.parquet"
PARCEL_TOL_M = 40.0
BLDG_TOL_M = 30.0
TINY_M2 = 60.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geom", required=True)
    ap.add_argument("--refs", default=None, help="CSV with address/tour_address/apn columns")
    a = ap.parse_args()

    sites = buildings(a.geom)
    b = sqlite3.connect(f"file:{ASSESSOR}?mode=ro", uri=True)
    v = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)

    par = {}
    for apn, la, lo in b.execute("SELECT APN,Latitude,Longitude FROM parcels WHERE Latitude IS NOT NULL"):
        c = to_canonical_apn(apn, "alameda")
        if c and la not in (None, ""):
            par[c] = (float(lo), float(la))

    claim = {}
    if a.refs:
        for r in csv.DictReader(l for l in open(a.refs) if not l.startswith("#")):
            for addr in (r.get("address"), r.get("tour_address")):
                if addr:
                    claim[G.normkey(addr)] = r["apn"]
    for pid, apn in v.execute("SELECT pp.project_id,p.apn_raw FROM project_parcels pp "
                              "JOIN parcels p ON p.id=pp.parcel_id"):
        row = v.execute("SELECT address_display FROM v_projects_flat WHERE project_id=?", (pid,)).fetchone()
        if row:
            claim.setdefault(G.normkey(row[0]), apn)

    ov = None
    if os.path.exists(OVERTURE):
        try:
            import pyarrow.parquet as pq
            t = pq.read_table(OVERTURE)
            ov = (t.column("xmin").to_pylist(), t.column("xmax").to_pylist(),
                  t.column("ymin").to_pylist(), t.column("ymax").to_pylist(),
                  t.column("wkt").to_pylist())
        except ImportError:
            print("  (pyarrow unavailable — physical check skipped)")

    def area(w, lat):
        p = [tuple(map(float, q.split())) for q in re.findall(r"(-?\d+\.\d+ -?\d+\.\d+)", w)]
        if len(p) < 3:
            return 0
        k = math.cos(math.radians(lat)) * 111320
        return abs(sum(p[i][0]*k*p[(i+1) % len(p)][1]*111320 - p[(i+1) % len(p)][0]*k*p[i][1]*111320
                       for i in range(len(p)))) / 2

    print(f"  {len(sites)} footprints · {len(par):,} parcels canonicalised\n")
    print(f"  {'building':26} {'→parcel':>9} {'→building':>10} {'area m²':>8}  note")
    print(f"  {'-'*26} {'-'*9} {'-'*10} {'-'*8}  {'-'*30}")
    flags = 0
    for k in sorted(sites):
        lon, lat = sites[k][0], sites[k][1]
        kk = math.cos(math.radians(lat))
        raw = claim.get(G.normkey(k))
        c = to_canonical_apn(raw, "alameda") if raw else None
        dp = None
        if c and c in par:
            dp = math.hypot((par[c][0]-lon)*kk*111320, (par[c][1]-lat)*111320)
        bd, ba = None, 0
        if ov:
            X0, X1, Y0, Y1, W = ov
            bd = 1e9
            for i in range(len(X0)):
                cx, cy = (X0[i]+X1[i])/2, (Y0[i]+Y1[i])/2
                d = math.hypot((cx-lon)*kk*111320, (cy-lat)*111320)
                if d < bd:
                    bd, ba = d, area(W[i], lat)
        note = []
        if dp is None:
            note.append("no parcel claimed")
        elif dp > PARCEL_TOL_M:
            note.append("OFF PARCEL"); flags += 1
        if bd is not None and bd > BLDG_TOL_M:
            note.append("no building near"); flags += 1
        elif ba and ba < TINY_M2:
            note.append("nearest is tiny — unbuilt or newer than imagery?")
        print(f"  {k[:26]:26} {(f'{dp:8.0f}m' if dp is not None else '        -')} "
              f"{(f'{bd:9.0f}m' if bd is not None else '         -')} {ba:8.0f}  {', '.join(note)}")
    print(f"\n  {flags} hard flag(s). Tiny-area notes are questions for the eye, not failures.")


if __name__ == "__main__":
    main()
