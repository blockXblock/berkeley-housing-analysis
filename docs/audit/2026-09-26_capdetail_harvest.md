# CapDetail harvest — the city's own record of its own processing

**Date:** 2026-09-26 · **Status:** harvest running; ingest NOT proposed yet (read-only throughout)
**Scripts:** `scripts/parse_capdetail.py`, `scripts/harvest_capdetail.py`,
`scripts/reparse_capdetail.py`, `scripts/summarize_capdetail.py`
**Output:** `scratch/2026-09-26_capdetail/` (gitignored: `pages/<record>.html.gz` + parsed JSONL)

## Why

v2 can say when an application was FILED and when it was ENTITLED. The step between — the city
**accepting** the application as complete, after each department's review — had never been a fact in
our data; it was inferred from a list-view `Status` string, and earlier in this session I described
the interval as one that "cannot be computed".

That was too flat. The city publishes it. Every Planning record's CapDetail page carries a
PROCESSING STATUS block: each department review task, **the due date the city set itself**, the
disposition, the date it was marked, and **the staff member who marked it**. `ZP2021-0046`
(2136 San Pablo, 126 units):

| task | due | marked | on | by |
|---|---|---|---|---|
| Completeness Review | 2021-04-17 | Incomplete Pending Applicant | 2021-04-29 | Sharon Gong |
| Completeness Review | 2021-04-17 | Application Complete | 2021-08-27 | Sharon Gong |
| CEQA Determination | 2022-08-17 | EIR Required | 2021-08-27 | Sharon Gong |
| Staff Decision | 2022-08-17 | Approved | 2024-03-28 | MJ |
| Appeal | 2024-04-04 | No Appeal | 2024-05-22 | MJ |
| Case Closed | 2024-05-22 | Approved | 2024-05-22 | MJ |

Because both the DUE date and the ACTUAL date are published, filed→accepted can be compared with
the city's own deadline, per record and per year. That is the historical baseline the ministerial /
by-right shift (SB 9, SB 35, SB 330) will be measured against — see
`docs/methodology/seven_rungs_and_the_ministerial_shift.md`, where this is rung 3.

Coverage before this run: **14,936 Planning capIDs held, ~95 visited (0.6%)**, all by hand
(`data/raw/accela_status/*.txt`).

## Scope

The record set is the SAME filter the Planning ingest already owns — `DEV` (record-number prefix)
+ `HOUSING` (language) — **imported** from `scripts/migration/ingest_planning_scope_a.py`, not
retyped. **1,746 records, 100% with a `capdetail_href`**, 2015–2026, ~100–200/year.

`ZCHO` / `ZCBL` / short-term-rental records (home occupations, business licences) dominate the
15,105 Planning records and are not housing; excluding them is what makes this a 1,746-page fetch
rather than a 14,936-page one.

## Parser validated against ground truth, not inspected by eye

`data/raw/accela_status/ZP2021-0046_2136_SAN_PABLO_Ave.txt` turns out to hold **6 records** at that
address, not one — 21 dispositions in total. Compared against **record 1 only**, the parse is an
**exact match: 6 dispositions, none missing, none extra.** Re-verified after every parser change.

## Six traps, each one measured rather than assumed

1. **Processing Status sits in a HIDDEN tab.** `page.inner_text()` returns the page without it
   entirely — the first probe looked like the data did not exist. It is in the HTML, AJAX-filled by
   `ExpandWorkflowSection()`, no click needed. **Parse HTML, not rendered text.**
2. **Waiting on `#divProcessingTable tr` captures the page too early.** That selector matches the
   PLACEHOLDER row present before the AJAX returns, so the page was grabbed empty and only the
   retry got the data. Measured cost: **40% of records needing a needless second fetch, 12.8s/rec
   and a 6-hour ETA.** Waiting for the workflow TEXT (`/Due on|Marked as/`) instead: **4.2s/rec,
   zero retries.**
3. **A retry must be stronger than the first attempt.** With a short settle, `DRCF2018-0007`
   reported **0 tasks when it has 4**, and the retry at the same timeout faithfully reproduced the
   error. The retry now doubles its patience. (CLAUDE.md: *a 0-result is not evidence of absence
   until retried* — but only if the retry is a real retry.)
