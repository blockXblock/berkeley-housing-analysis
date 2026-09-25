---
title: "Historical block-density sources — what to fetch, and which need UC credentials"
date: 2026-09-24
type: plan
status: for-review
area: notes
---

# Historical block density: the acquisition list

**Goal:** show, block by block, how dense Berkeley is *and how it got that way*. The present-day
layer is built (`scripts/city_block_index.py` — 1,119 real blocks, measured coverage, block FAR).
What is missing is time depth. These are the sources, in priority order, with what each answers.

**Division of labor:** John authenticates (UC faculty credentials); CC can index, fetch and parse
anything open. Everything below is identified — none of it is speculative.

---

## 1. Sanborn fire insurance maps — the block-by-block historical record

**Not Thomas Brothers.** Thomas Brothers are street atlases — good for street geometry, silent on
buildings. **Sanborn sheets show every building footprint with number of STORIES, construction
MATERIAL and USE**, which is precisely the present-day index one century earlier.

### FREE, already indexed (no login) — Library of Congress
`data/raw/sanborn/loc_berkeley_index.json` · **12 Berkeley editions, 235+ sheets:**

| date | sheets | note |
|---|---|---|
| 1890-04 | 6 | "East Berkeley" |
| 1894-05 | 14 | |
| **1911** | **104 + 111** | two volumes — the first full-city coverage |
| 1917-11 | ? | |
| **1929** | 3 volumes | |
| **1950** | 4 volumes | LoC coverage ends here |

Public domain, downloadable as high-resolution TIFF/JP2. **CC can fetch all of these now.**

### NEEDS UC LOGIN — ProQuest *Digital Sanborn Maps*
`digitalsanbornmaps.proquest.com` — the licensed set. Worth it for **post-1950 updates and the
paste-on correction layers** that LoC lacks. UC's Earth Sciences & Map Library notes it largely
duplicates the CRL microfilm, so check overlap against the LoC index above before spending time.

---

## 2. Historical aerial photography — the gap-filler between Sanborn editions

**UC Berkeley Earth Sciences & Map Library holds 80,000+ air photos, 1931 to present**, Bay Area
emphasis, scales 1:2,400 – 1:40,000. Many are digitized in the Library's **Digital Map & Air Photo
Collections**. Reference: `epslibs@berkeley.edu`.

**Why this matters more than it sounds:** Sanborn stops at 1950 in the free set. Berkeley's
post-war densification — the apartment boom, the ADU and in-law layer — happens *after* that.
Aerials give footprints at dates Sanborn does not cover, and at 1:2,400 individual buildings are
resolvable. Combined with the Overture footprints (2026) that is a footprint time series.

---

## 3. Alameda County block books — the pre-GIS version of what we just built

Historical assessor **block books** record every lot within every block, by block. That is the
direct ancestor of `city_block_index.py`, and it would let the present-day block geometry be
traced backwards through subdivision. **Search UC Library Search and WorldCat** for Alameda County
block books / Berkeley lot books. Likely in Bancroft or Earth Sciences.

---

## 4. BAHA and the Bancroft — building-level documentation

- **BAHA** (Berkeley Architectural Heritage Association): building files, the plaque project,
  architect attributions. Not a spatial dataset — a per-building archive, best used to verify
  specific parcels rather than to compute anything.
- **Bancroft Library**: original fire insurance maps for some California cities, architectural
  drawings, Berkeley collections. Worth a catalog search for Berkeley architectural drawing
  collections and for anything from the Department of City & Regional Planning.

---

## 5. Still unsent, and it asks exactly the right question

**`notes/2026-08-14_waddell_outreach.md` — status `open`, drafted 2026-08-14, never sent.**
Question 3 asks Paul Waddell (UrbanSim founder, UC CED) for his **assessor → building-attributes
pipeline** — turning messy county records into reliable year-built / sqft / units / type. That is
the exact problem behind the `implied_stories` anomaly below. A faculty-to-faculty email costs
nothing and may save months.

---

## What the historical layer would fix

The present index carries one known defect worth naming, because a historical source may resolve it:

> **`implied_stories` (floor area ÷ footprint) medians 1.10 citywide** — too low for a city with
> this many two-storey houses. Assessor `BldgSqft` appears to omit basements and garages while
> Overture footprints include garages, sheds and ADUs. **Both errors push the same direction.**

**Sanborn sheets state the storey count directly on every building.** Digitizing even one
edition's storey counts for a sample of blocks would calibrate the assessor-vs-footprint gap and
convert `implied_stories` from a diagnostic into a publishable figure.

---

## Suggested order

1. **CC fetches the 235 LoC sheets now** — free, no login, and enough to test whether storey counts
   can be read reliably at that resolution.
2. **John tries ProQuest Digital Sanborn** — establish whether post-1950 Berkeley coverage exists.
3. **John queries UC Library Search / WorldCat** for Alameda County block books and Berkeley air
   photo runs; CC drafts the search strings if useful.
4. **John sends the Waddell letter.**
