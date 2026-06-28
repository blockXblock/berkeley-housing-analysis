# FORENSIC AUDIT — `migrate_v1_to_v2.py` and the factual provenance of every value in v2

**Type:** Read-only forensic investigation. **NO writes, NO fixes, NO scraping.** Stage findings only.
**Authority:** the live `databases/berkeley_housing_v2.db`, the actual migration/import source code, and the raw source feeds on disk — **never** docs, summaries, PROGRESS.md, or memory. Quote artifacts; re-verify every number before relying on it.
**Output:** a findings doc at `/tmp/forensic_migration_audit.md`, ranked by severity and by units-at-stake, with a per-fact-type "asserted vs derived vs droppable" verdict and a re-derivability split.

---

## WHY THIS AUDIT EXISTS (the proven template)

A read-only investigation of the **completions** fact-type just found a systemic, multi-stage migration bug, not a localized defect. v2's build **silently dropped ~568 units of real, Finaled, multifamily housing** (10 Tier-1 buildings, e.g. 2001 Fourth St 152u B2016-03894 Finaled 2018-07-31; 1950 Addison 107u; 1900/1922 Walnut 65u) plus a ~100-unit small-project tail. The root cause was **three compounding flaws in the migration's *method***:

1. **Lossy spine** — `migrate_v1_to_v2.py` carries forward only buildings already in v1's hand-built `housing_projects_FINAL.csv`. Anything v1 didn't know, v2 never learns.
2. **Match-or-drop** — `import_cpra_*.py` attaches a CPRA permit only if it APN/fuzzy-matches a *pre-existing* v2 project; net-new buildings are created **only from a hardcoded ~2-project whitelist** (`match_permit_to_project`). Real new construction with no prior project "falls on the floor."
3. **Text-parse over structured columns** — unit counts were parsed from `WorkDescription` prose ("…39 dwelling units…"), so phased "Phase 3 … close-in" permits read as 0 units — **while the structured `UnitsAdded` / `NumberUnits` columns sat in the feed unused the entire time.**

The lesson generalizes: **the migration asserted facts it should have derived, dropped facts whose text-parse failed, and ignored structured source columns in favor of prose.** This audit's job is to determine whether that same method corrupted **every other fact-type** the same way — and to quantify, for each, how much of v2 is migration-inference vs evidence-backed, and how much is **re-derivable from structured sources we already hold**.

**The method that just worked, applied to everything:** key on the *structured source-of-truth*, not on what v2 says; ask *what the build dropped or asserted* vs *what the raw feeds actually contain*; prefer structured columns over parsed text; treat the migration's output as one more source to *verify against*, never as ground truth.

---

## PHASE 0 — MAP THE MIGRATION'S METHOD (source-code read)

Read the actual code, not its docstrings (docstrings have lied before — `permit_role_classifier`'s claims the export uses it; it doesn't). Cover the full build chain:
`migrate_v1_to_v2.py`, `import_cpra_2023_2025.py`, the v1-era CPRA importer, `dedupe_r2_permits` / `extract_master_permit` / `match_permit_to_project`, and any seed/correction scripts that ran during the build.

