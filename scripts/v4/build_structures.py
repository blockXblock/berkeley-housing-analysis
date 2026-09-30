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

  .venv/bin/python scripts/v4/build_structures.py                     # preview (live v4, read-only)
  .venv/bin/python scripts/v4/build_structures.py --evidence FILE     # use model labels
  .venv/bin/python scripts/v4/build_structures.py --db BUILD.db --write   # the BUILD STEP

THE WRITE (added 2026-09-29, cutover phase 2). `--write` fills `structures`, `structure_events`,
`structure_parcels` and `units` in the DB named by --db, in ONE transaction, after clearing all four:
structures are a PROJECTION of the event stream, re-derived on every build, never edited. It runs as
the chain step after JN-F, on the chain's build DB; live v4 receives it the way it receives every
other stage -- by being replaced with a verified build. It REFUSES the live DB unless
BUILD_STRUCTURES_ALLOW_LIVE=1.
"""
from __future__ import annotations

import argparse
import collections
import os
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

# ---------------------------------------------------------------- the completion rule
# JOHN'S RULING, 2026-09-28: "adopt the middle option".
#
#   A structure's completion comes from ITS OWN MASTER PERMIT. A finaled revision or
#   deferred-submittal permit (-REV/-DEF, or any attached non-master) does NOT complete the building:
#   it changes plans, and it does not show the building is occupiable. Where the master has no finaled
#   event but DOES have an APPROVED "Building Final" inspection, that inspection date is the
#   completion. Anything else is NOT COUNTED as complete, and not dropped either -- it is carried
#   with a named reason.
#
# Rationale (John): HCD's phase rule -- the phase whose work completes the units carries them.
#
# This replaces `completed_on = MAX(completion event over ALL the structure's events)`, which the v4
# schema comment describes and which marked 22 structures complete off an attached revision, always
# EARLIER than the master's own evidence. The rule lives here, in code, rather than in a note.
BUILDING_FINAL = "Building Final"
# JOHN'S SECOND RULING, 2026-09-28: "yes, adopt your Building Final recommendation".
#   "Approved with Conditions" COUNTS as an approved final -- a conditional final is still a pass;
#   the city finaled the work. (1 structure / 1 unit.)
#   "Partially Approved" does NOT -- part of the work did not pass, so it is not the building's
#   completion. It stays not-complete. (7 structures / 7 units.)
#   Every other result stays not-complete.
INSPECTION_APPROVED = ("Approved", "Approved with Conditions")

# The build's event stream now also carries PLANNING events (planning_filed / planning_task, added to
# live v4 2026-09-28). This fold is about BUILDINGS: its unit of work is a building permit, and a
# planning record is not one. The keys are disjoint today, so excluding them changes no structure --
# but "changes nothing today" is not a reason to read rows a fold has no rule for, and an event_count
# that silently grows with an unrelated ingest is how a figure drifts without anyone deciding to
# move it.
NOT_A_PERMIT_EVENT = ("planning_filed", "planning_task")

# The not-complete set is NOT a "hold" in the sense of the +147, which is a number we could state and
# deliberately do not. This is the ordinary case of a building that has not finished, plus a tail of
# records where our evidence stops -- and those two need opposite work, so they are named apart
# (3c's naming point, 2026-09-28, adopted):
#   NOT_YET_COMPLETE   permit 2022 or later: plausibly still under construction. Nothing to fix.
#   STALE_NEEDS_SOURCE permit 2021 or earlier and still no completion of its own: either it finished
#                      and we do not hold the evidence, or it expired / was withdrawn / was
#                      re-permitted. Each one needs a look at the city's own record.
# The boundary is the PERMIT YEAR, not a completion date (there is none to read).
STALE_PERMIT_BEFORE = "2022"


def not_complete_category(master_keys) -> str:
    """-> 'NOT_YET_COMPLETE' | 'STALE_NEEDS_SOURCE', from the newest master permit's year."""
    yrs = [m.group(1) for k in master_keys
           for m in [re.search(r"(\d{4})-", str(k))] if m]
    return "NOT_YET_COMPLETE" if (yrs and max(yrs) >= STALE_PERMIT_BEFORE) else "STALE_NEEDS_SOURCE"


def approved_building_finals(db) -> dict:
    """permit -> latest APPROVED 'Building Final' inspection date.

    Berkeley issues no standard Certificate of Occupancy; the closing artifact is an
    inspector-signed final. Only 834 of 32,909 permits have one, so this is strong evidence where it
    exists and never a substitute signal.
    """
    import json as _json
    out = {}
    try:
        rows = db.execute("SELECT source_record_key, raw_payload, event_date FROM events "
                          "WHERE event_type_code='inspection'")
    except Exception:
        return out
    for key, payload, date in rows:
        try:
            p = _json.loads(payload or "{}")
        except Exception:
            continue
        if BUILDING_FINAL in str(p.get("type_code") or "") \
                and str(p.get("result")) in INSPECTION_APPROVED:
            if date and (key not in out or date > out[key]):
                out[key] = date
    return out


