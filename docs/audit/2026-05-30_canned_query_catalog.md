# Canned Query Catalog for CPRA Datasette Publication

Drafted 2026-05-30 morning, ahead of Track 3 implementation. These queries will be encoded in `datasette-deploy/metadata.json` once `databases/cpra_permits.db` is built. They become both:

- Clickable named URL endpoints in the deployed Datasette instance
- Worked examples in `docs/citizen_apr.html` (the new public page)
- Reference SQL in `docs/audit/hypothetical_accela_api.md` (Track 5)

The catalog spans four tiers based on what data the query requires.

## Tier 1: Directly from CPRA permits

These queries work against `databases/cpra_permits.db` alone. They become available as soon as `scripts/build_cpra_db.py` produces the SQLite.

### 1. New housing units permitted by year

```sql
SELECT
  strftime('%Y', issuance_date) AS year,
  SUM(units_added) AS units_permitted,
  COUNT(*) AS permit_count
FROM permits
WHERE work_type = 'New'
  AND units_added > 0
GROUP BY year
ORDER BY year;
```

### 2. ADU production by year

```sql
SELECT
  strftime('%Y', issuance_date) AS year,
  SUM(units_added) AS adus_permitted,
  COUNT(*) AS adu_permits
FROM permits
WHERE adu = 'Yes'
  AND work_type = 'New'
  AND units_added > 0
GROUP BY year
ORDER BY year;
```

### 3. Projects with 5+ units permitted but not yet completed

```sql
SELECT
  permit_number, parcel_number,
  street_number || ' ' || street_name || ' ' || street_type AS address,
  units_added,
  issuance_date,
  finaled_status
FROM permits
WHERE work_type = 'New'
  AND units_added >= 5
  AND (finaled_status IS NULL OR finaled_status != 'Finaled')
ORDER BY units_added DESC;
```

### 4. Demolitions by year

```sql
SELECT
  strftime('%Y', issuance_date) AS year,
  SUM(units_removed) AS units_demolished,
  COUNT(*) AS demolition_permits
FROM permits
WHERE work_type = 'Demolition'
  AND units_removed > 0
GROUP BY year
ORDER BY year;
```

### 5. Average job valuation per new unit by year

```sql
SELECT
  strftime('%Y', issuance_date) AS year,
  ROUND(AVG(job_valuation * 1.0 / units_added), 0) AS avg_value_per_unit,
  SUM(units_added) AS units
FROM permits
WHERE work_type = 'New'
  AND units_added > 0
  AND job_valuation > 0
GROUP BY year
ORDER BY year;
```

### 6. Time from submittal to issuance by year

```sql
SELECT
  strftime('%Y', issuance_date) AS issued_year,
  ROUND(AVG(julianday(issuance_date) - julianday(submittal_date)), 0) AS avg_days_submittal_to_issuance,
  COUNT(*) AS permits_in_year
FROM permits
WHERE submittal_date IS NOT NULL
  AND issuance_date IS NOT NULL
  AND work_type = 'New'
GROUP BY issued_year
ORDER BY issued_year;
```

### 7. Largest new housing projects (lifetime)

```sql
SELECT
  permit_number,
  street_number || ' ' || street_name || ' ' || street_type AS address,
  units_added,
  issuance_date,
  finaled_status,
  work_description
FROM permits
WHERE work_type = 'New'
  AND units_added >= 20
ORDER BY units_added DESC
LIMIT 50;
```

### 8. Single-family vs. multifamily new construction by year

```sql
SELECT
  strftime('%Y', issuance_date) AS year,
  occ_type,
  SUM(units_added) AS units,
  COUNT(*) AS permits
FROM permits
WHERE work_type = 'New'
  AND units_added > 0
GROUP BY year, occ_type
ORDER BY year, units DESC;
```

## Tier 2: CPRA joined with parcels and zoning

Requires a `parcels` table in the database (or attached) with at minimum `apn`, `zoning_code`, `council_district`, `latitude`, `longitude`. The project has parcel data in `databases/berkeley.db` (29,024 parcels with zoning per project history). Bringing this into the CPRA database — or attaching it at query time — enables these queries.

### 9. ADU production by city council district

