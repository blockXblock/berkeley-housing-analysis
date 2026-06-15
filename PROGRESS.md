# Berkeley Housing Pipeline — PROGRESS (current state)

**Purpose:** The live current-state snapshot. Read this first (after `CLAUDE.md`) at session start. Updated at the end of every gated step (see *State-update discipline* in `CLAUDE.md`). This file is canonical; auto-loaded memory is a hint, not ground truth — verify against the DB / `git log`.

---

## Where we are (2026-06-15)

**Verdict layer — 8-year backfill COMPLETE.**
- All **956 permits classified** by `permit_role_classifier @ 112cb03`; verdict+basis materialized into the existing `permits` columns (no new schema).
- Distribution: **completes 693 · does_not 106 · ambiguous 157**. Basis: **evidentiary 671 · description_only 284 · human_override 1** (≈97% of completes evidentiary).
- **Counted-completed = 674** (`v_projects_flat.co_issued_date`, verdict-driven); **published = 672** (explorer/APR reject the `2024-01-01` migration stub). **CY2023/2024/2025 = 103/86/94.**
- **18 DECISIONS-layer holds preserved** (12 human-holds, 5 harvester-inspection, 1 proj34 human_override `@1154b9e`). `verdict_by`: 938 `@112cb03` + tagged holds; zero stale.
- Evidence layer untouched throughout: events 3873 / permits 956 / versions 883 / affordability 890.
- Rollback: `keep_snapshot_2026-06-15_pre-8yr-backfill.db`.

**Classifier — Phase-1 hardening done & verified.**
- `112cb03` (committed dev): sixth-pass FIX-E (ADU/conversion/abbreviation blind-spots) + Phase-1 trade/demo/minor leads + demo-then-build pre-check. **85/85 self-tests**, AGENT-1-VERIFY independent PASS (0 real completions lost, 0 false admitted across 823).

