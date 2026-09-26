"""reading_rules.py — the shared DEFINITIONS every model prompt over Berkeley permit records uses.

Definitions of what is being counted, not tips about reading the data. A 2026-09-26 control
(same 205 human-ruled permits, rules on vs off) found that eight reading tips added no accuracy and
pushed the model toward crediting less: "trust UnitsAdded" made it follow the city's 0 on junior
ADUs, "phases are one building" made it give 0 to completing phases, "sleeping rooms are not
dwellings" made it reject a mini-dorm John ruled as one dwelling. The model reads the prose well
cold; what it cannot guess is our CONVENTIONS, which the definitions below state. Question layers
(scripts/llm_permit_effect.py per permit, scripts/batch_stage_classify.py per project) add only
their own question.

Provenance of the conventions (grounded_counts.csv rulings): junior ADUs count (B2022-02844,
B2022-04367); co-living with in-unit kitchens counts (El Jardin B2018-03422, 55); a mini-dorm is one
dwelling (B2018-03160); the completing phase carries the units (El Jardin Phase III, Logan Park South
Phase II B2021-03302).
"""

DEFINITIONS = """Definitions used in this count:

- A dwelling unit is a place for independent living with its own cooking facilities (a full or
  efficiency kitchen). Accessory dwelling units (ADUs) and junior ADUs are dwelling units. Co-living
  rooms with in-unit kitchens are dwelling units. A building occupied as one household, such as a
  single-family house or a mini-dorm, is one dwelling unit.
- Dwellings created means net new dwelling units the permitted work adds: new units minus units
  removed or merged.
- A sub-permit is a permit whose own scope is part of construction permitted under another permit
  number (for example foundation-only work, a deferred submittal "-DEF", or a revision "-REV"). It
  creates no dwellings itself.
- When one building is built under several phase permits, the phase whose work completes the
  dwellings carries the building's dwellings; earlier phases create none.
"""