def completion_for(master_keys, permits, finals) -> tuple[str | None, str]:
    """-> (date, basis).

    basis is 'master_finaled' | 'master_building_final' (both complete, with a date) or
    'NOT_YET_COMPLETE' | 'STALE_NEEDS_SOURCE' (no date: not counted, not dropped).
    """
    own = [d for k in master_keys for (_, t, d) in permits[k]["events"]
           if t in COMPLETION and d]
    if own:
        return max(own), "master_finaled"
    insp = [finals[k] for k in master_keys if k in finals]
    if insp:
        return max(insp), "master_building_final"
    return None, not_complete_category(master_keys)


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
            "e.raw_description, e.raw_apn, e.raw_address, e.raw_units FROM events e "
            "WHERE e.event_type_code NOT IN (%s)"
            % ",".join("?" * len(NOT_A_PERMIT_EVENT)), NOT_A_PERMIT_EVENT):
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
        "FROM events e JOIN event_classifications c USING(event_id) "
        "WHERE e.event_type_code NOT IN (%s) GROUP BY 1"
        % ",".join("?" * len(NOT_A_PERMIT_EVENT)), NOT_A_PERMIT_EVENT).fetchall()
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


def load_parents(csv_path):
    r"""permit -> parent_permit, from a MODEL-DERIVED parent file. An explicit lane, never implicit.

    My own lineage lanes are (a) the permit NUMBER's -REV/-DEF suffix and (b) an explicit
    cross-reference in the description. Session 3c's evidence file adds 662 NON-SUFFIXED parents a
    permit number cannot reveal -- and note their parents are often OLD-STYLE numbers ("B08-2450",
    "13-0855", "05-4152") that my base_permit() pattern does not even parse, so they must be matched
    as literal keys.

    Kept OPTIONAL and separate for two reasons: the fold must stay runnable without a model pass, and
    `cites` is NOT parentage -- a reference is not belonging, which bit me on Planning records
    ("refer to BP # ... for Demo" is not a parent). Only parent_source='sonnet' rows are read here;
    'permit number' rows duplicate lane (a), and blank rows carry cites only.
    """
    import csv as _csv
    out = {}
    if not csv_path:
        return out
    for row in _csv.DictReader(open(csv_path)):
        if (row.get("parent_source") or "").strip() != "sonnet":
            continue
        pn, par = (row.get("permit") or "").strip(), (row.get("parent_permit") or "").strip()
        if pn and par and pn != par:
            out[pn] = par
    return out


def fold(permits: dict, model_parents: dict | None = None):
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
    model_parents = model_parents or {}
    for k, p in permits.items():
        if p["is_master"]:
            continue
        b = base_permit(k)
        tgt = master_of_base.get(b) if b != k else None
        if tgt:
            how["permit_number_suffix"] += 1
        elif model_parents.get(k):
            par = model_parents[k]
            tgt = (par if par in masters else master_of_base.get(base_permit(par)))
            if tgt:
                how["model_parent_permit"] += 1
        if tgt is None:
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
    ap.add_argument("--parents", default=None,
                    help="model-derived permit_parents.csv; adds the non-suffixed parent lane")
    ap.add_argument("--db", default=str(V4), help="the v4 DB to fold (default: live, read-only)")
    ap.add_argument("--write", action="store_true",
                    help="write structures into --db (a build DB; refuses live without the env flag)")
    args = ap.parse_args()
    dbp = Path(args.db)
    if args.write:
        if dbp.resolve() == V4.resolve() and os.environ.get("BUILD_STRUCTURES_ALLOW_LIVE") != "1":
            raise SystemExit(f"REFUSED: --write targets the LIVE DB ({V4}). Structures reach live by "
                             "replacing it with a verified build. Point --db at the chain's build DB.")
        db = sqlite3.connect(dbp)
    else:
        db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)

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
    groups, attach, merges, how, unattached = fold(permits, load_parents(args.parents))
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
    finals = approved_building_finals(db)
    out = OUT / "structures_preview.jsonl"
    basis_count = collections.Counter()
    with open(out, "w") as f:
        for root, keys in sorted(groups.items()):
            ev = [e for k in keys + attach.get(root, []) for e in permits[k]["events"]]
            comp_date, basis = completion_for(keys, permits, finals)
            basis_count[basis] += 1
            comp = [comp_date] if comp_date else []
            f.write(json.dumps({
                "master_permits": sorted(keys),
                "attached_permits": sorted(attach.get(root, [])),
                "building_label": next((permits[k]["label"].key for k in keys
                                        if permits[k]["label"].key), None),
                "net_units": max(permits[k]["net_units"] or 0 for k in keys),
                "completed_on": comp_date,
                "completion_basis": basis,
                "event_count": len(ev),
                "site": list(permits[keys[0]]["site"] or []),
                "cls_source": permits[keys[0]]["cls_source"],
            }) + "\n")
    print(f"\ncompletion under John's 2026-09-28 ruling: "
          + " ".join(f"{k}={v}" for k, v in basis_count.most_common()))
    print(f"\nPREVIEW written to {out}")
    if not args.write:
        print(f"nothing in {dbp.name} was touched -- opened mode=ro.")
        return 0
    print("\nWRITE:", write(db, permits, groups, attach, finals))
    return 0


