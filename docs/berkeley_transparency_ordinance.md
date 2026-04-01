# CITY OF BERKELEY
## DRAFT MUNICIPAL ORDINANCE

# BERKELEY OPEN DATA AND TRANSPARENCY ORDINANCE

**Ordinance No. ____-N.S.**

**Adding Chapter 2.150 to the Berkeley Municipal Code**

---

## FINDINGS AND PURPOSE

### SECTION 1. FINDINGS

The City Council of the City of Berkeley hereby finds and declares that:

**A. Public Access to Government Data is Essential to Democracy.** Residents, researchers, journalists, and civic organizations require timely access to accurate, machine-readable government data to participate meaningfully in democratic governance, hold public officials accountable, and collaborate with the City to address community challenges.

**B. Current Data Practices are Inadequate.** Independent audits of City data practices have revealed significant gaps:

1. **Housing Permit Data Quality.** An independent audit of Berkeley's housing pipeline data conducted in 2025-2026, cross-referencing City permit records against state Annual Progress Report (APR) filings, found a 97.4% match rate for reported projects but identified approximately 885 housing units potentially missing from the City's 2024 APR submission to the California Department of Housing and Community Development (HCD). This discrepancy represents a significant reporting gap that affects state housing compliance assessments and regional planning.

2. **Affordable Housing Accountability Gap.** The same audit found that in-lieu fee payments to the Affordable Housing Trust Fund are not recorded in the City's Accela permitting system. Without structured data on in-lieu contributions, residents cannot track whether developers are meeting affordable housing obligations or whether Trust Fund dollars are being deployed effectively. At least $11 million in identified in-lieu fee commitments from a single project (2128 Oxford Street) lack transparent tracking in public records.

3. **State-Level Data Quality Concerns.** Research by the Possibility Lab at UC Berkeley has documented systematic data quality issues in APR submissions statewide, including inconsistent status classifications, missing application dates, and incomplete affordability designations. Berkeley's data practices contribute to these broader accountability challenges.

4. **Technical Barriers to Public Access.** Legitimate data collection efforts by civic technologists and researchers have been blocked by web application firewall (WAF) configurations that cannot distinguish between malicious bots and good-faith civic data projects. These technical barriers violate the spirit of public records laws and impede civic engagement.

5. **Building Permit Archival.** Building permits for completed projects appear to be archived and removed from public search in the City's Accela permitting system. Projects confirmed as physically completed (2000 University, 2711 Shattuck) return no building permit results in the public portal. This means the public cannot verify construction completion, certificate of occupancy dates, or final fee payments for completed housing developments.

**C. Best Practices Exist.** Other California jurisdictions have successfully implemented open data programs:

1. The City and County of San Francisco's Administrative Code Chapter 22D, enacted in 2010 and amended in 2018, established a comprehensive open data program with clear timelines, accountability mechanisms, and technical standards.

2. The City of Oakland's Open Data Policy (Administrative Instruction 1401), adopted in 2013, requires publication of high-value datasets and annual compliance reporting.

3. California Government Code Section 6253.10, enacted through AB 169 (2019), requires state agencies to provide data in machine-readable formats upon request.

**D. Technology Standards Have Matured.** Modern API design patterns, cloud infrastructure, and data interchange formats make it feasible for municipalities of Berkeley's size to implement robust open data programs at reasonable cost.

### SECTION 2. PURPOSE

The purpose of this Chapter is to:

A. Ensure all City data of public interest is accessible to residents, researchers, journalists, and civic organizations in machine-readable formats without unreasonable barriers;

B. Establish clear technical standards for data publication, API access, and bulk download capability;

C. Require housing and permitting data to be published with sufficient granularity to enable independent verification of City reports to state and federal agencies;

D. Create accountability mechanisms including a Chief Data Officer position, annual compliance reporting, and public request processes;

E. Foster community engagement through partnerships with educational institutions and regular public forums; and

F. Position Berkeley as a leader in municipal transparency and data-driven governance.

---

## CHAPTER 2.150 - OPEN DATA

### ARTICLE I. DEFINITIONS AND SCOPE

#### 2.150.010 Definitions

For purposes of this Chapter, the following terms have the meanings set forth below:

