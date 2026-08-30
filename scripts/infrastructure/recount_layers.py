#!/usr/bin/env python3
"""Re-probe counts for every layer in the inventory, gently (low concurrency),
capturing the FULL error object so 'no count' is diagnosable."""
import json, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

INV = "data/raw/infrastructure/berkeley_arcgis_inventory_2026-08-30.json"
d = json.load(open(INV)); L = d["layers"]
UA = {"User-Agent": "berkeley-data research (john.gage@gmail.com)"}

def count(l):
    u = l["url"] + "/query?" + urllib.parse.urlencode(
        {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    last = None
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
                body = r.read().decode("utf-8", "replace")
            j = json.loads(body)
            if "count" in j:
                l["count"], l["count_error"] = j["count"], None
                return l
            last = json.dumps(j)[:300]
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 + 2 * i)
    l["count"], l["count_error"] = None, last
    return l

with ThreadPoolExecutor(max_workers=3) as ex:
    out = list(ex.map(count, L))
    for i, l in enumerate(out):
        if i % 50 == 0: print(f"  {i}/{len(out)}", file=sys.stderr, flush=True)

d["layers"] = out
d["counts_reprobed"] = "2026-08-30"
json.dump(d, open(INV, "w"), indent=1)
ok = sum(1 for l in out if isinstance(l.get("count"), int))
print(f"done: {ok}/{len(out)} layers returned a count", file=sys.stderr)
