#!/usr/bin/env python3
"""preview_capdetail_units.py -- READ-ONLY: compare the unit count in the CITY'S OWN CapDetail
project description against v2's `total_units`. Writes nothing.

WHAT THIS IS NOT. A first version of this script compared EVERY record's unit count against v2 and
reported 32 "differences" as candidate evidence that v2 was wrong. That framing was a category error.
2128 Oxford has two design-review records -- 283 units in 2021, 485 in 2022 -- and v2 says 456: the
project CHANGED, and neither source is wrong. proj144 settles it: 66 units at design-review
preliminary (2023-04), 58 at final (2024-03), and v2 holds 58. v2 carries a LATE count, so comparing
it against an early record measures elapsed time, not error.

So this reports a TRAJECTORY -- the program as the city described it at each step, which is real new
information (v2 even has an event type for it, `program_revised`, id 22) -- and only then compares the
LATEST city count against v2.

WHY THIS IS LEGITIMATE EVIDENCE. The description is written by the city on its own record page, so
it is a PRIMARY source (working rule 1) -- unlike the CKAN/HCD mirror, which is the verification
target and must never be a derivation input. A disagreement here is two independent sources
disagreeing, which is exactly what `contested` is supposed to mean.

WHY THE EXTRACTION IS THE WEAK LINK, STATED UP FRONT. Pulling "how many units" out of English prose
with a regex is the fragile part, not the join. Real descriptions look like:

    "construction of a new 6 story mixed-use building with 126 dwelling units (of which 3 are
     live/work) and 10 are provided as low income units"

Three numbers, one answer. A pattern that grabs the wrong one silently corrupts a comparison that
LOOKS authoritative. So this script:
  * takes the count from an explicit "<N> dwelling units"/"<N> units" phrase, preferring the LARGEST
    such phrase, since sub-counts (live/work, low income, ADU) are subsets of the total;
  * REFUSES to report a number when the description names several unit counts that cannot be
    resolved that way -- those are listed as `needs_review`, not guessed;
  * labels everything CANDIDATE. A model reading the sentence (scripts/llm_permit_effect.py, the
    per-permit classifier) is the better instrument and is the right escalation for the ambiguous
    tail; a regex is the cheap first pass, not the verdict.

  .venv/bin/python scripts/preview_capdetail_units.py
"""
from __future__ import annotations

import argparse
import collections
import glob
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from capdetail_select import addr_key, load_rows          # noqa: E402
from housing_rules.planning_record import role            # noqa: E402

V2 = f"file:{ROOT/'databases/berkeley_housing_v2.db'}?mode=ro"

# "126 dwelling units", "48-unit", "a 55 unit building". Sub-counts are captured too and resolved by
# taking the max; SUBSET_HINT marks phrases that can never be a total.
# "126 dwelling units", "166 dwellings", "48-unit", "a 55 unit building".
# THE PLURAL BUG, found 2026-09-26 (caught in the sibling filter first, then here): an optional
# "dwelling" followed by a required "units?" CANNOT match "166 dwellings" -- the optional group
# consumes "dwelling" and then `units?` demands "unit". Worse, "with 166 dwellings, including 17
# Very Low-Income units" matched NOTHING, because the words between "17" and "units" blocked the
# other branch too. That silently classified a 10-storey, 166-dwelling project as "no unit phrase".
# Both nouns are now first-class and either may be plural, and intervening qualifiers are allowed
# before the noun.
UNITS = re.compile(
    r"(\d{1,4})\s*[-\s]?\s*"
    r"((?:(?:new|additional|total|net|proposed|residential|rental|apartment|affordable|bmr|"
    r"very\s+low[-\s]?income|low[-\s]?income|moderate[-\s]?income|market[-\s]?rate|"
    r"live[-/\s]?work|senior|studio|accessory|junior)[-\s]+){0,4})"
    r"(?:dwelling\s+units?|dwellings?|units?|apartments?)\b", re.I)
# A number is a SUBSET of the total when its OWN phrase says so ("17 Very Low-Income units"), or when
# the noun itself is not a dwelling ("14 parking spaces"). Judged from the captured qualifier group,
# NOT from a proximity window: a 40-character window around "166 dwellings, including 17 Very
# Low-Income units" sees "Very Low" and wrongly flags the 166 as a subset, which is how a first
# attempt at this fix returned 17 as the total (2026-09-26).
SUBSET_QUAL = re.compile(r"(affordable|bmr|very\s*low|low[-\s]?income|moderate|market[-\s]?rate|"
                         r"live[-/\s]?work|senior|accessory|junior|studio)", re.I)
NON_DWELLING = re.compile(r"\b\d{1,4}\s*(?:[-\s])?\s*(parking|bike|bicycle|storage|bedroom|"
                          r"space|stall|foot|feet|sq|square|story|stories|storey)", re.I)


