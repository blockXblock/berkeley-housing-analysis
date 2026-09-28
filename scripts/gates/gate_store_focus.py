#!/usr/bin/env python3
r"""GATE: is the project CONVERGING on one data store, or maintaining several?

WHY THIS GATE EXISTS. The project has four stores -- v1 (archived), v2 (serves everything), v3 (a
2.6 MB stub), v4 (a 140 MB event substrate) -- and the stated direction since 2026-09-26 is that v4
becomes the build and v2 becomes its output. On 2026-09-26 BOTH happened in one day: v4's event layer
was rebuilt from sources (89,108 events) while three separate writes went into v2. Neither was wrong
alone; together they are the focus loss this whole post-mortem is about, and nobody noticed because
no instrument was pointed at it.

This gate is that instrument. It does not forbid anything. It PRINTS THE SHAPE of the divergence in
numbers a person can read in ten seconds, and fails only on the one condition that means the migration
has stalled rather than progressed: v4's entity layer still empty while v2 keeps growing.

WHAT "ON THE PATH TO v4" WOULD LOOK LIKE: v4's entity tables filling, the count of live scripts
reading v2 falling, v3 retired. Anything else is maintenance of a fork.
"""
from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
V2, V4 = ROOT / "databases/berkeley_housing_v2.db", ROOT / "databases/berkeley_housing_v4.db"
# the v4 tables that must fill before v4 can replace v2
V4_ENTITY = ("projects", "structures", "units", "parcels", "addresses")


def _count(db, t):
    try:
        return db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    except Exception:
        return None


def run() -> tuple[bool, list[str]]:
    msgs, ok = [], True
    v4 = sqlite3.connect(f"file:{V4}?mode=ro", uri=True)
    v2 = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)

    ev = _count(v4, "events") or 0
    ent = {t: _count(v4, t) for t in V4_ENTITY}
    ent_total = sum(v or 0 for v in ent.values())
    msgs.append(f"     v4 substrate: {ev:,} events · entity layer: "
                + " ".join(f"{t}={ent[t]}" for t in V4_ENTITY))

    v2_proj = _count(v2, "projects") or 0
    v2_ev = _count(v2, "project_events") or 0
    msgs.append(f"     v2 (serving):  {v2_proj:,} projects · {v2_ev:,} events")

    # who reads what -- the real measure of coupling
    def readers(name):
        try:
            out = subprocess.run(["grep", "-rl", name, "--include=*.py", "scripts/"],
                                 cwd=ROOT, capture_output=True, text=True, timeout=60).stdout
            return len([l for l in out.splitlines() if "superseded" not in l])
        except Exception:
            return -1
    r2, r4, r3 = readers("berkeley_housing_v2"), readers("berkeley_housing_v4"), \
        readers("berkeley_housing_v3")
    msgs.append(f"     live scripts reading: v2={r2}  v4={r4}  v3={r3}")

    if ev > 0 and ent_total == 0:
        ok = False
        msgs.append("FAIL v4 has a substrate and NO entities: every one of "
                    f"{', '.join(V4_ENTITY)} is empty. v4 cannot replace v2 in this state, so any "
                    "work that deepens v2 widens the fork. THIS IS THE STALL -- name the next entity "
                    "stage and build it, or say plainly that v2 is the destination after all.")
    elif ent_total:
        msgs.append(f"ok   v4 entity layer has {ent_total} rows -- the migration is moving")
    if r2 > 0 and r4 >= 0 and r2 > 3 * max(r4, 1):
        msgs.append(f"note v2 coupling is {r2}/{r4} = {r2/max(r4,1):.0f}x v4's. Re-pointing that is "
                    "the bulk of any cutover, and it is not started.")
    if r3 > 0:
        msgs.append(f"note v3 still has {r3} live readers but its DB is a stub "
                    "-- decide: finish it or retire it.")
    return ok, msgs


if __name__ == "__main__":
    ok, m = run()
    print("\n".join(m))
    raise SystemExit(0 if ok else 1)
