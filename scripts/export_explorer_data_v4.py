#!/usr/bin/env python3
"""export_explorer_data_v4.py -- the Explorer's data (docs/explorer_data.js) from the canonical v4 database.

Cutover phase 6, step 4 (John, 2026-10-01: "start the Explorer re-point"). Replaces export_explorer_data_v2.py, which
reads v2. Same DATA shape, so docs/explorer.js changes only where v4 adds something (two stages, the v2-id crosswalk).
READ-ONLY on v4 (mode=ro). Reads v4's SERVING VIEWS (build_views.py) and never re-derives what a view already states;
the few Explorer-only fields (the inactive stages, the first inspection, the fee aggregates) are computed here from
v4 rows and each says how. Names: owner names are public record and published as v4 holds them (John, 2026-10-02: "show names").

Writes docs/explorer_data_v4_working.js. Promotion to the served docs/explorer_data.js is a separate, reviewed copy.

  .venv/bin/python scripts/export_explorer_data_v4.py
"""
from __future__ import annotations

import collections
import json
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))
from housing_rules.owner_name import is_organisation  # noqa: E402

DB_PATH = BASE_DIR / "databases" / "berkeley_housing_v4.db"
V2_PATH = BASE_DIR / "databases" / "berkeley_housing_v2.db"      # read ONLY for the old-link crosswalk
OUTPUT_PATH = BASE_DIR / "docs" / "explorer_data_v4_working.js"

TODAY = date.today()
CUT_6 = (TODAY - timedelta(days=183)).isoformat()
CUT_24 = (TODAY - timedelta(days=730)).isoformat()
CUT_36 = (TODAY - timedelta(days=1095)).isoformat()


def mask(name, label="individual owner"):
    """No masking: owner names are public record and published as v4 holds them (John, 2026-10-02: "show names"). Kept as the single place a future presentation rule would go."""
    return name


def money(s):
    return float(str(s).replace("$", "").replace(",", "")) if s else 0.0


