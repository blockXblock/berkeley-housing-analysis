#!/usr/bin/env python3
"""upload_pdfs_to_r2.py — put project PDFs in R2 and print the rows that record them.

WHY THIS EXISTS. berkeleybuild.com tells people the documents are freely available, so a plan
set that exists only in a scratch directory on one laptop is a promise we are not keeping. The
older experiments/accela_scrape/upload_harvest_to_r2.py is manifest-driven and defaulted its
manifest to /tmp -- which macOS purges on restart, which is the likeliest reason the August 2026
harvest was never mirrored at all. This one takes FILES, so it works on whatever is in front of
you, and it is re-runnable: already-uploaded keys are skipped, not clobbered.

KEY CONVENTION (matches the 274 architect_plans keys already in the bucket):
    architect_plans/proj<id>_<address-slug>_<YYYY-MM-DD>.pdf
The address slug comes from the DATABASE (v_projects_flat.address_display), never from the
filename, so the key agrees with what the site calls the project. A file whose name carries no
leading date gets _nodate_<sha8> instead, which is what the existing nodate keys look like.

COLLISIONS ARE REAL AND MUST NOT OVERWRITE. proj + address + date does NOT identify a document:
2115 Kittredge filed a Tabulation Form AND a revised Entitlement Plan Set on 2023-01-27, and the
bare convention maps both to one key -- uploading the second would have destroyed the first
(documents id 2307) and silently broken its published URL. So when a key exists, this compares
content first: same bytes means already mirrored (skip, no upload); DIFFERENT bytes means a
distinct document, and it disambiguates with a kind token taken from the source filename
(the bucket already has _planset_ and _zoning-resubmission_ keys), falling back to _<sha8>.
Nothing is ever replaced unless --overwrite is passed explicitly.

THE ':' GUARD IS LOAD-BEARING. Two keys in the bucket read architect_plans%3Aproj15_... -- a
colon reached a key and got percent-encoded, so the object is not under the architect_plans/
prefix at all. Any key whose basename contains '/' or ':' is refused here.

VERIFY, DON'T ASSERT. After each upload the object is re-read with head_object and its
ContentLength compared to the local size. An upload that cannot be confirmed is reported as an
error, not as a success.

IT DOES NOT WRITE THE DATABASE. It prints TSV rows for the documents insert and stops, because
a DB write is gated (snapshot -> preview -> go-ahead) and an uploader should not be the thing
that decides to take that step.

  .venv/bin/python scripts/upload_pdfs_to_r2.py --dry-run FILE...
  .venv/bin/python scripts/upload_pdfs_to_r2.py FILE...
"""
import argparse, hashlib, os, re, sqlite3, sys

DB = "databases/berkeley_housing_v2.db"
ENV_FILE = ".env.r2"
PREFIX = "architect_plans"
ENV_KEYS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET", "R2_PUBLIC_BASE")


def load_env(path=ENV_FILE):
    """Fill any unset R2_* var from the gitignored .env.r2. Values are never printed."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line[7:].strip() if line.startswith("export ") else line
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in ENV_KEYS and not os.environ.get(k):
            os.environ[k] = v


def need(name):
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Missing {name}. Put it in {ENV_FILE} or the environment.")
    return v


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slug(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def project_of(path, override):
    """Project id from --project, else the numeric parent directory the harvester wrote."""
    if override:
        return override
    parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if parent.isdigit():
        return int(parent)
    sys.exit(f"Cannot infer a project id for {path}. Pass --project.")


def kind_token(path, address):
    """A short readable token for what the document IS, from the source filename.

    Follows the two hand-made keys already in the bucket (_planset_, _zoning-resubmission_)
    rather than inventing a scheme. Drops the leading date and every word of the address --
    both are already in the key -- and truncates on a word boundary, so the token reads as
    words rather than ending mid-syllable.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}[_\s-]*", "", stem)
    words = slug(stem).split("-")
    drop = set(slug(address).split("-")) | {"of", "the"}
    words = [w for w in words if w and w not in drop]
    tok = ""
    for w in words:
        if len(tok) + len(w) + 1 > 36:
            break
        tok = f"{tok}-{w}" if tok else w
    return tok or "doc"


