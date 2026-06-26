#!/usr/bin/env python3
# INDEPENDENT verification of JN-A. Read-only on v4.db.
# CRITICAL: this does NOT re-use the discovery heuristic (an earlier version did, and so it
# inherited the discovery bug and falsely passed). Instead it (1) counts the REAL date columns
# directly by exact name, and (2) checks the per-type event counts against KNOWN ANCHORS.
# If discovery mis-maps a column, this catches it because it counts the truth independently.
import sqlite3, glob
import pandas as pd
DB          = '/Users/johngage/berkeley-data/databases/berkeley_housing_v4.db'
FEED        = sorted(glob.glob('/Users/johngage/berkeley-data/data/raw/cpra-downloads/BP_Annual Permit Report-*.xlsx'))
HEADER_ROW  = 7
DATE_COLS   = {'Submittal Date': 'permit_submitted', 'Issuance Date': 'permit_issued', 'Finaled Date': 'permit_finaled', 'Completed Date': 'permit_completed'}          # exact real date column names -> expected event_type
ANCHORS     = {'permit_submitted': 32202, 'permit_issued': 31940, 'permit_finaled': 21650, 'permit_completed': 1}           # known per-axis event-count anchors

con = sqlite3.connect(DB)
events  = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
by_type = dict(con.execute("SELECT event_type_code,COUNT(*) FROM events GROUP BY event_type_code").fetchall())
run     = con.execute("SELECT rows_in_source,rows_ingested,rows_rejected,conserved FROM ingestion_runs ORDER BY run_id DESC LIMIT 1").fetchone()

# Independently count non-null cells in each REAL date column, straight from the files.
truth = {}
for f in FEED:
    df = pd.read_excel(f, header=HEADER_ROW, dtype=str)
    for col, etype in DATE_COLS.items():
        if col in df.columns:
            truth[etype] = truth.get(etype, 0) + int(df[col].notna().sum())

print("events in db                       :", events)
print("events by type                     :", by_type)
print("ingestion_runs (in/ingested/rej/conserved):", run)
print("independent date-column truth      :", truth)
print("known anchors                      :", ANCHORS)

problems = []
for etype, expected in ANCHORS.items():
    got = by_type.get(etype, 0)
    if got != expected:
        problems.append((etype, got, expected))
# also compare against independently-counted truth (catches anchor staleness too)
for etype, t in truth.items():
    got = by_type.get(etype, 0)
    if got != t:
        problems.append((etype + " (vs file truth)", got, t))

conserved_ok = (run is not None and run[3] == 1 and events == run[1])
if problems:
    print("INDEPENDENT VERDICT: FAIL - per-axis mismatch (discovery mis-mapping or anchor drift):")
    for et, got, exp in problems:
        print("   ", et, "got", got, "expected", exp)
elif not conserved_ok:
    print("INDEPENDENT VERDICT: FAIL - conservation flag or count mismatch")
else:
    print("INDEPENDENT VERDICT: PASS")
