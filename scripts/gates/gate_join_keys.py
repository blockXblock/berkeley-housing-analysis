#!/usr/bin/env python3
r"""GATE: a join key must be able to identify ONE thing.

WHY. On 2026-09-26 four projects were "conflated" purely because their address is "0 <street>", a real
city convention for an unnumbered parcel that several distinct APNs share -- keyed literally it matches
every record on the street. Hours later, the write that fixed those addresses set
`normalized_address` to the STREET ALONE ('LE ROY'), recreating the same wildcard in an INDEXED
matching column. Knowing the rule did not prevent it; this gate would have.

WHAT IT CHECKS, in v4 (re-pointed 2026-10-02 from v2's projects/project_addresses/parcels):
  1. no wildcard address keys: an `addresses.normalized` key must carry a real house number. The v4
     form of the 'LE ROY' wildcard is a numberless situs ('7TH ST') parsed as number 7 + street 'th':
     one key then stands for every unnumbered parcel on that street;
  2. one convention in `addresses.normalized` (a column holding two shapes cannot be joined on), and
     one address row per normalized key;
  3. every `parcel_identifiers.apn_normalized` is in the canon's own output form, and a CURRENT
     canonical APN names ONE parcel;
  4. the public and record keys identify one thing: `v_projects.project_key` is present and unique,
     a Planning record (`project_records.record_key`) belongs to one project, and a structure belongs
     to one project. (v2's "two current addresses" check has no v4 meaning: a v4 project's address is
     a single field of the project row.)
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
V4 = f"file:{ROOT/'databases/berkeley_housing_v4.db'}?mode=ro"

# a street that is ONLY an ordinal suffix means the house number swallowed the street's own number
ORDINAL_SUFFIX = ("st", "nd", "rd", "th")


def run() -> tuple[bool, list[str]]:
    db = sqlite3.connect(V4, uri=True)
    msgs, ok = [], True

    # 1. wildcard keys
    q = ",".join("?" * len(ORDINAL_SUFFIX))
    wild = db.execute(
        f"SELECT a.normalized, COUNT(DISTINCT pa.parcel_id), COUNT(DISTINCT ea.event_id) "
        f"FROM addresses a LEFT JOIN parcel_addresses pa USING(address_id) "
        f"LEFT JOIN event_addresses ea USING(address_id) "
        f"WHERE LOWER(a.street) IN ({q}) OR a.number IS NULL OR a.number = '' "
        f"   OR a.number NOT GLOB '[0-9]*' "
        f"GROUP BY a.address_id ORDER BY 2 DESC", ORDINAL_SUFFIX).fetchall()
    if wild:
        ok = False
        msgs.append(f"FAIL wildcard keys: {len(wild)} addresses.normalized keys have no real house "
                    f"number (a numberless '7TH ST' read as 7|th), covering "
                    f"{sum(w[1] for w in wild)} parcel links and {sum(w[2] for w in wild)} event "
                    f"links -- e.g. {[(w[0], w[1]) for w in wild[:4]]}")
    else:
        msgs.append("ok   wildcard keys: every addresses.normalized key carries a house number")

    # 2. one convention, one row per key
    shapes = collections.Counter()
    for (v,) in db.execute("SELECT normalized FROM addresses WHERE normalized IS NOT NULL"):
        shapes["pipe" if "|" in v else ("space" if re.match(r"^\d+\s", v) else "other")] += 1
    if len([k for k, n in shapes.items() if n]) > 1:
        ok = False
        msgs.append(f"FAIL mixed conventions in addresses.normalized: {dict(shapes)} -- "
                    f"a matching column with two shapes cannot be joined on")
    else:
        msgs.append(f"ok   one convention in addresses.normalized: {dict(shapes)}")
    dupkey = db.execute("SELECT COUNT(*) FROM (SELECT normalized FROM addresses "
                        "WHERE normalized IS NOT NULL GROUP BY 1 HAVING COUNT(*)>1)").fetchone()[0]
    if dupkey:
        ok = False
        msgs.append(f"FAIL {dupkey} normalized address keys have more than one addresses row")
    else:
        msgs.append("ok   one addresses row per normalized key")

    # 3. APN canon + one parcel per current APN
    bad = []
    for (a,) in db.execute("SELECT apn_normalized FROM parcel_identifiers "
                           "WHERE apn_normalized IS NOT NULL"):
        try:
            if to_canonical_apn(a, "alameda") != a:
                bad.append(a)
        except Exception:
            bad.append(a)
    if bad:
        ok = False
        msgs.append(f"FAIL {len(bad)} parcel_identifiers.apn_normalized are not the canon's own "
                    f"output: {bad[:4]}")
    else:
        msgs.append("ok   every parcel_identifiers.apn_normalized is canonical")
    multi = db.execute("SELECT COUNT(*) FROM (SELECT apn_normalized FROM parcel_identifiers "
                       "WHERE is_current=1 AND apn_normalized IS NOT NULL GROUP BY 1 "
                       "HAVING COUNT(DISTINCT parcel_id)>1)").fetchone()[0]
    if multi:
        ok = False
        msgs.append(f"FAIL {multi} current canonical APNs name more than one parcel")
    else:
        msgs.append("ok   each current canonical APN names one parcel")

    # 4. project / record / structure keys
    n, n_key, n_distinct = db.execute(
        "SELECT COUNT(*), COUNT(project_key), COUNT(DISTINCT project_key) FROM v_projects").fetchone()
    if n_key != n or n_distinct != n:
        ok = False
        msgs.append(f"FAIL project_key: {n} projects, {n_key} with a key, {n_distinct} distinct")
    else:
        msgs.append(f"ok   project_key present and unique on all {n} projects")
    rec = db.execute("SELECT COUNT(*) FROM (SELECT record_key FROM project_records GROUP BY 1 "
                     "HAVING COUNT(DISTINCT project_id)>1)").fetchone()[0]
    st = db.execute("SELECT COUNT(*) FROM (SELECT structure_id FROM project_structures GROUP BY 1 "
                    "HAVING COUNT(*)>1)").fetchone()[0]
    if rec or st:
        ok = False
        msgs.append(f"FAIL {rec} Planning records and {st} structures belong to more than one project")
    else:
        msgs.append("ok   every Planning record and every structure belongs to one project")
    return ok, msgs


if __name__ == "__main__":
    ok, m = run()
    print("\n".join(m))
    raise SystemExit(0 if ok else 1)
