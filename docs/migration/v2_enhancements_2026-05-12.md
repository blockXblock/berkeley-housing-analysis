# v2 Database Enhancements — 2026-05-12

Captures the v2 schema and data work performed on May 11-12, 2026.
Companion to the CPRA import work documented in cpra_lessons_learned_2026-05-11.md
and accela_cross_check_2026-05-12.md.

---

## Summary of changes

| Change | Type | Detail |
|--------|------|--------|
| APN audit + corrections | Data | 4 mismatches fixed, 6 missing-APN parcels linked |
| CPRA 2023-2025 import | Data | 121 permits, 2 new projects, 55 finaling events |
| Description backfill | Schema + Data | Added project_versions.description; 175 of 179 backfilled from v1 |
| Project 141 permit reconstruction | Data | B2024-01268 + 66 events linked |
| Fees table | Schema + Data | New fees table + vocabulary_fee_categories; 441 rows backfilled, $14.1M |
| Sidebar Accela attributions | Data | 2 UNKNOWN-permit fee batches resolved |

State after these changes: v2 has 240 permits, 181 projects, 2787+ events, 441 fees.

---

## 1. Description backfill

### Background

Phase B migration created v2.project_versions but did not include a description column.
v1.projects.description had rich narrative content (avg 221 chars, range 3-833) for 175 of 179
projects, capturing zoning law, height, units, density bonus context — essential for the
Explorer to differentiate projects beyond their addresses.

### Schema change

```sql
ALTER TABLE project_versions ADD COLUMN description TEXT;
```

### Backfill

Single UPDATE statement with ATTACH to v1, joined by project_id (verified IDs match between
v1 and v2 via sample check of projects 1, 100, 153, 179).

Backup created at `databases/berkeley_housing_v2_pre_description_backfill_2026-05-12.db`
before schema change.

### Validation

- 175 of 179 current versions have descriptions (matches v1 exactly)
- Average length 221 characters (matches v1)
- Sample text verification: project 133 (Core Spaces) description character-for-character
  identical between v1 and v2
- New CPRA-imported projects (183, 184) correctly have NULL descriptions (legitimate;
  they are not in v1)

### Mapping for Explorer rewrite

v1.projects.description → v2.project_versions.description WHERE is_current = 1

---

## 2. Project 141 permit reconstruction

### Background

Project 141 (2016 Ashby Ave, CHDC 50-unit affordable housing) had:
- 65 events in v1.permit_events referencing permit B2024-01268
- 1 fee row in v1.permit_fees: $2,192,720.87 total
- ZERO rows in v1.building_permits or v1.project_permits for B2024-01268
- ZERO rows in v2.permits for B2024-01268

Sidebar Accela verification confirmed B2024-01268 exists in Accela as "Issued" 50-unit BEMP.
CPRA 2023-2025 delivery did not include this permit (verified via direct xlsx search) —
representing a real CPRA scope gap.

### Approach

Reconstructed the missing permit row from event data with explicit provenance:

```sql
INSERT INTO permits (
  project_id, source_system, permit_number, permit_type_id, permit_status_type_id,
  filed_date, issued_date, description, notes
) VALUES (
  141, 'v1_events_reconstruction', 'B2024-01268', 5, 5,
  '2024-03-20',  -- earliest event (Plan Distribution)
  '2026-03-26',  -- "Issued" event date
  '100% affordable housing, 50 units. Community Housing Development Corp, Lowney Architecture.',
  'Permit record reconstructed 2026-05-12 from v1 permit_events (65 events) and v1 permit_fees
   ($2,192,720.87 total). v1 had events and fees referencing this permit but no permit-table row.
   CPRA 2023-2025 delivery did not include this permit. Reconstruction draws dates from events.'
);
```

Then linked all 66 NULL-permit_id events for project 141 to the new permit row.

### Validation

- New permit id: 240
- 66 of 66 events now linked
- FK integrity clean

### Honest caveat

This is reconstructed data. `source_system = 'v1_events_reconstruction'` marks it clearly.
If a future CPRA refresh or direct Accela lookup provides the authoritative permit record,
we should update or replace this row with full provenance.

---

## 3. Fees table

### Background

v1 had `permit_fees` with 441 rows totaling $14,125,974.51. The Explorer reads this for its
fees tab. v2 had no equivalent table — would have lost this data shape for the rewrite.

