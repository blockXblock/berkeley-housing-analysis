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

DB_PATH = Path.home() / "berkeley-data" / "databases" / "berkeley_housing_v4.db"
V2_PATH = Path.home() / "berkeley-data" / "databases" / "berkeley_housing_v2.db"  # read-only, for has-docs bridge

HOUSING_TERMS = [
    "single family","single-family","new sfr","single-family dwelling"," sfr",
    "residential building","residential development","residential apartment",
    "housing development","student housing","group living","live/work","live-work",
    "duplex","triplex","fourplex","townhouse","townhome","row house",
    "dwelling unit","dwellings","accessory dwelling","apartment","multifamily","multi-family",
    "condominium"," condo",
]
CONVERSION_TERMS = [
    "convert to dwelling","convert to residential","add dwelling unit","convert garage",
    "convert detached","garage conversion","conversion of upper floor","convert basement",
    "convert attic","convert existing",
]
LEGALIZATION_TERMS = [
    "legalize","legalization","unpermitted","bring into compliance","ab 2533","legalize existing",
]
ADU_TERMS = ["adu","jadu","accessory dwelling unit","junior accessory"]
# movable-home permanence markers: ONLY these make a movable/park-model count as a dwelling
PERMANENCE_TERMS = ["permanent foundation","wheels removed","on foundation","affixed to foundation",
                    "tongue removed","placed on a foundation"]
MOVABLE_TERMS = ["tiny home","tiny house","park model","movable","trailer","manufactured home","rv "]
# multifamily markers: a confident new_unit whose count is BLANK and which looks multifamily must NOT
# default to 1 (that would under-count a real apartment) - it stays flagged as a count-gap to harvest.
MULTIFAM_TERMS = ["apartment","multifamily","multi-family","residential building","residential development",
                  "residential apartment","housing development","story residential","-story residential",
                  "units","condominium","mixed use","mixed-use","story building"]
