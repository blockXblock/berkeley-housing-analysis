---
title: "Phase 6: what the publishers need from v4, and the decisions it takes"
date: 2026-09-30
type: plan
status: proposed (awaiting John)
---

# Phase 6: what the publishers need from v4

**Goal:** every published output reads v4, so v2 can be archived. The publishers mostly read v2's flat view
`v_projects_flat` (40 columns) plus project events, permits, documents, fees and participants. Measured on live v4
`11b07920` (2026-09-30).

## v_projects_flat, column by column

| v2 column(s) | v4 source | Status |
|---|---|---|
| project_id | v4 `project_id` -- **renumbers when inputs change** | DECISION D1 |
| name | `projects.name` (address, or City-stated name verbatim) | ready |
| address_display / address_normalized | `notes.address`; canon via `housing_rules.address` | ready |
| latitude / longitude | label point of the project's first parcel (`geometries`) | derivable: 1,133/1,139 with buildings, 374/401 application-only |
| status_code / status_label | from milestones + building status | DECISION D2 |
| total_units | buildings: sum of units (ready); application-only: **no count** (scope read gives buckets only) | DECISION D4 |
| eli / vli / li / mod_units | `notes.affordability` (approved ledger; 31 projects) | ready |
| market_units | total minus the tiers | derivable |
| building_sqft, parking_spaces | none | DROP (cutover plan) |
| height_stories / height_feet | heights not yet built | phase 4 remainder (D7) |
| developer / architect | v2 values are unsourced; v4 has `record_owner` (all eras) and `applicant` (2025-26 log) | DECISION D5 |
| owner_current | assessor `owner_of_record` via project parcels | derivable: 1,032/1,139 |
| filed_date / entitled_date | `notes.filed` / `notes.entitled` (milestone rule incl. pre-2015 wording) | ready |
| bp_issued_date | first `permit_issued` of the project's master permits | derivable |
| co_issued_date | buildings' `completed_on` | DECISION D3 (several buildings) |
| assessed_value / net_taxable / exemption / est_annual_tax / as_of | `assessed_values` via parcels (+ the 1.25% rule) | derivable |
| planning_applicant | `applicant` actions (2025-26 only) | partial by source |

## Decisions

- **D1 Public identifier.** v4 `project_id`s shift when a ruling removes a project. Proposal: publish the stable
  `project_key` (anchor record, else first master permit, else external id) as the public id, plus a one-time v2->v4
  crosswalk so existing Explorer links keep resolving.
- **D2 Status.** Proposal, from evidence only: `completed` (every building complete) · `under_construction` (a master
  permit issued, not all complete) · `entitled` · `in_review` (filed, accepted or pending) · `withdrawn` / `denied` /
  `void` · `stale` (the STALE_NEEDS_SOURCE buildings, named as such). Outside-City projects take their source status.
- **D3 Completion of multi-building projects.** Proposal: `co_issued_date` = when the LAST building completed (the project is
  complete), with `first_co_date` alongside; per-building dates stay in `structures`.
- **D4 Proposed units for application-only projects.** Proposal: a model read of each anchor's text for the stated number
  of dwelling units, kept only with a verbatim quote (the names/pathways pattern; cents).
- **D5 Developer / architect.** Still-open cutover decision #1: carry v2's unsourced names as a ledger marked "carried
  from v2, unsourced", or drop them and publish the sourced `record_owner` / `applicant` instead.
- **D6 project_records.** Proposal: add the table now (project_id, record, role); the Explorer timeline needs records
  per project and JSON-in-notes does not index.
- **D7 Heights.** Build them (phase 4 remainder) or carry v2's 168 values as unsourced until then.
- **D8 Serving layer.** Proposal: a final chain step (`build_views.py`) creates v4 views (`v_projects`, `v_project_events`,
  ...) that the publishers read; no publisher re-derives a field.

## Order of re-pointing (smallest first, each diffed against its v2 output before switching)

1. `generate_apr_v2.py` (v_projects_flat + events + classifications)
2. `gen_datasette_dbs.py` and the public Datasette-Lite DB (needs a generator)
3. `gen_pipeline_state_page.py`, `gen_players_page.py`
4. `export_explorer_data_v2.py` (the largest: fees, participants, documents, permits, timeline)
5. tours / KML (needs heights and geometry)
6. analysis notebooks (JN-J/K/L/MeasureU) and tools
