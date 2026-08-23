#!/usr/bin/env python3
"""discover_planning_records.py — for projects whose Planning (ZP/DRCP) record we do NOT hold, find
candidate entitlement records by ADDRESS, and emit a harvest queue.

Read-only discovery. For each project: address-search the Planning module (the 2026-08-23 date-fill
fix makes this work), collect the plan-bearing candidate records (ZP/UP/DRCP/DRCF/LMSAP), rank newest-
first, cap a few per project, and write a queue CSV (project_id, permit, address, module=Planning) to
feed harvest_by_record.py. The harvester's classifier then filters each candidate to real plan sets.

Avoids the earlier crawler's session-contamination bug by doing ONLY searches (no attachment-grid
loads interleaved) and a FRESH browser context per project. Run in .venv:
  .venv/bin/python scripts/discover_planning_records.py --projects 141,143,144,154,157,5,146,148,149
"""
import sys, os, time, re, argparse, random
import pandas as pd, sqlite3

sys.path.insert(0, "experiments/accela_scrape")
from harvest_address import search_by_address
from playwright.sync_api import sync_playwright

OUT = "scratch/2026-08-23/phase2_discovered_queue.csv"
SUFFIXES = {"AVE", "ST", "WAY", "SQ", "BLVD", "DR", "RD", "LN", "CT", "PL", "TER", "CIR",
            "PATH", "WALK", "PKWY", "PLZ", "ROW", "AVENUE", "STREET"}
PLAN_PREFIX_RANK = {"ZP": 0, "UP": 1, "AUP": 1, "DRCP": 2, "DRCF": 2, "LMSAP": 3}  # plan-bearing only
CAP = 3   # newest plan-bearing candidates per project


def parse_addr(addr):
    toks = str(addr).upper().split()
    if not toks or not toks[0][0].isdigit():
        return None, str(addr)
    no = re.sub(r"\D", "", toks[0])
    rest = toks[1:]
    if rest and rest[-1] in SUFFIXES:
        rest = rest[:-1]
    return no, " ".join(rest)


def prefix(p):
    m = re.match(r"([A-Z]+)", p or ""); return m.group(1) if m else ""


def year(p):
    m = re.search(r"(\d{4})", p or ""); return int(m.group(1)) if m else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", required=True, help="comma-separated project ids")
    a = ap.parse_args()
    pids = [int(x) for x in a.projects.split(",") if x.strip()]

    v2 = sqlite3.connect("databases/berkeley_housing_v2.db")
    flat = pd.read_sql("SELECT project_id, address_display FROM v_projects_flat", v2).set_index("project_id").address_display.to_dict()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rows = []
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    try:
        for pid in pids:
            addr = flat.get(pid, "")
            no, name = parse_addr(addr)
            ctx = browser.new_context()   # FRESH context per project — no session bleed
            page = ctx.new_page()
            try:
                res = search_by_address(page, name, no, module="Planning", errors=[])
                recs = res.get("records", [])
            except Exception as e:
                recs = []; print(f"proj{pid} search err: {str(e)[:50]}")
            finally:
                ctx.close()
            cands = [r for r in recs if prefix(r.get("permit_number_displayed", "")) in PLAN_PREFIX_RANK]
            cands.sort(key=lambda r: (PLAN_PREFIX_RANK[prefix(r["permit_number_displayed"])],
                                      -year(r["permit_number_displayed"])))
            picked = cands[:CAP]
            print(f"proj{pid} {addr}: {len(recs)} recs, {len(cands)} plan-bearing -> "
                  f"{[r['permit_number_displayed'] for r in picked]}")
            for r in picked:
                rows.append(dict(project_id=pid, permit=r["permit_number_displayed"], address=addr, module="Planning"))
            time.sleep(random.uniform(2, 4))
    finally:
        browser.close(); p.stop()

    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\ndiscovered {len(rows)} candidate records / {len({r['project_id'] for r in rows})} projects -> {OUT}")


if __name__ == "__main__":
    main()
