#!/usr/bin/env python3
"""harvest_agencycounter.py — status harvest via the AgencyCounter/Building Eye JSON API.

berkeley.agencycounter.com mirrors Berkeley's Accela permit data as clean JSON, searchable by address,
daily-fresh, with full status + review workflow. This replaces the broken aca-prod Building address-search
and the fragile postback scraper for STATUS reconciliation. Read-only; writes only a CSV we then adjudicate
against v2 status_label (the v2 write stays a separate gated step; NO auto-labelling here).

API (reverse-engineered + verified 2026-08-27; header 'Agency-Counter-Tenant: berkeley'):
  POST /api/search/location {___address, ___viewport}          -> located parcels (GUIDs)
  POST /api/search/detail   {___address, ___viewport, ___location:[guid...]} -> records[]
Each record: agency_reference (permit#), module_code, record_type, status_text, record_date,
status_date, closed_date, description, total_fee, workflow[].

COMPLETENESS CAVEAT (measured): address-lookup misses permits filed under a CHANGED parcel/address
(re-platting) — 2538 Durant returns only pre-demolition permits, not its new 8-story BP. The harvester
FLAGS such cases (newest record older than the project's v2 activity) rather than silently dropping them.

Run: /opt/miniconda3/envs/jupyter_env/bin/python scripts/harvest_agencycounter.py [--ids 1,2] [--all-nonterminal]
Resumable; polite. Output: data/reference/agencycounter_status_2026-08-27.csv
"""
import sys, os, re, json, time, random, argparse, sqlite3
import requests
import pandas as pd

DB = "databases/berkeley_housing_v2.db"
OUT = "data/reference/agencycounter_status_2026-08-27.csv"
STATE = "scratch/2026-08-27/agencycounter_state.json"
BASE = "https://berkeley.agencycounter.com"
HDRS = {"Agency-Counter-Tenant": "berkeley", "Content-Type": "application/json",
        "Accept": "application/json", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
VIEWPORT = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon",
    "coordinates": [[[-122.34, 37.835], [-122.234, 37.835], [-122.234, 37.907],
                     [-122.34, 37.907], [-122.34, 37.835]]]}, "properties": {}}]}
NONTERMINAL = ("In Review", "Entitled", "Under Construction", "Permitted", "Pre-Application", "Stalled")
NEWCON = re.compile(r"new construction|new (?:\d+-?story|multi|residential|building|dwelling)|construct", re.I)
DEMO = re.compile(r"\bdemol", re.I)
MINOR = re.compile(r"washer|dryer|water heater|reroof|re-roof|roofing|window|seismic|retrofit|solar|"
                   r"photovolt|\bpv\b|electric|plumb|mechanical|hvac|sign\b|fence|deck\b|temporary power", re.I)


def norm_addr(a):
    a = str(a).upper().strip()
    a = re.sub(r"\s+", " ", a)
    # AgencyCounter wants the suffix spelled: ST->STREET? No — verified "2538 DURANT AVE" works. Keep as-is.
    return a


