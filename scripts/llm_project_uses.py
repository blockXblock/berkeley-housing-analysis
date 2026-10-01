#!/usr/bin/env python3
r"""llm_project_uses.py -- read what the City's own text says about a project's NON-RESIDENTIAL space and TENURE, and
what each later City record at its buildings says about a business there.

John, 2026-10-01: "load the commercial records for mixed-use projects" -- then read them, and extract what else is
useful. Two readings, one definition each, every value KEPT ONLY with a quote that appears VERBATIM in the cited
record (a number only if the quote contains it; a tenure only if the quote names it):

  --target projects   per project (its Planning descriptions + master building-permit descriptions):
                      commercial_sqft, commercial_spaces, commercial_uses, tenure_stated (rental / ownership / mixed)
  --target listings   per City record listed at a project's building addresses beyond the project's own records
                      (v_project_records_listed): is it about a non-residential space or business, the business name,
                      the kind of use, the action (new business, tenant improvement, sign, closure, change of use),
                      stated sq ft; and whether it is a condominium map / conversion (for-sale tenure evidence)

Evidence: data/derived/project_uses_evidence_<date>.json and listing_uses_evidence_<date>.json (append-only).
No database write. Reads a BUILD DB that has the views (build_views.py).

  .venv/bin/python scripts/llm_project_uses.py --target projects|listings --dry-run --db BUILD
  .venv/bin/python scripts/llm_project_uses.py --target projects|listings --sonnet submit|status|collect --db BUILD
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
from llm_building_measures import project_texts, _has_number  # noqa: E402  (the same texts the measures read)

OUT = ROOT / "scratch/2026-10-01_uses"

DEF_PROJECTS = """Report what this housing project's own text states about NON-RESIDENTIAL space and about TENURE:
- commercial_sqft: square feet of commercial / retail / office / restaurant space ("5,000 sq.ft. of commercial space").
  Not residential area, not the building's gross area, not lot size. null if not stated.
- commercial_spaces: the number of commercial spaces or storefronts, if stated as a number. null otherwise.
- commercial_uses: the kinds of non-residential use the text names (e.g. "retail", "restaurant", "office",
  "community space"), as a short list of the text's own words. null if none named.
- tenure_stated: "rental" if the text says the homes are rental / for rent / apartments for rent; "ownership" if it says
  condominiums / for sale / ownership units; "mixed" if it states both; null if it does not say.
