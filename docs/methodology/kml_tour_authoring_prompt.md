# Prompt: KML Tour Authoring for berkeleybuild.com

**Purpose:** Start a fresh Claude chat focused on authoring Google Earth
KML tours for the Berkeley Housing Pipeline (berkeleybuild.com). This
prompt encodes the conventions, constraints, and patterns developed
through earlier sessions so a new chat can produce working tours
without re-deriving them.

**Save location:** `docs/methodology/kml_tour_authoring_prompt.md`

**Last updated:** 2026-05-14

---

## How to use this prompt

Copy everything from "BEGIN PROMPT" to "END PROMPT" below. Paste it as
the FIRST MESSAGE in a new Claude chat. Then describe the tour you
want.

---

## BEGIN PROMPT

I'm John Gage, working on the Berkeley Housing Pipeline at
berkeleybuild.com. I need help authoring Google Earth KML tours that
showcase Berkeley housing projects. Each tour gets recorded in Google
Earth Pro Movie Maker, uploaded to YouTube
(@BuildBerkeley2050), and embedded on the website.

### My toolchain

- **Building geometry:** `~/berkeley-data/docs/kml_versions/Geometry-2026-05-14-a.kml`
  (183 polygons with extruded heights, hand-corrected; this is loaded
  alongside the tour KML in Google Earth)
- **Project data:** `~/berkeley-data/databases/berkeley_housing_v2.db`
  (181 projects, addresses, heights, stages, units)
- **Google Earth Pro** on macOS for previewing and recording
- **Claude Code (CC)** in terminal for file operations
- **This Claude chat** for designing tour XML

### My workflow with Claude

1. I describe the tour I want (route, behavior at each stop, final shot)
2. You draft the complete `<gx:Tour>` KML XML and save it as a file in
   `/mnt/user-data/outputs/` so I can download it
3. I download to `~/Downloads/`, then move to `~/berkeley-data/docs/kml_versions/`
4. I open both KMLs in Google Earth, preview the tour, report back
5. We iterate on specific aspects (camera tilt, orbit radius, durations)
6. Once approved, I record with Movie Maker, upload, embed

### Technical conventions developed across sessions

**Coordinate offsets at Berkeley latitude (~37.87 N):**
- 100m N or S = 0.000901 degrees latitude
- 100m E or W = 0.001140 degrees longitude
- 200m N or S = 0.001802 degrees latitude
- 200m E or W = 0.002280 degrees longitude

Note: "moving east" in the western hemisphere means making the
negative longitude LESS negative (closer to zero). Example: from
-122.2546260, moving 100m east gives -122.2534860.

**Camera approach pattern (default):**
- Approach each building from 200m east, looking west (heading 270)
- Camera altitude: building height + ~50m (gives comfortable framing
  with building centered, sky above, ground below)
- Tilt: 70 degrees (camera looks 20 degrees down from horizontal)
- flyToMode: smooth

**Orbit pattern (default):**
- Camera moves around building at constant radius (typically 200m)
- 4 segments per full 360 orbit (E -> S -> W -> N -> E)
- Each segment lasts 2.5s for a 10s orbit (or 1.5s for 6s orbit)
- Heading rotates 90 degrees per segment, always pointing back at building center
- Building stays roughly centered in frame throughout

**Common segment durations:**
- Inter-stop flight: 5s
- Orbit: 10s total (4 x 2.5s) for slower, cinematic feel
- Inter-stop pause: 2s
- Establishing shot hold: 3s
- Final hold: 3s

**Final shot conventions:**
- Often pulls up 200ft (~61m) for a wide view
- May tilt to 75-85 degrees for panoramic feel
- May move further east (e.g., 300m total) for wider pull-back

### Known building coordinates (from v2.db and KML, verified 2026-05-14)

Use these centroid values as orbit centers. Heights are extrusion
heights from the KML (already correct in Geometry-2026-05-14-a.kml).

| Project | Address | Centroid (lon, lat) | Height |
|---------|---------|---------------------|-------:|
| 170 | 1950 OXFORD St | -122.2665495, 37.8728161 | 46.9m |
| 165 | 2200 BANCROFT Way | -122.2655379, 37.8675063 | 77.1m |
| 177 | 2556 HASTE St (North main) | -122.2573102, 37.8660373 | 40.2m |
| 177 | 2556 HASTE St (South wing) | -122.2569341, 37.8656472 | (lower) |
| 171 | 2400 BOWDITCH St (North tower) | -122.2569060, 37.8669718 | 85.3m |
| 171 | 2400 BOWDITCH St (South wing) | -122.2567394, 37.8665759 | 45.0m |

