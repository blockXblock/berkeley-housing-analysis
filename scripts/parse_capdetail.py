#!/usr/bin/env python3
"""parse_capdetail.py -- extract the CapDetail facts the existing harvester throws away.

`experiments/accela_scrape/inspection_scraper.py` visits CapDetail and keeps ONLY the inspection
table. The same page also carries the city's own record of its own processing performance -- the
PROCESSING STATUS workflow: every department review task, its DUE date, the disposition it was
MARKED as, the date it was marked, and the staff member who marked it. That is what turns
filed -> ACCEPTED -> entitled into dated events instead of an inference, and it is the shape
already present in the 95 hand-captured files in data/raw/accela_status/*.txt.

Parse only -- no network, no DB write. Validated against
data/raw/accela_status/ZP2021-0046_2136_SAN_PABLO_Ave.txt (8 tasks, 6 with a disposition).

Anchoring notes (learned from a live probe, scratch/2026-09-26_capdetail/):
  * Processing Status lives in a HIDDEN tab, so page.inner_text() misses it entirely -- parse the
    HTML, not the rendered text. The block is AJAX-filled by ExpandWorkflowSection(); it is present
    a few seconds after domcontentloaded without any click.
  * Task rows have NO stable id and nested tables duplicate them; the only reliable structure is
    the DIRECT tr children of the outer table in #divProcessingTable, alternating name row / detail
    row.
  * Header field ids carry a volatile numeric suffix (label_project639260346545086368), so header
    fields are found by LABEL TEXT, never by id.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

# record numbers come in two shapes: ZP2021-0046 AND ESR-2022-01158 (see parse_related_records)
_RECNO = re.compile(r"\b[A-Z]{1,5}-?\d{4}-\d{3,5}\b")

_DISP = re.compile(
    r"Due on\s*(?P<due>\d{1,2}/\d{1,2}/\d{4})?"
    r"(?:\s*,\s*assigned to\s*(?P<assigned>.*?))?"
    r"\s*Marked as\s*(?P<status>.*?)\s*on\s*(?P<marked>\d{1,2}/\d{1,2}/\d{4})"
    r"(?:\s*by\s*(?P<by>.*?))?"
    r"(?=\s*(?:Due on|Comment:|$))",
    re.S,
)


def _txt(el) -> str:
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def _iso(mdy: str | None) -> str | None:
    if not mdy:
        return None
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})$", mdy.strip())
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else None


def parse_processing_status(soup: BeautifulSoup) -> list[dict]:
    """PROCESSING STATUS -> one dict per DISPOSITION, in page order.

    A task with no disposition yet (Public Hearing never held) still yields a row, with
    status=None -- that pending-ness is itself the signal that the record is mid-pipeline.
    A task can carry SEVERAL dispositions (Completeness Review: Incomplete Pending Applicant,
    then Application Complete) and each is its own row, with seq counting within the task.
    """
    div = soup.find(id="divProcessingTable")
    if not div:
        return []
    table = div.find("table")
    body = table.find("tbody") if table else None
    if not body:
        return []
    rows = body.find_all("tr", recursive=False)

    out: list[dict] = []
    task = None
    for tr in rows:
        t = _txt(tr)
        if not t:
            continue
        if "Due on" not in t and "Comment:" not in t:
            task = t                      # a task-name row
            out.append({"task": task, "seq": 0, "due_date": None, "assigned_to": None,
                        "status": None, "status_date": None, "status_by": None, "comment": None})
            continue
        if task is None:
            continue
        hits = list(_DISP.finditer(t))
        if not hits:
            continue
        cm = re.search(r"Comment:\s*(.+?)\s*$", t)
        comment = cm.group(1) if cm else None
        # the placeholder row added at the task name is replaced by its real dispositions
        if out and out[-1]["task"] == task and out[-1]["status"] is None and out[-1]["seq"] == 0:
            out.pop()
        for n, m in enumerate(hits):
            d = m.groupdict()
            out.append({
                "task": task,
                "seq": n,
                "due_date": _iso(d["due"]),
                "assigned_to": (d["assigned"] or "").strip() or None,
                "status": (d["status"] or "").strip() or None,
                "status_date": _iso(d["marked"]),
                "status_by": (d["by"] or "").strip() or None,
                "comment": comment if n == len(hits) - 1 else None,
            })
        task = None                       # each task has exactly one detail row
    return out


_PARCEL = re.compile(r"Parcel Number:\s*([0-9A-Za-z][0-9A-Za-z \-]*?)\s*(?:\*|<|$)")


def parse_parcels(soup: BeautifulSoup) -> list[str]:
    """the APNs the city itself attaches to the record, from the hidden More Details block.

    Source-faithful strings only (ADR-003 apn_raw). The canonical form is produced by
    housing_rules.to_canonical_apn -- NEVER a local re-implementation (CLAUDE.md rule 4).
    Observed format here is '056 197701101' (space-separated), which the canon function accepts.
    """
    div = soup.find(id=re.compile(r"palParceList$"))
    if not div:
        return []
    return sorted({m.group(1).strip() for m in _PARCEL.finditer(div.get_text(" ", strip=False))})


def parse_related_records(soup: BeautifulSoup) -> list[dict]:
    """Related Records -> the linked records, with the RELATIONSHIP where the page states it.

    This is the non-APN edge: a record naming another record directly, which survives the
    re-platting that makes APNs unusable as identity (CLAUDE.md rule 4).

    Two corrections measured 2026-09-26 against scratch/2026-09-26_capdetail_look/:
      * the tab lists the record ITSELF as the tree root, so self must be excluded or every
        record appears to reference something;
      * record numbers are NOT all `PREFIX2022-0001` -- B2022-02844's parent is `ESR-2022-01158`
        (prefix, hyphen, year, hyphen, serial). A pattern written from Planning records alone
        silently drops that whole family.
    The page states direction in prose ("parent to permit B2022-02844"), so it is kept verbatim
    rather than interpreted here.
    """
    div = soup.find(id="tab-related_records")
    if not div:
        return []
    self_num = None
    hdr = soup.find(id=re.compile(r"lblPermitNumber$")) or soup.find(id=re.compile(r"lblCapID$"))
    if hdr:
        self_num = _txt(hdr)
    if not self_num:
        m = re.search(r"Record\s+([A-Z]{1,5}-?\d{4}-\d{3,5}):", _txt(soup.find("body") or soup))
        self_num = m.group(1) if m else None

    out, seen = [], set()
    for tr in div.find_all("tr"):
        cells = [_txt(td) for td in tr.find_all("td")]
        row = " ".join(cells)
        for m in _RECNO.finditer(row):
            num = m.group(0)
            if num == self_num or num in seen:
                continue
            seen.add(num)
            rel = re.search(r"\(([^)]*\b(?:parent|child|related)\b[^)]*)\)", row, re.I)
            out.append({"record": num,
                        "relationship": rel.group(1) if rel else None,
                        "row": row[:200] or None})
    return out


_LABELS = {
    "Project Description:": "description",
    "Owner:": "owner",
    "Applicant:": "applicant",
    "Parcel Number:": "parcel",
    "District:": "district",
}


def parse_record_details(soup: BeautifulSoup) -> dict:
    """header + Record Details, found by LABEL TEXT because the span ids are volatile."""
    d: dict = {}
    st = soup.find(id=re.compile(r"lblRecordStatus$"))
    d["record_status"] = _txt(st) or None
    wl = _txt(soup.find(id="tbl_worklocation"))
    # CapDetail's work-location cell carries page furniture that would corrupt any address key:
    # a trailing "*" (the county-situs marker) and, for a multi-frontage site, a
    # "View Additional Locations>> 1) ... 2) ..." tail. Those are artifacts of THIS page, so they
    # are cleaned here rather than in the shared address normalizer
    # (housing_rules.address.normalize_address, the rule-4c canon), which is correct for real
    # addresses and must not learn one source's quirks. The canon already drops a trailing "*";
    # what it cannot know is the "View Additional Locations" tail, which is this page's invention.
    extra = []
    m = re.search(r"View Additional Locations\s*>*\s*(.*)$", wl, re.S)
    if m:
        wl = wl[:m.start()]
        extra = [x.strip() for x in re.split(r"\d+\)", m.group(1)) if x.strip()]

    def _clean(a: str) -> str:
        return re.sub(r"\s+", " ", a.replace("*", " ")).strip(" ,;")

    d["work_location"] = _clean(wl) or None
    d["work_locations_all"] = sorted({_clean(x) for x in [wl] + extra if _clean(x)}) or None
    for span in soup.find_all("span"):
        lab = _txt(span)
        key = _LABELS.get(lab)
        if not key or d.get(key):
            continue
        h1 = span.find_parent("h1")
        sib = (h1 or span).find_next_sibling("span")
        d[key] = _txt(sib) or None
    return d


def parse_capdetail(page_html: str) -> dict:
    soup = BeautifulSoup(page_html, "lxml")
    return {
        **parse_record_details(soup),
        "parcels_raw": parse_parcels(soup),
        "processing_status": parse_processing_status(soup),
        "related_records": parse_related_records(soup),
    }
