# URL discovery orchestrator pre-flight report

**Generated:** 2026-05-22T08:27:54
**Scope:** 3 smoke-test permits processed through `scripts/run_url_discovery.py --limit 3` against the /tmp working queue; outputs compared to the prior direct-`discover_url` smoke-test baselines.

## 1. Pre-run state checks

| check | result |
|---|---|
| Working queue `pending` count | 90 (matches expected) |
| `/tmp/url_discovery_pre_flight/` pre-existed | no (fresh dir) |
| Baseline `B2019-05575.json` present | yes (1733 bytes) |
| Baseline `B2021-02225.json` present | yes (4585 bytes) |
| Baseline `B2021-02404_postfix.json` present | yes (8635 bytes; used as baseline for -02404 since the pre-fix file is from before pagination support) |

## 2. Orchestrator invocation

```
python3 scripts/run_url_discovery.py \
  --queue-db /tmp/cic_recon_queue_url_discovery.db \
  --output-dir /tmp/url_discovery_pre_flight \
  --log-dir /tmp/url_discovery_pre_flight_logs \
  --limit 3 --sleep-min 2 --sleep-max 4
```

- Total orchestrator runtime: **84.6s**
- Chromium launched once at start, reused across all 3 permits (single Page)
- Inter-permit sleeps: 2.5s and 3.6s observed
- Permits processed: 3 / 3 (all `succeeded`)
- Per-permit durations: B2019-05575 = 21.6s · B2021-02225 = 25.1s · B2021-02404 = 29.6s

## 3. Final summary line from orchestrator stdout

```
============================================================
Orchestrator stopped
============================================================
Reason: Limit reached (3 permits)
Runtime: 84.6s
Permits processed: 3

This run:
  succeeded: 3

url_discovery_queue state:
  pending: 87
  succeeded: 3
```

## 4. Per-permit queue row state (post-run)

| id | permit_number | status | attempts | last_attempt_at | succeeded_at | output_file | error_message |
|---|---|---|---|---|---|---|---|
| 1 | B2019-05575 | succeeded | 1 | 2026-05-22T08:25:21.325781 | 2026-05-22T08:25:42.926351 | `/tmp/url_discovery_pre_flight/B2019-05575.json` | (null) |
| 2 | B2021-02225 | succeeded | 1 | 2026-05-22T08:25:45.483109 | 2026-05-22T08:26:10.612891 | `/tmp/url_discovery_pre_flight/B2021-02225.json` | (null) |
| 3 | B2021-02404 | succeeded | 1 | 2026-05-22T08:26:14.231466 | 2026-05-22T08:26:43.866229 | `/tmp/url_discovery_pre_flight/B2021-02404.json` | (null) |

## 5. Per-permit JSON inventory (post-run)

| permit | size (bytes) | master.capid_triplet | related | records_seen | pages_walked | final_state | duration_s |
|---|---|---|---|---|---|---|---|
| B2019-05575 | 1756 | `DUB19-00000-00KIL` | 2 | 3 | 1 | ok | 21.59 |
| B2021-02225 | 4608 | `DUB21-00000-00EMR` | 9 | 10 | 1 | ok | 25.13 |
| B2021-02404 | 8635 | `DUB21-00000-00EZS` | 19 | 20 | 2 | ok | 29.63 |

All 3 JSON top-level keys: `permit_number, search_url, found, ambiguous, master, related_records, errors, metadata` (matches the design-sketch shape).

## 6. Log file inventory

Count: **3** (one per permit, in `/tmp/url_discovery_pre_flight_logs/`)

- `url_discovery_20260522_B2019-05575.log` (2038 bytes)
- `url_discovery_20260522_B2021-02225.log` (2043 bytes)
- `url_discovery_20260522_B2021-02404.log` (2142 bytes)

Each log has the timestamp + level + message format and includes `[scraper]` DEBUG lines from the underlying scraper's stdout capture. Format verified by inspecting the tail of one file.

## 7. Smoke-test vs orchestrator comparison

| permit | metric | smoke (direct discover_url) | orchestrator | match |
|---|---|---|---|---|
| B2019-05575 | master triplet | `DUB19-00000-00KIL` | `DUB19-00000-00KIL` | yes |
| B2019-05575 | records_seen | 3 | 3 | yes |
| B2019-05575 | related_records count | 2 | 2 | yes |
| B2019-05575 | final_state | ok | ok | yes |
| B2019-05575 | pages_walked | None | 1 | NO |
| B2019-05575 | scrape_duration_s | 22.66 | 21.59 | (info-only; varies run-to-run) |
| B2021-02225 | master triplet | `DUB21-00000-00EMR` | `DUB21-00000-00EMR` | yes |
| B2021-02225 | records_seen | 10 | 10 | yes |
| B2021-02225 | related_records count | 9 | 9 | yes |
| B2021-02225 | final_state | ok | ok | yes |
| B2021-02225 | pages_walked | None | 1 | NO |
| B2021-02225 | scrape_duration_s | 28.15 | 25.13 | (info-only; varies run-to-run) |
| B2021-02404 | master triplet | `DUB21-00000-00EZS` | `DUB21-00000-00EZS` | yes |
| B2021-02404 | records_seen | 20 | 20 | yes |
| B2021-02404 | related_records count | 19 | 19 | yes |
| B2021-02404 | final_state | ok | ok | yes |
| B2021-02404 | pages_walked | 2 | 2 | yes |
| B2021-02404 | scrape_duration_s | 35.87 | 29.63 | (info-only; varies run-to-run) |

Note on `pages_walked = None` rows: the smoke baselines for B2019-05575 and B2021-02225 were generated BEFORE the pagination fix added the `pages_walked` metadata key. The "NO" cells for `pages_walked` on those two permits reflect that the baseline file simply doesn't carry that key, not a behavioral difference. The orchestrator's value of 1 (a single results page) is consistent with both permits' record counts (3 and 10 records, both fitting on one page). The verdict computation does not gate on `pages_walked` — only on master triplet, records_seen, related count, and final_state.

Baselines used:
- B2019-05575 ← `/tmp/url_discovery_smoke_test/B2019-05575.json`
- B2021-02225 ← `/tmp/url_discovery_smoke_test/B2021-02225.json`
- B2021-02404 ← `/tmp/url_discovery_smoke_test/B2021-02404_postfix.json`

## 8. Verdict

**PASS** — orchestrator-produced JSONs match the smoke-test baselines on every gated comparison axis (master triplet, records_seen, related count, final_state). All 3 queue rows transitioned `pending → succeeded` with `attempts=1` and a populated `succeeded_at`. The orchestrator's status mapping and queue-update logic are working as designed.

## 9. Anomalies and warnings

None observed. The pre-flight ran clean:

- No exceptions captured by the orchestrator's outer try/except.
- No `[scraper stderr]` warnings in the per-permit logs.
- `consecutive_failures` stayed at 0 throughout.
- Queue summary at the end reflects exactly 3 rows transitioned (no other rows touched).
- Per-permit timings are slightly faster than smoke (21.6/25.1/29.6 vs 22.7/28.2/35.9), consistent with reusing one Chromium instance instead of launching three.
