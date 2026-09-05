#!/usr/bin/env python3
"""harvest_permit_fees.py — per-permit fee snapshot from AgencyCounter, for JN-L (fiscal flows).

JN-L notes the itemized developer/impact/in-lieu fees are "NOT MATERIALIZED in v2 (data gap)". AgencyCounter
carries `total_fee` per permit (the amount charged), which fills that gap at the permit grain. This harvests
it to a DATED SNAPSHOT (reproducible — JN-L reads the file, not a live call), for the reportable development
projects (non-UC, >=20 units). Read-only. One row per building permit with a fee.

Output: data/reference/permit_fees_<date>.csv  (project_id, address, units, status_label, permit, module,
        record_type, permit_status, record_date, total_fee, description)
Run in the .venv: .venv/bin/python scripts/harvest_permit_fees.py
"""
import sqlite3, json, os, time, random, datetime
import requests, pandas as pd

DB = "databases/berkeley_housing_v2.db"
DATE = "2026-09-01"
OUT = f"data/reference/permit_fees_{DATE}.csv"
STATE = f"scratch/2026-09-01/permit_fees_state.json"
BASE = "https://berkeley.agencycounter.com"
HDRS = {"Agency-Counter-Tenant": "berkeley", "Content-Type": "application/json",
        "Accept": "application/json", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
VP = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon",
      "coordinates": [[[-122.34, 37.835], [-122.234, 37.835], [-122.234, 37.907],
                       [-122.34, 37.907], [-122.34, 37.835]]]}, "properties": {}}]}


def guids(o, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and len(v) == 36 and v.count("-") == 4:
                acc.append(v)
            guids(v, acc)
    elif isinstance(o, list):
        for x in o:
            guids(x, acc)
    return acc


def main():
    v = sqlite3.connect(DB)
    ucp = {r[0] for r in v.execute("SELECT c.project_id FROM project_classifications c "
           "JOIN vocabulary_classification_types t ON t.id=c.classification_type_id WHERE t.code='uc_project'")}
    tgt = pd.read_sql("SELECT project_id,address_display,total_units,status_label FROM v_projects_flat "
                      "WHERE total_units>=20 ORDER BY total_units DESC", v)
    tgt = tgt[~tgt.project_id.isin(ucp)]
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}, "rows": []}
    rows = state["rows"]
    s = requests.Session(); s.headers.update(HDRS)
    print(f"fee harvest: {len(tgt)} reportable projects (>=20u, non-UC)")
    for _, pr in tgt.iterrows():
        pid = int(pr.project_id)
        if str(pid) in state["done"]:
            continue
        addr = str(pr.address_display).upper()
        try:
            loc = s.post(f"{BASE}/api/search/location", json={"___address": addr, "___viewport": VP}, timeout=30).json()
            g = list(dict.fromkeys(guids(loc, [])))
            det = s.post(f"{BASE}/api/search/detail", json={"___address": addr, "___viewport": VP, "___location": g}, timeout=30).json()
            recs = det.get("data", {}).get("details", []) if isinstance(det.get("data"), dict) else []
        except Exception as e:
            recs = []; print(f"  proj{pid} {addr}: ERR {str(e)[:40]}")
        n = 0
        for r in recs:
            if r.get("module_code") != "building":
                continue
            fee = r.get("total_fee") or 0
            if fee <= 0:
                continue
            rows.append({"project_id": pid, "address": pr.address_display, "units": pr.total_units,
                         "status_label": pr.status_label, "permit": r.get("agency_reference"),
                         "record_type": r.get("record_type"), "permit_status": r.get("status_text"),
                         "record_date": (r.get("record_date") or "")[:10], "total_fee": round(float(fee), 2),
                         "description": (r.get("description", "") or "")[:80]})
            n += 1
        state["done"][str(pid)] = True; state["rows"] = rows
        json.dump(state, open(STATE, "w"))
        pd.DataFrame(rows).to_csv(OUT, index=False)
        print(f"  proj{pid:<4} {str(pr.address_display)[:22]:22} {int(pr.total_units):>4}u  {n} fee-bearing permits")
        time.sleep(random.uniform(0.5, 1.2))
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"\n{'#'*56}\nPERMIT FEES -> {OUT}")
    print(f"  {len(df)} fee-bearing building permits across {df.project_id.nunique()} projects")
    print(f"  total fees: ${df.total_fee.sum():,.0f}")


if __name__ == "__main__":
    main()
