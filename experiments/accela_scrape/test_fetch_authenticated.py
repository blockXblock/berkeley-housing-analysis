"""
Fetch B2019-05574 with an authenticated session.

Reads the Cookie header value from cookies.txt (which the user creates
by copy-pasting from Chrome DevTools), then fetches the permit detail page.
Verifies the response is the full 3.4MB document with Processing Status
data, not the 290KB anonymous shell.
"""
import sys
from pathlib import Path
import requests

URL = "https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY&IsToShowInspection="
COOKIE_FILE = Path("cookies.txt")

if not COOKIE_FILE.exists():
    print("ERROR: cookies.txt not found.")
    print()
    print("To create it:")
    print("  1. In Chrome, while logged into Accela, open DevTools (Cmd+Option+I)")
    print("  2. Network tab")
    print("  3. Reload the Accela page (or navigate to any Accela URL)")
    print("  4. Click the request to aca-prod.accela.com in the network log")
    print("  5. Headers tab → Request Headers → find 'Cookie:'")
    print("  6. Right-click the Cookie value, Copy value")
    print("  7. Save to cookies.txt in this directory")
    print()
    print("Then re-run this script.")
    sys.exit(1)

cookie_header = COOKIE_FILE.read_text().strip()
print(f"Loaded cookie header: {len(cookie_header)} chars")

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Cookie": cookie_header,
    "Referer": "https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Building",
}

print(f"\nFetching {URL[:100]}...")
response = requests.get(URL, headers=headers, timeout=60)
print(f"Status: {response.status_code}")
print(f"Size: {len(response.content):,} bytes")
print(f"  (Anonymous baseline was 290,553 bytes)")
print(f"  (CIC reported authenticated size: ~3,400,000 bytes)")

text = response.text
print(f"\nContent verification:")
print(f"  Sharon Gong: {'YES' if 'Sharon Gong' in text else 'NO'}")
print(f"  Kong Chung: {'YES' if 'Kong Chung' in text else 'NO'}")
print(f"  Bill Schrader: {'YES' if 'Bill Schrader' in text else 'NO'}")
print(f"  01/14/2022 (Finaled date): {'YES' if '01/14/2022' in text else 'NO'}")
print(f"  09/10/2020 (Issued date): {'YES' if '09/10/2020' in text else 'NO'}")
print(f"  'Phase II of II' (description): {'YES' if 'Phase II of II' in text else 'NO'}")

out_path = "response_authenticated.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)
print(f"\nSaved to: {out_path}")

if len(response.content) > 1_000_000 and "Sharon Gong" in text:
    print("\n✓ SUCCESS: Authenticated session returns full content. Pipeline path confirmed.")
elif len(response.content) < 500_000:
    print("\n✗ Still receiving stripped response. Cookies may be expired or wrong.")
else:
    print("\n⚠ Partial result. Check the saved file manually.")
