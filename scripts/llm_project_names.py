#!/usr/bin/env python3
r"""llm_project_names.py -- read whether the City's own records give a housing development a NAME.

John, 2026-09-30: every project is DISPLAYED by its address (sourced); a proper name is added only where the
City's own text states one, quoted word for word. Telling "Acheson Commons" from "2131 University" or from "AUP:
910 Indian Rock Avenue" is a reading of prose, so a model reads it against the written definition below -- and the
build accepts a name only if it appears VERBATIM in the record the model cites, so an invented name cannot land.

READ ONCE, STORE, LOOK UP (scripts/model_readers.py): the answers go to data/derived/project_names_evidence_<date>.json
keyed by the project's STABLE key -- its anchor Planning record, or its first master permit when it has no
application -- never by project_id, which a rebuild may renumber. Nothing here writes to a database.

  .venv/bin/python scripts/llm_project_names.py --dry-run
  .venv/bin/python scripts/llm_project_names.py --sonnet submit|status|collect [--pack 12]
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import model_readers as mr  # noqa: E402

V4 = ROOT / "databases/berkeley_housing_v4.db"
OUT = ROOT / "scratch/2026-09-30_names"

DEFINITION = """A development NAME is a proper name the City's record gives this housing development or its building:
examples are "Acheson Commons", "The Overture", "Logan Park", "El Jardin", "The Den", "Hope Center", "Anchor House".
These are NOT names:
- a street address ("2131 University Ave", "2029-2035 Blake Street"), even when written as a title;
- a permit or process label ("Use Permit Modification", "AUP: 910 Indian Rock Avenue", "UPPH: 3036 Regent", "Final Design Review");
- a description of the building ("6 story mixed use building", "New apartment building", "ADU", "duplex");
- the name of a person, applicant, owner, company, architect or business tenant ("Wells Fargo", "Panoramic Interests").
If the record states no name, answer null. Never invent, translate or complete a name: copy it exactly as written."""


def records_text():
    """project key -> [(source key, text)], read-only from live v4 + the list dumps (Project Name field)."""
    db = sqlite3.connect(f"file:{V4}?mode=ro", uri=True)
    listing = {}
    for fn in glob.glob(str(ROOT / "data/raw/accela/date_range/Planning_*.jsonl")):
        for line in open(fn):
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("Record Number"):
                listing[d["Record Number"]] = d
    planning = {}
    for k, pl in db.execute("SELECT source_record_key, raw_payload FROM events WHERE event_type_code='planning_filed'"):
        planning[k] = json.loads(pl)
    permit_desc = dict(db.execute("SELECT source_record_key, MAX(raw_description) FROM events "
                                  "WHERE event_type_code LIKE 'permit_%' GROUP BY 1"))
    masters = {sid: json.loads(n)["master_permits"] for sid, n in db.execute("SELECT structure_id, notes FROM structures")}
    out = {}
    for pid, notes in db.execute("SELECT project_id, notes FROM projects"):
        n = json.loads(notes)
        sids = [s for (s,) in db.execute("SELECT structure_id FROM project_structures WHERE project_id=?", (pid,))]
        mps = [m for s in sids for m in masters[s]]
        key = n.get("anchor") or (sorted(mps)[0] if mps else None)
        if not key:
            continue
        texts = []
        for rec in ([n["anchor"]] if n.get("anchor") else []) + [r for r in (n.get("records") or []) if r != n.get("anchor")][:3]:
            pn = (listing.get(rec, {}).get("Project Name") or "").strip()
            desc = (planning.get(rec, {}).get("description") or listing.get(rec, {}).get("Description") or "").strip()
            t = " | ".join(x for x in (pn, desc) if x)
            if t:
                texts.append((rec, t[:600]))
        for m in mps[:3]:
            if permit_desc.get(m):
                texts.append((m, permit_desc[m][:400]))
        if texts:
            out[key] = texts
    return out


def verify(answer: dict, texts: list) -> str | None:
    """the name, only if it appears VERBATIM (case-insensitive, whitespace-normalised) in the cited source text."""
    name = (answer.get("name") or "").strip()
    src = answer.get("source")
    if not name:
        return None
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
    for k, t in texts:
        if k == src and norm(name) in norm(t):
            return name
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"])
    ap.add_argument("--pack", type=int, default=12)
    a = ap.parse_args()
    recs = records_text()
    keys = sorted(recs)
    print(f"{len(keys)} projects with text to read")
    groups = [keys[i:i + a.pack] for i in range(0, len(keys), a.pack)]
    state = OUT / "sonnet_batch_state.json"

    def prompt(g):
        body = "\n\n".join(f"PROJECT {k}\n" + "\n".join(f"  [{s}] {t}" for s, t in recs[k]) for k in g)
        return (f"You are reading City of Berkeley records about {len(g)} housing projects. Judge each project on its "
                f"own text only.\n\n{DEFINITION}\n\nFor EACH project, answer with a JSON array only, one object per "
                f"project, in order:\n[{{\"project\": <PROJECT key>, \"name\": <the name copied exactly, or null>, "
                f"\"source\": <the [bracketed] key of the text the name is copied from, or null>}}]\n\n{body}")

    if a.dry_run:
        print(prompt(groups[0])[:3000])
        tok = sum(len(prompt(g)) for g in groups) / 4
        print(f"\n{len(groups)} requests, ~{tok/1e6:.2f}M input tokens (Batch, Sonnet). NOTHING ASKED.")
        return 0
    if a.sonnet == "submit":
        OUT.mkdir(parents=True, exist_ok=True)
        reqs = [{"custom_id": f"g{i}", "params": {"model": mr.BATCH_MODEL, "max_tokens": 120 * len(g) + 400,
                 "messages": [{"role": "user", "content": prompt(g)}]}} for i, g in enumerate(groups)]
        (OUT / "groups.json").write_text(json.dumps(groups))
        mr.batch_submit(reqs, state)
        return 0
    if a.sonnet == "status":
        mr.batch_status(state)
        return 0
    if a.sonnet == "collect":
        groups = json.loads((OUT / "groups.json").read_text())
        rows, bad = [], []
        for cid, parsed, raw, _ in mr.batch_results(state):
            g = groups[int(cid[1:])]
            got = {str(x.get("project")): x for x in (parsed or []) if isinstance(x, dict)}
            for k in g:
                ans = got.get(k)
                if ans is None:
                    bad.append(k)
                    continue
                v = verify(ans, recs[k])
                rows.append({"project_key": k, "name_proposed": ans.get("name"), "source": ans.get("source"),
                             "name": v, "verbatim": bool(v) if ans.get("name") else None})
        named = [r for r in rows if r["name"]]
        rejected = [r for r in rows if r["name_proposed"] and not r["name"]]
        print(f"answers {len(rows)}; names accepted (verbatim) {len(named)}; proposed but NOT verbatim, rejected "
              f"{len(rejected)}; unanswered {len(bad)}")
        mr.write_evidence(rows, "project_names", DEFINITION,
                          extra={"source": "live v4 projects + Accela list Project Name + record/permit descriptions",
                                 "model": mr.BATCH_MODEL, "rule": "accepted only if verbatim in the cited source text",
                                 "unanswered": bad})
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
