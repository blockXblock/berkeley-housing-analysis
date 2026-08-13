# Corridor housing-density investigation (2026-08-12)

**Question:** does College Ave / Elmwood carry more multi-unit housing per block than its "single-family"
zoning label implies, and are households adding backyard ADUs there? Compare to other corridors + the rest
of Berkeley. Consolidated as **JN-M** (`notebooks/v4/JN-M_corridor_density.ipynb`, generator
`scripts/v4/build_jn_m.py`; core `scripts/block_density_index.py`).

## Finding
College–Elmwood (Dwight→Alcatraz) ≈ **15 du/land-acre — 2.2× the citywide median (6.8)** — and exceeds the
University Ave commercial corridor (6.0). The **East side of College** (kept low-zoned "for fire evacuation")
carries **~4× the ADU-building rate of the West** (0.44 vs 0.14 ADU/acre) — densification concentrated on the
side the map freezes. This existing-density finding is **regime-independent** (it's the already-built stock).

## Current regime = Middle Housing (NOT the old districts)
The **Middle Housing Ordinance 7,978-N.S. (effective Nov 1 2025)** allows **up to 8 units by-right on a
typical 5,000 sf residential lot (~70 du/ac)**, everywhere residential **except high fire-hazard hills** —
superseding the old R-1/R-2/R-2A/R-3/R-4 du/ac caps. So the benchmark is the **MH allowance, not the defunct
districts**: College–Elmwood at 15 du/ac is only **~22% of the ~70 du/ac now permitted** → the story is
"already dense, and vastly more is now legal by-right." The relevant map becomes **MH-eligible vs
fire-hazard-EXEMPT** (fire zones are on the Berkeley ArcGIS org, curl-accessible). *(Superseded framing: an
earlier pass benchmarked against old R-2A=26 / R-1=8.7 caps — obsolete as of Nov 1 2025.)*

## Fire-exemption overlay (§2 in JN-M) — hypothesis DISPROVED
Overlaid Berkeley Hill/Fire Zones (`data/reference/berkeley_fire_hill_zones.geojson`, from the city ArcGIS
org; Hill Zone 2-3 = high fire-hazard hills MH exempts) on the corridor blocks. **College–Elmwood = 0/44
blocks in the fire-hazard zone** (it's flatland) — **both sides fully MH-eligible.** So the ~4× ADU
concentration on the **East** side is **NOT** a fire-exemption artifact (a tempting story, tested and
rejected); its cause is elsewhere (larger SF lots / owner-builder incentive — to test). Citywide, ~364/1,522
blocks (~24%, the hills) are MH-exempt; **every density corridor sits outside it** — MH's 8-units-by-right
reaches exactly where the hidden density already is.

## ⚠️ The ADU-undercount discovery (Benvenue) — a load-bearing data-quality result
Measuring *recent* densification from assessor **YearBuilt** is a definitional error: an ADU adds a dwelling
unit **without changing the building's year built**, so YearBuilt counts new *structures*, not new *units*
(an early pass wrongly read "3 units since 1995" as "frozen"). Ground truth — **2811 / 2822 Benvenue** (owner
built two ADUs, holds a rental license, had an RHSP inspection + paid a fee): **six datasets miss all of it** —
assessor YearBuilt (blind), assessor Units (2822 reads 1), business licenses (13,004 records, absent), our
2018+ ADU cohort (absent), v4 permit events (absent), Rent Board `rent_control` (1,098 rows, absent). The city
holds every record; they live in **Accela ACA** — the only complete source. **The correct temporal metric is
`permitted_units_added`** (the ADU building-permit event, harvested from Accela), never YearBuilt. Harvest
scoped: `notes/2026-08-12_accela_benvenue_adu_harvest_scope.md` (3 record classes — permits, rental licenses,
RHSP inspections+fees; validates iff 2811 & 2822 light up).

## Method
- **Existing stock** = Census 2020 PL 94-171 (P1_001N pop, H1_001N housing units) joined to TIGER2020
  `tabblock20` on GEOID20. Parse verified vs Berkeley's known 2020 pop 124,321 (got 124,197 for 1,522
  centroid-in blocks). Density = units per **land** acre (`ALAND20`), consistent across corridors.
- **Adds** = our fixed-classifier ADU cohort (`data/processed/adu_mh_cohort.csv`, ~93% recall vs HCD APR).
- **Corridors** cut at the city's own boundaries — **College = Dwight (37.866) → Alcatraz (37.851)**, matching
  the CZU; College split **East/West** of the avenue centerline (linear fit from College parcels). Others by
  parcel street-name → containing block.
- **Derive + baseline gate:** all figures derived; asserted vs `data/baselines/corridor_density_baseline_2026-08-12.json`.

## Boundary decision (why Dwight, and why "College = Elmwood")
The **Southside Plan's southern boundary IS Dwight Way**; the **CZU's College project area is Dwight→Alcatraz**.
The two plans meet at Dwight. North of Dwight along College is **campus/institutional** (Clark Kerr, fraternity
row) — 6 du/ac, not dense residential; the student density is on **Telegraph (16.7)**. So the College
*residential* story is entirely the **Elmwood** stretch. (My first pass used a flat lat 37.861 ≈ 3 blocks south
of Dwight — corrected.)

## CZU integration (Corridors Zoning Update, Raimi + Assoc)
- CZU corridors = **College, N. Shattuck, Solano** — the city's **"high-resource areas,"** targeted for AFFH
  upzoning (≥2,000 units on corridors by Dec 2026) to balance formerly red-lined areas. Directly aligned with
  the thesis. Zoning-table extract: `docs/audit/2026-08-12_czu_zoning_extract.md`.
- **Load-bearing correction:** Berkeley zoning *"does not contain a maximum density in units per acre for the
  majority of its districts"* — it is **form-based** (FAR/height/lot-area-per-unit). So "vs zoned" is du/ac only
  for R-1/R-2/R-2A; R-3/R-4/commercial need **FAR + height** (realized FAR needs per-parcel building sqft — gap).

## Data-acquisition decisions (the durable lessons)
- **Census keyless API is dead** (all endpoints → `missing_key`) → downloaded the **CA PL 94-171 file (76 MB)**
  directly and parsed (P1 seg1 field[5]; H1 seg2 field[-3]; SUMLEV 750).
- **Berkeley per-parcel zoning is via Accela ACA, NOT Socrata.** Socrata (`data.cityofberkeley.info`)
  **WAF-blocks this environment** (all paths 403 — an IP-level block; open to a normal browser). The Berkeley
  ArcGIS org exposes no clean citywide zoning layer (the ArcGIS "Berkeley Zoning" hit is **Berkeley, NJ**).
  → harvest per-parcel zoning from **`aca-prod.accela.com/BERKELEY/`** with our HARVESTER (John logs in). Queued.
- **CPRA drafted** (`notes/2026-08-12_cpra_corridors_parcel_gis.md`) for Raimi's parcel GIS (existing units +
  opportunity coding) as an independent cross-check.

## Artifacts
- `scripts/block_density_index.py` (core, importable), `scripts/v4/build_jn_m.py` → `notebooks/v4/JN-M_corridor_density.ipynb`
- `data/processed/berkeley_blocks_2020.geojson`, `block_density_index.csv`, `berkeley_block_census_2020.csv`
- `data/baselines/corridor_density_baseline_2026-08-12.json`
- Viz in `scratch/2026-08-12/`: choropleth, corridor comparison, vs-zoned, `berkeley_density_3d.kml` (extruded skyline)

## Next
1. **Accela ACA per-parcel zoning harvest** → parcel-exact "denser than zoned."
2. Building footprints/sqft → realized FAR for the form-based corridors.
3. deck.gl / 3D-KML density skyline for the web.
