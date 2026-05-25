# URL discovery orchestrator — consecutive-failures fix

**Generated:** 2026-05-22T13:13:43
**Target file:** `scripts/run_url_discovery.py` (in-place edit)

## 1. Original logic (pre-fix)

Counter mutation block (lines 471–476 pre-edit):

```python
# Update consecutive-failures counter per status mapping
if outcome in ("failed", "not_found"):
    consecutive_failures += 1
else:
    consecutive_failures = 0
logger.info(f"Consecutive failures: {consecutive_failures}")
```

Both `failed` AND `not_found` incremented the counter. This caused the 87-permit run to halt after 5 consecutive `not_found` outcomes, which were a data-coverage finding (Accela's public search doesn't surface every CPRA-listed permit), not a true error condition.

Two supporting documentation strings also baked in the old semantics:
- Module docstring around line 36–37: "--max-consecutive-failures hit (failed + not_found count; succeeded + ambiguous reset the counter)"
- `--max-consecutive-failures` argparse help: "Abort after this many consecutive failed+not_found permits ..."

## 2. New logic (post-fix)

Counter mutation block (now lines 471–486):

```python
# Update consecutive-failures counter per status mapping.
# Only 'failed' (true scraper/parse/network errors) counts;
# 'succeeded', 'not_found', and 'ambiguous' all reset.
# Rationale: 'not_found' / 'ambiguous' reflect Accela's
# response to a search that worked — they are coverage
# findings, not failures. The cap exists to catch real
# blocking (Cloudflare, repeated network errors).
if outcome == "failed":
    consecutive_failures += 1
else:
    consecutive_failures = 0
logger.info(
    f"Consecutive failed (true-error) count: "
    f"{consecutive_failures}"
)
```

Docstring updated:

```
- --max-consecutive-failures hit (only 'failed' counts; 'succeeded',
  'not_found', and 'ambiguous' all reset the counter — the cap exists to
  catch true errors such as Cloudflare or network failures, not coverage
  gaps where Accela's search returned 0 records or matched >1 master)
```

CLI help string updated:

```
--max-consecutive-failures MAX_CONSECUTIVE_FAILURES
    Abort after this many consecutive 'failed' (true-error) permits
    in a row. 'not_found' and 'ambiguous' do NOT count — they reset
    the counter. (default: 5)
```

## 3. Per-status behavior table

| outcome | meaning | counter behavior |
|---|---|---|
| `succeeded` | found, not ambiguous, master extracted | **reset** to 0 |
| `not_found` | Accela's search returned 0 records, OR returned records but none matched the exact search query | **reset** to 0 (was: increment) |
| `ambiguous` | >1 record on results page had `displayed permit_number == search query` | **reset** to 0 |
| `failed` | scraper raised an exception, or `metadata.final_state == 'error'` (Cloudflare, login wall, navigation timeout, etc.) | **increment** by 1 |

## 4. Validation

| check | result |
|---|---|
| `python3 -c "import ast; ast.parse(...)"` | **AST OK** |
| `python3 scripts/run_url_discovery.py --help` | exits 0; help text reflects the new semantics |

`--help` output (verbatim):

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
                        Abort after this many consecutive 'failed' (true-
                        error) permits in a row. 'not_found' and 'ambiguous'
                        do NOT count — they reset the counter. (default: 5)
  --headless, --no-headless
                        Run Chromium headless (default). Use --no-headless to
                        debug visually.
  -v, --verbose         Verbose logging + write per-permit debug
                        screenshots/HTML under {log-
                        dir}/url_discovery_debug/{permit_number}/
```

## 5. Grep audit (post-edit)

```
336:    print(f"Max consecutive failures: {args.max_consecutive_failures}")
345:    consecutive_failures = 0
380:                    if consecutive_failures >= args.max_consecutive_failures:
382:                            f"{consecutive_failures} consecutive failures "
481:                        consecutive_failures += 1
483:                        consecutive_failures = 0
486:                        f"{consecutive_failures}"
```

Audit interpretation:

- Line 336: banner print (read-only)
- Line 345: initialization to 0 (read-only)
- Line 380: cap check site (`if consecutive_failures >= args.max_consecutive_failures`)
- Line 382: stop-reason string interpolation (read-only)
- **Line 481: the single increment site** (in the `outcome == 'failed'` branch)
- **Line 483: the single reset site** (in the `else` branch — covers `succeeded` + `not_found` + `ambiguous` via fall-through)
- Line 486: log message (read-only)

Note on the task spec's "three reset sites" expectation: the natural Pythonic expression of "failed increments, everything else resets" is one `if/else` with two branches, which is what this implementation uses. Semantically equivalent to three explicit `elif outcome == '<status>': consecutive_failures = 0` branches — the `else` covers `succeeded`, `not_found`, and `ambiguous` identically. The result is one increment site, one reset site, one cap check — same end behavior.

Total references: **7** (1 banner + 1 init + 1 check + 1 stop-reason + 1 increment + 1 reset + 1 log) — matches expected.