**A. "API" (Application Programming Interface)** means a documented set of protocols, routines, and tools that allows software applications to communicate with City data systems and retrieve data programmatically without human intervention.

**B. "API Endpoint"** means a specific URL through which an API can be accessed to retrieve a particular dataset or perform a specific query.

**C. "Bulk Download"** means the ability to download an entire dataset or a substantial portion thereof in a single operation, without pagination limits that would require multiple requests to obtain complete data.

**D. "Chief Data Officer" or "CDO"** means the City official designated pursuant to Section 2.150.100 to oversee implementation of this Chapter.

**E. "City Department"** means any department, office, agency, board, commission, or other organizational unit of the City of Berkeley, including the offices of elected officials.

**F. "Dataset"** means a collection of related data records organized in a structured format that can be processed by computer systems.

**G. "Machine-Readable Format"** means a structured data format that can be automatically read and processed by a computer system without human interpretation. Machine-readable formats include, but are not limited to:
   1. Comma-Separated Values (CSV);
   2. JavaScript Object Notation (JSON);
   3. Geographic JavaScript Object Notation (GeoJSON) for spatial data;
   4. Extensible Markup Language (XML); and
   5. Parquet or similar columnar storage formats.

   Portable Document Format (PDF), scanned images, and unstructured HTML are not machine-readable formats for purposes of this Chapter.

**H. "Open Data"** means data that is:
   1. Available to any member of the public;
   2. Accessible without registration, login, or identification requirements for read-only access;
   3. Published in at least one machine-readable format;
   4. Available for bulk download;
   5. Not subject to licensing restrictions that limit redistribution, derivative works, or commercial use; and
   6. Published with clear metadata describing the data structure, update frequency, and point of contact.

**I. "Open Data Portal"** means the centralized web-based platform through which the City publishes open data, provides API access, and maintains a catalog of available datasets.

**J. "Personally Identifiable Information" or "PII"** means information that can be used to distinguish or trace an individual's identity, either alone or when combined with other information that is linked or linkable to a specific individual. PII includes, but is not limited to:
   1. Full name in combination with Social Security number, driver's license number, or financial account numbers;
   2. Home address of residential property owners when not already public record;
   3. Personal email addresses and phone numbers not associated with business operations;
   4. Biometric data; and
   5. Information about minors that would be protected under the California Consumer Privacy Act or the Family Educational Rights and Privacy Act.

   PII does not include:
   1. Names and contact information of property owners as recorded in public real property records;
   2. Names and business contact information of permit applicants, contractors, and design professionals;
   3. Business addresses and business contact information; or
   4. Information that the individual has voluntarily made public.

**K. "Permit"** means any approval, license, entitlement, certificate, or other authorization issued by the City that allows a specific activity, construction, business operation, or land use.

**L. "Project-Level Linkage"** means the technical capability to associate all permits, applications, inspections, and other records related to a single development project through a common identifier, regardless of which City department issued the individual records.

**M. "Structured Data Field"** means a discrete data element within a database that stores a specific type of information in a consistent format, allowing for filtering, sorting, and aggregation.

#### 2.150.020 Scope

A. This Chapter applies to all City Departments and to all data systems maintained by or on behalf of the City.

B. This Chapter applies to data systems operated by third-party vendors under contract with the City to the extent specified in Section 2.150.070.

C. This Chapter does not require disclosure of:
   1. Records exempt from disclosure under the California Public Records Act (Government Code Section 6250 et seq.);
   2. PII as defined in Section 2.150.010(J);
   3. Records related to active criminal investigations where disclosure would compromise the investigation;
   4. Information protected by attorney-client privilege or attorney work product doctrine;
   5. Trade secrets and proprietary business information as defined in Evidence Code Section 1061; or
   6. Data specifically prohibited from disclosure by state or federal law.

D. Where a dataset contains both disclosable and exempt information, the City shall publish the dataset with exempt fields redacted or aggregated to prevent identification, unless such redaction is technically infeasible, in which case the City shall document the reason in the dataset catalog.

---

### ARTICLE II. OPEN DATA REQUIREMENTS

#### 2.150.030 Open Data Portal

A. **Establishment.** Within twelve (12) months of the effective date of this ordinance, the City shall establish and maintain a centralized Open Data Portal accessible to the public via the Internet.

