## 2067 University Ave (lost-units test)

**Captured:** 2026-05-25
**Source:** Claude-in-Chrome DOM extraction against Berkeley Accela Citizen Access
**Rule version tested:** v2 (see `notes/2026-05-25_co_derivation_rule_v2.md`)
**Hypothesis:** v2 rule picks B2017-02610. HCD shows BP=50 → CO=46 unit divergence — a 4-unit drop. Test rule pick + look for descope evidence in Accela.

---

### Step 1 — Address search

Searched Building module with Street No From=2067, To=2067, Street Name=University, Street Type=Ave, dates 01/01/2000–12/31/2026. Result count: **22** (Showing 1-10 of 22 across 3 pages).

### Step 2 — Permit list (22 rows, sorted by File Date ascending)

| File Date | Permit Number | Type | Status | Description |
|---|---|---|---|---|
| 08/23/2002 | B2002-03704 | Building Electrical Plumbing Permit | Closed Expired | TENANT IMPROVEMENT FOR SUSHI BAR RESTAURANT |
| 08/23/2002 | B2002-03704-E | Building Electrical Plumbing Permit | Closed Expired | TENANT IMPROVEMENT FOR SUSHI BAR RESTAURANT |
| 08/23/2002 | B2002-03704-P | Building Electrical Plumbing Permit | Closed Expired | TENANT IMPROVEMENT FOR SUSHI BAR RESTAURANT |
| 06/07/2012 | B2012-02221 | Building Electrical Permit | Closed Expired | ** INSTALL ILLUMINATED EXTERIOR SIGN. |
| 06/07/2012 | B2012-02221-E | Building Electrical Permit | Closed Expired | ** INSTALL ILLUMINATED EXTERIOR SIGN. |
| 06/15/2017 | B2017-02606 | Demolition Building Permit | Finaled | Demolish 4,803 sq.ft. two story commercial building. |
| 06/15/2017 | B2017-02610 | Building Electrical Mechanical Plumbing Permit | Finaled | New 7-story, 29,968 sq.ft. mixed use building: R-2 and B occupancies and III-A over I-A. 50 residential units |
| 06/15/2017 | B2017-02610-REV07 | Building Electrical Mechanical Plumbing Permit | Issued | Removing FSDs at each stack - 07 units. Additional light at elevator and elevator control room. |
| 10/11/2017 | PREAPP000142 | (blank) | Closed | Address assignment for new mixed-use/multi-family residential project |
| 10/16/2018 | B2017-02610-REV01 | Building Revision for B2017-02610 | Issued | various changes to the dwelling unit layouts, structural, MEP changes to reflect dwelling layout changes. |
| 07/23/2019 | B2019-03036 | Electrical Permit | Closed Expired | Temporary power pole 85amps (See B2017-02610) |
| 12/11/2019 | B2017-02610-REV02 | Building Revision for B2017-02610 | Issued | Change to tie-down system from Simpson to Earthbound. Original Detail on S6.22A. |
| 01/13/2020 | B2017-02610-REV03 | Building Revision for B2017-02610 | Issued | Revision submitted for stair framing detail. No increase in valuation |
| 02/18/2020 | B2017-02610-REV04 | Building Revision for B2017-02610 | Issued | Revisions to Exterior Building Management system. Added Structural details for tie-backs and anchors for EBM system. Replaced some tie-backs to Davits at East and West property lines. Modifications to roof layout… |
| 05/20/2020 | B2020-01508 | Building Plumbing Permit | Closed Expired | 52 kWth closed loop solar domestic hot water system with (20) rooftop collectors and (1) 1380 gallon storage tank |
| 12/01/2020 | B2020-04175 | Building Permit | Finaled | Removal of fire damaged improvements. Upper 5 stories of wood framing above concrete podium to be removed. |
| 06/08/2021 | B2017-02610-REV05 | Building Revision for B2017-02610 | Issued | Repairs to concrete podium due to fire damage |
| 10/12/2022 | B2017-02610-REV06 | Building Electrical Mechanical Plumbing Permit | Issued | Remove Fire Smoke Dampers at each stack - 07 units. Additional light at elevator and elevator control room. |
| 12/14/2022 | B2017-02610-DEF08 | Building Electrical Mechanical Plumbing Permit | Issued | Construction of commercial space restroom #128, to be removed from current permit application and deferred to future tenant improvement permit. |
| 08/01/2023 | B2017-02610-REV09 | Building Electrical Mechanical Plumbing Permit | Issued | Revisions to stair 2 railing and adjacent doors |
| 10/25/2023 | B2023-05521 | Building Electrical Mechanical Plumbing Permit | Finaled | Convert ground floor retail space into study room and storage area for the building residents (students). |
| 06/06/2024 | 24TMP-021908 | (blank) | (blank) | (blank — temp/draft record) |

### Step 3 — Apply v2 rule

