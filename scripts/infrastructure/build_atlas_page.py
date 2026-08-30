#!/usr/bin/env python3
"""Assemble the self-contained Berkeley Pole and Pipe Atlas page by inlining the
map bundle into the template. The published page must stay self-contained: no
external requests beyond Google Fonts, which is the only host the Artifact CSP allows.

usage: build_atlas_page.py [bundle_json] [out_html]
"""
import os, sys

HERE   = os.path.dirname(os.path.abspath(__file__))
DATE   = "2026-08-30"
bundle_path = sys.argv[1] if len(sys.argv) > 1 else f"scratch/infrastructure/map_bundle_{DATE}.json"
out         = sys.argv[2] if len(sys.argv) > 2 else "scratch/infrastructure/berkeley-pole-pipe-atlas.html"

bundle = open(bundle_path).read()
html   = open(os.path.join(HERE, "atlas_template.html")).read()
assert "/*__BUNDLE__*/" in html, "template lost its bundle placeholder"

os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
open(out, "w").write(html.replace("/*__BUNDLE__*/", bundle))
print(f"wrote {out}  {os.path.getsize(out)/1e6:.2f} MB")
