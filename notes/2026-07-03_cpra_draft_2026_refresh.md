# CPRA drafts — 2026 refresh + planning pathways + fees (Day 1 of mayor-presentation prep)

**Status: SUBMITTED as NextRequest #26-1972. Request 2 / item 1 — RESPONSE RECEIVED 2026-08-09
→ RESPONSIVE-BUT-HOLLOW → follow-up drafted (below).** Two separate requests on purpose: #1 is a
re-run of a report the City has produced before (fast to fulfill, hard to delay); #2 is new material
(pathway + clock + fee data). Keeping them separate prevents the novel items from slowing the
refresh. Sent via the City's NextRequest portal (records.cityofberkeley.info).

---

## RESPONSE + FOLLOW-UP — #26-1972 (added 2026-08-09)

**What landed (Request 2 / item 1, the planning-applications ask):** the Planning Dept's internal
staff tracking spreadsheet — **"2026 Master Permits Log.xlsx"** (`scratch/2026-08-09/master_permits_log.xlsx`),
9 sheets, 487 applications. **VERIFIED live:** the City filled the 6 fields it maintains by hand —
Application #, Site Address, Applicant, Description, Date Received, Assigned Planner (93–100%) — and left
**every structured field the request named BLANK: Date Deemed Complete 0/158, New/Total/Demolished Units
0/158, Streamlining pathway 0/158, BMR/VLI/density-bonus/Final-Action/NOD 0.** Verdict: **not a failure to
respond** (right scope, real data) but **responsive-and-hollow**. Two readings — (A) the City doesn't
MAINTAIN that data queryably (→ best evidence for the mayor-deck open-data ask), or (B) it lives in Accela
and they gave the hand-log instead (→ incomplete production; deemed-complete DOES surface on ACA
Processing-Status pages, so lean B for that one field). Data extracted (NOT a DB write):
`data/processed/planning_pipeline_2025.csv` (2025 planning-application tail; 450 applicant names).
Distinct from the Clariti CPRA **#26-2306** (filed 2026-08-09, awaiting response).

**FOLLOW-UP — ✅ SUBMITTED via NextRequest 2026-08-10 (John).** Awaiting the City's either/or reply.

**FOLLOW-UP TEXT (as submitted — forces the either/or on the record):**

> Re: Request #26-1972 — follow-up on the production received (the "2026 Master Permits Log"). Thank you
> for the Master Permits Log produced in response to this request. That spreadsheet includes columns for
> several fields my request specifically sought — **Date Deemed Complete, proposed dwelling-unit counts
> (new/total/demolished), the approval pathway or streamlining provision (e.g., SB 9, SB 35, AB 2011,
> Density Bonus, Middle Housing), decision/Final Action and NOD dates, and BMR/affordability counts** —
> but those columns are **blank across all records**. Because my request sought these as an **export from
> the City's permitting system (Accela/ACA)**, please either (1) **produce these fields as they are
> maintained in that system** (the deemed-complete date is the field from which Government Code § 65943 /
> § 66317's completeness clock runs, and it is displayed on the ACA "Processing Status" pages, so the City
> appears to maintain it), or (2) **confirm in writing that the City does not maintain these fields in any
> queryable or exportable form** and identify where, if anywhere, that information is recorded. If some
> fields fall under (1) and others under (2), please say which is which.

---

## Request 1 — Building-permit report refresh (mirrors the wording of the fulfilled 2018–2022 request)

> Under the California Public Records Act (Gov. Code § 7920 et seq.), I request a report similar
> to the Building Permits reports previously produced to me (covering January 1, 2018 through
> December 31, 2022, and 2023 through 2025), for the subsequent period: **January 1, 2025 through
> the date this request is fulfilled**, in the same electronic format (Excel).
>
> Specifically, all building permits with activity during this period (the same scope as the
> prior productions), including but not limited to:
>
> - Permit number
> - Property address (street number, street name, street type)
> - APN (Assessor Parcel Number)
> - Permit type (new construction, addition, ADU, JADU, demolition)
> - Work description
> - Number of dwelling units (existing, proposed, added, removed)
> - Permit application date (submittal date)
> - Permit issued date (issuance date)
> - Final inspection date (if applicable)
> - Certificate of occupancy date / "finalized" date (whichever field Accela maintains for
>   permit completion)
> - Current permit status (issued, finaled, expired, cancelled)
> - Valuation amount (job valuation)
> - Applicant/contractor name
> - Total fees assessed
>
> Note: the prior productions did not include the last two fields (applicant/contractor name and
> total fees assessed) although the underlying system maintains them; please include them in this
> production if at all possible, for the full requested period. I request the export as an
> electronic record in its native format per § 7922.570.
>
> Please also identify any filter or selection criteria the report applies (permit types, record
> statuses, or categories excluded): a comparison of the prior production against the public
> Accela portal's records for the same months indicates the report captures substantially fewer
> building-permit records than were filed, and I would like to understand the report's intended
> scope.

*(Why: our feed ends with the 2023–2025 production; Middle Housing ordinance and current
ministerial-path activity live in late-2025/2026 filings. The 2025 overlap is deliberate — it
refreshes statuses/finaled dates on permits that have advanced since the last production. The
contractor + fees fields were requested before but never produced; getting them here would also
unlock the Players and fee-actuals work without a separate ask.)*

## Request 2 — Planning pathways, application-completeness dates, and permit fees

> Under the California Public Records Act, I request the following electronic records, each as an
> export from the City's permitting system (Accela) in Excel or CSV:
>
> 1. **Planning applications** (all record types: ZP, UP, AP, DR, LM, PREAPP) filed from
>    **July 1, 2024 through fulfillment**, with: record number, record type, application/filed
>    date, **date deemed complete**, decision and decision date, project address and APN, proposed
>    dwelling-unit counts, and any field identifying the **approval pathway or enabling program**
>    (e.g., State Density Bonus, SB 9, ADU state standards, Middle Housing / R-1 multi-unit
>    pathway, SB 35 / ministerial streamlining).
> 2. **Application-completeness dates for building permits**: for all building permits with an
>    ADU flag or a dwelling-unit change filed from **January 1, 2023 through fulfillment**, the
>    permit number, submittal date, and **date the application was deemed complete** (the field
>    from which Government Code § 66317's 60-day clock runs).
> 3. **Permit fee ledger**: for all building permits issued from **January 1, 2018 through
>    fulfillment**, the fees assessed and fees paid per permit, itemized by fee schedule line
>    where the system records it (permit fee, plan check, and any impact or mitigation fees).
> 4. **Affordable-housing in-lieu / mitigation payments**: records sufficient to identify each
>    payment into the Housing Trust Fund (or successor affordable-housing mitigation account) by
>    project address and amount, from January 1, 2018 through fulfillment.
>
> If any portion cannot be produced as requested, please produce the remainder and identify the
> withheld portion per § 7922.540. I am happy to discuss narrowing any item that is burdensome.

*(Why: item 1 = Middle Housing ordinance effectiveness; item 2 = converts JN-I's 60-day SCREEN
into statutory verdicts; items 3–4 = the money-flows model's actuals, replacing valuation-formula
estimates.)*

---

**Presentation-timeline note:** statutory response window is 10 days (extendable 14) — neither
request lands before the mayor presentation. The 5-day window is covered by the Accela date-range
harvest (Day 1–2 track 2). These requests are the durable follow-through the presentation can
announce as "in progress."