def get_projects(db):
    """One Explorer row per v4 project (v_projects), the page's field names kept."""
    q = lambda sql, *a: db.execute(sql, a).fetchall()
    first_insp, last_insp = {}, {}
    for k, lo, hi in q("""SELECT json_extract(p.notes, '$.project_key'), MIN(e.event_date), MAX(e.event_date) FROM projects p
                          JOIN project_structures ps USING(project_id) JOIN structure_events se USING(structure_id)
                          JOIN events e USING(event_id) WHERE e.event_type_code = 'inspection' GROUP BY 1"""):
        first_insp[k], last_insp[k] = lo, hi
    permits = collections.defaultdict(list)
    for k, rec in q("""SELECT DISTINCT json_extract(p.notes, '$.project_key'), e.source_record_key FROM projects p
                       JOIN project_structures ps USING(project_id) JOIN structure_events se USING(structure_id)
                       JOIN events e USING(event_id) WHERE se.role_in_structure IN ('master', 'phase')
                       ORDER BY 2"""):
        permits[k].append(rec)
    submitted_only = {k for (k,) in q("""SELECT json_extract(p.notes, '$.project_key') FROM projects p
                       JOIN project_structures ps USING(project_id) JOIN structure_events se USING(structure_id)
                       JOIN events e USING(event_id) WHERE se.role_in_structure IN ('master', 'phase')
                       GROUP BY 1 HAVING SUM(e.event_type_code = 'permit_issued') = 0""")}
    demo = dict(q("""SELECT json_extract(p.notes, '$.project_key'), MIN(e.event_date) FROM projects p
                     JOIN project_structures ps USING(project_id) JOIN structure_events se USING(structure_id)
                     JOIN events e USING(event_id) JOIN event_classifications c USING(event_id)
                     WHERE c.housing_role = 'demolition' AND e.event_type_code = 'permit_issued' GROUP BY 1"""))
    desc = dict(q("""SELECT json_extract(p.notes, '$.project_key'),
                            COALESCE((SELECT json_extract(e.raw_payload, '$.description') FROM events e
                                      WHERE e.event_type_code = 'planning_filed'
                                        AND e.source_record_key = json_extract(p.notes, '$.anchor') LIMIT 1),
                                     (SELECT MAX(e.raw_description) FROM project_structures ps JOIN structures s USING(structure_id)
                                      JOIN events e ON e.event_id = s.master_event_id WHERE ps.project_id = p.project_id))
                     FROM projects p"""))
    apn = dict(q("""SELECT json_extract(p.notes, '$.project_key'), MIN(pi.apn_normalized) FROM projects p
                    JOIN project_parcels pp USING(project_id)
                    JOIN parcel_identifiers pi ON pi.parcel_id = pp.parcel_id AND pi.is_current = 1 GROUP BY 1"""))
    # ONE name per project and role: an ORGANISATION before a person (the firm, not the individual who signed), then
    # the name the records repeat most -- not the alphabetically first (which published "Isaiah Stackhouse" over
    # Trachtenberg Architects for 1974 Shattuck, 2026-10-02)
    people = collections.defaultdict(dict)
    cand = collections.defaultdict(collections.Counter)
    for k, role, name in q("""SELECT project_key, role, name FROM v_project_people
                              WHERE role IN ('developer', 'plans_developer', 'plans_architect', 'architect') AND name IS NOT NULL"""):
        cand[(k, role)][name.strip()] += 1
    for (k, role), c in cand.items():
        people[k][role] = sorted(c, key=lambda n: (not is_organisation(n), -c[n], n))[0]
    cur = db.execute("SELECT * FROM v_projects")
    cols = [d[0] for d in cur.description]
    out = []
    for row in cur.fetchall():
        v = dict(zip(cols, row))
        k = v["project_key"]
        units = (v["units_built_or_permitted"] or v["proposed_units"] or v["units_reported_by_source"] or 0)
        pw = set(json.loads(v["pathways"] or "[]"))
        st, ins = v["status"], first_insp.get(k)
        # THE PAGE'S STAGES, from v4's evidence-based status (D2) + the inactivity rules v2 used (2026-05-13):
        # a building permit unused 24 months with NO inspection, an entitlement 36 months with no permit.
        if st == "completed":
            stage = "Completed"
        elif st in ("under_construction", "stale"):
            # SPLIT by the City's own inspection record (John, 2026-10-03): active = inspected in the last 6 months;
            # quiet = inspected before, not since; never inspected = not started (inactive once the permit is 24
            # months old, the rule v2 used)
            last = last_insp.get(k)
            if k in submitted_only:
                stage = "Building Permits Filed"
            elif last and last >= CUT_6:
                stage = "Under Construction"
            elif last:
                stage = "Construction Quiet"
            elif v["bp_issued_date"] and v["bp_issued_date"] < CUT_24:
                stage = "Permitted but Inactive"
            else:
                stage = "Permitted, Not Started"
        elif st == "entitled":
            stage = "Entitled but Inactive" if (v["entitled_date"] or "9999") < CUT_36 else "Entitled"
        elif st == "in_review":
            stage = "Pre-Application" if v["anchor_role"] == "pre_application" else "Under Review"
        else:
            stage = {"withdrawn": "Withdrawn", "denied": "Denied", "void": "Expired",
                     "pre_application": "Pre-Application", "under_construction": "Under Construction",
                     "approved": "Entitled"}.get(st, str(st).replace("_", " ").title())
        filed, ent = v["filed_date"], v["entitled_date"]
        try:
            pdays = (date.fromisoformat(ent) - date.fromisoformat(filed)).days if filed and ent else None
        except ValueError:
            pdays = None
        fees = (v["fees_paid"] or 0) + (v["planning_fees_paid"] or 0)
        uc = bool(v["rhna_excluded"]) and (v["anchor_role"] == "outside_city_permitting" or
                                           "uc_" in (v["classifications"] or ""))
        out.append({
            # two City records carry no address at all (the place is only in their prose); never invented
            "id": k, "address": v["address_display"] or f"{k} (no address on the City record)",
            "name": v["name"], "apn": apn.get(k),
            "owner": mask(v["owner_current"]), "units": units, "new_units": units, "old_units": 0,
            "status": stage, "pipeline_stage": st, "accela_status": stage, "accela_status_date": None,
            "year": filed[:4] if filed else None, "permits": ",".join(permits.get(k, [])),
            "num_permits": len(permits.get(k, [])), "description": desc.get(k),
            "project_size": "Large" if units >= 50 else "Medium" if units >= 10 else "Small",
            "latitude": v["latitude"], "longitude": v["longitude"], "unit_category": None, "tenure": None,
            "eli_units": v["eli_units"] or 0, "vli_units": v["vli_units"] or 0, "li_units": v["li_units"] or 0,
            "mod_units": v["mod_units"] or 0, "market_units": v["market_units"],
            "density_bonus": "density_bonus" in pw, "density_bonus_pct": None,
            "sb330": any(p.startswith("sb330") for p in pw), "sb35": any(p.startswith("sb35") for p in pw),
            "ab2011": "ab2011" in pw,
            "app_filed": filed, "app_complete": v["accepted_date"], "entitled": ent,
            "bp_issued": v["bp_issued_date"], "co_date": v["co_issued_date"], "first_co_date": v["first_co_date"],
            # assessed values for COMPLETED projects only, as the page states ("completed housing") and v2 exported:
            # a parcel's value before or during construction is not the new housing's value
            **({"assessed_value": v["assessed_value"], "assessed_net_taxable": v["assessed_net_taxable"],
                "est_annual_tax": v["est_annual_tax_1pct_rule"], "assessed_as_of_date": v["assessed_as_of_date"],
                "assessed_tax_exempt": v["assessed_value"] is not None and v["assessed_net_taxable"] == 0}
               if stage == "Completed" and v["co_issued_date"] else
               {"assessed_value": None, "assessed_net_taxable": None, "est_annual_tax": None,
                "assessed_as_of_date": None, "assessed_tax_exempt": False}),
            "assessed_exemption": None,
            "construction_start": ins, "last_inspection": last_insp.get(k), "construction_status": None, "estimated_completion": None,
            "processing_days": pdays, "height_stories": v["height_stories"], "height_feet": v["height_feet"],
            "app_packet_mb": 0, "total_fees": fees, "fee_per_unit": (fees / units) if units else 0,
            "building_fees": v["fees_paid"] or 0, "planning_fees": v["planning_fees_paid"] or 0,
            "fee_count": 0, "permit_type": "Unknown", "construction_data_reliability": "Unknown",
            "is_uc_project": uc, "is_stalled": False,
            "developer": people[k].get("developer") or people[k].get("plans_developer"),
            "architect": people[k].get("plans_architect") or people[k].get("architect"),
            "planning_applicant": mask(v["planning_applicant"], "individual"),
            "field_survey_date": None, "field_survey_notes": None,
            "demolition_permit_date": demo.get(k), "demolition_start_date": None, "construction_substage": None,
            "beds": v["beds"], "source_confidence": v["source_confidence"], "anchor_record": v["anchor_record"],
            "anchor_role": v["anchor_role"],
        })
    out.sort(key=lambda p: -(p["units"] or 0))
    return out


