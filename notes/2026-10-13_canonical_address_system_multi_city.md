---
title: "A canonical street-address system for every city (Oakland, San Francisco, San Jose)"
date: 2026-10-13
type: design sketch (notes/ -> settled ADR in docs/audit/ when built)
status: proposed (John asked, 2026-10-13: "create a canonical street address system for each city, using what we
  learned from our six months of detail work in Berkeley")
---

# A canonical street-address system for every city

## The one-sentence design
**Each city's own address authority is the dictionary. A shared normalizer proposes keys, a resolver looks them up in
that dictionary, a model chooses among the dictionary's candidates when the lookup fails, and whatever is still
unresolved stays "unmatched, with provenance".** Nothing is ever matched by a pattern alone.

## What Berkeley taught us (each lesson is now a rule)
| # | What happened in Berkeley | Rule for every city |
|---|---|---|
| 1 | Four per-script copies of address matching drifted apart (2026-07-03), and two were back by 2026-09-26; two more were still live on 2026-10-13 | **One canon, imported everywhere.** A city adds CONFIG, never a copy of the code. |
| 2 | The canon matched only 78% of v4's event addresses to the City's address list, and nobody knew, because it was tested on cases we wrote, not on the City's list | **Measure against the authority.** Every change reports the match rate per source, gained and lost. |
| 3 | `AV` (19,169 City points) and `BERKELEY CA 94705 United States` tails silently keyed as different streets | **Read the authority's own spellings first** (its type codes, its unit fields) before writing a single rule. |
| 4 | `\bdwelling\b` missed "dwellings" and dropped a 166-unit project; the regex role classifier polluted v2 | **Patterns parse formats; they never make judgments.** A judgment (is this the same place?) is a lookup or a quoted model reading. |
| 5 | APNs are re-platted and vanish (Acheson); corner lots carry two addresses (1951 Shattuck / 2108 Berkeley Way) | **An address is not a parcel, and neither is an identity.** Keep address ID, parcel ID and lineage separately. |
| 6 | Rose Walk vs Rose St, Indian Rock Path vs Ave, California St vs the state, Terrace Walk | **Collisions are measured, not guessed:** a change may not add a key that two different authority streets share. |
| 7 | 1817 Carleton A/B/C are three houses on three parcels; 2615 Telegraph Ave 101 is a unit in one building | **The unit is kept as its own field, never thrown away:** the site key drops it, the identity keeps it. |
| 8 | The model reading of permits disagreed with the cheap reader 2,625 times in 5,773 | **A model reading is a choice from the authority's candidates, verified, stored as dated evidence** -- never free text. |

## The layers
**L0 Authority registry (per city, data not code).** A row per city, like `APN_FORMATS`: the address-point source
(URL, pinned by SHA-256 and date), its ID field, its street-name / type / unit / number fields and their codes, the
centerline layer, the parcel layer and the APN format, the city/zip tails that appear in its records, its known aliases
(MLK, ordinals), and its permit system (Accela, AMANDA, ...).

**L1 Normalizer (shared code, per-city tables).** Today's `housing_rules.address.normalize_address` split into a
core (cut at the comma, strip the tails, cut after the street type, fold ordinals, keep halves) and the tables L0
supplies (type codes, aliases, tails). Returns `(house_number, street, street_type, unit)`: the unit is kept, not
lost. Berkeley's 42 cases become the shared test suite; each city adds its own.

**L2 Resolver.** `resolve(raw, city) -> (address_id | None, how, candidates)`: exact key in the authority; else
candidates (nearby numbers on the street, close street names, the record's parcel's address) handed to a model
reading (`scripts/llm_address_resolve.py` is the Berkeley prototype: a pick must be an offered candidate, a stated
address must appear verbatim and be in the list); else unmatched with provenance. Readings are append-only evidence
files, looked up by raw string.

**L3 Identity.** Projects and buildings carry the authority's address ID (where the city has one: SF's EAS ID), the
parcel through its lineage, and the raw strings as evidence. Joins use address ID or parcel, never the raw text.

**Gates (each city, each change):** share of each source's addresses resolved; gained/lost against the previous
canon (lost must be 0 or explained); no new two-street key collisions; the shared + city cases pass; a scratch chain
rebuild diff before anything reaches the canonical database.

## The three cities
| | Oakland | San Francisco | San Jose |
|---|---|---|---|
| Address authority | **to find**: no published City address-point layer turned up in a first search (check the City's GIS portal and Alameda County's countywide layers) | **Enterprise Addressing System (EAS)**: base addresses (388,550, nightly) + "Addresses with Units" with block/lot | **Site Address Points** (367,746 at 2018 build; NENA model, built from AMANDA, County GIS, Assessor) |
| Parcel / APN | Alameda County -- the same format and canon as Berkeley (`057-2046-001-00`) | Block/lot (SF is its own county) -- a new `APN_FORMATS` row | Santa Clara County -- a new `APN_FORMATS` row |
| Permit system | Accela (same harvester family as Berkeley) | DBI permits on DataSF (weekly); Planning separately | AMANDA (new adapter) |
| What carries over | almost everything: county, APN canon, assessor, the address layer's quirks may differ | the resolver design; EAS IDs make L3 easier than Berkeley | the resolver design; NENA fields map cleanly to L0 |

## Order of work
1. **Finish Berkeley as the reference implementation** (now): commit the 2026-10-13 canon, apply the model-read
   resolutions as evidence, re-point the last two private matchers and the Explorer search.
2. **Refactor into L0/L1/L2** with Berkeley as the first registry row -- and prove it by rebuilding Berkeley from the
   registry with identical results (if Berkeley cannot be rebuilt from config, no other city can be built from it).
3. **Oakland**: find its address authority first; then the registry row, its test cases, the match-rate report on its
   Accela records. Expect weeks, not days: the judgment work (what a building, a completion, a unit is) repeats.
4. **San Francisco**, then **San Jose**, each starting from the authority and its measured match rate.

See also the multi-city architecture draft from the cloud session (branch `scratch/arch-doc`, `45cf6bb`, not in this
clone), which proposes "every published number is a named fact"; the two fit together.

Sources: [SF EAS addresses (data.gov)](https://catalog.data.gov/dataset/san-francisco-addresses-enterprise-addressing-system),
[SF EAS addresses with units](https://catalog.data.gov/dataset/san-francisco-addresses-with-units-enterprise-addressing-system),
[San Jose Site Address Points metadata](https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/36/metadata).
