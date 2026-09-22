# Berkeley Rent Stabilization Board — unit-registration database — CPRA #26-2375

**Request** filed 2026-08-13 (`notes/2026-08-13_cpra_rent_board_registry.md`); **granted 2026-08-17** (Rent Board;
redactions per Gov. Code 7923.600 / 7927.500 by the Board's staff attorney — tenant identifiers). **Retrieved 2026-09-21**
(`scratch/2026-09-21/download_26-2375_rentboard.sh`, signed-in session). PROGRESS.md entries through 2026-08-27 call
this "pending" — it had already been fulfilled.

| file | sheet | rows | cols | content |
|---|---|---|---|---|
| `2026-07-13 Unit Full Details.xlsx` | UNITFULLDETAILSREPORT | 41,279 | 29 | one row per registered unit, snapshot 2026-07-13: APN, Registration Status, Master Property Address, Unit Address, House/Street, **Unit Designation** (73% filled), Unit Status Code, Unit Fee Status, **Type of Coverage**, total / exempt units on property, Occupant Type, Bedrooms, Tenancy start date, Starting Rent (67%), Current Rent (15%), Rent Ceiling (52%), Housing Services, Subsidy type/flag, Owner / Owner business / Manager / Bill contact |
| `UnitHistory_2026 Database Export.xlsx` (City's name: `UnitHistory_ 2026 Database Export.xlsx`) | Tenants | 112,353 | 9 | tenancy history: APN Number, Unit Name, Address, Initial Rent, Rent Ceiling, Reason, End Reason (9%), Start Date Of Tenancy, Unit Regulation Type |

11,618 distinct APNs (details) / 11,553 (history). APNs are 12-digit `052154500500` form; the history file drops leading
zeros on some rows (`53167101000`) — normalize BOTH sides with `housing_rules.to_canonical_apn` before any join
(CLAUDE.md rule 4). Raw, unmodified, not yet joined to `berkeley.db` or v2.
