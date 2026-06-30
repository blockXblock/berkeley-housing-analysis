#!/usr/bin/env python3
"""Build JN-C_classify.ipynb (pass 1): reversible housing-role labeling over the v4 event stream.
#1 housing/non-housing (description-first, ADU=Yes requires description corroboration, generous-
inconclusive) + #2 master-collapse on permit family. Defers #3 (phantom-master). Emits a harvest
queue with a has_r2_documents flag (bridged to v2.db documents by address/APN). Compares confident
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
- **#1 housing vs non-housing** - description-first, NEVER UnitsAdded-first (Durant: a temp-power
  permit carried UnitsAdded=83 and is still non-housing). `ADU=Yes` is a dirty flag (v3 found it
  over-broad) so it requires **description corroboration** (new-ADU / conversion / legalization
  language). Generous: signals disagree -> **inconclusive**, never guess.
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

# CELL 1 - vocabulary
md(r"""
### What this cell does
Declares the classification vocabulary as data: housing indicators, conversion indicators,
legalization indicators, movable-home permanence markers, and non-housing disqualifiers (the cross-ref
trap guards). These lists are the only domain knowledge; the rules are mechanical over them.
""")
code(r"""
from pathlib import Path
import sqlite3, json, datetime as dt, hashlib, csv
import pandas as pd
import sys, os
# Import the classifier + its vocabulary from its single importable home (June-7 architecture;
# the June-18 drift fix). This NB demonstrates the real machinery — it does not redefine it.
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "berkeley-data", "scripts"))
from housing_rules.permit_role import (
    classify, net_units, payload_get,
    HOUSING_TERMS, CONVERSION_TERMS, LEGALIZATION_TERMS, ADU_TERMS,
    PERMANENCE_TERMS, MOVABLE_TERMS, MULTIFAM_TERMS, NONHOUSING_TERMS,
)

DB_PATH = Path.home() / "berkeley-data" / "databases" / "berkeley_housing_v4.db"
V2_PATH = Path.home() / "berkeley-data" / "databases" / "berkeley_housing_v2.db"  # read-only, for has-docs bridge

print("Imported classifier + vocabulary from housing_rules.permit_role:",
      len(HOUSING_TERMS),"housing,",len(CONVERSION_TERMS),"conversion,",
      len(LEGALIZATION_TERMS),"legalization,",len(NONHOUSING_TERMS),"disqualifiers.")
""")
md(r"""
### What just happened
The word lists are in memory - the whole domain knowledge of the classifier. Housing terms = real
creation; conversion + legalization = ADU-via-alteration that *does* add a unit; permanence markers
gate movable homes; disqualifiers stop cross-references (a "PV solar" mention in a real new-SFR, a
siding repair on an "existing two story" building) from masquerading as housing.
""")

# CELL 2 - payload field access + rule engine
md(r"""
### What this cell does
Reads the REAL payload fields (confirmed keys: `Work Type`, `WorkDescription`, `ADU`, `OccType`,
`SubType`, `UnitsAdded`, `UnitsRemoved`, `Parcel Number`) and implements the rules in the approved
priority order. Role from description+work-type (prose); `net_units` from the structured unit fields
only (prose-blind). `ADU=Yes` requires description corroboration to be confident.
""")
code(r"""
import inspect
from housing_rules import permit_role
# Demonstrate the REAL machinery: render the imported classify/net_units source so the curriculum
# shows exactly the priority-order rule engine that runs — defined once in housing_rules, not here.
print("classify() imported from:", permit_role.__file__)
print(inspect.getsource(permit_role.classify))
print(inspect.getsource(permit_role.net_units))
print("Rule engine ready (imported from housing_rules.permit_role; ADU=Yes needs description "
      "corroboration; net_units prose-blind).")