```sql
SELECT
  p.council_district,
  strftime('%Y', perm.issuance_date) AS year,
  SUM(perm.units_added) AS adus_permitted
FROM permits perm
JOIN parcels p ON perm.parcel_number = p.apn
WHERE perm.adu = 'Yes'
  AND perm.work_type = 'New'
  AND perm.units_added > 0
GROUP BY p.council_district, year
ORDER BY p.council_district, year;
```

### 10. Housing units completed in commercial zones by year

```sql
SELECT
  strftime('%Y', perm.finaled_date) AS completion_year,
  p.zoning_code,
  SUM(perm.units_added) AS units_completed
FROM permits perm
JOIN parcels p ON perm.parcel_number = p.apn
WHERE perm.finaled_status = 'Finaled'
  AND perm.units_added > 0
  AND p.zoning_code LIKE 'C-%'
GROUP BY completion_year, p.zoning_code
ORDER BY completion_year, units_completed DESC;
```

Note: Berkeley's actual commercial zoning prefixes (C-1, C-N, C-DMU, etc.) need verification against the parcel data; adjust the LIKE pattern accordingly.

### 11. Permits and units by council district, cumulative

```sql
SELECT
  p.council_district,
  SUM(CASE WHEN perm.work_type = 'New' THEN perm.units_added ELSE 0 END) AS new_units_permitted,
  SUM(CASE WHEN perm.work_type = 'Demolition' THEN perm.units_removed ELSE 0 END) AS units_demolished,
  COUNT(DISTINCT perm.parcel_number) AS active_parcels
FROM permits perm
JOIN parcels p ON perm.parcel_number = p.apn
GROUP BY p.council_district
ORDER BY new_units_permitted DESC;
```

### 12. Density bonus projects (large multifamily, text-pattern detection)

```sql
SELECT
  perm.permit_number,
  perm.street_number || ' ' || perm.street_name || ' ' || perm.street_type AS address,
  p.council_district,
  p.zoning_code,
  perm.units_added,
  perm.issuance_date,
  perm.work_description
FROM permits perm
JOIN parcels p ON perm.parcel_number = p.apn
WHERE perm.work_type = 'New'
  AND perm.units_added >= 10
  AND (perm.work_description LIKE '%density bonus%'
       OR perm.work_description LIKE '%state density%'
       OR perm.work_description LIKE '%SB 35%'
       OR perm.work_description LIKE '%SB 9%')
ORDER BY perm.units_added DESC;
```

### 13. Pipeline by zoning district, all stages

```sql
SELECT
  p.zoning_code,
  SUM(CASE WHEN perm.finaled_status = 'Finaled' THEN perm.units_added ELSE 0 END) AS completed,
  SUM(CASE WHEN perm.issuance_status = 'Issued' AND perm.finaled_status != 'Finaled'
           THEN perm.units_added ELSE 0 END) AS under_construction,
  COUNT(DISTINCT perm.parcel_number) AS parcels
FROM permits perm
JOIN parcels p ON perm.parcel_number = p.apn
WHERE perm.work_type = 'New'
GROUP BY p.zoning_code
ORDER BY completed DESC;
```

## Tier 3: Cross-domain (roadmap, require additional data ingestion)

These are valuable journalism questions but require data the CPRA pull does not provide. Listed for transparency about what the project currently cannot answer and what additional data ingestion would enable.

### 14. Number of beds by council district

Requires bed-count data. CPRA tracks dwelling units, not beds. Berkeley may track this separately for dorm/SRO projects via Use Permit conditions; would need to ingest Use Permit data. **Roadmap.**

### 15. Sales tax revenue by commercial zone

Requires California Department of Tax and Fee Administration (CDTFA) data joined with Berkeley parcel-level commercial zone classification. CDTFA publishes by jurisdiction, not by zone; apportionment to zones would require methodology. **Roadmap, possibly partnership with CDTFA or Berkeley Finance.**

### 16. Affordability tier breakdown (deed-restricted vs. non-deed-restricted, by income tier)

Requires Density Bonus Eligibility Statements and Affordability Covenants filed with planning. Not in CPRA pull. Would require either a separate CPRA request or per-project research from planning records. ABAG's 30/30/30/10 methodology for ADU income-tier distribution could be applied as a default. **Roadmap.**

### 17. Construction worker permits / certified payroll

Useful for tracking project labor practices. Public records but separate dataset from CPRA. **Roadmap.**

### 18. Project timeline reconciliation: planning approval → permit issuance → completion

