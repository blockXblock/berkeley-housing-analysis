#!/usr/bin/env python3
"""ingest_cpra_2026.py — load the 2025/2026 CPRA building-permit feed into v2.

WHY. v2's permit feed stopped at 2025-12-22, so every 2026 completion was missing: v2 held 2
projects with a 2026 CO while the city had finaled 113 housing permits, including 3030 Telegraph
at 144 units. `BP_Annual Permit Report-2025-2026-07-07.xlsx` has been sitting in the repo unloaded.

SCOPE (gated by John 2026-09-25, "full housing scope"): the permits the housing-role classifier
calls `new_unit`, and only those. The feed's 5,018 alterations and 1,204 subsidiary permits are
re-roofs, water heaters and panel upgrades; loading them would swamp a project-oriented serving
database. Preview: docs/audit/2026-09-25_cpra_2026_ingest_preview.md

WHY THE CLASSIFICATION IS TRUSTWORTHY HERE. This file carries Work Type, OccType, ADU, UnitsAdded
and UnitsRemoved — the inputs `housing_rules.permit_role.classify` is built for and the Accela list
scrape lacks. Fed the full inputs, ambiguity over these same 8,039 rows falls from 82.7% to 15.4%.
Every `new_unit` row also carries a Parcel Number, so projects are matched through
`to_canonical_apn` rather than fuzzy address matching (the 890/892-false-dead trap).

COMPLETION VERDICT. A permit the City has FINALED is evidence the building is occupiable — per
CLAUDE.md the finaled permit outranks an assessor Imps=$0. Those get `completes` / `evidentiary`.
Issued-but-not-finaled permits get **no verdict at all** (NULL), never a guess.

DISCIPLINE. Snapshot taken before running (keep_snapshot_2026-09-25_pre-cpra-2026-ingest.db).
Dry-run by default. The write is a single transaction that verifies its own row deltas and
**rolls back** if any count is off.

Usage:
    python scripts/migration/ingest_cpra_2026.py              # dry run, prints the plan
    python scripts/migration/ingest_cpra_2026.py --commit     # transactional write
"""
import argparse
import collections
import datetime
import re
import sqlite3
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from housing_rules import to_canonical_apn                       # noqa: E402
from housing_rules.permit_role import classify                   # noqa: E402

BP_FILE = ROOT / "data/raw/cpra-downloads/BP_Annual Permit Report-2025-2026-07-07.xlsx"
V2 = ROOT / "databases/berkeley_housing_v2.db"
BERK = ROOT / "databases/berkeley.db"

CITY_ID = 1
COUNTY = "alameda"
VERDICT_BY = "permit_role_classifier@4eb77df+cpra_2026_ingest"
SOURCE_SYSTEM = "cpra"
SOURCE_URL = "CPRA: BP_Annual Permit Report-2025-2026-07-07.xlsx"

V = {  # vocabulary ids, read from the database 2026-09-25
    "permit_building": 5, "status_issued": 5, "status_finaled": 7,
    "ev_bp_issued": 14, "ev_permit_finaled": 25,
    "ver_as_built": 5, "ver_bp_set": 4,
    "stage_completed": 6, "stage_permitted": 4,
    "rel_primary": 1, "conf_high": 1,
}


def canon(a):
    try:
        return to_canonical_apn(a, COUNTY)
    except Exception:
        return None


def num(x):
    try:
        return int(float(str(x).strip()))
    except Exception:
        return 0


def d(x):
    """Dates in this feed are MIXED: Submittal/Finaled arrive as datetimes, Issuance Date as a
    'MM/DD/YYYY' STRING. Handling only datetimes silently dropped all 7,889 BP-issued events on the
    first pass — and bp_issued_date is what the RHNA 6th-cycle credit rule turns on."""
    if isinstance(x, datetime.datetime):
        return x.date().isoformat()
    s = str(x or "").strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    return m.group(0) if m else None


def units_for(units_added, number_units, net):
    """Net new dwellings, with the basis recorded. UnitsAdded is the source's own net-new field and
    is present on 79% of new_unit rows. NumberUnits is TOTAL units in the building, which agrees
    with UnitsAdded on only 144/351 rows where both exist, so it is a fallback, never a substitute.
    Where neither is usable we record 1 as a DOCUMENTED FLOOR -- a new_unit permit creates at least
    one dwelling by definition -- and flag the row. We never silently adopt the classifier's own
    default, which returns 1 for every such row regardless of the evidence."""
    if units_added:
        return num(units_added), "cpra_units_added"
    if num(number_units) > 0:
        return num(number_units), "cpra_number_units"
    return 1, "floor_new_unit_role"


