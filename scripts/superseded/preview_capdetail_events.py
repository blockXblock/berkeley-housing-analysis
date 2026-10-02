#!/usr/bin/env python3
"""preview_capdetail_events.py -- READ-ONLY report on the rung-3 facts the CapDetail harvest holds.
Writes NOTHING; opens every DB mode=ro.

The join and the selection come from scripts/capdetail_select.py, the SAME module the ingest
imports, so this preview cannot approve one thing while the write does another.

Rung 3 is `application_complete` (vocabulary_event_types id 3, "Application deemed complete by
staff") -- it already exists, so nothing here needs a schema change. What was missing is not a
column but IDENTITY: measured 2026-09-26, 100 of v2's dated application_complete events name no
record at all, which is why a project-level date had to be aggregated instead of selected.
See docs/methodology/identity_is_the_product.md.

  .venv/bin/python scripts/preview_capdetail_events.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import re
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from capdetail_select import (EV_APP_COMPLETE, accepted_task, load_rows,   # noqa: E402
                             select_rung3)
from housing_rules import to_canonical_apn                                 # noqa: E402  THE canon
from housing_rules.planning_record import role                             # noqa: E402

V2 = f"file:{ROOT/'databases/berkeley_housing_v2.db'}?mode=ro"
ASSESSOR = f"file:{ROOT/'databases/berkeley.db'}?mode=ro"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=None)
    args = ap.parse_args()
    d = ROOT / "scratch/2026-09-26_capdetail"
    src = args.jsonl or (sorted(glob.glob(str(d / "capdetail_reparsed_*.jsonl")))
                         or [str(d / "capdetail_parsed.jsonl")])[-1]
    rows = load_rows(src)
    db = sqlite3.connect(V2, uri=True)
    sel = select_rung3(rows, db)
    print(f"source {src}\nrecords {len(rows)}   "
          f"with a dated ACCEPTED disposition {len(sel['accepted_records'])}")

    import collections
    byrole = collections.Counter(role(r.get("record_type")) for r in sel["accepted_records"])
    print("  by record role:", dict(byrole.most_common()))

    j = sel["join"]
    print("\nWHICH PROJECT (two joins, neither trusted alone -- rule 4: APNs are not identity):")
    print(f"  both joins reach a project : {j['both']}   (project sets DISAGREE on {len(sel['disagree'])})")
    print(f"  address only               : {j['address_only']}")
    print(f"  canonical APN only         : {j['apn_only']}   <- reachable ONLY via the new APN")
    print(f"  neither -> no v2 project   : {j['no_project']}")
    for x in sel["disagree"][:5]:
        print(f"    disagree: {x[0]:16} {str(x[1])[:28]:28} addr->{x[2]} apn{x[3]}->{x[4]}")

    # standing stale-APN guard (CLAUDE.md rule 4): flag, never auto-re-point
    assessor = set()
    try:
        adb = sqlite3.connect(ASSESSOR, uri=True)
        for (a,) in adb.execute("SELECT APN FROM parcels WHERE APN IS NOT NULL"):
            try:
                assessor.add(to_canonical_apn(a, "alameda"))
            except Exception:
                pass
    except Exception as e:
        print("  (assessor unreadable, stale-APN guard SKIPPED:", e, ")")
    if assessor:
        stale = sorted({(r["record"], c) for r in sel["accepted_records"]
                        for c in (r.get("parcels_canonical") or []) if c and c not in assessor})
        print(f"  STALE-APN GUARD: {len(stale)} record APNs absent from the current assessor "
              f"-- flag for John, NEVER auto-re-point (re-platted and too-new look identical)")

    print("\nWHICH ACTION -- SELECTED from the primary application, never reduced over all records:")
    print(f"  one primary application (or one anchored by filed_date) : {len(sel['selected'])}")
    print(f"  NO primary application -> unknown with provenance       : {len(sel['no_primary'])}")
    print(f"  of those, a CHAIN resolved to its root                  : {len(sel['chains'])}")
    print(f"  SEVERAL, none anchored -> flagged, not written          : {len(sel['ambiguous'])}")
    print(f"  CONFLATED: separate applications sharing an address     : {len(sel['conflated'])}"
          f"   <- a DATA FINDING, not a selection")
    for pid, root, superseded in sel["chains"][:8]:
        print(f"    chain proj{pid:<5} root={root:16} superseded by {superseded}")
    for pid, recs, filed in sel["conflated"][:8]:
        print(f"    CONFLATED proj{pid:<5} unrelated primaries={recs} v2 filed_date={filed}")
    for pid, roles, recs in sel["no_primary"][:6]:
        print(f"    proj{pid:<5} roles present={roles} records={recs[:4]}")
    for pid, recs, filed in sel["ambiguous"][:6]:
        print(f"    proj{pid:<5} competing={recs} project filed_date={filed}")

    existing = collections.defaultdict(list)
    for pid, date in db.execute("SELECT project_id,event_date FROM project_events "
                                f"WHERE event_type_id={EV_APP_COMPLETE}"):
        existing[pid].append(date)
    buckets = collections.Counter()
    conflicts = []
    for pid, (rec, task) in sel["selected"].items():
        ex = existing.get(pid, [])
        if not ex:
            buckets["no event yet"] += 1
        elif all(e is None for e in ex):
            buckets["undated -> gains a date"] += 1
        elif task["status_date"] in ex:
            buckets["already dated, AGREES"] += 1
        else:
            buckets["already dated, DISAGREES"] += 1
            conflicts.append((pid, rec["record"], task["status_date"], [e for e in ex if e]))
    print(f"\nthe {len(sel['selected'])} selected facts vs what v2 holds now:")
    for k in ("no event yet", "undated -> gains a date", "already dated, AGREES",
              "already dated, DISAGREES"):
        print(f"  {k:28} {buckets[k]}")
    for c in conflicts[:8]:
        print(f"    proj{c[0]:<5} {c[1]:16} selected={c[2]}  v2 holds={c[3]}")

    lags, vs_due = [], []
    for r in sel["accepted_records"]:
        t = accepted_task(r)
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(r.get("list_date") or ""))
        if m and t["status_date"]:
            f = dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            g = (dt.date.fromisoformat(t["status_date"]) - f).days
            if 0 <= g < 2000:
                lags.append(g)
        if t["due_date"] and t["status_date"]:
            vs_due.append((dt.date.fromisoformat(t["status_date"])
                           - dt.date.fromisoformat(t["due_date"])).days)
    for v, lab in ((lags, "filed -> accepted"),
                   (vs_due, "accepted vs the city's OWN due date (negative = early)")):
        if v:
            print(f"\n  {lab}: n={len(v)} median={statistics.median(v):.0f}d "
                  f"mean={statistics.mean(v):.0f}d p90={sorted(v)[int(.9*len(v))-1]}d")

    print("\nNOTHING WRITTEN. All DBs opened mode=ro; the canonical DBs are chmod a-w.")
    print("Next: John's go-ahead -> scripts/migration/ingest_capdetail_events.py --commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
