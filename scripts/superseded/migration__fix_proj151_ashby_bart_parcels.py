#!/usr/bin/env python3
from __future__ import annotations
# ============================ SEQUESTERED 2026-09-29 ============================
# DO NOT RUN. Original path: scripts/migration/fix_proj151_ashby_bart_parcels.py
# WHY: Applied one-time v2 write (John, 2026-09-28).
raise SystemExit('SEQUESTERED 2026-09-29 -- see header; original path scripts/migration/fix_proj151_ashby_bart_parcels.py')
# ================================================================================
r"""fix_proj151_ashby_bart_parcels.py -- proj151 (Ashby BART) is on the wrong parcel.
PREVIEW BY DEFAULT; --commit needs John's go-ahead and an unlocked DB.

THE DEFECT. proj151 is Berkeley's largest tracked project -- 618 units, 309 of them affordable, the
Ashby BART joint development at Adeline and Ashby. v2 links it to APN 053-1652-001-05, which the
County documents as **1099 ASHBY AVE, zip 94710** -- West Berkeley, $5.49M of improvements, 1.5 km
WEST of the station. It is on Ashby AVENUE but at the wrong end of it: a street-name match that
landed in the wrong neighbourhood.

This is NOT the ambiguous case CLAUDE.md rule 4 protects (absent-from-assessor, where re-platted and
too-new look identical). The stored APN is affirmatively documented at a different address, so it is a
WRONG VALUE, not a stale one. Rule 4's own text allows the re-point where the correct parcel is
"AFFIRMATIVELY documented at the exact address".

THE EVIDENCE for the two parcels (John's local knowledge + the assessor):
  053-1597-039-04   " ADELINE ST" 94703, 194,348 sqft (4.5 ac), UseCode 0300 (tax-exempt: zero
                    improvements, zero land value, no street number -- the signature of a public
                    agency), 17 m from the coordinates v2 ALREADY holds for proj151, and its last
                    recorded document is **1971-03-01**. BART's Berkeley service opened in 1972, so a
                    1971 conveyance is exactly when BART acquired the station site. -> PRIMARY.
  053-1703-009-00   " ADELINE ST" 94703, 79,542 sqft (1.8 ac), also exempt, 123 m FURTHER EAST
                    (-122.26887 vs -122.27027) -- the separate parking lot east of Adeline, which
                    John identified as a distinct lot. -> SECONDARY (John: two parcels).

proj151's stored coordinates (37.8531, -122.2704) were ALREADY correct and are not touched; it was
only the parcel that was wrong, which is why the error survived -- the map looked right.

WHY NOT parcel_lineage. That table records prior->child parcel events (re-plats, renumbering). This is
not lineage: 1099 Ashby Ave was never this project's parcel, so there is no ancestry to record. The
correction is recorded as an append-only `observation` event naming the old APN, the new ones and the
evidence, plus notes on the new links.

  .venv/bin/python scripts/migration/fix_proj151_ashby_bart_parcels.py            # preview
  .venv/bin/python scripts/migration/fix_proj151_ashby_bart_parcels.py --commit
"""

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from housing_rules import to_canonical_apn            # noqa: E402  THE canon

V2 = ROOT / "databases/berkeley_housing_v2.db"
ASSESSOR = ROOT / "databases/berkeley.db"
PROJ = 151
WRONG_APN = "053-1652-001-05"
OBSERVED_BY = "proj151_ashby_bart_parcel_fix@2026-09-28"
EV_OBSERVATION, CONF_HIGH = 24, 1
# (assessor APN, relationship_type_id, is_primary, why)
TARGETS = [
    ("53-1597-39-4", 1, 1, "station block and west surface lot; exempt, 4.5 ac, 17 m from the "
                           "project's own coordinates, last conveyance 1971-03-01 (BART Berkeley "
                           "opened 1972)"),
    ("53-1703-9", 2, 0, "separate parking lot east of Adeline, 123 m east of the station block; "
                        "exempt, 1.8 ac (John, 2026-09-28: two parcels)"),
]


def assessor_rows():
    db = sqlite3.connect(f"file:{ASSESSOR}?mode=ro", uri=True)
    out = {}
    for apn, addr, lot, lat, lon in db.execute(
            "SELECT APN,SitusAddre,LotSize,Latitude,Longitude FROM parcels WHERE APN IN (?,?)",
            tuple(t[0] for t in TARGETS)):
        out[apn] = {"situs": " ".join(str(addr or "").split()),
                    "lot": int(str(lot or "0").replace(",", "") or 0),
                    "lat": lat, "lon": lon}
    return out


