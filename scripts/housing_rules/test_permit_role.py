"""Anchored unit tests for scripts.housing_rules.permit_role. Run as:

    python -m scripts.housing_rules.test_permit_role

Mandatory: this file must pass before any notebook/script integration. These are the SAME 16
vocabulary cases + 9 deflation (net_units) cases that were pinned inside build_jn_c's test cell —
each anchored to a specific real prior-research case (2641 College siding -> alteration; Durant
temp-power@83 -> ambiguous; ADU conversions/legalizations -> new_unit; ADU-flagged kitchen remodel
with no ADU language -> ambiguous (the dirty-flag case); movable homes with/without permanence
markers; the deflation blank-count cases). Lifted verbatim with the classifier (June-7 architecture).
"""
try:  # dual-path: `python -m scripts.housing_rules.test_permit_role` (from repo root) OR scripts/ on sys.path
    from scripts.housing_rules.permit_role import classify, net_units
except ImportError:
    from housing_rules.permit_role import classify, net_units

# (work_type, description, adu_flag, occtype, units_added, units_removed, permit) -> expected_role
TESTS = [
  ("New","Construct a one-story single-family dwelling on a vacant lot","No","R-3","1","0","B2025-00820","new_unit"),
  ("New","Building new Single Family Residence (see PV solar permit)","No","R-3","1","0","B2024-02570","new_unit"),
  ("New","New construction of 5-story residential apartment. Shoring under separate permit","No","R-2","50","0","B2023-02354","new_unit"),
  ("Alteration","Replace 760 sq ft of deteriorated siding on the existing two story main residence","No","R-3","0","0","B2025-02413","alteration"),
  ("Alteration","Re-roof existing single family residence","No","R-3","0","0","B2024-09999","alteration"),
  ("Other","Temporary power pole for construction staging","No","","83","0","B2020-DURANT","ambiguous"),
  # ADU cases: flag REQUIRES corroboration
  ("Alteration","Legalize existing ADU","Yes","R-3","1","0","B2024-07001","new_unit"),     # corroborated by legalize+ADU
  ("Alteration","Convert detached garage into ADU","Yes","R-3","1","0","B2024-07002","new_unit"),  # corroborated
  ("Addition/Alteration","Conversion of upper floor into a 410 sf JADU","Yes","R-3","1","0","B2024-07003","new_unit"),  # corroborated
  ("Alteration","Interior remodel of kitchen and bath","Yes","R-3","0","0","B2024-07050","ambiguous"),  # ADU flag, NO corroboration -> harvest
  # movable home cases
  ("New","Install park model tiny home, wheels removed, on permanent foundation","No","R-3","1","0","B2025-07100","new_unit"),
  ("New","Place movable tiny house on lot","No","R-3","1","0","B2025-07101","ambiguous"),  # no permanence markers
  ("Demolition","Demolish existing 3-story SFR","No","","0","0","B2023-04472","demolition"),
  ("Sign","Install wall sign","No","","0","0","B2024-08001","non_housing"),
  ("New","Revision to approved apartment plans","No","R-2","50","0","B2023-02354-REV1","subsidiary"),
  ("New","New ground-floor retail shell, no residential","No","B","0","0","B2024-06001","ambiguous"),
]

# DEFLATION-FIX TESTS: net_units defaulting for blank UnitsAdded on confident new_unit.
# (units_added, role, description) -> expected net_units
NU_TESTS = [
    (None, "new_unit", "Construct a new single-family dwelling", 1),   # blank SFR -> 1
    (None, "new_unit", "Convert detached garage into ADU", 1),        # blank ADU -> 1
    ("", "new_unit", "New duplex", 1),                                  # blank small -> 1
    (None, "new_unit", "New construction of 5-story residential apartment", None),  # blank multifam -> flagged
    (None, "new_unit", "New 50 unit apartment building", None),        # blank multifam -> flagged
    ("12", "new_unit", "New apartment", 12),                            # real count preserved
    ("0", "new_unit", "New SFR", 0),                                    # explicit 0 preserved (not overridden)
    (None, "alteration", "Re-roof", 0),                                # non-creating -> 0
    (None, "subsidiary", "REV", 0),                                    # child -> 0
]


def run():
    fails=[]
    for wt,desc,adu,occ,ua,ur,pn,exp in TESTS:
        got,_,note=classify(wt,desc,adu,occ,ua,ur,pn)
        ok = "ok" if got==exp else "** FAIL"
        if got!=exp: fails.append((pn,exp,got,desc[:40]))
        print(f"  [{ok}] {pn:<18} expect {exp:<11} got {got:<11} | {desc[:42]}")
    assert not fails, f"VOCAB TEST FAILURES: {fails}"
    print("\nALL VOCABULARY TESTS PASS.")

    nu_fails=[]
    for ua, role, desc, exp in NU_TESTS:
        got = net_units(ua, None, role, desc)
        flag = "ok" if got==exp else "** FAIL"
        if got!=exp: nu_fails.append((desc[:40], exp, got))
        print(f"  [{flag}] net_units({ua!r:<6},{role:<11}) = {str(got):<5} expect {str(exp):<5} | {desc[:38]}")
    assert not nu_fails, f"NET_UNITS TEST FAILURES: {nu_fails}"
    print("DEFLATION-FIX TESTS PASS: blank SFR/ADU->1, blank multifamily->flagged(None), real counts preserved.")
    print(f"\nALL {len(TESTS)}+{len(NU_TESTS)} permit_role TESTS PASS.")


if __name__ == "__main__":
    run()
