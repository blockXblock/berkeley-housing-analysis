# Requirements for Berkeley's Clariti permit system — derived from real faults

*Draft for the City staff member negotiating the Clariti implementation. Every requirement below
is grounded in a specific defect we hit while building an INDEPENDENT reconstruction of Berkeley's
housing pipeline from primary sources (CPRA permits + Alameda assessor). We are not speculating
about what a good system needs; we are reporting what the absence of each feature cost us, with the
evidence. If the new system captures these at intake, no one has to reconstruct them later.*

*Companion goal: these requirements become the scoring rubric for **CaliforniaBuild.com**, a public
leaderboard ranking every California city's permit-data system — a Hugging Face for urban data.*

---

## The one principle behind all of it

**A permit system is not a workflow tool that happens to store data. It is the city's structured,
permanent record of how the built environment changes — and it should be designed for ANALYSIS and
public verification first, processing second.** Every fault below is a place where Berkeley's
current system optimised for moving a permit through a queue and lost the ability to answer a
question about the city. Clariti should be told, in the contract, that the schema is a public
analytic asset, not an internal convenience.

The test for every field: *could an independent party reconstruct the built environment and its
history from the public record alone?* Today the answer is no, and this document is the list of
why.

---

## A. Entity model — the thing that does not exist today

Berkeley's records are a stream of permits. There is no first-class **project / development** that
aggregates the many records, parcels, structures and units that make up one real thing. We had to
reconstruct it, badly, and it is the root of most other faults.

- **A1. PROJECT entity** aggregating every record (planning ZP, building BP, revisions, sub-records)
  for one development. *Fault:* plan sets live on the ZP record, permits on BP records, and nothing
  links them; a 308-unit development scattered across records looked like unrelated permits.
- **A2. One-to-many PARCEL ↔ STRUCTURE ↔ UNIT hierarchy.** *Fault:* the county models parcels with
  ONE `YearBuilt` each. 2811 Benvenue has three structures (1903 house, 1903 carriage house, 1990s
  reading room) and two dwelling units on one parcel; every source we hold collapses it to a single
  1903 dot. Berkeley has ~29,000 parcels but ~62,000+ structures — the current model cannot see the
  other 33,000.
- **A3. STRUCTURE as a first-class record** with its own year-built, stories, height, footprint,
  gross floor area, use, and status. *Fault:* the "structures" concept had to be bolted on; floor
  area was captured for 2 of 895 projects.
- **A4. Agency-permitted flag** (UC, BART) — exempt from city permitting, counted in beds not units.
  *Fault:* UC towers distort every count unless special-cased by hand.

## B. Geometry — footprints are not parcels

- **B1. Building FOOTPRINT geometry stored distinctly from the PARCEL boundary.** *Fault:* 76% of
  the "building footprints" we could find were actually the parcel outline; a 0.87-acre hillside lot
  rendered as a three-storey block covering the whole acre.
- **B2. Geometry VALIDATED at intake:** footprint must lie within its parcel; lot coverage bounded;
  no zero-length segments; no duplicate rings. *Fault:* half-drawn footprints passed every location
  check we had — a footprint on the right lot, next to the right building, drawn at half size, is
  invisible to distance checks. Only flying the 3D model or comparing areas caught it.
- **B3. Height as MEASURED data, never a placeholder.** *Fault:* 39% of heights in a working layer
  were a hard-coded 10.5 m "default 3 stories" rendered to the public as though measured.

## C. Structured intake — stop burying data in PDFs

The City's own **1.E Tabulation Form** already collects, per project, the numbers analysts need:
dwelling units, stories, lot area, gross floor area, building footprint, lot coverage, FAR, useable
open space, parking — each as EXISTING / PROPOSED / REQUIRED. Today it is a PDF. We parsed 80 of
them by hand-built extraction; the layout varies enough that ~30 produced garbage.

- **C1. Every 1.E field captured as a structured DB field at submission**, with the three columns
  (existing/proposed/required) as distinct values, not a scanned form.
- **C2. Affordability by income tier as structured data** — ELI / VLI / LI / MOD / ACUTELY-LOW
  (added 2025), with unit counts, restriction type, restriction term, and recorded date per tier.
- **C3. The document survives, but the DATA does not depend on re-reading it.** Keep the PDF as
  provenance; store its numbers as fields.

## D. Provenance & confidence on every asserted field