Requires joining CPRA permits to entitlement records (planning approvals, environmental review). Berkeley has separate planning records that would need ingestion. **Partial — some entitlement dates appear in HCD APR data, but the granular timeline isn't in CPRA.**

## Tier 4: Reconciliation against Berkeley's HCD submission

These queries illuminate the project's audit work. They require either the HCD mirror to be joined (via `ATTACH DATABASE`) or summary data to be embedded in the CPRA database.

### 19. Projects in CPRA data not in any year of Berkeley's HCD submission

```sql
-- Requires: ATTACH DATABASE 'databases/hcd_apr_mirror.db' AS hcd;
SELECT
  perm.permit_number,
  perm.street_number || ' ' || perm.street_name || ' ' || perm.street_type AS address,
  perm.units_added,
  perm.issuance_date
FROM permits perm
WHERE perm.work_type = 'New'
  AND perm.units_added > 0
  AND perm.permit_number NOT IN (
    SELECT JURS_TRACKING_ID FROM hcd.table_a2
    WHERE JURIS_NAME = 'BERKELEY' AND JURS_TRACKING_ID IS NOT NULL
  )
ORDER BY perm.units_added DESC;
```

This surfaces the 4 confirmed under-reports plus any others in the CPRA data: 2328 Channing (12u), 2512 Regent (9u), 2028 Essex (1u), 707 Cragmont (1u).

### 20. CY 2024 reconciliation summary: our reproduction vs. Berkeley's HCD submission

```sql
SELECT
  'Berkeley HCD submission' AS source,
  708 AS co_units,
  731 AS bp_units,
  '228 rows' AS notes
UNION ALL
SELECT
  'Our CPRA reproduction (post all fixes)' AS source,
  SUM(CASE WHEN finaled_status = 'Finaled'
            AND strftime('%Y', finaled_date) = '2024'
       THEN units_added ELSE 0 END) AS co_units,
  SUM(CASE WHEN strftime('%Y', issuance_date) = '2024'
       THEN units_added ELSE 0 END) AS bp_units,
  'Gap: 9% CO, 21% BP, fully attributed at row level' AS notes
FROM permits
WHERE work_type = 'New' AND units_added > 0;
```

### 21. Bijection reconciliation ledger summary across 8 years

Requires summary tables from `data/audit/cy{year}_reconciliation/`. Either materialize these as a SQLite table in the CPRA database, or attach the HCD mirror and JOIN.

```sql
-- Conceptual; exact form depends on whether bijection ledgers are
-- ingested into the CPRA database or queried separately.
SELECT
  year,
  hcd_co_total,
  d5_co_total,
  hcd_co_total - d5_co_total AS gap_units,
  ROUND(100.0 * (hcd_co_total - d5_co_total) / hcd_co_total, 1) AS gap_percent
FROM bijection_summary
ORDER BY year;
```

## Implementation notes

**Plugin requirements for Datasette deployment:**
- `datasette-cluster-map` (already installed) — automatically renders maps for any query returning `latitude` / `longitude` columns. Tier 2 queries with parcels join become map-renderable.
- `datasette-leaflet` (already installed) — base map tiles for the cluster-map plugin.
- `datasette-geojson` (already installed) — adds `.geojson` export option per query.

**metadata.json structure:**
Each query above becomes a canned query entry. Title, description, SQL, and optionally `fragment` for default sort or pagination.

**Map-enabling pattern:**
Any Tier 2 query that includes `p.latitude, p.longitude` in its SELECT becomes a map. Add these columns to relevant queries.

**Performance considerations:**
- Indexes on `parcel_number`, `issuance_date`, `finaled_date`, `work_type`, `adu` (per Track 3 schema)
- For Tier 2 queries, additional index on `parcels.apn` if not already PK
- Tier 4 queries that ATTACH the HCD mirror are slower than queries within a single database; acceptable for an audit tool, less so for journalist exploration

**Tier-by-tier rollout for `metadata.json`:**
- Phase 1 (today): all Tier 1 queries (~8). Available immediately upon SQLite build.
- Phase 2 (today, if parcels table integration lands): all Tier 2 queries (~5). Requires resolving how parcels join into the published database (embed vs. attach).
- Phase 3 (today): all Tier 4 queries (~3). Requires deciding how HCD mirror gets to Datasette (committed alongside cpra_permits.db, or attached at query time).
- Phase 4 (roadmap): Tier 3 queries appear as documentation only with "additional data required" notes.
