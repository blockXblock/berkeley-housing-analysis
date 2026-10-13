"""Block canon: IDs are unique, deterministic, and survive a re-digitised re-fetch.
Run: .venv/bin/python -m scripts.housing_rules.test_blocks"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from housing_rules import blocks as hb  # noqa: E402


def main():
    g = hb.load_city_blocks()
    assert g.block_id.is_unique and g.block_id.str.match(r"^CB-[0-9a-f]{8}$").all()
    assert set(g.kind) == {"enclosed", "edge"}
    assert hb.load_city_blocks().block_id.tolist() == g.block_id.tolist(), "minting is not deterministic"

    # a re-fetch where the City nudged every polygon 3 m: minted IDs change, inherited IDs must not
    reg = g[["block_id", "rep_x", "rep_y"]]
    moved = g.copy()
    moved["geometry"] = moved.geometry.translate(3, 3)
    assert (moved.geometry.map(hb.mint_block_id) != g.block_id).mean() > 0.99
    tmp = Path(__file__).resolve().parent / "_test_blocks_moved.geojson"
    try:
        moved.to_crs(4326)[["geometry"]].to_file(tmp, driver="GeoJSON")
        again = hb.load_city_blocks(path=tmp, registry=reg, include_edge=False)
    finally:
        tmp.unlink(missing_ok=True)
    kept = again.block_id.isin(set(g.block_id)).mean()      # the shifted file carries edge blocks too
    assert kept > 0.99, f"only {kept:.1%} of IDs survived a 3 m shift"
    print(f"blocks: {len(g)} unique CB- IDs, deterministic; {kept:.1%} survive a 3 m re-digitising -- PASS")


if __name__ == "__main__":
    main()
