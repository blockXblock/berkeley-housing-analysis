#!/usr/bin/env python3
r"""accela_grid.py -- THE one way to open and page an Accela CapDetail attachment grid.

WHY A MODULE. This logic has now been written three times: once in
experiments/accela_scrape/harvest_plansets.py (correctly, June), once in
list_affordability_statements.py (which TESTED the pager and never fired it, so every record with
more than 10 attachments reported exactly 10 -- 33 of 105 records), and once more the moment a
fetcher needed the same walk. CLAUDE.md's standing lesson is that an anonymous rule gets
re-invented, and re-invented wrong. This is its named home; import it, never re-type it.

WHAT IT KNOWS, each part paid for:
  * the tab must be activated with handlePortletNavigation(a) -- a plain a.click() does nothing, and
    an un-clicked tab shows only the upload widget, which LOOKS like "no attachments";
  * the grid lives in an IFRAME that only fills after that click, so rows must be POLLED for, never
    read once after a fixed sleep (harvest_plansets: "proj27: 0 in batch, 3 on isolated re-run");
  * advancing a page means FIRING __doPostBack AND then waiting for the first row to change --
    firing without checking inflated one record 8x (10 files read eight times, reported as 80);
    checking without firing truncated 33 records to page 1;
  * the pager publishes its own page count in its numbered links, so a short walk RAISES rather than
    returning a plausible-looking partial list.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "hp", ROOT / "experiments/accela_scrape/harvest_plansets.py")
hp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hp)                 # read_rows, find_next, grid_size_bytes, IFRAME_ID

BASE = "https://aca-prod.accela.com"
read_rows, grid_size_bytes = hp.read_rows, hp.grid_size_bytes


def open_grid(page, href: str, poll: int = 15):
    """navigate to a CapDetail page, click the attachments tab, return the populated grid frame."""
    page.goto(BASE + href, wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    ok = page.evaluate("""() => {const a=document.querySelector('a[data-control="tab-attachments"]');
                          if(!a||typeof handlePortletNavigation!=='function')return 'no';
                          handlePortletNavigation(a);return 'ok';}""")
    if ok != "ok":
        raise RuntimeError("attachment grid activation failed")
    page.wait_for_timeout(2500)
    el = page.wait_for_selector(f"#{hp.IFRAME_ID}", state="attached", timeout=30000)
    frame = el.content_frame()
    try:
        frame.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    for _ in range(poll):
        if read_rows(frame):
            break
        page.wait_for_timeout(1000)
    return frame


def declared_pages(frame) -> int:
    """how many pages the grid ITSELF says it has, from its numbered pager links."""
    return frame.evaluate("""() => {
        let mx = 1;
        for (const a of document.querySelectorAll("a[href*='__doPostBack']")) {
            const t = (a.innerText || '').trim();
            if (/^[0-9]{1,3}$/.test(t)) mx = Math.max(mx, parseInt(t, 10));
        }
        return mx;
    }""")


def walk(page, frame, max_pages: int = 40):
    """yield each grid page's rows, in order, advancing the pager properly.

    Rows carry `target` (the row's own __doPostBack id), so a caller that wants to DOWNLOAD a file
    must act while it is on that file's page -- which is why this is a generator and not a function
    returning one flat list.

    Raises if fewer pages were walked than the grid declared: a truncated read must be VISIBLE.
    """
    declared = declared_pages(frame)
    pages = 0
    while pages < max_pages:
        rows = read_rows(frame)
        yield rows
        pages += 1
        nxt = hp.find_next(frame)
        if not nxt:
            break
        sig = (rows[0]["target"], rows[0]["filename"]) if rows else None
        frame.evaluate(f"__doPostBack('{nxt['target']}','')")
        changed = False
        for _ in range(16):
            page.wait_for_timeout(500)
            try:
                after = read_rows(frame)
            except Exception:
                after = []
            if after and (after[0]["target"], after[0]["filename"]) != sig:
                changed = True
                break
        if not changed:
            break
    if pages < declared:
        raise RuntimeError(f"truncated: walked {pages} of {declared} declared pages")
