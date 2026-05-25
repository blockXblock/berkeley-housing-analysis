# url_discovery_queue: insert 15 B-permits (permitted stage)

**Generated:** 2026-05-22T23:14:45
**Scope:** transactional INSERT of 15 B-prefix permits (project stage `permitted`, no v2 `source_url`, not already in the queue) into canonical `databases/cic_recon_queue.db`.

## 1. Pre-insert state

| field | value |
|---|---|
| Canonical SHA256 (pre) | `e2df093913c83ffd12eb6249548aa6e98f3629a54058015d690e228990739b3e` |
| `url_discovery_queue.succeeded` | 90 (today's URL discovery results, untouched) |
| `url_discovery_queue.pending` (pre) | 0 |
| `scrape_queue.succeeded` (pre) | 92 (untouched throughout) |

Note on canonical SHA: it changed from `29258f2f…` (after the morning scrape_queue → pending update) to `e2df0939…` between then and now — consistent with the inspection orchestrator having been run by the user against the 90 pending permits, all 92 of which are now `succeeded` in `scrape_queue`. This insert is independent of that run; it only adds new rows to `url_discovery_queue`.

## 2. The 15 permits identified

Selection criteria (matches the Workstream D definition in `/tmp/overnight_candidate_set.md`):

- `permit_number LIKE 'B%'`
- `source_url IS NULL OR source_url = ''`
- project's `current_stage_type_id` maps to `vocabulary_stage_types.code = 'permitted'`
- `permit_number NOT IN (SELECT permit_number FROM scrape_queue WHERE status='succeeded')`

| v2 permit_id | permit_number | project_id | stage | address |
|---|---|---|---|---|
| 217 | B2022-04987 | 60 | permitted | 1464 SIXTH St |
| 199 | B2022-05881 | 32 | permitted | 1740 SAN PABLO Ave |
| 238 | B2022-05957 | 183 | permitted | 2328 CHANNING Way |
| 218 | B2024-02508 | 60 | permitted | 1464 SIXTH St |
| 186 | B2024-04964 | 113 | permitted | 2138 KITTREDGE St |
| 239 | B2025-00168 | 184 | permitted | 2330 BLAKE St |
| 136 | B2025-00820 | 163 | permitted | 0 PARKER St |
| 209 | B2025-01579 | 72 | permitted | 5 W PARNASSUS Ct |
| 214 | B2025-02361 | 131 | permitted | 811 Cedar |
| 215 | B2025-02795 | 131 | permitted | 811 Cedar |
| 211 | B2025-04241 | 132 | permitted | 1627 Jaynes St |
| 216 | B2025-04363 | 131 | permitted | 811 Cedar |
| 210 | B2025-04912 | 67 | permitted | 1419 GRANT St |
| 133 | B2025-05247 | 85 | permitted | 1730 PARKER St |
| 212 | B2025-05288 | 132 | permitted | 1627 Jaynes St |

Cross-project clustering worth noting:

- Project 131 (811 Cedar): **3 permits** (B2025-02361, B2025-02795, B2025-04363)
- Project 60 (1464 SIXTH St): 2 permits (B2022-04987, B2024-02508)
- Project 132 (1627 Jaynes St): 2 permits (B2025-04241, B2025-05288)
- 8 other distinct projects with 1 permit each

## 3. Backup

| field | value |
|---|---|
| Path | `databases/cic_recon_queue_pre_15_b_permits_2026-05-22.db` |
| Size | 86,016 bytes |
| SHA256 | `e2df093913c83ffd12eb6249548aa6e98f3629a54058015d690e228990739b3e` |
| Matches canonical pre-state SHA256 | yes ✓ |

## 4. Insert operation

Single SQLite transaction. For each of the 15 permits:

```sql
INSERT INTO url_discovery_queue
  (permit_id, permit_number, status, attempts, created_at)
VALUES (?, ?, 'pending', 0, ?)
```

`created_at` = `2026-05-22T23:13:29.259214` (UTC ISO timestamp at insert time).

Per-statement assertion: `rowcount == 1`. Total inserted: **15** (assertion passed).

In-transaction post-checks:

- `url_discovery_queue` counts: `{'pending': 15, 'succeeded': 90}` ✓
- Anchor row check (B2019-05575, one of today's succeeded): byte-identical to pre-insert snapshot — `id=1, permit_id=244, status='succeeded', attempts=1, output_file='/tmp/url_discovery_pre_flight/B2019-05575.json'` ✓
- `scrape_queue` counts unchanged: `{'succeeded': 92}` ✓

Transaction COMMITTED.

## 5. Post-insert state

| field | value |
|---|---|
| Canonical SHA256 (post) | `9e10de060351e352105b0c6710d5187cfbe7ef18b3d13434cfe260f6f25fead2` |
| `url_discovery_queue` total | 105 (was 90) |
| `url_discovery_queue.succeeded` | 90 (unchanged) |
| `url_discovery_queue.pending` | 15 (new) |
| `scrape_queue` total | 92 (unchanged) |
| `scrape_queue.succeeded` | 92 (unchanged) |

New row IDs: 91 through 105 (incremental from the existing 90 succeeded rows that occupied ids 1-90).

## 6. Sample post-insert rows

| queue id | v2 permit_id | permit_number | status | attempts | created_at |
|---|---|---|---|---|---|
| 91 | 217 | B2022-04987 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 92 | 199 | B2022-05881 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 93 | 238 | B2022-05957 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 94 | 218 | B2024-02508 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 95 | 186 | B2024-04964 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 96 | 239 | B2025-00168 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 97 | 136 | B2025-00820 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 98 | 209 | B2025-01579 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 99 | 214 | B2025-02361 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 100 | 215 | B2025-02795 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 101 | 211 | B2025-04241 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 102 | 216 | B2025-04363 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 103 | 210 | B2025-04912 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 104 | 133 | B2025-05247 | pending | 0 | 2026-05-22T23:13:29.259214 |
| 105 | 212 | B2025-05288 | pending | 0 | 2026-05-22T23:13:29.259214 |

All 15 rows: `status='pending'`, `attempts=0`, `last_attempt_at` / `error_message` / `output_file` / `succeeded_at` all NULL. Ready for the URL discovery orchestrator.

## 7. Verdict

**PASS** — 15 rows inserted as expected, no duplicates, no constraint violations, the 90 already-succeeded rows are byte-identical to their pre-insert snapshot, `scrape_queue` untouched. Safety net: `databases/cic_recon_queue_pre_15_b_permits_2026-05-22.db` preserves the pre-insert state.

Inserted permit_numbers (one-line list):

B2022-04987, B2022-05881, B2022-05957, B2024-02508, B2024-04964, B2025-00168, B2025-00820, B2025-01579, B2025-02361, B2025-02795, B2025-04241, B2025-04363, B2025-04912, B2025-05247, B2025-05288
