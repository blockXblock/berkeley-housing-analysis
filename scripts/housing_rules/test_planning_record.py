"""test_planning_record.py -- python -m scripts.housing_rules.test_planning_record"""
from scripts.housing_rules.planning_record import is_primary, role

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
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
