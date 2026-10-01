# Sweep: a building's existing units read as new units (2026-09-30, read-only)

Three of three suspicious "no City row" cases (1421 Arch, 2501 Telegraph, 2212 McGee) were the same model misreading:
a permit's NumberUnits (the building's EXISTING units) read as new units on an electrical or remodel permit. This sweep
looks for the pattern across every permit v4 counts as creating units (1,188 permits; 1,168 have an Accela record
type in the Building sweep files), using STRUCTURED fields, not description patterns:

- **Tier A:** the Accela record type is trade-only (Electrical / Mechanical / Plumbing and their combinations, no
  "Building"). Such a record cannot create a dwelling on its own.
- **Tier B:** the CPRA Work Type is alteration/repair/remodel, UnitsAdded is blank or 0, and the credited count equals
  NumberUnits exactly.

**Result: 2 Tier A permits (4 units), 87 Tier B (129 units)** — candidates in `2026-09-30_misread_sweep_candidates.csv`.
Read one by one, nearly all are real units: Acheson Building A (a landmark rehabilitated to 37 apartments), a boarding
house and a care facility converted to duplexes, new houses, a manufactured home, and many ADU/JADU conversions (four
"remodel" descriptions end in "creating a Junior ADU" or similar). **One new clear misreading: 2707 Hillegass,
B2019-02963** (finding O10), an Electrical Permit credited with 3 units while the cottage it serves is counted under its
own permit; permits only, never finaled. **2334 Jefferson, B2018-01255, settled the same day (finding O11):** the house remodel; the ADU is counted under its own
permit B2018-01256, so the remodel's 1 unit is a double count (CO +1 in 2020, BP +1 in 2018).

**Conclusion:** with the three already ruled, the misreading is real but rare — five permits, 15 units (CO −12, BP −15).
It does not look systemic, so no re-read of the whole corpus is needed. Limitation: a misread on a permit typed "New"
or with UnitsAdded filled would not be flagged here.
