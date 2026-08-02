#!/usr/bin/env python3
"""Copy a card's KEEP content to T7-2026/CARDS-consolidated/<label>/, skipping junk.
READ-ONLY source. Resilient. Usage: copy_card_keep.py "/Volumes/NAME" LABEL"""
import os, sys, shutil, csv, time
if len(sys.argv)<3: sys.exit("usage: copy_card_keep.py <mount> <label>")
SRC, LABEL = sys.argv[1], sys.argv[2]
DST=f"/Volumes/T7-2026/CARDS-consolidated/{LABEL}"
LOG=os.path.expanduser(f"~/mac-cleanup-2026-07/drives/cardcopy_{LABEL}_fail.csv")
if not os.path.isdir(SRC): sys.exit(f"ABORT: source not mounted: {SRC}")
if not os.path.isdir("/Volumes/T7-2026"): sys.exit("ABORT: T7-2026 not mounted")
SKIP_DIR={'ZoteroDump','GaragebandBooks','GarageBandFolder','__MACOSX','System Volume Information',
          '$RECYCLE.BIN','.Spotlight-V100','.fseventsd','.Trashes','SanDiskSecureAccess','.TemporaryItems'}
SKIP_EXT=('.exe','.lnk','.url','.dmg','.ipa','.spclean','.spdirty')
SKIP_NAME_SUB=('SecureAccess','RunSanDisk','RunClub','T-AMBAUSC','mimobot')
os.makedirs(DST, exist_ok=True)
ok=f=skip=0; b=0; fails=[]; t0=time.time()
for dp,dn,fns in os.walk(SRC, topdown=True, onerror=lambda e: fails.append(("DIR",str(e)))):
    dn[:]=[d for d in dn if d not in SKIP_DIR]
    rel=os.path.relpath(dp,SRC); out=os.path.join(DST,rel) if rel!="." else DST
    for fn in fns:
        if fn.startswith("._") or fn in ('.DS_Store','.apdisk','.localized'): continue
        low=fn.lower()
        if low.endswith(SKIP_EXT) or any(s in fn for s in SKIP_NAME_SUB): skip+=1; continue
        s=os.path.join(dp,fn); d=os.path.join(out,fn)
        try:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            if os.path.exists(d) and os.path.getsize(d)==os.path.getsize(s): continue
            shutil.copy2(s,d); ok+=1; b+=os.path.getsize(d)
        except OSError as e:
            f+=1; fails.append((s,e.strerror))
        if (ok+f)%5000==0: print(f"  {ok:,} files, {b/2**30:.2f} GiB ({time.time()-t0:.0f}s)", flush=True)
with open(LOG,"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["path","error"]); w.writerows(fails)
print(f"DONE {LABEL}: {ok:,} copied ({b/2**30:.2f} GiB), {skip:,} junk-skipped, {f:,} failed, {time.time()-t0:.0f}s")
