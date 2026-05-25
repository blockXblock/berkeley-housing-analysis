# Classification system added (Option C event-based approach)

**Date:** 2026-05-20
**Status:** Schema work complete. Export script update and CIC reconnaissance for other problem projects deferred to future sessions.

## What got built

Five new vocabulary entries in `vocabulary_event_types` (IDs 25-29):

| ID | code | label | implies_stage |
|---|---|---|---|
| 25 | permit_finaled | Permit Finaled | NULL |
| 26 | permit_classified_primary | Permit Classified as Primary | NULL |
| 27 | permit_classified_subsidiary | Permit Classified as Subsidiary | NULL |
| 28 | first_inspection_observed | First Inspection Observed | under_construction |
| 29 | final_inspection_passed | Final Inspection Passed | NULL |

Three data fixes:

1. **Event 2658** (2680 Bancroft, the misattributed seismic retrofit): changed from `co_issued` to `permit_finaled`. Kept linked to project 34 and permit 149 (schema requires `project_id NOT NULL`). Classification event 2794 added to mark permit 149 as subsidiary.

2. **Event 2794** (new): `permit_classified_subsidiary` event for permit 149 on project 34. First entry in the new classification system.

3. **Event 2793** (2352 Shattuck Finaled, created yesterday as a placeholder `status_update`): changed to `permit_finaled` for accurate semantics.

## Why this design

### The problem we discovered

Todays work started with a question: why do some projects have negative-delta timelines in our analysis (CofO date earlier than entitlement date)?

Investigation of 6 problem projects (174, 161, 126, 129, 34, 113) revealed a systemic pattern: **one parcel often has multiple unrelated permits spanning years.** Existing-building maintenance permits, signage permits, accessory work, AND the new developments permits all coexist at the same parcel. The data model treated all events at a project_id as if they belonged to the same lifecycle. They dont.

The clearest example is 2680 Bancroft (project 34): an `inferred` event existed with `event_type_id=17` (co_issued) for B2024-00543, but B2024-00543 is a seismic retrofit on the existing Bancroft Hotel structure, NOT new-development completion. Someone (jgage, presumably) had already annotated this with `[MISATTRIBUTED SUBSIDIARY: ...]` in the summary text. But that annotation was inline narrative, not structured data - invisible to queries.

### Three design options considered

**Option A:** Add classification fields directly to the `permits` table (is_project_primary, classification_confidence_type_id, etc.). Simple but adds columns that may not always be populated; doesnt match v2s "everything is an event with provenance" pattern.

**Option B:** Separate `permit_project_classifications` table. More normalized but overengineered for whats likely one-classification-per-permit-per-project.

**Option C (chosen):** Use the existing `project_events` table with new vocabulary entries for classification (`permit_classified_primary`, `permit_classified_subsidiary`). Classifications become events with full provenance (observed_by, observed_at, confidence_type_id, source_type). Consistent with v2s design philosophy.

### Why permit_finaled implies NULL stage

A natural reading would be: permit_finaled imply completed (matching the existing co_issued imply completed mapping). We chose NULL instead, deliberately.

Reasoning: projects can have multiple primary permits. 2352 Shattuck has B2019-05574 (Phase II North Building, Finaled 2022-01-14) AND B2019-05575 (Phase I South Building, also Finaled). If `permit_finaled` advances stage to `completed`, then the first Finaled permit would prematurely flip the project to completed - even if Phase I hasnt been finaled yet.

Inspection data (when we have it) will let us properly determine "project_completed" by checking that ALL primary permits have passed their final inspections. Until then, NULL is the safe choice.

This is also why `first_inspection_observed` DOES imply `under_construction` (id=5) - the first inspection on ANY primary permit is a reliable signal that physical construction has started. Stage *entry* signals are safe; stage *completion* signals require more care.

### Why first_inspection_observed has stage implication but final_inspection_passed doesnt

Same reasoning extended: the first inspection on any primary permit is unambiguous evidence construction is underway. The "final" inspection on any single permit is just that permits final, not necessarily the projects final.

