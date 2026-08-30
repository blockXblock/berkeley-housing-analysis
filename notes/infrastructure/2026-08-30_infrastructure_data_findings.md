# Berkeley infrastructure — what's public, what isn't (session 1)

**Date:** 2026-08-30 · read-only research · nothing gated, nothing written to any DB
**Raw pulls:** `data/raw/infrastructure/` · **Scripts:** `scratch/2026-08-30/`
**Rule applied throughout:** every count below was verified against the server's own
`returnCountOnly` and against the retrieved feature count. Where a number is not
public, it is named as such and the records request that would get it is named too.

---

## 1. The headline finding: 4,499 wood poles, free, today

The City's streetlight layer carries a **`POLEMAT` (pole material)** field. Splitting
on it separates the two pole populations the project set out to distinguish:

| Pole material | Streetlight records | Reading |
|---|---:|---|
| **Wood** | **4,499** | Almost certainly **joint-use utility poles** (PG&E/AT&T) that the City has hung a streetlight on — the City does not set wood poles for street lighting |
| Metal | 3,304 | City-owned dedicated streetlight standards |
| Fiberglass | 98 | City-owned |
| Concrete | 19 | City-owned |
| Unknown | 49 | — |
| **Total** | **7,969** | matches the server count exactly |

Of the 4,499 wood-pole records, **4,456 carry a `UTIL_PN` (utility pole number)** —
**4,428 distinct IDs**, overwhelmingly PG&E's `B####` Berkeley series — at **4,487
distinct coordinates**. The layer also carries `FIELD_PN` (the tag read in the field
during the 2014 Tanko Lighting LED-conversion audit), which agrees with `UTIL_PN` on
**95.6%** of wood poles; the disagreements are mostly prefix noise (`BMI451` vs `MI451`).

**Why this matters.** The project brief assumed no public utility-pole locations exist.
That is true of the *complete* inventory, but **~4,400 Berkeley utility poles are
publicly located right now, with PG&E's own pole IDs attached**, as a side effect of
the City's streetlight asset management. This is:
- a **hard, defensible lower bound** on Berkeley's utility-pole count;
- a **join key** into PG&E's records — which transforms the data request from "please
  give us your pole database" into "here are 4,428 of your pole IDs, please attach the
  transformer attributes" (a much smaller and more grantable ask);
- a **spatial sample frame** for any imagery-based transformer survey.

**Caveats, stated plainly.**
1. `POLEMAT` = Wood is *strong evidence of* but not *proof of* joint-use ownership.
   Verification path: spot-check a sample against street-level imagery, and ask PG&E
   to confirm the `B####` series in the data request.
2. This only finds utility poles **that carry a city streetlight**. Poles on blocks
   with no streetlight, mid-block poles, and rear-lot poles are invisible here. The
   true utility-pole count is **higher** than 4,499 — unknown by how much.
3. 2 of 7,969 records have null geometry but carry `LATITUDE`/`LONGITUDE` attributes,
   so all 7,969 are placeable.

## 2. Correcting the brief's OSM figure

Queried Overpass directly for the Berkeley admin boundary (2026-08-30):

| OSM tag | Count |
|---|---:|
| `highway=street_lamp` | 88 |
| `power=pole` | 84 |
| `power=tower` | 84 (transmission towers, not distribution poles) |
| `power=line` (ways) | 24 |
| `power=substation` | 17 |
| **`power=transformer`** | **7** |
| `power=minor_line` (ways) | 3 |

The brief's "88 Berkeley poles" is the **street_lamp** count; distribution poles in OSM
number 84. Either way the conclusion holds — OSM is unusable as an inventory. Note in
particular that OSM has **7** transformers mapped in a city that certainly has
thousands.

## 3. The transformer inventory: not public, and here is exactly why

**Nothing gives a public, per-pole Berkeley transformer count today.** Each candidate
route and its specific blocker:

