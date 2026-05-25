# url_discovery_queue build report

**Generated:** 2026-05-22T07:45:07
**Scope:** /tmp working copy of `databases/cic_recon_queue.db`. The canonical DB was NOT modified by this prompt.

## 1. Working DB and SHA256

| field | value |
|---|---|
| Source DB | `databases/cic_recon_queue.db` |
| Working DB | `/tmp/cic_recon_queue_url_discovery.db` |
| Source SHA256 (pre-write) | `2efdbab7e12a7930d45f3392c87deb7d387d1a80f9d36682529cc2e7c2253393` |
| Working SHA256 (after table create + 90 inserts) | `35efc06bff8cf1a30ed58a6d9c82b5192609891e397d1783af6742c89801013f` |

After Step 0 (copy) the two SHAs were identical. The working SHA changed after Step 1 (table) and Step 5 (90 inserts). The source SHA above is whatever `databases/cic_recon_queue.db` is at report time — this prompt did not touch it.

## 2. Schema change applied (on working DB only)

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

Indexes:

- `idx_url_discovery_status`: `CREATE INDEX idx_url_discovery_status
      ON url_discovery_queue(status)`
- Plus auto index for the `UNIQUE(permit_id)` constraint (`sqlite_autoindex_url_discovery_queue_1`).

Status code semantics (documentation only — no CHECK constraint):

| status | meaning |
|---|---|
| `pending` | to be discovered |
| `running` | orchestrator currently working on it |
| `succeeded` | URL found, JSON written |
| `failed` | transient error, retry possible |
| `not_found` | permit does not exist in Accela (permanent) |
| `ambiguous` | multiple records match query (defer to manual review) |

## 3. Script

- Path: `scripts/build_url_discovery_queue.py`
- Line count: 236
- Executable: yes (chmod +x)

## 4. --help output

```
usage: build_url_discovery_queue.py [-h] [--queue-db QUEUE_DB] [--v2-db V2_DB]
                                    [--dry-run] [--limit LIMIT] [-v]

Build the url_discovery_queue from v2 in-scope B-permits.

options:
  -h, --help           show this help message and exit
  --queue-db QUEUE_DB  Path to queue database (default:
                       databases/cic_recon_queue.db)
  --v2-db V2_DB        Path to v2 database (default:
                       databases/berkeley_housing_v2.db)
  --dry-run            Count rows that would be inserted; do not write.
  --limit LIMIT        Enqueue at most N permits (default: unlimited).
  -v, --verbose        Verbose logging (DEBUG level).
```

## 5. Dry-run output (from Step 4 of this build)

```
2026-05-22 07:45:07,355 INFO v2 database: databases/berkeley_housing_v2.db
2026-05-22 07:45:07,355 INFO Queue database: /tmp/cic_recon_queue_url_discovery.db
2026-05-22 07:45:07,355 INFO Dry run: True
2026-05-22 07:45:07,356 INFO Querying v2 for in-scope B-permits...
2026-05-22 07:45:07,363 INFO v2 returned 90 in-scope permits
2026-05-22 07:45:07,363 INFO WOULD insert: 0  Skipped (already in queue): 90
2026-05-22 07:45:07,364 INFO url_discovery_queue total rows: 90
2026-05-22 07:45:07,364 INFO   pending: 90
```

Notes: Step 4 was the original dry-run against an empty `url_discovery_queue`. It reported `WOULD insert: 90, Skipped: 0`. The verbatim block above is from a re-run of the same command against the now-populated queue; the dry-run counts inverted as expected (`WOULD insert: 0, Skipped: 90`), which itself is a second idempotency signal.

## 6. Real run output and row counts (from Step 5)

Captured from the original Step 5 invocation against the empty queue:

```
INFO v2 database: databases/berkeley_housing_v2.db
INFO Queue database: /tmp/cic_recon_queue_url_discovery.db
INFO Dry run: False
INFO Querying v2 for in-scope B-permits...
INFO v2 returned 90 in-scope permits
INFO Inserted: 90  Skipped (already in queue): 0
INFO url_discovery_queue total rows: 90
INFO   pending: 90
```

## 7. Idempotency check

Re-ran the same command (Step 6); fresh capture:

```
2026-05-22 07:45:07,432 INFO v2 database: databases/berkeley_housing_v2.db
2026-05-22 07:45:07,432 INFO Queue database: /tmp/cic_recon_queue_url_discovery.db
2026-05-22 07:45:07,432 INFO Dry run: False
2026-05-22 07:45:07,432 INFO Querying v2 for in-scope B-permits...
2026-05-22 07:45:07,433 INFO v2 returned 90 in-scope permits
2026-05-22 07:45:07,434 INFO Inserted: 0  Skipped (already in queue): 90
2026-05-22 07:45:07,434 INFO url_discovery_queue total rows: 90
2026-05-22 07:45:07,434 INFO   pending: 90
```

Result: 0 inserts, 90 skipped, total unchanged at 90. Idempotency confirmed.

## 8. Final queue state

| status | count |
|---|---|
| `pending` | 90 |
| **TOTAL** | **90** |

## 9. Sample rows (first 5 by id)

| id | permit_id | permit_number | status | attempts | created_at |
|---|---|---|---|---|---|
| 1 | 244 | B2019-05575 | pending | 0 | 2026-05-22T07:44:22.520134 |
| 2 | 137 | B2021-02225 | pending | 0 | 2026-05-22T07:44:22.520134 |
| 3 | 134 | B2021-02404 | pending | 0 | 2026-05-22T07:44:22.520134 |
| 4 | 182 | B2021-03950 | pending | 0 | 2026-05-22T07:44:22.520134 |
| 5 | 193 | B2022-01278 | pending | 0 | 2026-05-22T07:44:22.520134 |

