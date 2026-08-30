#!/usr/bin/env python3
"""Page a full ArcGIS layer using esriJSON (the server's geojson formatter breaks
on some layers) and convert to GeoJSON locally. Verifies count + OID coverage."""
import json, sys, time, urllib.parse, urllib.request

url, out = sys.argv[1], sys.argv[2]
UA = {"User-Agent": "berkeley-data research (john.gage@gmail.com)"}

def q(params, tries=4, timeout=120):
    u = url + "/query?" + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout) as r:
                j = json.loads(r.read().decode("utf-8", "replace"))
            if isinstance(j, dict) and "error" in j:
                last = json.dumps(j["error"])[:200]
            else:
                return j
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 * (i + 1))
    raise SystemExit(f"FAILED after {tries}: {last}\n  {u[:220]}")

def ring_area(r):
    return sum((r[i][0] * r[i+1][1] - r[i+1][0] * r[i][1]) for i in range(len(r)-1)) / 2.0

def to_geojson_geom(g, gtype):
    if not g: return None
    if gtype == "esriGeometryPoint":
        if g.get("x") is None or g.get("x") == "NaN": return None
        return {"type": "Point", "coordinates": [g["x"], g["y"]]}
    if gtype in ("esriGeometryPolyline",):
        paths = [[[p[0], p[1]] for p in path] for path in g.get("paths", []) if len(path) >= 2]
        if not paths: return None
        return {"type": "LineString", "coordinates": paths[0]} if len(paths) == 1 \
               else {"type": "MultiLineString", "coordinates": paths}
    if gtype in ("esriGeometryPolygon",):
        rings = [[[p[0], p[1]] for p in r] for r in g.get("rings", []) if len(r) >= 4]
        if not rings: return None
        polys, cur = [], None
        for r in rings:
            if ring_area(r) < 0:                      # Esri: clockwise = outer ring
                cur = [r]; polys.append(cur)
            elif cur is not None:
                cur.append(r)                          # hole
            else:
                cur = [r]; polys.append(cur)
        return {"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1 \
               else {"type": "MultiPolygon", "coordinates": polys}
    if gtype == "esriGeometryMultipoint":
        pts = [[p[0], p[1]] for p in g.get("points", [])]
        return {"type": "MultiPoint", "coordinates": pts} if pts else None
    return None

total = q({"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
oids = sorted(q({"where": "1=1", "returnIdsOnly": "true", "f": "json"}).get("objectIds") or [])
print(f"  server count={total} oids={len(oids)}", file=sys.stderr, flush=True)

feats, seen, PAGE = [], set(), 1000
offset = 0
while offset < total:
    d = q({"where": "1=1", "outFields": "*", "outSR": "4326", "returnGeometry": "true",
           "f": "json", "resultOffset": offset, "resultRecordCount": PAGE})
    gtype = d.get("geometryType")
    got = d.get("features", [])
    if not got:
        print(f"  empty page at offset {offset}", file=sys.stderr); break
    for ft in got:
        a = ft.get("attributes", {})
        oid = a.get("OBJECTID")
        seen.add(oid)
        feats.append({"type": "Feature", "id": oid, "properties": a,
                      "geometry": to_geojson_geom(ft.get("geometry"), gtype)})
    offset += len(got)
    print(f"  {len(feats)}/{total}", file=sys.stderr, flush=True)

missing = sorted(set(oids) - seen)
if missing:                                            # backfill any OIDs paging skipped
    print(f"  backfilling {len(missing)} missing OIDs", file=sys.stderr)
    for i in range(0, len(missing), 100):
        ch = missing[i:i+100]
        d = q({"where": f"OBJECTID IN ({','.join(map(str,ch))})", "outFields": "*",
               "outSR": "4326", "f": "json"})
        for ft in d.get("features", []):
            a = ft.get("attributes", {})
            feats.append({"type": "Feature", "id": a.get("OBJECTID"), "properties": a,
                          "geometry": to_geojson_geom(ft.get("geometry"), d.get("geometryType"))})

nogeom = sum(1 for f in feats if f["geometry"] is None)
json.dump({"type": "FeatureCollection", "source_url": url, "retrieved": "2026-08-30",
           "server_count": total, "oid_count": len(oids), "null_geometry": nogeom,
           "features": feats}, open(out, "w"))
ok = "OK" if len(feats) == total == len(oids) else "MISMATCH"
print(f"  {ok}: {len(feats)} features (count {total}, oids {len(oids)}), "
      f"{nogeom} null-geom -> {out}", file=sys.stderr)
