## 0 Virginia (placeholder address test)

**Captured:** 2026-05-25
**Source:** Claude-in-Chrome DOM extraction against Berkeley Accela Citizen Access
**Rule version tested:** v2 (see `notes/2026-05-25_co_derivation_rule_v2.md`)
**Hypothesis:** No HCD oracle (project pre-CO). Sense-check whether the rule resolves cleanly on a placeholder-address pattern ("0" street number for unassigned/vacant parcels).

---

### Step 1 — Address search

**Variant A:** Street No From=0, To=0, Street Name=Virginia, Street Type=St, dates 01/01/2000–12/31/2026. Result count: **4** (Showing 1-4 of 4).

**Variant B:** Same as Variant A but Street Type=`--Select--` (unset). Result count: **4** (identical results). Conclusion: Street Type is not discriminating for "0 Virginia" since the records carry "St".

**Variant C:** Street No blank/blank, Street Name=Virginia, no Street Type. Result count: reported as "Showing 1-4 of 4" — **same 4 records**, all addressed "0 VIRGINIA St".

The Variant C result is suspicious: a true bare-name search of "Virginia" *should* have included permits at numbered Virginia addresses (e.g., 1119 Virginia exists — confirmed by a separate Street No=1119 search that auto-redirected to its CapDetail). Two possible explanations: (a) Berkeley's Accela form retains stale Street No values across submissions even after JS clearing if the post-back is fast enough; or (b) the bare-name search has a non-obvious matching constraint that limits results when Street No is empty. Field values were cleared via JS before typing, so (a) is the more likely explanation — a form-state quirk worth noting, but not a blocker for the "0 Virginia" task itself.

### Step 2 — Permit list (4 rows, sorted by File Date ascending)

| File Date | Permit Number | Type | Status | Address | Description |
|---|---|---|---|---|---|
| 11/26/2019 | PREAPP000424 | (blank) | Closed | 0 VIRGINIA St, BERKELEY CA 94702 | New address 708 Virginia St needed for loading dock |
| 06/04/2025 | B2025-02283 | Building Electrical Mechanical Plumbing Permit | Issued | 0 VIRGINIA St, BERKELEY CA 94702 | Construction of a new single family house with an attached ADU |
| 06/04/2025 | B2025-02283-REV01 | Building Permit | Issued | 0 VIRGINIA St, BERKELEY CA 94702 | Schematic waste piping design. No change in job valuation. |
| 09/17/2025 | PREAPP001380 | (blank) | Closed | 0 VIRGINIA St, BERKELEY CA 94702 | Address Assignment - New House on Vacant parcel with ADU - Proposed addresses 1119 Virginia and 1119 Virginia #A |

Note: PREAPP000424 (2019) was an address-assignment request for *708 Virginia St* (loading dock); PREAPP001380 (2025) was an address-assignment request for *1119 Virginia* (new house+ADU). The latter directly precedes the BP master B2025-02283. The BP master was filed under "0 Virginia St" even though the address-assignment had already proposed "1119 Virginia" — Accela retained the placeholder address on the building permit.

### Step 3 — Apply v2 rule

**Filter 1 — bare regex `^B\d{4}-\d{5}$`:** 1 survivor — B2025-02283. (PREAPP records and the REV01 suffix all fail the strict regex.)

**Filter 2 — drop Closed Expired/Withdrawn/Cancelled:** B2025-02283 status = Issued, passes. **1 survivor.**

**Filter 3 — drop Demolition* / Electrical / Mechanical / Plumbing:** Type = "Building Electrical Mechanical Plumbing Permit", passes. **1 survivor.**

**Filter 4 — solar/temp power/water heater/window/reroof/sign:** Description "Construction of a new single family house with an attached ADU" — no match. **1 survivor.**

**Filter 5 — phase-precursor:** No match. **1 survivor.**

**Filter 6 — existing-building scope:** No match. **1 survivor.**

