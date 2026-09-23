#!/usr/bin/env python3
"""Extract public-comment participants from a Berkeley hearing packet table.

Reads the markdown table John keeps in the Obsidian vault (addresses + subject lines taken
from the City's published supplemental-communications packet -- a public record) and writes
a sortable CSV. Groups identical subject lines, which is how organised write-in campaigns
show up on both sides.

Output goes to a FILE. Nothing is printed but counts -- addresses should not end up in a
chat transcript, a commit, or anything published.

Usage:
    python3 scripts/extract_comment_participants.py [out.csv]
Default out: ~/Obsidian/MainAction/Action/nov6_participants.csv   (vault, not the repo)
"""
import csv, os, re, sys, collections

SRC = os.path.expanduser(
    "~/Obsidian/MainAction/Action/Berkeley November 6 City Council Hearing.md")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Obsidian/MainAction/Action/nov6_participants.csv")

def name_guess(email):
    local = re.sub(r'\d+', '', email.split('@')[0])
    parts = [p for p in re.split(r'[._-]+', local) if len(p) > 1]
    return ' '.join(p.capitalize() for p in parts)

def main():
    if not os.path.exists(SRC):
        sys.exit(f"source not found: {SRC}")
    text = open(SRC).read().split('%%')[0]          # stop before the excalidraw blob
    rows = []
    for line in text.splitlines():
        m = re.match(r'\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|', line)
        if m:
            rows.append((m.group(1).strip(), m.group(2).strip()))

    subj = collections.Counter(s for _, s in rows)
    seen, out = set(), []
    for email, s in rows:
        key = (email.lower(), s)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            'email': email,
            'name_guess': name_guess(email),
            'subject': s,
            'identical_subject_count': subj[s],
            'campaign': 'YES' if subj[s] >= 3 else '',
        })

    out.sort(key=lambda r: (-r['identical_subject_count'], r['subject'], r['email'].lower()))
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)

    print(f"wrote {OUT}")
    print(f"  {len(rows)} table rows -> {len(out)} unique (email, subject) pairs")
    print(f"  {len(set(e.lower() for e, _ in rows))} distinct addresses")
    print(f"\n  identical-subject clusters of 3+ (organised write-ins, either direction):")
    for s, n in subj.most_common():
        if n >= 3:
            print(f"    {n:4}  {s[:66]}")

if __name__ == '__main__':
    main()
