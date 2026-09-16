---
title: "What the City actually sent us — and what a future CPRA should ask for"
date: 2026-09-10
type: diagnostic
status: record
area: notes
---

# What the City actually sent us — and what a future CPRA should ask for

**Status: analysis, 2026-09-10. No request drafted or sent yet.**
Subject: the two fulfilled productions in `data/raw/cpra-downloads/`
(`BP_Annual Permit Report-2018-2022.xlsx`, NextRequest **26-1368**, fulfilled 2026-05-20;
`BP_Annual Permit Report-2023-2025.xlsx`, fulfilled ~2026-04-20).
Every number below was derived by reading the two workbooks, not from the README.

---

## 1. The tactic that worked — reuse it

We did not ask the City to build us a dataset. We asked for **a report the City already runs
under its own name**: the "BP Annual Permit Report." That is why it was fulfilled quickly and
completely. Contrast **#26-1972**, where we described the *fields* we wanted from Planning: the
City produced a hand-kept staff spreadsheet with every structured column blank
(responsive-but-hollow; follow-up submitted 2026-08-10, no reply on record).

**Rule for the next request: name the artifact, not the schema.** Ask what the report is called
if you don't know, then ask for it by that name.

---

## 2. What arrived

Two workbooks, one sheet each, six banner rows + blank + header on row 8, data from row 9.
**26 columns as the sheet is laid out**, of which three (positions 4, 13, 17) are unnamed spacer
columns that are empty on every one of the 32,202 rows — so **23 columns carry data**. The README's
"26 columns total" is true of the raw sheet; read it as 23 when planning a load.

| | 2018-2022 | 2023-2025 | combined |
|---|---|---|---|
| rows | 18,053 | 14,149 | 32,202 |
| unique permit numbers | | | 30,764 |

Columns: `PermitNumber, Submittal Date, Issuance Status, Issuance Date, Finaled Status,
Finaled Date, Completed, Completed Date, Parcel Number, StreetNumber, StreetName, StreetType,
JobValuation, WorkDescription, ADU, Detached, Work Type, OccType, SubType, NumberUnits,
UnitsAdded, UnitsRemoved, CO Required`.

This is a genuinely good permit backbone. Identity, address, parcel, dates and work description
are populated at 96–100%. It is the right spine for the BP layer and we should keep refreshing it.

---

## 3. Five defects in what was delivered

These are only visible by reading the files. Each is cheap for the City to fix and each should be
named explicitly in the next request.

**(a) The field named "Completed" is empty.** `Completed` carries a value on **6 of 32,202** rows;
`Completed Date` on **1**. The column exists in the report and is not maintained. So `Finaled Date`
is the only completion signal in the production — which matters because it is *not* a certificate
of occupancy (§5).

**(b) `UnitsAdded` is inflated ~12.8× by subsidiary permits.** Every `-DEF` deferred-submittal and
`-REV` revision permit repeats the **parent building's full unit count**. On the ≥50-unit cohort:
**317 rows across just 28 distinct addresses**, summing to **32,767 units** where the true figure is
**2,563**. 2000 Dwight alone appears on 20 permits, each carrying 113.

Parentage is recoverable *only* because Berkeley's permit numbers happen to carry a `-DEF##`/`-REV##`
suffix on the parent's number. **There is no delivered parent/master field.** Any consumer who sums
`UnitsAdded` without knowing that convention gets a number an order of magnitude wrong.
(This is exactly what `housing_rules.permit_role.classify` exists to undo.)

**(c) 2,008 rows contradict themselves.** `Finaled Status = "Finaled"` with `Finaled Date` blank —
1,302 in the 2018-2022 file, 706 in 2023-2025.

**(d) The scope rule is undocumented and is a union.** `Finaled Date` is strictly bounded to the
window, but **35.9% / 28.8% of rows carry no Finaled Date at all** — those are in-window by
**Submittal Date** (96.6% / 91.2%). So the real rule is *finaled in window OR submitted in window*,
which nobody stated.

**(e) The two deliveries are snapshots at different times, not disjoint year ranges.**
**1,430 permit numbers appear in both files**, and **1,278 of them gained a Finaled Date between the
two productions**. Knowing this, the overlap is a free two-point time series. Not knowing it, it is a
silent double-count. (Also: `Issuance Date` ships as **text** while `Submittal Date` and
`Finaled Date` ship as real dates.)

---

## 4. What is absent altogether — and it is most of the APR

Nothing in the production supplies:

| APR need | Where it lands | In the report? |
|---|---|---|
| affordability by income tier (VLI / LI / Mod / AMI / Acutely Low) | Table A2 cols 6–9 | **no** |
| tenure (rent vs own) | Table A2 col 5 | **no** |
| bedroom count / unit size | Table A2 | **no** |
| entitlement date + planning application no. (ZP) | Table A2 cols 10–11 | **no** |
| certificate-of-occupancy date | Table A2 col 12 | **no** |
| streamlining pathway (SB 9, SB 35, AB 2011, density bonus) | Table A2 cols 14–19 | **no** |
| demolished-unit address and tenure | Table A2 demolition cols | **no** |
| applicant / owner of record | project identity | **no** |

