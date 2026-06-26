# RESUME — chat-Claude, v4 rebuild (written 2026-06-26, before the first JN-A run)

**You (chat-Claude) plan, fact-check, and write prompts. You NEVER edit the repo. CC executes; John
owns all irreversible operations and is the bridge that moves your presented files into the repo.**
If you have just been compacted: read this whole file, then ask John where things stand before
proposing anything. Do not re-derive the decisions below.

---

## WHAT THIS PROJECT IS NOW (the pivot — do not re-litigate)
The Berkeley Housing Pipeline is being rebuilt as **v4**, the single largest data transformation in
the project's history. v2 (good schema, corrupted data) and v3 (good data, address-keyed schema that
collapses multi-building developments) both hit a structural ceiling — 1173 Hearst, Logan Park, the
+34 phantom buildings. v4 is the way through.

**v4's organizing commitment:** a building's record is a **sourced, typed, actor-attributed
lifecycle EVENT STREAM** (append-only ground truth). All entities — parcels, structures, units,
projects, actors — are **PROJECTIONS over that stream**. Classification, identity, and completion
verdicts are **reversible LABELS on permanent evidence, never gates that delete.** This kills the
silent-data-loss class that defined v1->v2->v3.

**The five real entities:** parcel (land), structure (a physical building = its master permit),
permit (the identity signal), unit (lives in a structure — the edge v2/v3 never wired), project
(human grouping spanning parcels/structures). Address and APN are M:N attributes, NEVER keys.

## THE FIVE GOALS v4 SERVES (the "why" that constrains the schema)
1. Sophisticated Berkeley housing website (Explorer). 2. City-agnostic data-science curriculum (JN).
3. APR-migration path for cities doing APR-by-spreadsheet. 4. The thesis: one method, three audiences.
5. Open citizen data access / data journalism — which forces provenance, divergence, and
actor-actions to be FIRST-CLASS queryable tables. This is why v4 is city-neutral: the lifecycle
vocabulary is abstract; Berkeley is the first ADAPTER, not the template.

## SETTLED DECISIONS — do NOT re-derive
- **Re-derive from sources, NOT migrate from v2/v3.** v4 is the pipeline's output, reproducible by a
  student from raw CPRA. Migrating v3's rows would import its phantom-master bugs as fact.
- **Schema is DESIGN-ONLY and committed** (commit f1a37a8, schema/v4/schema_v4.sql, 27 tables, 2
  views). It is empty. v3 remains live and untouched.
- **Completeness is VERIFIED.** The two canonical CPRA files (BP_Annual Permit Report-2018-2022.xlsx
  + -2023-2025.xlsx, 32,202 raw rows) contain every city BP-extract in the 26-1525 drop as a subset,
  AND reproduce the 96/96 CKAN-reported CY2024 completions. "Complete against every city pull and
  report we can check" — strong, bounded, defensible.
- **The feed's date axes (probe-verified):** Submittal 32,202 / Issuance 31,940 / Finaled 21,650 /
  Completed 1. Finaled-axis is cleanly in-window 2018-2025; out-of-window dates exist only on
  submittal/issuance (long-lifecycle permits) and are FLAGGED not filtered.
- **Each permit row is a BUNDLE of events** (submitted/issued/finaled/completed), exploded one event
  per present date. Table A2 BP-section = fold permit_issued; CO-section = fold permit_finaled.

## CURRENT STATE — SUPERSEDED BY HANDOVER_v4_2026-06-26.md
**READ `notes/v4/HANDOVER_v4_2026-06-26.md` FIRST — it has the live current state.** This section is
kept for settled-architecture context; the progress below is now behind the handover.

- schema/v4/schema_v4.sql — committed, 27 tables.
- notebooks/v4/JN-A_ingestion.ipynb — RUN CLEAN, COMMITTED (cbcdeee). 85,793 events, four-axis,
  conserved, verifier PASS. Settled — do not re-run.
- notebooks/v4/JN-C_classify.ipynb — **BUILT, RUNS CLEAN, COMMITTED.** Pass 1: #1 housing/non-housing
  + #2 master-collapse, defers #3. 16 vocabulary tests pass. Reversible labels to event_classifications.
  Generator at scripts/v4/build_jn_c.py (SOURCE OF TRUTH — edit it, regenerate; never hand-edit .ipynb).
- **LIVE WORK (see handover):** deflation fix approved-not-implemented (confident SFR/ADU blank units→1;
  multifamily-blank→flag); then inflation check on the 20-99 band (REV double-count?); then the v4↔HCD
  ADU bijection (HCD oracle-only, canonical-APN join, no address-collapse). JN-B/JN-D and the SALVAGE
  conversation remain planned/deferred. Do NOT re-run JN-A or rebuild JN-C from scratch — extend it.

## THE RUN THAT WORKED (and the finding it surfaced — for reference)
The first real JN-A run mis-mapped 3 of 4 date axes (bound *Status columns instead of *Date),
producing a submittal-only stream. Conservation PASSED anyway (internally consistent) — proving
conservation guards against LOSS but NOT against MIS-DISCOVERY. The per-axis anchor check caught it.
Three fixes (all proven on synthetic reproductions before the clean re-run): (1) preference-scoring
in the column matcher (Date > Status); (2) CHECK 4 hard anchor halt for known cities; (3) a verifier
that counts real columns independently rather than inheriting the discovery bug. LESSON: anchors guard
mis-discovery, conservation guards loss — you need both.

## HARD-WON LESSONS FROM TODAY (do not repeat)
- **VERIFY THE ACTUAL FILE ON DISK before trusting any error report.** Today an hour was lost because
  a broken file sat in the repo while fixes lived only in the sandbox; the error's `resource` path
  named the real file and it was read past three times. When John reports an error, check WHICH file
  on HIS disk throws it.
- **The download button writes the file INTO THE REPO** (e.g. notebooks/v4/), NOT to ~/Downloads. It
  lands under the presented name; John then copies it over the canonical name.
- **NAMING: never put "v3" (or any DB-generation number) on a v4 artifact.** It collides with the
  database names that mean something specific. Use dates or plain descriptors.
- **Escaping across generator layers is the bug factory.** When emitting notebook code, avoid
  backslash-heavy constructs (inline regex); prefer `" ".join(s.split())` over `re.sub(r"\s+")`. Gate
  every generated notebook with compile-under-warnings-as-errors (what Pylance does), not just
  execution (which tolerates bad escapes).
- **Present every file with a version-unambiguous name and a download button.** CC cannot see
  /mnt/user-data/outputs/. John is the only bridge.
- **Do NOT jump ahead to CC prompts or actions without John's go.** State the plan, wait.

## DISCIPLINE (standing)
Read-only by default. Every build gated: snapshot -> read-only preview -> STOP for John -> guarded
write -> fingerprint -> idempotency. dev branch only, no push without instruction. CKAN/HCD is
oracle-never-source. A conservation FAILURE or discovery HALT is a real FINDING, never a thing to
engineer around. Verify artifacts directly; CC summaries can be confidently wrong.
