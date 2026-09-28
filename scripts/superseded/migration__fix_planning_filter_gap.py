#!/usr/bin/env python3
# ============================ SEQUESTERED 2026-09-28 ============================
# DO NOT RUN. Original path: scripts/migration/fix_planning_filter_gap.py
# WHY: One-time gated v2 write adding the planning events the broken filter missed (applied 2026-09-28 in 8745def: 18 events). Its OLD_HOUSING regex existed only to compute that difference.
raise SystemExit("SEQUESTERED 2026-09-28 -- see header; original path scripts/migration/fix_planning_filter_gap.py")
# ================================================================================
"""fix_planning_filter_gap.py -- repair the v2 planning events the BROKEN housing filter missed.
PREVIEW BY DEFAULT; --commit needs John's go-ahead and an unlocked DB.

THE DEFECT. scripts/migration/ingest_planning_scope_a.py wrote 1,188 planning events into v2 using a
HOUSING pattern whose `\\bdwelling\\b` cannot match the plural "dwellings". 40 development records were
therefore never ingested -- including ZP2022-0046, 3000 Shattuck, 10 storeys, **166 dwellings**. The
corrected pattern now lives in housing_rules.planning_filter (queue 1,747 -> 1,787, 40 gained, 0 lost,
so the fix is purely ADDITIVE and cannot retract an existing event).

WHY A NEW GATED WRITE AND NOT A RE-RUN. CLAUDE.md's .py disposition rule: a DATA ERROR is a new gated
write, never a re-run of the applied script. Re-running the original would also re-derive the 1,147
records it already handled, risking duplicates for no benefit.

WHAT IT WRITES. One `application_submitted` event per missing record that (a) is a real application by
housing_rules.planning_record.role -- Zoning Research Letters are INQUIRIES and get nothing -- and
(b) joins to a v2 project by the rule-4c address canon or canonical APN. Each row NAMES ITS RECORD in
`summary`, because an event whose referent is unrecoverable is what created this mess
(docs/methodology/identity_is_the_product.md).

It does NOT write acceptance or entitlement events: those now come with real dates and identity from
the CapDetail harvest (ingest_capdetail_events.py), and writing dateless placeholders for them is
what forced `entitled_date` to be a MAX over events in the first place.

  .venv/bin/python scripts/migration/fix_planning_filter_gap.py            # preview
  .venv/bin/python scripts/migration/fix_planning_filter_gap.py --commit   # after John's go-ahead
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from capdetail_select import addr_key                                  # noqa: E402  rule-4c canon
from housing_rules import to_canonical_apn                             # noqa: E402  THE APN canon
from housing_rules.planning_filter import DEV, HOUSING                 # noqa: E402  corrected filter
from housing_rules.planning_record import role                         # noqa: E402

V2 = ROOT / "databases/berkeley_housing_v2.db"
EV_SUBMITTED = 2
CONF_HIGH = 1
OBSERVED_BY = "planning_filter_gap_fix@2026-09-26"
SOURCE = "Accela Planning list view (corrected housing filter)"


def iso(mdy) -> str | None:
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(mdy or "").strip())
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else None


def planning_records() -> dict:
    recs = {}
    for fn in glob.glob(str(ROOT / "data/raw/accela/date_range/Planning_*.jsonl")):
        for line in open(fn):
            try:
                d = json.loads(line)
            except Exception:
                continue
            n = str(d.get("Record Number") or "")
            if n:
                recs[n] = d
    return recs


def build_plan(db):
    recs = planning_records()

    def blob(d):
        return " ".join(str(d.get(f, "")) for f in ("Description", "Project Name", "Record Type"))

    # EXACTLY the records the BROKEN pattern missed -- new filter MINUS old filter. Not every record
    # the original ingest skipped: it also skipped records for want of a project join or a date, and
    # re-deriving those is a re-run of an applied write, not the repair of this defect. Scope stays on
    # the plural bug (measured: 40 gained, 0 lost).
    OLD_HOUSING = re.compile(
        r"(\b(dwelling|adu|jadu|duplex|triplex|fourplex|apartment|residence|residential|"
        r"middle housing|sb ?9|sb ?330|sb ?35|sb ?684|ab ?2011|town ?home|housing|single.family|"
        r"infill|live.?work)\b|\d+\s*[-\s]?\s*units?\b)", re.I)
    new_set = {n for n, d in recs.items() if DEV.match(n) and HOUSING.search(blob(d))}
    old_set = {n for n, d in recs.items() if DEV.match(n) and OLD_HOUSING.search(blob(d))}
    selected = new_set - old_set
    print(f"corrected filter {len(new_set)} · broken filter {len(old_set)} · "
          f"GAINED {len(selected)} (lost {len(old_set - new_set)} -- must be 0)")
    assert not (old_set - new_set), "the corrected filter LOST records; it must be additive only"

    # which records v2 already has an ingested event for
    named = set()
    for (s,) in db.execute("SELECT summary FROM project_events WHERE summary IS NOT NULL"):
        for m in re.finditer(r"\b([A-Z]{2,5}\d{4}-\d{3,4})\b", s):
            named.add(m.group(1))

    by_addr = collections.defaultdict(set)
    for pid, a in db.execute("SELECT project_id,address_display FROM v_projects_flat "
                             "WHERE address_display IS NOT NULL"):
        k = addr_key(a)
        if k:
            by_addr[k].add(pid)
    by_apn = collections.defaultdict(set)
    for pid, apn in db.execute("SELECT pp.project_id,p.apn_normalized FROM project_parcels pp "
                               "JOIN parcels p ON p.id=pp.parcel_id "
                               "WHERE p.apn_normalized IS NOT NULL"):
        by_apn[apn].add(pid)

    # the harvest gives each record its parcel (Planning CapDetail carries the APN)
    harvest = {}
    for f in sorted(glob.glob(str(ROOT / "scratch/2026-09-26_capdetail/capdetail_reparsed_*.jsonl"))):
        for line in open(f):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("record"):
                harvest[r["record"]] = r

    plan, skipped = [], collections.Counter()
    for n in sorted(selected - named):
        d = recs[n]
        rl = role(d.get("Record Type"))
        if rl in ("not_an_application", "unknown"):
            skipped[f"role={rl}"] += 1
            continue
        when = iso(d.get("Date"))
        if not when:
            skipped["no filing date"] += 1
            continue
        h = harvest.get(n) or {}
        pids = set(by_addr.get(addr_key(h.get("work_location")), set()))
        for c in (h.get("parcels_canonical") or []):
            if c:
                pids |= by_apn.get(c, set())
        if not pids:
            cells = d.get("_cells") or []
            a = next((c for c in reversed(cells) if re.match(r"^\s*\d+\s+\S", str(c))), "")
            pids = set(by_addr.get(addr_key(a), set()))
        if not pids:
            skipped["no v2 project"] += 1
            continue
        if len(pids) > 1:
            skipped["ambiguous project"] += 1
            continue
        pid = pids.pop()
        plan.append({"project_id": pid, "record": n, "event_date": when,
                     "summary": f"Application {n} filed",
                     "details": (f"{d.get('Record Type')}; status {d.get('Status')}; "
                                 f"{str(d.get('Description') or '')[:260]}"),
                     "role": rl})
    return plan, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    db = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    plan, skipped = build_plan(db)
    db.close()

    print(f"records the corrected filter adds that v2 has NO event for, and which resolve to a "
          f"single project: {len(plan)}")
    print("  not planned:", dict(skipped) or "none")
    for r in plan:
        print(f"  proj{r['project_id']:<5} {r['event_date']}  {r['summary']:34} [{r['role']}]")
        print(f"        {r['details'][:104]}")
    if not args.commit:
        print("\nPREVIEW ONLY -- nothing written. Purely ADDITIVE: 40 gained, 0 lost, so no existing "
              "event is retracted or changed.")
        return 0
    if not plan:
        print("\nnothing to write.")
        return 0

    snap = ROOT / f"databases/keep_snapshot_{time.strftime('%Y-%m-%d')}_pre-planning_filter_gap.db"
    if not snap.exists():
        shutil.copy2(V2, snap)
    print(f"\nsnapshot {snap.name} ({snap.stat().st_size:,} bytes)")
    w = sqlite3.connect(V2)
    if w.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit("integrity_check failed -- aborting")
    w.execute("PRAGMA foreign_keys=ON")
    before = w.execute("SELECT COUNT(*) FROM project_events WHERE observed_by=?",
                       (OBSERVED_BY,)).fetchone()[0]
    n = 0
    try:
        w.execute("BEGIN")
        for r in plan:
            cur = w.execute(
                "INSERT INTO project_events (project_id,event_type_id,event_date,"
                "event_date_precision,summary,details,confidence_type_id,is_inferred,"
                "source_type,source_url,observed_by,observed_at) "
                "VALUES (?,?,?,'exact',?,?,?,0,'city_portal',?,?,?)",
                (r["project_id"], EV_SUBMITTED, r["event_date"], r["summary"], r["details"],
                 CONF_HIGH, SOURCE, OBSERVED_BY, time.strftime("%Y-%m-%dT%H:%M:%S")))
            if cur.rowcount != 1:
                raise RuntimeError(f"rowcount {cur.rowcount} for proj{r['project_id']}")
            n += 1
        # verify the DELTA, not the total -- see ingest_capdetail_events.py for the failure this
        # prevents (a legitimate incremental run rolled back because the running total != this run).
        got = w.execute("SELECT COUNT(*) FROM project_events WHERE observed_by=?",
                        (OBSERVED_BY,)).fetchone()[0]
        if got != before + n:
            raise RuntimeError(f"verify failed: {before} before + {n} inserted != {got} present")
        w.commit()
        print(f"committed {n} events")
    except Exception as e:
        w.rollback()
        print(f"ROLLED BACK: {e}")
        return 1
    finally:
        w.close()
    fresh = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    print(f"fresh-connection fingerprint: "
          f"{fresh.execute('SELECT COUNT(*) FROM project_events WHERE observed_by=?', (OBSERVED_BY,)).fetchone()[0]}"
          f" rows by {OBSERVED_BY}; integrity "
          f"{fresh.execute('PRAGMA integrity_check').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
