# Architecture Decisions of Record — Berkeley Housing Pipeline

**Status:** Living document. The single home for cross-cutting architecture/data-model decisions.
**Started:** 2026-06-14
**Scope:** Decisions that affect more than one consumer (v2 schema, `v_projects_flat`, the APR
notebooks, the explorer export, the classifier). Per-task/roadmap choices stay in per-session
notes; this file is only for decisions future work must not silently re-litigate.

**Format per entry:** `ID · Title · Status (SETTLED / OPEN / SUPERSEDED) · Date` → Context →
Decision (or Lean, if OPEN) → Consequences → Companion links.

---

## ADR-001 · Completion-date precedence is centralized in `v_projects_flat` · SETTLED · 2026-06-14

**Context.** A project can carry several completion-signalling events — an evidentiary
`permit_finaled`, an evidentiary `co_issued` (incl. a human override), an inferred `co_issued`
with a real date, and a migration stub dated `2024-01-01`. Multiple consumers need "the
project's completion date" (explorer export, `generate_apr_v2.py`, eventually D5). If each
reimplements which event wins, they drift.

**Decision.** The precedence lives in **one place — the `v_projects_flat` view** — so every
consumer reads a single consistent answer. The rule (highest to lowest):
1. evidentiary `permit_finaled` (`is_inferred=0`, real date),
2. evidentiary `co_issued` (`is_inferred=0`, real date) — includes the proj219-style override,
3. inferred `co_issued` with a real (non-stub) date,
4. `2024-01-01` stub `co_issued` — loser; only surfaces if nothing else exists.
The existing "NOT `permit_classified_subsidiary`" filter is preserved in every tier, so a
subsidiary permit's events never surface as a completion.

**Consequences.** Implemented as a view change (snapshot `keep_snapshot_2026-06-14_pre-viewchange.db`),
validated across all 885 projects (3 co_dates changed, 0 regressions, 0 lost completions),
regenerated into the explorer and pushed (`origin/main` commit `6ef5bb3`). The view is the
choke point: changing precedence = changing the view, once, with a whole-view preview.
Trade-off accepted: consumers cannot locally override precedence (by design).

**Companion:** ADR-002 (the *verdict* that feeds tier 1/2 of this precedence).

---

## ADR-002 · Completion verdict: materialize vs compute-on-the-fly · SETTLED · 2026-06-14

**Settled:** MATERIALIZE, with overwrite discipline and a 3-valued verdict. Implemented 2026-06-14 (wire-in STEP 0–3).

**Context.** The completion verdict (completes / does_not / ambiguous) was a pure function (permit_role_classifier reads permit.description → verdict), stored nowhere. The 8-year backfill forced the storage question. Decisive evidence: the live completion classification had DRIFTED because it was re-derived per-script across 9 scripts, with CKAN-anchoring (the city's own APR) leaking in as a classification input — a circular dependency making the independent reconstruction depend on the city's report. Re-derivation-per-consumer is the exact mechanism that produced the drift.

**Decision.** MATERIALIZE the verdict — store it on the permit, written once by the principled classifier, read by all consumers. This makes drift structurally impossible (one definition, one place) and gives the iterate-against-residual loop a queryable verdict (the ambiguous set IS the harvest queue, which requires a stored WHERE verdict='ambiguous'). Verdict stays 3-VALUED, never collapsed to binary — the ~23 ambiguous are the harvest queue; collapsing to primary/subsidiary would either strip real completions (ambiguous→subsidiary) or re-admit contamination (ambiguous→primary).

**Three-layer guard (enforced).** EVIDENCE (events/permits/docs) = append-only/triangulation, never written by the verdict layer. VERDICT (this label) = overwrite, one current answer per permit, idempotent-recompute. DECISIONS (human overrides, contested-holds) = append-only. The wire-in writes ONLY the verdict layer; evidence confirmed byte-untouched across STEP 1 + STEP 3 (events 3873 / permits 956 / versions 883 / affordability 890, unchanged).

**Implementation.** 5 columns on permits: completion_verdict (CHECK completes/does_not/ambiguous), completion_basis (CHECK evidentiary/description_only/human_override/contested), completion_basis_note, completion_verdict_by (mandatory provenance, e.g. 'permit_role_classifier@1154b9e' — this stamp IS the staleness query: verdict_by != current_version finds stale verdicts), completion_verdict_at. Invariants (evidentiary⇒note names a CPRA/inspection source, never CKAN; the "confidence=high but uncited" failure barred) enforced by the write script + fingerprint (SQLite can't add cross-column CHECK via ADD COLUMN). 819 verdicts materialized 2026-06-14T18:47. Settled distribution: completes 683 / does_not 113 / ambiguous 23; basis evidentiary 664 / description_only 154 / human_override 1 / contested 0.

**Staleness cost — handled.** Re-running the (pure, cheap) classifier re-derives the layer; "change patterns → re-run the classification step" is the discipline. The mandatory verdict_by + verdict_at make staleness queryable.

**Companion:** ADR-001 (precedence consumes this verdict in tiers 1–2).