def get_events(db, addr):
    """Planning records filed, their dated review tasks (who marked them), and the building permits' milestones,
    per project -- v_project_timeline plus the task payloads. Inspections are not listed one by one (47k); the
    first one is each project's construction_start."""
    ev = []
    for k, rec, role, typ, d, desc in db.execute("SELECT * FROM v_project_timeline"):
        if typ == "planning_task":
            continue
        label = {"planning_filed": "Application filed", "permit_submitted": "Building permit submitted",
                 "permit_issued": "Building permit issued", "permit_finaled": "Building permit finaled",
                 "permit_completed": "Building permit completed"}.get(typ, typ)
        ev.append({"project_id": k, "address": addr.get(k), "permit": rec, "stage": "Permit" if typ.startswith("permit")
                   else "Application", "type": f"{label}: {rec}", "date": d, "assigned_to": None, "staff": None,
                   "comment": (desc or "")[:300], "status": None, "permit_type": role})
    for k, rec, pl in db.execute("""SELECT json_extract(p.notes, '$.project_key'), e.source_record_key, e.raw_payload
                                    FROM projects p JOIN project_records pr USING(project_id)
                                    JOIN events e ON e.source_record_key = pr.record_key AND e.event_type_code = 'planning_task'"""):
        t = json.loads(pl)
        ev.append({"project_id": k, "address": addr.get(k), "permit": rec, "stage": "Review",
                   "type": f"{t.get('task')}: {t.get('status')}", "date": t.get("status_date"),
                   "assigned_to": t.get("assigned_to"), "staff": t.get("status_by"), "comment": t.get("comment") or "",
                   "status": t.get("status"), "permit_type": t.get("record_type")})
    ev.sort(key=lambda e: e["date"] or "", reverse=True)
    return ev


