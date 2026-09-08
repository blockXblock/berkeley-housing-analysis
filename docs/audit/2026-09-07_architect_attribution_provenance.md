# The v1→v2 migration's architect attributions are wrong ~41% of the time

**2026-09-07** · read-only finding · no corrections applied

## What was tested

Every project in v2 that holds **both** a plan set on R2 **and** a named architect — 29 of
them — had its plan-set title block read and compared with what `project_participants`
asserts. Title blocks were read by OCR (`pdftoppm -r 300` → rotate → `tesseract --psm 6`);
architectural title blocks run vertically down the sheet edge, so orientation is searched
and the pass with the most recoverable language is kept.

## The result

| provenance of v2's architect row | agree | **disagree** | unreadable |
|---|---:|---:|---:|
| `migration_v1_to_v2_20260507` | 13 | **9** | 1 |
| `planset_title_block_2026-09-02` | 6 | **0** | 0 |

**Every disagreement is a v1→v2 migration row. Every drawings-sourced row is correct.**

This is the finding. Not "v2's architect data is unreliable" — the drawings-sourced rows are
sound 6 for 6 — but "the v1→v2 migration's architect attributions are unreliable, at roughly
a 41% error rate, and the remedy is known."

The 6/6 does double duty: it is also an independent check on the OCR method, because those
six were read off the same title blocks by a different route on 2 September.

## The shape of the errors

Six of the nine are v2 naming **one of the two dominant firms where the drawings name the
other** — not a scatter of random names:

| project | units | v2 says | the title block says |
|---|---:|---|---|
| 2700 Shattuck Ave | 359 | Studio KDA | Trachtenberg Architects |
| 2920 Shattuck Ave | 242 | Studio KDA | Trachtenberg Architects |
| 1899 Oxford St | 212 | Studio KDA | Trachtenberg Architects |
| 2462 Bancroft Way | 66 | Studio KDA | Trachtenberg Architects |
| 2442 Haste St | 34 | SDT | studiokda.com |
| 2115 Kittredge St | 148 | DLR Group | Studio KDA (+ Gilbane Development) |

Three name firms absent from v2 entirely:

| project | units | v2 says | the title block says |
|---|---:|---|---|
| 2127 Dwight Way | 58 | SDT | **Levy Design Partners / LDP Architecture** |
| 2018 Blake St | 12 | SDT | **DNM Architecture** |
| 2100 Milvia St | 205 | SDT | inconclusive — OCR too poor to call |

**Consequence for the concentration claim.** The finding that two firms dominate Berkeley's
large-project design work SURVIVES — it is strengthened, since four large projects move
*to* Trachtenberg/SDT. What does not survive is the split between the two. Any public
statement of the form "firm X designed N% of Berkeley's housing" is resting on rows that
are wrong about a third of the time, in a way that specifically confuses those two firms
with each other.

## Scope of what remains

- **44** architect rows are migration-sourced (8,484 units); **6** are plan-set-sourced (2,121).
- **21** migration rows covering **5,374 units** have a plan set on R2 and are **unchecked**.
  At the observed rate, roughly **nine more are wrong**.
- **20** further projects hold a plan set and name **no architect at all** — there the title
  block teaches a name rather than checking one.

## What the title blocks carry beyond the architect

Role headers found across the 29 sheets:

```
OWNER 24 · LANDSCAPE ARCHITECT 13 · APPLICANT 10 · ARCHITECTURE 9 · SURVEYOR 4
CIVIL ENGINEER 2 · MECHANICAL 2 · ELECTRICAL 2 · PLUMBING 2 · GENERAL CONTRACTOR 2
CONTRACTOR 2 · ARCHITECT OF RECORD 2 · DESIGN CONSULTANT 2 · STRUCTURAL ENGINEER 1
INTERIOR DESIGN 1 · LIGHTING 1 · TITLE 24 1
```

**16 of v2's 21 role types have zero rows.** Landscape architects are named on 13 of 29
sheets. The 2352 Shattuck sheet alone yields eight firms across eight roles including a
general contractor (West Builders, Inc.) — and marks with an asterisk which consultants are
under separate contract to the owner, which is contract structure the players page currently
disclaims knowing.

This corrects an earlier expectation recorded in the same investigation: that plan sets
would not name contractors because the GC is not chosen at entitlement. On the larger sheets
they do.

## First read from the no-architect group

`3030 Telegraph Ave` (proj150, 144 units) held a plan set and named no professional at all —
v2 knew only its assessor owner, `ALTA BATES MEDICAL CENTER`. The title block, read at the
highest OCR confidence of any sheet so far, names four:

| role on the sheet | firm | in v2? |
|---|---|---|
| ARCHITECTURE | **Left Coast Architecture Inc.** (leftcoastarch.com) | new |
| LANDSCAPE ARCHITECT | **JETT Landscape Architecture** | new |
| civil (inferred: `GIBSON, INC` + `cbandg.com`) | **Carlson, Barbee & Gibson** | new |
| DEVELOPER | Riaz Capital (riazcapital.com) | already recorded |

Three firms entirely new to the database, on a project that previously had no professional
of any kind — and the developer independently corroborates a firm already on the record.
JETT also appears on the 2700 Shattuck sheet, so the landscape tier has repeat players too.

This is the pattern the remaining 19 no-architect projects should follow: the gap group
teaches names, where the verification group only checks them.

## Status and cautions

**Nothing has been corrected.** These are OCR candidates, not findings-of-record. The
consultant block is a multi-column layout that OCR flattens — role headers land on one line
and firm names on another — so positional assignment is a guess. Each of the nine
disagreements needs a human looking at the sheet before any row changes.

Artifacts: `scratch/2026-09-07/plansets/team_candidates.json` (per-project roles and firm
candidates), `scratch/2026-09-07/planset_team.py` (verification run),
`scratch/2026-09-07/planset_gap.py` (the no-architect projects).
