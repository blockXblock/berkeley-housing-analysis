#!/usr/bin/env python3
"""Upload a recorded tour video to YouTube and repoint the site at it.

YouTube will NOT let you replace the file of an existing video -- that is permanent
platform policy, not a setting we are missing. A re-record is always a NEW video with
a NEW id, so the job is: upload, then swap the id everywhere the site names it.

The site names it in TWO places that nothing keeps in sync:
  * docs/index.html  -- hardcoded <iframe src=".../embed/<id>?rel=0&modestbranding=1">
  * docs/tours.json  -- entry["video"]["youtube"]
This script updates BOTH, and refuses to update one without the other.

Quota: videos.insert costs 1600 units against a default 10,000/day allowance, so about
SIX uploads per day. Plan a ten-video re-record as two days, or request a quota raise.

Usage:
  python scripts/upload_tour_video.py --tour telegraph-s2n \
      --video "/Volumes/T7-2025/Berkeley-Tours/New/1-Telegraph-S-N.m4v" [--privacy unlisted]
  python scripts/upload_tour_video.py --tour telegraph-s2n --video ... --dry-run
  python scripts/upload_tour_video.py --tour telegraph-s2n --set-id dQw4w9WgXcQ   # no upload
"""
import argparse, json, pathlib, re, socket, sys, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOURS = ROOT / "docs/tours.json"
INDEX = ROOT / "docs/index.html"
SECRETS = ROOT / ".secrets/youtube_client_secret.json"   # gitignored; you create this
TOKEN   = ROOT / ".secrets/youtube_token.json"           # written on first auth
SCOPES  = ["https://www.googleapis.com/auth/youtube.upload"]
ID_RE   = re.compile(r"^[A-Za-z0-9_-]{11}$")
FIRST_PUBLISH_ID = [None]   # set in main(), used by swap_site_id on first publish


def load_catalog():
    d = json.loads(TOURS.read_text())
    entries = d if isinstance(d, list) else d.get("tours", d)
    if isinstance(entries, dict):
        entries = list(entries.values())
    return d, entries


def find_entry(entries, tour_id):
    hit = [e for e in entries if e.get("id") == tour_id]
    if not hit:
        near = [e.get("id") for e in entries if tour_id in str(e.get("id"))]
        sys.exit(f"no catalog entry with id {tour_id!r}" + (f"; did you mean {near}?" if near else ""))
    return hit[0]


def describe(entry):
    """Title and description from the catalog, so the video says what it actually shows."""
    title = entry.get("title") or entry["id"]
    sha = entry.get("package_geometry_sha", "unknown")
    dur = entry.get("duration_s")
    lines = [
        "A flight over Berkeley's housing pipeline, from berkeleybuild.com.",
        "",
        "Buildings are drawn from the project's own reconstruction of the pipeline "
        "from entitlement, to building permit, to certificate of occupancy, built from primary sources "
        "(CPRA permit records and the Alameda County assessor), not from the city's own filing.",
        "",
        f"Geometry version: geom-{sha}",
        f"Recorded: {datetime.date.today().isoformat()}",
    ]
    if dur:
        lines.append(f"Tour length: {int(dur // 60)}m {int(dur % 60)}s")
    lines += ["", "https://berkeleybuild.com"]
    desc = "\n".join(lines)
    # YouTube rejects < and > anywhere in a title or description (invalidDescription).
    return title.replace("<", "").replace(">", ""), desc.replace("<", "").replace(">", "")


def swap_site_id(old_id, new_id, dry=False):
    """Update BOTH places, or neither. Returns (index_hits, catalog_hits)."""
    if not ID_RE.match(new_id):
        sys.exit(f"{new_id!r} is not a YouTube id (11 chars of [A-Za-z0-9_-])")
    html = INDEX.read_text()
    n_html = html.count(old_id) if old_id else 0
    raw = TOURS.read_text()
    n_json = raw.count(f'"{old_id}"') if old_id else 0
    if old_id and n_html == 0 and n_json == 0:
        sys.exit(f"old id {old_id} appears in neither docs/index.html nor docs/tours.json — refusing")
    if not dry:
        if old_id:
            INDEX.write_text(html.replace(old_id, new_id))
            TOURS.write_text(raw.replace(f'"{old_id}"', f'"{new_id}"'))
    return n_html, n_json


