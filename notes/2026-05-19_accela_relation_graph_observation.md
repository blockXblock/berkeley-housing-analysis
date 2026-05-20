# Observation: Accela Related Records relation graph is empty for ZP2018-0135

**Date:** 2026-05-19
**Status:** Preliminary observation from a single record. Pattern not yet verified across multiple permits. Worth investigating systematically.

## What we observed

While building a freshness pipeline to keep our 179-project database current with Berkeley's permit system, we did detailed reconnaissance on the Accela record for ZP2018-0135 (2352 Shattuck Ave, an approved 5-story mixed-use project).

Our local database records four permits for this project:
- ZP2018-0135 (zoning permit, master entitlement)
- DRCF2020-0003 (design review)
- B2019-05574 (building permit)
- B2019-05575 (building permit)

We expected Accela's "Related Records" feature to link these into a project graph. Instead, the Related Records sub-tab on ZP2018-0135 shows "No records found." Both the inline directly-related list and the "View Entire Tree" panel return empty.

We don't yet know whether the building permits B2019-05574 and B2019-05575 actually exist in Accela. If they do, they aren't linked to the zoning permit through the relation table. If they don't, our database is incorrect about this project — itself a freshness-pipeline failure mode.

## Why this matters

Public housing data accountability depends on being able to ask, of any given project, the questions a journalist or resident would naturally ask:

- What is the current status of this project?
- How long did each phase take?
- Where does the project sit in the permit pipeline today?
- When will it be complete?

These questions are easy to answer if a project's permits are linked into a graph. They are hard or impossible to answer if each permit is an isolated record without explicit connection to the project it serves.

In a city aiming to demonstrate transparent housing-pipeline performance to its residents and to the state (via HCD's Annual Progress Report), the lack of a reliable project-level graph in Accela is a systemic accountability gap. It is also a practical obstacle: every data consumer (the city itself for APR reporting, researchers like us, journalists at Berkeleyside or the East Bay Times, advocacy groups) has to independently reconstruct the project-permit linkage from address strings and approximate matching.

This duplicated reconstruction work is wasteful and introduces inconsistency. Different consumers will reach different conclusions about which permits "belong" to which project.

## How this should be engineered

If we were designing Berkeley's permit system from first principles to support transparent housing-pipeline reporting, we would specify:

1. **A "Project" entity as a first-class concept**, separate from individual permits. A project would have a stable identifier, a primary address, an APN, and a current pipeline stage. Every permit (planning, design review, demolition, building, mechanical, electrical, etc.) would have a foreign-key reference to its parent project. Status changes on any permit would propagate to the project's stage by rule.

2. **Mandatory relation creation at filing time.** When a new permit is filed for an existing project (e.g., the building permit following an approved zoning permit), the relation should be required, not optional. The filing UI should auto-suggest related records by parcel and require staff confirmation before saving.

3. **Public API endpoints with project-level queries.** A public read-only API endpoint that returns, for any project ID or parcel APN, the full graph of permits with their statuses, dates, and milestones. JSON output. No login required. Documented rate limits (10,000 requests/day minimum per the open data ordinance draft we authored in April).

4. **Status vocabulary discipline.** A small, fixed vocabulary of project-pipeline stages (e.g., Pre-Application / Application Submitted / In Review / Entitled / Permits Active / Under Construction / Completed / Withdrawn / Stalled), with documented transition rules. Permit-level statuses (which are rich and varied) map cleanly to project-level stages via the rules. This is what Berkeley's APR process tries to reconstruct manually each year.

5. **Daily incremental publication.** Every status change exported to a public daily feed. Researchers and advocates can subscribe; no scraping required.

6. **Backward population.** Existing projects' permit relations should be backfilled, at least for the housing pipeline. The work to reconstruct relations from address/APN matching is finite (179 active housing projects in our tracking; thousands of permits total) and one-time. This is exactly the kind of work an AI-assisted data project could complete in days.

## What we are doing in the meantime

Building our own project-permit relation graph by address and APN matching. Each freshness query searches Accela by address rather than relying on Accela's relation table. The redundant work that 50+ data consumers are doing in parallel — that's the gap we are filling, but it's a gap that shouldn't exist.

This note will be revisited as we examine more permits. If the pattern of empty relation graphs holds across many projects, that strengthens the case for systemic improvement. If it's specific to older records (the ZP we examined is from 2018), that informs the scope of any backfill effort.