**Reference landmark not in KML:**
- Sather Tower (Campanile): -122.2578, 37.8723 (approximate)

To find OTHER project coordinates not listed above, I can run SQL on
v2.db or grep the KML.

### Stylistic principles I care about

1. **Camera should show the BUILDING, not look down past it.** Earlier
   drafts placed camera directly above buildings, which meant the
   building wasn't in frame. Always offset camera horizontally from the
   building so the building is what's framed.

2. **Smooth transitions, not stepped jumps.** Use `<gx:flyToMode>smooth</gx:flyToMode>`
   for all FlyTo elements. If a 4-segment orbit feels stepped, increase
   to 8 segments.

3. **Cinematic pacing, not frantic.** Better to hold a shot 2-3 seconds
   longer than to rush through it. Total tour 50-90s is the sweet spot
   for YouTube viewing.

4. **Heights matter for realism.** Camera altitude needs to relate to
   building height. Camera at 95m AGL viewing a 46m building is at
   roughly twice the building height — gives a sense of scale. Camera
   at 1000m AGL viewing same building loses all scale.

### KML structure I use

```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
     xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
  <name>Tour name</name>
  <description>Multi-line description of what the tour shows.</description>
  <gx:Tour>
    <name>Tour name</name>
    <gx:Playlist>
      <!-- Establishing shot -->
      <gx:FlyTo>
        <gx:duration>0</gx:duration>
        <gx:flyToMode>smooth</gx:flyToMode>
        <Camera>
          <longitude>X</longitude>
          <latitude>Y</latitude>
          <altitude>Z</altitude>
          <heading>270</heading>
          <tilt>75</tilt>
          <altitudeMode>relativeToGround</altitudeMode>
        </Camera>
      </gx:FlyTo>
      <gx:Wait><gx:duration>3</gx:duration></gx:Wait>
      <!-- ... more FlyTo and Wait elements ... -->
    </gx:Playlist>
  </gx:Tour>
</Document>
</kml>
```

### What I want you to do

When I describe a tour, draft the complete `<gx:Tour>` KML following
the conventions above. Save the result to `/mnt/user-data/outputs/`
with a filename like `[tour_theme]_tour_YYYY-MM-DD.kml`.

If I describe an iteration (e.g., "make the orbit slower" or "open
from a different angle"), rewrite the relevant sections cleanly. Don't
just describe the changes; produce the full updated KML.

Be honest about tradeoffs:
- If a request would produce a bad shot (e.g., camera directly above
  building), say so and suggest a better approach.
- If I ask for something ambiguous, ask one clarifying question rather
  than guessing.
- If I say "shorter" but don't specify how short, ask whether I mean
  total runtime, per-stop duration, or orbit speed.

### Things I do NOT need help with in this chat

- Recording the tour (I do that in GE Movie Maker)
- Uploading to YouTube (I do that manually)
- Editing the geometry KML (handled in a different workflow)
- Database queries (handled by Claude Code separately)
- Web HTML edits (handled in a different chat session)

This chat is ONLY for drafting and iterating on tour KML XML.

### Starting point

I want to create a [DESCRIBE TOUR HERE — route, stops, behaviors, etc.]

## END PROMPT

---

## Why this prompt exists

Earlier sessions spent significant time re-deriving:
- Coordinate offsets at Berkeley's latitude
- That east-hemisphere longitude math goes the "wrong" intuitive direction
- That camera centered on a building doesn't show the building
- Reasonable durations for orbits and pauses
- The general structure of `<gx:Tour>` XML

This prompt captures those lessons so future tours can be authored in
minutes instead of hours of trial-and-error.

## Maintenance

When new conventions emerge (different orbit patterns, new camera
techniques, etc.), update this prompt. The next chat that uses it
benefits.

When new building coordinates are needed (new projects, new
polygons), add to the building inventory table above.

Consider versioning this prompt (kml_tour_authoring_prompt_v2.md)
if significant changes accumulate, so older chats that referenced an
earlier version remain reproducible.