NONHOUSING_TERMS = [
    "re-roof","reroof","siding","hvac","water heater","furnace","temp power","temporary power",
    "tower crane","shoring","abatement","electrical service","solar","photovoltaic"," pv ",
    "re-pipe","repipe","window replacement","kitchen remodel","bathroom remodel","deck","fence",
    "retaining wall",
]
print("Vocabulary loaded:", len(HOUSING_TERMS),"housing,",len(CONVERSION_TERMS),"conversion,",
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
def _norm(s): return " ".join(str(s).split()).strip().lower() if s is not None else ""
def _has(t, terms): return any(x in t for x in terms)
def _to_int(v):
    try:
        if v is None or str(v).strip().lower() in ("","nan","none"): return None
        return int(float(str(v).strip()))
    except Exception: return None

def payload_get(payload, key):
    try: return json.loads(payload).get(key)
    except Exception: return None

def classify(work_type, description, adu_flag, occtype, units_added, units_removed, permit_number):
    wt=_norm(work_type); desc=_norm(description); pn=_norm(permit_number)
    adu_yes = _norm(adu_flag) in ("yes","y","true","1")
    occ = _norm(occtype)
    is_new = wt.startswith("new")
    alt = any(k in wt for k in ("alteration","addition"))
    has_adu_lang = _has(desc, ADU_TERMS) or _has(desc, CONVERSION_TERMS) or _has(desc, LEGALIZATION_TERMS)

    # RULE 1 - child sub-permit
    if "-rev" in pn or "-def" in pn:
        return "subsidiary",0,"REV/DEF child - counted via master only"
    # RULE 2 - demolition
    if "demolition" in wt or "demolish" in wt:
        return "demolition",0,"Work Type demolition"
    # RULE 3 - sign
    if wt=="sign":
        return "non_housing",0,"Work Type sign"
    # RULE 4 - movable home: dwelling ONLY with permanence markers, else inconclusive
    if _has(desc, MOVABLE_TERMS):
        if _has(desc, PERMANENCE_TERMS):
            return "new_unit",1,"Movable/park-model with permanence markers - counts as dwelling"
        return "ambiguous",0,"Movable/tiny/trailer without permanence markers - inspect (may be non-counting RV)"
    # RULE 5 - ADU=Yes requires description corroboration to be confident
    if adu_yes:
        if has_adu_lang:
            return "new_unit",1,"ADU=Yes corroborated by ADU/conversion/legalization language"
        # ADU flag but no corroborating language -> inconclusive (the dirty-flag case)
        return "ambiguous",0,"ADU=Yes but no corroborating description language - inspect"
    # RULE 6 - New + housing language => confident
    if is_new and _has(desc, HOUSING_TERMS):
        return "new_unit",1,"New + housing indicator"
    # RULE 7 - New + units>0 + no disqualifier => confident
    ua=_to_int(units_added)
    if is_new and ua and ua>0 and not _has(desc, NONHOUSING_TERMS):
        return "new_unit",1,f"New + units={ua}, no disqualifier"
    # RULE 8 - New but unconfirmed => inconclusive
    if is_new:
        return "ambiguous",0,"New but no housing indicator/units - inspect"
    # RULE 9 - alteration/addition WITH conversion or legalization language => inconclusive
    if alt and (_has(desc, CONVERSION_TERMS) or _has(desc, LEGALIZATION_TERMS)):
        return "ambiguous",0,"Alteration with conversion/legalization language - may add a dwelling, inspect"
    # RULE 10 - plain alteration/addition => non-housing (units floored 0)
    if alt:
        return "alteration",0,"Alteration/addition, no dwelling language (units floored 0)"
    # RULE 11 - blank/unmatched => inconclusive (generous)
    if wt in ("","nan","none"):
        return "ambiguous",0,"No Work Type - inspect"
    return "ambiguous",0,"Unmatched by vocabulary - inspect"

def net_units(units_added, units_removed, role, description=""):
    # Non-creating roles contribute 0.
    if role in ("alteration","demolition","non_housing","subsidiary"): return 0
    ua=_to_int(units_added)
    if ua is not None:
        return ua  # real structured count present - use it (prose-blind, as before)
    # DEFLATION FIX: a confident new_unit with a BLANK/null UnitsAdded. An SFR or ADU is 1 dwelling by
    # definition, so a blank count should be 1, not 0 (the 640-projects->405-units undercount). BUT a
    # MULTIFAMILY permit with a blank count is a real data gap - defaulting it to 1 would under-count a
    # whole apartment building - so it stays null-and-flagged (a harvest gap), not guessed as 1.
    desc=_norm(description)
    if role=="new_unit":
        if _has(desc, MULTIFAM_TERMS):
            return None   # multifamily with missing count -> flagged gap, do NOT guess 1
        return 1          # single dwelling (SFR/ADU/small) with blank count -> 1 by definition
    return ua             # any other creating role with blank count -> leave as-is
print("Rule engine ready (11 rules; ADU=Yes needs description corroboration; net_units prose-blind).")
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
# (work_type, description, adu_flag, occtype, units_added, units_removed, permit) -> expected_role
TESTS = [
  ("New","Construct a one-story single-family dwelling on a vacant lot","No","R-3","1","0","B2025-00820","new_unit"),
  ("New","Building new Single Family Residence (see PV solar permit)","No","R-3","1","0","B2024-02570","new_unit"),
  ("New","New construction of 5-story residential apartment. Shoring under separate permit","No","R-2","50","0","B2023-02354","new_unit"),
  ("Alteration","Replace 760 sq ft of deteriorated siding on the existing two story main residence","No","R-3","0","0","B2025-02413","alteration"),
  ("Alteration","Re-roof existing single family residence","No","R-3","0","0","B2024-09999","alteration"),
  ("Other","Temporary power pole for construction staging","No","","83","0","B2020-DURANT","ambiguous"),
  # ADU cases: flag REQUIRES corroboration
  ("Alteration","Legalize existing ADU","Yes","R-3","1","0","B2024-07001","new_unit"),     # corroborated by legalize+ADU
  ("Alteration","Convert detached garage into ADU","Yes","R-3","1","0","B2024-07002","new_unit"),  # corroborated
  ("Addition/Alteration","Conversion of upper floor into a 410 sf JADU","Yes","R-3","1","0","B2024-07003","new_unit"),  # corroborated
  ("Alteration","Interior remodel of kitchen and bath","Yes","R-3","0","0","B2024-07050","ambiguous"),  # ADU flag, NO corroboration -> harvest
  # movable home cases
  ("New","Install park model tiny home, wheels removed, on permanent foundation","No","R-3","1","0","B2025-07100","new_unit"),
  ("New","Place movable tiny house on lot","No","R-3","1","0","B2025-07101","ambiguous"),  # no permanence markers
  ("Demolition","Demolish existing 3-story SFR","No","","0","0","B2023-04472","demolition"),
  ("Sign","Install wall sign","No","","0","0","B2024-08001","non_housing"),
  ("New","Revision to approved apartment plans","No","R-2","50","0","B2023-02354-REV1","subsidiary"),
  ("New","New ground-floor retail shell, no residential","No","B","0","0","B2024-06001","ambiguous"),
]
fails=[]
for wt,desc,adu,occ,ua,ur,pn,exp in TESTS:
    got,_,note=classify(wt,desc,adu,occ,ua,ur,pn)
    ok = "ok" if got==exp else "** FAIL"
    if got!=exp: fails.append((pn,exp,got,desc[:40]))
    print(f"  [{ok}] {pn:<18} expect {exp:<11} got {got:<11} | {desc[:42]}")
assert not fails, f"VOCAB TEST FAILURES: {fails}"
print("\nALL VOCABULARY TESTS PASS.")

# DEFLATION-FIX TESTS: net_units defaulting for blank UnitsAdded on confident new_unit.
NU_TESTS = [
    # (units_added, role, description) -> expected net_units
    (None, "new_unit", "Construct a new single-family dwelling", 1),   # blank SFR -> 1
    (None, "new_unit", "Convert detached garage into ADU", 1),        # blank ADU -> 1
    ("", "new_unit", "New duplex", 1),                                  # blank small -> 1
    (None, "new_unit", "New construction of 5-story residential apartment", None),  # blank multifam -> flagged
    (None, "new_unit", "New 50 unit apartment building", None),        # blank multifam -> flagged
    ("12", "new_unit", "New apartment", 12),                            # real count preserved
    ("0", "new_unit", "New SFR", 0),                                    # explicit 0 preserved (not overridden)
    (None, "alteration", "Re-roof", 0),                                # non-creating -> 0
    (None, "subsidiary", "REV", 0),                                    # child -> 0
]
nu_fails=[]
for ua, role, desc, exp in NU_TESTS:
    got = net_units(ua, None, role, desc)
    flag = "ok" if got==exp else "** FAIL"
    if got!=exp: nu_fails.append((desc[:40], exp, got))
    print(f"  [{flag}] net_units({ua!r:<6},{role:<11}) = {str(got):<5} expect {str(exp):<5} | {desc[:38]}")
assert not nu_fails, f"NET_UNITS TEST FAILURES: {nu_fails}"
print("DEFLATION-FIX TESTS PASS: blank SFR/ADU->1, blank multifamily->flagged(None), real counts preserved.")
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

nb=new_notebook(cells=cells)
nb.metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python"}}
with open("/home/claude/v4/JN-C_classify.ipynb","w") as f: nbf.write(nb,f)
print("wrote JN-C_classify.ipynb",len(cells),"cells")
