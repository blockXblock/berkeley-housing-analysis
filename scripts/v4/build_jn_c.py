#!/usr/bin/env python3
"""Build JN-C_classify.ipynb (pass 1): reversible housing-role labeling over the v4 event stream.
#1 housing/non-housing (description-first, ADU=Yes requires description corroboration, generous-
inconclusive) + #2 master-collapse on permit family. Defers #3 (phantom-master). Emits a harvest
queue with a has_r2_documents flag (from v4's own documents table). Compares confident
completions-by-year to v3 prior research as a floor..ceiling range. What-Just-Happened sandwich on
every code cell. Field names are the REAL payload keys confirmed from the v4 db."""

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
cells=[]
def md(t): cells.append(new_markdown_cell(t.strip("\n")))
def code(s): cells.append(new_code_cell(s.strip("\n")))

md(r"""
# JN-C pass 1 - Reversible Housing-Role Labeling (#1 housing/non-housing + #2 master-collapse)

JN-A proved every permit row is a conserved event. JN-C **labels** those events with a housing role -
reversibly, never deleting. A re-run overwrites the label, never the event. We are *just labeling*.

**This pass does two of three classification jobs and defers the third on purpose:**
- **#1 what each permit does to housing** - read by a model, not matched by word lists. Jev (TypeSafe)
  read every permit and Claude Sonnet 5 read the ones that needed reasoning, both under HCD's Annual
  Progress Report definitions (`housing_rules.reading_rules.DEFINITIONS`). The answers are stored as
  evidence (`data/derived/permit_effect_evidence_2026-09-26_hcd.json`); this notebook looks them up and
  never calls a model. A permit the models could not settle is **ambiguous**, never guessed.
- **#2 master-collapse** - a building = its New master permit; `-REV`/`-DEF` are children, counted
  master-only (REV restatement bug). Collapse on **permit family**, not address (avoids Logan Park).
- **#3 phantom-master discriminator - DEFERRED.** The inconclusive set (with permit/address/APN and a
  has-documents flag) is the **harvest queue** for the next iteration.

**Completion rule (the clean v4 rule):** a building completes in the year its **master New permit's
`permit_finaled` event** fires. No best-permit-pick fallback. Consequence by design: ADU-via-
alteration/legalization without a New master falls inconclusive unless description corroborates -
so v4's confident floor sits below v3 in those cases, and v3's number should fall inside v4's
floor..ceiling range (the spread is the ADU harvest band). That is the result we run to see.

**ADU reality (why description gates, not work-type):** an ADU can be added with little/no new
construction - garage/basement conversion (Alteration work type) or legalization of an existing
unit (AB 2533). Movable/tiny homes count only with permanence markers (wheels removed, permanent
foundation) and otherwise are inconclusive. So description is the trustworthy gate; Work Type=New
supports but is not required.

**Comparison target (v3):** CY2024=708 (settled); 8-yr 4,310 vs city 4,022 (+288..+301); CY2025~497
(least-settled - divergence is a finding, not a failure).
""")