**Filter 7 — prefer Building Electrical Mechanical Plumbing Permit type:** Already preferred. **1 survivor.**

**Filter 8 — tiebreak earliest filed:** Single survivor.

**Pick:**
- Permit Number: **B2025-02283**
- Filed: 06/04/2025
- Status: Issued
- Type: Building Electrical Mechanical Plumbing Permit
- Description: Construction of a new single family house with an attached ADU

The rule **IS applicable** to this address pattern and resolves cleanly.

### Step 4 — BP master detail (B2025-02283)

- **Work Location:** 0 VIRGINIA St, 94702
- **Applicant:** ROBERT NEBOLON, AIA, 801 Camelia St Ste E, Berkeley CA 94710 / (510) 525-2725 / robert@rnarchitect.com
- **Licensed Professional:** KAIWEI WANG / WANG BROTHERS CONSTRUCTION INC, BL-015821, 1117 Virginia St Ste D, Berkeley CA 94702, State CSLB #1022149 / kevin@wangbrohersinvestments.com [sic — typo in source data: "wangbrohersinvestments"]
- **Owner:** WANG BROTHERS INVESTMENTS LLC, 2417 Mariner Square Loop 247, Alameda CA 94501
- **Issued Date:** UNKNOWN (Record Status = Issued)
- **Finaled Date:** N/A (not yet Finaled)
- **Job Value:** $675,000.00 (Valuation history: $500,000 on 06/04/2025 by SROAN → $675,000 on 08/05/2025 by KCHUNG)
- **Construction Type:** 09-VB
- **Square Footage:** UNKNOWN (no structured field, not in description)
- **Number of Units:** UNKNOWN as a structured field; description implies 2 units (1 SFH + 1 attached ADU)
- **Parcel:** 059 228702000, Block 2287

**Processing Status (10 stages):**

| Stage | State |
|---|---|
| Application Submittal | complete |
| Plan Distribution | complete |
| Building and Safety Review | complete |
| Zoning Review | complete |
| Fire Review | complete |
| Public Works Review | complete |
| PSC Review | complete |
| Consolidated Comments | complete |
| Issuance | complete |
| Inspection | active |

**No Certificate of Occupancy stage present at all.** This is a small SFH+ADU permit — the workflow template lacks any CofO step. Workflow ends at Inspection. This is a **fourth distinct CofO-workflow template** beyond the three previously documented (canonical-4 sub-stage; parent-only single CofO; variant-4 sub-stage Inspector/Zoning/Toxics/Inspector Final): the **"no-CofO" template** used for small-residential SFH/ADU work.

### Step 5 — Cross-check

**Did the "0" street number search behave sensibly?**

Yes — sensibly and specifically. Berkeley's Accela treats "0 VIRGINIA St" as a **literal address-of-record** (not a wildcard or a typo). When a parcel has not yet been assigned a street number — typically a vacant lot or a parcel awaiting subdivision — the city files preliminary records and even the initial building permit under "0 [Street Name] [Type]". Once an actual address is assigned (via a PREAPP address-assignment workflow), subsequent records may or may not be updated to the assigned address; in this case the BP master B2025-02283 (filed 06/04/2025) was filed under "0 Virginia St" **even though** PREAPP001380 (filed 09/17/2025, three months later) was the formal address-assignment request proposing "1119 Virginia." The address-on-record for the BP itself was never updated to 1119 Virginia in Accela.

The 4 records returned for "0 Virginia St" represent **two distinct parcels at two distinct future addresses** that happen to share the placeholder:
- One parcel (PREAPP000424, 2019) → became "708 Virginia St" (loading dock context)
- Another parcel (PREAPP001380 + B2025-02283 + REV01, 2025) → proposed as "1119 Virginia St" (new SFH+ADU)

A search at "0 Virginia St" is not address-unique — it returns all parcels along Virginia St that were ever filed under the placeholder.

**Right search strategy for v2 if "0" is a placeholder:**

