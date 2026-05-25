# CPRA source-data inventory

**Generated:** 2026-05-22T13:54:00
**Scope:** read-only file/grep search across the repo, the user's `~/Library/CloudStorage/`, and the user's home directory; cross-referenced against the ingestion scripts and logs.

## 1. CPRA source files identified

### A. The CPRA-2023-2025 source (authoritative)

| field | value |
|---|---|
| Path | `/Users/johngage/Library/CloudStorage/GoogleDrive-[redacted-email]/My Drive/Corridors/BP-downloads/BP_Annual Permit Report.xlsx` |
| Size | 2,839,652 bytes (~2.8 MB) |
| Modified | 2026-05-10T11:09:00 |
| File type | Microsoft Excel 2007+ (.xlsx) |
| Sheets | one sheet, named `BP_Annual Permit Report` |
| Header row | row 8 (per `cpra_dedup.load_cpra`: `pd.read_excel(input_path, header=7)`) |
| Lives outside the repo | yes (Google Drive mount) |

Folder context (same Google Drive directory):

```
~/Library/CloudStorage/GoogleDrive-[redacted-email]/My Drive/Corridors/BP-downloads/
└── BP_Annual Permit Report.xlsx   (only file in the folder)
```

Confirmed as the source by:
- Hardcoded `CPRA_FILE` constant at `scripts/migration/import_cpra_2023_2025.py:50`
- Both the 2026-05-11 and 2026-05-12 import logs explicitly log this path on every run: "INFO | CPRA file: /Users/johngage/Library/CloudStorage/.../BP_Annual Permit Report.xlsx"

### B. Possibly-related TSVs in `data/raw/accela_status/building/`

| path | size | mtime | header (first row) |
|---|---|---|---|
| `data/raw/accela_status/building/R2_permits_2023_2025.tsv` | 35,123 | 2026-04-13 11:03:35 | `Date\tPermit Number\tStatus\tAddress` |
| `data/raw/accela_status/building/R2_R3_permits_2023_2025.tsv` | 123,765 | 2026-04-13 11:03:35 | `Date\tPermit Number\tStatus\tAddress\tOccupancy Class` |

These match the year range in `import_cpra_2023_2025` (2023–2025) and are tabular permit data — but they are NOT referenced by `import_cpra_2023_2025.py`, `cpra_dedup.py`, or any other tracked script (grep returned no hits). They live in `data/raw/accela_status/` whose other contents are clipboard-pasted human-readable Accela record summaries. They were almost certainly produced from a different workflow (likely a manual Accela search-results export) and **are not the CPRA source ingested into v2**. Listed here for completeness.

### C. The CPRA-2018-2022 batch: REQUESTED, but no response file present

- `docs/cpra/2026-05-10_request_2018-2022.md` (8 KB, 2026-05-13) is a CPRA request document targeting the 2018–2022 timeframe.
- No 2018-2022 response file is present on disk (verified: `find ... '*2018*2022*' ... '*2018_2022*' ... '*2018-2022*'` returns only this request document).
- Implication: the 2018–2022 CPRA response either hasn't arrived yet, is stored elsewhere off-disk, or was received and consumed by a not-yet-built ingestion workstream. Worth confirming with the user.

## 2. Ingestion scripts identified

| path | size | mtime | role |
|---|---|---|---|
| `scripts/migration/import_cpra_2023_2025.py` | 34,018 bytes | 2026-05-13T14:53:43 | Authoritative ingestion script. Reads the xlsx via `load_cpra()` and writes to v2. Driven by decisions in `docs/migration/cpra_import_plan.md` (§14, §16). |
| `scripts/cpra_dedup.py` | 9,470 bytes | 2026-05-13T14:53:43 | Utility module imported by the migration script (`load_cpra`, `dedupe_permits`, `normalize_apn`, etc.). Also runnable as a standalone CLI for ad-hoc dedup. Its `__doc__` example paths are placeholders (`/path/to/...`); it has no production hardcoded path. |

Supporting artifacts (not ingestion scripts but related):

| path | role |
|---|---|
| `docs/migration/cpra_import_plan.md` | The import-plan reference cited by the ingestion script's docstring (§14, §16). |
| `docs/methodology/cpra_lessons_learned_2026-05-11.md` | Post-mortem from the first import. |
| `data/apr/cpra_import_results_2026-05-11.md` | Per-run summary, first import. |
| `data/apr/cpra_import_results_2026-05-12.md` | Per-run summary, second import. |
| `data/apr/cpra_2023_2025_comparison.md` | Comparison of imported data vs the source file. |
| `databases/berkeley_housing_v2_pre_cpra_import_2026-05-11.db` | Pre-import v2 backup (the snapshot taken just before the first CPRA import). |
| `scripts/migrations/2026-05-13_date_corrections.sql` | A SQL migration cleaning up post-CPRA date inconsistencies. |
| `scripts/migration/logs/cpra_import_2026-05-11*.log{,_summary.md}` | First-import logs (4 files: dry-run log, dry-run summary, live log, live summary). |
| `scripts/migration/logs/cpra_import_2026-05-12*.log{,_summary.md}` | Second-import logs (same 4-file pattern). |

## 3. Coverage map — which script reads which source?

| ingestion script | source file (per script + verified by logs) | resolves on disk? |
|---|---|---|
| `scripts/migration/import_cpra_2023_2025.py` | `~/Library/CloudStorage/GoogleDrive-[redacted-email]/My Drive/Corridors/BP-downloads/BP_Annual Permit Report.xlsx` | **yes** (verified — 2.8 MB, 2026-05-10) |
| `scripts/cpra_dedup.py` | (no hardcoded path; takes input via CLI arg or function parameter) | n/a — utility module |

Flags:

- **Source files referenced by scripts but not found on disk:** **none**. The single referenced path resolves.
- **Source files on disk not referenced by any script:** the two R2 TSVs in `data/raw/accela_status/building/` are tabular and year-tagged like the CPRA work but no script reads them. Likely orphans from a different (probably scraped) workflow.
- **Multiple scripts pointing at the same source:** no. Only one script reads the source.
- **CPRA-2018-2022:** request document exists; response file does not appear on disk.

## 4. Bottom-line summary and recommendation

**1 CPRA source file found, 1 ingestion script + 1 utility module found; the single source is fully mapped, no orphans on the script side.**

If you need to audit the CPRA ingestion against the original data:

- **Authoritative source:** `~/Library/CloudStorage/GoogleDrive-[redacted-email]/My Drive/Corridors/BP-downloads/BP_Annual Permit Report.xlsx` (2.8 MB, 2026-05-10, single sheet `BP_Annual Permit Report`, header row 8).
- **Loader:** `cpra_dedup.load_cpra(input_path)` — applies `pd.read_excel(..., header=7)` then adds derived columns (`norm_apn`, `master_permit`, `is_sub_permit`, `IssueYear`, `SubmitDate`).
- **Pre-import snapshot:** `databases/berkeley_housing_v2_pre_cpra_import_2026-05-11.db` (use this for diff-against-current-v2 audits without having to re-run the import).
- **Run-time logs and summaries:** under `scripts/migration/logs/cpra_import_2026-05-1{1,2}*` — six files for the first import day, six for the second.
- The two R2 TSVs in `data/raw/accela_status/building/` are NOT the CPRA source despite the year match; ignore them for the CPRA audit.
