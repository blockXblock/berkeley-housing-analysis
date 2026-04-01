# Time-Flow Sankey: Berkeley Housing Pipeline Visualization

## Concept

A **time-series project flow** visualization where each housing project is a horizontal thread moving through permitting stages over real calendar time. Unlike traditional Sankey diagrams with fixed categorical stages, this shows the actual temporal journey of 164 projects through Berkeley's development pipeline from 2020-2026.

Think of it as a river with 164 tributaries — each project thread merges into review pools, splits through correction cycles, and flows toward completion. The visualization reveals systemic patterns: bottlenecks, seasonal variations, and the "correction loop" that traps many projects.

---

## Visual Design

### Axes

| Axis | Description |
|------|-------------|
| **X-axis** | Calendar time (January 2020 – December 2026) |
| **Y-axis** | Vertical groupings by current stage |

### Vertical Stage Bands (top to bottom)

```
┌─────────────────────────────────────────────────────────────────┐
│  COMPLETED                                                       │
├─────────────────────────────────────────────────────────────────┤
│  UNDER CONSTRUCTION                                              │
├─────────────────────────────────────────────────────────────────┤
│  BP ISSUED                                                       │
├─────────────────────────────────────────────────────────────────┤
│  BP APPLIED                                                      │
├─────────────────────────────────────────────────────────────────┤
│  ENTITLED                                                        │
├─────────────────────────────────────────────────────────────────┤
│  CORRECTIONS LOOP ←→ UNDER REVIEW                               │
├─────────────────────────────────────────────────────────────────┤
│  APPLICATION FILED                                               │
├─────────────────────────────────────────────────────────────────┤
│  PRE-APPLICATION / FIRST MENTION                                │
└─────────────────────────────────────────────────────────────────┘
```

### Thread Properties

| Property | Encoding |
|----------|----------|
| **Width** | Proportional to unit count (5 units = thin line, 500 units = thick band) |
| **Color** | By developer, project type, or affordability status |
| **Opacity** | Active = 1.0, Stalled (>12 months no movement) = 0.4 |
| **Path** | Smooth Bézier curves connecting stage transitions |

---

## The Corrections Loop

The most distinctive feature: visualizing correction cycles.

When a project moves from "Under Review" to "Corrections Issued" and back to "Under Review", its thread oscillates vertically within the Corrections Loop band. Multiple oscillations are visible as a sinusoidal pattern:

```
       ┌── Review ──┐     ┌── Review ──┐     ┌── Review ──┐
       │            │     │            │     │            │
──────►│    ↓       │────►│    ↓       │────►│    ↓       │──► Entitled
       │            │     │            │     │            │
       └── Corr ────┘     └── Corr ────┘     └── Corr ────┘
         Cycle 1            Cycle 2            Cycle 3
```

**Visual insight**: Projects with 3+ correction cycles have visibly wavy threads. This immediately reveals which projects got stuck in review hell.

---

## Data Sources

### 1. SFYimby First Mentions (`sfyimby_projects`)
- **Purpose**: Earliest visibility into pipeline (pre-application)
- **Date field**: `date_parsed`
- **Match**: `matched_project_id` links to FINAL.csv

### 2. Permit Events (`permit_events`)
- **Purpose**: Stage transition timestamps
- **Key events**: Application filed, completeness review, corrections issued, entitled, BP applied, BP issued, CO issued
- **Date field**: `event_date`

### 3. Project Metadata (`housing_projects_FINAL.csv`)
- **Purpose**: Units, developer, project type, coordinates
- **Key fields**: `net_units`, `status`, milestone dates, `is_uc_project`

### Merged Timeline Example

```
2127 DWIGHT Way (58 units)
──────────────────────────────────────────────────────────────────
Oct 2023    SFYimby first mention (pre-application)
Jan 2024    Application filed
Mar 2024    Completeness review
May 2024    Corrections issued
Jul 2024    Resubmittal
Aug 2024    Entitled
Oct 2024    BP applied
Dec 2024    BP issued
Jun 2025    Construction started (foundation)
Jan 2026    Topped out
Mar 2026    Completed
```