def plan(db):
    asr = assessor_rows()
    steps = []
    for apn, rel, prim, why in TARGETS:
        c = to_canonical_apn(apn, "alameda")
        row = db.execute("SELECT id FROM parcels WHERE apn_normalized=?", (c,)).fetchone()
        steps.append({"apn_raw": apn, "canon": c, "existing_parcel_id": row[0] if row else None,
                      "rel": rel, "is_primary": prim, "why": why, **asr.get(apn, {})})
    old = db.execute("SELECT pp.id,pp.parcel_id,p.apn_normalized FROM project_parcels pp "
                     "JOIN parcels p ON p.id=pp.parcel_id WHERE pp.project_id=?",
                     (PROJ,)).fetchall()
    return steps, old


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    db = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)

    # IDEMPOTENCY. Without this, a second run deletes the CORRECT links, re-adds them with new ids,
    # and appends a SECOND correction event -- the net data is identical but the history is not, and
    # an append-only record that can be appended twice for one correction is no longer a record of
    # what happened. Checked before anything is planned.
    want = {to_canonical_apn(a, "alameda") for a, *_ in TARGETS}
    have = {r[0]: r[1] for r in db.execute(
        "SELECT p.apn_normalized, pp.is_primary FROM project_parcels pp "
        "JOIN parcels p ON p.id=pp.parcel_id WHERE pp.project_id=?", (PROJ,))}
    primary_ok = have.get(to_canonical_apn(TARGETS[0][0], "alameda")) == 1
    if set(have) == want and primary_ok:
        print(f"proj{PROJ} ALREADY carries exactly the two correct parcels "
              f"({', '.join(sorted(want))}), primary set correctly. Nothing to do.")
        return 0

    steps, old = plan(db)
    addr, units = db.execute("SELECT canonical_address,"
                             "(SELECT total_units FROM project_versions WHERE project_id=? "
                             " AND is_current=1) FROM projects WHERE id=?",
                             (PROJ, PROJ)).fetchone()
    print(f"proj{PROJ}  {addr!r}  {units} units\n")
    print("REMOVE these project_parcels links:")
    for pid, parcel_id, apn in old:
        shared = db.execute("SELECT COUNT(*) FROM project_parcels WHERE parcel_id=? "
                            "AND project_id<>?", (parcel_id, PROJ)).fetchone()[0]
        print(f"   link id={pid} -> parcel {parcel_id} ({apn})   "
              f"{'WRONG: 1099 Ashby Ave, 94710, 1.5 km west' if apn == WRONG_APN else ''}")
        print(f"      that parcel row is shared with {shared} other project(s) -- "
              f"{'kept, only the LINK is removed' if shared == 0 else 'MUST NOT be deleted'}")
    print("\nADD:")
    for s in steps:
        kind = "PRIMARY" if s["is_primary"] else "secondary"
        print(f"   {kind:9} {s['canon']}  ({s['apn_raw']})  {s.get('situs')!r}")
        print(f"      lot {s.get('lot'):,} sqft · parcels row "
              f"{'exists id=' + str(s['existing_parcel_id']) if s['existing_parcel_id'] else 'NEEDS INSERT'}")
        print(f"      {s['why']}")
    print("\nplus one append-only `observation` event recording the correction and its evidence.")
    print("proj151's coordinates are NOT touched (they were already correct).")
    db.close()
    if not args.commit:
        print("\nPREVIEW ONLY -- nothing written.")
        return 0

    snap = ROOT / f"databases/keep_snapshot_{time.strftime('%Y-%m-%d')}_pre-proj151_parcels.db"
    if not snap.exists():
        shutil.copy2(V2, snap)
    print(f"\nsnapshot {snap.name} ({snap.stat().st_size:,} bytes)")
    w = sqlite3.connect(V2)
    if w.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit("integrity_check failed -- aborting")
    w.execute("PRAGMA foreign_keys=ON")
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    before_links = w.execute("SELECT COUNT(*) FROM project_parcels WHERE project_id=?",
                             (PROJ,)).fetchone()[0]
    try:
        w.execute("BEGIN")
        # 1. drop the wrong LINK only; the parcel row itself is a real parcel and is kept
        for pid, parcel_id, apn in old:
            if w.execute("SELECT COUNT(*) FROM project_parcels WHERE parcel_id=? AND project_id<>?",
                         (parcel_id, PROJ)).fetchone()[0] == 0:
                pass  # not shared: safe to unlink, parcel row retained
            cur = w.execute("DELETE FROM project_parcels WHERE id=?", (pid,))
            if cur.rowcount != 1:
                raise RuntimeError(f"rowcount {cur.rowcount} deleting link {pid}")
        # 2. ensure both parcels exist, then link
        for s in plan(w)[0]:
            parcel_id = s["existing_parcel_id"]
            if parcel_id is None:
                city = w.execute("SELECT city_id FROM projects WHERE id=?", (PROJ,)).fetchone()[0]
                cur = w.execute(
                    "INSERT INTO parcels (city_id,apn,address,lot_sqft,apn_raw,apn_normalized,"
                    "assessing_county,geometry_source,notes) VALUES (?,?,?,?,?,?,'Alameda',?,?)",
                    (city, s["canon"], s.get("situs"), s.get("lot"), s["apn_raw"], s["canon"],
                     "alameda_assessor_2026-06-16",
                     f"Ashby BART; added 2026-09-28 correcting proj{PROJ} off {WRONG_APN} "
                     f"(1099 Ashby Ave, 94710 -- wrong end of Ashby Ave, 1.5 km west)"))
                parcel_id = cur.lastrowid
            cur = w.execute("INSERT INTO project_parcels (project_id,parcel_id,"
                            "relationship_type_id,is_primary,notes) VALUES (?,?,?,?,?)",
                            (PROJ, parcel_id, s["rel"], s["is_primary"], s["why"]))
            if cur.rowcount != 1:
                raise RuntimeError(f"rowcount {cur.rowcount} linking {s['canon']}")
        # 3. append-only record of the correction
        w.execute("INSERT INTO project_events (project_id,event_type_id,event_date,"
                  "event_date_precision,summary,details,confidence_type_id,is_inferred,"
                  "source_type,source_url,observed_by,observed_at) "
                  "VALUES (?,?,?,'exact',?,?,?,0,'observation',?,?,?)",
                  (PROJ, EV_OBSERVATION, now[:10],
                   f"Parcel correction: {WRONG_APN} was not this project's parcel",
                   "proj151 Ashby BART was linked to 053-1652-001-05, which the County documents as "
                   "1099 ASHBY AVE 94710 -- West Berkeley, 1.5 km west of the station, $5.49M "
                   "improvements. Re-pointed to 053-1597-039-04 (primary: station block and west "
                   "surface lot, exempt, 194,348 sqft, 17 m from the project's stored coordinates, "
                   "last conveyance 1971-03-01, BART Berkeley opened 1972) and 053-1703-009-00 "
                   "(secondary: separate lot 123 m east of Adeline). Not recorded as parcel_lineage: "
                   "1099 Ashby Ave was never this project's parcel, so there is no ancestry. "
                   "Coordinates unchanged -- they were already correct, which is why the wrong parcel "
                   "survived. John's ruling 2026-09-28: two parcels.",
                   CONF_HIGH, "Alameda assessor 2026-06-16 refresh; John 2026-09-28", OBSERVED_BY,
                   now))
        after = w.execute("SELECT COUNT(*) FROM project_parcels WHERE project_id=?",
                          (PROJ,)).fetchone()[0]
        if after != 2:
            raise RuntimeError(f"verify failed: proj{PROJ} has {after} parcel links, expected 2")
        prim = w.execute("SELECT COUNT(*) FROM project_parcels WHERE project_id=? AND is_primary=1",
                         (PROJ,)).fetchone()[0]
        if prim != 1:
            raise RuntimeError(f"verify failed: {prim} primary parcels, expected exactly 1")
        still = w.execute("SELECT COUNT(*) FROM project_parcels pp JOIN parcels p "
                          "ON p.id=pp.parcel_id WHERE pp.project_id=? AND p.apn_normalized=?",
                          (PROJ, WRONG_APN)).fetchone()[0]
        if still:
            raise RuntimeError("the wrong APN is still linked")
        w.commit()
        print(f"committed: links {before_links} -> {after} (1 primary, 1 secondary), "
              f"correction event recorded")
    except Exception as e:
        w.rollback()
        print(f"ROLLED BACK: {e}")
        return 1
    finally:
        w.close()
    f = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    print("fresh-connection fingerprint:")
    for r in f.execute("SELECT p.apn_normalized,p.address,pp.is_primary,pp.relationship_type_id "
                       "FROM project_parcels pp JOIN parcels p ON p.id=pp.parcel_id "
                       "WHERE pp.project_id=? ORDER BY pp.is_primary DESC", (PROJ,)):
        print(f"   {r[0]}  {r[1]!r}  primary={r[2]} rel={r[3]}")
    print("   integrity", f.execute("PRAGMA integrity_check").fetchone()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