def extract(desc: str):
    """-> (units, confidence, all_found). 'high' when unambiguous, else a named reason."""
    if not desc:
        return None, "no_description", []
    found = []
    for m in UNITS.finditer(desc):
        n = int(m.group(1))
        if not (0 < n <= 2000):
            continue
        qual = m.group(2) or ""
        phrase = m.group(0)
        is_sub = bool(SUBSET_QUAL.search(qual)) or bool(NON_DWELLING.match(phrase))
        found.append((n, is_sub))
    totals = [n for n, sub in found if not sub]
    if not totals:
        return None, ("only_subset_counts" if found else "no_unit_phrase"), [n for n, _ in found]
    if len(set(totals)) == 1:
        return totals[0], "high", [n for n, _ in found]
    big = max(totals)
    if sum(t for t in totals if t != big) <= big:
        return big, "high", [n for n, _ in found]
    return None, "needs_review", [n for n, _ in found]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=None)
    args = ap.parse_args()
    d = ROOT / "scratch/2026-09-26_capdetail"
    src = args.jsonl or (sorted(glob.glob(str(d / "capdetail_reparsed_*.jsonl")))
                         or [str(d / "capdetail_parsed.jsonl")])[-1]
    rows = load_rows(src)
    db = sqlite3.connect(V2, uri=True)
    by_addr = collections.defaultdict(set)
    units = {}
    for pid, a, u in db.execute("SELECT project_id,address_display,total_units FROM v_projects_flat "
                               "WHERE address_display IS NOT NULL"):
        k = addr_key(a)
        if k:
            by_addr[k].add(pid)
        units[pid] = u
    by_apn = collections.defaultdict(set)
    for pid, apn in db.execute("SELECT pp.project_id,p.apn_normalized FROM project_parcels pp "
                               "JOIN parcels p ON p.id=pp.parcel_id WHERE p.apn_normalized IS NOT NULL"):
        by_apn[apn].add(pid)

    conf = collections.Counter()
    hist = collections.defaultdict(list)
    review, unmatched = [], 0
    for r in rows:
        if role(r.get("record_type")) not in ("primary_application", "companion_review"):
            continue
        n, c, found = extract(r.get("description") or "")
        conf[c] += 1
        pids = set(by_addr.get(addr_key(r.get("work_location")), set()))
        for x in (r.get("parcels_canonical") or []):
            if x:
                pids |= by_apn.get(x, set())
        if not pids:
            if n is not None:
                unmatched += 1
            continue
        if c == "needs_review":
            review.append((r["record"], found, sorted(pids)))
            continue
        if n is None:
            continue
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(r.get("list_date") or ""))
        when = f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else "?"
        for pid in pids:
            hist[pid].append((when, r["record"], n, r.get("record_type")))

    print(f"source {src}\nrecords considered: {sum(conf.values())}")
    print("  extraction confidence:", dict(conf.most_common()))
    print(f"  records with a unit count but NO v2 project: {unmatched}")
    print(f"  ambiguous prose (escalate to the model, never guess): {len(review)}")

    revised = {p: sorted(v) for p, v in hist.items() if len({x[2] for x in v}) > 1}
    print(f"\nPROGRAM REVISION TRAJECTORIES -- projects the city described with DIFFERENT unit")
    print(f"counts over time: {len(revised)}. Neither source is wrong; this is the project changing.")
    for pid, v in sorted(revised.items(), key=lambda kv: -len(kv[1]))[:12]:
        traj = " -> ".join(f"{x[0][:7]}:{x[2]}u" for x in v)
        print(f"    proj{pid:<5} v2={units.get(pid)}u   {traj}")

    print("\nLATEST city count vs v2 (the only fair comparison):")
    agree, differ = [], []
    for pid, v in hist.items():
        latest = sorted(v)[-1]
        v2u = units.get(pid)
        if v2u is None:
            continue
        (agree if v2u == latest[2] else differ).append((pid, latest, v2u))
    print(f"  agrees  : {len(agree)}")
    print(f"  differs : {len(differ)}   <- worth a look, still CANDIDATE: the count comes from a")
    print("              regex over English prose, which is the fragile part of this whole script")
    for pid, latest, v2u in sorted(differ, key=lambda x: -abs(x[1][2] - x[2]))[:15]:
        print(f"    proj{pid:<5} latest {latest[0]} {latest[1]:16} city={latest[2]:4} "
              f"v2={v2u:4} gap={latest[2]-v2u:+5}")
    for rec, found, pids in review[:8]:
        print(f"    AMBIGUOUS {rec:16} numbers={found} projects={pids}")

    print("\nNOTHING WRITTEN. Any correction is a separate gated write after John reviews these.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
