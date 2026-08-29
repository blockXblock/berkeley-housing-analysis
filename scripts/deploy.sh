#!/usr/bin/env bash
# Stage a berkeleybuild.com deploy and gate it. Does NOT push -- John owns that.
#
# Why this exists: the deploy used to be hand-typed, with the gate run as a
# heredoc inside a pipeline. A pipeline's exit code is its LAST command's, so a
# failed assertion vanished and the push proceeded anyway (2026-08-28). Here the
# gate is a plain command under `set -e`, so a non-zero exit stops everything,
# and the trap puts the tree back the way it was found.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

[ "$(git rev-parse --abbrev-ref HEAD)" = dev ] || { echo "run from dev"; exit 2; }
git diff --quiet && git diff --cached --quiet || { echo "dev has uncommitted changes -- commit them first"; exit 2; }
DEV=$(git rev-parse HEAD)

GATE=$(mktemp -t deploy_gate.XXXXXX.py)
restore() { rm -f "$GATE"; git reset -q --hard HEAD 2>/dev/null || true; git checkout -qf dev 2>/dev/null || true; }
trap 'rc=$?; [ $rc -ne 0 ] && { echo; echo "DEPLOY ABORTED (exit $rc) -- nothing pushed, tree restored."; restore; }; exit $rc' EXIT

# deploy is SELECTIVE: only the public site and its KML source cross to main
git checkout -q main
git checkout "$DEV" -- docs kml

echo "staged for main:"
git diff --cached --stat | sed 's/^/  /'
echo

# the gate lives on dev; main has no scripts/ -- run dev's copy from a temp path
git show "$DEV":scripts/deploy_gate.py > "$GATE"
python3 "$GATE"
echo

git commit -q -m "deploy: site + KML from dev ${DEV:0:7}"
echo "main is now $(git rev-parse --short HEAD) -- NOT pushed."
echo
echo "John: to publish, run"
echo "    git push origin main && git checkout dev"
echo "to abandon instead:"
echo "    git reset --hard origin/main && git checkout dev"
rm -f "$GATE"
trap - EXIT
