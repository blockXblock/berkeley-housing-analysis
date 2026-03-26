# Permitting System Transparency Requirements

## A Policy Brief for Berkeley City Council and California State Legislature

**Prepared by:** Berkeley Data Journalism & Civic Challenge
**Date:** March 2026
**Contact:** [berkeley-housing-analysis project]

---

## Executive Summary

California faces a severe housing crisis, yet basic data about housing permit pipelines remains inaccessible or incomplete in most jurisdictions. Our independent audit of Berkeley's housing pipeline—conducted over four months using publicly available permit data—revealed significant gaps in data accessibility, consistency, and completeness that impede effective policy oversight and public accountability.

This brief presents evidence-based recommendations at three levels:
1. **Specific requirements for Berkeley's new Clariti permitting system**
2. **Model state legislation for permitting transparency**
3. **Documented findings from our independent audit**

Our work builds on the Possibility Lab's research partnership with the California Department of Housing and Community Development (HCD) and Professor Moira O'Neill's findings on permit processing barriers in San Francisco, which identified similar data accessibility challenges across California jurisdictions.

---

## Part I: Berkeley Requirements for Clariti Implementation

Berkeley is transitioning from Accela to the Clariti permitting system. This transition presents a critical opportunity to implement transparency features that the current system lacks. Based on our direct experience building an independent housing database from Accela data, we recommend Berkeley require the following capabilities in any permitting system contract:

### 1. Automatic Cross-Referencing Between Permit Types

**Current Problem:** Planning permits (ZP, PLN) and building permits (B) for the same project are stored in separate modules with no systematic linkage. Our audit found that tracking a single project from application through Certificate of Occupancy requires manually searching both the Planning and Building tabs and inferring connections based on address matching.

**Requirement:** The Clariti system must automatically link all permits associated with the same project or address, including:
- Planning applications (Use Permits, Zoning Permits)
- Environmental review records (CEQA determinations)
- Building permits (foundation, structural, full design)
- Mechanical, electrical, and plumbing permits
- Demolition permits
- Certificates of Occupancy

**Implementation:** Each project should have a unique Project ID that persists across all permit types and is visible in public-facing interfaces.

### 2. Structured Data Fields for Affordable Housing

**Current Problem:** Affordable unit counts, income levels, and deed restriction terms are buried in free-text description fields or PDF attachments. Our audit required custom text parsing to extract phrases like "5 VLI units" or "15% of base density at Very Low Income" from project descriptions.

**Requirement:** The system must include structured, queryable fields for:
- Total proposed units
- Units by income level (Extremely Low, Very Low, Low, Moderate, Above Moderate)
- Deed restriction type and duration
- Density bonus percentage requested
- Density bonus concessions/waivers granted
- SB 35, SB 330, AB 2011 streamlining flags

**Implementation:** These fields should be mandatory for all residential projects and validated at application intake.

### 3. Single Project Lifecycle View

**Current Problem:** There is no unified view showing a project's complete history. Status information is fragmented across multiple screens, requiring manual assembly of timelines.

**Requirement:** Provide a single dashboard view for each project showing:
- All associated permits with current status
- Complete processing status history with timestamps
- All inspection records and results
- Fee schedule with payment status
- Key milestone dates (filed, deemed complete, entitled, building permit issued, CO)
- Document list with direct links

**Implementation:** This view should be accessible both to staff and to the public via the citizen portal.

### 4. Public API Access

**Current Problem:** The current Accela system provides no public API. Data extraction requires manual copying from web interfaces, which is blocked by Cloudflare rate limiting for systematic collection.

**Requirement:** Provide a RESTful API with:
- Read access to all public permit records
- Query capabilities by address, permit number, date range, status, and project type
- Access to complete status history for each permit
- Document metadata (though document content may require separate access)
- Rate limits sufficient for research and journalism use (minimum 1,000 requests/hour)
- API documentation and developer resources

**Implementation:** API access should be available without registration for basic queries; authenticated access may be required for higher rate limits.

### 5. Real-Time Data Export

**Current Problem:** Bulk data export is not available. Our audit required processing 153 individual permit records manually.

**Requirement:** Provide automated data export in:
- CSV format for spreadsheet analysis
- JSON format for programmatic access
- GeoJSON format for mapping applications
- Updates available at minimum daily frequency

**Implementation:** Export should include all public fields, not a limited subset.

### 6. Automated APR Table Generation

**Current Problem:** Annual Progress Report (APR) preparation requires manual compilation from permit records. Our audit identified potential discrepancies between city-reported data and permit system records.

