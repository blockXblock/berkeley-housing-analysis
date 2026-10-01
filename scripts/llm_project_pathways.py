#!/usr/bin/env python3
r"""llm_project_pathways.py -- read which STATE-LAW PATHWAY(S) the City's records say a housing project uses.

Cutover phase 4 (John, 2026-09-30). v2 carried 73 hand tags (density bonus 54, SB 330 15, SB 35 2, AB 2011 2); v4
re-derives them from the City's own text. A pathway is prose ("requesting a 50% density bonus", "SB 35 application",
"Preliminary Application under SB 330"), so a model reads it against the written definition below; every pathway it
reports must come with a quote that appears VERBATIM in the record it cites, or the build drops it. Where the City's
own 2026 master log (CPRA 26-1972) states a pathway in a column, that statement is evidence too and is passed in.

READ ONCE, STORE, LOOK UP (scripts/model_readers.py): data/derived/project_pathways_evidence_<date>.json, keyed by the
project's stable key (anchor record, else first master permit). Nothing here writes to a database.

  .venv/bin/python scripts/llm_project_pathways.py --dry-run
  .venv/bin/python scripts/llm_project_pathways.py --sonnet submit|status|collect
  .venv/bin/python scripts/llm_project_pathways.py --eval      # vs v2's tags (a comparison, not ground truth)
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import model_readers as mr  # noqa: E402

V4 = ROOT / "databases/berkeley_housing_v4.db"
OUT = ROOT / "scratch/2026-09-30_pathways"
PATHWAYS = ("density_bonus", "sb330_preliminary", "sb35_streamlined", "ab2011", "sb9", "sb684_small_lot", "ab2162_supportive")

DEFINITION = """Report each California STATE-LAW PATHWAY that the record's own text says this housing project uses or applies under.
- density_bonus: the State Density Bonus Law (Gov. Code 65915): "density bonus", "DBL", "waivers/concessions" under it.
- sb330_preliminary: a Housing Crisis Act / SB 330 PRELIMINARY APPLICATION (Gov. Code 65941.1), or "SB 330" vesting.
- sb35_streamlined: SB 35 / SB 423 streamlined ministerial approval (Gov. Code 65913.4).
- ab2011: AB 2011 / the Affordable Housing and High Road Jobs Act (Gov. Code 65912.100).
- sb9: SB 9 two-unit development or urban lot split (Gov. Code 65852.21, 66411.7).
- sb684_small_lot: SB 684 / SB 1123 small-lot subdivision.
- ab2162_supportive: AB 2162 by-right supportive housing.
Report ONLY what the text states. Do not infer a pathway from a unit count, an affordability level, a building size, or a
zoning district. A mention that a law does NOT apply ("not an SB 35 project") is not a pathway. If none is stated, return
an empty list. For each pathway, copy the exact words that state it."""


def project_texts(dbp=V4):
    db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    planning = {k: json.loads(p) for k, p in db.execute(
        "SELECT source_record_key, raw_payload FROM events WHERE event_type_code='planning_filed'")}
    log = {}
    for k, p in db.execute("SELECT source_record_key, raw_payload FROM events WHERE event_type_code='planning_log_entry'"):
        d = json.loads(p)
        bits = [f"{c}: {d[c]}" for c in d if re.search(r"(?i)density bonus|streamlin|preliminary|waiver|concession", c)]
        if bits:
            log.setdefault(k, []).append("CITY 2026 MASTER LOG -- " + "; ".join(bits))
    masters = {sid: json.loads(n)["master_permits"] for sid, n in db.execute("SELECT structure_id, notes FROM structures")}
    out = {}
    for pid, notes in db.execute("SELECT project_id, notes FROM projects"):
        n = json.loads(notes)
        if not n.get("anchor"):
            continue                                   # pathways attach to APPLICATIONS; building-only projects have none
        key = n["anchor"]
        texts = []
        for rec in [key] + [r for r in (n.get("records") or []) if r != key][:5]:
            r = planning.get(rec, {})
            t = (r.get("description") or "").strip()
            if t:
                texts.append((rec, f"{r.get('record_type')}: {t}"[:700]))
            for line in log.get(rec, []):
                texts.append((rec + "#log", line[:500]))
        if texts:
            out[key] = texts
    return out


def verify(items, texts):
    """keep only pathways in the vocabulary whose quote appears verbatim in the cited text."""
    norm = lambda s: re.sub(r"\s+", " ", s or "").strip().lower()
    src = {k: norm(t) for k, t in texts}
    keep = []
    for it in items or []:
        p, q, s = it.get("pathway"), it.get("quote"), str(it.get("source") or "").strip().strip("[]").strip()
        if p in PATHWAYS and q and s in src and norm(q) in src[s]:
            keep.append({"pathway": p, "quote": q, "source": s})
    return keep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"])
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--pack", type=int, default=10)
    ap.add_argument("--db", default=str(V4), help="read projects from this v4 DB (read-only), e.g. a verified build")
    ap.add_argument("--retry-unanswered", action="store_true",
                    help="submit / collect ONLY the projects the stored reading left unanswered, merged into it")
    a = ap.parse_args()
    tag = "_retry" if a.retry_unanswered else ""
    state = OUT / f"sonnet_batch_state{tag}.json"
    if a.eval:
        ev = json.load(open(ROOT / "scratch/2026-09-30_cycle2/pathway_eval_set.json"))
        ed = sorted(ROOT.glob("data/derived/project_pathways_evidence_*.json"))[-1]
        got = {r["project_key"]: {x["pathway"] for x in r["pathways"]} for r in json.load(open(ed))["readings"]}
        db = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
        key = {pid: json.loads(n).get("anchor") for pid, n in db.execute("SELECT project_id, notes FROM projects")}
        mp = {"density_bonus": "density_bonus", "sb330": "sb330_preliminary", "sb35": "sb35_streamlined", "ab2011": "ab2011"}
        agree = [(p, c) for p, c, _ in ev if mp[c] in got.get(key[p], set())]
        print(f"v2 tags {len(ev)}; the reading agrees on {len(agree)}")
        for p, c, v2pid in ev:
            if (p, c) not in agree:
                print(f"   missed {c:<14} v4 project {p} anchor {key[p]} (v2 proj{v2pid}); reading said {sorted(got.get(key[p], []))}")
        return 0
    recs = project_texts(Path(a.db))
    keys = sorted(recs)
    prior = None
    if a.retry_unanswered:
        prior_path = sorted(ROOT.glob("data/derived/project_pathways_evidence_*.json"))[-1]
        prior = json.load(open(prior_path))
        keys = sorted(set(prior["unanswered"]) & set(recs))
        a.pack = min(a.pack, 3)
    groups = [keys[i:i + a.pack] for i in range(0, len(keys), a.pack)]
    print(f"{len(keys)} application-anchored projects with text")

    def prompt(g):
        body = "\n\n".join(f"PROJECT {k}\n" + "\n".join(f"  [{s}] {t}" for s, t in recs[k]) for k in g)
        return (f"You are reading City of Berkeley Planning records for {len(g)} housing projects. Judge each project on "
                f"its own text only.\n\n{DEFINITION}\n\nAnswer with a JSON array only, one object per project, in order:\n"
                f"[{{\"project\": <PROJECT key>, \"pathways\": [{{\"pathway\": <one of {list(PATHWAYS)}>, \"quote\": "
                f"<exact words>, \"source\": <the [bracketed] key>}}]}}]\n\n{body}")

    if a.dry_run:
        print(prompt(groups[0])[:2500])
        print(f"\n{len(groups)} requests, ~{sum(len(prompt(g)) for g in groups)/4/1e6:.2f}M input tokens (Batch, Sonnet). NOTHING ASKED.")
        return 0
    if a.sonnet == "submit":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"groups{tag}.json").write_text(json.dumps(groups))
        mr.batch_submit([{"custom_id": f"g{i}", "params": {"model": mr.BATCH_MODEL, "max_tokens": 1200 * len(g) + 800,
                          "messages": [{"role": "user", "content": prompt(g)}]}} for i, g in enumerate(groups)], state)
        return 0
    if a.sonnet == "status":
        mr.batch_status(state)
        return 0
    if a.sonnet == "collect":
        groups = json.loads((OUT / f"groups{tag}.json").read_text())
        rows, unanswered, dropped = [], [], 0
        for cid, parsed, raw, _ in mr.batch_results(state):
            got = {str(x.get("project")): x for x in (parsed or []) if isinstance(x, dict)}
            for k in groups[int(cid[1:])]:
                if k not in got:
                    unanswered.append(k)
                    continue
                kept = verify(got[k].get("pathways"), recs[k])
                dropped += len(got[k].get("pathways") or []) - len(kept)
                rows.append({"project_key": k, "pathways": kept})
        print(f"answers {len(rows)}; projects with a pathway {sum(1 for r in rows if r['pathways'])}; pathways dropped "
              f"(not verbatim / not in vocabulary) {dropped}; unanswered {len(unanswered)}")
        if prior is not None:                       # MERGE: keep every earlier answer, add the retried ones
            have = {r["project_key"] for r in rows}
            rows = [r for r in prior["readings"] if r["project_key"] not in have] + rows
            prior_path.rename(OUT / f"{prior_path.stem}_before_retry.json")
            print(f"merged: {len(rows)} readings; still unanswered {len(unanswered)}")
        mr.write_evidence(rows, "project_pathways", DEFINITION,
                          extra={"model": mr.BATCH_MODEL, "rule": "kept only if the quote is verbatim in the cited text",
                                 "unanswered": unanswered})
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