def build_key(conn, path, project_id, digest):
    row = conn.execute(
        "SELECT address_display FROM v_projects_flat WHERE project_id=?", (project_id,)
    ).fetchone()
    if not row or not row[0]:
        sys.exit(f"proj{project_id} has no address_display — refusing to invent a key.")
    m = re.match(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    stamp = m.group(1) if m else f"nodate_{digest[:8]}"
    key = f"{PREFIX}/proj{project_id}_{slug(row[0])}_{stamp}.pdf"
    base = key.split("/")[-1]
    if "/" in base or ":" in base:
        sys.exit(f"Refusing key with '/' or ':' in the basename: {key}")
    return key, row[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--project", type=int, help="override the inferred project id")
    ap.add_argument("--db", default=DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace an existing key (default: skip it)")
    a = ap.parse_args()

    load_env()
    account, bucket = need("R2_ACCOUNT_ID"), need("R2_BUCKET")
    public = need("R2_PUBLIC_BASE").rstrip("/")

    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    s3 = boto3.client("s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
                      aws_access_key_id=need("R2_ACCESS_KEY_ID"),
                      aws_secret_access_key=need("R2_SECRET_ACCESS_KEY"),
                      config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
                      region_name="auto")
    conn = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)

    print(f"bucket={bucket}  prefix={PREFIX}/  files={len(a.files)}"
          f"{'  [DRY RUN]' if a.dry_run else ''}\n" + "-" * 78)
    rows, errors = [], []
    for path in a.files:
        if not os.path.isfile(path):
            errors.append((path, "not a file")); continue
        pid = project_of(path, a.project)
        size = os.path.getsize(path)
        digest = sha256_file(path)
        key, addr = build_key(conn, path, pid, digest)
        url = f"{public}/{key}"

        def remote_len(k):
            try:
                return s3.head_object(Bucket=bucket, Key=k)["ContentLength"]
            except ClientError as e:
                if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                    return None
                raise

        try:
            taken = remote_len(key)
            if taken is not None and taken != size and not a.overwrite:
                # a DIFFERENT document already owns this key -- disambiguate, never replace
                for cand in (f"{key[:-4]}_{kind_token(path, addr)}.pdf", f"{key[:-4]}_{digest[:8]}.pdf"):
                    if remote_len(cand) is None:
                        print(f"  collision on {os.path.basename(key)}"
                              f" (remote {taken:,}B != local {size:,}B) -> {os.path.basename(cand)}")
                        key = cand
                        url = f"{public}/{key}"
                        taken = None
                        break
                else:
                    errors.append((key, "collision and both fallback keys are taken")); continue
        except ClientError as e:
            errors.append((key, f"head_object: {e}")); continue

        if taken is not None and not a.overwrite:
            print(f"  skip (already mirrored, same size)  {key}")
            rows.append((pid, addr, path, size, digest, url)); continue
        if a.dry_run:
            print(f"  would upload  {size/1048576:8.1f} MB  {key}")
            rows.append((pid, addr, path, size, digest, url)); continue

        with open(path, "rb") as f:
            s3.upload_fileobj(f, bucket, key, ExtraArgs={"ContentType": "application/pdf"})
        try:
            got = s3.head_object(Bucket=bucket, Key=key)["ContentLength"]
        except ClientError as e:
            errors.append((key, f"uploaded but unverifiable: {e}")); continue
        if got != size:
            errors.append((key, f"size mismatch after upload: local={size} remote={got}")); continue
        print(f"  uploaded + verified  {size/1048576:8.1f} MB  {key}")
        rows.append((pid, addr, path, size, digest, url))

    print("-" * 78)
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for k, e in errors:
            print(f"  {k}: {e}")
    out = "scratch/r2_upload_rows.tsv"
    os.makedirs("scratch", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("project_id\taddress\tlocal_path\tfile_size_bytes\tsha256\tr2_url\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")
    print(f"{len(rows)} row(s) for the documents insert -> {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
