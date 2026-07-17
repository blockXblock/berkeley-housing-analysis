# CPRA Import Plan (BP_Annual Permit Report → v2)
**Drafted:** 2026-05-10
**Status:** 🟡 PLAN — not yet executed
**Source:** `BP_Annual Permit Report.xlsx` (local project drive; path redacted from public copy)
**Target:** `databases/berkeley_housing_v2.db` (`permits`, `project_events`, possibly new tables)
**Related:** `data/apr/cpra_2023_2025_comparison.md` (full analytical findings), `scripts/cpra_dedup.py` (deduplication module)

---

## 1. Goal and Scope

Bring CPRA building permit data 2023-2025 (~14,143 raw permits → ~5,000-7,000 master permits after deduplication) into v2 so it can be queried alongside existing project, permit, and event data. The import enables APR-style reconciliation and ongoing refresh from future CPRA responses.

### In scope
- Decide how CPRA permits map into v2's schema
- Decide how to handle CPRA permits matching v1 projects vs unmatched
- Decide how to preserve master/sub-permit structure
- Build a repeatable import script
- Apply on the 2023-2025 dataset
- Validate against existing v2 data

### Not in scope (later phases)
- Importing the upcoming 2018-2022 CPRA (will reuse the same script when delivered)
- Per-permit BMR/income tagging (CPRA does not have it; needs supplementary source)
- Itemized fee data (CPRA shows aggregate "Total Paid" only, often empty)
- Cross-reference with NotebookLM-corrected APR (separate analysis layer)

---

## 2. Source data summary

From `data/apr/cpra_2023_2025_comparison.md`:

- 14,143 raw rows across 26 columns
- ~5,000-7,000 distinct master permits after deduplication (`scripts/cpra_dedup.py`)
- Sub-permits inherit master\'s UnitsAdded — leads to 6x unit inflation if not deduped
- Headers at row 8; rows 1-7 are title/blank
- Covers Jan 2023 – Dec 2025, filtered by Issuance Date (includes older permits issued in window)

Key columns available:
PermitNumber, Submittal Date, Issuance Status, Issuance Date, Finaled Status, Finaled Date, Completed, Completed Date, Parcel Number, StreetNumber, StreetName, StreetType, JobValuation, WorkDescription, ADU, Detached, Work Type, OccType, SubType, NumberUnits, UnitsAdded, UnitsRemoved, CO Required

Missing from CPRA: applicant/contractor name, total fees assessed, per-permit BMR designation, parent permit reference (will be in next CPRA request).

---

## 3. Open Decision 1: Which CPRA permits to import?

Three real options. Plan recommends Option B.

- **Option A:** All 14,143 raw rows verbatim. No information loss but adds schema bloat and sub-permit noise.
- **Option B:** Deduplicated master permits only (~5-7K). Clean queryable surface; matches analytical questions. Loses sub-permit history (recoverable from source file).
- **Option C:** Hybrid — master permits in `permits` table; raw rows in separate `cpra_permits_raw` table. Best of both, more complexity.

**Recommendation: Option B for tonight; preserve raw file path in documentation. If we need sub-permit detail later, we re-run dedup against the source file.**

---

## 4. Open Decision 2: How to link to v2 projects

CPRA permits fall into three buckets based on the analysis:

- Matches existing v1 project by APN: ~324 permits. Insert with `project_id` set to existing project.
- Matches existing v1 project by fuzzy address: ~30-50 permits. Same as above, with provenance flag.
- No v1 project match: ~13,800 permits. See sub-decision below.

For unmatched CPRA permits:

- **Option 2a:** Create one v2 project per master permit. Maximally complete but floods v2 with single-permit "projects" (ADU additions, etc.).
- **Option 2b:** Create v2 projects only for multi-unit (UnitsAdded >= 5). Adds the ~64 R-2 master permits as projects. Conservative; preserves v1\'s curated nature.
- **Option 2c:** Import all CPRA without project link (`permits.project_id` NULLABLE). Most flexible; schema change required.

**Recommendation: Option 2b. Import master permits matching v1 projects (~324) + add new v2 projects for R-2 master permits with UnitsAdded >= 5 (~41 from earlier finding). Other CPRA permits stored in raw CPRA reference table only.**

---

## 5. Open Decision 3: Sub-permit structure

