# Elmwood (C-E): which parcels meet the Option 1B criteria

**2026-10-24, read-only.** This check replaces the 2026-09-23 corner check in
`notes/2026-09-23_czu_narrative_evidence_spine.md` §4 and §9. That check found corners from address points
and estimated depth with a rotated rectangle. The script is `scratch/2026-10-24_corners/corner_check.py`
and its output is `scratch/2026-10-24_corners/ce_parcels_option1b.csv`.

## The criteria
From the May 6, 2026 staff report (Item 10A, pp. 4–5), a parcel must meet all of:
- a lot of at least 7,000 sf
- a lot depth of at least 80 ft
- a corner location
- no existing residential units
- not designated a historic resource

The staff presentation (slide 15) words the third test as **"Corner or through lot"**.

The Planning Commission's 6–2 motion adopted "the Alternative 1B map" and allowed no further lots to qualify by
aggregation. For the Elmwood, that map is slide 16 of the presentation; its 1B parcels total 1.0 acre.

## Method
All five tests are measured from primary layers.
- **Scope:** every parcel the Raimi geodatabase zones Elmwood Commercial on the College corridor, plus the
  Wells Fargo lot (52-1567-16), which Section 14 rezones from R-2 to C-E. That is 36 parcels, all with an
  assessor polygon.
- **Lot size:** the area of the assessor polygon. It agrees with Raimi's `Lot_area_sqft` on all 36.
- **Frontage:** the edges of a parcel that no neighboring parcel shares. Each edge is named by the nearest City
  street centerline (`Street_Centerline.geojson`); alleys and paths are excluded.
- **Corner or through lot:**
  - corner = frontage on two named streets whose frontages meet at 30° or more;
  - through = frontage on two roughly parallel streets.
  - None of the 36 is a through lot, so the report's wording and the slide's wording give the same answer.
- **Depth:** the average perpendicular distance from the front lot line across the lot, sampled every 0.5 ft.
  On a corner lot the front is the shorter street frontage. This is the usual convention; the BMC
  definition could not be fetched, because berkeley.municipal.codes refuses automated requests.
- **Residential units:** Rent Board units on the parcel, from `data/reference/rent_control.csv` and the
  Raimi rent-controlled layer. The two sources agree on all 36.
- **Historic:** Raimi's `historic_resource` field.

## Result: five parcels, matching the City's map
**Three parcels meet all five tests on their own:**

| Parcel | Lot | Depth | Corner of |
|---|---|---|---|
| 2887 College (7-Eleven) | 14,372 sf | 119 ft | College and Russell |
| 2701 Webster (post office lot) | 9,363 sf | 111 ft | College and Webster |
| 2901 College (Nabolom / Five Little Monkeys) | 7,140 sf | 112 ft | College and Russell |

**Two more appear on the City's 1B map only through aggregation with 2701 Webster:**

| Parcel | Lot | Fails |
|---|---|---|
| 2709 Webster | 6,791 sf | lot size; not a corner |
| 2999 College | 4,114 sf | lot size; not a corner |

**Checking these five against the City's map:**
- Slide 16, zoomed in, shows three parcels shaded at Webster: 2999 College, 2701 Webster (with the notch
  where 2999 sits) and 2709 Webster. The other two shaded parcels are 2887 and 2901 College.
- The five lots total 41,780 sf, or 0.96 acre, which the slide rounds to 1.0 acre.
- The same parcels give the 1A map's 0.9 acre: 2887 College, the three Webster parcels and the Wells Fargo
  lot total 0.93 acre.

**Ownership:** 2701 Webster, 2709 Webster and 2999 College are owned by JCJ9 Property Management LLC and
Earl J. March, trustee. 2901 College is owned by JCJ9 Property Management LLC. The 7-Eleven parcel is owned
by Ward J. Miottel Jr., trustee. This is assessor public record.

**Parcels that fail a single test:**
- **2944 College** (College and Ashby corner): 7,529 sf, 104 ft deep, but 5 Rent Board units.
- **2642 Russell** (City-owned, Raimi grade 3B): 10,839 sf, but not a corner.
- **2711 Ashby Place** (Wells Fargo lot): a corner of Ashby Place and Ashby Avenue, 82 ft deep, but only
  5,750 sf. It is on staff's 1A map, not the 1B map.

## What changed from the September check
1. **2887 College and 2701 Webster are corners.** The September detector needed a City address point on
   both streets and missed them.
2. **2901 College is 112 ft deep, not 62.** The rotated rectangle measured frontage, not depth.
3. **The College/Alcatraz parcel (052-1410-016-01) is outside this district.** It isn't zoned C-E, so it is
   not on the Elmwood 1B map. The September finding that the criteria select a parcel graded "no
   redevelopment potential" applies to the criteria in general, not to the adopted Elmwood map.

## Consequence for the Elmwood tour (`kml/geometry/college-opportunity-sites.kml`)
- **On the adopted 1B map:**
  - 2887 College
  - the post office pair (2701 and 2709 Webster)
  - 2999 College
  - 2901 College
- **Not on it:**
  - the Wells Fargo lot (a 1A site, and below the lot-size minimum)
  - 2942 College (C & C Cleaners; 6,027 sf and not a corner)
  - the lot behind 2900 College, west side (City-owned parcels, not corners)
  - the lot behind 2900 College, east side (the rear of private store parcels)