# CELL 1 - setup and the evidence the labels come from
md(r"""
### What this cell does
Opens the build database and shows where the housing roles come from: the stored model readings and the
definitions the models were given. Nothing here decides a role; cell 4 looks each permit up.
""")
code(r"""
from pathlib import Path
import sqlite3, json, datetime as dt, hashlib, csv
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "berkeley-data", "scripts"))
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "berkeley-data", "scripts", "v4"))
from housing_rules.permit_effect import EVIDENCE, evidence_hash
from housing_rules.reading_rules import DEFINITIONS
import stage_methods as SM   # the stage-method home; cell 4 CALLS SM.classify_all, never re-types it

def _norm(s): return " ".join(str(s).split()).strip().lower() if s is not None else ""   # key for the has-docs join

# DB target PARAMETERIZED (env JN_C_DB_PATH, else the chain-wide PIPELINE_DB_PATH); DEFAULT = the
# JN-A throwaway rebuild, NEVER the live DB. JN-C DELETE+INSERTs event_classifications, and the
# corrections JN-F applies afterwards would be lost if it ran against live.
_LIVE   = Path.home() / "berkeley-data" / "databases" / "berkeley_housing_v4.db"
DB_PATH = Path(os.environ.get("JN_C_DB_PATH") or os.environ.get("PIPELINE_DB_PATH")
          or str(Path.home() / "berkeley-data" / "scratch" / "jn_a_throwaway" / "berkeley_housing_v4.db"))
if DB_PATH.resolve() == _LIVE.resolve() and os.environ.get("JN_C_ALLOW_LIVE") != "1":
    raise SystemExit(
        f"REFUSED: DB_PATH is the LIVE DB ({_LIVE}).\n"
        f"JN-C would DELETE+INSERT event_classifications, losing the corrections JN-F applies.\n"
        f"Point JN_C_DB_PATH at a rebuild (default: the JN-A throwaway), or set JN_C_ALLOW_LIVE=1.")

rows = json.loads(EVIDENCE.read_text())
print(f"Evidence: {EVIDENCE.name}  ({evidence_hash()})")
print(f"  permits read: {len(rows):,}   read by Sonnet: {sum(1 for r in rows if r.get('sonnet_effect')):,}")
print("\n" + DEFINITIONS)
""")
md(r"""
### What just happened
The labels this notebook writes are lookups into that file. The hash is stamped on every label, so a
re-reading (a new evidence file) shows up as a different hash, never as a silent change. The definitions
are HCD's own, so these counts are comparable to the city's Annual Progress Report row for row.
""")

# CELL 4 - classify all events, write reversible labels
md(r"""
### What this cell does
Loads every event, classifies on its real payload fields, writes reversible labels to
`event_classifications` (overwrite-idempotent; a re-run with a tuned vocabulary just overwrites).
Reads `events`, writes only `event_classifications`. The event stream is never touched.
""")
md(r"""
## Evidence: inspections and stored documents (loaded before classification)
Two kinds of evidence the CPRA permit files do not carry, loaded AFTER JN-B's dedup (so distinct inspections on
one day are never collapsed) and BEFORE classification: the harvested Accela **inspection histories**
(`data/raw/accela_inspections/*.json`, one `sources` row per file with its SHA-256, one `inspection` event per
record or a rejection with its reason) and the **stored documents** we hold copies of in R2
(`data/derived/documents_r2_manifest_2026-09-28.csv` -> the `documents` table). Documents link by record number;
all current ones belong to PLANNING records, which enter the build with the CapDetail harvest.
Also the **reference layer**: the county's parcels (`databases/berkeley.db`, Feb-2026 feed) become v4 parcels
with a stable internal id and their APN as a time-labeled identifier (ADR-003), with assessed values; owners of
record (`data/reference/berkeley_parcel_owners_2026-08-13.csv`) become actors with an `owner_of_record` action
on the parcel. Rows that do not land are recorded with their reason (e.g. an APN since re-platted).
Last, the city's **Planning records** (`data/raw/accela_capdetail/capdetail_2026-09-26.jsonl`, the CapDetail harvest of
all 1,786 housing Planning records): one `planning_filed` event per record carrying the whole parsed record, one
`planning_task` event per DATED review task (task, disposition, the due date the city set itself, who marked it), and
each marker as a city-staff actor exactly as written. Which task means "accepted" or "entitled" is decided later, not
here. Planning events get no housing-role label: they are not building permits.
""")
code(r"""
con=sqlite3.connect(DB_PATH); con.execute("PRAGMA foreign_keys=ON")
print("inspections:", SM.load_inspections(con))
print("documents:  ", SM.load_documents(con))
print("parcels:    ", SM.load_parcels(con))   # assessor parcels + APN identifiers + assessed values + owners of record
print("lineage:    ", SM.load_parcel_lineage(con))   # re-plat candidates: former APNs, former parcels, candidate splits
print("planning:   ", SM.load_planning(con))   # the city's Planning records: filed + dated review tasks, staff who marked them
""")
code(r"""
con=sqlite3.connect(DB_PATH); con.execute("PRAGMA foreign_keys=ON")
# THE materialization is stage_methods.classify_all — one importable home for the recipe
# (2026-07-02 review: the loop + hash recipe were duplicated here as a cell-string, the exact
# aa6ded0 anti-pattern). The hash is permit_effect.evidence_hash(): the evidence file's content.
from housing_rules.permit_effect import evidence_hash
dist = SM.classify_all(con)
print(f"Classified {sum(v for k, v in dist.items() if not k.startswith('_')):,} events from model-read evidence (hash={evidence_hash()}).")
for r,c in sorted(dist.items(), key=lambda x: -x[1]):
    print(f"   {r:<12} {c:>7,}")
""")
md(r"""
### What just happened
Every event carries a reversible housing-role label; the distribution shows the split across
new_unit / alteration / demolition / subsidiary / non_housing / ambiguous. Only
`event_classifications` was written; `events` is untouched; a re-run overwrites these labels. The
`ambiguous` rows are the harvest queue (Cell 6).
""")

