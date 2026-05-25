#!/usr/bin/env python3
"""
URL Discovery Orchestrator.

Processes the `url_discovery_queue` table in the queue database. For each
pending row, invokes experiments.accela_scrape.url_discovery_scraper.discover_url(),
writes the result dict to disk as JSON, and updates the queue row's status.

A single Chromium browser is launched at startup and a single Page is reused
across all permits (via discover_url's `page=` keyword), substantially faster
than launching per-permit. Anti-detection courtesy sleep between permits is
configurable via --sleep-min / --sleep-max.

Inputs
------
--queue-db  : Path to cic_recon_queue.db (READ-WRITE; only url_discovery_queue
              is touched, never scrape_queue)
--output-dir: Where to write {permit_number}.json (always written, regardless
              of outcome — even failed/not_found rows produce an artifact)
--log-dir   : Where to write per-permit log files
              (url_discovery_YYYYMMDD_{permit_number}.log)

Status mapping (queue row.status after each permit)
--------------------------------------------------
    found=True,  ambiguous=False, master is not None  -> 'succeeded'
    found=True,  ambiguous=True                       -> 'ambiguous'
    found=False                                       -> 'not_found'
    metadata.final_state == 'error'                   -> 'failed'
    otherwise (unexpected)                            -> 'failed'

Stop conditions
---------------
- Queue empty (no pending rows)
- --limit reached
- --max-runtime-seconds elapsed
- --max-consecutive-failures hit (only 'failed' counts; 'succeeded',
  'not_found', and 'ambiguous' all reset the counter — the cap exists to
  catch true errors such as Cloudflare or network failures, not coverage
  gaps where Accela's search returned 0 records or matched >1 master)
- SIGINT / KeyboardInterrupt (mid-flight row reverted to pending)

Idempotency
-----------
Only rows with status='pending' are processed. Failed / ambiguous / not_found
rows are NOT auto-retried; reset them to 'pending' manually before re-running.

Usage
-----
    python3 scripts/run_url_discovery.py
    python3 scripts/run_url_discovery.py --limit 3 --sleep-min 0 --sleep-max 1
    python3 scripts/run_url_discovery.py --no-headless -v
"""

import argparse
import contextlib
import io
import json
import logging
import pathlib
import random
import signal
import sqlite3
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Make the scraper module importable. experiments/accela_scrape is not a
# package; use the namespace-package path trick that scrape_inspections.py
# also uses.
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "experiments" / "accela_scrape"))
from url_discovery_scraper import discover_url  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_QUEUE_DB = "databases/cic_recon_queue.db"
DEFAULT_OUTPUT_DIR = "data/raw/accela_url_discovery"
DEFAULT_LOG_DIR = "logs"
DEFAULT_MAX_RUNTIME = 7200  # 2 hours, generous for a 90-permit run
DEFAULT_SLEEP_MIN = 2
DEFAULT_SLEEP_MAX = 10
DEFAULT_MAX_CONSEC_FAILURES = 5
PER_PERMIT_MAX_RUNTIME = 120  # passed to discover_url


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    print("\n*** Shutdown requested (Ctrl-C). Will exit after current permit. ***")


# ---------------------------------------------------------------------------
# Queue row helpers
# ---------------------------------------------------------------------------


def get_next_pending_row(conn):
    """Return the next row with status='pending', ordered by id."""
    return conn.execute(
        "SELECT * FROM url_discovery_queue "
        "WHERE status = 'pending' ORDER BY id LIMIT 1"
    ).fetchone()


def mark_running(conn, row_id):
    now = datetime.now().isoformat()
    conn.execute(
        """
        UPDATE url_discovery_queue
        SET status = 'running',
            attempts = attempts + 1,
            last_attempt_at = ?,
            error_message = NULL
        WHERE id = ?
        """,
        (now, row_id),
    )
    conn.commit()


def mark_succeeded(conn, row_id, output_file):
    now = datetime.now().isoformat()
    conn.execute(
        """
        UPDATE url_discovery_queue
        SET status = 'succeeded',
            error_message = NULL,
            output_file = ?,
            succeeded_at = ?
        WHERE id = ?
        """,
        (output_file, now, row_id),
    )
    conn.commit()


