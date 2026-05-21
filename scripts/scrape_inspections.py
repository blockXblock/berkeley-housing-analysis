#!/usr/bin/env python3
"""
Inspection Scraper Orchestrator

Processes the scrape queue, invokes the inspection scraper module for each
actionable permit, writes JSON output, updates queue status, and logs
everything for next-day diagnosis.

Usage:
    python3 scrape_inspections.py [options]

Dependencies:
    - Queue: /tmp/cic_recon_queue.db (built by build_scrape_queue.py)
    - Scraper: /tmp/inspection_scraper.py (refactored POC)
"""

import argparse
import contextlib
import io
import json
import logging
import random
import signal
import sqlite3
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# inspection_scraper lives in experiments/accela_scrape/
# Resolve its path relative to this script's repo location.
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "experiments" / "accela_scrape"))
from inspection_scraper import scrape_inspections


# Default paths (relative to script location)
SCRIPT_DIR = Path(__file__).parent
DEFAULT_QUEUE_DB = "/tmp/cic_recon_queue.db"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "data" / "raw" / "accela_inspections"
DEFAULT_LOG_DIR = SCRIPT_DIR / "logs"
DEFAULT_MAX_RUNTIME = 28800  # 8 hours
DEFAULT_SLEEP_MIN = 2
DEFAULT_SLEEP_MAX = 10


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle Ctrl-C for graceful shutdown."""
    global shutdown_requested
    shutdown_requested = True
    print("\n*** Shutdown requested (Ctrl-C). Will exit after current permit. ***")


def get_next_pending_row(conn):
    """
    Get the next row with status='pending' (exactly).

    NOTE: This deliberately excludes 'pending_url_discovery' rows.
    URL discovery is a separate workstream.
    """
    cursor = conn.execute("""
        SELECT * FROM scrape_queue
        WHERE status = 'pending'
        ORDER BY id
        LIMIT 1
    """)
    row = cursor.fetchone()
    return row


def mark_running(conn, row_id):
    """Mark a row as running."""
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE scrape_queue
        SET status = 'running', last_attempt_at = ?
        WHERE id = ?
    """, (now, row_id))
    conn.commit()


def mark_succeeded(conn, row_id, inspections_count, output_file):
    """Mark a row as succeeded."""
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE scrape_queue
        SET status = 'succeeded',
            inspections_count = ?,
            output_file = ?,
            succeeded_at = ?,
            attempts = attempts + 1,
            last_attempt_at = ?,
            error_message = NULL
        WHERE id = ?
    """, (inspections_count, output_file, now, now, row_id))
    conn.commit()


def mark_failed_retry(conn, row_id, error_message):
    """Mark a row for retry (back to pending)."""
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE scrape_queue
        SET status = 'pending',
            attempts = attempts + 1,
            last_attempt_at = ?,
            error_message = ?
        WHERE id = ?
    """, (now, error_message[:500] if error_message else None, row_id))
    conn.commit()


def mark_failed_terminal(conn, row_id, error_message):
    """Mark a row as terminally failed."""
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE scrape_queue
        SET status = 'failed',
            attempts = attempts + 1,
            last_attempt_at = ?,
            error_message = ?
        WHERE id = ?
    """, (now, error_message[:500] if error_message else None, row_id))
    conn.commit()


def mark_skipped(conn, row_id, reason):
    """Mark a row as skipped (permanent, never retry)."""
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE scrape_queue
        SET status = 'skipped',
            last_attempt_at = ?,
            error_message = ?
        WHERE id = ?
    """, (now, reason, row_id))
    conn.commit()


def mark_pending_unchanged(conn, row_id):
    """Mark a row back to pending without incrementing attempts (for Ctrl-C)."""
    conn.execute("""
        UPDATE scrape_queue
        SET status = 'pending'
        WHERE id = ?
    """, (row_id,))
    conn.commit()


def get_queue_summary(conn):
    """Get count by status for final summary."""
    cursor = conn.execute("""
        SELECT status, COUNT(*) as cnt
        FROM scrape_queue
        GROUP BY status
        ORDER BY status
    """)
    return {row['status']: row['cnt'] for row in cursor.fetchall()}


def setup_permit_logger(log_dir, permit_number):
    """
    Set up a logger for a specific permit with both file and stdout handlers.

    Returns (logger, file_handler) so caller can close the handler later.
    """
    date_str = datetime.now().strftime("%Y%m%d")
    log_filename = f"scrape_inspections_{date_str}_{permit_number}.log"
    log_path = log_dir / log_filename

    # Create a unique logger for this permit
    logger_name = f"permit_{permit_number}_{time.time()}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers = []  # Clear any existing handlers

    # Formatter with timestamp
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # File handler for this permit
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream handler for stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger, file_handler, log_path