""")
md(r"""
### What just happened
The classifier reads real payload keys and applies the rules. `ADU=Yes` no longer auto-confirms - it
needs ADU/conversion/legalization language (Rule 5), so the dirty flag alone -> inconclusive. Movable
homes need permanence markers (Rule 4). Description gates housing; the structured unit fields only set
*how many*, never *whether*. Confident roles plus the generous `ambiguous` are the output.
""")

# CELL 3 - vocabulary tests
md(r"""
### What this cell does
Proves the vocabulary on real cases from prior research before classifying anything. Halts on any
failure - we never classify with a broken vocabulary.
""")
code(r"""
# The 16 vocabulary anchors + 9 deflation cases now live as REAL unit tests beside the classifier:
# scripts/housing_rules/test_permit_role.py. Run them from their home so a vocabulary regression
# halts the notebook (we never classify with a broken vocabulary).
from housing_rules.test_permit_role import run as run_permit_role_tests
run_permit_role_tests()
""")
md(r"""
### What just happened
The classifier is proven on the real cases: 2641 College siding -> alteration (the 'two story'
describing an existing building doesn't flip it); new SFRs/apartments stay housing despite PV/Shoring
cross-refs; Durant temp-power@83 -> inconclusive not housing; ADU conversions/legalizations WITH
language -> confident; an ADU-flagged kitchen remodel with no ADU language -> inconclusive (the
dirty-flag case, harvested); a movable home -> confident only with permanence markers, else
inconclusive. A failure would halt the notebook. The vocabulary is trustworthy.
""")

# CELL 4 - classify all events, write reversible labels
md(r"""
### What this cell does
Loads every event, classifies on its real payload fields, writes reversible labels to
`event_classifications` (overwrite-idempotent; a re-run with a tuned vocabulary just overwrites).
Reads `events`, writes only `event_classifications`. The event stream is never touched.
""")
code(r"""
con=sqlite3.connect(DB_PATH); con.execute("PRAGMA foreign_keys=ON")
CLF_HASH=hashlib.sha256((json.dumps([HOUSING_TERMS,CONVERSION_TERMS,LEGALIZATION_TERMS,NONHOUSING_TERMS])+"rules-v1").encode()).hexdigest()[:16]
NOW=dt.datetime.now(dt.timezone.utc).isoformat()
rows=con.execute("SELECT event_id, raw_payload, raw_description, raw_units, source_record_key FROM events").fetchall()
labels=[]
for ev_id, payload, desc, raw_units, permit in rows:
    wt   = payload_get(payload,"Work Type")
    d    = desc if desc is not None else payload_get(payload,"WorkDescription")
    adu  = payload_get(payload,"ADU")
    occ  = payload_get(payload,"OccType")
    ua   = payload_get(payload,"UnitsAdded")
    ur   = payload_get(payload,"UnitsRemoved")
    role,is_master,note = classify(wt,d,adu,occ,ua,ur,permit)
    nu = net_units(ua,ur,role,d)
    labels.append((ev_id,role,is_master,nu,CLF_HASH,NOW,"description",note))
con.execute("DELETE FROM event_classifications")
con.executemany("INSERT INTO event_classifications (event_id,housing_role,is_master,net_units,classifier_hash,classified_at,basis,basis_note) VALUES (?,?,?,?,?,?,?,?)",labels)
con.commit()
print(f"Classified {len(labels):,} events (hash={CLF_HASH}).")
for r,c in con.execute("SELECT housing_role,COUNT(*) FROM event_classifications GROUP BY housing_role ORDER BY 2 DESC"):
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
description, AND a **has_r2_documents** flag bridged to v2.db's `documents` table by address/APN (v2
docs key on project_id; v4 keys on permit, so the bridge is via the project's address/APN). The flag
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

# Build the has-documents bridge from v2.db (read-only). v2.documents has BOTH a direct permit_number
# (often blank) and project_id -> projects (canonical/normalized_address; NO apn column). We use the
# direct permit match first, then the address path. We account for merged_into_id (absorbed projects)
# so docs on a merged project still surface via the survivor's address.
doc_permits=set(); doc_addrs=set()
try:
    v2=sqlite3.connect(f"file:{V2_PATH}?mode=ro", uri=True)
    # (1) direct permit_number key on documents that carry an r2_url
    for (pn,) in v2.execute("SELECT permit_number FROM documents WHERE r2_url IS NOT NULL AND permit_number IS NOT NULL AND permit_number<>''"):
        doc_permits.add(_norm(pn))
    # (2) address path: documents.project_id -> projects (follow merged_into_id to survivor)
    for (caddr, naddr) in v2.execute('''
        SELECT COALESCE(surv.canonical_address, p.canonical_address),
               COALESCE(surv.normalized_address, p.normalized_address)
        FROM documents d
        JOIN projects p ON p.id = d.project_id
        LEFT JOIN projects surv ON surv.id = p.merged_into_id
        WHERE d.r2_url IS NOT NULL'''):
        if caddr: doc_addrs.add(_norm(caddr))
        if naddr: doc_addrs.add(_norm(naddr))
    v2.close()
    print(f"Bridge: {len(doc_permits)} permit-keyed + {len(doc_addrs)} address-keyed R2 documents in v2.")
except Exception as ex:
    print("has-documents bridge unavailable:", ex)
    print("Proceeding; has_r2_documents will be 'unknown'. (Check v2 schema: documents.permit_number, projects.canonical_address/normalized_address/merged_into_id.)")

def has_docs(permit, addr):
    if not doc_permits and not doc_addrs: return "unknown"
    if permit and _norm(permit) in doc_permits: return "yes"
    if addr and _norm(addr) in doc_addrs: return "yes"
    return "no"

queue=[]
for permit,yr,addr,apn,descr,note in harvest:
    queue.append((permit,yr,addr,apn,has_docs(permit,addr),descr,note))

n_yes=sum(1 for q in queue if q[4]=="yes")
print(f"\nHarvest queue: {len(queue):,} inconclusive permits finaled 2018-2025.")
print(f"  has R2 documents (resolvable now by reading): {n_yes:,}")
print(f"  need Accela document-fetch (no R2 doc): {sum(1 for q in queue if q[4]=='no'):,}")
print("First 12:")
for q in queue[:12]:
    print(f"   {q[1]} {q[0]:<16} docs={q[4]:<7} {str(q[2])[:24]:<24} {str(q[5])[:36]}")
out=DB_PATH.parent.parent/"output"/"jn_c_harvest_queue.csv"
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

*Note: the v2 bridge join (documents -> projects) assumes v2's project table is named `projects` with
`address`/`apn` columns; if v2 differs, the flag reads 'unknown' and the join needs a one-line fix.*
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
import os as _osh, subprocess as _sp
try:
    _PR_HASH=_sp.check_output(["git","-C",_osh.path.expanduser("~/berkeley-data"),"log","-1","--format=%h","--","scripts/housing_rules/permit_role.py"],text=True).strip()
except Exception:
    _PR_HASH="(unknown)"

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
DBP=os.path.join(os.path.expanduser('~'),'berkeley-data','databases','berkeley_housing_v4.db')
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

md(f"""
### VIZ 2 — the `classify()` decision skeleton (structural)
**What it shows.** The branch order of `housing_rules.permit_role.classify`: payload → non_housing? →
demolition? → subsidiary? → new_unit? → alteration? → else ambiguous. **Stamped with the classifier's current
commit `{_PR_HASH}`** (read live at build time, not hardcoded).
""")
_c2 = r'''
from IPython.display import Markdown, display
m = """```mermaid
flowchart TD
  S["event payload (work_type · description · ADU · occtype · units)"] --> NH{non-housing terms or non-residential occtype?}
  NH -- yes --> RNH([non_housing])
  NH -- no --> DEM{demolition terms?}
  DEM -- yes --> RDEM([demolition])
  DEM -- no --> SUB{REV/DEF child · ancillary · see-permit-X?}
  SUB -- yes --> RSUB([subsidiary])
  SUB -- no --> NEW{new-dwelling / ADU terms + unit signal?}
  NEW -- yes --> RNEW([new_unit])
  NEW -- no --> ALT{alteration terms?}
  ALT -- yes --> RALT([alteration])
  ALT -- no --> RAMB([ambiguous])
```"""
display(Markdown(m))
print("DECISION SKELETON as of permit_role.classify @ HASHSTAMP")
'''.replace('HASHSTAMP', _PR_HASH)
code(_c2)
md(f"""
**⚠⚠ HIGH DRIFT RISK — read this.** This is a **decision *skeleton*, hand-drawn, as of commit `{_PR_HASH}`**.
Unlike the quantitative charts it **cannot auto-derive its shape** from the code — so **if
`housing_rules.permit_role.classify` changes, THIS DIAGRAM LIES until it is regenerated.** The **authoritative
logic is always `permit_role.classify`** (+ its vocab lists + branch order), never this picture. The skeleton
also elides the vocab detail (HOUSING_TERMS / CONVERSION_TERMS / ADU_TERMS / NONHOUSING_TERMS) and ordering
subtleties — use it to *navigate* the logic, then read the function for truth.
""")

nb=new_notebook(cells=cells)
nb.metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python"}}
import os as _os
_NB_OUT = _os.path.join(_os.path.expanduser("~"), "berkeley-data", "notebooks", "v4", "JN-C_classify.ipynb")
with open(_NB_OUT,"w") as f: nbf.write(nb,f)
print("wrote", _NB_OUT, len(cells),"cells")