B. **Portal Requirements.** The Open Data Portal shall:
   1. Provide a searchable catalog of all published datasets;
   2. Display metadata for each dataset including description, source department, update frequency, date of last update, data dictionary, and point of contact;
   3. Allow bulk download of datasets in CSV format at minimum, with JSON and GeoJSON formats for datasets containing structured or spatial data;
   4. Provide API access with documented endpoints;
   5. Be accessible without registration, login, or identification for read-only access;
   6. Comply with Web Content Accessibility Guidelines (WCAG) 2.1 Level AA standards;
   7. Function properly on mobile devices and common web browsers; and
   8. Maintain an archive of historical dataset versions for at least three (3) years.

C. **No Barriers to Access.** The Open Data Portal and associated APIs shall not:
   1. Require registration, login, or identification for read-only access to public data;
   2. Impose CAPTCHA or similar human-verification challenges on API requests;
   3. Block access based on user-agent strings commonly associated with programming languages or data collection tools;
   4. Impose rate limits below the minimums specified in Section 2.150.050(B)(3); or
   5. Use web application firewalls (WAF), content delivery networks (CDN), or other security tools in a manner that blocks legitimate bulk data access.

D. **Legitimate Access Criteria.** For purposes of subsection (C)(5), "legitimate bulk data access" means automated requests that:
   1. Access only publicly available data;
   2. Do not attempt to circumvent access controls or extract non-public information;
   3. Do not degrade system performance to the point of affecting other users;
   4. Comply with published rate limits; and
   5. Include a valid user-agent string identifying the requesting application.

#### 2.150.040 Required Datasets

A. **General Requirements.** All City Departments shall publish datasets of public interest through the Open Data Portal. The Chief Data Officer shall maintain a master inventory of all City datasets and a prioritized publication schedule.

B. **Mandatory Datasets.** The following datasets shall be published within the timelines specified in Article VI:

   1. **Permitting Data:**
      - Building permit applications, approvals, and status histories
      - Planning permit applications (use permits, variances, design review), approvals, and status histories
      - Demolition permits
      - Mechanical, electrical, and plumbing permits
      - Public works permits (encroachment, excavation, utility connections)
      - Code enforcement cases and resolutions
      - Business license applications and approvals
      - Rental housing registration and inspection records

   2. **Housing-Specific Data:**
      - Housing development permit applications with unit counts and project type
      - Entitlement dates and conditions of approval
      - Building permit issuance and certificate of occupancy dates
      - Affordable housing unit counts by income level (Extremely Low, Very Low, Low, Moderate, Above Moderate)
      - Deed restriction status and expiration dates for affordable units
      - Density bonus applications and concessions granted
      - SB 35, SB 330, AB 2011, and other streamlining law applicability
      - In-lieu fee payments with project address, amount, date, and receiving fund
      - Affordable Housing Trust Fund receipts by source
      - Affordable Housing Trust Fund expenditures by project and amount

   3. **Financial Data:**
      - Fee schedules for all City services
      - Budget allocations by department and program
      - Trust fund and special fund balances
      - Grant receipts and expenditures
      - Contract awards and vendor payments
      - Revenue by source

   4. **Other High-Value Data:**
      - City Council agendas, minutes, and voting records
      - Board and commission agendas and minutes
      - City employee positions and salary ranges
      - Property ownership records to the extent permitted by state law
      - GIS parcel data and zoning designations
      - Infrastructure project status and timelines

C. **Update Frequency.** Datasets shall be updated according to the following schedule unless a different schedule is approved by the Chief Data Officer based on technical constraints:
   1. **Daily:** Permit applications, permit status changes, code enforcement cases
   2. **Weekly:** Financial transactions, contract awards, fee collections
   3. **Monthly:** Aggregate reports, trust fund balances, staffing data
   4. **Annually:** Fee schedules (or upon amendment), organizational charts, policy documents

D. **Data Quality Standards.** All published datasets shall:
   1. Use consistent field names, data types, and coding conventions;
   2. Include unique identifiers that remain stable over time;
   3. Provide project-level linkages as defined in Section 2.150.010(L) for all permit data;
   4. Include timestamps for record creation and last modification;
   5. Document null values and their meaning; and
   6. Be validated against data quality rules before publication.