| Route | Status | Blocker |
|---|---|---|
| **PG&E JUMP** (Joint Use Map Portal) | Closed | Restricted by PG&E's terms to utilities and communications infrastructure providers in the service territory, plus their contracted vendors under NDA. Members can download up to 1,000 poles at a time. We are not eligible. |
| **CPUC pole databases (D.21-10-019)** | Closed | The Track 2 decision requires AT&T, PG&E, SCE, SDG&E and Verizon to build pole-attachment databases (20 data fields, phased in Aug 2023 – Apr 2024) — but **D.21-10-019 expressly does not intend them to be publicly available**. Access is for attachers and authorized users. |
| **PG&E GRIP / ICA map** | Registration-gated | The public 2020 ArcGIS web map for PG&E's ICA layers (`ICADisplay_gdb` — LineDetail, FeederDetail, Substations) is **now token-protected**: every query returns `499 Token Required`, verified 2026-08-30. Bulk ICA downloads run through the Grid Resource Integration Portal by division. **Worth pursuing** — it is the closest thing to a public distribution-network dataset, and eligibility needs checking. |
| **EPA PCB Transformer Registration Database** | Public but nearly empty for our purpose | Registration under 40 CFR 761.30(a) applies to **PCB Transformers (≥500 ppm)**. Pole-mounted distribution units are almost all **PCB-Contaminated (50–499 ppm)** and are *not* registration-triggering. Expect near-zero Berkeley pole-mounted entries. |
| **CPUC GO 165 inspection reports** | Partly public | GO 165 requires records of circuit/equipment inspected, inspector, date, problems found, and scheduled corrective action. Historic annual reports are posted at `files.cpuc.ca.gov/ESRB_Audits/GO165/`; recent years need a PRA request. These are **inspection** records, not an asset register — useful for condition, not for a count. |
| **PG&E WMP filings (OEIS/CPUC)** | Public PDFs | Contain program-level equipment counts and describe replacement of overhead distribution line transformers. Granularity is system- or region-level, not per-pole. Not yet mined — queued. |
| **PG&E GRC (A.25-05-009, 2027 GRC)** | Public filings | Exhibits/workpapers are the most likely public home of a **distribution transformer unit count and age distribution**. Not found in search; needs direct mining of `docs.cpuc.ca.gov`. Queued. |

### The regulatory hook that makes manufacture year the key field

**40 CFR 761.2**: any mineral-oil-filled electrical equipment manufactured **before
July 2, 1979** whose PCB concentration has not been established **must be assumed to be
PCB-Contaminated Electrical Equipment** (≥50 ppm, <500 ppm). And all pole-top and
pad-mounted distribution transformers manufactured before that date must be assumed
mineral-oil filled.

This is the spine of the security story, and it is a legal fact rather than an
allegation: **every pre-July-1979 pole-mounted transformer still in service in Berkeley
is, by federal regulation, presumed PCB-contaminated unless PG&E has tested it.** The
single most valuable field in the whole data request is therefore **manufacture year**,
followed by **test status**. Those two fields alone convert "thousands of old
transformers" into a defensible count.

## 4. What we can and cannot say about a Berkeley transformer count

**We cannot state a Berkeley transformer count, and should not estimate one yet.**
A ratio-based estimate (customers per transformer) would be a fabricated number
dressed as a finding. What we *can* say today:
- ~4,400+ located utility poles, of which some fraction carry transformers;
- most residential poles carry 0 or 1 transformer; three-phase locations carry banks of 3.

Two honest routes to a real number, in order of cost:
1. **Ask** (the data request in `records_requests/`).
2. **Count them ourselves from imagery** — pole-mounted transformers are visually
   unmistakable. We already hold ~4,400 pole coordinates, which is a ready-made sample
   frame: survey a stratified random sample (hills vs flats, arterial vs residential),
   get a transformers-per-pole rate with a confidence interval, and publish the
   estimate *as* an estimate with its method. This is the fallback if PG&E declines,
   and it is genuinely publishable.

