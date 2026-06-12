# Session Summary — 2026-05-29

## Headline

Today landed three D5 fixes in two distinct workstreams: the parcel-collapse
fix (CY 2018-2025), and the Causes 2 and 3 fix (Alteration/Demolition
negative-master floor plus tightened ADU classification). Combined with
yesterday's Cause 1 (REV summation) fix, CY 2024 D5 reproduction moved from
497 CO / 238 BP at session start to **643 CO / 576 BP** — closing the gap
against Berkeley's reported 708 CO / 731 BP from ~30% to **9% (CO)** and
**21% (BP)**. Nine commits shipped to `origin/dev` across two pushes, plus
a forward-revert sequence to clean up a stowaway-file slip in mid-session.

## What shipped to origin/dev today

### Push 1 — parcel-collapse fix (3 commits)
- **`2f7b8a7`** `docs(audit)` — parcel-collapse diagnostic for 2026-05-29
  session. Documents the 14 same-year sibling parcels, the rejected
  cross-year cases (Durant/Euclid false positives), and the same-year
  gating design decision.
- **`3d9171d`** `fix(d5)` — Cell 5: treat sibling New-construction permits
  on the same parcel as separate masters when ≥2 same-year New-with-units
  permits exist. Gated by same-year to avoid Durant temp-power inheritance.
- **`ff8ff7a`** `feat(d7)` — regenerate 8-year reconciliation ledgers post
  parcel-collapse fix. D7 notebook + per-year README.md + matched_pairs.csv
  + cross_year_summary.csv.

### Push 2 — Causes 2/3 fix, with forward-revert sequence (6 commits)
- **`2acc568`** `docs(audit)` — Causes 2 and 3 diagnostic. Per-year tables
  showing 502 negative-master Alteration/Demolition rows across 8 years
  (-1,278 BP / -789 CO) and the over-broad ADU classification (843
  adu_flagged in CY 2025, ~700+ non-New rows in CY 2024).
- **`9f19a46`** `docs(audit)` — 8-matched-case residual divergence
  observation. **SLIPPED**: included a stowaway `cy2024/matched_pairs.csv`
  from an earlier `git checkout <ref> -- <path>` that staged the file in
  the index. Caught pre-push; preserved in history per the visible-correction
  rule.
- **`2beaa9d`** Revert of `9f19a46` — forward-revert (not history rewrite)
  that preserves the slip in the audit trail.
- **`ae3f905`** `docs(audit)` — clean re-apply of the 8-matched-case
  observation. Single-file commit; staged set verified before commit.
- **`9592159`** `fix(d5)` — Cell 14: (a) floor at 0 for Alteration/
  Demolition/Addition-Alteration masters with `bp_units < 0`; (b) tighten
  `is_adu` to require `Work Type == "New"`.
- **`17719b4`** `feat(d7)` — regenerate 8-year reconciliation ledgers post
  Cause 2/3 fix. 14 ledger files (c_unmatched + matched_pairs per affected
  year). `cross_year_summary.csv` byte-identical to ff8ff7a — the fix is
  value-based, not membership-based.

Verify: `git log --oneline origin/dev | head -12`.

## Numeric impact summary

**Parcel-collapse fix**: +22 BP units recovered across 8 years. 14 same-year
sibling parcels promoted to separate masters (2018: 2; 2019: 2; 2020: 1;
2022: 1; 2024: 4; 2025: 4). One unit-neutral de-match in CY 2024 (1614 Sixth
re-wire alteration no longer cosmetically matched to HCD row 1301).

**Causes 2/3 fix**: +1,278 BP and +789 CO across 8 years. 502 Alteration/
Demolition negative-units masters floored at 0; ~1,428 ADU-flagged rows
(700 in CY 2024 + 728 in CY 2025) reclassified from `UNIT_CAT='ADU'` to
`SFD` or `2-4` as appropriate (pure relabeling; bijection membership
unchanged).

### Per-year D5 post-all-fixes vs HCD reported

Source: `output/D5/table_a2_CY{2018..2025}.csv` + `output/D7/cross_year_summary.csv`.