4. **Accela's SESSION degrades after about four CapDetail views — this was the big one.** A
   controlled A/B over the same 8 records: on one reused page, the first **four** return their
   workflow and **every view after that returns ZERO tasks** and burns the full timeout (16.7s
   each); the same 8 records each on a **fresh page** all return in 2.6–5.0s. So it was never the
   portal's speed, the record type, or the page content — it was the harvester. Worse, **the retry
   was hiding it**: what looked like 73% of records legitimately needing a second look was really a
   fresh session getting one more good view. Measured cost: **18.9s/rec, 73% "retried", ETA 8.7
   hours** → **4.4s/rec, zero retries, zero empties** with a fresh page per record (~0.2s to open).
   Asset blocking also moved from `route("**/*")`, which round-trips every HTML and XHR request
   through a Python callback, to a URL pattern.
5. **An empty capture must never count as done.** The harvester writes the page whether or not the
   parse found anything, and resume skips records whose page exists — so an empty capture becomes
   **permanent**, immune to the retry rule, and indistinguishable from a record that genuinely has
   no workflow. That happened: `DRCP2015-0002` was cached with zero tasks, and a refetch on a fresh
   session returned **5** (*"2597 Telegraph DR for 10 units bldg."*, Withdrawn). Resume now counts a
   page as done only if it actually contains workflow text; a genuinely-empty record is re-attempted
   each run, which is the right price for not fossilising a false absence.
6. **Pages are the durable artifact; the parsed JSONL is derived.** Every page is saved gzipped, so
   parser corrections apply retroactively via `reparse_capdetail.py` without asking the city's
   portal for anything twice.

## Finaled ≠ completed (cross-session, 2026-09-26)

Session 3c looked at five BUILDING CapDetail pages and found the **Certificate of Occupancy
workflow task carries no disposition** even on finaled buildings (`B2019-05574`, `B2021-03302`),
while `Inspection → Finaled` does. Correct — a CO *task* is not a CO fact.

But their conclusion that "the Finaled marking is the fact" of completion is **half the rule**.
`B2018-04001` is *"Full structure Demolition for clearing site for ACHESON COMMONS"* and it is
`Inspection → Finaled` too (2022-02-04). **A demolition finals exactly like a building.** Finaled
is the fact that the permitted WORK finished; what it completed depends on the permit's scope,
which lives in the ADR-002 verdict layer, not in the workflow. Treating Finaled as completion is
the 1914 Fifth Street error (a demo + parking lot + beer garden credited as housing) in a new
place.

Also confirmed: **no dwelling-unit field anywhere on a building CapDetail** — only job value,
construction type, square footage and occupancy class. Units must come from CPRA + the model.
Planning CapDetail *does* carry the parcel APN; building CapDetail does not.

## Related Records is thinner than expected

On the first sample the tab was populated on **1 of 10** records; `ZP2021-0046`'s reads literally
*"No records found."* Two parser corrections came out of 3c's look, both real:

- record numbers are **not** all `PREFIX2022-0001` — `B2022-02844`'s parent is **`ESR-2022-01158`**
  (prefix, hyphen, year, hyphen, serial). A pattern written from Planning records alone drops that
  whole family silently.
- the tab lists the record **itself** as the tree root, so self must be excluded or every record
  appears to reference something.

The relationship prose is now kept verbatim (`"parent to permit B2022-02844"`) rather than
interpreted. **If the low rate holds across all 1,746, the ZP→BP bridge is not in Related Records**,
and permit-to-permit cross-references are the only non-APN edge available to the build's structures
stage — APNs cannot carry identity across re-platting (CLAUDE.md rule 4).

*The measured rate over all 1,746 is appended below when the run completes — not estimated from ten.*

## Next

1. Finish the harvest; re-parse from saved pages; `summarize_capdetail.py` for the rung-3 numbers.
2. **Read-only preview** of the events this would add to v2 (`application_accepted` at rung 3),
   then STOP for John. The canonical DBs are `chmod a-w`; no write is attempted here.
3. Report the Related Records rate to the structures stage.

---

## Dry-run finding (45 records, 2026-09-26): ingesting these naively would DEGRADE `app_complete`

Running the chain on the first 45 records surfaced a semantics problem that the preview gate exists
to catch, and it is the reason no write is proposed yet.

**`application_complete` is per-RECORD; v2 stores it per-PROJECT.** A project has many Planning
records — `2136 San Pablo` has six — and **each one has its own Completeness Review**. `proj38`
(2449 Dwight, 39u) already holds two Application Complete events, 2022-09-30 and 2022-09-27, and
`DRCF2026-0001` at the same site adds a third, **2026-04-02**: the completeness review of a *Design
Review Committee Final* filed in 2026, four years after the application was actually accepted.

**`v_projects_flat.app_complete` aggregates with MAX** (deliberate, 2026-07-10, recorded in
CLAUDE.md). So writing one `application_complete` row per harvested record would set proj38's rung-3
date to 2026-04-02 — the latest sibling review — and the published figure would get *worse*, not
better. This is the same shape as the 3030 Telegraph MAX/entitled trap already documented.

