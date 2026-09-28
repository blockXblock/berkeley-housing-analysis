"""test_building_label.py -- python -m scripts.housing_rules.test_building_label

Every string is VERBATIM from a v4 raw_description. The point of the file is the false friends: a
designator that is really the word "building", and an ordinal that looks like a phase but names a
second house.
"""
from scripts.housing_rules.building_label import extract, same_building

REAL = {
    "B2015-02995": "ACHESON BLDG A: REHABILITATION OF AN EXISTING 24429 SFT, 4 STORY LANDMARKED BUILDING TO A MIXED USE: 37",
    "B2015-02998": "ACHESON BLDG B: NEW 6 STORY, 32,673 SFT. BUILDING, TYPE IIIA OVER IA, WITH 35 NEW RESIDENTIAL UNITS",
    "B2015-03000": '"ACHESON COMMONS" - BUILDING "C": (N) 82,740 SFT, 65 RES. UNIT, 6 STORY, TYPE III-A',
    "B2015-03005": "ACHESON BLDG D: NEW 6 STORY 67,558 SFT  BUILDING, TYPE IIIA OVER IA, WITH 68 NEW RESIDENTIAL UNITS",
    "B2019-05575": "Phase I of II - South Building (companion permit to B2019-05574).",
    "B2021-03302": "Phase II of South Building: Structural Super Structure, MEP, landscaping",
    "B2018-02626": "Bldg C, 2813 Channing Way; Partial Demo Removal of 36 sq ft and addition",
    "B2015-04522": "CONSTRUCTION OF THE FIRST OF TWO (N) DETACHED TWO-STORY HOUSES W/ATTACHED GARAGE",
    "B2015-04523": "** 1st Ext. from March 17, 2018 to March 17, 2019. Bldg only.  CONSTRUCTION OF SECOND OF TWO (N) DETACHED",
    "B2016-05139": "BUILD (N) 4-STORY MIXED USED BUILDING - refer to BP # B2016-05399 for Demo of existing building",
    "B2017-01244": "2nd Extension for B, E & P permits until 7-11-2020.",
    # THE ARTICLE TRAP: case-insensitive [A-H] matches the word "a". Two of these merged into one
    # structure on 2026-09-26, erasing a real second house.
    "B2017-05297": "Building a new house 2107sqft",
    "B2017-05298": "Building a new house (rear) 1669SqFt. Address assignment in process",
    "B0000-0001": "building a 3-story addition to an existing duplex",
    # DIFFERENT PHASE SEQUENCES on one block: an 8-storey in 2 phases and a 6-storey (El Jardin) in
    # 3 phases. These merged under the old "both are phases" rule, which would erase one building.
    "B2018-01337": "Phase II of II: Superstructure and close in for a new 8 story mixed use building",
    "B2018-03422": "Phase III of III for a New 6-Story mixed use building. See Permit B2018-01337",
}

EXPECT_KEY = {
    "B2015-02995": "BLDG:A", "B2015-02998": "BLDG:B", "B2015-03000": "BLDG:C",
    "B2015-03005": "BLDG:D", "B2019-05575": "BLDG:SOUTH", "B2021-03302": "BLDG:SOUTH",
    "B2018-02626": "BLDG:C", "B2015-04522": "ORD:1/2", "B2015-04523": "ORD:2/2",
    "B2016-05139": None,      # "MIXED USED BUILDING" is prose, not a designator
    "B2017-01244": None,      # "for B, E & P permits" is a permit-type list, not Building B
    "B2017-05297": None,      # "Building a new house" -- the ARTICLE, not Building A
    "B2017-05298": None,
    "B0000-0001": None,
    "B2018-01337": None,      # a phase, but no building designator
    "B2018-03422": None,
}

PAIRS = [
    ("B2015-02995", "B2015-03005", False, "Acheson A vs D: four buildings, never merge"),
    ("B2015-02998", "B2015-03000", False, "Acheson B vs C"),
    ("B2019-05575", "B2021-03302", True, "Phase I and II of the SOUTH building are one building"),
    ("B2015-04522", "B2015-04523", False, "first/second of two houses are TWO houses"),
    ("B2016-05139", "B2017-01244", None, "neither names a building -> the text does not say"),
    ("B2017-05297", "B2017-05298", None,
     "two 'Building a new house' permits must NOT merge -- front and rear are two houses"),
    ("B2018-01337", "B2018-03422", False,
     "Phase II-of-II and Phase III-of-III are different SEQUENCES, so different buildings"),
]


def main() -> int:
    fails = []
    for k, want in EXPECT_KEY.items():
        got = extract(REAL[k]).key
        if got != want:
            fails.append(f"{k} key {got!r}, wanted {want!r}")
    # the phases must still be read even when a designator is present
    if extract(REAL["B2019-05575"]).phase != 1 or extract(REAL["B2021-03302"]).phase != 2:
        fails.append("phase numbers not read on the Logan South pair")
    if extract(REAL["B2019-05575"]).phase_of != 2:
        fails.append('"Phase I of II" did not yield phase_of=2')
    # a demolition cross-reference must NOT be offered as a parent
    lab = extract(REAL["B2016-05139"])
    if lab.xrefs or lab.demo_xrefs != ["B2016-05399"]:
        fails.append(f"demo xref misfiled: xrefs={lab.xrefs} demo={lab.demo_xrefs}")
    # "companion permit to B2019-05574" IS a plain xref (the North building), not a demo
    if extract(REAL["B2019-05575"]).xrefs != ["B2019-05574"]:
        fails.append("companion-permit xref not captured")
    for a, b, want, why in PAIRS:
        got = same_building(extract(REAL[a]), extract(REAL[b]))
        if got is not want:
            fails.append(f"same_building({a},{b}) = {got}, wanted {want} -- {why}")
    for f in fails:
        print("  FAIL", f)
    total = len(EXPECT_KEY) + 4 + len(PAIRS)
    print(f"building_label: {total-len(fails)}/{total} checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
