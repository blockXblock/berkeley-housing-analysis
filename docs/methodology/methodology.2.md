# Methodology

This page explains how the Berkeley housing pipeline database is built, what it counts, how its numbers are produced, why those numbers may differ from official reports, and how readers can verify or challenge any claim.

The short version: this project is an independent, database-first record of Berkeley's housing development pipeline, assembled from public permit data, parcel data, published reports, and direct observation. Headline numbers on the site should trace back to explicit SQL logic, documented views, or versioned snapshots in the public repository.

> Draft status: This is a working methodology skeleton intended for review and refinement before publication.

## Recommended file structure

To avoid naming overlap, a folder structure is cleaner than a single top-level methodology file.

```text
docs/
  methodology/
    methodology.2.md          # working draft
    methodology.md            # eventual published canonical page
    definitions.md            # glossary of stage, workflow, and unit terms
    sources.md                # source systems and provenance notes
    validation.md             # QA checks and reconciliation rules
    changelog.md              # edits to methodology itself
```

If the project later splits into several repositories, this structure still works well:

- Keep the public-facing narrative methodology in the site or deployment repo.
- Keep schema-specific methodology close to the framework repo.
- Keep city-specific source notes in each city repo.

One possible multi-repo pattern:

```text
civic-permit-pipeline/
  docs/
    schema/
    methodology/
      data-contract.md
      provenance.md
      validation.md

berkeley-permit-pipeline/
  docs/
    methodology/
      methodology.md
      sources.md
      local-decisions.md
      reconciliation.md
```

## Purpose

This database is intended to support public accountability, housing-policy analysis, reproducible reporting, and independent verification of Berkeley housing pipeline claims. It is not an official city reporting system, and it should not be read as a substitute for the City's own statutory filings.

The database is designed to answer questions such as:

- How many units are in Berkeley's active development pipeline?
- Which projects are still in planning review versus approved but not yet permitted?
- Which projects are under construction or completed?
- How do unit counts, affordability counts, and project statuses change over time?
- Where do independent counts differ from city-published counts, and why?

## Scope

### Included

- Residential projects in the City of Berkeley that appear in tracked planning or permit sources.
- New construction, substantial infill, mixed-use projects with residential units, and adaptive reuse where housing production is part of the project.
- Projects that are active, approved, permitted, under construction, completed, stalled, or withdrawn, if they fall within the maintained observation window.

### Excluded or limited

- Accessory Dwelling Units, unless a later scope expansion explicitly adds them.
- Small projects below the maintained project threshold, if the project chooses to keep a threshold.
- Demolition-only permits with no replacement housing.
- Non-residential projects.
- University of California projects on UC-owned land, unless they are explicitly tracked as a separate scoped category.

### Time window

Projects are tracked from their first appearance in a monitored source through completion, withdrawal, archival, or a project-defined inactivity rule.

## Counting rules

### Analytic buckets

The public site may group projects into simplified analytic buckets for readability. These buckets are analytic categories derived from source statuses and dated events; they are not legal determinations.

Suggested public buckets:

- Planning review.
- Approved, pre-permit.
- Permit activity, pre-construction.
- Under construction.
- Completed.
- Withdrawn or inactive.

### Lifecycle vs workflow

Source systems often use one status field to encode two different things:

- A **lifecycle stage**, such as pre-application, review, approved, permitted, under construction, or completed.
- A **workflow state**, such as waiting on staff, waiting on applicant, pending hearing, or pending final action.

Where possible, the database should distinguish between these concepts. If the current implementation still flattens them, the raw source status should still be preserved for auditability.

### Entitled, approved, and finalized

This methodology should define these terms explicitly:

- **Entitled** means a project has received a land-use or planning approval.
- **Approved** may be treated as part of the same analytic bucket when Berkeley source systems use `Approved` and `Entitled` interchangeably for planning approvals.
- **Finalized** or **finaled** building permits refer to construction or inspection completion, not planning entitlement.

## Unit accounting

The project should define several distinct unit measures because they answer different questions.

### Core unit fields

- `total_units`: total units in the project as built or proposed in the relevant version.
- `gross_units_proposed`: new units proposed before subtracting existing units removed.
- `units_demolished`: existing housing units removed by the project.
- `net_new_units`: `gross_units_proposed - units_demolished`.

### Why this matters

Different public reports use different unit concepts. A project replacing existing housing may have a large total unit count but a smaller net addition to Berkeley's housing stock. This distinction should be visible in both the schema and the public methodology.

### Affordability counts

If affordability counts are included, the methodology should specify:

