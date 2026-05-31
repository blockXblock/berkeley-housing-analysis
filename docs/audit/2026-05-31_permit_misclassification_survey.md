# Permit-Misclassification Systemic Survey — 2026-05-31

**Scope:** Read-only survey of the full v2 dataset to scope the permit-
misclassification problem (minor alteration permits ingested as project-level
BP/CO milestones) and design a corrective filter. **No data, DB, or script
modified.** Does not touch external drives or the Toshiba copy.

---

## Headline: confirmed, pervasive, and the filter works

~**50% of milestone-driving permits are alteration permits.** Excluding
alteration-driven CO milestones moves the totals **onto the validated reference**
without stripping any known real completion:

| | Current (all permits) | Corrected (filtered) | NotebookLM ref |
|---|---|---|---|
| **CY2024 CO units** | 1360 | **786** | ~708 |
| **CY2025 CO units** | 810 | **577** | ~482 |

The APR pilot's CO overshoot is **largely explained by permit misclassification.**

---

## Stage 1 — How milestones derive, and the discriminator fields

`v_projects_flat.bp_issued_date` / `co_issued_date` = `MAX(event_date)` over
`project_events` of type `building_permit_issued` / `co_issued`. Each such event
may link to a `permits` row. Discriminator fields available on `permits`:

| Field | Usefulness |
|---|---|
| **`description`** | **Best signal** — free text ("New 7-story 69-unit…" vs "Install exterior sign") |
| `valuation` | Secondary — **124 of 244 are NULL**; solar can reach $107k, so threshold-alone is unreliable |
| `permit_type_id` | **Weak** — all building permits are type 5 (`building_permit`); doesn't separate new-construction from a window replacement |
| **event types 26/27** | `permit_classified_primary` / `permit_classified_subsidiary` **already exist in the vocabulary** — the schema anticipated this — **but were never populated** |

## Stage 2 — Classification of the 191 BP+CO milestone-driving permits

| Class | Count | Examples |
|---|---|---|
| **ALTERATION** (should NOT drive milestones) | **95** | windows, solar/PV, signs, water heater, furnace, heat pump, siding, remodel, temp power, shoring, demo, retrofit, "repair lights," "replace washer & dryer" |
| STRUCTURAL (should drive) | 40 | "New 7-story 69-unit mixed-use," "72 units market rate," "5-story residential apartment," "New SFR" |
| NO_DESC (manual completion, no permit) | 32 | human-asserted CO events (often Jan-1-floored year markers) |
| AMBIGUOUS | 24 | shoring/grading/demolish, large-valuation-no-desc |

**~50% (95/191) of milestone-driving permits are alteration permits.** Recurring
culprits by keyword: **photovoltaic/solar, window/door, sign, temp power, water
heater/furnace/heat pump, remodel, siding, shoring/grading, demolish.**

## Stage 3 — Impact on APR CO totals (the reconciliation)

Filter rule applied: a project's CO in year Y is **valid** if it has a co_issued
event that is **STRUCTURAL or NO_DESC (manual)**; **spurious** if its only
in-year co_issued events are **ALTERATION/AMBIGUOUS**.

- **CY2024: 1360 → 786 units** (15 → 6 projects; **ref ~708**). Down ~574 units.
- **CY2025: 810 → 577 units** (22 → 13 projects; **ref ~482**). Down ~233 units.

Both corrected totals land **near the NotebookLM references** — strong evidence
the overshoot was permit misclassification, not a counting-method difference.

