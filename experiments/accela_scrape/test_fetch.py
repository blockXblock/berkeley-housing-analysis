"""
Test whether Accela permit detail pages can be fetched without a browser.

Two URLs to try (both confirmed stable from Claude in Chrome reconnaissance):
  - ZP2018-0135 (Planning module)
  - B2019-05574 (Building module)

Reports HTTP status, response size, content-type, and detects whether
the response looks like:
  - the actual permit page (contains permit number text)
  - a login redirect / page
  - some kind of error or anti-bot page
"""
import requests
from urllib.parse import urlparse


TEST_URLS = [
    {
        "name": "ZP2018-0135 (Planning)",
        "url": "https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Planning&TabName=Planning&capID1=18PLN&capID2=00000&capID3=00808&agencyCode=BERKELEY&IsToShowInspection=",
        "expected_text": "ZP2018-0135",
    },
    {
        "name": "B2019-05574 (Building)",
        "url": "https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY&IsToShowInspection=",
        "expected_text": "B2019-05574",
    },
]

# Realistic browser User-Agent to avoid trivial bot blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def looks_like_login_page(text):
    """Heuristic: detect ASP.NET login forms or Accela login redirects."""
    lower = text.lower()
    return any(
        marker in lower for marker in (
            "login.aspx",
            "sign in",
            "<title>citizen access</title>",  # Accela login landing
            "please login",
        )
    )


def looks_like_anti_bot(text):
    """Heuristic: Cloudflare or anti-bot challenge."""
    lower = text.lower()
    return any(
        marker in lower for marker in (
            "cloudflare",
            "captcha",
            "are you a human",
            "please enable javascript",
            "checking your browser",
        )
    )


def test_url(name, url, expected_text):
    print(f"\n{'=' * 70}")
    print(f"Testing: {name}")
    print(f"URL: {url[:100]}{'...' if len(url) > 100 else ''}")
    print(f"{'=' * 70}")

    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        response = session.get(url, timeout=30, allow_redirects=True)
    except requests.exceptions.Timeout:
        print("✗ Request timed out after 30 seconds")
        return
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        return

    print(f"HTTP status: {response.status_code}")
    print(f"Final URL after redirects: {response.url}")
    print(f"Response size: {len(response.content):,} bytes")
    print(f"Content-Type: {response.headers.get('Content-Type', '(missing)')}")
    print(f"Set-Cookie present: {'yes' if 'Set-Cookie' in response.headers else 'no'}")
    print(f"Number of redirects: {len(response.history)}")

    text = response.text

    # Look for the expected permit text
    has_permit_text = expected_text in text
    print(f"Contains '{expected_text}': {'YES' if has_permit_text else 'NO'}")

    # Look for diagnostic markers
    if looks_like_login_page(text):
        print("⚠ Response looks like a login page")
    if looks_like_anti_bot(text):
        print("⚠ Response looks like an anti-bot challenge")
    if "<form" in text.lower() and "viewstate" in text.lower():
        print("✓ Response contains ASP.NET viewstate (real Accela page)")
    if "<iframe" in text.lower():
        iframe_count = text.lower().count("<iframe")
        print(f"  iframe tags found: {iframe_count}")

    # Save the response body for manual inspection
    safe_name = name.split()[0].replace("-", "_")
    out_path = f"response_{safe_name}.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  Response saved to: {out_path} ({len(text):,} chars)")

    # Quick verdict
    if response.status_code == 200 and has_permit_text:
        print("\n✓ SUCCESS: page fetched, contains expected permit info")
    elif response.status_code == 200 and not has_permit_text:
        print("\n⚠ 200 OK but expected permit text not found — page may be a login or error page")
    elif response.status_code in (301, 302):
        print(f"\n⚠ Redirected (final URL: {response.url})")
    else:
        print(f"\n✗ Non-success status: {response.status_code}")


if __name__ == "__main__":
    print("Accela URL scriptability test")
    print("Tests whether Accela permit detail pages can be fetched without a browser.")

    for test in TEST_URLS:
        test_url(test["name"], test["url"], test["expected_text"])

    print(f"\n{'=' * 70}")
    print("Done. Inspect response_*.html files to see what came back.")
    print(f"{'=' * 70}")
