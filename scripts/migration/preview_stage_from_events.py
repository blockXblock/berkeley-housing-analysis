#!/usr/bin/env python3
"""preview_stage_from_events.py — READ-ONLY: what stage does the evidence say each project is at?

WHY. `projects.current_stage_type_id` was never derived from the event stream; it is materialised
independently, and it drifts. Today that drift is visible and wrong in public: 2902 Adeline (54
units) and 2016 Ashby (50 units) are shown as **withdrawn** while inspectors are on site — 2902
Adeline was inspected on 2026-09-22. Separately, 71 projects read `completed` with no completion
date at all.

Now that inspection events exist (625 projects with a first inspection, up from 18), the event
stream can actually answer the question, so this proposes a stage for every project and diffs it
against what is stored.

TWO GUARDS JOHN'S LOCAL KNOWLEDGE FORCED, both of which the draft lacked:

  **A passed Building Final is NOT a project completion.** The draft proposed marking 1914 Fifth
  (257 units) and 2420 Shattuck (132 units) completed on 2017 Building Finals. 1914 Fifth is a
  parking lot: its finaled permits are "DEMO OF EXISTING WAREHOUSE (13300 SF)" and "GRADING &
  PAVING PARKING LOT ... BEER GARDEN PATIO". 2420 Shattuck's is "Commercial Restaurant T.I. for
  Giovanni's" — a pizza fit-out. All five permits carry `completion_verdict='ambiguous'`, so the
  ADR-002 verdict layer had already ruled them out and the fallback bypassed it. It affected 50
  projects. Completion now comes from `co_issued_date` alone, which is ADR-001's 4-tier precedence
  and respects verdicts.

  **Evidence must postdate the project's own application.** A project accumulates the SITE's whole
  permit history — demolitions, re-roofs, restaurant fit-outs — long before the development it
  now describes. 1914 Fifth's inspections stop in 2017; the 257-unit tower was filed 2023-06-20.
  Construction evidence older than `filed_date` describes what used to be on the lot, not the
  proposal, and is ignored.

THE RULE, highest precedence first. Each step is evidence, not inference:
  completed           a completion date in v_projects_flat (ADR-001) — verdict-respecting
  under_construction  a first/observed inspection, or construction_start_observed, and no completion
  permitted           a building_permit_issued event, and no construction evidence
  entitled            an entitlement_approved event, and no permit
  in_review           an application_submitted or application_complete event, and nothing later
  pre_application     a pre_app_meeting event only
  withdrawn           a project_withdrawn event AND no evidence dated after it

TWO RULES THE FIRST DRAFT GOT WRONG, both caught by reading its own output:

  * **Jan-1 dates are placeholders, not evidence.** `application_submitted` carries ~100 `-01-01`
    dates from the v1 migration (CLAUDE.md; it is why the Table A anchor is `application_complete`).
    The draft proposed moving 2400 Bowditch (1,500 units) and Ashby BART (618 units) out of
    pre_application on the strength of "application 2026-01-01" and "2025-01-01". Jan-1 dates on
    application events are now ignored.

  * **Absence of an event is not evidence the step did not happen.** The draft proposed moving
    2449 Dwight from under_construction BACK to entitled, and 2442 Haste back to permitted, purely
    because no inspection row exists for them. Our BP coverage is partial and our inspection
    coverage is partial, so a missing event means we did not observe it, not that it did not occur.
    A stage is therefore only ever proposed FORWARD along
    pre_application < in_review < entitled < permitted < under_construction < completed.
    Backward candidates are reported separately as evidence gaps and never proposed as moves.

WITHDRAWN IS NOT STICKY, and the test must use the LATEST inspection, not the first. The draft
missed 2902 Adeline entirely: `first_inspection_observed` records the FIRST inspection (2025-05-28),
which is earlier than the last `project_withdrawn` (2026-01-23), so "nothing happened after the
withdrawal" looked true while inspectors were on site through 2026-09-22. The live `inspections`
table is consulted directly for the latest activity date.

⚠ AND THOSE WITHDRAWALS ARE NOT WITHDRAWALS. 2902 Adeline carries **14** `project_withdrawn` events,
every one summarised "Auto-Closed" and paired with a "Documents Uploaded" status update. That is
Accela closing a document-upload record, not an applicant abandoning a 54-unit project. Whatever
maps Accela statuses onto `project_withdrawn` is treating a routine administrative close as a
withdrawal, and that mis-mapping is why the project reads withdrawn on the public site. Flagged
here; fixing the mapping is separate work. `stalled` is never proposed: no
event asserts it, and a project sitting still is not something the stream can see.

Writes nothing. Emits data/reference/stage_from_events_review.csv for John to review before any
gated write.

Usage:  python scripts/migration/preview_stage_from_events.py
"""
import collections
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "databases/berkeley_housing_v2.db"
OUT = ROOT / "data/reference/stage_from_events_review.csv"

RANK = {"pre_application": 1, "in_review": 2, "entitled": 3, "permitted": 4,
        "under_construction": 5, "completed": 6}

EV = {"pre_app": 1, "app_sub": 2, "app_complete": 3, "entitled": 9,
      "bp": 14, "constr": 15, "co": 17, "withdrawn": 19, "finaled": 25,
      "first_insp": 28, "final_passed": 29}


