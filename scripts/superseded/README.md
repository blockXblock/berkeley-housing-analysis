# Superseded scripts

Scripts retained for history but **must not be run** — they bypass current
canonical logic and would silently revert published fixes.

- **export_explorer_data.py.SUPERSEDED** (sequestered 2026-06-15) — reads raw
  `project_events` for BP/CO milestones, bypassing the completion-verdict /
  Option-B fix in `v_projects_flat`. Superseded by the view-driven
  `scripts/export_explorer_data_v2.py`, which generates the live
  `docs/explorer_data.js` with completion display derived from validated
  `co_date` (ADR-001 one-definition; see docs/audit/architecture_decisions.md).

## 2026-09-26 sequester (38 files)
Moved by `git mv` from their original paths (recorded in each file's header). Every `.py` now begins
with `raise SystemExit(...)` so it cannot run by accident; the `.sh` exits 1. Four classes:
destructive (migrate_v1_to_v2, update_housing_data), dead v1-era, one-time writes already applied,
and one broken audit script. Files that came from subfolders carry a `migration__` / `analysis__` prefix.
Reference check: no live script, notebook, shell script or config imports or calls any of them.
Full reasoning: `docs/audit/2026-09-26_machinery_and_schema_audit.md`.
Restore one with `git mv` back to its original path and delete the header block.
