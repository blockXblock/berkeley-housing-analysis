#!/usr/bin/env python3
"""verify_capdetail_complete.py -- prove the harvest is COMPLETE, per record, with evidence.

"The run finished" is not the same claim as "every record is accounted for". This puts each of the
1,746 queued records into exactly one bucket and refuses to call the harvest done unless the
unaccounted bucket is empty:

  captured        a saved page that actually contains workflow text
  verified_empty  in the append-only absence ledger -- looked for properly and genuinely absent
  page_no_wf      a page on disk with NO workflow text and NOT in the ledger  <- SUSPECT, refetch
  errored         the last attempt raised (e.g. ERR_TIMED_OUT); no page saved, so still queued
  missing         never attempted

page_no_wf is the bucket that matters. It is how a false absence becomes permanent: resume would
skip it as "have a page", and nothing would ever look again. DRCP2015-0002 sat in exactly that state
on 2026-09-26 and a refetch returned 5 workflow tasks.

Read-only. Exit 0 only when captured + verified_empty == the whole queue.
  .venv/bin/python scripts/verify_capdetail_complete.py
"""
from __future__ import annotations

import collections
import glob
import gzip
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
HARVEST = ROOT / "scratch/2026-09-26_capdetail"


def main() -> int:
    spec = importlib.util.spec_from_file_location("h", ROOT / "scripts/harvest_capdetail.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    queue = {r["record"]: r for r in m.queue()}

    try:
        ledger = set(json.loads((HARVEST / "verified_empty.json").read_text()))
    except Exception:
        ledger = set()

    errored = set()
    for fn in glob.glob(str(HARVEST / "capdetail_parsed.jsonl")):
        for line in open(fn):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("record"):
                (errored.add if r.get("error") else errored.discard)(r["record"])

    bucket = {}
    for rec in queue:
        f = HARVEST / "pages" / f"{rec}.html.gz"
        if f.exists():
            try:
                has = "Marked as" in gzip.decompress(f.read_bytes()).decode("utf-8", "replace")
            except Exception:
                has = False
            if has:
                bucket[rec] = "captured"
                continue
            bucket[rec] = "verified_empty" if rec in ledger else "page_no_wf"
            continue
        if rec in ledger:
            bucket[rec] = "verified_empty"
        elif rec in errored:
            bucket[rec] = "errored"
        else:
            bucket[rec] = "missing"

    counts = collections.Counter(bucket.values())
    print(f"queue {len(queue)} housing Planning records\n")
    for k in ("captured", "verified_empty", "page_no_wf", "errored", "missing"):
        print(f"  {k:16} {counts[k]:5}")
    accounted = counts["captured"] + counts["verified_empty"]
    print(f"\n  accounted for: {accounted} / {len(queue)}"
          f"   ({100*accounted/len(queue):.1f}%)")

    by_type = collections.Counter(
        queue[r]["record_type"] for r, b in bucket.items() if b == "verified_empty")
    if by_type:
        print("\n  verified absences by record type:")
        for t, n in by_type.most_common():
            tot = sum(1 for q in queue.values() if q["record_type"] == t)
            print(f"    {str(t)[:44]:46} {n:4} of {tot:4}")

    for b, label in (("page_no_wf", "SUSPECT -- page saved with no workflow and NOT in the ledger; "
                                    "refetch these (a false absence would become permanent)"),
                     ("errored", "last attempt raised; no page saved, so still queued"),
                     ("missing", "never attempted")):
        bad = sorted(r for r, x in bucket.items() if x == b)
        if bad:
            print(f"\n  {b} ({len(bad)}) -- {label}")
            for r in bad[:15]:
                print(f"    {r:16} {queue[r]['record_type']}")
            if len(bad) > 15:
                print(f"    ... and {len(bad)-15} more")

    if accounted == len(queue):
        print("\nCOMPLETE: every queued record is either captured or a verified absence.")
        return 0
    print(f"\nNOT COMPLETE: {len(queue)-accounted} records unaccounted for. Re-run the harvester "
          "(resume skips what is already accounted for); page_no_wf needs its page deleted first.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