def upload(video_path, title, description, privacy):
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        sys.exit("missing deps. Install into the project venv:\n"
                 "  .venv/bin/pip install google-api-python-client google-auth-oauthlib")
    socket.setdefaulttimeout(300)   # default is short; a stalled chunk killed a 670 MB upload
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not SECRETS.exists():
                sys.exit(f"no OAuth client secret at {SECRETS}. See the header of this file.")
            creds = InstalledAppFlow.from_client_secrets_file(str(SECRETS), SCOPES).run_local_server(port=0)
        TOKEN.parent.mkdir(parents=True, exist_ok=True)
        TOKEN.write_text(creds.to_json())
    yt = build("youtube", "v3", credentials=creds)
    body = {"snippet": {"title": title[:100], "description": description[:5000],
                        "tags": ["Berkeley", "housing", "Google Earth", "berkeleybuild"],
                        "categoryId": "27"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True,
                            mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk(num_retries=5)
        if status:
            print(f"  upload {int(status.progress() * 100):3d}%", end="\r", flush=True)
    print()
    return resp["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", required=True, help="catalog id, e.g. telegraph-s2n")
    ap.add_argument("--video", help="path to the recorded .m4v/.mp4 (on the T7)")
    ap.add_argument("--set-id", help="skip the upload; just repoint the site at this existing id")
    ap.add_argument("--privacy", default="unlisted", choices=["private", "unlisted", "public"])
    ap.add_argument("--recorded", help="ISO date the video was recorded; also stamps the era")
    ap.add_argument("--era", help="geometry sha the recording was flown against, e.g. geom-a3d103322890")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    _, entries = load_catalog()
    entry = find_entry(entries, a.tour)
    old = (entry.get("video") or {}).get("youtube")
    FIRST_PUBLISH_ID[0] = entry["id"]
    title, desc = describe(entry)

    print(f"tour     : {entry['id']}")
    print(f"title    : {title}")
    print(f"current  : {old or '(none published)'}")
    if not a.set_id:                     # on --set-id nothing is uploaded, so the
        print(f"privacy  : {a.privacy}") # default privacy flag is not what YouTube holds

    if a.set_id:
        new_id = a.set_id
    else:
        if not a.video:
            sys.exit("need --video (or --set-id)")
        vp = pathlib.Path(a.video)
        if not vp.exists():
            sys.exit(f"no such video: {vp}")
        print(f"video    : {vp}  ({vp.stat().st_size / 1e6:.0f} MB)")
        print("\n--- description ---\n" + desc + "\n-------------------")
        if a.dry_run:
            print("\nDRY RUN — nothing uploaded, nothing edited.")
            n_h, n_j = swap_site_id(old, "AAAAAAAAAAA", dry=True) if old else (0, 0)
            print(f"would swap {n_h} ref(s) in docs/index.html and {n_j} in docs/tours.json")
            return
        new_id = upload(vp, title, desc, a.privacy)
        print(f"uploaded : https://youtu.be/{new_id}")

    if a.dry_run:
        print("DRY RUN — site not edited.")
        return
    n_h, n_j = swap_site_id(old, new_id)
    # --set-id used to swap the id and leave `recorded`/`recorded_geometry_era` describing the
    # PREVIOUS video: the large-projects entry claimed a May recording for a September file.
    # Provenance that silently describes the wrong footage is worse than none.
    if a.recorded or a.era:
        d = json.loads(TOURS.read_text())
        entries = d if isinstance(d, list) else d.get("tours", d)
        for e in (entries.values() if isinstance(entries, dict) else entries):
            if e.get("id") == entry["id"]:
                if a.recorded:
                    e["recorded"] = a.recorded
                    e["needs_rerecord"] = False
                if a.era:
                    e["recorded_geometry_era"] = a.era
        TOURS.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        print(f"provenance: recorded={a.recorded or 'unchanged'}  era={a.era or 'unchanged'}")
    print(f"site     : {n_h} ref(s) updated in docs/index.html, {n_j} in docs/tours.json")
    if old and n_h == 0:
        print("  !! WARNING: the old id was not in index.html — that page may not embed this tour")
    print("\nNot committed. Review with: git diff docs/index.html docs/tours.json")


if __name__ == "__main__":
    main()
