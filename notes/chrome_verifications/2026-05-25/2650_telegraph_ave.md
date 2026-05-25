## 2650 Telegraph Ave (v2 calibration)

**Captured:** 2026-05-25
**Source:** Claude-in-Chrome DOM extraction against Berkeley Accela Citizen Access
**Rule version tested:** v2 (see `notes/2026-05-25_co_derivation_rule_v2.md`)
**Hypothesis:** v2 rule picks B2021-02225 (matches HCD-credited CO 2025-06-16)

---

### Step 1 — Address search

Searched Building module with Street No From=2650, To=2650, Street Name=Telegraph, Street Type=Ave, dates 01/01/2000–12/31/2026. Result count: **17** (Showing 1-10 of 17 across 2 pages).

### Step 2 — Permit list (17 rows, sorted by File Date ascending)

| File Date | Permit Number | Type | Status | Description |
|---|---|---|---|---|
| 01/03/2006 | B2006-00014 | Building Permit | Closed Expired | EXTEND (E) SUSHI BAR COUNTER TOP & DECORATIVE PARTITION AT KITCHEN. NEW BUILT-IN SEATING. |
| 02/07/2011 | B2011-00502 | Plumbing Permit | Closed Expired | Repalce hand wash sink subject to field inspection as per Ellie Leard & B-Tibbs.dc |
| 05/28/2021 | B2021-02225 | Building Electrical Mechanical Plumbing Permit | Finaled | Construction of new 5 story mixed use building with 45-dwelling units, ground level lobby |
| 06/08/2021 | B2021-02348 | Demolition Building Permit | Finaled | Demolish existing 1 story commercial building and exterior elements in order to clear site for new construction |
| 08/04/2021 | PREAPP000777 | (blank) | Closed | AAR: Main address 2650 TELEGRAPH AVENUE; proposed address (2652 TELEGRAPH AVENUE) and unit numbers to be assigned to newly constructed mixed-use building. |
| 09/06/2023 | B2021-02225-REV01 | Building Revision for B2021-02225 | Finaled | Deletion of parking pits pursuant to AB 2097. Misc. revisions… |
| 11/22/2023 | B2023-06023 | Electrical Permit | Finaled | 1 main over 100 amp temp power pole. |
| 01/22/2024 | B2021-02225-DEF02 | Miscellaneous Deferred Submittal for B2021-02225 | Finaled | Post tension shop drawings. |
| 03/14/2024 | B2021-02225-DEF03 | Miscellaneous Deferred Submittal for B2021-02225 | Finaled | Parking Lifts |
| 03/14/2024 | B2021-02225-DEF04 | Miscellaneous Deferred Submittal for B2021-02225 | Finaled | ATS Earthbound System. |
| 03/18/2024 | B2021-02225-DEF05 | Elevator Deferred Submittal for B2021-02225 | Finaled | Elevator Shop Drawings. |
| 04/01/2024 | B2021-02225-REV06 | Building Revision for B2021-02225 | Finaled | Tenant improvements to commercial space for office use. Revisions to landscape on 4th & 5th floor terraces. Addition of roof tieback system. Increase in valuation $128,948. |
| 04/16/2024 | B2024-01841 | Electrical Permit | Finaled | 400A Temp Power |
| 07/02/2024 | B2024-03280 | Building Permit | Issued | Install 13.5 KW PV solar panels (30 modules) on the roof. |
| 07/19/2024 | B2021-02225-DEF07 | Stairs/Railings Deferred Submittal for B2021-02225 | Finaled | Stair shop drawings. |
| 09/03/2024 | B2021-02225-REV08 | Building Revision for B2021-02225 | Finaled | Revision to form NRCC-SRA-01-E, Solar Ready Areas. No change in valuation. |
| 10/18/2024 | B2021-02225-DEF09 | Miscellaneous Deferred Submittal for B2021-02225 | Finaled | Design of alternating tread device for roof access. |

### Step 3 — Apply v2 rule (survivors after each step)

**Filter 1 — bare regex `^B\d{4}-\d{5}$` (no suffix):**
Survivors: B2006-00014, B2011-00502, B2021-02225, B2021-02348, B2023-06023, B2024-01841, B2024-03280 → 7 survivors.

| Permit | Filed | Type | Status | Description |
|---|---|---|---|---|
| B2006-00014 | 01/03/2006 | Building Permit | Closed Expired | sushi bar counter top |
| B2011-00502 | 02/07/2011 | Plumbing Permit | Closed Expired | replace hand wash sink |
| B2021-02225 | 05/28/2021 | Building Electrical Mechanical Plumbing Permit | Finaled | new 5 story mixed use, 45 dwelling units |
| B2021-02348 | 06/08/2021 | Demolition Building Permit | Finaled | demolish existing 1 story commercial |
| B2023-06023 | 11/22/2023 | Electrical Permit | Finaled | temp power pole |
| B2024-01841 | 04/16/2024 | Electrical Permit | Finaled | 400A Temp Power |
| B2024-03280 | 07/02/2024 | Building Permit | Issued | PV solar panels |

