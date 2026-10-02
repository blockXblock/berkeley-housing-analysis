#!/usr/bin/env python3
"""v4_source.py — THE one place the tour / KML scripts read housing data from: v4, read-only.

Cutover (2026-10-02): every tour script used to open databases/berkeley_housing_v2.db and read
v_projects_flat. v2 is being archived, so they read the canonical v4 database's SERVING VIEWS
through here instead. One module, so the fourteen scripts cannot drift into fourteen readings.

THE STAGE IS THE EXPLORER'S, IMPORTED, NOT RE-TYPED. A building's stage comes from
scripts/export_explorer_data_v4.get_projects() -- the same function that writes the Explorer's
data -- so the map and the Explorer cannot disagree about a building. The KML palette is coarser
than the Explorer's eleven stages (the published legend and videos use it), so KML_BUCKET folds
each Explorer stage into one legend colour. The label TEXT keeps the Explorer's own word.

ADDRESS JOIN = housing_rules.address.normalize_address (CLAUDE.md rule 4c), after folding the two
spellings the geometry file uses that the canon does not handle: a house-number range
("1701- 1717 San Pablo") and MLK. v4 often holds SEVERAL projects at one address (a withdrawn
application and its successor; ADU permits beside a development), so by_address() applies two
declared tie-breaks and REPORTS every address it still cannot resolve -- it never picks one.

Read-only: sqlite3 "file:...?mode=ro". Writes nothing.
"""
from __future__ import annotations

import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V4 = ROOT / "databases" / "berkeley_housing_v4.db"
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
from housing_rules.address import normalize_address  # noqa: E402

# Explorer stage -> the KML legend's colour bucket (restyle_by_status.PALETTE / update_legend.GLOSS).
# The Explorer has no separate "Permitted" stage (v4 status under_construction covers BP-issued);
# "Building Permits Filed" is not yet permitted, so it shares Entitled's colour, whose legend
# phrase is "entitled (approved, no building permit yet)". The two inactive stages are the
# legend's "Stalled"; Denied and Expired are off-ramps, drawn with Withdrawn.
KML_BUCKET = {
    "Pre-Application": "Pre-Application",
    "Under Review": "In Review",
    "Entitled": "Entitled",
    "Building Permits Filed": "Entitled",
    "Entitled but Inactive": "Stalled",
    "Permitted but Inactive": "Stalled",
    "Under Construction": "Under Construction",
    "Completed": "Completed",
    "Withdrawn": "Withdrawn",
    "Denied": "Withdrawn",
    "Expired": "Withdrawn",
    "Stalled": "Stalled",
}
# the legacy v2 label words, still on placemarks until a sync rewrites them
LEGACY_LABEL = {"In Review": "In Review", "Permitted": "Permitted"}
OFF_RAMP = {"Withdrawn", "Denied", "Expired"}

_CACHE = {}


def connect():
    return sqlite3.connect(f"file:{V4}?mode=ro", uri=True)


def bucket(stage):
    """Explorer stage (or a legacy v2 label word) -> KML legend bucket, None if unknown."""
    return KML_BUCKET.get(stage) or LEGACY_LABEL.get(stage)


def projects():
    """Every v4 project as a dict, the Explorer's stage included. Cached per process (~10 s)."""
    if "rows" in _CACHE:
        return _CACHE["rows"]
    from scripts.export_explorer_data_v4 import get_projects
    db = connect()
    exp = {p["id"]: p for p in get_projects(db)}
    # every address on a project's structures, as v4 stores it ("number|street", the canon's own
    # form) -- the umbrella address the geometry was drawn under is often not address_display
    other = collections.defaultdict(set)
    for k, norm in db.execute("""SELECT DISTINCT json_extract(p.notes, '$.project_key'), a.normalized
                                 FROM projects p JOIN project_structures ps USING(project_id)
                                 JOIN structure_addresses sa USING(structure_id) JOIN addresses a USING(address_id)
                                 WHERE a.normalized LIKE '%|%'"""):
        other[k].add(norm)
    cur = db.execute("SELECT project_key, address_display, name, anchor_role, status, beds, building_sqft,"
                     " classifications, owner_current FROM v_projects")
    cols = [d[0] for d in cur.description]
    out = []
    for row in cur.fetchall():
        v = dict(zip(cols, row))
        e = exp[v["project_key"]]
        cls = {c.get("classification") for c in json.loads(v["classifications"] or "[]")}
        uc = "uc_student_housing" in cls
        bart = "bart_joint_development" in cls
        owner = e["owner"] if e["owner"] == v["owner_current"] else None   # Explorer masks individuals
        out.append({
            "project_key": v["project_key"], "name": v["name"], "address_display": v["address_display"],
            "anchor_role": v["anchor_role"], "pipeline_status": v["status"],
            "stage": e["status"], "kml_status": bucket(e["status"]),
            "units": e["units"] or 0, "beds": v["beds"], "uc": uc, "bart": bart,
            "agency": "UC Project" if uc else "BART Project" if bart else None,
            "height_stories": e["height_stories"], "height_feet": e["height_feet"],
            "building_sqft": v["building_sqft"], "architect": e["architect"], "developer": e["developer"],
            "owner": owner, "filed_date": e["app_filed"], "bp_issued_date": e["bp_issued"],
            "co_issued_date": e["co_date"], "latitude": e["latitude"], "longitude": e["longitude"],
            "apn": e["apn"], "other_addresses": sorted(other.get(v["project_key"], ())),
        })
    db.close()
    _CACHE["rows"] = out
    return out


