# Documents Workflow — v2 PDF URL Backfill

**Created:** 2026-05-12
**Status:** Proof-of-concept validated; pattern ready for replication

Purpose: capture the workflow for adding working PDF URLs to v2.documents.
Most v2.documents rows (1,406 of 1,409 as of 2026-05-12) have NO URLs —
v1 captured document titles but not retrievable links. This workflow
adds durable Google Drive URLs that survive Accela session expiration.

---

## Background

### Why Accela URLs don't work directly

Berkeley's Accela document links are JavaScript postbacks:

```
javascript:__doPostBack('attachmentList$gdvAttachmentList$ctl10$lnkFileName','')
```

There is no stable URL to put in the database. Each PDF requires:
- An active Accela session
- The specific page state (postback target)
- Server-side interpretation of the postback to stream the file

This means Accela URLs cannot be saved and re-used. The PDFs themselves
exist on Accela's server but are unreachable via stable URLs.

### Why Google Drive

For each PDF we want to preserve and link to:
1. Download from Accela (manual click via active session)
2. Upload to Google Drive
3. Get a per-file shareable URL (durable, doesn't expire)
4. Record in v2.documents.drive_url

The drive_url field in v2.documents was designed for exactly this purpose,
alongside source_url (Accela), ia_url (Internet Archive), and r2_url
(Cloudflare R2). Drive is the most accessible mirror for civic transparency
because anyone with a browser can view the URL without authentication.

---

## Directory naming convention

### Format

`<zero-padded-project-id>_<normalized-address>`

### Examples

| Project ID | Canonical Address | Drive folder name |
|-----------:|-------------------|-------------------|
| 1 | 1750 SACRAMENTO St | `01_1750_sacramento_st` |
| 5 | 2425 DURANT Ave | `05_2425_durant_ave` |
| 133 | 2128 Oxford St | `133_2128_oxford_st` |
| 141 | 2016 ASHBY Ave | `141_2016_ashby_ave` |
| 151 | Ashby BART | `151_ashby_bart` |
| 171 | 2400 BOWDITCH St | `171_2400_bowditch_st` |

### Normalization rules

- Project ID: zero-pad to 2 digits if < 100, no padding if >= 100
- Street address: lowercase, replace spaces with underscores
- Drop the comma and ZIP code if present
- Special cases (BART, UC properties without street numbers): use a descriptive
  short name matching the canonical_address pattern

### Why this convention

- **Globally unique** — project_id prefix prevents collisions
- **Human-readable** — address suffix makes browsing Drive useful
- **Sorts naturally** — numeric prefix orders folders by project age
- **Maps to v2** — matches project_id FK in v2.documents
- **Handles edge cases** — BART parcels, UC properties, multi-address projects

---

## File naming within folders

### Format

`<published-date>_<permit-or-doctype>_<descriptive-name>.pdf`

### Examples

- `2024-11-15_zp2024-xxxx_entitlement_plan_set.pdf`
- `2025-04-11_zp2024-xxxx_revised_plan_set_v2.pdf`
- `2024-08-15_zab_packet_2138_oxford.pdf`
- `2023-10-12_ceqa_initial_study.pdf`
- `2024-03-01_density_bonus_application.pdf`

### Why this format

- **Date prefix** sorts chronologically when browsing Drive
- **Permit/doctype mid-section** allows filtering by document category
- **Descriptive name** makes purpose clear without opening the file
- Filename comes AFTER directory choice — Drive folder is project-centric,
  filename is document-specific (may reference a permit if relevant)

---

## Step-by-step workflow

### Per project

**1. Identify target project**
- Query v2 for project details (canonical_address, current_version_id)
- Note any major permits in v2.permits (their permit_numbers will appear
  in filenames if documents relate to specific permits)

**2. Open Accela in browser**
- Authenticated to Berkeley Accela (Construction/Building or Planning module)
- Navigate to the project's primary record (search by address or permit)

**3. Identify documents to capture**
- Plan sets (largest PDFs, architects' drawings)
- Entitlement application packets
- ZAB / planning commission staff reports
- CEQA documents (Mitigated Negative Declaration, Initial Study)
- Density bonus or SB-330 applications
- Renderings (separate from plan sets)
- Conditions of approval
- Issued permit PDFs (after approval)

Priority order: largest PDFs first (typically plan sets), then critical
public-interest documents (CEQA, conditions, ZAB packets).

**4. Download each PDF**
- Click the JavaScript postback link in Accela
- File downloads to local filesystem
- Rename if needed to match the file naming convention

**5. Create Drive folder for project**
- Use the directory naming convention: `<zero-padded-id>_<normalized-address>`
- Location: `Berkeley Housing Pipeline/Documents/<folder-name>/`
- Sharing: "Anyone with the link → Viewer" (for public civic transparency)
- Flat structure within folder (no subfolders) — keep it simple

**6. Upload PDFs to Drive folder**
- Drag-and-drop or use Drive's upload UI
- Verify the file is in the right folder before getting the link

**7. Get shareable URL for each file**
- Right-click the file in Drive → "Get link" or "Share"
- Confirm permission level is "Anyone with the link can view"
- Copy the URL in the form: `https://drive.google.com/file/d/<id>/view?usp=sharing`

**8. INSERT into v2.documents**

Template SQL:

```sql
INSERT INTO documents (
  project_id,
  document_type_id,
  title,
  published_date,
  drive_url,
  url_last_verified,
  url_status,
  source_system,
  fetched_at,
  notes
) VALUES (
  <project_id>,
  <document_type_id from vocabulary_document_types>,
  '<title from filename>',
  '<YYYY-MM-DD from filename>',
  '<drive_url>',
  '<today YYYY-MM-DD>',
  'active',
  'manual_drive_upload',
  '<today YYYY-MM-DD>',
  '<provenance note explaining Accela origin and re-hosting>'
);
```

Required columns to fill:
- `project_id` — v2 project ID (must reference existing projects.id)
- `document_type_id` — see vocabulary table (1-23: application, plan_set, staff_report, zab_packet, etc.)
- `title` — descriptive title, typically matches filename
- `published_date` — date on the document (not date of upload)
- `drive_url` — the per-file Drive URL with ?usp=sharing
- `url_last_verified` — today
- `url_status` — `'active'` (CHECK constraint allows: active/broken/moved/unknown/NULL)
- `source_system` — `'manual_drive_upload'`
- `fetched_at` — today
- `notes` — provenance explaining Accela JavaScript postback origin and Drive re-hosting

**9. Verify INSERT**

```sql
SELECT id, project_id, title, drive_url, url_status
FROM documents
WHERE project_id = <project_id>
  AND source_system = 'manual_drive_upload';
```

Should return new rows with drive_url populated.

---

## Document type vocabulary (v2.vocabulary_document_types)

For reference:

| id | code | typical use |
|---:|------|------------|
| 1 | application | Entitlement applications |
| 2 | plan_set | Architectural drawings, plan sets, exhibits |
| 3 | staff_report | Planning staff reports |
| 4 | zab_packet | Zoning Adjustments Board packets |
| 5 | design_review_packet | Design Review Committee packets |
| 6 | agenda | Meeting agendas |
| 7 | minutes | Meeting minutes |
| 8 | mitigated_neg_dec | Mitigated Negative Declarations |
| 9 | eir | Environmental Impact Reports |
| 10 | categorical_exemption | CEQA Categorical Exemptions |
| 11 | fee_schedule | Fee schedule documents |
| 12 | fee_receipt | Fee receipt PDFs |
| 13 | inspection_report | Inspection reports |
| 14 | certificate_of_occupancy | Certificates of Occupancy |
| 15 | conditions_of_approval | Conditions of Approval letters |
| 16 | affordable_housing_agreement | Affordable housing covenant agreements |
| 17 | density_bonus_application | Density bonus applications |
| 18 | sb35_application | SB-35 streamlining applications |
| 19 | correspondence | City letters, applicant responses |
| 20 | public_comment | Public comments from outreach |
| 21 | rendering | Project renderings, illustrative images |
| 22 | photograph | Site photographs |
| 23 | other | Catch-all for uncategorized |

---

## Provenance notes template

In the notes field, capture three pieces of information:

1. **Why this document is significant** — context about the project, what
   this document represents in the development process
2. **How it was obtained** — "Downloaded from Berkeley Accela via JavaScript
   postback download (URL was non-durable); re-hosted to Google Drive for
   permanent civic access."
3. **Drive folder reference** — link to the parent folder for browsing related
   documents

Example:

```
Original entitlement plan set for 2425 Durant Ave (Collabhome, 117 units,
20-story SB-330 project). Plan set is exhibits 2+3 of the application packet.
Downloaded from Berkeley Accela via JavaScript postback download (URL was
non-durable); re-hosted to Google Drive for permanent civic access. Drive
folder: https://drive.google.com/drive/folders/<folder-id>?usp=sharing.
Part of revision sequence: original (2024-11-15), revised 1 (2025-02-13),
revised 2 (2025-04-11).
```

---

## Honest constraints

### What works well

- Manual workflow: 5-10 minutes per project for 3-5 documents
- Drive URLs are durable; survive Accela session expiration
- Public Drive sharing supports civic transparency
- v2.documents schema cleanly accommodates the data with proper provenance
- Pattern proven via project 5 (2425 Durant) on 2026-05-12 — 3 plan sets
  populated successfully

### What does not yet work

- **Bulk backfill is labor-intensive**: ~117 hours for all 1,406 v1-migrated
  documents at 5 minutes each. Not feasible without prioritization.
- **No automation**: each download requires manual Accela session interaction
- **Internet Archive snapshots don't capture postback-driven downloads** —
  IA crawler can't follow the JavaScript, only sees the page HTML
- **Cloudflare R2 not yet set up** — drive_url is currently the only working
  durable storage path

### When to apply this workflow

Priority order:
1. Active high-visibility projects (current entitlement or construction)
2. Projects where the Explorer's documents tab is being demonstrated
3. Projects with substantial public interest (large unit counts, density bonus,
   SB-330 / SB-35 / AB-2011)
4. Documents that have been requested (CPRA backups, journalism inquiries)

Not worth backfilling:
- Documents with empty or trivial titles in v1 migration
- Documents at projects that have never had a permit (entitlement-only,
  pre-application)
- Documents older than ~5 years where Accela retention may be questionable

---

## Future automation paths

### Option A: Headless browser scraping

Use Playwright or Puppeteer to:
1. Authenticate to Accela
2. Navigate to each permit's documents tab
3. Click each postback link, capture the resulting download
4. Upload to Drive/R2 via API
5. Record in v2.documents via INSERT

Scope: 4-8 hours to build; days to run across all projects.
Risk: Berkeley Accela may rate-limit or detect scraping.

### Option B: Sidebar-driven workflow

Sidebar (with Accela access) downloads individual documents and provides
their URLs back to us for INSERT. Per-document, slower than headless
automation but more reliable for Accela's quirks.

Sidebar limitation: cannot upload to Drive itself, so workflow becomes:
1. Sidebar identifies documents to capture
2. Human downloads via Accela
3. Human uploads to Drive
4. Sidebar (or human) constructs INSERT statements

### Option C: City Permit Center direct query

For some documents (especially permit PDFs and conditions of approval),
the City Permit Center can directly email PDFs in response to a specific
request. Useful for capped scope (1-3 documents) when Accela is broken.

---

## Replicating for the next project

1. Pick a project from v2 (e.g., 2128 Oxford / Core Spaces / project 133)
2. Note its canonical_address and project_id
3. Follow steps 2-8 above
4. INSERT documents with proper provenance
5. Update this document with any new edge cases encountered

The workflow should evolve as we encounter projects with unusual document
structures (multi-permit projects, projects with no main permit, etc.).

---

*Workflow documented 2026-05-12 after successful proof-of-concept on
project 5 (2425 Durant Ave): 3 plan sets populated with working
Google Drive URLs.*