# CELL 5 - completions BY UNITS per year vs v3, + size-band x type distribution
md(r"""
### What this cell does
Counts completions the clean v4 way but **by UNITS, not by permit count** - summing `net_units` of
master `new_unit` permits whose `permit_finaled` event fired, per year. (The prior pass counted
distinct permits, i.e. buildings, which is why it read far below v3's unit totals.) v4 floor = units
on confident new_unit masters; ceiling = floor + units on ambiguous-that-finaled. Then it breaks the
completions into Berkeley's real size bands - 1 / 2-4 / 5-19 / 20-99 / 100+ units (anchored on the
5-unit legal multifamily line and the 2-19 "middle housing" band) - crossed with ADU vs new vs
addition, per year, so we see whether units come from a few big towers or the small-housing tail.
""")
code(r"""
# DEDUP-CORRECT: a permit is ONE building regardless of how many source rows / finaled events it has
# (JN-A faithfully preserved duplicate rows; the dedup belongs HERE at the counting layer). We collapse
# to one row per distinct source_record_key first, taking that permit's finaled year and net_units,
# then aggregate. Without this, cross-file-overlap and within-file-duplicate permits double-count (~47u).
# One finaled event per permit: MIN(event_id) picks a single representative row per permit.
con.execute("DROP VIEW IF EXISTS _jnc_finaled_permits")
con.execute('''CREATE TEMP VIEW _jnc_finaled_permits AS
  SELECT e.source_record_key AS permit,
         strftime('%Y', e.event_date) AS yr,
         c.housing_role AS role, c.is_master AS is_master, c.net_units AS net_units
  FROM events e JOIN event_classifications c ON c.event_id=e.event_id
  WHERE e.event_type_code='permit_finaled'
    AND e.event_id = (SELECT MIN(e2.event_id) FROM events e2
                      WHERE e2.source_record_key=e.source_record_key
                        AND e2.event_type_code='permit_finaled')''')

# UNIT-summed completions per year (master new_unit), prose-blind net_units, master-only, DEDUPED.
floor=dict(con.execute('''SELECT yr, COALESCE(SUM(net_units),0) FROM _jnc_finaled_permits
  WHERE role='new_unit' AND is_master=1 GROUP BY yr''').fetchall())
ceil=dict(con.execute('''SELECT yr, COALESCE(SUM(net_units),0) FROM _jnc_finaled_permits
  WHERE role IN ('new_unit','ambiguous') AND COALESCE(net_units,0) >= 0 GROUP BY yr''').fetchall())
bld=dict(con.execute('''SELECT yr, COUNT(*) FROM _jnc_finaled_permits
  WHERE role='new_unit' AND is_master=1 GROUP BY yr''').fetchall())

V3={"2024":708,"2025":497}  # settled unit refs; earlier per-year not all pinned here
print("COMPLETIONS BY UNITS (v4 clean rule, DEDUPED by permit) vs v3:")
print(f"{'year':<6}{'v4 floor':>10}{'v4 ceil':>9}{'bldgs':>7}{'u/bldg':>8}{'v3':>7}   inside?")
tf=tc=tb=0
for y in [str(x) for x in range(2018,2026)]:
    f=floor.get(y,0); c=ceil.get(y,0); b=bld.get(y,0); v=V3.get(y); tf+=f; tc+=c; tb+=b
    upb = f/b if b else 0
    inside="" if v is None else ("YES" if f<=v<=c else "** v3 OUTSIDE")
    print(f"{y:<6}{f:>10,}{c:>9,}{b:>7,}{upb:>8.1f}{(str(v) if v else ''):>7}   {inside}")
print(f"{'TOT':<6}{tf:>10,}{tc:>9,}{tb:>7,}")
print(f"\nv3 8-yr scorecard ref: 4,310 units (city 4,022; +288..+301). v4 floor={tf:,} ceil={tc:,} units.")
print("Read: does v3 fall INSIDE floor..ceiling? u/bldg flags big-project- vs small-housing-driven years.")
print("KNOWN deferred inflation NOT removed here: 1951 Shattuck phased double-count (+163, CY2024) - the")
print("  first #3 phantom-master case. CY2024 corrected for it lands ~v3's 708.")

# DEFLATION-FIX diagnostic: confident new_unit masters with NULL net_units (multifamily missing a count,
# flagged not guessed). DEDUPED.
null_mf = con.execute('''SELECT COUNT(*) FROM _jnc_finaled_permits
  WHERE role='new_unit' AND is_master=1 AND net_units IS NULL''').fetchone()[0]
print(f"\nMultifamily count-gap (confident new_unit, finaled, NULL net_units): {null_mf} permits.")
print("  Apartments missing a unit count - flagged not guessed; add 0 to the sums. Large = a 2nd harvest target.")

# SIZE-BAND x TYPE distribution (shape of how Berkeley adds housing), confident new_unit, DEDUPED.
def band(u):
    u = u or 0
    if u <= 1: return "1 unit (SFR/ADU)"
    if u <= 4: return "2-4 (small middle)"
    if u <= 19: return "5-19 (lg middle)"
    if u <= 99: return "20-99 (mid-rise)"
    return "100+ (major)"

dist = con.execute('''SELECT p.net_units, e.raw_payload
  FROM _jnc_finaled_permits p
  JOIN events e ON e.source_record_key=p.permit AND e.event_type_code='permit_finaled'
  WHERE p.role='new_unit' AND p.is_master=1
    AND e.event_id=(SELECT MIN(e2.event_id) FROM events e2 WHERE e2.source_record_key=p.permit AND e2.event_type_code='permit_finaled')''').fetchall()
import collections
band_units = collections.Counter(); band_count = collections.Counter()
for nu, payload in dist:
    b = band(nu); band_units[b]+=(nu or 0); band_count[b]+=1
print("\nSIZE-BAND DISTRIBUTION (confident new_unit completions, all years, DEDUPED):")
print(f"{'band':<20}{'projects':>10}{'units':>10}")
for b in ["1 unit (SFR/ADU)","2-4 (small middle)","5-19 (lg middle)","20-99 (mid-rise)","100+ (major)"]:
    print(f"{b:<20}{band_count[b]:>10,}{band_units[b]:>10,}")
print("Read: this is the shape - how many units come from the 100+ towers vs the 2-4 middle vs the 1-unit/ADU tail.")
""")
md(r"""
### What just happened
This is the real comparison - by UNITS. v4 floor/ceiling now sum net_units (prose-blind, master-only),
so they are directly comparable to v3's unit totals. The `u/bldg` column reads the character of each
year: ~1.0 means an ADU/SFR-dominated year, a high value means a few big projects drove it. The
size-band table is the shape you asked for: how Berkeley's housing splits across the 100+ major
projects, the 20-99 mid-rise, the 5-19 and 2-4 middle housing, and the 1-unit SFR/ADU tail. If v4 now
overshoots v3, the bands tell us *where* - a few big towers (check for REV double-count) or genuine
small-housing volume (likely real, likely what v3's address-keyed pipeline undercounted).
""")