Of 19 projects in the slice with an existing dated event, **11 disagree with CapDetail** — and on
inspection the disagreements are **not errors in either source**. They are different records'
reviews. (The slice is DRC-heavy because pages fetch in sorted order; ZP records, the primary
entitlement applications, come later — so this slice overstates the sibling effect and is not a
basis for a rate.)

**What this means for the ingest, for John to decide:**
per-record rows are the right EVIDENCE (append-only, faithful to the source), but the project-level
rung-3 date must come from the project's **primary entitlement application**, not from whichever
sibling review happened last. My recommendation is to write the evidence per record with the record
number retained in `summary` (as the existing rows do), and derive rung 3 from the primary
application — **not** to flip the view's MAX to MIN, which CLAUDE.md settled for reasons that still
hold.

## Stale-APN guard fired, and was verified rather than asserted

21 record APNs in the slice are absent from the current assessor. A rate that high looked like the
890/892 false-dead trap, so it was checked both ways: the assessor side canonicalises **29,134 of
29,134** rows, `056-1977-011-01` **is** present (as `56-1977-11-1`), and `059-2310-002-05` is
**genuinely** absent — the assessor holds `59-2310-3-2/4/5/6/7/8/9` on that page but no `2-5`.
So the flags are real (re-platted or too-new) and go to John; **nothing is auto-re-pointed.**

Also confirmed: Planning CapDetail gives the parcel APN, and for 1 record in the slice that APN was
the **only** route to the project — the address key missed it.

---

## Machinery, as built (all read-only except the gated ingest, which has not been run)

| script | role |
|---|---|
| `scripts/parse_capdetail.py` | parse one CapDetail page: processing status, parcels, related records, header |
| `scripts/harvest_capdetail.py` | fetch the queue; fresh page per record; verified-empty ledger |
| `scripts/reparse_capdetail.py` | rebuild the parsed JSONL from saved pages (parser fixes apply retroactively) |
| `scripts/capdetail_select.py` | **the one** implementation of "which action is this project's rung 3" |
| `scripts/preview_capdetail_events.py` | read-only report: joins, selection, conflicts, intervals, stale-APN guard |
| `scripts/migration/ingest_capdetail_events.py` | the gated write. Preview by default; `--commit` needs John |
| `scripts/summarize_capdetail.py` | the city's task/disposition VOCABULARY + coverage + false-negative guard |
| `scripts/verify_capdetail_complete.py` | per-record completeness proof; exits non-zero until every record is accounted for |
| `scripts/housing_rules/planning_record.py` | canonical record-ROLE rule (+ `test_planning_record.py`, 13 cases) |

`capdetail_select.py` exists because the preview and the ingest must not hold two copies of the
selection rule — the preview would approve one thing and the write would do another. `summarize`
deliberately does not recompute rung 3.

## The write path is TESTED, not merely written

Exercised against a throwaway copy made by `sqlite3`'s backup API (the canonical DB opened `mode=ro`
throughout; the first attempt, which used `chmod u+w`, was correctly DENIED by John's
`Bash(chmod:*)` rule and was not retried):

| check | result |
|---|---|
| failure injected mid-transaction | rolled back, **0 rows survived** |
| normal commit | committed, verify passed |
| second run | **skips the row** — idempotent |
| `integrity_check` after writes | ok |
| canonical DB during all of it | **refused the write** ("attempt to write a readonly database") |

This proves the MECHANISM. It does not prove the content, because no `ZP` primaries had landed.

## Completeness is asserted with evidence, not with "the run finished"

`verify_capdetail_complete.py` puts every queued record in exactly one bucket: `captured`,
`verified_empty`, `page_no_wf`, `errored`, `missing`. **`page_no_wf` is the dangerous one** — a page on
disk with no workflow and no ledger entry, which resume would skip forever. It has stayed at **0**
since the resume rule was fixed, and it is where `DRCP2015-0002` sat when it reported zero tasks and
actually had five.

## The city labels the same fact differently by record type

| record type | Completeness Review disposition |
|---|---|
| `Zoning Permit` (primary application) | **`Application Complete`** |
| `Zoning Certificate Building Permit` (ministerial) | **`Complete`** |
| `Design Review Staff Level` | `Complete` 25, `Incomplete Pending Applicant` 27, `Void` 27 |
| `Zoning Research Letter` | *none at all* — confirms `not_an_application`: an inquiry is processed, but nothing is ever deemed complete because nothing was applied for |

