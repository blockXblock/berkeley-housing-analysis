#!/usr/bin/env python3
"""Track D — per-record STATUS REFRESH against Accela's public CapDetail pages (read-only, no DB write).

Why: the date-range census (data/raw/accela/date_range/) lists records by FILING date with the status they
had when that window was scraped — older records keep a stale status forever. This script re-reads the
record's own CapDetail page for a target list and records: current record_status, permit_type_text,
work_location (the site address the census lacks for Planning rows), applicant_name.

Targets (default): from the latest data/derived/multiunit_records_<date>.csv — every record that is
  (a) Building in an active/pending status, or (b) Planning not in a terminal status, or (c) address-less.
  Or pass --records FILE (one record number per line) / --record ZP2026-0091.
URL: the record's capdetail_href from the census (complete CapDetail URL — no search/discovery needed).
Parsing: record_status_scraper.parse_record_info (the same 4 fields, same element ids).

Output (append-only discipline):
  data/raw/accela_record_status/<record>.json   — latest snapshot (overwritten; same shape as the 2026-05 files)
  data/raw/accela_record_status/_history.jsonl  — one line per fetch, never rewritten (the time series)
Harvester retry rule: one automatic retry on a non-200 / unparsed page; a twice-failed record is logged, not
concluded. Politeness: --sleep seconds between fetches (default 2).

Usage: python scripts/refresh_record_status.py [--date YYYY-MM-DD] [--records FILE] [--record N ...] [--sleep 2] [--dry-run]
"""
import argparse, csv, datetime as dt, glob, json, sys, time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from record_status_scraper import parse_record_info, USER_AGENT          # noqa: E402
from multiunit_master_list import load_census, ACTIVE_BUILDING           # noqa: E402

OUT = ROOT / "data/raw/accela_record_status"
HIST = OUT / "_history.jsonl"
BASE = "https://aca-prod.accela.com"
PLANNING_TERMINAL = {"Approved", "Closed", "Withdrawn", "Denied", "Void", "Expired"}
SCRAPER_VERSION = "refresh_record_status_v1.0"


def default_targets(date):
    files = sorted(glob.glob(str(ROOT / f"data/derived/multiunit_records_{date or '*'}.csv")))
    if not files:
        sys.exit("no multiunit_records_*.csv — run scripts/multiunit_master_list.py first")
    rows = list(csv.DictReader(open(files[-1])))
    picked = []
    for r in rows:
        active = (r["module"] == "Building" and r["status"] in ACTIVE_BUILDING) or \
                 (r["module"] == "Planning" and r["status"] not in PLANNING_TERMINAL)
        if active or not r["address"].strip():
            picked.append(r["record"])
    print(f"targets from {Path(files[-1]).name}: {len(picked)} of {len(rows)} records", file=sys.stderr)
    return picked


def fetch(session, url):
    r = session.get(url, timeout=30)
    if r.status_code != 200:
        return None, f"http {r.status_code}"
    info = parse_record_info(r.text)
    if not info.get("record_status"):
        return None, "no record_status on page"
    return info, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="which multiunit_records_<date>.csv to read (default: latest)")
    ap.add_argument("--records", type=Path, help="file with one record number per line")
    ap.add_argument("--record", action="append", default=[], help="a single record number (repeatable)")
    ap.add_argument("--sleep", type=float, default=2.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    targets = a.record or (a.records.read_text().split() if a.records else default_targets(a.date))
    census = {}
    census.update(load_census("Building", "Permit Number"))
    census.update(load_census("Planning", "Record Number"))

    todo, missing = [], []
    for rec in dict.fromkeys(targets):
        href = (census.get(rec) or {}).get("capdetail_href")
        if href and href != "None":
            todo.append((rec, BASE + href))
        else:
            missing.append(rec)
    print(f"{len(todo)} with a CapDetail URL, {len(missing)} without (skipped): {missing[:8]}", file=sys.stderr)
    if a.dry_run:
        for rec, u in todo[:10]:
            print(rec, u)
        return

    OUT.mkdir(parents=True, exist_ok=True)
    s = requests.Session(); s.headers["User-Agent"] = USER_AGENT
    ok = failed = changed = 0
    for i, (rec, url) in enumerate(todo, 1):
        info = err = None
        for attempt in (1, 2):                                   # retry rule
            info, err = fetch(s, url)
            if info:
                break
            time.sleep(5)
        now = dt.datetime.now().isoformat(timespec="seconds")
        prev = None
        pf = OUT / f"{rec}.json"
        if pf.exists():
            try: prev = json.load(open(pf)).get("record_status")
            except Exception: prev = None
        entry = {"permit_number": rec, "capdetail_url": url, **(info or {}),
                 "scraped_at": now, "scraper_version": SCRAPER_VERSION,
                 "census_status": census[rec].get("Status"), "census_status_asof": census[rec].get("_status_asof"),
                 "error": err}
        with open(HIST, "a") as f:
            f.write(json.dumps(entry) + "\n")
        if info:
            ok += 1
            json.dump(entry, open(pf, "w"), indent=1)
            flag = ""
            if info["record_status"] != census[rec].get("Status"):
                changed += 1; flag = f"  ← census had '{census[rec].get('Status')}'"
            print(f"[{i}/{len(todo)}] {rec:14} {info['record_status']:28} {str(info.get('work_location') or '')[:32]:32}{flag}")
        else:
            failed += 1
            print(f"[{i}/{len(todo)}] {rec:14} FAILED twice: {err}")
        time.sleep(a.sleep)
    print(f"\nrefreshed {ok}, failed {failed}, status changed vs census {changed}, no-URL {len(missing)}")


if __name__ == "__main__":
    main()