Decision: extend v2 with a normalized fees table that supports both v1's mostly-aggregate data
AND future itemized fee data from CPRA. (See discussion in conversation history.)

### Schema

```sql
CREATE TABLE vocabulary_fee_categories (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  display_name TEXT,
  notes TEXT
);

CREATE TABLE fees (
  id INTEGER PRIMARY KEY,
  permit_id INTEGER REFERENCES permits(id),       -- nullable; FK to permits
  project_id INTEGER REFERENCES projects(id),     -- nullable; FK to projects
  permit_number_text TEXT,                        -- always populated; fallback identifier
  fee_category_id INTEGER REFERENCES vocabulary_fee_categories(id),
  fee_description TEXT,
  amount REAL NOT NULL,
  paid_date TEXT,
  is_aggregate INTEGER DEFAULT 0,                 -- 1 = "Total Paid" lump; 0 = itemized
  source_system TEXT,
  source_url TEXT,
  source_document_id INTEGER REFERENCES documents(id),
  asserted_by TEXT,
  asserted_at TEXT,
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fees_permit ON fees(permit_id);
CREATE INDEX idx_fees_project ON fees(project_id);
CREATE INDEX idx_fees_permit_number ON fees(permit_number_text);
```

### Vocabulary entries (14 categories)

total_aggregate, total_aggregate_building, building_permit, plan_check, impact_fee,
school_fee, housing_trust, inclusionary, zoning_planning, design_review, landmark,
outstanding, other, unknown

### Backfill from v1.permit_fees

441 rows inserted with the following logic:
- permit_id: LEFT JOIN on permit_number (60 of 122 v1 permits match v2 permits = 49%)
- project_id: from v1.permit_fees.project_id directly
- permit_number_text: always carry forward v1's permit_number value
- fee_category_id: CASE expression mapping fee_description and permit prefix:
  - "Total Paid" → total_aggregate (is_aggregate=1)
  - "Total Paid (building)" → total_aggregate_building
  - "Outstanding" → outstanding
  - Blank desc + ZP/PLN/AUP/P prefix → zoning_planning
  - Blank desc + DR prefix → design_review
  - Blank desc + LM prefix → landmark
  - Blank desc + permit_number = "UNKNOWN" → unknown
  - Blank desc + B prefix → other
- source_system: 'v1_migration'
- asserted_by: 'fees_backfill_2026-05-12'
- notes: 'Migrated from v1.permit_fees on 2026-05-12. Original v1 row id: N'

### FK violations encountered and resolved

Two fees rows (id 36, 148) initially had FK violations because v1 referenced a phantom
project_id=29 (2138 Kittredge ZP permits in events/fees with no corresponding v1.projects row).
v2 has 2138 Kittredge as projects 113 and 118 (amendment and original entitlement, both real
SB-330 versions of the same development). Fees reattributed to project 113 (the active
amendment with the actual building permit), provenance captured in notes.

### Sidebar Accela investigations

Two UNKNOWN-permit fee batches resolved via sidebar Accela lookups:

**Project 157 (2587 Telegraph, Gilbane 52-unit):**
8 rows totaling $1,759,549.01 attributed to permit 140 (B2024-03583, Phase I BEMP).
Per sidebar Accela findings, 2587 Telegraph has 5 master permits; bulk fees attach to
Phase I main permit per Berkeley typical pattern.

**Project 143 (2902 Adeline, Realtex 54-unit):**
4 rows totaling $751,490.65 attributed to permit 127 (B2021-04232, primary BEMP).
Confidence HIGH per sidebar analysis.

### Validation

- 441 rows ✓
- $14,125,974.51 total ✓ (matches v1 to the penny)
- FK integrity clean
- Distribution:
  - total_aggregate: 126 rows, $11,653,776.94
  - zoning_planning: 258 rows, $800,027.37
  - unknown: 48 rows, $406,530.81 (62 fewer than initial 110 after attribution work)
  - total_aggregate_building: 1 row, $1,259,375.39
  - landmark: 2 rows, $5,570
  - outstanding: 1 row, $250
  - other: 5 rows, $444

### Honest gaps

74 fee rows still have `permit_number_text = 'UNKNOWN'`:

| Project | Rows | $ Amount | Attribution Status |
|---------|-----:|---------:|-------------------|
| 157 (2587 Telegraph) | 8 | $1,759,549.01 | ✓ ATTRIBUTED (permit 140) |
| 133 (2128 Oxford / Core Spaces) | 31 | $755,449.02 | NOTED (B2024-00318 probable, not in v2) |
| 143 (2902 Adeline) | 4 | $751,490.65 | ✓ ATTRIBUTED (permit 127) |
| 153 (1701 San Pablo) | 25 | $57,612.60 | UNATTRIBUTED |
| 152 | 5 | $37,710.60 | UNATTRIBUTED |
| (NULL project) | 1 | $3,734.00 | UNATTRIBUTED |

The 62 unattributed UNKNOWN rows ($854,506.22 total) can be addressed in future sessions
via sidebar Accela investigations (one per project, ~5 min each).

---

## 4. CPRA scope gaps identified

This work surfaced specific permits that are in Accela but were NOT in the CPRA 2023-2025
delivery — representing a real CPRA scope concern:

| Project | Permit | Significance |
|---------|--------|--------------|
| 141 (2016 Ashby) | B2024-01268 | 50-unit Issued 2024, $2.19M fees in v1 |
| 157 (2587 Telegraph) | B2024-03056 (demo, Finaled 6/20/2024) | Minor; not in v2 |
| 133 (2128 Oxford) | B2024-00318 | Phase 1 Foundation, primary fee permit |
| 133 (2128 Oxford) | B2025-05345 | Phase 2 BEMP (Pending Payment) |
| 133 (2128 Oxford) | B2025-05341 | Shoring |
| 133 (2128 Oxford) | B2025-03675 | Demolition |
| 143 (2902 Adeline) | B2026-01311 | 2026 electrical (outside CPRA window) |
| 143 (2902 Adeline) | B2021-05386 | Demo (Closed Expired) |

Action: when the 2018-2022 CPRA response arrives (sent 2026-05-10), spot-check whether
similar gaps appear and consider a follow-up to City Clerk asking about filter scope.

---

## 5. Backups created during this work

Each major write was preceded by a snapshot backup (kept locally, gitignored):

- `databases/berkeley_housing_v2_apr22_baseline.db` (May 7)
- `databases/berkeley_housing_v2_pre_cpra_import_2026-05-11.db` (May 11)
- `databases/berkeley_housing_v2_pre_description_backfill_2026-05-12.db` (May 12 10:54)
- `databases/berkeley_housing_v2_pre_recon_2026-05-12.db` (May 12 12:06)
- `databases/berkeley_housing_v2_pre_fees_2026-05-12.db` (May 12 12:36)

Each represents a recoverable state.

---

## 6. Pending work

Tracked for next session(s):

1. **Explorer rewrite against v2** — query mapping complete, script not yet written. ~4-6 hours.
2. **Project 63 demolition-vs-construction co_issued query** — handle in Explorer rewrite.
3. **2018-2022 CPRA response processing** — expected ~10 days from 2026-05-10.
4. **4 UC projects without APNs** — schema decision pending (NULLABLE apn vs marker values).
5. **11 format-error APNs** — minor cleanup.
6. **Project 133 + 4 missing permits** — backfill from sidebar findings or future CPRA.
7. **62 remaining UNKNOWN-permit fee attributions** — incremental sidebar work.

---

## 7. Lessons captured

For reuse in future v2 work and for other cities adapting this approach:

- **Always PRAGMA table_info before writing queries against unfamiliar tables.** Schema
  assumptions caused multiple failed queries tonight (projects.apn, permits.source,
  permits.units_added, project_events.updated_at, v1.project_permits.address_display).
- **Backup before every schema-changing operation.** ALTER TABLE is not rollback-safe
  in SQLite.
- **v1 had subtle data quality issues** (phantom project_ids, permit numbers as text, 2138
  Kittredge entity ambiguity) that surfaced during migration but weren't blocking. Documenting
  the resolutions in notes preserves the decision trail.
- **CPRA's coverage is narrower than expected.** Multi-unit affordable projects (CHDC at
  2016 Ashby, Core Spaces at 2128 Oxford) are absent from the 2023-2025 delivery despite
  being in scope. This is a real concern to surface with the City Clerk.
- **Sidebar Accela investigations are useful but expensive.** Time-box and target high-value
  cases (the 12 attributions done tonight resolved $2.5M of UNKNOWN exposure; the remaining
  62 rows represent ~$850K and can be done incrementally).

---

*Document compiled 2026-05-12 by Claude/John Gage. Captures v2 enhancements completed
2026-05-11 and 2026-05-12.*