The rung-3 rule matches `^application complete$`, which is right for the only path it reads. The regex
was **not** widened to catch the bare `Complete`: that would also absorb the ministerial `Complete`,
which plausibly means *the clearance finished* rather than *the application was accepted* — a
different fact. Instead `summarize_capdetail.py` carries a **false-negative guard** that prints any
primary-application completeness disposition the rule does not recognise, flagging acceptance-shaped
strings for a decision. Widening a pattern to make a count rise is how a classifier starts agreeing
with itself.

## Corrections made to this session's own work, recorded because the pattern repeats

1. **`Structural Alteration Permit` → `primary_application`** was wrong; all 18 are `LMSAP`, a
   *Landmarks* alteration approval. It selected a landmarks review as a project's acceptance date.
2. **A 2-token address key** collided every multi-word street (`1820 SAN PABLO` matched `1843 San
   Ramon`), inflating a "missing housing" claim from 9 records/659 units to 14/1,587.
3. **The wrong canon was imported.** `build_v2/s0_keys.normalize_address` is the v3 pipeline's internal
   keying; the rule-4c canon is `housing_rules.address.normalize_address`. Importing the decoy *felt*
   like compliance. CLAUDE.md flags the APN canon unmissably and never names the address function —
   four copies were consolidated 2026-07-03 and two had reappeared by 2026-09-26.
4. **The auto-loaded memory `apn-crosswalk-apn-norm` was actively wrong** — it recommended
   strip-non-digits (the 890/892 false-dead trap) as "the canonical matcher" and cited a `apn_norm`
   column the June refresh had removed. Rewritten.

All four are the same failure: a key or a rule with no addressable referent gets re-invented.

---

## ⚠ THE QUEUE ITSELF HAS A FALSE-NEGATIVE BUG (found 2026-09-26, late in the harvest)

**`ZP2022-0046` — 3000 Shattuck, 10 stories, 166 dwellings, 17 very-low-income, density bonus — was
never fetched, because the `HOUSING` filter does not match its description.**

    "Demolish the existing gas station, and construct a 10-story (114 feet) mixed-use building
     utilizing a Density Bonus, with 166 dwellings, including 17 Very Low-Income units, and
     1,043 square-feet of commercial space."

Two holes, both in one regex:
* `\bdwelling\b` **cannot match the plural "dwellings"** — there is no word boundary between
  `dwelling` and `s`. A description that says "166 dwellings" instead of "166 units" is invisible.
* the numeric branch is `\d+\s*[-\s]?\s*units?\b` — it recognises "N units" and **never "N dwellings"**.

### It inverted a conclusion recorded earlier in this document

The `proj10` "conflation" finding above had the records right and the verdict backwards. v2's `proj10`
holds **166 units**; `ZP2022-0046` describes **166 dwellings**. **proj10 IS the 2022 project.** So v2's
`app_complete` of 2022-08-03 was CORRECT, and the harvest's selection of `ZP2015-0229` → 2017-04-30 was
WRONG — it chose an older, different application at the same address because the filter had hidden the
right one. At least one of the selected rung-3 rows is wrong for this reason, and nothing guarantees it
is the only one.

### Scale

**184** `DEV` records are excluded by `HOUSING` yet match a wider housing pattern: **58 Zoning
Permits**, 38 `ZCBP`, 13 Pre-Applications, 18 design review, 40 Zoning Research Letters (the last are
correctly excluded — they are inquiries). Only one other states a dwelling count the filter could not
see (`ZP2019-0159`, "3 dwellings"), so most of the 184 are plausibly genuine non-housing — but the 58
Zoning Permits need individual review before the queue can be called complete.

### What this means for every number in this document

**The 1,746 is a FLOOR, not a census.** Every count here rests on that filter, and the filter has a
demonstrated hole. Restating the counts without restating this qualification would be exactly the
error the identity work is about: a figure whose provenance is not recoverable.

### Whose bug, honestly

`HOUSING` is imported from `scripts/migration/ingest_planning_scope_a.py` — imported deliberately, so
as not to write a fourth per-script copy, which was the right call and stays the right call. But
importing the canon is not the same as verifying it, and CLAUDE.md's "verify artifacts, never trust a
summary" applies to inherited CODE as much as to an inherited number. The filter was adopted on the
strength of it being canonical, and never tested against a description that says "dwellings". The fix
belongs in `ingest_planning_scope_a.py`, not in a local patch here — and the 1,746-record queue it
produced needs a second pass over the excluded Zoning Permits (John's scope call).

**This is also the single best argument for the model layer.** "Is this record a housing development?"
is the question a regex just failed on a sentence any reader answers instantly — and it now has a
known-positive test case with a name and a unit count.