def close_permit_logger(logger, file_handler):
    """Close and remove the file handler from a permit logger."""
    file_handler.close()
    logger.removeHandler(file_handler)


def sleep_random(min_seconds, max_seconds, logger):
    """Sleep for a random duration between min and max seconds."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.info(f"Sleeping {delay:.1f}s before next permit...")
    time.sleep(delay)


def write_json_output(output_dir, permit_number, result):
    """Write scraper result to JSON file."""
    output_path = output_dir / f"{permit_number}.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    return str(output_path)


def process_result(conn, row, result, output_dir, logger):
    """
    Process the result from scrape_inspections and update queue accordingly.

    Returns:
        str: 'succeeded', 'failed', 'skipped', or 'retry'
    """
    row_id = row['id']
    permit_number = row['permit_number']
    attempts = row['attempts']

    state = result.get("metadata", {}).get("final_pagination_state", "unknown")
    errors = result.get("errors", [])
    errors_str = "; ".join(errors) if errors else None
    inspections_count = len(result.get("inspections", []))

    logger.info(f"Processing result: state={state}, inspections={inspections_count}, errors={len(errors)}")

    if state in ("last_page", "success"):
        # Success case
        if state == "success":
            # Defensive: 'success' as final state is unexpected
            logger.warning("final_pagination_state='success' is unexpected; treating as success anyway")

        # Write JSON output
        output_file = write_json_output(output_dir, permit_number, result)
        logger.info(f"Wrote {inspections_count} inspections to {output_file}")

        mark_succeeded(conn, row_id, inspections_count, output_file)
        return 'succeeded'

    elif state == "failed":
        # Transient failure — retry candidate
        if attempts + 1 < 3:
            logger.info(f"Marking for retry (attempt {attempts + 1} of 3)")
            mark_failed_retry(conn, row_id, errors_str)
            return 'retry'
        else:
            logger.info(f"Terminal failure after {attempts + 1} attempts")
            mark_failed_terminal(conn, row_id, errors_str)
            return 'failed'

    elif state == "not_reached":
        # Could not reach inspection table
        if "Timeout loading main page" in errors:
            # Network timeout — treat as transient
            if attempts + 1 < 3:
                logger.info("Page load timeout; marking for retry")
                mark_failed_retry(conn, row_id, errors_str)
                return 'retry'
            else:
                logger.info("Page load timeout; terminal failure after max attempts")
                mark_failed_terminal(conn, row_id, errors_str)
                return 'failed'

        elif result.get("metadata", {}).get("requires_auth"):
            # Login redirect — permanent, never retry
            logger.info("Requires authentication; marking as skipped")
            mark_skipped(conn, row_id, "requires_auth")
            return 'skipped'

        else:
            # No table found — permit may have no inspections
            # Treat as succeeded with count=0
            logger.info("No inspection table found; treating as succeeded with 0 inspections")
            output_file = write_json_output(output_dir, permit_number, result)
            mark_succeeded(conn, row_id, 0, output_file)
            return 'succeeded'

    else:
        # Unknown state — defensive
        logger.error(f"Unknown final_pagination_state: {state}")
        mark_failed_terminal(conn, row_id, f"unknown state: {state}")
        return 'failed'


def run_orchestrator(args):
    """Main orchestrator loop."""
    global shutdown_requested

    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Resolve paths
    queue_db_path = Path(args.queue_db)
    output_dir = Path(args.output_dir)
    log_dir = Path(args.log_dir)

    # Create output directories if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Inspection Scraper Orchestrator")
    print("=" * 60)
    print(f"Queue DB: {queue_db_path}")
    print(f"Output dir: {output_dir}")
    print(f"Log dir: {log_dir}")
    print(f"Max runtime: {args.max_runtime_seconds}s")
    print(f"Limit: {args.limit if args.limit else 'unlimited'}")
    print(f"Mode: {'headed' if args.headed else 'headless'}")
    print(f"Sleep between permits: {'disabled' if args.no_sleep else f'{DEFAULT_SLEEP_MIN}-{DEFAULT_SLEEP_MAX}s'}")
    print()

    # Connect to queue database
    conn = sqlite3.connect(queue_db_path)
    conn.row_factory = sqlite3.Row

    # Tracking variables
    start_time = time.time()
    permits_processed = 0
    consecutive_failures = 0
    results_summary = {'succeeded': 0, 'failed': 0, 'skipped': 0, 'retry': 0}
    stop_reason = None
    current_row_id = None

    try:
        while True:
            # Check stop conditions
            elapsed = time.time() - start_time

            if shutdown_requested:
                stop_reason = "Shutdown requested (Ctrl-C)"
                break

            if args.limit and permits_processed >= args.limit:
                stop_reason = f"Limit reached ({args.limit} permits)"
                break

            if elapsed > args.max_runtime_seconds:
                stop_reason = f"Max runtime exceeded ({args.max_runtime_seconds}s)"
                break

            if consecutive_failures >= 5:
                stop_reason = "5 consecutive failures (possible Accela blocking)"
                break

            # Get next pending row
            row = get_next_pending_row(conn)
            if row is None:
                stop_reason = "Queue empty (no pending rows)"
                break

            current_row_id = row['id']
            permit_number = row['permit_number']
            url = row['url']

            # Mark as running
            mark_running(conn, current_row_id)

            # Set up per-permit logging
            logger, file_handler, log_path = setup_permit_logger(log_dir, permit_number)

            logger.info(f"=" * 50)
            logger.info(f"Starting permit: {permit_number}")
            logger.info(f"URL: {url}")
            logger.info(f"Queue row ID: {current_row_id}, attempts: {row['attempts']}")
            logger.info(f"Log file: {log_path}")

            permit_start = time.time()

            try:
                # Capture stdout/stderr from scraper into log
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()

                with contextlib.redirect_stdout(stdout_capture), \
                     contextlib.redirect_stderr(stderr_capture):
                    result = scrape_inspections(
                        permit_number,
                        url,
                        headless=not args.headed,
                    )

                # Log captured output
                stdout_text = stdout_capture.getvalue()
                if stdout_text:
                    for line in stdout_text.strip().split('\n'):
                        logger.debug(f"[scraper] {line}")

                stderr_text = stderr_capture.getvalue()
                if stderr_text:
                    for line in stderr_text.strip().split('\n'):
                        logger.warning(f"[scraper stderr] {line}")

            except Exception as e:
                # Uncaught exception from scraper
                tb = traceback.format_exc()
                logger.error(f"Exception in scrape_inspections: {e}")
                logger.error(tb)

                # Mark as failed (no retry on uncaught exceptions)
                error_msg = f"Exception: {str(e)[:400]}"
                mark_failed_terminal(conn, current_row_id, error_msg)

                outcome = 'failed'
                consecutive_failures += 1
                results_summary['failed'] += 1

            else:
                # Process the result
                outcome = process_result(conn, row, result, output_dir, logger)
                results_summary[outcome] += 1

                # Update consecutive failures counter
                if outcome == 'failed':
                    consecutive_failures += 1
                else:
                    consecutive_failures = 0

            permit_duration = time.time() - permit_start
            logger.info(f"Permit {permit_number} completed: {outcome} in {permit_duration:.1f}s")
            logger.info(f"Consecutive failures: {consecutive_failures}")

            # Close per-permit log
            close_permit_logger(logger, file_handler)

            permits_processed += 1
            current_row_id = None

            # Sleep before next permit (unless --no-sleep or last permit)
            if not args.no_sleep and not shutdown_requested:
                # Check if there's another pending row before sleeping
                next_row = get_next_pending_row(conn)
                if next_row is not None:
                    # Use a basic print since permit logger is closed
                    delay = random.uniform(DEFAULT_SLEEP_MIN, DEFAULT_SLEEP_MAX)
                    print(f"Sleeping {delay:.1f}s before next permit...")
                    time.sleep(delay)

    except KeyboardInterrupt:
        # Backup handler in case signal handler doesn't catch it
        stop_reason = "Shutdown requested (KeyboardInterrupt)"

    finally:
        # If we were in the middle of processing a permit, mark it back to pending
        if current_row_id is not None:
            print(f"\nMarking row {current_row_id} back to pending (interrupted)")
            mark_pending_unchanged(conn, current_row_id)

        # Final summary
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
        print("Queue state:")
        for status, count in sorted(queue_summary.items()):
            print(f"  {status}: {count}")

        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Inspection scraper orchestrator - processes scrape queue"
    )
    parser.add_argument(
        "--queue-db",
        default=DEFAULT_QUEUE_DB,
        help=f"Path to queue database (default: {DEFAULT_QUEUE_DB})"
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Where to write {{permit_number}}.json (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--log-dir",
        default=str(DEFAULT_LOG_DIR),
        help=f"Where to write per-permit log files (default: {DEFAULT_LOG_DIR})"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N permits this run (default: unlimited)"
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=int,
        default=DEFAULT_MAX_RUNTIME,
        help=f"Max runtime in seconds (default: {DEFAULT_MAX_RUNTIME})"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (visible); default is headless"
    )
    parser.add_argument(
        "--no-sleep",
        action="store_true",
        help="Skip random sleep between permits (for testing only)"
    )

    args = parser.parse_args()
    run_orchestrator(args)


if __name__ == "__main__":
    main()
