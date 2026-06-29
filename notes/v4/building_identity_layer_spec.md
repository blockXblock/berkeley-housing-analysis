# Building-Identity Layer — Design Spec (v1, 2026-06-29)

**Status:** DESIGN, prototype-validated (9/9 known cases, over-merge guard held), NOT yet built as a
committed layer. This is the buildable spec for that build.

**Supersedes:** the deterministic "a building's identity IS its New master permit" decision
(`scratch/2026-06-25/building_identity_decision_restated.md`). That decision is **demoted, not
discarded**: the master-permit-label remains the strongest grouping *signal* and the default
*representative-permit pointer*, but it is **a revisable medium-confidence inference, NOT the
building's identity.** See §7.

**Provenance:** blind-CC first-principles architecture (2026-06-28, derived with no knowledge of prior
work) + John's epistemics correction + the prototype validation run (2026-06-28/29). The convergence of
a blind design with the hand-resolved groundtruth is the evidence this is structural, not invented.

---

## 1. The core epistemic stance (why this layer exists)

A **building is a real physical thing** that exists in the world. The permit data has **no building
identifier** — it has permits. So a building can only be **inferred** from permits, and an inference
must be stored as a **claim-with-confidence**, never as a hard fact that silently erases or doubles a
real building.

The deterministic framing ("the master permit IS the building") quietly converted an *inference* (which
permit is the master) into a *definition*, hiding that we *chose* the discriminator and could be wrong.
This layer makes the inference explicit: **buildings are latent entities; permits are observations of
them; building-identity is the probabilistic problem of linking observations to the latent building
with the highest defensible confidence.**

## 2. Schema

**`buildings`** — one row per inferred building; the row is a *materialized claim*, rebuildable from
permits, droppable and re-derivable when inference improves.
- `building_id` — synthetic, stable surrogate key (e.g. `BLD0042`). **NEVER a PermitNumber** (the
  cardinal error: keying by permit means re-grouping destroys identity). Changing which permits link to
  a building, or which is representative, leaves `building_id` stable.
- `representative_permit_id` — a **revisable pointer** (the unit-bearing completion permit by default),
  NOT the identity. (§4)
- `inferred_unit_count` — derived (§5), carries its own confidence.
- `status` — `active` | `contested`.
- per-dimension confidence (§6): `grouping_confidence`, `representative_confidence`.

**`permit_building`** — many:many link table; **the inference lives here.**
- `(permit_id, building_id, link_role, confidence, evidence, method, rule_version)`
- `link_role` ∈ {`completion`, `phase`, `sitework`, `ancillary`, `revision`}
- `method` ∈ {`explicit_xref`, `building_label`, `phase_lang`, `apn_cluster`, `cooccurrence`}
- `evidence` — the actual text/signal that drove the link ("Phase II of B2019-05575")
- many:many is the honest cardinality: many-permits→one-building (common), one-permit→>1-building
  ("Buildings A & B"), building→many-permits. Subsumes 1:1 and 1:many.

**`building_grouping_log`** — append-only (ADR-002 EVIDENCE-layer discipline applied to identity).
Which permits linked, when, by what rule, at what confidence. A re-group is a **new claim appended**,
never an overwrite — fully auditable and reversible.

## 3. The inference — two-stage (cluster, then split/confirm)

The key asymmetry (prototype-confirmed): **APN/address are good for CLUSTERING candidates but bad for
final grouping (they over-merge); cross-refs/labels are good for CONFIRMING and SPLITTING.**

- **Stage 1 — cluster:** group permits by APN + address into *candidate* clusters (a co-location prior,
  low confidence alone).
- **Stage 2 — split/confirm within the cluster:** apply the stronger signals to either confirm "one
  building" or split into distinct buildings.

**Signal trust ranking (prototype-validated):**
| signal | trust | role |
|---|---|---|
| explicit permit# cross-ref ("Phase II of B2019-05575", "see B2018-02708") | HIGHEST | anchor (confirm same building) — capture reference *type* (phase vs demo-ref vs adjacent) |
| building label ("North/South Building", "Building C") | HIGH for splitting | **split** co-located distinct buildings (the protection direction) |
| phase language, no permit# ("Phase II") | MEDIUM | flags phased-ness; needs APN/address to link |
| APN | MEDIUM-LOW | cluster prior only — over-merges (distinct buildings/lot) AND under-merges (re-plat) → **never identity** |
| address | MEDIUM-LOW | cluster prior — corner lots, ranges, big-building-many-addresses |
| co-occurrence (same APN + overlapping dates + repeated unit-count + compatible OccType) | WEAK corroborator | repeated count across phases (two permits both "163 units") ⇒ phases of one building, not two summing |

