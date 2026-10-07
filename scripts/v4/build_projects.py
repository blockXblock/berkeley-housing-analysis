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
import re
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
EXTERNAL_PROJECTS = ROOT / "corrections/v4/external_projects.csv"
HISTORIC_PROJECTS = ROOT / "corrections/v4/historic_projects.csv"
AFFORDABILITY = ROOT / "corrections/v4/affordability_rulings.csv"
CLASSIFICATIONS = ROOT / "corrections/v4/classification_rulings.csv"
FUNDING = ROOT / "corrections/v4/funding_ledger.csv"
# Names (John, 2026-09-30): every project is named by its ADDRESS as the City wrote it; a proper name only where the
# City's own text states one, accepted at read time only if VERBATIM in the cited record (scripts/llm_project_names.py).
# Keyed by the project's stable key (anchor record, else first master permit). A re-reading is a new dated file.
NAMES_EVIDENCE = ROOT / "data/derived/project_names_evidence_2026-09-30.json"
# State-law pathways (cutover phase 4): read from each project's own Planning text, kept only with a VERBATIM quote
# (scripts/llm_project_pathways.py). Same stable key as the names.
PATHWAYS_EVIDENCE = ROOT / "data/derived/project_pathways_evidence_2026-09-30.json"
# Proposed units of APPLICATION-ONLY projects (phase 6 D4): read from the City's text, verbatim quote containing the number.
UNITS_EVIDENCE = ROOT / "data/derived/project_units_evidence_2026-10-03.json"   # HCD definitions (John, 2026-10-03)
# a project the 10-03 read left UNANSWERED (no answer is not a judgment) keeps the 10-01 reading
UNITS_EVIDENCE_PRIOR = ROOT / "data/derived/project_units_evidence_2026-10-01.json"   # incl. by_definition (John 2026-10-01)
# Building measures (phase 6; John: square footage and parking KEPT, heights from sources -- D7): gross sq ft, parking,
# stories, height in feet, each kept only with a verbatim quote containing the number (scripts/llm_building_measures.py).
MEASURES_EVIDENCE = ROOT / "data/derived/building_measures_evidence_2026-09-30.json"
# MEASURE RULINGS (John, 2026-10-03): a measure or an application's unit count stated in an approved plan set or the
# UC's own documents, each with a verbatim quote, overriding the model's read of the application text (2128 Oxford:
# the approved hearing set says 456 units / 27 storeys / 285'-4", the 2022 application said 485 / 26).
MEASURE_RULINGS = ROOT / "corrections/v4/measure_rulings.csv"
# WHAT THE ZONING ADJUSTMENTS BOARD HEARD (John, 2026-10-07): units, stories, height and State Density Bonus read from
# the Board's Action Minutes items (scripts/llm_zab_items.py), each kept only with a verbatim quote stating it. A LAST
# fallback: used only where v4's own readings give nothing; approved measure rulings still override.
ZAB_ITEM_OK: dict = {}
ZAB_ITEMS_EVIDENCE = (ROOT / "data/derived/zab_items_evidence_2026-10-07.json",    # the reading
                      ROOT / "data/derived/zab_items_evidence_2026-10-07b.json")   # its re-ask of the max_tokens misses
