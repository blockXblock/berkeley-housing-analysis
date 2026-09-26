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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["submit", "status", "collect", "score"])
    ap.add_argument("--permits"); ap.add_argument("--out", required=True); ap.add_argument("--eval")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-rules", action="store_true", help="control run: omit DEFINITIONS to measure cold ability")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    state = out / "batch_state.json"

    if a.cmd == "submit":
        import pandas as pd
        rules = "" if a.no_rules else DEFINITIONS
        prompt_hash = hashlib.sha256(QUESTION.format(rules=rules, record="").encode()).hexdigest()[:12]
        permits = list(dict.fromkeys(pd.read_csv(a.permits, dtype=str).permit))
        recs = records(permits)
        missing = [p for p in permits if p not in recs]
        reqs = [{"custom_id": re.sub(r"[^A-Za-z0-9_-]", "_", p),
                 "params": {"model": MODEL, "max_tokens": 4000, "messages": [{"role": "user",
                            "content": QUESTION.format(rules=rules, record=json.dumps(recs[p], indent=1))}]}}
                for p in permits if p in recs]
        (out / "meta.json").write_text(json.dumps({"model": MODEL, "prompt_hash": prompt_hash, "rules": not a.no_rules,
            "ids": {r["custom_id"]: p for r, p in zip(reqs, [p for p in permits if p in recs])},
            "records": recs, "missing": missing}, indent=1))
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
        rows, bad = [], []
        for r in anthropic.Anthropic(api_key=api_key()).messages.batches.results(json.loads(state.read_text())["batch_id"]):
            p = meta["ids"][r.custom_id]
            if r.result.type != "succeeded":
                bad.append({"permit": p, "why": r.result.type}); continue
            txt = "".join(b.text for b in r.result.message.content if getattr(b, "type", "") == "text")
            m = re.search(r"\{.*\}", txt, re.S)
            try:
                got = json.loads(m.group(0))
            except Exception:
                bad.append({"permit": p, "why": "unparseable", "text": txt[:300]}); continue
            rows.append({"permit": p, "model": meta["model"], "prompt_hash": meta["prompt_hash"], **got})
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
            if e.truth_kind == "v2_completion":
                if e.truth == "ambiguous":
                    ok = None
                else:
                    ok = creates == (e.truth == "completes")
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