## 4. The representative permit — a revisable pointer

Default: the **unit-bearing completion permit** (Work Type=New + units>0 + reached
finaled/superstructure) — the permit that best *is* the building as housing.
- **Medium confidence.** It can be wrong: (i) the real completion permit may be ambiguous/countless in
  text while a sibling carries the count; (ii) phased buildings split the completion; (iii) the
  heuristic could land on foundation/demo.
- **Revisable without data loss:** it's a POINTER (`representative_permit_id`) over the stable
  `building_id`. Change the pointer → identity, permits, links all survive.
- **Tied phases** (Shattuck: both phases carry full 163, neither is foundation): flag
  `representative_status='ambiguous_tie'`, `representative_confidence=low`, record BOTH candidates in
  the log. Pick one for stability (deterministic tiebreak) but mark it a low-confidence revisable choice.

## 5. Unit count — inherits grouping uncertainty

- Within a confirmed building: the count is the **unit-bearing phase's count** (max-per-building when
  phases repeat the whole-building count, NOT a sum — the Shattuck rule). Sitework/foundation phases
  carry 0.
- The building's unit total **inherits the grouping tier**: a wrong grouping double-counts (under-merge)
  or vanishes (over-merge) units, so the unit total carries the grouping confidence.
- NULL when no phase carries a count (the ambiguous-completion multifamily — held, needs Accela, NOT
  city-adopted). Never invent a count; NULL ≠ 0.

## 6. Per-dimension confidence (the prototype's key refinement)

Confidence is **NOT one tier** — the prototype proved a building can be confidently *grouped* while its
*representative* is a guess. Three separate scores:
- `grouping_confidence` — sure these permits are one building (HIGH when xref/label/phase-explicit).
- `representative_confidence` — sure the chosen representative is the canonical permit (MEDIUM when
  role-inferred; LOW when phases tie).
- `role_confidence` — sure each permit's `link_role` is correct.

A wrong representative must NOT masquerade as high-confidence. Counts depend on grouping (high);
which-permit-represents depends on representative (medium). Keep them separate so consumers see which
certainty they're relying on.

## 7. Failure modes + the bias rule (the moral core)

Two silent failures, **asymmetric**:
- **Over-merge** (collapse co-located distinct buildings — Buildings B&C, 3 SFRs on a lot) → undercount
  buildings AND **erase their units. The worst error: invisible.**
- **Under-merge** (miss phases of one building) → overcount buildings AND double-count units. Bad, but
  **visible and fixable.**

**BIAS RULE (load-bearing):** when grouping evidence is ambiguous, **prefer under-merging** (leave a
possible double) **over over-merging** (risk erasing a real building). A double-count is visible and
correctable; an erased building is not. This is the rule we practiced by hand this session (protecting
Buildings B&C, the 3 SFRs) — now schema law.

## 8. Relationship to existing v4

- Sits ON the immutable permit spine + `event_classifications` (this is a NEW derived layer, doesn't
  touch them).
- The 5 gated writes this session (Shattuck collapse, the −199 multifamily collapse, etc.) become
  **seed entries in `building_grouping_log`** — the hand-resolved groupings are the layer's first,
  highest-confidence claims.
- `building_identity_review.py` (this session) is the prototype seed; the validated prototype
  (`scratch/2026-06-29/proto_*.csv`) is the reference implementation.
- The classifier (`housing_rules.permit_role`) still sets per-permit role; this layer groups permits
  into buildings ABOVE the permit grain. Complementary, not overlapping.

## 9. Build plan (next session)
1. Apply the 3 prototype fixes (clause-aware role, per-dimension confidence, tied-representative) — DONE
   in `scratch/2026-06-29/` before this spec was finalized.
2. Build the 3 tables + the two-stage inference as a committed module (`scripts/building_identity/` or
   `housing_rules/building_identity.py`).
3. Seed from the hand-resolved session-28 groupings (highest-confidence claims) + run inference across
   all multi-permit buildings.
4. Produce the tiered building + unit count (point estimate + confidence band), feeding the APR
   reconciliation's multifamily side.
5. The UNDER-count buildings (the +147 held this session) get `inferred_unit_count=NULL` until Accela
   harvest supplies independent counts — the layer records them as known-but-unsized, NOT city-adopted.

---
*Design validated on 9/9 known cases; supersedes the deterministic master-permit-identity decision by
demoting it to a revisable pointer; the moral core is the bias-to-under-merge erasure guard, which held
on the dangerous co-located cases in the prototype.*
