# v4 correction SOURCE inputs — the Berkeley calibration behind the raw→3,676 pipeline

**What this is.** The **versioned SOURCE data** for the v4 CO-reconciliation corrections — the local
calibration that takes the base ingested/classified state to the corrected **3,676 CO / 82,923 events**.
These were one `scratch/` cleanup from being lost; they are promoted here (2026-07-01) so the correction
notebooks can READ them as source. **The universal METHODS are curriculum-teachable; the DATA in this folder
is the Berkeley-specific calibration each method needs.**

**Provenance note.** Each file's per-row `note` column + this README carry provenance (CSVs stay clean data).
The corresponding gated-write scripts live in `scratch/2026-06-28/` and `scratch/2026-06-29/` (one-shot,
snapshot-guarded, idempotent-via-WHERE); the audit trail is `docs/audit/2026-06-{28,29}_*`. The reconciliation
is gated in JN-E against `data/baselines/reconciliation_baseline_2026-06-29.json`.

## The files
| file | drives | consumed by (scratch script) | net CO | universal METHOD | Berkeley CALIBRATION (this file) |
|---|---|---|---|---|---|
| `c2_count_recovery.csv` | C2 count-gap recovery (T1 + T2) | `c2_tranche1_write.py`, `c2_tranche2_write.py` | **+907 / +129** | count-from-WorkDescription (finaled-master, NULL net_units; noun-anchored) | the accepted/curated permits + recovered counts + live-work/sleeping conventions |
| `c3_tail_demote_list.json` | C3 ADU-tail ancillary demotion | `c3_tail_write.py` | **−17** | ancillary-demotion (solar/meter/panel ≠ dwelling; PROTECT the paired real ADU) | the 17 parcels: `{apn, demote, net, keep}` |
| `c3_shattuck_collapse.csv` | C3 phantom-master collapse | `c3_shattuck_write.py` | **−163** | phantom-master / phase-collapse (one-building-one-count) | 1951 Shattuck: keep Phase-1, demote Phase-2 |
| `c_multifamily_collapse.csv` | C-multifamily phase-collapse | `c_multifamily_collapse_write.py` | **−199** | phased-multifamily: demote foundation/podium, keep completion | the 3 buildings (+ the B2021-02423 40→41 bump) |
| `dedup47_permits.csv` | dedup47 duplicate finaled-master collapse | `dedup47_write.py` | **−47** | duplicate file-row collapse (overlapping CPRA exports) | the 4 double-counted permits |

**Regenerable vs source:** `c2_count_recovery.csv` and `c3_tail_demote_list.json` are *derived-then-curated* —
the RAW extraction regenerates (`c2_count_recovery.py` / `c3_tail_pairings_guard.py`), but the **accepted
subset + convention flags are SOURCE** and belong here. The three permit-list CSVs were **inline literals in
the scripts** (fragile) — externalized here as versioned source. All diagnostic/review/prototype CSVs
(`prototype_scores*`, `calibration_harvest*`, `*_review`, `dedup_584`, `jn_d_*`, `split_704`) stay in
`scratch/` (regenerable — NOT source).

