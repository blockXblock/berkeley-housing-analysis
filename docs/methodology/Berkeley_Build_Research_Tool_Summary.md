# A reproducible tool for auditing housing-pipeline data from primary sources

**Berkeley Build — capability summary for researchers and reporters**
*berkeleybuild.com · June 2026*

## What it is

Berkeley Build is an independent reconstruction of Berkeley's Housing Element Annual Progress Report (APR), built entirely from public records, with one distinguishing property: **every figure can be traced back to the primary-source document that establishes it.** It is not a dashboard that restates the city's numbers. It is a pipeline that reproduces those numbers from the underlying permit data and entitlement documents — and, in doing so, surfaces where the official figures are incomplete or wrong.

The system pairs a normalized public database (published as a queryable Datasette instance and a web Explorer) with a document-harvesting capability that pulls architect plan sets and entitlement filings directly from the city's Accela permitting portal. The result is a reproducible chain: **public permit → primary-source document → verified data point → APR table**, with the source document one click away at every step.

## The two problems it solves

**1. Public documents that aren't actually accessible.** Berkeley's permit records and their attachments — plan sets, density-bonus statements, affordability tabulations — are public, but the portal exposes them only through session-bound JavaScript interactions with no stable URLs. A specific plan set cannot be linked, cited, or retrieved programmatically; it can only be reached by a person clicking through a live session. We built and validated an anonymous harvesting engine that retrieves these documents intact, stores them at stable public URLs, and catalogs them with cryptographic checksums. To date this has captured 54 architect plan sets across 19 major projects, each verified byte-for-byte against its source. *The data was always public; for the first time it is reliably reachable and citable.*

**2. Income-tier data that is largely missing from the reported figures.** This is the finding most relevant to RHNA and APR work. The affordability breakdown that Table A2 fundamentally requires — units by very-low, low, moderate, and above-moderate income — is **substantially absent from the permit-derived data the city and state systems carry.** In our reconstruction, the majority of affordability records carried no income tier at all, and there was effectively **no low-income or moderate-income tier data** in the structured record — precisely the categories density-bonus projects rely on most. We have demonstrated that this data can be recovered, accurately and auditably, from the primary entitlement documents themselves: Density Bonus Eligibility Statements and Tabulation Forms state the exact tier splits in plain text. On a validation case where the correct answer was independently known, the extraction matched exactly (9 very-low and 9 moderate-income units), and across a varied sample it correctly distinguished cases where the official data was *confirmed* by the document from cases where it was *contradicted*.

## How it works

The pipeline takes public CPRA permit data and Accela records, normalizes them into a canonical database, and reproduces the APR tables project by project against the city's published report — explaining every divergence rather than papering over it. Where the structured data is incomplete or suspect, the harvested primary-source documents become the arbiter. Corrections are applied through a disciplined, reversible process: each change is guarded, previewed, and recorded with the source document and the verbatim language that justifies it. Nothing is asserted that a document does not state; what the documents leave unstated is left explicitly blank rather than inferred.

## What it produces that didn't exist before

- **A citable corpus** of primary-source housing documents at stable public URLs, indexed by project.
- **Source-linked corrections** to the public record — every fix traceable to the document and the sentence that supports it.
- **Recovered income-tier data** for Table A2, extracted from entitlement documents, with the source quote preserved alongside each value so the extraction is auditable rather than a black box.
- **A reproducible methodology**, designed from the outset to be portable to other California jurisdictions — Berkeley is the reference implementation, not the limit of the approach.

## Why this is useful to your work

**For reporters:** you can independently verify the city's housing claims against primary sources, and when a number is wrong, point to the exact document that shows it. The tool has already identified concrete discrepancies in the official APR — including double-counted units, projects omitted from required tables despite having received certificates of occupancy, and unit counts that disagree with the developer's own stamped plans.

**For housing and RHNA researchers:** it offers a reproducible audit of APR accuracy and, more pointedly, a method for recovering the income-tier affordability data that is systematically thin in the reported figures. That gap is not unique to Berkeley; the recovery method is not either. A reproducible, document-grounded approach to Table A2 is the kind of thing that could be standardized across jurisdictions.

## Honest scope

This is an **independent** reconstruction, not an official record. It is Berkeley-first, with generalization to other cities a deliberate design goal rather than a completed fact. The APR reproduction is close and improving but not yet a perfect match — and the divergences themselves are part of the value, since each one is either a finding about the city's data or a correction to ours. The document-extraction capability is proven on the dominant entitlement-form family and is being extended to others. We would rather state these limits plainly than overclaim; the credibility of the tool rests on its traceability, and that traceability is the point.

---

*Contact: berkeleybuild.com. The full pipeline, database, and document corpus are public. We welcome scrutiny of any figure — every one is meant to be checkable against its source.*
