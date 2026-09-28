"""test_planning_record.py -- python -m scripts.housing_rules.test_planning_record"""
from scripts.housing_rules.planning_record import is_primary, milestones, role

CASES = [
    ("Zoning Permit", "primary_application"),
    ("Structural Alteration Permit", "companion_review"),   # LMSAP = Landmarks
    ("Zoning Certificate Building Permit", "ministerial_clearance"),
    ("Pre-Application", "pre_application"),
    ("Design Review Committee Preliminary", "companion_review"),
    ("Design Review Committee Final", "companion_review"),
    ("Landmarks Initiation", "companion_review"),
    ("Appeal", "companion_review"),
    ("Zoning Research Letter", "not_an_application"),
    ("  Zoning Permit  ", "primary_application"),      # whitespace tolerated
    ("Some New City Type", "unknown"),                  # surfaces as a gap, never bucketed
    (None, "unknown"),
    ("", "unknown"),
]


# ---- milestones(): real records from the 2026-09-26 CapDetail harvest; tasks as (task, status, date)
MILESTONE_CASES = [
    # ZP2021-0046: staff approval; appeal period and closing kept separate
    ('ZP2021-0046', '03/18/2021', [
        ('Completeness Review', 'Incomplete Pending Applicant', '2021-04-29'),
        ('Completeness Review', 'Application Complete', '2021-08-27'),
        ('CEQA Determination', 'EIR Required', '2021-08-27'),
        ('Staff Decision', 'Approved', '2024-03-28'),
        ('Appeal', 'No Appeal', '2024-05-22'),
        ('Hearing Notice', None, None),
        ('Public Hearing', None, None),
        ('Notice of Decision', None, None),
        ('Case Closed', 'Approved', '2024-05-22'),
    ], {'accepted': '2021-08-27', 'entitled': '2024-03-28', 'entitled_by': 'staff', 'flags': []}),
    # ZP2015-0043: appealed to Council, Council approved: Council date, not staff
    ('ZP2015-0043', '03/05/2015', [
        ('Completeness Review', 'Incomplete Pending Applicant', '2015-04-03'),
        ('Completeness Review', 'Resubmittal Pending Staff', '2015-05-26'),
        ('Completeness Review', 'Application Complete', '2015-06-04'),
        ('CEQA Determination', 'Categorically Exempt', '2016-04-21'),
        ('Staff Decision', 'Approved', '2016-06-09'),
        ('Appeal', 'Appeal to City Council', '2016-07-19'),
        ('Hearing Notice', 'Notice Issued', '2016-07-05'),
        ('Public Hearing', 'City Council Approved', '2016-07-16'),
        ('Notice of Decision', None, None),
        ('Case Closed', 'Approved', '2016-07-20'),
    ], {'accepted': '2015-06-04', 'entitled': '2016-07-16', 'entitled_by': 'city_council', 'flags': []}),
    # ZP2015-0087: ZAB approved, Council DENIED on appeal: denied, later "Approved" closing flagged
    ('ZP2015-0087', '04/08/2015', [
        ('Completeness Review', 'Application Complete', '2015-01-16'),
        ('CEQA Determination', 'Categorically Exempt', '2015-01-16'),
        ('Staff Decision', 'Approved', '2016-03-10'),
        ('Appeal', 'Appeal to City Council', '2016-04-04'),
        ('Appeal', 'Appeal to City Council', '2016-04-04'),
        ('Hearing Notice', 'Notice Issued', '2016-06-08'),
        ('Hearing Notice', 'Notice Issued', '2016-06-28'),
        ('Public Hearing', 'ZAB Approved', '2016-06-23'),
        ('Public Hearing', 'City Council Denied', '2016-07-12'),
        ('Notice of Decision', 'Notice Issued', '2016-03-21'),
        ('Case Closed', 'Denied', '2016-07-13'),
        ('Case Closed', 'Approved', '2017-12-05'),
    ], {'accepted': '2015-01-16', 'denied': '2016-07-12', 'denied_by': 'city_council', 'flags': ['accepted_before_filed', 'closed_approved_after_denial']}),
    # ZP2022-0109: approved with no acceptance mark: flagged
    ('ZP2022-0109', '08/17/2022', [
        ('Completeness Review', 'Incomplete Pending Applicant', '2022-10-11'),
        ('Completeness Review', 'Resubmittal Pending Staff', '2022-11-22'),
        ('Completeness Review', 'Incomplete Pending Applicant', '2022-12-09'),
        ('Completeness Review', 'Incomplete Pending Applicant', '2023-04-26'),
        ('Completeness Review', 'Resubmittal Pending Staff', '2023-06-02'),
        ('Completeness Review', 'Incomplete Pending Applicant', '2023-07-03'),
        ('CEQA Determination', 'Categorically Exempt', '2023-08-10'),
        ('Staff Decision', 'Approved', '2023-08-10'),
        ('Appeal', 'No Appeal', '2023-08-21'),
        ('Hearing Notice', None, None),
        ('Public Hearing', None, None),
        ('Notice of Decision', None, None),
        ('Case Closed', 'Approved', '2023-09-25'),
    ], {'entitled': '2023-08-10', 'entitled_by': 'staff', 'flags': ['entitled_without_acceptance']}),
    # ZP2015-0032: withdrawn before any decision
    ('ZP2015-0032', '02/17/2015', [
        ('Completeness Review', 'Incomplete Pending Applicant', '2015-03-04'),
        ('Completeness Review', 'Withdrawn', '2015-06-11'),
        ('CEQA Determination', None, None),
        ('Staff Decision', None, None),
        ('Appeal', None, None),
        ('Hearing Notice', None, None),
        ('Public Hearing', None, None),
        ('Notice of Decision', None, None),
        ('Case Closed', None, None),
    ], {'ended': '2015-06-11', 'flags': []}),
    # ZP2015-0240: several "Application Complete": the first is acceptance
    ('ZP2015-0240', '11/16/2015', [
        ('Completeness Review', 'Application Complete', '2016-05-12'),
        ('Completeness Review', 'Application Complete', '2016-05-13'),
        ('CEQA Determination', 'Categorically Exempt', '2016-05-12'),
        ('CEQA Determination', 'Categorically Exempt', '2016-05-12'),
        ('Staff Decision', 'Approved', '2016-05-16'),
        ('Appeal', 'No Appeal', '2016-06-06'),
        ('Hearing Notice', None, None),
        ('Public Hearing', None, None),
        ('Notice of Decision', None, None),
        ('Case Closed', 'Approved', '2016-06-07'),
    ], {'accepted': '2016-05-12', 'entitled': '2016-05-16', 'entitled_by': 'staff', 'flags': []}),
    # ZP2017-0047: accepted before filed: flagged, not corrected
    ('ZP2017-0047', '04/06/2017', [
        ('Completeness Review', 'Application Complete', '2017-02-04'),
        ('Completeness Review', 'Application Complete', '2017-07-10'),
        ('CEQA Determination', 'Categorically Exempt', '2017-02-04'),
        ('CEQA Determination', 'Categorically Exempt', '2017-08-01'),
        ('Staff Decision', 'Approved', '2017-07-27'),
        ('Staff Decision', 'Approved', '2017-08-21'),
        ('Appeal', 'No Appeal', '2017-08-16'),
        ('Hearing Notice', None, None),
        ('Public Hearing', None, None),
        ('Notice of Decision', None, None),
        ('Case Closed', 'Approved', '2018-08-17'),
    ], {'accepted': '2017-02-04', 'entitled': '2017-08-21', 'entitled_by': 'staff', 'flags': ['accepted_before_filed']}),
    # ZP2026-0039: heard by ZAB (staff decision Not Applicable): the ZAB date
    ('ZP2026-0039', '04/01/2026', [
        ('Completeness Review', 'Incomplete Pending Applicant', '2026-04-21'),
        ('Completeness Review', 'Resubmittal Pending Staff', '2026-05-01'),
        ('Completeness Review', 'Application Complete', '2026-05-06'),
        ('Application Processing', 'Pending Final Action', '2026-05-06'),
        ('CEQA Determination', 'Statutorily Exempt', '2026-04-03'),
        ('Staff Decision', 'Not Applicable', '2026-08-13'),
        ('Appeal', 'No Appeal', '2026-09-17'),
        ('Hearing Notice', 'Notice Issued', '2026-07-30'),
        ('Public Hearing', 'ZAB Approved', '2026-08-13'),
        ('Notice of Decision', 'Notice Issued', '2026-08-13'),
        ('Case Closed', 'Approved', '2026-09-17'),
    ], {'accepted': '2026-05-06', 'entitled': '2026-08-13', 'entitled_by': 'zab', 'flags': []}),
]


