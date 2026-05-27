# HCD APR mirror — table coverage gaps

**Date:** 2026-05-27
**Origin:** discovered during Phase A investigation for the cycle-aware D5/D6 work
**Scope of this note:** capture the gap, not resolve it. ~30 minutes.

## What we have

`databases/hcd_apr_mirror.db` currently contains 7 data tables plus `_pull_metadata`:

| table | rows (Berkeley) | purpose |
|---|---|---|
| `table_a` | (varies by year) | annual project listing, unit-category-level |
| `table_a2` | 216–474/year (CY 2018–2025) | per-permit detail — this is the working table for D5/D6 |
| `table_d` | 41–184/year | Programs reported under the Housing Element (mostly text); has `APPLICABLE_CYCLE` column but it's blank for CY 2018–2024 |
| `table_f` | (small) | units developed without RHNA credit (e.g., student housing exemptions). Uses `JURISDICTION_NAME` not `JURIS_NAME` — schema drift relative to A/A2/D |
| `table_i` | n/a | inventory site data |
| `table_k` | n/a | locally-adopted policies |
| `table_l` | n/a | historic site reuse (has `HISTORIC_SITE_PERIOD` column — unrelated to RHNA cycle) |

## What we don't have

Per the build script's intent (`scripts/build_hcd_mirror.py`, per session memory) the mirror was supposed to pull 12 tables: **A, A2, C, D, E, F, F2, G, H, I, K, L**. Five+ are missing:

| table | what it captures | significance |
|---|---|---|
| **`table_b`** | **RHNA progress (the "scoreboard" — units permitted by income tier, by year, with a Projection Period column)** | **Critical gap. Section below.** |
| `table_c` | Sites Inventory annual update | medium — needed for entitlement-pipeline cross-reference |
| `table_e` | Commercial Development Bonus | low — niche reporting |
| `table_f2` | (variant of F) | low |
| `table_g` | Locally-owned surplus sites | medium |
| `table_h` | Locally-owned sites at risk | medium |

The build script never had `table_b` in its pull list (grep against `scripts/build_hcd_mirror.py` returns zero hits for `table_b`/`TABLE_B`/single-`'B'`/single-`"B"`). So this is an **original-design gap**, not a regression.

## Why `table_b`'s absence matters

Table B is HCD's RHNA-progress accounting table. It has a structure roughly like:

```
Income Level | RHNA | Projection Period | 2023 | 2024 | ... | Total | Remaining
```

The **Projection Period column** is where the ~492-unit CY 2024 total (per `docs/berkeley_2024_apr_comparison.md`) lives. Without Table B in the mirror:

1. **The 492 figure is not independently verifiable from our queryable data.** It exists only in:
   - The PDF submission Berkeley uploaded to HCD
   - The rendered `docs/berkeley_2024_apr_comparison.md` (a manually-typed comparison)
   - HCD's CKAN feed (if Table B is published there — see open question below)

2. **Our cycle-aware D5/D6 work computes a parallel projection-period flag from `BP_ISSUE_DT1` dates in Table A2.** D5's per-row classification gives 363 unique permits with `bp_in_projection_period=True` (BP dates in 2022-06-30 .. 2023-01-30). This is a **bottom-up reconstruction**, not a Table B audit.

3. **Cross-checking the 363 figure against Berkeley's reported 492 requires getting Table B in the mirror** — at which point we could segment by income tier and compare per-tier (the breakdown is VLI 25 / LI 0 / MOD 25 / AMI 442 = 492 per the comparison doc).

## Open question — CKAN feed gap vs HCD PDF-only

Two hypotheses for why Table B is absent from the mirror:

**Hypothesis A: HCD's CKAN datastore exposes Table B and we just don't pull it.** Resolution: extend `scripts/build_hcd_mirror.py` to add Table B's CKAN resource ID. This is a code change, not a data-availability change.

**Hypothesis B: HCD's CKAN datastore does NOT expose Table B — it lives only inside the submission PDFs that jurisdictions upload.** Resolution: the only way to populate Table B locally is to parse the submission PDFs ourselves. This is a much heavier lift (PDF parsing, schema reconstruction, multi-jurisdiction inconsistency).

**Not resolving now. Flagging for future work.** The first diagnostic step would be:
- Hit HCD's CKAN catalog API for the same datastore the mirror script uses, list available resources, and check whether a Table B equivalent appears
- Or check HCD's published data documentation for which tables they distribute via CKAN

**Owner:** TBD. Probably becomes load-bearing the next time someone asks "what's Berkeley's actual projection-period figure?" — at which point we'll need to either parse the PDF or extend the mirror.

## Related artifacts

- `scripts/build_hcd_mirror.py` — the script that defines what we pull
- `databases/hcd_apr_mirror.db` — the resulting SQLite mirror
- `docs/berkeley_2024_apr_comparison.md` — where the 492 figure currently lives
- `04_reporting/D5_apr_from_cpra.ipynb` — bottom-up projection-period reconstruction
- `output/D6/cycle_segmented_summary.csv` — cycle/projection-period totals derived from Table A2