#### 2.150.050 API Requirements

A. **API Publication.** For each dataset published on the Open Data Portal, the City shall provide API access that allows programmatic queries and data retrieval.

B. **API Standards.** APIs shall:
   1. Follow RESTful design principles or GraphQL standards;
   2. Support filtering, sorting, and pagination;
   3. Allow a minimum of 10,000 requests per day per IP address without registration;
   4. Return data in JSON format at minimum, with CSV and GeoJSON options for applicable datasets;
   5. Use HTTPS with valid TLS certificates;
   6. Return appropriate HTTP status codes and error messages;
   7. Support conditional requests using ETags or Last-Modified headers; and
   8. Provide bulk download endpoints that bypass pagination for complete dataset retrieval.

C. **Documentation.** The City shall publish comprehensive API documentation including:
   1. Complete endpoint reference with parameters and response schemas;
   2. Authentication requirements (if any) and rate limit policies;
   3. Example queries in multiple programming languages (Python, JavaScript, R at minimum);
   4. Use case tutorials demonstrating common data retrieval scenarios;
   5. Changelog documenting API version history and breaking changes; and
   6. Contact information for technical support.

D. **Versioning and Stability.** The City shall:
   1. Maintain backward compatibility for at least twelve (12) months after any breaking change;
   2. Provide at least ninety (90) days advance notice before deprecating API versions; and
   3. Maintain a stable URL structure that does not change without notice.

---

### ARTICLE III. PERMITTING SYSTEM REQUIREMENTS

#### 2.150.060 Permitting Software Standards

A. **Public API Access.** Any permitting software system used by the City, including but not limited to Accela, Clariti, Tyler Technologies, or successor systems, shall provide public API access to:
   1. Permit applications with application date, type, and status;
   2. Complete status history with timestamps and assigned staff;
   3. Document metadata (document type, upload date, page count) for public documents;
   4. Inspection scheduling and results;
   5. Conditions of approval;
   6. Fee assessments and payments; and
   7. Project comments and correspondence (excluding those exempt from disclosure).

B. **Project-Level Linkage.** Permitting systems shall:
   1. Assign a unique project identifier to each development project;
   2. Link all permits (planning, building, demolition, mechanical, electrical, plumbing) to the project identifier;
   3. Allow public query of all permits associated with a project identifier;
   4. Maintain linkage across system migrations and upgrades; and
   5. Provide a crosswalk table mapping historical permit numbers to current project identifiers.

C. **Affordable Housing Data Fields.** For housing development projects, permitting systems shall maintain the following as structured data fields (not only in document attachments or free-text notes):
   1. Total proposed unit count;
   2. Unit count by bedroom count (studio, 1BR, 2BR, 3BR, 4BR+);
   3. Unit count by income level (Extremely Low Income, Very Low Income, Low Income, Moderate Income, Above Moderate Income);
   4. Affordability covenant or deed restriction recording status;
   5. Deed restriction expiration date;
   6. Density bonus percentage and concessions/waivers granted;
   7. In-lieu fee amount, payment date, and receiving fund;
   8. Replacement unit requirements under SB 330 and compliance status; and
   9. Applicable streamlining provisions (SB 35, SB 330, AB 2011, etc.).

D. **Processing Time Metrics.** Permitting systems shall automatically calculate and publish:
   1. Median processing days from application to completeness determination, by project type;
   2. Median processing days from completeness to entitlement, by project type;
   3. Median processing days from entitlement to building permit issuance;
   4. Median inspection response time;
   5. Breakdown by project size category (1-4 units, 5-25 units, 26-100 units, 100+ units);
   6. Comparison to Permit Streamlining Act timelines; and
   7. Resubmittal counts and associated delays.

E. **Annual Progress Report Integration.** Permitting systems shall:
   1. Track all data fields required for HCD Annual Progress Report Tables A, A2, B, C, D, E, and F;
   2. Provide a direct export function generating HCD-compatible CSV or Excel files;
   3. Maintain audit trail of changes to APR-reportable fields;
   4. Flag projects approaching or exceeding APR reporting deadlines; and
   5. Generate discrepancy reports comparing system records to submitted APR data.

