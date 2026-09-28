#!/usr/bin/env python3
r"""baseline_structures.py -- derive the buildings-stage figures and compare them to an EXTERNAL
TIMESTAMPED BASELINE. Read-only; writes only a baseline file when asked.

WHY THIS EXISTS. CLAUDE.md's investigation-JN discipline: derive every figure from the data, then
assert derived == an external timestamped baseline carrying the source sha and per-figure provenance —
never against constants in the logic. Until now the buildings-stage numbers (1,187 structures, 5,439
units, 4,099 units completed 2018-2025) lived in a chat message, which is precisely what that rule
forbids, and a number in a chat message cannot fail.

ANCHORED TO WHAT STAYS TRUE, NOT TO WHAT MOVES. Figures are split:
  INVARIANT   — must not change for a given source sha (the fold is deterministic). A mismatch here
                means the code changed behaviour, and that is a real failure.
  MOVES       — legitimately changes when the substrate is rebuilt or a ruling lands. Recorded with
                its cause so a later change is diagnosable, and NEVER asserted.
A legitimate change is recorded by APPENDING a new dated baseline, never by editing one.

  .venv/bin/python scripts/v4/baseline_structures.py --write     # append a new dated baseline
  .venv/bin/python scripts/v4/baseline_structures.py             # verify against the newest
  .venv/bin/python scripts/v4/baseline_structures.py --db PATH   # against another build
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
BASE = ROOT / "data/baselines"
_spec = importlib.util.spec_from_file_location("bs", ROOT / "scripts/v4/build_structures.py")
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)

WINDOW = ("2018-01-01", "2025-12-31")


def sha16(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()[:16]


def derive(dbpath: Path, parents=None) -> dict:
    db = sqlite3.connect(f"file:{dbpath}?mode=ro", uri=True)
    permits = bs.load(db, None)
    groups, attach, merges, how, unattached = bs.fold(permits, bs.load_parents(parents))
    finals = bs.approved_building_finals(db)
    masters = {k for k, p in permits.items() if p["is_master"]}
    per_structure = 0
    by_basis = {"master_finaled": [], "master_building_final": [],
                "NOT_YET_COMPLETE": [], "STALE_NEEDS_SOURCE": []}
    comp, comp_win = [], []
    for root, keys in groups.items():
        u = max(permits[k]["net_units"] or 0 for k in keys)
        per_structure += u
        # JOHN'S RULING 2026-09-28: completion from the structure's OWN master permit; an approved
        # Building Final inspection where the master never finaled; otherwise HELD.
        date, basis = bs.completion_for(keys, permits, finals)
        by_basis[basis].append({"masters": sorted(keys), "units": u, "date": date})
        if date:
            comp.append(u)
            if WINDOW[0] <= date <= WINDOW[1]:
                comp_win.append(u)
    cls = [r[0] for r in db.execute(
        "SELECT DISTINCT classifier_hash FROM event_classifications")]
    return {
        "invariant": {
            "master_permits": len(masters),
            "structures": len(groups),
            "text_merges": len(merges),
            "non_masters_attached": sum(len(v) for v in attach.values()),
            "attach_by_permit_number": how.get("permit_number_suffix", 0),
            "attach_by_cross_reference": how.get("explicit_cross_reference", 0),
            "units_once_per_structure": per_structure,
            "units_summed_per_master": sum(permits[k]["net_units"] or 0 for k in masters),
            "logan_park_south_structures": _cases(groups, ["B2019-05575", "B2021-03302"]),
            "acheson_commons_structures": _cases(
                groups, ["B2015-02995", "B2015-02998", "B2015-03000", "B2015-03005"]),
        },
        "named_cases": {
            "completion_from_building_final_inspection":
                [x["masters"] + [x["date"]] for x in by_basis["master_building_final"]][:40],
            "stale_needs_source_all": sorted(
                ([x["masters"], x["units"]] for x in by_basis["STALE_NEEDS_SOURCE"]),
                key=lambda r: -r[1]),
            "not_yet_complete_largest_by_units": sorted(
                ([x["masters"], x["units"]] for x in by_basis["NOT_YET_COMPLETE"]),
                key=lambda r: -r[1])[:20],
        },
        "moves": {
            "structures_with_any_completion": len(comp),
            "units_at_completed_structures": sum(comp),
            f"structures_completed_{WINDOW[0][:4]}_{WINDOW[1][:4]}": len(comp_win),
            f"units_completed_{WINDOW[0][:4]}_{WINDOW[1][:4]}": sum(comp_win),
            "completion_basis_master_finaled": len(by_basis["master_finaled"]),
            "completion_basis_building_final_inspection": len(by_basis["master_building_final"]),
            "structures_NOT_YET_COMPLETE_permit_2022plus": len(by_basis["NOT_YET_COMPLETE"]),
            "units_NOT_YET_COMPLETE": sum(x["units"] for x in by_basis["NOT_YET_COMPLETE"]),
            "structures_STALE_NEEDS_SOURCE_permit_pre2022":
                len(by_basis["STALE_NEEDS_SOURCE"]),
            "units_STALE_NEEDS_SOURCE": sum(x["units"] for x in by_basis["STALE_NEEDS_SOURCE"]),
        },
        "provenance": {
            "source_db": str(dbpath.relative_to(ROOT) if dbpath.is_relative_to(ROOT) else dbpath),
            "source_sha16": sha16(dbpath),
            # AN INPUT IS PART OF THE IDENTITY. The parent-lane CSV changes the fold's output
            # legitimately, so a baseline written WITH it is not comparable to a fold run WITHOUT it.
            # Without recording this, the checker compared the two and reported "the fold changed
            # behaviour on the same data -- a code regression", which was false: a stale-check false
            # failure of exactly the kind CLAUDE.md warns erodes trust in checking itself.
            "inputs": {"parents_file": (str(Path(parents).relative_to(ROOT))
                                        if parents and Path(parents).is_relative_to(ROOT)
                                        else (str(parents) if parents else None)),
                       "parents_sha16": sha16(Path(parents)) if parents else None},
            "events": db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "classifier_hash": cls,
            "fold_code": "scripts/v4/build_structures.py",
            "label_rule": "scripts/housing_rules/building_label.py",
            "derived_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "notes": {
                "units_once_per_structure": "max(net_units) over the structure's master permits; "
                                            "the phase rule means the completing phase carries them",
                "completion_rule": "JOHN'S RULING 2026-09-28 'adopt the middle option': completion "
                                   "comes from the structure's OWN master permit. A finaled revision "
                                   "or deferred submittal does NOT complete a building. Where the "
                                   "master never finaled but has an APPROVED 'Building Final' "
                                   "inspection, that date is the completion. Everything else is not "
                                   "counted and not dropped, split into NOT_YET_COMPLETE (permit "
                                   "2022+) and STALE_NEEDS_SOURCE (older, needs the city's record). "
                                   "Rationale: HCD's phase rule. This "
                                   "REPLACES MAX-over-all-events, which gave 860 structures / 4,099 "
                                   "units for 2018-2025 by crediting attached revisions.",
                "moves_why": "these change when the substrate is rebuilt or a completion ruling "
                             "lands; they are recorded, never asserted",
            },
        },
    }


def _cases(groups, keys):
    roots = set()
    for root, ks in groups.items():
        if set(ks) & set(keys):
            roots.add(root)
    return len(roots)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "databases/berkeley_housing_v4.db"))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--label", default=None,
                    help="suffix for a same-day baseline, e.g. completion-ruling. A baseline is "
                         "APPEND-ONLY: a rule change gets a NEW file, never an edit to an old one.")
    ap.add_argument("--parents", default=None)
    args = ap.parse_args()
    got = derive(Path(args.db), args.parents)
    BASE.mkdir(parents=True, exist_ok=True)
    have = sorted(BASE.glob("structures_baseline_*.json"))

    if args.write:
        lab = f"_{args.label}" if args.label else ""
        out = BASE / f"structures_baseline_{time.strftime('%Y-%m-%d')}{lab}.json"
        if out.exists():
            print(f"{out.name} already exists -- a baseline is APPEND-ONLY. Use a later date or "
                  f"delete deliberately.")
            return 1
        out.write_text(json.dumps(got, indent=2) + "\n")
        print(f"wrote {out}")
        for k, v in got["invariant"].items():
            print(f"   invariant  {k:42} {v}")
        for k, v in got["moves"].items():
            print(f"   moves      {k:42} {v}")
        return 0

    if not have:
        print("no baseline exists yet -- run with --write")
        return 1
    # COMPARE LIKE WITH LIKE: the newest baseline built from the SAME inputs, not merely the newest.
    def inputs_of(d):
        return (d.get("provenance", {}).get("inputs") or {}).get("parents_sha16")
    mine = inputs_of(got)
    cands = [f for f in have if inputs_of(json.loads(f.read_text())) == mine]
    if not cands:
        print(f"no baseline was built from these inputs (parents_sha16={mine}); "
              f"{len(have)} exist for other input sets. Run with --write --label to record one. "
              f"NOT comparing -- a cross-input comparison is a false failure, not a check.")
        return 1
    ref = json.loads(cands[-1].read_text())
    print(f"comparing against {cands[-1].name}")
    print(f"  baseline source sha {ref['provenance']['source_sha16']}  "
          f"({ref['provenance']['events']:,} events, {ref['provenance']['classifier_hash']})")
    print(f"  current  source sha {got['provenance']['source_sha16']}  "
          f"({got['provenance']['events']:,} events, {got['provenance']['classifier_hash']})")
    same_src = ref["provenance"]["source_sha16"] == got["provenance"]["source_sha16"]
    bad = []
    for k, v in ref["invariant"].items():
        g = got["invariant"].get(k)
        if g != v:
            bad.append((k, v, g))
    for k, v in ref["moves"].items():
        g = got["moves"].get(k)
        if g != v:
            print(f"  moved  {k}: {v} -> {g}   (expected to move; not a failure)")
    if not bad:
        print("\nINVARIANTS HOLD.")
        return 0
    print("\nINVARIANT MISMATCH -- diagnose before doing anything else:")
    for k, v, g in bad:
        print(f"   {k}: baseline {v}  ->  now {g}")
    print(f"\n  source sha {'IDENTICAL' if same_src else 'DIFFERENT'} between baseline and now.")
    print("  If IDENTICAL, the FOLD CHANGED BEHAVIOUR on the same data -- that is a code regression.")
    print("  If DIFFERENT, the substrate was rebuilt; confirm the change is intended, then APPEND a "
          "new dated baseline. Never edit the old one.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
