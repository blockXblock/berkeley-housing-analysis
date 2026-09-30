# Attributing the +66 (2026-09-30, in progress)

The Housing Audit page shows ours 4,131 vs the City's 4,022 for 2018–25 (+109), of which +43 is explained by
verified findings. This memo accounts for the rest, building by building.

**Method (read-only; scripts in `2026-09-30_attributing_the_66/`).** Every counted completion of ours (live v4,
finaled `new_unit` masters with units, 849 rows / 4,131 units) and every City completion row (HCD APR table A2
CO columns, 806 rows / 4,022 units) is resolved to current parcels with `housing_rules.parcel_lineage.Resolver`
(County lineage; read-only on the peer session's chain build). Rows are grouped into buildings when they share a
current parcel, an address (the address canon), or the identical source APN (a split parcel the Resolver cannot
place). Totals reconcile exactly (+109).

**Result: every unit of the +66 is assigned to a building** (`2026-09-30_attributing_the_66_triage.csv`):

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
1421 Arch (+5): "Renew old permit B2017-02937"; the 2017 permit is not in our data — Accela check needed.
2501 Telegraph (+4): completes work "approved under B2014-04083" — Accela check needed.

**Next:** Accela checks for the parent permits behind the "no row" cases; confirm the 15 permit-but-no-completion
cases against the City's CY2026 report when published; review the 8 City-only rows against our readings
(e.g. `B2018-03595`, which our model reads as a sub-permit of the ADU under `B2018-03594`). Each verified case
becomes a row in `corrections/v4/audit_findings.csv`, and the page's "not yet attributed" shrinks.
