#!/usr/bin/env python3
r"""GATE: a dated event must name the city action it came from.

WHY. This is the project's central defect, measured 2026-09-26: of v2's dated `application_complete`
events, 100 named NO record -- no permit, no document, no record number. A date with no referent can
only be AGGREGATED, and an aggregate silently promotes one action to speak for the project: MIN picked
a prior project's application, MAX picked a design review three years later. The fix was never a better
aggregate; it was restoring the referent. docs/methodology/identity_is_the_product.md.

WHAT IT CHECKS, in v4 (re-pointed 2026-10-02 from v2's project_events). v4 is built so that a date
has a referent by construction; this gate makes sure it stays that way, at the three places a date
lives:
  1. EVENTS: every dated event names its source record (source_record_key) and resolves to a
     declared source and ingestion run;
  2. PROJECT MILESTONES (filed / accepted / entitled in projects.notes): the date is carried by an
     event of the project's own ANCHOR record -- selected from the primary application, never
     aggregated across records;
  3. BUILDINGS: a structure's completed_on is carried by an event attached to that structure.
Floors are the share measured on 2026-10-02 (all 100%), so the gate fails on REGRESSION -- a build
that writes an anonymous or aggregated date trips it. Never lower a floor to make the gate pass.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
V4 = f"file:{ROOT/'databases/berkeley_housing_v4.db'}?mode=ro"

# name -> (floor %, SQL returning (identified, total)). Measured 2026-10-02.
CHECKS = {
    "dated events name a source record": (100, """
        SELECT SUM(COALESCE(e.source_record_key,'') <> ''
                   AND EXISTS (SELECT 1 FROM sources s WHERE s.source_id = e.source_id)
                   AND EXISTS (SELECT 1 FROM ingestion_runs r WHERE r.run_id = e.ingestion_run_id)),
               COUNT(*)
        FROM events e WHERE e.event_date IS NOT NULL"""),
}
for _m in ("filed", "accepted", "entitled"):
    CHECKS[f"project '{_m}' date is an anchor-record event"] = (100, f"""
        WITH p AS (SELECT json_extract(notes, '$.anchor') anc, json_extract(notes, '$.{_m}') d
                   FROM projects WHERE json_extract(notes, '$.{_m}') IS NOT NULL)
        SELECT SUM(EXISTS (SELECT 1 FROM events e WHERE e.source_record_key = p.anc
                           AND substr(e.event_date, 1, 10) = substr(p.d, 1, 10))), COUNT(*)
        FROM p""")
CHECKS["structure completed_on is an event of that structure"] = (100, """
    SELECT SUM(EXISTS (SELECT 1 FROM structure_events se JOIN events e USING (event_id)
                       WHERE se.structure_id = s.structure_id
                         AND substr(e.event_date, 1, 10) = substr(s.completed_on, 1, 10))), COUNT(*)
    FROM structures s WHERE s.completed_on IS NOT NULL""")


def run() -> tuple[bool, list[str]]:
    db = sqlite3.connect(V4, uri=True)
    msgs, ok = [], True
    for name, (floor, sql) in CHECKS.items():
        idn, tot = db.execute(sql).fetchone()
        idn = idn or 0
        pct = 100 * idn / tot if tot else 100
        if pct + 0.005 < floor:
            ok = False
            msgs.append(f"FAIL {name}: {idn:,}/{tot:,} = {pct:.2f}%; floor is {floor}% -- something "
                        f"wrote a date with no referent")
        else:
            msgs.append(f"ok   {name}: {idn:,}/{tot:,} = {pct:.0f}% (floor {floor}%)")
    return ok, msgs


if __name__ == "__main__":
    ok, m = run()
    print("\n".join(m))
    raise SystemExit(0 if ok else 1)
