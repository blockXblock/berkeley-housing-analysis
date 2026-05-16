# Prompt: Continuing the permit_role classifier and stage-derivation fix

**Save location:** `docs/methodology/permit_classifier_session_handoff.md`

**Created:** 2026-05-15

**Purpose:** Hand off mid-task work on fixing the Berkeley Housing Pipeline's
project-stage misclassification bug. The previous chat session became long
enough to slow rendering. This prompt lets a fresh chat pick up at the exact
point of progress.

---

## How to use this prompt

Copy everything between "BEGIN PROMPT" and "END PROMPT" below. Paste it as
the first message in a new Claude chat. The fresh chat will have full
context to continue the work.

---

## BEGIN PROMPT

I'm John Gage, working on the Berkeley Housing Pipeline at berkeleybuild.com.
I need help continuing mid-task work that became too long for the previous
chat. This message captures the full state so we can continue without
re-deriving anything.

### Repository context

- Repo: `~/berkeley-data` (blockXblock/berkeley-housing-analysis)
- Database: `~/berkeley-data/databases/berkeley_housing_v2.db`
- v2 schema: 47 tables, 181 projects, 240 permits, 2,340 events, 1,275 documents
- Backups: multiple in `~/berkeley-data/databases/berkeley_housing_v2_*.db`
- Branches: `main` (production, deploys to berkeleybuild.com via GitHub Pages)
  and `dev` (in-progress work)

### My working style and what I expect from you

- I prefer reversible steps. Backups before destructive operations.
- Show proposed changes before applying them. Audit-before-action.
- Push back on my ideas when you genuinely disagree. Don't deflect to
  "your call."
- Don't mention time of day or fatigue. Professional data-science register.
- Use plain text. Avoid bullet-only responses when prose works.
- Distinguish my decisions from CC's (Claude Code, in terminal). CC has
  sometimes acted faster than I asked; I want to verify before applying.

### The bug we're fixing

The Berkeley Housing Pipeline's public Explorer at berkeleybuild.com
showed 38 projects as "Completed" in 2025. A 10-project sample audit
revealed 50% (5 of 10) were actually misclassified: their stage was
advanced to "Completed" because of CO events on subsidiary permits
(solar PV, electrical, furnace replacement, voluntary seismic retrofit,
demolition, housing code repairs) rather than the project's main
new-construction permit.

Root cause: a script called "Fix A" (run on 2026-05-13) advanced any
project to "Completed" if it had any CO event, without distinguishing
whether the CO was for the primary development permit or a subsidiary
trade permit. Berkeley uses a combined BEMP permit structure where each
distinct scope of work gets its own building permit, so a project
parcel may have many BEMP permits (one for new construction, separate
ones for solar, retrofit, etc.).

### Decisions already made in the prior chat

1. **Solve via keyword-based classifier**, not schema change. The
   classifier reads each permit's `description` field at stage-derivation
   time. No `permit_role` column was added to the permits table.

2. **Three-value classifier:** `completes_project`,
   `does_not_complete_project`, `ambiguous`.

3. **Standalone module** at `scripts/permit_role_classifier.py`. Imported
   by `scripts/export_explorer_data_v2.py`.

4. **Stub CO events (no permit_id, no summary, no source_url) do not
   drive stage decisions.** Filtered out by `is_evidentiary_co_event()`.
   15 such events exist in v2; they remain in the database but are
   ignored by the corrected stage logic.

5. **Re-run Fix A logic with corrected classifier (Option B from earlier
   discussion):** advance stage to completed only when project has at
   least one evidentiary CO event classified as `completes_project`.

6. **Project 34 (2680 Bancroft Way) was manually corrected** as the
   canonical example: stage reverted `completed -> entitled`. Migration:
   `scripts/migrations/2026-05-14_project_34_correction.sql`. Other
   confirmed misclassifications (projects 70, 79, 90, 27, 150) were NOT
   manually corrected; they will be corrected automatically by the
   structural fix when applied.

### What's already built

**File:** `scripts/permit_role_classifier.py` (in repo, committed)

Three public functions:
- `classify_permit_for_completion(description) -> str`
- `is_evidentiary_co_event(event) -> bool`
- `project_has_completion_evidence(project_id, conn) -> (bool, list[dict])`

Plus 17 self-test cases drawn from real audit findings. All pass:
`python3 scripts/permit_role_classifier.py` returns "Results: 17 passed,
0 failed" (CC reported 18 passed; the extra was the None test case).

### Where we stopped

Ran the classifier against all 240 permits and all 70 CO events.
Distribution:

**All 240 permits:**
- completes_project: 25 (10.4%)
- does_not_complete_project: 69 (28.7%)
- ambiguous: 146 (60.8%) — mostly empty-description ZP permits, which is
  expected because zoning permits aren't construction permits

**All 70 CO events:**
- completes_project: 7 (10%) — real completions
- does_not_complete_project: 31 (44%) — confirmed subsidiary misattributions
- ambiguous: 17 (24%) — pattern gaps to address
- no_permit_link: 15 (21%) — stubs, already decided to ignore

CC then analyzed the 17 ambiguous CO events and identified pattern gaps:

**False negatives (should be completes_project but classified ambiguous) — 2 cases:**

