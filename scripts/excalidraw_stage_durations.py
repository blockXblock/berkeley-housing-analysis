#!/usr/bin/env python3
"""Generate an Excalidraw "stage duration" chart from the Explorer data.

Reads docs/explorer_data.js (the file the site loads), computes per-project
stage segments between dated milestones, and writes an Obsidian-Excalidraw
markdown drawing: one left-aligned bar per project, a median reference bar on
top, unknown spans hatched, out-of-order milestones flagged, open-ended
projects drawn as a dashed arrow to the export date.

Usage: python scripts/excalidraw_stage_durations.py [--top N] [--out PATH]
"""
import argparse, datetime as dt, json, random, re, statistics, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JS = ROOT / "docs" / "explorer_data.js"
DEFAULT_OUT = Path.home() / "Obsidian/MainAction/Excalidraw/Stage Durations - Top Projects.md"
SITE = "https://berkeleybuild.com/explorer.html"

# milestone -> (label of the stage that ENDS at this milestone, color)
MILESTONES = [
    ("app_filed",          None, None),
    ("app_complete",       "Completeness review",       "#94a3b8"),
    ("entitled",           "City decision",             "#fbbf24"),
    ("bp_issued",          "Entitled → building permit", "#a78bfa"),
    ("co_date",            "Construction",              "#f97316"),
]
GROUND_BROKEN = "construction_start"  # too sparse (11 projects) for its own stage; drawn as a marker
LABELS = {m: (lab, col) for m, lab, col in MILESTONES if lab}
ORDER = [m for m, _, _ in MILESTONES]
PX_PER_DAY = 0.4
ROW_H = 34
LABEL_W = 270
BAR_H = 18
FONT = 1  # Virgil (hand-drawn)


def D(s):
    return dt.date.fromisoformat(s[:10])


def load():
    s = DATA_JS.read_text()
    d = json.loads(s[s.index("{"):].rstrip().rstrip(";"))
    return d


def segments(p, today):
    """Walk milestones in canonical order. Returns (segs, flags, open_end, total).
    seg = dict(start_day, end_day, label, color, hatched)  -- days from first milestone."""
    known = [(m, D(p[m])) for m in ORDER if p.get(m)]
    if len(known) < 2:
        return None
    origin = known[0][1]
    cursor = origin
    cursor_m = known[0][0]
    segs, flags = [], []
    for m, d in known[1:]:
        if d < cursor:
            flags.append(((cursor - origin).days, f"{m} ({p[m][:10]}) precedes {cursor_m} ({cursor})"))
            continue
        lab, col = LABELS[m]
        skipped = ORDER.index(m) - ORDER.index(cursor_m) > 1
        segs.append(dict(a=(cursor - origin).days, b=(d - origin).days, label=lab, color=col,
                         hatched=skipped, start=cursor_m, end=m))
        cursor, cursor_m = d, m
    open_end = None
    finished = p.get("co_date") or p.get("status") in ("Withdrawn",)
    if not finished and today > cursor:
        open_end = ((cursor - origin).days, (today - origin).days)
    total = (cursor - origin).days
    gb = (D(p[GROUND_BROKEN]) - origin).days if p.get(GROUND_BROKEN) else None
    return dict(segs=segs, flags=flags, open_end=open_end, total=total, n=len(known), origin=origin, ground_broken=gb)


# ---------------------------------------------------------------- excalidraw
class Scene:
    def __init__(self):
        self.els = []
        self.rng = random.Random(42)
        self.now = int(time.time() * 1000)

    def _idx(self):
        i = len(self.els)
        b62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        if i < 62:
            return "a" + b62[i]
        i -= 62
        return "b" + b62[i // 62] + b62[i % 62]

    def _id(self):
        return "".join(self.rng.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8))

    def _base(self, typ, x, y, w, h, **kw):
        e = dict(id=self._id(), type=typ, x=x, y=y, width=w, height=h, angle=0,
                 strokeColor="#1e1e1e", backgroundColor="transparent", fillStyle="solid",
                 strokeWidth=1, strokeStyle="solid", roughness=1, opacity=100, groupIds=[],
                 frameId=None, index=self._idx(), roundness=None, seed=self.rng.randint(1, 2**31),
                 version=1, versionNonce=self.rng.randint(1, 2**31), isDeleted=False,
                 boundElements=[], updated=self.now, link=None, locked=False)
        e.update(kw)
        self.els.append(e)
        return e

    def rect(self, x, y, w, h, fill, **kw):
        return self._base("rectangle", x, y, w, h, backgroundColor=fill, **kw)

    def text(self, x, y, s, size=16, color="#1e1e1e", align="left", **kw):
        lines = s.split("\n")
        w = max(len(l) for l in lines) * size * 0.55
        h = len(lines) * size * 1.25
        if align == "right":
            x -= w
        elif align == "center":
            x -= w / 2
        return self._base("text", x, y, w, h, strokeColor=color, fontSize=size, fontFamily=FONT,
                          text=s, textAlign=align, verticalAlign="top", containerId=None,
                          originalText=s, autoResize=True, lineHeight=1.25, **kw)

    def line(self, x, y, pts, color="#1e1e1e", arrow=False, **kw):
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        typ = "arrow" if arrow else "line"
        return self._base(typ, x, y, max(xs) - min(xs), max(ys) - min(ys), strokeColor=color,
                          points=pts, lastCommittedPoint=None, startBinding=None, endBinding=None,
                          startArrowhead=None, endArrowhead="arrow" if arrow else None,
                          roundness={"type": 2}, **kw)


