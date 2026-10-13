# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "pandas", "altair", "shapely"]
# ///
"""Berkeley housing by block — a prototype marimo app.

Type a street address to find your block, or browse blocks ranked by housing units.

A BLOCK is a street-bounded city block: the City's own block polygons plus edge blocks closed by the
city limit (scripts/housing_rules/blocks.py), with stable IDs like CB-27b08582. Each address also
carries its STREET SEGMENT ("the 2800 block of Benvenue Ave"), the other sense of "my block".

Reads only published files:
  docs/data/berkeley_housing_public.db   the v4 public database (the Datasette Lite mirror)
  docs/data/blocks/*                     scripts/build_address_block_lookup.py: address and parcel
                                         lookups, block and segment geometry, and a verbatim copy of
                                         the address canon (housing_rules/address.py)
Every number on the page is computed from those files at load time; nothing is typed by hand.

Run locally:        uvx marimo run --sandbox apps/block_units.py
Edit:               uvx marimo edit --sandbox apps/block_units.py
Static web build:   marimo export html-wasm apps/block_units.py -o site/blocks --mode run
                    (in the browser the app fetches the same files from berkeleybuild.com/data/)
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", app_title="Berkeley housing by block")


@app.cell
def _():
    import io
    import json
    import re
    import sqlite3
    import sys
    import tempfile
    import types
    from difflib import get_close_matches
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import pandas as pd
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree

    return (Path, Point, STRtree, alt, get_close_matches, io, json, mo, pd, re, shape,
            sqlite3, sys, tempfile, types)


@app.cell
def _(mo):
    mo.md(r"""
    # Berkeley housing, block by block

    Type your address to find your block, or pick a stage and a time window and click a block on
    the map or in the table to see the projects behind its count. A **block** here is a
    street-bounded city block from the City's own GIS. Along the city limit, where the last row of
    lots is closed off by the Oakland, Albany or Kensington line rather than a street, the block
    ends at the city limit.
    """)
    return


@app.cell
async def _(Path, sys, tempfile):
    # Load the published files: from the repo when run locally, from berkeleybuild.com when the
    # app runs in a browser (WebAssembly), where there is no local filesystem to read.
    SITE = "https://berkeleybuild.com/data/"
    LOCAL = Path(__file__).resolve().parent.parent / "docs" / "data"

    async def read_bytes(name):
        if "pyodide" in sys.modules:
            from pyodide.http import pyfetch

            resp = await pyfetch(SITE + name)
            if not resp.ok:
                raise RuntimeError(f"could not fetch {SITE + name}: HTTP {resp.status}")
            return await resp.bytes()
        path = LOCAL / name
        if not path.exists():
            raise FileNotFoundError(f"published file not found at {path}")
        return path.read_bytes()

    def scratch_path(name, data):
        path = Path(tempfile.gettempdir()) / name
        path.write_bytes(data)
        return path

    source = SITE if "pyodide" in sys.modules else str(LOCAL)
    return read_bytes, scratch_path, source


@app.cell
async def _(io, json, mo, pd, read_bytes, scratch_path, sqlite3, types):
    with mo.status.spinner("Loading the public database and the block lookups…"):
        _db = scratch_path("berkeley_housing_public.db", await read_bytes("berkeley_housing_public.db"))
        conn = sqlite3.connect(f"file:{_db}?mode=ro", uri=True)
        lookup = pd.read_csv(io.BytesIO(await read_bytes("blocks/address_block_lookup.csv")),
                             dtype={"house_number": str, "street": str, "street_type": str})
        parcel_blocks = pd.read_csv(io.BytesIO(await read_bytes("blocks/parcel_block_lookup.csv")))
        block_geo = json.loads(await read_bytes("blocks/city_blocks.geojson"))
        segment_geo = json.loads(await read_bytes("blocks/street_segments.geojson"))
        # THE address canon, republished verbatim by build_address_block_lookup.py
        canon = types.ModuleType("address_canon")
        exec((await read_bytes("blocks/address.py")).decode(), canon.__dict__)
    normalize_address = canon.normalize_address
    return block_geo, conn, lookup, normalize_address, parcel_blocks, segment_geo


@app.cell
def _(Point, STRtree, block_geo, pd, shape):
    # Block polygons, their labels, and a point inside each one for the overview map.
    _feats = block_geo["features"]
    block_shapes = [shape(f["geometry"]) for f in _feats]
    block_ids = [f["properties"]["block_id"] for f in _feats]
    block_tree = STRtree(block_shapes)
    _rp = [g.representative_point() for g in block_shapes]
    block_info = pd.DataFrame({
        "block_id": block_ids,
        "block_label": [f["properties"]["block_label"] for f in _feats],
        "kind": [f["properties"]["kind"] for f in _feats],
        "acres": [f["properties"]["acres"] for f in _feats],
        "b_lon": [p.x for p in _rp],
        "b_lat": [p.y for p in _rp],
    })
    block_feature = dict(zip(block_ids, _feats))

    def block_at(lon, lat):
        """The block containing a point, or None."""
        if pd.isna(lon) or pd.isna(lat):
            return None
        _p = Point(lon, lat)
        for i in block_tree.query(_p, predicate="within"):
            return block_ids[int(i)]
        return None

    return block_at, block_feature, block_info


@app.cell
def _(block_at, conn, lookup, parcel_blocks, parse_address, pd):
    # One row per project (v4 public DB). Completion = co_issued_date (the project's rule).
    projects = pd.read_sql(
        """
        SELECT project_key, project_id, name, address_display AS address, status,
               units_built_or_permitted, proposed_units, beds, co_issued_date,
               latitude, longitude,
               COALESCE(classifications, '') LIKE '%uc_student_housing%' AS is_uc
        FROM projects
        """,
        conn,
    )
    projects["co_year"] = pd.to_datetime(projects["co_issued_date"], errors="coerce").dt.year
    _built = projects["units_built_or_permitted"].fillna(0)
    _proposed = projects["proposed_units"].fillna(0)
    _done = projects["co_issued_date"].notna()
    projects["stage"] = "other"
    projects.loc[_done, "stage"] = "completed"
    projects.loc[projects["status"].eq("completed") & ~_done, "stage"] = "completed, no CO date"
    _pipe = projects["status"].isin(["under_construction", "entitled", "in_review", "pre_application"]) & ~_done
    projects.loc[_pipe, "stage"] = "pipeline"
    # completed: units built; pipeline: units permitted, else units proposed
    projects["units"] = _built.where(_done | (_built > 0), _proposed).astype(int)

    # Project -> block through its parcels (APN -> block); where its parcels sit on more than one
    # block, or none is known, the project's own coordinates decide.
    _pp = pd.read_sql("SELECT DISTINCT project_key, apn FROM parcels", conn).merge(
        parcel_blocks[["apn_canonical", "block_id"]], left_on="apn", right_on="apn_canonical", how="left")
    _per = _pp.dropna(subset=["block_id"]).groupby("project_key")["block_id"].agg(lambda s: sorted(set(s)))
    _majority = _pp.dropna(subset=["block_id"]).groupby("project_key")["block_id"].agg(lambda s: s.mode().iloc[0])

    # unique (house number, street) keys only: an ambiguous key places nothing
    _keys = lookup.dropna(subset=["block_id"]).drop_duplicates(["house_number", "street"], keep=False)
    _by_address = dict(zip(zip(_keys["house_number"], _keys["street"]), _keys["block_id"]))

    def _assign(r):
        _bs = _per.get(r.project_key)
        if _bs is not None and len(_bs) == 1:
            return _bs[0], "parcel"
        _b = block_at(r.longitude, r.latitude)
        if _b:
            return _b, "coordinates"
        _b = _by_address.get(parse_address(r.address)[:2]) if isinstance(r.address, str) else None
        if isinstance(_b, str):
            return _b, "address"
        if _bs is not None:
            return _majority[r.project_key], "parcel majority"
        return None, "none"

    projects[["block_id", "block_method"]] = projects.apply(_assign, axis=1, result_type="expand")
    return (projects,)


@app.cell
def _(mo, projects):
    _years = projects["co_year"].dropna().astype(int)
    # ?address=2811+Benvenue+Ave opens the page on that address (a shareable link)
    address_box = mo.ui.text(
        value=mo.query_params().get("address") or "",
        placeholder="e.g. 2811 Benvenue Ave", label="Your address", full_width=True,
    )
    stage = mo.ui.radio(
        options={
            "Completed (certificate of occupancy issued)": "completed",
            "In the pipeline (not yet completed)": "pipeline",
        },
        value="Completed (certificate of occupancy issued)",
        label="Stage",
    )
    years = mo.ui.range_slider(
        start=int(_years.min()), stop=int(_years.max()), step=1,
        value=[int(_years.min()), int(_years.max())],
        label="Completion year", show_value=False, full_width=True,
    )
    include_uc = mo.ui.checkbox(value=False, label="Include UC student housing")
    min_units = mo.ui.slider(
        start=0, stop=50, step=1, value=0, label="Only projects with at least N units",
        show_value=True,
    )
    return address_box, include_uc, min_units, stage, years


@app.cell
def _(get_close_matches, lookup, normalize_address, pd, re):
    # The City address layer's street-type codes, for telling apart two streets that share a name
    # (10 Hillcrest Ct and 10 Hillcrest Rd are on different blocks).
    TYPE_CODE = {
        "ave": "AV", "avenue": "AV", "av": "AV", "st": "ST", "street": "ST", "rd": "RD", "road": "RD",
        "ct": "CT", "court": "CT", "blvd": "BL", "boulevard": "BL", "bl": "BL", "way": "WY", "wy": "WY",
        "dr": "DR", "drive": "DR", "pl": "PL", "place": "PL", "ln": "LN", "lane": "LN", "ter": "TE",
        "terrace": "TE", "te": "TE", "cir": "CI", "circle": "CI", "walk": "WK", "path": "PA",
        "common": "CM", "hwy": "HW", "highway": "HW",
    }
    _streets = sorted(lookup["street"].dropna().unique())

    def parse_address(text):
        """Typed or recorded address -> (house_number, street key, street-type code or None).
        THE canon does all the normalizing (tails, units, MLK, ordinals, half-addresses); this only
        reads the street type the canon drops, to tell Hillcrest Ct from Hillcrest Rd."""
        hn, st = normalize_address(text)
        _w = re.findall(r"[a-z]+", str(text).lower())
        _types = [TYPE_CODE[t] for i, t in enumerate(_w) if i >= 1 and t in TYPE_CODE]
        return hn, st, (_types[-1] if _types else None)

    def find_address(text):
        """-> (row or None, message, close-match rows). Never guesses: no match is said plainly."""
        hn, st, code = parse_address(text)
        if not hn or not st:
            return None, "Type a house number and a street, e.g. *2811 Benvenue Ave*.", None
        hits = lookup[(lookup["house_number"] == hn) & (lookup["street"] == st)]
        if len(hits) > 1:
            if code:
                hits = hits[hits["street_type"] == code]
            if len(hits) > 1:
                return None, (f"More than one street is called that: "
                              f"{', '.join(hits['address'])}. Add the street type (Ct, Rd, …)."), hits
        if len(hits) == 1:
            return hits.iloc[0], "", None
        same = lookup[lookup["street"] == st]
        if len(same):
            _n = pd.to_numeric(same["house_number"], errors="coerce")
            _near = same.assign(_d=(_n - float(hn)).abs()).nsmallest(5, "_d")
            return None, f"No address **{hn}** on that street in the City's address list. Closest numbers:", _near
        _close = get_close_matches(st, _streets, n=5, cutoff=0.75)
        if _close:
            _near = lookup[lookup["street"].isin(_close)].drop_duplicates(["street", "street_type"])
            _near = _near.assign(address=_near["address"].str.split(" ", n=1).str[1])   # the street, not an address
            return None, "That street is not in the City's address list. Did you mean one of these streets?", _near
        return None, "That street is not in the City's address list.", None

    return find_address, parse_address


@app.cell
def _(address_box, find_address):
    found, found_msg, found_near = (None, "", None)
    if address_box.value.strip():
        found, found_msg, found_near = find_address(address_box.value)
    my_block = found["block_id"] if found is not None and isinstance(found["block_id"], str) else None
    return found, found_msg, found_near, my_block


@app.cell
def _(address_box, include_uc, min_units, mo, stage, years):
    _controls = [address_box, stage, include_uc, min_units]
    if stage.value == "completed":
        # the slider's own readout formats years as "2,018", so show the range in words
        _controls.insert(2, mo.vstack([years, mo.md(f"{years.value[0]}–{years.value[1]}")], gap=0.1))
    mo.vstack(_controls, gap=0.75)
    return


@app.cell
def _(found, found_msg, found_near, mo, my_block):
    _out = None
    if found is not None:
        if my_block is None:
            _out = mo.callout(mo.md(
                f"**{found['address']}** is in the City's address list, but its point lies "
                f"{found['distance_m']:.0f} m from the nearest block, too far to assign one."), kind="warn")
        else:
            _seg = found["segment_label"] if isinstance(found["segment_label"], str) else "no street segment on record"
            _how = "" if found["match_method"] == "inside" else (
                f" (its address point is {found['distance_m']:.0f} m outside the block; nearest block used)")
            _units = int(found["unit_count"])
            _out = mo.callout(mo.md(
                f"**{found['address']}** is on block **{found['block_label'] or my_block}** "
                f"(`{my_block}`{', closed by the city limit' if found['block_kind'] == 'edge' else ''}){_how}.  \n"
                f"Street segment: **{_seg}**."
                + (f"  \nThe City lists {_units} units at this address." if _units else "")), kind="success")
    elif found_msg:
        _parts = [mo.md(found_msg)]
        if found_near is not None and len(found_near):
            _parts.append(mo.md("  \n".join(f"- {a}" for a in found_near["address"])))
        _out = mo.callout(mo.vstack(_parts), kind="warn")
    _out
    return


@app.cell
def _(include_uc, min_units, projects, stage, years):
    shown = projects[projects["stage"].eq(stage.value) & projects["block_id"].notna()]
    if stage.value == "completed":
        shown = shown[shown["co_year"].between(years.value[0], years.value[1])]
    if not include_uc.value:
        shown = shown[~shown["is_uc"].astype(bool)]
    shown = shown[shown["units"] >= min_units.value]
    return (shown,)


@app.cell
def _(block_info, shown):
    blocks = (
        shown.groupby("block_id")
        .agg(units=("units", "sum"), projects=("project_id", "size"), largest=("units", "max"))
        .reset_index()
        .merge(block_info, on="block_id", how="left")
        .sort_values("units", ascending=False)
        .reset_index(drop=True)
    )
    return (blocks,)


@app.cell
def _(blocks, mo, shown, stage, years):
    _top = blocks.head(10)["units"].sum()
    _total = blocks["units"].sum()
    _share = (_top / _total * 100) if _total else 0
    _window = f" in {years.value[0]}–{years.value[1]}" if stage.value == "completed" else ""
    mo.hstack(
        [
            mo.stat(f"{_total:,}", label="Units", caption=f"{stage.value}{_window}"),
            mo.stat(f"{len(shown):,}", label="Projects"),
            mo.stat(f"{len(blocks):,}", label="Blocks with any"),
            mo.stat(f"{_share:.0f}%", label="Share in top 10 blocks"),
        ],
        widths="equal",
    )
    return


@app.cell
def _(alt, block_info, blocks, found, mo, my_block, pd, projects):
    # One layer (marimo can only read selections from single-layer charts): faint dots for every
    # tracked project give the city's outline; blue circles are blocks, area ~ units; the address
    # you typed is a red dot.
    _bg = projects.dropna(subset=["latitude", "longitude"])[["latitude", "longitude"]].assign(
        kind="project", block_id=None, block_label=None, units=None, projects=None, largest=None, msize=6.0
    )
    _bk = blocks.dropna(subset=["b_lat", "b_lon"]).rename(columns={"b_lat": "latitude", "b_lon": "longitude"})
    _bk = _bk.assign(kind="block")
    _max = max(float(_bk["units"].max()), 1.0) if len(_bk) else 1.0
    _bk["msize"] = 15 + 1400 * _bk["units"] / _max
    _layers = [_bg, _bk[["latitude", "longitude", "kind", "block_id", "block_label", "units", "projects",
                         "largest", "msize"]]]
    if my_block is not None:
        _layers.append(pd.DataFrame([{
            "latitude": found["latitude"], "longitude": found["longitude"], "kind": "your address",
            "block_id": my_block,
            "block_label": block_info.set_index("block_id")["block_label"].get(my_block),
            "msize": 160.0,
        }]))
    _layer = pd.concat(_layers, ignore_index=True)

    block_map = mo.ui.altair_chart(
        alt.Chart(_layer)
        .mark_circle(stroke="white", strokeWidth=0.4)
        .encode(
            # Plain x/y, not a geo projection: Vega crashes on click-selection over a
            # projected chart ("Cannot read properties of undefined (reading 'on')").
            # At city scale the distortion is small; axes hidden so it reads as a map.
            x=alt.X("longitude:Q", scale=alt.Scale(zero=False), axis=None),
            y=alt.Y("latitude:Q", scale=alt.Scale(zero=False), axis=None),
            size=alt.Size("msize:Q", scale=None, legend=None),
            color=alt.Color(
                "kind:N",
                scale=alt.Scale(domain=["block", "project", "your address"],
                                range=["#2a6f97", "#b8b8b0", "#c0392b"]),
                legend=None,
            ),
            opacity=alt.condition("datum.kind == 'project'", alt.value(0.4), alt.value(0.75)),
            order=alt.Order("kind:N", sort="descending"),
            tooltip=[
                alt.Tooltip("block_label:N", title="Block"),
                alt.Tooltip("units:Q", title="Units", format=","),
                alt.Tooltip("projects:Q", title="Projects"),
                alt.Tooltip("largest:Q", title="Largest project", format=","),
            ],
        )
        .properties(width="container", height=560)
        .configure_view(stroke=None),
        chart_selection="point",
        legend_selection=False,
    )
    return (block_map,)


@app.cell
def _(blocks, mo):
    block_table = mo.ui.table(
        blocks[["block_label", "units", "projects", "largest", "block_id"]],
        selection="multi",
        page_size=10,
        label="Blocks ranked by units (select rows to drill down)",
        format_mapping={"units": "{:,}".format, "largest": "{:,}".format},
    )
    return (block_table,)


@app.cell
def _(block_map, block_table, mo):
    mo.vstack([block_map, block_table], gap=1)
    return


@app.cell
def _(alt, block_feature, found, mo, my_block, pd, projects, segment_geo):
    # Your block, close up: its outline, your street segment, your address and the tracked
    # projects on the block (every stage). A geo projection is safe here: nothing to click.
    _out = None
    if my_block is not None:
        _feats = [block_feature[my_block]]
        _seg = [f for f in segment_geo["features"] if f["properties"]["segment_id"] == found["segment_id"]]
        _here = projects[projects["block_id"].eq(my_block)].dropna(subset=["latitude", "longitude"])
        _pts = pd.concat([
            _here[["latitude", "longitude", "address", "units", "status"]].assign(kind="project"),
            pd.DataFrame([{"latitude": found["latitude"], "longitude": found["longitude"],
                           "address": found["address"], "kind": "your address"}]),
        ], ignore_index=True)
        _base = alt.Chart(alt.Data(values=_feats)).mark_geoshape(
            fill="#dbe8f2", stroke="#2a6f97", strokeWidth=1.5)
        _line = alt.Chart(alt.Data(values=_seg or [_feats[0]])).mark_geoshape(
            filled=False, stroke="#c0392b" if _seg else "transparent", strokeWidth=4)
        _dots = alt.Chart(_pts).mark_circle(size=90, stroke="white").encode(
            longitude="longitude:Q", latitude="latitude:Q",
            color=alt.Color("kind:N", scale=alt.Scale(domain=["project", "your address"],
                                                      range=["#2a6f97", "#c0392b"]), legend=None),
            tooltip=[alt.Tooltip("address:N"), alt.Tooltip("units:Q", title="Units"), alt.Tooltip("status:N")],
        )
        _out = mo.vstack([
            mo.md(f"### Your block: {found['block_label'] or my_block}"),
            alt.layer(_base, _line, _dots).project("mercator").properties(width="container", height=320),
            mo.md("Blue outline: the block. Red line: your street segment. Blue dots: tracked "
                  "housing projects on the block, at every stage."),
        ])
    _out
    return


@app.cell
def _(block_info, block_map, block_table, mo, my_block, shown):
    _picked = set(block_table.value["block_id"]) if len(block_table.value) else set()
    if len(block_map.value):
        _picked |= set(block_map.value["block_id"].dropna())
    if my_block is not None:
        _picked.add(my_block)

    if not _picked:
        _out = mo.callout(
            mo.md("Type an address, or select a block on the map or in the table, to list its projects."),
            kind="neutral",
        )
    else:
        _labels = block_info.set_index("block_id")["block_label"]
        _rows = (
            shown[shown["block_id"].isin(_picked)]
            .assign(block=lambda d: d["block_id"].map(_labels))
            .sort_values(["block", "units"], ascending=[True, False])
            [["block", "address", "name", "units", "co_issued_date", "status", "project_id", "block_id"]]
            .rename(columns={"co_issued_date": "CO issued"})
        )
        _label = "; ".join(sorted(_labels.get(b, b) for b in _picked)) if len(_picked) <= 3 else f"{len(_picked)} blocks"
        _out = mo.vstack(
            [
                mo.md(f"### Projects on {_label}: {_rows['units'].sum():,} units, for the current filters"),
                mo.ui.table(_rows, selection=None, page_size=15) if len(_rows)
                else mo.md("_No projects on this block match the current stage and filters._"),
            ]
        )
    _out
    return


@app.cell
def _(alt, mo, shown, stage):
    # Citywide context: completions by year (only meaningful for the completed stage).
    _out = None
    if stage.value == "completed" and len(shown):
        _by_year = shown.groupby("co_year")["units"].sum().reset_index()
        _out = mo.vstack(
            [
                mo.md("### Completed units by year, for the current filters"),
                alt.Chart(_by_year)
                .mark_bar(color="#2a6f97")
                .encode(
                    x=alt.X("co_year:O", title=None),
                    y=alt.Y("units:Q", title="Units"),
                    tooltip=[alt.Tooltip("co_year:O", title="Year"),
                             alt.Tooltip("units:Q", title="Units", format=",")],
                )
                .properties(width="container", height=220),
            ]
        )
    _out
    return


@app.cell
def _(lookup, mo, projects, source):
    _m = projects["block_method"].value_counts()
    _no_block = int(_m.get("none", 0))
    _no_date = int(projects["stage"].eq("completed, no CO date").sum())
    _other = int(projects["stage"].eq("other").sum())
    _uc = int(projects["is_uc"].astype(bool).sum())
    _addr_none = int(lookup["match_method"].eq("none").sum())
    mo.accordion(
        {
            "About this data": mo.md(
                f"""
                - **Source:** the v4 public database and the block lookups published at
                  `{source}` (`berkeley_housing_public.db`, `blocks/`).
                - **Units:** for completed projects, units built; for the pipeline, units permitted,
                  or units proposed where nothing is permitted yet. Gross, not net of demolitions.
                  The tracked list covers development projects and finaled ADU/infill completions;
                  it is not every permit in the city.
                - **Completed** means the project has a certificate-of-occupancy date.
                  **{_no_date}** projects are marked completed but have no CO date on record, and
                  **{_other}** are withdrawn, denied, void or stale. Both groups are left out of
                  both stages rather than guessed.
                - **Blocks:** a project is placed by its parcels' blocks
                  ({int(_m.get('parcel', 0))} projects). Where its parcels sit on more than one
                  block, or none is known, its own coordinates decide
                  ({int(_m.get('coordinates', 0))}), then its street address
                  ({int(_m.get('address', 0))}), then the block holding most of its parcels
                  ({int(_m.get('parcel majority', 0))}). **{_no_block}** projects cannot be placed
                  and are not shown.
                - **Addresses** come from the City's address-point layer ({len(lookup):,} street
                  addresses). {_addr_none} lie too far from any block to assign one.
                - **UC student housing** ({_uc} projects) is off by default: UC is exempt from city
                  permitting and is counted outside the city's housing-element totals. UC projects
                  are counted in beds, which this page does not show.
                """
            )
        }
    )
    return


if __name__ == "__main__":
    app.run()