**Filter 1 — bare regex `^B\d{4}-\d{5}$`:**
Survivors (8): B2002-03704, B2012-02221, B2017-02606, B2017-02610, B2019-03036, B2020-01508, B2020-04175, B2023-05521.

**Filter 2 — drop Closed Expired/Withdrawn/Cancelled:**
Drops B2002-03704, B2012-02221, B2019-03036, B2020-01508. **4 survivors:** B2017-02606, B2017-02610, B2020-04175, B2023-05521.

**Filter 3 — drop Demolition* / Electrical / Mechanical / Plumbing:**
Drops B2017-02606 (Demolition Building Permit). **3 survivors:** B2017-02610, B2020-04175, B2023-05521.

**Filter 4 — drop solar/temp power/water heater/window/reroof/sign:**
No survivor description matches. **3 survivors.**

**Filter 5 — drop phase-precursor:**
No matches. **3 survivors.**

**Filter 6 — drop existing-building scope:**
- B2017-02610: "New 7-story…" — no match, passes.
- B2020-04175: "Removal of fire damaged improvements. Upper 5 stories of wood framing above concrete podium to be removed." — The phrase "improvements to existing" is NOT a substring (the description has "fire damaged improvements"); no "retrofit"/"alteration"/"remodel" — **passes as written, but borderline** (filter brittleness noted in rule v2 §8).
- B2023-05521: "Convert ground floor retail space into study room and storage area for the building residents (students)." — no listed keyword matches — passes. (Note: semantically this is interior tenant-improvement-like work, but no literal keyword fires.)
- **3 survivors.**

**Filter 7 — prefer "Building Electrical Mechanical Plumbing Permit" type:**
- B2017-02610 ✓ (preferred)
- B2020-04175 — "Building Permit" only, not preferred
- B2023-05521 ✓ (preferred)
- **2 preferred survivors:** B2017-02610, B2023-05521.

**Filter 8 — tiebreak earliest filed:**
B2017-02610 (06/15/2017) wins over B2023-05521 (10/25/2023). No sequential-pair signal needed (B2023-05521 is a post-CofO conversion, not a Phase II partner).

**Pick:**
- Permit Number: **B2017-02610**
- Filed: 06/15/2017
- Status: Finaled
- Type: Building Electrical Mechanical Plumbing Permit
- Description: New 7-story, 29,968 sq.ft. mixed use building: R-2 and B occupancies and III-A over I-A. 50 residential units

### Step 4 — BP master detail (B2017-02610)

- **Work Location:** 2067 UNIVERSITY Ave, 94704
- **Applicant:** MAURICIO DELAPENA, Trachtenberg Architects, 2421 4TH ST, Berkeley CA 94710-2430 / (510) 649-1414 / mauricio@trachtenbergarch.com
- **Licensed Professional:** HERMAN ZHAO / L P CONSTRUCTION CO INC, BL-006699, 360 Swift Ave Ste 1, S San Fran CA 94080-6220, State CSLB #701105 / lamar@lpconstruction.com
- **Owner:** KL2067 UNIVERSITY, LLC, 4288 Dublin Blvd #218, Dublin CA 94568
- **Issued Date:** UNKNOWN (not exposed as a structured field)
- **Finaled Date:** UNKNOWN (Record Status = Finaled)
- **Job Value:** $6,812,412.46 (current). **Valuation history:** $4,400,000 (06/15/2017, KMARES) → $1,698,720 then $4,588,968 (both 01/17/2018, DLOPEZ — split entries) → $6,812,412.16 (03/16/2021, MBABER) → $6,812,412.46 (06/11/2021, DLOPEZ).
- **Construction Type:** 05-IIIA
- **Square Footage:** 29,968 sq.ft. (from description only, no structured field)
- **Number of Units:** 50 residential units (from description only; **no structured "Number of Units" field** in Application Information). Application Info exposes: Fire Sprinkler Available=No, Detached=No, Expired LP Within Year=No, PV/Solar=No. No unit-count field, no live-work flag, no fee buyout flag.
- **Parcel:** 057 205300500, Block 2053
- **Contacts:** Telesis (architect/contractor); KL2067 University LLC (owner); Jacob Ely, Leo Torres (LP Construction); Mark Bluford (Alameda County Assessor)

**Processing Status (9 stages):**

| Stage | State |
|---|---|
| Application Submittal | complete |
| Resubmittal-Revision | complete |
| Plan Distribution | complete |
| Building and Safety Review | complete |
| PSC Review | complete |
| Consolidated Comments | complete |
| Issuance | complete |
| Inspection | asterisk |
| Certificate of Occupancy | active |

CofO is a **single parent stage with no sub-stages**, in active state. Workflow template: **parent-only / no-CofO-sub-stages**.

### Step 5 — Cross-check

**Hypothesis match? YES** — v2 rule picks B2017-02610, matching the HCD-expected master.

**Unit count — Accela vs. HCD:**

HCD shows BP=50 units → CO=46 units (a 4-unit drop). Accela's evidence:

- **B2017-02610 description: "50 residential units"** — confirms BP'd unit count of 50.
- **No structured "Number of Units" field** is exposed in the public Application Info for this record. The unit count lives only in the project-description text.
- **No revision permit explicitly reduces the unit count.** Scanning all 9 REV/DEF descriptions for B2017-02610:
  - REV01 (10/16/2018): "various changes to the dwelling unit layouts, structural, MEP changes to reflect dwelling layout changes" — **layout changes, not explicit unit-count reduction**. This is the most likely candidate for the descope but the description does not state "from 50 to 46" or similar.
  - REV02: tie-down system change (structural)
  - REV03: stair framing detail
  - REV04: EBM (Exterior Building Management) system
  - REV05: **"Repairs to concrete podium due to fire damage"** (06/08/2021) — fire damage signal
  - REV06: FSD removal, light additions (07 units mentioned — refers to fire-smoke dampers at 7 stacks, NOT 7 dwelling units)
  - REV07 (originally listed 06/15/2017 — backdated): same FSD content as REV06
  - DEF08: "Construction of commercial space restroom #128, to be removed from current permit application and deferred to future tenant improvement permit" — **a deferral/descope** of a ground-floor commercial restroom (not a dwelling unit)
  - REV09: stair 2 railing and door revisions
- **Major fire-damage signal in the permit history:**
  - B2020-04175 (12/01/2020): "Removal of fire damaged improvements. **Upper 5 stories of wood framing above concrete podium to be removed.**" — Finaled.
  - B2017-02610-REV05 (06/08/2021): "Repairs to concrete podium due to fire damage" — Issued.
  - This indicates a **fire during construction** that destroyed the upper 5 stories of wood framing. The building was rebuilt above the concrete podium.
- **B2023-05521 (10/25/2023):** "Convert ground floor retail space into study room and storage area for the building residents (students)." — A **post-CofO conversion of retail/commercial space** to amenity space. Consistent with descoping commercial/study/amenity area but does not directly state unit-count change.

**Best evidence for the 4-unit drop (50→46):**

The most likely descope event is **REV01 (10/16/2018) — "various changes to the dwelling unit layouts, structural, MEP changes to reflect dwelling layout changes."** The wording "changes to the dwelling unit layouts" is consistent with reconfiguring/eliminating a small number of units, although the description does not numerically state the change. No live-work flag, no fee buyout flag, and no other revision references unit-count math.

A secondary possibility: the **fire-damage rebuild (B2020-04175 + REV05)** may have provided an opportunity to re-plan the upper floors at a slightly reduced density during reconstruction. The timing and scope is consistent — upper 5 stories were entirely removed and rebuilt — but no description text explicitly says "rebuilt with 46 units instead of 50."

**No "fee buyout," "live-work conversion," or "AB 2097-style descope" wording appears anywhere in the permit history.** The valuation history is consistent with cost growth (4.4M → 6.8M), not a major descope (which would typically *reduce* valuation).

**CofO workflow state:**
Template: **parent-only / no-CofO-sub-stages** (single "Certificate of Occupancy" stage, currently active). All preceding stages complete; Inspection in asterisk (sub-tasks). The CofO is **not yet complete in Accela's workflow** even though HCD apparently sees a CO=46 count. Consistent with the systemic finding in rule v2 §3a: Berkeley's APR submissions use a CO-date source outside Accela's workflow state tracking.

### Failure mode classification for the lost-units case

The v2 rule **correctly picks the master permit (B2017-02610)** for this address. However, **the rule provides no mechanism to detect or report unit-count drops** — the only place the unit count lives in Accela for this record is the free-text project description, which contains "50 residential units" but never references "46". To derive a CO unit count of 46 from Accela alone, an analyst would need to:
1. Manually read REV01 ("changes to the dwelling unit layouts") and infer it descoped 4 units, OR
2. Cross-reference with HCD/external CO data, OR
3. Search for an associated CofO record/document (not visible in this Building module view).

This is a **"reporting gap" finding**, distinct from the prior batch's pick-failure modes — the v2 rule got the master right, but the data needed to compute the unit drop is not exposed at the master-permit level. **No v2-rule change is indicated** since the rule's job is master-pick, not unit-derivation. The audit-metadata field `unit divergence flag` documented in rule v2 §4 captures this case: when HCD's BP unit count differs from CO unit count, flag for review; use HCD's CO_units as authoritative.

### Bonus civic-data finding

The fire-damage rebuild (December 2020 removal of 5 stories of wood framing + 2021 podium repairs) makes 2067 University a publishable case study: a project with documented mid-construction catastrophe, recovery, and ultimate completion. The valuation history alone tells the story (4.4M initial → 6.8M after rebuild). Worth banking for the TILBlog or methodology writeup. Not blocking.

### Content injection note

The `<div id="claude-agent-stop-container">` injection ("Stop Claude") again present on both the search results and the B2017-02610 CapDetail page. Chrome-Claude's own UI bleeding through; ignored per protocol.
