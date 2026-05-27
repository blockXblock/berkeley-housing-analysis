"""
Compare anonymous fetch sizes with different header sets to figure out
why our response (290KB) is much smaller than CIC's (3.4MB).
"""
import requests

URL = "https://aca-prod.accela.com/BERKELEY/Cap/CapDetail.aspx?Module=Building&TabName=Building&capID1=DUB19&capID2=00000&capID3=00KIJ&agencyCode=BERKELEY&IsToShowInspection="

# Test 1: minimal headers
HEADERS_MINIMAL = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
}

# Test 2: full browser-like headers including Referer (the page would normally be
# arrived at by clicking a search result, so Referer would be set)
HEADERS_FULL = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Building&TabName=Building",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
}

# Test 3: pre-warm a session by visiting CapHome first (sets cookies that
# might unlock the full response)
def test_with_warmup():
    session = requests.Session()
    session.headers.update(HEADERS_FULL)
    print("\n--- Test 3: session warmup ---")
    print("First fetching CapHome to establish session cookies...")
    warmup = session.get(
        "https://aca-prod.accela.com/BERKELEY/Cap/CapHome.aspx?module=Building&TabName=Building",
        timeout=30,
    )
    print(f"  CapHome status: {warmup.status_code}, size: {len(warmup.content):,} bytes")
    print(f"  Cookies after warmup: {len(session.cookies)} cookies set")
    print(f"  Cookie names: {[c.name for c in session.cookies]}")
    print("Now fetching the permit detail with warmed session...")
    response = session.get(URL, timeout=30)
    return response

def test(name, headers):
    print(f"\n--- {name} ---")
    response = requests.get(URL, headers=headers, timeout=30)
    print(f"  Status: {response.status_code}, size: {len(response.content):,} bytes")
    return response

if __name__ == "__main__":
    print(f"Target URL: {URL[:100]}...")

    r1 = test("Test 1: minimal headers (no Referer)", HEADERS_MINIMAL)
    with open("response_v2_test1.html", "w") as f:
        f.write(r1.text)

    r2 = test("Test 2: full browser headers + Referer", HEADERS_FULL)
    with open("response_v2_test2.html", "w") as f:
        f.write(r2.text)

    r3 = test_with_warmup()
    with open("response_v2_test3.html", "w") as f:
        f.write(r3.text)
    print(f"  Final status: {r3.status_code}, size: {len(r3.content):,} bytes")

    print("\n--- Content check (all three) ---")
    for fname in ("response_v2_test1.html", "response_v2_test2.html", "response_v2_test3.html"):
        with open(fname) as f:
            content = f.read()
        has_gong = "Sharon Gong" in content or "sharon gong" in content.lower()
        has_chung = "Kong Chung" in content or "kong chung" in content.lower()
        has_jan_date = "01/14/2022" in content
        print(f"  {fname}: {len(content):,} chars | Sharon Gong: {has_gong} | Kong Chung: {has_chung} | 01/14/2022: {has_jan_date}")
