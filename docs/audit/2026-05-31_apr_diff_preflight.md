# APR v1-vs-v2 Diff Pre-flight — 2026-05-31

**Purpose:** Before the APR pilot diff (`generate_apr.py` on v1 vs
`generate_apr_v2.py` on v2), classify format/representation differences between
the two sources so each APR diff can be labeled **artifact** vs **real change**.

**Sources:** v1 = `berkeley_housing_analysis.db` `projects` (179 rows, frozen ~Apr 22);
v2 = `berkeley_housing_v2.db` `v_projects_flat` (181 rows). Read-only; sampled
actual stored values. Internal disk only — untouched external drives / copy.

---

## Headline

**The representation artifacts the diff might have produced are largely ABSENT —
the differences are real.** Date *format* matches (both ISO), NULL handling
matches (no sentinels), unit types match. The APR diff will be dominated by
**legitimate date-value changes** (enrichment + the known MIN/MAX anchor
semantic) plus **+2 new projects** and a **deliberate status recoding** — not by
format noise. So most diffs are signal, not artifact.

---

## Stage 1 — Date formats: FORMAT MATCHES, VALUES DIFFER (real)

All date columns are **ISO `YYYY-MM-DD` in both** — no MM/DD/YYYY, no Excel
serials. So format is *not* a diff source. But per-project **values** differ:

| Column pair (v1→v2) | # projects differing | Breakdown |
|---|---|---|
| `filed` → `filed_date` | 3 | minor |
| `entitled` → `entitled_date` | 19 | anchor/enrichment |
| `bp_issued` → `bp_issued_date` | **51** | 36 enrichment + 15 anchor-semantic + 0 regressions |
| `co_date` → `co_issued_date` | **30** | 25 enrichment + 5 anchor-semantic |

**Two distinct real causes:**
1. **Enrichment** (36 bp, 25 co): v1 was NULL/blank, v2 has a date (CPRA import +
   reconciliation populated dates v1 lacked). These projects will **move into**
   an APR year bucket. *Real improvement, not regression.*
2. **Anchor-semantic** (15 bp, 5 co): both populated but different — v1 values are
   **month-floored** (`2022-11-01`, `2024-10-01`) while v2 has real day-precision
   dates in a different period (`2025-09-08`, `2025-07-07`). This is the known
   v2 **MIN/MAX `event_date` anchor** change: v2 picks a different permit event.
   *Intentional semantic change.* Example: project 117 `2022-11-01` → `2025-09-08`.

**Implication for APR:** Table A2 (BP/CO-permitted-in-year) counts will shift
**substantially and legitimately** between v1 and v2. Do NOT dismiss date diffs
as artifacts — they're real and directly re-bucket projects by year.

## Stage 2 — NULL / empty / sentinel: CLEAN, matches

No `''` empties or `'None'`/`'N/A'` string sentinels in either source — both use
real `NULL`. Counts align:

| Column | v1 nulls | v2 nulls | Note |
|---|---|---|---|
| units / total_units | 0 | 2 | the 2 nulls = the +2 new projects |
| status / status_label | 0 | 0 | — |
| owner / owner_current | 150 | 152 | 152 = 150 + 2 new |
| address_display | 0 | 0 | — |

**Not a diff source.** (Both clean; the only delta is the +2 projects.)

## Stage 3 — Numeric types: one artifact (`height_feet`)

| Column | v1 type | v2 type | Diff |
|---|---|---|---|
| units / total_units | integer | integer | ✅ match |
| vli_units | integer | integer | ✅ match |
| **height_feet** | **integer** (200) | **real** (200.0) | ⚠️ format artifact |

`height_feet` renders `200` (v1) vs `200.0` (v2). **Artifact** — but APR
Tables A/A2/B don't surface height, so likely irrelevant to the APR diff
specifically. Flag in case any height appears.

## Stage 4 — Status strings: DELIBERATE RECODING (22 → 8)

v1 carries **22 distinct free-text Accela statuses**; v2 collapses them into **8
normalized vocabulary labels**:

| v1 (free-text, 22 values) | → | v2 (vocab, 8 values) |
|---|---|---|
| Under Review (42), In Review (17), Corrections/Incomplete/Resubmittal Pending, ZAB Review, Amendment Pending… | → | **In Review (78)** |
| Approved (15), Pending Final Action (11), Entitled (16) | → | **Entitled (34)** |
| Building/Demolition Permits Filed | → | **Permitted (14)** |
| Completed (17) | → | **Completed (37)** |
| Under Construction (10), Demolition Underway | → | **Under Construction (6)** |