---

## 5. The conclusion that should drive the next request

**The BP Annual Permit Report cannot reproduce the APR, and no refresh of it ever will.**

Table A2 reports units **by income tier at three moments** — entitled, permitted, completed. The
report we hold has **no income tier, no entitlement, and no completion**. It has one permit date and
one final date. Asking for a wider or fresher permit report is asking the same question louder.

And the definitional gap is real, not a formatting problem: the APR's completion column reports
**units issued certificates of occupancy**, while **Berkeley does not issue traditional COs** — the
City finals permits. Our CO derivation rule bridges that gap
(`notes/2026-05-24_apr_workflow_audit.md` §4), but it is *our* rule. It is not the City's, and the
Possibility Lab would have to take it on trust.

---

## 6. What to ask for instead — three asks, in priority order

### A. The APR submission workbooks themselves (highest value)

HCD distributes a **fillable Excel APR form**; the city fills it and uploads it, and the PDF on CKAN
is a rendering of that workbook. **The filled workbook is a record the City holds.**

Ask for: *"the completed HCD Annual Progress Report Excel workbooks, as submitted to the Department
of Housing and Community Development, for calendar years 2018 through 2025, in their native Excel
format."* Likely custodian: **Housing & Community Services**, not Permit Service Center.

Why this is the right ask:
- it is a **named artifact the City already produces** — the §1 tactic;
- it is **row-level Table A2**, which is precisely the eight missing fields in §4;
- it **eliminates PDF extraction entirely** — no parser to trust, no last-date anchoring;
- it makes our reconstruction independently checkable by anyone, which is the whole point of the
  Possibility Lab conversation.

Note the role discipline: the workbook is an **oracle, a reconcile target — never a data source**
(CLAUDE.md rule 1). It answers "what did the City report," not "what is true." That is its value
here: it is what we are trying to verify against, and today we only have a PDF rendering of it.

### B. The report the City runs to *fill* Table A2

Staff must run *something* against Accela to populate the form. Ask what it is called, then ask for
its output — same tactic, one step earlier in their workflow:

> Please identify by name any report, query or export the City runs from its permitting or housing
> system to compile Table A2 of the Annual Progress Report, and produce that report's output for
> calendar years 2018 through 2025 in electronic format.

If the answer is "staff assemble it by hand," **that answer is itself the finding** — and it is the
strongest possible evidence for the open-data argument in the mayor deck and the Possibility Lab
email.

### C. The missing fields as an Accela export — with the either/or already built in

Only if A and B fail. Reuse the #26-1972 follow-up framing, which forces a written answer:

> For each building permit, produce: deed-restricted affordable unit counts by income category;
> tenure; bedroom count; the associated planning/zoning application number; date deemed complete;
> entitlement/final-action date; certificate-of-occupancy or building-final date; and any
> streamlining provision applied. **Either** produce these as maintained in the permitting system,
> **or** confirm in writing that the City does not maintain them in queryable or exportable form,
> and identify where that information is recorded. If some fall under the first and some the second,
> please say which is which.

### D. Two cheap fixes to the report we already get

Add to any future refresh of the BP report — each answers a §3 defect:

1. **the parent / master permit number as its own column** (fixes (b), the 12.8× inflation);
2. **a stated scope rule and a snapshot date** on the banner (fixes (d) and (e));
3. and note that `Completed`/`Completed Date` arrive empty (a), in case that is unintended.

---

## 7. Boilerplate to carry over

- Gov. Code **§ 7920.000 et seq.** (CPRA), **§ 7922.570** (electronic format — *"in the format in
  which it is maintained, rather than as PDF or a paginated report"*).
- **§ 7922.525** — if any portion is withheld, cite the exemption for that portion and produce the
  remainder.
- Request a **cost estimate before processing** and its statutory basis.
- File via **records.cityofberkeley.info** (NextRequest), as with 26-1368 and 26-1972.
- **Keep A separate from C.** A is a re-production of an existing document and should be fast; C is
  novel and will be slow. Bundling them lets the slow half delay the fast half — the same reason
  #26-1972 was split in two.

---

## Open CPRA state as of this note

| # | Subject | Status |
|---|---|---|
| 26-1368 | BP Annual Permit Report 2018-2022 | ✅ fulfilled 2026-05-20 |
| — | BP Annual Permit Report 2023-2025 | ✅ fulfilled ~2026-04-20 |
| 26-1972 | 2026 refresh + planning pathways/fees | responsive-but-hollow; follow-up submitted 2026-08-10, **no reply on record** |
| 26-2306 | Clariti contract | filed 2026-08-09, **awaiting response** |
| *(new)* | **APR submission workbooks, CY2018–2025** | **not drafted** — recommended above |
