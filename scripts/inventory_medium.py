#!/usr/bin/env python3
"""Inventory ANY mounted medium (drive, SD card, optical disc, Takeout folder) into
the media index, and report its image/movie content.

READ-ONLY. Adds rows to ~/mac-cleanup-2026-07/drives/drive_index.db table `f`
so every medium becomes queryable alongside the others.

Usage:
    python scripts/inventory_medium.py /Volumes/SomeDisc  LABEL
    python scripts/inventory_medium.py ~/Downloads/Takeout GPHOTOS-TAKEOUT-2026-07
"""
import os, sys, csv, sqlite3, time, hashlib
from pathlib import Path

IMG = ('.jpg','.jpeg','.png','.tif','.tiff','.heic','.heif','.gif','.bmp','.webp',
       '.cr2','.cr3','.nef','.arw','.dng','.orf','.rw2','.raf','.psd','.ai')
MOV = ('.mov','.mp4','.avi','.m4v','.mpg','.mpeg','.3gp','.mts','.m2ts','.wmv','.mkv','.dv','.flv')
SKIP = {'.Trashes','.Spotlight-V100','.fseventsd','.DocumentRevisions-V100',
        'System Volume Information','.TemporaryItems','$RECYCLE.BIN','.git','node_modules'}
DB = Path.home()/"mac-cleanup-2026-07/drives/drive_index.db"

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, label = sys.argv[1], sys.argv[2]
    root = os.path.expanduser(root)
    if not os.path.isdir(root):
        sys.exit(f"ABORT: not a readable directory: {root}")
    con = sqlite3.connect(DB)
    already = con.execute("SELECT COUNT(*) FROM f WHERE vol=?", (label,)).fetchone()[0]
    if already:
        print(f"NOTE: label '{label}' already has {already:,} rows. Use a new label or delete first.")
        if "--force" not in sys.argv: sys.exit("ABORT (pass --force to add anyway)")
    n=img=mov=0; b=ib=mb=0; errs=0; batch=[]; t0=time.time()
    for dp, dn, fns in os.walk(root, topdown=True):
        dn[:] = [d for d in dn if d not in SKIP]
        for fn in fns:
            if fn in ('.DS_Store','.localized') or fn.startswith('._'): continue
            p = os.path.join(dp, fn)
            try: st = os.lstat(p)
            except OSError: errs += 1; continue
            if not os.path.isfile(p) or os.path.islink(p): continue
            batch.append((label, st.st_size, int(st.st_mtime), p, fn)); n += 1; b += st.st_size
            low = fn.lower()
            if low.endswith(IMG): img += 1; ib += st.st_size
            elif low.endswith(MOV): mov += 1; mb += st.st_size
            if len(batch) >= 20000:
                con.executemany("INSERT INTO f VALUES (?,?,?,?,?)", batch); con.commit(); batch=[]
                print(f"  {n:,} files ({b/2**30:.1f} GiB)...", flush=True)
    if batch: con.executemany("INSERT INTO f VALUES (?,?,?,?,?)", batch); con.commit()
    print(f"\n=== {label} ===")
    print(f"  {n:,} files, {b/2**30:.2f} GiB, {errs} unreadable, {time.time()-t0:.0f}s")
    print(f"  IMAGES: {img:,} files, {ib/2**30:.2f} GiB")
    print(f"  MOVIES: {mov:,} files, {mb/2**30:.2f} GiB")
    # anything unique to this medium?
    q = con.execute(f"""SELECT COUNT(*), COALESCE(SUM(a.size),0) FROM f a
        WHERE a.vol=? AND NOT EXISTS (
          SELECT 1 FROM f b WHERE b.vol<>a.vol AND b.size=a.size AND b.name=a.name)""", (label,)).fetchone()
    print(f"  UNIQUE to this medium (size+name found nowhere else): {q[0]:,} files, {q[1]/2**30:.2f} GiB")
    con.close()

if __name__ == "__main__":
    main()
