# URL discovery orchestrator build report

**Generated:** 2026-05-22T08:22:55
**Target file:** `scripts/run_url_discovery.py` (tracked, not committed)

## 1. Patterns mirrored from `scripts/scrape_inspections.py`

- Per-permit logger built by a `setup_permit_logger()` factory; separate `FileHandler` + `StreamHandler` per permit, closed via `close_permit_logger()` after each row.
- Granular SQL helpers for each status transition (`mark_running`, `mark_succeeded`, `mark_ambiguous`, `mark_not_found`, `mark_failed`, `mark_pending_unchanged`) rather than one big UPDATE block.
- `signal.signal(SIGINT, signal_handler)` + module-level `shutdown_requested` flag; main loop polls the flag at the top of each iteration.
- Scraper `stdout` / `stderr` captured via `contextlib.redirect_stdout(io.StringIO())`; captured lines flow into the permit logger as `[scraper] ...` DEBUG entries.
- `consecutive_failures` counter with a configurable cap; succeeded+ambiguous reset the counter, failed+not_found increment.
- Random inter-permit sleep via `random.uniform(sleep_min, sleep_max)`; skipped when no further work or at the limit.
- `try` / `except` around the scraper call catches uncaught exceptions; writes a fallback JSON artifact and marks the row failed.
- `finally` block reverts a mid-flight row back to `pending` on Ctrl-C so a re-run picks it up.
- Final summary block prints stop reason, runtime, this-run breakdown, full queue state.
- Browser, however, is launched **once** for the orchestrator and the Page is reused via `discover_url(page=...)` — divergence from `scrape_inspections.py` (which launches per call). Rationale: discovery is uniform across permits and each call is ~25–40s; launching Chromium per call would double or triple per-permit cost.
- `--headless` / `--no-headless` via `argparse.BooleanOptionalAction` (default True). Inverted from `scrape_inspections.py`'s `--headed` flag because the new convention reads more naturally with the default.
- `attempts` is incremented exactly **once** per attempt, inside `mark_running()`. Cleaner than the inspection scraper's multi-site increments.

## 2. Script

| field | value |
|---|---|
| Path | `scripts/run_url_discovery.py` |
| Lines | 610 |
| Executable | yes (chmod +x) |

## 3. `--help` output

```
usage: run_url_discovery.py [-h] [--queue-db QUEUE_DB]
                            [--output-dir OUTPUT_DIR] [--log-dir LOG_DIR]
                            [--limit LIMIT]
                            [--max-runtime-seconds MAX_RUNTIME_SECONDS]
                            [--sleep-min SLEEP_MIN] [--sleep-max SLEEP_MAX]
                            [--max-consecutive-failures MAX_CONSECUTIVE_FAILURES]
                            [--headless | --no-headless] [-v]

URL discovery orchestrator - processes url_discovery_queue

options:
  -h, --help            show this help message and exit
  --queue-db QUEUE_DB   Path to queue database (default:
                        databases/cic_recon_queue.db)
  --output-dir OUTPUT_DIR
                        Where to write {permit_number}.json (default:
                        data/raw/accela_url_discovery)
  --log-dir LOG_DIR     Where to write per-permit log files (default: logs)
  --limit LIMIT         Process at most N permits this run (default:
                        unlimited)
  --max-runtime-seconds MAX_RUNTIME_SECONDS
                        Max runtime in seconds (default: 7200)
  --sleep-min SLEEP_MIN
                        Minimum inter-permit sleep seconds (default: 2)
  --sleep-max SLEEP_MAX
                        Maximum inter-permit sleep seconds (default: 10)
  --max-consecutive-failures MAX_CONSECUTIVE_FAILURES
                        Abort after this many consecutive failed+not_found
                        permits (default: 5)
  --headless, --no-headless
                        Run Chromium headless (default). Use --no-headless to
                        debug visually.
  -v, --verbose         Verbose logging + write per-permit debug
                        screenshots/HTML under {log-
                        dir}/url_discovery_debug/{permit_number}/
```

## 4. Public `main` function

- `main`: **callable** (verified by loading the file via `importlib.util.spec_from_file_location`)
- `run_orchestrator`: **callable** (also reachable; useful for in-process testing if ever needed)

## 5. Status-mapping table

