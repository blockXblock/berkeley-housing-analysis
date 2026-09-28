#!/usr/bin/env python3
r"""model_readers.py -- THE one place that calls a model to READ a Berkeley record.

WHY A MODULE. Two facts from this project decided the shape:
  * a regex over prose can only match words we thought of, so scope and effect questions are read by
    a model against a WRITTEN DEFINITION (housing_rules.reading_rules);
  * and every rule that had no named home got re-derived, wrong -- four copies of the address
    normalizer, two of the permit classifier. The Jev HTTP call, its retry ladder and its resumable
    log were about to become the third such copy the moment a second question needed them.

READ ONCE, STORE, LOOK UP. A reading is never made at query time. It is made once, written to
data/derived/<topic>_evidence_<date>.json with the model id, the definitions text it read against and
a prompt hash, and thereafter looked up deterministically -- the pattern housing_rules.permit_effect
already uses over 32,897 permits. A re-reading is a NEW evidence file with a new hash, never an edit,
so a figure can always be traced to the wording that produced it.

WHAT IS HERE. Keys, the Jev call with retries, and a resumable runner. What each QUESTION asks stays
in its own script -- llm_permit_effect.py (what a permit does), llm_planning_scope.py (whether a
Planning record is a housing development). Nothing here writes to a database.
"""
from __future__ import annotations

import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = Path.home() / "Library/Application Support/io.datasette.llm/keys.json"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
RETRYABLE = (429, 529, 500, 502, 503)


def key(name: str) -> str:
    """an API key from llm's own keystore, so no key is ever written into this repo."""
    k = (json.load(open(KEYS)) or {}).get(name)
    return k or sys.exit(f"no {name} key: run `llm keys set {name}`")


def jev_ask(state: dict, questions: dict, model: str = "jev-latest", timeout: int = 60) -> dict:
    """one Jev call. Returns its JSON, or {"error": ...} -- never raises, never partially retries.

    Jev is TypeSafe's classifier: it answers `choice`/`noul`/`score` questions over STRUCTURED input
    and returns a label with a confidence, no prose. That suits a scope question whose classes are
    fixed, and it is why input_format is a dict of fields rather than a paragraph: every regex defect
    of 2026-09-25 came from reading an Accela description as though it were a field.
    """
    body = json.dumps({"state": state, "model": model, "questions": questions}).encode()
    err = "unknown"
    for attempt in range(6):
        try:
            req = urllib.request.Request(
                JEV_URL, body,
                {"Authorization": f"Bearer {key('typesafe')}", "Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except urllib.error.HTTPError as e:
            if e.code in RETRYABLE:
                time.sleep(2 ** attempt)
                err = f"HTTP {e.code}"
                continue
            return {"error": f"HTTP {e.code}"}
        except Exception as e:                       # noqa: BLE001  a transport error is retryable
            err = str(e)
            time.sleep(2 ** attempt)
    return {"error": err}


def run_resumable(ids, ask, log_path: Path, id_field: str = "id", workers: int = 8,
                  every: int = 500) -> list[dict]:
    """ask(id) -> dict for every id, appending each answer to a JSONL as it arrives.

    Resumable by design: a run over thousands of records WILL be interrupted, and re-asking what was
    already answered costs money and changes answers. An errored row is NOT counted as done, so a
    re-run retries exactly the failures -- the harvester rule (a 0-result is not evidence of absence
    until retried) applied to model calls.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    done: dict[str, dict] = {}
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if "error" not in r and r.get(id_field):
                done[r[id_field]] = r
    todo = [i for i in ids if i not in done]
    print(f"{len(done)} already answered, {len(todo)} to ask", flush=True)
    rows = list(done.values())
    with open(log_path, "a") as fh, concurrent.futures.ThreadPoolExecutor(workers) as ex:
        for n, r in enumerate(ex.map(ask, todo), 1):
            rows.append(r)
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            if n % every == 0:
                print(f"  {n}/{len(todo)}", flush=True)
    errs = [r for r in rows if "error" in r]
    print(f"answered {len(rows) - len(errs)} of {len(rows)}"
          + (f"; {len(errs)} errors left for a re-run" if errs else ""), flush=True)
    return rows


def write_evidence(rows: list[dict], topic: str, definitions: str, extra: dict | None = None,
                   date: str | None = None) -> Path:
    """store a reading as evidence: APPEND-ONLY, stamped with what it read against.

    The stamp is the point. permit_effect's file carries the model id and "HCD APR FAQ, adopted
    2026-09-26" on every row, which is why a figure derived from it can be traced to an exact wording
    months later. A file that already exists is NOT overwritten -- a re-reading is a new dated file.
    """
    import hashlib
    date = date or time.strftime("%Y-%m-%d")
    out = ROOT / "data/derived" / f"{topic}_evidence_{date}.json"
    if out.exists():
        sys.exit(f"{out.name} exists -- a reading is append-only. Use a later date, deliberately.")
    payload = {
        "topic": topic,
        "read_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "definitions_sha16": hashlib.sha256(definitions.encode()).hexdigest()[:16],
        "definitions": definitions,
        **(extra or {}),
        "readings": rows,
    }
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {out.relative_to(ROOT)}  ({len(rows)} readings)")
    return out


# ---------------------------------------------------------------------------------------------
# THE BATCH API PATH. A second reader, for the records the cheap classifier is unsure about. The
# permit_effect reading paid for itself here: on the 5,773 permits that needed reasoning, Jev and
# Sonnet DISAGREED 2,625 times -- so a single reader's label, however confident it looks, is not
# evidence. Batch rather than live calls: half price, and a reading is not urgent.
BATCH_MODEL = "claude-sonnet-5"


def batch_submit(requests: list[dict], state_path: Path) -> str:
    """submit a batch and record its id. Returns the batch id."""
    import anthropic
    b = anthropic.Anthropic(api_key=key("anthropic")).messages.batches.create(requests=requests)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"batch_id": b.id, "n": len(requests),
                                      "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S")}))
    print(f"submitted {b.id}  ({len(requests)} requests)")
    return b.id


def batch_status(state_path: Path):
    import anthropic
    bid = json.loads(state_path.read_text())["batch_id"]
    b = anthropic.Anthropic(api_key=key("anthropic")).messages.batches.retrieve(bid)
    print(b.processing_status, b.request_counts)
    return b


def batch_results(state_path: Path):
    """yield (custom_id, parsed_json_or_None, raw_text, usage) for every result."""
    import anthropic
    import re as _re
    bid = json.loads(state_path.read_text())["batch_id"]
    for r in anthropic.Anthropic(api_key=key("anthropic")).messages.batches.results(bid):
        if r.result.type != "succeeded":
            yield r.custom_id, None, r.result.type, None
            continue
        txt = "".join(b.text for b in r.result.message.content if getattr(b, "type", "") == "text")
        m = _re.search(r"\[.*\]|\{.*\}", txt, _re.S)
        try:
            yield r.custom_id, json.loads(m.group(0)), txt, r.result.message.usage
        except Exception:
            yield r.custom_id, None, txt, r.result.message.usage
