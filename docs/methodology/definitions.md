# Definitions

This page defines key terms used in the Berkeley housing pipeline database and on the public site. The goal is to keep everyday language aligned with the underlying schema, so that readers, collaborators, and future cities all mean the same thing when they use a term.

> Draft status: working glossary to accompany `methodology.2.md`.

## Project and pipeline

**Project**  
A distinct development proposal or construction effort that adds, removes, or substantially alters housing units on one or more parcels. A project may span multiple permits and phases but is tracked as a single logical record.

**Pipeline**  
The set of projects that are not yet fully completed or that remain within a defined observation window. Depending on context, this may mean “all active projects” or “all projects with any activity in the last N years.”

## Stages and workflow

### Lifecycle stage

**Lifecycle stage**  
An analytic category describing where a project is in the development process, regardless of who is currently doing work on it. Examples include pre-application, in review, entitled, permitted, under construction, completed, and withdrawn.

Lifecycle stages are designed for questions like:
- How many units are still in planning review?
- How many units are entitled but not yet permitted?
- How many units are under construction or completed?

### Workflow state

**Workflow state**  
An analytic category describing who the next move belongs to in an active review or permit process. Examples include waiting on staff, waiting on applicant, pending hearing, and pending final action.

Not all implementations separate lifecycle and workflow yet, but the distinction is useful for questions like “how many projects are stalled on the applicant’s side?” versus “how many are in review at all?”

## Entitlements, permits, and completion

**Entitlement**  
A land-use or planning approval that authorizes a proposed use, density, or form under the city’s zoning and planning rules. Examples include Zoning Certificates, Use Permits, Variances, and similar approvals. Entitlement is about legal permission to build in principle.

**Planning approval**  
A decision by the planning or zoning authority that a project’s proposed use and design meets applicable planning and zoning standards. In many Berkeley records this appears as statuses like “Approved” or “Entitled.” In this database, those terms are treated as part of the same analytic bucket.

**Building permit**  
An authorization to construct, alter, or demolish structures, usually issued after entitlements are in place. Building permits operate under building codes and safety requirements rather than zoning rules.

**Permit issued**  
A building permit status indicating that the city has granted permission to proceed with the permitted work.

**Permit finaled / finalized**  
A building permit status indicating that permitted work and required inspections have been completed and the permit is closed. This is a construction/completion milestone, not a planning entitlement.

**Certificate of Occupancy (CO)**  
An official document stating that a building or portion of a building is safe and approved for occupancy. In the pipeline, this is often treated as the point at which units become “completed” for counting purposes.

## Unit measures

**Total units** (`total_units`)  
The total number of housing units in the project as proposed or built in a given project version.

**Gross units proposed** (`gross_units_proposed`)  
The number of new housing units proposed by a project, before accounting for existing units that will be removed.

**Units demolished** (`units_demolished`)  
The number of existing housing units removed by a project (for example, when an older building is demolished and replaced).

**Net new units** (`net_new_units`)  
The net change in the housing stock from a project, usually defined as `gross_units_proposed - units_demolished`. This is the concept that aligns with California HCD’s Annual Progress Report guidance for counting housing production.

### Affordability

**Very Low Income (VLI) units**  
Units reserved for households at or below the Very Low Income threshold defined for the relevant jurisdiction and year.

**Low Income (LI) units**  
Units reserved for households at or below the Low Income threshold.

**Moderate Income (MOD) units**  
Units reserved for households at or below the Moderate Income threshold.

**Unrestricted or market-rate units**  
Units without formal income restrictions, regardless of actual rent levels.

The database should also record where each affordability figure comes from (regulatory agreement, conditions of approval, staff report, inference) and with what confidence.

## Geography and identifiers

**Parcel**  
A legally defined piece of land, usually identified by an Assessor’s Parcel Number (APN). A project may cover one or many parcels; a parcel may participate in zero or more projects over time.

**APN (Assessor’s Parcel Number)**  
The county-assigned identifier for a parcel. Used to link projects to assessor data such as lot size and ownership history.

**Site address**  
A street address used for human communication and mapping. A project may have multiple addresses; addresses may change over time. The database typically tracks both a canonical address representation and the raw address strings from sources.

## Provenance and evidence

**Source system**  
The originating system or document set for a fact (for example, a city permit portal, a county assessor roll, or a published report).

**Source record ID**  
The identifier used by the source system for a particular record (for example, a permit number or application ID).

**Assertion**  
A specific claim stored in the database, such as a unit count, status value, event date, or classification.

**Asserted by** (`asserted_by`)  
Who or what created a particular assertion. Examples include a scraper, a data-cleaning script, an observation, or a manual correction.

**Confidence**  
A qualitative measure of how reliable a particular assertion is judged to be, based on source quality and consistency. The exact scale should be documented in the provenance methodology.

**Inferred** (`is_inferred`)  
A flag indicating that a fact was derived or inferred from other data rather than directly observed in a source document.

**Evidence link**  
A reference to an underlying document, image, or note that supports a particular assertion or correction, often via a mirrored URL or archival identifier.

## Corrections and changes

**Correction**  
A change applied to the database when a previously stored value is shown to be inaccurate, ambiguous, or incomplete, supported by documented evidence.

**Original value**  
The value as it appeared in the source system or prior snapshot, preserved for transparency even after a correction is applied.

**Version**  
A snapshot of a project’s key attributes at a given logical point in its lifecycle (for example, proposal, entitlement, permit issue, or completion). Project versions are used to track changes over time.

## Cross-city concepts

Because this project is also a reference implementation for other cities, some definitions are intentionally generic and should hold outside Berkeley. City-specific terms, permit types, and workflows can be documented in additional pages, while the core concepts here should remain shared across deployments.

