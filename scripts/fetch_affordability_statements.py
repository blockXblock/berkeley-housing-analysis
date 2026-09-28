#!/usr/bin/env python3
r"""fetch_affordability_statements.py -- download the tier-1 affordability documents a model picked
from the listing, with a manifest that can be checked.

WHY. Berkeley's 1.E tabulation form never states affordability; income tiers live only in a Density
Bonus Eligibility Statement, an Affordable Housing Compliance Plan or similar. Only 255 of ~1,200
affordable units in v2 are sourced. list_affordability_statements.py listed every attachment on the
records reaching the 26 unsourced projects (1,419 files, downloading nothing); a model judged which
are likely sources; John approved fetching tier 1. This fetches EXACTLY the approved filenames.

  --list  data/.../fetch_list.csv   project_id,address,record,filename,bytes,likelihood,tier,why
  --tier  1                         only these rows (tier 2 is 388 MB of ZAB reports, NOT approved)

DISCIPLINE.
  * The grid walk is scripts/accela_grid.py -- the one home for the tab click, the row polling and
    the pager. Not re-typed here; that is how the listing came to report 10 files for a record
    holding 123.
  * A file is downloaded by firing ITS OWN row's __doPostBack, so the walk must be on the page that
    holds the row -- the reason accela_grid.walk is a generator.
  * EXACT filename match against the approved list. No fuzzy matching: fetching something the list
    does not name would be fetching what John did not approve.
  * The manifest records sha256 and the size CHECKED against the listing's bytes, because a 200-byte
    HTML error page saved as .pdf is a "successful" download that a size check catches.
  * Resumable: a file already on disk with a matching size is skipped, so a re-run costs nothing.
  * Failures retried once per record (CLAUDE.md: a 0-result is not evidence of absence until retried).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import accela_grid as ag                      # noqa: E402  THE one grid walk

OUT = ROOT / "scratch/2026-09-28_affordability/tier1"


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def hrefs_for(records: set[str]) -> dict[str, str]:
    """record -> capdetail_href, from the harvest's own parsed output (no re-discovery)."""
    import glob
    import json
    out = {}
    src = sorted(glob.glob(str(ROOT / "scratch/2026-09-26_capdetail/capdetail_reparsed_*.jsonl")))
    for line in open(src[-1]):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("record") in records and r.get("href") and r["record"] not in out:
            out[r["record"]] = r["href"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default=str(ROOT / "scratch/2026-09-28_affordability/fetch_list.csv"))
    ap.add_argument("--tier", default="1")
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--limit", type=int, default=0, help="stop after N records (smoke test)")
    args = ap.parse_args()

    want: dict[str, dict[str, dict]] = defaultdict(dict)      # record -> filename -> row
    for r in csv.DictReader(open(args.list)):
        if (r.get("tier") or "").strip() == args.tier:
            want[r["record"]][r["filename"].strip()] = r
    recs = sorted(want)
    if args.limit:
        recs = recs[:args.limit]
    total = sum(len(want[r]) for r in recs)
    print(f"tier {args.tier}: {total} files across {len(recs)} records "
          f"({sum(int(v['bytes'] or 0) for r in recs for v in want[r].values())/1e6:.1f} MB listed)",
          flush=True)
    href = hrefs_for(set(recs))
    missing = [r for r in recs if r not in href]
    if missing:
        print(f"NO capdetail_href for {len(missing)}: {missing}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for i, rec in enumerate(recs, 1):
            files = want[rec]
            dest_dir = OUT / rec
            dest_dir.mkdir(parents=True, exist_ok=True)
            got: dict[str, str] = {}
            err = ""
            for attempt in (1, 2):
                todo = {fn: row for fn, row in files.items() if fn not in got}
                # resume: a file already on disk at the listed size is done
                for fn, row in list(todo.items()):
                    f = dest_dir / fn.replace("/", "_")
                    if f.exists() and abs(f.stat().st_size - int(row["bytes"] or 0)) <= 2048:
                        got[fn] = "ok-already-on-disk"
                        todo.pop(fn)
                if not todo or rec not in href:
                    break
                pg = b.new_page()
                pg.set_default_timeout(60000)
                try:
                    frame = ag.open_grid(pg, href[rec])
                    for page_rows in ag.walk(pg, frame):
                        for r in page_rows:
                            fn = (r.get("filename") or "").strip()
                            if fn not in todo or not r.get("target"):
                                continue
                            f = dest_dir / fn.replace("/", "_")
                            try:
                                with pg.expect_download(timeout=180000) as dl:
                                    frame.evaluate(f"__doPostBack('{r['target']}','')")
                                dl.value.save_as(str(f))
                                got[fn] = "ok"
                            except Exception as e:
                                got[fn] = f"FAILED-{type(e).__name__}"
                            time.sleep(0.4)
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"[:160]
                pg.close()
                if all(v.startswith("ok") for v in got.values()) and len(got) == len(files):
                    break
                time.sleep(2)
            for fn, row in files.items():
                f = dest_dir / fn.replace("/", "_")
                st = got.get(fn, "FAILED-not-found-in-grid" + (f" ({err})" if err else ""))
                size = f.stat().st_size if f.exists() else 0
                listed = int(row["bytes"] or 0)
                # a size check catches the download that "succeeded" and saved an error page
                if st.startswith("ok") and listed and abs(size - listed) > 2048:
                    st = f"SIZE-MISMATCH listed={listed} got={size}"
                manifest.append({"project_id": row["project_id"], "record": rec, "filename": fn,
                                 "listed_bytes": listed, "bytes": size,
                                 "sha256": sha256_of(f) if size else "",
                                 "likelihood": row.get("likelihood", ""),
                                 "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "status": st,
                                 "local_path": str(f.relative_to(ROOT)) if size else ""})
            ok = sum(1 for fn in files if got.get(fn, "").startswith("ok"))
            print(f"  [{i}/{len(recs)}] {rec:16} {ok}/{len(files)} files", flush=True)
            time.sleep(args.delay)
        b.close()

    mpath = OUT.parent / "tier1_manifest.csv"
    with open(mpath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0]))
        w.writeheader()
        w.writerows(manifest)
    okn = sum(1 for m in manifest if m["status"].startswith("ok"))
    print(f"\n{okn}/{len(manifest)} files fetched, {sum(m['bytes'] for m in manifest)/1e6:.1f} MB")
    for m in manifest:
        if not m["status"].startswith("ok"):
            print(f"  NOT OK  {m['record']:16} {m['filename'][:58]}  {m['status']}")
    print(f"manifest -> {mpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
