"""
Resolve real links (lab websites, Google Scholar profiles, publications pages)
by chaining: OpenAlex -> ORCID -> personal websites -> scrape for links.

Pipeline per professor:
1. Fetch OpenAlex author record for ORCID
2. Fetch ORCID profile for researcher URLs (personal website, lab page)
3. Scrape each discovered page for Google Scholar profile links and pub pages
4. Save everything incrementally

Uses polite delays. Saves progress after every 5 professors.
"""

import json
import os
import random
import re
import time
from urllib.parse import quote, urljoin, urlparse

import requests

LABS_FILE = "../data/labs.json"
CACHE_FILE = "../data/links_cache.json"
SCHOLAR_CACHE = "../data/scholar_cache.json"

MIN_DELAY = 0.5
MAX_DELAY = 1.5

session = requests.Session()
session.headers.update({
    "User-Agent": "MIT-Lab-Explorer/1.0 (academic research project; polite bot)",
})


def load_cache(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_cache(cache, path):
    with open(path, "w") as f:
        json.dump(cache, f, indent=2)


def fetch_html(url, timeout=10):
    """Fetch URL, return (html, final_url) or (None, None)."""
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and len(resp.text) > 100:
            return resp.text, resp.url
    except Exception:
        pass
    return None, None


def fetch_json(url, timeout=10, headers=None):
    """Fetch URL as JSON."""
    try:
        resp = session.get(url, timeout=timeout, headers=headers or {})
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def find_scholar_id(html):
    """Extract first Google Scholar user ID from HTML."""
    ids = re.findall(r'scholar\.google\.com/citations\?[^"\'<>\s]*user=([A-Za-z0-9_-]{12})', html)
    return ids[0] if ids else None


def find_publications_url(html, base_url):
    """Find a publications/papers page link from HTML."""
    # Match links whose text or href contains publication-related words
    # Pattern: <a href="URL">...text with publication keyword...</a>
    matches = re.findall(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL
    )
    for href, text in matches:
        combined = (href + " " + text).lower()
        if any(kw in combined for kw in ['publication', 'papers', 'selected works', 'bibliography', 'research output']):
            url = urljoin(base_url, href)
            # Skip google scholar, anchors, javascript
            if 'scholar.google' in url or 'javascript:' in url:
                continue
            if url == base_url or url == base_url + '#':
                continue
            # Must be a real URL
            if url.startswith('http'):
                return url
    return None


def find_lab_website(html, base_url):
    """Find external lab/personal website from an MIT or ORCID-linked page."""
    matches = re.findall(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL
    )
    for href, text in matches:
        combined = (href + " " + text).lower()
        if any(kw in combined for kw in ['lab', 'group', 'research group', 'homepage', 'personal', 'website']):
            url = urljoin(base_url, href)
            if url.startswith('http') and 'scholar.google' not in url:
                return url
    return None


def get_orcid_from_openalex(openalex_id):
    """Get ORCID from OpenAlex author record."""
    data = fetch_json(f"https://api.openalex.org/authors/{openalex_id}")
    if data:
        orcid = data.get("orcid", "")
        if orcid:
            return orcid.split("/")[-1]
    return None


def get_urls_from_orcid(orcid_id):
    """Get researcher URLs from ORCID public API."""
    data = fetch_json(
        f"https://pub.orcid.org/v3.0/{orcid_id}/person",
        headers={"Accept": "application/json"},
    )
    urls = []
    if data:
        researcher_urls = data.get("researcher-urls", {}).get("researcher-url", [])
        for entry in researcher_urls:
            url = entry.get("url", {}).get("value", "")
            name = entry.get("url-name", "")
            if url:
                urls.append({"url": url, "name": name})

        # Also check websites section
        websites = data.get("external-identifiers", {}).get("external-identifier", [])
        for w in websites:
            ext_type = w.get("external-id-type", "")
            ext_url = w.get("external-id-url", {}).get("value", "")
            if ext_url:
                urls.append({"url": ext_url, "name": ext_type})
    return urls


def resolve_professor(name, openalex_id):
    """Resolve links for one professor. Returns dict."""
    result = {
        "scholar_id": None,
        "lab_website": None,
        "publications_page": None,
        "mit_profile": None,
        "orcid_urls": [],
    }

    pages_to_scan = []  # list of (html, url) to scan for scholar/pub links

    # ── Step 1: OpenAlex → ORCID → URLs ──
    orcid_id = None
    if openalex_id:
        orcid_id = get_orcid_from_openalex(openalex_id)
        time.sleep(random.uniform(0.2, 0.5))

    orcid_urls = []
    if orcid_id:
        orcid_urls = get_urls_from_orcid(orcid_id)
        result["orcid_urls"] = [u["url"] for u in orcid_urls]
        time.sleep(random.uniform(0.2, 0.5))

    # ── Step 2: Fetch each ORCID URL ──
    for entry in orcid_urls:
        url = entry["url"]
        url_name = (entry.get("name") or "").lower()

        # Check if it's directly a Google Scholar link
        if "scholar.google" in url:
            sid = find_scholar_id(url)
            if sid:
                result["scholar_id"] = sid
            continue

        # Skip social media
        if any(s in url for s in ['twitter.com', 'linkedin.com', 'facebook.com', 'github.com', 'youtube.com', 'x.com']):
            continue

        # Fetch the page
        html, final_url = fetch_html(url)
        if html:
            pages_to_scan.append((html, final_url or url))

            # If this looks like a lab/personal page, record it
            if not result["lab_website"]:
                parsed = urlparse(final_url or url)
                domain = parsed.hostname or ""
                # MIT pages are MIT profiles, not lab websites
                if "mit.edu" in domain:
                    if "search/?q=" not in (final_url or url):
                        result["mit_profile"] = final_url or url
                else:
                    result["lab_website"] = final_url or url

        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    # ── Step 3: If we found a lab website, also check for /publications etc. ──
    if result["lab_website"] and len(pages_to_scan) > 0:
        # We already have the lab website HTML from step 2
        pass

    # ── Step 4: Try MIT department pages (common patterns) ──
    # If we found a mit_profile from ORCID, fetch it
    if result["mit_profile"] and not any(result["mit_profile"] in (p[1] or "") for p in pages_to_scan):
        html, final_url = fetch_html(result["mit_profile"])
        if html:
            pages_to_scan.append((html, final_url or result["mit_profile"]))
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    # ── Step 5: Scan all pages for Scholar IDs and publications ──
    for html, base_url in pages_to_scan:
        if not result["scholar_id"]:
            sid = find_scholar_id(html)
            if sid:
                result["scholar_id"] = sid

        if not result["publications_page"]:
            pub = find_publications_url(html, base_url)
            if pub:
                result["publications_page"] = pub

        if not result["lab_website"]:
            lab = find_lab_website(html, base_url)
            if lab:
                result["lab_website"] = lab

    # ── Step 6: If we found a lab website but haven't scanned it for scholar ──
    if result["lab_website"] and not result["scholar_id"]:
        already_scanned = any(result["lab_website"] in (p[1] or "") for p in pages_to_scan)
        if not already_scanned:
            html, final_url = fetch_html(result["lab_website"])
            if html:
                sid = find_scholar_id(html)
                if sid:
                    result["scholar_id"] = sid
                if not result["publications_page"]:
                    pub = find_publications_url(html, final_url or result["lab_website"])
                    if pub:
                        result["publications_page"] = pub
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    return result


def main():
    with open(LABS_FILE) as f:
        labs = json.load(f)

    cache = load_cache(CACHE_FILE)
    scholar_cache = load_cache(SCHOLAR_CACHE)

    # Deduplicate by name, collect OpenAlex IDs
    professors = []
    seen = set()
    for lab in labs:
        n = lab["n"]
        if n not in seen:
            professors.append({"name": n, "oa": lab.get("oa", "")})
            seen.add(n)

    todo = [p for p in professors if p["name"] not in cache]
    print(f"Total: {len(professors)}, cached: {len(cache)}, todo: {len(todo)}")

    for idx, prof in enumerate(todo):
        name = prof["name"]
        print(f"[{idx+1}/{len(todo)}] {name}...", end=" ", flush=True)

        result = resolve_professor(name, prof["oa"])
        cache[name] = result

        parts = []
        if result["scholar_id"]:
            parts.append(f"scholar={result['scholar_id']}")
        if result["lab_website"]:
            domain = urlparse(result["lab_website"]).hostname or ""
            parts.append(f"web={domain}")
        if result["publications_page"]:
            parts.append("pubs=yes")
        if result["mit_profile"]:
            parts.append("mit=yes")
        print(" | ".join(parts) if parts else "nothing found")

        if (idx + 1) % 5 == 0:
            save_cache(cache, CACHE_FILE)

        # Polite delay between professors
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        # Longer break every 100
        if (idx + 1) % 100 == 0:
            pause = random.uniform(5, 10)
            print(f"  -- Pause {pause:.0f}s --")
            time.sleep(pause)

    save_cache(cache, CACHE_FILE)

    # ── Apply results to labs.json ──
    scholar_found = 0
    web_found = 0
    pub_found = 0
    mit_found = 0

    for lab in labs:
        name = lab["n"]
        info = cache.get(name, {})
        if not info:
            continue

        if "k" not in lab:
            lab["k"] = {}

        # Google Scholar: prefer cache hit, then old scholar_cache
        existing_g = lab["k"].get("g", "")
        has_real_scholar = "user=" in existing_g

        if info.get("scholar_id") and not has_real_scholar:
            lab["k"]["g"] = f"https://scholar.google.com/citations?user={info['scholar_id']}"
            scholar_found += 1
        elif not has_real_scholar:
            sc = scholar_cache.get(name)
            if sc and sc not in ("RATELIMIT", "CAPTCHA"):
                lab["k"]["g"] = f"https://scholar.google.com/citations?user={sc}"
                scholar_found += 1

        # Lab website
        if info.get("lab_website") and "w" not in lab["k"]:
            lab["k"]["w"] = info["lab_website"]
            web_found += 1

        # Publications page
        if info.get("publications_page") and "p" not in lab["k"]:
            lab["k"]["p"] = info["publications_page"]
            pub_found += 1

        # MIT profile (only real ones, not search URLs)
        if info.get("mit_profile"):
            mit_url = info["mit_profile"]
            if "search/?q=" not in mit_url:
                lab["k"]["m"] = mit_url
                mit_found += 1

    with open(LABS_FILE, "w") as f:
        json.dump(labs, f, separators=(",", ":"))

    print(f"\n── Applied to labs.json ──")
    print(f"New Scholar profiles: {scholar_found}")
    print(f"Lab websites: {web_found}")
    print(f"Publications pages: {pub_found}")
    print(f"Real MIT profiles: {mit_found}")

    # Stats
    total_scholar = sum(1 for l in labs if "user=" in l.get("k", {}).get("g", ""))
    total_web = sum(1 for l in labs if l.get("k", {}).get("w"))
    total_pub = sum(1 for l in labs if l.get("k", {}).get("p"))
    print(f"\n── Totals ──")
    print(f"Scholar profiles: {total_scholar}/{len(labs)}")
    print(f"Lab websites: {total_web}/{len(labs)}")
    print(f"Publications: {total_pub}/{len(labs)}")


if __name__ == "__main__":
    main()
