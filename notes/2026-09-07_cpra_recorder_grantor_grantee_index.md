# CPRA draft — Alameda County Recorder: grantor/grantee index (INDEX ONLY, no images)

**Status: DRAFT 2026-09-07 — not sent.** To the **Alameda County Clerk-Recorder** (Auditor-Controller/
Clerk-Recorder Agency, 1106 Madison Street, Oakland CA 94607 — *verify address, current officeholder,
and whether the Recorder runs its own records channel separate from the county portal*).

**The one rule that decides this request: ask for the INDEX, never the IMAGES.**
- Gov. Code **§ 27301** restricts making *document images* of deeds and similar instruments publicly
  available online. It does **not** restrict the index. Nearly every objection and nearly all of the
  cost live on the image side, so excluding images removes both.
- The index fields are the whole prize anyway. **Document type** is the field that separates a grant
  deed (a sale) from a deed of trust (a refinance) — the only way to compute true years-owned.

**Why we need it specifically.** This project has now produced a wrong tenure answer **twice** from
two different fields, for the same reason: both record the last document of *any* kind. The 2017
`LatestDocu` said 2811 Benvenue was a 5-year hold when it has been owned since 1988; the Assessor's
`Mailing_Address_Effective_Date` says 2021 for the same parcel. A refinance or a trust transfer resets
those dates without changing ownership, so "years owned" is systematically understated and no
arithmetic on the data we hold can fix it. **Document type is the missing field, and only the Recorder
has it.**

**Legal basis to verify before sending:** recorded instruments are public records (Gov. Code
**§ 27201 et seq.**) and the Recorder maintains grantor/grantee indexes (**§ 27230 et seq.** — confirm
the exact sections). Electronic format and cost: Gov. Code **§ 7922.570**. Note that Recorder fees run
under their own schedule (**§ 27366**), not CPRA's duplication-cost rule, so a fee is likely and is
not itself a refusal.

---

**Subject: Public Records Act request — grantor/grantee index data (index fields only; no document images)**

Under the California Public Records Act (Gov. Code § 7920.000 et seq.) and Gov. Code § 27201 et seq.,
I request an electronic extract of the **grantor/grantee index** for instruments affecting real
property in the **City of Berkeley**, as CSV or delimited text (Gov. Code § 7922.570), with these
fields per indexed instrument:

1. **document number** (and series/prefix if separate);
2. **recording date** (and recording time if carried);
3. **document type** and its **type code** — e.g. grant deed, quitclaim, deed of trust, reconveyance,
   trustee's deed, affidavit of death, lien — **this field is essential to the request**;
4. **grantor name(s)**, as indexed;
5. **grantee name(s)**, as indexed;
6. **APN(s)** and any parcel or situs reference carried in the index;
7. **documentary transfer tax** amount, and any city/county split, where carried in the index;
8. any **related/prior document reference** the index carries.

**I am expressly NOT requesting document images or copies of the instruments themselves.** This
request is for **index data only**, which is not subject to the internet-display restriction of
Gov. Code § 27301.

**Scope, to keep this small and cheap:** instruments affecting **Berkeley APNs**, recorded
**1990-01-01 to present**. If a county-wide extract is materially easier to produce than a filtered
one, county-wide is acceptable and I will filter it myself. If the date range drives the cost, I will
take **2000 to present**, or a single year as a pilot.

**On format and fee.** Please provide the data in the format in which it is maintained rather than as
PDF or a paginated report. If your office already provides this index as a **bulk-data extract or
subscription product** — as is commonly provided to commercial data aggregators — I am glad to obtain
it on those terms instead, and would appreciate being told what the product and terms are. Please
provide a **cost estimate before processing** if any fee applies, and identify its statutory basis.

If any portion is withheld, please cite the specific exemption for that portion and produce the
remainder (Gov. Code § 7922.525). Please redact any information protected under the Safe at Home
program (Gov. Code § 6205 et seq.) or by court order, and produce the rest.

*(Requester name / email / date to be filled by John.)*

---

**If they push back.** Two objections are likely, and both have the same answer:
1. *"This is bulk personal information."* The grantor/grantee index is already a public record, is
   already searchable by name at the counter and through the county's online portal, and is already
   provided in bulk to commercial aggregators — whose product is resold to Zillow, Redfin and to the
   vendor behind the SF Chronicle's statewide property map. This request seeks the same public record
   on the same terms, for a non-commercial civic purpose.
2. *"The images can't be released."* Correct, and none are requested. This is index data only.

**What we would do with it.** Compute true years-owned (grant deeds only, excluding financing
instruments); replace the "years since last recorded document" colouring on the public ownership map,
which is currently an honest but weak proxy; and extend transfer history back before **2023-03-31**,
the start of the two-year rolling window in the Assessor's Ownership Transfer List (4,392 Berkeley
documents, already ingested into `parcel_facts.db`).

**Pairs with:** `notes/2026-09-07_cpra_assessor_roll_with_names.md`. The Assessor roll gives **who owns
it now** and should land first and cheaper; the Recorder index gives **how long, and how it changed
hands**, and is the more valuable of the two.
