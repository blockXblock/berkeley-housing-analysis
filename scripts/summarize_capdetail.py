#!/usr/bin/env python3
"""summarize_capdetail.py -- the harvest's VOCABULARY and COVERAGE report.

Deliberately NOT a second rung-3 report. preview_capdetail_events.py owns the join, the selection
and the intervals (both it and the ingest import scripts/capdetail_select.py, so there is exactly one
implementation of "which action is rung 3"). Two scripts computing the same number differently is how
a project ends up with outputs that contradict each other, which is what the 2026-09-26 machinery
audit found across 304 scripts.

What this owns instead, and nothing else does:
  * the WORKFLOW TASK and DISPOSITION vocabulary the city actually uses, per record type -- this is
    how a new disposition string surfaces as a gap rather than being silently bucketed by a
    classifier that has never seen it;
  * which dispositions are UNMAPPED by the rung rules, listed explicitly;
  * per-record-type coverage: how many records carry a workflow at all.

Read-only; reads the reparsed harvest JSONL and writes nothing.
  .venv/bin/python scripts/summarize_capdetail.py
"""
from __future__ import annotations

import argparse
import collections
import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from capdetail_select import ACCEPTED, ACCEPT_TASK, load_rows   # noqa: E402
from housing_rules.planning_record import role                 # noqa: E402

# the rung rules' known dispositions. Anything outside these is reported as UNMAPPED, never guessed.
KNOWN = [re.compile(p, re.I) for p in (
    r"^application complete$", r"incomplete pending applicant", r"^approved", r"^denied",
    r"^withdrawn", r"^expired", r"^complete", r"^issued", r"^finaled", r"^no appeal",
    r"^resubmittal pending", r"^continued", r"^eir required", r"^no notice required",
    r"^note$", r"^tbd$")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=None)
    args = ap.parse_args()
    d = ROOT / "scratch/2026-09-26_capdetail"
    src = args.jsonl or (sorted(glob.glob(str(d / "capdetail_reparsed_*.jsonl")))
                         or [str(d / "capdetail_parsed.jsonl")])[-1]
    rows = load_rows(src)
    print(f"source {src}\nrecords {len(rows)}\n")

    print("COVERAGE -- records carrying a workflow, by record type:")
    tot = collections.Counter(r.get("record_type") for r in rows)
    wf = collections.Counter(r.get("record_type") for r in rows if r.get("processing_status"))
    acc = collections.Counter(r.get("record_type") for r in rows
                              if any(t.get("status") and ACCEPTED.search(t["status"])
                                     and ACCEPT_TASK.search(t["task"])
                                     for t in (r.get("processing_status") or [])))
    for t, n in tot.most_common():
        print(f"  {str(t)[:42]:44} {wf[t]:4}/{n:4} with a workflow · {acc[t]:4} with a dated "
              f"ACCEPTED · role={role(t)}")

    print("\nWORKFLOW TASKS the city uses (count = dispositions recorded against that task):")
    task = collections.Counter()
    for r in rows:
        for x in (r.get("processing_status") or []):
            task[x["task"]] += 1
    for t, n in task.most_common(20):
        print(f"  {n:6}  {t[:70]}")

    print("\nDISPOSITION vocabulary:")
    vocab = collections.Counter()
    for r in rows:
        for x in (r.get("processing_status") or []):
            if x["status"]:
                vocab[x["status"]] += 1
    for v, n in vocab.most_common(24):
        mapped = any(p.search(v) for p in KNOWN)
        print(f"  {n:6}  {'   ' if mapped else '?? '}{v[:64]}")
    unmapped = sorted(v for v in vocab if not any(p.search(v) for p in KNOWN))
    print(f"\n  UNMAPPED dispositions ({len(unmapped)}) -- decide these deliberately, "
          f"do not let a classifier bucket them:")
    for v in unmapped:
        print(f"    {vocab[v]:5}  {v[:70]}")

    # THE FALSE-NEGATIVE GUARD. The city labels the same fact differently by record type: a Zoning
    # Permit's Completeness Review says "Application Complete", a Zoning Certificate Building
    # Permit's says plain "Complete", and Design Review Staff Level uses both plus "Void". The rung-3
    # rule matches only "Application Complete", which is correct for the primary-application path it
    # reads -- but if a Zoning Permit ever used the bare "Complete", the acceptance would be missed
    # in SILENCE. So any primary_application record whose Completeness Review carries a disposition
    # the rule does not recognise is printed here as a GAP to decide, not absorbed by widening the
    # regex on a guess (widening it would also pull in ministerial "Complete", which may mean the
    # clearance finished rather than the application being accepted -- a different fact).
    print("\nFALSE-NEGATIVE GUARD -- primary_application records whose Completeness Review has a")
    print("disposition the rung-3 rule does NOT match (should be only refusals/pending):")
    gaps = collections.Counter()
    for r in rows:
        if role(r.get("record_type")) != "primary_application":
            continue
        for x in (r.get("processing_status") or []):
            if ACCEPT_TASK.search(x["task"]) and x["status"] and not ACCEPTED.search(x["status"]):
                gaps[x["status"]] += 1
    if gaps:
        for v, n in gaps.most_common():
            flag = "  <-- LOOKS LIKE AN ACCEPTANCE, DECIDE IT" if re.match(
                r"^(complete|completed|deemed complete|accepted)", v, re.I) else ""
            print(f"    {n:5}  {v[:60]}{flag}")
    else:
        print("    none -- every primary-application completeness disposition is recognised")

    print("\nOTHER FIELDS the harvest recovered:")
    for f in ("parcels_raw", "related_records", "owner", "description", "work_locations_all"):
        k = sum(1 for r in rows if r.get(f))
        print(f"  {f:20} present on {k:5} of {len(rows)}  ({100*k//max(len(rows),1)}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
