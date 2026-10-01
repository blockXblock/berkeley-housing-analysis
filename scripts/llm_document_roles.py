#!/usr/bin/env python3
r"""llm_document_roles.py -- read WHO each party is, by role, from the project documents held in R2: the plan sets'
cover sheets and title blocks, application forms, density-bonus applications, tabulation forms, Zoning Board packets.

John, 2026-10-01: "pull the title block". The City's permit pages name the builder (contractor) and the owner, but
never the architect or the developer; the drawings do ("Grosvenor Americas", "Solomon Cordwell Buenz"). Each party is
KEPT only if its quote appears VERBATIM in the document's text AND contains the party's name -- so a name cannot be
invented or carried from another project.

  --extract   download each document (v4 `documents`), verify its SHA-256 against the row, keep the text of its
              opening pages (cover, project team, first title block), delete the file. Resumable. A document with no
              text layer (a scan) is recorded as such, never guessed.
  --sonnet submit|status|collect   the quoted read -> data/derived/document_roles_evidence_<date>.json

No database write. Reads the documents table of --db.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import model_readers as mr  # noqa: E402

OUT = ROOT / "scratch/2026-10-01_doc_roles"
TEXTS = OUT / "texts.jsonl"
TYPES = ("plan_set", "application", "density_bonus_application", "tabulation_form", "zab_packet", "staff_report",
         "affordable_housing_agreement", "correspondence")
PAGES = 3                     # cover sheet, project team / data sheet, the first drawing's title block
CHARS = 7000

ROLES = ("developer", "owner", "applicant", "architect", "landscape_architect", "structural_engineer", "civil_engineer",
         "mep_engineer", "general_contractor", "property_manager", "lender", "investor", "other")

DEFINITION = """From this City of Berkeley project document's own text (a plan set's cover sheet / project team / title
block, or an application form), list every PARTY it names with the ROLE the document gives it:
developer, owner, applicant, architect, landscape_architect, structural_engineer, civil_engineer, mep_engineer
(mechanical / electrical / plumbing), general_contractor, property_manager, lender, investor, or other (say which in
"label"). Use the role the document STATES ("Owner/Developer:", "Architect:", "Applicant", a title-block firm labelled
as the architect); if a firm appears with no stated role, use other with label "unlabelled". A company on a copyright
line or title block of an architecture firm is the architect only if the document makes that clear.
For each party give its name exactly as written, a licence number if the text states one, and copy the exact words that
show the name together with its role."""


def docs(dbp):
    db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    q = ("SELECT document_id, record_key, doc_type, title, store_url, sha256 FROM documents WHERE doc_type IN (%s) "
         "ORDER BY document_id" % ",".join("?" * len(TYPES)))
    return db.execute(q, TYPES).fetchall()


def extract(dbp):
    import pymupdf
    OUT.mkdir(parents=True, exist_ok=True)
    done = {d["document_id"] for d in map(json.loads, open(TEXTS)) if "error" not in d} if TEXTS.exists() else set()
    rows = [r for r in docs(dbp) if r[0] not in done]
    print(f"{len(done)} already extracted, {len(rows)} to go")
    tmp = OUT / "current.pdf"
    for i, (did, rec, typ, title, url, sha) in enumerate(rows, 1):
        rec_out = {"document_id": did, "record_key": rec, "doc_type": typ, "title": title, "url": url}
        try:
            h = hashlib.sha256()
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.7.1"})   # the CDN refuses Python's default UA
            with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 20):
                    h.update(chunk)
                    f.write(chunk)
            rec_out["sha_ok"] = (not sha) or h.hexdigest() == sha
            d = pymupdf.open(tmp)
            text = "\n".join(d[p].get_text() for p in range(min(PAGES, d.page_count)))
            text = re.sub(r"[ \t]+", " ", text)
            rec_out.update(pages=d.page_count, text=text[:CHARS], text_layer=bool(text.strip()))
            d.close()
        except Exception as e:
            rec_out.update(error=str(e)[:200])
        finally:
            tmp.unlink(missing_ok=True)
        with open(TEXTS, "a") as f:
            f.write(json.dumps(rec_out) + "\n")
        print(f"  [{i}/{len(rows)}] {did} {typ} {'ok' if rec_out.get('text_layer') else rec_out.get('error') or 'NO TEXT LAYER'}",
              flush=True)


def norm(x):
    return re.sub(r"\s+", " ", str(x or "")).strip().lower()


def verify(ans, text):
    t = norm(text)
    kept = []
    for p in ans.get("parties") or []:
        name, role, q = p.get("name"), p.get("role"), p.get("quote")
        if not (name and q and role in ROLES) or norm(q) not in t or norm(name) not in norm(q):
            continue
        lic = p.get("license")
        kept.append({"name": name, "role": role, "label": p.get("label"), "quote": q,
                     "license": lic if lic and norm(lic) in t else None})
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"])
    a = ap.parse_args()
    if a.extract:
        extract(Path(a.db))
        return 0
    state = OUT / "sonnet_batch_state.json"
    recs = {str(r["document_id"]): r for r in map(json.loads, open(TEXTS)) if r.get("text_layer")}
    keys = sorted(recs, key=int)
    print(f"{len(keys)} documents with a text layer")

    def prompt(k):
        r = recs[k]
        return (f"{DEFINITION}\n\nAnswer with JSON only: {{\"parties\": [{{\"name\": ..., \"role\": ..., \"label\": <or null>, "
                f"\"license\": <or null>, \"quote\": <exact words>}}]}}\n\nDOCUMENT {k} ({r['doc_type']}, record "
                f"{r['record_key']}, \"{r['title']}\"):\n{r['text']}")

    if a.dry_run:
        print(prompt(keys[0])[:3000])
        print(f"\n{len(keys)} requests, ~{sum(len(prompt(k)) for k in keys)/4/1e6:.2f}M input tokens. NOTHING ASKED.")
        return 0
    if a.sonnet == "submit":
        mr.batch_submit([{"custom_id": f"d{k}", "params": {"model": mr.BATCH_MODEL, "max_tokens": 2500,
                          "messages": [{"role": "user", "content": prompt(k)}]}} for k in keys], state)
        return 0
    if a.sonnet == "status":
        mr.batch_status(state)
        return 0
    if a.sonnet == "collect":
        rows, rejected, unanswered = [], 0, []
        for cid, parsed, raw, _ in mr.batch_results(state):
            k = cid[1:]
            got = parsed[0] if isinstance(parsed, list) and parsed else parsed
            if not isinstance(got, dict):
                unanswered.append(k)
                continue
            kept = verify(got, recs[k]["text"])
            rejected += len(got.get("parties") or []) - len(kept)
            rows.append({"document_id": int(k), "record_key": recs[k]["record_key"], "doc_type": recs[k]["doc_type"],
                         "parties": kept})
        print(f"documents {len(rows)}; parties kept {sum(len(r['parties']) for r in rows)}; rejected (quote not verbatim"
              f" or name not in quote) {rejected}; unanswered {len(unanswered)}")
        mr.write_evidence(rows, "document_roles", DEFINITION,
                          extra={"model": mr.BATCH_MODEL, "pages_read": PAGES, "chars": CHARS,
                                 "rule": "kept only if the quote is verbatim in the text and contains the name",
                                 "unanswered": unanswered})
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
