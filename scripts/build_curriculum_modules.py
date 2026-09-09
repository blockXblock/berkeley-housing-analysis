#!/usr/bin/env python3
"""build_curriculum_modules.py — build the module tarball the curriculum notebooks fetch.

WHY THIS EXISTS. The 18 curriculum notebooks bootstrap in Colab by downloading
curriculum_modules.tar.gz from public object storage and unpacking it. That tarball was
previously hand-made, so it DRIFTED: housing_rules/__init__.py gained `.address`
(2026-07-03) and `.owner_name` (2026-09-07), neither of which was ever added to the archive.
Every Colab run of a notebook importing housing_rules therefore died with
`ModuleNotFoundError: No module named 'housing_rules.address'` — a stale-asset failure that
Colab reports with a misleading "install it with !pip" hint.

THE GUARD. This script does not take a hand-written file list. It PARSES
housing_rules/__init__.py, collects every relative import, and fails loudly if any of them is
missing from disk — so the archive cannot silently lose a module again.

    python scripts/build_curriculum_modules.py            # build + verify locally
    python scripts/build_curriculum_modules.py --upload   # also publish to R2 (overwrites)
"""
import ast, os, sys, tarfile, tempfile, subprocess, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
PKG = "scripts/housing_rules"
EXTRA = ["scripts/build_v2/s0_keys.py", "scripts/build_v2/housing_predicates.py",
         "scripts/cpra_dedup.py"]
OUT = "curriculum_modules.tar.gz"
KEY = "curriculum/curriculum_modules.tar.gz"

def required_submodules():
    """Every relative import in housing_rules/__init__.py — the contract the archive must meet."""
    tree = ast.parse(open(f"{PKG}/__init__.py").read())
    return sorted({n.module.split(".")[0] for n in ast.walk(tree)
                   if isinstance(n, ast.ImportFrom) and n.level == 1 and n.module})

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--upload", action="store_true")
    a = ap.parse_args()

    need = required_submodules()
    print(f"housing_rules/__init__.py requires {len(need)} submodules: {', '.join(need)}")
    missing = [m for m in need if not os.path.exists(f"{PKG}/{m}.py")]
    if missing:
        sys.exit(f"FATAL: __init__ imports modules that do not exist on disk: {missing}")

    files = sorted(f"{PKG}/{f}" for f in os.listdir(PKG) if f.endswith(".py"))
    files += [f for f in EXTRA if os.path.exists(f)]
    with tarfile.open(OUT, "w:gz") as t:
        for f in files: t.add(f)
    print(f"\nwrote {OUT} ({os.path.getsize(OUT):,} bytes, {len(files)} files)")

    # VERIFY: unpack into a clean tree and import the package with nothing else present.
    with tempfile.TemporaryDirectory() as d:
        with tarfile.open(OUT) as t: t.extractall(d)
        probe = ("import sys; sys.path.insert(0, %r); import housing_rules as h; "
                 "h.normalize_address('2190 SHATTUCK Ave'); h.to_canonical_apn('57-2046-1','alameda'); "
                 "print('VERIFIED: housing_rules imports and works from the archive alone')"
                 % os.path.join(d, "scripts"))
        r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip()[-400:])
        if r.returncode != 0:
            sys.exit("FATAL: the archive does not import cleanly on its own.")

    if a.upload:
        import boto3
        from dotenv import load_dotenv
        load_dotenv(".env.r2")
        s3 = boto3.client("s3",
            endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
        B = os.environ["R2_BUCKET"]
        with open(OUT, "rb") as fh:
            s3.upload_fileobj(fh, B, KEY, ExtraArgs={"ContentType": "application/gzip"})
        got = s3.head_object(Bucket=B, Key=KEY)["ContentLength"]
        local = os.path.getsize(OUT)
        print(f"uploaded -> {KEY}: {got:,} bytes remote vs {local:,} local — "
              f"{'VERIFIED' if got == local else 'MISMATCH'}")

if __name__ == "__main__":
    main()
