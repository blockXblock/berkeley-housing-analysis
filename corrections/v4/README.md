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

## APPLIED vs HELD
- **APPLIED (→ 3,676):** all five files above (event-dedup is a separate structural write, CO-neutral).
- **HELD — identified but deliberately NOT applied (a correction notebook must ENCODE these as hold-not-apply):**
  - **+147** — 3 multifamily ambiguous-completion buildings (`B2021-03302`/69, `B2018-03422`/55, `B2016-05139`/23):
    NO independent unit count in our WorkDescriptions → the city's number can't be adopted (oracle-not-source);
    Accela-blocked. **The headline held item** (see JN-H / the +147 harvest).
  - **event-dedup Tier-2 (3 groups)** + **Tier-3 (12 different-date finaled)** — held (substantive-differ / possible re-finals).
  - **C1 relabel** — a **PHANTOM** (considered and REJECTED: the 584 were already counted; applying it would double-count). Encode as considered-not-applied, never applied.
  - **B2020-03895** (#3, excluded from C2-T1); **~−150 residual** (open question, not a correction).
