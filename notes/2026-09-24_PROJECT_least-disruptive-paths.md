---
title: "PROJECT — Paths to new housing that least affect the small commercial district"
date: 2026-09-24
type: project
status: open
area: notes
---

# PROJECT — Paths to new housing that least affect the small commercial district

**Standing question.** Berkeley's corridor debate assumes a trade: to get housing on College Ave you
must redevelop the shops. The Elmwood merchants hear that as an eviction notice and the housing
advocates hear the objection as obstruction, and both are arguing from intuition about a system
neither has measured. **Is the trade real?** How much housing can the district absorb along paths
that barely touch the commercial strip at all — and what do the city's own records say is actually
happening on those paths right now?

This is the frame the website already states — *"See if what you believe about new housing matches
what Berkeley is actually building"* — applied to the one corridor where the stakes are personal.

**Posture: measurement, not advocacy.** The honest finding may be that the gentle paths are too slow
to matter, or that they are doing more than anyone thinks. Both are publishable. What is not
publishable is a number chosen because it supports a side. Everything here is built from primary
sources (Accela, CPRA, Alameda assessor, Sanborn); **CKAN/HCD stays the verification target and
never a source**, because "the city's APR agrees with us" is circular.

---

## The four evidence streams

### 1. Middle Housing — the legal capacity, and the revealed demand

Effective **1 Nov 2025**, up to **8 units on almost any parcel**. In eleven months: **31 projects,
largest proposes 4 units, net +16 dwellings, ZERO completions.** Two-thirds are single-family
homeowners enlarging their houses; one application *removes* a unit; one converts a medical office
back to a single house.

→ **`notes/2026-09-24_middle_housing_first_year.md`** · tracker:
`scripts/middle_housing_tracker.py`, reviewed counts in
`data/reference/middle_housing_units_reviewed.csv`

**What this stream is for.** It separates **what the law allows** from **what people do with it** —
which is precisely the gap between intuition and evidence the project exists to measure. An upzoning
that nobody uses at scale is weak evidence for either side's prediction, and that is itself the
story. Re-run the tracker quarterly; the trend over 2-3 years is the real result, not the snapshot.

### 2. ADUs — the path that touches no commercial parcel at all

Same eleven months: **217 ADU building records, 35 issued, 15 FINALED.** ADUs completed 15 dwellings
while middle housing completed none. The citywide ADU cohort is ~857 units, validated at ~93% recall
against the APR oracle (`scripts/adu_mh_cohort.py`).

**What this stream is for.** It is the existence proof for the project's whole premise: a delivery
path that adds units without a single commercial demolition, already running at ~7× middle housing's
volume. The questions to answer: **how many more can the Elmwood's lots physically take?** (needs
lot size, existing coverage, rear-yard geometry — we have all three); **what is the ceiling?**; and
**is the rate rising or flat?**

### 3. Block-level housing density — the denominator everything else needs

`scripts/city_block_index.py` computes density and floor-area index on **1,119 REAL city blocks**
(street-enclosed, from the second GIS endpoint — *not* Census tabulation blocks, which merge parallel
streets and are wrong for this). Overture footprints by overlay, parcels by point-in-polygon with
owner classification.

**Known correction outstanding:** `notes/Elmwood-housing-argument.md` counts the Elmwood as **93
blocks** from the Census layer; on the real layer it is **73-74**. Re-baseline `JN-M_corridor_density`
before any figure from it is published.

**What this stream is for.** Every claim in the project is a *rate* — units per block, units per
acre, share of blocks affected — and this is the denominator. It also answers the question the
merchants actually ask: *how much housing arrives near me, and where does it go?*

### 4. Historical density — has this district changed before?

Sanborn 1911 and 1950, sheets 179/180, read 2026-09-24. **The Elmwood commercial strip did not exist
in 1911** — vacant lots on College between Russell and Ashby, while the residential blocks around it
were already built out. By 1950 it was continuously built, **one storey everywhere**, and it is one
storey today.

→ **`notes/2026-09-24_sanborn_elmwood_1911_1950.md`** · `scripts/fetch_sanborn_elmwood.py`

**What this stream is for.** It converts "the Elmwood has always been like this" from an assumption
into a testable claim — and the claim is **false for the commercial strip** (invented between 1911
and 1950) and roughly **true for its height** (one storey for ~75 years). That is a genuinely
surprising, genuinely sourced fact, and it reframes the debate: the strip is not an inheritance
being defended, it is a 20th-century addition that stopped changing.

---

## What is missing, ranked

1. **Join the Middle Housing and ADU cohorts to the real block layer.** Neither is mapped to blocks,
   so we cannot yet say *which* blocks absorb gentle density, or whether the Elmwood is above or
   below the city rate. This is the single highest-value missing join and everything else builds on
   it. Both cohorts are geocoded to parcel centroids already; the block layer is built. It is an
   afternoon.
2. **Elmwood lot geometry → ADU/middle-housing headroom.** How many of the ~74 blocks' parcels can
   physically take a rear unit? We have parcel polygons, Overture footprints, and block geometry —
   the calculation is coverage and rear-yard depth, and it produces the project's central number:
   *the gentle-path capacity of the district.*
3. **Parcel depth on the College corridor.** The consultant's Grade 2A criterion turns on an **80-ft
   depth** and our min-rotated-rectangle proxy measured the *frontage* (40-70 ft) not the depth.
   Surveyed depths are still needed; this decides which corner parcels are even eligible.
4. **Per-record capID detail pages** for the middle-housing cohort, to replace the address join with
   the Planning record's own "Related Records" link. Removes the tracker's main weakness.
5. **1929 Sanborn via ProQuest** (John's UC login) — splits the 39-year gap and would date the
   commercial strip's construction to the decade.
6. **Commercial-side measures** already sketched but not built: revenue per block, sales-tax
   contribution, employees per block, distance residents travel for food. These say what the
   district *does*, so that "protecting the shops" becomes a measurable claim rather than a mood.

## Deliverables this feeds

- **berkeleybuild.com** — a corridor view that shows gentle-path activity block by block next to the
  corridor proposal, so a reader can compare the two futures on one map.
- **The DFW-voice history** — this project supplies its spine: intuition vs. knowledge, told through
  a district that genuinely does not know its own past (the 1911 vacant lots) or its own present
  (31 middle-housing projects, 0 built).
- **The op-ed / Measure U advisory work** — a defensible capacity number for the gentle paths is the
  thing that argument currently lacks.

## Standing cautions

- **The RHNA progress bar stays held.** v2 models ~28 tracked projects with a materialized primary
  BP against Berkeley's hundreds of housing BPs; publishing that as city progress understates
  reality. CO-completion metrics are complete and remain the trustworthy headline.
- **Segment the CO-only cohort** (713 projects with no pre-CO lifecycle event) out of any funnel
  metric — it inverts funnels.
- **Derive, never hardcode.** Every figure above must come from a script against a timestamped
  baseline, and a legitimate change is an **appended** baseline, never an edited constant. The
  middle-housing counts will move; the tracker recomputes them, and unreviewed records announce
  themselves rather than being silently guessed.
- **Small-n honesty.** 31 projects is a small number and eleven months is a short window. Say so
  every time. The trend matters more than the snapshot, which is the argument for re-running the
  tracker on a schedule rather than quoting today's figure as a finding.
