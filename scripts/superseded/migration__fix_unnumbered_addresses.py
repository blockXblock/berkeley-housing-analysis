#!/usr/bin/env python3
from __future__ import annotations
# ============================ SEQUESTERED 2026-09-29 ============================
# DO NOT RUN. Original path: scripts/migration/fix_unnumbered_addresses.py
# WHY: Applied one-time v2 write (John, 2026-09-28).
raise SystemExit('SEQUESTERED 2026-09-29 -- see header; original path scripts/migration/fix_unnumbered_addresses.py')
# ================================================================================
r"""fix_unnumbered_addresses.py -- give the "0 <street>" placeholder projects their real addresses.
PREVIEW BY DEFAULT; --commit needs John's go-ahead and an unlocked DB.

THE FINDING (John, 2026-09-26). "0 <street>" is not bad data: it is how ONE city department records an
unnumbered or vacant parcel, and the same structure often carries a real street address from a
DIFFERENT department. Three sources, three answers for the same parcel -- proj73 is filed by Planning
as "0 LE ROY Ave", the County assessor's situs is BLANK, and the City's own address-point layer says
**1463 Le Roy Ave**. "Unnumbered" was never a fact about the parcel, only about who was asked.

SOURCES, both primary (never CKAN -- working rule 1):
  * `data/reference/berkeley_addresses_with_fields.csv` -- the CITY address-point layer, keyed here by
    canonical APN via housing_rules.to_canonical_apn (25,511 rows resolve).
  * `databases/berkeley.db` parcels.SitusAddre -- the COUNTY assessor situs.

INDEPENDENT CHECK. Each resolved address is only accepted if the address-point COORDINATES fall within
a short distance of the coordinates v2 already holds for the project. That makes the claim falsifiable
on geometry rather than on a string match: proj73's stored point is ~4 m from 1463 Le Roy's.

THE ORIGINAL IS KEPT, not overwritten. v2 has a purpose-built `project_addresses` history table
(is_current / change_reason / asserted_by / notes). The placeholder is retained as a superseded row
with is_current=0 and the new row records where the number came from. `projects.canonical_address` is
then updated so the site and its geocoding see the real address.

  .venv/bin/python scripts/migration/fix_unnumbered_addresses.py            # preview
  .venv/bin/python scripts/migration/fix_unnumbered_addresses.py --commit   # after go-ahead
"""

import argparse
import csv
import math
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from housing_rules import to_canonical_apn                     # noqa: E402  THE APN canon
from housing_rules.address import normalize_address            # noqa: E402  THE rule-4c canon

V2 = ROOT / "databases/berkeley_housing_v2.db"
ASSESSOR = ROOT / "databases/berkeley.db"
POINTS = ROOT / "data/reference/berkeley_addresses_with_fields.csv"
OBSERVED_BY = "unnumbered_address_resolution@2026-09-26"
CONF_HIGH, CONF_MED = 1, 2
MAX_METRES = 120          # a parcel's own address point should be within a lot's width


