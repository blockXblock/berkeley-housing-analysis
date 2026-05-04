# Methodology

This page explains how the BlockXBlock Berkeley Housing Pipeline database is built, what it counts, why it sometimes differs from official reports, and how readers can verify or challenge any number. The public site is https://BerkeleyBuild.com

The short version: this project is an independent, database-first record of Berkeley's housing development pipeline, assembled from city permit portals, county assessor data, and direct observation. Every headline number on this site traces back to a SQL query against a public database. If a number looks wrong, the query is linked — run it yourself.

For those unfamiliar with SQL, check out the UC Berkeley classes in data science: Data Science 8. Use Claude or Perplexity, or both in tandem, to create SQL queries to explore your questions.

---

## Scope

**What's in:** Residential housing projects in the City of Berkeley that appear in the city's permit or planning records and involve five or more housing units. This includes new construction, major infill, mixed-use projects with residential components, and adaptive reuse.

**What's out:**

- Accessory Dwelling Units (ADUs). Berkeley's ADU pipeline is large and well-covered by the city's own dashboards. ADUs are not in this database; they are tracked via the city’s own dedicated ADU dashboards.
- Single-family home permits (fewer than five units).
- Demolition-only permits with no replacement housing.
- Non-residential construction.
- University of California projects on UC-owned land, which follow a separate entitlement process outside the city's jurisdiction. We flag these where we see them but don't claim completeness.

**Time range:** Projects are included from their first appearance in any tracked source (typically a planning application filing) through either completion, withdrawal, or five years of inactivity, whichever comes first.

---

## What we count, bucket by bucket

A project's position in the pipeline is recorded as a lifecycle stage. The database uses the following buckets, each backed by a specific database query you can verify. These stages are analytic buckets derived from city statuses and events, not legal categories:

**Planning review (active).** Projects that have filed an application but do not yet have approval. This includes every sub-state of Berkeley's internal workflow — under staff review, waiting on the applicant, scheduled for ZAB, and so on.  The exact definition is encoded as a SQL view in the public database (see v_projects_planning_review in the schema).

**Approved, pre-permit.** Projects with planning approval (status `Entitled` or `Approved` in city data) but no building permit yet issued. This is the entitlement-to-construction gap. 
**Permit-filed, pre-construction.** Projects with building permit or demolition permit activity but no observed construction. Includes "Pending Final Action," "Building Permits Filed," and "Demolition Permits Filed" statuses. 

**Under construction.** Projects with active construction observed or reported. This is the smallest bucket. 
**Completed.** Projects with Certificate of Occupancy issued within the reporting period. 

A note on the Entitled/Approved distinction: Berkeley's Accela system uses both status strings, seemingly interchangeably, for projects that have received planning approval but have not yet pulled building permits. This database treats them as a single analytic bucket. Query: `WHERE status IN ('Entitled', 'Approved')`.

City ‘status’ strings encode two things: where a project is in its lifecycle, and who the work is waiting on. The database separates these into lifecycle stages and workflow states so questions like ‘how many projects are stuck waiting on the applicant?’ are answerable.

In this database, “entitled” means a project has received a land‑use/planning approval (e.g. Zoning/Use Permit decision). “Finalized” building permits, which indicate that construction work and inspections are complete, are treated as completion events, not as entitlements.

---

## Unit accounting

Three unit counts are tracked for every project because they answer different questions:

- **Total units** (`units`) — the headline count, matching how the city typically reports a project's size.
- **Gross units proposed** (`new_units`) — new construction unit count, pre-demolition.
- **Units demolished** (`old_units`) — existing units being removed, for infill projects replacing existing housing.
- **Net new units** (`net_new_units`) — `gross_units_proposed - units_demolished`. Net new units (net_new_units) is the metric that aligns with California HCD’s Annual Progress Report guidance for counting production.

Example: if a 20‑unit project replaces a 10‑unit rent‑controlled building, gross_units_proposed = 20, units_demolished = 10, total_units = 20, and net_new_units = 10.

For greenfield projects on vacant land, all four are equal and `units_demolished` is zero. For infill projects replacing existing rental housing, `total_units` and `net_new_units` can differ substantially, and the difference matters for honest accounting of Berkeley's net housing production.

**Very Low Income (VLI), Low Income (LI), and Moderate Income (MOD)** units are counted from project affordability agreements where they exist, from planning conditions of approval where they don't, and are flagged with a lower confidence value when inferred rather than documented.

---

## Counting student housing: beds vs. units

UC Berkeley student housing projects (and dormitory-style developments generally) are reported by the developer in **beds**, not dwelling units. A traditional dorm room with two beds in a shared room is counted as 2 beds but may correspond to a fraction of a "unit" for planning purposes. Apartment-style student housing with private bedrooms in shared suites has a different ratio.

