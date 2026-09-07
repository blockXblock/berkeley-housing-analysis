# Archival research — the 23 buildings in the Panoramic/Kennedy tour

**2026-09-04.** Purpose: `kml/tours/panoramic-kennedy-legacy.kml` carries its own 23 hand-traced
polygons, named by project rather than address ("GAIA Building (2001) · 91 units"), so the standard
label engine — which matches on address against the canonical geometry — could label none of them.
This establishes what each building is, whether v2 already holds it, and what a gated write would
need.

## Method, and why it beat the archives

The polygons carry coordinates. So identification was a **spatial join**, not a search: each
polygon centroid → nearest Alameda assessor parcel in `berkeley.db` (29,130 parcels with
coordinates) → canonical APN via `housing_rules.to_canonical_apn` → v2 by `project_parcels`.

**Every one of the 23 matched a parcel at 0–4 m.** Whoever traced those polygons traced them
accurately, and that single fact removed most of the archival work before it started.

Units and completion years then came from the developer's own project pages (panoramic.com),
which are a **secondary source** and are recorded as such below.

## What v2 already holds — corrected twice while checking

| method | found in v2 |
|---|---|
| developer name = "Panoramic Interests" | 6 |
| + address match | 8 |
| + **canonical APN match** | **9** |

The APN layer alone found GAIA's parcel. This is the three-layer cross-walk rule (CLAUDE.md rule 4)
earning its keep: address matching alone would have reported GAIA missing.

**But one of the nine is a false positive.** The GAIA parcel `057-2030-002-00` holds **proj775 —
2116 Allston, 2 units, CO 2021** — which is *not* the 91-unit GAIA Building of 2001. It is a later
small permit on the same parcel (the CO-only import cohort). Attributing GAIA's developer to it
would have put a wrong fact in v2 *and* hidden that GAIA is genuinely absent.

**Final: 8 present, 15 absent.**

### Written 2026-09-04 (gated, snapshot `keep_snapshot_2026-09-04_pre-panoramic-attribution.db`)

Three projects v2 held without crediting the developer. Unit counts corroborate independently — the
tour caption and v2 agree on each without either being derived from the other.

| project | address | units | tour name |
|---|---|---|---|
| proj46 | 1745 Cedar St | 6 | Panoramic Cedar (2027) |
| proj47 | 1850 Berryman St | 6 | Panoramic Berryman (2027) |
| proj890 | 2539 Telegraph Ave | 70 | Panoramic Berkeley (2019) |

v2 now credits Panoramic Interests on **9** projects. proj775 deliberately left alone.

## The 15 absent — findings

**Two are not housing and must never be added as housing projects:**

| building | year | what it actually is |
|---|---|---|
| UC Storage | 2006 | **800 storage units**, not residential |
| 2130 Center | 2009 | **commercial only** — historic renovation, no residences |

They belong in the tour as part of Kennedy's built work; they do not belong in a housing pipeline.
That leaves **13 housing candidates**.

**Confirmed from the developer's own pages (secondary source, recorded as such):**

| building | year | units | affordable | assessor situs | canonical APN | assessed Imps |
|---|---|---|---|---|---|---|
| The Berkeleyan | 1998 | 56 | — | 1910 Oxford St | 057-2047-002-01 | $27,967,816 |
| GAIA | 2001 | **91** | **19 low-income** | 2116 Allston Way | 057-2030-002-00 | $41,422,542 |
| Acton Courtyard | 2004 | **71** | **20 low-income** | 1375 University Ave | 057-2073-004-00 | $447,050 |
| Fine Arts | 2004 | **100** | **20 low-income** | 2115 Haste St | 055-1891-010-00 | $1,174,095 |
| Touriel | 2004 | 35 | — | 2004 University Ave | 057-2025-014-00 | $13,980,003 |
| Bachenheimer | 2004 | **44** | **7 low-income** | 2119 University Ave | 057-2046-009-00 | $18,289,246 |

**The affordability figures are the real prize.** 66 below-market units across four buildings, from
1998–2004, that the CPRA permit feed (2018–2025) cannot see at all.

**Carried from the tour's own captions, not yet independently confirmed:**
Henry Court 1990/6 · Westside Place 1993/7 · Shattuck Lofts 1995/24 · University Lofts 1997/29 ·
ARTech 2002/21 · Shattuck Studios 2018/22.

## Address discrepancies — resolved, and the resolution is a rule

Five buildings' developer-published addresses disagreed with the traced parcel's assessor situs.
Checking each against the assessor settled four of them the same way:

| building | developer says | assessor situs | verdict |
|---|---|---|---|
| ARTech | 2002 Addison | 2001 Addison | **2002 Addison does not exist in the assessor** |
| Acton Courtyard | 1370 University | 1375 University | **1370 does not exist** |
| Fine Arts | 2110 Haste | 2115 Haste | **2110 does not exist** |
| Panoramic Legacy | 1685 Shattuck | 1690 Shattuck | **1685 does not exist** |

**The developer publishes marketing addresses; the assessor holds the assessed one.** Where they
disagree, the traced parcel is right. This is the same division-of-authority pattern CLAUDE.md
rule 4 case (2) already records for corner lots — a second instance, from a different cause.

## Two open cases — do NOT write these without resolving

**Westside Place is a condominium, not a parcel.** The traced centroid sits on `54-1746-36`
(947 Pardee St, **Imps $0**), but four sibling parcels sit at **0 m** from the same point:
`-29`/`-30`/`-31`/`-32` = 2720/2718/2716/**2714** 9th St, units 1–4, each separately assessed
($517k, $632k, $427k, $422k). The developer's "2714 9th St" is **unit 4**. A 7-unit project mapped
across ~7 parcels needs a parcel SET, and 947 Pardee at $0 is likely common area, not the building.

**Fine Arts' assessment does not add up.** 100 units assessed at **$1,174,095** is implausible —
GAIA's 91 units are assessed at $41.4M. Neighbouring parcels (2421 Shattuck $2.0M, 2429 Shattuck
$331k, 2401 Shattuck $0) are no better. Either the building is condo-mapped like Westside Place, or
the complex spans Haste and Shattuck frontages and the value sits somewhere this single-parcel
match does not reach. **Unresolved.**

## Also flagged

`1752 Shattuck` (Panoramic Northside): a press source describes it as **7-story, 68-unit** while v2
and the tour both say **72**. Not chased; recorded so it is not lost.

## What a gated write would need

1. A **provenance convention for secondary sources.** Rule 1 says build from CPRA + assessor and
   record "unknown with provenance" where they are silent. These unit counts come from the
   developer's website. They are good but they are not primary, and v2 has no way to say so today.
   That convention is the prerequisite, not the data entry.
2. Parcel sets for Westside Place, and a resolution for Fine Arts.
3. A decision on whether pre-2018 completions belong in a pipeline built from a 2018–2025 permit
   feed at all, or whether they are a distinct class of record.

Machine-readable parcel map: `scratch/2026-09-04/kennedy_parcel_map.json`.

**Sources:** [Panoramic projects index](https://www.panoramic.com/projects/) ·
[GAIA](https://www.panoramic.com/project/gaia-building/) ·
[Fine Arts](https://www.panoramic.com/project/fine-arts-building/) ·
[Acton Courtyard](https://www.panoramic.com/project/acton-courtyard/) ·
[Bachenheimer](https://www.panoramic.com/project/bachenheimer/) ·
[Touriel](https://www.panoramic.com/project/touriel-building/) ·
[The Berkeleyan](https://www.panoramic.com/project/berkeleyan/) ·
[UC Storage](https://www.panoramic.com/project/uc-storage/) ·
[2130 Center](https://www.panoramic.com/project/2130-center/) ·
[Berkeleyside, Equity Residential purchase](https://www.berkeleyside.org/2015/11/16/equity-residential-to-sell-8-berkeley-apartment-buildings)

---

## Accela probe of the historic Panoramic buildings (2026-09-06)

After fixing the address-search harness (Accela now errors on any date fill — commit e01d2d2),
probed the pre-2018 Panoramic buildings in the Building module. **The earlier assumption of a
"coverage cliff before 2010" was WRONG — Accela holds most of them:**

| building | address searched | Building records |
|---|---|---|
| GAIA (2001) | 2116 Allston | 10 |
| Fine Arts (2004) | 2451 Shattuck | 12 |
| Berkeleyan (1998) | 1910 Oxford | 5 |
| Shattuck Lofts (1995) | 1849 Shattuck | 10 |
| University Lofts (1997) | 1801 University | 2 |
| ARTech (2002) | 2001 Addison | 4 |
| UC Storage (2006) | 2721 Shattuck | 19 |
| 2130 Center (2009) | 2130 Center | 13 |
| Shattuck Studios (2018) | 2711 Shattuck | 4 |
| Henry Court (1990) | 1509 Henry | 0 |
| Westside Place (1993) | 2714 9th | 0 |
| Acton Courtyard (2004) | 2002 Acton | **0 — suspect** |
| Touriel (2004) | 2004 University | **0 — suspect** |
| Bachenheimer (2004) | 2119 University | **0 — suspect** |

**9 of 14 have Accela records.** The three 2004 zeros (Acton, Touriel, Bachenheimer) are almost
certainly ADDRESS false-negatives, not true absences — these are substantial buildings, and it is
the same marketing-vs-assessed-vs-Accela address divergence documented above (Accela may index a
corner building on its other frontage, or a different street number). A probe by exact street
number can miss them; a street-name-only search or the alternate frontage would likely find them.
The two genuine zeros (Henry Court 1990, Westside Place 1993) are the oldest and smallest.

**Consequence:** the architect plans / tabulation data for the historic Panoramic buildings are
reachable in Accela and can be harvested — they need not come only from the developer's website.
The harvest workflow (discover_url by permit number, or address search → record → attachments) is
now unblocked.

### Address→record discovery for the 9 (2026-09-06) — and the real coverage cliff

Ran the fixed address search for all 9 historic buildings that returned records, and inventoried
every Accela record number (full list: `data/reference/kennedy_historic_accela_records_2026-09-06.json`).
**All 54 records are Building-module (B-) permits — none are Planning (ZP) records**, because
Berkeley's Planning module post-dates these buildings' entitlements.

The important nuance: having records ≠ having the ORIGINAL construction documents. Classifying each
B-permit's year against the building's completion year:

| building | built | records | construction-era permit | plans recoverable from Accela? |
|---|---|---|---|---|
| Fine Arts | 2004 | 12 | **B2006-04062** | likely |
| UC Storage | 2006 | 19 | **B2008-00223** | likely |
| 2130 Center | 2009 | 13 | **B2010-02709** | likely |
| Shattuck Studios | 2018 | 4 | **B2016-05441** | likely |
| GAIA | 2001 | 10 | none (earliest B2007) | **no — predates Accela** |
| Berkeleyan | 1998 | 5 | none (earliest B2020) | **no** |
| Shattuck Lofts | 1995 | 10 | none (earliest B2015) | **no** |
| University Lofts | 1997 | 2 | none (earliest B2021) | **no** |
| ARTech | 2002 | 4 | none (earliest B2016) | **no** |

**The coverage cliff is ~2005-2006 and it is about the ORIGINAL construction record specifically.**
Later maintenance/renovation permits exist for all 9, but the architect plan set + 1.E tabulation
for the five buildings completed before ~2005 (GAIA, Berkeleyan, Shattuck Lofts, University Lofts,
ARTech) are not in Accela — they are paper-archive or developer-website only. Four buildings
(Fine Arts, UC Storage, 2130 Center, Shattuck Studios) have a construction-era B-permit worth
harvesting for documents. Also surfaced: 3 non-permit records (GAIA ESR-2022-01017 + PREAPP000535;
Shattuck Lofts PREAPP000155).

**Net:** the harvest target for original plans is 4 buildings, not 9. This is itself a Clariti
requirement — a permit system should not lose the construction record when the vendor's digital
coverage begins; retro-digitisation of pre-2005 paper permits is part of a complete built-environment
record.

### Building-record document harvest (2026-09-06) — no plan sets, as the rule predicts

Ran the Building-module document harvester (discover_url module_hint="Building" → harvest_record with
the detail href, which skips the ZP-only gate — the mechanism generalizes across record types, per
generalize_test.py) on the 4 construction-era B-records: Fine Arts B2006-04062, Shattuck Studios
B2016-05441, UC Storage B2008-00223, 2130 Center B2010-02709.

**All 4 discovered cleanly; all 4 returned NO-PLANSETS. Zero documents.** This is the
`plansets-on-zp-not-bp` rule confirmed: plan sets attach to the Planning (ZP) record, not the
Building (BP) record. The historic buildings' Planning records predate Accela's digital Planning
module, and their Building records don't carry the architect plans.

**Conclusion for the historic Panoramic buildings: no architect plans are recoverable from Accela.**
The developer-website figures (already in the v2 entities at MEDIUM confidence) are the best
available source; the tour-caption figures (LOW) remain unverified. This is not a gap to keep
chasing — it is a hard limit of Accela's coverage for pre-2005 construction, and itself a Clariti
requirement (retro-digitise pre-2005 permits + attach plans to a project, not scattered by record
type).