def mark_ambiguous(conn, row_id, error_message, output_file):
    conn.execute(
        """
        UPDATE url_discovery_queue
        SET status = 'ambiguous',
            error_message = ?,
            output_file = ?
        WHERE id = ?
        """,
        (error_message[:500] if error_message else None, output_file, row_id),
    )
    conn.commit()


def mark_not_found(conn, row_id, output_file):
    conn.execute(
        """
        UPDATE url_discovery_queue
        SET status = 'not_found',
            error_message = NULL,
            output_file = ?
        WHERE id = ?
        """,
        (output_file, row_id),
    )
    conn.commit()


def mark_failed(conn, row_id, error_message, output_file):
    conn.execute(
        """
        UPDATE url_discovery_queue
        SET status = 'failed',
            error_message = ?,
            output_file = ?
        WHERE id = ?
        """,
        (error_message[:500] if error_message else None, output_file, row_id),
    )
    conn.commit()


def mark_pending_unchanged(conn, row_id):
    """Revert a mid-flight row back to pending (Ctrl-C recovery)."""
    conn.execute(
        "UPDATE url_discovery_queue SET status = 'pending' WHERE id = ?",
        (row_id,),
    )
    conn.commit()


def get_queue_summary(conn):
    cursor = conn.execute(
        "SELECT status, COUNT(*) AS cnt FROM url_discovery_queue "
        "GROUP BY status ORDER BY status"
    )
    return {row["status"]: row["cnt"] for row in cursor.fetchall()}


# ---------------------------------------------------------------------------
# Per-permit logging
# ---------------------------------------------------------------------------


def setup_permit_logger(log_dir: Path, permit_number: str, verbose: bool):
    date_str = datetime.now().strftime("%Y%m%d")
    log_filename = f"url_discovery_{date_str}_{permit_number}.log"
    log_path = log_dir / log_filename

    logger_name = f"url_disco_{permit_number}_{time.time()}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers = []

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger, file_handler, log_path


def close_permit_logger(logger, file_handler):
    file_handler.close()
    logger.removeHandler(file_handler)


# ---------------------------------------------------------------------------
# Result -> queue mapping
# ---------------------------------------------------------------------------


def write_json_output(output_dir: Path, permit_number: str, result: dict) -> str:
    out_path = output_dir / f"{permit_number}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    return str(out_path)


