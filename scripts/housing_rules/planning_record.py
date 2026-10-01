"""planning_record.py -- what ROLE a Berkeley Accela Planning record plays in the pipeline.

Lives here, not in a caller, because more than one consumer needs it (the CapDetail harvest's
rung-3 selection, and any later entitlement-event ingest) and CLAUDE.md's standing rule is one
canonical implementation, never a per-script copy.

WHY A ROLE AND NOT A DATE RULE. A project has many Planning records and EACH has its own
Completeness Review, so "when was this project's application accepted" cannot be answered by
reducing over all of them -- an extremum promotes one record's action to speak for the project
(MAX picks the latest companion review, MIN picks whatever came first at the address, possibly a
prior project's). The date must be SELECTED from the record that actually is the project's
application, which requires knowing which record that is. See
docs/methodology/identity_is_the_product.md.

ROLES
  primary_application  the discretionary land-use application whose approval IS the entitlement.
  ministerial_clearance a by-right zoning sign-off attached to a building permit, not a discretionary
                       approval -- a different rung, and the one the by-right reforms are moving work
                       INTO (docs/methodology/seven_rungs_and_the_ministerial_shift.md).
  pre_application      SB330-style preliminary filing; precedes the application, does not replace it.
  companion_review     design review, landmarks, appeal -- real city actions on the same project,
                       each with its own completeness review, none of which is the application.
  not_an_application   a zoning research letter is an INQUIRY. 65 of them pass an address+housing-
                       language filter while representing no application at all; counting one as a
                       filing would invent a project.
  unknown              an unrecognised type. Returned rather than guessed, so a new city record type
                       surfaces as a gap instead of being silently bucketed.
"""
import datetime as _dt
import re as _re

RECORD_ROLES = {
    "Zoning Permit": "primary_application",
    # "Structural Alteration Permit" is a COMPANION approval, not an entitlement, despite a name
    # that reads like a permit in its own right: every one of the 18 in the 2026-09-26 harvest
    # carries the LMSAP prefix -- Landmarks Structural Alteration Permit, a Landmarks Preservation
    # Commission approval for work on a designated landmark. Mapping it to primary_application
    # selected LMSAP2024-0003 as proj129's application and would have written the Landmarks
    # completeness review as the project's acceptance date.
    "Structural Alteration Permit": "companion_review",
    "Zoning Certificate Building Permit": "ministerial_clearance",
    "Zoning Certificate Accessory Dwelling Units": "ministerial_clearance",
    "Pre-Application": "pre_application",
    "Design Review Committee Preliminary": "companion_review",
    "Design Review Committee Final": "companion_review",
    "MOD Design Review committee Preliminary": "companion_review",
    "Design Review Staff Level": "companion_review",
    "Design Review Signs and Awnings": "companion_review",
    "Landmarks Initiation": "companion_review",
    "Landmarks Signs and Awnings": "companion_review",
    "Landmarks Mills Act Contracts": "companion_review",
    "Appeal": "companion_review",
    "Condo Conversion Parcel Map": "companion_review",
    "Condo Conversion Tract Map": "companion_review",
    "Condo Conversion Local Law Compliance": "companion_review",
    "Zoning Research Letter": "not_an_application",
    "Development-Related Fee Calculations": "not_an_application",
    # ---- PRE-2015 record-type names (the older hierarchical taxonomy), approved by John 2026-09-30. Each takes the
    # role of its current-era equivalent, checked against its record-number prefix (every type maps to ONE prefix
    # in the 2006-2014 sweep: UP, AUP, MODUP, MODAUP, ZCBP, DRSL, DRSA, DRCP, DRCF, LMSAP, LMIN, PLN).
    # Business licenses (ZCBL) and home occupations (ZCHO) are deliberately NOT listed: they are not development
    # applications, and 'unknown' keeps them out of projects.
    "Planning/Use Permit/Standard/NA": "primary_application",
    "Use Permit Standard": "primary_application",
    "Planning/Administrative Use Permit/NA/NA": "primary_application",
    "Administrative Use Permit": "primary_application",
    # modifications: capdetail_select's chain rule makes each a CHILD of the permit it modifies
    "Planning/MOD/Use Permit/Standard": "primary_application",
    "MOD Use Permit Standard": "primary_application",
    "Planning/MOD/Administrative Use Permit/NA": "primary_application",
    "MOD Administrative Use Permit": "primary_application",
    "Planning/Zoning Certificate/Building Permit/NA": "ministerial_clearance",
    "Planning/Design Review/Staff Level/NA": "companion_review",
    "Planning/Design Review/Signs/NA": "companion_review",
    "Planning/Design Review/Committee/Preliminary": "companion_review",
    "Planning/Design Review/Committee/Final": "companion_review",
    "Planning/Landmarks/SAP/NA": "companion_review",
    "Planning/Landmarks/Initiation/NA": "companion_review",
    "Planning/Special Request/Appeal/NA": "companion_review",
    "Planning/Application/Subdivision/NA": "companion_review",
    "Planning/Special Request/Zoning Research/NA": "not_an_application",
    # a request for a MEETING, not an SB 330 preliminary application (John approved the call, 2026-09-30)
    "Planning/Special Request/PreApplication Meeting/NA": "not_an_application",
}


