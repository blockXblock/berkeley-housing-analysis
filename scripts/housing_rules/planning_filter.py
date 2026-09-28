r"""planning_filter.py -- which Accela PLANNING records are housing-development records.

THE CANONICAL HOME for the DEV + HOUSING pair. Lifted here 2026-09-26 from
scripts/migration/ingest_planning_scope_a.py, where it lived as module-level regexes inside an
applied one-time write -- the same "drift to where nothing imports it" shape that CLAUDE.md records
for permit_role. Two consumers now import it: the CapDetail harvest queue and that ingest.

⚠ WHY IT HAD TO MOVE: the original HOUSING pattern had a FALSE NEGATIVE that cost a real project.

    ZP2022-0046, 3000 Shattuck: "Demolish the existing gas station, and construct a 10-story
    (114 feet) mixed-use building utilizing a Density Bonus, with 166 dwellings, including 17
    Very Low-Income units, and 1,043 square-feet of commercial space."

It was EXCLUDED, because:
  * `\bdwelling\b` cannot match the plural "dwellings" -- there is no word boundary between
    `dwelling` and `s`;
  * the numeric branch was `\d+\s*[-\s]?\s*units?\b`, which knows "N units" and never "N dwellings".

Consequences measured that day: 184 DEV records excluded while matching a wider housing pattern, 58
of them Zoning Permits; the harvest queue of 1,746 is a FLOOR, not a census; and the 1,188 planning
events the ingest already wrote into v2 are missing this project's 2022 application entirely (v2 has
its workflow hand-captured ANONYMOUSLY -- "Application Complete 2022-08-03 by Allison Riemer" with no
record number).

Re-running the applied ingest with the corrected filter is a DATA decision for John (CLAUDE.md: a data
error is a new gated write, not a re-run), not something importing this module performs.
"""

import re

# Record-number prefixes that are development records at all.
DEV = re.compile(r"^(ZP|PLN|DRS|DRC|LM|ZCBP)", re.I)

# Housing language. Both nouns are first-class and either may be plural; a count may attach to
# either ("166 dwellings" and "48 units" must both match). Keep additions ANCHORED to word
# boundaries that tolerate plurals -- write `dwellings?`, never `\bdwelling\b`.
NUMWORD = (r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
           r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)")

HOUSING = re.compile(
    r"(\b(dwellings?|adus?|jadus?|duplex(?:es)?|triplex(?:es)?|fourplex(?:es)?|apartments?|"
    r"residences?|residential|middle housing|sb ?9|sb ?330|sb ?35|sb ?423|sb ?684|ab ?2011|"
    r"town ?home(?:s)?|town ?house(?:s)?|rowhouse(?:s)?|condominium(?:s)?|housing|"
    r"single.family|multi.family|infill|live.?work|density bonus|habitable)\b"
    r"|(?:\d+|" + NUMWORD + r")\s*[-\s]?\s*(?:units?|dwellings?|bedrooms?)\b)", re.I)


def is_development(record_number: str | None) -> bool:
    return bool(DEV.match(str(record_number or "")))


def mentions_housing(*fields: str | None) -> bool:
    """True when any supplied field uses housing language."""
    return bool(HOUSING.search(" ".join(str(f or "") for f in fields)))


def is_housing_development(record_number: str | None, *fields: str | None) -> bool:
    return is_development(record_number) and mentions_housing(*fields)