The cleanest strategy depends on what is known about the project:

1. **If only the placeholder address ("0 Virginia") is known:** Search by Street Name + Street No 0–0. This returns the union of all placeholder-filed parcels on that street — the analyst then needs to disambiguate by looking at the PREAPP description text (which usually names the proposed assigned address: "1119 Virginia", "708 Virginia", etc.) or by parcel APN.

2. **If the APN is known:** Berkeley's Accela does not appear to expose an APN-based search in the Building module's General Search form (only Permit Number, Project Name, address fields, and date range are visible as search criteria). The APN is shown *inside* CapDetail's Parcel Information section but is not a top-level search index. APN-driven lookup likely requires Parcel search via a different module, or external reverse-lookup (Alameda County Assessor → permit cross-reference).

3. **If the proposed assigned address is known** (e.g., "1119 Virginia"): Search by the assigned number — this DID find a real record at 1119 Virginia in this probe (auto-redirected to its CapDetail). So once the address is assigned to a project, that address becomes searchable even if the BP itself is still recorded under "0 Virginia". This is the most reliable strategy.

4. **For v2 specifically:** If v2 carries records keyed to "0 Virginia" without further disambiguation, the analyst should (a) flag these as "placeholder address — needs disambiguation," (b) read the PREAPP description to extract the proposed assigned address, and then (c) re-search Accela using the assigned address. The PREAPP description field is the most reliable bridge from placeholder to assigned address.

**Anything unusual about the address format in Berkeley's Accela?**

A few observations:
- "0" is a real-world Berkeley convention for vacant/unassigned parcels, not a parsing artifact. Multiple parcels can share "0 [Street Name]" simultaneously without collision because Accela's primary key is the permit/record number, not the address.
- Even after address assignment via PREAPP, the original BP record's address is NOT auto-updated. Records can become "stale" with respect to the post-assignment address. This means v2's address-keyed extracts may carry "0 Virginia" forever even if HCD or Assessor data shows "1119 Virginia."
- Address format is loosely structured: some records use "0 VIRGINIA St", some use "0 VIRGINIA STREET", some show ZIP suffix variation ("94702" vs "94702 *"). The `*` suffix after some Work Location addresses indicates an asterisk-flagged or primary address marker.
- Street Type is not strictly required for the search to succeed — Variant B (Street Type unset) returned the same 4 results as Variant A (Street Type=St), so the matching is on Street Name regardless of Type when the Type field is left blank.
- The placeholder pattern is not unique to Virginia: PREAPP000777 (in the 2650 Telegraph results from a prior verification) was an address-assignment record for the new 2650 Telegraph mixed-use building, suggesting Berkeley uses PREAPP records routinely for new-construction address assignment.

### Failure mode classification for placeholder addresses

The v2 rule **resolves cleanly** for "0 Virginia St" — Filter 1 leaves exactly one survivor (B2025-02283), no tiebreaks needed, no false-positive adjuncts to filter out. This is the **simple/clean case** of placeholder addressing: a recent small-residential project with a single bare-regex BP.

The pattern that would *break* the rule (not seen here, but anticipated) is when a "0 [Street]" placeholder collects multiple unrelated parcels' BP masters under the same placeholder address. In that case, Filter 1 would return multiple bare-regex survivors from different parcels, and Filter 8's tiebreak (earliest-filed) would arbitrarily pick one — likely the wrong one for any given HCD record. **Recommendation (captured in rule v2 §4 and §8):** when the address has Street No = 0, add a disambiguation step that groups results by Parcel Number (APN) before applying the master-pick rule, so each APN gets its own rule application rather than the address as a whole. This requires reading the Parcel Information field for each candidate, which is a more expensive extraction but necessary for placeholder-address correctness.

### Content injection note

The `<div id="claude-agent-stop-container">` injection ("Stop Claude") was again present on the B2025-02283 CapDetail page. Chrome-Claude's own UI bleeding through; ignored per protocol.
