---
title: What we can and cannot count — structures, units, people, area
date: 2026-09-25
type: methodology
status: open
area: docs/methodology
---

# What we can and cannot count

John's model: the city is an **area**, partitioned into **parcels**; parcels carry **structures**;
some structures contain **housing units**; housing units contain **people**; and people who sleep in
Berkeley but not in a housing unit are counted separately. Blocks — areas bounded by streets — are a
convenient intermediate. The model is right, and everything in it is countable in principle.

This is what our data can actually answer, measured 2026-09-25, not asserted.

---

## The area closes — once you admit the Bay

From TIGER 2020 (`census_blocks_2020.geojson`, `ALAND20` / `AWATER20`):

| | acres | sq mi | |
|---|---|---|---|
| **land** | 6,654 | 10.40 | |
| **water** | 4,624 | 7.23 | **41% of the city** |
| total | 11,278 | 17.62 | |

**Two-fifths of Berkeley is the Bay.** Any per-area figure computed over the city's nominal 17.6
square miles is wrong by 70%. Always divide by land.

## But our two land partitions do not agree, and neither is complete

| partition | acres | share of land |
|---|---|---|
| parcels (`addresses_arcgis.LotSqft`, deduped to APN) | 5,579 | **84%** |
| real city blocks (1,119, street-enclosed) | 3,911 | **59%** |

Parcels + streets ≈ land, which is plausible. **The block layer is the one that does not close** —
it misses roughly 1,700 acres. Measured directly: **1,960 of 29,130 parcels (7%) fall outside every
city block, and 1,669 of those carry a structure.** They are the ungridded parts — the hills, the
campus, the parks, the shoreline. The block layer covers the part of Berkeley laid out in a grid.

**Consequence for the model:** blocks are a good unit for the flat, gridded city and a bad one for
the whole. Any citywide "per block" figure silently drops 7% of parcels and 1,669 structures. Use
parcels or land acres as the denominator for citywide claims; use blocks for corridor and
neighbourhood work, which is what they were built for.

---

## The four countable things, and why they don't reconcile

| thing | our count | source | grain problem |
|---|---|---|---|
| addresses | **65,459** | `addresses_arcgis` | 2.24 per parcel — naive sums double-count |
| parcels | **29,170** | assessor | legal, not physical |
| structures | **62,651** | Overture footprints | includes garages and sheds; no housing flag |
| registered rental units | **41,279** | Rent Board registry | **rentals only** — no ownership units |
| tracked pipeline units | **19,956** | v2 | **since 2018 only**, and 52% is unbuilt paper |

**There is no crosswalk between these.** Four different countable things, four different grains, no
join that carries one into another. That is the single biggest structural gap in the model, and it
is why none of John's four questions can be answered end-to-end today.

## The four questions, answered honestly

**1. How many structures?** ~62,651 footprints from Overture — but only **14% carry a class** and
**3% a floor count** (71% have a height). We can count shapes. We cannot yet say which are
buildings people live in versus garages, sheds and utility enclosures.

**2. How many structures contain housing?** **We cannot say.** There is no structure→housing flag.
The obvious proxy, assessor `UseCode`, is documented in CLAUDE.md as unreliable for exactly this:
tracked multi-unit housing sits on commercial and institutional codes, while `1xxx` residential
codes mark single-family. A footprint-to-parcel overlay plus a trustworthy housing flag would
answer it; we have the first half.

**3. How many people live in the housing?** **We hold no population data at all.** Not one
population figure exists in `data/reference` or `data/processed`, and the TIGER blocks we hold carry
geography only — no `POP20`. This is the largest gap in the model and the cheapest to close: 2020
Decennial P1/H1 at block level is a free public download that joins to `census_blocks_2020.geojson`
on `GEOID20`.

**4. How dense?** Partially.
- **units per acre** — yes, for the 24 neighbourhoods in `neighborhood_density_2020.csv`, and per
  block from `city_block_index.geojson`. Both are units, not people.
- **people per acre** — **no.** No population layer.
- **beds per acre** — **no.** Bedroom counts exist in the Rent Board registry
  (`Number of Bedrooms`) but only for registered rentals, and UC is counted in beds rather than
  units, so the two are not additive.

---

## On vocabulary — John's point about jurisdictions

A "housing unit" is not one thing. The Census counts a unit by separate entrance and independent
cooking facilities. The Rent Board counts a registered rental, exempting owner-occupied and much
new construction. HCD counts what a jurisdiction reports. The assessor counts what it values, and
its `Units` field **counts commercial bays as units** — 2901 College reads "5 units" and is a toy
shop. UC reports **beds**, not units: Anchor House is 772 beds in 244 apartments.

These are not reconcilable by choosing one. The model should carry the definition alongside the
number, and never add across definitions. Adding UC beds to APR units is the concrete error to
avoid, and `generate_apr_v2.py` already guards it with `UC_EXCLUDE`.

---

## What would make the model answer its own questions

Ordered by value per effort:

1. **Census 2020 block population and housing counts.** Free, public, joins on `GEOID20` to a file
   we already hold. Closes question 3 and half of question 4 in an afternoon.
2. **A structure→parcel overlay.** Overture footprints intersected with parcel geometry, giving
   each footprint an APN and each parcel a footprint count and area. Turns 62,651 shapes into
   structures belonging to somewhere. Half-built already inside `city_block_index.py`.
3. **A housing flag that is not `UseCode`.** Best candidate is the Rent Board registry joined by
   canonical APN — it names 11,451 parcels that certainly contain rental housing. Combined with
   assessor residential codes it would bracket the answer from both sides.
4. **A street/right-of-way layer** to make the land partition explicit: parcels + ROW + water =
   city. We hold `row.geojson` and `Street_Centerline.geojson` but have never differenced them
   against parcels.
5. **Homelessness** is a real term in the model and we hold nothing. The annual EveryOne Home /
   Alameda County PIT count is the standard source; it is a count of people, not of places, and
   should be carried as its own figure and never folded into a housing-unit total.

## The honest summary

We can measure **area** well, **structures** as shapes, and **units** for a biased subset. We cannot
currently count **people**, and we cannot reliably say which structures are housing. Those two gaps
are what stand between the present data and the model John describes — and neither requires new
fieldwork, only a public download and a spatial join.