def get_fees(db, projects):
    """The City's own fee totals (CapDetail Fees tab): building permits and Planning records, per project. by_year is
    by the year the fee page was RETRIEVED is meaningless, so it is by the project's first building-permit year
    (building fees) -- labelled in by_year_basis."""
    total = sum(p["total_fees"] for p in projects)
    rows = db.execute("SELECT e.source_record_key, e.raw_payload FROM events e WHERE e.event_type_code = 'fees_recorded'").fetchall()
    all_paid = sum(money(json.loads(pl).get("total_paid")) for _, pl in rows)
    by_year = collections.Counter()
    for p in projects:
        if p["building_fees"] and p["bp_issued"]:
            by_year[p["bp_issued"][:4]] += p["building_fees"]
    by_project = dict(sorted(((p["address"], p["total_fees"]) for p in projects if p["total_fees"]),
                             key=lambda x: -x[1])[:20])
    addr = {}
    for k, rec in db.execute("""SELECT json_extract(p.notes, '$.project_key'), pr.record_key FROM projects p
                                JOIN project_records pr USING(project_id)
                                UNION SELECT json_extract(p.notes, '$.project_key'), e.source_record_key FROM projects p
                                JOIN project_structures ps USING(project_id) JOIN structure_events se USING(structure_id)
                                JOIN events e USING(event_id) WHERE se.role_in_structure IN ('master', 'phase')"""):
        addr[rec] = next((p["address"] for p in projects if p["id"] == k), None)
    large = sorted(({"address": addr.get(rec, "(unattributed)"), "description": f"total paid on {rec}",
                     "amount": money(json.loads(pl).get("total_paid")), "date": None}
                    for rec, pl in rows if money(json.loads(pl).get("total_paid")) >= 100000), key=lambda x: -x["amount"])
    units = sum(p["units"] or 0 for p in projects if p["total_fees"])
    return {"total": total, "linked": total, "unlinked": all_paid - total, "count": len(rows),
            "permit_count": len(rows), "by_year": dict(sorted(by_year.items())),
            "by_year_basis": "building-permit fees by the year the project's first building permit was issued",
            "by_project": by_project, "large_fees": large, "avg_per_unit": total / units if units else 0}


def get_staff(db):
    """City staff who marked review tasks on the projects' Planning records, as the records name them."""
    rows = db.execute("""SELECT name, COUNT(*), COUNT(DISTINCT project_key) FROM v_project_people
                         WHERE role = 'city_reviewer' AND name NOT IN ('', 'TBD') GROUP BY name ORDER BY 2 DESC""").fetchall()
    return [{"name": n, "actions": a, "projects": p} for n, a, p in rows]


def get_players(projects, db):
    """Developers (CTCAC / plans), architects (plans' title blocks), owners of record (organisations only)."""
    agg = {r: collections.defaultdict(lambda: {"projects": [], "total_units": 0, "total_fees": 0})
           for r in ("developers", "architects", "owners")}
    for p in projects:
        for r, name in (("developers", p["developer"]), ("architects", p["architect"]),
                        ("owners", p["owner"])):
            if name:
                a = agg[r][name]
                a["projects"].append(p["address"]); a["total_units"] += p["units"] or 0; a["total_fees"] += p["total_fees"]
    return {r: sorted(({"name": n, **v} for n, v in d.items()), key=lambda x: -x["total_units"]) for r, d in agg.items()}


