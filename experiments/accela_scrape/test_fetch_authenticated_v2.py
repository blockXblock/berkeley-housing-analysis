"""
Refined authenticated fetch. Differences from v1:
- Matches User-Agent to the Chrome version you're actually using (147)
- Adds sec-ch-ua headers Chrome sends
- Reports response section content more granularly
"""
import sys
from pathlib import Path
import requests

URL = "https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY&IsToShowInspection="
COOKIE_FILE = Path("cookies.txt")

if not COOKIE_FILE.exists():
    print("ERROR: cookies.txt not found.")
    sys.exit(1)

cookie_header = COOKIE_FILE.read_text().strip()
print(f"Loaded cookie header: {len(cookie_header)} chars")

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cookie": cookie_header,
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

print(f"\nFetching {URL[:100]}...")
response = requests.get(URL, headers=headers, timeout=60)
print(f"Status: {response.status_code}")
print(f"Size: {len(response.content):,} bytes")
print(f"  (Anonymous baseline: 290,553 bytes)")
print(f"  (v1 authenticated: 293,044 bytes)")
print(f"  (CIC reported: ~3,400,000 bytes)")

text = response.text

print(f"\n=== Content checks ===")
checks = [
    ("Bill Schrader (applicant)", "Bill Schrader"),
    ("'Phase II of II' (description)", "Phase II of II"),
    ("Kong Chung (B-permit reviewer)", "Kong Chung"),
    ("David Lopez (B-permit reviewer)", "David Lopez"),
    ("01/14/2022 (Finaled date)", "01/14/2022"),
    ("09/10/2020 (Issued date)", "09/10/2020"),
    ("'Inspector' string", "Inspector"),
    ("Processing Status text", "Processing Status"),
    ("'shProcessStatus' div ID", "shProcessStatus"),
    ("Empty processing status span", "shProcessStatus'></span>"),
    ("Empty processing status span variant", 'shProcessStatus"></span>'),
]
for label, needle in checks:
    found = needle in text
    print(f"  {'YES' if found else 'NO ':3} | {label}")

out_path = "response_authenticated_v2.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)
print(f"\nSaved to: {out_path}")