# CELL 6 - harvest queue with has_r2_documents flag
md(r"""
### What this cell does
Emits the harvest queue: inconclusive permits that finaled in-window, with permit/address/APN/
description, AND a **has_r2_documents** flag from v4's own `documents` table, matched by record key, canonical
APN, or canonical address (the build does not open v2). The flag
marks which inconclusive cases are resolvable NOW by reading an existing R2 PDF, versus which need an
Accela document-fetch. Writes the queue to CSV.
""")
code(r"""
harvest=con.execute('''SELECT DISTINCT e.source_record_key permit, strftime('%Y',e.event_date) yr,
   e.raw_address addr, e.raw_apn apn, e.raw_description descr, c.basis_note
   FROM events e JOIN event_classifications c ON c.event_id=e.event_id
   WHERE e.event_type_code='permit_finaled' AND c.housing_role='ambiguous'
     AND strftime('%Y',e.event_date) BETWEEN '2018' AND '2025'
   ORDER BY yr, permit''').fetchall()

# The has-documents bridge reads v4's OWN `documents` table (same DB as the events; 2026-09-29, phase 1 of
# the cutover -- the build no longer opens v2). Keys: the document's record key, its canonical APN hint, and
# its address hint through the address canon. v4 holds the 306 stored R2 documents; v2's attachment
# listings are a RE-DERIVE item, so a "no" here means "no stored document in v4", not "none exists".
from housing_rules import to_canonical_apn
from housing_rules.address import normalize_address
def _apn(a):
    try: return to_canonical_apn(a, "Alameda") if a else None
    except Exception: return None
def _addr(a):
    try: return normalize_address(a) if a else None
    except Exception: return None
doc_permits=set(); doc_addrs=set(); doc_apns=set()
for key, ah, ph in con.execute("SELECT record_key, address_hint, apn_hint FROM documents"):
    if key: doc_permits.add(_norm(key))
    if _addr(ah): doc_addrs.add(_addr(ah))
    if _apn(ph): doc_apns.add(_apn(ph))
print(f"Bridge: {len(doc_permits)} record-keyed, {len(doc_apns)} APN-keyed, {len(doc_addrs)} address-keyed documents in v4.")

def has_docs(permit, addr, apn=None):
    if not doc_permits and not doc_addrs: return "unknown"
    if permit and _norm(permit) in doc_permits: return "yes"
    if _apn(apn) and _apn(apn) in doc_apns: return "yes"
    if _addr(addr) and _addr(addr) in doc_addrs: return "yes"
    return "no"

queue=[]
for permit,yr,addr,apn,descr,note in harvest:
    queue.append((permit,yr,addr,apn,has_docs(permit,addr,apn),descr,note))

n_yes=sum(1 for q in queue if q[4]=="yes")
print(f"\nHarvest queue: {len(queue):,} inconclusive permits finaled 2018-2025.")
print(f"  has R2 documents (resolvable now by reading): {n_yes:,}")
print(f"  need Accela document-fetch (no R2 doc): {sum(1 for q in queue if q[4]=='no'):,}")
print("First 12:")
for q in queue[:12]:
    print(f"   {q[1]} {q[0]:<16} docs={q[4]:<7} {str(q[2])[:24]:<24} {str(q[5])[:36]}")
# repo-root anchored (2026-07-02 fix: was DB_PATH.parent.parent, which broke when DB_PATH became
# parameterized — a scratch target sent the queue to gitignored scratch/output/)
out=Path.home()/"berkeley-data"/"output"/"jn_c_harvest_queue.csv"
out.parent.mkdir(parents=True,exist_ok=True)
with open(out,"w",newline="") as f:
    w=csv.writer(f); w.writerow(["permit","finaled_year","address","apn","has_r2_documents","description","basis_note"])
    w.writerows(queue)
print(f"\nWrote harvest queue -> {out}")
""")
md(r"""
### What just happened
The harvest queue exists, split by `has_r2_documents`. The `yes` rows are resolvable now by reading an
existing R2 PDF; the `no` rows are the Accela document-fetch worklist (small ADU permits whose
documents aren't yet in R2). This is the precise, bounded target for the next step - not a blind
Accela sweep, but exactly the inconclusive ADU permits that need evidence. Labels stay reversible, so
each resolved case is a reversible relabel on richer evidence.

*Note: the flag reads v4's `documents` (306 stored R2 documents); a "no" means no stored document in v4,
not that none exists.*
""")

