#!/usr/bin/env python3
"""deploy_gate.py — refuse a deploy that would publish something broken.

WHY IT IS A SCRIPT AND NOT A HEREDOC. This check used to live inline in the deploy shell as
`git show :docs/index.html | python3 -c "...assert..."`. On 2026-08-29 an assertion in it FAILED
and the push went ahead regardless: the failing python was the tail of a pipeline, `set -e` did
not propagate it, and the deploy proceeded past the gate written to stop it. It happened to be a
false alarm. That is worse, not better -- a gate that is ignored when it fires teaches you to
ignore it.

It reads the STAGED tree (`git show :path`), not the working tree, because the staged tree is
what a commit will contain. Exits non-zero on any failure, and the caller must be `set -e` or
check the status.

  git checkout main && git rm -rq docs kml && git checkout dev -- docs kml
  python3 scripts/deploy_gate.py && git commit ... && git push origin main
"""
import json, re, subprocess, sys

FAIL = []
def check(ok, msg, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {msg}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAIL.append(msg)

def staged(path):
    r = subprocess.run(["git", "show", f":{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

def in_index(path):
    """True if PATH exists in the staged tree. Unlike staged(), safe for binaries, and unlike
    staged_files(), it sees unchanged files too."""
    return subprocess.run(["git", "cat-file", "-e", f":{path}"],
                          capture_output=True).returncode == 0

def staged_files():
    r = subprocess.run(["git", "diff", "--cached", "--name-only", "-z"], capture_output=True, text=True)
    return [p for p in r.stdout.split("\0") if p]

def main():
    files = staged_files()
    check(bool(files), "something is staged", f"{len(files)} files")

    # 1. NOTHING OUTSIDE THE PUBLISHED TREES. dev carries advocacy drafts and the working data
    #    set; a branch-shaped push would publish all of it.
    outside = [f for f in files if not f.startswith(("docs/", "kml/"))]
    check(not outside, "nothing staged outside docs/ and kml/", ", ".join(outside[:4]))
    for d in ("notes/", "team/", "data/", "scripts/", "experiments/", "PROGRESS.md"):
        n = sum(1 for f in files if f.startswith(d))
        check(n == 0, f"nothing from {d}", f"{n} files")

    h = staged("docs/index.html")
    if h is None:
        check(False, "docs/index.html is staged or unchanged")
    else:
        # VIDEO IDS COME FROM data-yt, NOT FROM THE EMBED URL. The embeds moved to
        # youtube-nocookie.com on 2026-09-22, and the old r"youtube\.com/embed/" pattern does
        # not match "youtube-nocookie.com/embed/" -- it would have matched nothing and passed
        # vacuously, which is worse than failing. data-yt is the facade's own marker.
        yt = re.findall(r'data-yt="([A-Za-z0-9_-]+)"', h)
        check(h.count("<div") == h.count("</div>"), "divs balance",
              f"{h.count('<div')} open, {h.count('</div>')} close")
        check(len(yt) >= 8, "the flyovers are still on the page", f"{len(yt)} found")
        check(len(yt) == len(set(yt)), "no duplicated video",
              ", ".join(sorted({v for v in yt if yt.count(v) > 1})))

        # THE COLOUR LEGEND IS SHARED, NOT PER-BLOCK (changed 2026-09-22). It used to be
        # repeated in all ten video paragraphs: 1,280 words, 54% of the page's video text, and
        # a wall of duplicate prose on a phone. It now lives once in a <details> under the
        # stage-legend figure. So the guarantee to enforce is no longer "every block has one"
        # but "the page has exactly one, and it names every stage".
        # American spelling as of 2026-09-24 (the page said "Colour" throughout; a
        # Berkeley, California site should not). Count both so an older deploy still passes.
        nleg = h.count("Color shows where each project stands") + \
               h.count("Colour shows where each project stands")
        check(nleg == 1, "the shared colour legend appears exactly once", f"found {nleg}")
        stages = ["pre-application", "under review", "entitled", "permitted, not yet started",
                  "under construction", "completed and occupiable", "withdrawn"]
        absent_stage = [t for t in stages if t not in h]
        check(not absent_stage, "the shared legend names every stage", ", ".join(absent_stage))

        # EVERY LOCAL ASSET THE PAGE REFERENCES IS ACTUALLY IN THE COMMIT. Added 2026-09-22,
        # after the hero loop: *.mp4 is gitignored (.gitignore:111), so a referenced video can
        # sit on disk, be absent from the commit, and 404 on the live site -- and deploy.sh's
        # untracked warning never sees it, because an IGNORED file is not an UNTRACKED file.
        # Without this check that failure is silent and lands on the homepage.
        refs = sorted(set(re.findall(r'(?:src|poster)="((?:videos|img|svg)/[^"]+)"', h)))
        absent = [r for r in refs if not in_index(f"docs/{r}")]
        check(not absent, "every local asset the page references is in the commit",
              ", ".join(absent[:4]))

    c = staged("docs/tours.json")
    if c is not None:
        cat = json.loads(c)
        ids = [t["id"] for t in cat["tours"]]
        check(len(ids) == len(set(ids)), "no duplicate catalog ids")
        vids = [(t["id"], (t.get("video") or {}).get("youtube")) for t in cat["tours"]]
        onsite = set(re.findall(r"youtube\.com/embed/([A-Za-z0-9_-]+)", h or ""))
        incat = {v for _, v in vids if v}
        check(onsite <= incat, "every video on the page has a catalog entry",
              ", ".join(onsite - incat))
        # a package path that does not exist is the sitewide 404 this project has shipped twice
        import os
        # entries may legitimately have no package -- an unsourced legacy video has no tour
        gone = [t["package"] for t in cat["tours"] if t.get("package") and not os.path.exists(t["package"])]
        check(not gone, "every catalog package exists on disk", f"{len(gone)} missing")

    # 4. THE SERVED DATA IS NOT STALE. export_explorer_data_v2.py writes
    #    docs/explorer_data_v2_working.js; docs/explorer.html -- the page every link on the site
    #    points at -- reads docs/explorer_data.js. Promotion between them is a manual copy, and
    #    on 2026-09-04 it emerged that it had not happened since the owner join landed: the live
    #    explorer had 28 owners populated out of 895 projects while the working file had 852.
    #    Nothing caught it. The export prints a cheerful success line about a file nobody serves,
    #    and this gate passed 15/15 while shipping month-old data.
    #
    #    Compare the two directly. Byte-identical is the only safe state; anything else means an
    #    export ran and was never promoted. The header carries a "Generated:" line that differs
    #    on every run, so compare the DATA and report the dates when they disagree.
    served, working = staged("docs/explorer_data.js"), staged("docs/explorer_data_v2_working.js")
    if served is None or working is None:
        check(served is not None, "docs/explorer_data.js is present")
    else:
        def gen(t):
            m = re.search(r"Generated:\s*(.+)", t)
            return m.group(1).strip() if m else "unknown"
        def payload(t):
            i = t.find("DATA =")
            return t[i:] if i >= 0 else t
        fresh = payload(served) == payload(working)
        check(fresh, "served explorer data matches the latest export",
              f"served {gen(served)} vs working {gen(working)} — "
              "run scripts/export_explorer_data_v2.py, then "
              "cp docs/explorer_data_v2_working.js docs/explorer_data.js")

    print()
    if FAIL:
        print(f"DEPLOY BLOCKED — {len(FAIL)} check(s) failed:")
        for f in FAIL:
            print(f"  - {f}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
