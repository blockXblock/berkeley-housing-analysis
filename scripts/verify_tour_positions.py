#!/usr/bin/env python3
"""verify_tour_positions.py — is a tour flying to the right places?

Two checks with DIFFERENT failure mechanisms, which is the whole value. Either alone can agree with
a wrong answer; both are unlikely to be wrong in the same direction.

  1. ADMINISTRATIVE — distance from each footprint to the Alameda assessor parcel we claim for it.
     Catches a footprint drawn on the wrong lot. Blind to whether anything is built there.
  2. INDEPENDENT PHYSICAL — distance to the nearest Overture building footprint, and its area.
     Catches a footprint drawn where no building stands. Blind to buildings that do not exist yet
     or post-date the imagery, so a miss here is a QUESTION, never a verdict.
  3. COVERAGE — the traced footprint's AREA against the Overture building it sits inside.
     Checks 1 and 2 both verify LOCATION and are both blind to a footprint that is on the right
     lot, next to the right building, and drawn at half size. That is exactly how 2451 Shattuck
     (Fine Arts) and 2002 Addison (ARTech) shipped cut-short until John caught them by flying the
     tour, 2026-09-06. This compares the traced area to the Overture footprint the trace's centroid
     falls INSIDE (point-in-polygon, so a shed next door cannot be the match) and flags a trace far
     smaller than the mapped building. It is a QUESTION, not a verdict — Overture has its own
     errors, and a genuine multi-building site can legitimately trace one wing.

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
COVERAGE_MIN = 0.55     # traced/Overture below this = likely an INCOMPLETE trace
# ONLY the INCOMPLETE direction is flagged, and that is deliberate. traced/Overture BELOW 1 is
# trustworthy: Overture under-maps buildings (small, shaded, occluded), which can only SUPPRESS a
# false incomplete, never manufacture one -- so if Overture maps more building than we traced, we
# almost certainly under-traced. The OTHER direction is noise: an early version flagged "oversized"
# on 11 of 23 and "is-the-lot" on 18 of 23, because Overture undercounts AND many footprints
# genuinely fill their lots (a real downtown tower is 99% lot coverage). Footprint-vs-parcel quality
# is a real question, but it belongs to the Aug-22 geometry survey, not this per-record check --
# here it cried wolf and buried the one signal that matters. The traced/overture ratio is still
# PRINTED for the eye; only < 55% raises a note.


def poly_verts(wkt_or_coords, lat):
    """[(x,y)...] from either an Overture WKT or a KML coordinate blob."""
    return [tuple(map(float, q.split()[:2])) if "," not in q
            else (float(q.split(",")[0]), float(q.split(",")[1]))
            for q in re.findall(r"-?\d+\.\d+[ ,]-?\d+\.\d+", wkt_or_coords)]


def poly_area_m2(verts, lat):
    if len(verts) < 3:
        return 0.0
    k = math.cos(math.radians(lat)) * 111320.0
    return abs(sum(verts[i][0] * k * verts[(i + 1) % len(verts)][1] * 111320.0
                   - verts[(i + 1) % len(verts)][0] * k * verts[i][1] * 111320.0
                   for i in range(len(verts)))) / 2.0


def point_in(verts, x, y):
    inside = False
    n = len(verts)
    for i in range(n):
        xi, yi = verts[i]
        xj, yj = verts[(i - 1) % n]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi:
            inside = not inside
    return inside


def traced_footprints(geom_path):
    """{placemark_name: (centroid_lon, centroid_lat, area_m2)} for every polygon in the geom."""
    from gen_building_loop import placemark_name
    out = {}
    txt = open(geom_path, errors="replace").read()
    for pm in re.findall(r"<Placemark.*?</Placemark>", txt, re.S):
        if "<Polygon>" not in pm:
            continue
        k = placemark_name(pm)
        m = re.search(r"<Polygon>.*?<coordinates>\s*(.*?)\s*</coordinates>", pm, re.S)
        if not (k and m):
            continue
        v = [(float(p.split(",")[0]), float(p.split(",")[1]))
             for p in m.group(1).split() if len(p.split(",")) >= 2]
        if len(v) >= 3:
            clat = sum(y for _, y in v) / len(v)
            out[k] = (sum(x for x, _ in v) / len(v), clat, poly_area_m2(v, clat))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geom", required=True)
    ap.add_argument("--refs", default=None, help="CSV with address/tour_address/apn columns")
    a = ap.parse_args()

    sites = buildings(a.geom)
    traced = traced_footprints(a.geom)      # centroid + traced AREA, keyed like sites
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
    print(f"  {'building':26} {'→parcel':>8} {'→bldg':>6} {'traced':>7} {'overture':>8} {'cover':>6}  note")
    print(f"  {'-'*26} {'-'*8} {'-'*6} {'-'*7} {'-'*8} {'-'*6}  {'-'*26}")
    flags = 0
    for k in sorted(sites):
        lon, lat = sites[k][0], sites[k][1]
        kk = math.cos(math.radians(lat))
        raw = claim.get(G.normkey(k))
        c = to_canonical_apn(raw, "alameda") if raw else None
        dp = None
        if c and c in par:
            dp = math.hypot((par[c][0]-lon)*kk*111320, (par[c][1]-lat)*111320)

        # COVERAGE: match the Overture building this trace sits INSIDE (point-in-polygon, largest
        # if several), not the nearest centroid — a shed abutting the target must not become the
        # comparison. Fall back to nearest-centroid only when nothing contains the point.
        bd, ov_area = None, 0.0
        if ov:
            X0, X1, Y0, Y1, W = ov
            bd = 1e9
            contain_area, near_area = 0.0, 0.0
            for i in range(len(X0)):
                cx, cy = (X0[i]+X1[i])/2, (Y0[i]+Y1[i])/2
                d = math.hypot((cx-lon)*kk*111320, (cy-lat)*111320)
                if d < bd:
                    bd, near_area = d, area(W[i], lat)
                if X0[i] <= lon <= X1[i] and Y0[i] <= lat <= Y1[i]:
                    verts = poly_verts(W[i], lat)
                    if point_in(verts, lon, lat):
                        a_i = poly_area_m2(verts, lat)
                        if a_i > contain_area:
                            contain_area = a_i
            ov_area = contain_area or near_area
        traced_area = traced.get(k, (None, None, None))[2] or 0.0
        cover = (traced_area / ov_area) if ov_area else None

        note = []
        if dp is None:
            note.append("no parcel claimed")
        elif dp > PARCEL_TOL_M:
            note.append("OFF PARCEL"); flags += 1
        if bd is not None and bd > BLDG_TOL_M:
            note.append("no building near"); flags += 1
        if ov_area and ov_area < TINY_M2:
            note.append("mapped bldg tiny — unbuilt or newer than imagery?")
        elif cover is not None and cover < COVERAGE_MIN:
            note.append(f"INCOMPLETE? traces {cover*100:.0f}% of the mapped building"); flags += 1
        print(f"  {k[:26]:26} {(f'{dp:7.0f}m' if dp is not None else '       -')} "
              f"{(f'{bd:5.0f}m' if bd is not None else '     -')} "
              f"{traced_area:7.0f} {ov_area:8.0f} "
              f"{(f'{cover*100:5.0f}%' if cover is not None else '     -')}  {', '.join(note)}")
    print(f"\n  {flags} flag(s). INCOMPLETE? and the tiny note are questions for the eye, not")
    print(f"  failures: Overture under-maps small/shaded buildings, and a real multi-building")
    print(f"  site can legitimately trace one wing. Flying the tour is still the final check.")


if __name__ == "__main__":
    main()
