---
title: "CPRA draft — building-permit report refresh #2 (closes the July-to-now gap)"
date: 2026-10-20
type: note
status: draft (John files it via NextRequest; nothing sent)
area: notes
---

# CPRA draft — building-permit report refresh #2

**Why now.** Our permit feed ends 2026-07-07 (the #26-1971 production). NextRequest checked 2026-10-20: no permit-data
request is pending, so completions after June are only what the Accela harvest captures (provisional). The City
granted #26-1971 in 4 days because it is a re-run of a report it already produces; this asks for the same report,
same scope, a later window. **Ask for the window from January 1, 2025, not July:** the 07-07 re-runs showed that a
re-run catches permits whose status changed since the last production (278 gained "Finaled" in the 2023-25 re-run),
and the overlap costs the City nothing.

**After it lands:** download all files the same day (the #26-1971 files sat unretrieved for 11 weeks), log the
fulfillment in `data/raw/cpra-downloads/README.md`, pin each file by SHA-256 in JN-A, never by a filename pattern
(the 2026-10-20 curriculum and S9 failures came from a pattern catching new files).

---

## Request text (paste into records.cityofberkeley.info)

> Under the California Public Records Act (Gov. Code § 7920.000 et seq.), I request a re-run of the "BP Annual Permit
> Report" produced to me in response to request #26-1971 (that production covered Post Date January 1, 2025 to
> July 7, 2026), for the period **Post Date January 1, 2025 through the date this request is fulfilled**, in the same
> electronic format (Excel) and with the same columns.
>
> This is the same report, run with a later end date; I am not asking the City to create a new report. Please include
> permits whose status changed after July 7, 2026 (for example, permits issued earlier and finaled since), as the
> report does when re-run.
>
> If the City's change from Accela to its new permit system (Clariti) affects how or whether this report can be run,
> please let me know, and please produce the report from whichever system holds the records for this period.
>
> Thank you.

---

## Optional second item (a separate request, so it cannot slow the first)

> Any records showing the planned or actual date on which the City's new permit management system (Clariti Cloud Inc.,
> RFP 24-11661-C) replaces Accela for building permits, including the current project schedule, and any records
> describing how permit records from Accela will remain available to the public after that date.

*Why:* the harvest that fills our gap between CPRA productions reads Accela Citizen Access. If Accela goes away, that
path ends, and the #26-2306 release included only a DRAFT schedule (`Berkeley Project Schedule DRAFT.mpp`).
