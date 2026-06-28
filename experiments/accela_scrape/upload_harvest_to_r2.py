#!/usr/bin/env python3
"""
Upload harvested plan-set PDFs to Cloudflare R2, driven by the harvest manifest.

Reads /tmp/harvest_stage/manifest.csv, uploads each STAGED file to its
suggested_r2_key (URL-safe, slash-only-as-key-prefix), verifies the upload by
re-reading the object's size, and prints the public URL for each.

KEY RULE: the local filename never contains '/' or ':'. The '/' appears ONLY in
the R2 object key (the folder separator), set as a string here at upload time.

CREDENTIALS: read from environment (never hard-coded, never committed):
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_BASE
Example (.env, gitignored):
  export R2_ACCOUNT_ID=xxxxxxxxxxxxxxxx
  export R2_ACCESS_KEY_ID=...
  export R2_SECRET_ACCESS_KEY=...
  export R2_BUCKET=berkeleybuild-docs
  export R2_PUBLIC_BASE=https://pub-2cee87f70da64080ab70ee0a34b55099.r2.dev

Usage:
  python upload_harvest_to_r2.py --dry-run     # show what WOULD upload, no writes
  python upload_harvest_to_r2.py               # actually upload
  python upload_harvest_to_r2.py --overwrite   # allow replacing an existing key
"""
import os, sys, csv, hashlib, argparse

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:
    sys.exit("Missing boto3. Install:  pip install boto3")

MANIFEST = "/tmp/harvest_stage/manifest.csv"

def env(name):
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Missing env var {name}. Set R2 credentials (see header) before running.")
    return v

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--manifest", default=MANIFEST,
                    help="harvest manifest CSV (default: run-1's %(default)s)")
    args = ap.parse_args()

    account = env("R2_ACCOUNT_ID")
    bucket  = env("R2_BUCKET")
    public_base = env("R2_PUBLIC_BASE").rstrip("/")
    endpoint = f"https://{account}.r2.cloudflarestorage.com"

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=env("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        region_name="auto",
    )

    if not os.path.exists(args.manifest):
        sys.exit(f"Manifest not found: {args.manifest}")

    with open(args.manifest, newline="") as f:
        rows = list(csv.DictReader(f))

    # Only upload files that were actually staged (skip dedup/failed rows).
    to_upload = [r for r in rows if (r.get("status", "").strip().lower().startswith("staged"))]

    print(f"Manifest rows: {len(rows)}  |  to upload (staged): {len(to_upload)}")
    print(f"Bucket: {bucket}   Endpoint: {endpoint}")
    print("-" * 78)

    results, errors = [], []
    for r in to_upload:
        local = r["local_path"].strip()
        key   = r["suggested_r2_key"].strip()
        # Safety: key uses '/' only as prefix separator; the basename has no '/' or ':'.
        base = key.split("/")[-1]
        if "/" in base or ":" in base:
            errors.append((key, "basename contains '/' or ':' — fix the key"))
            continue
        if not os.path.exists(local):
            errors.append((key, f"local file missing: {local}"))
            continue

        size = os.path.getsize(local)
        url = f"{public_base}/{key}"

        # Skip if the key already exists (unless --overwrite).
        exists = False
        try:
            s3.head_object(Bucket=bucket, Key=key)
            exists = True
        except ClientError as e:
            if e.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
                errors.append((key, f"head_object error: {e}"))
                continue

        if exists and not args.overwrite:
            print(f"SKIP (exists)   {key}  ->  {url}")
            results.append((key, url, "skipped-exists", size))
            continue

        if args.dry_run:
            print(f"WOULD UPLOAD    {key}   ({size/1048576:.1f} MiB)  ->  {url}")
            results.append((key, url, "dry-run", size))
            continue

        try:
            s3.upload_file(
                local, bucket, key,
                ExtraArgs={"ContentType": "application/pdf"},
            )
            # Verify by re-reading the object's size.
            head = s3.head_object(Bucket=bucket, Key=key)
            remote_size = head["ContentLength"]
            ok = (remote_size == size)
            status = "uploaded-verified" if ok else f"SIZE-MISMATCH local={size} remote={remote_size}"
            print(f"{'OK' if ok else 'WARN'}   {key}  ({size/1048576:.1f} MiB)  ->  {url}")
            results.append((key, url, status, size))
            if not ok:
                errors.append((key, status))
        except ClientError as e:
            print(f"FAIL  {key}: {e}")
            errors.append((key, str(e)))

    print("-" * 78)
    ok_ct = sum(1 for _, _, s, _ in results if s in ("uploaded-verified", "skipped-exists", "dry-run"))
    print(f"Done. {ok_ct}/{len(to_upload)} ok.  Errors: {len(errors)}")

    # Write a URL map CC can use for the v2 write: key -> public_url.
    # Derived from the manifest's directory so run-2 doesn't clobber run-1's map.
    out = os.path.join(os.path.dirname(args.manifest), "r2_uploaded_urls.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["suggested_r2_key", "public_url", "status", "size_bytes"])
        for key, url, status, size in results:
            w.writerow([key, url, status, size])
    print(f"URL map written: {out}  (feed this to the v2 enrich step)")

    if errors:
        print("\nERRORS:")
        for k, msg in errors:
            print(f"  {k}: {msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
