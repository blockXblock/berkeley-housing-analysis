#!/usr/bin/env python3
"""
Planning-module BACKFILL — the entitlement universe 2015-01-01 .. 2025-05-31 (launched 2026-07-03).

Extends the fresh-permits harvest backward so the date_range store covers the ENTIRE audited
period. Same 4-day windows, same output dir/naming as sweep_recent_permits.py (no collisions:
date ranges differ), same append-only/skip-if-exists resumability, same one-auto-retry rule.
Planning module (sibling of backfill_building.py, which completed 2026-07-03). Purpose: the
entitlement layer citywide (ZP/UP/AP/DR/PLN filings + status); the front half of the pipeline
timeline; planning-stage denials/withdrawals; the ZP target list for harvest_affordability.py.

Run:  cd ~/berkeley-data && .venv/bin/python experiments/accela_scrape/backfill_planning.py
"""

import json
import pathlib
import sys
import time
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from date_range_discovery import discover_range

ROOT = pathlib.Path("~/berkeley-data").expanduser()
OUT = ROOT / "data" / "raw" / "accela" / "date_range"
LOG = OUT / "_sweep_log.jsonl"

WINDOWS = []
d = date(2015, 1, 1)   # 5th-RHNA-cycle start; city APR PDFs begin CY2015
END = date(2025, 5, 31)
while d <= END:
    e = min(d + timedelta(days=3), END)
    WINDOWS.append((d.strftime("%m/%d/%Y"), e.strftime("%m/%d/%Y"), f"{d.isoformat()}_{e.isoformat()}"))
    d = e + timedelta(days=1)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    done = skipped = failed = 0
    for start, end, tag in WINDOWS:
        path = OUT / f"Planning_{tag}.jsonl"
        if path.exists() and path.stat().st_size > 0:
            skipped += 1
            continue
        res = None
        for attempt in (1, 2):
            res = discover_range(start, end, "Planning", max_pages=400)
            if res["status"] == "ok" and res["rows"]:
                break
            time.sleep(5)
        with open(path, "w") as f:
            for r in res["rows"]:
                f.write(json.dumps(r) + "\n")
        with open(LOG, "a") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "module": "Planning",
                                "window": tag, "status": res["status"], "pages": res["pages"],
                                "rows": len(res["rows"]), "errors": res["errors"][:3]}) + "\n")
        done += 1
        failed += (res["status"] != "ok")
        print(f"Planning {tag}: {res['status']} pages={res['pages']} rows={len(res['rows']):,}"
              f"   [{done} done / {skipped} skipped / {failed} flagged]", flush=True)
        time.sleep(3)
    print(f"BACKFILL COMPLETE: {done} pulled, {skipped} skipped, {failed} flagged")


if __name__ == "__main__":
    run()
