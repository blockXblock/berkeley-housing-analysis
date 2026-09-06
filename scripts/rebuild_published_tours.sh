#!/usr/bin/env bash
# Rebuild the labelled packages for the published corridor/scatter tours with the current engine.
# Each entry: "tour-stem|street-set-or-empty|max-labels". Streets fold in orientation signs; empty
# means the flight is scattered/multi-street and gets none. All run --all (every building the flight
# passes gets a label, capped on screen by max-labels). Kennedy is NOT here -- it carries its own
# geometry and is built with --geom; these use the canonical kml/geometry/geometry.kml.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
IMG=scratch/2026-08-31/svg-labels          # shared canonical-geometry label cache
TOURS=(
  "tour-private-pipeline-over-200-units-2026-05-16||3"
  "university-880-uc|university-880-uc|3"
  "uc-dormitories||3"
  "durant-w2e|durant|3"
  "san-pablo-n2s|san-pablo|3"
)
for row in "${TOURS[@]}"; do
  IFS='|' read -r stem street maxl <<< "$row"
  echo "=== $stem ==="
  args=(--tour "$stem" --all --max-labels "$maxl" --imgs "$IMG")
  [ -n "$street" ] && args+=(--street "$street")
  python3 scripts/svg_label_tour.py "${args[@]}" 2>&1 | tail -4
  echo
done