def process_result(conn, row, result: dict, output_dir: Path, logger):
    """
    Apply the result-to-status mapping documented in the module docstring.

    Returns one of: 'succeeded', 'ambiguous', 'not_found', 'failed'.
    """
    row_id = row["id"]
    permit_number = row["permit_number"]
    metadata = result.get("metadata") or {}
    state = metadata.get("final_state")
    errors = result.get("errors") or []
    master = result.get("master")
    found = bool(result.get("found"))
    ambiguous = bool(result.get("ambiguous"))
    records_seen = metadata.get("records_seen", 0)

    # Always write the JSON artifact, regardless of outcome.
    output_file = write_json_output(output_dir, permit_number, result)
    logger.info(
        f"Wrote result JSON: {output_file}  "
        f"(final_state={state}, found={found}, ambiguous={ambiguous}, "
        f"records_seen={records_seen})"
    )

    if found and not ambiguous and master is not None:
        mark_succeeded(conn, row_id, output_file)
        return "succeeded"

    if found and ambiguous:
        msg = f"{records_seen} exact matches"
        mark_ambiguous(conn, row_id, msg, output_file)
        return "ambiguous"

    if not found and state != "error":
        mark_not_found(conn, row_id, output_file)
        return "not_found"

    if state == "error":
        msg = ", ".join(errors)[:500] if errors else "error (no errors[] populated)"
        mark_failed(conn, row_id, msg, output_file)
        return "failed"

    # Unexpected combination — be defensive.
    msg = f"unexpected state: final_state={state!r} found={found} ambiguous={ambiguous}"
    mark_failed(conn, row_id, msg, output_file)
    return "failed"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run_orchestrator(args):
    global shutdown_requested

    signal.signal(signal.SIGINT, signal_handler)

    queue_db_path = Path(args.queue_db)
    output_dir = Path(args.output_dir)
    log_dir = Path(args.log_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    debug_root = None
    if args.verbose:
        debug_root = log_dir / "url_discovery_debug"
        debug_root.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("URL Discovery Orchestrator")
    print("=" * 60)
    print(f"Queue DB: {queue_db_path}")
    print(f"Output dir: {output_dir}")
    print(f"Log dir: {log_dir}")
    print(f"Max runtime: {args.max_runtime_seconds}s")
    print(f"Limit: {args.limit if args.limit else 'unlimited'}")
    print(f"Mode: {'headless' if args.headless else 'headed'}")
    print(f"Sleep between permits: {args.sleep_min}-{args.sleep_max}s")
    print(f"Max consecutive failures: {args.max_consecutive_failures}")
    print(f"Verbose: {args.verbose}")
    print()

    conn = sqlite3.connect(queue_db_path)
    conn.row_factory = sqlite3.Row

    start_time = time.time()
    permits_processed = 0
    consecutive_failures = 0
    results_summary = {"succeeded": 0, "ambiguous": 0, "not_found": 0, "failed": 0}
    stop_reason = None
    current_row_id = None

    try:
        with sync_playwright() as p:
            print("Launching Chromium (one browser shared across all permits)...")
            browser = p.chromium.launch(
                headless=args.headless,
                slow_mo=50 if not args.headless else 0,
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1400, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36"
                    ),
                )
                page = context.new_page()

                while True:
                    elapsed = time.time() - start_time
                    if shutdown_requested:
                        stop_reason = "Shutdown requested (Ctrl-C)"
                        break
                    if args.limit and permits_processed >= args.limit:
                        stop_reason = f"Limit reached ({args.limit} permits)"
                        break
                    if elapsed > args.max_runtime_seconds:
                        stop_reason = (
                            f"Max runtime exceeded ({args.max_runtime_seconds}s)"
                        )
                        break
                    if consecutive_failures >= args.max_consecutive_failures:
                        stop_reason = (
                            f"{consecutive_failures} consecutive failures "
                            f"(possible Accela blocking)"
                        )
                        break

                    row = get_next_pending_row(conn)
                    if row is None:
                        stop_reason = "Queue empty (no pending rows)"
                        break

                    current_row_id = row["id"]
                    permit_number = row["permit_number"]

                    mark_running(conn, current_row_id)

                    logger, file_handler, log_path = setup_permit_logger(
                        log_dir, permit_number, args.verbose
                    )

                    logger.info("=" * 50)
                    logger.info(f"Starting permit: {permit_number}")
                    logger.info(
                        f"Queue row ID: {current_row_id}, "
                        f"attempts (post-increment): {row['attempts'] + 1}"
                    )
                    logger.info(f"Log file: {log_path}")

                    permit_start = time.time()
                    debug_dir_for_permit = (
                        debug_root / permit_number if debug_root else None
                    )

                    outcome = None
                    try:
                        stdout_capture = io.StringIO()
                        stderr_capture = io.StringIO()
                        with contextlib.redirect_stdout(stdout_capture), \
                                contextlib.redirect_stderr(stderr_capture):
                            result = discover_url(
                                permit_number,
                                page=page,
                                debug_dir=debug_dir_for_permit,
                                max_runtime_seconds=PER_PERMIT_MAX_RUNTIME,
                            )
                        stdout_text = stdout_capture.getvalue()
                        if stdout_text:
                            for line in stdout_text.rstrip().split("\n"):
                                logger.debug(f"[scraper] {line}")
                        stderr_text = stderr_capture.getvalue()
                        if stderr_text:
                            for line in stderr_text.rstrip().split("\n"):
                                logger.warning(f"[scraper stderr] {line}")
                    except Exception as e:
                        tb = traceback.format_exc()
                        logger.error(f"Exception in discover_url: {e}")
                        logger.error(tb)
                        msg = f"Exception: {str(e)[:400]}"
                        # Build a minimal result dict so we still write JSON.
                        fallback_result = {
                            "permit_number": permit_number,
                            "found": False, "ambiguous": False,
                            "master": None, "related_records": [],
                            "errors": [msg],
                            "metadata": {"final_state": "error"},
                        }
                        out_path = write_json_output(
                            output_dir, permit_number, fallback_result
                        )
                        mark_failed(conn, current_row_id, msg, out_path)
                        outcome = "failed"
                        results_summary["failed"] += 1
                    else:
                        outcome = process_result(conn, row, result, output_dir, logger)
                        results_summary[outcome] += 1
                        # Console one-liner for the per-permit summary
                        m = result.get("master") or {}
                        related = result.get("related_records") or []
                        triplet = m.get("capid_triplet") if m else None
                        logger.info(
                            f"Permit {permit_number}: {outcome}  "
                            f"master={triplet}  "
                            f"related={len(related)}  "
                            f"records_seen={result.get('metadata', {}).get('records_seen')}"
                        )

                    permit_duration = time.time() - permit_start
                    logger.info(
                        f"Permit {permit_number} completed: {outcome} "
                        f"in {permit_duration:.1f}s"
                    )

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

                    close_permit_logger(logger, file_handler)
                    permits_processed += 1
                    current_row_id = None

                    # Anti-detection courtesy sleep, only if more work pending
                    if not shutdown_requested and not (
                        args.limit and permits_processed >= args.limit
                    ):
                        next_row = get_next_pending_row(conn)
                        if next_row is not None and args.sleep_max > 0:
                            delay = random.uniform(args.sleep_min, args.sleep_max)
                            print(f"Sleeping {delay:.1f}s before next permit...")
                            time.sleep(delay)

            finally:
                try:
                    browser.close()
                except Exception:
                    pass

    except KeyboardInterrupt:
        stop_reason = stop_reason or "Shutdown requested (KeyboardInterrupt)"
    finally:
        # If we were mid-flight on a row, revert it to pending so the next
        # run picks it up. attempts increment from mark_running is preserved.
        if current_row_id is not None:
            print(f"\nMarking row {current_row_id} back to pending (interrupted)")
            try:
                mark_pending_unchanged(conn, current_row_id)
            except Exception as e:
                print(f"  (cleanup failed: {e})")

        total_elapsed = time.time() - start_time
        queue_summary = get_queue_summary(conn)

        print()
        print("=" * 60)
        print("Orchestrator stopped")
        print("=" * 60)
        print(f"Reason: {stop_reason}")
        print(f"Runtime: {total_elapsed:.1f}s")
        print(f"Permits processed: {permits_processed}")
        print()
        print("This run:")
        for outcome, count in sorted(results_summary.items()):
            if count > 0:
                print(f"  {outcome}: {count}")
        print()
        print("url_discovery_queue state:")
        for status, count in sorted(queue_summary.items()):
            print(f"  {status}: {count}")

        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="URL discovery orchestrator - processes url_discovery_queue"
    )
    parser.add_argument(
        "--queue-db",
        default=DEFAULT_QUEUE_DB,
        help=f"Path to queue database (default: {DEFAULT_QUEUE_DB})",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Where to write {{permit_number}}.json (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--log-dir",
        default=DEFAULT_LOG_DIR,
        help=f"Where to write per-permit log files (default: {DEFAULT_LOG_DIR})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N permits this run (default: unlimited)",
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=int,
        default=DEFAULT_MAX_RUNTIME,
        help=f"Max runtime in seconds (default: {DEFAULT_MAX_RUNTIME})",
    )
    parser.add_argument(
        "--sleep-min",
        type=float,
        default=DEFAULT_SLEEP_MIN,
        help=f"Minimum inter-permit sleep seconds (default: {DEFAULT_SLEEP_MIN})",
    )
    parser.add_argument(
        "--sleep-max",
        type=float,
        default=DEFAULT_SLEEP_MAX,
        help=f"Maximum inter-permit sleep seconds (default: {DEFAULT_SLEEP_MAX})",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=DEFAULT_MAX_CONSEC_FAILURES,
        help=(
            f"Abort after this many consecutive 'failed' (true-error) "
            f"permits in a row. 'not_found' and 'ambiguous' do NOT count — "
            f"they reset the counter. (default: {DEFAULT_MAX_CONSEC_FAILURES})"
        ),
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run Chromium headless (default). Use --no-headless to debug visually.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging + write per-permit debug screenshots/HTML under "
             "{log-dir}/url_discovery_debug/{permit_number}/",
    )
    args = parser.parse_args()
    if args.sleep_min < 0 or args.sleep_max < 0 or args.sleep_max < args.sleep_min:
        parser.error("invalid --sleep-min/--sleep-max")
    run_orchestrator(args)


if __name__ == "__main__":
    main()