For **each script**, report:
- **0.1** Its inputs (which files/tables/columns it reads) and outputs (which v2 tables/columns it writes).
- **0.2** Its **selection rule** — what survives, what is dropped, and on what key. Quote the exact predicate (the completion drop was a spine-membership + match-or-whitelist rule — find the analogue for every fact-type).
- **0.3** Its **value source per field** — for every column it writes, does the value get **COPIED** from a source, **DERIVED** from evidence, **PARSED from text**, or **ASSERTED/INFERRED** with no source? Build a field-by-field provenance table.
- **0.4** Every place it **parses prose** (`WorkDescription`, narrative, address strings) where a **structured column existed** in the same feed (the `UnitsAdded`/`NumberUnits` failure — find all of them).
- **0.5** Every **hardcoded list, whitelist, or magic constant** (the ~2-project create-whitelist is one; find the rest — they're silent scope limits).
- **0.6** Whether it sets `is_inferred` / `confidence` honestly, or stamps asserted data as if verified.

---

## PHASE 1 — PER-FACT-TYPE FORENSICS (apply the 3-flaw template to each)

For **every** fact-type below, answer the same five questions, and quote raw-source vs v2 side by side:
- **(a) ASSERTED vs DERIVED:** how did the migration populate it — copy / derive / text-parse / assert?
- **(b) SPINE-DROP:** what real instances were dropped because the spine (FINAL.csv) or match-or-whitelist rule excluded them? Size it against the **full raw feed**, keyed on the structured status column, NOT on the parse that may have caused the drop.
- **(c) STRUCTURED-COLUMN-IGNORED:** was there a structured source column that the migration bypassed in favor of text/inference? (the `UnitsAdded` pattern)
- **(d) BLAST RADIUS:** how many v2 rows/projects/units carry an asserted-or-parsed value with no underlying source? How many units at stake?
- **(e) RE-DERIVABILITY:** of the wrong/missing values, how many can we now re-derive from structured sources we **already hold** (CPRA xlsx columns, `R2_R3_permits_2023_2025.tsv`, the `.txt` Processing Status corpus, inspection JSONs, permit rows) vs genuinely absent? Split "re-derivable from disk" vs "needs acquisition."

### 1.1 COMPLETIONS / CO (template case — confirm & extend)
Already sized at ~568 Tier-1 units + tail. Reconfirm against the full feed and **extend**: beyond Work Type=New, do **REV/phased/master-permit families** hide completions (collapse via `extract_master_permit`)? Are there Finaled R-1/R-3 (not just R-2) completions also dropped? Final number: total real residential completions + units the build dropped, per tier, with the structured unit count for each.

### 1.2 UNIT COUNTS (everywhere, not just completions)
- Where did each project's `total_units` / `unit_program` counts come from — structured `UnitsAdded`/`NumberUnits`, FINAL.csv, or `WorkDescription` parse?
- How many v2 unit counts disagree with the structured CPRA column for the same permit? (the proj15 110-vs-131 leak is one symptom — find the population)
- The cumulative-vs-marginal REV trap: confirm whether the build used a master permit's `UnitsAdded` or summed REV sub-permits (double-count risk). Quantify affected projects.

### 1.3 STAGE (`current_stage_type_id`)
- The audit shows stage is **migration-asserted**: 744 "entitled+" have no `entitlement_approved` event; 731 "completed/UC" have no BP date. Confirm and quantify exactly how stage was set in the migration (copied from a FINAL.csv status string? inferred from presence of a permit?).
- For all 885 projects: how many have a stage that is **contradicted by, or unsupported by**, the events/permits now in v2? Cross-check stage against: entitlement event present? BP issued_date present? evidentiary CO present?
- How many stages are **re-derivable** from the milestone events we can materialize (the 57 BP / 44 Finaled permit-row dates + the 568 recovered completions) vs need more data?

### 1.4 MILESTONE EVENTS (entitlement / BP-issued / CO-finaled)
- 91% of `co_issued` events are `is_inferred=1`. Where did the migration get the inferred ones — from a stage string, with no permit? Quantify inferred-with-no-permit vs permit-linked.
- The 57 BP `issued_date` + 44 `finaled_date` already in `permits` rows but only ~32 surfaced as events — confirm the materialization gap and which projects it covers.
- Cross-check every milestone DATE against the structured CPRA date column for the same permit — agreements vs disagreements.

### 1.5 AFFORDABILITY / INCOME TIERS
- For the migration-era affordability rows (not today's 9 cited): copied from FINAL.csv, asserted, or sourced? The audit flags **105 rows confidence=high but source_document_id NULL** (inferred-as-verified) and **704 rows cited to untyped stub documents**. Characterize the full migrated-affordability population: how many have a real source vs are asserted.
- Are there projects whose affordability the migration set to all-market / blank by *default* when the source actually had tiers (the proj35 all-market-452 pattern, pre-correction)? Size it.

### 1.6 ADDRESSES & KEYS (the corruption that defeats dedup)
- The `(id:NNN)` suffix is baked into **both `canonical_address` AND `normalized_address`** — find the migration step that injected it, for how many projects, and whether it corrupts the dedup key for all of them.
- The 10 shared-APN duplicate pairs (`25/115, 54/62, 86/109, 96/138, 113/118, 162/127, 362/888, 544/852, 624/869, 645/880`): are these migration-created duplicates (same building entered twice under different keys)? For each pair, which is the real record and which is the artifact?
- **CRITICAL for the re-ingest:** the corrected completion-matching is APN-tolerant + fuzzy-address. Confirm it will **not over-create** new duplicates against these already-corrupted address fields. The dedup fix and the re-ingest matching must be designed together.

### 1.7 PERMIT STRINGS & LINKS
- proj2 `ZP2023-00401974` (= `ZP2023-0040` + `1974`) — a migration parse concatenation. Scan ALL permit_number values for the same concatenation/corruption class against the structured permit-number column in the feed.
- Permit→project mislinks (the proj152↔164 pattern): now that the 568 buildings prove APNs change, re-test whether any permits are attached to the wrong project because the match keyed on a stale APN.

### 1.8 APN / PARCEL
- 2503 Haste proved APN drift (CPRA `055-1875-045` vs city A2 `055-1875-004`). How many v2 projects' APNs disagree with the current Alameda County parcel / the city A2 APN for the same address? APN drift that the match-or-drop rule would have turned into phantom "gaps."

### 1.9 PARTICIPANTS / DEVELOPERS / OWNERS
- `people` table = 0; participants link to `organizations`. Were participant/owner fields copied, parsed, or dropped? (Lower priority, but the flyby will name developers publicly — wrong attribution discredits the tool, so flag accuracy issues even if we don't fix now.)

---

## PHASE 2 — THE HEADLINE NUMBERS (the verdict)

- **2.1 v2 inference ratio:** of all fact-bearing values in v2 (stage, units, milestones, affordability, addresses), what fraction trace to a migration ASSERTION/PARSE with no underlying source vs are evidence-backed? **This is the single number that decides everything.**
- **2.2 Units-at-stake summary:** total housing units mis-stated or dropped across all fact-types — completions dropped, unit counts wrong, stages misplaced — with the net direction (is v2 *under*-counting the city, *over*-counting, or both in different places?).
- **2.3 Re-derivability split:** of all the wrong/missing values, what % is **re-derivable from structured sources already on disk** vs needs new acquisition? (Strong prior from the completion case: most is on disk, in structured columns the migration ignored.)
- **2.4 The strategic verdict — patch vs re-derive:** Given 2.1–2.3, is the right path (A) patch the specific migration bugs in place, or (B) **re-derive v2's facts from primary-source structured columns**, using FINAL.csv / the old migration output only as ONE cross-checked source among several (never the spine)? Make a recommendation with reasoning. If (B), sketch what a clean `build_v2_from_sources` would do differently: structured-column-first, status-keyed not match-or-drop, APN-tolerant address+permit-family matching, honest is_inferred/confidence, FINAL.csv demoted to a corroborating input.

---

## PHASE 3 — RECONCILIATION MATRIX (multi-source cross-check — the standing design principle)

For the overlap where ≥2 sources cover the same building/permit (CPRA xlsx · `R2_R3` building TSV · `.txt` Processing Status · inspection JSONs · city A2 / CKAN mirror · v2):
- **3.1** Where they AGREE on key fields (BP date, CO/Finaled date, unit count, status) → high-confidence facts.
- **3.2** Where they DISAGREE → these are *findings* (city error / scrape error / migration error / real discrepancy), not noise. Sample and show the disagreeing values per source.
- **3.3** Which facts come from only ONE source (no corroboration) → flag as lower-confidence.
This matrix is the durable artifact: it tells us, per fact, how many independent sources back it. It is also the template the replicable any-city framework reuses.

---

## CONSTRAINTS & DISCIPLINE
- **Read-only. No writes, no snapshots-as-writes, no scraping, no commits.** Stage all findings + any candidate lists to `/tmp/`.
- **Verify, don't trust:** re-derive every cited number from the live DB / raw feeds. An empty grep ≠ absence. A docstring claim ≠ behavior.
- **Quote raw-source vs v2 side by side** for every claimed discrepancy — the credibility of this audit is that it shows the structured source said X and v2 says Y.
- **Don't conflate "correctly excluded" with "wrongly dropped."** Trade/alteration/non-residential permits SHOULD be out (the 18,940 alterations are remodels, not housing). Only residential new-construction completions wrongly dropped count as the gap. Apply the same care to every fact-type — distinguish a legitimate exclusion from a bug.
- **Flag, don't fix.** Where uncertain, flag for review rather than asserting. The 587-ambiguous lesson: don't trade a false-positive for a false-negative by over-correcting.
- **Size everything in UNITS, not just rows** — units-at-stake is the metric that matters for the APR.

## DELIVERABLE
`/tmp/forensic_migration_audit.md`: Phase-0 method map · per-fact-type forensics (1.1–1.9) each with the asserted/dropped/structured-ignored/blast-radius/re-derivability verdict · the Phase-2 headline numbers (inference ratio, units-at-stake, re-derivability split, patch-vs-re-derive recommendation) · the Phase-3 reconciliation matrix. Ranked by severity AND units-at-stake. No fixes — this is the ground-truth basis on which we design ONE corrected re-derivation pass, rather than patching errors one at a time.