- which affordability categories are tracked;
- whether counts are sourced from regulatory agreements, conditions of approval, permit documents, or inference;
- how confidence levels are assigned when affordability numbers are incomplete or ambiguous.

## Data sources

The methodology should document each source system in plain language.

### Primary sources

- City permit and planning systems.
- Parcel and assessor data.
- City and state housing reports.
- Planning commission and zoning board documents.
- Direct observation and dated photographic evidence.

### Source notes

For each source, document:

- what it is used for;
- known limitations;
- expected refresh cadence;
- the identifier or join method used to connect it to projects;
- whether it is mirrored or archived.

## Provenance

Every substantive fact should have a provenance trail or be traceable to a source record, event, document, observation, or derived transformation.

Suggested provenance concepts to document:

- `source_system`
- `source_record_id`
- `asserted_by`
- `asserted_at`
- `confidence`
- `is_inferred`
- links to source documents, mirrors, or evidence files

The public page should emphasize that corrections, derived values, and inferred events are marked rather than silently merged into source truth.

## Validation and QA

The methodology should explain how the dataset is checked before publication.

Suggested validation categories:

- foreign-key integrity;
- duplicate current versions;
- duplicate current geometries;
- missing required event links;
- unit-count reconciliation;
- orphan documents;
- broken source URLs;
- export parity checks between normalized tables and compatibility views.

This section can later link to a dedicated `validation.md` page with the exact checks.

## Why counts may differ from official reports

Differences from city or state counts do not necessarily mean either source is wrong. They may reflect:

- different definitions of entitled, permitted, completed, or active;
- different reporting windows;
- different treatment of phased projects;
- corrections to source data errors;
- inclusion of direct observations not present in official systems;
- lag between internal city records and public-facing portals.

The methodology should state clearly that official city reports remain the authoritative record of what the city officially reported, while this database is the authoritative record of this project's independently maintained observations and reconciliations.

## Update cadence

This section should describe the expected operating rhythm without overcommitting beyond what is sustainable.

Suggested structure:

### Automated

- Scrape or sync monitored source systems.
- Detect changed statuses, permit activity, and new documents.
- Run validation checks.
- Rebuild exports and public views when validation passes.

### Human review

- Review uncertain matches and deduplication decisions.
- Confirm major unit-count corrections.
- Review observations and stage changes.
- Reconcile against official reports when published.

### Snapshotting

- Generate versioned database snapshots.
- Archive release artifacts.
- Publish selected releases to a long-term repository with a DOI.

## Zenodo

Zenodo is a public research repository used to archive datasets and software releases with persistent DOIs. If this project publishes periodic database snapshots there, readers and researchers should cite the snapshot DOI rather than the live database, because the live database changes over time.

## Limitations

The methodology should explicitly acknowledge limits.

Suggested limitations:

- incomplete visibility into projects outside public city systems;
- inconsistent or messy status data in source systems;
- subjective judgment in observed construction milestones;
- weaker historical completeness in earlier years;
- incomplete affordability documentation for some projects;
- limited visibility into post-occupancy outcomes such as rents, tenure stability, or resident characteristics.

## Corrections

Readers should have a clear path to challenge or improve the data.

Suggested correction workflow:

1. Identify the project, metric, or query in dispute.
2. Provide the claimed correct value.
3. Provide documentary evidence or a link to the relevant source.
4. Log the correction publicly.
5. Preserve both the original source claim and the corrected interpretation when useful for transparency.

## Citation and reuse

This section should eventually specify:

- how to cite the database;
- how to cite versioned snapshots;
- software license;
- data license;
- expectations for reuse by researchers, journalists, and other cities.

## Internal link targets to add later

Replace temporary placeholders with stable links to:

- saved queries or Datasette pages;
- schema documentation;
- validation checks;
- changelog entries;
- release snapshots;
- correction log or GitHub issue templates.

## Open drafting questions

These are useful prompts before publishing the canonical methodology page:

- Is the site threshold still five or more units, or should that be reconsidered?
- Should UC projects remain excluded, separately flagged, or partially tracked?
- Will ADUs always remain out of scope?
- How should synthetic entitlement events be described in public-facing language?
- Which public buckets should appear on the homepage versus only in detailed docs?
- How much operational detail belongs here versus in separate validation and sources pages?

## Publication note

When this draft becomes the canonical public page, consider renaming:

- `docs/methodology/methodology.2.md` -> working draft
- `docs/methodology/methodology.md` -> published version

That pattern keeps draft iteration and public naming separate.
