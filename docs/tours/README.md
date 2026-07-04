# Tour KMLs

Tour files animate camera paths over the Berkeley housing skyline. Open
alongside `docs/berkeley_skyline.kml` so the extruded buildings render
during flight.

Tours are recorded as videos for the public website. They serve as a
visual companion to the project database — turning what a static map
shows (where projects are) into something a viewer can experience
(their scale, their relationship to neighborhoods, the corridor patterns
that emerge).

## File organization

| Location | Purpose | Tracked by git? |
|----------|---------|-----------------|
| `docs/tours/*.kml` | Tour definition files (this directory) | Yes |
| `data/raw/tour_video/*.m4v` | Uncompressed source recordings from GEP | No (gitignored) |
| `docs/videos/*.mp4` | Compressed videos served on the public website | Yes |

## Naming convention

`tour-{corridor}-{direction}-{variant}.kml`

- **corridor** — lowercase, hyphenated. Examples: `shattuck`, `bancroft`,
  `university`, `adeline`, `telegraph`, `san-pablo`. Multi-corridor tours
  join with `+` (e.g., `adeline+shattuck`, `elmwood+college+bancroft+shattuck`)
  or use a route name (e.g., `downtown-loop`, `campanile-to-shattuck`).
- **direction** — `s2n`, `n2s`, `e2w`, `w2e`, `loop`, `pan`.
- **variant** (optional) — single word. Reserved vocabulary:
  - `slow`, `fast` — pace
  - `low`, `high` — altitude
  - `dawn`, `dusk` — Google Earth lighting
  - `narrate` — long pauses for voiceover
  - `draft` — preview, not for publication
  - `v2`, `v3` — iteration on same route/pace/altitude

Date is metadata in the tour's `<description>`, not the filename. Filenames
stay stable; new content replaces old at the same filename when revising.

Source recording filenames in `data/raw/tour_video/` may include their
capture date as a suffix (e.g., `tour-foo-s2n-2026-05-05.m4v`) since
recordings are physical artifacts tied to a specific capture session,
unlike the KML which represents the tour itself.

Compressed deployed videos in `docs/videos/` use the same name as their
KML, with `.mp4` extension (e.g., `tour-foo-s2n.mp4`).

## Theme tours (no corridor)

Some tours showcase a project category rather than a route:
- `tour-uc-projects-tour.kml`
- `tour-completed-tour.kml`
- `tour-stalled-tour.kml`

These are useful when the journalism subject is "all projects matching X"
rather than "everything along corridor Y."

## Workflow

### 0. Regenerating an old tour with current geometry

Tours are CAMERA-ONLY (no buildings inside); a recorded video shows whatever
geometry was loaded at record time — which is why older videos show outdated
skylines. To re-record any tour against the current hand-edited footprints:

```bash
python scripts/build_tour_package.py docs/tours/<tour>.kml   # or --all
```

This emits `docs/tours/packages/<tour>__geom-<sha>.kml` — ONE self-contained
file: the canonical geometry (`docs/geometry.kml`) + the tour's camera path,
with the geometry source/sha stamped inside. Open the package in Google Earth
Pro, play, record (steps 2–5 below). Packages are DERIVED — hand-edit
footprints only in `docs/geometry.kml`, then regenerate.

### 1. Draft the tour

Two paths:

**A. Describe in natural language, generate KML.** Useful for
precisely-controlled tours. The author specifies start position,
headings, altitudes, durations, and waypoints. A KML is generated
with `<gx:Tour>` and `<gx:FlyTo>` elements.

**B. Record interactively in Google Earth Pro.** GEP's Tour menu
(View → Tour) provides a record button. The author flies through the
tour with the mouse + arrow keys. GEP captures the trajectory and saves
it as KML. This produces less precise tours but captures real
"what feels right when flying" intuition.

The two approaches can be combined: record an interactive draft, then
refine specific timing, headings, or altitudes in the KML.

### 2. Test in Google Earth Pro

1. **File → Open** the KML file
2. The tour appears in Places sidebar under "Temporary Places"
3. Click the tour name to select
4. Use the play controls in the Places panel or the main viewport
5. Iterate on the KML and reload (delete the old tour from Places first
   to avoid duplicates)

### 3. Record the playback

Use one of:

- **GEP's Movie Maker** (Tools → Movie Maker) — built-in, decent quality,
  occasional crashes on long tours
- **OBS Studio** — free third-party, more reliable, supports separate
  audio tracks
- **QuickTime screen recording** — simplest, lowest quality

Recommended capture settings for documentary-quality output:
- Resolution: 1920×1080 minimum
- Frame rate: 30fps for web, 60fps for filmmaker source material
- Audio: separate track if narrating, otherwise none

Save to `data/raw/tour_video/<tour-name>-<date>.m4v` (or `.mov`).

