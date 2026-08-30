#!/usr/bin/env python3
"""Walk the Berkeley ArcGIS REST server: every folder -> service -> layer,
with a returnCountOnly feature count for each queryable layer. Read-only."""
import json, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = "https://gis.cityofberkeley.info/arcgis/rest/services"
UA = {"User-Agent": "berkeley-data research (john.gage@gmail.com)"}

def get(url, params=None, tries=2, timeout=45):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e; time.sleep(1)
    return {"__error__": str(last)}

def walk_folders(folder=""):
    url = ROOT + ("/" + folder if folder else "")
    d = get(url, {"f": "json"})
    out = [(folder, s["name"], s["type"]) for s in d.get("services", [])]
    for f in d.get("folders", []):
        out += walk_folders(f)
    return out

services = [s for s in walk_folders() if s[2] in ("MapServer", "FeatureServer")]
print(f"# map/feature services: {len(services)}", file=sys.stderr, flush=True)

def do_service(item):
    folder, name, stype = item
    svc_url = f"{ROOT}/{name}/{stype}"
    meta = get(svc_url, {"f": "json"})
    if "__error__" in meta or "error" in meta:
        return [{"folder": folder, "service": name, "type": stype, "url": svc_url,
                 "error": meta.get("__error__") or str(meta.get("error"))}]
    return [(folder, name, stype, svc_url, l) for l in
            (meta.get("layers") or []) + (meta.get("tables") or [])]

with ThreadPoolExecutor(max_workers=8) as ex:
    svc_results = list(ex.map(do_service, services))

layers, errors = [], []
for res in svc_results:
    for r in res:
        (errors if isinstance(r, dict) else layers).append(r)
print(f"# layers to probe: {len(layers)} ({len(errors)} service errors)", file=sys.stderr, flush=True)

def do_layer(t):
    folder, name, stype, svc_url, lyr = t
    lid = lyr.get("id"); lurl = f"{svc_url}/{lid}"
    lmeta = get(lurl, {"f": "json"})
    cnt = get(lurl, {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    rec = {"folder": folder, "service": name, "type": stype, "layer_id": lid,
           "layer_name": lyr.get("name"), "url": lurl,
           "count": cnt.get("count"),
           "count_error": cnt.get("__error__") or (cnt.get("error") or {}).get("message"),
           "geometry_type": lmeta.get("geometryType"),
           "sublayer_of": lyr.get("parentLayerId"),
           "fields": [f.get("name") for f in (lmeta.get("fields") or [])],
           "description": (lmeta.get("description") or "")[:600]}
    print(f"{rec['count']!s:>8}  {name}/{stype}/{lid}  {rec['layer_name']}", file=sys.stderr, flush=True)
    return rec

with ThreadPoolExecutor(max_workers=12) as ex:
    inventory = list(ex.map(do_layer, layers))

out = "data/raw/infrastructure/berkeley_arcgis_inventory_2026-08-30.json"
json.dump({"swept": "2026-08-30", "root": ROOT, "service_errors": errors,
           "layers": inventory}, open(out, "w"), indent=1)
print(f"\nwrote {out}: {len(inventory)} layers, {len(errors)} service errors", file=sys.stderr)