def guids_from(loc_json):
    out = []
    def w(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and len(v) == 36 and v.count("-") == 4:
                    out.append(v)
                w(v)
        elif isinstance(o, list):
            for x in o:
                w(x)
    w(loc_json)
    return list(dict.fromkeys(out))


def fetch_records(sess, addr):
    """Return the AgencyCounter records[] for an address (may be empty)."""
    body = {"___address": addr, "___viewport": VIEWPORT}
    loc = sess.post(f"{BASE}/api/search/location", json=body, timeout=30)
    guids = guids_from(loc.json()) if loc.ok else []
    if not guids:
        return []
    det = sess.post(f"{BASE}/api/search/detail", json={**body, "___location": guids}, timeout=30)
    data = det.json().get("data", {}) if det.ok else {}
    return data.get("details", []) if isinstance(data, dict) else []


def summarize(recs, v2_label):
    """Compact per-project signal from the records. Informative only — no auto-label."""
    def dt(r):
        return (r.get("status_date") or r.get("record_date") or "")[:10]
    bld = [r for r in recs if r.get("module_code") == "building"]
    pln = [r for r in recs if r.get("module_code") == "planning"]
    newest = max(recs, key=dt) if recs else None
    # major (new-construction / demolition) building permits, excluding minor work
    major = [r for r in bld if (NEWCON.search(r.get("description", "") or "") or DEMO.search(r.get("description", "") or ""))
             and not MINOR.search(r.get("description", "") or "")]
    demo = [r for r in bld if DEMO.search(r.get("description", "") or "")]
    newcon = [r for r in bld if NEWCON.search(r.get("description", "") or "") and not DEMO.search(r.get("description", "") or "")]
    def latest_status(rs):
        return (max(rs, key=dt).get("status_text"), max(rs, key=dt).get("agency_reference"), dt(max(rs, key=dt))) if rs else (None, None, None)
    ns, nref, nd = latest_status(newcon)
    ds, dref, dd = latest_status(demo)
    ps, pref, pd_ = latest_status(pln)
    newest_year = int(dt(newest)[:4]) if newest and dt(newest)[:4].isdigit() else 0
    flag = ""
    if not recs:
        flag = "NO_RECORDS_at_address"
    elif not major and v2_label in ("Under Construction", "Permitted", "Entitled"):
        flag = "only_minor_or_old_permits (possible re-platted parcel)"
    elif newest_year and newest_year < 2023 and v2_label in ("Under Construction", "Permitted"):
        flag = f"stale_newest_{newest_year}"
    return {"n_records": len(recs), "n_building": len(bld), "n_planning": len(pln),
            "newcon_status": ns, "newcon_ref": nref, "newcon_date": nd,
            "demo_status": ds, "demo_ref": dref, "demo_date": dd,
            "planning_status": ps, "planning_ref": pref, "planning_date": pd_,
            "newest_ref": newest.get("agency_reference") if newest else None,
            "newest_status": newest.get("status_text") if newest else None,
            "newest_date": dt(newest) if newest else None, "flag": flag}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids"); ap.add_argument("--all-nonterminal", action="store_true")
    a = ap.parse_args()
    v = sqlite3.connect(DB)
    if a.all_nonterminal:
        ph = ",".join(f"'{s}'" for s in NONTERMINAL)
        tgt = pd.read_sql(f"SELECT project_id, address_display, total_units, status_label FROM v_projects_flat "
                          f"WHERE status_label IN ({ph}) ORDER BY total_units DESC", v)
    else:
        ids = [int(x) for x in (a.ids or "").split(",") if x.strip()]
        tgt = pd.read_sql(f"SELECT project_id, address_display, total_units, status_label FROM v_projects_flat "
                          f"WHERE project_id IN ({','.join(map(str,ids)) or '0'})", v)
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}, "rows": []}
    rows = state["rows"]
    sess = requests.Session(); sess.headers.update(HDRS)
    print(f"targets: {len(tgt)}")
    for _, pr in tgt.iterrows():
        pid = int(pr.project_id)
        if str(pid) in state["done"]:
            continue
        addr = norm_addr(pr.address_display)
        try:
            recs = fetch_records(sess, addr)
        except Exception as e:
            recs = []; print(f"  proj{pid} {addr}: ERR {str(e)[:50]}")
        s = summarize(recs, pr.status_label)
        row = {"project_id": pid, "address": pr.address_display, "units": pr.total_units,
               "v2_status": pr.status_label, **s}
        rows.append(row)
        state["done"][str(pid)] = True; state["rows"] = rows
        json.dump(state, open(STATE, "w"))
        pd.DataFrame(rows).to_csv(OUT, index=False)
        print(f"  proj{pid:<4} {str(pr.address_display)[:22]:22} v2={pr.status_label:<18} "
              f"recs={s['n_records']:<2} newest={s['newest_ref']} {s['newest_status']} {s['flag']}")
        time.sleep(random.uniform(0.6, 1.4))
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"\n{'#'*60}\nAgencyCounter status -> {OUT} ({len(df)} projects)")
    print("flags:", df.flag.value_counts().to_dict())


if __name__ == "__main__":
    main()
