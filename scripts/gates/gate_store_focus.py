#!/usr/bin/env python3
r"""GAUGE: has the cutover to ONE store (v4) finished?

WHY THIS GAUGE EXISTS. The project had four stores -- v1 (archived), v2 (served everything), v3 (a
2.6 MB stub), v4 (the event substrate) -- and on 2026-09-26 v4's event layer was rebuilt from sources
while three separate writes went into v2. Neither was wrong alone; together they were the focus loss,
and nobody noticed because no instrument was pointed at it.

RE-POINTED 2026-10-02. The first version measured v2-vs-v4 CONVERGENCE by opening both stores and
comparing their entity counts. Since 2026-10-01 every publisher reads v4 and v2 is being archived, so
a v2 row count no longer measures anything: it is a frozen store, not a fork that grows. What is left
of the question is the CUTOVER itself, and this gauge measures only that, without opening v2:
  1. v4 has housing entities (structures, projects, units, project_structures), not just reference
     tables -- the condition that let v4 serve at all;
  2. NO live script names the v2 database (files under scripts/superseded/ are excluded; this file
     builds the name in pieces so it does not count itself);
  3. the v2 file is archived read-only (no write bit).
DONE = all three. It never fails the run; red means "the re-pointing is not finished", not a defect.
Once DONE it can be retired.
"""
from __future__ import annotations

import os
import sqlite3
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
V4 = ROOT / "databases/berkeley_housing_v4.db"
V2_NAME = "berkeley_housing_" + "v2"          # in pieces, so this file is not one of its own readers
V2_FILE = ROOT / "databases" / f"{V2_NAME}.db"
# REFERENCE tables describe the world; HOUSING-ENTITY tables are what let v4 serve. Conflating them
# once made this gauge read DONE while projects/structures were still empty (2026-09-28).
V4_REFERENCE = ("parcels", "parcel_identifiers", "assessed_values", "documents", "actors")
V4_HOUSING_ENTITY = ("structures", "projects", "units", "project_structures")


def _count(db, t):
    try:
        return db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    except Exception:
        return None


def _readers(name):
    """Live (non-superseded) .py files under scripts/ that name a store."""
    try:
        out = subprocess.run(["grep", "-rl", name, "--include=*.py", "scripts/"],
                             cwd=ROOT, capture_output=True, text=True, timeout=60).stdout
        return sorted(l for l in out.splitlines() if "superseded" not in l)
    except Exception:
        return None


def run() -> tuple[bool, list[str]]:
    msgs, ok = [], True
    v4 = sqlite3.connect(f"file:{V4}?mode=ro", uri=True)

    ev = _count(v4, "events") or 0
    ref = {t: _count(v4, t) for t in V4_REFERENCE}
    ent = {t: _count(v4, t) for t in V4_HOUSING_ENTITY}
    ent_total = sum(v or 0 for v in ent.values())
    msgs.append(f"     v4 substrate:  {ev:,} events")
    msgs.append("     v4 reference:  " + " ".join(f"{t}={ref[t]:,}" for t in V4_REFERENCE if ref[t] is not None))
    msgs.append("     v4 HOUSING ENTITIES: "
                + " ".join(f"{t}={ent[t]:,}" for t in V4_HOUSING_ENTITY if ent[t] is not None))

    r2 = _readers(V2_NAME)
    r4 = _readers("berkeley_housing_" + "v4")
    r3 = _readers("berkeley_housing_" + "v3")
    msgs.append(f"     live scripts naming: v2={len(r2) if r2 is not None else '?'}  "
                f"v4={len(r4) if r4 is not None else '?'}  v3={len(r3) if r3 is not None else '?'}")

    if V2_FILE.exists():
        writable = bool(V2_FILE.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        v2_state = "WRITABLE" if writable else "read-only"
    else:
        writable, v2_state = False, "moved (not at databases/)"
    msgs.append(f"     v2 file: {v2_state}")

    if ent_total == 0:
        ok = False
        msgs.append("OPEN v4 has no housing entities -- it cannot serve; the cutover has not begun.")
    if r2 is None:
        ok = False
        msgs.append("OPEN could not count v2 readers (grep failed)")
    elif r2:
        ok = False
        msgs.append(f"OPEN {len(r2)} live scripts still name the v2 database -- the cutover is the "
                    f"RE-POINTING: {', '.join(os.path.relpath(p, 'scripts') for p in r2[:8])}"
                    + (" ..." if len(r2) > 8 else ""))
    if writable:
        ok = False
        msgs.append("OPEN the v2 file still has a write bit -- archive it read-only once its readers are gone")
    if r3:
        msgs.append(f"note v3 still has {len(r3)} live readers but its DB is a stub "
                    "-- decide: finish it or retire it.")
    if ok:
        msgs.append("     cutover complete: v4 serves, nothing live names v2, v2 is read-only "
                    "-- this gauge can be retired")
    return ok, msgs


if __name__ == "__main__":
    ok, m = run()
    print("\n".join(m))
    raise SystemExit(0 if ok else 1)
