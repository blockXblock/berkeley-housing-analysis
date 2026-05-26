# scripts/

Working scripts for the Berkeley Housing Pipeline. Each is documented in its own module docstring; this README is a brief index.

## HCD APR mirror

**`build_hcd_mirror.py`** — canonical method for pulling Berkeley APR data from California HCD's CKAN datastore and mirroring it locally to `databases/hcd_apr_mirror.db`.

The mirror DB itself is gitignored (it's regenerable); this script is the source of truth. Run anytime HCD's data updates.

Usage:

```bash
# build/refresh mirror
python scripts/build_hcd_mirror.py

# drop and rebuild from scratch
python scripts/build_hcd_mirror.py --rebuild

# build + run the CY 2025 doubling diagnostic
python scripts/build_hcd_mirror.py --diagnose
```

The script pulls 12 HCD APR table resources (A, A2, C, D, E, F, F2, G, H, I, K, L), filters each to Berkeley rows, and writes the result to per-table SQLite tables. A `_pull_metadata` table records when each pull happened, the HCD resource URL, and the upstream schema.

Idempotence: each invocation drops and recreates each table within a transaction. Running twice produces the same final DB state.

Cached raw responses (for debugging) land in `/tmp/hcd_pull_YYYY-MM-DD/` — outside the repo, not gitignored because git doesn't see `/tmp/`.

## Other scripts

(This README only documents the HCD mirror script. Other scripts in this directory should add their own sections here as they're committed.)
