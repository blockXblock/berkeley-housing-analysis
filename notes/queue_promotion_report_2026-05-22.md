# Queue promotion: url_discovery_queue from /tmp/ to canonical

**Generated:** 2026-05-22T17:13:27
**Scope:** add the `url_discovery_queue` table + 90 succeeded rows to `databases/cic_recon_queue.db`, preserving `scrape_queue` unchanged.

## 1. Pre-promotion inventory

| DB | size | sha256 | tables (rows) |
|---|---|---|---|
| `/tmp/cic_recon_queue_url_discovery.db` (working) | 61,440 B | `11d9ce20fffc0ebf8821af60836e23226fb46987c783c1c34b2aab1d8de4d5ed` | scrape_queue (92), url_discovery_queue (90) |
| `databases/cic_recon_queue.db` (canonical, pre) | 32,768 B | `2efdbab7e12a7930d45f3392c87deb7d387d1a80f9d36682529cc2e7c2253393` | scrape_queue (92) — NO url_discovery_queue |

**scrape_queue divergence check:** `/tmp/` and canonical scrape_queue rows compared by `(id, permit_number, status)` — **identical, no divergence**.

## 2. Backup

| field | value |
|---|---|
| Path | `databases/cic_recon_queue_pre_url_discovery_2026-05-22.db` |
| Size | 32,768 bytes |
| SHA256 | `2efdbab7e12a7930d45f3392c87deb7d387d1a80f9d36682529cc2e7c2253393` |
| Matches canonical pre-state SHA256 | yes ✓ |

## 3. Promotion operation

Single-transaction Python sqlite3 promotion (after a first attempt via `ATTACH DATABASE` hit an unexpected lock on the working DB; the first attempt's transaction rolled back cleanly — canonical SHA was unchanged afterward, verified, then retried via cursor read + `executemany` write, which does not require ATTACH).

Operations performed in the committed transaction:

1. `CREATE TABLE IF NOT EXISTS url_discovery_queue (...)` — same shape as the working DB:

```sql
CREATE TABLE url_discovery_queue (
    id INTEGER PRIMARY KEY,
    permit_id INTEGER NOT NULL,
    permit_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    error_message TEXT,
    output_file TEXT,
    created_at TEXT NOT NULL,
    succeeded_at TEXT,
    UNIQUE(permit_id)
)
```

2. `CREATE INDEX IF NOT EXISTS idx_url_discovery_status ON url_discovery_queue(status)` plus auto-created `sqlite_autoindex_url_discovery_queue_1` for the UNIQUE constraint.
3. `executemany(INSERT INTO url_discovery_queue (...) VALUES (?, ?, ...))` with all 90 rows read from `/tmp/`, preserving original `id` values.
4. Post-INSERT in-transaction verification: 90 total rows / 90 status='succeeded' / 92 scrape_queue rows unchanged byte-for-byte.
5. COMMIT.

## 4. Post-promotion canonical state

| field | value |
|---|---|
| Tables | `scrape_queue`, `url_discovery_queue` |
| `url_discovery_queue` total | 90 |
| `url_discovery_queue` status breakdown | `succeeded: 90` |
| `scrape_queue` total | 92 |
| `scrape_queue` status breakdown | `pending_url_discovery: 90`, `succeeded: 2` |
| `url_discovery_queue` indexes | `sqlite_autoindex_url_discovery_queue_1` (UNIQUE permit_id), `idx_url_discovery_status` |
| Canonical SHA256 (post-promotion) | `6cc8416c490eb364b29db8aa24a8aa6dd5e80a84599e5f873e1ded90fee1c4ae` |

Sample of inserted rows (first 3 by id):

```
(1, 'B2019-05575', 'succeeded', 1, '/tmp/url_discovery_pre_flight/B2019-05575.json')
(2, 'B2021-02225', 'succeeded', 1, '/tmp/url_discovery_pre_flight/B2021-02225.json')
(3, 'B2021-02404', 'succeeded', 1, '/tmp/url_discovery_pre_flight/B2021-02404.json')
```

## 5. /tmp/ working DB state check

| field | value |
|---|---|
| `/tmp/cic_recon_queue_url_discovery.db` SHA256 (post-promotion) | `11d9ce20fffc0ebf8821af60836e23226fb46987c783c1c34b2aab1d8de4d5ed` |
| Matches pre-promotion SHA256 | yes (unchanged) ✓ |
| url_discovery_queue rows | 90 succeeded |
| scrape_queue rows | 92 (pending_url_discovery: 90, succeeded: 2) |

## 6. Observation worth flagging (NOT acted on)

- `url_discovery_queue.output_file` paths: **3** rows point to `/tmp/url_discovery_pre_flight/*.json` (the 3 pre-flight smoke-test permits whose JSONs lived in /tmp/, not the canonical path); **87** rows point to `data/raw/accela_url_discovery/*.json` (canonical). The 3 /tmp/ paths are historical pointers that won't survive a `/tmp/` cleanup or machine restart. The canonical JSONs for those 3 permits exist at the canonical path too (they were re-processed by the pre-flight and the post-fix runs against the canonical output dir), so the actual data isn't at risk — but a strict ingest later would want to either rewrite those 3 `output_file` values to the canonical paths or accept the inconsistency.

## 7. Verdict

**PASS** — canonical `databases/cic_recon_queue.db` now contains the `url_discovery_queue` table with 90 succeeded rows; `scrape_queue` is preserved byte-identical (verified by row-tuple equality in-transaction); `/tmp/` working DB is unchanged; backup is intact and matches the pre-promotion canonical SHA256.

Safety net: `databases/cic_recon_queue_pre_url_discovery_2026-05-22.db` is the rollback target if anything downstream surfaces a problem with the promoted state.