F. **Permit Record Retention and Public Access.** All permit records shall remain publicly searchable regardless of project status:
   1. Building permits shall not be archived, removed, or hidden from public search upon project completion, certificate of occupancy issuance, or permit finalization;
   2. All historical permit records, including those for completed projects, shall remain accessible through the public portal and API;
   3. Certificate of occupancy dates, final inspection records, and final fee payments shall be publicly searchable;
   4. The City shall not implement any "archival" or "closed records" policy that removes completed project permits from public view; and
   5. Any permit record accessible to City staff shall also be accessible to the public through the Open Data Portal, subject only to the exemptions in Section 2.150.020(C).

#### 2.150.070 Vendor Contract Requirements

A. **New Contracts.** Any contract for permitting software or data systems executed or renewed after the effective date of this ordinance shall require the vendor to:
   1. Provide public API access meeting the standards of Section 2.150.050;
   2. Support project-level linkages as defined in Section 2.150.010(L);
   3. Export data in open, non-proprietary formats;
   4. Provide the City with full data ownership and portability rights;
   5. Not impose licensing restrictions that prevent publication of data as open data; and
   6. Cooperate with the City in meeting compliance requirements of this Chapter.

B. **Existing Contracts.** For existing contracts that do not meet the requirements of subsection (A), the City Manager shall:
   1. Within six (6) months, report to City Council on compliance gaps;
   2. Negotiate amendments to bring contracts into compliance where feasible;
   3. Implement workarounds (such as middleware or ETL processes) to publish data pending contract compliance; and
   4. Include compliance requirements in any contract renewal or replacement.

---

### ARTICLE IV. INFRASTRUCTURE AND SECURITY

#### 2.150.080 Technical Infrastructure

A. **Availability.** The Open Data Portal and API endpoints shall maintain 99.5% uptime availability, measured monthly, excluding scheduled maintenance. Scheduled maintenance windows shall be announced at least 48 hours in advance.

B. **Security Standards.** All systems publishing open data shall:
   1. Use HTTPS with TLS 1.2 or higher and valid certificates from a trusted certificate authority;
   2. Implement appropriate access controls for administrative functions;
   3. Log access attempts and API requests for security monitoring;
   4. Comply with the City's information security policies; and
   5. Not store or transmit PII through the Open Data Portal.

C. **Zero-Trust Architecture.** City IT systems handling open data shall implement zero-trust security principles including:
   1. Verification of all users and devices regardless of network location;
   2. Least-privilege access controls;
   3. Micro-segmentation of network resources;
   4. Continuous monitoring and validation; and
   5. Encryption of data in transit and at rest.

D. **Vulnerability Assessment.** The City shall conduct annual vulnerability assessments of all systems publishing open data, including:
   1. Penetration testing by qualified security professionals;
   2. Review of access controls and authentication mechanisms;
   3. Assessment of third-party components and dependencies; and
   4. Remediation of identified vulnerabilities within 30 days for critical issues, 90 days for others.

E. **Disaster Recovery.** The City shall maintain:
   1. Automated daily backups of all published datasets;
   2. Geographic redundancy with backups stored in a separate physical location;
   3. Recovery time objective (RTO) of 24 hours for Open Data Portal restoration; and
   4. Annual testing of backup and recovery procedures.

F. **Web Application Firewall Configuration.** If the City uses Cloudflare, Akamai, AWS WAF, or similar services, the City shall:
   1. Configure rules to allow programmatic access that meets the legitimate access criteria of Section 2.150.030(D);
   2. Whitelist user-agent strings commonly used by data science tools (Python requests, R httr, curl, wget);
   3. Provide a bypass mechanism for researchers and civic technologists who can demonstrate legitimate purpose;
   4. Monitor and review blocked requests weekly to identify false positives; and
   5. Document WAF configuration and exception policies in API documentation.

---

### ARTICLE V. ACCOUNTABILITY AND ENFORCEMENT

#### 2.150.100 Chief Data Officer

A. **Designation.** The City Manager shall designate a Chief Data Officer (CDO) within six (6) months of the effective date of this ordinance. The CDO may be an existing staff position with additional responsibilities or a new position.

B. **Qualifications.** The CDO shall have expertise in data management, information technology, and public policy. Preferred qualifications include experience with open data programs, API development, and government transparency.

