#!/usr/bin/env python3
"""gen_camera_proximity.py — rank tour structures by how much the CAMERA actually sees them.

WHY: units is the wrong metric for a flyover. A 40-unit building the camera passes at 60 m
matters more visually than a 200-unit one it never approaches. Harvest effort and footprint
corrections should follow the camera, not the unit count.

MODEL (a proxy, and honest about it):
  Each tour is a sequence of <gx:FlyTo> waypoints, each carrying a <gx:duration> and either a
  <Camera> (the camera's own position) or a <LookAt> (the point being looked AT). For a LookAt
  the target coordinate IS the subject, so it counts fully. For a Camera we use its position:
  the building being filmed is near the camera on these low-altitude passes (median altitude is
  tens of metres), so proximity is a reasonable stand-in for visibility.

  For each structure we compute
     nearest_m   : distance from the polygon centroid to the closest waypoint, any tour
     dwell_s     : total <gx:duration> of waypoints within NEAR_M
     n_tours     : how many distinct tours come within NEAR_M
  and rank by dwell_s, then by -nearest_m.

  NOT MODELLED: heading, tilt and field of view. A camera can be close to a building and pointed
  away from it. So this OVER-includes rather than under-includes, which is the safe direction for
  a harvest target list. Treat the ranking as "candidates the camera plausibly sees", not proof.

Output: data/reference/camera_proximity.csv    READ-ONLY on all sources.
"""
import csv, glob, math, re, sqlite3

KML_GEOM = "kml/geometry/geometry.kml"
TOURS = "kml/tours/*.kml"
OUT = "data/reference/camera_proximity.csv"
NEAR_M = 150.0          # a building within 150 m of a waypoint is plausibly in frame
R = 6371000.0


def haversine_m(a, b):
    (lon1, lat1), (lon2, lat2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))


def waypoints():
    """[(lon, lat, duration_s, tour_name, kind)] across every tour."""
    out = []
    for path in sorted(glob.glob(TOURS)):
        name = path.split("/")[-1].replace(".kml", "")
        t = open(path, errors="replace").read()
        for fly in re.findall(r"<gx:FlyTo>.*?</gx:FlyTo>", t, re.S):
            d = re.search(r"<gx:duration>([\d.]+)</gx:duration>", fly)
            dur = float(d.group(1)) if d else 0.0
            blk = re.search(r"<(LookAt|Camera)>(.*?)</\1>", fly, re.S)
            if not blk:
                continue
            kind = blk.group(1)
            lon = re.search(r"<longitude>(-?[\d.]+)</longitude>", blk.group(2))
            lat = re.search(r"<latitude>(-?[\d.]+)</latitude>", blk.group(2))
            if lon and lat:
                out.append((float(lon.group(1)), float(lat.group(1)), dur, name, kind))
    return out


def centroids():
    """{address_upper: (lon, lat)} from the canonical tour geometry."""
    out = {}
    for pm in re.findall(r"<Placemark>.*?</Placemark>", open(KML_GEOM).read(), re.S):
        ad = re.search(r"<b>([^<]*)</b><br/>", pm)
        poly = re.search(r"<Polygon>.*?</Polygon>", pm, re.S)
        if not (ad and poly):
            continue
        cs = re.search(r"<coordinates>\s*(.*?)\s*</coordinates>", poly.group(0), re.S).group(1)
        pts = [tuple(float(x) for x in q.split(",")[:2]) for q in cs.split()]
        if len(pts) < 4:
            continue
        ring = pts[:-1]
        out.setdefault(ad.group(1).upper().strip(),
                       (sum(p[0] for p in ring)/len(ring), sum(p[1] for p in ring)/len(ring)))
    return out


def main():
    wps = waypoints()
    cents = centroids()
    print(f"{len(wps)} camera waypoints across {len(set(w[3] for w in wps))} tours; "
          f"{len(cents)} structure centroids")

    c = sqlite3.connect("databases/berkeley_housing_v2.db"); c.row_factory = sqlite3.Row
    tab = {r[0] for r in c.execute(
        "select distinct project_id from documents where (title like '%1.E%' "
        "or lower(title) like '%tabulation%') and r2_url is not null")}
    plans = {r[0] for r in c.execute(
        "select distinct d.project_id from documents d left join vocabulary_document_types v "
        "on v.id=d.document_type_id where v.code='plan_set' and d.r2_url is not null")}

    rows = []
    for r in c.execute("select project_id,address_display,total_units,status_label from v_projects_flat"):
        key = (r["address_display"] or "").upper().strip()
        if key not in cents:
            continue
        cen = cents[key]
        near, dwell, tours = 1e9, 0.0, set()
        for lon, lat, dur, tname, kind in wps:
            d = haversine_m(cen, (lon, lat))
            near = min(near, d)
            if d <= NEAR_M:
                dwell += dur
                tours.add(tname)
        rows.append(dict(project_id=r["project_id"], address=r["address_display"],
                         units=r["total_units"], status=r["status_label"],
                         nearest_m=round(near), dwell_s=round(dwell, 1), n_tours=len(tours),
                         has_tabulation=int(r["project_id"] in tab),
                         has_plan_set=int(r["project_id"] in plans)))
    rows.sort(key=lambda x: (-x["dwell_s"], x["nearest_m"]))
    for i, x in enumerate(rows, 1):
        x["camera_rank"] = i
        # the harvest target: the camera sees it, and we do NOT yet hold a stated footprint
        x["harvest_target"] = int(x["dwell_s"] > 0 and not x["has_tabulation"])
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["camera_rank", "project_id", "address", "units", "status",
                                           "nearest_m", "dwell_s", "n_tours", "has_tabulation",
                                           "has_plan_set", "harvest_target"])
        w.writeheader(); [w.writerow(x) for x in rows]
    seen = [x for x in rows if x["dwell_s"] > 0]
    print(f"wrote {OUT}: {len(rows)} structures")
    print(f"  within {NEAR_M:.0f} m of a waypoint : {len(seen)}")
    print(f"  harvest targets (seen, no 1.E)   : {sum(x['harvest_target'] for x in rows)}")
    print(f"\n  top 20 by camera dwell:")
    print(f"  {'rk':>3} {'address':26} {'u':>5} {'dwell':>7} {'near_m':>7} {'tours':>5} {'1.E':>4}")
    for x in rows[:20]:
        print(f"  {x['camera_rank']:>3} {str(x['address'])[:24]:26} {str(x['units']):>5} "
              f"{x['dwell_s']:>7.1f} {x['nearest_m']:>7} {x['n_tours']:>5} {'yes' if x['has_tabulation'] else '-':>4}")


if __name__ == "__main__":
    main()
