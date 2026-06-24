# ADR-003 — Parcel-identity model (APN ≠ identity; lineage from maps, not strings)

**Status:** PROPOSED (design + migration assessment only — NOT built). 2026-06-16.
**Supersedes:** the "enforce a single 12-digit canonical APN by overwriting stored APNs" plan
(2026-06-16, pre-build) — that plan is WITHDRAWN (see §7).

## 1. Context / problem

We have been treating the **APN string as the parcel's identity** and inferring **lineage from
APN-string patterns** (the `parcel_crosswalk` re-points, the canon comparisons). This is wrong in
a load-bearing way:

- **BOE / county practice (confirmed):** when a parcel splits, the children get **arbitrary new
  numbers** — parcel `2` may become parcels `9` and `10`, NOT `2A/2B`. The renumber does **not**
  encode the parent. **Lineage lives in the recorded MAP / deed, not in the number.**
- Therefore APN-string crosswalk is a **heuristic**, not authoritative — which is exactly why the
  **proj136-class errors recur**: we keep inferring identity from strings that don't carry it
  (nearest-address, book/page continuity, strip-non-digits). Each is a guess dressed as a fact.
- The APN is also **time-bounded** (a parcel's APN changes on split/merge/re-map) and **external**
  (assigned by the county, not us). It is an *identifier valid for a period*, not the identity.

## 2. Decision

Adopt a **parcel-identity model**: a stable internal parcel identity, APNs as time-bounded
external identifiers (raw preserved + normalized for matching), and **lineage as explicit recorded
events** (parent/child from maps/deeds), with our string-matches demoted to **candidate** lineages
to be confirmed. Parcels are first-class and **separate from projects**.

## 3. The model (target / full)

1. **Stable internal `parcel_id`** — never changes; the parcel's IDENTITY, distinct from any APN.
   *(EXISTS today: `parcels.id`.)*
2. **APNs as time-bounded external identifiers** — `parcel_identifiers(parcel_id, apn_raw,
   apn_normalized, valid_from, valid_to, is_current, county, source)`. **Store BOTH**: `apn_raw`
   (hyphens/leading zeros preserved, NEVER mutated) AND `apn_normalized` (12-digit, for matching).
   One parcel → many identifier rows over time. **"Normalize but do not replace."**
3. **Lineage as explicit `parcel_events`** — `event_type ∈ {sb9_split, merger, lot_line_adjustment,
   condo_map, renumber}`, `event_date`, `recorded_map_ref`, `source`, with `parcel_event_links`
   (parent `parcel_id` → child `parcel_id`). **Recorded from maps/deeds, NOT inferred from APN
   strings.** Our existing string-matches become **candidate** events (`status='candidate'`) to
   confirm against the recorded map, never authoritative.
4. **Geometry TIME-VERSIONED** — `parcel_geometries(parcel_id, geojson, valid_from, valid_to,
   source)`; boundaries change on split.
5. **Parcel SEPARATE from project** — a project spans multiple parcels; a parcel can split
   mid-project. *(Structure EXISTS: `project_parcels` is already project↔parcel m:n with
   `is_primary`.)* Solves proj178 (Acheson umbrella → 4 children) + proj179 (Logan Park N/S split →
   2 children) **natively** — they become multiple `project_parcels` rows + lineage events.
6. **`county`/`jurisdiction` field** — multi-county native (today `parcels.city_id` is a proxy).

## 4. Two APR-pipeline facts (this is not over-engineering)

- **HCD APR requires BOTH Prior APN + Current APN.** The lineage model (`parcel_identifiers`
  valid_from/to + `parcel_events`) **directly produces the APR's prior/current APN fields** — it
  serves the deliverable, it is not gold-plating.
- **SB 9 unit-count rule (classifier):** an **SB 9 lot split is NOT a unit-producing event.** A
  lot-split permit *alone* contributes **0 units** unless an accompanying building-permit / unit
  event exists. **Bake into the classifier** (`housing_rules`): lot-split-only ⇒ 0 units, don't
  count. As SB 9 splits accelerate this prevents systematic unit inflation.

## 5. Migration assessment (current → target)

**Already in place (no migration):**
- `parcels.id` = the stable identity (888 parcels).
- `project_parcels` = project↔parcel m:n with `is_primary` (891 rows; 0 multi-parcel *used* today,
  but the structure supports it — proj178/179 just add rows).
- **Only ONE FK references `parcels`** (`project_parcels.parcel_id`) → the blast radius is tiny.
- `project_geometries` already time-versioned (is_current/superseded_by) — a pattern to mirror.

**New work (the actual cost):**
| piece | rows to migrate | effort |
|---|---|---|
| `parcel_identifiers` (raw+normalized+valid_from/to+county) | 888 current + ~25 prior (from crosswalk) | low — one backfill |
| `parcel_events` + `parcel_event_links` | bootstrap ~25 renumbers + held splits as candidates | low |
| `parcel_geometries` (time-versioned) | 888 (copy current the_geom from berkeley.db) | medium — DEFERABLE |
| consumer rewiring (read `apn_normalized`, not `parcels.apn`) | 4 scripts: materialize_assessed_value, export_explorer_data_v2, build_parcel_crosswalk, shake_detectors | medium |
| SB 9 classifier rule | `housing_rules` | low |

**Bootstrap (answers "can the existing crosswalk seed this?"):** YES. The 25 Phase-2 re-points +
the `parcel_crosswalk` table become **candidate** `parcel_events` (`renumber`, `status='candidate'`,
the 4-source evidence carried over). The 25 were classified `renumber` (1→1, identity continuous) so
they're low-risk candidates; the held splits (proj179, Acheson) become `sb9_split`/`condo_map`
candidates awaiting the recorded map. **Nothing is authoritative until confirmed against the map** —
which is the whole point.

## 6. Minimum-viable version (recommended start)

Do NOT build the full event model first. **MVP:**
1. **Keep `parcels.id`** (identity — exists).
2. **Add `parcels.apn_raw` + `parcels.apn_normalized`** (current era only; `apn_raw` = the preserved
   original, never mutated; `apn_normalized` = `to_canonical_apn(apn_raw)`). Backfill 888.
3. **Add one `parcel_lineage` table** (`parent_parcel_id, child_parcel_id, event_type, event_date,
   confidence, status, source`) — bootstrap the 25 + held splits as `status='candidate'`.
4. **SB 9 0-units classifier rule** in `housing_rules`.
5. **Rewire the 4 consumers** to read `apn_normalized`.

**Grow later (when splits actually need it):** promote `parcel_identifiers` to a full time-history
(multiple APN eras with valid_from/to), `parcel_events`+`event_links` richness, time-versioned
`parcel_geometries`, multi-county. The MVP already fixes the storage mess, reframes the crosswalk as
candidate lineage, and serves the APR prior/current — without the full event machinery.

## 7. Revised normalize/constraint (the WITHDRAWN plan, corrected)

The earlier plan was: overwrite every stored APN to a single 12-digit form + a rigid
`CHECK(apn GLOB 12-digits)`. **WITHDRAWN** because:
- It would **destroy `apn_raw`** (the preserved external identifier) — violates "never lose the raw."
- A rigid 12-digit CHECK would **reject the arbitrary new split numbers** BOE describes and any
  future county format — the constraint would fight reality.

**Corrected approach:**
- Store **`apn_raw` untouched** (hyphens/zeros preserved) + **`apn_normalized`** derived via
  `to_canonical_apn`.
- **Constrain ONLY `apn_normalized`** (digits/structure — it's the internal matching key); leave
  `apn_raw` free-form.
- The 25 Phase-2 re-points stay valid (renumbers, identity continuous); they are **reframed** as
  confirmed `renumber` lineage with the prior APN preserved in `parcel_crosswalk`/`apn_raw`.

## 8. Consequences

- **+** Identity is stable; lineage is evidenced, not guessed → the proj136-class error becomes
  structurally hard (we stop inferring identity from strings).
- **+** Serves the APR prior/current APN deliverable directly; SB 9 inflation prevented.
- **+** proj178/179 multi-parcel resolved natively.
- **−** A migration + consumer rewiring (contained: 1 FK, 4 scripts).
- **−** Lineage confirmation needs a source we don't yet harvest (recorded maps / county
  parcel-change records) — until then, lineage stays `candidate`. The model makes that honesty
  explicit rather than hiding it behind a string match.

## 9. Open decisions (for John, before any build)
- MVP vs full now? (recommend MVP.)
- proj178 multi-APN cell: under MVP, `apn_raw` keeps the original comma-list (preserved), and the
  Acheson split becomes candidate lineage + multiple `project_parcels`. (No lossy first-APN
  truncation needed once we stop forcing one canonical APN per row.)
- Where does confirmed-lineage evidence come from (which county map/record source to harvest)?

## 10. Reconciliation — book-letter (48A/48H) compliance fix (2026-06-24)
This ADR declared the alphanumeric book-letter class (48A/48H) in scope, but the
implementation was **doc-vs-code non-compliant**: `to_canonical_apn`'s single-token branch
stripped non-digits then required `isdigit()`, so the *concatenated* raw form the permit feed
actually uses (`048H769000300`) returned `None`. Found in the Phase-1a signal forensic.
- **Scope:** 8 distinct book-letter APNs / 28 permit rows. **All 28 are alterations**
  (net_units=0), correctly absent from the v3 spine — so this was a **LATENT** defect with
  **0 current spine impact**, NOT a migration/fidelity data-loss. It would bite a *future*
  New-construction book-letter hill parcel, and any consumer canonicalizing assessor APNs.
- **Fix (code-only):** added a single-token alphanumeric branch (mirrors the numeric concat;
  book → 3-char registered form, e.g. `048H…`→`48H-7690-003-00`), validated against the
  registered pattern. Delta verified: 8 newly-accepted, 0 others changed, 6 malformed still
  rejected (now via `canon_with_reason`, logged not silent), idempotent (`canon(canon(x))==canon(x)`).
- **No v3 write:** verified 0 of the 8 addresses in `s1_projects`/`s0_key_index`; no backfill applies.
- Status: **doc-vs-code gap CLOSED.** Benefits all `to_canonical_apn` consumers.