To make these projects comparable to apartment-style housing in our pipeline, we apply a conversion factor:

> **Student housing total beds × 0.39 ≈ dwelling units**

This factor is derived from UC Berkeley's own reported conversions for Anchor House (1950 Oxford St), where 772 beds corresponds to 300 units. The ratio varies by project depending on unit configuration (traditional dorms vs. apartment-style suites), but 0.39 is a reasonable central estimate for UC Berkeley projects.

**This is an approximation.** The actual bed-to-unit ratio depends on:
- Unit mix (studios vs. 2-bed vs. 4-bed suites)
- Whether beds are in shared or private rooms
- How the developer defines a "unit" for their reporting

When a UC project reports both beds and units, we use the developer's unit count. When only beds are available, we apply the 0.39 conversion factor and flag the unit count as `confidence = 'low'`.

### UC projects in this database

| Project | Address | Beds | Units | Ratio |
|---------|---------|------|-------|-------|
| Channing-Bowditch | 2400 BOWDITCH St | ~1,500 | 750 | 0.50 |
| People's Park | 2556 HASTE St | 1,113 | 556 | 0.50 |
| Bancroft-Fulton | 2200 BANCROFT Way | 1,625 | 550 | 0.34 |
| Anchor House | 1950 OXFORD St | 772 | 300 | 0.39 |

**Note on UC projects and RHNA:** University of California projects on UC-owned land are exempt from city zoning and are not counted toward Berkeley's Regional Housing Needs Allocation (RHNA). They are included in this database for completeness but are flagged as UC projects and excluded from RHNA-reportable totals.

---

Net unit change. We follow HCD's APR methodology and count net change in housing stock. Projects that eliminate units (mergers, demolitions without replacement) are recorded as negative values. This means our totals match RHNA-reportable figures rather than gross-unit-construction figures.

---

## Data sources

**City of Berkeley Accela portal.** The primary source for planning applications, use permits, design review, building permits, and inspection records. Scraped via a targeted adapter that respects the city's rate limits and records every request. Berkeley is expected to migrate from Accela to Clariti; this database's schema is designed to accommodate the transition.

**Alameda County Assessor.** Primary source for parcel geometry, APNs, and lot sizes. Cross-referenced monthly.

**HCD Annual Progress Reports.** Berkeley's own submissions to the California Department of Housing and Community Development. Used to cross-check and occasionally to correct.

**Direct observation.** Site visits, dated photographs, and correspondence with city staff. Events sourced this way are marked `is_inferred = 0`, `source_type = 'observation'` and attributed in the `observed_by` field.Events from on‑the‑ground observation are tagged with asserted_by = 'observation' and medium confidence, and they link to photo or note evidence where possible.

**Public correspondence.** Planning Commission packets, ZAB packets, staff reports, CEQA documents. Mirrored to Internet Archive and Cloudflare R2 so the record survives reorganizations of the city's own document storage.

Every fact in the database carries a provenance record: which source it came from, who or what system asserted it, when, and with what confidence. This is queryable; nothing is a black box.

The provenance fields are first‑class columns in the database, not annotations on this page; you can filter or group by asserted_by and confidence in any query.

---

## How this may differ from official counts

The city of Berkeley and the state of California publish their own housing pipeline numbers. When our counts differ from theirs, the difference is usually traceable to one of the following:

