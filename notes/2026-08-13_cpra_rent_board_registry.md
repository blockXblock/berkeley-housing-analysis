# CPRA draft — Berkeley Rent Board full unit-registration database

**Status: ✅ SUBMITTED 2026-08-13 — NextRequest Request #26-2375.** Awaiting response. Submitted to the **Berkeley Rent Stabilization Board** (a separate
agency; records via rentboard.berkeleyca.gov or NextRequest). **Rationale:** the Rent Board registers ~19,000
rental units and counts *actual* dwelling units **regardless of whether the unit was ever permitted** — so it is
the single best source for finding the hundreds of unrecorded/converted/backyard units (like 2811½ Benvenue)
that building permits and the assessor miss. We hold only a **partial 1,098-row copy**; the ghost-unit detector
(`scripts/ghost_units.py`) already flags ~79 Elmwood candidates from that fragment + business licenses — the
full registry is the master list.

---

**Subject: Public Records Act request — Rent Board unit-registration database (all registered units)**

Under the California Public Records Act (Gov. Code § 7920.000 et seq.), I request an electronic export of the
**Rent Board's rental-unit registration database** — all registered units citywide — as a **native database
export or CSV/Excel** (§ 7922.570), with, per unit/property:

1. **APN** and **property (master) address**;
2. **unit address / unit designation**, including secondary-unit forms (e.g. "½", "A"/"B", "Rear", "Cottage",
   "In-Law", "ADU") — this field is essential;
3. **number of units on the property** (and number of registered / exempt units);
4. **registration status**, **unit status**, and **type of coverage** (fully covered / exempt / partially exempt),
   and the **basis for any exemption**;
5. **number of bedrooms**;
6. **tenancy start date** and registration/re-registration dates;
7. **rent data** to the extent disclosable — starting rent, current rent, and rent ceiling — or, if any
   portion is exempt, the non-exempt fields plus a citation for what is withheld (§ 7922.525);
8. **owner / managing-agent name** as carried in the registry.

I am **not** requesting tenant names or other personal tenant identifiers; please redact those and produce the
rest. If the database includes geospatial fields, please include them.

Please provide the record in the **format in which it is maintained** (database export, or CSV/Excel) rather than
PDF. I am happy to confer to scope or sequence. **Highest priority: items 1–4** (APN, unit designation, and unit
counts) — the fields that let a unit be located and counted.

*(Requester name / email / date to be filled by John.)*

---
**Why this pairs with the Accela RHSP harvest:** the Rent Board registry catches units the owner *registered*;
the Accela RHSP/RFS inspection records catch units the city *inspected* (like 2811½'s RFS-2023-00094). Together
they cover the two ways a permit-less unit still leaves a government footprint. Both feed `ghost_units.py`.
