#!/usr/bin/env python3
"""capdetail_select.py -- ONE implementation of "which city action is this project's rung 3".

Imported by BOTH scripts/preview_capdetail_events.py (which prints it) and
scripts/migration/ingest_capdetail_events.py (which writes it). Factored out rather than copied,
because two copies of a selection rule drift and the drift is invisible: the preview would approve
one thing and the ingest write another.

The rule, and why it is a SELECTION and not an aggregate, is
docs/methodology/identity_is_the_product.md. Short form: a project has many Planning records and
each has its own Completeness Review, so MIN/MAX over them promotes one record's action to speak for
the project. Rung 3 is the acceptance of the project's PRIMARY APPLICATION, identified by record
role (housing_rules.planning_record) -- and where that record cannot be identified, the honest
answer is "unknown with provenance" (working rule 1), not an extremum.

Read-only: takes an already-open read-only v2 connection and a parsed-harvest JSONL path.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from housing_rules.address import normalize_address   # noqa: E402  THE rule-4c canon
from housing_rules.address_points import resolve as resolve_address  # noqa: E402  lane 3
from housing_rules.planning_record import role        # noqa: E402  THE record-role canon

EV_APP_COMPLETE = 3
from housing_rules.planning_record import ACCEPTED, ACCEPT_TASK  # noqa: E402  one definition of "accepted"
ANCHOR_TOLERANCE_DAYS = 60

# Records state their own lineage IN THE DESCRIPTION. Measured 2026-09-26 over all 2,310 Zoning
# Permits: 72 cite another record by number and 60 of those are explicit modifications
# ("Use Permit Modification of ZP2016-0117", "UP Mod of ZP2022-0179"). This matters because 19% of
# v2 projects (76 of 395) sit at an address with MORE THAN ONE Zoning Permit, and most of those are
# not ambiguity -- they are a CHAIN: an original use permit plus its later modifications, which is
# ONE project. Rung 3 then belongs to the ROOT of the chain, not to whichever modification is latest
# or happens to sit nearest filed_date.
#
# The distinction the citation buys us is between two very different situations:
#   CHAIN      -- one record modifies another in the set  -> select the root, no ambiguity
#   CONFLATED  -- several primaries with NO citation between them -> v2 has stitched one timeline
#                 from separate applications (proj10 3000 Shattuck: filed_date from ZP2015-0229,
#                 app_complete from the unrelated ZP2022-0046, a 9-storey gas-station scheme).
#                 That is a DATA FINDING to report, not a selection to make.
# A WITHDRAWN or EXPIRED application's acceptance is not the project's rung 3 when a live application
# exists: proj45 selected ZP2016-0091 (Withdrawn 2016) for a project whose later ZP2025-0085 also
# withdrew, and proj41 selected the withdrawn ZP2021-0073 over the APPROVED ZP2022-0113. The city
# accepting an application that was then abandoned is a real fact about that RECORD, but it is not the
# acceptance that carried the project forward. Where every primary is dead, the only acceptance on
# record is still the honest answer -- so this PREFERS live applications, it does not discard dead ones.
DEAD_STATUS = re.compile(r"^(withdrawn|expired|void|cancel)", re.I)

CITE = re.compile(r"\b(ZP|UP|PLN|DRC[PF]?)\s*#?\s*(\d{4})-(\d{3,4})\b", re.I)
MODWORD = re.compile(r"\b(modif|mod of|amend|extension of|extend|supersed)", re.I)


def addr_key(a: str | None):
    """(house number, street core) via the rule-4c canon -- never a local key.

    NOT scripts/build_v2/s0_keys.normalize_address, which is the v3 pipeline's internal keying and
    leaves the county-situs "*" in the street ('SHATTUCK AVE *', matching nothing).
    """
    if not a:
        return None
    num, street = normalize_address(a)
    if not (num and street):
        return None
    # HOUSE NUMBER 0 IS A REAL CONVENTION, AND IT IS MANY-TO-ONE.
    # "0 <street>" is how the City records an unnumbered or vacant parcel, and BOTH departments use
    # it: v2 holds 6 such projects and the Planning records for the same sites say "0 LATHAM Ln",
    # "0 CRAGMONT Ave", "0 GRIZZLY PEAK Blvd" too. So it is not junk to be discarded -- but several
    # DISTINCT parcels share one such string ("0 Latham Ln" covers APNs ...034-02, -26, -37, -38), so
    # the street cannot identify the project and keying on it manufactured 4 false "conflations".
    #
    # THE APN IS THE DISAMBIGUATOR, and it works: proj197 ("0 Cragmont Ave", 063-2986-022-00) matches
    # ZP2020-0058 on exactly that parcel, while ZP2021-0177 on 063-2952-023-00 correctly does not.
    # So the address key is withheld for these and the APN join carries them.
    #
    # The assessor often holds the real street address for the same parcel (proj377 -> 1024 GRIZZLY
    # PEAK, proj769 -> 1298 QUEENS RD, proj828 -> 1028 GRIZZLY PEAK -- note v2 calls that one LATHAM,
    # the division-of-authority case in CLAUDE.md rule 4). Those numbers do NOT appear on any Planning
    # record, so they cannot be used to join here -- but they are the right starting point if these
    # projects ever need a real address, and proj73 ("0 LE ROY Ave") is unnumbered in the assessor too,
    # so it may genuinely have none. (John's insight, 2026-09-26.)
    if num == "0":
        return None
    return (num, street)


def addr_key_resolved(addr, apns, lat=None, lon=None):
    """LANE 3: the address key, with a placeholder resolved through the CITY ADDRESS-POINT LAYER.

    Lanes 1 and 2 (normalized address, canonical APN) both fail on a project whose address is a
    "0 <street>" placeholder. The City's address-point layer answers by PARCEL, so a placeholder plus
    an APN becomes a real key: proj73's "0 LE ROY Ave" on 058-2244-025-01 resolves to 1463 Le Roy Ave.
    Returns (key, source) so a caller can record WHERE the key came from -- a resolved key is evidence
    with a provenance, not a silent substitution.
    """
    resolved, src = resolve_address(addr, apns, lat, lon)
    return addr_key(resolved), src


def cited_records(rec: dict) -> set[str]:
    """record numbers this record's own prose names (excluding itself)."""
    blob = " ".join(str(rec.get(f) or "") for f in ("description", "record"))
    me = str(rec.get("record") or "")
    out = set()
    for m in CITE.finditer(blob):
        n = f"{m.group(1).upper()}{m.group(2)}-{m.group(3)}"
        if n != me:
            out.add(n)
    return out


