#!/usr/bin/env python3
"""clock_decomposition.py -- split completeness-review waiting into APPLICANT-held and CITY-held
time, using the city's OWN disposition labels. No model, no inference. Read-only.

THE MEASUREMENT IS FREE BECAUSE THE CITY NAMES THE HOLDER ITSELF:
    "Incomplete Pending Applicant"  -> the city returned it; the applicant holds the clock
    "Resubmittal Pending Staff"     -> the applicant returned it; the city holds the clock
The interval between one dated completeness step and the next is therefore attributable without
anybody's judgement. (This is why a model is the wrong instrument here: it would be re-deriving a
fact the parser already extracts.)

⚠ THE CAVEATS PRINT WITH THE NUMBER, DELIBERATELY. This figure is easy to misread as
"applicants cause N% of delay", which it does NOT support:

 1. ONE PARTY HOLDS THE PEN. The city records "Pending Applicant" when it returns an application.
    Nothing obliges it to mark its own receipt with equal diligence. A 2:1 imbalance in label counts
    may measure recording practice rather than elapsed responsibility. This is a STRUCTURAL bias in
    the source, not noise that more records will average away.
 2. APPLICANT-HELD TIME IS MOSTLY REAL WORK. Months after "Incomplete Pending Applicant" is an
    architect redesigning a building. That is not blameworthy delay; for a large project it is the
    expected cost of a substantive correction.
 3. ONLY THE SPANS BETWEEN DATED COMPLETENESS STEPS ARE ATTRIBUTED. Filing to the first disposition
    is unattributed, and it is often the largest single span.
 4. RECORD MIX DECIDES THE ANSWER. Design-review companions iterate differently from the Zoning
    Permit that is the actual application. Read the per-record-type table, never the headline alone.

What it legitimately supports: the discretionary bottleneck is ITERATION WITH AN ATTRIBUTABLE OWNER
PER STEP, attributed by the city's own label rather than our inference -- and a by-right path whose
vocabulary contains no "Incomplete Pending Applicant" cannot generate applicant-held time at all,
which is the ministerial comparison in docs/methodology/seven_rungs_and_the_ministerial_shift.md.

  .venv/bin/python scripts/clock_decomposition.py
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from capdetail_select import load_rows                 # noqa: E402
from housing_rules.planning_record import role         # noqa: E402

APPLICANT = re.compile(r"pending applicant", re.I)
CITY = re.compile(r"pending staff", re.I)
STEP = re.compile(r"completeness review|intake", re.I)
MAX_SPAN_DAYS = 1500


def spans(rows):
    """-> list of (record_type, holder, days) for every attributable completeness-review span."""
    out = []
    for r in rows:
        steps = [t for t in (r.get("processing_status") or [])
                 if STEP.search(t["task"]) and t["status_date"] and t["status"]]
        steps.sort(key=lambda t: t["status_date"])
        for a, b in zip(steps, steps[1:]):
            d = (dt.date.fromisoformat(b["status_date"])
                 - dt.date.fromisoformat(a["status_date"])).days
            if not 0 <= d <= MAX_SPAN_DAYS:
                continue
            if APPLICANT.search(a["status"]):
                out.append((r.get("record_type"), "applicant", d))
            elif CITY.search(a["status"]):
                out.append((r.get("record_type"), "city", d))
    return out


def stat(v):
    return (f"n={len(v):4} total={sum(v):6}d median={statistics.median(v):5.0f}d "
            f"mean={statistics.mean(v):5.0f}d max={max(v):5}d") if v else "n=   0"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=None)
    args = ap.parse_args()
    d = ROOT / "scratch/2026-09-26_capdetail"
    src = args.jsonl or (sorted(glob.glob(str(d / "capdetail_reparsed_*.jsonl")))
                         or [str(d / "capdetail_parsed.jsonl")])[-1]
    rows = load_rows(src)
    sp = spans(rows)
    print(f"source {src}\nrecords {len(rows)}   attributable spans {len(sp)}\n")

    for holder in ("applicant", "city"):
        print(f"  clock held by the {holder.upper():9}: {stat([x[2] for x in sp if x[1]==holder])}")
    ta = sum(x[2] for x in sp if x[1] == "applicant")
    tc = sum(x[2] for x in sp if x[1] == "city")
    if ta + tc:
        print(f"\n  share of ATTRIBUTED waiting: applicant {100*ta/(ta+tc):.0f}%  "
              f"city {100*tc/(ta+tc):.0f}%   <- read the caveats below before quoting this")

    print("\n  by record type (the mix decides the headline):")
    types = collections.Counter(x[0] for x in sp)
    for t, _ in types.most_common():
        a = [x[2] for x in sp if x[0] == t and x[1] == "applicant"]
        c = [x[2] for x in sp if x[0] == t and x[1] == "city"]
        share = f"{100*sum(a)/(sum(a)+sum(c)):3.0f}%" if (sum(a) + sum(c)) else "  - "
        print(f"    {str(t)[:40]:42} role={role(t):20} applicant {share} of its waiting "
              f"({len(a)} spans) · city ({len(c)} spans)")

    print("\n" + "=" * 78)
    print("CAVEATS -- these travel WITH the number, not as a footnote:")
    print(" 1. ONE PARTY HOLDS THE PEN. The city writes 'Pending Applicant' when it returns an")
    print("    application; nothing obliges it to mark its own receipt as diligently. A label-count")
    print("    imbalance may measure RECORDING PRACTICE, not elapsed responsibility. Structural.")
    print(" 2. APPLICANT-HELD TIME IS MOSTLY REAL WORK -- an architect redesigning a building.")
    print(" 3. ONLY SPANS BETWEEN DATED COMPLETENESS STEPS are attributed; filing -> first")
    print("    disposition is UNATTRIBUTED and is often the largest single span.")
    print(" 4. This does NOT support 'applicants cause N% of delay'. It supports: the discretionary")
    print("    bottleneck is iteration with an owner named per step BY THE CITY'S OWN LABEL.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
