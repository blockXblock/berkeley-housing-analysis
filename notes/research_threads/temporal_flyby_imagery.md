# Research thread: temporal flyby imagery

**Status**: Concept stage. Schema designed, not yet implemented.
**Drafted**: 2026-05-24
**Related**:
- `notes/2026-05-24_data_trust_history.md` (the worked example explaining why this thread deserves a deliberate schema)
- `notes/research_threads/modular_construction.md` (one of the tour themes this enables)

## Goal

Build a KML tour generation system that takes a fixed sequence of Berkeley housing project sites and renders multiple tours over that sequence, each tour displaying different imagery layers per site. The data shape is the same; the imagery selection differs by tour theme.

## Tour themes (initial set)

- **Time-lapse**: same sites, imagery from Google Earth Historical at intervals (2010, 2015, 2020, 2025, today). Shows neighborhood change.
- **Design-vs-reality**: same sites, architect's rendering paired with current built reality. Shows what got built vs what was proposed.
- **Permitting-lifecycle**: per site, walk through pre-existing structure → demolition photo → construction phase → CO. Shows the full project arc.
- **Modular-construction**: subset of sites where prefab/modular was used. Highlights module-arrival, lift, and assembly. Connects to the modular research thread.
- **Regional comparison**: same project type across Berkeley, Oakland, Albany. Shows how different jurisdictions handle similar projects.
- **Civic-controversy**: sites that drew significant public comment, with imagery juxtaposing the rendering vs the final built form, and text from public comments or ZAB hearings.

The list is open. Each new theme is a new filter on the same data, not a new database structure.

## Data needs

The concept requires imagery to be:

1. **Tied to project_id** (joinable to existing data)
2. **Tagged with date_observed** (the date the imagery was captured, not when it was cataloged)
3. **Tagged with source_type** (vocabulary: historical_aerial, architect_rendering, construction_photo, etc.)
4. **Provenanced** (where each asset came from — permit attachment, Google Earth Historical, drone, etc.)
5. **Geographically positionable in KML** (anchor point, viewing angle, altitude — for image overlays in 3D Earth space)

None of this exists in the current schema. Polygon geometry is in `project_geometries`. Permit documents are in `documents`. Neither serves the imagery-tied-to-time-and-project use case.

## Proposed schema addition

A new table `project_visual_assets` with provenance mixin:

```sql
CREATE TABLE project_visual_assets (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    source_type_id INTEGER NOT NULL REFERENCES vocabulary_visual_asset_types(id),
    date_observed TEXT,           -- YYYY-MM-DD when the imagery was captured
    file_path TEXT,               -- local path or empty if url-only
    url TEXT,                     -- canonical URL (R2, IA, Drive, etc.)
    geometry_hint TEXT,           -- JSON: {anchor: [lat, lon], altitude, viewing_angle}
    width_px INTEGER,
    height_px INTEGER,
    provenance_permit_id INTEGER REFERENCES permits(id),  -- if extracted from a permit
    provenance_source_url TEXT,   -- if scraped from external source
    provenance_captured_by TEXT,  -- if drone or fieldwork
    notes TEXT,
    -- provenance mixin (matches v2 convention)
    source_document_id INTEGER REFERENCES documents(id),
    asserted_by TEXT,
    asserted_at TEXT,
    confidence_type_id INTEGER REFERENCES vocabulary_confidence_types(id)
);

CREATE INDEX idx_pva_project ON project_visual_assets(project_id);
CREATE INDEX idx_pva_source_type ON project_visual_assets(source_type_id);
CREATE INDEX idx_pva_date ON project_visual_assets(date_observed);
```

Vocabulary table `vocabulary_visual_asset_types` seeded with at least: `historical_aerial`, `current_aerial`, `architect_rendering`, `construction_photo`, `drone_capture`, `permit_application_rendering`, `street_view`, `modular_module_lift`, `before_demolition`, `during_construction`, `finished_building`, `public_comment_image`.

## Tour generator architecture

A single Python module that takes:

- A sequence of project_ids (the tour stops)
- A theme name (which maps to one or more source_type values)
- Optional date range (for time-lapse tours)
- Optional KML output path

And produces a KML file with one image overlay per project_id, where the overlay's imagery is the most-recent asset of the requested source_type within the date range. If no asset matches, the project is either skipped or shown with a placeholder, configurable.

The generator runs are themselves logged — each KML file produced has an associated record in a `tour_runs` table (or similar) capturing: which sequence, which theme, which date range, which assets were selected per project, when the run happened. Reproducibility is the goal.

## Initial population sources

In priority order:

1. **Architect renderings from existing Accela permit attachments.** Many permits have application packages with renderings as PDF pages. Extract page-as-image, tag with permit_id provenance, source_type='permit_application_rendering' or 'architect_rendering'.

2. **Current and historical aerials from Google Earth Historical.** Berkeley has good imagery coverage going back ~2002. Capture for each project's coordinates at 5-year intervals.

3. **Construction photos from public sources.** SFYIMBY, blockxblock, developer websites (Panoramic, etc.) often have construction-phase photos. Backfill as time permits.

4. **Drone captures** (if any exist or get commissioned).

## Connections to other workstreams

- **Modular construction research**: tour theme "modular-construction" is one of the highest-value initial tours. Synergy Modular's lift events for 1598 University would be a great example — if photos exist or can be commissioned.
- **APR cross-check**: design-vs-reality tour at Berkeley scale could reveal which projects got built as proposed vs which got redesigned. The 2556 Telegraph case (76 units entitled → 22 BP'd → 22 CO'd) is exactly this kind of story.
- **Civic-tech publishing**: each tour is a publishable artifact for the YouTube channel (@BuildBerkeley2050), the TILBlog, or the berkeleybuild.com site.

## What's not in scope yet

- Real-time tour rendering (these are pre-rendered KML files, not interactive)
- Audio narration (could come later via the MacWhisper / NotebookLM pipeline already established)
- Per-tour query interface (initially the tours are hand-curated sequences; later a query interface could generate sequences from filters)

## Next steps

This is a research thread, not an active workstream. Activation order would be:

1. Schema addition committed (one migration, no data yet)
2. First population pass: architect renderings from existing permits in `documents` table (read-only against v2)
3. First tour generation: design-vs-reality for the 5 named CY 2025 CO projects we've been verifying
4. Evaluate the result, refine the schema if needed
5. Backfill historical aerials for top 50 projects
6. Second tour theme: time-lapse
7. Open the workstream to additional themes

Steps 1-3 are probably a half-day each. Don't rush; this is the kind of work where doing it right matters more than doing it fast.

## Why this thread is captured separately from the modular thread

The modular construction thread is about *what gets built* — a research question. The temporal flyby thread is about *how we show what gets built* — a methodology question. They overlap in the modular-construction tour theme but they're not the same workstream. Keeping them separate prevents schema bloat (we'd be tempted to add modular-specific columns to a flyby-specific table or vice versa).

## Connection to the data-trust posture

This thread is an explicit test case for the "visualizations are first-class schema drivers, with deliberate commitment" principle documented in `notes/2026-05-24_data_trust_history.md` (Implication 5). The temporal-flyby concept is new enough that we can implement it correctly from the start — proper schema first, vocabulary seeded, then population, then generation. No ad-hoc columns on the `projects` table.

If this thread succeeds in its discipline, future visualization concepts can follow the same pattern. If it fails (e.g., we cave and add a `rendering_url` column to `projects` because it's "just one column"), that's a signal to revisit the discipline.