### 4. Compress for the web

Compressed deployment files use H.264 at approximately 4Mbps via two-pass
encoding:

```bash
# First pass — analyzes the source
ffmpeg -y -i <source> -c:v libx264 -b:v 4000k -pass 1 -an \
  -f mp4 -r 30 -movflags +faststart -pix_fmt yuv420p /dev/null

# Second pass — produces the output
ffmpeg -y -i <source> -c:v libx264 -b:v 4000k -pass 2 -an \
  -f mp4 -r 30 -movflags +faststart -pix_fmt yuv420p \
  <destination>.mp4
```

Target output size: 40-80MB for a 1-2 minute tour. Adjust bitrate
downward if file size is too large.

A planned `scripts/compress_tour_video.sh` will standardize this step.

### 5. Deploy to the website

1. Place the compressed mp4 at `docs/videos/<tour-name>.mp4`
2. Update `docs/index.html` to reference the new file
3. Commit to dev branch
4. Merge dev → main (the public site publishes from main)
5. Push origin main
6. Verify after Cloudflare cache propagation (typically 5-30 minutes)

## Tour types — examples

The same tour-definition pattern supports a wide range of journalism use
cases. A tour generator (planned, not yet built) will allow tours to be
specified by structured queries against the project database rather than
hand-authored KML.

### Geographic corridor tours (current pattern)

Direct hand-authored tours along a defined route. Examples:

- `tour-elmwood+college+bancroft+shattuck-s2n.kml` — 50m above the
  Elmwood Theater, north along College Ave to Bancroft, west to Shattuck.
  ~48 second tour.
- `tour-adeline+shattuck-s2n.kml` — Campanile-anchored view following
  the corridor south to north.

### Database-driven tours (future)

Once the v2 schema migration completes and structured tour generation is
built, tours can be specified by SQL queries against the project database.
Each query returns an ordered list of projects that the tour visits in
sequence.

**Example: All projects by a single architect.**

```sql
SELECT p.canonical_address, p.latitude, p.longitude
FROM projects p
JOIN project_participants pp ON pp.project_id = p.id
JOIN organizations o ON o.id = pp.organization_id
JOIN vocabulary_role_types rt ON rt.id = pp.role_type_id
WHERE o.canonical_name = 'Studio KDA'
  AND rt.code = 'architect'
ORDER BY p.canonical_address;
```

Generated tour: `tour-studio-kda-portfolio-pan.kml`. 30 seconds at each
of the firm's projects with brief altitude lift between them. Useful for
stories like "What does this firm's Berkeley portfolio look like?"

**Example: All projects by a single developer.**

Same pattern with `rt.code = 'developer'` and the developer's name. File
naming follows: `tour-{developer-slug}-portfolio-pan.kml`.

**Example: All projects above 100 units, ordered by size.**

```sql
SELECT canonical_address, latitude, longitude, total_units
FROM v_projects_current_flat
WHERE total_units >= 100
ORDER BY total_units DESC;
```

File naming: `tour-100plus-by-size-pan.kml`. Camera altitude scales with
project size — a 500-unit project gets a higher pull-back than a 120-unit
project. Visual aggregation that's hard to convey in a table.

**Example: Pipeline by stage of completion.**

A tour visiting projects in five clusters: Pre-Application → Approved →
Permitted → Under Construction → Completed. Each cluster gets a brief
title card and 5-10 second visit per project. File naming:
`tour-pipeline-by-stage-pan.kml`. This becomes a "state of the pipeline"
video updated quarterly or annually.

## Tours as continuous policy audit

Database-driven tours serve a function beyond journalism. As the project
database grows and v2's structured data captures the full lifecycle of
each project — application, entitlement, permitting, construction,
completion — tours can become a regularly-updated public audit of housing
policy outcomes.

### Three audiences

**Planning staff and the Planning Commission.** Each Planning Commission
decision is one project at a time: a Use Permit here, a Design Review
there. The cumulative effect of these individual decisions is hard to see
in agenda packets. A tour of "all projects entitled in 2020" — flown
five years later — shows which were built, which stalled, and what the
entitlement-to-construction gap looks like in physical Berkeley.

This is direct feedback on past decisions. It also informs current ones:
a Commissioner reviewing today's agenda can ask "what happened to similar
projects we approved before?" and answer the question with a flyby
rather than another spreadsheet.

