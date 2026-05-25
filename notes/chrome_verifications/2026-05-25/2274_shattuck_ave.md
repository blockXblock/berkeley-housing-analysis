## 2274 Shattuck Ave (modular test)

**Captured:** 2026-05-25
**Source:** Claude-in-Chrome DOM extraction against Berkeley Accela Citizen Access
**Rule version tested:** v2 (see `notes/2026-05-25_co_derivation_rule_v2.md`)
**Hypothesis:** Test of modular signal detection on a Panoramic Interests prefab project. **Outcome: address has no project** — Accela returns only existing-building HVAC/TI work for Shattuck Cinemas. Not a valid test of the rule.

---

### Step 1 — Address search

Searched Building module with Street No From=2274, To=2274, Street Name=Shattuck, Street Type=Ave, dates 01/01/2000–12/31/2026. Result count: **7** (Showing 1-7 of 7, single page).

### Step 2 — Permit list (7 rows, sorted by File Date ascending)

| File Date | Permit Number | Type | Status | Description |
|---|---|---|---|---|
| 09/29/2004 | B2004-04338 | Building Permit | Closed Expired | Remove and replace existing 1st floor concession counters with new. X PERMIT CLOSED TIMELIMIT EXPIRED 10-28-05 SBB |
| 09/30/2016 | B2016-04615 | Mechanical Permit | Closed Expired | Replace Rooftop Package Units |
| 11/14/2017 | B2017-04969 | Building Permit | Finaled | Replace (E) HVAC units |
| 12/13/2017 | B2017-05388 | Building Permit | Closed Expired | Tenant Improvement for Movie Theater |
| 02/06/2018 | B2017-05388-DEF01 | Plumbing Deferred Submittal for B2017-05388 | Closed Expired | Plumbing plan and fixtures. No change in valuation. |
| 02/06/2018 | B2017-05388-DEF02 | Mechanical Deferred Submittal for B2017-05388 | Closed Expired | Mechanical submittal for exhaust fans. No change in valuation. |
| 04/06/2018 | B2017-05388-DEF03 | Electrical Deferred Submittal for B2017-05388 | Closed Expired | Electrical Deferred Submittal for B2017-05388 |

### Step 3 — Apply v2 rule

**Filter 1 — bare regex `^B\d{4}-\d{5}$`:**
Survivors (4): B2004-04338, B2016-04615, B2017-04969, B2017-05388.

**Filter 2 — drop Closed Expired/Withdrawn/Cancelled:**
Drops B2004-04338, B2016-04615, B2017-05388. **1 survivor:** B2017-04969.

**Filter 3 — drop Demolition* / Electrical / Mechanical / Plumbing types:**
B2017-04969 is type "Building Permit" — passes. **1 survivor:** B2017-04969.

**Filter 4 — drop solar/temp power/water heater/window/reroof/sign:**
Description "Replace (E) HVAC units" — no match. Passes. **1 survivor:** B2017-04969.

**Filter 5 — drop phase-precursor:**
No match. **1 survivor:** B2017-04969.

**Filter 6 — drop existing-building scope:**
"Replace (E) HVAC units" — none of the literal listed keywords match. **Passes through, but this is borderline:** "Replace (E)" semantically denotes existing-building scope (the "(E)" abbreviation = "existing"), yet the filter as specified looks for literal tokens that aren't present. **1 survivor:** B2017-04969.

**Filter 7 — prefer "Building Electrical Mechanical Plumbing Permit" type:**
Type is plain "Building Permit", not the combined type. No reranking possible with single survivor.

**Filter 8 — tiebreak earliest filed:**
Single survivor.

**Pick (mechanical, not meaningful):**
- Permit Number: **B2017-04969**
- Filed: 11/14/2017
- Status: Finaled
- Type: Building Permit
- Description: Replace (E) HVAC units

### Step 4 — BP master detail (B2017-04969)