def main() -> int:
    bad = [(t, want, role(t)) for t, want in CASES if role(t) != want]
    assert is_primary("Zoning Permit")
    assert not is_primary("Design Review Committee Final")
    assert not is_primary("Zoning Research Letter")
    assert not is_primary("Structural Alteration Permit")
    for t, want, got in bad:
        print(f"  FAIL {t!r}: want {want}, got {got}")
    print(f"planning_record: {len(CASES)-len(bad)}/{len(CASES)} role cases pass"
          + (" + 3 is_primary assertions" if not bad else ""))
    mbad = []
    for record, listed, tasks, want in MILESTONE_CASES:
        rec = dict(record=record, record_type="Zoning Permit", list_date=listed,
                   processing_status=[dict(task=t, status=s, status_date=d) for t, s, d in tasks])
        m = milestones(rec)
        got = {k: m[k] for k in ("accepted", "entitled", "entitled_by", "denied", "denied_by", "ended") if m[k]}
        got["flags"] = m["flags"]
        if got != want:
            mbad.append(record)
            print(f"  FAIL milestones {record}: want {want}, got {got}")
    print(f"planning_record: {len(MILESTONE_CASES)-len(mbad)}/{len(MILESTONE_CASES)} milestone cases pass")
    return 1 if bad or mbad else 0


if __name__ == "__main__":
    raise SystemExit(main())
