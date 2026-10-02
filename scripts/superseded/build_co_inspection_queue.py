#!/usr/bin/env python3
"""Build the CO-determination inspection queue (Phase 1) for the existing Playwright harvester.

Why: Berkeley issues no traditional certificate of occupancy — it FINALS permits, and the moment that
happens is an inspection: `Building 1200 Building Final`, result `Approved`, with a date. That dated
event is the only first-class completion evidence we can get, and the APR reports completions BY YEAR,
so the date matters. The CPRA feed's alternatives are weaker: `Finaled Date` is reliable but absent on
402 of 915 units-adding permits, `Finaled Status='Finaled'` appears on 2,060 primary permits with NO
date (it grew 706 -> 985 in the 2023-25 window between two productions), and `Completed`/`Completed
Date` ship empty. `CO Required` (Yes on 810 permits) says a CO is REQUIRED, never that one issued.

Targets (Phase 1 — the APR core):
  - primary CPRA permits with UnitsAdded >= 2 and no inspection JSON yet, and
  - v2 permits carrying completion_verdict='ambiguous' (ADR-002) — the cases the feed could not settle.
CapDetail URLs come from the Accela date-range census, so no URL discovery pass is needed.

Writes a queue DB with the same schema `scripts/scrape_inspections.py` expects, in its own file so the
existing `databases/cic_recon_queue.db` is untouched. permit_id is synthetic and project_id is 0 for
permits v2 does not track (the harvester only reads permit_number + url).

Read-only with respect to every existing database.

Usage:  python scripts/build_co_inspection_queue.py [--out databases/co_inspection_queue_<date>.db]
Then:   .venv/bin/python scripts/scrape_inspections.py --queue-db <that file> --output-dir data/raw/accela_inspections
"""
import argparse, datetime as dt, glob, sqlite3, sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from multiunit_master_list import load_census                      # noqa: E402

INSPECTIONS = ROOT / "data/raw/accela_inspections"
V2 = ROOT / "databases/berkeley_housing_v2.db"
BASE = "https://aca-prod.accela.com"

SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_queue (
    id INTEGER PRIMARY KEY,
    permit_id INTEGER NOT NULL,
    permit_number TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    project_address TEXT,
    capid_triplet TEXT,
    url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    error_message TEXT,
    inspections_count INTEGER,
    output_file TEXT,
    created_at TEXT NOT NULL,
    succeeded_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_scrape_queue_status ON scrape_queue(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scrape_queue_permit_id ON scrape_queue(permit_id);
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--min-units", type=int, default=2)
    a = ap.parse_args()
    out = Path(a.out) if a.out else ROOT / f"databases/co_inspection_queue_{dt.date.today().isoformat()}.db"

    frames = [pd.read_excel(f, header=7) for f in glob.glob(str(ROOT / "data/raw/cpra-downloads/BP_Annual*.xlsx"))]
    df = pd.concat(frames).drop_duplicates("PermitNumber", keep="last")
    prim = df[~df.PermitNumber.astype(str).str.contains("-DEF|-REV", na=False)]
    units = pd.to_numeric(prim.UnitsAdded, errors="coerce").fillna(0)
    multi = set(prim[units >= a.min_units].PermitNumber)

    con = sqlite3.connect(V2)
    amb = {r[0] for r in con.execute(
        "select permit_number from permits where completion_verdict='ambiguous' and permit_number is not null")}
    v2meta = {r[0]: (r[1], r[2]) for r in con.execute(
        "select pm.permit_number, pm.project_id, f.address_display from permits pm "
        "join v_projects_flat f on f.project_id=pm.project_id where pm.permit_number is not null")}
    con.close()

    done = {p.stem for p in INSPECTIONS.glob("*.json")}
    census = load_census("Building", "Permit Number")

    rows, no_url = [], []
    for i, pn in enumerate(sorted((multi | amb) - done), start=1):
        href = (census.get(pn) or {}).get("capdetail_href")
        if not href or href == "None":
            no_url.append(pn)
            continue
        pid, addr = v2meta.get(pn, (0, (census.get(pn) or {}).get("Address")))
        rows.append((i, pn, pid, addr, BASE + href,
                     "multi_unit" if pn in multi else "ambiguous_verdict"))

    out.parent.mkdir(exist_ok=True)
    q = sqlite3.connect(out)
    q.executescript(SCHEMA)
    now = dt.datetime.now().isoformat(timespec="seconds")
    q.executemany("insert or ignore into scrape_queue "
                  "(permit_id, permit_number, project_id, project_address, url, status, created_at) "
                  "values (?,?,?,?,?,'pending',?)",
                  [(i, pn, pid or 0, addr, url, now) for i, pn, pid, addr, url, _ in rows])
    q.commit()
    print(f"{out}: {len(rows)} queued "
          f"({sum(1 for r in rows if r[5]=='multi_unit')} multi-unit, "
          f"{sum(1 for r in rows if r[5]=='ambiguous_verdict')} ambiguous-verdict)")
    print(f"  skipped — already harvested: {len((multi | amb) & done)}   no CapDetail URL in census: {len(no_url)}")
    if no_url:
        print(f"  no-URL permits (need a discovery pass): {' '.join(sorted(no_url)[:12])}")
    q.close()


if __name__ == "__main__":
    main()