v2\'s current `permits` table has no `parent_permit_id` column. Sub-permits relate to master permits in CPRA via shared APN and permit number patterns (e.g., `-REV`, `-DEF` suffixes).

- **Option 3a:** Drop sub-permits. Simplest; matches Option B above. Lose audit trail for sub-permit dates.
- **Option 3b:** Add `parent_permit_id` column. Schema change + import all. Preserves full structure.
- **Option 3c:** Store raw CPRA in separate reference table. Sub-permits live in `cpra_permits_raw`; masters go to `permits`.

**Recommendation: Option 3a. Drop sub-permits on import. The `scripts/cpra_dedup.py` module identifies them via suffix patterns; we just don\'t store them. If sub-permit history matters later, we re-run from the source file.**

---

## 6. Open Decision 4: Event generation

Each CPRA master permit issuance is an event in v2\'s `project_events` table.

- Submittal Date → `application_submitted` event (per permit; many will duplicate v1\'s project-level events)
- Issuance Date → `building_permit_issued` (or `demo_permit_issued` for demolitions). The core APR data point.
- Finaled Date (= CO) → `co_issued` event. Per Berkeley\'s "finalized" terminology.
- Completed Date → only if non-null and different from Finaled Date (rare per sampling).

**Recommendation: Generate `building_permit_issued` (or demo equivalent) for each master permit. Generate `co_issued` events only when Finaled Date is present and Finaled Status indicates completion. Skip `application_submitted` events from CPRA to avoid duplicating v1\'s events — those came from a different scrape with richer status data.**

---

## 7. Open Decision 5: Conflict handling with v1-migrated permits

v2 has 118 permits already (from v1 migration). Some of these will be the same permits CPRA delivers, but with possibly different field values.

- **Option 7a:** Replace. When CPRA permit_number matches existing v2 permit, replace v2\'s fields with CPRA\'s.
- **Option 7b:** Skip. Keep v2\'s existing record; ignore CPRA\'s.
- **Option 7c:** Append. Insert CPRA as a new permit row; let queries dedupe.
- **Option 7d:** Field-by-field merge. For each field, prefer non-null CPRA value over existing.

**Recommendation: Option 7d, field-by-field merge with provenance tracking. CPRA is more authoritative for issuance/final dates and valuations; v1 may have richer description/status text from its different scrape. Record `source_system=cpra` for CPRA-sourced fields.**

---

## 8. Proposed schema changes

Based on the recommendations above, minimal schema changes needed:

- None to `permits` if we drop sub-permits (Option 3a)
- None to `project_events` for event generation
- Possibly add `parcels.notes` flag for parcels created from CPRA-only sources (no v1 history)

If we relax recommendations:

- Adding `parent_permit_id` to `permits` would require schema migration (Option 3b)
- Making `permits.project_id` NULLABLE would require schema migration (Option 2c)

Plan keeps tonight\'s schema unchanged. Future iterations can add columns as needed.

---

## 9. Workflow steps

Once decisions are confirmed:

1. Read deduplicated CPRA using `scripts/cpra_dedup.py`
2. Identify import candidates:
   - Master permits matching v1 projects by APN → existing project_id
   - R-2 master permits >=5 units not matching v1 → create new v2 project rows
   - Everything else → skip (for v2) but preserve in raw CPRA file
3. For each import candidate:
   - INSERT into `permits` with provenance fields populated
   - INSERT into `project_events` for issuance event
   - INSERT into `project_events` for CO event if Finaled Date present
   - If field-level merge with existing v2 permit: UPDATE with CPRA fields where non-null
4. Validate:
   - Permit count delta makes sense (start: 118; expect: ~450 after import)
   - Event count delta makes sense
   - No FK violations
   - Stale projects from `data/apr/v1_staleness_assessment_2026-05-10.csv` now have CPRA-sourced events

---

## 10. Empirical sections — CC tasks

Before executing, CC should empirically verify:

### 10a. How many CPRA master permits actually exist after dedup?
- Run `cpra_dedup.py` on the source file
- Report total master permits, breakdown by year, breakdown by Work Type

**Results:**

| Metric | Count |
|--------|-------|
| Total raw CPRA rows | 14,149 |
| Master permits (no -REV/-DEF/-ADD) | 12,186 |
| Sub-permits | 1,963 |
| Master permits 2023-2025 | 10,856 |

**By Year (master permits):**

| Year | Count |
|------|-------|
| 2016 | 2 |
| 2017 | 8 |
| 2018 | 16 |
| 2019 | 34 |
| 2020 | 46 |
| 2021 | 189 |
| 2022 | 1,013 |
| 2023 | 3,586 |
| 2024 | 3,567 |
| 2025 | 3,703 |
| 2026 | 4 |

**By Work Type (top 7):**

| Work Type | Count |
|-----------|-------|
| Alteration | 10,336 |
| (blank) | 511 |
| New | 468 |
| Addition/Alteration | 431 |
| Addition | 224 |
| Demolition | 169 |
| Sign | 47 |

**By OccType (top 5):**

| OccType | Count |
|---------|-------|
| R-3 (1-2 unit residential) | 9,627 |
| R-2 (3+ unit residential) | 1,688 |
| Not Applicable | 376 |
| U (Garages, Sheds, etc.) | 262 |
| undefined | 123 |

### 10b. How many master permits map to existing v1 projects?
- For each master permit, find matching v1 project by APN (use cleaned-up v2.parcels.apn now that audit is partial-complete)
- Report match counts: exact APN match, fuzzy address match, no match

**Results (2023-2025 master permits only):**

| Match Type | Permits |
|------------|---------|
| Exact APN match | 110 |
| Fuzzy address match (≥90%) | 592 |
| No match | 10,154 |
| **Total** | **10,856** |

**Unique v1 projects with CPRA matches:** 130 of 179 (73%)

**Unmatched permits by OccType:**

| OccType | Count |
|---------|-------|
| R-3 (1-2 unit) | 8,127 |
| R-2 (3+ unit) | 1,272 |
| Not Applicable | 351 |
| U (Garages, etc.) | 210 |
| undefined | 118 |

**Unmatched permits with UnitsAdded > 0:** 289
- of which R-2: 23

**Note:** The high fuzzy match count (592) reflects address normalization catching permits where v1 has the project but APN differs or is missing. The 10,154 unmatched permits are primarily R-3 single-family work not tracked in v1.

### 10c. Which CPRA permits >=5 units don't match v1?
- The 5 "genuinely missing" R-2 projects from prior analysis
- Verify each is still genuinely missing (run again, in case APN audit affected matching)

**Results:**

Deduplicated R-2 projects (2023-2025): 64
- with UnitsAdded ≥ 5: 37
- NOT matching v1 (by APN or fuzzy address): **5 projects, 48 units**

| Permit | Address | Units | Year |
|--------|---------|-------|------|
| B2022-05957 | 2328 CHANNING Way | 13 | 2024 |
| B2025-03731 | 2012 CHANNING Way | 11 | 2025 |
| B2024-05284 | 2307 PIEDMONT Ave | 10 | 2025 |
| B2024-04593 | 2235 HEARST Ave | 8 | 2024 |
| B2025-00168 | 2330 BLAKE St | 6 | 2025 |

**Prior "genuinely missing" status check:**

| Permit | Prior Status | Current Status |
|--------|--------------|----------------|
| B2018-03255 | Missing | Now matches v1 (fuzzy address) |
| B2022-05957 | Missing | Still missing (13 units) |
| B2021-04907 | Missing | Not in ≥5 units dataset (3 units) |
| B2022-01345 | Missing | Not in ≥5 units dataset (3 units) |
| B2020-01168 | Missing | Not in ≥5 units dataset (2 units) |

**Conclusion:** Only 5 R-2 projects with ≥5 units are genuinely missing from v1. These are candidates for new v2 project creation per Section 4 recommendation.

### 10d. How do CPRA's Finaled Date/Status map to v2 events?
- Sample 30 CPRA permits with Finaled Status = "Finaled" — what dates do they have?
- Sample 30 permits with Finaled Status = (blank) — what is their state?

**Results:**

**Finaled Status distribution (all master permits):**

| Finaled Status | Count |
|----------------|-------|
| Finaled | 9,613 |
| (blank) | 2,573 |

**Finaled Date presence:**

| Condition | Count |
|-----------|-------|
| Has Finaled Date | 8,996 |
| Missing Finaled Date | 3,190 |

**Sample: 30 permits with Finaled Status = "Finaled":**
- All have Finaled Date populated (with rare exceptions)
- Finaled Dates range from 2023 to 2025
- Mix of R-2 and R-3 OccTypes
- Example: B2017-02610 finaled 2023-08-10, B2014-05752 finaled 2025-05-22

**Sample: 30 permits with Finaled Status = (blank):**
- All have blank Finaled Date
- These are permits issued but not yet finalized (construction in progress or abandoned)
- Example: B2017-04296 issued 2018-06-25, still not finaled

**Anomaly check:** 0 permits have Finaled Date present but Finaled Status ≠ "Finaled"

**CO Event Mapping Recommendation:**
1. Generate `co_issued` event when: Finaled Status = "Finaled" AND Finaled Date is not null
2. Use Finaled Date as the event date
3. Skip permits with blank Finaled Status or missing Finaled Date
4. **Applies to 8,996 master permits**

### 10e. Conflict count: how many CPRA permits already exist in v2.permits?
- Match by permit_number; report counts and sample conflicts
- For 5-10 sample conflicts, show v2's current fields vs CPRA's fields

**Results:**

| Metric | Count |
|--------|-------|
| v2 permits total | 118 |
| v2 building permits (B-prefix) | 16 |
| v2 planning permits (ZP, DRCF, DRCP) | 102 |
| **v2 permits matching CPRA** | **0** |
| CPRA master permits | 12,186 |

**Finding: No conflicts exist.**

v2's current permits are primarily planning permits (ZP, DRCF, DRCP prefixes) from the v1 migration. CPRA contains only building permits (B-prefix). The 16 v2 building permits do not overlap with CPRA's permit numbers.

**v2 building permit samples (not in CPRA):**

| Permit | v2 Issued |
|--------|-----------|
| B2025-05534 | (blank) |
| B2025-05535 | (blank) |
| B2015-02460 | (blank) |
| B2016-01435 | (blank) |
| B2019-05657 | (blank) |

**Implications for import:**
1. No field-level merge needed (Section 7 Option 7d) — there are no conflicts
2. All CPRA permits can be inserted as new rows
3. v2's existing permits are from different data sources (planning pipeline vs building permits)
4. Consider whether v2's planning permits should link to CPRA building permits for the same projects (by project_id, not permit_number)

**Empirical fill completed: 2026-05-10**

---

## 11. Open Questions for Human Decision

- Which CPRA permits to import? (Section 3): A / B / C
- How to link unmatched permits? (Section 4): 2a / 2b / 2c
- Sub-permit structure? (Section 5): 3a / 3b / 3c
- Event generation rule? (Section 6): see recommendation
- Conflict handling? (Section 7): 7a / 7b / 7c / 7d
- Run import all at once or in batches? Single transaction vs per-project transactions
- What to do about UC projects? They have no APN, will be excluded from CPRA matching; need separate decision

---

## 12. Status and next actions

**Status:** Plan drafted. CC empirical fills pending.

**Next action:** Hand to CC with the 5 prompts in section 10 to fill in empirical sections.

**After empirical fill:** Review with human, lock decisions, draft import script.

**After import:** Run validation queries. Update `cpra_2023_2025_comparison.md` with post-import state.

---

## 13. Future phases (one paragraph each)

### Phase 2: Historical CPRA 2018-2022 import
The second CPRA request (drafted 2026-05-10) covers 2018-2022. Once delivered (~10 days based on prior turnaround), re-run the same import script. Expect ~25,000-35,000 raw rows. Same deduplication and merge logic should apply.

### Phase 3: Per-permit BMR/income tagging
Neither v1 nor CPRA has affordability data per permit. To match Berkeley\'s APR by income category, we need a supplementary source: City staff records, density bonus filings, or manual review of staff reports. Build a workflow to attach affordability to specific permits.

### Phase 4: Automated CPRA refresh
Berkeley turned around the request in 10 days. If CPRA becomes a periodic ask (e.g., quarterly), the import script becomes the foundation of an ongoing refresh workflow. No automated scraping needed — just periodic CPRA + scripted import.

### Phase 5: APR query layer
Once CPRA is integrated, build canned queries against v2 that reproduce APR Tables A, A2, B by year. Compare to NotebookLM-corrected APR; identify and document discrepancies.

---

*Drafted 2026-05-10. Phase 1 of 5.*


---

## 14. Decisions Locked 2026-05-10

After empirical fill of Section 10, decisions confirmed:

| Decision | Locked Option | Notes |
|----------|---------------|-------|
| §3 Which permits to import | **Option B** — deduplicated master permits only | ~12,186 master permits available; we import a subset (see §4) |
| §4 How to link to v2 projects | **Option 2b-relaxed** — import permits matching v1 projects (702) PLUS create 5 new R-2 projects ≥5 units (48 units) and import their permits | ~707 permits total |
| §5 Sub-permit structure | **Option 3a** — drop sub-permits on import | Recoverable from source file if needed |
| §6 Event generation | building_permit_issued per master permit; co_issued when both Finaled Status AND Finaled Date present | 8,996 of 12,186 will generate co_issued events |
| §7 Conflict handling | **Moot** — empirical fill found zero overlap between v2 and CPRA permits | No merge logic needed |
| Run order | Single transaction with savepoints per batch of 100 permits | Allows partial rollback if validation fails mid-import |
| UC projects | **Excluded from this import** | 4 UC projects have no APN/parcel; defer to schema decision (separate work) |

### Locked import scope

- **Permits to insert:** ~707 CPRA master permits
  - 110 exact APN match to v1 projects → existing project_id
  - 592 fuzzy address match to v1 projects (≥90% similarity) → existing project_id with provenance flag
  - ~5 R-2 master permits ≥5 units not matching v1 → new v2 projects + linked permits
- **Permits to skip:** ~11,479 unmatched master permits (mostly single-family/ADU)
  - Source file remains the canonical reference for these
  - Can be revisited later if scope expands beyond housing pipeline

### New v2 projects to create (the 5 R-2 from §10c)

Pending CC empirical confirmation of the current 5-project list after APN audit:
- B2022-05957: 2328 Channing Way (13 units, largest)
- (4 others from prior analysis, possibly updated by APN audit work)

CC should re-verify the 5 projects against current v2 state before insert.

### Events to generate

- 707 `building_permit_issued` (or `demo_permit_issued`) events — one per master permit
- ~520 `co_issued` events — for permits with Finaled Status AND Finaled Date (proportional to the 8,996/12,186 ratio applied to 707)
- Skip `application_submitted` events — v1 already has these from a richer scrape

### Validation queries (post-import)

1. Permit count: was 118, expect ~825 (118 + 707 new). Verify count.
2. project_events count: should grow by ~1,200 (707 + ~520).
3. FK integrity: PRAGMA foreign_key_check must return empty.
4. project_id integrity: no permits should have NULL project_id (the 5 new projects must be inserted before their permits).
5. Staleness check: v1_staleness_assessment STALE projects should now have CPRA-sourced events. Re-run staleness logic, expect STALE count to drop substantially.
6. Conflict check: no two permits with the same permit_number in v2.permits.

### Out of scope for this import (deferred)

- The 11,479 unmatched master permits — raw file remains canonical
- The 4 UC projects without parcels — schema decision needed
- Per-permit BMR/income tagging — needs supplementary source
- Itemized fees — not in CPRA data
- The 1,963 sub-permits — recoverable from source if needed

---

## 15. Next Steps After Decision Lock

1. **CC drafts import script** based on locked decisions in §14
   - Script path: `scripts/migration/import_cpra_2023_2025.py`
   - Idempotent (safe to re-run; uses INSERT OR IGNORE patterns)
   - Logs to `scripts/migration/logs/cpra_import_YYYY-MM-DD.log`
2. **Human reviews script** before any execution
3. **Test run** on subset (5-10 permits) with rollback verification
4. **Full run** in single transaction
5. **Validation queries** as listed above
6. **Update `cpra_2023_2025_comparison.md`** with post-import state
7. **Commit to dev branch**

*Decisions locked 2026-05-10 19:XX:XX. Pending CC script draft.*


---

## 16. Plan Revisions 2026-05-10 (post-Q19 verification)

After CC re-verified the 5 missing R-2 projects (data/apr/cpra_2023_2025_comparison.md §Q19), two changes to the locked plan in §14:

### Revision 1: Fuzzy matching threshold tightened

**Original §14:** "fuzzy address match (≥90% similarity)" used for project linking.

**Revised:** Require **exact StreetNumber match** AND fuzzy StreetName match (≥90% similarity on street name only). This prevents false positives like B2018-03255 (2527 San Pablo) wrongly matching v2 project #16 (2720 San Pablo).

**Implication:** Some of the 592 "fuzzy address matches" from §10b may not pass the tighter rule. Import script must re-run matching with tightened logic and report final counts before any inserts.

### Revision 2: New v2 projects reduced from 5 to 2

CC verified that of 5 R-2 master permits ≥5 units not matching v2, only 2 are genuine new construction:

| Permit | Address | Units | Valuation | Verdict |
|--------|---------|------|-----------|---------|
| B2022-05957 | 2328 CHANNING Way | 13 | $3.89M | Genuine — Luttrell House restoration + 13 new units |
| B2025-00168 | 2330 BLAKE St | 6 | $1.98M | Genuine — 6 ADUs in single permit |

The other 3 (B2025-03731 water heater, B2024-05284 wood repair, B2024-04593 reroof) have UnitsAdded reflecting existing building size, not new construction — confirmed by low valuations ($2K-$56K).

**Implication:** Import creates 2 new v2 projects, not 5. Expected new v2 projects: 2 with 19 total units.

### Revised import scope

- **Permits to insert:** approximately 700-710 CPRA master permits (depending on tightened matching results)
  - Exact APN matches to v1/v2 projects: 110
  - Tightened fuzzy address matches (exact street number + fuzzy street name): TBD by CC empirical re-run, expected <592
  - 2 new R-2 projects + their permits
- **New v2 projects:** 2 (down from 5)
- **Validation thresholds adjusted accordingly** — permit count will be slightly less than the ~825 originally projected

*Plan revisions locked 2026-05-10.*

---

## 17. Final Import Scope (2026-05-12)

After dry-run verification and Q20 investigation, final adjustments before live import:

### Project 93 Exclusion (All Match Types)

Project 93 (1312 ADDISON St) is excluded from **ALL match types** (both APN and fuzzy). Rationale:

1. **Wrong v1 APN:** Project 93's v1 APN (056199300100) was incorrect — it actually points to **2200 Acton St**, an unrelated single-family home, not 1312 Addison
2. **False-positive APN matches prevented:** Without this exclusion, 3 permits at 2200 Acton would incorrectly link to project 93:
   - B2023-01651: 5.2kW solar installation at 2200 Acton
   - B2024-05921: re-roof at 2200 Acton
   - B2025-00577: solar remove-and-reinstall at 2200 Acton
3. **Address ambiguity:** Berkeley ArcGIS shows no parcel for "1312 ADDISON" — only "1314 ADDISON". The 1312 appears to be a sub-unit designation of the 1314 parcel (duplex)
4. **Non-housing permit:** The only CPRA permit at "1312 ADDISON" (B2023-06383) is an electrical meter upgrade, not housing construction
5. **Borderline scope:** Project 93 itself is a 0-unit attic addition (ZP2024-0125), borderline housing pipeline scope

**Action:** Import script checks `EXCLUDE_PROJECTS = {93}` and skips **both** APN matches and fuzzy matches to these projects with logged reason.

**Future work:** When project 93's correct APN is determined and corrected in v2, remove the exclusion and re-run import to pick up any legitimate permits.

### Fuzzy Matching Limitation

Even with tightened matching (exact StreetNumber + fuzzy StreetName ≥90%), semantically wrong matches can occur when:
- v2 project address is a sub-unit of a larger parcel
- CPRA permit is at same address but for non-housing work (electrical, roofing, etc.)
- Both match on address but represent different scopes

**Recommendation for future imports:** Consider adding description-text similarity filters or permit-type filters (skip electrical/plumbing-only permits) to reduce false positives.

### Final Import Counts

| Metric | Count |
|--------|-------|
| Exact APN matches | 118 (121 - 3 false positives at 2200 Acton) |
| Tightened fuzzy matches | 1 (project 173 at 2000 DWIGHT only) |
| New R-2 projects | 2 |
| Excluded (project 93) | 4 permits (3 APN + 1 fuzzy) |
| **Total permits to insert** | **121** |

### Validation Thresholds (Updated)

| Table | Before | After | Delta |
|-------|--------|-------|-------|
| v2.permits | 118 | 239 | +121 |
| v2.projects | 179 | 181 | +2 |
| v2.project_events | ~proportional growth based on issuance + CO events |

*Final scope locked 2026-05-12.*
