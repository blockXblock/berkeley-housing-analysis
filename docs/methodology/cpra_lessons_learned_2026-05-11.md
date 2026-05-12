# Lessons Learned: Public Records Requests for Civic Housing Data

**Project:** Berkeley Housing Pipeline
**Date documented:** 2026-05-11
**Author:** John Gage, Open Public Data
**Repository:** github.com/blockXblock/berkeley-housing-analysis

## Audience

This document is written for:
1. **Other cities** wishing to clone this approach — understanding the workflow before starting
2. **Data science classes** using civic records work as a teaching case
3. **This project, going forward** — guidance for receiving the 2018-2022 CPRA response

---

## Project context

The Berkeley Housing Pipeline tracks housing development projects in Berkeley, California, from initial application through entitlement to building permit issuance to certificate of occupancy. As of May 2026 it covers 179 projects representing about 14,000 dwelling units, and is published as berkeleybuild.com with full data in a SQLite database (v2 schema, normalized).

A core challenge has been keeping the database current with city permit activity. Berkeley uses the Accela permitting system, but the public-facing portal does not expose bulk export. This forced reliance on either manual permit-by-permit scraping or Public Records Act (CPRA in California; FOIA-equivalent in other jurisdictions) bulk requests.

In April 2026, we submitted a CPRA request for all residential building permits issued 2023-2025. The City fulfilled in 10 days, providing an Excel export of 14,143 permits. The trajectory of analyzing, cleaning, and importing this data into our database exposed errors we are documenting here.

---

## The trajectory

This is what actually happened, in order. Each step represents a real learning opportunity.

### 1. We discovered we did not have what we claimed to have

The project documentation said we ran an "Accela scraper." Investigation showed this was a manual workflow: a Python script that generated Accela search URLs as a CSV checklist, plus parsing scripts for processing-status text the user manually copy-pasted from the browser. No actual scraping occurred. The data freshness depended on someone sitting down and doing the manual rounds. The last manual round had been over a month earlier.

**Lesson:** Verify what your data pipeline actually does before claiming it as automated. Aspirational naming ("scraper") obscures real limitations.

### 2. The CPRA request as initially drafted was imperfect

The request asked for fourteen fields including Certificate of Occupancy date, applicant/contractor name, and total fees assessed. The response delivered 26 columns including most requested fields, but:

- CO Date column was empty for every row
- Applicant name was not included as a column
- Total fees assessed was not included as a column

Investigation revealed that Berkeley uses "finalized date" as terminology equivalent to "certificate of occupancy date." The CPRA staff likely searched for a column literally named "CO Date" in Accela and found none, so left it blank. The actual data was available under "Finaled Date."

**Lesson:** Cities use their own internal terminology. Field names in your request matter. When a field could have multiple internal names, list both: "Certificate of occupancy date / 'finalized' date (please include whichever field Accela maintains for permit completion)."

### 3. The bulk data required immediate deduplication

The 14,143 rows were not 14,143 distinct projects. Each construction project generates multiple permits: a primary building permit plus sub-permits for electrical, plumbing, mechanical, fire, signage, and revisions. Each sub-permit inherits the master permit's unit count in the Accela export, leading to dramatic over-counting:

- Naive analysis: 16,357 multi-unit (R-2) "units" 2023-2025
- After deduplication: 2,387 units across 64 master permits

The 6x inflation came from sub-permit proliferation. The largest single project (1951 Shattuck Ave, 163 units, 25 sub-permits) accounted for 4,075 of the inflated "units" from one real project.

**Lesson:** Bulk permit exports include all permits, not just master permits. Deduplication is required before analysis. Identify sub-permits by:
- Permit number suffixes (`-REV`, `-DEF`, `-ADD`)
- Shared APN with another permit on the same date
- Work type indicators (Electrical, Plumbing, etc. vs. Building)

The right next ask in any CPRA request: **a parent permit reference column**, if the city's permit system tracks it. This makes deduplication trivial. Without it, suffix parsing is fragile.

### 4. We discovered our existing database had data quality problems

When matching CPRA permits to our existing 179 projects, mismatches surfaced. An APN audit found:

- **4 APN mismatches** where the stored APN pointed to a different parcel than the project's address
- **11 format errors** in APN strings (abbreviated forms, missing spaces, dash-separated variants)
- **10 missing APNs** (NULL values)

The most striking: project 153 (1701 San Pablo Ave) had an APN that actually belonged to 1740 San Pablo Ave — a different building. The migration from an older database had carried this error forward without detection.

**Lesson:** External data delivery is a chance to audit your existing database, not just import new data. Cross-reference APNs against an authoritative source. For Berkeley, that source is the city's ArcGIS parcel layer; other cities will have equivalents (Open Data portals, county assessor APIs).

The ArcGIS verification revealed that 1701 San Pablo's correct APN is `058 212901700` (long form) or `58-2129-17` (abbreviated). v1's `058 212701403` was the 1740 parcel's APN, misattributed.

### 5. We made false assumptions about our own schema

In the import process, we made multiple wrong assumptions about column names in the v2 database:

- `projects.apn` does not exist — APNs are in `parcels.apn`, linked via `project_parcels`
- `permits.source` does not exist — provenance field is `permits.source_system`
- `permits.units_added` does not exist — unit data is in `unit_program` and `project_versions`
- `permits.work_description` does not exist — the column is `permits.description`
- `permits.job_value` does not exist — the column is `permits.valuation`
- `project_versions.bmr_units` does not exist — BMR breakdown is not in this column

These assumptions came from familiarity with the v1 schema. v2 normalized many fields to other tables. The lesson is operational, not conceptual: **always run `PRAGMA table_info(<table>)` before writing queries against any table.**

A subtle related issue: AI assistants helping with this work made the same assumptions. The author and CC both wrote queries that failed silently or with errors. Treat schema introspection as a required first step in any session, regardless of how familiar the database feels.

### 6. Initial analytical reports over-counted "missing projects"

The CPRA analysis initially flagged 41 R-2 master permits >=5 units as potentially missing from our database. Verification reduced this dramatically:

- **41 originally flagged**
- After APN format normalization: 32 matched existing projects
- After tightened fuzzy address matching (exact street number + fuzzy street name only, not full address fuzzy): 36 matched
- After verifying remaining 5 by reading work descriptions: only **2** were genuine new construction

Three of the 5 had inflated UnitsAdded values that reflected the existing building size rather than new construction. Their valuations gave them away — $2,000 (water heater), $30,000 (wood repair), $56,000 (reroof) — none of which represents new housing.

**Lesson:** Each layer of verification subtracts false positives. Counts produced by automated matching should be treated as upper bounds. The honest count emerges only after human review of the underlying records.

### 7. Tightened matching rules helped but did not fully solve the false-positive problem

Initial fuzzy address matching used "90% similarity on full address." This produced 592 matches between CPRA permits and existing projects. Many were wrong:

- "3200 SHATTUCK Ave" matched "2700 SHATTUCK Ave" at 94% similarity (different building, same street)
- "1710 HARMON St" matched "1708 HARMON St" at 93% similarity (different parcel)
- "2527 SAN PABLO Ave" matched "2720 SAN PABLO Ave" at 92% similarity (different building)

Tightening to "exact street number AND fuzzy street name only" reduced 592 fuzzy matches to 2. The other 590 were rejected as false positives.

But the tightened rule still produced one false positive: a permit at "1312 ADDISON St" matched a project at the same address. Both addresses were literally identical. The semantic problem was that the permit was an electrical meter upgrade ("Upgrade 100/100 amps dual Meter 200 amps for each meter"), not the residential addition the project tracked. Address identity does not imply project identity.

**Lesson:** Syntactic matching has limits. When two records share the same address but represent different work, only reading the work description distinguishes them. Build manual review steps into the import workflow for any project with sparse data, where a false-positive match could go undetected.

### 8. Our validation tests passed while missing the most important field

The import script's validation block tested:
- Total permit count matched expected delta
- Total project count matched expected delta
- Foreign key integrity (no orphaned references)
- No duplicate permit numbers

All four passed. The import committed. We were ready to commit to git.

A final manual verification — running queries against the imported data — revealed that **zero of the 124 imported permits had `finaled_date` populated.** The CPRA source data had Finaled Date for approximately 70-100 of these permits. The import script had silently failed to write this field.

This is the **most important** failure in the whole sequence. The entire point of building this database is to track whether housing actually gets built. The "finalized" (CO) date is the strongest signal that a permitted project became real housing. The import committed with this field uniformly empty across all new rows.

**Lesson:** Validation tests must reflect analytical purpose, not just structural integrity. The questions to ask:

- *What is the most important field this data is meant to support?*
- *Does my validation check that this field is populated where the source has it?*

A better validation block would have included: "Count CPRA permits with non-null Finaled Date in the source file. Count v2.permits with non-null finaled_date after import. If the second is less than 80% of the first, abort and roll back."

This kind of test would have caught the bug before commit.

### 9. The backup made the rollback trivial

Before running the live import, we made a snapshot copy of the database:

```bash
cp ~/berkeley-data/databases/berkeley_housing_v2.db \\
   ~/berkeley-data/databases/berkeley_housing_v2_pre_cpra_import_2026-05-11.db
```

When we discovered the finaled_date bug, rolling back was one command:

```bash
cp ~/berkeley-data/databases/berkeley_housing_v2_pre_cpra_import_2026-05-11.db \\
   ~/berkeley-data/databases/berkeley_housing_v2.db
```

The cost of the backup: a copy command and 1.6 MB of disk space. The cost of not having a backup: commit a flawed import, have to write reverse-migration SQL to undo it. The asymmetry is enormous.

**Lesson:** Backup before any irreversible write to a canonical database. One disk-cheap copy avoids hours of recovery work. Snapshot before any import, schema migration, or bulk update.

### 10. Honest documentation matters more than clean documentation

This document deliberately includes the failures, not just the successes. A clean methodology document that says "we ingested CPRA data into v2" would mislead anyone trying to clone the approach. The truth — that this is iterative, error-prone work where each layer of verification reveals problems in earlier layers — is more useful than a polished narrative.