def role(record_type: str | None) -> str:
    """The record's pipeline role. Unrecognised types return 'unknown', never a guess."""
    return RECORD_ROLES.get((record_type or "").strip(), "unknown")


def in_reading_corpus(record_type: str | None) -> bool:
    """Is this Planning record one the scope reading should read? Any record whose TYPE has a known role -- an
    exact table lookup on the city's own record-type field, never a pattern over the record number (John,
    2026-09-30: the DEV prefix regex it replaces missed 127 records, 18 of them ADU clearances). Zoning research
    letters ARE read: some applications were filed under that type (2001 Ashby's SB 35 application, PLN2019-0059).
    Unknown types (business licenses, home occupations, rezonings, plan amendments) are not."""
    return role(record_type) != "unknown"


def is_primary(record_type: str | None) -> bool:
    return role(record_type) == "primary_application"


# ---------------------------------------------------------------- MILESTONES of one Planning record
# John approved 2026-09-28 ("approve the milestone rule"), from the city's own Processing Status on the
# 1,116 primary applications harvested 2026-09-26:
#   ACCEPTED = the FIRST dated "Application Complete" on the Completeness Review (or intake) task; later ones
#              are resubmittals after changes.
#   ENTITLED = the ruling of the HIGHEST body that ruled: City Council, else ZAB, else staff. When a hearing was
#              held, the earlier "Staff Decision -> Approved" is not the approval. If that body's last ruling is a
#              denial, the record is DENIED, not entitled.
#   The end of the appeal period ("No Appeal") and the case closing are kept as separate dates, never used as
#   the entitlement date. Date-order anomalies are FLAGGED as the city recorded them, never corrected.
# Stage MEANING belongs to primary applications (role above); which application speaks for a PROJECT is a
# separate selection (scripts/capdetail_select.py), never an aggregate over records.
# "Complete" is the PRE-2015 wording of the same acceptance (John, 2026-09-30): 342 of the 380 old records carrying it
# date it on a day other than the case closing, so it is the city's acceptance, not the workflow shutting down.
ACCEPTED = _re.compile(r"^(application )?complete$", _re.I)
ACCEPT_TASK = _re.compile(r"completeness review|intake", _re.I)
DECIDING_BODIES = (   # highest first: (body, task, approved status, denied status)
    ("city_council", "Public Hearing", "City Council Approved", "City Council Denied"),
    ("zab", "Public Hearing", "ZAB Approved", "ZAB Denied"),
    ("staff", "Staff Decision", "Approved", "Denied"),
)
ENDED = ("Withdrawn", "Void")

# PRE-2015 WORKFLOW WORDING (John, 2026-09-30). The 2006-2014 records name their hearings "ZAB Meeting" / "ZAB 1st
# Meeting" / "ZAB 2nd Meeting" and their rulings "Approved", "Approved with Changes" or "Project Approved"; read
# with regexes over the city's own task labels (machine form), never over prose.
OLD_ZAB_TASK = r"^ZAB( 1st| 2nd)? Meeting$"
OLD_ZAB_OK = r"Approved|Approved with Changes|Project Approved"
OLD_ZAB_NO = r"Denied"
# Decision tasks whose status says only "Completed": the DATE is the decision task's, the OUTCOME is the case closing's
# (Approved / Denied). The closing never supplies the date (the 2026-09-28 rule keeps closing a separate date).
OLD_COMPLETED_DECISIONS = (("zab", r"^ZAB( 1st| 2nd)? Meeting$"),
                           ("staff", r"^Prepare Notice of Administrative Decision$"))


