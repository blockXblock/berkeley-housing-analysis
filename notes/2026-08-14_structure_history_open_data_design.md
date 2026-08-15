# Structure-History Open Data — schema & architecture design

**Status:** design sketch (notes/ — in-flight). Author: CC + John, 2026-08-14.
**Goal:** join every source we can find about a building — architect plans, deeds, owner names,
tax rolls, assessor records, contractor records, business & rental licenses, permits, inspections,
photos — into ONE interactive, map-based **complete history of each structure**.

---

## 0. The one idea that makes or breaks this: identity is the spine, not the data

The temptation is to make a wide `parcels` table and bolt columns on. That fails here, because the
thing John wants a history *of* — a **structure** — is not what any single source is keyed to, and the
keys the sources DO use are unstable and non-1:1. We have already been burned by every one of these:

- **Parcel ≠ structure.** One parcel can hold a main house + an ADU (2 structures). One condo tower
  is 1 structure on *many* parcels (the ghost multi-match bug: a point landed on 66 APNs).
- **APN ≠ stable identity.** Parcels get re-platted/renumbered and the old APN vanishes from the
  assessor (Acheson → 57-2046-11-1). ADR-003 already models this with `parcel_lineage`.
- **Address ≠ structure.** Secondary addresses (½, A–D, Rear, Cottage) mark *units the assessor
  misses* — the RPP layer is an inventory of dwellings, not a 1:1 structure key.
- **Everything is temporal.** Owners change (deeds), APNs change (re-plat), a structure is born
  (built) and can die (demo→rebuild — proj174/208). "Complete history" = valid-time on every edge.

So the architecture is **four identities, joined by dated crosswalks, with lineage** — and every
source attaches as *evidence* to one of those identities, never as an authoritative column.

```
        STRUCTURE  ──(dated)──  PARCEL  ──(dated)──  OWNER
        (building)              (APN, land)          (deed grantee)
           │                       │
        (dated)                 lineage: split/merge/replat  (ADR-003)
           │
        ADDRESS  ── DWELLING_UNIT
        (situs,½,A/B)  (rentable unit → rental license, rent board, tenancy)
```

The structure is the subject John asked for, but we **bootstrap parcel-first** (we already have that
spine) and **lift to structure incrementally** where footprints + permits let us. No source hands you
a stable building id — it is *constructed* by triangulation, exactly the v4 event-stream philosophy.

### Prior art: UrbanSim (Paul Waddell, UC Berkeley CED / UDST) — validates the spine

