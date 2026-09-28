"""test_planning_filter.py -- python -m scripts.housing_rules.test_planning_filter

The first four cases are the FALSE NEGATIVES the previous pattern produced. They are verbatim from
the Planning store so a future edit cannot regress them by paraphrase.
"""
from scripts.housing_rules.planning_filter import (is_development, is_housing_development,
                                                   mentions_housing)

MUST_MATCH = [
    ("ZP2022-0046", "Demolish the existing gas station, and construct a 10-story (114 feet) "
     "mixed-use building utilizing a Density Bonus, with 166 dwellings, including 17 "
     "Very Low-Income units, and 1,043 square-feet of commercial space.",
     "THE case: plural 'dwellings' -- excluded by the old pattern"),
    ("ZP2019-0159", "Second story addition to existing front SFR on lot with 3 dwellings",
     "plural, small count"),
    ("ZP2021-0046", "construction of a new 6 story mixed-use building with 126 dwelling units",
     "the singular form must still match"),
    ("ZP2015-0229", "Demo existing commercial use, build 5 story mixed use, 50 units", "N units"),
    ("PLN2022-0026", "SB 330 Preliminary Application", "statute name alone"),
    ("ZP2026-0091", "middle housing certificate for 8 units", "middle housing"),
    ("ZP2020-0001", "New ADUs at the rear of the property", "plural ADUs"),
]
MUST_NOT_MATCH = [
    ("ZCBL2015-0012", "SMOG CHECKS", "a business licence"),
    ("ZP2018-0207", "Change of use from dry cleaners to full-service restaurant", "commercial"),
    ("PLN2015-0001", "Zoning research letter regarding permitted commercial uses", "an inquiry"),
]


def main() -> int:
    fails = []
    for num, desc, note in MUST_MATCH:
        if not is_housing_development(num, desc):
            fails.append(f"MISSED {num}: {note}")
    for num, desc, note in MUST_NOT_MATCH:
        if mentions_housing(desc):
            fails.append(f"FALSE POSITIVE {num}: {note}")
    if not is_development("ZP2022-0046") or is_development("ZCBL2015-0012"):
        fails.append("DEV prefix test failed")
    for f in fails:
        print("  FAIL", f)
    total = len(MUST_MATCH) + len(MUST_NOT_MATCH) + 1
    print(f"planning_filter: {total-len(fails)}/{total} cases pass")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