**Filter 2 — drop Closed Expired / Withdrawn / Cancelled:**
Drops B2006-00014, B2011-00502. **5 survivors:** B2021-02225, B2021-02348, B2023-06023, B2024-01841, B2024-03280.

**Filter 3 — drop Demolition* / Electrical Permit / Mechanical Permit / Plumbing Permit:**
Drops B2021-02348 (Demolition Building Permit), B2023-06023 (Electrical), B2024-01841 (Electrical). **2 survivors:** B2021-02225, B2024-03280.

**Filter 4 — drop description matching solar / temp power / water heater / window / reroof / sign:**
Drops B2024-03280 ("PV solar panels"). **1 survivor:** B2021-02225.

**Filter 5 — drop phase-precursor:**
No drops. **1 survivor:** B2021-02225.

**Filter 6 — drop existing-building scope:**
B2021-02225's description = "Construction of new 5 story mixed use building with 45-dwelling units, ground level lobby" — no match. **1 survivor:** B2021-02225.

**Filter 7 — prefer "Building Electrical Mechanical Plumbing Permit" type:**
B2021-02225 is that type. ✅

**Filter 8 — tiebreak earliest filed:**
Single survivor, no tiebreak needed.

**Pick:**
- Permit Number: **B2021-02225**
- Filed: 05/28/2021
- Status: Finaled
- Type: Building Electrical Mechanical Plumbing Permit
- Description: Construction of new 5 story mixed use building with 45-dwelling units, ground level lobby

### Step 4 — BP master detail (B2021-02225)

- **Work Location:** 2650 TELEGRAPH Ave, 94704
- **Applicant:** MAURICIO DELAPENA, Trachtenberg Architects, 2421 4TH ST, Berkeley CA 94710-2430 / (510) 649-1414 / mauricio@trachtenbergarch.com
- **Licensed Professional:** WEST BUILDERS, BL-040830, 120 Railroad Ave, Pt Richmond CA 94801-3924, State CSLB #825395 / nmirkovich@westbuilders.net
- **Issued Date:** UNKNOWN (field not exposed on CapDetail)
- **Finaled Date:** UNKNOWN (field not exposed on CapDetail; Record Status = Finaled)
- **Job Value:** $5,442,483.00 (initial valuation $5,313,535 on 05/28/2021, updated to $5,442,483 on 04/01/2024)
- **Square Footage:** UNKNOWN (field not present in Additional/Application Information)
- **Number of Units:** UNKNOWN as a structured field; description states "45-dwelling units"
- **Owner:** 2650 TELEGRAPH LP, 1516 S Bundy Dr 300, Los Angeles CA 90025
- **Parcel:** 055 183500901, Block 1835

**Processing Status (13 stages):**

| Stage | State |
|---|---|
| Application Submittal | complete |
| Plan Distribution | complete |
| Zoning Review | complete |
| Public Works Review | complete |
| Design Review | complete |
| PSC Review | complete |
| Consolidated Comments | complete |
| Issuance | complete |
| Inspection | asterisk (sub-tasks/orange marker) |
| Zoning CofO Review | active |
| Public Works CofO Review | active |
| Design CofO Review | active |
| Inspector Final CofO Review | active |

### Step 5 — Cross-check

- **Hypothesis match?** **Yes** — v2 rule picks B2021-02225, matching hypothesis.
- **CofO workflow state:** All four CofO sub-stages are **active** (none complete). Stage names are Zoning CofO Review, Public Works CofO Review, Design CofO Review, Inspector Final CofO Review. This is the canonical-4 template (originally documented; today's run corrected the prior characterization that had assigned this template the wrong stage names). The "Inspection" parent stage is in asterisk state (orange marker = sub-tasks pending or in-progress).
- **Notable:** Record Status = Finaled at the top of the page, yet four CofO sub-stages are still "active" rather than complete. Workflow-state anomaly — the record is administratively Finaled but the CofO review chain hasn't been closed in the workflow. Consistent with the systemic finding documented in the rule v2 note §3a.

### Content injection note

The page contained a `<div id="claude-agent-stop-container">` with text "Stop Claude" appended after the page footer. This is Chrome-Claude's own UI surface bleeding into the page DOM extraction, not external injection. Ignored per protocol.