C. **Responsibilities.** The CDO shall:
   1. Oversee implementation of this Chapter;
   2. Maintain the master inventory of City datasets;
   3. Coordinate with City Departments to prioritize dataset publication;
   4. Establish and enforce data quality standards;
   5. Manage the Open Data Portal and API infrastructure;
   6. Respond to public dataset requests;
   7. Prepare annual compliance reports;
   8. Represent the City in open data communities and partnerships;
   9. Advise on data-related contract provisions; and
   10. Report to the City Manager and, as requested, to City Council on open data matters.

#### 2.150.110 Annual Compliance Report

A. **Report Required.** The CDO shall prepare an annual compliance report and present it to City Council no later than April 1 of each year, covering the preceding calendar year.

B. **Report Contents.** The annual compliance report shall include:
   1. Complete inventory of published datasets with publication dates;
   2. API availability metrics including uptime percentage and request volume;
   3. Datasets pending publication with target dates;
   4. Public dataset requests received, granted, and denied;
   5. Reasons for denied requests;
   6. Data quality metrics and improvement initiatives;
   7. Technical infrastructure status and planned upgrades;
   8. Community engagement activities;
   9. Comparison to prior year performance; and
   10. Recommendations for policy or resource changes.

C. **Public Availability.** The annual compliance report shall be published on the Open Data Portal and the City's website.

#### 2.150.120 Public Dataset Requests

A. **Request Process.** Any resident of Berkeley may request publication of a dataset not currently available on the Open Data Portal by submitting a request through a form provided on the Portal.

B. **Response Timeline.** The CDO shall respond to dataset requests within thirty (30) calendar days with either:
   1. A publication timeline specifying when the requested dataset will be available; or
   2. A written explanation of why the request cannot be fulfilled.

C. **Grounds for Denial.** Requests may be denied only if:
   1. The requested data constitutes PII as defined in Section 2.150.010(J);
   2. Disclosure would compromise an active law enforcement investigation;
   3. The data does not exist in any City system;
   4. Disclosure is prohibited by state or federal law; or
   5. The request is duplicative of a dataset already published or pending publication.

D. **Appeal.** A requester may appeal a denial to the City Manager within thirty (30) days. The City Manager shall issue a final determination within thirty (30) days of receiving the appeal.

E. **Request Log.** The CDO shall maintain a public log of all dataset requests, responses, and dispositions.

#### 2.150.130 City Auditor Oversight

A. **Audit Authority.** The City Auditor is authorized to audit compliance with this Chapter and report findings to City Council.

B. **Audit Scope.** Audits may examine:
   1. Completeness of dataset publication;
   2. Accuracy of published data compared to source systems;
   3. API availability and performance;
   4. Response to public dataset requests;
   5. Vendor contract compliance; and
   6. Data security practices.

C. **Access.** City Departments shall provide the City Auditor with access to source systems, documentation, and personnel necessary to conduct audits.

D. **Reporting.** The City Auditor shall report audit findings to City Council and publish findings on the City's website.

---

### ARTICLE VI. COMMUNITY ENGAGEMENT

#### 2.150.140 Annual Open Data Forum

A. **Forum Required.** The City shall host an annual Open Data Community Forum, open to all members of the public, to:
   1. Present the annual compliance report;
   2. Demonstrate new datasets and API capabilities;
   3. Receive requests for new datasets;
   4. Gather feedback on data quality and usability;
   5. Discuss emerging data needs and priorities; and
   6. Recognize civic data projects and community contributions.

B. **Notice.** The forum shall be noticed at least thirty (30) days in advance through the City's website, social media, and email lists.

C. **Accessibility.** The forum shall be accessible to persons with disabilities and shall offer remote participation options.

#### 2.150.150 Educational Partnerships

A. **Partnership Program.** The City shall establish a Data Literacy and Civic Data Partnership Program with:
   1. University of California, Berkeley;
   2. Berkeley City College;
   3. Berkeley Unified School District; and
   4. Other educational institutions and community organizations as appropriate.

B. **Program Activities.** Partnership activities may include:
   1. Student projects using City open data;
   2. Internships in the Chief Data Officer's office;
   3. Curriculum development for data literacy;
   4. Hackathons and civic tech challenges;
   5. Research collaborations; and
   6. Faculty consultations on data policy.

