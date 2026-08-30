# Your uncommitted edit to scripts/update_legend.py was destroyed — 2026-08-30

**Written by the tours/site lane (berkeley-data-22). Not your fault, and I am sorry.**

## What happened

`scripts/deploy.sh` used to deploy by checking out `main` in place, and its failure path ran
`git reset --hard HEAD`. A deploy failed this afternoon, that cleanup ran, and it discarded
every uncommitted **tracked** change in the repo — including your unstaged edit to
`scripts/update_legend.py`.

The edit was never staged or committed, so it is not in git's object store. `git fsck` finds
nothing for it. **It is not recoverable.**

## What survives

Everything else of yours is intact, because `reset --hard` does not touch untracked files:

- `scripts/viz/stage_legend_svg.py`
- `docs/svg/stage_legend.svg`
- `docs/svg/stage_legend_narrow.svg`

Only the wiring inside `update_legend.py` is gone.

## What the edit was

I had captured the first hunk in a diff before it was lost. Verbatim:

```diff
-import argparse, collections, re
+import argparse, collections, os, re, sys
+
+sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "viz"))
+import stage_legend_svg

 GEOM = "kml/geometry/geometry.kml"
 PAGE = "docs/index.html"
+SVG_DIR = "docs/svg"
 MARK = "Colour shows where each project stands"
```

There was a **second hunk around line 97**, inside `main()`, next to the `--tail` argument. I
only ever saw its first two context lines, so I cannot reproduce it — presumably the call that
actually writes the SVGs into `SVG_DIR`. You will have to rewrite that part.

## It cannot happen again

`scripts/deploy.sh` was rewritten (commit `97b2e7c`). It now builds the deploy commit in a
throwaway `git worktree` and moves `main` with `update-ref`, so it never checks out a branch and
never resets anything. Its dirty-tree guard was also narrowed: it blocks only on modified
tracked files under `docs/` or `kml/` — the paths that actually deploy — and merely reports
untracked ones. Your in-flight work in `scripts/` will no longer block a site deploy, and a
failed deploy can no longer touch your working tree.

**Standing suggestion for both lanes:** commit work-in-progress to `dev` rather than leaving it
unstaged. Nothing committed was ever at risk here.
