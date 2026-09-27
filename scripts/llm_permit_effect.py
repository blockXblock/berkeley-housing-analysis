#!/usr/bin/env python3
"""llm_permit_effect.py — ask a model what ONE permit does to Berkeley's housing stock, via the Batch API.

The per-permit question layer over housing_rules.reading_rules.DEFINITIONS (the per-project layer is
batch_stage_classify.py). Input is the raw CPRA row only — never a v2 field, never CKAN. Each answer
is stored with the model id and prompt hash so a build can read stored answers instead of re-asking.

  submit  --permits FILE.csv (column `permit`) --out DIR   [--dry-run]
  status  --out DIR
  collect --out DIR          -> DIR/answers.json
  score   --out DIR --eval FILE.csv (permit, truth_kind, truth)

Run with the project venv (pandas + anthropic): .venv/bin/python scripts/llm_permit_effect.py ...
Nothing is written to any database.
"""
import argparse, glob, hashlib, json, re, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.housing_rules.reading_rules import DEFINITIONS

MODEL = "claude-sonnet-5"
FIELDS = ["PermitNumber", "Work Type", "SubType", "Submittal Date", "Issuance Status", "Issuance Date",
          "Finaled Status", "Finaled Date", "StreetNumber", "StreetName", "StreetType", "WorkDescription",
          "UnitsAdded", "UnitsRemoved", "NumberUnits", "ADU", "Detached", "OccType"]
QUESTION = """You are reading ONE building-permit record from the City of Berkeley.

{rules}
Question: what does THIS permit's own scope do to the housing stock?

Answer with JSON only:
{{"effect": "creates" | "alters" | "demolishes" | "subpermit" | "not_housing" | "unclear",
  "dwellings_created": <integer, 0 unless this permit's own scope builds new dwelling units>,
  "dwellings_removed": <integer>,
  "parent_permit": <permit number this is a part of, or null>,
  "cites": [<permit numbers your answer rests on>],
  "reason": <one sentence>,
  "confidence": "high" | "medium" | "low"}}

Record:
{record}"""
PACKED = """You are reading {n} building-permit records from the City of Berkeley. Judge each record
on its own; do not let one record inform another.

{rules}
Question, for EACH record: what does that permit's own scope do to the housing stock?

Answer with a JSON array only, one object per record, in the same order:
[{{"permit": <PermitNumber>,
  "effect": "creates" | "alters" | "demolishes" | "subpermit" | "not_housing" | "unclear",
  "dwellings_created": <integer>, "dwellings_removed": <integer>,
  "parent_permit": <permit number or null>, "cites": [<permit numbers>],
  "reason": <one sentence>, "confidence": "high" | "medium" | "low"}}, ...]

Records:
{records}"""
# --trim: fields that bear on housing effect only; addresses and dates do not change what the scope does
TRIM = ["PermitNumber", "Work Type", "SubType", "Finaled Status", "WorkDescription",
        "UnitsAdded", "UnitsRemoved", "NumberUnits", "ADU", "Detached", "OccType"]


def api_key():
    k = json.load(open(Path.home() / "Library/Application Support/io.datasette.llm/keys.json")).get("anthropic")
    return k or sys.exit("no anthropic key in llm's keys.json")


