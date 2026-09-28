---
title: "Policy brief: open API access to Berkeley permit data"
date: 
type: note
status: record
area: notes
---

# Policy brief: open API access to Berkeley permit data

**To:** Members of the Berkeley City Council
**From:** John Gage, Berkeley Civic Action / berkeleybuild.com
**Date:** 2026-05-23
**Subject:** Strengthening Berkeley's open data infrastructure to include programmatic API access for the full housing permitting pipeline — and ensuring the new Clariti permitting system, currently being implemented, ships with API access as a first-class feature

---

## Executive summary

Berkeley publishes housing data through the [Open Data Portal](https://data.cityofberkeley.info/) and the [Open Government Ordinance](https://berkeleyca.gov/your-government/public-records/open-government-ordinance) provides strong legal access guarantees. But the city's permitting system — Accela Citizen Access — provides **no programmatic API for housing permit data**. To analyze permit pipeline outcomes (filing → entitlement → permit issuance → construction → completion), independent researchers, advocacy organizations, and journalists must scrape the public portal one page at a time.

Berkeley is currently implementing a new permitting system from [Clariti](https://www.claritisoftware.com/) (per the [October 2024 RFP](https://berkeleyca.gov/sites/default/files/documents/24-11661-C_Comprehensive%20Permit%20Management%20Software%20Solution.pdf)). This implementation is the once-in-a-decade opportunity to require API access as a contractual deliverable, ensuring future researchers will not face the same costs that present researchers have faced.

This brief documents the costs of the current system using real numbers from our work, demonstrates the value of peer-city API access (San Francisco, Oakland, San Diego), and proposes concrete contract terms for Berkeley's Clariti implementation. The work to support this brief was completed using AI-assisted scrapers and validation tools — itself an indicator that civic data accessibility now matters even more, because AI tools are democratizing analysis but cannot work miracles on systems that don't expose data programmatically.

---

## What we have built and what it cost

Berkeley Civic Action's housing pipeline database (berkeleybuild.com) tracks 181 housing projects through Berkeley's permit pipeline. As of May 23, 2026, the database contains:

- 181 normalized project rows
- 174+ permit records (CPRA-sourced for 2018-2025) plus 105 verified Accela master capID triplets
- 2,347 v2 project_events covering planning, zoning, building permit stages
- 441 fee records (aggregated totals only — no per-fee breakdown without expensive scraping)
- 6,303 inspection records covering 92 active or recently-finaled building permits
- 1,423 document attachment references
- 67 city staff identified across planning and inspection roles
- 157 manually-scraped Accela page captures totaling ~855 KB

### Methods used to build this

Because Accela exposes no API, every datum above was acquired by one of the following methods, in order of how expensive each was per project:

| Method | Effort per project | Reliability | Examples |
|---|---|---|---|
| CPRA records request (one-time bulk) | Hours per request, weeks to fulfill | High, but stale once received | The 2018-2025 building permits bulk export |
| Manual Chrome sidebar scraping | 20-30 min per project | Variable; multiple format rewrites required | The 157 .txt corpus files; 90+ projects |
| Headless HTTP scraping (last 30 days) | Seconds per permit, automated | High; verified 100% match to UI | URL discovery (102 permits), inspection scraping (92 permits), record-status scraping (107 permits) |

The headless scraping required substantial AI-assisted development:

- **URL discovery scraper** (yesterday, 2026-05-22): ~6 hours of design and build to develop, then ~30 minutes of supervised runtime across 105 permits. Recovered 100% after a critical bug fix mid-development.
- **Inspection scraper** (2026-05-22): ~3 hours of design and build, ~25 minutes runtime across 92 permits. Captures 6,303 inspection records.
- **Record-status scraper** (today, 2026-05-23): ~1 hour of design and build, ~3 minutes runtime across 107 permits. Reveals the authoritative permit-level state.
- **Processing-status scraper** (today, 2026-05-23): ~2 hours of design and build, ~45 minutes runtime across 107 permits. Captures full workflow history including current bottleneck state.

**Total of ~12-15 hours of skilled development work to acquire data that an API would provide in a single function call.**

### What we still can't get

Even after this scraping infrastructure, we still face systematic gaps:

- **Per-fee detail**: Berkeley collects rich fee data (we observed 17 separate "Plan Check Fee – Building Revisions" totaling >$1.4M for one 144-unit project) but Accela aggregates fees at the permit level. The detail is in the inspection record card scans, which are not machine-readable PDFs.
- **Certificate of Occupancy data**: Berkeley does not issue a single canonical CofO document. Instead, Accela's workflow contains 9 distinct CofO-named stages (Zoning CofO Review, Fire CofO Review, Public Works CofO Review, Inspector Final CofO Review, etc.) — a multi-departmental review process that produces an inspector-signed final inspection card as the closing artifact. We discovered this only by scraping the Processing Status workflow of 107 permits. **This is canonical permit-status data that Berkeley has internally and the public cannot query.** For the HCD APR (Annual Progress Report) we are required to provide a CO date for every project; lacking API access, every Berkeley researcher must independently rediscover this workflow structure and derive their own CO-equivalent date. A defensible derivation rule (the date when the last CofO Review department signed off) exists — but it took ~2 hours of scraper development and 36 minutes of runtime to discover.
- **Plan-check correction cycles**: We observed one project requiring 4 review cycles ("4th and Subsequent Review" fee). Whether Berkeley's correction cycles correlate with project size, fee size, or applicant identity is critical to understanding the cost-of-housing puzzle, but answering it requires scraping every project's Processing Status page individually.
- **Cross-project staff workload**: We have 67 identified city staff names. Connecting their names to specific permits requires reading every permit's Processing Status individually. We have not done this at scale.

### What we cannot do that an API would enable

- Daily refresh of housing pipeline state. (Today our data is up to ~5 weeks stale on average across the 181 projects.)
- Real-time monitoring of new permit applications, new entitlement approvals, or new building permit issuances.
- Project-level reporting on time-to-permit, fees-by-category-by-project, staff-hours-per-project-stage.
- Verification of HCD APR submissions against authoritative source data.
- Cross-city comparisons (Berkeley vs Oakland vs San Francisco), because we cannot scrape three cities in parallel at scale.

---

## How peer cities compare

### San Francisco (DataSF + Socrata)

San Francisco publishes building permits through [DataSF](https://data.sfgov.org/), powered by the Socrata Open Data API (SODA). The result:

- [Building Permits dataset](https://data.sfgov.org/Housing-and-Buildings/Building-Permits/i98e-djp9) is queryable via a standard REST API.
- Datasets covering business locations, property assessments, complaints, violations, inspections, and addenda are all programmatically accessible.
- An independent developer can build a [permits MCP server with 21 tools](https://glama.ai/mcp/servers/tbrennem-source/sf-permits-mcp) accessing all this data without coordinating with city staff.

**Note:** San Francisco is currently implementing its own Clariti system (the PermitSF initiative), with [September 2025 project status reports](https://sfpublicworks.org/sites/default/files/Commissions/Sept%2011,%202025/Item%205_PWC%20Permitting%20Update%202025-9-11%20%20v910.pdf) suggesting full implementation is in progress. The expectation is that the SODA API endpoints will continue. Berkeley should ensure equivalent continuity in its Clariti implementation.

### Oakland (multiple portals, less mature)

Oakland operates several data portals:

- The [Oakland Open Data Portal](https://data.oaklandca.gov/) has datasets on permitting, construction, and building inspections, though the API access is less mature than DataSF's.
- The [Access Oakland portal](https://accessoakland.oakgov.com/) and [Open Oakland community dataset](https://data.openoakland.org/dataset/building-permits-0) provide additional building permit access.
- For older or complex projects, Oakland still relies on a [Records Request workflow](https://www.oaklandca.gov/Planning-Building/Planning-Building-Records-Requests).

Even Oakland's intermediate-maturity API access is materially better than Berkeley's complete absence of API access.

### Los Angeles (Clariti, in implementation)

The [Los Angeles Department of Building and Safety](https://www.unisys.com/news-release/city-of-los-angeles-selects-clariti-and-unisys-for-new-permitting-system-and-implementation/) selected Clariti in November 2024 to replace its current system. LADBS issued 167,000+ permits in 2023; the implementation will affect 1 million inspections per year. Whether LA's Clariti implementation includes API access remains to be seen. Berkeley can position itself ahead of LA on this dimension.

### What this comparison tells us

Berkeley is one of California's most academically and technically capable cities (UC Berkeley researchers, BITSS at the Center for Effective Global Action, Code for Berkeley, and many other civic-tech volunteers). The absence of API access for permit data leaves all this expertise blocked from contributing to housing pipeline analysis at scale.

---

## Lessons learned (from 60+ days of building berkeleybuild.com)

In approximate order of how much pain each caused:

**1. Per-project scraping does not scale.** The 30-second-per-page Chrome sidebar workflow we used for the first 90 projects required 45 hours of human attention. Headless scraping (developed in the last 30 days) cut this to seconds per project, but only after weeks of AI-assisted development.

**2. Berkeley's web portal evolves silently.** Between February and May 2026, Accela's URL parameters changed at least twice. Our scrapers required redesign each time. An API contract would freeze the interface and force change-control through normal version-bump procedures.

**3. Format drift on manual scrapes is catastrophic.** Our Chrome-sidebar scrapes used at least 10 different output formats over 2 months because each Claude session invented its own conventions. We rebuilt our parsers 10 times. Structured data formats prevent this entirely.

**4. Cross-table lookups require scraping multiple pages per project.** A single Berkeley housing project has on average 4-7 permits, each with its own Processing Status, Fees, Inspections, Attachments, and Related Records sections. Building a complete project profile requires ~10 page fetches today. An API would consolidate this to a single query.

**5. Authority is unclear without canonical data.** The most striking finding of our work: Berkeley does not issue standard Certificates of Occupancy. Our project state determinations are derived from heuristics applied to multiple permit-level signals. A clear data model — exposed via API — would make these signals authoritative and reproducible.

**6. The CPRA route is slow and incomplete.** The 2018-2025 building permits bulk export we obtained was helpful, but it omitted critical fields like fees breakdown, CO equivalents, and detailed inspection results. Each subsequent CPRA request takes weeks. APIs return data in seconds.

**7. AI-assisted scraping democratizes but does not solve.** AI tools (like Claude Code and Claude in Chrome) make it possible for independent researchers to build infrastructure that would have required institutional support a decade ago. But AI cannot create canonical data from scraped pages — it can only extract what is exposed. Better data exposure is the multiplier on AI's capability.

---

## What Berkeley should do

### Short term (within 90 days)

**Action 1: Publish what already exists.**

Berkeley's [Open Data Portal](https://data.cityofberkeley.info/) hosts datasets on building footprints, property assessments, and the like. Add building permits as a Socrata-style dataset, updated nightly from Accela's database export. This would not require any change to Accela; it requires only nightly export plus a publishing pipeline.

The Annual Progress Report (HCD-required, Berkeley publishes annually) is the closest analog. Make the underlying data — not just the aggregated APR — available.

**Action 2: Acknowledge the "no CO" reality in policy documentation.**

Document the fact that Berkeley does not issue standard Certificates of Occupancy. Specify which permit-level signal serves as the CO equivalent for HCD reporting. Make this policy visible. Currently, every Berkeley housing data analyst must rediscover this fact independently, often after substantial work has been wasted.

### Long term (in the Clariti implementation contract)

Berkeley is implementing Clariti. The contract is the leverage point.

The Clariti platform [supports flexible APIs](https://www.claritisoftware.com/products/enterprise-permitting-software). Berkeley should require their use to be exposed to the public. Specific contract terms should include:

---

## Proposed Clariti contract terms

(For inclusion in the contract being negotiated between Berkeley and Clariti, or in a contract amendment if execution has already begun.)

### A. Public API access — mandatory

**A.1.** The Clariti platform shall expose a public, read-only REST or GraphQL API providing access to:
- All issued and pending building permits and their full metadata
- All planning and zoning permit applications
- Processing status workflows for every record, including stage names, dates, assigned staff, and current step
- Fees data (per-fee, not aggregate)
- Inspection records, including type, date, result, and inspector
- Document attachments and their metadata (filename, date, type)
- Related Records relationships between permits

**A.2.** API access shall not require authentication for read-only queries. Authentication may be required for write access (e.g., from other city systems).

**A.3.** API documentation shall be public, versioned, and maintained in accordance with current industry standards (OpenAPI 3.x or equivalent).

**A.4.** Where personal data (e.g., applicant phone numbers, certain medical accommodations) is collected by the system, the API shall enforce field-level access controls but shall not block access to public-record metadata.

### B. Data freshness

**B.1.** API data shall be no more than 24 hours stale relative to the internal Clariti database.

**B.2.** Each API response shall include a `last_updated_at` timestamp at the record level.

**B.3.** Webhook-style notifications shall be available so that downstream consumers can refresh in near-real-time.

### C. Schema stability

**C.1.** API schemas shall be versioned. Breaking changes shall require a deprecation period of at least 12 months with the prior version remaining functional.

**C.2.** Schema documentation shall include data dictionaries explaining field semantics. Specifically, fields like "Record Status" shall be documented with their full vocabulary (e.g., "Issued," "Finaled," "Closed Expired," "Withdrawn"), including what each value means in workflow terms.

**C.3.** Where Berkeley uses a derived or heuristic field (such as our CO-equivalent date), this shall be explicitly documented as derived, with the derivation rule exposed.

### D. Export

**D.1.** Bulk export of all read-accessible data shall be available in JSON, CSV, and Parquet formats.

**D.2.** Exports shall be available at no charge to users querying less than 1 GB per day.

**D.3.** Historical data going back to at least 2010 shall be accessible at parity with current data, recognizing that some older records may have less detail.

### E. Specific Berkeley needs (because of the no-CO reality)

**E.1.** The API shall expose, for each housing project, a `project_completion_signal` field with explicit derivation rules documented in the data dictionary. The signal shall use Accela's internal CofO workflow data (Berkeley has 9 CofO-named workflow stages: Zoning CofO Review, Fire CofO Review, Public Works CofO Review, Traffic CofO Review, Design CofO Review, Toxics CofO Review, Inspector CofO Review, Inspector Final CofO Review, and a "Certificate of Occupancy" stage). The derivation rule shall be:
- If all required CofO Review stages are complete: `CO_date = max(completion_date across CofO stages)`
- Else if the master permit is Finaled and no CofO workflow ran (e.g., small alterations): `CO_date = master permit Finaled date`
- Else: `CO_date = NULL` (project not completed)

This field shall be Berkeley's authoritative CO-equivalent statistic for HCD APR reporting. Until this is published via API, every researcher must independently scrape and rediscover Berkeley's CofO workflow structure.

**E.2.** The API shall expose, for each housing project, the `master_permit_id` — the single permit that authoritatively defines the project's state. This addresses the multi-permit / multi-revision complication that today requires every researcher to redefine independently.

**E.3.** Fees data shall be itemized, not aggregated. Each fee shall include category (Plan Check, Building Permit, Impact Fee, In-Lieu BMR, etc.), amount, payment date, and the permit it applies to.

### F. Performance

**F.1.** API responses for individual permit lookups shall return in <1 second under normal load.

**F.2.** Batch queries (e.g., "all permits in Council District 4") shall return within 30 seconds under normal load.

**F.3.** A query rate of at least 1,000 requests per hour per unauthenticated client shall be supported.

### G. Future-proofing

**G.1.** Berkeley shall retain the right to publish any data from the Clariti system to other open-data platforms (DataSF, ArcGIS Hub, data.ca.gov, etc.) without additional licensing fees.

**G.2.** API access shall not be deprecated upon contract termination. Successor systems shall continue to expose equivalent API endpoints.

**G.3.** Berkeley shall reserve the right to require Clariti to provide written documentation of the data dictionary, schema, and API surface area at any point during the contract.

### H. Accountability

**H.1.** Berkeley shall publish a quarterly "API health report" — uptime, query volume, error rates, and freshness statistics. Public visibility into API performance is essential for civic trust.

**H.2.** The City Manager shall designate a staff liaison for civic data users who can resolve API questions and act as the primary point of contact for the open-data community.

---

## The state-law question: what would make every city comparable

Berkeley can fix Berkeley in the Clariti contract. It cannot make itself *comparable* to Oakland or
Fresno, and comparability is the point — a measurement of progress that cannot be set beside another
city's is an assertion, not a measurement. That requires a lever above the city.

### The Annual Progress Report is not a record; it is a computation over records

This distinction decides which law applies. The California Public Records Act gives access to records
that **exist**. An APR is a *derived* quantity — a report assembled from permit records under HCD's
definitions. So "extend CPRA to real-time APR calls" asks the wrong statute for the wrong object.

The right ask is **real-time access to the underlying permit records**. Then any party — the City, HCD,
a journalist, a neighbouring city's staff — computes the APR continuously, from the same inputs, by a
published rule. The report becomes a query.

### Why CPRA cannot carry a real-time feed

Three structural features, none of them accidental:

1. **Retrospective and per-request.** There is no standing or subscription request; each request reaches
   records existing at that moment. A feed is a continuing obligation CPRA does not create.
2. **Its clock is a determination in 10 days, with extensions.** "Promptly" is not real time.
3. **It compels neither format, schema stability, nor interface.** The electronic-records provision
   requires a format the agency *holds* — a spreadsheet export satisfies it. Agencies may also charge
   for data compilation, extraction or programming.

Making CPRA deliver a feed converts it from an access statute into a **service-provision mandate** for
every agency in the state, including the many with no IT capacity. That is a large change, it would be
contested for years, and it is not necessary to get what we need.

### The one CPRA amendment worth wanting, and it is narrow

> **No interface downgrade.** Where an agency already publishes a record to the public through an
> interactive portal, it shall also make that record available in a documented, machine-readable form.

*Public to a human, public to a machine.* This mandates no new data collection, burdens no jurisdiction
that publishes nothing, and reaches precisely our situation. Berkeley's processing-status workflow **is
already public** — any browser renders it. Reading 1,786 Planning records of it required a purpose-built
browser framework and a workaround for a portal session that stops returning data after about four
views. **The inaccessibility is an artifact of interface, not of policy**, and that is the narrowest
possible thing to legislate.

### But the primary lever is HCD, and it is rulemaking rather than legislation

APRs exist under Gov. Code § 65400, with HCD specifying the forms and content. HCD already compels this
data annually from every jurisdiction and already republishes it. If HCD required **record-level
structured submission, continuously or quarterly, through a documented endpoint**, real-time APR
follows without touching CPRA — and it arrives uniformly across all ~540 California cities and counties
instead of one contract at a time.

HCD also has enforcement leverage CPRA lacks: housing-element compliance findings, and SB 35
streamlining eligibility, already turn on APR data.

**This is a rulemaking petition, not a bill.**

### The comparability argument, which is the strongest one

HCD collects an APR from every California jurisdiction and publishes them together, which invites
comparison. **Today that comparison is unsound, and Berkeley is the proof.**

- **Berkeley issues no standard Certificate of Occupancy.** Its permitting workflow contains nine
  distinct CofO-named review stages. Berkeley's "CO date" is therefore a *derived* value, and the
  derivation rule is nowhere published. Every jurisdiction with a non-standard completion process is in
  the same position, each deriving differently.
- **An independent reconstruction of ONE city's APR, built from that city's own source records,
  disagrees with that city's own filing in 84 of 779 rows** — 60 completions the City filed that the
  reconstruction does not carry, 24 the reconstruction carries that the City did not file. Some of
  those are our defects and some are the City's; the point is that **the disagreement is invisible
  from the APR alone.**
- If a single city cannot be reconciled against itself without record-level access, then a table
  ranking 540 cities against each other cannot mean what it appears to mean.

**What becomes genuinely comparable once record-level workflow data is exposed** — and these are
measurements, not opinions:

| metric | why it is comparable across cities |
|---|---|
| **days from application filed to application accepted** | every jurisdiction has an intake step; the dates are the city's own |
| **performance against the city's OWN stated due date** | each city sets its own deadline, so the comparison is each city against its own promise, not against a state average. Berkeley's median is **12 days late**, p90 **+216** |
| **who held the clock at each step** | the disposition vocabulary names it ("Incomplete Pending Applicant" vs "Resubmittal Pending Staff"); no model or judgement required |
| **share of housing on a ministerial path** | measured as the fraction moving to a record type whose disposition vocabulary contains **no** refusal step. A statutory framework (SB 9, SB 35, SB 423, AB 2011) applies identically statewide, so this is the cleanest cross-city measure of by-right reform actually taking effect |
| **iteration count before acceptance** | Berkeley's discretionary design-review records average **2.6** completeness dispositions each; the by-right path has **one** |

Note what is *not* on that list: nothing requiring a jurisdiction to adopt a new definition, and nothing
requiring HCD to arbitrate. Each metric is computed from dates and vocabulary the city already records
for its own operational purposes.

### Three levers, three horizons, and they are complementary

| lever | horizon | what it needs | what it gets |
|---|---|---|---|
| **Clariti procurement** | now | a contract clause | Berkeley, and a working example |
| **HCD rulemaking** | 1–2 years | a petition | all ~540 jurisdictions, uniformly |
| **CPRA amendment** | 2+ years, contested | a bill | a backstop where portals exist but endpoints do not |

The Clariti contract creates the **proof**; HCD **generalises** it; a narrow CPRA amendment **backstops**
it. Pursuing only the third is the slowest route to the least. Pursuing the first alone fixes one city
and leaves the comparison impossible.

### The specific asks

1. **Berkeley:** the contract terms above, plus publication of its CO-equivalent derivation rule — so
   that anyone recomputing Berkeley's APR gets Berkeley's answer.
2. **HCD:** a rulemaking petition for record-level, continuously-submitted APR data through a
   documented endpoint, with each jurisdiction's completion-signal derivation rule published alongside.
3. **The Legislature:** the no-interface-downgrade principle, as narrow as stated above.

*This section is analysis, not legal advice; statutory citations should be confirmed against the
current codification (the CPRA was recodified in 2023 to Gov. Code § 7920 et seq.).*

---

## The vision

Berkeley should aim to be the example of an independent permit pipeline database that is open to queries on all aspects of the pipeline — fees, costs, timelines, delays, and outcomes. We want to track every housing proposal to see if any project actually built and brought to market any housing at any price or income level.

That ambition requires Berkeley to be more transparent than its peer cities, not less. Berkeley already leads on housing policy (Density Bonus, SB35 streamlining, BMR programs). Berkeley should lead on housing data infrastructure as well.

The cost is small: marginal staff time to configure the Clariti API access, and contract negotiation to ensure these terms are in place. The benefit is substantial: every Berkeley researcher, journalist, advocate, and community member would gain instant access to the data that is currently locked behind hours of expert-only scraping work.

Our work over the past 60 days demonstrates what's possible when one motivated independent researcher uses AI-assisted scraping tools. With actual API access, this work could be replicated and extended by dozens of others, with verifiable accuracy, and at the scale Berkeley deserves.

---

## Evidence update, 2026-09-28 — what four months of building since this brief now proves

Everything below is measured, not estimated, and all of it postdates the 2026-05-23 draft. It is here
because the Clariti implementation contract is the once-a-decade moment to fix it, and because each
item is a *missing field*, not a missing feature.

### The parcel mapping is essentially solved; identity is not

**32,055 of 32,897 permits (97.4%) join directly to one of the 29,122 current assessor parcels**; 841
remain, almost all re-plats. Berkeley's permit data is small — ~33,000 permits, ~1,200 housing
structures, on 3.7% of parcels. **The obstacle was never volume.** It is that the records do not
contain the entity the work needs (a building), and state the facts that matter in prose.

The cost of that, concretely: 259 live scripts and 183 database files to track **1,189 structures** —
22 scripts per 100 structures. Most of that apparatus exists to parse English and reconcile
disagreeing sources. An API with the right fields deletes it.

### Six fields, each of which cost weeks

**1. Unit counts as integers, not prose.** `ZP2022-0046` — 3000 Shattuck, ten storeys, *"with 166
dwellings"* — was excluded from a housing query because the pattern matched `dwelling` and not the
plural. A 166-dwelling tower, lost to a word boundary; two further patch rounds found more classes of
miss. **`units_total` / `units_added` / `units_removed` as integers retires the single most expensive
defect class in four months of work.** Where the City's own fields are known-wrong (0 on junior ADUs,
a building total repeated on each phase permit), the API should expose the raw field *and* document the
error, not silently correct it.

**2. Workflow tasks with the City's own due dates.** This brief described scraping 107 permits. That is
now **1,786 Planning records**, and the result is the City's own performance record: acceptance of a
housing application runs a **median 12 days past the due date the City set for itself**, p90 **+216
days**. Also measurable only from workflow: which party held the clock at each step, because the
disposition strings say so (`Incomplete Pending Applicant` vs `Resubmittal Pending Staff`). None of
this is derived or inferred — the City writes it down and publishes it to a browser.

**3. `relationship` REQUIRED on related records.** Across 32,897 permits, exactly **4** link a zoning
approval to its building permit. The entitlement→construction bridge does not exist in
machine-readable form, and an untyped reference cannot substitute: *"refer to BP # B2016-05399 for
Demo"* is not a parent; *"Use Permit Modification of ZP2016-0117"* is. Required values:
`parent`, `child`, `modification_of`, `phase_of`, `references`.

**4. Addresses must name their assigning authority.** One parcel, three answers: Planning files it
"0 Le Roy Ave", the County assessor's situs is blank, the City's address-point layer says
**1463 Le Roy Ave**. Elsewhere the County says *Grizzly Peak* where the City says *Latham*.
"Unnumbered" was never a fact about the parcel, only about who was asked.

**5. A building identifier, or a typed `phase_of`.** Logan Park South is **one** 69-unit building under
two phase permits — counted per permit it doubles. Acheson Commons is **four** buildings at one address
totalling 205 units — grouped by address they merge. Both are currently inferred from prose, where
*"Building a new house"* parses as Building **A** and *"first of two detached houses"* looks like a
phase but names a second house. **If Clariti does not maintain building identity, the contract should
say so explicitly** — that answer is worth more than a guess.

**6. APN history across re-plats.** Acheson was re-platted mid-project and its old APN vanished from
the assessor; a parcel sweep silently missed a 308-unit development, and a naive normalizer once
reported 890 of 892 parcels dead. `apn_prior[]` / `apn_successor[]` makes re-platting visible.

### Priority, if Clariti can carry only part of it

1. unit counts as integers (§1)
2. workflow tasks with due dates (§2)
3. stable per-document URLs
4. `relationship` required (§3)
5. a `changes?since=` feed — the difference between an annual APR and a current one

Items 1–3 alone would let the independent reconstruction be deleted rather than maintained.

### The acceptance test to write into the contract

> A clean-room implementation, reading only the API, reproduces **Table A of the Housing Element
> Annual Progress Report**, and agrees with the City's submitted APR within a stated tolerance, with
> every disagreement attributable to a documented definitional difference rather than to missing data.

That is the right test because Table A is the City's own statutory product. If it cannot be met, the
gap between the API and Table A *is* the remaining specification.

### What an API does not replace — stated so the ask is credible

Collection, yes: CPRA requests, scraping, the harvester, workflow dates, record links, APN history.
**Judgement, no.** What a permit's prose *means* for housing, correcting the City's own data-entry
errors, applying HCD's definitions (group quarters, gross vs net, phases), affordability and tenure
(which live in regulatory agreements, not permits), and independent verification — a check that merely
echoes the City's own field verifies nothing. With an API the independent role shifts from
*reconstructing* the City's numbers to *auditing* them, which is the more useful posture for both
sides.

---

## Appendix: References

- [Berkeley RFP for Comprehensive Permit Management Software Solution (Oct 2024)](https://berkeleyca.gov/sites/default/files/documents/24-11661-C_Comprehensive%20Permit%20Management%20Software%20Solution.pdf)
- [Berkeley Open Government Ordinance](https://berkeleyca.gov/your-government/public-records/open-government-ordinance)
- [Berkeley Public Records portal](https://berkeleyca.gov/your-government/public-records)
- [San Francisco DataSF Building Permits](https://data.sfgov.org/Housing-and-Buildings/Building-Permits/i98e-djp9)
- [San Francisco Open Data Developer Resources](https://www.sf.gov/resource--2023--open-data-developer-resources)
- [San Francisco PermitSF / Clariti implementation status, September 2025](https://sfpublicworks.org/sites/default/files/Commissions/Sept%2011,%202025/Item%205_PWC%20Permitting%20Update%202025-9-11%20%20v910.pdf)
- [Oakland Open Data Portal](https://data.oaklandca.gov/)
- [Access Oakland portal](https://accessoakland.oakgov.com/)
- [Clariti Enterprise — flexible APIs documentation](https://www.claritisoftware.com/products/enterprise-permitting-software)
- [Los Angeles Clariti implementation announcement (Nov 2024)](https://www.unisys.com/news-release/city-of-los-angeles-selects-clariti-and-unisys-for-new-permitting-system-and-implementation/)
- berkeleybuild.com — the source of the data and analysis cited in this brief

---

**Contact:** John Gage / Berkeley Civic Action / berkeleybuild.com