Spurious CO milestones removed (sample): 1598 University (207, "shoring" — not
complete, just started), 2001 Ashby (87, solar), 2441 Le Conte (65, "repair
lights"), 2344 Fulton (18, "replace washer & dryer"), 2641 College (3, siding),
3001 Benvenue (1, furnace), 411 Vassar (kitchen remodel). **BP milestones are
equally contaminated** (e.g. 2138 Kittredge's $690 bathroom window) — the filter
should apply to `building_permit_issued` too, correcting the "permitted" counts
(Table A2/B) as well.

## Stage 4 — Filter design + both-direction error check

**Recommended rule (not executed):** classify each milestone-driving permit via
**description keywords** (primary) backstopped by **valuation** (secondary), and
**keep manual NO_DESC events**:

```
SPURIOUS (drop as milestone driver) if description matches:
  solar|photovolta|pv |window|door|sign|water heater|furnace|heat pump|
  siding|insulation|drywall|remodel|temp(orary) power|temp meter|sub ?panel|
  meter (main|release)|washer|dryer|reroof|shoring|grading|EV charg|
  repair|seismic-only|"revised job card"
STRUCTURAL (keep) if: "new construction"/"construct… building|residence|home",
  "N units"/"N-story", "mixed-use building", "apartment building", congregate/
  senior living  — OR valuation ≥ $1M with no alteration keyword.
KEEP manual completions (NO_DESC, no linked permit) — researcher-asserted.
DEMO/SHORING/GRADING → not a completion (drop from CO; may inform start).
```

Ideally, **populate the existing `permit_classified_primary/subsidiary` events**
rather than filtering at query time — the schema is already built for it.

### Error analysis — BOTH directions
- **Correctly removes:** the 9 CY2024 + 9 CY2025 alteration-only "completions"
  above (furnace, solar, sign, window, repair, shoring, demolish). All clearly
  not completions.
- **False negatives — 0 among known completions.** All 8 tested real completions
  **survive** (each has a STRUCTURAL or manual NO_DESC CO):
  2150 Kittredge (169u, via NO_DESC), 3030 Telegraph (144u, via NO_DESC),
  2352 mixed (72u, STRUCTURAL), 8-story 28u, 2555 College (11u), senior 6-story,
  5-story apt, 5-story mixed — **none wrongly stripped.**
- **Residual false-negative RISK (verify, do not auto-drop):**
  - **2352 Shattuck (id179, 237u)** — dropped on "revised job card" (admin). A
    large project; its real structural CO may simply not be ingested. **Verify
    against Accela before excluding from 2024.**
  - **2440 Shattuck (id176, 40u)** — 2024 CO event is solar; has a 2023 Phase-II
    structural permit. Confirm completion year.

A valuation-**only** filter is rejected: 124 NULL valuations + $100k solar
permits would both mis-sort. Description keywords + NO_DESC-keep is the safe core.

## Specific projects with spurious milestones (beyond 2138/2150)

CY2024 CO: 1598 University (shoring), 2001 Ashby (solar), 2440 Shattuck (solar),
1614 Sixth (remodel), 2705 Benvenue, 1109 Cowper, 2009 Addison (LED sign), 1246 Rose (solar).
CY2025 CO: 2441 Le Conte (repair lights), 2344 Fulton (washer/dryer), 2641 College
(siding), 3001 Benvenue (furnace), 1111 Allston (solar), 40 Hill (windows),
576 San Luis (solar), 411 Vassar (kitchen remodel). Plus BP-side: 2138 Kittredge
(bathroom window), and many others where `building_permit_issued` rests on
solar/window/temp-power permits.

---

## Recommendation

1. **Populate `permit_classified_primary/subsidiary`** (or add a query-time
   filter) using the keyword+valuation rule above; keep manual NO_DESC events.
2. **Apply to BOTH `building_permit_issued` and `co_issued`** milestones (BP side
   is equally contaminated → fixes Table A2/B permitted counts too).
3. **Verify, don't auto-drop, the 2 residual-risk projects** (2352 & 2440
   Shattuck) against Accela.
4. Re-run the APR pilot after applying — expect CY2024 ≈ 786 (vs ref 708) and
   CY2025 ≈ 577 (vs ref 482), with real completions intact.

*Diagnosis only. No data/DB/script modified. Uncommitted — review before any fix.*
