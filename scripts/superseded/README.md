# Superseded scripts

Scripts retained for history but **must not be run** — they bypass current
canonical logic and would silently revert published fixes.

- **export_explorer_data.py.SUPERSEDED** (sequestered 2026-06-15) — reads raw
  `project_events` for BP/CO milestones, bypassing the completion-verdict /
  Option-B fix in `v_projects_flat`. Superseded by the view-driven
  `scripts/export_explorer_data_v2.py`, which generates the live
  `docs/explorer_data.js` with completion display derived from validated
  `co_date` (ADR-001 one-definition; see docs/audit/architecture_decisions.md).