**Methodology differences in what counts as "entitled."** The city's HCD Annual Progress Report follows HCD's statutory definitions, which are specific to the reporting year and exclude some projects (e.g., those entitled in prior years that didn't progress). This database counts all currently-pending entitlements regardless of which year they originated in. Both are correct for their purposes; they answer different questions.

**Timing lag.** City dashboards update on varying schedules. This database updates weekly and is typically more current on the planning-review side. Conversely, the city sometimes has advance information about permit issuances that hasn't appeared in the public Accela feed yet, in which case the city will be more current.

**Inclusion of projects the city doesn't count in a given report.** HCD reporting categorizes projects narrowly; this database includes the full pipeline. So for example a project in design review that has not yet been approved won't appear in an HCD "entitled" count but will appear in our "planning review" bucket.

**Correction of errors.** Where we've found clear data errors in city sources — duplicate project entries, unit counts that don't match the approved plans, addresses that don't resolve — we've corrected them, documented the correction, and flagged the original source. All corrections are logged with `asserted_by = 'correction'` and a link to the evidence.

**Observations the city doesn't make.** Construction-start dates, topping-out dates, and similar milestones are often not recorded in the city's permit data. We record them when we observe them directly. These carry lower confidence than city-recorded facts and are marked accordingly.

When in doubt, the city's own published numbers are the authoritative source for what the city has officially reported; this database is the authoritative source for what we have independently observed and documented. Both have value.

---

## Update cadence

The pipeline will be maintained on the following aspirational cadence, which will improve as we add resources:

**Daily (automated).**
- Accela scraper runs at 03:00 Pacific to pull newly-filed applications, permit status changes, and newly-issued permits. Results written to a staging table; the scraper refuses to overwrite existing records without manual approval.
- URL verification job checks a rolling sample of document `source_url` fields to detect link rot. Broken URLs flagged `url_status = 'broken'` and queued for re-mirroring from the Internet Archive or R2.

**Weekly (automated + human review).**
- Monday: the week's staging-table rows are reviewed against existing project records. New projects are created; matches to existing projects are applied as updates or new events. Organizations are deduplicated by normalized name.
- Tuesday: document mirroring pipeline runs. Any PDF referenced in new records is downloaded, SHA-256 hashed, and pushed to all three mirrors (Internet Archive, Cloudflare R2, Google Drive).
- Wednesday: the validation suite runs. Any failing check blocks the weekly export. Failures are investigated before proceeding.
- Thursday: if validation passes, CSV/JSON/GeoJSON/KML exports regenerate from the database via the compatibility views. The public Datasette instance is redeployed pointing at the fresh database.
- Friday: publication snapshot is taken. The full database is dumped to a timestamped file in `snapshots/`, committed to git, tagged as `vYYYY.WW-weekly`, and (on a monthly or report-triggered cadence) released to Zenodo with a new DOI.

**Monthly (human review).**
- Parcel geometry refresh from Alameda County assessor.
- Site observations: a pass through active-construction projects to photograph and update construction stage.
- Reconciliation against city HCD APR submissions when they're published.

**As-needed.**
- Project-level correspondence with city staff when data anomalies warrant follow-up.
- Investigation of reader-submitted corrections.
- Publication of full Citizen APR reports tied to the city's own APR cycle.

The week's activity is summarized in a brief `docs/changelog/YYYY-WW.md` file so readers can see what moved and why.

---

## Limitations

**Projects outside Accela.** If a project never files with the city — for example, a small-scale rental conversion that doesn't require a permit — we won't see it. This database reflects the pipeline of projects the city can see, which is not the totality of housing activity in Berkeley.

**Accela data quality.** The source system has known data issues: inconsistent status strings, free-form address fields that don't always geocode, permit numbers that don't match across modules. We clean what we can and flag what we can't.

**Subjective boundary decisions.** "When did construction start?" is a judgment call; different observers will draw the line differently. Our observations are dated and attributed so readers can apply their own threshold.

**Historical completeness.** Data coverage is strongest for projects that entered the pipeline after roughly 2019, when Accela became the city's primary system. Earlier projects are represented where documented but shouldn't be treated as a complete record of Berkeley's housing history.

**Demographics, rent, and outcomes.** This database tracks the permit pipeline, not post-occupancy outcomes. It does not include actual rents, tenure stability, or resident demographics. Those questions require different data sources.

---

## Citation and reuse

Every published snapshot of this database is archived on Zenodo with a Digital Object Identifier (DOI). Academic and journalistic citations should reference the specific DOI used, not the live database, because live data changes.

Zenodo is a public, long-term research data repository operated by CERN, widely used to archive datasets with DOIs so they can be cited like papers.

The software, schema, and documentation are licensed under Apache License 2.0. The data is licensed under Creative Commons Attribution 4.0 (CC-BY 4.0). Cite as:

Berkeley Open Data (2026). BlockXBlock Berkeley Housing Pipeline [Version 2026.04-initial]. Zenodo. DOI forthcoming.
Note: Zenodo registration is in process; this citation will be updated with a DOI when available.

Forks for other jurisdictions are encouraged. A cross-city data contract is maintained so other cities can adopt the same schema with their own local vocabulary and source-system adapters. See [`docs/new-city-checklist.md`](./new-city-checklist.md).

---

## Corrections

If you believe a specific number in this database is wrong, please open an issue at the project's GitHub repository at https://github.com/blockXblock/berkeley-housing-analysis with:

1. The project or query in question.
2. The number you're disputing.
3. The source you believe is authoritative.
4. A permalink to the source, if available.

Corrections with documented sources are applied promptly and logged in the weekly changelog. The correction history is itself part of the database, queryable via the `asserted_by = 'correction'` filter on any fact table.

We do not take corrections from anonymous sources when the correction claim lacks documentation. This is not a reflection on the corrector; it's a reflection on the standard of defensibility this database is held to.

---

*Last reviewed: 2026-05-02. This methodology page is versioned; its history is in the project's git repository.*
