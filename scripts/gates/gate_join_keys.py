#!/usr/bin/env python3
r"""GATE: a join key must be able to identify ONE thing.

WHY. On 2026-09-26 four projects were "conflated" purely because their address is "0 <street>", a real
city convention for an unnumbered parcel that several distinct APNs share -- keyed literally it matches
every record on the street. Hours later, the write that fixed those addresses set
`normalized_address` to the STREET ALONE ('LE ROY'), recreating the same wildcard in an INDEXED
matching column. Knowing the rule did not prevent it; this gate would have.

WHAT IT CHECKS, in v2:
  1. no `normalized_address` without a house number (a street-only key is a wildcard);
  2. one convention per matching column (a column holding both '1609|FIFTH' and '0 LE ROY AVE'
     cannot be joined on reliably);
  3. every `parcels.apn_normalized` is in the canon's own output form;
  4. no project carries two current addresses.
"""
from __future__ import annotations

import collections
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from housing_rules import to_canonical_apn            # noqa: E402
V2 = f"file:{ROOT/'databases/berkeley_housing_v2.db'}?mode=ro"


def run() -> tuple[bool, list[str]]:
    db = sqlite3.connect(V2, uri=True)
    msgs, ok = [], True

    wild = [(p, a, n) for p, a, n in db.execute(
        "SELECT id,canonical_address,normalized_address FROM projects "
        "WHERE normalized_address IS NOT NULL AND merged_into_id IS NULL")
        if not re.match(r"^\d", n)]
    # a project whose SOURCE address has no number cannot be blamed on the key
    unfixable = [x for x in wild if not re.match(r"^\s*\d", str(x[1] or ""))]
    real = [x for x in wild if x not in unfixable]
    if real:
        ok = False
        msgs.append(f"FAIL wildcard keys: {len(real)} projects have a numberless "
                    f"normalized_address while their canonical_address HAS a number -- "
                    f"{[(p, a, n) for p, a, n in real[:4]]}")
    else:
        msgs.append(f"ok   wildcard keys: none derivable-but-dropped "
                    f"({len(unfixable)} genuinely have no street number: "
                    f"{[x[1] for x in unfixable[:3]]})")

    shapes = collections.Counter()
    for (v,) in db.execute("SELECT normalized_address FROM projects "
                           "WHERE normalized_address IS NOT NULL"):
        shapes["pipe" if "|" in v else ("space" if re.match(r"^\d+\s", v) else "other")] += 1
    if len([k for k, n in shapes.items() if n]) > 1:
        ok = False
        msgs.append(f"FAIL mixed conventions in projects.normalized_address: {dict(shapes)} -- "
                    f"a matching column with two shapes cannot be joined on")
    else:
        msgs.append(f"ok   one convention in normalized_address: {dict(shapes)}")

    bad = []
    for (a,) in db.execute("SELECT apn_normalized FROM parcels WHERE apn_normalized IS NOT NULL"):
        try:
            if to_canonical_apn(a, "alameda") != a:
                bad.append(a)
        except Exception:
            bad.append(a)
    if bad:
        ok = False
        msgs.append(f"FAIL {len(bad)} parcels.apn_normalized are not the canon's own output: "
                    f"{bad[:4]}")
    else:
        msgs.append("ok   every apn_normalized is canonical")

    dup = db.execute("SELECT COUNT(*) FROM (SELECT project_id FROM project_addresses "
                     "WHERE is_current=1 GROUP BY project_id HAVING COUNT(*)>1)").fetchone()[0]
    if dup:
        ok = False
        msgs.append(f"FAIL {dup} projects have TWO current addresses")
    else:
        msgs.append("ok   no project has two current addresses")
    return ok, msgs


if __name__ == "__main__":
    ok, m = run()
    print("\n".join(m))
    raise SystemExit(0 if ok else 1)
