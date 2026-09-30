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
  P6 COMPANIONS non-anchor in-scope records at a site (design review, modifications, pre-applications) attach
                to the anchor filed nearest them in time; they add evidence, never a project.

  .venv/bin/python scripts/v4/build_projects.py --db BUILD.db     # preview -> scratch/2026-09-29_phase3/
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from housing_rules import to_canonical_apn                         # noqa: E402
from housing_rules.address import normalize_address                # noqa: E402
from housing_rules.planning_record import milestones               # noqa: E402
from capdetail_select import resolve_chain, cited_records, is_modification  # noqa: E402

V4 = ROOT / "databases/berkeley_housing_v4.db"
RULINGS = ROOT / "corrections/v4/planning_scope_rulings.csv"
OUT = ROOT / "scratch/2026-09-29_phase3"
ANCHOR_PRIORITY = ("primary_application", "pre_application", "ministerial_clearance", "companion_review")
DEAD = ("Withdrawn", "Void")


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
    args = ap.parse_args()
    db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)

    pid_of = dict(db.execute("SELECT apn_normalized, parcel_id FROM parcel_identifiers "
                             "WHERE apn_normalized IS NOT NULL ORDER BY is_current"))

    def parcel(a):
        try:
            return ("parcel", pid_of.get(to_canonical_apn(a, "alameda")) or to_canonical_apn(a, "alameda"))
        except Exception:
            return None

    # ---- P1: in-scope planning records
    excluded = {r["record"] for r in csv.DictReader(open(RULINGS)) if r["ruling"] == "exclude"}
    recs = {}
    for (pl,) in db.execute("SELECT raw_payload FROM events WHERE event_type_code='planning_filed'"):
        r = json.loads(pl)
        m = milestones(r)
        if r["record"] in excluded or m["role"] in ("not_an_application", "unknown"):
            continue
        r["_m"] = m
        r["_sites"] = ({parcel(a) for a in (r.get("parcels_raw") or [])} |
                       {addr_key(a) for a in (r.get("work_locations_all") or [r.get("work_location")])}) - {None}
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
        s["sites"] |= {x for x in (parcel(apn) if apn else None, addr_key(addr)) if x}
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
        live = [a for a in cands if not recs[a]["_m"]["denied"]
                and not (recs[a]["_m"]["ended_status"] or "").startswith(DEAD)]
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

    # ---- assemble projects
    projects = []
    by_anchor = collections.defaultdict(list)
    for sid, a in home.items():
        if a:
            by_anchor[a].append(sid)
    for a, members in anchors.items():
        sids = by_anchor.get(a, [])
        m = recs[a]["_m"]
        projects.append(dict(anchor=a, anchor_role=m["role"], records=sorted(r["record"] for r in members),
                             structures=sorted(sids), units=sum(units.get(x) or 0 for x in sids),
                             filed=m["filed"], entitled=m["entitled"], denied=m["denied"],
                             ended=m["ended_status"], stated_units=None))
    for sid, a in home.items():
        if a is None:
            projects.append(dict(anchor=None, anchor_role="structure_only", records=[], structures=[sid],
                                 units=units.get(sid) or 0, filed=None, entitled=None, denied=None, ended=None))

    # ---- report
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "projects_preview.jsonl", "w") as f:
        for p in projects:
            f.write(json.dumps(p) + "\n")
    print(f"planning records loaded {n_loaded}; in scope {len(recs)} "
          f"(excluded by ruling {len(excluded & set(_all_keys(db)))}, not_an_application/unknown "
          f"{n_loaded - len(recs) - len(excluded & set(_all_keys(db)))})")
    print(f"site clusters {len(clusters)}  {dict(kinds)}")
    print(f"anchors (application-projects) {len(anchors)}")
    print(f"structures {len(S)}: {dict(basis)}")
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
    print(f"\nPREVIEW written to {OUT/'projects_preview.jsonl'}; nothing written to any DB.")
    return 0


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
