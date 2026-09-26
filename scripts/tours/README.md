# scripts/tours — the flyover tours, KML geometry, labels and tour videos

Moved here from `scripts/` on 2026-09-26 to separate the website's 3-D tour tooling from the housing
data machinery. Nothing here writes a database. Imports are `scripts.tours.<name>`; run from the repo
root, e.g. `python3 scripts/tours/rebuild_corridor.py ...`.

KML files generated before the move record the generator's old path (`scripts/<name>.py`) in their
comments; that is history, not a live reference.
