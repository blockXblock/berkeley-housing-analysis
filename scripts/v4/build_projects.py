#!/usr/bin/env python3
r"""build_projects.py -- THE PROJECTS STAGE (cutover phase 3). READ-ONLY PREVIEW; no write step yet.

A PROJECT is what the published outputs count and link: a housing development proposal at a site, from its
application to its buildings. v4 has the two halves as separate identities -- Planning records (the city's
applications) and STRUCTURES (build_structures.py, one per master building permit). This stage joins them.

THE RULES (APPROVED by John 2026-09-30, P1-P6 as written; withdrawn/void/denied applications STAY as projects,
marked with their outcome; gaps close through corrections/v4/project_rulings.csv, never a looser site rule):
  P1 SCOPE      a Planning record is in scope unless corrections/v4/planning_scope_rulings.csv EXCLUDES it
                (John, 2026-09-29), and unless its role is 'not_an_application' (a zoning research letter is
                an inquiry). Everything loaded was either admitted by the old filter or INCLUDED by a ruling.
  P2 ANCHOR     a project is anchored by ONE record: the ROOT of a primary application's modification chain
                (capdetail_select.resolve_chain -- a record that says it modifies another joins it). Where a
                site has no primary application, a pre-application, then a ministerial clearance, then a
                companion review is the anchor (some carry the development text, e.g. DRCF2021-0006, 163u).
                Several unrelated primaries at one site are SEPARATE projects (the "conflated" case is a
                finding, never a merge).
  P3 SITE       records and structures meet on PARCEL identity (any APN the parcel has carried, current or
                former, via parcel_identifiers) or on the canonical address (housing_rules.address). APNs are
                not identity (CLAUDE.md rule 4), so either lane is enough and a disagreement is reported.
  P4 BUILDINGS  a structure joins the anchor at its site that was FILED MOST RECENTLY ON OR BEFORE the
                structure's master permit was submitted (the application that preceded the building permit).
                A denied or withdrawn anchor never takes a building. No such anchor -> the structure is its
                OWN project (ministerial / ADU tail, or its approval predates the Jan-2015 harvest).
  P5 ONE HOME   every structure is in exactly one project; a project may have many (Acheson: 4 buildings).
                A project with no structure is an application not (yet) built: pending, entitled, denied or
                withdrawn -- the pipeline, not an error.
  P1b PRE-2015  (John, 2026-09-30) an application FILED BEFORE 2015 becomes a project only if it reaches a building.
                Our building-permit stream starts around 2014, so an older application with no building here was most
                likely built before our data, not "entitled and unbuilt"; it stays as evidence, not a project.
  P4b DEAD      (2026-09-30) an application is dead for P4 if its milestones show a denial or a Withdrawn/Void end,
                OR its RECORD STATUS reads Denied / Withdrawn / Void / Expired. Pre-2015 records carry a denial only in
                the status (UP2012-0039, 70 units at 2701 Shattuck, denied 2012, was otherwise reaching the later
                57-unit building).
  P6 COMPANIONS non-anchor in-scope records at a site (design review, modifications, pre-applications) attach
                to the anchor filed nearest them in time; they add evidence, never a project.

  .venv/bin/python scripts/v4/build_projects.py --db BUILD.db           # preview -> scratch/2026-09-29_phase3/
  .venv/bin/python scripts/v4/build_projects.py --db BUILD.db --write   # the BUILD STEP (after build_structures)

THE WRITE (2026-09-30). Clears and refills `projects`, `project_structures`, `project_parcels` in ONE transaction:
projects are a projection of the planning records + structures + John's rulings, re-derived every build, never
edited. v4 has no project->record table, so each project's records, anchor and milestones live in `notes` (JSON)
until John decides on one. Refuses the live DB unless BUILD_PROJECTS_ALLOW_LIVE=1.
"""
from __future__ import annotations

import argparse
import os
import collections
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from housing_rules.address import normalize_address                # noqa: E402
from housing_rules.planning_record import milestones               # noqa: E402
from capdetail_select import resolve_chain, cited_records, is_modification  # noqa: E402

