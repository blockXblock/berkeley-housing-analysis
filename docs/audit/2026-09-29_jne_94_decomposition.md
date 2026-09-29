# JN-E's 94-unit gap, decomposed (2026-09-29)

**Question.** JN-E asserts that its waterfall of documented correction steps sums to the derived
completions. Since 2026-09-26 the steps summed to 4,229 while derived completions were 4,323, so the
assert failed. What moved the 94?

**Method (read-only).** Per-permit diff of counted completions (finaled `new_unit` master, `net_units > 0`)
between `keep_snapshot_2026-09-26_pre-v4-rebuild.db` (4,229, all in 2018–25) and
`keep_snapshot_2026-09-28_pre-v4-evidence-rebuild.db` (4,323; 4,072 in 2018–25). Every changed permit
is assigned to exactly one step; the per-permit table is `2026-09-29_jne_94_decomposition_permits.csv`
(columns: units before/after, final dates, finaled-event state and reading note after, step).

**Result: +94 = +251 − 157.**

| Step | Permits | Units |
|---|---|---|
| New 2026 window (completions finaled 2026-01-01..07-07, from the July productions) | — | +251 |
| Group quarters under HCD definitions: 2000 Dwight 113, 2100 San Pablo 96, GLA `B2021-02423` 40 (1 manager's unit kept), GLA `B2019-02693` 1 | 4 | −250 |
| Not a new unit: solar and electrical permits for ADUs, sheds, garages, a workspace, ADU sub-permits, alterations | 49 | −49 |
| Phase rule: 1951 Shattuck's 163 move from Phase 1 `B2019-05608` to Phase 2 `B2021-04893` (same final date, 2024-10-24) | 2 | 0 |
| Logan Park South Phase I `B2019-05575` counted beside Phase II (a double count the rebuild introduced) | 1 | +69 |
| Count corrections, incl. Building A `B2018-02291` 14 → 6 (the old count gave Building A the whole 14-unit project while Buildings B and C were counted too) | 7 | −6 |
| Newly recognized units: ADUs and conversions read as alterations/ambiguous before, a 7-unit landmark conversion, a renewal, a completion permit | 55 | +79 |
| **Net** | 118 | **+94** |

**Checks made on the doubtful cases.** 1951 Shattuck: the carrier (Phase 2) is counted, so the move nets to
zero. Building A: Buildings B (`B2019-02831`, 4) and C (`B2019-02824`, 4 live-work) are counted separately,
so the new 6 is right and the old 14 double-counted 8. `B2024-05916` ("Renew old permit B2017-02937"):
the 2017 permit is not in the data, so the renewal counts the 5 once. `B2017-05275` completes work under
`B2014-04083`, which carries no count, so the 4 are counted once.

**Since then (2026-09-29 write):** Dwight +88 (unit plans), Logan Park South Phase I −69 (`phase_carried`):
+19 → 4,342. Baseline `reconciliation_baseline_2026-09-29b.json` carries all steps; they sum to 4,342.

**Open, not part of the gap:** `B2014-01391` finaled twice (2021, 2026), 2 units each, counted twice.
