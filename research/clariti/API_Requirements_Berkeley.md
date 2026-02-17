# Clariti API Requirements for City of Berkeley
**Civic Data Science & Smart City Analytics**

**Date:** 2026-01-14  
**Prepared by:** Berkeley Housing Data Science Project  
**Purpose:** Enable comprehensive urban analytics, research, and public transparency

---

## 1. EXECUTIVE SUMMARY

The City of Berkeley is transitioning to Clariti for permit management. To support:
- Academic research
- Civic transparency
- Data-driven policy
- Smart city initiatives
- Public health analysis
- Economic development tracking

We require comprehensive, programmatic API access to all permit and planning data.

---

## 2. CORE REQUIREMENTS

### 2.1 API Architecture

**RESTful API with:**
- JSON response format (primary)
- CSV export capability (for bulk downloads)
- GraphQL support (optional, for complex queries)
- WebSocket support (optional, for real-time updates)

**Authentication:**
- App token system (like Socrata)
- OAuth 2.0 for authenticated users
- Rate limiting that allows reasonable academic/research use
- Higher limits for registered .edu users

**Base URL Structure:**
```
https://api.clariti.berkeley.gov/v1/
https://data.cityofberkeley.info/clariti/v1/  (alternative)
```

---

### 2.2 Essential Data Endpoints

#### A. Building Permits
```
GET /permits/building
GET /permits/building/{permit_id}
GET /permits/building/search?{filters}
```

**Required Fields:**
- `permit_id` (unique identifier)
- `permit_number` (display number)
- `address` (full street address)
- `parcel_apn` (assessor parcel number)
- `permit_type` (new construction, addition, alteration, etc.)
- `work_description` (detailed description)
- `status` (issued, under review, completed, etc.)
- `status_date` (date of current status)
- `issue_date` (when permit was issued)
- `final_date` (completion/CO date)
- `expiration_date`
- `valuation` (project value)
- `units_new` (new housing units created)
- `units_demolished` (units removed)
- `square_footage` (total square footage)
- `stories` (number of stories)
- `occupancy_type`
- `construction_type`
- `applicant_name`
- `contractor_name`
- `architect_name`
- `coordinates` (latitude, longitude in WGS84/EPSG:4326)

**Optional but Valuable:**
- `inspection_history` (array of inspections)
- `fees_paid`
- `appeals` (any appeals filed)
- `related_permits` (links to other permits)
- `documents` (links to plans, reports)

#### B. Zoning & Planning Permits
```
GET /permits/planning
GET /permits/zoning
GET /permits/use
```

**Required Fields:**
- All building permit fields (where applicable)
- `zoning_district`
- `land_use_type`
- `ceqa_determination` (environmental review)
- `variance_requested`
- `public_hearing_date`
- `planning_commission_action`
- `appeal_period_end`

#### C. Business Licenses
```
GET /licenses/business
GET /licenses/business/{license_id}
```

**Required Fields:**
- `license_id`
- `business_name`
- `dba_name` (doing business as)
- `business_type`
- `naics_code` (industry classification)
- `address`
- `owner_name`
- `issue_date`
- `expiration_date`
- `status` (active, expired, suspended)
- `employee_count`

#### D. Code Enforcement
```
GET /enforcement/cases
GET /enforcement/violations
```

**Required Fields:**
- `case_id`
- `address`
- `violation_type`
- `status`
- `open_date`
- `close_date`
- `compliance_date`

#### E. Inspections
```
GET /inspections
GET /inspections?permit_id={id}
```

**Required Fields:**
- `inspection_id`
- `permit_id` (link to permit)
- `inspection_type`
- `scheduled_date`
- `completed_date`
- `result` (passed, failed, conditional)
- `inspector_notes`

---

### 2.3 Query Capabilities

**Filtering:**
```
?status=issued
?issue_date_from=2024-01-01&issue_date_to=2024-12-31
?address=*Shattuck*
?zoning_district=C-DMU
?units_new>=50
```

**Pagination:**
```
?limit=1000
?offset=5000
?page=3&per_page=500
```

**Sorting:**
```
?sort=issue_date
?sort=-valuation  (descending)
```

**Field Selection:**
```
?fields=permit_id,address,units_new,issue_date
```

**Aggregation:**
```
?aggregate=sum(units_new)&group_by=year
?aggregate=count(*)&group_by=zoning_district
```

---

### 2.4 Geospatial Data