def records(permits):
    """Latest CPRA row per permit across all feed files (reruns republish whole windows);
    v2 permits row as the fallback for permits outside the CPRA windows."""
    import pandas as pd
    frames = []
    for f in sorted(glob.glob(str(ROOT / "data/raw/cpra-downloads/BP_Annual Permit Report-*.xlsx"))):
        d = pd.read_excel(f, header=None, dtype=str)
        h = d.index[d.apply(lambda r: r.astype(str).str.contains("PermitNumber").any(), axis=1)][0]
        d.columns = [str(c) for c in d.iloc[h]]
        d = d.iloc[h + 1:].loc[:, lambda x: ~x.columns.duplicated()]
        d["_rank"] = 1 if "rerun" in f or "2025-2026" in f else 0
        frames.append(d[d.PermitNumber.isin(permits)])
    a = pd.concat(frames).sort_values("_rank").drop_duplicates("PermitNumber", keep="last")
    out = {r.PermitNumber: {k: r[k] for k in FIELDS if k in r and pd.notna(r[k])} for _, r in a.iterrows()}
    v2 = sqlite3.connect(f"file:{ROOT}/databases/berkeley_housing_v2.db?mode=ro", uri=True)
    for p in set(permits) - set(out):
        r = v2.execute("SELECT description, filed_date, issued_date, finaled_date FROM permits "
                       "WHERE permit_number=?", (p,)).fetchone()
        if r:
            out[p] = {"PermitNumber": p, "WorkDescription": r[0], "Submittal Date": r[1],
                      "Issuance Date": r[2], "Finaled Date": r[3], "_note": "from v2 permits (outside CPRA windows)"}
    return out


EFFECTS = {  # the same five outcomes the Sonnet question asks for, stated as Jev choice criteria
    "creates": "This permit's own scope builds new dwelling units (net new).",
    "alters": "Work on existing buildings that adds no dwelling unit.",
    "demolishes": "Demolishes a building or removes dwelling units.",
    "subpermit": "Part of construction permitted under another permit number (phase, foundation, -DEF, -REV).",
    "not_housing": "Work unrelated to housing (commercial, signage, site work, temporary power).",
}
UNIT_BUCKETS = {"0": "no new dwelling units", "1": "one", "2": "two", "3-9": "three to nine",
                "10-49": "ten to forty-nine", "50+": "fifty or more"}