C. **Data Licensing.** Data provided through partnership programs shall be licensed under Creative Commons CC0 or a similarly permissive license that allows academic publication, derivative works, and commercial use.

#### 2.150.160 Developer Support

A. **Developer Documentation.** The City shall provide comprehensive developer documentation including:
   1. Getting started guides for common use cases;
   2. Code examples in Python, JavaScript, and R;
   3. Sample applications demonstrating API usage;
   4. Data dictionaries and schema documentation;
   5. FAQ and troubleshooting guides; and
   6. Community forum or support channel for technical questions.

B. **Developer Office Hours.** The CDO or designated staff shall hold quarterly virtual office hours for developers and data users to ask questions and provide feedback.

---

### ARTICLE VII. IMPLEMENTATION TIMELINE

#### 2.150.170 Phased Implementation

Implementation of this Chapter shall proceed according to the following timeline:

A. **Phase 1: Foundation (0-6 months)**
   1. City Manager appoints Chief Data Officer;
   2. CDO conducts complete inventory of City datasets;
   3. CDO assesses current permitting system capabilities and vendor contract provisions;
   4. CDO develops data quality standards and publication guidelines;
   5. City establishes or procures Open Data Portal infrastructure; and
   6. CDO reports to City Council on implementation plan and resource needs.

B. **Phase 2: Initial Publication (6-12 months)**
   1. Open Data Portal launched with public access;
   2. Top 20 high-value datasets published including:
      - Building permits (current and historical)
      - Planning permits
      - Business licenses
      - Code enforcement cases
      - Budget allocations
      - Fee schedules
      - City Council voting records
      - GIS parcel and zoning data;
   3. API access available for published datasets;
   4. Developer documentation published; and
   5. First annual Open Data Forum held.

C. **Phase 3: Permit System Integration (12-18 months)**
   1. All permit data available via API with project-level linkages;
   2. Affordable housing data fields implemented per Section 2.150.060(C);
   3. Processing time metrics calculated and published;
   4. APR export functionality operational;
   5. In-lieu fee payments tracked in permitting system; and
   6. Housing Trust Fund receipts and expenditures published.

D. **Phase 4: Full Compliance (18-24 months)**
   1. All mandatory datasets published per Section 2.150.040;
   2. All API requirements met per Section 2.150.050;
   3. Vendor contracts amended or replaced for compliance;
   4. Annual compliance report covers full year of operations;
   5. Community partnerships established per Section 2.150.150; and
   6. CDO presents full compliance certification to City Council.

#### 2.150.180 Progress Reporting

A. The CDO shall provide quarterly progress reports to the City Manager during the 24-month implementation period.

B. The CDO shall present semi-annual progress reports to City Council during the implementation period.

C. Progress reports shall document achievements, challenges, resource expenditures, and adjustments to the implementation plan.

---

### ARTICLE VIII. GENERAL PROVISIONS

#### 2.150.190 Severability

If any section, subsection, sentence, clause, phrase, or word of this Chapter is for any reason held to be invalid or unconstitutional by a court of competent jurisdiction, such decision shall not affect the validity of the remaining portions of this Chapter.

#### 2.150.200 Relationship to Public Records Act

This Chapter supplements but does not replace obligations under the California Public Records Act (Government Code Section 6250 et seq.). Nothing in this Chapter shall be construed to limit the public's right to request records under the Public Records Act or to limit the City's obligations under that Act.

#### 2.150.210 Effective Date

This ordinance shall become effective thirty (30) days after its final adoption.

---

## CERTIFICATION

I hereby certify that the foregoing ordinance was adopted by the Council of the City of Berkeley at a _______ meeting of the Council held on _____________, 20___, by the following vote:

AYES:

NOES:

ABSENT:

ABSTAIN:

______________________________
City Clerk

APPROVED:

______________________________
Mayor

APPROVED AS TO FORM:

______________________________
City Attorney

---

## APPENDIX A: MODEL DATA SCHEMA FOR HOUSING PERMITS

*The following schema illustrates the minimum structured data fields for housing development permits as required by Section 2.150.060(C):*