def main() -> int:
    db = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    ev = collections.defaultdict(dict)          # project -> code -> max date
    PLACEHOLDER_PRONE = {"app_sub", "app_complete", "entitled"}
    for pid, tid, d in db.execute(
            "SELECT project_id, event_type_id, event_date FROM project_events WHERE event_date IS NOT NULL"):
        for name, code in EV.items():
            if tid != code:
                continue
            if name in PLACEHOLDER_PRONE and str(d).endswith("-01-01"):
                continue                      # v1-migration placeholder, not an observation
            ev[pid][name] = max(ev[pid].get(name, ""), d or "")
    flat = {pid: (co, ad, u, st) for pid, co, ad, u, st in db.execute(
        "SELECT project_id, co_issued_date, address_display, total_units, status_code FROM v_projects_flat")}
    # latest real activity per project, straight from the inspection rows
    last_insp = {pid: d for pid, d in db.execute(
        """SELECT project_id, MAX(inspection_date) FROM inspections
           WHERE project_id IS NOT NULL AND IFNULL(inspection_date,'') <> ''
           GROUP BY project_id""")}
    filed_date = {pid: d for pid, d in db.execute(
        "SELECT project_id, filed_date FROM v_projects_flat WHERE filed_date IS NOT NULL")}
    autoclosed = {pid: n for pid, n in db.execute(
        """SELECT project_id, COUNT(*) FROM project_events
           WHERE event_type_id = 19 AND IFNULL(summary,'') LIKE '%Auto-Closed%'
           GROUP BY project_id""")}

    def propose(pid):
        e = ev.get(pid, {})
        co, _, _, _ = flat[pid]
        withdrawn_on = e.get("withdrawn")
        if withdrawn_on:
            later = [v for k, v in e.items() if k != "withdrawn" and v > withdrawn_on]
            li = last_insp.get(pid)
            if li and li > withdrawn_on:
                later.append(li)
            if not later and not co:
                return "withdrawn", f"withdrawn {withdrawn_on}, nothing after"
        if co:
            return "completed", f"completion {co}"
        filed = filed_date.get(pid)
        li = last_insp.get(pid)
        # construction evidence that predates the application belongs to the previous building
        if li and filed and li < filed:
            li = None
        insp = e.get("first_insp") or e.get("constr")
        if insp and filed and insp < filed and not li:
            insp = None
        if insp or li:
            d = insp or li
            note = f"inspections from {d}" + (f", latest {li}" if li and li != d else "")
            return "under_construction", note
        if e.get("bp"):
            return "permitted", f"BP issued {e['bp']}"
        if e.get("entitled"):
            return "entitled", f"entitlement approved {e['entitled']}"
        if e.get("app_complete") or e.get("app_sub"):
            d = e.get("app_complete") or e.get("app_sub")
            return "in_review", f"application {d}"
        if e.get("pre_app"):
            return "pre_application", f"pre-app meeting {e['pre_app']}"
        return None, "no dated events"

    rows, moves, noev, backward = [], collections.Counter(), 0, []
    for pid, (co, ad, u, cur) in flat.items():
        new, why = propose(pid)
        if new is None:
            noev += 1
            continue
        if new == cur:
            continue
        rec = {"project_id": pid, "address": (ad or "")[:40], "units": u or "",
               "stage_now": cur, "stage_proposed": new, "evidence": why}
        forward = RANK.get(new, 0) > RANK.get(cur, 0)
        revived = cur in ("withdrawn", "stalled")
        if forward or revived:
            moves[(cur, new)] += 1
            rows.append(rec)
        else:
            backward.append(rec)

    print("Stage derived from the event stream — READ-ONLY preview\n")
    print(f"  projects                          {len(flat):,}")
    print(f"  no dated events, cannot propose   {noev:,}  (left exactly as they are)")
    print(f"  stage AGREES with the evidence    {len(flat)-noev-len(rows):,}")
    print(f"  stage WOULD MOVE                  {len(rows):,}\n")
    print("  proposed moves:")
    for (a, b), n in moves.most_common():
        print(f"    {n:>4}  {a:<19} -> {b}")
    if backward:
        print(f"\n  {len(backward)} projects where the evidence is BEHIND the stored stage.")
        print("  NOT proposed as moves — a missing event means we did not observe the step,")
        print("  not that it did not happen. These are coverage gaps to chase:")
        for r in sorted(backward, key=lambda r: -(r["units"] or 0))[:8]:
            print(f"    proj{r['project_id']:<5} {r['address'][:26]:<26} {str(r['units']):>4}u  "
                  f"stored {r['stage_now']:<19} evidence only reaches {r['stage_proposed']}")
    big = sorted([r for r in rows if isinstance(r["units"], int) and r["units"] >= 20],
                 key=lambda r: -r["units"])
    if big:
        print(f"\n  the {len(big)} moves on projects of 20+ units — check these by eye:")
        for r in big[:16]:
            print(f"    proj{r['project_id']:<5} {r['address'][:26]:<26} {r['units']:>4}u  "
                  f"{r['stage_now']:<19} -> {r['stage_proposed']:<19} {r['evidence']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["project_id", "address", "units", "stage_now",
                                           "stage_proposed", "evidence"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: -(r["units"] or 0)))
    ac = {p: n for p, n in autoclosed.items() if n >= 3}
    if ac:
        print(f"\n  ⚠ {len(ac)} projects carry 3+ 'Auto-Closed' events mapped to project_withdrawn.")
        print("    Accela auto-closing a document-upload record is NOT a withdrawal. Worst offenders:")
        for p, n in sorted(ac.items(), key=lambda kv: -kv[1])[:6]:
            a = flat.get(p, ("", "", "", ""))
            print(f"      proj{p:<5} {str(a[1])[:26]:<26} {str(a[2]):>4}u  {n} auto-closed  stage={a[3]}")
    print(f"\n  full list -> {OUT.relative_to(ROOT)}")
    print("\n  Nothing written to the database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
