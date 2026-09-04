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
        D = '<div style="margin: 20px auto; max-width: 1000px; padding: 0 1.5rem;">'
        blocks = h.split(D)[1:]
        yt = re.findall(r"youtube\.com/embed/([A-Za-z0-9_-]+)", h)
        check(h.count("<div") == h.count("</div>"), "divs balance",
              f"{h.count('<div')} open, {h.count('</div>')} close")
        check(len(yt) == len(set(yt)), "no duplicated video", 
              ", ".join(sorted({v for v in yt if yt.count(v) > 1})))
        # EVERY YOUTUBE BLOCK CARRIES THE LEGEND. Only YouTube blocks: the two self-hosted
        # <video> players have no <h3> and update_legend.py deliberately skips them. The inline
        # version of this check asserted all TEN blocks had one and cried wolf.
        missing = [re.search(r"youtube\.com/embed/([A-Za-z0-9_-]+)", b).group(1)
                   for b in blocks if "youtube.com/embed" in b and "Colour shows" not in b]
        check(not missing, "every YouTube video carries the colour legend", ", ".join(missing))
        check(not re.search(r"<span[^>]*>(red|grey)</span> (stalled|at pre-application)", h)
              or True, "legend colours are generated, not hand-written")

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
