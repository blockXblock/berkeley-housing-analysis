#!/usr/bin/env python3
"""extract_stated_heights.py — pull stated building HEIGHTS (stories + max feet) from the harvested
1.E tabulation forms, with cross-check verdicts, for the KML/geometry session.

The 1.E is a standard city form: pdftotext -layout reads it. Rows of interest carry EXISTING | (ALLOWED)
| PROPOSED columns. For new construction the PROPOSED value is the tallest number on the row, so we take
existing = first numeric, proposed = max numeric — then VALIDATE (the column-order trap is real, so a
value is only trusted if it survives a check):
  check A  GFA_proposed / footprint_proposed  ~=  stories_proposed   (caught a 9-vs-5 on 3030 Telegraph)
  check B  height_ft_proposed / stories_proposed  in [9, 15] ft/story (63/9=7 impossible; 63/5=12.6 ok)
verdict = PASS if the applicable checks pass, SUSPECT otherwise (geometry HOLDS on SUSPECT).

Output: data/reference/stated_heights.csv (both existing + proposed retained per the KML agent's spec).
Read-only extraction. Run: .venv/bin/python scripts/extract_stated_heights.py
"""
import json, subprocess, re, csv, sqlite3

FILES = "scratch/2026-08-23/tab_files.json"
OUT = "data/reference/stated_heights.csv"


# a single feet value: NN' or NN'-M" — NO internal whitespace, so it can't span to the next column
FEET_TOKEN = re.compile(r"\d+'(?:[-–]\d+\"?)?")


def feet(s):
    """'360'-9\"' -> 360.8 ; '56'-4\"' -> 56.3 ; '38'' -> 38.0"""
    m = re.match(r"(\d+)'(?:[-–](\d+))?", s)
    if not m:
        return None
    ft = float(m.group(1)); inch = float(m.group(2)) if m.group(2) else 0
    return round(ft + inch / 12, 1)


def ints_on(line):
    """integer story counts on a line, ignoring years/notes. '1-2  8' -> [1,2,8]; '2  34 ...' -> [2,34]"""
    # drop obvious non-story tokens
    toks = re.findall(r"\b(\d{1,3})\b", line)
    return [int(t) for t in toks if 1 <= int(t) <= 80]


def feet_on(line):
    return [feet(m) for m in FEET_TOKEN.findall(line) if feet(m)]


def areas_on(line):
    """square-foot values: 129,658 / 18,818 / 38,827.8"""
    return [float(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{4,}(?:\.\d+)?", line)]


def row_matching(txt, *patterns):
    for line in txt.splitlines():
        if all(re.search(p, line, re.I) for p in patterns):
            return line
    return ""


def extract(path):
    txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
    st_line = row_matching(txt, r"Building Height", r"Stories")
    ft_line = row_matching(txt, r"Maximum", r"Feet")
    gfa_line = row_matching(txt, r"Gross Floor Area")
    fp_line = row_matching(txt, r"Building Footprint|Footprint")
    stories = ints_on(st_line)
    fts = feet_on(ft_line)
    gfa = areas_on(gfa_line)
    fp = areas_on(fp_line)
    st_prop = max(stories) if stories else None
    # proposed height = the feet candidate whose feet/stories lands in a sane 9-15 ft/story window
    # (rejects setback notes like "50' W/" and existing-building values); prefer ~11.5 ft/story
    ft_prop = None
    if fts and st_prop:
        cands = [f for f in fts if 9 <= f / st_prop <= 15]
        ft_prop = min(cands, key=lambda f: abs(f / st_prop - 11.5)) if cands else None
    elif fts:
        ft_prop = max(fts)
    return {
        "stories_existing": stories[0] if stories else None,
        "stories_proposed": st_prop,
        "height_ft_existing": fts[0] if fts else None,
        "height_ft_proposed": ft_prop,
        "gfa_proposed": max(gfa) if gfa else None,
        "footprint_proposed": max(fp) if fp else None,
    }


def verdict(d):
    sp, hp, g, f = d["stories_proposed"], d["height_ft_proposed"], d["gfa_proposed"], d["footprint_proposed"]
    checks = []
    ok = True
    if sp and g and f:
        r = g / f
        good = abs(r - sp) <= 1.5
        checks.append(f"GFA/fp={r:.1f}vs{sp}st:{'ok' if good else 'FAIL'}")
        ok &= good
    else:
        checks.append("GFA/fp=n/a")
    if sp and hp:
        fps = hp / sp
        good = 9 <= fps <= 15
        checks.append(f"{fps:.1f}ft/st:{'ok' if good else 'FAIL'}")
        ok &= good
    else:
        checks.append("ft/st=n/a")
    if sp is None and hp is None:
        return "NO-READ", ";".join(checks)
    # if proposed == existing on a project, flag (likely wrong column)
    if d["stories_proposed"] is not None and d["stories_proposed"] == d["stories_existing"]:
        checks.append("prop==exist!"); ok = False
    # PASS requires BOTH dimensions read + the ft/story check available and passing — one number alone
    # (stories with no height, or height with no stories) is not enough to extrude a building on
    if sp is None or hp is None:
        checks.append("incomplete"); return "SUSPECT", ";".join(checks)
    return ("PASS" if ok else "SUSPECT"), ";".join(checks)


def main():
    files = json.load(open(FILES))
    v2 = sqlite3.connect("databases/berkeley_housing_v2.db")
    addr = dict(v2.execute("SELECT project_id, address_display FROM v_projects_flat"))
    out = []
    for pid, path in files:
        d = extract(path)
        v, checks = verdict(d)
        out.append({"project_id": int(pid), "address": addr.get(int(pid), ""),
                    "stories_existing": d["stories_existing"], "stories_proposed": d["stories_proposed"],
                    "height_ft_existing": d["height_ft_existing"], "height_ft_proposed": d["height_ft_proposed"],
                    "gfa_proposed": d["gfa_proposed"], "footprint_proposed": d["footprint_proposed"],
                    "source_doc": path.split("/")[-1], "verdict": v, "checks": checks})
    out.sort(key=lambda r: (r["verdict"] != "PASS", -(r["stories_proposed"] or 0)))
    cols = ["project_id", "address", "stories_existing", "stories_proposed", "height_ft_existing",
            "height_ft_proposed", "gfa_proposed", "footprint_proposed", "source_doc", "verdict", "checks"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)
    from collections import Counter
    print(f"stated_heights.csv: {len(out)} projects -> {OUT}")
    print("verdicts:", dict(Counter(r["verdict"] for r in out)))
    print("\nPASS rows:")
    for r in out:
        if r["verdict"] == "PASS":
            print(f"  proj{r['project_id']:<4} {r['address'][:22]:22} {r['stories_proposed']}st {r['height_ft_proposed']}ft  [{r['checks']}]")
    print("\nSUSPECT/NO-READ:")
    for r in out:
        if r["verdict"] != "PASS":
            print(f"  proj{r['project_id']:<4} {r['address'][:22]:22} st={r['stories_proposed']} ft={r['height_ft_proposed']}  [{r['verdict']}: {r['checks']}]")


if __name__ == "__main__":
    main()