- **D1. Each field carries: source document, asserting party, timestamp, and a confidence level**
  (verified-primary / secondary / derived / disputed). *Fault:* migrated values with no source were
  indistinguishable from verified ones; a 485-unit figure from a superseded application outranked
  the 456 in the approved plan set until we traced provenance by hand.
- **D2. Record the MECHANISM that produced a number, not just where it was found.** *Fault:* two
  records that agree can be one witness counted twice (a developer's website and a form transcribed
  from it). Independence, not agreement, is what makes a figure trustworthy.
- **D3. Never overwrite history.** Evidence append-only; a correction is a new versioned assertion
  with its own provenance, not an edit of the old one.

## E. Lifecycle completeness & the event model

- **E1. A complete event timeline per project** — application, completeness, entitlement, building
  permit issued, each inspection, certificate of occupancy — with dates. *Fault:* a cohort of ~713
  projects had only a CO event and no lifecycle, inverting every funnel metric.
- **E2. `units_affected` on every event** — units added and removed. *Fault:* this field was 100%
  null, making unit-conservation across stages (entitlement → BP → CO) impossible to check.
- **E3. Completion recorded as the physical signal (CO / final inspection), never inferred from tax
  valuation.** *Fault:* assessor improvement value reads $0 for 1–2 years after a building is
  finished (reassessment lag) and after a demolition — neither means "unbuilt".

## F. Identifiers, lineage & addresses

- **F1. A stable internal ID for every parcel, structure and project, independent of the APN.**
  *Fault:* APNs are re-platted and the old APN vanishes from the assessor, silently orphaning any
  join keyed on it (an 8-digit re-plat nearly lost a 308-unit development).
- **F2. Parcel LINEAGE** — prior→child records for splits, merges and re-plats, from recorded county
  maps. *Fault:* we could only guess re-plat relationships from address patterns.
- **F3. Address disambiguation & aliases.** *Fault:* two distinct parcels in adjacent blocks both
  carry situs "1367 University Ave"; developers publish a marketing address (1370 University) that
  does not exist in the assessor while the real one is 1375. A canonical address plus an alias set,
  with unique location IDs, is required — nearest-address matching silently put buildings on the
  wrong lot.

## G. Participants — who actually builds it

- **G1. Distinct participant roles: developer, architect, owner-of-record, and financier**, each an
  organisation or person with a source. *Fault:* the owner of record is usually a single-purpose LLC
  that reveals nothing; the actual developer/architect had to be harvested from plan sets and
  developer websites.
- **G2. Version-scoped participants** — a project changes architects across schemes; the record must
  hold the history, not just the current name.

## H. Public API, open data & verification

- **H1. A complete, machine-readable public API** exposing every non-confidential field above —
  not a PDF portal. *Fault:* we reconstructed the pipeline from CPRA spreadsheet requests and a
  browser-automation scrape of a stateful ASP.NET portal because there was no API.
- **H2. Bulk open-data exports** of parcels, structures, projects, units, events and geometry, dated
  and versioned.
- **H3. The data must be independently VERIFIABLE** — stable IDs, provenance, and geometry that a
  third party can check against imagery and the assessor. The state APR (HCD) should be a REPORT
  GENERATED FROM this system, not a separately keyed submission that can silently disagree with it.

---

## The CaliforniaBuild.com leaderboard — turning this into a standard

Each section above becomes a scoring dimension. A city earns points for what its permit-data system
actually exposes:

| dimension | question | max |
|---|---|---|
| Entity model | Are project / structure / unit first-class, or just permits? | |
| Geometry | Building footprints distinct from parcels, validated? | |
| Structured intake | Tabulation-form fields as data, or PDFs? | |
| Provenance | Source + confidence on every field? | |
| Lifecycle | Complete event timeline with unit deltas? | |
| Identifiers | Stable IDs + parcel lineage + address disambiguation? | |
| Participants | Developer / architect / owner / financier captured? | |
| Public API | Complete machine-readable API + bulk exports? | |
| Verifiability | Independently checkable; APR generated from the system? | |

Berkeley, post-Clariti, is the reference implementation and sets the high bar. Every other CA city
is scored against the same rubric. CaliforniaBuild.com hosts the rankings, the rubric, and each
city's scorecard — a public, methodical incentive for cities to build analysable permit systems,
the way a leaderboard drives model quality on Hugging Face.

---

## How this document should grow

This is a living list. Every new fault we hit reconstructing the pipeline is appended here as a
dated requirement with its evidence. By the time the Clariti schema is under negotiation, the
document is the accumulated, evidence-backed specification — not a wishlist, a bug report against
the old system written as requirements for the new one.
