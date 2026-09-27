"""reading_rules.py — the shared DEFINITIONS every model prompt over Berkeley permit records uses.

Since 2026-09-26 these are HCD's own definitions, from the Housing Element Annual Progress Report
FAQ (https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-faq.pdf,
"How does HCD define 'unit'", "What living quarters do not count as a housing unit", "Do I only report
net-new units"). Adopting the reporting form's definitions makes an independently built APR comparable
to the city's, row for row. John adopted them on 2026-09-26, replacing our own wording, which had
counted net rather than gross and had no rule for care facilities or student housing.

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
- Dwellings created means ALL new housing units the permitted work builds, not net of demolition.
  Units demolished or removed are reported separately as dwellings removed.
- A sub-permit is a permit whose own scope is part of construction permitted under another permit
  number (for example foundation-only work, a deferred submittal "-DEF", or a revision "-REV"). It
  creates no housing units itself.
- When one building is built under several phase permits, the phase whose work completes the housing
  units carries the building's units; earlier phases create none.
"""
