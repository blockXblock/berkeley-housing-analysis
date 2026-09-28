#!/usr/bin/env python3
r"""GATE: a dated event must name the city action it came from.

WHY. This is the project's central defect, measured 2026-09-26: of v2's dated `application_complete`
events, 100 named NO record -- no permit, no document, no record number. A date with no referent can
only be AGGREGATED, and an aggregate silently promotes one action to speak for the project: MIN picked
a prior project's application, MAX picked a design review three years later. The fix was never a better
aggregate; it was restoring the referent. docs/methodology/identity_is_the_product.md.

WHAT IT CHECKS. Per event type, the share of dated events that identify their source (a permit_id, a
document_id, or a record number in the summary), against a floor. The floors are deliberately set at
TODAY'S measured values so the gate fails on REGRESSION -- a new ingest that writes anonymous events
trips it, while existing history does not.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
V2 = f"file:{ROOT/'databases/berkeley_housing_v2.db'}?mode=ro"

# event_type_id -> (name, floor % identified). Measured 2026-09-28; raise a floor when it improves,
# never lower one to make the gate pass.
# event_type_id -> (name, floor % of DATED events that identify their source).
# MEASURED 2026-09-28 on dated events only. The first version of this gate set the entitlement floor
# from a measurement over ALL events (including undated ones) and the gate failed on correct data --
# a floor is only meaningful against the population it was measured on. Raise a floor when the number
# improves; never lower one to make the gate pass.
FLOORS = {2: ("application_submitted", 84), 3: ("application_complete", 77),
          9: ("entitlement_approved", 25),      # <-- THE WORST RUNG, and the next thing to fix
          14: ("building_permit_issued", 93), 17: ("co_issued", 98)}
IDENT = ("(permit_id IS NOT NULL OR document_id IS NOT NULL OR "
         "COALESCE(summary,'') GLOB '*[A-Z][A-Z]2[0-9][0-9][0-9]-*')")


def run() -> tuple[bool, list[str]]:
    db = sqlite3.connect(V2, uri=True)
    msgs, ok = [], True
    for tid, (name, floor) in FLOORS.items():
        tot = db.execute("SELECT COUNT(*) FROM project_events WHERE event_type_id=? "
                         "AND event_date IS NOT NULL", (tid,)).fetchone()[0]
        idn = db.execute(f"SELECT COUNT(*) FROM project_events WHERE event_type_id=? "
                         f"AND event_date IS NOT NULL AND {IDENT}", (tid,)).fetchone()[0]
        pct = 100 * idn / tot if tot else 100
        if pct + 0.5 < floor:
            ok = False
            msgs.append(f"FAIL {name}: {idn}/{tot} = {pct:.0f}% of DATED events name their "
                        f"source; floor is {floor}% -- something wrote anonymous events")
        else:
            msgs.append(f"ok   {name}: {idn}/{tot} = {pct:.0f}% identified (floor {floor}%)")
    return ok, msgs


if __name__ == "__main__":
    ok, m = run()
    print("\n".join(m))
    raise SystemExit(0 if ok else 1)