**Requirement:** The system should automatically generate:
- HCD Table A (applications) from planning permit data
- HCD Table A2 (building activity) from building permit data
- HCD Table B (entitled projects) from approval records
- Field mappings that align with HCD APR specifications

**Implementation:** Automated reports should be reviewable by staff before submission, with audit trails showing data sources.

### 7. Project Status Dashboard

**Current Problem:** No public dashboard exists showing the housing pipeline from application through occupancy.

**Requirement:** Publish a real-time dashboard showing:
- All active housing projects by status stage
- Processing time metrics by stage and project type
- Permit volume trends over time
- Geographic distribution of applications
- Affordable housing pipeline tracking

**Implementation:** Dashboard should update automatically and be embeddable on city websites.

---

## Part II: Model State Legislation for Permitting Transparency

California should establish statewide requirements ensuring all jurisdictions provide consistent, accessible permit data. The following provisions should apply to all cities and counties:

### Section 1: Public API Requirements

**(a)** Every jurisdiction operating an electronic permitting system shall provide public application programming interface (API) access to permit records within 24 months of this act's effective date.

**(b)** The API shall provide, at minimum:
1. Query access to all permit records that are public under the California Public Records Act
2. Complete permit status history including all status changes with timestamps
3. Query capabilities by address, assessor's parcel number, permit number, date range, and permit type
4. Response formats including JSON and XML

**(c)** Rate limits shall permit at minimum 500 API requests per hour for unauthenticated access and 5,000 requests per hour for authenticated research access.

### Section 2: Open Data Portal Publication

**(a)** Every jurisdiction shall publish building permit data on a municipal open data portal or the state's open data portal.

**(b)** Data shall be updated at minimum weekly and shall include:
1. All building permits issued, with permit number, address, permit type, valuation, and issue date
2. All certificates of occupancy issued, with permit number, address, and issue date
3. Permit status including active, expired, finaled, and withdrawn

**(c)** Historical data shall be maintained for at minimum 10 years.

### Section 3: Project-Level Linkages

**(a)** Permitting systems shall maintain linkages between all permits associated with the same development project.

**(b)** Project linkages shall connect:
1. Planning entitlement records
2. Environmental review records
3. Building permits of all types
4. Certificates of occupancy

**(c)** A unique project identifier shall be assigned at initial application and maintained through project completion.

### Section 4: Structured Affordable Housing Data

**(a)** All jurisdictions shall record affordable housing information in structured database fields, not solely in document attachments.

**(b)** Required fields shall include:
1. Total units by bedroom count
2. Affordable units by income category as defined by HCD
3. Affordability term in years
4. Deed restriction recording information when available
5. Density bonus provisions utilized

**(c)** These fields shall be mandatory for all residential projects of five or more units.

### Section 5: Machine-Readable APR Source Data

**(a)** Alongside PDF Annual Progress Report submissions to HCD, jurisdictions shall publish the source data in machine-readable format.

**(b)** Source data shall include:
1. Individual permit records underlying Table A, A2, and B summaries
2. Address, APN, permit number, unit counts, and income level data for each record
3. Data dictionary explaining all fields

**(c)** HCD shall establish a standard data schema for APR source data publication.

### Section 6: Processing Time Transparency

**(a)** Permitting systems shall automatically calculate and publish processing time metrics including:
1. Days from application to deemed complete
2. Days from deemed complete to approval or denial
3. Days from approval to building permit issuance
4. Days from building permit to certificate of occupancy

**(b)** Metrics shall be published quarterly, disaggregated by:
1. Project size (units)
2. Permit type
3. Whether streamlining provisions (SB 35, SB 330) were utilized

### Section 7: Project Completion Linkage

**(a)** Certificate of Occupancy records shall include reference to the original planning entitlement permit number.

**(b)** Jurisdictions shall maintain a public registry linking completed projects to their original applications, enabling tracking of project timelines from application through occupancy.

---

## Part III: Evidence from Berkeley Housing Pipeline Audit

Our independent audit of Berkeley's housing permit pipeline, conducted from December 2025 through March 2026, documented the following findings:

### Finding 1: High APR Match Rate Achievable with Independent Data Collection

We achieved a **97.4% match rate** between our independently collected permit data and the city's official 2024 APR submission to HCD. This demonstrates that accurate housing data can be assembled from public permit records—but required:
- 153 individual permit lookups
- Manual address normalization across inconsistent formats
- Custom parsing of 7 different data output formats
- Cross-referencing between Planning and Building modules