def _dated(rec, task_re, status_re):
    return sorted(t["status_date"] for t in (rec.get("processing_status") or [])
                  if t.get("status_date") and _re.search(task_re, t.get("task") or "", _re.I)
                  and _re.fullmatch(status_re, (t.get("status") or "").strip(), _re.I))


def milestones(rec: dict) -> dict:
    """-> dict(role, filed, accepted, entitled, entitled_by, denied, denied_by, no_appeal, closed,
    closed_status, ended, ended_status, flags) for one parsed CapDetail Planning record."""
    filed = None
    if rec.get("list_date"):
        filed = _dt.datetime.strptime(rec["list_date"], "%m/%d/%Y").date().isoformat()
    acc = sorted(t["status_date"] for t in (rec.get("processing_status") or [])
                 if t.get("status_date") and ACCEPTED.search((t.get("status") or "").strip())
                 and ACCEPT_TASK.search(t.get("task") or ""))
    out = dict(role=role(rec.get("record_type")), filed=filed, accepted=acc[0] if acc else None,
               entitled=None, entitled_by=None, denied=None, denied_by=None,
               no_appeal=None, closed=None, closed_status=None, ended=None, ended_status=None, flags=[])
    for body, task, ok, no in DECIDING_BODIES:
        rulings = sorted([(d, "approved") for d in _dated(rec, _re.escape(task), _re.escape(ok))] +
                         [(d, "denied") for d in _dated(rec, _re.escape(task), _re.escape(no))])
        if rulings:
            day, outcome = rulings[-1]
            if outcome == "approved":
                out["entitled"], out["entitled_by"] = day, body
            else:
                out["denied"], out["denied_by"] = day, body
            break
    if not out["entitled"] and not out["denied"]:                       # pre-2015 wording
        ok = _dated(rec, OLD_ZAB_TASK, OLD_ZAB_OK)
        no = _dated(rec, OLD_ZAB_TASK, OLD_ZAB_NO)
        rulings = sorted([(d, "approved") for d in ok] + [(d, "denied") for d in no])
        if rulings:
            day, outcome = rulings[-1]
            out["entitled" if outcome == "approved" else "denied"] = day
            out["entitled_by" if outcome == "approved" else "denied_by"] = "zab"
        else:
            closing = sorted((t["status_date"], (t.get("status") or "").strip()) for t in (rec.get("processing_status") or [])
                             if t.get("status_date") and (t.get("task") or "").strip().lower() == "case closed"
                             and (t.get("status") or "").strip() in ("Approved", "Denied"))
            if closing:
                outcome = closing[-1][1]
                for body, task in OLD_COMPLETED_DECISIONS:
                    days = _dated(rec, task, r"Completed")
                    if days:
                        key = "entitled" if outcome == "Approved" else "denied"
                        out[key], out[key + "_by"] = days[-1], body
                        out["flags"].append("outcome_from_case_closing")
                        break
    na = _dated(rec, r"^appeal$", r"No Appeal")
    out["no_appeal"] = na[-1] if na else None
    closings = sorted((t["status_date"], (t.get("status") or "").strip()) for t in (rec.get("processing_status") or [])
                      if t.get("status_date") and (t.get("task") or "").strip().lower() == "case closed")
    if closings:
        out["closed"], out["closed_status"] = closings[-1]
    ends = sorted((t["status_date"], t["status"].strip()) for t in (rec.get("processing_status") or [])
                  if t.get("status_date") and (t.get("status") or "").strip() in ENDED)
    if ends:
        out["ended"], out["ended_status"] = ends[0]
    f = out["flags"]
    if out["accepted"] and filed and out["accepted"] < filed:
        f.append("accepted_before_filed")
    decided = out["entitled"] or out["denied"]
    if decided and out["accepted"] and decided < out["accepted"]:
        f.append("decided_before_accepted")
    if out["entitled"] and not out["accepted"]:
        f.append("entitled_without_acceptance")
    if out["accepted"] and any(t.get("status_date") == out["accepted"] and (t.get("task") or "").strip().lower() == "case closed"
                               for t in (rec.get("processing_status") or [])):
        f.append("accepted_same_day_as_closing")
    if out["denied"] and out["closed_status"] == "Approved":
        f.append("closed_approved_after_denial")
    if out["entitled"] and out["ended"]:
        f.append("ended_after_or_despite_entitlement")
    return out