def _f(x):
    """coords arrive as str from the assessor and float from the CSV -- coerce, never assume."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def metres(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = _f(lat1), _f(lon1), _f(lat2), _f(lon2)
    if None in (lat1, lon1, lat2, lon2):
        return None
    dlat = (lat2 - lat1) * 111_320
    dlon = (lon2 - lon1) * 111_320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dlat, dlon)


def address_points() -> dict:
    """canonical APN -> (address, lat, lon) from the City address-point layer."""
    out = {}
    with open(POINTS) as f:
        for row in csv.DictReader(f):
            apn = (row.get("APN") or "").strip()
            addr = (row.get("ADDRESS") or "").strip()
            if not apn or not addr:
                continue
            try:
                k = to_canonical_apn(apn, "alameda")
            except Exception:
                continue
            # THE FILE CARRIES TWO COORDINATE SYSTEMS. X_CORD/Y_CORD are WEB MERCATOR
            # (-13609197, 4563294) and there are separate `longitude`/`latitude` columns in WGS84.
            # Reading X_CORD/Y_CORD as lat/long produced a 1.5-trillion-metre "distance" and rejected
            # a CORRECT address (1298 Queens Rd), while rows with X_CORD blank but longitude present
            # looked like they had no point at all. Use the WGS84 pair.
            lat, lon = _f(row.get("latitude")), _f(row.get("longitude"))
            out.setdefault(k, (addr, lat, lon))
    return out


def assessor_situs() -> dict:
    out = {}
    db = sqlite3.connect(f"file:{ASSESSOR}?mode=ro", uri=True)
    for apn, addr, lat, lon in db.execute(
            "SELECT APN,SitusAddre,Latitude,Longitude FROM parcels WHERE APN IS NOT NULL"):
        try:
            k = to_canonical_apn(apn, "alameda")
        except Exception:
            continue
        # the assessor situs carries a "<CITY> <ZIP>" tail ("1024 GRIZZLY PEAK BLVD BERKELEY 94708");
        # v2 stores street addresses alone ("1974 SHATTUCK Ave"), so trim it rather than store a
        # differently-shaped string that every later address key would have to cope with.
        a = " ".join(str(addr or "").split())
        a = re.sub(r"\s+BERKELEY(\s+CA)?(\s+\d{5}(-\d{4})?)?\s*$", "", a, flags=re.I).strip()
        # a situs with no house number is the same placeholder problem, not an answer
        if a and normalize_address(a)[0]:
            out[k] = (a, lat, lon)
    return out


def build_plan(db):
    pts, sit = address_points(), assessor_situs()
    plan, rejected = [], []
    for pid, addr, lat, lon in db.execute(
            "SELECT id,canonical_address,latitude,longitude FROM projects "
            "WHERE canonical_address IS NOT NULL AND merged_into_id IS NULL"):
        if normalize_address(addr)[0] != "0":
            continue
        apns = [r[0] for r in db.execute(
            "SELECT p.apn_normalized FROM project_parcels pp JOIN parcels p ON p.id=pp.parcel_id "
            "WHERE pp.project_id=? AND p.apn_normalized IS NOT NULL", (pid,))]
        cands = []
        for k in apns:
            if k in pts:
                cands.append(("city_address_points", *pts[k]))
            if k in sit:
                cands.append(("county_assessor_situs", *sit[k]))
        if not cands:
            rejected.append((pid, addr, apns, "no address in either source"))
            continue
        # agreement between the two independent sources is the strongest evidence
        streets = {normalize_address(c[1]) for c in cands}
        both = len({c[0] for c in cands}) > 1 and len(streets) == 1
        src, new_addr, plat, plon = cands[0]
        d = metres(lat, lon, plat, plon)
        if d is not None and d > MAX_METRES:
            rejected.append((pid, addr, apns,
                             f"{new_addr!r} from {src} is {d:.0f} m from the project's own point "
                             f"(limit {MAX_METRES} m) -- NOT accepted"))
            continue
        plan.append({"project_id": pid, "old": addr, "new": new_addr,
                     "sources": sorted({c[0] for c in cands}), "agree": both,
                     "metres": d, "apns": apns,
                     "confidence": CONF_HIGH if both else CONF_MED})
    return plan, rejected


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    db = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    plan, rejected = build_plan(db)
    print(f'projects whose address is a "0 <street>" placeholder and which RESOLVE: {len(plan)}\n')
    for r in plan:
        d = f"{r['metres']:.0f} m" if r["metres"] is not None else "no point"
        print(f"  proj{r['project_id']:<5} {r['old']!r}  ->  {r['new']!r}")
        print(f"        sources={r['sources']} agree={r['agree']} "
              f"distance-from-stored-point={d} apn={r['apns']}")
    if rejected:
        print(f"\n  NOT resolved ({len(rejected)}):")
        for pid, addr, apns, why in rejected:
            print(f"    proj{pid:<5} {addr!r} apn={apns}: {why}")
    db.close()
    if not args.commit:
        print("\nPREVIEW ONLY -- nothing written. The placeholder is KEPT as a superseded "
              "project_addresses row; only projects.canonical_address is updated.")
        return 0
    if not plan:
        return 0

    snap = ROOT / f"databases/keep_snapshot_{time.strftime('%Y-%m-%d')}_pre-unnumbered_addresses.db"
    if not snap.exists():
        shutil.copy2(V2, snap)
    print(f"\nsnapshot {snap.name} ({snap.stat().st_size:,} bytes)")
    w = sqlite3.connect(V2)
    if w.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit("integrity_check failed -- aborting")
    w.execute("PRAGMA foreign_keys=ON")
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    before = w.execute("SELECT COUNT(*) FROM project_addresses WHERE asserted_by=? AND is_current=1",
                       (OBSERVED_BY,)).fetchone()[0]
    n = 0
    try:
        w.execute("BEGIN")
        for r in plan:
            pid, old, new = r["project_id"], r["old"], r["new"]
            # 1. retain the placeholder as history (insert it if the table never had a row)
            has = w.execute("SELECT COUNT(*) FROM project_addresses WHERE project_id=? AND address=?",
                            (pid, old)).fetchone()[0]
            if has:
                w.execute("UPDATE project_addresses SET is_current=0, end_date=?, "
                          "notes=COALESCE(notes,'')||' | superseded "
                          "2026-09-26: an unnumbered placeholder, not the parcel''s only address' "
                          "WHERE project_id=? AND address=?", (now[:10], pid, old))
            else:
                w.execute("INSERT INTO project_addresses (project_id,address,normalized_address,"
                          "is_current,end_date,change_reason,asserted_by,asserted_at,"
                          "confidence_type_id,notes) VALUES (?,?,?,0,?,?,?,?,?,?)",
                          (pid, old, normalize_address(old)[1].upper(), now[:10],
                           "placeholder_recorded", OBSERVED_BY, now, CONF_HIGH,
                           'the "0 <street>" placeholder v2 held before resolution'))
            # 2. the resolved address becomes current
            w.execute("INSERT INTO project_addresses (project_id,address,normalized_address,"
                      "is_current,start_date,change_reason,asserted_by,asserted_at,"
                      "confidence_type_id,notes) VALUES (?,?,?,1,?,?,?,?,?,?)",
                      (pid, new, normalize_address(new)[1].upper(), now[:10],
                       "resolved_unnumbered_placeholder", OBSERVED_BY, now, r["confidence"],
                       f"was {old!r}; resolved via APN {r['apns']} from "
                       f"{', '.join(r['sources'])}"
                       + ("; both sources agree" if r["agree"] else "; single source")
                       + (f"; {r['metres']:.0f} m from the point v2 already held"
                          if r["metres"] is not None else "")))
            cur = w.execute("UPDATE projects SET canonical_address=?, normalized_address=?, "
                            "updated_at=? WHERE id=?",
                            (new, normalize_address(new)[1].upper(), now, pid))
            if cur.rowcount != 1:
                raise RuntimeError(f"rowcount {cur.rowcount} updating proj{pid}")
            n += 1
        cur_rows = w.execute("SELECT COUNT(*) FROM project_addresses WHERE asserted_by=? "
                             "AND is_current=1", (OBSERVED_BY,)).fetchone()[0]
        # the DELTA, not the total (see ingest_capdetail_events.py)
        if cur_rows != before + n:
            raise RuntimeError(f"verify failed: {before} before + {n} != {cur_rows} current rows")
        bad = w.execute("SELECT COUNT(*) FROM (SELECT project_id FROM project_addresses "
                        "WHERE is_current=1 GROUP BY project_id HAVING COUNT(*)>1)").fetchone()[0]
        if bad:
            raise RuntimeError(f"{bad} projects would have TWO current addresses")
        w.commit()
        print(f"committed: {n} projects re-addressed, placeholders retained as history")
    except Exception as e:
        w.rollback()
        print(f"ROLLED BACK: {e}")
        return 1
    finally:
        w.close()
    f = sqlite3.connect(f"file:{V2}?mode=ro", uri=True)
    print("fresh-connection fingerprint:")
    for r in f.execute("SELECT id,canonical_address FROM projects WHERE id IN "
                       "(SELECT project_id FROM project_addresses WHERE asserted_by=?)",
                       (OBSERVED_BY,)):
        print(f"   proj{r[0]:<5} {r[1]!r}")
    print("   integrity", f.execute("PRAGMA integrity_check").fetchone()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
