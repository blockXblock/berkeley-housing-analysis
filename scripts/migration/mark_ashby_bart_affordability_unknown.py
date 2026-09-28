#!/usr/bin/env python3
r"""mark_ashby_bart_affordability_unknown.py -- proj151 Ashby BART: affordability becomes UNKNOWN
WITH PROVENANCE, per John, 2026-09-28 ("yes, mark Ashby BART unknown with provenance").

WHY. v2 asserts 309 VLI + 309 ABOVE_MOD on Ashby BART's 618 units. That 50/50 split is a PLANNING
TARGET carried in by migrate_v1_to_v2 (2026-05-07), not an entitled or cited figure: the site is
pre-entitlement, and the CapDetail harvest found NO Berkeley planning record on either Ashby BART
parcel, so no document exists to source it from. CLAUDE.md rule 1 is explicit -- where primary
sources are silent, record "unknown with provenance", never a filled figure. Ledger row A900 already
records the ruling; this is the v2 side of it.

WHAT IT CHANGES (both rows kept, nothing deleted, so a restore is two category ids):
  A  unit_program_affordability id 137  VLI(2)       -> UNKNOWN(6), provenance appended
     unit_program_affordability id 138  ABOVE_MOD(5) -> UNKNOWN(6), provenance appended
     309 + 309 = 618 is preserved; the SPLIT is what was never sourced, and UNKNOWN(6) is the
     established convention here (712 rows already use it).
  B  project_versions.description for proj151 -- the published string reads "618 units, 50%
     affordable", which is the SAME unsourced figure. Marking the DB unknown while the explorer keeps
     publishing "50% affordable" would leave the claim in the one place the public actually reads.

PUBLISHED EFFECT, stated because it is large: proj151 contributes 309 of the city-wide 1,085 VLI
units in v_projects_flat -- 28%. After this write that total reads 776. The units do NOT vanish
(total_units stays 618); their TIER becomes unknown. The APR's RHNA tables credit on BP issuance and
Ashby BART has no BP, so Table A is unaffected; the explorer's affordability display is.

  --preview   read-only, prints before/after and changes nothing   (run this first)
  --apply     transactional, per-row rowcount==1, verify-or-rollback, fresh-connection fingerprint
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / "databases/berkeley_housing_v2.db"
UNKNOWN = 6
ROWS = {137: 2, 138: 5}                    # id -> the category id it must currently hold
PROV = (" | 2026-09-28 John: UNKNOWN WITH PROVENANCE. The 309 VLI / 309 ABOVE_MOD split was a 50% "
        "planning target, not an entitled or cited figure; Ashby BART is pre-entitlement and the "
        "CapDetail harvest found no Berkeley planning record on either station parcel "
        "(053-1597-039-04, 053-1703-009-00), so there is no document to source a tier from. "
        "CLAUDE.md rule 1. Ledger corrections/v4/affordability_rulings.csv A900.")
OLD_DESC = ("618 units, 50% affordable. Developer Adeline Alliance/Relequity selected Aug 2025. "
            "BART transit-oriented development.")
NEW_DESC = ("618 units; affordability UNKNOWN -- the 50% figure is a planning target, not an "
            "entitlement (no planning record exists on the station parcels). Developer Adeline "
            "Alliance/Relequity selected Aug 2025. BART transit-oriented development.")


def show(db) -> None:
    print("  unit_program_affordability:")
    for r in db.execute("""SELECT a.id, ic.code, a.unit_count, substr(a.asserted_by,1,60)
                           FROM unit_program_affordability a
                           JOIN vocabulary_income_categories ic ON ic.id = a.income_category_id
                           WHERE a.id IN (137,138) ORDER BY a.id"""):
        print(f"     id {r[0]}  {r[1]:10} {r[2]:4}u   {r[3]}...")
    print("  v_projects_flat proj151:",
          db.execute("""SELECT total_units, eli_units, vli_units, li_units, mod_units, market_units
                        FROM v_projects_flat WHERE project_id=151""").fetchone(),
          "(total, eli, vli, li, mod, market)")
    print("  city-wide VLI:", db.execute("SELECT SUM(vli_units) FROM v_projects_flat").fetchone()[0])
    print("  description:", (db.execute("SELECT description FROM project_versions "
                                        "WHERE project_id=151").fetchone() or [None])[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.preview or args.apply):
        print(__doc__)
        return 2

    if args.preview:
        db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        print("BEFORE (read-only):")
        show(db)
        print("\nWOULD CHANGE:")
        for rid, cur in ROWS.items():
            print(f"  A  unit_program_affordability id {rid}: income_category_id {cur} -> {UNKNOWN}"
                  f" (UNKNOWN), asserted_by += provenance")
        print(f"  B  project_versions.description for proj151 -> {NEW_DESC[:80]}...")
        print("\nNOTHING WRITTEN. Re-run with --apply (the DB must be writable).")
        return 0

    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    before = db.execute("SELECT SUM(vli_units) FROM v_projects_flat").fetchone()[0]
    try:
        with db:
            for rid, cur in ROWS.items():
                # GUARDED: the row must still hold the category this script was written against.
                cur_now = db.execute("SELECT income_category_id FROM unit_program_affordability "
                                     "WHERE id=?", (rid,)).fetchone()
                if not cur_now or cur_now[0] != cur:
                    raise RuntimeError(f"id {rid} holds {cur_now}, expected {cur} -- refusing")
                c = db.execute("UPDATE unit_program_affordability "
                               "SET income_category_id=?, asserted_by = asserted_by || ? "
                               "WHERE id=? AND income_category_id=?",
                               (UNKNOWN, PROV, rid, cur))
                if c.rowcount != 1:
                    raise RuntimeError(f"id {rid}: rowcount {c.rowcount} != 1")
            c = db.execute("UPDATE project_versions SET description=? "
                           "WHERE project_id=151 AND description=?", (NEW_DESC, OLD_DESC))
            if c.rowcount != 1:
                raise RuntimeError(f"description: rowcount {c.rowcount} != 1 "
                                   f"(already changed, or text differs)")
            after = db.execute("SELECT vli_units, total_units FROM v_projects_flat "
                               "WHERE project_id=151").fetchone()
            if after[0] != 0 or after[1] != 618:
                raise RuntimeError(f"verify failed: proj151 reads vli={after[0]} total={after[1]}")
        print("COMMITTED.")
    except Exception as e:
        print(f"ROLLED BACK: {e}")
        return 1
    db.close()
    fresh = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)      # fresh-connection fingerprint
    print("\nAFTER (fresh connection):")
    show(fresh)
    print(f"\ncity-wide VLI {before} -> "
          f"{fresh.execute('SELECT SUM(vli_units) FROM v_projects_flat').fetchone()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