md(r"""
---
## JN-C pass 1 complete

**Exists:** reversible housing-role labels on every event; confident completions-by-year as a floor;
a v3 comparison range; a harvest queue with addresses/APNs and a has-R2-documents flag splitting
resolvable-now from needs-Accela.

**Deferred by design:** #3 phantom-master identity, best-permit-pick, affordability tiers, BP-issued
side. The inconclusive set is the honest residue and the worklist.

**Next:** read the v3 comparison (does 708 fall in CY2024's range?); then the harvest loop - read R2
PDFs for the `has_r2_documents=yes` subset, aim an Accela document-fetch at the `no` subset (small ADU
docs), each resolution a reversible relabel. Later, #3 lands on this fully-labeled evidence.

*Reversible: writes only event_classifications (overwrite-idempotent) + an output CSV. Never touches
events or v3. Commit nothing until John reviews.*
""")

# ============================================================ VISUALIZATIONS (derive-from-data, text-sandwiched)
md("""
## Visualizations
Per the viz convention: text-sandwiched, **derive-from-data** (read live from `event_classifications`,
never hardcoded), with *what-it-could-mislead-about* annotations.
""")

md("""
### VIZ 1 — housing_role distribution (the subject)
**What it shows.** How JN-C labeled every event — `alteration` dominates, then subsidiary / ambiguous /
new_unit / demolition / non_housing. Log scale (alteration dwarfs the rest). Derives live from
`event_classifications GROUP BY`, and overlays the **count grain** (master+finaled+new_unit) so the
events-vs-buildings gap is concrete.
""")
code("""
import sqlite3, os
import plotly.graph_objects as go
DBP=str(DB_PATH)   # the SAME parameterized target this notebook classified (was a hardcoded live path)
con=sqlite3.connect(f'file:{DBP}?mode=ro',uri=True)   # READ-ONLY — viz never writes
dist=con.execute("SELECT housing_role,COUNT(*) FROM event_classifications GROUP BY 1 ORDER BY 2 DESC").fetchall()
masters=con.execute("SELECT COUNT(*) FROM event_classifications WHERE is_master=1").fetchone()[0]
counted=con.execute("SELECT COUNT(*) FROM events e JOIN event_classifications c ON c.event_id=e.event_id "
  "WHERE e.event_type_code='permit_finaled' AND c.housing_role='new_unit' AND c.is_master=1 AND COALESCE(c.net_units,0)>0").fetchone()[0]
roles=[r for r,_ in dist]; vals=[c for _,c in dist]
fig=go.Figure(go.Bar(x=vals, y=roles, orientation='h', text=vals, textposition='outside'))
fig.update_layout(title=f'housing_role over {sum(vals):,} EVENTS · {masters:,} masters · {counted:,} counted-CO buildings',
   xaxis_type='log', xaxis_title='events (log scale)', yaxis_title='housing_role', height=430)
fig.show()
print(f'events={sum(vals):,}  masters={masters:,}  counted-CO={counted:,}')
""")
md("""
**⚠ mislead-guards.** (1) This is a distribution over **EVENTS, not buildings** — the ~2,618 `new_unit`
events are **NOT 2,618 buildings**; the count grain is **master + finaled + new_unit** (the much smaller
`counted-CO` number in the title). (2) The ~85% `alteration` is **not noise** — it's *housing-hides-in-
alteration* (garage/basement → ADU conversions live here), which is exactly why we classify all of it rather
than filter at intake. (3) Log scale: the bars compress 3 orders of magnitude — read the labels, not the lengths.
""")

nb=new_notebook(cells=cells)
nb.metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python"}}
import os as _os
_NB_OUT = _os.path.join(_os.path.expanduser("~"), "berkeley-data", "notebooks", "v4", "JN-C_classify.ipynb")
with open(_NB_OUT,"w") as f: nbf.write(nb,f)
print("wrote", _NB_OUT, len(cells),"cells")
