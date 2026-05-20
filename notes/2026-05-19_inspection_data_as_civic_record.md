Inspection data as permanent civic record
Date: 2026-05-19
Status: Strategic vision document. Surfaced during Accela pipeline reconnaissance. Not yet a committed workstream.
What this document is
While doing reconnaissance for the Accela freshness pipeline (see notes/2026-05-19_accela_pipeline_recon.md), we discovered that the building permit for 2352 Shattuck Ave has 553 inspections recorded — far richer detail than expected. Each inspection is a city inspector's confirmation of a specific aspect of the building's construction: framing, electrical, plumbing, mechanical, fire, accessibility, energy compliance.
This volume of structured data, currently invisible outside Accela's per-permit detail pages, has potential civic value beyond the freshness-pipeline use case. This document captures the vision before it gets lost; whether it becomes a workstream is a separate decision.
The vision
The freshness pipeline answers a transactional question: "is this project complete?" It treats inspections as a binary signal (latest result = freshness sentinel).
An alternative framing treats inspections as a permanent record of building characteristics. Aggregated across Berkeley's 179 tracked housing projects (plus the much larger universe of all building permits citywide), this could become a queryable record of how Berkeley's actual building stock was constructed and what standards it meets.
Examples of questions such a dataset could answer:

How many residential projects in the past 5 years passed Title 24 energy compliance final inspection? Did any fail and require re-inspection?
Across all-electric ordinance-era projects, how often does the gas-line removal inspection appear?
Are heat pump installations being inspected and approved, or are they bypassing inspection?
For projects in the sewer lateral upgrade zone, how many have completed lateral inspection?
What's the distribution of inspection counts per project type?
Which inspectors handle which projects? Are there workload imbalances?
For failed inspections, what's the typical time-to-resolution?

These questions are not currently answerable by Berkeley itself, by journalists, or by researchers. The data exists in Accela but isn't aggregated, structured, or surfaced in any analyzable form.
Why this might matter for housing pipeline accountability
Berkeley has progressive building standards in several domains:

Energy: All-electric ordinance for new construction (2020). Title 24 compliance. Building Energy Saving Ordinance (BESO).
Climate adaptation: Stormwater management (NPDES post-construction requirements for projects 10,000 sq ft and larger).
Public health: Sewer lateral inspection in EBMUD's Private Sewer Lateral program zones.
Habitat: Native plant preservation, oak tree protection ordinance, riparian setback requirements.

Compliance is enforced through plan review (entitlement), permit conditions, and final inspection. Without aggregated inspection data, no one outside Berkeley's permitting department can verify whether progressive ordinances are being effectively enforced in practice.
A queryable inspection record would let residents, advocacy groups, journalists, and researchers independently assess Berkeley's actual climate, sewer, stormwater, and habitat compliance.
Honest caveats and limitations
Not all environmental standards are enforced through individual inspections. Berkeley's all-electric ordinance is mostly enforced via permit conditions and plan review. Stormwater is implemented through engineered site features reviewed at plan stage. Habitat / native plant standards are mostly enforced at entitlement. Title 24 final compliance is signed off but underlying calculations are done by third-party consultants.
So the inspection record captures some of Berkeley's environmental enforcement but is not a complete record.
Inspection notes may not be capturable. CIC's reconnaissance saw inspection rows with date, type, result, and inspector initials — but not inspector notes text. The structured data alone is valuable but less rich than a complete record.
The data is at building-permit level, not project level. A project has multiple permits, each with its own inspection set. Pipeline must aggregate per-project from per-permit data.
The data only exists for buildings already permitted through Accela. Berkeley moved to Accela in the mid-2010s. The dataset would skew strongly toward post-2015 construction.
Berkeley may eventually replace Accela with Clariti. Any pipeline built on Accela becomes obsolete at that point. Hedge: structured data captured before migration retains historical archive value.
What would be required to make this real
Roughly in order of dependency:

The Accela freshness pipeline (Playwright-based). Necessary precondition. Once it works for status updates, the same infrastructure can capture inspection rows.
A new database schema for inspections. Proposed structure (SQLite columns): project_id (FK), permit_number, accela_inspection_id, inspection_type, inspection_type_code, result, result_date, inspector_initials, notes, source_url, source_fetched_at, raw_html_snapshot, data_reliability. Indexes on project_id, permit_number, inspection_type_code, result_date, inspector_initials.
Inspection-type taxonomy. The 4-digit codes (1150, 1200, 2100) are Berkeley's vocabulary. Need to map: code to standard inspection type to environmental standard relevance.
Parsing logic. BeautifulSoup or lxml parser; about 50 lines per row pattern. Reuses the pipeline's authenticated-fetch infrastructure.
Pagination strategy. 553 inspections across 111 pages requires careful pagination, ViewState replay, and incremental capture. Snapshot-diff handles routine refresh; full backfill requires walking all pages once per record.
Storage scale. Hundreds of thousands of rows over 10 years. SQLite handles this. Decision needed on raw HTML snapshots — every row or just summary.
Surface area for analysis. A Datasette interface that lets users query the record. Without this, the data sits in a SQLite file no one reads.

Honest scope assessment
The freshness pipeline alone is multi-session work: 5-10 sessions to a robust daily-running pipeline.
Adding inspection capture as a comprehensive civic record is substantially more work: schema, parsing, historical backfill, taxonomy mapping, surface area, maintenance. A conservative estimate is 6-12 months of part-time work to a complete civic-record system.
A focused version (status + inspection counts + final-inspection dates per project, no per-inspection capture) could be achieved in the same timeline as the freshness pipeline alone.
This document is not a commitment. It's a record of the vision so it's not lost.
Relationship to existing civic data work

The April 2026 transparency ordinance draft specifically calls for project-level data structure and public API access for permit records. Inspection capture is a natural extension.
BuildBerkeley.online currently surfaces project-level pipeline data but no inspection or compliance detail.
HCD's Annual Progress Report focuses on entitlement and permit issuance, not construction compliance. An inspection record would complement APR data with what happens AFTER permit issuance.
The methodology page would need to honestly describe what's captured, what's not, and where the limits are.

Decision needed in a future session
Before any inspection-capture work begins:

Is this a priority workstream, or a "nice to have eventually"?
Full-scope or scoped-down?
Relationship to the freshness pipeline — same code path, separate sub-pipeline, or after freshness is stable?
Public-facing or research-only?

None need to be answered tonight. The vision is captured. The pipeline foundation work is the prerequisite either way.