## Order dependency (load-bearing)
One true coupling: **`c_multifamily_collapse` must run AFTER `c2_count_recovery`/tranche-2** — the
056-1928-019 row re-homes the convention flag/count that C2-T2 set on `B2021-04949` (the `bump 40→41` guard
assumes C2's value is present). Everything else is order-independent. event-dedup is CO-neutral.

## Pipeline-stage calibration (added 2026-07-02 — the JN-B/JN-F build + review hardening)
- **`event_dedup_holds.json`** — JN-B tier-2 HOLD groups (the universal dedup method never collapses
  these; a hold matching no group HALTS the stage — calibration drift must be loud).
- **`held_items.json`** — the HOLD-NOT-APPLY registry (the +147 permits, the C2 exclusion, the
  C1-phantom record). `assert_held()`/`apply_c2` read it; a hold is RESOLVED by editing this file
  with provenance, never by editing code.
- **`calibration_checksums.json`** — approved-set integrity pins (the original one-shots' 15/907-style
  HALT guards, re-externalized). The apply_* methods assert these BEFORE writing; a legitimate
  calibration change updates rows + checksums together in one reviewed edit.
- **`grounded_counts.csv`** — the held-item RESOLUTION ledger (per-permit document-grounded counts with
  source provenance; the 2026-07-02 harvest's +69). `apply_grounded_counts` refuses permits still held
  and never overwrites an existing count. This ledger is also the anti-re-derivation MEMORY: an
  adjudicated permit lives here as data, not as audit prose a future session must know to find.
- Consumers: **`scripts/v4/stage_methods.py`** (THE importable stage-method home) via the
  `notebooks/v4/JN-B_event_dedup.ipynb` → `JN-C_classify.ipynb` → `JN-F_corrections.ipynb` chain.

## APPLIED vs HELD
- **APPLIED (→ 3,676):** all five files above (event-dedup is a separate structural write, CO-neutral).
- **HELD — identified but deliberately NOT applied (a correction notebook must ENCODE these as hold-not-apply):**
  - **+147** — 3 multifamily ambiguous-completion buildings (`B2021-03302`/69, `B2018-03422`/55, `B2016-05139`/23):
    NO independent unit count in our WorkDescriptions → the city's number can't be adopted (oracle-not-source);
    Accela-blocked. **The headline held item** (see JN-H / the +147 harvest).
  - **event-dedup Tier-2 (3 groups)** + **Tier-3 (12 different-date finaled)** — held (substantive-differ / possible re-finals).
  - **C1 relabel** — a **PHANTOM** (considered and REJECTED: the 584 were already counted; applying it would double-count). Encode as considered-not-applied, never applied.
  - **B2020-03895** (#3, excluded from C2-T1); **~−150 residual** (open question, not a correction).

## Planning scope rulings (added 2026-09-29)
- **`planning_scope_rulings.csv`**: which Accela Planning records are housing developments under Gov. Code
  § 65589.5(h)(2) (units-stated sufficiency, John 2026-09-28). This replaces the `housing_rules.planning_filter`
  regex's scope judgement. `include` = 44 records the regex missed; `exclude` = 857 it wrongly admitted.
  Each row quotes the reader's reason and names its evidence file with a sha. The first reading (Jev) is
  `data/derived/planning_scope_evidence_2026-09-28.json` and the second reading (Sonnet) is
  `data/derived/planning_scope_second_read_2026-09-28.json`. Generated by `scripts/planning_scope_decision_set.py`;
  approved by John 2026-09-29. Records not listed keep the regex queue's answer; the 58 HOLD_UNKNOWN stay unresolved.
  **Not yet read by any build step.**

## Project grouping rulings (added 2026-09-30)
- **`project_rulings.csv`**: where the projects stage's rules (P1-P6 in `scripts/v4/build_projects.py`) cannot join a
  building to its approval, a ruling does, with the record's own words quoted. `group_structures` makes several
  buildings one project (Acheson Commons); `anchor_record` joins a building to the record that approved it (a
  merged site, a through-lot, an SB 35 application filed as a Pre-Application or Zoning Research Letter).
  **Only rows with `status=approved` apply**; `awaiting_sweep` / `needs_source` rows are open work, kept here so
  the gap stays visible. Seven approved by John 2026-09-30 (G001-G007).

## Funding ledger (added 2026-09-30)
- **`funding_ledger.csv`** — who funds each affordable project, from the CITY'S OWN primary records (Council
  resolutions, City Manager reports, the Measure O impacts report), never from the APR's `FIN_ASSIST_NAME`
  (the APR is the verification target). One row per funding ACTION: a recommendation, a reservation, an award or
  commitment, an adoption, an extension. The same money appears in several rows as it moves through those steps,
  so **never sum the amounts across rows**. Each row carries the document's City URL, the SHA-256 of the local
  copy (`data/raw/funding/`, PDFs gitignored) and a quote verified verbatim against the text. `status` says how
  far the action is confirmed: `recommended` rows still need the adopted resolution sourced.
  State tax-credit rows come from CTCAC's statewide *List of Projects* (through June 2026): one row per
  application for the annual federal credit (claimed over 10 years) and one for any state credit. `apn` is
  canonical (`to_canonical_apn`); `apn_check` records the standing stale-APN guard against the Feb-2026 assessor.