---

## Stage Mapping

Map raw permit event types to visualization stages:

| Event Type Pattern | Visualization Stage |
|--------------------|---------------------|
| `Pre-Application`, `Preliminary Application`, SFYimby first mention | PRE-APPLICATION |
| `Application`, `Filed`, `Submitted` | APPLICATION FILED |
| `Completeness Review`, `Under Review`, `Staff Review` | UNDER REVIEW |
| `Corrections`, `Incomplete`, `Resubmittal` | CORRECTIONS LOOP |
| `Approved`, `Entitled`, `Use Permit Approved` | ENTITLED |
| `Building Permit Applied`, `BP Submittal` | BP APPLIED |
| `Building Permit Issued`, `BP Issued` | BP ISSUED |
| `Under Construction`, `Foundation`, `Framing`, `Topped Out` | UNDER CONSTRUCTION |
| `Certificate of Occupancy`, `Finaled`, `Completed` | COMPLETED |

---

## Interaction Design

### Hover on Thread
```
┌────────────────────────────────────────┐
│  2276 SHATTUCK Ave                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Units: 336                            │
│  Developer: Trammell Crow              │
│  Current Stage: Entitled               │
│  First Seen: Oct 2023 (SFYimby)        │
│  Processing Days: 428                  │
│  Correction Cycles: 2                  │
│  ──────────────────────────────────── │
│  Timeline:                             │
│  • Oct 2023: Pre-application           │
│  • Mar 2024: Filed                     │
│  • Jun 2024: Corrections (1)           │
│  • Sep 2024: Corrections (2)           │
│  • Dec 2024: Entitled                  │
└────────────────────────────────────────┘
```

### Click on Thread
- Opens detailed project panel
- Shows all permit events with dates
- Links to Accela record
- Map pin highlights location

### Filter Controls

| Filter | Options |
|--------|---------|
| **Time range** | Slider to zoom into specific period |
| **Unit count** | Show only 50+ units, 100+ units, etc. |
| **Stage** | Highlight all projects currently in stage X |
| **Developer** | Filter to single developer's portfolio |
| **Affordability** | VLI/LI projects only |
| **Stalled** | Highlight projects with no movement >12 months |

### Animation
- **Play button**: Animate time from 2020 to present
- Shows threads appearing (first mention) and progressing through stages
- Reveals waves of applications (density bonus law changes, SB35 adoption)

---

## Technical Implementation

### Data Pipeline

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  sfyimby_projects │     │  permit_events   │     │  FINAL.csv       │
│  (249 entries)    │     │  (2,294 events)  │     │  (164 projects)  │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Merged Timeline Table  │
                    │  (project_id, date,     │
                    │   stage, source)        │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  D3.js Sankey Renderer  │
                    │  - Custom link paths    │
                    │  - Time-scaled x-axis   │
                    │  - Stage-grouped y-axis │
                    └─────────────────────────┘
```

### D3.js Approach

Use `d3-sankey` as a base but override:

1. **Node positioning**: Fixed X based on calendar date, fixed Y based on stage band
2. **Link paths**: Custom Bézier curves that allow vertical oscillation for correction cycles
3. **Force simulation**: Prevent thread overlap within same stage at same time

### Key Functions

```javascript
// Convert event to stage
function eventToStage(event_type) {
    if (/correction|incomplete|resubmit/i.test(event_type)) return 'CORRECTIONS';
    if (/entitled|approved/i.test(event_type)) return 'ENTITLED';
    if (/bp.*issued|building.*permit.*issued/i.test(event_type)) return 'BP_ISSUED';
    // ... etc
}

// Calculate thread path
function projectToPath(project) {
    const points = project.timeline.map(event => ({
        x: timeScale(event.date),
        y: stageScale(eventToStage(event.type)),
        type: event.type
    }));
    return smoothPath(points);
}

// Width scale
const widthScale = d3.scaleSqrt()
    .domain([1, 500])
    .range([1, 20]);