def get_timeline(projects):
    m = collections.defaultdict(lambda: [0, 0])
    for p in projects:
        if p["app_filed"]:
            m[p["app_filed"][:7]][0] += 1; m[p["app_filed"][:7]][1] += p["units"] or 0
    return [{"month": k, "applications": a, "units": u} for k, (a, u) in sorted(m.items())]


def get_documents(db):
    """Files held in R2 (with URL and SHA-256) and the City's attachment lists (title + upload date; not held)."""
    docs = [{"id": f"d{d}", "project_id": k, "title": t, "filename": t, "url": u, "type": typ, "source": "r2",
             "date_added": dd, "notes": None}
            for d, k, t, u, typ, dd in db.execute("""SELECT DISTINCT d.document_id, json_extract(p.notes, '$.project_key'),
                       d.title, d.store_url, d.doc_type, d.doc_date FROM projects p JOIN project_records pr USING(project_id)
                       JOIN documents d ON d.record_key = pr.record_key""")]
    docs += [{"id": f"a{i}", "project_id": k, "title": f, "filename": f, "url": None, "type": "attachment_listed",
              "source": f"Accela attachment list ({rec})", "date_added": up, "notes": f"{size}; listed by the City, not held"}
             for i, (k, rec, up, f, size) in enumerate(db.execute("SELECT * FROM v_project_attachments"))]
    return docs


