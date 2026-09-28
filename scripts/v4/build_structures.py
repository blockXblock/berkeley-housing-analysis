#!/usr/bin/env python3
r"""build_structures.py -- THE BUILDINGS STAGE. Fold v4's event stream into STRUCTURES.
READ-ONLY by default; --commit is gated on John and an unlocked v4.

WHY A STAGE AND NOT A PATCH. Counting per permit double-counts a building permitted in phases (Logan
Park South: Phase I B2019-05575 and Phase II B2021-03302, one 69-unit building) and merges buildings
that merely share an address (Acheson Commons A/B/C/D, four buildings, 205 units). Neither is fixable
per permit: both need a view in which a BUILDING is the thing that exists. v4 was designed for this --
`structures`, `structure_events`, `structure_parcels` have been sitting empty with the answer in the
schema comment: `master_event_id -- the New master permit-event (identity)`.

IDENTITY, NOT AGGREGATION. A structure IS a city action -- the master permit event that created it --
not an address, not a parcel, not a fuzzy cluster. Everything else attaches to that. This is the same
principle as docs/methodology/identity_is_the_product.md one level up: the reason permit counting
fails is that a permit is not a building, and no aggregate over permits can invent the missing
referent.

THE FOLD
  1. SEED      one candidate structure per master permit (is_master=1).
  2. MERGE     masters at the SAME SITE that the text says are one building
               (housing_rules.building_label.same_building -> True). Acheson A vs D returns False and
               stays four; Logan South Phase I vs II returns True and becomes one.
  3. ATTACH    non-master permits, by DETERMINISTIC lineage first:
                 a. permit-number suffix  B2021-03302-REV1 -> B2021-03302   (4,215 permits carry one)
                 b. an explicit non-demolition cross-reference to a master in the description
               A demolition reference is NOT a parent ("refer to BP # ... for Demo").
  4. COUNT     units once per structure, from the master (or the completing phase).
  5. COMPLETE  completed_on = MAX(completion-signal date) over the structure's events -- MAX is right
               here, unlike over sibling applications: a structure completes at its LAST completion
               event, and that is what the schema says.

WHAT IT REFUSES TO DO. Where the text does not say whether two masters are one building,
`same_building` returns None and they stay SEPARATE. Merging on a shared address would erase real
buildings -- CLAUDE.md's merge discipline, and the reason "first of two detached houses" is read as a
DESIGNATOR rather than a phase.

CLASSIFICATION IS AN INPUT, NOT A DECISION. The is_master/net_units labels come from
`event_classifications` (currently the regex classifier hash 743edfb626399efc) or, with
--evidence, from a model evidence file. This stage groups; it does not judge what a permit does.
Session 3c owns the classification layer and is retiring the regex.

  .venv/bin/python scripts/v4/build_structures.py                     # preview
  .venv/bin/python scripts/v4/build_structures.py --evidence FILE     # use model labels
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from housing_rules import to_canonical_apn                       # noqa: E402
from housing_rules.address import normalize_address              # noqa: E402
from housing_rules.building_label import extract, same_building   # noqa: E402

V4 = ROOT / "databases/berkeley_housing_v4.db"
OUT = ROOT / "scratch/2026-09-26_structures"
SUFFIX = re.compile(r"^(?P<base>B?\d{4}-\d{3,5})[-\s]*(REV|DEF|PH|R)\s*\d*$", re.I)
COMPLETION = ("permit_finaled", "permit_completed")


def base_permit(key: str) -> str:
    m = SUFFIX.match(str(key or "").strip())
    return m.group("base") if m else str(key or "").strip()


def site_key(apn_raw, address):
    r"""the SITE a permit sits on -- the BLOCK (APN book+page), not the parcel.

    Parcel-level scoping FAILS on the case this stage exists for: Logan Park South's two phase
    permits sit on DIFFERENT parcels (055 189501805 and 055 189504100), so a parcel-scoped comparison
    never even considered merging them and the +69 double survived. Both are book 055, page 1895 --
    the same block. CLAUDE.md rule 4 says APNs are not stable identity, and a phased building being
    re-platted mid-construction is exactly that.

    Widening to the block is safe ONLY because the text rule is conservative: Acheson's A/B/C/D are
    all on block 057-2046 and stay four structures because their designators differ, and
    `same_building` returns None -- no merge -- whenever the text does not positively say two permits
    are one building. The block decides WHO IS COMPARED; the text decides whether they merge.
    """
    if apn_raw:
        try:
            c = to_canonical_apn(apn_raw, "alameda")
            book, page = c.split("-")[0], c.split("-")[1]
            return ("block", f"{book}-{page}")
        except Exception:
            pass
    if address:
        num, street = normalize_address(address)
        if num and street and num != "0":
            return ("addr", f"{num}|{street}")
    return None


def load(db, evidence: Path | None):
    """-> permits: key -> dict(events, description, site, is_master, net_units, label)"""
    cls = {}
    if evidence:
        for row in json.load(open(evidence)):
            pn = row.get("permit") or row.get("permit_number")
            if not pn:
                continue
            eff = row.get("sonnet_effect") or row.get("jev_effect")
            cls[pn] = {"is_master": 1 if eff == "creates" else 0,
                       "net_units": row.get("dwellings_created") or 0,
                       "source": "model_evidence"}
    permits: dict[str, dict] = {}
    for (eid, etype, edate, key, desc, apn, addr, units) in db.execute(
            "SELECT e.event_id, e.event_type_code, e.event_date, e.source_record_key, "
            "e.raw_description, e.raw_apn, e.raw_address, e.raw_units FROM events e"):
        p = permits.setdefault(key, {"events": [], "description": None, "apn": None,
                                     "address": None, "units": None})
        p["events"].append((eid, etype, edate))
        if desc and not p["description"]:
            p["description"] = desc
        p["apn"] = p["apn"] or apn
        p["address"] = p["address"] or addr
        p["units"] = p["units"] if p["units"] is not None else units
    rows = db.execute(
        "SELECT e.source_record_key, MAX(c.is_master) m, MAX(COALESCE(c.net_units,0)) u "
        "FROM events e JOIN event_classifications c USING(event_id) GROUP BY 1").fetchall()
    for key, m, u in rows:
        if key in permits:
            src = cls.get(key)
            permits[key]["is_master"] = src["is_master"] if src else (m or 0)
            permits[key]["net_units"] = src["net_units"] if src else (u or 0)
            permits[key]["cls_source"] = "model_evidence" if src else "v4_event_classifications"
    for key, p in permits.items():
        p.setdefault("is_master", 0)
        p.setdefault("net_units", 0)
        p.setdefault("cls_source", "unclassified")
        p["label"] = extract(p["description"])
        p["site"] = site_key(p["apn"], p["address"])
    return permits


def fold(permits: dict):
    masters = {k: p for k, p in permits.items() if p["is_master"]}
    # 1-2. seed, then merge masters the TEXT says are one building, within a site
    parent = {k: k for k in masters}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    merges = []
    by_site = collections.defaultdict(list)
    for k, p in masters.items():
        if p["site"]:
            by_site[p["site"]].append(k)
    for site, keys in by_site.items():
        for i, a in enumerate(sorted(keys)):
            for b in sorted(keys)[i + 1:]:
                verdict = same_building(masters[a]["label"], masters[b]["label"])
                if verdict is True:
                    union(a, b)
                    merges.append((site, a, b))
    groups = collections.defaultdict(list)
    for k in masters:
        groups[find(k)].append(k)

    # 3. attach non-masters
    master_of_base = {}
    for k in masters:
        master_of_base.setdefault(base_permit(k), k)
    attach, unattached = collections.defaultdict(list), []
    how = collections.Counter()
    for k, p in permits.items():
        if p["is_master"]:
            continue
        b = base_permit(k)
        tgt = master_of_base.get(b) if b != k else None
        if tgt:
            how["permit_number_suffix"] += 1
        else:
            for x in p["label"].xrefs:            # demo_xrefs deliberately excluded
                cand = master_of_base.get(base_permit(x)) or (x if x in masters else None)
                if cand:
                    tgt, _ = cand, how.update(["explicit_cross_reference"])
                    break
        if tgt:
            attach[find(tgt)].append(k)
        else:
            unattached.append(k)
    return groups, attach, merges, how, unattached


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=None, help="model permit-effect evidence JSON")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    if args.commit:
        raise SystemExit("--commit is not implemented yet: this run is a PREVIEW of the fold. "
                         "The v4 write needs John's review of these numbers first.")
    db = sqlite3.connect(f"file:{V4}?mode=ro", uri=True)

    # REFUSE ON AN EMPTY SUBSTRATE rather than report zero. A fold over no classifications yields
    # "0 structures", which is indistinguishable from a correct answer about an empty database and
    # from a v4 whose classification lives somewhere this script is not looking. Today's repeated
    # lesson: a check that cannot tell "nothing there" from "not looking" is not a check. So the
    # preconditions are asserted loudly, with the counts, before anything is folded.
    n_events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    n_cls = db.execute("SELECT COUNT(*) FROM event_classifications").fetchone()[0]
    n_master = db.execute("SELECT COUNT(DISTINCT e.source_record_key) FROM events e "
                          "JOIN event_classifications c USING(event_id) "
                          "WHERE c.is_master=1").fetchone()[0]
    hashes = [r[0] for r in db.execute(
        "SELECT DISTINCT classifier_hash FROM event_classifications")]
    print(f"v4 substrate: {n_events} events · {n_cls} classifications · "
          f"{n_master} master permits · classifier {hashes}")
    if not n_events or not n_cls:
        raise SystemExit("REFUSING: v4 has no events or no classifications. This is not an empty "
                         "answer, it is an absent input.")
    if not n_master and not args.evidence:
        raise SystemExit("REFUSING: zero master permits in event_classifications. Either the "
                         "classification did not land or it lives in an evidence file -- pass "
                         "--evidence. Reporting '0 structures' here would be a false zero.")

    permits = load(db, Path(args.evidence) if args.evidence else None)
    groups, attach, merges, how, unattached = fold(permits)
    if not groups:
        raise SystemExit("REFUSING: the fold produced NO structures from a non-empty substrate -- "
                         "that is a bug in the fold, not a fact about Berkeley.")

    print(f"permits {len(permits)}   masters {sum(1 for p in permits.values() if p['is_master'])}")
    print(f"STRUCTURES folded: {len(groups)}")
    print(f"  masters merged into an existing structure by TEXT: {len(merges)}")
    print(f"  non-master permits attached: {sum(len(v) for v in attach.values())} "
          f"{dict(how)}")
    print(f"  non-master permits UNATTACHED (alterations etc.): {len(unattached)}")

    units = 0
    for root, keys in groups.items():
        units += max(permits[k]["net_units"] or 0 for k in keys)
    print(f"  units counted ONCE per structure: {units}")
    print(f"  (sum over master permits, i.e. the double-counting total: "
          f"{sum(permits[k]['net_units'] or 0 for k in permits if permits[k]['is_master'])})")

    print("\nmerges the text justified:")
    for site, a, b in merges[:12]:
        print(f"   {site}  {a} + {b}")
        print(f"      {str(permits[a]['description'])[:70]}")
        print(f"      {str(permits[b]['description'])[:70]}")

    print("\nthe two cases John sent:")
    for label, keys in (("Logan Park South", ["B2019-05575", "B2021-03302"]),
                        ("Acheson Commons", ["B2015-02995", "B2015-02998", "B2015-03000",
                                             "B2015-03005"])):
        roots = {}
        for k in keys:
            if k in permits and permits[k]["is_master"]:
                roots.setdefault(_root_of(groups, k), []).append(k)
        print(f"   {label}: {len(roots)} structure(s) from {len(keys)} permits -> "
              + " | ".join(",".join(v) for v in roots.values()))
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "structures_preview.jsonl"
    with open(out, "w") as f:
        for root, keys in sorted(groups.items()):
            ev = [e for k in keys + attach.get(root, []) for e in permits[k]["events"]]
            comp = [d for (_, t, d) in ev if t in COMPLETION and d]
            f.write(json.dumps({
                "master_permits": sorted(keys),
                "attached_permits": sorted(attach.get(root, [])),
                "building_label": next((permits[k]["label"].key for k in keys
                                        if permits[k]["label"].key), None),
                "net_units": max(permits[k]["net_units"] or 0 for k in keys),
                "completed_on": max(comp) if comp else None,
                "event_count": len(ev),
                "site": list(permits[keys[0]]["site"] or []),
                "cls_source": permits[keys[0]]["cls_source"],
            }) + "\n")
    import os
    mode = "read-only" if not os.access(V4, os.W_OK) else "WRITABLE (John has it unlocked)"
    print(f"\nPREVIEW written to {out}")
    print(f"nothing in v4 was touched -- opened mode=ro; the file is currently {mode}.")
    return 0


def _root_of(groups, k):
    for root, keys in groups.items():
        if k in keys:
            return root
    return None


if __name__ == "__main__":
    raise SystemExit(main())