For each, copy the exact words that state it and give the record key they come from."""

DEF_LISTINGS = """For each City record below, judge from its own type and text only:
- non_residential: true if the record concerns a commercial / retail / office / restaurant space or a business
  (a business licence, a store's tenant improvement, a business sign, a change of use to commercial); false if it is
  about the dwellings, the building's systems, or construction of the building; null if the text does not say.
- business_name: the business's name if the text states it ("Cold Stone Creamery"), else null.
- use_kind: the kind of business or use in a few of the text's own words ("ice cream shop", "restaurant"), else null.
- action: one of "new_business", "tenant_improvement", "sign", "change_of_use", "closure", "other", or null.
- sqft: square feet the text states for the space, else null.
- condominium: true if the record is a condominium map, condominium conversion or subdivision for condominiums
  (homes created for sale); else false.
For every non-null value copy the exact words that state it."""

TENURE_WORDS = {"rental": ("rent", "rental", "for rent", "lease"),
                "ownership": ("condo", "condominium", "for sale", "for-sale", "ownership", "owner-occupied")}


def norm(x):
    return re.sub(r"\s+", " ", str(x or "")).strip().lower()


def listing_texts(dbp):
    db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    out = {}
    for rk, rtype, when, status, desc, unit, addr in db.execute(
            "SELECT DISTINCT record_key, record_type, listed_on, status, description, unit, address "
            "FROM v_project_records_listed WHERE NOT in_project"):
        if not (desc or "").strip() and not (rtype or "").strip():
            continue
        out[rk] = f"{rtype or ''} | listed {when} | {status or ''} | {addr}{(' suite ' + unit) if unit else ''} | {desc or ''}"[:600]
    return out


def verify_project(ans, texts):
    src = {k: norm(t) for k, t in texts}
    kept = {}
    for m in ("commercial_sqft", "commercial_spaces"):
        it = ans.get(m) or {}
        v, q, s = it.get("value"), it.get("quote"), str(it.get("source") or "").strip().strip("[]").strip()
        try:
            v = int(float(str(v).replace(",", ""))) if v is not None else None
        except Exception:
            v = None
        if v is not None and q and s in src and norm(q) in src[s] and _has_number(q, v):
            kept[m] = {"value": v, "quote": q, "source": s}
    it = ans.get("commercial_uses") or {}
    v, q, s = it.get("value"), it.get("quote"), str(it.get("source") or "").strip().strip("[]").strip()
    if v and q and s in src and norm(q) in src[s]:
        vals = [x for x in (v if isinstance(v, list) else [v]) if norm(x) and norm(x) in norm(q)]
        if vals:
            kept["commercial_uses"] = {"value": vals, "quote": q, "source": s}
    it = ans.get("tenure_stated") or {}
    v, q, s = it.get("value"), it.get("quote"), str(it.get("source") or "").strip().strip("[]").strip()
    if v in ("rental", "ownership", "mixed") and q and s in src and norm(q) in src[s]:
        need = TENURE_WORDS["rental"] + TENURE_WORDS["ownership"] if v == "mixed" else TENURE_WORDS[v]
        if any(w in norm(q) for w in need):
            kept["tenure_stated"] = {"value": v, "quote": q, "source": s}
    return kept


def verify_listing(ans, text):
    t = norm(text)
    kept = {}
    for m in ("non_residential", "condominium", "business_name", "use_kind", "action", "sqft"):
        it = ans.get(m) or {}
        v, q = it.get("value"), it.get("quote")
        if v is None or v == "" or not q or norm(q) not in t:
            continue
        if m == "sqft":
            try:
                v = int(float(str(v).replace(",", "")))
            except Exception:
                continue
            if not _has_number(q, v):
                continue
        if m in ("business_name", "use_kind") and norm(v) not in norm(q):
            continue
        if m == "action" and v not in ("new_business", "tenant_improvement", "sign", "change_of_use", "closure", "other"):
            continue
        kept[m] = {"value": v, "quote": q}
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["projects", "listings"], required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sonnet", choices=["submit", "status", "collect"])
    ap.add_argument("--db", required=True)
    a = ap.parse_args()
    out = OUT / a.target
    state = out / "sonnet_batch_state.json"
    if a.target == "projects":
        recs, pack, defn = project_texts(Path(a.db)), 6, DEF_PROJECTS
    else:
        recs, pack, defn = listing_texts(Path(a.db)), 20, DEF_LISTINGS
    keys = sorted(recs)
    groups = [keys[i:i + pack] for i in range(0, len(keys), pack)]
    print(f"{len(keys)} {a.target} with text")

    def prompt(g):
        if a.target == "projects":
            body = "\n\n".join(f"PROJECT {k}\n" + "\n".join(f"  [{s}] {t}" for s, t in recs[k]) for k in g)
            shape = ", ".join(f"\"{m}\": {{\"value\": <...>, \"quote\": <exact words or null>, \"source\": <record key "
                              f"without brackets, or null>}}" for m in ("commercial_sqft", "commercial_spaces",
                                                                         "commercial_uses", "tenure_stated"))
            return (f"You are reading City of Berkeley records for {len(g)} housing projects. Judge each on its own "
                    f"text.\n\n{defn}\n\nAnswer with a JSON array only, one object per project, in order:\n"
                    f"[{{\"project\": <PROJECT key>, {shape}}}]\n\n{body}")
        body = "\n".join(f"RECORD {k}: {recs[k]}" for k in g)
        shape = ", ".join(f"\"{m}\": {{\"value\": <...>, \"quote\": <exact words or null>}}" for m in
                          ("non_residential", "business_name", "use_kind", "action", "sqft", "condominium"))
        return (f"You are reading {len(g)} City of Berkeley permit and planning records.\n\n{defn}\n\nAnswer with a "
                f"JSON array only, one object per record, in order:\n[{{\"record\": <RECORD key>, {shape}}}]\n\n{body}")

    if a.dry_run:
        print(prompt(groups[0])[:2500])
        print(f"\n{len(groups)} requests, ~{sum(len(prompt(g)) for g in groups)/4/1e6:.2f}M input tokens. NOTHING ASKED.")
        return 0
    if a.sonnet == "submit":
        out.mkdir(parents=True, exist_ok=True)
        (out / "groups.json").write_text(json.dumps(groups))
        mr.batch_submit([{"custom_id": f"g{i}", "params": {"model": mr.BATCH_MODEL, "max_tokens": 700 * len(g) + 800,
                          "messages": [{"role": "user", "content": prompt(g)}]}} for i, g in enumerate(groups)], state)
        return 0
    if a.sonnet == "status":
        mr.batch_status(state)
        return 0
    if a.sonnet == "collect":
        groups = json.loads((out / "groups.json").read_text())
        rows, unanswered, rejected = [], [], 0
        idf = "project" if a.target == "projects" else "record"
        for cid, parsed, raw, _ in mr.batch_results(state):
            got = {str(x.get(idf)): x for x in (parsed or []) if isinstance(x, dict)}
            for k in groups[int(cid[1:])]:
                if k not in got:
                    unanswered.append(k)
                    continue
                kept = verify_project(got[k], recs[k]) if a.target == "projects" else verify_listing(got[k], recs[k])
                proposed = sum(1 for m, it in got[k].items() if isinstance(it, dict) and it.get("value") not in (None, "", False))
                rejected += max(0, proposed - sum(1 for m, it in kept.items() if it["value"] is not False))
                rows.append({("project_key" if a.target == "projects" else "record_key"): k, **kept})
        fields = sorted({m for r in rows for m in r if not m.endswith("_key")})
        print(f"answers {len(rows)}; " + "; ".join(f"{m} {sum(1 for r in rows if m in r)}" for m in fields)
              + f"; values rejected (not verbatim / not in quote) {rejected}; unanswered {len(unanswered)}")
        mr.write_evidence(rows, "project_uses" if a.target == "projects" else "listing_uses", defn,
                          extra={"model": mr.BATCH_MODEL, "rule": "kept only if the quote is verbatim (numbers and "
                                 "names must appear in it; a tenure only if the quote names it)",
                                 "unanswered": unanswered})
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
