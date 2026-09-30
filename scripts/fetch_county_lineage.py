"""READ-ONLY fetch of the Alameda Assessor's parcel-lineage layers (every row, every field, no geometry).
Each layer's download is checked against the County's own count (returnCountOnly) before it is kept."""
import json, hashlib, csv, time, urllib.request, urllib.parse, pathlib
BASE = "https://services5.arcgis.com/ROBnTHSNjoZ2Wm1P/arcgis/rest/services"
OUT = pathlib.Path("data/raw/county_parcel_lineage")
svc = json.load(urllib.request.urlopen(f"{BASE}?f=json", timeout=120))["services"]
names = sorted(x["name"] for x in svc if x["name"].startswith(("Assessor_Office_Deleted_Parcel_List", "Parcels_Inactivated_in_Roll_Year")))
def get(url, params):
    q = urllib.parse.urlencode(params)
    for a in range(3):
        try:
            with urllib.request.urlopen(f"{url}?{q}", timeout=120) as r:
                return json.load(r)
        except Exception as e:
            err = e; time.sleep(5)
    raise err
manifest = []
for n in names:
    meta = get(f"{BASE}/{n}/FeatureServer", {"f": "json"})
    ids = [t["id"] for t in meta.get("tables", []) + meta.get("layers", [])]
    assert len(ids) == 1, f"{n}: expected one table/layer, found {ids}"
    lay = f"{BASE}/{n}/FeatureServer/{ids[0]}/query"
    total = get(lay, {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    rows, off = [], 0
    while len(rows) < total:
        d = get(lay, {"where": "1=1", "outFields": "*", "returnGeometry": "false", "orderByFields": "OBJECTID",
                      "resultOffset": off, "resultRecordCount": 2000, "f": "json"})
        feats = d.get("features", [])
        if not feats: break
        rows += [f["attributes"] for f in feats]; off += len(feats)
    assert len(rows) == total, f"{n}: got {len(rows)} of the County's {total}"
    p = OUT / f"{n}.json"
    p.write_text(json.dumps({"layer": n, "source": lay.replace('/query',''), "fetched": time.strftime("%Y-%m-%d"),
                             "county_count": total, "rows": rows}))
    manifest.append([p.name, n, total, hashlib.sha256(p.read_bytes()).hexdigest()])
    print(f"{n}: {total} rows", flush=True)
with open(OUT / "manifest_2026-09-30.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["file", "layer", "rows", "sha256"]); w.writerows(manifest)
print("layers", len(manifest), "rows", sum(m[2] for m in manifest))
