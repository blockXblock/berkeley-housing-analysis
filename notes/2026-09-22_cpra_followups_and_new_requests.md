---
title: "CPRA follow-ups and two new requests — ready to send"
date: 2026-09-22
type: plan
status: draft
area: notes
---

# CPRA follow-ups and two new requests — ready to send

Copy-paste texts. Three are **follow-ups on existing threads** (reply to the NextRequest email, or the request page's
message box — replies reach the same staff). Two are **new requests** filed at records.cityofberkeley.info.
Background: `notes/2026-09-21_multiunit_master_list_plan.md`.

**Standing tactic (proved twice):** *name the artifact, not the schema.* #26-1368 and #26-1971 were fulfilled in days
because they asked for a report the City already runs under its own name. #26-1972 described fields and came back
with every structured column blank.

---

## 1. FOLLOW-UP on #26-1971 — the third file will not download

> Re: request #26-1971. Thank you for the production of 7 July 2026. Of the three files released, two downloaded
> successfully (`BP_Annual Permit Report (1).xlsx` and `(2).xlsx`). The third, `BP_Annual Permit Report.xlsx`, does not
> download from the request page — the link returns to the request listing and the portal reports no available file.
> Could you please re-attach that file, or confirm its date range so I can tell whether it duplicates one of the other
> two? Thank you.

*(Low stakes: most likely the 2018–2022 window re-run — a third snapshot of the oldest period. Worth one line.)*

## 2. FOLLOW-UP on #26-2306 — the winning vendor's documents were not produced

> Re: request #26-2306 (Clariti Cloud Inc. / RFP 24-11661-C). Thank you for the 13 August 2026 production. It contains
> the solicitation materials, the City's Appendices C–G, the scoring guide and vendor scores, and the proposals of six
> competing vendors. It does **not** contain the two records the request listed first:
>
> 1. the **fully executed contract/agreement with Clariti Cloud Inc.**, including exhibits, attachments, schedules, the
>    Statement of Work, the software subscription/licence agreement and any data-processing addendum or amendments; and
> 2. **Clariti's own proposal** in response to RFP 24-11661-C.
>
> These are the records that address items 4 and 5 of my request — data ownership, bulk export and portability, open-data
> and API provisions, and the City's right to extract and republish its own permit data. Please produce them, or, if any
> portion is withheld, identify the exemption relied on for that portion and produce the remainder (Gov. Code § 7922.525).
> If they are held by a department other than Planning, please let me know which.

## 3. FOLLOW-UP on #26-2367 — format note (courtesy, no records sought)

> Re: request #26-2367 (Corridors Zoning Update parcel GIS). Thank you — the data produced is exactly what was needed,
> and releasing the native geodatabase rather than a PDF was the right call. One practical note for future GIS
> productions: an Esri file geodatabase is a *folder*, and it was uploaded as 99 separate component files. The portal
> offers no bulk download, so retrieving it meant fetching all 99 individually; a single `.zip` of the `.gdb` folder
> would be one upload for staff and one download for the requester. Separately, these layers (parcel conditions, zoning,
> opportunity sites, the Housing Element sites inventory) are exactly the kind of dataset that belongs on the City's
> open-data portal, where no records request would be needed at all. Offered as feedback only — no further records sought.

---

## 4. NEW REQUEST A — the Planning "Master Permits Log", prior years

**Why:** we hold the 2026 log (#26-1972, 487 applications). Prior-year logs give the entitlement pipeline 2018–2025 in
the City's own words — the single biggest hole in our data (v2 has an `entitled` date for 59 of 909 projects, and the
Accela census's 2,287 Zoning Permits are a scrape, not a record).

> Under the California Public Records Act (Gov. Code § 7920.000 et seq.), I request the Planning Department's
> **"Master Permits Log"** workbooks — the same record produced to me on 5 August 2026 in response to request #26-1972
> (`2026 Master Permits Log.xlsx`) — for each prior year the Department maintains one: **2018, 2019, 2020, 2021, 2022,
> 2023, 2024 and 2025**, in their native Excel format (§ 7922.570). If the log is kept as a single rolling workbook
> rather than per-year files, please produce that workbook in full, including any archived or hidden sheets.
>
> Separately, and only if it is maintained: for every **Zoning Permit / Use Permit record (ZP)** in the permitting system
> (Accela) with an application date from **1 January 2015 through fulfilment**, an export of the record number, record
> type, application date, current record status, status date, project address, APN, and the **proposed dwelling-unit
> count** field where the system records one. If no such export exists, please say so and produce only the Master
> Permits Log workbooks.
>
> Please identify any portion withheld and the exemption relied on (§ 7922.525), and let me know of any cost estimate
> before processing. The prior production was exactly the record I needed — thank you.

## 5. NEW REQUEST B — the BP Annual Permit Report, all statuses

**Why:** every production to date is `Issuance Status = Issued` only, so expired, cancelled and withdrawn permits are
absent by construction. We can see them in the public portal (the Accela census shows 12,889 `Closed Expired` building
records) but we have no *record* of them from the City. Our permit-role classifier also has to infer parentage from the
`-DEF`/`-REV` suffix convention because no parent field is delivered — which is why raw `UnitsAdded` overstates units
by ~12.8× on large projects.

> Under the California Public Records Act, I request the **"BP Annual Permit Report"** — the report previously produced
> to me under requests #26-1368 and #26-1971 — re-run **without a status filter**, for permits with any activity from
> **1 January 2015 through fulfilment**, in native Excel (§ 7922.570).
>
> The prior productions contain only records whose Issuance Status is "Issued." I am asking for the same columns for
> **all record statuses the system carries** — including Expired / Closed Expired, Cancelled, Withdrawn, Void, Under
> Review, Approved and Ready to Issue — with the **current status** and the **status date** as two columns. (My earlier
> request #26-1971 asked for "current permit status (issued, finaled, expired, cancelled)"; the production did not
> include a status column, which is why I am asking again explicitly.)
>
> Three small additions to the same report, if the system supports them:
> 1. the **parent / master permit number** on `-DEF` (deferred submittal) and `-REV` (revision) rows. These rows repeat
>    the parent building's full dwelling-unit count, so anyone summing the units column without knowing that convention
>    overstates production by roughly an order of magnitude;
> 2. the report's **selection criteria and run date** printed on the banner — the scope rule of the prior productions
>    ("finaled in window OR submitted in window") had to be inferred;
> 3. please note that the `Completed` and `Completed Date` columns arrive empty on all but a handful of the 32,000+ rows
>    delivered to date, in case that is unintended.
>
> Please advise of any cost estimate before processing, and produce the remainder if any portion is withheld
> (§ 7922.525).

---

## Deliberately NOT re-asked

**Streamlining / approval pathway** (SB 9, SB 35, AB 2011, Density Bonus, Middle Housing). The City answered in writing
on 2026-09-04 (#26-2321): *"While our report does list the provision on it; however, we currently do not have a way to
track these. The department is trying to figure out a way to do so but, we do not have that at this time."* That answer
is itself the finding — it is the strongest evidence for the open-data argument, and re-asking spends goodwill for
nothing. Cite it; don't repeat it.

## Open question

**#26-1638** (filed 2026-06-05, published and closed 80 minutes later, no documents released). No request text survives
in the notes or in the email. Check `records.cityofberkeley.info/requests/26-1638` and record what it was.