def jev(recs, permits, out, trim):
    """Ask TypeSafe's Jev the same question: effect as a choice, net new dwellings as a bucket choice.
    Jev returns numbers only (no reasons, no permit citations); key from llm's keys.json 'typesafe'."""
    import urllib.request, concurrent.futures, time
    key = json.load(open(Path.home() / "Library/Application Support/io.datasette.llm/keys.json")).get("typesafe")
    if not key:
        sys.exit("no typesafe key: run `llm keys set typesafe`")
    q = {"effect": {"type": "choice", "instructions": "What does THIS permit's own scope do to the housing stock?\n" + DEFINITIONS,
                    "criteria": EFFECTS},
         "net_new_units": {"type": "choice", "instructions": "How many net new dwelling units does THIS permit's own scope add?\n" + DEFINITIONS,
                           "criteria": UNIT_BUCKETS}}
    def ask(p):
        state = {k: v for k, v in recs[p].items() if not trim or k in TRIM}
        body = json.dumps({"state": state, "model": "jev-latest", "questions": q}).encode()
        for attempt in range(6):
            try:
                req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", body,
                        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                return p, json.load(urllib.request.urlopen(req, timeout=60))
            except urllib.error.HTTPError as e:
                if e.code in (429, 529, 500, 502, 503): time.sleep(2 ** attempt); continue
                return p, {"error": f"HTTP {e.code}"}
            except Exception as e:
                time.sleep(2 ** attempt); err = str(e)
        return p, {"error": err}
    rows, tin = [], 0
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for p, r in ex.map(ask, permits):
            if "answers" not in r:
                rows.append({"permit": p, "error": r.get("error")}); continue
            a = r["answers"]; tin += r.get("usage", {}).get("input_tokens", 0)
            b = a["net_new_units"]["choice"]
            rows.append({"permit": p, "model": r.get("model"), "effect": a["effect"]["choice"],
                         "effect_confidence": a["effect"].get("confidence"), "units_bucket": b,
                         "units_confidence": a["net_new_units"].get("confidence"),
                         "dwellings_created": {"0": 0, "1": 1, "2": 2}.get(b), "dwellings_removed": 0,
                         "confidence": a["effect"].get("confidence")})
    (out / "answers.json").write_text(json.dumps(rows, indent=1))
    ok = [r for r in rows if "error" not in r]
    print(f"answered {len(ok)} of {len(rows)}; input tokens per permit {tin / max(len(ok), 1):.0f}; "
          f"projected 32,897 permits: ${32897 * tin / max(len(ok), 1) * 0.042 / 1e6:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["submit", "status", "collect", "score", "jev"])
    ap.add_argument("--permits"); ap.add_argument("--out", required=True); ap.add_argument("--eval")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pack", type=int, default=1, help="permits per request")
    ap.add_argument("--trim", action="store_true", help="send only housing-relevant fields, compact JSON")
    ap.add_argument("--no-rules", action="store_true", help="control run: omit DEFINITIONS to measure cold ability")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    state = out / "batch_state.json"

    if a.cmd == "jev":
        import pandas as pd
        permits = list(dict.fromkeys(pd.read_csv(a.permits, dtype=str).permit))
        recs = records(permits)
        (out / "meta.json").write_text(json.dumps({"model": "jev-latest", "trim": a.trim}, indent=1))
        return jev(recs, [p for p in permits if p in recs], out, a.trim)

    if a.cmd == "submit":
        import pandas as pd
        rules = "" if a.no_rules else DEFINITIONS
        permits = list(dict.fromkeys(pd.read_csv(a.permits, dtype=str).permit))
        recs = records(permits)
        missing = [p for p in permits if p not in recs]
        def show(p):
            r = {k: v for k, v in recs[p].items() if not a.trim or k in TRIM}
            return json.dumps(r, separators=(",", ":")) if a.trim else json.dumps(r, indent=1)
        have = [p for p in permits if p in recs]
        groups = [have[i:i + a.pack] for i in range(0, len(have), a.pack)]
        template = QUESTION if a.pack == 1 else PACKED
        prompt_hash = hashlib.sha256((template + rules + f"trim={a.trim}").encode()).hexdigest()[:12]
        reqs, ids = [], {}
        for i, g in enumerate(groups):
            cid = re.sub(r"[^A-Za-z0-9_-]", "_", g[0]) if a.pack == 1 else f"g{i:05d}"
            text = (QUESTION.format(rules=rules, record=show(g[0])) if a.pack == 1 else
                    PACKED.format(n=len(g), rules=rules, records="\n".join(show(p) for p in g)))
            reqs.append({"custom_id": cid, "params": {"model": MODEL, "max_tokens": 4000 * min(a.pack, 4),
                         "messages": [{"role": "user", "content": text}]}})
            ids[cid] = g
        (out / "meta.json").write_text(json.dumps({"model": MODEL, "prompt_hash": prompt_hash, "rules": not a.no_rules,
            "pack": a.pack, "trim": a.trim, "ids": ids, "records": recs, "missing": missing}, indent=1))
        print(f"{len(reqs)} requests, {len(missing)} permits with no record {missing[:10]}; prompt {prompt_hash}, rules={not a.no_rules}")
        if a.dry_run:
            print(reqs[0]["params"]["messages"][0]["content"][:3000]); return
        import anthropic
        b = anthropic.Anthropic(api_key=api_key()).messages.batches.create(requests=reqs)
        state.write_text(json.dumps({"batch_id": b.id}))
        print("submitted", b.id)

    elif a.cmd == "status":
        import anthropic
        b = anthropic.Anthropic(api_key=api_key()).messages.batches.retrieve(json.loads(state.read_text())["batch_id"])
        print(b.processing_status, b.request_counts)

    elif a.cmd == "collect":
        import anthropic
        meta = json.loads((out / "meta.json").read_text())
        rows, bad, tin, tout = [], [], 0, 0
        for r in anthropic.Anthropic(api_key=api_key()).messages.batches.results(json.loads(state.read_text())["batch_id"]):
            ps = meta["ids"][r.custom_id]
            ps = ps if isinstance(ps, list) else [ps]
            if r.result.type != "succeeded":
                bad += [{"permit": p, "why": r.result.type} for p in ps]; continue
            tin += r.result.message.usage.input_tokens; tout += r.result.message.usage.output_tokens
            txt = "".join(b.text for b in r.result.message.content if getattr(b, "type", "") == "text")
            m = re.search(r"\[.*\]" if len(ps) > 1 or meta.get("pack", 1) > 1 else r"\{.*\}", txt, re.S)
            try:
                got = json.loads(m.group(0))
            except Exception:
                bad += [{"permit": p, "why": "unparseable", "text": txt[:300]} for p in ps]; continue
            if isinstance(got, dict):
                got = [dict(got, permit=ps[0])]
            byp = {g.get("permit"): g for g in got if isinstance(g, dict)}
            for p in ps:
                if p in byp:
                    rows.append({**byp[p], "permit": p, "model": meta["model"], "prompt_hash": meta["prompt_hash"]})
                else:
                    bad.append({"permit": p, "why": "missing from packed answer"})
        n = len(rows) or 1
        print(f"tokens per answered permit: input {tin / n:.0f}, output {tout / n:.0f}; "
              f"projected 32,897 permits on Batch: ${32897 * (tin / n * 1.0 + tout / n * 5.0) / 1e6:.0f}")
        (out / "answers.json").write_text(json.dumps(rows, indent=1))
        print(f"parsed {len(rows)}  failed {len(bad)}")
        if bad:
            (out / "failures.json").write_text(json.dumps(bad, indent=1))

    elif a.cmd == "score":
        import pandas as pd
        ans = {r["permit"]: r for r in json.loads((out / "answers.json").read_text())}
        ev = pd.read_csv(a.eval, dtype=str)
        res = []
        for e in ev.itertuples():
            g = ans.get(e.permit)
            if g is None:
                res.append((e.permit, e.truth_kind, e.truth, None, None, "no answer", "")); continue
            made = int(g.get("dwellings_created") or 0) - int(g.get("dwellings_removed") or 0)  # net
            creates = g.get("effect") == "creates" and int(g.get("dwellings_created") or 0) > 0
            if g.get("units_bucket") is not None:
                creates = g.get("effect") == "creates" and g["units_bucket"] != "0"
            if e.truth_kind == "v2_completion":
                if e.truth == "ambiguous":
                    ok = None
                else:
                    ok = creates == (e.truth == "completes")
            elif g.get("units_bucket") is not None:   # Jev answers a range, not a count
                t = int(float(e.truth)); lo, hi = {"0": (0, 0), "1": (1, 1), "2": (2, 2), "3-9": (3, 9),
                                                    "10-49": (10, 49), "50+": (50, 10**6)}[g["units_bucket"]]
                ok = lo <= t <= hi
                creates = g.get("effect") == "creates" and hi > 0
            else:
                ok = made == int(float(e.truth))
            res.append((e.permit, e.truth_kind, e.truth, g.get("effect"), made, ok, g.get("confidence")))
        R = pd.DataFrame(res, columns=["permit", "truth_kind", "truth", "effect", "model_units", "correct", "confidence"])
        R.to_csv(out / "scores.csv", index=False)
        if "rule_source" in ev.columns:   # rows that helped WRITE a reading rule leak into a rules-on run
            R["rule_source"] = ev.rule_source.fillna("").astype(str).str.lower().isin(["true", "1"]).values
        else:
            R["rule_source"] = False
        s = R[R.correct.isin([True, False])]
        print(s.groupby(["rule_source", "truth_kind"]).correct.agg(["sum", "count"]).to_string())
        h = s[~s.rule_source]
        print("HELD-OUT", int(h.correct.sum()), "/", len(h), "| rule-source rows", int(s[s.rule_source].correct.sum()), "/", int(s.rule_source.sum()))
        print("\nMISSES:\n" + R[R.correct == False].to_string(index=False))


if __name__ == "__main__":
    main()
