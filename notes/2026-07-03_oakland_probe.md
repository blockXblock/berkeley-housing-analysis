# Oakland parallel-project probe — findings (2026-07-03)

Probes: Socrata catalog (API), Accela ACA via the date-range scraper (agency param), and a CIC
session (Download-results export + CO record-type taxonomy). Specimen committed:
`data/raw/accela/oakland/RecordList_2026-06_downloaded_2026-07-03.csv` (2,351 records, June 2026).

## What holds up

- **Acquisition is easier than Berkeley's.** ACA live at agency `OAKLAND`; our scraper worked with
  one parameter changed; and the **Download-results export bypasses the "200+" display cap** —
  one click returned the full 2,351-record month with Description. Monthly downloads (or an
  `expect_download` automation) = a complete filings feed with no pagination and no CPRA wait.
- **The status taxonomy exposes the waiting room and the clock states** Berkeley's feed hides:
  `Pending - Incomplete`, `Intake - Completed` (~deemed-complete), `In Review`, `On Hold`, plus
  completion-side `Final` / `Complete` / `Certificate Issued`. Statutory-clock states are public.
- **Record types pre-classify**: 1&2-unit vs 3+ residential vs commercial, New Construction vs
  Alteration, SolarApp+, etc. — much of permit_role's work arrives pre-labeled.
- Same Alameda assessor feed; same statewide HCD CKAN oracle (`JURIS_NAME='OAKLAND'`).

## What did NOT hold up (correction to the first read)

- **"Certificate of Occupancy" as a record type is NICHE, not the completion stream.** Only 14 CO
  records filed in Jan–Jun 2026, and the inspected example (CO2600062) is a *cannabis business*
  occupancy certificate; the workflow branches ("Construction CO" / "Housing CO") exist but the
  volume says routine residential completion is recorded as permit STATUS (`Final`/`Complete`),
  same inference class as Berkeley's finaled. **The earlier "Oakland's CO is documentary — not
  close" read was premature; retracted.** Verdict: Oakland completion ≈ status-based like
  Berkeley, with a niche CO instrument for use-changes, PLUS a `Certificate Issued` status whose
  scope (ReRoof certificates vs building COs?) needs calibration.
- **Public detail pages hide milestone dates.** The CO record's public view exposes only File
  Date + current Status — no issued/applied/finaled dates without login (unverified whether a
  free registered account reveals them). The export likewise carries **File Date only**. So
  Oakland's free layer is BROAD (all filings + live status) but SHALLOW (one date); Berkeley's
  CPRA xlsx is gated but DEEP (submittal/issuance/finaled dates). **An Oakland timelines/JN-I
  equivalent needs an Oakland CPRA for the dated feed** — the export alone can't do durations.

## Oakland parallel-project shape (if pursued)

1. Free live layer: monthly Download-results pulls (filings + status; snapshot-diff gives status
   TRANSITIONS over time — which partially reconstructs dates going forward, JN-G style).
2. CPRA layer: the Berkeley Request-1 template, Oakland-addressed, for the dated permit extract.
3. Calibration registry: permit-number grammar (RBC/RE/SEA/CO prefixes + year), record-type map,
   completion semantics (`Final` vs `Complete` vs `Certificate Issued`).
4. Reuse unchanged: assessor feed, CKAN oracle machinery, reconciliation method, curriculum.

**Sharpest insight from the probe:** a monthly Oakland export snapshot started NOW costs one click
a month and reconstructs the dates the public layer hides (status-transition timestamps accrue in
our snapshots even though Oakland won't show us its own). Same lesson as the license watcher:
snapshot first, analyze later.
