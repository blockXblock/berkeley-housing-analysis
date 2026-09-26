# ============================ SEQUESTERED 2026-09-26 ============================
# DO NOT RUN. Original path: scripts/test-sfyimby-datasette.py
# WHY: DEAD v1-era: reads/writes the frozen v1 DB or a DB path that no longer exists (sqlite3.connect would silently create an empty stray DB).
# Audit: docs/audit/2026-09-26_machinery_and_schema_audit.md
raise SystemExit("SEQUESTERED 2026-09-26 -- see header; original path scripts/test-sfyimby-datasette.py")
# ================================================================================
import sqlite3
print("hello")
