> **⚠ SUPERSEDED 2026-06-29** — by the building-identity layer design
> ([building_identity_layer_spec.md](building_identity_layer_spec.md)). The master-permit-label
> conclusion below is RETAINED as the strongest grouping SIGNAL + the default representative POINTER,
> but it is a **revisable, medium-confidence INFERENCE, NOT identity.** Identity = a synthetic
> building_id; permits link to it as confidence-scored claims (many:many). Demoted per the
> prototype-validated (9/9 known cases) + harvest-calibrated (low-conf 364→2, 0 erasures, 9/9 intact)
> layer design 2026-06-29. **Reasoning preserved below — do not delete.**

---

# Building-identity decision — RESTATED from the canonical record (read-only, 2026-06-25)

Re-anchoring to what John already settled (~June 18 + ADR-003), quoted from the record — NOT a new
design. Where the current spec/code drifted from the decision, the **decision wins; the spec gets
corrected to match it**, not the reverse.

## 1. The settled IDENTITY RULE (verbatim)
**A building's identity is its New master construction permit (+ its CO). Address and APN are
ATTRIBUTES carried on it (M:N), not the key.**

> "**The real fix = permit-based building identity** (a building = its own New master permit + its
> CO), re-keying S1 AND S2–S8…"  — `notes/HANDOFF_2026-06-18.md` L40

> "**APN is NOT the fix.** … One parcel routinely holds many buildings; one building can span many
> parcels (condos). **So neither address nor APN is a valid building key.**"  — HANDOFF L34-38

The M:N (building↔parcel) is structurally backed in ADR-003:
> "*(Structure EXISTS: `project_parcels` is already project↔parcel m:n …)*" — `docs/audit/2026-06-16_ADR-003_parcel_identity_model.md` L45; "`project_parcels` = project↔parcel m:n" L63-64

And the build-rule already names permit-family (not address/APN) as the identity signal:
> "CREATE is the default; **ATTACH only on strong identity (permit-family / address).**" — `notes/build_v2_lessons.md` L45

## 2. What was ALREADY DECIDED — discrimination + routing
**Discrimination (phased-one-building vs distinct-buildings) needs permit/description logic, not a
blind aggregate:**
> "Discrimination is the hard part: must tell 4-distinct-buildings (SUM) from phased-one-building
> (MAX, the reason MAX exists) from New+alterations (MAX). **Needs description/permit-type logic, not
> a blind SUM.**" — HANDOFF L47-48

> "genuinely unresolvable → FLAG, don't guess (2352 Shattuck … held at 135, flagged to S8 … no number
> invented)." — `build_v2_lessons.md` L203-205

**Routing key = permit identity, NOT bare APN** (the direct corollary of "APN is NOT the fix",
HANDOFF L34). A building is routed by its master permit / building-label, because one parcel holds
many buildings and one building spans many parcels.

## 3. Decided vs BUILT — the gap, stated plainly
| | status | source |
|---|---|---|
| permit-based building identity (S1 + S2–S8 re-key) | **DECIDED, NOT BUILT** | HANDOFF L40-42 ("Proposed as a scoped 'S1.5 building-identity from permits' stage … not yet built") |
| `split_multibuilding` in `build_s1.py` | **WRITTEN but UNWIRED — and APN-based = the SUPERSEDED approach** | HANDOFF L44-45: "carries the split rule WRITTEN but UNWIRED … **Do NOT wire it without the S2–S8 re-key**" |
| current S1 keying | **address-tuple `(number,street,stype)`** (collapses multi-building) | HANDOFF L28-30 |
| `structures` layer (physical structure ≠ units) | prior art, **9 rows, NOT built**; missing structure↔unit edge | HANDOFF L50-53 |

**The gap:** the decided identity is **permit-master-label**; the live code keys by **address**
(S1) and the unwired split rule + the S1.5 spec key by **APN**. APN-grouping is the very approach the
decision rejected — so wiring `split_multibuilding` as-is does not implement the decision.

## 4. ADR-003 / parcel_lineage bounds (the APN/parcel side)
- "**APN ≠ identity**"; "The APN is **time-bounded** … an *identifier valid for a period*, not the
  identity." — ADR-003 title + L19-20.
- "**Stable internal `parcel_id`** — never changes; the parcel's IDENTITY, distinct from any APN." — L31.
- "**Lineage lives in the recorded MAP / deed, not in the number**"; our string-matches "become
  **candidate** events (`status='candidate'`) … never authoritative." — L15, L40-41, L79-82.
→ So APN is an attribute on both the parcel and (transitively) the building; lineage (e.g. 2352's
018-05 → 041-00) is **candidate, not fact**, until confirmed against a recorded map.

## 5. Where the current spec/code DRIFTED from the decision (correct the spec to match)
**`notes/s1_5_v1_design.md` routes by APN — contradicting "permit identity, not APN":**
- **Site 2, L77-78:** "route each permit to its sub-building **by the permit's canon-APN**
  (`r.ParcelNumber → canonicalize_apn`)." → This is APN-routing — the rejected key (HANDOFF L34).
- **L91-95:** "**The CO-year bug fixes itself through this routing** … North's group → max = its real
  2022 CO." → **Empirically FALSE.** Stage-1 verification (2026-06-25) showed North (018-05) lands
  **2023-08-08** because `B2019-05575` ("Phase I — **South Building**", 69u, finaled 2023) was filed
  under the **pre-split parent APN 018-05** and APN-routing misroutes it onto North. The South
  building's permits straddle two APNs (Phase I `018-05`, Phase II `041-00`); **APN cannot
  discriminate them — the master-permit/building-label can** ("North Building" `05574` vs "South
  Building" `05575`). So the spec's self-fixing-CO claim depends on a routing the APN key does not
  deliver, on the very case it targets.
- **Site 1:** `split_multibuilding` itself groups **per canon-APN** — the superseded approach; it
  produces the right *units* (135/69 by MAX-per-APN) but the *wrong date* for North.

**Correction the decision implies (for chat-Claude to fold into the spec — restated, not newly
designed):** route by **master-permit / building-label identity** (the decided rule), with APN/address
as carried attributes. The split's discrimination and S2's routing must key on the New master permit
(and its "North/South Building" label / sibling-master structure), not `r.ParcelNumber`. The
"CO-year fixes itself" line must be retracted: it is contingent on correct (permit-identity) routing,
which APN-routing does not provide for phased developments filed under a shared parent APN.

---
*Read-only; quoted the record; no new design, no build, no write, no commit. This re-anchors the work
to the settled permit-identity decision; the spec is what moves to match it.*
