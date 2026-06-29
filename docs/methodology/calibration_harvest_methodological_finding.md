# Methodological finding: the calibration-harvest lesson + building-identity confusion taxonomy

**Date:** 2026-06-29. **Status:** durable methodological finding, with an explicit Berkeley→Oakland
transfer test. This is bin-1 *candidate* knowledge (possibly universal) — the transfer test is how we'd
confirm it.

## The lesson: curated validation hides the dominant failure mode

The building-identity layer was validated on **9 hand-curated cases** (Shattuck, 3 phase-collapses, 2
co-located-distinct protect cases). It passed 9/9 — grouping correct, counts correct, over-merge guard
held. We concluded "the design works."

Then we ran a **calibration harvest** — the same layer across **all 936 multi-permit clusters / 974
inferred buildings**, the unfamiliar population. The result reframed everything:

- **592/974 (61%) fired ambiguous-tie; 364/974 (37%) were APN-only groupings.** The dominant reality at
  scale is **same-APN multi-permit ≠ one building** — most clusters are *unrelated* permits (years of
  renovations, separate ADUs, ancillary work) that the APN-cluster stage fused into a *phantom building*.
- **The 9 cases were the easy tail.** They were all genuinely-phased single buildings — the exact case
  the layer handles well — and contained *none* of the dominant failure mode. A validation set that
  doesn't *contain* the failure mode cannot reveal it.
- We had calibrated the **wrong dimension**: the prototype told us "representative-pick is the
  medium-confidence weak point," and we believed it — but the real weak point is one level up: **"is
  this one building at all?"** The representative-tie rule fires on clusters where there's no single
  building to represent.

**The durable lesson (candidate-universal):** *A design validated only on curated, understood cases will
pass while hiding its dominant failure mode, because the failure mode lives in the cases you didn't
curate. Confidence from an easy-tail validation set is false confidence. The only way to find the real
failure surface is to run at scale on the unfamiliar population (a calibration harvest) and let the
low-confidence cases float up.* The harvest manufactures the calibration that curated tests can't.

**Why this matters beyond building-identity:** every layer we validate on anchors (the classifier, the
scorer, the completion verdict) carries the same risk — anchors are curated, so they're the easy tail.
Anchor-passing ≠ correct-at-scale. The harvest pattern (run on the full unfamiliar population, sort by
confidence, adjudicate the shaky top) should be applied to any layer before trusting it in production.

## What saved us (the design was sound, just mis-scoped)

The failure was **benign**, and two design choices made it so:
- **Over-grouping concentrated in non-housing.** 0 of the 364 low-confidence groupings carried a
  new_unit/ambiguous role — every housing-formation grouping was high/med confidence. The layer fails on
  *routine non-housing noise*, not on the cases that matter.
- **The over-merge guard held at scale: 0 erasures.** Across all co-located-distinct candidates, the
  layer never merged 2 distinct buildings into one. The bias-to-under-merge erasure guard — the moral
  core — is rock-solid at scale, not just on the 2 protect cases.

So the layer wasn't broken; it was **incompletely scoped** — trying to make buildings out of parcels
that have no building. The fix is an upstream "is-this-a-building?" evidence-positive discriminator +
an ancillary-only filter (not a redesign).

## The building-identity confusion-class taxonomy (the candidate-universal catalog)

The harvest produced a *catalog of confusion classes* — the patterns where permit→building inference is
genuinely hard. **This catalog is the bin-1 candidate knowledge: it may recur in any city's permit data.**

1. **Unrelated-permits-on-one-APN** (dominant, ~364+ cases) — co-located permits, no shared building
   signal. APN over-groups them.
2. **Ancillary-only parcels** (99) — solar/reroof/water-heater/meter clusters, no building permit. Not
   a building formation at all.
3. **Cross-APN-same-building** (39) — re-platted/multi-parcel buildings; xref says same, co-location
   says distinct. The hardest signal-conflict.
4. **Co-located-distinct buildings** (45 / "Building A/B/C", multiple SFRs on a lot) — the over-merge
   guard's target; must NOT merge.
5. **Unlabeled-residual-after-split** (8) — leftover permits after a labeled site splits; which building
   do they belong to?
6. **Large-cluster** (≥4 permits, 81) — genuine multi-building/multi-phase vs messy permit history;
   indistinguishable without review.
7. **Ambiguous-tie phased** (the genuine Shattuck class, buried in the 592) — real phased buildings where
   ≥2 phases carry the whole-building count and which-is-representative is genuinely undetermined.

## The Berkeley→Oakland transfer test (how to confirm bin-1)

The open methodological question (from the "are we learning universal lessons" thread): **is this
taxonomy universal, or Berkeley-specific?** The architecture (latent-building, confidence-linked,
evidence-positive grouping, bias-to-under-merge) is *derivable from the data* (blind-CC re-derived it) —
strong universal candidate. But the *specific confusion classes and their relative frequencies* are
unproven beyond Berkeley.

**The test, when a second city (Oakland/SF) is attempted:** run the same calibration harvest on the new
city's multi-permit clusters and check —
- Do the **same confusion classes** appear (unrelated-on-APN, ancillary-only, cross-APN, co-located-
  distinct, large-cluster)? If yes → the taxonomy is universal (bin-1 confirmed).
- Are the **relative frequencies** similar (is unrelated-on-APN dominant there too)? Or does the city's
  permit structure shift the distribution (e.g. SF's high-rise density → more genuine phased buildings,
  fewer ADU-noise clusters)?
- Does the **evidence-positive discriminator** transfer, or does it need re-calibrated signals (different
  cities may phrase phase/building-labels differently)?
- Does the **0-erasure guard** still hold on a different city's co-located-distinct patterns?

Whatever recurs is universal method; whatever shifts is local calibration. *That* split — confirmed by a
second city — is what turns "Berkeley case study" into "replicable method," which is the project's
stated goal.

---
*The harvest did its job: it exposed that our 9-case validation was unrepresentative, sized the real
failure mode (over-grouping, benign, non-housing-concentrated), confirmed the erasure guard at scale (0),
and produced a confusion-class taxonomy that is the candidate-universal knowledge a second city will
test.*