def _fold_identity() -> str:
    import hashlib
    here = Path(__file__).read_bytes() + (ROOT / "scripts/housing_rules/building_label.py").read_bytes()
    return "build_structures@" + hashlib.sha256(here).hexdigest()[:12]


def write(con, permits, groups, attach, finals) -> dict:
    """Clear and refill the four structure tables in ONE transaction; verify, else roll back.

    structures        one row per folded group; identity = the ROOT master permit's issuance event
                      (else its earliest event). status = 'complete' or the named not-complete reason.
    structure_events  every event of the group's permits: 'master', 'attached', or 'inspection'.
    structure_parcels every current-or-former parcel a MASTER permit's APN resolves to; primary = root's.
    units             one row per structure with units: count once (max over the masters, the phase
                      rule), tenure and affordability 'unknown' until the ledgers are applied (phase 5).
    """
    fold_id = _fold_identity()
    # Which CURRENT parcel(s) a building sits on: through the County's lineage and John's split rule
    # (housing_rules.parcel_lineage, 2026-09-30) -- never a bare APN lookup, which leaves a re-platted
    # building on a retired parcel or, worse, on a wrong one.
    from housing_rules.parcel_lineage import Resolver
    resolver = Resolver(con)

    event_meta = {eid: (t, d, src) for eid, t, d, src in con.execute(
        "SELECT event_id, event_type_code, event_date, source_id FROM events")}
    tables = ("units", "structure_parcels", "structure_events", "structures")
    counts = collections.Counter()
    con.isolation_level = None                         # explicit BEGIN/COMMIT, no implicit transaction
    try:
        con.execute("BEGIN")
        for t in tables:
            con.execute(f"DELETE FROM {t}")
        for root, keys in sorted(groups.items()):
            keys = sorted(keys)
            comp_date, basis = completion_for(keys, permits, finals)
            evs = permits[root]["events"]
            issued = sorted((d or "9999", eid) for eid, t, d in evs if t == "permit_issued")
            master_eid = issued[0][1] if issued else min(evs, key=lambda e: (e[2] or "9999", e[0]))[0]
            label = next((permits[k]["label"].key for k in keys if permits[k]["label"].key), None)
            units = max(permits[k]["net_units"] or 0 for k in keys)
            seen, pbasis = [], []
            for k in [root] + [x for x in keys if x != root]:
                pids, basis = resolver.resolve(permits[k]["apn"], permits[k]["address"])
                pbasis.append(basis)
                for pid in pids:
                    if pid not in seen:
                        seen.append(pid)
            notes = json.dumps({"fold": fold_id, "master_permits": keys, "parcel_basis": pbasis[0],
                                "attached_permits": len(attach.get(root, [])),
                                "completion_basis": basis,
                                "site": list(permits[root]["site"] or []),
                                "cls_source": permits[root]["cls_source"]})
            sid = con.execute(
                "INSERT INTO structures (master_event_id, building_label, structure_type, stories, "
                "status, completed_on, projection_run_id, notes) VALUES (?,?,?,?,?,?,?,?)",
                (master_eid, label, None, None,
                 "complete" if comp_date else basis, comp_date, None, notes)).lastrowid
            counts["structures"] += 1
            for k in keys + sorted(attach.get(root, [])):
                role = "master" if k in keys else "attached"
                for eid, t, _ in permits[k]["events"]:
                    con.execute("INSERT OR IGNORE INTO structure_events VALUES (?,?,?)",
                                (sid, eid, "inspection" if t == "inspection" else role))
                    counts["structure_events"] += 1
            counts["parcel_basis:" + pbasis[0]] += 1
            for i, pid in enumerate(seen):
                con.execute("INSERT INTO structure_parcels VALUES (?,?,?)", (sid, pid, int(i == 0)))
                counts["structure_parcels"] += 1
            counts["structures_without_parcel"] += int(not seen)
            if units > 0:
                con.execute("INSERT INTO units (structure_id, unit_count, tenure, affordability_tier, "
                            "dr_ndr, source_id) VALUES (?,?,?,?,?,?)",
                            (sid, units, "unknown", "unknown", None, event_meta[master_eid][2]))
                counts["unit_rows"] += 1
                counts["units"] += units
        # verify before commit
        got = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        assert got["structures"] == len(groups), got
        assert got["units"] == counts["unit_rows"], got
        assert con.execute("SELECT COALESCE(SUM(unit_count),0) FROM units").fetchone()[0] == counts["units"]
        orphan = con.execute("SELECT COUNT(*) FROM structure_events se LEFT JOIN events e "
                             "USING(event_id) WHERE e.event_id IS NULL").fetchone()[0]
        assert orphan == 0, f"{orphan} structure_events point at no event"
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    counts["structure_events_distinct"] = got["structure_events"]
    counts["fold"] = fold_id
    return dict(counts)


def _root_of(groups, k):
    for root, keys in groups.items():
        if k in keys:
            return root
    return None


if __name__ == "__main__":
    raise SystemExit(main())