# ATTRIBUTIONS (John, 2026-10-03): who developed / designed / applied for a project, from a cited source (tabulation
# form, title block, SFYIMBY article, the developer's own site, a tour caption) -- v2's sourced credits plus re-sourced
# Panoramic credits and the historic buildings' architects. Names as the source writes them.
ATTRIBUTIONS = ROOT / "corrections/v4/attribution_ledger.csv"
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
                    roots = [min(cand, key=lambda r: (r["_m"]["filed"] or "9999", r["record"]))]   # record breaks ties
                    kinds["cluster:no_primary->" + role] += 1
                    break
        for r in roots:
            anchors[r["record"]] = [r]
        # P6: every other member attaches to the root filed nearest it
        for r in members:
            if r["record"] in anchors:
                continue
            f = r["_m"]["filed"] or ""
            best = min(roots, key=lambda a: (abs(_days(a["_m"]["filed"], f)), a["record"]))
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
            # DETERMINISTIC: the record number breaks a same-day tie. Without it the choice followed Python's set
            # order, which varies between runs -- project 659 got UP2007-0021 in one build, UP2007-0022 in the next.
            before.sort(key=lambda a: (recs[a]["_m"]["filed"], a))
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
    entitled_by_doc = {}       # record -> (date, by, ruling): a ministerial approval the record's own tasks never show
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
            # COMPANIONS (John 2026-09-30, G004-G006): the same site's withdrawn/void application for THIS development
            # joins the ruled project instead of standing as a separate empty project.
            for c in [x.strip() for x in (r.get("companion_records") or "").split(";") if x.strip()]:
                cr = recs.get(c) or held_by_type.get(c)
                assert cr, f"project ruling {r['ruling_id']}: companion {c} is not loaded"
                if c in anchors and c != rec:
                    anchors[rec].extend(x for x in anchors.pop(c) if x["record"] != rec)
                    for sid_, h in list(home.items()):
                        if h == c:
                            home[sid_] = rec
                else:
                    for a, members in anchors.items():
                        members[:] = [x for x in members if x["record"] != c]
                    anchors[rec].append(cr)
                applied["companion_absorbed"] += 1
        elif r["action"] == "entitled_by_document":
            # MINISTERIAL APPROVALS (John, 2026-10-03; G022 = North Berkeley BART, AB 2011, 2024-12-11): SB 35 / AB 2011
            # approvals are filed as pre-application-type records with no decision workflow, so milestones() cannot see
            # them. The ruling states the date and the deciding body, quoted from a City document.
            rec = r["record"].strip()
            assert rec in recs or rec in held_by_type, f"project ruling {r['ruling_id']}: record {rec} is not loaded"
            assert r.get("entitled"), f"project ruling {r['ruling_id']}: entitled_by_document needs an entitled date"
            entitled_by_doc[rec] = (r["entitled"].strip(), (r.get("entitled_by") or "").strip() or None, r["ruling_id"])
        elif r["action"] == "group_structures":
            homes = {home[s] for s in sids if home[s]}
            assert len(homes) <= 1, f"project ruling {r['ruling_id']}: buildings already in different projects {homes}"
            for sid in sids:
                home[sid] = next(iter(homes)) if homes else None
                if not homes:
                    groups_of[sid] = r["ruling_id"]
        applied[r["action"]] += 1

    # ---- MINISTERIAL APPROVAL LETTERS (John, 2026-10-03): a Letter of Compliance attached to any of a project's
    # Planning records, recognized by the City's own file-naming convention (housing_rules.approval_letter). Used only
    # where the record's own tasks show no entitlement and no ruling states one; where a ruling also exists the two must
    # agree, and any disagreement is printed (the ruling stands).
    from housing_rules.approval_letter import approval_from_filename
    letters = collections.defaultdict(list)
    for rec_, f_ in db.execute("SELECT source_record_key, json_extract(raw_payload, '$.file') FROM events "
                               "WHERE event_type_code = 'attachment_listed'"):
        got = approval_from_filename(f_ or "")
        if got and got[2] == "approval":
            letters[rec_].append((got[0], got[1], f_))
    letter_mismatch = []
    # ---- THE DECIDING BODY, from the Board's own minutes (John approved 2026-10-07): the City's workflow logs many
    # Zoning Adjustments Board decisions as a "Staff Decision". Where the Board's Action Minutes record APPROVED on one of
    # the project's records ON its entitlement date, the body is the ZAB, cited to those minutes. Record AND date must both
    # match, so a mistyped number in the minutes cannot move a decision (2532 Durant: the minutes cite ZP2015-0099, a
    # different project). Heard on another date, or no minutes for the date: the body stays as the City recorded it.
    # THE ITEM MUST BE ABOUT THIS RECORD'S SITE (2026-10-07): the minutes can mistype a record number -- 2532 Durant's
    # item cites ZP2015-0099, which is 2311 Roosevelt. An item counts for a record only if its heading names that
    # record's own Accela address (house number and street), so a typo can move neither a decision nor a unit count.
    from housing_rules.address import normalize_address as _na
    rec_addr = {}
    for rec_, ra in db.execute("SELECT source_record_key, raw_address FROM events WHERE event_type_code = 'planning_filed' "
                               "AND raw_address IS NOT NULL"):
        try:
            h_, st_ = _na(ra)
        except Exception:
            continue
        if h_ and st_:
            rec_addr.setdefault(rec_, (h_, st_))

    from housing_rules.address import _ORD as _ord_words

    def item_is_about(rec_, heading, item_text="", cited=None):
        """the item names the record's site: its heading -- or, where the parser took a section title ("Consent
        Calendar") as the heading, the opening of its text -- contains a distinctive word of the record's street
        ("king" for M L KING JR, "9th" for NINTH, ordinals folded) and a house number within 10 of the record's (ranges
        "2495-2497 Valley", second frontages, "23 Tanglewood" for 25); a record numbered 0 needs the street only."""
        a_ = rec_addr.get(rec_)
        if not a_:
            return False
        it = item_text or ""
        at = it.find(cited) if cited else -1                     # a consent calendar lists several projects: read the
        win = it[max(0, at - 300): at + 300] if at >= 0 else it[:400]   # words around the record's own citation
        text = f"{heading or ''} {win}".lower()
        text = re.sub(r"\b(" + "|".join(_ord_words) + r")\b", lambda m: _ord_words[m.group(1)], text)
        words = set(re.findall(r"[a-z0-9]+", text))
        street = [w for w in re.findall(r"[a-z0-9]+", a_[1].lower()) if len(w) >= 3 and w not in ("jr", "the")]
        if not street or not any(w in words for w in street):
            return False
        n0 = re.match(r"\d+", str(a_[0]))
        if not n0 or int(n0.group()) == 0:
            return True
        return any(abs(int(x) - int(n0.group())) <= 10 for x in re.findall(r"\b\d{1,5}\b", text))

    zab = collections.defaultdict(list)          # record -> [(date, action, minutes file, item)]
    zab_off_site = collections.Counter()
    zab_item_ok = ZAB_ITEM_OK                    # (date, item) -> records the item is verifiably about (module-level:
    zab_item_ok.clear()                          # the write step reads it too)
    for rec_, d_, pl in db.execute("SELECT source_record_key, event_date, raw_payload FROM events "
                                   "WHERE event_type_code = 'zab_action'"):
        j = json.loads(pl)
        if not item_is_about(rec_, j.get("heading"), j.get("item_text"), j.get("record_cited")):
            zab_off_site[rec_] += 1
            continue
        zab[rec_].append((d_, j.get("action"), j.get("minutes_file"), j.get("item")))
        zab_item_ok.setdefault((d_, str(j.get("item"))), set()).add(rec_)
    print(f"ZAB items not about their cited record's site (left out): {sum(zab_off_site.values())} "
          f"on {len(zab_off_site)} records, e.g. {sorted(zab_off_site)[:6]}")
    decided = collections.Counter()

    def decided_by(records, entitled, recorded):
        if not entitled or (recorded or "").startswith("staff (ministerial"):
            return recorded, None, []
        acts = [(r_, x) for r_ in records for x in zab.get(r_, [])]
        same = [(r_, x) for r_, x in acts if x[0] == entitled and x[1] == "APPROVED"]
        if same:
            r_, x = same[0]
            decided["zab_by_minutes" if recorded != "zab" else "zab_confirmed"] += 1
            return "zab", f"ZAB Action Minutes {x[0]}, item {x[3]} ({r_}): {x[2]}", []
        if acts:
            decided["heard_other_date"] += 1
            return recorded, None, ["zab_heard_other_date:" + ",".join(sorted({x[0] for _, x in acts}))]
        decided["as_recorded"] += 1
        return recorded, None, []

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
        ltr = min((x for r_ in members for x in letters.get(r_["record"], [])), default=None)
        if ltr and a in entitled_by_doc and entitled_by_doc[a][0] != ltr[0]:
            letter_mismatch.append((a, entitled_by_doc[a][0], ltr[0], ltr[2]))
        use_letter = ltr if (ltr and not m["entitled"] and a not in entitled_by_doc) else None
        ent_ = m["entitled"] or (entitled_by_doc.get(a) or (None,))[0] or (use_letter or (None,))[0]
        rec_by_ = (m["entitled_by"] or (entitled_by_doc.get(a) or (None, None))[1]
                   or (f"staff (ministerial, {use_letter[1] or 'approval'} letter)" if use_letter else None))
        body_, body_src_, body_flags_ = decided_by([r["record"] for r in members], ent_, rec_by_)
        projects.append(dict(decided_by=body_, decided_by_source=body_src_,anchor=a, anchor_role=m["role"], records=sorted(r["record"] for r in members),
                             structures=sorted(sids), units=sum(units.get(x) or 0 for x in sids),
                             filed=m["filed"], accepted=m["accepted"],
                             entitled=m["entitled"] or (entitled_by_doc.get(a) or (None,))[0] or (use_letter or (None,))[0],
                             entitled_by=m["entitled_by"] or (entitled_by_doc.get(a) or (None, None))[1]
                             or (f"staff (ministerial, {use_letter[1] or 'approval'} letter)" if use_letter else None),
                             denied=m["denied"], ended=m["ended_status"],
                             record_status=recs[a].get("record_status"),
                             milestone_flags=m["flags"] + ([f"entitled_by_document:{entitled_by_doc[a][2]}"]
                                                           if a in entitled_by_doc and not m["entitled"] else [])
                                             + ([f"entitled_by_letter:{use_letter[2]}"] if use_letter else [])
                                             + body_flags_,
                             parcels=sorted(x[1] for x in recs[a]["_sites"] if x[0] == "parcel" and isinstance(x[1], int))))
    print(f"deciding body from the ZAB minutes: {dict(decided)}")
    print(f"approval letters: {sum(len(v) for v in letters.values())} on {len(letters)} records; ruling/letter "
          f"disagreements: {len(letter_mismatch)} {letter_mismatch[:5]}")
    grouped = collections.defaultdict(list)
    for sid, a in home.items():
        if a is None:
            grouped[groups_of.get(sid, f"s{sid}")].append(sid)
    for g, sids in grouped.items():
        projects.append(dict(anchor=None, anchor_role="structure_only", records=[], structures=sorted(sids),
                             units=sum(units.get(x) or 0 for x in sids), filed=None, entitled=None, denied=None,
                             ended=None, ruling=g if not g.startswith("s") else None))
    # PROJECTS OUTSIDE CITY PERMITTING (corrections/v4/external_projects.csv, John 2026-09-30): no City record, no
    # building permit -- the four UC buildings. Projects with NO buildings, beds/units and status from the UC source.
    for x in csv.DictReader(open(EXTERNAL_PROJECTS)):
        par = [pid_ for (pid_,) in db.execute("SELECT parcel_id FROM parcel_identifiers WHERE apn_normalized=? "
                                              "AND is_current=1", (x["apn"],))] if x["apn"] else []
        projects.append(dict(anchor=None, anchor_role="outside_city_permitting", records=[], structures=[], units=0,
                             filed=None, entitled=None, denied=None, ended=None, parcels=par,
                             external_id=x["external_id"], ruling_ref=x["ruling_ref"], external_name=x["name"],
                             external_address=x["address"],
                             beds=int(x["beds"]) if x["beds"] else None, external_units=int(x["units"]) if x["units"] else None,
                             permitting_authority=x["permitting_authority"], status=x["status"],
                             status_date=x["status_date"] or None, source=x["source_url"], verification=x["verification"]))

    # PRE-COVERAGE HISTORIC PROJECTS (corrections/v4/historic_projects.csv, John 2026-10-01 -- the v2 -> v4 audit):
    # City-permitted buildings that predate v4's permit sources (the CPRA feed from 2018, Planning from 2006), each
    # carried WITH its cited source and confidence. No City record, no building; parcels by the address's County situs.
    from housing_rules.address import normalize_address
    situs = collections.defaultdict(list)
    for pid_, norm in db.execute("SELECT pa.parcel_id, a.normalized FROM parcel_addresses pa JOIN addresses a USING(address_id)"):
        situs[norm].append(pid_)
    for x in csv.DictReader(open(HISTORIC_PROJECTS)):
        try:
            num, street = normalize_address(x["address"])
            par = sorted(set(situs.get(f"{num}|{street}", [])))
        except Exception:
            par = []
        projects.append(dict(anchor=None, anchor_role="pre_coverage_historic", records=[], structures=[], units=0,
                             filed=None, entitled=None, denied=None, ended=None, parcels=par,
                             external_id=x["historic_id"], external_name=x["name"], external_address=x["address"],
                             external_units=int(x["units"]) if x["units"] else None, status=x["status"],
                             completed_year=x["completed_year"], use=x["use"], source=x["source"],
                             confidence=x["confidence"], verification=x["verification"]))

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