## 5. A trap in the data: the "Berkeley" gas layer is regional

`Police/PublicSafety/MapServer/13` is named `PGE_gasPipelines` and is served from
Berkeley's own public-safety map. It is **not a Berkeley layer**. Its 5,411 features
extend east to longitude **-121.56** and south to latitude **37.46** — out past the
Central Valley. **Only 322 of the 5,411 touch the Berkeley envelope.** Quoting 5,411
as a Berkeley figure would be wrong by a factor of seventeen.

Corrected Berkeley-only figures (322 features, ~37.7 miles of line):

| | Berkeley-touching | Whole regional layer |
|---|---:|---:|
| Features | 322 | 5,411 |
| Distribution pipe ≥60 psig | 267 | 2,953 |
| Transmission pipeline | 47 | 2,403 |
| Transmission *or* distribution | 8 | 55 |
| Installed pre-1980 | 148 / 310 = **47.7%** | 2,766 / 5,203 = 53.2% |
| In a High Consequence Area | 46 | 1,404 |

Two further limits worth stating whenever this layer is used:
- **It only holds 60 psig and above.** The low-pressure street mains that actually
  feed individual houses are **not in it** and are not public anywhere. Pipey's gas
  half is therefore much less complete than the water and sewer halves.
- **It is a 2007–2016 snapshot** (`DateModifi` ranges over exactly that window), not
  today's network.

*How this was caught:* drawing the map. Fitting the view to all layers squeezed
Berkeley into a thumbnail because the gas geometry dragged the bounding box halfway
across the state. A table of counts would never have shown it — which is an argument
for building the map early in any layer sweep.

## 6. The other pipes, and the asymmetry that is the story

**EBMUD water mains — 13,396 segments, all within Berkeley.**
**63% were laid before 1960**; the largest single decade is the **1930s** (2,621
segments, 20%); the oldest on record is from the **1860s**. `MATERIALTY` is **100%
null** in the public layer — an honest gap and a good first question for EBMUD.

**Sanitary sewer — 7,744 mains, 29,484 laterals, 7,615 manholes.**
This layer carries a whole rehabilitation programme: `REHAB_YEAR`, `REHAB_NOTES`
(spec A/B/C/D), `CD_12YR_PLAN`, `Planning_Unit_Cost` and `Planning_Cost` per segment.
**4,939 of 7,744 mains are HDPE**, i.e. already relined, against 1,028 still vitrified
clay.

**The asymmetry to build the public story on:** Berkeley's sewer is being fixed on a
funded, scheduled, publicly documented clock — you can read the cost of each segment's
rehabilitation out of the City's own GIS. The transformers hanging over the same
streets have **no clock, no public register, and no count at all**. Same city, same
decades of age, opposite levels of public accountability.

## 7. Berkeley context worth carrying forward

- Berkeley has ~26 miles of arterial streets, **49% already undergrounded**, and ~36
  miles of collector streets, about **one-third** undergrounded; roughly **37.9 miles**
  remain, estimated at **~$134M**. Undergrounding District No. 48 (Grizzly Peak /
  Senior / Summit / Avenida) covers 178 residential parcels.
- The City has been pressing PG&E to include Berkeley in its 10,000-mile undergrounding
  program. Undergrounding is the one intervention that removes Poley, Stretch **and**
  the transformer at once — which is exactly why the transformer inventory is
  politically load-bearing.

## 8. Verification note on one brief item

The brief attributes the CPUC's 45-day pole-attachment "shot clock" to a contest over
Sonic's access. Searching surfaced the shot clock in connection with a **Crown Castle**
arbitration win against PG&E, with Sonic appearing as a party in related pole
proceedings. **Flagging rather than asserting** — worth pinning to the actual decision
before it appears in any public writing.