```

---

## Visual Patterns to Reveal

### 1. Bottleneck Detection
Dense horizontal bands show where projects accumulate. If the "Under Review" band is thick in mid-2023, it reveals a processing backlog.

### 2. Correction Cycle Analysis
Projects with wavy threads (multiple oscillations) vs smooth threads (direct entitlement) visually segregate problematic vs streamlined projects.

### 3. Developer Speed
Color-coding by developer shows which developers consistently move through the pipeline faster.

### 4. Policy Impact
Vertical markers for policy changes (SB35 adoption, density bonus updates) show acceleration/deceleration in flows.

### 5. Seasonal Patterns
If threads cluster at certain months (fiscal year end, election cycles), it reveals political patterns in approvals.

### 6. The "Graveyard"
Threads that fade to low opacity (stalled >12 months) show projects trapped in limbo — a visible "project graveyard."

---

## Implementation Phases

### Phase 1: Data Preparation
- [x] Create `sfyimby_projects` table with first-mention dates
- [x] Cross-reference with FINAL.csv (155 matched, 70 unmatched 10+)
- [ ] Create unified `project_timeline` view merging all sources
- [ ] Add `correction_cycle_count` to each project

### Phase 2: Static Visualization
- [ ] D3.js prototype with fixed layout
- [ ] Stage bands with proper spacing
- [ ] Thread width by unit count
- [ ] Basic color scheme

### Phase 3: Interactivity
- [ ] Hover tooltips
- [ ] Click to expand
- [ ] Filter controls
- [ ] Time range slider

### Phase 4: Animation
- [ ] Time playback
- [ ] Smooth thread transitions
- [ ] Policy event markers

---

## Data Requirements

### Minimum Viable Dataset

| Field | Source | Required |
|-------|--------|----------|
| `project_id` | FINAL.csv | Yes |
| `address` | FINAL.csv | Yes |
| `units` | FINAL.csv | Yes |
| `developer` | FINAL.csv | Nice to have |
| `first_mention_date` | sfyimby_projects | Yes |
| `app_filed_date` | permit_events / FINAL.csv | Yes |
| `entitled_date` | permit_events / FINAL.csv | Yes |
| `bp_issued_date` | FINAL.csv | Yes |
| `co_date` | FINAL.csv | Yes |
| `correction_events[]` | permit_events | Yes |

### Query for Merged Timeline

```sql
CREATE VIEW project_timeline AS
SELECT
    p.id AS project_id,
    p.address_display AS address,
    p.net_units AS units,
    'sfyimby' AS source,
    s.date_parsed AS event_date,
    'FIRST_MENTION' AS stage
FROM housing_projects_FINAL p
JOIN sfyimby_projects s ON s.matched_project_id = p.id

UNION ALL

SELECT
    p.id AS project_id,
    p.address_display AS address,
    p.net_units AS units,
    'permit_events' AS source,
    e.event_date,
    CASE
        WHEN e.event_type LIKE '%Correction%' THEN 'CORRECTIONS'
        WHEN e.event_type LIKE '%Entitled%' THEN 'ENTITLED'
        -- ... more mappings
    END AS stage
FROM housing_projects_FINAL p
JOIN permit_events e ON e.project_id = p.id

ORDER BY project_id, event_date;
```

---

## Why This Matters

The current pipeline view (163 projects in various stages) is a **snapshot**. This visualization shows the **movie** — how Berkeley's housing pipeline actually moves through time.

It answers questions that static data cannot:
- Which projects get stuck? Where? For how long?
- Do certain developers navigate faster?
- Has processing improved or worsened since 2020?
- What happens after SB35/density bonus law changes?
- How many correction cycles does a typical project endure?

**The 164 threads flowing through time tell the story of Berkeley's housing crisis — or its solution — in motion.**

---

*Specification created: March 31, 2026*
*Data sources: sfyimby_projects (249 entries), permit_events (2,294 events), FINAL.csv (164 projects)*