def count_label(r):
    """'1,625 beds' for UC (CLAUDE.md: UC counted in BEDS, no ratio), else 'N units'; None if no figure."""
    if r["uc"]:
        return f"{r['beds']} beds" if r["beds"] else None
    return f"{r['units']} units" if r["units"] else None


def akey(addr):
    """Canonical 'number|street' join key (housing_rules.address) or None."""
    if not addr:
        return None
    s = str(addr).upper()
    s = re.sub(r"\b(\d+)\s*-\s*\d+\b", r"\1", s)                     # 1701-1717 -> 1701
    s = re.sub(r"\bMARTIN\s+LUTHER\s+KING(\s+JR\.?)?\b|\bM\s*L\s*KING(\s+JR\.?)?\b|\bMLK(\s+JR\.?)?\b",
               "MLK", s)
    num, street = normalize_address(s)
    return _strip_unit(f"{num}|{street}") if num and street else None


def _strip_unit(k):
    """'2000|dwight a' -> '2000|dwight': a trailing one-letter unit suffix is not the street."""
    return re.sub(r" [a-z]$", "", k)


def _resolve(groups):
    res, amb, ties = {}, {}, []
    for k, g in groups.items():
        cand = g
        live = [r for r in cand if r["stage"] not in OFF_RAMP]
        if live and len(live) < len(cand):
            ties.append((k, live, [r for r in cand if r not in live], "off-ramp yields to live"))
            cand = live
        dev = [r for r in cand if r["anchor_role"] != "structure_only"]
        if dev and len(dev) < len(cand):
            ties.append((k, dev, [r for r in cand if r not in dev], "lone permit yields to development"))
            cand = dev
        if len(cand) == 1:
            res[k] = cand[0]
        else:
            amb[k] = cand
    return res, amb, ties


def by_address(rows=None):
    """({key: row} resolved, {key: [rows]} ambiguous, [(key, kept, dropped, rule)] tie-breaks).

    TWO TIERS. A project's own address_display decides first; only a key no project displays is
    looked up among the addresses on projects' STRUCTURES (2131 University, Acheson's umbrella
    address; 2150 Kittredge, which v4 displays as 2176). Within a tier, two tie-breaks, each
    recorded: (1) an off-ramp project (withdrawn/denied/expired) yields to a live one at the same
    address; (2) a structure-only project (a lone building permit, e.g. an ADU) yields to a
    Planning-anchored development at the same address. Anything still plural is AMBIGUOUS and
    resolves to nothing -- the caller reports it, never guesses.
    """
    rows = rows if rows is not None else projects()
    g1, g2 = collections.defaultdict(list), collections.defaultdict(list)
    for r in rows:
        k = akey(r["address_display"])
        if k:
            g1[k].append(r)
    for r in rows:
        for k in r.get("other_addresses", ()):
            k = _strip_unit(k)
            if k not in g1 and r not in g2[k]:
                g2[k].append(r)
    r1, a1, t1 = _resolve(g1)
    r2, a2, t2 = _resolve(g2)
    return {**r2, **r1}, {**a2, **a1}, t1 + t2


def address_rows(index=None):
    """One row per ADDRESS that resolves to exactly one project. A row resolved through one of the
    project's other structure addresses (Acheson's 2131 University) carries THAT address in
    address_display, so it meets the geometry under the address the footprint is drawn with;
    `via` says which ('display' | 'structure'). One project can therefore appear more than once."""
    out = []
    for k, r in (index or by_address())[0].items():
        if akey(r["address_display"]) == k:
            # "2000 DWIGHT Way A": the unit letter is not part of the address the geometry draws
            txt = re.sub(r"\s+[A-Za-z]$", "", r["address_display"].strip())
            out.append({**r, "address_display": txt, "via": "display", "akey": k})
        else:
            txt = " ".join(w if w[:1].isdigit() else w.capitalize() for w in k.replace("|", " ").split())
            out.append({**r, "address_display": txt, "via": "structure", "akey": k})
    return out


def lookup(addr, index=None):
    """The one v4 project at an address, or None (unknown OR ambiguous -- never a guess)."""
    res = (index or by_address())[0]
    return res.get(akey(addr))


def projects_with_document(doc_type=None, title_like=None):
    """{project_key} holding a STORED document (store_url) of that doc_type and/or title pattern,
    joined documents.record_key -> project_records -> projects (the Explorer's own join)."""
    where, args = ["d.store_url IS NOT NULL"], []
    if doc_type:
        where.append("d.doc_type = ?"); args.append(doc_type)
    if title_like:
        where.append("(" + " OR ".join("lower(d.title) LIKE ?" for _ in title_like) + ")")
        args += [t.lower() for t in title_like]
    db = connect()
    out = {k for (k,) in db.execute(
        "SELECT DISTINCT json_extract(p.notes, '$.project_key') FROM documents d "
        "JOIN project_records pr ON pr.record_key = d.record_key JOIN projects p ON p.project_id = pr.project_id "
        "WHERE " + " AND ".join(where), args)}
    db.close()
    return out


def tabulation_projects():
    """Projects holding an architect Tabulation Form (1.E): v4 doc_type tabulation_form, or the
    title pattern v2 used ('1.E' / 'tabulation'), whichever names it."""
    return (projects_with_document("tabulation_form")
            | projects_with_document(title_like=["%1.e%", "%tabulation%"]))
