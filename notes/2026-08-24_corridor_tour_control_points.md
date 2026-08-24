# Corridor flyover tours — control points, and how to correct them

**For John.** Three new tours: **A San Pablo N→S · B Adeline N→S · C Telegraph S→N**, each
orbiting its largest towers once. Standard cruise **20 m**; tower orbits at **roof height + 10 m**.

---

## How the workflow actually works (recovered from the Shattuck flight)

The Shattuck N→S tour was **not** generated from a road dataset. It was interpolated between
**four hand-placed control points** you set in Google Earth Pro and exported as
`Shattuck Control Points.kml`:

| point | coordinate |
|---|---|
| `N-Shattuck-North` | -122.2695303310, 37.8820504394 |
| `N-Shattuck-South` | -122.2682361111, 37.8706472222 |
| `S-Shattuck-North` | -122.2680956222, 37.8703355190 |
| `S-Shattuck-South` | -122.2661377085, 37.8523733449 |

Confirmed by measurement: the tour's **first camera matches control point #1 to ten decimal
places**, and **86 of its 112 waypoints sit within 25 m** of a control-point segment (median
offset **4.9 m**). The other 26 waypoints are the two tower orbits leaving the centreline.
Four points rather than two because **Shattuck jogs at ~37.870** — it is two straight runs.

**Consequence: we need no road data at all.** Your eye on real imagery beats any centreline
dataset, and **more control points = more fidelity** on a curving street.

---

## What I generated

`scripts/gen_tour_control_points.py` → `kml/tours/control_points/`

| corridor | points | span | housing along it |
|---|---|---|---|
| **San Pablo** | 8 | 2.90 mi | 18 projects / 1,473 units + 28 ADUs |
| **Adeline** | 6 | 1.40 mi | 3 projects / 118 units + 7 ADUs |
| **Telegraph** | 8 | 1.44 mi | 10 projects / 543 units + 12 ADUs |

Candidates come from **the housing itself**: bin by latitude, take the median longitude of the
buildings in each band. Buildings front the street, so their median longitude tracks the roadway
— approximately, which is why they are candidates. Points named `-ANCHOR` are the **corridor end
points** you specified; they carry no housing behind them and are my rough guess at the Albany
line, the Oakland line, a block north of Shattuck/Adeline, and Bancroft.

---

## How to correct them

**Open** `kml/tours/control_points/<Corridor> Control Points CANDIDATE.kml` in Google Earth Pro.

1. **Drag each pushpin onto the true centreline** of the street. Aim for the middle of the
   roadway; the flight will follow the line between consecutive points.
2. **Add points wherever the street bends.** A straight run needs only its two ends. Telegraph
   bends near Dwight and again approaching the Oakland line; San Pablo is nearly straight;
   Adeline is short and straight. Right-click a folder → *Add → Placemark*.
3. **Fix the anchors first** — they are my weakest guesses. `*-ANCHOR` marks each corridor end.
4. **Delete any point that is plainly wrong** rather than dragging it a long way.
5. **Order is the flight order.** San Pablo and Adeline run N→S, Telegraph runs S→N. Reordering
   the placemarks in the sidebar reorders the flight.
6. **Save over the same file** (*File → Save → Save Place As*), dropping `CANDIDATE` from the
   filename. Tell me it is ready and I will generate the tour.

### If you would rather instruct me than drag
Any of these is enough, no Earth Pro needed:
- *"San Pablo CP03 is a block too far east"* — I will shift it.
- *"add a control point at San Pablo and Gilman"* — I will place it from the intersection.
- *"start Telegraph at Woolsey instead"* — I will move the anchor.
- *"Adeline is too thin, fold it into Shattuck"* — I will merge the corridors.

---

## Orbit targets (roof + 10 m)

| corridor | tower | units | roof | orbit altitude |
|---|---|---|---|---|
| San Pablo | 2601 San Pablo | 223 | 28.0 m | **38.0 m** |
| San Pablo | 2733 San Pablo | 152 | 28.0 m | **38.0 m** |
| Adeline | 3031 Adeline | 64 | 24.5 m | **34.5 m** |
| Telegraph | 3030 Telegraph | 144 | 19.2 m | **29.2 m** |
| Telegraph | 2455 Telegraph | 68 | 28.0 m | **38.0 m** |

Roof heights come from the KML extrusion where one exists. **These move as we correct heights**
— 3030 Telegraph was 35 m until its tabulation put it at 19.2 m — so orbit altitudes are derived
at generation time, never hardcoded. Regenerate the tour after a height correction and the orbit
follows.

---

## Two things worth knowing before recording

**1. The geometry these tours fly past is mostly still wrong.**

| corridor | verified footprints | parcel-shaped |
|---|---|---|
| San Pablo | **0 of 14** | 11 |
| Telegraph | 1 of 8 | 4 |
| Adeline | **0 of 3** | 2 |

At 20 m you are close enough to read individual buildings, so lot-shaped blocks will show. The
harvest session is fetching 1.E forms for San Pablo projects now; corridor geometry should
improve before recording. **Tours are cheap to regenerate — record after the footprints land.**

**2. Adeline is thin.** Three tracked projects and about seven ADUs across 1.4 miles. It will
feel empty next to San Pablo. Worth considering folding it into the Shattuck tour, which it
meets, or accepting it as a deliberate two-minute short.

---

## Converging workflow

Each correction improves every future tour, because nothing is hardcoded: control points are
yours, orbit altitudes derive from current heights, footprints derive from architect tabulations,
and the tour is regenerated from all three. The loop is *correct the data → regenerate → record*,
and it gets better every pass.