**Implication:** The data exists but is not accessible in a form that enables routine oversight.

### Finding 2: Potential APR Omissions

Our audit identified **3 large projects totaling 885 units** that may be missing from the city's official 2024 APR:

| Project | Units | Status | Potential Issue |
|---------|-------|--------|-----------------|
| 1750 Sacramento St | 739 | Under Review | Filed Dec 2024, not in APR |
| 2276 Shattuck Ave | 336 | In Review | Deemed complete Aug 2025, not in APR |
| Project C | [Additional verification needed] | | |

**Implication:** Without systematic data publication, neither the public nor oversight bodies can verify APR accuracy.

### Finding 3: Processing Time Data Not Publicly Available

We calculated **median processing time of 428 days** from application to entitlement for projects in our database. This metric is not published anywhere by the city.

Processing time distribution:
- Fastest 25%: Under 180 days
- Median: 428 days
- Slowest 25%: Over 600 days
- Maximum observed: 1,035 days (nearly 3 years)

**Implication:** Without published metrics, there is no accountability for processing delays and no way to assess the impact of streamlining legislation.

### Finding 4: Building Permit Data Requires Separate Manual Collection

Our initial data collection from the Planning module yielded **0% coverage of building permit dates**. Obtaining building permit information required:
- Separate searches in the Building tab for each address
- Manual correlation of building permits to planning applications
- Address matching across inconsistent formats (e.g., "2099 MLK Jr Way" vs. "2099 M L KING JR WAY")

**Implication:** Tracking projects from entitlement through construction is effectively impossible without manual research for each project.

### Finding 5: Inconsistent Data Formats Require Custom Parsing

We developed **7 different parser functions** to handle variations in how Accela outputs processing status data:
1. Original Accela collapsible format
2. Markdown table with stage headers
3. Markdown table with stage columns
4. Bullet/arrow format
5. Pipe-delimited format
6. Entry-based format
7. Building permit list format

**Implication:** Even manual data collection is unreliable without technical expertise to handle format variations.

### Finding 6: Systematic Data Collection Blocked

Our automated data collection attempts were blocked by **Cloudflare security** after approximately 50 requests. This forced us to conduct all collection manually over several weeks.

**Implication:** The public cannot efficiently access public records at scale, even for legitimate research and journalism purposes.

### Finding 7: Fee Data Not Aggregated or Published

We documented **$45,861 in planning fees** for a single 599-unit project (1974 Shattuck Ave). This information was only available by manually opening the fee detail screen for that permit. No aggregate fee data is published.

**Implication:** The public cannot assess whether fee structures are appropriate or how fees vary by project type.

### Finding 8: Stalled Projects Not Tracked

We identified **19 potentially stalled projects representing 1,464 units** with no recorded activity in over 12 months. The city does not publish any tracking of stalled applications.

| Status | Projects | Units |
|--------|----------|-------|
| Incomplete Pending Applicant >12 months | 11 | 892 |
| Corrections Pending >12 months | 5 | 398 |
| In Review with no activity >18 months | 3 | 174 |

**Implication:** Entitled projects that never proceed to construction represent a hidden gap in housing production that current reporting does not capture.

---

## Statewide Context

### Possibility Lab Research Partnership

The Possibility Lab at UC Berkeley has partnered with HCD to improve housing data systems statewide. Their research has documented similar data accessibility challenges across California jurisdictions, finding that:
- Most jurisdictions cannot easily generate APR data from permit systems
- Affordable housing tracking relies heavily on manual processes
- No standardized data schema exists across jurisdictions

Our findings in Berkeley are consistent with their statewide observations and underscore the need for legislative standards.

### San Francisco Findings (Professor Moira O'Neill)

Professor Moira O'Neill's research on San Francisco's permitting process identified that:
- Permit processing data was not systematically published
- Tracking projects across permit types required manual assembly
- Processing time variations were not transparent to applicants or the public

Berkeley exhibits the same structural barriers, suggesting these are systemic issues requiring statewide solutions rather than jurisdiction-by-jurisdiction advocacy.

---

## Recommendations Summary

### For Berkeley City Council

1. **Require all features listed in Part I** in the Clariti system contract
2. **Establish a public housing pipeline dashboard** within 6 months of Clariti deployment
3. **Publish processing time metrics quarterly** beginning immediately, using existing Accela data
4. **Mandate API access** in the Clariti contract with minimum rate limits specified

### For California State Legislature