**Sweep — Phase 2-MONITOR FULL 2018-2025 tuned pass COMPLETE (8 detectors, read-only).** Thresholds confirmed; ran across all 8 years.
- **ACCURACY**: match 79-94%/yr, **all sub-90 = categorized COVERAGE gap not correctness** (we-have/city-lacks=0 in 7/8 years; 100% evidentiary every year). 2025 has +2 we-have/city-lacks (NEW — investigate).
- **D8 channel-split (the acquisition list)**: 99 missing completions 8-yr = **69 INGESTION (in feed, load) + 30 ACQUIRE (CPRA request)**. ~70% closes by loading the feed. Completion-match gap is consistent (NOT collapsing in recent years); the housing-permit backlog grows (137→964) but is mostly under-construction/un-matched, not completed.
- **PLACEHOLDER**: stubs concentrate 2024(46)/2025(51) — recent entitlement-date placeholders (NEW pattern). **D5**: 0-2/yr (consistent). **OUTLIER (de-noised)**: 0 except 2025 proj154 (counted, no completes sibling — NEW). **D6**: 0 all years — structurally under-powered (CPRA vs description NOT independent; needs assessor). **D7/DEPENDENCY**: 103 mis-binned / 0 stale.
- **NEW patterns (older-year blind spots)**: (1) 2025 +2 city-lacks-we-have; (2) 2024-25 stub concentration; (3) proj154 no-completes-sibling; (4) D6 non-independence.
- **Calibration calibration (2018-2019 detail)** retained in git history.
- **D7-SCOPE**: 103 planning records (ZP/PLN/DRCF) mis-binned in the completion-ambiguous set → **real harvest queue = 54 B-permits** (26 terse-candidate + 28 genuine-uncertain), not 157.
- **PLACEHOLDER**: 91 year-precision event-date stubs (51 `@2025-01-01`, 40 `@2024-01-01`) + 33 zero-unit projects. (CO count already rejects the 2 CO stubs; the rest are entitlement/Table-A date-quality.)
- **ACCURACY** (vs CKAN reconcile-target): CY2018 **89%**, CY2019 **84%** — gap is **entirely COVERAGE** (we-have/city-lacks = 0; city-has/we-lack = 7/17), **100% evidentiary** on our side. Below-90 = a categorized coverage finding, not a correctness failure.
- **D5-TEMPORAL**: 13 ordering violations, mostly the `2025-01-01` entitlement-stub class (cross-confirms PLACEHOLDER); 2-3 genuine (proj91, proj161).
- **D8-COMPLETENESS** (parse corrected & complete): both feed files parsed (header @ `PermitNumber` row, stdlib) → **30,764 unique B-permits** (sanity confirmed). Per-year **RAW gap** ~3,600/yr (mostly non-housing) vs **HOUSING gap** (UnitsAdded>0/ADU/new-dwelling): 137(2018)→964(2024), growing. **D8↔ACCURACY CONFIRM** by APN: the city-has/we-lack completion gap self-categorizes — 14/24 (2018-19) = **ingestion-backlog** (permit already in feed, load it), 10/24 = **acquire** (absent from feed → pre-window CPRA). = the Phase-4 acquisition list, derived. (Feed dates are Excel serials — convert on any future ingest.) 13 orphan completions; Table B absent from mirror (known).
- **OUTLIER**: too loud — fires on expected main+subsidiary mixed-verdict and the bimodal ADU+tower size tail. **Needs tuning.**
- **DEPENDENCY**: 0 stale-source fires + the **`housing_rules` false-absent meta-catch** (a builder almost recomputed canonical cycle/tier logic inline off `ls scripts/housing_rules.py` — it's a package dir, committed `7165f3b`). First recorded DEPENDENCY catch.
- **D6-CONSISTENCY**: under-powered for SFR/ADU years (no multi-unit description counts; assessor lacks reliable unit counts).

**Site / publish state.**
- Completion display now **derives from `co_date`** (export_explorer_data_v2.py); CO stat == map markers == **672** by construction. Non-v2 export sequestered to `scripts/superseded/`.
- **NOT pushed:** dev commit `58ffdf4` (the 672 republish) is staged; the **live site still shows the old number**. STEP 5 republish (push + Cloudflare purge) is **pending John** — John owns all irreversible ops.

---

## Next steps
1. **WATCHER GATE — John reviews the full-pass union** (esp. the 4 new patterns) before Phase 3. The detector findings feed Phase 3/4 directly: the D8 channel-split (69 ingest / 30 acquire) IS the prioritized acquisition list.
2. **Phase 3** (per-year): generate APR via `generate_apr_v2` (reads view) → diff vs CKAN (read-only target) → categorize every disagreement (COVERAGE / CITY-UNDER-REPORT / COUNTING-CONVENTION). Builds on the D7 bijection. AGENT-3-VERIFY per year.
3. **Phase 4** synthesis: per-year match vs ≥90% (with the categorized coverage account already in hand), cross-year pattern, the 69-ingest/30-acquire acquisition list. The deliverable.
4. **Resolve the 4 new patterns**: investigate 2025's +2 city-lacks-we-have; the proj154 no-completes-sibling; decide on the 2024-25 entitlement date-stub cleanup; rebuild D6 on a genuinely-independent unit source (or retire it).

## Parked
- Optimizer watchers (ACQUISITION-YIELD) — next sweep.
- **5-project pre-window CPRA request** (proj175/481/505/525/555 — `B2016/2017` permits the harvester can't reach).
- **CIC spot-check proj117 / proj32** (the two 0-inspection harvester extractions — rule out an extraction miss; low priority, uncounted either way).
- Exclude the **103 D7 planning records** from the completion harvest queue (queue hygiene).

## Open decisions / risks
- **STEP 5 republish not pushed** — live site shows stale number until John pushes `58ffdf4` + purges.
- **OUTLIER threshold un-tuned** — fires on expected patterns; calibrate before the full run.
- **D6 needs a third independent unit source** — assessor unit counts unreliable; D6 weak in SFR years.
- **Year-precision entitlement date stubs** (51 `@2025-01-01` + 40 `@2024-01-01` events) — data-quality issue on the Table-A/cycle side, not yet addressed; affects cycle-segmentation precision.
- **`contested` basis deferred (0)** — awaits post-harvest reconciliation with genuinely-independent third sources (staff reports / AHCPs / inspections); never from CKAN-disagreement (circularity).

---
*Prior narrative PROGRESS retained in git history (this file was rewritten as a current-state snapshot 2026-06-15).*