**GeoJSON Support:**
```
GET /permits/building.geojson
```

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.2728, 37.8715]
      },
      "properties": {
        "permit_id": "...",
        "address": "...",
        ...
      }
    }
  ]
}
```

**Bounding Box Queries:**
```
?bbox=-122.30,37.85,-122.23,37.92  (west,south,east,north)
```

**Integration with Berkeley GIS:**
- Cross-reference to parcel data
- Link to zoning maps
- Connect to city infrastructure datasets

---

## 3. SMART CITY DATA INTEGRATION

### 3.1 Multi-Domain Analytics

Enable cross-domain queries connecting:

**Housing + Economic Development:**
```
GET /analytics/housing-business-correlation
```
- New housing units vs new business licenses
- Residential development impact on commercial corridors

**Public Health + Building:**
```
GET /analytics/health-housing
```
- Housing conditions violations
- Lead paint remediation permits
- ADA compliance upgrades

**Energy + Building:**
```
GET /analytics/energy-permits
```
- Solar installation permits
- Energy efficiency upgrades
- EV charging infrastructure

**Waste + Building:**
```
GET /analytics/waste-construction
```
- Construction debris tracking
- Recycling compliance
- Hazardous material removal

**Water + Building:**
```
GET /analytics/water-permits
```
- Plumbing permits
- Water conservation measures
- Graywater systems

---

### 3.2 UrbanSim Integration

**Data Export Format:**
```
GET /export/urbansim
```

Provide data in UrbanSim-compatible format:
- Parcels table
- Buildings table
- Households table
- Jobs table
- Development pipeline table

**Schema mapping documentation** for:
- Converting Clariti permits to UrbanSim buildings
- Aggregating to parcel level
- Time-series development tracking

---

## 4. PERFORMANCE REQUIREMENTS

### 4.1 Response Times
- Single record: < 200ms
- Paginated queries (1000 records): < 2 seconds
- Bulk exports (10,000+ records): < 30 seconds
- Geospatial queries: < 5 seconds

### 4.2 Rate Limits
- **Public (no auth):** 100 requests/hour
- **Registered users:** 1,000 requests/hour
- **Academic/Research (.edu):** 10,000 requests/hour
- **City partners:** 100,000 requests/hour

### 4.3 Availability
- 99.5% uptime SLA
- Planned maintenance windows announced 7 days in advance
- Status page: `status.clariti.berkeley.gov`

---

## 5. DATA QUALITY & STANDARDS

### 5.1 Address Standardization
- USPS-standardized addresses
- Geocoding using NAD83 / EPSG:4326
- Quality flag for geocoding confidence

### 5.2 Date Formats
- ISO 8601: `2024-01-15T14:30:00-08:00`
- Consistent timezone (Pacific)

### 5.3 NULL Handling
- Explicit `null` in JSON (not empty strings)
- Documentation of which fields can be null

### 5.4 Data Dictionary
- Complete field documentation
- Enumerated values (e.g., all permit statuses)
- Units of measurement clearly specified

---

## 6. DOCUMENTATION REQUIREMENTS

### 6.1 Public API Documentation
- Interactive documentation (Swagger/OpenAPI)
- Code examples in Python, R, JavaScript
- Authentication guide
- Rate limit explanations
- Common query patterns

### 6.2 Changelog
- Version history
- Breaking changes clearly marked
- Migration guides for API updates

### 6.3 Sample Data
- Anonymized/redacted sample datasets
- Test endpoints with synthetic data
- Sandbox environment for development

---

## 7. HISTORICAL DATA

### 7.1 Accela Migration
- All historical Accela data accessible via Clariti API
- Minimum 10 years of history
- Clearly marked legacy vs new data
- Field mapping documentation (Accela → Clariti)

### 7.2 Data Retention
- Permits: Permanent retention
- Inspections: 10 years minimum
- Code violations: 7 years minimum

---

## 8. PRIVACY & REDACTION

### 8.1 Public Records Act Compliance
- Applicant/owner names: public
- Personal phone/email: redacted
- Financial details beyond valuation: redacted

### 8.2 Sensitive Data Handling
- DV SafeAtHome addresses: redacted
- Ongoing investigations: delayed publication

---

## 9. DEVELOPER SUPPORT

### 9.1 Getting Started
- Self-service app token registration
- Quick start guide
- Jupyter notebook examples
- R package/Python library

### 9.2 Support Channels
- Developer forum/mailing list
- GitHub repository for community scripts
- Issue tracker for API bugs
- Quarterly developer office hours

---

## 10. REFERENCE IMPLEMENTATIONS

### 10.1 Example Use Cases
Provide working examples for:
- Housing pipeline analysis
- Economic development tracking
- Public health research
- Energy efficiency monitoring
- Transportation impact analysis

### 10.2 Open Source Tools
- Python SDK: `pip install clariti-berkeley`
- R package: `install.packages("claritiR")`
- Command-line tool: `clariti-cli`

---

## 11. COMPARISON TO BEST PRACTICES

### 11.1 Benchmark Systems
- **Socrata** (used by many cities)
- **OpenGov** (transparency focus)
- **San Francisco DataSF**
- **Chicago Data Portal**
- **NYC Open Data**

### 11.2 Standards Compliance
- Open311 (for service requests)
- BLDS (Building and Land Development Specification)
- PDDL (Public Domain Dedication License) for data

---

## 12. SUCCESS METRICS

### 12.1 Adoption Metrics
- Number of registered API users
- API call volume
- Number of derived applications
- Academic papers using the data

### 12.2 Quality Metrics
- API uptime
- Average response time
- Error rate
- User satisfaction surveys

---

## 13. FUTURE ENHANCEMENTS

### 13.1 Phase 2 Capabilities
- Real-time permit status webhooks
- Machine learning APIs (permit timeline prediction)
- 3D building model exports
- AR/VR integration endpoints

### 13.2 Advanced Analytics
- Time-series forecasting endpoints
- Anomaly detection APIs
- Comparative analytics (Berkeley vs peer cities)

---

## APPENDIX A: Contact Information

**City of Berkeley:**
- IT Department: [contact]
- Planning Department: [contact]
- Building Department: [contact]

**Clariti:**
- Implementation team: [contact]
- API support: [contact]

**Research Partners:**
- UC Berkeley: [contact]
- Community organizations: [contact]

---

## APPENDIX B: Example API Calls

### Get all permits issued in 2024
```bash
curl "https://api.clariti.berkeley.gov/v1/permits/building?issue_date_from=2024-01-01&issue_date_to=2024-12-31&limit=1000"
```

### Get large residential projects
```bash
curl "https://api.clariti.berkeley.gov/v1/permits/building?units_new>=50&permit_type=new_construction"
```

### Get permits on a specific street
```bash
curl "https://api.clariti.berkeley.gov/v1/permits/building?address=*Shattuck*&sort=-issue_date"
```

### Get geospatial data
```bash
curl "https://api.clariti.berkeley.gov/v1/permits/building.geojson?bbox=-122.30,37.85,-122.23,37.92"
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-14  
**Next Review:** Upon Clariti implementation kickoff