| year   | D5 CO | D5 BP | HCD CO | HCD BP | gap CO  | gap BP  |
|--------|-------|-------|--------|--------|---------|---------|
| CY2018 |    52 |   234 |    229 |    380 |   +177  |   +146  |
| CY2019 |   238 |   222 |    313 |    363 |    +75  |   +141  |
| CY2020 |    31 |   530 |    405 |    766 |   +374  |   +236  |
| CY2021 |   342 |   412 |    331 |    506 |    −11  |    +94  |
| CY2022 |   420 |   484 |    828 |    887 |   +408  |   +403  |
| CY2023 |   353 |   509 |    716 |    432 |   +363  |    −77  |
| CY2024 |   643 |   576 |    708 |    731 |    +65  |   +155  |
| CY2025 |   525 |   329 |    481 |    444 |    −44  |   +115  |
| TOTAL  | 2,604 | 3,296 |  4,011 |  4,509 | +1,407  | +1,213  |

CY 2024 is the validated end-to-end bijection target; remaining gaps in
earlier years reflect that pre-CY 2024 bijection coverage has not been
constructed and the systematic fixes (parcel-collapse, REV summation,
Cause 2/3) have not been audited against per-row HCD evidence outside
CY 2024. Two notable inversions: CY 2025 CO D5 exceeds HCD by 44 (worth
examining as a potential D5 over-count or year-routing artifact), and
CY 2023 BP D5 exceeds HCD by 77 (similar question).

## CY 2024 reconciliation, end state

- **Berkeley HCD submission**: 708 CO units, 731 BP units, 228 rows
- **D5 post-all-fixes**: 643 CO, 576 BP
- **CO gap**: 65 units (9%) — attributed to ABAG ADU income-tier
  methodology gap (deferred), HCD finer per-structure granularity beyond
  CPRA evidence (12 Case-2 multi_row parcels), year-routing methodology
  shift, and smaller scattered choices
- **BP gap**: 155 units (21%) — similar attribution, with the
  parcel-collapse + Cause 2 floor accounting for most of the recovery
  vs. yesterday's 493-unit gap
