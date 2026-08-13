# Elmwood Housing Argument

> **Thesis.** Raising the commercial-zoning height limits in the ~3-block Elmwood commercial district, to
> "add housing," is the wrong lever. The Elmwood is *already* one of Berkeley's denser neighborhoods —
> built up over a century — and it will keep densifying through its **residential** fabric: multi-unit
> apartments, single-family→rental conversions, ADUs, and the new **Middle Housing** ordinance. The housing
> is in the 376-acre neighborhood, not the 5.3-acre commercial strip.

Hub note — ties together the data, the records requests, and the open work. Sources linked inline.

---

## The claim, in one line
**Elmwood is ~1.85× as dense as non-student Berkeley today; the residential path holds ~5,300 units of
Middle-Housing capacity; the commercial strip the City wants to rezone is 5.3 acres. Strengthen the
residential densification — don't rezone the storefronts.**

## The evidence (numbers)

**1. Already dense — at the district level, not just the corridor.** *(baseline-gated in [[JN-M_corridor_density]])*
- **Elmwood District: 12.8 du/acre** (official city neighborhood boundary, 376 ac, 93 blocks) vs
  **non-student Berkeley 6.9** → **1.85×**.
- **69% of Elmwood blocks** are denser than the non-student median. *(Honest bound: a supermajority, **not**
  "every block" — the SF interior and hill-edge pull some blocks to average.)*
- The **College corridor** (Dwight→Alcatraz, both sides) runs **~15 du/ac ≈ 2× non-student Berkeley**.

**2. The commercial lever is tiny.** The Elmwood commercial **BID = 5.3 acres**. Against a **376-acre**
residential neighborhood already at 12.8 du/ac with large Middle-Housing headroom, the commercial-height
change is a rounding error — on the order of **~20:1** residential-vs-commercial capacity.

**3. Built over a century — then frozen to new *buildings*, not to new *units*.** *(temporal analysis is
ad-hoc in `scratch/2026-08-12/`, TaxParcel-based — NOT yet folded into JN-M)*
- Elmwood **median year built 1913; 79% of units in pre-1940 buildings**; only **~3 new *structures* since 1995**.
- But that "frozen" reading is a **definitional trap**: an ADU adds a *unit* without changing the building's
  *year built*. The residential densification continued — as apartments, conversions, and ADUs — largely
  **invisible to the assessor**. See the guardrail in [[2026-08-12_corridor_density_investigation]].

**4. Middle Housing (Ord. 7,978-N.S., eff. Nov 1 2025) is the real lever.** Up to **8 units by-right on a
5,000 sf residential lot (~70 du/ac)**, everywhere residential **except high fire-hazard hills**. Verified:
Elmwood is **0/44 corridor blocks in the fire-hazard zone — fully MH-eligible on both sides.** Existing
Elmwood density (~15 du/ac in the corridor) is only **~22% of the MH by-right ceiling** → enormous residential
headroom, right where demand is highest. Zoning caps that used to bind (old R-1/R-2/R-2A) are **defunct**.

**5. The mechanisms are exactly the residential ones — and the data undercounts them.** Apartments (historical,
59% of Elmwood units are in old apartment parcels), SF→rental conversions, and ADUs. **The ADU undercount is
proven on John's own parcels** (2811 / 2822 Benvenue: two ADUs, a rental license, an RHSP inspection + paid
fee) — **six datasets miss all of it** (assessor YearBuilt, assessor Units, business licenses, our ADU cohort,
v4 events, Rent Board). The records exist only in **Accela**. This is why the harvest matters.

## Honest bounds (so it can't be picked apart)
- **"Every block denser than everywhere" is NOT supported** — it's ~69%, a supermajority.
- **Absolute unit totals are soft** — the assessor `Units` field sums higher than Census (85k vs 52k); trust
  **year-built** and **relative** comparisons, use Census for existing density. (Reconciliation queued.)
- **The ~5,300-unit MH headroom is a theoretical legal ceiling**, not a forecast — real buildout is a fraction.
- **ADU/conversion counts are floors** until the Accela harvest lands.

## The data behind it
- **[[JN-M_corridor_density]]** — the committed, baseline-gated notebook (block density, corridors, Middle
  Housing reframe, fire-exemption overlay, Elmwood-District boundary). Generator: `scripts/v4/build_jn_m.py`;
  core: `scripts/block_density_index.py`.
- **[[2026-08-12_corridor_density_investigation]]** — the full write-up incl. the ADU-undercount discovery.
- **[[2026-08-12_czu_zoning_extract]]** — the CZU zoning tables (Raimi + Assoc, 3/5/25).
- Boundaries: `data/reference/berkeley_neighborhoods.geojson`, `berkeley_bid_elmwood.geojson`,
  `berkeley_fire_hill_zones.geojson`.

## Open work (turns the argument from strong to airtight)
- **[[2026-08-12_cpra_corridors_parcel_gis]]** — CPRA **#26-2367, submitted 2026-08-13** for Raimi's parcel database +
  the soft-site prioritization decision records + feasibility. Parcel-level Elmwood truth.
- **[[2026-08-12_accela_benvenue_adu_harvest_scope]]** — the Accela ADU/rental/inspection harvest (adapter
  `experiments/accela_scrape/harvest_address.py` written; Benvenue shakeout via Claude-in-Chrome underway).
  This is what converts "Elmwood densifies residentially" from assertion to **counted permits**.
- **Exclusionary history** — `Berkeley_Graded_Neighborhoods` (1930s HOLC redlining grades) is available to
  overlay: Elmwood was frozen to new buildings *by design* (Berkeley's 1916 single-family zoning, with the
  Elmwood as a motivating case; racial deed covenants). The residential densification happened *anyway*.

## Current state
See **[[PROGRESS]]** (top) for the live snapshot.
