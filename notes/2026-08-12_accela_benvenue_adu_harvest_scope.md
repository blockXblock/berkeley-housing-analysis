# Accela ADU harvest — Benvenue block pilot (scope)

**Goal:** measure the *real* ADU/rental densification of the Elmwood — the kind YearBuilt, assessor Units,
our 2018+ permit cohort, and the business-license registry all undercount — using the one source that
records it: the **Accela ACA permit + license stream**. The Benvenue block is the pilot because we have
**John's ground truth** to validate against (he built ADUs at 2811 & 2822 Benvenue and licenses a rental at
2811 — all four existing datasets miss them; see the 4-source table in chat / PROGRESS).

## Why Accela — SIX datasets miss John's ground truth (verified 2026-08-12)
2811 / 2822 Benvenue: two ADUs built, a rental license held, an RHSP inspection + paid fee — and **none of
six datasets records them:**
1. Assessor **YearBuilt** — structurally blind (an ADU doesn't change the house's build year).
2. Assessor **Units** — 2822 still reads **1**.
3. **Business licenses** (13,004, Nov-2025) — absent by APN + every address/"1/2" variant.
4. Our **ADU permit cohort** (2018+) — absent.
5. **v4 permit events** — absent (only 3006 / 3100-block Benvenue).
6. **Rent Board `rent_control`** — absent (and the table is only 1,098 rows — itself partial).

**Accela ACA holds all of it** — the ADU *building permits*, the rental *business license*, AND the RHSP
*inspection + fee* record — back further than 2018, not WAF-blocked like Socrata. It is the only complete source.

## Target set (the block)
- **APNs:** `53-1694-*` (even side, ~2810–2842 Benvenue) + `53-1695-*` (odd side, ~2811–2843 Benvenue) —
  ~40–50 parcels. Build the exact address/APN list from `databases/berkeley.db` parcels.
- **Validation anchors (must resolve or the harvest is wrong):**
  - `2811 Benvenue` (53-1695-26) → expect an **ADU building permit** + a **rental business license**.
  - `2822 Benvenue` (53-1694-9) → expect an **ADU building permit** (assessor still says 1 unit).

## Method (our HARVESTER — `aca-prod.accela.com/BERKELEY/`)
- Tooling: the Playwright HARVESTER (`experiments/accela_scrape/` — `url_discovery_scraper.py` /
  `date_range_discovery.py`; `scripts/processing_status_scraper.py`, `record_status_scraper.py`,
  `build_scrape_queue.py`). ACA search = `CapHome.aspx` (GeneralSearch, `__doPostBack` pagination) →
  `CapDetail.aspx` per record (the parcel/zoning/units section is in the DOM we already read).
- **Per address/APN, pull THREE record classes:**
  1. **Building permits** — record #, work type, description, **status + issued/finaled dates**, **units
     added** (ADU / new-dwelling). This is the "permitted unit added" event = the corrected temporal metric
     that replaces YearBuilt.
  2. **Business / rental licenses** — `Rental of Real Property` records + unit counts (the registry missed 2811).
  3. **RHSP inspections + fees** — the Rental Housing Safety Program inspection record and the paid fee (our
     `inspection_scraper.py` / `scrape_inspections.py` already pull Accela inspection grids; point them at the
     rental-inspection record type). This is the class 2811's ground truth lives in and we have NONE of locally.
- **Output:** per-parcel `{permitted_units_added, first_adu_permit_date, rental_license[y/n+units],
  rhsp_inspection[date+fee]}` → reconcile against the six existing sources; the delta = the systematic
  undercount, quantified against a known-true anchor (2811 must light up on all three classes).

## Operational
- **John logs into ACA** (public permit search may not need it, but log in so authenticated record fields
  resolve — John said he'd handle Accela login).
- **Memory discipline (load-bearing):** Playwright spiked swap and crashed the Mac earlier this session.
  Benvenue is small (~50 parcels) so it's a safe pilot, but **check `vm.swapusage` before launch, batch it,
  and do not run other heavy jobs concurrently.**
- **No-capID/0-result is NOT absence until retried** (transient ACA discovery flakiness — retry before
  concluding a parcel has no permit).

## Pilot RESULT (2026-08-13, via Claude-in-Chrome whole-street capture)
CIC captured all **577 Benvenue building-permit records (1992–2026)** → `data/raw/benvenue_permits_2026-08-13.csv`.
Run through `housing_rules.permit_role.classify` (NOT a keyword flag):
- **6 genuine `new_unit` (ADU) permits** — concentrated at the north/3000s end (2819 basement ADU, 3005, 3019,
  3020) — vs CIC's keyword flag catching **38** (≈6× over-count). Classifier >> keyword, confirmed.
- **4 merge/combine records that REDUCE units** (2626 "merge 2→1", 2705 "remove two kitchens") — densification
  reversed, which a keyword flag scores positive. The classifier catches the sign.
- 533 ambiguous (conservative) + 35 subsidiary (REV/DEF, netted 0).
- **Net permitted units on Benvenue ≈ +4 over 30 yr — small.** The lesson: Elmwood density is NOT from
  permitted new construction; it's pre-1940 stock + unpermitted conversions (2811½, invisible to permits).
  **=> the bulk harvest must classify, not keyword-flag; and the permitted stream is a FLOOR, not the story.**

## If the pilot validates (2811 + 2822 resolve)
Scale the same two-record-class harvest to **all Elmwood corridor parcels** (Dwight→Alcatraz, the ~1,356
parcels), then citywide — producing the first ADU-aware "units added over 20–30 years" count, and feeding
JN-M a `permitted_units_added` temporal metric (never YearBuilt). That is the number that tells John's story.