**Elected officials and policy advocates.** When City Council passes
housing legislation — a zoning change, a density bonus, a fee waiver —
the legislation typically asserts a theory of change ("this will produce
X kinds of housing in Y locations"). Tours produced years later test
that theory visually. Projects approved under SB330, AB2011, or local
zoning amendments can be tracked as cohorts and the actual built
outcomes compared against the policy's stated goals.

**The public.** Residents who attend Planning Commission meetings, write
letters to City Council, or vote on housing-related ballot measures
rarely see the cumulative physical result of years of policy decisions.
A regularly-updated tour ("State of the Berkeley Housing Pipeline,
Q3 2026") makes the abstract debate concrete.

### Examples

- `tour-entitled-2020-followup-pan.kml` — All projects entitled in
  calendar year 2020. Flown in 2026, this tour shows the six-year
  outcome distribution: completed, under construction, permitted but
  stalled, abandoned. Each project's current status displayed alongside
  its 2020 entitlement record.

- `tour-sb330-projects-pan.kml` — All projects filed under SB330
  preliminary application protections. Useful for tracking whether the
  state's housing acceleration laws produced their intended effects in
  Berkeley.

- `tour-density-bonus-projects-pan.kml` — All projects using state or
  local density bonuses. Visualizes which sites the policy mechanism
  actually reaches and what gets built.

- `tour-rhna-cycle-pan.kml` — All projects counted toward the current
  RHNA (Regional Housing Needs Allocation) cycle. Updated as RHNA
  accounting changes through the cycle's eight-year span.

### Update cadence

Database-driven tours are inherently regenerable. The tour KML is
produced from the current database state. As project records update —
new permits issued, status changes, completions reported — the same
tour query produces a fresh KML.

A standard production cadence:

- **Weekly or monthly:** Pipeline-state tours that reflect current
  entitlement and permit status. These can be auto-regenerated from
  pipelines that already update the database.
- **Quarterly:** "State of the pipeline" composite tours intended for
  public presentation.
- **Annually:** APR-aligned tours produced when the city's APR is filed,
  serving as visual companion to the table-form report.
- **Multi-year:** Cohort follow-up tours like the "entitled-2020-followup"
  example, produced at three-year and five-year marks after the cohort
  date.

This cadence transforms what is currently a one-time act (writing an
APR table) into a sustained public audit relationship between policy
and outcome.

## APR Visual Validation

The HCD Annual Progress Report (APR) is a state-mandated yearly filing
where Berkeley reports housing pipeline status. Tables A and A2 of the
APR contain hundreds of project-level rows with dates: entitlement date,
building permit issuance, completion. The tables are large, dense, and
error-prone — duplicate entries and incorrect dates are common.

A flyby tour built from APR data offers a different kind of audit. Each
project becomes a visual stop. The viewer sees the building's actual
geometry, location, and apparent stage. Errors that hide in a spreadsheet
— a project listed twice, a "completed" project that has no building, a
date that puts entitlement after construction — become immediately
apparent in flight.

**Five APR-derived tours to consider:**

- `tour-apr-by-application-year-pan.kml` — visits projects in order of
  when planning applications were submitted. Useful for spotting "this
  project has been in the pipeline for 8 years" stories.

- `tour-apr-by-entitlement-year-pan.kml` — visits projects in order of
  Use Permit / Design Review approval. Reveals the entitlement-to-
  construction gap visually.

- `tour-apr-by-building-permit-year-pan.kml` — visits projects when
  their building permits were issued. Distinguishes "permitted but not
  started" from "permitted and built."

- `tour-apr-by-demolition-permit-year-pan.kml` — visits projects where
  existing structures were demolished. Often the first physical step
  after entitlement.

- `tour-apr-by-completion-year-pan.kml` — visits projects in order of
  when construction was finaled. The "what actually got built" tour.

These five together visualize the temporal journey from application to
occupancy. Anomalies surface naturally:

- A project whose "completion" entry is in the APR but whose footprint
  is still parking surfaces
- Two projects with the same address but different IDs (the duplicate-
  row problem)
- A "completed" date that precedes the building permit (data entry error)
- Projects that vanish from one year's APR and reappear the next (RHNA
  accounting concerns)

The methodology is: **walk the APR, watch the buildings.** Patterns
visible from the air should match patterns reported in the table. Where
they don't, there's a story.

## Coordinate reference

Berkeley intersections used in tours so far:

| Location | Latitude | Longitude |
|----------|----------|-----------|
| Elmwood Theater (College & Ashby area) | 37.85633 | -122.25299 |
| College & Bancroft | 37.86930 | -122.25400 |
| Shattuck & Bancroft | 37.86940 | -122.26800 |
| Adeline & Ashby | 37.85490 | -122.26830 |
| Campanile | 37.87217 | -122.25767 |

This reference table grows as more tours are built. A future tour
generator will read named locations from a structured file.

## Tours index

See `scripts/list_tours.py` for an auto-generated index (TODO).

## See also

- `data/raw/tour_video/` — source recordings (gitignored)
- `docs/videos/` — deployed compressed videos
- `docs/index.html` — webpage that embeds the deployed videos
- `scripts/compress_tour_video.sh` — standardized compression (planned)
