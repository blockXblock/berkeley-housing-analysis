#!/usr/bin/env python3
"""fetch_stars.py — save UC Berkeley's 2025 AASHE STARS report, credit by credit, using John's AASHE account.

AASHE shows each credit's data only to signed-in users. Credentials are read from ~/.aashe.env (AASHE_USER, AASHE_PASS;
chmod 600, outside the repo) and are never printed, logged or written anywhere else. The script signs in through
AASHE's Auth0 page, opens the report's scorecard, collects every credit link, and saves each credit page as HTML and
plain text in data/raw/campus/stars_2025/, plus any files the report links to (uploaded spreadsheets, PDFs). Every saved
file is recorded in manifest.json with its source URL, fetch time and SHA-256. One request every ~2 seconds.

Run:  .venv/bin/python scripts/snapshot/fetch_stars.py [--limit N]
"""
import argparse, datetime, hashlib, json, os, re, time

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'data', 'raw', 'campus', 'stars_2025')
BASE = 'https://reports.aashe.org'
REPORT = '/institutions/university-of-california-berkeley-ca/report/2025-02-19/'


def creds():
    env = dict(l.split('=', 1) for l in open(os.path.expanduser('~/.aashe.env')).read().splitlines() if '=' in l)
    assert env.get('AASHE_USER') and env.get('AASHE_PASS'), '~/.aashe.env needs AASHE_USER and AASHE_PASS'
    return env['AASHE_USER'], env['AASHE_PASS']


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    mpath = os.path.join(OUT, 'manifest.json')
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    user, pw = creds()
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(accept_downloads=True, user_agent='Mozilla/5.0 (BerkeleyBuild research; john.gage)')
        pg = ctx.new_page()
        # ---- sign in (identifier first, then password); nothing about the credentials is printed
        pg.goto(BASE + '/auth0/authenticate/?next=' + REPORT, wait_until='networkidle', timeout=90000)
        pg.fill('input[name="username"]', user)
        pg.press('input[name="username"]', 'Enter')    # the Continue button sits under an overlay
        pg.wait_for_selector('input[name="password"]', timeout=60000)
        pg.fill('input[name="password"]', pw)
        pg.press('input[name="password"]', 'Enter')
        pg.wait_for_load_state('networkidle', timeout=90000)
        del pw
        if 'login.aashe.org' in pg.url:
            raise SystemExit('sign-in did not complete (still on the login page): check the account, or a second factor')
        print('signed in; at', pg.url.split('?')[0])
        # ---- the scorecard: every credit link under this report
        pg.goto(BASE + REPORT, wait_until='networkidle', timeout=90000)
        time.sleep(2)
        hrefs = sorted({h for h in pg.eval_on_selector_all('a[href]', 'els => els.map(e => e.getAttribute("href"))')
                        if h and REPORT in h and re.search(r'/[A-Z]{2,3}-\d+/?$', h)})
        print(f'{len(hrefs)} credit pages on the scorecard')
        if a.limit:
            hrefs = hrefs[:a.limit]
        files = set()
        for h in [REPORT] + hrefs:
            url = h if h.startswith('http') else BASE + h
            code = (re.search(r'/([A-Z]{2,3}-\d+)/?$', h) or [None, 'scorecard'])[1]
            pg.goto(url, wait_until='networkidle', timeout=90000)
            if 'login.aashe.org' in pg.url or '/accounts/login' in pg.url:
                raise SystemExit(f'session lost at {code}')
            html_path = os.path.join(OUT, f'{code}.html')
            txt_path = os.path.join(OUT, f'{code}.txt')
            open(html_path, 'w').write(pg.content())
            open(txt_path, 'w').write(pg.inner_text('body'))
            now = datetime.datetime.now().isoformat(timespec='seconds')
            for fpath in (html_path, txt_path):
                manifest[os.path.basename(fpath)] = dict(url=url, fetched_at=now, sha256=sha(fpath), bytes=os.path.getsize(fpath))
            for f in pg.eval_on_selector_all('a[href]', 'els => els.map(e => e.href)'):
                if re.search(r'stars-static|\.(xlsx?|csv|pdf|docx?)(\?|$)', f, re.I):
                    files.add(f)
            title = pg.title().split('|')[0].strip()
            print(f'  {code:10} {title[:60]}')
            time.sleep(2)
        # ---- linked files (uploaded spreadsheets and documents), fetched in the signed-in session
        for f in sorted(files):
            name = re.sub(r'[^A-Za-z0-9._-]', '_', f.split('?')[0].rsplit('/', 1)[-1])[:120]
            r = ctx.request.get(f, timeout=120000)
            if r.ok:
                path = os.path.join(OUT, 'files', name)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, 'wb').write(r.body())
                manifest['files/' + name] = dict(url=f.split('?')[0], fetched_at=datetime.datetime.now().isoformat(timespec='seconds'),
                                                 sha256=sha(path), bytes=os.path.getsize(path))
                print(f'  file {name} ({len(r.body()):,} bytes)')
            else:
                manifest['unavailable:' + name] = dict(url=f.split('?')[0], status=r.status)
                print(f'  file {name}: HTTP {r.status}')
            time.sleep(2)
        json.dump(manifest, open(mpath, 'w'), indent=1)
        b.close()
    print(f'saved {len(manifest)} entries; manifest {mpath}')


if __name__ == '__main__':
    main()
