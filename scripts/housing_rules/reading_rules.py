"""reading_rules.py — the shared DEFINITIONS every model prompt over Berkeley permit records uses.

Since 2026-09-26 these are HCD's own definitions, from the Housing Element Annual Progress Report
FAQ (https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-faq.pdf,
"How does HCD define 'unit'", "What living quarters do not count as a housing unit", "Do I only report
net-new units"). Adopting the reporting form's definitions makes an independently built APR comparable
to the city's, row for row. John adopted them on 2026-09-26, replacing our own wording, which had
counted net rather than gross and had no rule for care facilities or student housing.

2026-09-29 (John): care and congregate buildings read as "unclear" until someone reads the unit plans.
The permit label decided three such buildings on 2026-09-29 (2000 Dwight, 2100 San Pablo, Step Up) and
the unit plans overturned or reframed each; HCD's test (separate quarters vs group arrangement) is not
answerable from a permit record. The resolution path is a document-grounded row in
corrections/v4/grounded_counts.csv. Stored readings are unchanged until a re-read writes a new evidence file.

Definitions of what is counted, not tips about reading the data: a 2026-09-26 control showed reading
tips added nothing and pushed the model toward crediting less. The one project convention kept is the
phase rule, which HCD does not address.

Question layers (scripts/llm_permit_effect.py per permit, scripts/batch_stage_classify.py per project)
add only their own question.
"""

DEFINITIONS = """Definitions used in this count (California HCD Annual Progress Report rules):

- A housing unit is a house, an apartment, a mobile home, a group of rooms, or a single room occupied
  (or intended for occupancy) as separate living quarters: the occupants live and eat separately from
  any other persons in the building, with direct access from outside or through a common hall.
  Single-room occupancy (SRO) units, accessory dwelling units (ADUs) and junior ADUs are housing units.
- Group quarters are not housing units: dormitories; housing restricted to students, even if it has
  separate living quarters; and senior or assisted-living facilities where residents live in a group
  arrangement owned or managed by an entity providing housing and/or services. Senior housing that
  consists of separate living quarters is housing units.
- A licensed care facility (residential care, assisted living, memory care) and a building described as
  congregate, group living, rooming or single-room occupancy can fall on either side: its rooms are
  housing units when each is separate living quarters (for example SRO rooms held by tenants, or
  apartments with their own kitchens) and group quarters when residents live in a group arrangement.
  A permit record alone does not show which. For such a building answer "unclear" and give the stated
  room or unit count in the reason; do not answer 0 and do not report the stated count as dwellings.
- Dwellings created means ALL new housing units the permitted work builds, not net of demolition.
  Units demolished or removed are reported separately as dwellings removed.
- A sub-permit is a permit whose own scope is part of construction permitted under another permit
  number (for example foundation-only work, a deferred submittal "-DEF", or a revision "-REV"). It
  creates no housing units itself.
- When one building is built under several phase permits, the phase whose work completes the housing
  units carries the building's units; earlier phases create none.
"""


# ---------------------------------------------------------------------------------------------
# PLANNING-RECORD SCOPE. The question is which Berkeley Accela PLANNING records belong to the
# housing pipeline. Prose written by people, so a model reads it against this text; the record
# NUMBER's prefix stays a regex (DEV in housing_rules.planning_filter) because that is machine
# form, not meaning. Full rationale, the measured regex misses and the review plan:
# docs/methodology/planning_record_scope_definition.md (John reviewed 2026-09-28).
#
# The statutory definition is quoted rather than paraphrased. JOHN'S RULING 2026-09-28, verbatim
# "2" = UNITS-STATED SUFFICIENCY: a record that states dwelling units is a housing development
# even when the two-thirds square-footage split is unstated, with the unmet test recorded in the
# reason. Rationale: HCD's APR collects UNITS, not square footage, so strict statutory reading
# would mark real housing projects unknown and make "unknown" mean "we cannot tell the mix"
# instead of "we cannot tell whether this is housing".
PLANNING_SCOPE = """Definition used here (California Government Code section 65589.5(h)(2), the
Housing Accountability Act, as amended effective 2026-01-01 by SB 838; the same definition SB 330
preliminary applications use, per section 65941.1):

"Housing development project" means a use consisting of any of the following:
  (A) Residential units only.
  (B) Mixed-use developments consisting of residential and nonresidential uses, where at least
      two-thirds of the new or converted square footage is designated for residential use and there
      is no hotel or motel component; or at least 50 percent residential with 500 or more net new
      units; or at least 50 percent residential with 500 or more units plus demolition or conversion
      of 100,000 or more square feet of nonresidential space.
  (C) Transitional housing or supportive housing.
  (D) Farmworker housing, as defined in Health and Safety Code section 50199.7(h).

Units-stated sufficiency: a record that states dwelling units IS a housing development project even
when the square-footage split is unstated. Say so in the reason when the two-thirds test could not
be evaluated. A record is not disqualified for failing to state what it never had to state.

Classes:
- housing_development: the record is an application, or a step in one, for a project meeting the
  definition above.
- housing_adjacent_not_development: housing is present but this record is not a development
  application. A Zoning Research Letter asking WHETHER residential use is permitted is an inquiry,
  not an application. A landmarks review of windows on an existing apartment building alters no
  housing.
- not_housing: commercial, institutional, signage, telecommunications, public art.
- unknown: the record's own text does not say enough to decide. This is a real answer and never a
  polite way of guessing.

Terms used in Berkeley's records:
- TOD means transit-oriented development; in Berkeley it appears for housing on transit agency land
  (Ashby BART, North Berkeley BART).
- "50 percent schematic plans" is a DESIGN-COMPLETION milestone, meaning the drawings are half
  finished. It is not an affordability share and says nothing about affordability.
- A Zoning Research Letter (ZR) is a question put to staff about what a site allows.
- The 1.E form is Berkeley's unit tabulation form. It states unit counts and never affordability.
- LMSAP is a Landmarks Structural Alteration Permit: a landmarks approval, not a building permit.
- ZCBP is a zoning clearance for a building permit, and is ministerial.
- DRC, DRCP and DRCF are Design Review Committee records: companion reviews, not the application.

Read only what the city published on this record. Do not use any other project at the same address,
and do not use any state or HCD filing as evidence of what this record is.
"""
