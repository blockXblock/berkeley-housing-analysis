#!/usr/bin/env python3
"""refresh_inspections.py — granular Accela inspection pulse for the active-construction permits.

For each construction/demolition building permit in the target list (built from AgencyCounter, which
sees the current permits v2's feed is blind to), discover its Accela CapDetail URL and scrape the
INSPECTION tab — the individual dated inspections (footing, framing, final, demolition…) with result
and date. The LAST inspection date per permit = the true recency pulse of physical activity.

Only city-permitted (private-developer) projects appear here; UC/BART self-permit and self-inspect, so
they have no city inspection records (media/field is the only source for those).

Input:  scratch/2026-08-27/granular_inspection_targets.csv (project_id,address,units,permit,status,desc)
Output: data/raw/accela_inspections/<permit>.json (per permit) + data/reference/inspection_pulse_2026-08-27.csv
Read-only. Run in the .venv: .venv/bin/python scripts/refresh_inspections.py
"""
import sys, os, json, csv, datetime, traceback

sys.path.insert(0, "experiments/accela_scrape")
from url_discovery_scraper import discover_url
from inspection_scraper import scrape_inspections

TARGETS = "scratch/2026-08-27/granular_inspection_targets.csv"
OUTDIR = "data/raw/accela_inspections"
PULSE = "data/reference/inspection_pulse_2026-08-27.csv"
STATE = "scratch/2026-08-27/inspection_refresh_state.json"


def last_inspection(inspections):
    """Most recent inspection (by date) → (date, type, result), or (None,None,None)."""
    def key(i):
        d = i.get("date", "")
        try:
            m, dd, y = d.split("/"); return f"{y}-{m}-{dd}"
        except Exception:
            return ""
    good = [i for i in inspections if i.get("date")]
    if not good:
        return (None, None, None)
    top = max(good, key=key)
    return (top.get("date"), top.get("type_code"), top.get("result"))


def main():
    rows = list(csv.DictReader(open(TARGETS)))
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}, "pulse": []}
    pulse = state["pulse"]
    print(f"granular inspection refresh: {len(rows)} permits")
    for r in rows:
        permit = r["permit"].strip()
        if permit in state["done"]:
            print(f"  {permit} done, skip"); continue
        rec = {"project_id": r["project_id"], "address": r["address"], "units": r["units"],
               "permit": permit, "permit_status": r["status"]}
        try:
            disc = discover_url(permit, module_hint="Building")
            url = (disc or {}).get("capdetail_url") if isinstance(disc, dict) else None
            if not url:
                rec.update(n_inspections=-1, last_date=None, last_type=None, last_result="no capdetail_url")
            else:
                res = scrape_inspections(permit, url, headless=True)
                insp = res.get("inspections", []) if isinstance(res, dict) else []
                json.dump(res, open(f"{OUTDIR}/{permit}.json", "w"))
                d, t, rslt = last_inspection(insp)
                rec.update(n_inspections=len(insp), last_date=d, last_type=t, last_result=rslt)
        except Exception as e:
            rec.update(n_inspections=-1, last_date=None, last_type=None, last_result=f"ERR {str(e)[:40]}")
            traceback.print_exc()
        pulse.append(rec)
        state["done"][permit] = True; state["pulse"] = pulse
        json.dump(state, open(STATE, "w"))
        with open(PULSE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rec.keys())); w.writeheader(); w.writerows(pulse)
        print(f"  {permit:<14} n={rec['n_inspections']:<3} last={rec['last_date']} {rec['last_type']} {rec['last_result']}")

    print(f"\n{'#'*60}\nINSPECTION PULSE -> {PULSE}")
    # per-project rollup: latest inspection across its permits
    proj = {}
    for p in pulse:
        pid = p["project_id"]
        if p.get("last_date") and (pid not in proj or p["last_date"] > proj[pid]["last_date"]):
            proj[pid] = p
    for pid, p in sorted(proj.items(), key=lambda kv: kv[1].get("last_date") or "", reverse=True):
        print(f"  proj{pid:<4} {p['address'][:22]:22} last on-site {p['last_date']} ({p['last_type']} / {p['last_result']})")


if __name__ == "__main__":
    main()