V4 = ROOT / "databases/berkeley_housing_v4.db"
RULINGS = ROOT / "corrections/v4/planning_scope_rulings.csv"
PROJECT_RULINGS = ROOT / "corrections/v4/project_rulings.csv"
# Names (John, 2026-09-30): every project is named by its ADDRESS as the City wrote it; a proper name only where the
# City's own text states one, accepted at read time only if VERBATIM in the cited record (scripts/llm_project_names.py).
# Keyed by the project's stable key (anchor record, else first master permit). A re-reading is a new dated file.
NAMES_EVIDENCE = ROOT / "data/derived/project_names_evidence_2026-09-30.json"
OUT = ROOT / "scratch/2026-09-29_phase3"
ANCHOR_PRIORITY = ("primary_application", "pre_application", "ministerial_clearance", "companion_review")
DEAD = ("Withdrawn", "Void")
DEAD_STATUS = ("Denied", "Withdrawn", "Void", "Expired")
PRE_2015 = "2015-01-01"


def dead(rec) -> bool:
    m = rec["_m"]
    return bool(m["denied"] or (m["ended_status"] or "").startswith(DEAD)
                or str(rec.get("record_status") or "").startswith(DEAD_STATUS))


def addr_key(a):
    if not a:
        return None
    try:
        n, s = normalize_address(a)
    except Exception:
        return None
    return ("addr", n, s) if n and s and n != "0" else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(V4))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.write and Path(args.db).resolve() == V4.resolve() and os.environ.get("BUILD_PROJECTS_ALLOW_LIVE") != "1":
        raise SystemExit(f"REFUSED: --write targets the LIVE DB ({V4}); projects reach live by swapping in a verified build.")
    db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)

    # P3's parcel lane goes through the County's lineage (housing_rules.parcel_lineage, John's split rule 2026-09-30)
    from housing_rules.parcel_lineage import Resolver
    resolver = Resolver(db)

    def parcels(apn, address=None):
        return {("parcel", pid) for pid in resolver.resolve(apn, address)[0]}

    # ---- P1: in-scope planning records
    excluded = {r["record"] for r in csv.DictReader(open(RULINGS)) if r["ruling"] == "exclude"}
    recs, held_by_type = {}, {}
    for (pl,) in db.execute("SELECT raw_payload FROM events WHERE event_type_code='planning_filed'"):
        r = json.loads(pl)
        m = milestones(r)
        if r["record"] in excluded:
            continue
        r["_m"] = m
        r["_sites"] = (set().union(*[parcels(a, r.get("work_location")) for a in (r.get("parcels_raw") or [])]) |
                       {addr_key(a) for a in (r.get("work_locations_all") or [r.get("work_location")])}) - {None}
        if m["role"] in ("not_an_application", "unknown"):
            held_by_type[r["record"]] = r   # out by TYPE only: an approved project ruling may bring it back (G006)
            continue
        recs[r["record"]] = r
    n_loaded = db.execute("SELECT COUNT(*) FROM events WHERE event_type_code='planning_filed'").fetchone()[0]

    # ---- structures and their sites (parcel links + every master permit's APN and address)
    S = {}
    for sid, mev, notes, status, comp in db.execute(
            "SELECT structure_id, master_event_id, notes, status, completed_on FROM structures"):
        n = json.loads(notes)
        S[sid] = dict(masters=n["master_permits"], status=status, completed=comp, sites=set(), submitted=None)
    for sid, pid in db.execute("SELECT structure_id, parcel_id FROM structure_parcels"):
        S[sid]["sites"].add(("parcel", pid))
    units = dict(db.execute("SELECT structure_id, SUM(unit_count) FROM units GROUP BY 1"))
    master_of = {k: sid for sid, s in S.items() for k in s["masters"]}
    for key, t, d, apn, addr in db.execute(
            "SELECT source_record_key, event_type_code, event_date, raw_apn, raw_address FROM events "
            "WHERE event_type_code IN ('permit_submitted','permit_issued') AND source_record_key IN (%s)"
            % ",".join("?" * len(master_of)), list(master_of)):
        s = S[master_of[key]]
        s["sites"] |= parcels(apn, addr) | ({addr_key(addr)} - {None})
        if d and (t == "permit_submitted" or not s["submitted"]):
            if not s["submitted"] or d < s["submitted"]:
                s["submitted"] = d

    # ---- P2/P3: cluster records by shared site or citation, then pick anchors per cluster
    parent = {k: k for k in recs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_site = collections.defaultdict(list)
    for k, r in recs.items():
        for s in r["_sites"]:
            by_site[s].append(k)
        for c in cited_records(r):
            if c in recs:
                union(k, c)
    for ks in by_site.values():
        for k in ks[1:]:
            union(ks[0], k)
    clusters = collections.defaultdict(list)
    for k in recs:
        clusters[find(k)].append(recs[k])

    anchors, kinds = {}, collections.Counter()           # anchor record -> [member records]
    for members in clusters.values():
        prims = [r for r in members if r["_m"]["role"] == "primary_application"]
        roots = []
        if prims:
            nums = {r["record"] for r in prims}
            children = [r for r in prims if is_modification(r) and cited_records(r) & nums]
            roots = [r for r in prims if r not in children]
            root, kind = resolve_chain(prims)
            if root is not None:
                roots = [root]
            kinds["cluster:" + kind] += 1
        else:
            for role in ANCHOR_PRIORITY[1:]:
                cand = [r for r in members if r["_m"]["role"] == role]
                if cand:
                    roots = [min(cand, key=lambda r: r["_m"]["filed"] or "9999")]
                    kinds["cluster:no_primary->" + role] += 1
                    break
        for r in roots:
            anchors[r["record"]] = [r]
        # P6: every other member attaches to the root filed nearest it
        for r in members:
            if r["record"] in anchors:
                continue
            f = r["_m"]["filed"] or ""
            best = min(roots, key=lambda a: abs(_days(a["_m"]["filed"], f)))
            anchors[best["record"]].append(r)

    # ---- P4: structures to anchors
    anchor_sites = collections.defaultdict(set)
    for a, members in anchors.items():
        for s in recs[a]["_sites"]:
            anchor_sites[s].add(a)
    home, basis = {}, collections.Counter()
    ties, refused = [], []
    for sid, s in S.items():
        cands = set().union(*[anchor_sites[x] for x in s["sites"]]) if s["sites"] else set()
        live = [a for a in cands if not dead(recs[a])]
        before = [a for a in live if s["submitted"] and recs[a]["_m"]["filed"]
                  and recs[a]["_m"]["filed"] <= s["submitted"]]
        if before:
            before.sort(key=lambda a: recs[a]["_m"]["filed"])
            if len(before) > 1 and recs[before[-1]]["_m"]["filed"] == recs[before[-2]]["_m"]["filed"]:
                ties.append((sid, before[-2:]))
            home[sid] = before[-1]
            basis["joined_application"] += 1
        else:
            home[sid] = None
            basis["own_project:" + ("no_application_at_site" if not cands else
                                    "only_later_or_dead_applications")] += 1
            if cands and (units.get(sid) or 0) >= 5:
                refused.append((sid, sorted(cands)))

    # ---- PROJECT RULINGS (corrections/v4/project_rulings.csv): John's approved rows override P2-P4 where the rules
    # cannot see the evidence. anchor_record: the named record anchors the named buildings (promoted to its own project
    # if the rules had it as a companion). group_structures: the named buildings share one project. Every name must
    # resolve -- a missing record or permit HALTS, so a ruling never goes stale quietly.
    groups_of, applied = {}, collections.Counter()
    for r in csv.DictReader(open(PROJECT_RULINGS)):
        if r["status"] != "approved":
            continue
        sids = []
        for k in [x.strip() for x in r["master_permits"].split(";") if x.strip()]:
            assert k in master_of, f"project ruling {r['ruling_id']}: {k} is not a building's master permit"
            sids.append(master_of[k])
        if r["action"] == "anchor_record":
            rec = r["record"].strip()
            if rec not in recs and rec in held_by_type:      # filed under the wrong TYPE (2001 Ashby's SB 35 application
                recs[rec] = held_by_type[rec]                 # is typed "Zoning Research Letter"); the ruling is the authority
            assert rec in recs, (f"project ruling {r['ruling_id']}: record {rec} is not loaded, or the planning-scope "
                                 f"rulings exclude it")
            if rec not in anchors:
                for a, members in anchors.items():
                    if any(x["record"] == rec for x in members):
                        members[:] = [x for x in members if x["record"] != rec]
                anchors[rec] = [recs[rec]]
            for sid in sids:
                home[sid] = rec
        elif r["action"] == "group_structures":
            homes = {home[s] for s in sids if home[s]}
            assert len(homes) <= 1, f"project ruling {r['ruling_id']}: buildings already in different projects {homes}"
            for sid in sids:
                home[sid] = next(iter(homes)) if homes else None
                if not homes:
                    groups_of[sid] = r["ruling_id"]
        applied[r["action"]] += 1

    # ---- assemble projects
    projects = []
    by_anchor = collections.defaultdict(list)
    for sid, a in home.items():
        if a:
            by_anchor[a].append(sid)
    evidence_only = 0
    for a, members in anchors.items():
        sids = by_anchor.get(a, [])
        m = recs[a]["_m"]
        if not sids and (m["filed"] or "9999") < PRE_2015:      # P1b
            evidence_only += 1
            continue
        projects.append(dict(anchor=a, anchor_role=m["role"], records=sorted(r["record"] for r in members),
                             structures=sorted(sids), units=sum(units.get(x) or 0 for x in sids),
                             filed=m["filed"], accepted=m["accepted"], entitled=m["entitled"],
                             entitled_by=m["entitled_by"], denied=m["denied"], ended=m["ended_status"],
                             record_status=recs[a].get("record_status"), milestone_flags=m["flags"],
                             parcels=sorted(x[1] for x in recs[a]["_sites"] if x[0] == "parcel" and isinstance(x[1], int))))
    grouped = collections.defaultdict(list)
    for sid, a in home.items():
        if a is None:
            grouped[groups_of.get(sid, f"s{sid}")].append(sid)
    for g, sids in grouped.items():
        projects.append(dict(anchor=None, anchor_role="structure_only", records=[], structures=sorted(sids),
                             units=sum(units.get(x) or 0 for x in sids), filed=None, entitled=None, denied=None,
                             ended=None, ruling=g if not g.startswith("s") else None))

    # ---- report
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "projects_preview.jsonl", "w") as f:
        for p in projects:
            f.write(json.dumps(p) + "\n")
    print(f"planning records loaded {n_loaded}; in scope {len(recs)} "
          f"(excluded by ruling {len(excluded & set(_all_keys(db)))}, not_an_application/unknown "
          f"{n_loaded - len(recs) - len(excluded & set(_all_keys(db)))})")
    print(f"site clusters {len(clusters)}  {dict(kinds)}")
    print(f"anchors (application-projects) {len(anchors)}; pre-2015 anchors with no building kept as evidence "
          f"only (P1b): {evidence_only}")
    print(f"structures {len(S)}: {dict(basis)}")
    print(f"project rulings applied: {dict(applied)}")
    with_b = [p for p in projects if p["anchor"] and p["structures"]]
    print(f"PROJECTS {len(projects)}: application + buildings {len(with_b)} · "
          f"application only {sum(1 for p in projects if p['anchor'] and not p['structures'])} · "
          f"building only {sum(1 for p in projects if not p['anchor'])}")
    ao = [p for p in projects if p["anchor"] and not p["structures"]]
    st = collections.Counter("denied" if p["denied"] else (p["ended"] or "").lower() or
                             ("entitled" if p["entitled"] else "pending/other") for p in ao)
    print(f"  application-only by state: {dict(st)}")
    multi = [p for p in with_b if len(p["structures"]) > 1]
    print(f"  projects with several buildings: {len(multi)}; units in application-projects "
          f"{sum(p['units'] for p in with_b)}; in building-only {sum(p['units'] for p in projects if not p['anchor'])}")
    print(f"  tie on filing date (reported, latest kept): {len(ties)}")
    print(f"  5+ unit buildings whose site HAS applications but none precedes the permit: {len(refused)}")
    for sid, c in sorted(refused, key=lambda x: -(units.get(x[0]) or 0))[:10]:
        print(f"     {S[sid]['masters']} {units.get(sid)}u submitted {S[sid]['submitted']} | at site: "
              + ", ".join(f"{a}({recs[a]['_m']['filed']},{recs[a]['_m']['closed_status'] or recs[a]['_m']['ended_status']})"
                          for a in c[:3]))
    big = [p for p in with_b if p["units"] >= 50]
    print(f"\n  largest application-projects:")
    for p in sorted(big, key=lambda p: -p["units"])[:12]:
        print(f"     {p['anchor']:<14} {p['units']:>4}u  {len(p['structures'])} bldg  filed {p['filed']}  "
              f"entitled {p['entitled']}  records {len(p['records'])}")
    print(f"\nPREVIEW written to {OUT/'projects_preview.jsonl'}")
    if not args.write:
        print("nothing written to any DB.")
        return 0
    db.close()
    print("WRITE:", write(sqlite3.connect(args.db), projects))
    return 0