```json
{
  "project_id": "string (unique identifier)",
  "permits": ["array of associated permit numbers"],
  "address": "string",
  "apn": "string (assessor parcel number)",
  "project_name": "string (optional)",
  "applicant": {
    "name": "string",
    "company": "string",
    "contact_email": "string",
    "contact_phone": "string"
  },
  "application_date": "date (ISO 8601)",
  "completeness_date": "date (ISO 8601)",
  "entitlement_date": "date (ISO 8601)",
  "building_permit_date": "date (ISO 8601)",
  "certificate_of_occupancy_date": "date (ISO 8601)",
  "status": "string (enumerated)",
  "status_history": [
    {
      "status": "string",
      "date": "date (ISO 8601)",
      "assigned_staff": "string"
    }
  ],
  "units": {
    "total": "integer",
    "net_new": "integer",
    "demolished": "integer",
    "by_bedroom": {
      "studio": "integer",
      "one_br": "integer",
      "two_br": "integer",
      "three_br": "integer",
      "four_plus_br": "integer"
    },
    "by_income_level": {
      "extremely_low": "integer",
      "very_low": "integer",
      "low": "integer",
      "moderate": "integer",
      "above_moderate": "integer"
    }
  },
  "affordability": {
    "deed_restricted": "boolean",
    "covenant_recorded": "boolean",
    "covenant_recording_number": "string",
    "covenant_expiration_date": "date (ISO 8601)",
    "administering_agency": "string"
  },
  "density_bonus": {
    "applicable": "boolean",
    "base_units": "integer",
    "bonus_percentage": "number",
    "bonus_units": "integer",
    "concessions": ["array of strings"],
    "waivers": ["array of strings"],
    "incentives": ["array of strings"]
  },
  "streamlining": {
    "sb35_eligible": "boolean",
    "sb35_applied": "boolean",
    "sb330_applicable": "boolean",
    "ab2011_applicable": "boolean",
    "other_streamlining": ["array of strings"]
  },
  "in_lieu_fees": {
    "applicable": "boolean",
    "amount": "number (USD)",
    "payment_date": "date (ISO 8601)",
    "receiving_fund": "string"
  },
  "replacement_units": {
    "required": "boolean",
    "required_count": "integer",
    "provided_count": "integer",
    "income_levels_matched": "boolean"
  },
  "processing_metrics": {
    "days_to_completeness": "integer",
    "days_to_entitlement": "integer",
    "days_to_building_permit": "integer",
    "resubmittal_count": "integer",
    "total_processing_days": "integer"
  }
}
```

---

## APPENDIX B: REFERENCES

### Existing Open Data Ordinances and Policies

1. **San Francisco, California** - Administrative Code Chapter 22D "Open Data Policy" (2010, amended 2018)
   - https://codelibrary.amlegal.com/codes/san_francisco/latest/sf_admin/0-0-0-18147

2. **Oakland, California** - Administrative Instruction 1401 "Open Data Policy" (2013)
   - https://www.oaklandca.gov/resources/open-data

3. **California Government Code Section 6253.10** - State agency machine-readable data requirements (AB 169, 2019)
   - https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=6253.10.&lawCode=GOV

### Research and Data Quality Studies

4. **Possibility Lab, UC Berkeley** - Research on Annual Progress Report data quality and housing production accountability
   - https://possibilitylab.berkeley.edu/

5. **Terner Center for Housing Innovation, UC Berkeley** - Research on housing development costs and affordable housing finance
   - https://ternercenter.berkeley.edu/

### Technical Standards

6. **RESTful API Design Guidelines** - Microsoft REST API Guidelines
   - https://github.com/microsoft/api-guidelines

7. **Web Content Accessibility Guidelines (WCAG) 2.1**
   - https://www.w3.org/TR/WCAG21/

8. **California Department of Housing and Community Development** - Annual Progress Report Forms and Instructions
   - https://www.hcd.ca.gov/planning-and-community-development/annual-progress-reports

---

*This model ordinance was developed based on independent analysis of Berkeley's housing permit data conducted in 2025-2026, which identified significant data quality and transparency gaps. The analysis cross-referenced City Accela permit records against state APR submissions and public reporting, finding a 97.4% match rate for reported projects but identifying approximately 885 housing units potentially missing from APR filings and documenting the absence of structured in-lieu fee tracking.*
