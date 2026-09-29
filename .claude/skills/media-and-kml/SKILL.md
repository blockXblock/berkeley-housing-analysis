---
name: media-and-kml
description: Where berkeley-data's videos and KML live and which are tracked — full-length tour renders (YouTube + T7 masters, untracked) vs short web loops in docs/videos (tracked with git add -f), and kml/ source vs the docs/geometry.kml republished copy. Use when adding, deleting, or moving any .mp4/.m4v/.kml, or regenerating docs/geometry.kml.
---

# Media disposition rule
(Moved from CLAUDE.md 2026-09-29. The two safety rules — never delete a tracked mp4 in
docs/videos/ without grepping docs/index.html; docs/geometry.kml is a republished copy —
also stay in CLAUDE.md.)

- **Two classes of `.mp4`, and the difference is load-bearing:**
  - **FULL-LENGTH tour renders** (minutes long, 200–700 MB) are **NOT tracked** — they live on the
    **YouTube channel feeding berkeleybuild.com**, and the masters stay on
    **`/Volumes/T7-2025/Berkeley-Tours/`** (`New/1-*.m4v` = the current labelled, pushpin-free set,
    rendered 2026-09-07/08). A stray `*.mp4.backup-*` is a stale old-approach artifact → delete.
  - **SHORT web-served loops** (hero/teaser: **≤20 s, ≤5 MB**, silent, `+faststart`) **ARE tracked,
    deliberately**, in `docs/videos/` — the page must serve them itself, so they cannot live on
    YouTube. `*.mp4` is gitignored (`.gitignore:111`), so each one needs an explicit **`git add -f`**
    or it silently fails to deploy. ⚠ **NEVER delete a tracked mp4 in `docs/videos/` as a "stale
    artifact" without grepping `docs/index.html` first** — the live site depends on them. (The old
    blanket rule said every repo-tracked mp4 was stale; that was false and would have deleted two
    served videos. Corrected 2026-09-22.)
  - **Inventory (2026-09-22):** `hero-shattuck-loop.mp4` (2.71 MB, cut from the current
    2026-09-07 Shattuck render — keep) · `campanile-adeline-shattuck.mp4` (69 MB) and
    `tour-elmwood+college+bancroft+shattuck-s2n.mp4` (31 MB), both **`needs_rerecord: true`**,
    pushpin-era, and both **autoplaying below the fold** — retire to YouTube once re-recorded.
- **KML SOURCE lives in `kml/` (repo-root, reorganized 2026-07-22) and IS tracked** —
  **`kml/geometry/`** (building-polygon skyline: canonical `kml/geometry/geometry.kml` +
  `kml/geometry/versions/` history/control-points), **`kml/tours/`** (camera-only tour KMLs),
  **`kml/tours/packages/`** (DERIVED tour+geometry merges from `build_tour_package.py`).
  **`docs/` is the WEB-SERVE target, not KML source:** the ONE public download,
  `docs/geometry.kml`, is a **republished copy** of `kml/geometry/geometry.kml` (regenerate it
  whenever the canonical changes — the homepage "Open KML in Google Earth" button + explorer
  links point at it). `docs/tours.json` (served tour catalog) stays in `docs/`; its content
  now references `kml/` source paths. Raw hand-traced captures stay as provenance in
  `data/raw/google_earth_audit/`. A small asset a KML *references* (e.g. `transparent-1x1.png`)
  is a tracked **input dependency**; an image *rendered from* a KML would be derived → don't track.