def attach_ledgers(con, projects, master_of_s, sp, addr_of):
    """Phase 5 (John, 2026-09-30): affordability, classification and funding ledger rows -> projects.

    Lanes, strongest first: L1 a City record/permit key the project holds; L2 the row's current APN among the project's
    parcels; L3 the row's address (address canon) against the project's addresses. A row reaching several projects
    takes the one(s) WITH BUILDINGS when exactly one has them (funding implies construction); otherwise it stays
    UNATTACHED with the reason -- never a guess. Only approved affordability / classification rows apply."""
    import re as _re
    from housing_rules import to_canonical_apn
    from housing_rules.address import normalize_address

    def ak(a):
        try:
            n, st = normalize_address(a)
            return f"{n}|{st}" if n and st and n != "0" else None
        except Exception:
            return None

    cur_apn = collections.defaultdict(set)
    for pid_, apn in con.execute("SELECT parcel_id, apn_normalized FROM parcel_identifiers WHERE is_current=1"):
        cur_apn[pid_].add(apn)
    saddr = collections.defaultdict(set)
    for sid, a in con.execute("SELECT structure_id, a.normalized FROM structure_addresses JOIN addresses a USING(address_id)"):
        saddr[sid].add(a)
    by_key, by_apn, by_addr = (collections.defaultdict(set) for _ in range(3))
    for i, p in enumerate(projects):
        for k in (p.get("records") or []) + [m for s in p["structures"] for m in master_of_s[s]]:
            by_key[k].add(i)
        pars = set(p.get("parcels") or []).union(*[sp[s] for s in p["structures"]]) if p["structures"] else set(p.get("parcels") or [])
        for x in pars:
            for a in cur_apn[x]:
                by_apn[a].add(i)
        for a in [ak(addr_of.get(p["anchor"])) if p.get("anchor") else None, ak(p.get("external_address"))] + \
                 [x for s in p["structures"] for x in saddr[s]]:
            if a:
                by_addr[a].add(i)

    def find(row, keys, apns, addrs):
        ks = [k for k in _re.split(r"[,;\s]+", keys or "") if k]
        hit = set().union(*[by_key.get(k, set()) for k in ks]) if ks else set()
        lane = "record_key"
        if not hit:
            canon = []
            for a in (apns or "").split(";"):
                try:
                    canon.append(to_canonical_apn(a.strip(), "alameda"))
                except Exception:
                    pass
            hit, lane = (set().union(*[by_apn.get(a, set()) for a in canon]) if canon else set()), "apn"
        if not hit:
            for a in addrs:
                if ak(a) and by_addr.get(ak(a)):
                    hit, lane = by_addr[ak(a)], "address"
                    break
        if len(hit) > 1:
            built = {i for i in hit if projects[i]["structures"]}
            if len(built) == 1:
                hit, lane = built, lane + "+has_buildings"
        return hit, lane

    attached = collections.defaultdict(lambda: collections.defaultdict(list))
    unattached = collections.defaultdict(list)
    for kind, path, ok, keyf, fields in (
            ("affordability", AFFORDABILITY, lambda r: r["status"] == "approved", "city_record_keys",
             ("ruling_id", "income_tier", "units", "restriction", "source_url")),
            ("classifications", CLASSIFICATIONS, lambda r: r["status"] == "approved", "city_record_keys",
             ("ruling_id", "classification", "value", "rhna_effect")),
            ("funding", FUNDING, lambda r: True, "city_record_keys",   # keys added by berkeley-data-25 (F006, F026)
             ("funding_id", "funder", "program", "instrument", "amount_usd", "action", "action_date", "status"))):
        for r in csv.DictReader(open(path)):
            if not ok(r):
                continue
            hit, lane = find(r, r.get(keyf) if keyf else None, r.get("apn"), (r.get("address"), r.get("subject")))
            ref = [i for i, p in enumerate(projects) if p.get("ruling_ref") and p.get("ruling_ref") == r.get("ruling_id")]
            if ref:                              # L0: a project outside City permitting NAMES its ruling (R003 Anna Head)
                hit, lane = set(ref), "ruling_ref"
            entry = {f: r.get(f) for f in fields if r.get(f) not in (None, "")}
            entry["join"] = lane
            if len(hit) == 1:
                attached[next(iter(hit))][kind].append(entry)
            else:
                unattached[kind].append({**entry, "subject": r.get("subject"),
                                         "why": "no project reaches it" if not hit else f"reaches {len(hit)} projects"})
    return {i: dict(v) for i, v in attached.items()}, dict(unattached)