1. **Introduce legislation** establishing the transparency requirements in Part II
2. **Direct HCD** to develop standard data schemas for APR source data
3. **Appropriate funding** for jurisdictions to upgrade permitting systems to meet transparency requirements
4. **Establish enforcement mechanisms** including potential withholding of housing element certification for non-compliant jurisdictions

### For HCD

1. **Require machine-readable APR source data** alongside PDF submissions beginning with the 2025 reporting cycle
2. **Publish a model permitting system RFP** that jurisdictions can use when procuring new systems
3. **Create a statewide permit data portal** aggregating data from compliant jurisdictions

---

## Planned Expansions: What Transparent Data Enables

With transparent permitting data as the foundation, this project will extend to analyses that are currently impossible due to data fragmentation. These expansions demonstrate the broader public value of the transparency requirements we propose:

### 1. Modular and Off-Site Construction Tracking

**Analysis Goal:** Measure whether modular, prefabricated, or off-site construction methods reduce construction timelines compared to conventional building.

**Data Requirements:**
- Construction method field in building permits (currently not captured)
- Building permit issuance to Certificate of Occupancy timeline
- Inspection milestone dates throughout construction

**Policy Value:** If modular construction demonstrably accelerates housing delivery, jurisdictions could incentivize these methods through expedited permitting or fee reductions. Without construction timeline data, we cannot evaluate these policy options.

### 2. Full Cost Accounting for Housing Development

**Analysis Goal:** Calculate the true public and private costs of housing development, from initial application through occupancy.

**Data Requirements:**
- All permit fees by type and project (currently available only per-permit, not aggregated)
- City staff hours allocated to permit review (not currently tracked publicly)
- Developer costs for application preparation, revisions, and carrying costs during delays
- Infrastructure fee assessments and payment timing

**Policy Value:** Understanding full development costs enables evidence-based fee reform and identifies where process improvements would have the greatest impact. Our finding of $45,861 in planning fees for a single project represents only a fraction of total development costs that remain unquantified.

### 3. Infrastructure Capacity Analysis

**Analysis Goal:** Assess cumulative infrastructure demands from pipeline projects and identify capacity constraints before they cause delays.

**Data Requirements:**
- Project-level utility connection data (water, sewer, electrical capacity)
- Traffic study results linked to permit records
- School enrollment projections from residential projects
- Stormwater and drainage requirements

**Policy Value:** Proactive infrastructure planning prevents bottlenecks that delay housing production. Currently, infrastructure constraints emerge as surprises during permit review rather than being anticipated and addressed systematically.

### 4. Neighborhood Economic Impact Assessment

**Analysis Goal:** Measure how new housing development affects neighborhood economic indicators including local business activity, property values, and displacement risk.

**Data Requirements:**
- Geocoded permit data (achieved: 95.6% in our database)
- Business license data by location
- Property assessment data over time
- Rental housing inventory and rent-controlled unit tracking

**Policy Value:** Evidence-based assessment of development impacts can inform community benefit requirements, anti-displacement policies, and infrastructure investment priorities. Anecdotal concerns about development impacts could be replaced with measured outcomes.

### 5. Construction Workforce Analysis

**Analysis Goal:** Track local hiring, apprenticeship utilization, and workforce development outcomes in housing construction.

**Data Requirements:**
- Contractor license data linked to building permits
- Local hire and apprenticeship reporting (where required)
- Prevailing wage compliance records

**Policy Value:** Many jurisdictions require local hiring or apprenticeship utilization but have no systematic way to measure compliance or outcomes. Linked permit data would enable workforce development accountability.

---

**These analyses are only possible when the underlying permit and construction data is openly accessible.** The transparency requirements in this brief are not merely about public accountability—they are prerequisites for evidence-based housing policy. Every day that data remains locked in inaccessible systems is a day we cannot answer fundamental questions about what works in housing production.

---

## Appendix: Data and Methodology

All findings in this brief are derived from our Berkeley Housing Pipeline Analysis project, which:
- Collected permit data for 137 housing projects representing 8,175 units
- Achieved 95.6% geocoding coverage through address matching
- Documented processing status histories for 58 projects with filed dates
- Identified 30 entitled projects and 4 completed projects with COs in 2024

Our data, methodology, and code are available for review at:
- Interactive explorer: [berkeley-housing.fly.dev]
- GitHub repository: [github.com/blockXblock/berkeley-housing-analysis]

---

*This policy brief was prepared as part of the Berkeley Data Journalism & Civic Challenge. We welcome feedback and collaboration from policymakers, researchers, and housing advocates working to improve permitting transparency in California.*