def is_modification(rec: dict) -> bool:
    """does this record describe itself as modifying/amending/extending another record?"""
    return bool(MODWORD.search(str(rec.get("description") or "")) and cited_records(rec))


def _live(prims: list[dict]) -> list[dict]:
    """prefer applications that were not withdrawn/expired; fall back to all if none survive."""
    live = [r for r in prims if not DEAD_STATUS.match(str(r.get("record_status") or ""))]
    return live or prims


def resolve_chain(prims: list[dict]):
    """-> (root, kind). kind is 'single' | 'chain' | 'conflated' | 'unlinked'.

    A chain is resolved by dropping every record that modifies another record IN THIS SET. If exactly
    one survives, it is the root. If several primaries survive and none cites another, they are
    separate applications sharing an address -- reported, never silently reduced.
    """
    if len(prims) == 1:
        return prims[0], "single"
    nums = {str(r.get("record")) for r in prims}
    children = [r for r in prims if is_modification(r) and (cited_records(r) & nums)]
    roots = [r for r in prims if r not in children]
    if len(roots) == 1:
        return roots[0], "chain"
    # SIBLINGS OF A COMMON ANCESTOR are one project, even though neither cites the other. proj35
    # (2190 Shattuck, 452u): ZP2022-0026 and ZP2025-0101 BOTH cite ZP2016-0117 -- two modifications of
    # the same original, which is a modification FAMILY, not two buildings. Requiring one record to
    # cite the OTHER mislabelled that as conflated. The ancestor itself may not be in the set (it need
    # not have joined this project), so the earliest sibling carries the acceptance.
    ancestors = [cited_records(r) for r in roots]
    if len(roots) > 1 and set.intersection(*ancestors):
        earliest = sorted(roots, key=lambda r: str(r.get("list_date_iso") or _iso_list(r) or "9999"))
        return earliest[0], "chain"
    linked = any(cited_records(r) & nums for r in prims)
    return None, ("conflated" if not linked else "unlinked")


def _iso_list(rec: dict) -> str | None:
    d = _mdy_to_date(rec.get("list_date"))
    return d.isoformat() if d else None


def _mdy_to_date(s):
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(s or ""))
    return dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else None


def load_rows(jsonl: str | Path) -> list[dict]:
    rows = {}
    for line in open(jsonl):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("record") and not r.get("error"):
            rows[r["record"]] = r            # last write wins on a reparse
    return list(rows.values())


def accepted_task(r: dict):
    """the Completeness-Review disposition that means ACCEPTED, or None."""
    for t in (r.get("processing_status") or []):
        if t.get("status") and ACCEPTED.search(t["status"]) and ACCEPT_TASK.search(t["task"]):
            return t
    return None