**Deliberate representation change**, not data corruption. If the APR output
surfaces a status string, expect systematic recoding diffs — categorize as
artifact-of-normalization. (APR year-bucketing is date-driven, so status text
may not affect table counts directly.)

## Stage 5 — Row-set alignment: stable key, +2 rows

- Counts: **v1 = 179, v2 = 181** (+2).
- **Join key is stable:** v1 `id` == v2 `project_id`, same projects (1=1750
  Sacramento, 2=2276 Shattuck, 3=2700 Shattuck…).
- **The +2 (v2-only):** `project_id 183 = 2328 CHANNING Way`, `184 = 2330 BLAKE St`.
  These appear as **added** rows (with NULL units) — expected, not a regression.

---

## Stage 6 — Pre-flight diff classification

| Diff category | Cause | Expected? | How to recognize | Verdict |
|---|---|---|---|---|
| **Date enrichment** | v2 populated dates v1 lacked (36 bp, 25 co, some entitled) | **YES** | v1 null/blank → v2 has date; project enters a year bucket | REAL improvement |
| **Date anchor-semantic** | v2 MIN/MAX event-date vs v1 month-floored (15 bp, 5 co) | **YES (known)** | both have dates, differ; v1 often day=`01` | INTENTIONAL |
| **+2 projects** | v2 has 183 (2328 Channing), 184 (2330 Blake) | **YES** | rows only in v2; null units | EXPECTED add |
| **Status recoding** | 22 free-text → 8 vocab labels | **YES** | status column collapses to vocab set | ARTIFACT (deliberate) |
| **height_feet int→real** | type change (200 vs 200.0) | YES *if* surfaced | systematic `.0` suffix | ARTIFACT (likely N/A to APR) |
| Date **format** | — | **NO** | both ISO `YYYY-MM-DD` | NOT a diff source |
| NULL / sentinel | — | **NO** | both real NULL, no `''`/`None` | NOT a diff source |
| units/vli **type** | — | **NO** | both integer | NOT a diff source |
| **REAL unexpected data diff** | actual correction in v2 | **MAYBE — investigate** | none of the above patterns | **THE SIGNAL** |

### How to read the APR diff
Because format/NULL/type are NOT diff sources, **nearly every APR diff should
trace to one of: date enrichment, date anchor-semantic, the +2 rows, or status
recoding.** Anything that does *not* fit those four categories — especially a
unit-count change or a project shifting year-bucket with no underlying date
change — is the **real signal to investigate.**

---

## Validation rules (APR methodology, sourced from HCD instructions)

These rules govern how our totals are compared to the City's APR. Several
expected divergences are **methodology**, not error — label them as such.

1. **Group-quarters exclusion.** Student housing, dormitories, and bunkhouses
   **cannot** be counted as HCD housing units. Our database includes 4 major
   student-housing projects (~5,250 beds) that the City's APR excludes. When
   comparing to the City APR, student-housing **beds-counted-as-units are an
   EXPECTED divergence, not an error.** Report **beds** and **HCD-units** as
   **separate, labeled metrics — never blend them.**

2. **Student-housing bed→unit approximation.** We currently approximate
   **2 beds = 1 unit**. This is a rough default; actual ratios vary by type
   (apartment-style ~4:1, dorm-style ~1:1). Where plan-set data gives actual
   bed **and** unit counts (e.g. 2190 Shattuck), **use the actuals, not the 2:1
   approximation.**

3. **ELI accounting change.** Pre-2025, **ELI is a SUBSET of VLI**; for 2025,
   **ELI is ADDITIVE** at the summary level. **2024-vs-2025 BMR comparisons must
   account for this** or they will double- or under-count the lowest income band.

4. **ADU affordability is modeled, not observed (2025+).** ABAG methodology
   **assigns** ADU affordability by formula (30% VLI / 30% LI / 30% Mod / 10%
   Above-Mod) rather than measuring it. **2025+ ADU income breakdowns are
   modeled, not observed** — treat them as estimates, not ground truth.

5. **Multi-year reporting is prescribed.** HCD instructions state the same
   project **should** appear across years as it moves entitlement → permit → CO.
   **Appearance in multiple years is NOT double-counting.** Reissued building
   permits are permissible **if flagged as reissuances**. This reframes the
   NotebookLM "BMR double-count" finding — much of it is **legitimate
   stage-progression**, not error. (Pair with the master-permit-only rule:
   genuine double-counting is summing REV sub-permits, not cross-year appearance.)

---

*Diagnostic + methodology reference. No DB or script modified; Task 1 (assessor
bedroom inventory) was read-only.*