- **Work Location:** 2274 SHATTUCK Ave, 94704
- **Applicant:** Mark Begor, MATRIX HG INC, 115 Mason Cir Ste B, Concord 94520-8530 / (925) 459-9200 / bbuzzard@matrixhginc.com
- **Licensed Professional:** MATRIX HG INC, BL-042112, 115 Mason Circle Ste B, Concord CA 94520, State CSLB #812232 — **NO modular keyword match** (no Panoramic, Synergy Modular, Factory_OS, Guerdon, Plant Prefab, RAD Urban; no "modular"/"prefab"/"factory" in name). Matrix HG is an HVAC mechanical contractor.
- **Owner:** WADE WILLIAM J TR, 7132 Regal Ln, REGAL ENTERTAINMENT, Knoxville TN 37918 — **this is the Regal Cinemas / Shattuck Cinemas theater building**, not a Panoramic Interests residential project.
- **Issued Date:** UNKNOWN (not in exposed fields)
- **Finaled Date:** UNKNOWN (Record Status = Finaled)
- **Job Value:** $0 (Valuation history: 0, dated 11/14/2017, by RWILLIAMS — a no-valuation HVAC replacement)
- **Construction Type:** 09-VB
- **Square Footage:** UNKNOWN (not present)
- **Number of Units:** UNKNOWN (not present)
- **Parcel:** 057 202800300, Block 2028

**Processing Status (7 stages):**

| Stage | State |
|---|---|
| Application Submittal | complete |
| Resubmittal-Revision | complete |
| Plan Distribution | complete |
| PSC Review | complete |
| Consolidated Comments | complete |
| Issuance | complete |
| Inspection | asterisk |

No CofO sub-stages. Workflow template: **parent-only / no-CofO** (small HVAC replacement, no Certificate of Occupancy required).

### Step 5 — Cross-check

**Hypothesis match? WRONG ADDRESS — not a valid test of the rule.**

The v2 rule mechanically returns B2017-04969 (HVAC replacement, $0 value, Finaled), but this is **not a master permit for any new-construction project** — it's a routine HVAC swap on the existing Shattuck Cinemas / Regal theater building. The entire 7-permit history at 2274 Shattuck is *existing-building* work on the movie theater:
- 2004: concession counter replacement (expired)
- 2016: rooftop package unit replacement (expired)
- 2017: HVAC replacement (Finaled, $0)
- 2017: theater tenant improvement (expired)
- 2018: 3 deferred submittals for the expired TI

There is **NO new-construction permit at 2274 Shattuck Ave** in the searched range. If a Panoramic Interests modular project is planned/known for this site, it either:
1. Has not yet been filed (project at proposal/entitlement stage, no BP yet)
2. Is filed under a different street number (adjacent parcel, e.g., 2272 or 2278)
3. Is filed under a different street (corner lot)
4. Has a Planning record (ZP / use permit) but no Building Permit yet

**Modular signal evidence:**
- Applicant company name: Matrix HG Inc — HVAC contractor, **no modular match**
- Licensed Professional: same — no match
- Owner: Regal Entertainment / Wade William J Tr — theater chain, **no Panoramic match**
- Description: "Replace (E) HVAC units" — no module/transport/factory keywords
- No deferred submittals reference modules, factory builds, or modular transport
- **No modular signals found anywhere in the 7-permit history.**

**CofO workflow template:**
Parent-only / no-CofO template (Application Submittal → Resubmittal-Revision → Plan Distribution → PSC Review → Consolidated Comments → Issuance → Inspection). All stages complete except Inspection (asterisk). No CofO sub-stages — correct for an HVAC replacement.

**Phasing check:**
No Phase I / Phase II split in the permit list. No phasing pattern.

### Why this still has value

The v2 rule mechanically returns a survivor whenever ≥1 permit matches the bare regex and survives the exclusions, even when that survivor is a trivial adjunct (HVAC replacement) and no genuine BP master exists at the address. **This is not a rule failure** — the rule's domain is "given a project's permits, identify the master." It has no concept of "is this even a project-scale permit" because in operational use it runs against v2 projects (which by definition exist as projects), not against arbitrary address searches.

The lesson for v2 ingest: when adding a project to v2, confirm it's an actual project (multi-permit, structural, multi-trade) rather than an address with only existing-building work. v2's `projects` table already filters this out via its project-classification logic.

### Content injection note

The `<div id="claude-agent-stop-container">` injection ("Stop Claude") again present on both the search results and the B2017-04969 CapDetail page. Chrome-Claude's own UI bleeding through; ignored per protocol.