NOT_DWELLING = re.compile(
    r"(solar|photovoltaic|\bpv\b|roof.?mount|re-?roof|extension for .*permit|"
    r"\bextension\b.*\bpermit\b|meter panel|electrical service|water line|water meter|"
    r"temp(orary)? power|power pole|sewer lateral|seismic|pool\b|spa\b|hot tub|fence|"
    r"driveway|curb cut|retaining wall|landscap)", re.I)

VETOED = []
FEED_FINALED = {}          # permit_number -> finaled date, for EVERY row in the feed


def read_new_units():
    ws = openpyxl.load_workbook(BP_FILE, read_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    idx = {h: i for i, h in enumerate(rows[7]) if h}
    out = []
    for r in rows[8:]:
        if not r[0]:
            continue
        g = lambda k: r[idx[k]] if k in idx else None            # noqa: E731
        FEED_FINALED[str(g("PermitNumber")).strip()] = d(g("Finaled Date"))
        role, net, note = classify(
            work_type=g("Work Type") or "", description=g("WorkDescription") or "",
            adu_flag=g("ADU"), occtype=g("OccType") or "",
            units_added=g("UnitsAdded"), units_removed=g("UnitsRemoved"),
            permit_number=str(g("PermitNumber")))
        if role != "new_unit":
            continue
        # VETO: the source's own UnitsAdded field is authoritative when it is explicitly 0.
        # The classifier's RULE 5.5 fires on ADU=Yes plus conversion language, but in this feed
        # ADU=Yes marks a parcel that HAS an ADU, not a permit that CREATES one -- so "CONVERT
        # EXISTING METER PANEL" on an ADU parcel came back new_unit with UnitsAdded='0'. 100 of
        # the 447 new_unit rows are like this: pools, seismic upgrades, temp power, a burned bus
        # bar. Left in, they created projects AND moved real completion dates: proj483 finaled a
        # house in 2018 and a meter-panel swap in 2026 pushed its CO date to 2026.
        # We do not edit housing_rules.permit_role here -- it is the shared v4 classifier with its
        # own tests (CLAUDE.md: import it, never redefine it). We refuse the row at the ingest
        # boundary and write it out for review, per flag-for-review-never-auto.
        # SECOND VETO. Where UnitsAdded is ABSENT we fall back to NumberUnits, which is TOTAL
        # units in the building -- so a solar install or a permit extension on a 2-unit parcel
        # reads as "2 new units". 2236 Grant entered as a 2-unit 2025 completion off a roof-mount
        # PV permit that way. When the source gives us no net-new figure AND the description is
        # plainly not dwelling-creating work, refuse the row rather than invent a unit count.
        desc_txt = (g("WorkDescription") or "")
        if (not str(g("UnitsAdded") or "").strip() or str(g("UnitsAdded")).strip() in ("", "None")) \
                and NOT_DWELLING.search(desc_txt):
            VETOED.append({"permit": str(g("PermitNumber")).strip(), "units_added": "",
                           "number_units": str(g("NumberUnits") or "").strip(),
                           "work_type": g("Work Type") or "",
                           "note": "no UnitsAdded + non-dwelling description",
                           "desc": desc_txt.strip()})
            continue
        ua_raw = g("UnitsAdded")
        if ua_raw is not None and str(ua_raw).strip() not in ("", "None") and num(ua_raw) == 0:
            VETOED.append({"permit": str(g("PermitNumber")).strip(),
                           "units_added": str(ua_raw).strip(),
                           "number_units": str(g("NumberUnits") or "").strip(),
                           "work_type": g("Work Type") or "", "note": note,
                           "desc": (g("WorkDescription") or "").strip()})
            continue
        st = " ".join(str(x) for x in (g("StreetNumber"), g("StreetName"), g("StreetType")) if x).strip()
        units, ubasis = units_for(g("UnitsAdded"), g("NumberUnits"), net)
        out.append({
            "permit": str(g("PermitNumber")).strip(), "apn": canon(g("Parcel Number")),
            "apn_raw": str(g("Parcel Number") or "").strip(), "address": st,
            "filed": d(g("Submittal Date")), "issued": d(g("Issuance Date")),
            "finaled": d(g("Finaled Date")), "valuation": g("JobValuation"),
            "desc": (g("WorkDescription") or "").strip(),
            "units": units, "units_basis": ubasis, "note": note,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--db", default=str(V2), help="target database (default: the live v2)")
    args = ap.parse_args()

    rows = read_new_units()
    db = sqlite3.connect(args.db)
    db.execute("PRAGMA foreign_keys=ON")
    have = {p for (p,) in db.execute("SELECT permit_number FROM permits WHERE permit_number IS NOT NULL")}
    rows = [r for r in rows if r["permit"] not in have and r["apn"]]

    apn2proj, apn2parcel, addr2proj = {}, {}, {}
    # SECOND-PASS MATCH. The APN is primary, but v2 holds projects whose parcel link was never
    # made -- 2808 Ninth St (project 69) is one, and inserting it again violated the
    # (city_id, canonical_address) UNIQUE constraint on the first attempt. Falling back to the
    # canonical address attaches the permit to the real project AND backfills the missing APN link,
    # instead of creating a shadow duplicate that the merge rules would later have to clean up.
    for pid, a in db.execute("SELECT id, canonical_address FROM projects WHERE canonical_address IS NOT NULL AND merged_into_id IS NULL"):
        addr2proj.setdefault(a.strip().upper(), pid)
    for pid, apn in db.execute("""SELECT pp.project_id, pa.apn_normalized FROM project_parcels pp
                                  JOIN parcels pa ON pa.id=pp.parcel_id WHERE pa.apn_normalized IS NOT NULL"""):
        apn2proj.setdefault(apn, pid)
    for pid, apn in db.execute("SELECT id, apn_normalized FROM parcels WHERE apn_normalized IS NOT NULL"):
        apn2parcel[apn] = pid

    berk = sqlite3.connect(f"file:{BERK}?mode=ro", uri=True)
    latlon = {}
    for a, la, lo in berk.execute("SELECT APN,Latitude,Longitude FROM parcels WHERE Latitude IS NOT NULL"):
        c = canon(a)
        if c:
            latlon[c] = (float(la), float(lo))

    by_apn = collections.OrderedDict()
    for r in rows:
        by_apn.setdefault(r["apn"], []).append(r)
    # A project that ALREADY has a completion date, plus a permit that finals LATER, is two
    # buildings on one parcel -- the main house and a later ADU -- not one project. CLAUDE.md's
    # SHADOW vs ADU-PAIR rule is explicit: two real permits with two distinct COs are two real
    # buildings, PROTECT, never merge. Attaching anyway made v2 WRONG rather than incomplete,
    # because co_issued_date is MAX over finaled events: 1527 Woolsey's 2019 ADU became a 2025
    # completion, 2227 Carleton's 2025 ADU became 2026. So in that case we create a sibling
    # project on the same parcel instead of attaching.
    completed = {pid: co for pid, co in db.execute(
        "SELECT project_id, co_issued_date FROM v_projects_flat WHERE co_issued_date IS NOT NULL")}

    def would_move_completion(pid, items):
        """True when attaching would describe a DIFFERENT building than the one that completed.

        Checks the issue date as well as the final. A permit merely ISSUED after the project's CO
        is still a later, separate piece of work: attaching two of them gave projects a
        bp_issued_date LATER than their co_issued_date (1332 Neilson: CO 2024-02-05, BP
        2026-01-14), which is an impossible order and would hand those projects a spurious 6th-cycle
        RHNA credit, since credit turns on a first BP on/after 2022-06-30."""
        co = completed.get(pid)
        if not co:
            return False
        return any((i["finaled"] and i["finaled"] > co) or (i["issued"] and i["issued"] > co)
                   for i in items)

    def resolve(apn):
        """-> (project_id or None, how)"""
        items = by_apn[apn]
        cand = apn2proj.get(apn)
        if cand is None:
            a = (items[0]["address"] or "").strip().upper()
            cand = addr2proj.get(a) if a else None
            how = "address" if cand else None
        else:
            how = "apn"
        if cand is not None and would_move_completion(cand, items):
            return None, "sibling"          # separate building on the same parcel
        if cand is not None:
            return cand, how
        return None, "create"

    resolved = {a: resolve(a) for a in by_apn}
    new_apns = [a for a, (pid, _) in resolved.items() if pid is None]
    siblings = [a for a, (pid, how) in resolved.items() if how == "sibling"]
    by_addr = [a for a, (pid, how) in resolved.items() if how == "address"]

    if VETOED:
        vp = ROOT / "data/reference/cpra_2026_vetoed_zero_units.csv"
        vp.write_text("permit,units_added,number_units,work_type,classifier_note,description\n" + "".join(
            f'{v["permit"]},{v["units_added"]},{v["number_units"]},"{v["work_type"]}",'
            f'"{v["note"]}","{v["desc"][:120].replace(chr(34), chr(39))}"\n' for v in VETOED))
        print(f"VETOED (source says UnitsAdded=0): {len(VETOED)} -> {vp.name}")
    print(f"permits to insert          {len(rows)}")
    print(f"  attach to existing proj  {sum(len(v) for a, v in by_apn.items() if a in apn2proj)}")
    print(f"  on APNs with no project  {sum(len(v) for a, v in by_apn.items() if a not in apn2proj)}")
    print(f"  matched by address instead {len(by_addr)}" + (f"  {by_addr}" if by_addr else ""))
    print(f"  sibling (own project, would have moved a CO date) {len(siblings)}")
    print(f"projects to create         {len(new_apns)}")
    print(f"  geocodable               {sum(1 for a in new_apns if a in latlon)}")
    print(f"parcels to create          {sum(1 for a in new_apns if a not in apn2parcel)}")
    fin = [r for r in rows if r["finaled"]]
    print(f"events: bp_issued {sum(1 for r in rows if r['issued'])}  permit_finaled {len(fin)}")
    ub = collections.Counter(r["units_basis"] for r in rows)
    print("unit-count basis: " + "  ".join(f"{k}={v}" for k, v in ub.most_common()))
    flagged = [r for r in rows if r["units_basis"] == "floor_new_unit_role"]
    if flagged:
        fp = ROOT / "data/reference/cpra_2026_units_needs_review.csv"
        fp.write_text("permit,address,units_recorded,description\n" + "".join(
            f'{r["permit"]},"{r["address"]}",{r["units"]},"{r["desc"][:110]}"\n' for r in flagged))
        print(f"  {len(flagged)} rows recorded at the documented floor of 1 -> {fp.name}")
    print(f"completion verdicts 'completes': {len(fin)}   (issued-only get NULL, never a guess)")
    if not args.commit:
        print("\nDRY RUN — nothing written. Re-run with --commit.")
        return 0

    now = datetime.datetime.now().isoformat(timespec="seconds")
    before = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("permits", "projects", "project_versions", "project_parcels",
                        "parcels", "project_events")}
    made = collections.Counter()
    inserted_permit_ids = []
    try:
        db.execute("BEGIN")
        for apn, items in by_apn.items():
            pid, how = resolved[apn]
            if pid is not None and how == "address":
                # backfill the parcel link this project was missing
                parcel_id = apn2parcel.get(apn)
                if parcel_id is None:
                    c = db.execute(
                        """INSERT INTO parcels (city_id, apn, address, apn_raw, apn_normalized,
                           assessing_county, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)""",
                        (CITY_ID, apn, items[0]["address"], items[0]["apn_raw"], apn, COUNTY, now, now))
                    parcel_id = c.lastrowid
                    apn2parcel[apn] = parcel_id
                    made["parcels"] += 1
                linked = db.execute("SELECT 1 FROM project_parcels WHERE project_id=? AND parcel_id=?",
                                    (pid, parcel_id)).fetchone()
                if not linked:
                    db.execute("""INSERT INTO project_parcels (project_id, parcel_id,
                                  relationship_type_id, is_primary, notes) VALUES (?,?,?,0,?)""",
                               (pid, parcel_id, V["rel_primary"],
                                SOURCE_URL + " (APN link backfilled by address match)"))
                    made["project_parcels"] += 1
            if pid is None:
                head = items[0]
                la, lo = latlon.get(apn, (None, None))
                # A sibling shares its parcel's address with the project already there, and
                # (city_id, canonical_address) is UNIQUE. Disambiguate by the permit that
                # created it, so the row stays traceable to its source instead of getting a
                # meaningless serial suffix.
                addr = head["address"] or apn
                if how == "sibling":
                    addr = f"{addr} [{head['permit']}]"
                head = dict(head, address_key=addr)
                units = sum(i["units"] for i in items)
                anyfin = any(i["finaled"] for i in items)
                cur = db.execute(
                    """INSERT INTO projects (city_id, canonical_name, canonical_address,
                       normalized_address, latitude, longitude, current_stage_type_id,
                       created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (CITY_ID, head["address_key"], head["address_key"],
                     head["address_key"].upper(), la, lo,
                     V["stage_completed"] if anyfin else V["stage_permitted"], now, now))
                pid = cur.lastrowid
                made["projects"] += 1

                parcel_id = apn2parcel.get(apn)
                if parcel_id is None:
                    c = db.execute(
                        """INSERT INTO parcels (city_id, apn, address, apn_raw, apn_normalized,
                           assessing_county, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)""",
                        (CITY_ID, apn, head["address"], head["apn_raw"], apn, COUNTY, now, now))
                    parcel_id = c.lastrowid
                    apn2parcel[apn] = parcel_id
                    made["parcels"] += 1
                db.execute("""INSERT INTO project_parcels (project_id, parcel_id,
                              relationship_type_id, is_primary, notes) VALUES (?,?,?,1,?)""",
                           (pid, parcel_id, V["rel_primary"], SOURCE_URL))
                made["project_parcels"] += 1

                vc = db.execute(
                    """INSERT INTO project_versions (project_id, version_label, version_type_id,
                       effective_date, total_units, is_current, asserted_by, asserted_at,
                       confidence_type_id, created_at, updated_at, description)
                       VALUES (?,?,?,?,?,1,?,?,?,?,?,?)""",
                    (pid, "CPRA 2026 ingest",
                     V["ver_as_built"] if anyfin else V["ver_bp_set"],
                     max((i["finaled"] or i["issued"] or "") for i in items) or None,
                     units, VERDICT_BY, now, V["conf_high"], now, now,
                     f"[units basis: {', '.join(sorted({i['units_basis'] for i in items}))}] "
                     + head["desc"][:440]))
                db.execute("UPDATE projects SET current_version_id=? WHERE id=?", (vc.lastrowid, pid))
                made["project_versions"] += 1
                apn2proj[apn] = pid

            for it in items:
                finaled = bool(it["finaled"])
                pc = db.execute(
                    """INSERT INTO permits (project_id, source_system, source_permit_id,
                       permit_number, permit_type_id, permit_status_type_id, filed_date,
                       issued_date, finaled_date, valuation, source_url, description,
                       completion_verdict, completion_basis, completion_basis_note,
                       completion_verdict_by, completion_verdict_at, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (pid, SOURCE_SYSTEM, it["permit"], it["permit"], V["permit_building"],
                     V["status_finaled"] if finaled else V["status_issued"],
                     it["filed"], it["issued"], it["finaled"],
                     (float(it["valuation"]) if isinstance(it["valuation"], (int, float))
                      and float(it["valuation"]) >= 0 else None),
                     SOURCE_URL, it["desc"],
                     "completes" if finaled else None,
                     "evidentiary" if finaled else None,
                     (f"City finaled the permit; units basis={it['units_basis']}; " + it["note"])
                     if finaled else None,
                     VERDICT_BY if finaled else None, now if finaled else None, now, now))
                permit_id = pc.lastrowid
                inserted_permit_ids.append(permit_id)
                made["permits"] += 1
                if it["issued"]:
                    db.execute(
                        """INSERT INTO project_events (project_id, event_type_id, event_date,
                           event_date_precision, permit_id, summary, units_affected,
                           confidence_type_id, is_inferred, source_type, source_url,
                           observed_by, observed_at, created_at)
                           VALUES (?,?,?,'exact',?,?,?,?,0,'document',?,?,?,?)""",
                        (pid, V["ev_bp_issued"], it["issued"], permit_id,
                         f"BP {it['permit']} issued", it["units"] or None, V["conf_high"],
                         SOURCE_URL, VERDICT_BY, now, now))
                    made["project_events"] += 1
                if finaled:
                    db.execute(
                        """INSERT INTO project_events (project_id, event_type_id, event_date,
                           event_date_precision, permit_id, summary, units_affected,
                           confidence_type_id, is_inferred, source_type, source_url,
                           observed_by, observed_at, created_at)
                           VALUES (?,?,?,'exact',?,?,?,?,0,'document',?,?,?,?)""",
                        (pid, V["ev_permit_finaled"], it["finaled"], permit_id,
                         f"BP {it['permit']} finaled", it["units"] or None, V["conf_high"],
                         SOURCE_URL, VERDICT_BY, now, now))
                    made["project_events"] += 1

        # ---- BACK-FILL --------------------------------------------------------------------
        # Inserting only NEW permit numbers left 3030 Telegraph's 144-unit completion behind: its
        # permit was already in v2 carrying an EMPTY finaled_date, and the feed's 2026-04-16 final
        # was skipped along with the permit. 12 permits are in that position and NONE disagrees
        # with the feed, so this is missing EVIDENCE being filled in, not a correction.
        # Two rules, both deliberate:
        #   * verdicts are NEVER touched. 9 of the 12 are 'does_not' -- deliberate classifications
        #     (a subsidiary permit on 3030 Telegraph among them). ADR-002 makes VERDICT the
        #     overwrite layer, but overwriting one here would be inventing a completion.
        #   * a permit_finaled EVENT is added only where the verdict is already 'completes',
        #     because that event is what v_projects_flat reads for co_issued_date.
        backfilled = events_added = 0
        for pid_, pn_, fd_, verdict_ in db.execute(
                """SELECT id, permit_number, finaled_date, completion_verdict FROM permits
                   WHERE permit_number IS NOT NULL""").fetchall():
            feed_fd = FEED_FINALED.get(pn_)
            if not feed_fd or (fd_ or "").strip():
                continue
            db.execute("UPDATE permits SET finaled_date=?, updated_at=? WHERE id=?",
                       (feed_fd, now, pid_))
            backfilled += 1
            if verdict_ == "completes":
                proj_ = db.execute("SELECT project_id FROM permits WHERE id=?", (pid_,)).fetchone()[0]
                dup = db.execute(
                    """SELECT 1 FROM project_events e JOIN vocabulary_event_types t
                       ON t.id = e.event_type_id
                       WHERE e.permit_id=? AND t.code='permit_finaled'""", (pid_,)).fetchone()
                if not dup:
                    db.execute(
                        """INSERT INTO project_events (project_id, event_type_id, event_date,
                           event_date_precision, permit_id, summary, confidence_type_id,
                           is_inferred, source_type, source_url, observed_by, observed_at, created_at)
                           VALUES (?,?,?,'exact',?,?,?,0,'document',?,?,?,?)""",
                        (proj_, V["ev_permit_finaled"], feed_fd, pid_,
                         f"BP {pn_} finaled (back-filled from the 2026 CPRA feed)",
                         V["conf_high"], SOURCE_URL, VERDICT_BY, now, now))
                    events_added += 1
                    made["project_events"] += 1
        print(f"back-filled finaled_date on {backfilled} existing permits "
              f"(+{events_added} permit_finaled events; verdicts untouched)")

        after = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in before}
        problems = []
        for t in before:
            delta = after[t] - before[t]
            if delta != made[t]:
                problems.append(f"{t}: delta {delta} != inserted {made[t]}")
        if made["permits"] != len(rows):
            problems.append(f"permits inserted {made['permits']} != planned {len(rows)}")
        orph = db.execute("SELECT COUNT(*) FROM permits WHERE project_id NOT IN (SELECT id FROM projects)").fetchone()[0]
        if orph:
            problems.append(f"{orph} orphaned permits")
        # Verify THIS RUN's rows, not a global invariant. v2 already carries 25 pre-existing
        # 'completes' permits with a NULL finaled_date (22 description_only, 3 evidentiary), so a
        # whole-table assertion is a FALSE-FAILURE generator -- it fails on correct new data
        # because of old data. Anchor the check to what this write is responsible for.
        qs = ",".join("?" * len(inserted_permit_ids))
        bad = db.execute(f"""SELECT COUNT(*) FROM permits WHERE id IN ({qs})
                             AND completion_verdict='completes' AND finaled_date IS NULL""",
                         inserted_permit_ids).fetchone()[0]
        if bad:
            problems.append(f"{bad} newly-inserted 'completes' permits with no finaled_date")
        nover = db.execute(f"""SELECT COUNT(*) FROM permits WHERE id IN ({qs})
                               AND finaled_date IS NOT NULL AND completion_verdict IS NULL""",
                           inserted_permit_ids).fetchone()[0]
        if nover:
            problems.append(f"{nover} newly-inserted finaled permits carrying no verdict")
        if problems:
            db.execute("ROLLBACK")
            print("\nROLLED BACK — verification failed:")
            for p in problems:
                print("   " + p)
            return 1
        db.execute("COMMIT")
        print("\nCOMMITTED")
        for t in before:
            print(f"  {t:<18} {before[t]:>6,} -> {after[t]:>6,}  (+{after[t]-before[t]:,})")
    except Exception:
        db.execute("ROLLBACK")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