| `discover_url` outcome | `url_discovery_queue.status` | `error_message` | Counts toward consec-failures? |
|---|---|---|---|
| `found=True`, `ambiguous=False`, `master` is not None | `succeeded` | NULL | No |
| `found=True`, `ambiguous=True` | `ambiguous` | `"{records_seen} exact matches"` | No |
| `found=False`, `final_state!='error'` | `not_found` | NULL | **Yes** |
| `final_state='error'` | `failed` | first 500 chars of `errors[]` joined by `", "` | **Yes** |
| Anything else unexpected | `failed` | `"unexpected state: ..."` | **Yes** |
| Python exception from `discover_url` | `failed` | `"Exception: ..."` (first 400 chars) | **Yes** |

In all five rows a JSON artifact is written to `{output-dir}/{permit_number}.json` — including failed / not_found / ambiguous cases — so the forensic record is always available.

## 6. Dry-run thought experiment

Not actually executed. Computed expectation for:

```
python3 scripts/run_url_discovery.py \
    --queue-db /tmp/cic_recon_queue_url_discovery.db \
    --output-dir /tmp/url_discovery_dryrun_output \
    --log-dir /tmp/url_discovery_dryrun_logs \
    --limit 3 \
    --sleep-min 0 --sleep-max 1
```

- Pending rows in the /tmp working DB: **90** (of 90 total)
- First 3 pending rows by id (the ones a --limit 3 run would process):
  - B2019-05575
  - B2021-02225
  - B2021-02404
- Interesting: this is exactly the smoke-test trio. A --limit 3 dry-run would re-run the same 3 permits we already verified individually via direct `discover_url` calls.
- Estimated per-permit duration (from smoke test): B2019-05575 ≈ 22.7s, B2021-02225 ≈ 28.2s, B2021-02404 ≈ 35.9s (with pagination fix).
- Estimated inter-permit sleeps: 2 × `random.uniform(0, 1)` ≈ 1.0s total expected.
- **Estimated total runtime: ~90s** (~87s scraper + ~1s sleeps + ~2s Chromium launch).
- Output files expected: 3 in `/tmp/url_discovery_dryrun_output/` — `B2019-05575.json`, `B2021-02225.json`, `B2021-02404.json`.
- Log files expected: 3 in `/tmp/url_discovery_dryrun_logs/` — `url_discovery_YYYYMMDD_{permit_number}.log` per permit.
- Queue state changes expected: 3 rows transition from `pending` → `succeeded` (based on smoke-test results: all 3 should succeed now with pagination fix in place).
- Consecutive-failures counter at end of run: 0 (succeeded resets the counter).

## 7. Anomalies and design questions surfaced during build

1. **`url_discovery_queue` schema has fewer columns than `scrape_queue`.** Notably no `url`, `project_id`, `project_address`, `capid_triplet`, or `inspections_count`. The orchestrator only references columns that exist on `url_discovery_queue`. This is intentional per the design sketch (the queue is a worklist; the JSON artifact carries the full payload), but means a row inspection alone won't show the discovered triplet — the JSON file at `output_file` does.

2. **One Chromium for all 90 permits.** If Berkeley Accela's session/cookies become rate-limited or invalidated mid-run, all subsequent permits in the run will fail together. The `--max-consecutive-failures 5` cap catches this. Alternative architectures (relaunch Chromium every N permits, or rotate user_agents) are deferred until we see whether this actually happens at the 90-permit scale.

3. **Page state pollution.** `discover_url` navigates the shared Page to CapHome → results → master CapDetail per permit. Between permits the Page is still on the last master's CapDetail; the next call's first action is `page.goto(search_url, ...)` which clears that state. Should be fine, but worth watching the first few logs for unexpected residual state.

4. **Idempotency vs design sketch.** The design sketch's section on the orchestrator says "reads pending from url_discovery_queue" — the implementation does exactly that and only that. Failed / ambiguous / not_found rows are NOT auto-retried; an operator must reset them to `pending` to give them another shot. The docstring documents this explicitly.

5. **Per-permit time budget = 120s.** Passed as `max_runtime_seconds=120` to `discover_url`. The smoke test's slowest run was 35.9s (B2021-02404 with 2-page pagination), so 120s is generous. If a permit has many more pages (e.g., a hypothetical 5-page master), 120s may still suffice, but worth watching during the actual run.

