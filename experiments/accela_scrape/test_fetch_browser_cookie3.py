"""
Fetch B2019-05574 using cookies from Chrome's Default profile.

Reads from a copy of the cookie file (at /tmp/chrome_default_cookies.db)
to avoid Chrome lock issues. Reports which cookies were found, how they
differ from the manual cookies.txt set, and whether the fetch unlocks
the full ~3.4MB response.
"""
import sys
from pathlib import Path
import requests
import browser_cookie3

URL = "https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY&IsToShowInspection="
COOKIE_DB = "/tmp/chrome_default_cookies.db"

print("Extracting Chrome cookies for accela.com from Default profile...")
try:
    cj = browser_cookie3.chrome(domain_name="accela.com", cookie_file=COOKIE_DB)
except Exception as e:
    print(f"Error: {e}")
    print(f"\nMake sure you ran the cp command first to copy the cookie file.")
    sys.exit(1)

cookie_names = sorted([c.name for c in cj])
print(f"Got {len(cookie_names)} cookies: {cookie_names}")

# Compose Cookie header
cookie_header = "; ".join(f"{c.name}={c.value}" for c in cj)
print(f"Composed Cookie header: {len(cookie_header)} chars")
print(f"  (Manual cookies.txt was 831 chars)")

# Show what's new vs manual
manual_text = Path("cookies.txt").read_text().strip() if Path("cookies.txt").exists() else ""
manual_names = set()
for pair in manual_text.split(";"):
    pair = pair.strip()
    if "=" in pair:
        manual_names.add(pair.split("=", 1)[0])
jar_names = set(cookie_names)
missing_from_manual = jar_names - manual_names
extra_in_manual = manual_names - jar_names
if missing_from_manual:
    print(f"\nCookies present in Chrome but MISSING from manual cookies.txt:")
    for name in sorted(missing_from_manual):
        print(f"    + {name}")
else:
    print(f"\nAll Chrome cookies were already in manual cookies.txt.")
if extra_in_manual:
    print(f"Cookies in manual but NOT in Chrome (unexpected, but possible if Chrome cookies expired):")
    for name in sorted(extra_in_manual):
        print(f"    - {name}")

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Building",
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

print(f"\nFetching with Chrome's full cookie set...")
session = requests.Session()
session.cookies = cj
response = session.get(URL, headers=headers, timeout=60)
print(f"Status: {response.status_code}")
print(f"Size: {len(response.content):,} bytes")
print(f"  (Anonymous baseline: 290,553)")
print(f"  (v1/v2 with manual cookies: 293,044)")
print(f"  (CIC in browser: ~3,400,000)")

text = response.text
print(f"\n=== Content checks ===")
checks = [
    ("Bill Schrader (applicant)", "Bill Schrader"),
    ("'Phase II of II' (description)", "Phase II of II"),
    ("Kong Chung (B-permit reviewer)", "Kong Chung"),
    ("David Lopez (B-permit reviewer)", "David Lopez"),
    ("01/14/2022 (Finaled date)", "01/14/2022"),
    ("09/10/2020 (Issued date)", "09/10/2020"),
]
for label, needle in checks:
    found = needle in text
    print(f"  {'YES' if found else 'NO ':3} | {label}")

out_path = "response_browser_cookie3.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)
print(f"\nSaved to: {out_path}")

# Verdict
if len(response.content) > 1_000_000 and "Kong Chung" in text:
    print("\n✓ SUCCESS: Full cookie set unlocked the rich content.")
    print("  Conclusion: cookies were the missing piece. Pipeline can use requests.")
elif len(response.content) < 500_000:
    print("\n✗ Still receiving stripped ~293KB response.")
    print("  Conclusion: Cookies alone are NOT sufficient. The full content")
    print("  requires JavaScript execution. Pipeline needs Playwright or similar.")
else:
    print("\n⚠ Mixed result — inspect the saved file.")
