---
title: Middle Housing Ordinance — the first eleven months
date: 2026-09-24
type: note
status: open
area: notes
---

# Middle Housing Ordinance — the first eleven months

**Question John asked:** an updated list of every application for entitlement or building permit
under the Middle Housing law effective **1 November 2025**, which allows up to **8 units on almost
any parcel** in Berkeley — with entitlements, BPs issued, inspections and COs, which were unknown at
the last check (26 applications).

**Answer, as of the Accela sweep through 2026-09-19:** **32 records, 31 distinct projects.** The
count moved from 26 to 32 — six new since John last looked. But the interesting number is not 32.

Re-run: `python scripts/middle_housing_tracker.py --detail`
Output: `data/reference/middle_housing_tracker.csv` · hand-read unit counts in
`data/reference/middle_housing_units_reviewed.csv`

---

## The funnel

| stage | count | of 31 projects |
|---|---|---|
| applications filed | **32 records / 31 projects** | — |
| planning status **Approved** | 17 | 55% |
| under review / filed / pending / awaiting docs | 9 | 29% |
| withdrawn / closed / incomplete | 6 | 19% |
| addresses with a **construction** building permit | 19 | 61% |
| ...with a construction BP **issued** | 7 | 23% |
| ...with inspection records we hold | 2 | 6% |
| ...that passed a **Building Final** | **0** | **0%** |

**Zero completions. Zero certificates of occupancy.** Eleven months in, not one middle-housing
project has been finaled. Three permits at these addresses *are* finaled — a panel upgrade at 2780
Mabel, a panel upgrade at 1123 Blake, a re-roof at 2335 Russell. None is the middle-housing project.
That trap is why the tracker classifies every permit **construction** vs **incidental**; the naive
address join reports "3 built" and is wrong.

**Construction has genuinely started** at one site: **2808 Ninth St**, where the single-family house
is demolished and a duplex plus a garage-with-unit is going up. Setbacks/survey and anchor-bolt
inspections were approved 11 June 2026. That is the furthest any middle-housing project has got.

---

## The finding that matters: nobody is building 8 units

The ordinance permits up to 8 dwellings on almost any parcel. In eleven months:

- **largest project proposed: 4 dwellings** (2834 Eighth St, a warehouse converted to four units —
  still a pre-application under review). Nothing has come within half of the cap.
- **9 of 31 projects add dwellings at all.** **21 add none.** **1 removes one.**
- **net change across the whole cohort: +16 dwellings**, and the first of them is not yet built.

What the other 21 are: *major residential additions to single-family houses.* Lift the house and
add a storey below (2332 California). Add a partial second storey (1136 Francisco, 1468 Tenth,
2807 Ellsworth, 2227 Woolsey). Extend to the rear (1235 Ordway, 2015 Prince, 2800 Prince). Expand
the basement (2709 Dana). The Middle Housing Ordinance is being used, overwhelmingly, as **a
permitting pathway for single-family homeowners to enlarge their houses** — not as a multiplex
pathway.

Two records make the point sharply:
- **2215 Grant St** — "Middle Housing Zoning Certificate for the **decommission of one attic unit**
  for code compliance." A middle-housing application that *removes* a dwelling.
- **3036 Regent St** — "change of use of a **medical office to a single-family house**, restoring
  the property back to its original status." Middle housing used to convert commercial back to one
  house.

**Where the units actually come from** — the 9 projects that add dwellings, +16 net:

| address | proposal | net |
|---|---|---|
| 2834 Eighth St | warehouse → 3-storey building, 4 units | +4 |
| 2808 Ninth St | demo SFH → duplex + garage unit (3 total) | +2 |
| 2336 Eighth St | duplex → 4 units inside the existing shell, no expansion | +2 |
| 3032 Mabel St | demo uninhabitable SFH → 3 homes | +2 |
| 2335 Russell St | 2 one-beds → 4 studios | +2 |
| 2615 Ashby Ave | 2nd-floor medical office → 2 units, office stays below | +2 |
| 1521 Holly St | demo SFH → 2 detached units | +1 |
| 1803 Eighth St | new detached dwelling beside the existing one | +1 |
| 3036 Regent St | medical office → 1 dwelling | +1 |
| 1872 Allston Way | 3 townhomes on a 3,700 sf lot | *unknown — prior count not stated* |
| 2215 Grant St | decommission an attic unit | **−1** |

Note three of these (2834 Eighth, 2615 Ashby, 3036 Regent) **convert commercial or industrial space
to housing** — which is directly the "least affects the small commercial district" question, and
cuts both ways: it is housing without demolition, but it is also commercial space leaving.

---

## For scale: ADUs are doing ~7× the work

Same window (2025-11-01 → 2026-09-19), same Accela sweep:

| | Middle Housing | ADU |
|---|---|---|
| building records | 19 addresses / 26 construction permits | **217** |
| permits **Issued** | 7 | 35 |
| **Finaled (built)** | **0** | **15** |

ADUs have completed **15** dwellings in the period in which middle housing completed **none**.
Whatever the Middle Housing Ordinance eventually does, the accessory-dwelling pathway is currently
the one delivering units — and it does so without touching a commercial parcel at all.

---

## Method, and what would make it stronger

Two weaknesses, both documented in the script's docstring and both real:

1. **The Planning→Building join is by normalised street address.** The two Accela modules share no
   key in the list view, so a match proves a permit exists *at that address*, not that it belongs to
   the middle-housing project. Mitigated by the construction/incidental classifier and by printing
   every description for eye-checking; counts are stated as "addresses with a construction permit",
   never "middle-housing units permitted". **The fix is the per-record capID detail page** — the
   harvester can fetch it, and the Planning record's "Related Records" section names the BP directly
   (2808 Ninth's BP description even cites `PLN2025-0117`). Queued.
2. **Inspection coverage is partial** — 1,300 permits in `data/raw/accela_inspections/`, which is
   what the harvester has fetched, not every permit. A permit with no file reads `no inspection
   data`, which is **not** `no inspections`. The tracker prints a harvester queue; right now six
   issued construction permits need fetching: `B2025-05202 B2025-05429 B2025-05429-REV01
   B2025-05773 B2025-05896 B2026-01141`. Per the tool-vocabulary rule, a 0-result is not evidence
   of absence until retried.

Unit counts are **hand-read** from the full Accela descriptions (which are unusually explicit — they
state demolitions and resulting unit counts) into `middle_housing_units_reviewed.csv`, keyed by
record. A regex first pass over-counted by 7 — it read "addition to an existing duplex" as adding
units. Any record missing from the reviewed file prints **UNREVIEWED** rather than being guessed at,
so new applications force a human read.

**Not yet done:** these 31 parcels are not joined to the block layer from
`scripts/city_block_index.py`, so there is no map of *which blocks* are absorbing middle housing.
That join is the bridge to the density argument and is the obvious next step.
