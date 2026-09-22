#!/usr/bin/env python3
"""
Date-range sweep runner — fresh-permits harvest for the mayor presentation (Day 1, 2026-07-03).

Walks month windows 2025-06 .. 2026-07 for Building + Planning via
date_range_discovery.discover_range, persisting each (module, month) as JSONL to
data/raw/accela/date_range/<module>_<YYYY-MM>.jsonl — APPEND-ONLY at the file level:
an existing non-empty window file is SKIPPED (resumable; delete a file to re-pull it).

HARVESTER RETRY RULE: one automatic retry per window on a non-ok/0-row result;
a window that fails twice is recorded in the run log and left for manual retry.
"""

import json
import pathlib
import sys
import time
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from date_range_discovery import discover_range

ROOT = pathlib.Path("~/berkeley-data").expanduser()
OUT = ROOT / "data" / "raw" / "accela" / "date_range"
LOG = OUT / "_sweep_log.jsonl"

from datetime import timedelta
import argparse
# Re-runnable: --start/--end (ISO dates) extend the store forward; defaults = the original 2025-06 .. 2026-07-03
# sweep. 2026-09-21: re-pointed at 2026-07-04 .. today to refresh the census (existing windows are skipped).
_ap = argparse.ArgumentParser()
_ap.add_argument("--start", default="2025-06-01")
_ap.add_argument("--end", default="2026-07-03")
_args = _ap.parse_args()
WINDOWS = []
d = date.fromisoformat(_args.start)
END = date.fromisoformat(_args.end)
while d <= END:
    e = min(d + timedelta(days=3), END)          # 4-day windows: months truncated (2026-07-03)
    WINDOWS.append((d.strftime("%m/%d/%Y"), e.strftime("%m/%d/%Y"), f"{d.isoformat()}_{e.isoformat()}"))
    d = e + timedelta(days=1)

MODULES = ["Building", "Planning"]


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for module in MODULES:
        for start, end, tag in WINDOWS:
            path = OUT / f"{module}_{tag}.jsonl"
            if path.exists() and path.stat().st_size > 0:
                print(f"skip {path.name} (exists)")
                continue
            res = None
            for attempt in (1, 2):                     # retry rule: 0-result != absence until retried
                res = discover_range(start, end, module, max_pages=400)
                if res["status"] == "ok" and res["rows"]:
                    break
                print(f"  attempt {attempt} for {module} {tag}: {res['status']} rows={len(res['rows'])}")
                time.sleep(5)
            with open(path, "w") as f:
                for r in res["rows"]:
                    f.write(json.dumps(r) + "\n")
            entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "module": module, "window": tag,
                     "status": res["status"], "pages": res["pages"], "rows": len(res["rows"]),
                     "errors": res["errors"][:3]}
            with open(LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
            print(f"{module} {tag}: {res['status']} pages={res['pages']} rows={len(res['rows']):,}")
            time.sleep(3)                              # politeness between windows
    print("SWEEP COMPLETE")


if __name__ == "__main__":
    run()
