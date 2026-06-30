#!/usr/bin/env python3
# INDEPENDENT verification of JN-A. Read-only on v4.db.
#
# CRITICAL (unchanged): this does NOT re-use the discovery heuristic (an earlier version did, and so it
# inherited the discovery bug and falsely passed). It counts the REAL date columns directly by exact name
# from the source files, independently of how JN-A mapped them.
#
# PRINCIPLE (refreshed 2026-06-29): anchor to the STABLE INVARIANT, not the MOVING count.
#   The original check pinned `live event count == 85,793` — a frozen total. But legitimate later corrections
#   move the live total (the 2026-06-29 event-dedup removed 2,870 cross-file duplicate events), so a verifier
#   pinned to 85,793 FALSE-FAILS on dedup-clean data. The fix (same lesson as the JN-E baseline): verify
#   (1) INGESTION CONSERVATION — the invariant that never moves: the source files still hold the same per-axis
#       date-cell counts, and the ingestion_runs record shows 32,202 source rows -> 85,793 events, conserved=1;
#   (2) the LIVE state == ingestion anchors MINUS the DOCUMENTED deltas — so the ONLY subtractions are the ones
#       we recorded. Future legitimate corrections re-pass by appending a documented delta, never by editing a
#       frozen total.
import sqlite3, glob
import pandas as pd

DB         = '/Users/johngage/berkeley-data/databases/berkeley_housing_v4.db'
FEED       = sorted(glob.glob('/Users/johngage/berkeley-data/data/raw/cpra-downloads/BP_Annual Permit Report-*.xlsx'))
HEADER_ROW = 7
DATE_COLS  = {'Submittal Date': 'permit_submitted', 'Issuance Date': 'permit_issued',
              'Finaled Date': 'permit_finaled', 'Completed Date': 'permit_completed'}

# (1) INGESTION ANCHORS — the stable invariant: per-axis non-null date cells in the source files at ingestion.
#     These do NOT move (the files don't change); the file-truth count below must equal them.
INGESTION_ANCHORS = {'permit_submitted': 32202, 'permit_issued': 31940, 'permit_finaled': 21650, 'permit_completed': 1}
INGESTION_TOTAL   = 85793   # = sum(INGESTION_ANCHORS); the conserved ingestion count (ingestion_runs.rows_ingested)
SOURCE_ROWS       = 32202   # ingestion_runs.rows_in_source

# (2) DOCUMENTED DELTAS — append-only ledger of legitimate post-ingestion event removals (with provenance).
#     live[axis] must == INGESTION_ANCHORS[axis] - sum(deltas[axis]). Add a new entry when a future gated
#     correction removes events; NEVER edit the anchors above to chase a moved total.
DOCUMENTED_DELTAS = [
    {'name': 'event-dedup 2026-06-29 (cross-file duplicate milestone events)',
     'provenance': 'docs/audit/2026-06-29_event_dedup_write.md',
     'remove': {'permit_submitted': 1437, 'permit_issued': 1428, 'permit_finaled': 5, 'permit_completed': 0}},
]

def expected_live():
    exp = dict(INGESTION_ANCHORS)
    for d in DOCUMENTED_DELTAS:
        for ax, n in d['remove'].items():
            exp[ax] = exp.get(ax, 0) - n
    return exp

con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
events  = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
by_type = dict(con.execute("SELECT event_type_code,COUNT(*) FROM events GROUP BY event_type_code").fetchall())
run     = con.execute("SELECT rows_in_source,rows_ingested,rows_rejected,conserved FROM ingestion_runs ORDER BY run_id DESC LIMIT 1").fetchone()

# independent file-truth: count non-null cells in each REAL date column straight from the source files
truth = {}
for f in FEED:
    df = pd.read_excel(f, header=HEADER_ROW, dtype=str)
    for col, etype in DATE_COLS.items():
        if col in df.columns:
            truth[etype] = truth.get(etype, 0) + int(df[col].notna().sum())

exp_live = expected_live()
total_removed = sum(sum(d['remove'].values()) for d in DOCUMENTED_DELTAS)

print("events in db (live)                 :", events)
print("events by type (live)               :", by_type)
print("ingestion_runs (in/ingested/rej/cons):", run)
print("independent file-truth (date cols)  :", truth)
print("ingestion anchors (stable)          :", INGESTION_ANCHORS)
print("documented deltas removed (total)   :", total_removed, "->", [d['name'] for d in DOCUMENTED_DELTAS])
print("expected live (anchors - deltas)    :", exp_live)

problems = []
# LAYER 1 — ingestion conservation (the stable invariant)
for etype, anchor in INGESTION_ANCHORS.items():
    if truth.get(etype, 0) != anchor:
        problems.append(("INGESTION file-truth", etype, truth.get(etype, 0), anchor))
if run is None or run[0] != SOURCE_ROWS or run[1] != INGESTION_TOTAL or run[3] != 1:
    problems.append(("INGESTION conservation record", "ingestion_runs", run, (SOURCE_ROWS, INGESTION_TOTAL, 0, 1)))
# LAYER 2 — live == anchors - documented deltas (only documented removals moved the count)
for etype, exp in exp_live.items():
    if by_type.get(etype, 0) != exp:
        problems.append(("LIVE vs anchors-minus-deltas", etype, by_type.get(etype, 0), exp))
if events != sum(exp_live.values()):
    problems.append(("LIVE total", "events", events, sum(exp_live.values())))

if problems:
    print("\nINDEPENDENT VERDICT: FAIL")
    for layer, et, got, exp in problems:
        print(f"   [{layer}] {et}: got {got} expected {exp}")
    print("   -> If a NEW legitimate correction removed events, APPEND a DOCUMENTED_DELTAS entry (do not edit anchors).")
    raise SystemExit(1)
else:
    print("\nINDEPENDENT VERDICT: PASS")
    print(f"   ingestion conserved ({SOURCE_ROWS:,} rows -> {INGESTION_TOTAL:,} events); "
          f"live {events:,} == anchors {INGESTION_TOTAL:,} - documented {total_removed:,}.")
