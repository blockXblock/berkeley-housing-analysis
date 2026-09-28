r"""building_label.py -- read a BUILDING's identity out of a permit description.

The buildings (structures) stage needs to know when two permits describe ONE building and when they
describe TWO. The city writes the answer in the description, and v4's schema says so explicitly:
`structures.building_label TEXT -- 'North Building','Phase II', etc. (from raw_description)`.

THE DISTINCTION THAT MATTERS. Two permits at one site may differ by:
  * DESIGNATOR -- "ACHESON BLDG A" vs "ACHESON BLDG D", "South Building" vs "North Building".
    DIFFERENT BUILDINGS. Must never be merged.
  * PHASE -- "Phase I of II - South Building" vs "Phase II of South Building".
    ONE building, two permits. Must be merged, and the units counted once.
  * ORDINAL-OF-N -- "CONSTRUCTION OF THE FIRST OF TWO (N) DETACHED TWO-STORY HOUSES" vs
    "SECOND OF TWO". DIFFERENT BUILDINGS, phrased like a sequence. B2015-04522 / B2015-04523 are two
    houses; reading "first"/"second" as phases would erase one. This is CLAUDE.md's merge discipline
    ("never merge a real building away") in a new guise.

FALSE FRIENDS, all from real descriptions:
  * "Bldg only."                 -- scope of a permit, not a designator
  * "1st bldg., E,M,Ps. permit"  -- building PERMIT, not building #1
  * "refer to BP # B2016-05399 for Demo" / "Demo Permit is B2017-01908" -- a cross-reference to a
    DEMOLITION permit is not a parent; citing is not belonging (the same trap as ZP citations, where
    a reference only means lineage if it says it MODIFIES).

Returns evidence, never a guess: `designator=None, phase=None` means "the text does not say", which
leaves the grouping decision to a stronger signal rather than inventing one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# "BLDG A", "BUILDING \"C\"", "Bldg C," -- a single letter, optionally quoted, NOT followed by a word
# that reveals it is prose ("building only", "building permit").
# THE "Building a new house" TRAP. Case-insensitive [A-H] matches the ARTICLE "a": "Building a new
# house" and "building a 3-story addition" both read as Building A, and two such permits at one site
# merged into one structure -- erasing a real second house (2026-09-26). A designator is therefore
# either an UPPERCASE letter, or a lowercase one immediately followed by a delimiter (", " ":" etc.),
# never a lowercase letter followed by a word.
_DESIG_LETTER = re.compile(
    r"(?i:\b(?:bldg|building))\s*[\"'#:]?\s*"
    r"(?:([A-H])\b(?!\s*(?i:only|permit|ext))"          # an UPPERCASE designator: "BLDG A:", "Bldg C,"
    r"|([a-h])(?=\s*[,:;\"')\]]))")                      # or lowercase, but only before a delimiter

_DESIG_COMPASS = re.compile(
    r"\b(north|south|east|west)\s+(?:building|bldg|tower|wing)\b", re.I)
# "Phase II", "PHASE 3", "Phase I of II"
_PHASE = re.compile(r"\bphase\s*(?:#\s*)?([IVX]{1,4}|\d{1,2})\b", re.I)
_PHASE_OF = re.compile(r"\bphase\s*(?:[IVX]{1,4}|\d{1,2})\s*of\s*([IVX]{1,4}|\d{1,2})\b", re.I)
# "FIRST OF TWO", "SECOND OF TWO (N) DETACHED ... HOUSES"
_ORDINAL_OF = re.compile(
    r"\b(first|second|third|fourth)\s+of\s+(two|three|four|2|3|4)\b", re.I)
# a cross-reference to another permit, with the words that say what KIND of reference it is
_XREF = re.compile(r"\b(B\d{4}-\d{4,5}|\d{2}-\d{4,5})\b")
_XREF_DEMO = re.compile(r"\b(demo|demolition)\b", re.I)

_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_NUMWORD = {"two": 2, "three": 3, "four": 4, "2": 2, "3": 3, "4": 4}


def _num(tok: str | None):
    if not tok:
        return None
    t = tok.strip().upper()
    if t.isdigit():
        return int(t)
    return _ROMAN.get(t)


@dataclass
class BuildingLabel:
    designator: str | None = None      # 'A'..'H' or 'NORTH'/'SOUTH'/'EAST'/'WEST'
    phase: int | None = None           # 2 for "Phase II"
    phase_of: int | None = None        # 2 for "Phase I of II"
    ordinal: int | None = None         # 1 for "FIRST of two" -- a DISTINCT building, not a phase
    ordinal_of: int | None = None
    xrefs: list[str] = field(default_factory=list)      # permit numbers named in the text
    demo_xrefs: list[str] = field(default_factory=list)  # ... that are demolition references

    @property
    def distinguishes_building(self) -> bool:
        """True when this label asserts WHICH of several buildings -- a designator or an ordinal-of-N.
        A bare phase does NOT distinguish a building; it distinguishes a stage of one."""
        return self.designator is not None or self.ordinal is not None

    @property
    def key(self) -> str | None:
        """the building-identity part of the label, ignoring phase."""
        if self.designator:
            return f"BLDG:{self.designator}"
        if self.ordinal:
            return f"ORD:{self.ordinal}/{self.ordinal_of}"
        return None


def extract(description: str | None) -> BuildingLabel:
    d = str(description or "")
    lab = BuildingLabel()
    m = _DESIG_COMPASS.search(d)
    if m:
        lab.designator = m.group(1).upper()
    else:
        m = _DESIG_LETTER.search(d)
        if m:
            lab.designator = (m.group(1) or m.group(2)).upper()
    m = _PHASE.search(d)
    if m:
        lab.phase = _num(m.group(1))
    m = _PHASE_OF.search(d)
    if m:
        lab.phase_of = _num(m.group(1))
    m = _ORDINAL_OF.search(d)
    if m:
        lab.ordinal = _ORD.get(m.group(1).lower())
        lab.ordinal_of = _NUMWORD.get(m.group(2).lower())
    for x in _XREF.finditer(d):
        num = x.group(1)
        window = d[max(0, x.start() - 60):x.end() + 20]
        (lab.demo_xrefs if _XREF_DEMO.search(window) else lab.xrefs).append(num)
    return lab


def same_building(a: BuildingLabel, b: BuildingLabel) -> bool | None:
    """-> True (one building), False (different buildings), or None (the text does not say).

    None is the important return: it hands the decision to a stronger signal (permit-number lineage,
    an explicit citation) instead of guessing, and guessing here erases real buildings.
    """
    ka, kb = a.key, b.key
    if ka and kb:
        return ka == kb
    if ka or kb:
        # one names a building and the other does not -- not evidence either way
        return None
    # Neither names a building. A shared phase SEQUENCE is evidence; a bare phase number is not.
    # "Phase II of II" (an 8-storey) and "Phase III of III" (a 6-storey) merged into one structure on
    # 2026-09-26 under the old rule "both are phases -> same building" -- they are different buildings
    # on one block, one of them El Jardin. A sequence of 2 and a sequence of 3 cannot be the same
    # sequence, so the TOTAL is the discriminator.
    if a.phase_of and b.phase_of and a.phase_of != b.phase_of:
        return False
    if a.phase_of and b.phase_of and a.phase_of == b.phase_of and a.phase != b.phase:
        return True
    return None
