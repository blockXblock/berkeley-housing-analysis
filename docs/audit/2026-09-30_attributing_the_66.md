# Attributing the +66 (2026-09-30, in progress) — now +61 after the 1421 Arch ruling

The Housing Audit page shows ours 4,131 vs the City's 4,022 for 2018–25 (+109), of which +43 is explained by
verified findings. This memo accounts for the rest, building by building.

**Method (read-only; scripts in `2026-09-30_attributing_the_66/`).** Every counted completion of ours (live v4,
finaled `new_unit` masters with units, 849 rows / 4,131 units) and every City completion row (HCD APR table A2
CO columns, 806 rows / 4,022 units) is resolved to current parcels with `housing_rules.parcel_lineage.Resolver`
(County lineage; read-only on the peer session's chain build). Rows are grouped into buildings when they share a
current parcel, an address (the address canon), or the identical source APN (a split parcel the Resolver cannot
place). Totals reconcile exactly (+109).

**Update after the 2026-09-30 v4 swap (live sha 2b797a33):** 1421 Arch was our over-count (finding O07), corrected by a
reading ruling; ours 2018–25 is 4,126, the gap +104, outside the verified findings **+61** ('no City row' is now 27
buildings / +44). The scripts in `2026-09-30_attributing_the_66/` (match → classify → triage) re-derive the CSV from live.

**Result (first run, before the swap): every unit of the +66 is assigned to a building** (`2026-09-30_attributing_the_66_triage.csv`):

| Category | Buildings | Units |
|---|---|---|
| 698 buildings agree exactly; 4 differ only in year | 702 | 0 |
| We count; the City reported the building permit but no completion | 15 | +16 |
| We count; the City has no row for this permit at all | 28 | +49 |
| We count; the City has other rows at the parcel, not this permit | 9 | +10 |
| The City counts; we do not | 8 | −8 |
| Both count, different numbers (e.g. 2580 Bancroft 117 vs 122; 1601 Oxford 37 vs 34) | 31 | −1 |
| **Total outside the verified findings** | | **+66** |

Assigned is not the same as explained: each row is `to verify`. First reads of the three largest:
2532 Durant (+7): offices converted back to 7 apartments, finaled 2019-01-30, no City row — likely a City omission.
1421 Arch (+5): **OUR over-count (finding O07).** "Renew old permit B2017-02937"; the 2017 permit, found in the Accela Building sweep
(`data/raw/accela/date_range/Building_2017-07-05_2017-07-08.jsonl`), is an ELECTRICAL permit (200-amp service, 6 meters). The model read
the unit field (5 existing units) as 5 new units.
2501 Telegraph (+4): completes work "approved under B2014-04083". The 2014 permit predates the Building sweep (2015→); its 2016
revision (B2014-04083-REV01) changed "laundry room and lower porch … to storage, 2nd floor to remain as is" — reads like a renovation,
not new units. Accela check of B2014-04083 needed.

**Where parent permits live:** the Accela Building date-range sweep, `data/raw/accela/date_range/Building_*.jsonl` (1,071 files,
2015-01-01 → 2026-09-21), plus `data/processed/permits_clean.csv`. Permits before 2015 need an Accela CapDetail fetch.

**Next:** Accela checks for the parent permits behind the "no row" cases; confirm the 15 permit-but-no-completion
cases against the City's CY2026 report when published; review the 8 City-only rows against our readings
(e.g. `B2018-03595`, which our model reads as a sub-permit of the ADU under `B2018-03594`). Each verified case
becomes a row in `corrections/v4/audit_findings.csv`, and the page's "not yet attributed" shrinks.

## 2026-09-30, later: the 27 "no City row" buildings (+44), first read

Read from each permit's own description (and, where needed, the Accela sweep, the assessor and a CapDetail fetch):
- **Our errors, rulings proposed (+6):** 2501 Telegraph +4 (finding O08: a 363 sq ft rear-structure replacement; the
  parent B2014-04083 fetched from Accela) and 2212 McGee +2 (O09: an existing duplex's electrical upgrade).
- **Likely City omissions (~36):** real new units the City never listed — 2532 Durant (offices back to 7
  apartments), 1819 Fifth (2 units), 1336 Milvia (new duplex), 1631 Woolsey (boarding house to duplex), 2910
  Telegraph (2 units over commercial), 1648 MLK (office to 2 units), 2214 MLK (a relocated duplex), 1471 Scenic, 1400
  Queens, and about a dozen ADUs and studios.
- **Unclear (~6):** 11 Hill Rd ("create a kitchen for the second unit"), 2327 Curtis ("habitable accessory space"),
  1226 Parker and 1836 Capistrano ("accessory building"), 1627 Posen (studio with kitchenette), 707 Cragmont (a 2006
  permit finaled in 2024).
None of these is in the page's "explained" figure until verified one by one.