- **100% of HCD's reported 708 CO and 731 BP** remain accounted for at
  row level across the matched/multi_row/year_shifted/no_cpra_presence
  buckets (the bijection's invariant from yesterday holds).

## 4 confirmed under-reports persist

From the parcel-collapse and Causes 2/3 fix work, no new under-reports
surfaced; the four CY 2024 cases remain as documented yesterday:

- **2328 Channing Way** — 12 units (5+ category)
- **2512 Regent Street** — 9 units (5+ category, CO-only)
- **2028 Essex Street** — 1 unit (ADU)
- **707 Cragmont Avenue** — 1 unit (SFD, CO-only)

All four appear in CPRA-released permit data but not in any year of
Berkeley's HCD submission. Confirmed via tracking ID, APN, and address
cross-checks. Persist in `c_unmatched.csv` for CY 2024.

## Discipline patterns earned or reinforced today

1. **CC summaries can be wrong; verify artifacts** — yesterday's lesson,
   reinforced today by the morning verification catching that the user's
   handoff note described 2 pending commits but they had already landed.
2. **Diagnostic docs precede the fix commits that reference them** —
   never "forthcoming companion commit." The fix commit's reference to
   the doc must resolve at commit time.
3. **Regression test baselines update in the same commit as the code
   they test** — D7 Cell 12 baseline was refreshed alongside ff8ff7a so
   the test reflects the post-parcel-collapse state, not pre-.
4. **Predictions are imprecise; actual pipeline measurements are
   authoritative** — today's prediction-table conflation lesson: CO vs BP
   routing, gross vs net units, expected vs observed bijection shifts.
   If a prediction doesn't match measurement, investigate the prediction
   first before declaring failure.
5. **Same-year gating essential for sibling rules** — the Durant temp-power
   pattern (B2024-06011 inherited UnitsAdded=83 from its associated
   building permit) and the 1182 Euclid garage replacement showed
   cross-year sibling application produces false positives that
   contaminate unit totals.
6. **`git checkout <ref> -- <path>` stages the file in the index, not just
   the working tree** — today's 9f19a46 slip. The stale-in-index
   `matched_pairs.csv` rode along with an unrelated doc commit. Always
   check the index, not just the working tree.
7. **Always `git diff --cached --name-only` before every commit** — direct
   consequence of #6; the only reliable defense against staged-set drift.
8. **Visible correction over silent rewrite for committed-but-unpushed
   mistakes** — today's 9f19a46 → 2beaa9d → ae3f905 sequence preserves
   the slip in history rather than amending it away. Audit trail beats
   tidiness.
9. **Phase A read-only investigation precedes Phase B implementation** —
   the Causes 2/3 fix was characterized across all 8 CY years before any
   D5 code changed. The per-year tables in the diagnostic doc became the
   verification target post-fix.
10. **Working tree standing collateral — leave alone unless explicitly
    in scope** — D6 notebook M-state, `data/apr/2024/*`, `2026-05-28.md`,
    `data/apr/2024/developer_summary_2024.csv`, `notes/cc_prompts/`. All
    persisted across both pushes; the discipline of not committing them
    speculatively kept the commits surgical.

## Forensic findings from the repo-size investigation

Phase A inventory ran this afternoon. Headline:

- **`.git`: 553 MB, 3,020 loose objects, 0 packs.** `git gc` has never
  run (or ran early enough to be overridden). Loose-object zlib overhead
  is recoverable; delta compression on already-compressed video/PDF
  blobs is minimal.
- **Total blob bytes in history: 849 MB across 1,317 blobs.** Top 30
  blobs account for 83%; top 100 account for 91%. Heavy concentration
  in a small number of large files.
- **Dead historical versions of `docs/berkeley-flyover.mp4`**: 5 distinct
  blobs (76 / 70 / 59 / 45 / 21 MB) totaling **258 MB** still in `.git`.
  Working tree only holds the `.backup-2026-05-03` (76 MB); the other 4
  are gone from HEAD but persist in pack-less history.
- **Three overlapping `data/reference/alameda_lookup_*` CSVs** totaling
  **145 MB tracked** (lookup_complete 59M, address_lookup_normalized
  51M, lookup_corrected 35M) — likely evolving versions of one
  address-to-parcel dataset.
- **`site-by-site/` PDFs**: 120 MB across 3 entitlement-filing PDFs, all
  tracked.
- **`docs/videos/*.mp4`**: 100 MB tracked via the `!docs/videos/*.mp4`
  exception in `.gitignore` (intentional, for deployed tour videos).
- **Working tree footprint**: 1.55 GB excluding `.git`; 440 MB of that
  is tracked large files (>5 MB).

**Clone traffic in the last 14 days**: 492 clones from 176 unique cloners,
but only 1 unique web visitor in the same window. Pattern consistent with
automated/bot cloning; human attention is negligible. **History-rewrite
cost is therefore essentially zero** — invalidating clones costs us
nothing measurable.

Theoretical floor for clone size after a full cleanup (deduplicate
alameda lookups, externalize PDFs and videos, remove dead flyover
history, `git gc`): estimated **~50 MB**, down from current 553 MB.
Workstream details in tomorrow's priming doc.

## What's deliberately deferred

- **ABAG ADU income-tier distribution (Q5)** — D5 lumps all units into
  `ABOVE_MOD`; HCD distributes ADUs 30/30/30/10 across affordability tiers.
  Separate workstream; needed for column-by-column reconciliation but not
  for unit totals.
- **Cross-year siblings (~5 units across 3 parcels)** — Carleton (2u 2024
  + 1u 2025), 2310 Eighth (1u 2023 + 1u 2024), 2411 Sixth (1u 2023 + 1u
  2024). All are genuine siblings per text analysis, but cross-year
  application is contaminated by the Durant/Euclid false-positive pattern;
  requires per-row vetting workstream.
- **Year-routing convention decision** — D5 routes BP by issuance year, CO
  by finaled year; HCD appears to use entitlement year for some routing
  (6 CO / 4 BP units in CY 2024 land in adjacent years in D5). Decide and
  document before it compounds across cycles.
- **98 Avenida parcel-level ADU flagging boundary case** — both the SFR
  and the detached ADU classify as `UNIT_CAT='ADU'` because CPRA's ADU
  flag is parcel-level. The Cause 3 fix (Work Type filter) doesn't
  resolve this because both permits are `Work Type='New'`. Per-permit
  ADU evidence would be needed.
- **v2 cutover** (Datasette serving v2 directly) — separate multi-week
  workstream; not a quick task.
- **`main` fast-forward** — `main` is now **19 commits behind dev** (13
  from yesterday + 6 from today). Deferred decision; the website still
  runs on v1-derived data, so no rush, but the deferral should be
  conscious.

## Next session priorities

See `docs/audit/2026-05-29_next_session_priming.md`.