**Lesson:** Document the actual trajectory, not the intended trajectory. Future readers (including yourself in three months) need to know what went wrong and how it was discovered, not just what eventually worked.

---

## The deepest lesson

The failure that almost shipped — the empty finaled_date field — almost shipped because **validation tested for structural integrity rather than analytical purpose.**

Every other failure in the trajectory was caught by curiosity-driven inspection: looking at unexpected matches, querying surprising rows, reading work descriptions of flagged projects. These caught the Addison electrical permit, the 1701/1740 APN confusion, the inflated UnitsAdded values for maintenance permits.

The finaled_date bug slipped past because nobody was looking for it. Counts were right, structure was right, but the most important data field was empty. Validation that asks "do counts add up?" is easier to write than validation that asks "is the field we care most about actually populated?" The first is structural; the second is purposeful.

Structural validation catches programming errors. Purposeful validation catches the gap between what your code does and what your project is *for*.

Both matter. Most projects optimize for structural validation and underweight purposeful validation. The CPRA import here did exactly that.

---

## Methodology checklist for the next CPRA response

The second CPRA request was submitted 2026-05-10 and is expected to arrive within ~10 days. When it does:

### Hour 1: Initial inspection

1. **Confirm file location and ownership.** Where is it saved? Is it readable?
2. **Open file metadata.** Row count, column count, sheet count.
3. **Find the actual header row.** Bulk reports often have title/blank rows at the top.
4. **Inventory the columns.** Compare to what was requested. What's missing? What's extra?
5. **Spot-check 5 rows.** Do values match expected types (dates as dates, valuations as numbers)?

### Day 1: Structural understanding

1. **Identify sub-permit patterns.** Permit number suffixes, work types, valuation thresholds.
2. **Run deduplication.** Sub-permits dropped, masters retained.
3. **Count deduplicated records.** Does the number make sense given the time period and city size?
4. **Test cross-reference.** Pick 10 large projects you know exist; can you find them in the data?

### Day 2: Database integration planning

1. **Run schema introspection.** `PRAGMA table_info()` for every table you'll touch.
2. **Document the canonical column names** in a notebook cell or planning doc.
3. **Identify conflicts.** Will any new rows duplicate existing ones?
4. **Draft import script with explicit field-completeness validation.** Not just counts.

### Day 3: Dry-run

1. **Run the import in dry-run mode.** Inspect every kind of action it would take.
2. **Sample the proposed inserts.** Do they look right?
3. **Verify the most important fields will be populated.** For housing: issuance date, finaled date.
4. **Pause and read the script's output before committing.** Don't skip this.

### Day 4: Backup and live run

1. **Snapshot the database.** Named with date and purpose.
2. **Run live in a single transaction.** All-or-nothing.
3. **After commit, run independent verification queries.** Don't trust the script's own self-report.
4. **Verify the analytical fields.** Not just structural integrity.

### Day 5: Documentation and commit

1. **Generate a results report** comparing before/after state.
2. **Update the methodology document** with anything new you learned.
3. **Commit to dev branch** with a clear message.
4. **Update the project's user-facing methodology page.**

---

## Reusable templates

### CPRA request field list

Cities vary in field names, but the underlying concepts are universal. Always request:

1. Record number (permit number)
2. Property address (street number, street name, type — three separate fields if available)
3. Parcel number (APN, PIN, etc.)
4. Record type
5. Work description
6. Number of dwelling units (existing, proposed, added, removed)
7. Application/submittal date
8. Issuance date
9. Final inspection date if applicable
10. Certificate of occupancy date / completion date / "finalized" date — name multiple synonyms
11. Current status
12. Valuation amount
13. Applicant/contractor name
14. Total fees assessed
15. **Parent permit reference** (critical for deduplication)
16. **Affordability/BMR designation per permit** (if available)
17. Demolition permits — list explicitly to avoid exclusion

### Validation queries (post-import)

For any bulk import into a database, validate these:

1. **Row count delta:** Did the table grow by the expected number?
2. **Foreign key integrity:** `PRAGMA foreign_key_check` returns empty?
3. **No duplicate keys:** No two rows with the same primary identifier (e.g., permit_number)?
4. **Field completeness for analytically important fields:** Of the rows where the source has data, how many have that data in the database? Threshold ABORT if less than 80% (or whatever your tolerance is).
5. **Spot-check sample:** Pick 5 rows; verify every field round-trips correctly from source to database.
6. **Re-verify a few key analytical questions:** Run one or two queries that would surface the kinds of errors you care most about avoiding.

---

## Conclusion

This work is iterative, error-prone, and never finished. The honest version of "we built a housing pipeline database" is "we built a housing pipeline database, and continue to find and fix errors in it, and learn how to detect more kinds of errors than we used to."

The point of documenting the lessons is not to claim mastery. It is to make the next iteration cheaper for the next person, including ourselves.

The 2018-2022 CPRA response, when it arrives, will reveal new problems we cannot anticipate today. The methodology described here is the current best version, not the final version.

---

*Documented 2026-05-11. Project: Berkeley Housing Pipeline. Author: John Gage, Open Public Data.*
