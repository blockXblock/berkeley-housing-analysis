#!/usr/bin/env python3
"""GATED WRITE — proj133 (2128 Oxford St): append the ZAB-approved version.

Source of truth: documents.id=2188, "2024-09-12 ZAB Item 5 Att3 2128-2130 Oxford
Project Plans" (sha256 9be2399933263721a7a5904c810a1fddbb6ffac1e86533b9b1226c8b5488d9c4),
corroborated by documents.id=2350, the City 1.E Tabulation Form dated 2023-11-03
("Number of Dwelling Units: existing 16, proposed 456").

Version-scoped: APPENDS a new project_versions row (type 3 'entitled') plus its
unit_program / unit_program_affordability rows, then repoints
projects.current_version_id. Version 130 ("Initial migration", the 2023 SB330
application figures) is retained untouched as history.
"""
import sqlite3, sys, datetime

DB = "databases/berkeley_housing_v2.db"
DOC = 2188
ASSERTED_BY = "planset_verification_2026-09-04"
NOW = datetime.datetime.now().isoformat()

con = sqlite3.connect(DB); con.isolation_level = None
cur = con.cursor()
cur.execute("BEGIN")
try:
    cur.execute("UPDATE project_versions SET is_current=0 WHERE project_id=133 AND is_current=1")
    cur.execute("""INSERT INTO project_versions
        (project_id, version_label, version_type_id, effective_date, total_units,
         height_stories, height_feet, source_document_id, is_current,
         asserted_by, asserted_at, confidence_type_id, created_at, updated_at, description)
        VALUES (133, 'ZAB-approved plan set', 3, '2024-10-04', 456,
                27.0, 285.33, ?, 1, ?, ?, 1, ?, ?, ?)""",
        (DOC, ASSERTED_BY, NOW, NOW, NOW,
         "Zoning-compliance table on the ZAB hearing plan set (doc 2188): 456 dwelling "
         "units, 27 stories, 285'-4\". Density-bonus table: base 333 units at max "
         "residential density, 12% VLI (40 units) earning a 38.75% bonus = 130 bonus "
         "units, project-total ceiling 463; 456 proposed. Supersedes the 2023 SB330 "
         "application figures (485 units / 26 stories) carried by version 130. "
         "Affordability split held at version 130's VLI 47 (unverified) rather than "
         "the table's 40-unit qualifying minimum."))
    vid = cur.lastrowid

    cur.execute("""INSERT INTO unit_program
        (project_version_id, bedroom_count, tenure_type_id, unit_count, notes,
         source_document_id, asserted_by, asserted_at, confidence_type_id)
        VALUES (?, 1, 1, 456, 'Bedroom distribution unknown; placed as 1BR for schema compliance',
                ?, ?, ?, 1)""", (vid, DOC, ASSERTED_BY, NOW))
    up = cur.lastrowid

    # Affordability HELD at the version-130 split (VLI 47) by John's instruction
    # 2026-09-04. The approved density-bonus table names 40 VLI, but that is the
    # QUALIFYING MINIMUM for the 38.75% bonus, not a cap on delivery; 47 comes from
    # the 2023 SB330 application (5 ELI + 42 VLI, collapsed to VLI in v2). Neither
    # figure is a verified delivered count, so these rows carry NO source document
    # and confidence 3 (low) while total_units above is confidence 1.
    for cat, lo, hi, n in ((2, 30, 50, 47), (5, 120, None, 409)):
        cur.execute("""INSERT INTO unit_program_affordability
            (unit_program_id, income_category_id, ami_min, ami_max, unit_count,
             asserted_by, asserted_at, confidence_type_id)
            VALUES (?,?,?,?,?,?,?,3)""", (up, cat, lo, hi, n, ASSERTED_BY, NOW))

    cur.execute("UPDATE projects SET current_version_id=?, updated_at=? WHERE id=133", (vid, NOW))
    if cur.rowcount != 1:
        raise RuntimeError(f"projects update touched {cur.rowcount} rows, expected 1")

    row = cur.execute("""SELECT total_units, height_stories, height_feet, vli_units,
                                market_units, eli_units
                         FROM v_projects_flat WHERE project_id=133""").fetchone()
    if row[:3] != (456, 27.0, 285.33) or row[3] != 47 or row[4] != 409:
        raise RuntimeError(f"verify failed: {row}")
    cur.execute("COMMIT")
    print(f"OK  new project_version id={vid}  v_projects_flat -> {row}")
except Exception as e:
    cur.execute("ROLLBACK"); print("ROLLED BACK:", e); sys.exit(1)
finally:
    con.close()