def get_city_apr(db, projects):
    """Our completions vs the City's filed APR completions (HCD mirror = VERIFICATION TARGET, never a source), matched
    current APN -> former APN (County lineage) -> address. CO <-> CO only. Same buckets as the v2 serving projection."""
    from housing_rules import to_canonical_apn
    from housing_rules.address import normalize_address
    mirror_path = BASE_DIR / "databases" / "hcd_apr_mirror.db"
    if not mirror_path.exists():
        return [], {"available": False, "reason": "mirror not present"}

    def canon(a):
        try:
            return to_canonical_apn(a, "Alameda")
        except Exception:
            return None

    def ak(a):
        try:
            h, s = normalize_address(a)
            return f"{h}|{s}" if h and s else None
        except Exception:
            return None
    # a project ENTERS the comparison when its FIRST building completed (v4 first_co_date): the City files each
    # building as it gets its certificate, while v4's co_date is the LAST building's (D3) -- using it dropped every
    # project still finishing a later building out of the window (202 City rows, 2026-10-01)
    # the comparison window is the MIRROR'S OWN last filed year (read, never a constant: a hard-coded 2024 dropped
    # the City's 2025 filings out of the match, 2026-10-01)
    _m = sqlite3.connect(f"file:{mirror_path}?mode=ro", uri=True)
    last_year = _m.execute("SELECT MAX(YEAR) FROM table_a2 WHERE JURIS_NAME LIKE '%erkeley%' AND CO_ISSUE_DT1 > ''").fetchone()[0]
    _m.close()
    ours = {p["id"]: p for p in projects if p["first_co_date"] and p["first_co_date"][:4] <= str(last_year)
            and not p["is_uc_project"]}
    by_apn, by_addr = {}, {}
    for k, a, cur in db.execute("""SELECT json_extract(p.notes, '$.project_key'), pi.apn_normalized, pi.is_current
                                   FROM projects p JOIN project_parcels pp USING(project_id)
                                   JOIN parcel_identifiers pi ON pi.parcel_id = pp.parcel_id"""):
        if k in ours and a:
            by_apn.setdefault(a, k) if cur else by_apn.setdefault(a, k)
    for k, p in ours.items():
        if ak(p["address"]):
            by_addr[ak(p["address"])] = k
    # every address the project's BUILDINGS carry (permit addresses + ruled aliases) and its parcels' County situs:
    # the City files a multi-building project under each building's own address (Acheson: 2111 / 2131 University)
    for k, norm in db.execute("""SELECT json_extract(p.notes, '$.project_key'), a.normalized FROM projects p
                                 JOIN project_structures ps USING(project_id) JOIN structure_addresses sa USING(structure_id)
                                 JOIN addresses a USING(address_id)
                                 UNION SELECT json_extract(p.notes, '$.project_key'), a.normalized FROM projects p
                                 JOIN project_parcels pp USING(project_id) JOIN parcel_addresses pa USING(parcel_id)
                                 JOIN addresses a USING(address_id)"""):
        if k in ours:
            by_addr.setdefault(norm, k)
    CO = ["CO_VLOW_INCOME_DR", "CO_VLOW_INCOME_NDR", "CO_LOW_INCOME_DR", "CO_LOW_INCOME_NDR", "CO_MOD_INCOME_DR",
          "CO_MOD_INCOME_NDR", "CO_ABOVE_MOD_INCOME", "CO_EXTREMELY_LOW_INCOME_DR", "CO_EXTREMELY_INCOME_NDR"]
    m = sqlite3.connect(f"file:{mirror_path}?mode=ro", uri=True)
    num = lambda x: float(x or 0) if str(x or "0").replace(".", "", 1).isdigit() else 0.0
    city = [{"apn": canon(a), "address": ad, "units": sum(num(c) for c in cs)}
            for a, ad, d, *cs in m.execute(f"SELECT APN, STREET_ADDRESS, CO_ISSUE_DT1, {','.join(CO)} FROM table_a2 "
                                           "WHERE JURIS_NAME LIKE '%erkeley%' AND CO_ISSUE_DT1 > ''")]
    pulled = m.execute("SELECT MAX(pulled_at) FROM _pull_metadata").fetchone()[0]
    y0, y1 = m.execute("SELECT MIN(YEAR), MAX(YEAR) FROM table_a2 WHERE CO_ISSUE_DT1 > ''").fetchone()
    m.close()
    hit, only = collections.defaultdict(list), []
    for r in city:
        k = by_apn.get(r["apn"]) or (by_addr.get(ak(r["address"])) if r["address"] else None)
        (hit[k].append(r) if k else only.append(r))
    rows = [{"address": ours[k]["address"], "units": round(sum(r["units"] for r in rs)), "our_units": ours[k]["units"],
             "matched": True, "bucket": "matched", "status": ours[k]["status"], "city_rows": len(rs)} for k, rs in hit.items()]
    rows += [{"address": p["address"], "units": 0, "our_units": p["units"], "matched": False, "bucket": "ours_only",
              "status": p["status"], "city_rows": 0} for k, p in ours.items() if k not in hit]
    rows += [{"address": (r["address"] or "").split(",")[0], "units": round(r["units"]), "our_units": None,
              "matched": False, "bucket": "city_only", "status": "In the city's filing only", "city_rows": 1} for r in only]
    mt = [r for r in rows if r["bucket"] == "matched"]
    oo = [r for r in rows if r["bucket"] == "ours_only"]
    co = [r for r in rows if r["bucket"] == "city_only"]
    return rows, {"available": True, "milestone": "certificate of occupancy", "years": f"{y0}–{y1}", "mirror_pulled": pulled,
                  "matched_projects": len(mt), "ours_only_projects": len(oo), "ours_only_units": sum(r["our_units"] for r in oo),
                  "city_only_rows": len(co), "city_only_units": sum(r["units"] for r in co),
                  "city_rows_folded": sum(r["city_rows"] for r in mt), "multi_row_projects": len([r for r in mt if r["city_rows"] > 1]),
                  "match_rate": round(100.0 * len(mt) / len(rows), 1) if rows else 0.0,
                  "our_units": sum(p["units"] for p in ours.values()), "city_units": round(sum(r["units"] for r in city))}


