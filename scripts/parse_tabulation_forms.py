#!/usr/bin/env python3
"""Parse City 1.E tabulation forms -> proposed {units, stories, lot_area, gfa, footprint, coverage}.
Read-only. Emits a preview CSV; writes nothing to any DB."""
import re, subprocess, glob, os, csv, sys

def nums(s):
    return [float(x.replace(",","")) for x in re.findall(r"[\d,]+(?:\.\d+)?", s) if x.strip(",")]

def pct(s):
    m=re.findall(r"(\d+(?:\.\d+)?)\s*%", s)
    return [float(x) for x in m]

def parse(text):
    L=text.splitlines()
    d={"units":None,"stories":None,"lot_area":None,"gfa":None,"footprint":None,"coverage":None}
    for i,ln in enumerate(L):
        low=ln.lower()
        if "dwelling unit" in low and d["units"] is None:
            n=nums(ln.split("(#)")[-1] if "(#)" in ln else ln)
            if len(n)>=2: d["units"]=n[1]           # existing | PROPOSED | req
        elif "building height" in low and "stor" in low and d["stories"] is None:
            n=nums(ln.split(")")[-1]); 
            if len(n)>=2: d["stories"]=n[1]
        elif "lot area" in low and d["lot_area"] is None:
            n=nums(ln.split("(Square-Feet)")[-1] if "quare" in ln else ln)
            if n: d["lot_area"]=n[0]
        elif "gross floor" in low and d["gfa"] is None:
            n=nums(ln)
            if len(n)>=2: d["gfa"]=n[1]
            elif n: d["gfa"]=n[0]
        elif "total area covered" in low and d["gfa"] is None:
            n=nums(ln)                              # GFA line was blank; numbers wrapped to here
            if len(n)>=2: d["gfa"]=n[1] if n[0]>0 else n[0]
            elif n: d["gfa"]=n[0]
        elif "footprint" in low and "lot coverage" not in low and d["footprint"] is None:
            n=nums(ln)
            if len(n)>=2: d["footprint"]=n[1]      # existing | PROPOSED | max
            elif n: d["footprint"]=n[0]
        elif "lot coverage" in low and d["coverage"] is None:
            p=pct(ln)
            if len(p)>=2: d["coverage"]=p[1]
            elif p: d["coverage"]=p[0]
    # derive footprint from coverage x lot area when not explicit
    if not d["footprint"] and d["coverage"] and d["lot_area"]:
        d["footprint"]=round(d["lot_area"]*d["coverage"]/100.0)
        d["footprint_src"]="coverage*lot"
    else:
        d["footprint_src"]="explicit" if d["footprint"] else ""
    return d

rows=[]
for row in open("scratch/2026-09-06/tabforms/newest.txt"):
    did,pid,pdate,url=row.strip().split("|")
    f=f"scratch/2026-09-06/tabforms/doc{did}.pdf"
    if not os.path.exists(f): continue
    txt=subprocess.run(["pdftotext","-layout",f,"-"],capture_output=True,text=True).stdout
    d=parse(txt); d["project_id"]=pid; d["doc_id"]=did; d["date"]=pdate
    rows.append(d)

w=csv.DictWriter(sys.stdout,fieldnames=["project_id","doc_id","date","units","stories","lot_area","gfa","footprint","footprint_src","coverage"])
w.writeheader()
for r in sorted(rows,key=lambda x:int(x["project_id"])): w.writerow(r)
