#!/usr/bin/env bash
# Stage a berkeleybuild.com deploy and gate it. Does NOT push -- John owns that.
#
# WHY A WORKTREE. This used to `git checkout main` in place. That fails whenever ANY file
# differing between the branches has uncommitted changes -- so a half-finished edit in
# scripts/, belonging to a different lane entirely, aborted a deploy that only ever publishes
# docs/ and kml/. Building the commit in a throwaway worktree touches nothing in John's
# working tree: other lanes keep their edits, and a failed deploy cannot leave him on the
# wrong branch.
#
# The gate runs as a plain command under `set -e` (it was once a heredoc in a pipeline, whose
# exit code `set -e` never saw, so a failed assertion let the push through anyway).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
ROOT=$(pwd)

[ "$(git rev-parse --abbrev-ref HEAD)" = dev ] || { echo "run from dev"; exit 2; }
DIRTY=$(git status --porcelain --untracked-files=no -- docs kml | head -20)
[ -z "$DIRTY" ] || { echo "docs/ or kml/ has uncommitted TRACKED changes -- commit them first:"; echo "$DIRTY"; exit 2; }
UNTRACKED=$(git ls-files --others --exclude-standard -- docs kml | head -10)
[ -z "$UNTRACKED" ] || { echo "note: untracked under docs/ or kml/, NOT deployed:"; echo "$UNTRACKED" | sed 's/^/  /'; }
DEV=$(git rev-parse HEAD)

WT=$(mktemp -d -t deploywt)
GATE=$(mktemp -t deploy_gate.XXXXXX.py)
cleanup() { rm -f "$GATE"; git worktree remove --force "$WT" 2>/dev/null || true; rm -rf "$WT"; }
trap 'rc=$?; [ $rc -ne 0 ] && echo; [ $rc -ne 0 ] && echo "DEPLOY ABORTED (exit $rc) -- nothing pushed, working tree untouched."; cleanup; exit $rc' EXIT

git worktree add -q --detach "$WT" main
git show "$DEV":scripts/deploy_gate.py > "$GATE"
cd "$WT"
git checkout "$DEV" -- docs kml          # selective: only the site and its KML source cross

echo "staged for main:"
git diff --cached --stat | sed 's/^/  /'
echo
python3 "$GATE"
echo

git commit -q -m "deploy: site + KML from dev ${DEV:0:7}"
NEW=$(git rev-parse HEAD)
cd "$ROOT"
git update-ref refs/heads/main "$NEW"    # move main without ever checking it out
cleanup; trap - EXIT

echo "main is now $(git rev-parse --short main) -- NOT pushed. Still on $(git rev-parse --abbrev-ref HEAD)."
echo
echo "John: to publish, run"
echo "    git push origin main"
echo "to abandon instead:"
echo "    git update-ref refs/heads/main origin/main"
