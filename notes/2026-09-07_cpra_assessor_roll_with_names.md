# CPRA draft — Alameda County Assessor: secured assessment roll WITH assessee name

**Status: DRAFT 2026-09-07 — not sent.** To the **Alameda County Assessor's Office** (1221 Oak Street,
Room 145, Oakland CA 94612 — *verify address, current Assessor, and the county's current public-records
channel before sending*). Submit via the county's public-records portal if one is live.

**Why this is the cheapest possible ask.** We already hold **every other column of this exact table**.
`scripts/refresh_parcel_owners.py` ingests the county's own published
`Assessor_Office_Secured_Tax_Roll_2025_to_2026` (ArcGIS, services5.arcgis.com/ROBnTHSNjoZ2Wm1P) —
29,163 Berkeley parcels with mailing address, HOEX/OTEX, TRA, and the latest-document keys. The
published table even carries an `Attention_Name` column, but it is populated on **0 of 29,163**
Berkeley parcels. So this request adds **one field to a dataset the county already publishes**, and
we can prove we can load and use it correctly. That framing matters — it is a much smaller ask than
it sounds, and it should be answerable by re-running an existing extract with one column retained.

**Legal basis to verify before sending:** the assessment roll is a public record open to inspection
(**Rev. & Tax. Code § 408.3**; see also **§ 408.1** on the property-transfer list). Rev. & Tax. Code
**§ 408** makes *other* assessor records confidential — property statements filed under § 441 (§ 451),
audit workpapers, and market data gathered in confidence — none of which is requested here. Confirm
the current subdivision lettering; the request should cite the roll provision precisely.

---

**Subject: Public Records Act request — secured assessment roll including assessee name (City of Berkeley parcels)**

Under the California Public Records Act (Gov. Code § 7920.000 et seq.) and Rev. & Tax. Code § 408.3,
I request an electronic copy of the **secured assessment roll for parcels situated in the City of
Berkeley**, including the **name of the assessee**, as a CSV, delimited text, or native database
export (Gov. Code § 7922.570), with the following fields per parcel:

1. **APN** (and Sort/Print parcel forms if both are carried);
2. **name of assessee** as it appears on the roll;
3. **mailing address** (street, unit, city/state, ZIP) and mailing-address effective date;
4. **situs address** (street number, street name, unit, city, ZIP);
5. **Land**, **Imps**, **Fixtures**, **BPP**, **HPP**, **HOEX**, **OTEX**, **Total Net Value**;
6. **use code**, **economic unit**, **TRA primary** and **TRA secondary**;
7. **latest recorded document** prefix, series, date, and input date.

Fields 3–7 are already published by the county on its ArcGIS Open Data portal in
`Assessor_Office_Secured_Tax_Roll_2025_to_2026`; **item 2 (assessee name) is the only field this
request adds.** The published table's `Attention_Name` column is empty for all 29,163 Berkeley
parcels, which is why the request is necessary.

**Prior roll years.** Please provide the same, with assessee name, for **each roll year your office
can produce** — the county already publishes the 2019-20 through 2025-26 rolls without names. A
multi-year series would let ownership change be measured directly rather than inferred.

**Not requested:** any property statement filed under Rev. & Tax. Code § 441 or other record made
confidential by § 451 or § 408; audit workpapers; appraisal or market data gathered in confidence;
and any information about individuals protected under the Safe at Home program (Gov. Code § 6205 et
seq.) — please withhold those and produce the remainder, citing the basis for any withholding
(Gov. Code § 7922.525) rather than declining the request as a whole.

Please provide the record **in the format in which it is maintained** rather than as PDF. If any
fee applies beyond the direct cost of duplication, please identify the statutory basis and provide a
cost estimate before processing. I am glad to confer on scope, and to narrow to a single roll year if
that materially speeds the response.

*(Requester name / email / date to be filled by John.)*

---

**What this unlocks.** The county publishes no owner names anywhere — verified three ways: the Parcels
layer has no name field, the roll's `Attention_Name` is 0% populated, and the Ownership Transfer List
types rows TRANSFEROR/TRANSFEREE with no name column at all. Our current named-owner coverage is
**2,925 of 29,163 parcels** (10%), from Berkeley rental business licences. The roll with names would
take that to complete coverage from a primary source, and would retire the frozen 2017 ArcGIS
`TaxParcel` extract (last edited **2017-11-09**) that the public ownership map still rests on.

**Pairs with:** `notes/2026-09-07_cpra_recorder_grantor_grantee_index.md` (the Recorder's index gives
names *plus document type*, which is what yields true years-owned). The Assessor roll gives **who owns
it now**; the Recorder index gives **how long, and how it changed hands**. Ask for both; expect the
Assessor's to land first and cheaper.