def build(rows, medians, today, export_date, n_pool):
    sc = Scene()
    X0, Y0 = 0, 0
    x_bar = X0 + LABEL_W
    span_days = max(max((r["open_end"][1] if r["open_end"] else r["total"]) for _, r in rows),
                    sum(m for _, m, _ in medians))
    span_days = int((span_days // 365 + 1) * 365)
    W = span_days * PX_PER_DAY

    # title
    sc.text(X0, Y0, "How long does a Berkeley housing project take?", size=28)
    sc.text(X0, Y0 + 40, f"Days spent in each stage, from application filed. Projects with 3+ dated milestones, "
            f"longest {len(rows)} of {n_pool}. Data: berkeleybuild.com, exported {export_date}.", size=14, color="#6b7280")

    # legend
    ly = Y0 + 80
    lx = X0
    for m, (lab, col) in LABELS.items():
        sc.rect(lx, ly, 22, 14, col, strokeWidth=1)
        t = sc.text(lx + 28, ly - 3, lab, size=13)
        lx += 28 + t["width"] + 22
    sc.rect(lx, ly, 22, 14, "#e5e7eb", fillStyle="hachure"); t = sc.text(lx + 28, ly - 3, "spans an undated stage", size=13); lx += 28 + t["width"] + 22
    sc.line(lx, ly + 7, [[0, 0], [22, 0]], color="#9ca3af", strokeStyle="dashed", arrow=True); t = sc.text(lx + 28, ly - 3, "still running (to today)", size=13); lx += 28 + t["width"] + 22
    sc.text(lx, ly - 4, "▲", size=13, color="#7c2d12"); t = sc.text(lx + 18, ly - 3, "ground broken", size=13); lx += 18 + t["width"] + 22
    sc.text(lx, ly - 4, "✕", size=15, color="#dc2626"); sc.text(lx + 18, ly - 3, "milestone out of order (data error)", size=13)

    # axis
    ay = Y0 + 120
    sc.line(x_bar, ay, [[0, 0], [W, 0]], color="#9ca3af")
    for yr in range(0, span_days // 365 + 1):
        x = x_bar + yr * 365 * PX_PER_DAY
        sc.line(x, ay - 4, [[0, 0], [0, 8]], color="#9ca3af")
        sc.text(x, ay - 24, f"{yr} yr" if yr else "filed", size=12, color="#6b7280", align="center")
        # faint gridline down the rows
        sc.line(x, ay + 8, [[0, 0], [0, (len(rows) + 2) * ROW_H + 10]], color="#e5e7eb", strokeWidth=0.5, roughness=0)

    # median reference bar
    y = ay + 16
    sc.text(x_bar - 12, y - 2, "MEDIAN project", size=15, align="right")
    sc.text(x_bar - 12, y + 16, "(per-stage medians)", size=11, color="#6b7280", align="right")
    cx = x_bar
    for lab, med, n in medians:
        col = next(c for l, c in LABELS.values() if l == lab)
        w = med * PX_PER_DAY
        sc.rect(cx, y, w, BAR_H + 4, col, strokeWidth=2)
        sc.text(cx + w / 2, y + BAR_H + 8, f"{med:.0f}d (n={n})", size=11, color="#6b7280", align="center")
        cx += w
    sc.line(x_bar - 10, y + ROW_H + 10, [[0, 0], [W + 10, 0]], color="#d1d5db", strokeStyle="dashed", roughness=0)

    # project rows
    y += ROW_H + 22
    for p, r in rows:
        gid = sc._id()
        addr = p["address"].title()
        lab = sc.text(x_bar - 12, y - 1, addr, size=14, align="right", groupIds=[gid],
                      link=f"{SITE}?project={p['id']}")
        sc.text(x_bar - 12, y + 15, f"{p['units']} unit{'s' if p['units'] != 1 else ''} · {p['status']}", size=10, color="#6b7280", align="right", groupIds=[gid])
        for s in r["segs"]:
            w = max((s["b"] - s["a"]) * PX_PER_DAY, 2)
            sc.rect(x_bar + s["a"] * PX_PER_DAY, y, w, BAR_H, s["color"], groupIds=[gid],
                    fillStyle="hachure" if s["hatched"] else "solid")
            if w > 34:
                sc.text(x_bar + s["a"] * PX_PER_DAY + w / 2, y + 2, f"{s['b'] - s['a']}", size=10, align="center", groupIds=[gid])
        if r["open_end"]:
            a, b = r["open_end"]
            sc.line(x_bar + a * PX_PER_DAY, y + BAR_H / 2, [[0, 0], [(b - a) * PX_PER_DAY, 0]],
                    color="#9ca3af", strokeStyle="dashed", arrow=True, groupIds=[gid])
        else:
            sc.text(x_bar + r["total"] * PX_PER_DAY + 6, y - 2, f"{r['total']}d", size=11, color="#374151", groupIds=[gid])
        if r["ground_broken"] is not None and 0 <= r["ground_broken"] <= max(r["total"], (r["open_end"] or (0, 0))[1]):
            sc.text(x_bar + r["ground_broken"] * PX_PER_DAY - 6, y + BAR_H - 2, "▲", size=12, color="#7c2d12", groupIds=[gid])
        for day, why in r["flags"]:
            sc.text(x_bar + day * PX_PER_DAY - 5, y - 3, "✕", size=16, color="#dc2626", groupIds=[gid])
        y += ROW_H
    return sc


def write_md(sc, out):
    texts = "\n".join(f"{e['text']} ^{e['id']}\n" for e in sc.els if e["type"] == "text")
    links = "\n".join(f"{e['id']}: {e['link']}" for e in sc.els if e.get("link"))
    scene = dict(type="excalidraw", version=2,
                 source="https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.27.3",
                 elements=sc.els,
                 appState=dict(theme="light", viewBackgroundColor="#ffffff", gridSize=20, gridStep=5,
                               gridModeEnabled=False, currentItemFontFamily=FONT),
                 files={})
    md = f"""---
excalidraw-plugin: parsed
tags:
  - excalidraw
  - berkeleybuild
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==

Generated by `berkeley-data/scripts/excalidraw_stage_durations.py`. Re-run it to refresh from the Explorer data; hand edits to the drawing will be overwritten.

%%
# Excalidraw Data

## Text Elements
{texts}
## Element Links
{links}

## Drawing
```json
{json.dumps(scene, indent="\t", ensure_ascii=False)}
```
%%"""
    out.write_text(md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--min-milestones", type=int, default=3)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    d = load()
    export_date = d.get("export_date", "")[:10]
    today = D(export_date) if export_date else dt.date.today()

    rows = []
    per_seg = {}
    for p in d["projects"]:
        r = segments(p, today)
        if not r:
            continue
        for s in r["segs"]:
            if not s["hatched"]:
                per_seg.setdefault(s["label"], []).append(s["b"] - s["a"])
        if r["n"] >= a.min_milestones:
            rows.append((p, r))
    n_pool = len(rows)
    rows.sort(key=lambda pr: -(pr[1]["open_end"][1] if pr[1]["open_end"] else pr[1]["total"]))
    rows = rows[: a.top]

    # median bar: consecutive-stage medians with enough support; construction = bp->co if start dates are too sparse
    medians = []
    for lab, _ in LABELS.values():
        v = per_seg.get(lab, [])
        if len(v) >= 10:
            medians.append((lab, statistics.median(v), len(v)))

    sc = build(rows, medians, today, export_date, n_pool)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    write_md(sc, a.out)
    print(f"wrote {a.out}  ({len(sc.els)} elements, {len(rows)} projects of {n_pool} eligible)")
    for lab, med, n in medians:
        print(f"  median {lab:28s} {med:6.0f} d  n={n}")
    flagged = sum(len(r["flags"]) for _, r in rows)
    print(f"  out-of-order milestones flagged in shown rows: {flagged}")


if __name__ == "__main__":
    main()