def select_rung3(rows: list[dict], db) -> dict:
    """-> {'selected': {pid: (record, task)}, plus diagnostics for the preview to print}.

    Two joins to reach a project (address key AND canonical APN), reported separately because
    CLAUDE.md rule 4 is explicit that APNs are not stable identity; where they disagree, that IS
    the finding. Then one selection per project by record role.
    """
    by_addr = collections.defaultdict(set)
    proj_apns = collections.defaultdict(list)
    for pid, apn in db.execute(
            "SELECT pp.project_id, p.apn_normalized FROM project_parcels pp "
            "JOIN parcels p ON p.id=pp.parcel_id WHERE p.apn_normalized IS NOT NULL"):
        proj_apns[pid].append(apn)
    coords = {pid: (lat, lon) for pid, lat, lon in db.execute(
        "SELECT id,latitude,longitude FROM projects")}
    for pid, a in db.execute("SELECT project_id,address_display FROM v_projects_flat "
                             "WHERE address_display IS NOT NULL"):
        k = addr_key(a)
        if k:
            by_addr[k].add(pid)
        else:
            # a PROJECT whose own address is a placeholder is unreachable by lanes 1-2 unless its
            # parcel is known; lane 3 gives it a real key from the City address-point layer.
            lat, lon = coords.get(pid, (None, None))
            k3, src3 = addr_key_resolved(a, proj_apns.get(pid, []), lat, lon)
            # only a GEOMETRICALLY VERIFIED substitution may create a join key: proj151 "Ashby BART"
            # resolves to an address point 1,562 m away and must not be indexed under it.
            if k3 and src3 == "city_address_points":
                by_addr[k3].add(pid)
    by_apn = collections.defaultdict(set)
    for pid, apn in db.execute(
            "SELECT pp.project_id, p.apn_normalized FROM project_parcels pp "
            "JOIN parcels p ON p.id=pp.parcel_id WHERE p.apn_normalized IS NOT NULL"):
        by_apn[apn].add(pid)
    filed = {pid: f for pid, f in db.execute(
        "SELECT project_id, filed_date FROM v_projects_flat WHERE filed_date IS NOT NULL")}

    acc = [r for r in rows if accepted_task(r)]
    per_project = collections.defaultdict(list)
    join = collections.Counter()
    disagree = []
    for r in acc:
        canon_first = [c for c in (r.get("parcels_canonical") or []) if c]
        rkey, rsrc = addr_key_resolved(r.get("work_location"), canon_first)
        if rsrc == "city_address_points":
            join["lane3_address_point_resolved"] += 1
        a_pids = by_addr.get(rkey, set())
        canon = [c for c in (r.get("parcels_canonical") or []) if c]
        p_pids = set()
        for c in canon:
            p_pids |= by_apn.get(c, set())
        if a_pids and p_pids:
            join["both"] += 1
            if a_pids != p_pids:
                disagree.append((r["record"], r.get("work_location"),
                                 sorted(a_pids), canon, sorted(p_pids)))
        elif a_pids:
            join["address_only"] += 1
        elif p_pids:
            join["apn_only"] += 1
        else:
            join["no_project"] += 1
        for pid in (a_pids | p_pids):
            per_project[pid].append(r)

    selected, no_primary, ambiguous, chains, conflated = {}, [], [], [], []
    for pid, recs in per_project.items():
        prim = [r for r in recs if role(r.get("record_type")) == "primary_application"]
        if not prim:
            no_primary.append((pid, sorted({role(r.get("record_type")) for r in recs}),
                               [r["record"] for r in recs]))
            continue
        prim_all = prim
        prim = _live(prim)
        root, kind = resolve_chain(prim)
        if root is not None and kind in ("single", "chain"):
            selected[pid] = (root, accepted_task(root))
            if kind == "chain":
                chains.append((pid, str(root.get("record")),
                               [str(r.get("record")) for r in prim if r is not root]))
            continue
        if kind == "conflated":
            # Separate applications sharing an address. Do NOT fall through to the filed_date
            # anchor: proj10 (3000 Shattuck) has ZP2015-0229 filed the SAME DAY as v2's filed_date,
            # so the anchor matched at a 0-day gap and silently overrode the conflation verdict,
            # selecting the 2015 application for a project whose units (166) match the unrelated
            # 2022 one. A date coincidence is not evidence of identity, and proximity must never
            # outrank an explicit finding that the records are unrelated.
            conflated.append((pid, [r["record"] for r in prim], filed.get(pid)))
            continue
        if True:
            f = filed.get(pid)
            pick = None
            if f:
                fd = dt.date.fromisoformat(f)

                def gap(r):
                    d = _mdy_to_date(r.get("list_date"))
                    return abs((d - fd).days) if d else 10 ** 6
                best = sorted(prim, key=gap)
                if gap(best[0]) <= ANCHOR_TOLERANCE_DAYS and (
                        len(best) == 1 or gap(best[1]) > gap(best[0])):
                    pick = best[0]
            if pick is None:
                (conflated if kind == "conflated" else ambiguous).append(
                    (pid, [r["record"] for r in prim], f))
                continue
            selected[pid] = (pick, accepted_task(pick))

    return {"selected": selected, "no_primary": no_primary, "ambiguous": ambiguous,
            "chains": chains, "conflated": conflated,
            "join": join, "disagree": disagree, "accepted_records": acc,
            "per_project": per_project}