### Why we kept event 2658 attached to project 34 instead of disconnecting

Our first SQL attempt set `project_id = NULL` and `permit_id = NULL` to disconnect event 2658 from project 34. The dry-run caught a `NOT NULL constraint failed: project_events.project_id` error. The schema explicitly requires every event to be linked to a project.

This was a *good schema decision* (events without project context are hard to query later), but it forced a different approach: keep the event linked, change its type to be more accurate, and use the classification event to handle the disambiguation. The classification event marks permit 149 as subsidiary, so any downstream logic that respects classifications will correctly ignore this Finaled event for project completion purposes.

This is more consistent with the Option C design philosophy: facts (permit was finaled) stay linked; classification (this permit is subsidiary) is separate metadata.

### Why we deferred the export script update

The export script `scripts/export_explorer_data_v2.py` has two relevant queries:

1. Lines 142-159: a query that uses an explicit allowlist of event codes (`application_submitted, application_complete, entitlement_approved, building_permit_issued, co_issued, construction_start_observed, topped_out, demo_permit_issued`). Our new codes are NOT in this list.

2. Lines 290-310: the main events export, which pulls all events and maps codes to stage labels via `stage_label_map`. Our new codes are NOT in this map. Unknown codes default to `Other`.

So if we regenerated the JS now: events 2658 and 2793 (previously `co_issued` and `status_update`) would appear with `stage = Other` - a less informative label than they had before. The classification event 2794 would also appear with `Other`.

This is a regression in user-visible quality. Rather than push a regression, we deferred the JS regeneration until the export script is updated. Natural time to do that: after CIC reconnaissance produces classification data for the other 6 problem projects, so the update is part of a larger batch.

## Whats unresolved (for future sessions)

1. **Export script updates.** Add the 5 new codes to both queries:
   - Allowlist update (line 147): add `permit_finaled` so inactive-detection works correctly
   - stage_label_map update (line 318): map `permit_finaled` to Completion, `first_inspection_observed` to Construction, `final_inspection_passed` to Completion, classification events to either Classification (visible) or filtered out
   - Decide: are classification events visible on the public timeline, or admin-only?

2. **CIC reconnaissance for 6 other problem projects.** Projects 174 (1773 Oxford), 161 (2555 College), 126 (2427 San Pablo), 129 (1614 Sixth), 113 (2138 Kittredge). For each, classify which permits are primary vs subsidiary. This is the workstream the new vocabulary was built to support.

3. **Eventual project_stage_spans view review.** The view derives timeline bars from events via `implies_stage_type_id`. Our new vocabulary has NULL implies for permit_finaled - meaning that event wont contribute to the view. If we want completion bars to appear from permit_finaled events, the view (or a different mechanism) needs adjustment.

4. **Inspection data ingestion.** The bigger workstream from `2026-05-19_inspection_data_as_civic_record.md`. Once we have inspection rows in the database, `first_inspection_observed` and `final_inspection_passed` events can be generated automatically from inspection data.

5. **One more design question.** When CIC finds a primary permit whose Finaled date is the latest among all primary permits AND inspection data confirms its the projects true final inspection, should the system automatically create a `co_issued` event (or a future `project_completed` event) to advance the stage? Or should that always be a deliberate human decision? Lean toward "deliberate human decision" for now since automated stage advancement was the root of the 2680 Bancroft problem.

## What happened thats worth remembering

- The schemas `NOT NULL` constraint on `project_events.project_id` caught our first attempt at disconnecting an event. The dry-run-then-commit pattern saved us from a broken transaction. Worth keeping that discipline.
- Shell heredocs broke on quoting again. Used Python triple-quoted strings (via python3 with PYEOF marker) for the SQL file, same approach as last night for the notes file. Pattern to remember: for any multi-line content with quoting risks, write to a file via Python rather than shell heredoc.
- Reasoning that started this session ("sharpen the timeline estimates") landed at a much deeper architectural finding (permits at a parcel does not equal permits of a project) that fundamentally changes how the freshness pipeline must work. Good outcome from following the data honestly.
