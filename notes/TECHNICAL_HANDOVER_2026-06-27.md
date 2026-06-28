# TECHNICAL HANDOVER — 2026-06-27 (on-disk ground truth)

CC's on-disk complement to chat-Claude's strategy handover (`notes/HANDOVER_2026-06-27.md` — being
bridged in by John; ⚠ not on disk as of this commit, so don't fail if it's absent). Everything below
is **verified against the actual repo this session** (commands in §6 reproduce it). **Where this and the
strategy handover disagree, DISK WINS** — discrepancies flagged inline with ⚠.

---

## 1. GIT STATE (verified)
- **dev HEAD = `aa6ded0`** — "refactor(housing_rules): lift v4 classify out of build_jn_c cell-string
  into importable permit_role". ✅ This IS the classifier-lift commit.
- **`dev` is AHEAD of `origin/dev` by 1 commit → aa6ded0 is NOT pushed.** (`git status -sb` → `## dev...origin/dev [ahead 1]`.)
- **Files in commit `aa6ded0` (7, all tracked):**
  `scripts/housing_rules/permit_role.py` (new), `scripts/housing_rules/test_permit_role.py` (new),
  `scripts/housing_rules/__init__.py` (M), `scripts/v4/build_jn_c.py` (M),
  `scripts/v4/build_jn_d.py` (**new — committed**), `notebooks/v4/JN-C_classify.ipynb` (M, regenerated),
  `PROGRESS.md` (M).