Our land→structure→unit spine is not novel — it matches **UrbanSim's** battle-tested, regional-scale
schema (BSD-3 licensed, [github.com/UDST](https://github.com/orgs/UDST/repositories)):
`parcels` (land) → `buildings` (structure, FK `parcel_id`) → `residential_units` → `households`/`jobs`.
Their `buildings.parcel_id` is many-to-one, so **main-house + ADU on one lot is native** (our
shadow-vs-real-ADU case), and development changes *buildings* on a stable *parcel* — the same
land/structure split we need. We borrow the **hierarchy and FK discipline** as validated prior art.
What UrbanSim does NOT carry — and what makes ours a *history* rather than a *forecasting snapshot* —
is the **provenance/assertion layer, the bitemporal crosswalks (valid-time), and the lineage/verdict
layer** (replat, demo→rebuild). So: UrbanSim's hierarchy is the skeleton; §4–§7 below are our additions.
(Its regional parcel DATA is gated behind MTC/AWS credentials — not a public shortcut around our
`berkeley.db`; but the *design* is open and reusable.)

---

## 1. Seven layers

1. **Identity spine** — `structure`, `parcel`, `address`, `dwelling_unit`.
2. **Temporal crosswalks** — `structure_parcel`, `structure_address`, `structure_unit` (all M:N, all
   with `valid_from`/`valid_to`).
3. **Lineage** — `parcel_lineage` (ADR-003: split/merge/replat), `structure_lineage` (demo→rebuild,
   ADU-added, subdivision).
4. **Provenance registry** — `source` (dataset, publisher, **license**, retrieval date, hash, role)
   + `document` (the actual artifact: a scanned plan, a recorded deed, a permit PDF, an inspection photo).
5. **Assertion stream** — the heart: every fact is an append-only, provenance-carrying row
   (`subject`, `predicate`, `value`, `as_of`, `source`, `confidence`). Sources disagree → many
   assertions per predicate; nothing is overwritten.
6. **Unified timeline** — `structure_event` (constructed, permit_filed/issued, CO, deed_recorded,
   owner_changed, license_issued, inspection, altered, demolished) — the v4 event stream re-homed on
   structure.
7. **Resolution + serving** — `decision` (append-only log of which assertion won a contested
   attribute, with the classifier/decider hash — ADR-002) → materialized `v_structure_current` /
   `v_structure_history` views the map reads.

**Hybrid, not either/or:** keep source-faithful **normalized tables** (`deeds`, `assessments`,
`permits`, `licenses`) for fidelity AND emit **assertions** from them into the common stream. The
normalized tables preserve exactly what the source said; the assertion stream powers the unified view.

---

## 2. Core DDL sketch (SQLite-flavored — our stack)

```sql
-- ===== IDENTITY SPINE =====
CREATE TABLE structure (
  structure_id   TEXT PRIMARY KEY,     -- synthetic, stable: 'BRK-STR-000123' (APN is NOT the key)
  status         TEXT,                 -- extant | demolished | proposed | replaced
  footprint      TEXT,                 -- WKT/GeoJSON polygon if known (KML skyline, Sanborn, county)
  centroid_lon REAL, centroid_lat REAL,
  built_year     INTEGER,              -- RESOLVED best (from decision layer); nullable, never a guess
  demolished_year INTEGER,
  primary_use    TEXT,                 -- resolved: residential | mixed | commercial
  created_at TEXT, created_by TEXT     -- provenance of the ROW (which build/classifier hash)
);

CREATE TABLE parcel (                  -- ADR-003 shape (already live in v2)
  parcel_id      TEXT PRIMARY KEY,     -- synthetic; APN is an attribute, not the id
  apn_raw        TEXT NOT NULL,        -- source-faithful, NEVER mutated
  apn_normalized TEXT,                 -- option-B canonical (to_canonical_apn)
  county         TEXT,
  valid_from TEXT, valid_to TEXT,      -- when this APN was live in the assessor
  UNIQUE(apn_raw, county)
);

CREATE TABLE address (
  address_id     TEXT PRIMARY KEY,
  situs_normalized TEXT,               -- '2811 BENVENUE AVE'
  unit_designator  TEXT,               -- '' | '1/2' | 'A' | 'REAR' | 'COTTAGE'
  lon REAL, lat REAL,
  source_layer   TEXT                  -- RPP | assessor_situs | USPS
);

CREATE TABLE dwelling_unit (
  unit_id  TEXT PRIMARY KEY,
  label    TEXT,                       -- 'main' | 'ADU' | 'unit B'
  bedrooms INTEGER,
  tenure   TEXT                        -- 'unknown' allowed — with provenance, NEVER filled from CKAN
);

-- ===== TEMPORAL CROSSWALKS (M:N, dated) =====
CREATE TABLE structure_parcel (
  structure_id TEXT, parcel_id TEXT,
  valid_from TEXT, valid_to TEXT,
  confidence REAL, source_id TEXT,
  PRIMARY KEY (structure_id, parcel_id, valid_from)
);
CREATE TABLE structure_address (structure_id TEXT, address_id TEXT, valid_from TEXT, valid_to TEXT, source_id TEXT);
CREATE TABLE structure_unit    (structure_id TEXT, unit_id TEXT,   valid_from TEXT, valid_to TEXT);

-- ===== LINEAGE (identity changes over time) =====
CREATE TABLE parcel_lineage (          -- ADR-003
  event_id TEXT PRIMARY KEY,
  prior_parcel_id TEXT, child_parcel_id TEXT,
  kind TEXT,                           -- split | merge | replat | renumber
  status TEXT,                         -- candidate | confirmed (never a fact until a county map confirms)
  county_map_ref TEXT, effective_date TEXT
);
CREATE TABLE structure_lineage (
  event_id TEXT PRIMARY KEY,
  prior_structure_id TEXT, next_structure_id TEXT,
  kind TEXT,                           -- demolished_replaced | subdivided | merged | adu_added
  effective_date TEXT, source_id TEXT
);

-- ===== PROVENANCE REGISTRY =====
CREATE TABLE source (
  source_id TEXT PRIMARY KEY,
  name TEXT, publisher TEXT,
  license TEXT,                        -- open-data license — LOAD-BEARING for republishing
  url TEXT, retrieved_at TEXT, source_hash TEXT,
  role TEXT                            -- 'independent_input' | 'oracle_verify_only'  (CKAN/HCD = oracle!)
);
CREATE TABLE document (
  document_id TEXT PRIMARY KEY,
  source_id TEXT,
  doc_type TEXT,                       -- architectural_plan | deed | permit | inspection_photo | tax_bill | business_license | sanborn
  title TEXT, storage_url TEXT,        -- R2 / URL to the actual PDF/image
  doc_date TEXT, page_ref TEXT,
  structure_id TEXT, parcel_id TEXT, address_id TEXT   -- whichever identity it keys on
);

-- ===== THE ASSERTION STREAM (typed, append-only, provenance-carrying) =====
CREATE TABLE assertion (
  assertion_id TEXT PRIMARY KEY,
  subject_type TEXT,                   -- structure | parcel | unit | owner
  subject_id   TEXT,
  predicate    TEXT,                   -- built_year | owner_name | units | use_code | architect |
                                       --   contractor | sale_price | assessed_land | assessed_imps | rental_units ...
  value_text TEXT, value_num REAL, value_date TEXT,
  as_of        TEXT,                   -- date the fact is TRUE-as-of (roll year, sale date, permit date)
  observed_from TEXT, observed_to TEXT,-- validity window of the observation
  source_id TEXT, document_id TEXT,
  confidence REAL,
  created_at TEXT, created_by TEXT     -- ingest provenance
);   -- APPEND-ONLY: a correction is a NEW assertion, never an UPDATE.

-- ===== UNIFIED TIMELINE =====
CREATE TABLE structure_event (
  event_id TEXT PRIMARY KEY,
  structure_id TEXT,
  event_type TEXT,                     -- vocabulary: constructed | permit_filed | permit_issued |
                                       --   co_issued | deed_recorded | owner_changed | license_issued |
                                       --   inspection | altered | demolished
  event_date TEXT,
  source_id TEXT, document_id TEXT,
  detail_json TEXT,                    -- type-specific payload
  verdict TEXT, verdict_by TEXT        -- role/classification + classifier hash (ADR-002)
);

-- ===== RESOLUTION (contested attributes) =====
CREATE TABLE decision (                -- append-only log of resolutions
  decision_id TEXT PRIMARY KEY,
  subject_type TEXT, subject_id TEXT, predicate TEXT,
  chosen_assertion_id TEXT,            -- which assertion won
  rule TEXT, decided_by TEXT,          -- classifier hash | 'john_verified'
  decided_at TEXT, note TEXT
);

-- ===== SERVING =====
-- v_structure_current : structure + winning assertion per predicate (the map's info panel)
-- v_structure_history : structure_event ordered by date (the timeline the popup expands)
```

---

## 3. Every source John listed → which identity, what it contributes

| Source | Keys on | Contributes (assertions/events/docs) | Have it? |
|---|---|---|---|
| **Architect plans & drawings** | structure | `architect`, `design_date`, original units; `document(architectural_plan)` | partial (permit plan sets, BAHA, landmark files) |
| **Deeds** (County Recorder) | parcel→owner | `owner_name` (grantee), `sale_price`, `deed_recorded` event → tenure & turnover | **gap** (Regrid/Recorder — the movie fuel) |
| **Owner names** | parcel | `owner_name` + owner-type classification; county hides names, Recorder/Regrid supply them | yes (2026-08-13 snapshot) |
| **Tax records** (propinfo.acgov.org) | parcel | assessed land/imps **by roll year (35-yr series!)**, `use_code`, parent/child parcels → `parcel_lineage` | reachable per-parcel |
| **Assessor records** | parcel | `built_year` (unreliable → landmark override), `units`, `beds`, `use_code` | yes (berkeley.db) |
| **Contractor records** (CSLB / permit) | structure/permit | `contractor`, license #, ties builder to the permit | gap |
| **Business licenses** | parcel/address | rental-of-real-property, unit counts | yes (berkeley.db licenses) |
| **Rental licenses / RHSP** | address/unit | rental registration, `inspection` events + fees | partial (Accela; CPRA #26-2375) |
| **Building permits** (Accela) | structure | the **event backbone**: filed/issued/CO, units added, ADU flag | partial (CPRA feed; ADU tail unmodeled) |
| *+ later:* code enforcement, landmark designation, soft-story/seismic, PG&E hookup (birth signal), **Sanborn maps** (historical footprint), census unit counts, photos | mixed | timeline + footprint enrichment | future |

---

## 4. The honest hard parts (state them, don't hand-wave — "presume you're wrong")

1. **Structure identity is synthetic and constructed, not given.** No source has a stable building id.
   This is the expensive part. *Mitigation:* bootstrap parcel-keyed (we have it), lift to structure
   only where footprint + permits justify it; keep `confidence` on `structure_parcel`.
2. **Four identities, all M:N, all temporal.** The condo tower and house+ADU break every 1:1
   assumption. *Mitigation:* dated crosswalks from day one; never a foreign key that assumes 1:1.
3. **APNs (and structures) are unstable.** Lineage comes from **county maps / demo permits**, never
   string patterns (ADR-003; `status='candidate'` until confirmed).
4. **Sources disagree and are silent.** *Mitigation:* assertion stream + resolution layer, never a
   destructive merge; "unknown with provenance"; **CKAN/HCD stays `oracle_verify_only`** on the
   source table — a role flag enforces "verification target, never an input."
5. **Licensing travels with the data.** Open republishing is only safe if each `source.license` +
   `retrieved_at` + `source_hash` is recorded. Without it we can't legally/ethically re-serve.
6. **Privacy is a deliberate choice, not a default.** Owner names are public record, but the county
   *chose* to hide them and an owner→portfolio index has real ethics. Decide consciously; don't
   aggregate just because we can.
7. **Confidence + verdict are first-class**, not afterthoughts — every crosswalk and every resolved
   attribute carries who decided and how sure (the ghost-unit "candidate, not count" lesson).

---

## 5. Build order (incremental, reuses everything we have)

- **Phase 0 — identity spine (parcel-first).** Done: ADR-003 `parcel` + `to_canonical_apn`.
- **Phase 1 — attach existing sources as assertions.** Assessor, licenses, rent board, permits — all
  in hand. Stand up `source`, `assertion`, `structure_event` and backfill from normalized tables.
- **Phase 2 — deed/transfer history.** Regrid (free access, offered) or Recorder → `owner_changed`
  events + tenure timeline. Unlocks the ownership-turnover movie.
- **Phase 3 — lift parcel→structure.** Footprints (KML skyline, county, Sanborn) + permits →
  `structure`, `structure_parcel`, `structure_lineage`; resolve ADU pairs & condo towers.
- **Phase 4 — documents to R2.** Plans, deed PDFs, inspection photos → `document`, linked per structure.
- **Phase 5 — resolution + serving views → the interactive map.** `v_structure_current` /
  `v_structure_history` feed the clickable dots; the popup expands into a full timeline.

Each phase is independently useful and independently gated (snapshot → preview → John → write).

---

## 6. What the map does with it (the payoff)

Click a dot → popup shows `v_structure_current` (address, resolved build year + who says otherwise,
owner, units, use). "Expand history" → `v_structure_history`: built 1903 (architect A. Dodge Coplin,
plan on file) → sold 1988 → ADU permit 2011 → rental license 2019 → RHSP inspection 2023 — each row
linking to the actual document. That is the "complete structure history," and the schema above is what
makes every one of those rows carry its own source.

---

## 7. Taxation & bond-incidence layer (does the schema support "what will a new bond cost each owner?")

**Yes — because a property-tax bill is itself a JOIN, and the join key already exists in county data.**
A bill is not one number; it is a *stack of levies* from many taxing entities (city, county, school,
community college, EBMUD/water, fire, park, BART, AC Transit, library, plus parcel taxes and special
assessments). California administers this with the **Tax Rate Area (TRA)**: every parcel is assigned a
TRA code, and the TRA *is* the encoded answer to "which set of taxing entities apply to this parcel."
The Auditor-Controller publishes a rate by TRA each year. So the whole tax stack drops onto our
existing spine cleanly.

### New entities (attach to `parcel`, reuse everything else)

```sql
CREATE TABLE taxing_entity (
  entity_id TEXT PRIMARY KEY,
  name TEXT,                 -- 'City of Berkeley' | 'Alameda County' | 'Berkeley USD' |
                             --   'EBMUD' | 'East Bay Regional Park' | 'BART' | 'Peralta CCD' | 'AC Transit'
  entity_type TEXT,          -- city | county | school | community_college | water | fire | park | transit | library | special
  boundary TEXT              -- geometry (some countywide, some sub-city)
);

CREATE TABLE tax_rate_area (tra_code TEXT PRIMARY KEY, county TEXT);   -- the county's bundle
CREATE TABLE parcel_tra (
  parcel_id TEXT, tra_code TEXT, tax_year INTEGER,   -- assignment can change (annexation)
  source_id TEXT, PRIMARY KEY (parcel_id, tax_year)
);

CREATE TABLE measure (                      -- a ballot measure / bond that authorizes a levy
  measure_id TEXT PRIMARY KEY, name TEXT, jurisdiction_entity_id TEXT,
  kind TEXT,                                -- go_bond | parcel_tax | special_assessment | mello_roos
  principal_amount REAL, term_years INTEGER, purpose TEXT,
  election_date TEXT, status TEXT           -- proposed | passed | failed | active | retired
);

CREATE TABLE levy (                         -- a specific charge in a year, WITH ITS BASE MECHANISM
  levy_id TEXT PRIMARY KEY, entity_id TEXT, measure_id TEXT, tax_year INTEGER,
  base TEXT,                                -- ad_valorem | per_parcel | per_sqft_building | per_unit | per_sqft_land
  rate REAL,                                -- ad_valorem: fraction of AV (debt-service rate)
  flat_amount REAL,                         -- parcel/unit/sqft taxes: $ per base-unit
  applies_scope TEXT,                       -- tra list / entity boundary
  status TEXT                               -- actual | proposed | scenario   <-- keeps hypotheticals OUT of facts
);

CREATE TABLE tax_bill_line (                -- GROUND TRUTH: source-faithful billed lines (the validation oracle)
  bill_line_id TEXT PRIMARY KEY, parcel_id TEXT, tax_year INTEGER,
  levy_id TEXT, entity_name_raw TEXT, amount REAL,
  source_id TEXT, document_id TEXT
);
```

### The two levy mechanisms — and why the difference is the whole political story

- **Ad valorem** (the 1% Prop-13 base + **voter-approved bond debt service**): cost = `rate × assessed_value`.
  A bond's rate = `annual_debt_service ÷ (total assessed value in the district)`. So the cost to a
  parcel scales with **its assessed value**.
- **Parcel tax** (Mello-Roos / special taxes, 2/3 vote): a **flat** amount per parcel (or per sqft, per
  unit) — cost is **independent of value**.

A $300M measure raised as an *ad-valorem GO bond* vs as a *flat parcel tax* falls on completely
different owners. The schema models both (the `base` column), so we can show the incidence of each.

### Summation by every dimension John named = one GROUP BY

Because `owner`, `structure`, and `license` are all already crosswalked to `parcel`, and tax attaches
to `parcel` via TRA→levies, each requested roll-up is trivial:

| Sum by… | Join path |
|---|---|
| **parcel** | `tax_bill_line` GROUP BY parcel |
| **structure** | `structure_parcel → tax_bill_line` GROUP BY structure — *correctly* sums a condo tower's many parcels, or a house+ADU |
| **owner** | `parcel → owner` GROUP BY owner_name → *portfolio tax burden* (2700SP LLC across its 36 parcels) |
| **license** | `license → parcel → tax_bill_line` → tax attributable to licensed rentals |
| **assessed valuation** | GROUP BY AV band → the progressivity curve |

### The standout finding this unlocks for the bond op-ed (Prop 13 × tenure)

Assessed value is acquisition-based and frozen (+2%/yr) until sale. So under an **ad-valorem** bond,
**two identical houses pay wildly different amounts** — the one held since 1985 pays on a ~1985 base,
the one bought in 2024 pays on today's price, often **5–10× more for the same bond.** We *already hold
the data to map this*: `LatestDocu` (tenure) + assessed value + owner-type. **The tenure map we just
built becomes a tax-incidence map** — recolor each dot by "your share of a new $300M ad-valorem bond,"
and the long-held vs recent-buyer inequity is visible parcel by parcel. Flip the scenario to a flat
parcel tax and the burden redistributes — the map shows exactly who wins and loses under each design.
That is a data-journalism argument no press release can make.

### Bond-cost scenario = a non-destructive projection layer

A proposed bond is a `measure(status='proposed')` + `levy(status='scenario')`. A `scenario` function
computes each parcel's incremental levy (ad-valorem: `rate × AV`; parcel-tax: `flat_amount`), rolls it
up by owner / tenure / AV band / neighborhood, and **never writes into billed facts**. Same discipline
as assertion-vs-verdict and candidate-vs-confirmed: hypotheticals are flagged, isolated, reversible.

### Honest hard parts (acquire + validate; don't invent a rate)

1. **We must acquire two things:** the **parcel→TRA assignment** and the annual **tax-rate book by TRA**
   (Alameda Auditor-Controller). Present as an acquisition; validate format on arrival.
2. **The actual tax bill is the oracle.** Before trusting any bond projection, reproduce *current*
   bills from our `levy` model and reconcile against `tax_bill_line` — a rate we can't reproduce is a
   rate we don't understand. (Never fabricate a levy rate, same rule as CKAN.)
3. **Exemptions shift the base** — homeowner's ($7k AV), welfare/nonprofit, disabled-veteran. The
   ad-valorem base is AV *after* exemptions; model them or the incidence is off.
4. **AV ≠ market value** (Prop 13) — the feature, not a bug, for the incidence story; but it means our
   assessed-value distribution is *not* a wealth distribution, and we must say so.
5. **Direct charges vs ad valorem** — parcel taxes and assessments are "direct charges" on the bill,
   separate from the ad-valorem section; keep `base` explicit so we never sum a flat charge as if it
   scaled with value.

**Near-term, without waiting on the rate book:** we can already estimate an ad-valorem bond's incidence
using total district AV (Land+Imps, in hand) as the base — an approximate but directionally-honest
per-parcel share, enough to draft the op-ed's central chart while the exact TRA rates are acquired.
