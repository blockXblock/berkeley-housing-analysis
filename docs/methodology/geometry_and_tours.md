# Correcting the map, and naming the tours

How to change what the buildings look like, and how a change reaches a recorded video.
Written 2026-09-02. Everything here was verified against the repo, not remembered.

## 1. There is exactly one canonical geometry file

    kml/geometry/geometry.kml

Everything else is derived from it:

| file | what it is | edit it? |
|---|---|---|
| `kml/geometry/geometry.kml` | **the canonical map.** 197 polygons | **YES — this is the one** |
| `docs/geometry.kml` | republished copy, the public "Open in Google Earth" download | no — regenerated |
| `kml/tours/packages/*.kml` / `.kmz` | a tour **plus a spliced copy** of the geometry | no — derived |
| `kml/geometry/versions/*` | history and control points | no — archive |

A package is a tour and the map welded together so that **one file loads in Earth and is ready
to record**. That is why there are 68 of them for 41 tours: each tour gets a `.kml` (needs the
icon file beside it) and a `.kmz` (self-contained). They are cheap and disposable — delete the
lot and `--all` rebuilds them.

## 2. To correct a building

1. **Edit `kml/geometry/geometry.kml`.** A building is one `<Placemark>` with a `<Polygon>`.
   The `<coordinates>` are `lon,lat,height` triples; the height on every vertex is the roof, and
   `<extrude>1</extrude>` pulls it down to the ground.
2. **Give it a balloon address** — `<description><![CDATA[<b>2200 BANCROFT Way</b><br/>...]]>`.
   This is not decoration: `gen_building_loop.buildings()` groups a SITE on that bold address,
   and a polygon without one is invisible to every tour generator. Two UC wings were missing
   theirs and were silently dropped from their own sites.
3. **Re-stamp and rebuild:**

       python3 scripts/build_tour_package.py --all

   That calls `stamp_geometry.py` (updating the document name and content sha), re-splices all
   68 packages, renames them to the new sha, **prunes the previous generation**, repoints
   `docs/tours.json`, and republishes `docs/geometry.kml`.

4. **Check it took:**

       python3 scripts/svg_label_tour.py --tour <stem> --street <street> --all --max-labels 5

## 3. Label TEXT comes from the database, not the KML

Do not hand-edit units or status in a placemark name. `scripts/sync_status_from_v2.py` writes
them from `v_projects_flat`, and the next run will overwrite anything typed by hand.

- wrong unit count or status → fix it in **v2**, then run `sync_status_from_v2.py`
- wrong address, shape or height → fix it in **geometry.kml**
- UC projects are counted in **beds**, private in **units** — the sync knows the difference

The boxed SVG labels are separate again: `gen_svg_labels.py` renders a PNG per building from v2
(address, units/beds, status, storeys, height, floor area, architect, developer, owner) and
`svg_label_tour.py` splices them into a tour. Delete `scratch/.../svg-labels/` to force a
re-render after a data change — it caches by filename.

## 4. How to tell if a package is out of date

    python3 -c "import sys; sys.path.insert(0,'scripts'); from stamp_geometry import geometry_sha; print(geometry_sha())"
    ls kml/tours/packages/ | grep -oE 'geom-[0-9a-f]{12}' | sort -u

If those disagree, every package is stale and `--all` fixes it. **This happened on 2026-09-02**:
2526 Durant Ave was added to the canonical, so the canonical read `geom-a3d103322890` while all
68 packages still read `geom-3b3f51826e15` — every one of them missing that building.

The sha is a hash of the geometry's CONTENT with the stamped date excluded, so it moves when a
building moves and not when the clock does.

## 5. Naming

    <corridor>-<direction>[-cruise]

- **corridor** — lowercase, hyphenated: `shattuck`, `san-pablo`, `uc-dormitories`, `private-200`
- **direction** — `s2n`, `n2s`, `w2e`, `e2w`. **A direction is not a duplicate.** `bancroft-w2e`
  and `bancroft-e2w` are different films: the light, the skyline and the reveal all differ.
  Omit for tours that are not linear (`uc-dormitories`, `private-200`).
- **`-cruise`** — the same path with no orbits. The orbit version carries no suffix.

Non-conforming names as of today, and what they should be:

| current | should be | why |
|---|---|---|
| `shattuck-s2n-path` | `shattuck-s2n` | "-path" means nothing; its cruise twin is already `shattuck-s2n-cruise` |
| `Shattuck-centerline-flight-with-2190-and-2276-orbits` | retire | superseded by `shattuck-s2n` |
| `uc_dormitory_tour_2026-05-14 (4)` | retire | superseded by `uc-dormitories`; spaces and parens in a filename |
| `tour-private-pipeline-over-200-units-2026-05-16` | retire | superseded by `private-200`, which derives its set from v2 |
| `tour-private-pipeline-over-200-units-slow` | retire | ditto |
| `longerv2`, `berkeley-tour-extended-dramatic` | retire |名 says nothing; both under 1.5 min |
| `university-880-uc` | `university-w2e` … but that name is TAKEN | two different University tours exist; needs John's call on which survives |

Renaming is not free: the stem is the catalog id, the package filename and the argument to
`publish_video.py`. Rename in one pass or not at all.

## 6. The exception

`kml/tours/panoramic-kennedy-legacy.kml` (Patrick Kennedy / Panoramic Interests, 1990→2028)
carries **its own 23 polygons** rather than using the canonical geometry. Running the packager on
it would add 196 more on top. It needs either converting to canonical geometry or an explicit
exemption — do not put it through the standard pipeline. It was deleted on 2026-08-01 as a
"stray legacy KML dupe" and recovered from git on 2026-09-02.