- **Untracked, NOT gitignored (this session's prototypes — candidates for a future commit):**
  `scripts/v4/prototype_score_v2.py`, `scripts/v4/prototype_score_v2_cc.py`, `scripts/v4/prototype_score_v3.py`.
- **`scratch/` is gitignored** → everything under `scratch/2026-06-26/` and `scratch/2026-06-27/`
  (all sizing scripts, diagnostics, CSVs, the footprint cache) is throwaway/work-in-progress, never committed.

⚠ **DISCREPANCY vs the task framing:** `scripts/v4/build_jn_d.py` was described as "scratch/untracked".
DISK: it is **tracked and committed in aa6ded0**. (`build_jn_c.py` likewise tracked.) Only the three
`prototype_score_*` scripts are untracked.

---

## 2. THE CLASSIFIER LIFT (commit aa6ded0) — verified
- `scripts/housing_rules/permit_role.py` (143 lines) + `scripts/housing_rules/test_permit_role.py` (76 lines) **exist**.
- **25 anchored tests PASS NOW** (`python -m scripts.housing_rules.test_permit_role` →
  "ALL 16+9 permit_role TESTS PASS").
- **Behavior-identity proof: PASSED at lift-time, harness now STALE.** When run during the lift it reported
  **0 mismatches over all 85,793 events** (classify + net_units identical old-vs-new) and role-distribution
  exact. ⚠ **`scratch/2026-06-27/permit_role_identity_proof.py` no longer re-runs** — it raises
  `KeyError: 'classify'` because it exec-extracts the OLD cell-string `classify` from
  `notebooks/v4/JN-C_classify.ipynb`, and the lift **regenerated that notebook to IMPORT classify (not
  define it)**. The old comparand is gone by design. **Durable re-verify of the lift = the 25 tests +
  the role-distribution check (§below), both re-runnable.** Do NOT trust the proof harness as-is.
- **JN-C role distribution from the current committed `event_classifications` (verified):**
  `alteration 64,739 · subsidiary 9,597 · ambiguous 7,403 · new_unit 2,964 · demolition 920 · non_housing 170`
  (sum 85,793). Unchanged from pre-lift → the lift altered no classification.

---

## 3. ARTIFACT INVENTORY (verified paths + counts)

### Committed code (aa6ded0)
- `scripts/v4/build_jn_d.py` — **the JN-D engine** (HCD-anchored ADU bijection + 704-split + 584 harden +
  dedup/band + inverse). **5 HARD asserts: 842 / 649 / 839 / 584 / 531-584.** Verified: runs end-to-end,
  `match 839/842`, `UNIT BAND 531..584`. GIS address-point oracle 404s (non-fatal by design; Imps +
  footprint oracles load). Writes CSVs to `scratch/2026-06-26/jn_d_out/`.
- `scripts/v4/build_jn_c.py` — generator for `notebooks/v4/JN-C_classify.ipynb`; now imports+renders
  classify (does not define it); output path fixed to the real repo path.

### Untracked prototypes (scripts/v4/, calibration — NOT persisted)
- `prototype_score_v2.py` (JN) and `prototype_score_v2_cc.py` (CC) — the two independent two-axis scorers
  (reconciled at ρ=0.90 adu / 0.85 new_housing). Each → `scratch/2026-06-27/prototype_scores_v2{,_cc}.csv` (1966 rows).
- `prototype_score_v3.py` — **CURRENT** reconciled scorer (the 4 decisions baked in) →
  `scratch/2026-06-27/prototype_scores_v3.csv` (1966 rows). **Throwaway calibration instrument** (no DB write).

### Gitignored scratch (work-in-progress)
- `scratch/2026-06-27/four_corrections_sizing.py` — **KEEP-RESULTS** (the §4 magnitude table).
- `scratch/2026-06-27/apr_full_state_check.py` — **KEEP-RESULTS** (the full-APR v4-vs-city table).
- `scratch/2026-06-27/footprint_join_diag*.py`, `old_adu_vocab_gap.py`, `reconcile_v2.py`,
  `permit_role_identity_proof.py` (stale), `capfees_probe.py`, `adu_surface_probe*.py` — diagnostics.
- `scratch/2026-06-27/prototype_scores*.csv` (4 × 1966 rows) — **throwaway** calibration output.
- `scratch/2026-06-26/jn_d_adu_bijection.csv` (3,175 rows), `relabel_hardened.csv` (977; `jnc_role=='new_unit'`
  = the **584**), `dedup_584.csv` (584), `split_704.csv` (2,946) — **encode results we reuse.**
- `scratch/2026-06-26/jn_d_out/` — 4 CSVs: `jn_d_bijection_oracled.csv`, `jn_d_704_split.csv`,
  `jn_d_inverse.csv`, `jn_d_relabel_queue.csv`.
- **`scratch/2026-06-26/jn_d_out/_oracle_cache/footprints.json` — 36,091 outlines / 24,613 distinct
  canonical parcels. SHARED CACHE: build_jn_d, all three prototypes, and the footprint diagnostics
  reuse it as the footprint oracle. Don't delete — re-pulling is a live GIS hit.**

---

## 4. THE FOUR-CORRECTIONS APR SIZING — ⚠ CORRECTED 2026-06-28 (C1 is a PHANTOM)

> **⚠ CORRECTION (2026-06-28):** the original sizing below listed **C1 (584 ADU relabel) = +457** as an
> additive correction. **That was WRONG — C1 is a PHANTOM (already-counted units).** Verified this session:
> all 584 have `current_housing_role=new_unit` and their 441 finaled masters **already carry net_units
> (≈457 units) that are already in the 3,066 baseline.** A C1 write would **double-count +457.**
> **WHY (preserve the lesson):** the hardening pass re-ran the SAME `classify` that JN-C had already
> materialized into `event_classifications`, so its "584 new_unit verdicts" were permits **already
> classified new_unit — confirmations, never relabel targets.** *Lesson: a "relabel queue" derived by
> re-running the committed classifier finds already-correct classifications, not gaps.* (Review:
> `scratch/2026-06-28/c1_relabel_review.py`.)

**Corrected table (C1 struck):**
```
correction                  +/-   units   status            depends-on
C1  584 ADU relabel         ❌    +457   PHANTOM — already counted in 3,066; DO NOT WRITE (double-count)
C2  multifam count-gap      +CO  +1,036  ✅ DONE (commit 5d8fcdd, both tranches)   desc-regex (1 Accela)
C3  phantom-master          −CO    −163  pending   building-identity (1951 Shattuck)
C4  BP reporting-year       ~0        0  pending   reporting-year map (timing axis)
```

**Corrected reconciliation (C2 + C3 + C4 — NOT C1+C2+C3+C4):**
```
3,066  (baseline — ALREADY includes the ~457 C1 ADUs)
 + C2 +1,036  (DONE)          = 4,102   (+80 vs city 4,022)
 − C3   −163  (Shattuck, pending) = 3,939   (−83 vs city 4,022)
 C4 = BP timing axis (separate)
```
So with **only C2 done and C3 pending**, CO is within ~±83 of the city's 4,022. **C2 was the real lever**
(it WAS bigger than the relabel — the relabel just wasn't a lever at all).

**C2 detail (as written, commit 5d8fcdd):** 20 buildings / **+1,036 units**. Tranche 1 = 15 permits /
907 pure-dwelling (incl. compound 159+11 townhomes; consistency 37=34+1+2; duplex word). Tranche 2 = 5
permits / 129 convention-flagged (live-work+sleeping, `convention_dependent=true` in basis_note;
B2021-04949=41). Audit: `docs/audit/2026-06-28_c2_tranche{1,2}_write.md`.

**C3 detail:** **−163 from 1951 Shattuck alone** (`057-2046-001-00`, two 163-unit permits B2019-05608 +
B2021-04893, finaled CY2024). Full multi-master upper bound −231; non-Shattuck remainder tiny (−1…−4,
small-ADU duplicates → #3 review). **C4:** v4_BP 4,911 vs city 4,531 (+380, ~8%); ~67% year-reassignment,
~33% true excess → an alignment problem, not magnitude.

**Full-APR baseline (v4 vs city filed, all housing):** cumulative **CO v4 3,066 vs city 4,022 (−956 before
C2)**; **BP v4 4,911 vs city 4,531 (+380)**. (City CY2024 CO=708, BP=734.) The original "−956 → +1,036 to
recover" framing over-counted by treating C1 as additive; the −956 was effectively all C2 + the C3 over-years.

---

## 5. VERIFIED vs ASSUMED (be explicit)
- **(a) Committed + tested:** the classifier lift — `permit_role.py` + `test_permit_role.py` (25/25 pass),
  re-export via `housing_rules`, role distribution unchanged. On dev, **unpushed**.
- **(b) Verified-but-uncommitted-as-results:** JN-D engine *code* is committed (aa6ded0) and its 5 asserts
  pass, but its *outputs* are scratch CSVs. The four-corrections sizing + full-APR state check are scratch
  scripts, re-runnable, numbers verified this session (§4). The ADU bijection (839/842), 704-split, 584
  harden, band 531-584 — verified, scratch.
- **(c) Prototype / calibration (settled but NOT persisted):** the two-axis scorer (v3 current) and its
  **5 settled decisions** (medium band kept; weak-only→low; pre-2017 terms behind a creating-context
  guard; D4 regressions hold; bound `adu≤new_housing`). **No D5 / persisted scorer / notebook built yet.**
- **(c.1) DONE since this handover:** **C2 multifamily count-gap — committed `5d8fcdd`** (both tranches,
  +1,036, APR CO −956 → +80). ~~C1 584 relabel~~ — **CANCELLED: phantom (already counted), see §4.**
- **(d) NOT done (carried forward):** **C3 phantom-master / 1951 Shattuck** (−163) + general #3
  building-identity (incl. B2020-03895, the 102 of-584 on 49 multi-permit ADU parcels); **C4 BP
  reporting-year** realignment; **C2 mini-cleanup (gated, NOT a relabel):** 9 finaled masters within the
  584 with net_units 0/NULL (undercount *within* the counted set) + 2 stored-vs-desc mismatches
  (B2023-02975 stored-12/desc-11, B2024-00819 stored-2/desc-1); **OPEN INVESTIGATION — the REAL ADU
  recall gap** (if any) lives in the OTHER bijection buckets (`v4_adu_flag_nonhousing_role` 328, etc.),
  NOT the 584 — that's where a genuine relabel would have targets (not yet sized); the **curriculum
  notebooks**; the June-25 parcel-identity model (ADR-003); a capacity JN; discrepancy-framing; **push dev**.

---

## 6. RE-VERIFY COMMANDS (don't trust this doc — re-run)
```bash
cd ~/berkeley-data
# git state
git log --oneline -1                       # expect aa6ded0
git status -sb                             # expect: ## dev...origin/dev [ahead 1]
# the lift (durable checks; the proof harness itself is stale — see §2)
python3 -m scripts.housing_rules.test_permit_role     # expect ALL 16+9 PASS
sqlite3 'file:databases/berkeley_housing_v4.db?mode=ro' \
  "SELECT housing_role,COUNT(*) FROM event_classifications GROUP BY 1 ORDER BY 2 DESC;"  # the 6 counts
# JN-D engine (5 HARD asserts; crashes if any fail)
python3 scripts/v4/build_jn_d.py           # expect match 839/842, band 531..584, HEADLINE
# the sizing + state check (the §4 numbers)
python3 scratch/2026-06-27/four_corrections_sizing.py   # NOTE: prints "C1 +457" but that is the PHANTOM
                                                        # (already-counted; see §4). Real: C2 +1,036(done)/C3 -163.
                                                        # C1-phantom verified by: python3 scratch/2026-06-28/c1_relabel_review.py
python3 scratch/2026-06-27/apr_full_state_check.py      # expect CO 3066 vs 4022, BP 4911 vs 4531
# current scorer
python3 scripts/v4/prototype_score_v3.py   # 1966 rows; D1-D4 confirms
```

---

## 7. KEY PATHS / FACTS confirmed this session (a fresh CC needs these)
- **events date column = `event_date`** (NOT `occurred_at` — the build_jn_d bug fixed this session).
- **classifier:** `from housing_rules.permit_role import classify` (or `housing_rules.classify`), signature
  `classify(work_type, description, adu_flag, occtype, units_added, units_removed, permit_number) ->
  (role, is_master, note)`; companion `net_units(units_added, units_removed, role, description="")`.
  Per-event field mapping JN-C uses: `wt=Work Type`, `d=raw_description or WorkDescription`, `adu=ADU`,
  `occ=OccType`, `ua=UnitsAdded`, `ur=UnitsRemoved`, `permit=source_record_key`.
- **Canonical APN:** `housing_rules.to_canonical_apn(raw,'Alameda')` → Option-B (`052-1433-010-00`).
- **Footprint oracle:** Berkeley GIS `https://gis.cityofberkeley.info/arcgis/rest/services/Planning/
  Building_Safety/MapServer/7` ("Building Outlines"), field **`PARCELID`** in space-form
  `book(3)+' '+page(4)parcel(3)sub(2)` (e.g. `060 241705600`); `>=2` outlines = positive-only ADU
  corroboration (footprint=1 is 44.6% false on real detached ADUs → NEVER dissent). Cache reused at
  `scratch/2026-06-26/jn_d_out/_oracle_cache/footprints.json` (24,613 parcels).
- **HCD oracle (verification target only, never a source):** `databases/hcd_apr_mirror_2026-06-17_fresh.db`,
  `table_a2` (ADU rows: `UNIT_CAT='ADU'`; CO totals = sum `CO_*` cols, BP = sum `BP_*`, by `YEAR`).
- **Assessor:** `databases/berkeley.db` `parcels(APN, Imps, …)` — `Imps` = improvement-value oracle.
- **Canonical pipeline DB:** `databases/berkeley_housing_v4.db` (85,793 events; `events` +
  `event_classifications`). v3/v2 frozen reference.
```