def write(con, projects) -> dict:
    """Clear and refill projects / project_structures / project_parcels in ONE transaction; verify, else roll back."""
    con.isolation_level = None
    out = collections.Counter()
    try:
        con.execute("BEGIN")
        # project_records (phase 6 D6, John 2026-09-30): a project's Planning records, indexed -- the Explorer timeline
        # and every publisher need them, and JSON in notes does not index. Created by the build, like the projection.
        con.execute("CREATE TABLE IF NOT EXISTS project_records (project_id INTEGER NOT NULL REFERENCES projects(project_id), "
                    "record_key TEXT NOT NULL, role TEXT NOT NULL, PRIMARY KEY (project_id, record_key))")
        con.execute("CREATE INDEX IF NOT EXISTS idx_project_records_key ON project_records(record_key)")
        for t in ("project_records", "project_parcels", "project_structures", "projects"):
            con.execute(f"DELETE FROM {t}")
        measures = {}
        if MEASURES_EVIDENCE.exists():
            measures = {r["project_key"]: {k: v for k, v in r.items() if k != "project_key"}
                        for r in json.load(open(MEASURES_EVIDENCE))["readings"] if len(r) > 1}
        proposed = {}
        if UNITS_EVIDENCE.exists():
            _ev = json.load(open(UNITS_EVIDENCE))
            proposed = {r["project_key"]: r for r in _ev["readings"] if r.get("units") is not None}
            if UNITS_EVIDENCE_PRIOR.exists():
                _unans = set(_ev.get("unanswered") or [])
                for r in json.load(open(UNITS_EVIDENCE_PRIOR))["readings"]:
                    if r["project_key"] in _unans and r.get("units") is not None:
                        proposed[r["project_key"]] = r
        attributions = collections.defaultdict(list)
        if ATTRIBUTIONS.exists():
            for a_ in csv.DictReader(open(ATTRIBUTIONS)):
                if a_["status"] == "approved":
                    attributions[a_["project_key"]].append({k: a_[k] for k in ("attribution_id", "role", "name",
                                                            "source_kind", "source_ref", "source_quote", "confidence")})
        measure_rulings = collections.defaultdict(list)
        if MEASURE_RULINGS.exists():
            for mr in csv.DictReader(open(MEASURE_RULINGS)):
                if mr["status"] == "approved":
                    measure_rulings[mr["project_key"]].append(mr)
        sp = collections.defaultdict(set)
        for sid, pid in con.execute("SELECT structure_id, parcel_id FROM structure_parcels"):
            sp[sid].add(pid)
        # pathway quotes are attached by the RECORD each was quoted from (its "source"), not by the project key the
        # reading was filed under: when a ruling moves a record to another project (G033, 1740 San Pablo), its quotes go
        # with it. A quote with no source stays with the key it was read under.
        pathways = collections.defaultdict(list)
        if PATHWAYS_EVIDENCE.exists():
            for r in json.load(open(PATHWAYS_EVIDENCE))["readings"]:
                for x in r.get("pathways") or []:
                    pathways[x.get("source") or r["project_key"]].append(x)
        zab_items = {}
        for f_ in ZAB_ITEMS_EVIDENCE:            # the re-ask only fills projects the first reading left unanswered
            if f_.exists():
                for r in json.load(open(f_))["readings"]:
                    if len(r) > 1:
                        zab_items.setdefault(r["project_key"], r)
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
        attached, unattached = attach_ledgers(con, projects, master_of_s, sp, addr_of)
        for kind, rows in unattached.items():
            out[f"{kind}_unattached"] = len(rows)
        (OUT / "ledger_unattached.json").write_text(json.dumps(unattached, indent=1))
        for i, p in enumerate(projects):
            p.update(attached.get(i, {}))
            for kind in ("affordability", "classifications", "funding"):
                out[f"{kind}_rows_attached"] += len(p.get(kind) or [])
            mps = sorted(m for s in p["structures"] for m in master_of_s[s])
            key = p.get("anchor") or (mps[0] if mps else None) or p.get("external_id")
            address = (addr_of.get(p["anchor"]) if p.get("anchor") else None) or next((addr_of[m] for m in mps if addr_of.get(m)), None)
            basis = "address" if address else None
            if not address:                     # last fallback: the County's situs for the project's parcel
                pars = sorted(set(p.get("parcels") or []).union(*[sp[s] for s in p["structures"]]) if p["structures"]
                              else set(p.get("parcels") or []))
                address = next((situs[x] for x in pars if situs.get(x)), None)
                basis = "parcel_situs" if address else None
            p["project_key"], p["address"] = key, address
            p["name"] = names.get(key) or address
            # pathways are read per ANCHOR record; a project that absorbed another anchor (a ruling's companion) carries
            # both readings, each still with its own quote and source
            ev = [x for k in dict.fromkeys([key] + list(p.get("records") or [])) for x in pathways.get(k, [])]
            ev = [dict(t) for t in dict.fromkeys(tuple(sorted(x.items())) for x in ev)]   # one quote, once
            zi = dict(zab_items.get(key) or {})
            for f_ in [f for f in list(zi) if isinstance(zi[f], dict) and str(zi[f].get("source", "")).startswith("ZAB ")]:
                m_ = re.match(r"ZAB (\S+) item (\S+)", zi[f_]["source"])
                if not (m_ and ZAB_ITEM_OK.get((m_[1], m_[2]), set()) & set([key] + list(p.get("records") or []))):
                    zi.pop(f_)                        # the item is not verifiably about this project's site
                    out["zab_value_off_site"] += 1
            if zi.get("density_bonus") and not any(x["pathway"] == "density_bonus" for x in ev):
                ev.append({"pathway": "density_bonus", "quote": zi["density_bonus"]["quote"],
                           "source": zi["density_bonus"]["source"], "read_from": "zab_minutes"})
                out["pathway_density_bonus_from_zab"] += 1
            if ev:
                p["pathways"] = sorted({x["pathway"] for x in ev})
                p["pathway_evidence"] = ev
                out["with_pathway"] += 1
            p["name_basis"] = "city_stated_name" if names.get(key) else basis
            if measures.get(key):
                ms, bad = dict(measures[key]), {}
                # SELF-CONTRADICTION (John, 2026-10-01: flag and EXCLUDE): the City's own text can contradict itself --
                # ZP2016-0244 "a 40story, 60 feet tall" building; ZP2023-0040 "a 28-story, 28,319 sq ft" building. The
                # verbatim check cannot catch a typo the City wrote, so a pair that cannot both be true leaves the
                # published measures (kept in notes with the reason, never silently).
                st = (ms.get("stories") or {}).get("value")
                h = (ms.get("height_feet") or {}).get("value")
                sf = (ms.get("gross_sqft") or {}).get("value")
                if st and h and not (8 <= h / st <= 20):
                    bad["stories"] = bad["height_feet"] = f"height/stories = {h}/{st} ft per story, outside 8-20"
                # Area: only a TALL building with a tiny floor plate is impossible. Small houses and ADUs legitimately run
                # 230-500 sq ft per floor ("1,450 square-foot, 3-story single-family dwelling"); a first draft at 1,500
                # for every building flagged 91 projects, almost all real. Measured: this flags one (ZP2023-0040).
                if st and sf and st >= 5 and sf / st < 2000:
                    bad["stories"] = bad["gross_sqft"] = f"floor area/stories = {sf}/{st} sq ft on a {st}-story building, under 2,000"
                for m_ in bad:
                    ms.pop(m_, None)
                if bad:
                    p["measures_excluded"] = {m_: {**measures[key][m_], "why": w} for m_, w in bad.items()}
                    out["measures_flagged_projects"] += 1
                if ms:
                    p["measures"] = ms
                    out["with_measures"] += 1
            zst, zh = (zi.get("stories") or {}).get("value"), (zi.get("height_feet") or {}).get("value")
            zok = not (zst and zh and not (8 <= zh / zst <= 20))     # the same self-contradiction screen as above
            for m_ in ("stories", "height_feet"):
                if zok and zi.get(m_) and m_ not in (p.get("measures") or {}) and m_ not in (p.get("measures_excluded") or {}):
                    p.setdefault("measures", {})[m_] = {**zi[m_], "read_from": "zab_minutes"}
                    out[f"{m_}_from_zab"] += 1
            if not p["structures"] and proposed.get(key):          # D4: an application's own stated count
                p["proposed_units"] = proposed[key]["units"]
                p["proposed_units_evidence"] = {k: proposed[key][k] for k in ("quote", "source")}
                out["with_proposed_units"] += 1
            elif not p["structures"] and zi.get("units"):          # else what the Board heard (2026-10-07)
                p["proposed_units"] = zi["units"]["value"]
                p["proposed_units_evidence"] = {"quote": zi["units"]["quote"], "source": zi["units"]["source"],
                                                "read_from": "zab_minutes"}
                out["proposed_units_from_zab"] += 1
            for mr in measure_rulings.get(key, []):                  # approved measure rulings override the read
                val = float(mr["value"]); val = int(val) if val.is_integer() else val
                ev = {"value": val, "quote": mr["source_quote"], "source": mr["source_ref"], "ruling": mr["ruling_id"]}
                if mr["measure"] == "units":
                    if not p["structures"]:                          # built units always come from the buildings
                        p["proposed_units"], p["proposed_units_evidence"] = val, ev
                        out["measure_rulings_applied"] += 1
                else:
                    p.setdefault("measures", {})[mr["measure"]] = ev
                    (p.get("measures_excluded") or {}).pop(mr["measure"], None)
                    out["measure_rulings_applied"] += 1
            if attributions.get(key):
                p["attributions"] = attributions[key]
                out["attributed_projects"] += 1
            if p.get("external_id"):
                p["name"], p["address"], p["name_basis"] = p["external_name"], p["external_address"], "external_source"
            out["named_" + str(p["name_basis"])] += 1
            notes = {k: p.get(k) for k in ("anchor", "anchor_role", "records", "filed", "accepted", "entitled",
                                           "entitled_by", "decided_by", "decided_by_source", "denied", "ended",
                                           "record_status", "milestone_flags",
                                           "ruling", "project_key", "address", "name_basis", "pathways", "pathway_evidence",
                                           "external_id", "beds", "external_units", "permitting_authority", "status",
                                           "status_date", "source", "verification", "completed_year", "use", "confidence",
                                           "affordability", "classifications", "funding", "proposed_units", "proposed_units_evidence",
                                           "measures", "measures_excluded", "attributions")
                     if p.get(k) not in (None, [], "")}
            notes["units"] = p["units"]
            pid = con.execute("INSERT INTO projects (name, notes) VALUES (?, ?)",
                              (p["name"], json.dumps(notes))).lastrowid
            out["projects"] += 1
            for rec in (p.get("records") or []):
                con.execute("INSERT OR IGNORE INTO project_records VALUES (?,?,?)",
                            (pid, rec, "anchor" if rec == p.get("anchor") else "member"))
                out["project_records"] += 1
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
