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
import os, sqlite3, glob
import pandas as pd

# Portable paths (was hardcoded /Users/johngage/...). Env overrides let this validate a THROWAWAY rebuild:
#   BERKELEY_DATA_ROOT (repo root) and JN_A_DB_PATH (the DB to check — a throwaway in a from-raw test).
_ROOT      = os.environ.get('BERKELEY_DATA_ROOT', os.path.expanduser('~/berkeley-data'))
DB         = os.environ.get('JN_A_DB_PATH', os.path.join(_ROOT, 'databases', 'berkeley_housing_v4.db'))
# Inputs = the files the DB itself records it was built from (sources table: locator + SHA-256 prefix), never a
# filename pattern (a pattern silently grew from 2 to 5 files). Each file's bytes are re-checked against the record.
import hashlib
_con0 = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
FEED = []
for _loc, _ck in _con0.execute("SELECT locator, checksum FROM sources WHERE source_kind='cpra_permit_feed' ORDER BY source_id"):
    _f = os.path.join(_ROOT, 'data', 'raw', 'cpra-downloads', os.path.basename(_loc))
    _got = hashlib.sha256(open(_f, 'rb').read()).hexdigest()
    assert _got.startswith(_ck), f'input changed since ingestion: {os.path.basename(_f)} {_got[:16]} != recorded {_ck}'
    FEED.append(_f)
_con0.close()
HEADER_ROW = 7
DATE_COLS  = {'Submittal Date': 'permit_submitted', 'Issuance Date': 'permit_issued',
              'Finaled Date': 'permit_finaled', 'Completed Date': 'permit_completed'}

# (1) INGESTION ANCHORS — the stable invariant: per-axis non-null date cells in the source files at ingestion.
#     These do NOT move (the files don't change); the file-truth count below must equal them.
# Epoch 2026-09-26b (John adopted): the three 2026-07-07 productions (NextRequest 26-1971), SHA-256 pinned in JN-A.
# HISTORY — epoch 2026-06-26..09-26: the two 26-1368 productions, anchors 32202/31940/21650/1 = 85,793 events from
# 32,202 rows, with one documented delta (event-dedup 2026-06-29: -1437/-1428/-5/0, docs/audit/2026-06-29_event_dedup_write.md).
INGESTION_ANCHORS = {'permit_submitted': 40243, 'permit_issued': 39830, 'permit_finaled': 27300, 'permit_completed': 1}
INGESTION_TOTAL   = 107374  # = sum(INGESTION_ANCHORS); the conserved ingestion count (ingestion_runs.rows_ingested)
SOURCE_ROWS       = 40243   # ingestion_runs.rows_in_source

# (2) DOCUMENTED DELTAS — append-only ledger of legitimate post-ingestion event removals (with provenance).
#     live[axis] must == INGESTION_ANCHORS[axis] - sum(deltas[axis]). Add a new entry when a future gated
#     correction removes events; NEVER edit the anchors above to chase a moved total.
DOCUMENTED_DELTAS = [
    {'name': 'JN-B event dedup on the 2026-07-07 inputs (overlapping 2025 rows across productions + cross-file duplicates)',
     'provenance': 'scratch/2026-09-26_adopt/out/JN-B_event_dedup.ipynb; live v4 rebuilt 2026-09-26 (snapshot keep_snapshot_2026-09-26_pre-v4-rebuild.db)',
     'remove': {'permit_submitted': 7344, 'permit_issued': 7226, 'permit_finaled': 3696, 'permit_completed': 0}},
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