def v2_crosswalk(projects):
    """Old deep links (explorer.html?project=<v2 id>) keep working: v2 project id -> v4 project_key, matched by a
    shared permit / Planning record, else the address canon. Unmatched v2 ids are simply absent."""
    if not V2_PATH.exists():
        return {}
    from housing_rules.address import normalize_address

    def ak(a):
        try:
            h, s = normalize_address(a)
            return f"{h}|{s}" if h and s else None
        except Exception:
            return None
    by_rec, by_addr = {}, {}
    for p in projects:
        for r in [x for x in (p["permits"] or "").split(",") if x] + ([p["anchor_record"]] if p["anchor_record"] else []):
            by_rec.setdefault(r, p["id"])
        if ak(p["address"]):
            by_addr.setdefault(ak(p["address"]), p["id"])
    v2 = sqlite3.connect(f"file:{V2_PATH}?mode=ro", uri=True)
    recs = collections.defaultdict(list)
    for pid, pn in v2.execute("SELECT project_id, permit_number FROM permits"):
        recs[pid].append(pn)
    out = {}
    for pid, addr in v2.execute("SELECT project_id, address_display FROM v_projects_flat"):
        k = next((by_rec[r] for r in recs[pid] if r in by_rec), None) or by_addr.get(ak(addr))
        if k:
            out[str(pid)] = k
    v2.close()
    return out


def rhna_progress():
    """The APR generator's own Table B (data/apr), exactly as export_explorer_data_v2 reads it (restored 2026-10-01)."""
    yrs = sorted(int(p.parent.name) for p in (BASE_DIR / "data/apr").glob("20*/apr_20*.json") if p.parent.name.isdigit())
    cur = datetime.now().year
    full = max(y for y in yrs if y < cur)
    tb = lambda y: json.loads((BASE_DIR / "data/apr" / str(y) / f"apr_{y}.json").read_text())
    d = tb(full)
    rp = {"through_year": full, "income_levels": d["table_b"]["income_levels"], "summary": d["table_b"]["summary"],
          "generated": d.get("generated"), "source": f"data/apr/{full}/apr_{full}.json (scripts/generate_apr_v4.py)"}
    if cur in yrs:
        s = tb(cur)["table_b"]["summary"]
        rp["to_date"] = {"year": cur, "permitted": s["total_permitted"], "percent_of_goal": s["percent_of_goal"]}
    return rp


def main() -> int:
    from scripts.housing_rules import RHNA_ALLOCATIONS
    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    projects = get_projects(db)
    addr = {p["id"]: p["address"] for p in projects}
    events = get_events(db, addr)
    fees = get_fees(db, projects)
    city_apr, city_meta = get_city_apr(db, projects)
    data = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "projects": projects, "events": events, "fees": fees, "staff": get_staff(db),
        "players": get_players(projects, db), "timeline": get_timeline(projects), "documents": get_documents(db),
        "rhna": dict(RHNA_ALLOCATIONS["6th"]), "rhna_progress": rhna_progress(),
        "city_apr": city_apr, "city_apr_meta": city_meta, "v2_ids": v2_crosswalk(projects),
        "meta": {"generated": datetime.now().isoformat(), "export_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                 "source": "berkeley_housing_v4.db (serving views)", "project_count": len(projects),
                 "event_count": len(events), "total_units": sum(p["units"] or 0 for p in projects),
                 "total_fees": fees["total"], "linked_fees": fees["linked"], "unlinked_fees": fees["unlinked"]},
    }
    db.close()
    header = (f"// Berkeley Housing Explorer data -- Generated: {data['meta']['generated']}\n"
              f"// Source: databases/berkeley_housing_v4.db via scripts/export_explorer_data_v4.py\n"
              f"// DO NOT EDIT MANUALLY\n")
    OUTPUT_PATH.write_text(header + "const DATA = " + json.dumps(data, default=str) + ";\n")
    print(f"projects {len(projects):,} · events {len(events):,} · documents {len(data['documents']):,} · staff "
          f"{len(data['staff'])} · fees ${fees['total']:,.0f} · v2 ids mapped {len(data['v2_ids']):,}")
    print(f"wrote {OUTPUT_PATH.relative_to(BASE_DIR)} (NOT served; promote after review)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