def write(con, projects) -> dict:
    """Clear and refill projects / project_structures / project_parcels in ONE transaction; verify, else roll back."""
    con.isolation_level = None
    out = collections.Counter()
    try:
        con.execute("BEGIN")
        for t in ("project_parcels", "project_structures", "projects"):
            con.execute(f"DELETE FROM {t}")
        sp = collections.defaultdict(set)
        for sid, pid in con.execute("SELECT structure_id, parcel_id FROM structure_parcels"):
            sp[sid].add(pid)
        names = {}
        if NAMES_EVIDENCE.exists():
            names = {r["project_key"]: r["name"] for r in json.load(open(NAMES_EVIDENCE))["readings"] if r.get("name")}
        addr_of = {}
        for k, a in con.execute("SELECT source_record_key, raw_address FROM events WHERE raw_address IS NOT NULL "
                                "AND (event_type_code='planning_filed' OR event_type_code LIKE 'permit_%')"):
            addr_of.setdefault(k, a)
        situs = {}
        for pid_, num, street in con.execute("SELECT pa.parcel_id, a.number, a.street FROM parcel_addresses pa "
                                             "JOIN addresses a USING(address_id) ORDER BY a.address_id"):
            situs.setdefault(pid_, f"{num} {street}".upper())
        master_of_s = {sid: json.loads(n)["master_permits"] for sid, n in con.execute("SELECT structure_id, notes FROM structures")}
        for p in projects:
            mps = sorted(m for s in p["structures"] for m in master_of_s[s])
            key = p.get("anchor") or (mps[0] if mps else None)
            address = (addr_of.get(p["anchor"]) if p.get("anchor") else None) or next((addr_of[m] for m in mps if addr_of.get(m)), None)
            basis = "address" if address else None
            if not address:                     # last fallback: the County's situs for the project's parcel
                pars = sorted(set(p.get("parcels") or []).union(*[sp[s] for s in p["structures"]]) if p["structures"]
                              else set(p.get("parcels") or []))
                address = next((situs[x] for x in pars if situs.get(x)), None)
                basis = "parcel_situs" if address else None
            p["project_key"], p["address"] = key, address
            p["name"] = names.get(key) or address
            p["name_basis"] = "city_stated_name" if names.get(key) else basis
            out["named_" + str(p["name_basis"])] += 1
            notes = {k: p.get(k) for k in ("anchor", "anchor_role", "records", "filed", "accepted", "entitled",
                                           "entitled_by", "denied", "ended", "record_status", "milestone_flags",
                                           "ruling", "project_key", "address", "name_basis") if p.get(k) not in (None, [], "")}
            notes["units"] = p["units"]
            pid = con.execute("INSERT INTO projects (name, notes) VALUES (?, ?)",
                              (p["name"], json.dumps(notes))).lastrowid
            out["projects"] += 1
            for sid in p["structures"]:
                con.execute("INSERT INTO project_structures VALUES (?,?)", (pid, sid))
                out["project_structures"] += 1
            parcels = set(p.get("parcels") or []).union(*[sp[s] for s in p["structures"]]) if p["structures"] \
                else set(p.get("parcels") or [])
            for par in sorted(parcels):
                con.execute("INSERT INTO project_parcels VALUES (?,?)", (pid, par))
                out["project_parcels"] += 1
        n_s = con.execute("SELECT COUNT(*) FROM structures").fetchone()[0]
        homed = con.execute("SELECT COUNT(DISTINCT structure_id) FROM project_structures").fetchone()[0]
        dup = con.execute("SELECT COUNT(*) FROM (SELECT structure_id FROM project_structures GROUP BY 1 "
                          "HAVING COUNT(*) > 1)").fetchone()[0]
        assert homed == n_s and dup == 0, f"P5 ONE HOME broken: {homed} of {n_s} structures homed, {dup} in two projects"
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return dict(out)


def _all_keys(db):
    return [k for (k,) in db.execute("SELECT source_record_key FROM events WHERE event_type_code='planning_filed'")]


def _days(a, b):
    import datetime as dt
    try:
        return (dt.date.fromisoformat(a) - dt.date.fromisoformat(b)).days
    except Exception:
        return 10 ** 6


if __name__ == "__main__":
    raise SystemExit(main())
