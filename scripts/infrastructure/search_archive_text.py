#!/usr/bin/env python3
"""Search OCR'd archival text (Internet Archive _djvu.txt) for a phrase and print
context. OCR wraps lines arbitrarily and doubles spaces, so we flatten each
document to a single whitespace-normalised string before matching — line-based
grep silently misses anything that straddles a line break.

usage: search_archive_text.py <dir> <regex> [context_chars] [max_hits]
"""
import os, re, sys

d      = sys.argv[1]
pat    = sys.argv[2]
ctx    = int(sys.argv[3]) if len(sys.argv) > 3 else 220
maxhit = int(sys.argv[4]) if len(sys.argv) > 4 else 40

# allow flexible whitespace between words of the query
flex = r'\s+'.join(re.escape(w) for w in pat.split()) if ' ' in pat and not any(
    c in pat for c in '[](){}|*+?\\') else pat
rx = re.compile(flex, re.I)

hits = 0
for fn in sorted(os.listdir(d)):
    if not fn.endswith('.txt'):
        continue
    raw = open(os.path.join(d, fn), encoding='utf-8', errors='replace').read()
    flat = re.sub(r'\s+', ' ', raw)
    for m in rx.finditer(flat):
        a, b = max(0, m.start() - ctx), min(len(flat), m.end() + ctx)
        print(f"\n--- {fn} @ {m.start()} ---")
        print("  " + flat[a:b].strip())
        hits += 1
        if hits >= maxhit:
            print(f"\n[stopped at {maxhit} hits]")
            sys.exit(0)
print(f"\n[{hits} hits]")