- event_id 2716: "Construction of a 9665-SF, four story 39-unit
  congregate residence" — the `\d+\s*units` pattern misses hyphenated
  "39-unit"
- event_id 2649: "Construction of a...four story 11-unit + attached ADU"
  — same hyphenation issue

**False negatives (should be does_not_complete but classified ambiguous) —
~15 cases:**

CC recommended adding patterns for:
- remodel ("Kitchen & Bath Remodel", "Interior remodel", "Residential
  Remodel")
- siding ("Replace...siding")
- window ("Remove & replace one kitchen window")
- shoring, excavation, grading (site prep work)
- insulation, drywall (interior finish work)
- mural, LED screen, exterior sign (cosmetic/signage)
- "demolish.*(building|apartment|residence)" as a stronger demo signal

### Next concrete step

Update `scripts/permit_role_classifier.py` with two changes:

1. **Completes_project fix:** change `\d+\s*units?\b` to
   `\d+[- ]?units?\b` to catch hyphenated unit counts.

2. **Add does_not_complete_project patterns** for the 12 categories CC
   identified.

After patching, re-run self-tests (still must pass all 17 original tests)
PLUS add new test cases for the 17 ambiguous events to verify they now
classify correctly.

Then run the scan again. Target distribution for the 55 linked CO events:
- completes_project: 9-10 (the 7 already classified plus 2 newly caught)
- does_not_complete_project: ~46 (the 31 already plus ~15 newly caught)
- ambiguous: 0-2 (residual truly ambiguous cases)

### After the classifier is tuned

Three steps remain in this work stream:

**Step A:** Modify `scripts/export_explorer_data_v2.py` to use
`project_has_completion_evidence()` for stage derivation. Replace the
existing "any CO event = completed" logic. This is where the classifier
actually does its job.

**Step B:** Regenerate Explorer output. The "Completed" project count
should drop from 38 to approximately 10-15 (real completions only).
Verify by checking the 11 audited projects:
- Should STILL show Completed: 83, 134, 173, 176 (4 real completions)
- Should NOT show Completed: 34, 70, 79, 90, 27, 150 (5 confirmed
  misattributions) — already reverted for 34, others get auto-corrected
- Ambiguous: 154 (Stage=withdrawn but description says "OPEN June 2025"
  — separate investigation)

**Step C:** Commit and decide on push. Whichever branch we're on
(`main` or `dev`), verify the branch is what we want before pushing.
The change updates production data, so verifying branch is important.

### Methodology doc

The doc at `docs/methodology/project_status_methodology_2026-05-13.md`
already captures:
- The original Fix A bug
- The 10-project audit findings (50% misclassification)
- The decision to use a classifier-based fix without schema change
- Deferred future schema considerations (from a Perplexity advisory)

After Step C lands, update the doc with:
- Pattern coverage stats (how many CO events ultimately classified each
  way)
- Final "Completed" count on berkeleybuild.com after the fix
- Note that remaining ambiguous events (if any) need manual review

### Things to NOT do in this chat

- Don't add a `permit_role` column to the permits table. Decided against.
- Don't try to backfill `permit_id` on the 15 unlinked CO events tonight.
  Separate work.
- Don't re-do the audit of "completed" projects. The pattern is
  established; classifier addresses it systematically.
- Don't expand scope to the Perplexity framework (two-level lifecycle,
  status mapping, etc.). Documented as deferred future work.
- Don't push to main without verifying we mean to.

### Starting point

Update `scripts/permit_role_classifier.py` with the pattern fixes (unit
hyphenation + 12 new subsidiary patterns), add corresponding test cases,
verify all tests pass, then re-run the scan against all 70 CO events.

After that runs cleanly, modify `scripts/export_explorer_data_v2.py` to
use the classifier, regenerate, verify against the 11 audited projects,
and commit.

## END PROMPT

---

## Provenance

Created at the end of a multi-hour session that built:
- v2 deployment to berkeleybuild.com (commits `cd2023e`, `52b87c0`,
  `9290c80`)
- KML L-shape for 2400 Bowditch (Anna Head)
- UC Berkeley Dormitory Tour KML (5 iterations, recorded as YouTube
  video CLfV9vLPOJs, embedded on site)
- The permit_role classifier module (`scripts/permit_role_classifier.py`,
  uncommitted as of session end)
- Discovery of the 50% stage-misclassification rate via 10-project audit
- Multiple methodology doc updates

The session also revealed Claude Code was missing the existence of the
migration script `scripts/migration/migrate_v1_to_v2.py` (1,685 lines)
and `scripts/migration/import_cpra_2023_2025.py` (923 lines) until
explicit investigation. CC also drifted on terminology (proposing
`phased_component` and `revision` as permit_role categories that weren't
agreed). Both are noted for the new chat as patterns to verify.

Backup chain at handoff:
- `berkeley_housing_v2.db` — current state, project 34 corrected
- `berkeley_housing_v2_before_permit_role_2026-05-15.db` — from earlier
  in tonight's session (before any classifier work)
- `berkeley_housing_v2_after_dedup_2026-05-13.db` — post-dedup baseline
- `berkeley_housing_v2_after_fix_a_2026-05-13.db` — post-Fix A baseline
- `berkeley_housing_v2_after_date_fixes_2026-05-13.db` — earliest
  tonight's baseline
