"""
Resolve Google Scholar profile URLs using a real browser (Playwright).

Opens a visible Chrome window. If Google shows a CAPTCHA, the script
pauses and waits for you to solve it manually, then continues.

Usage:
    python3 resolve_scholar_browser.py
"""

import json
import os
import random
import re
import time
from urllib.parse import quote

from playwright.sync_api import sync_playwright

LABS_FILE = "../data/labs.json"
SCHOLAR_CACHE = "../data/scholar_cache.json"

MIN_DELAY = 6
MAX_DELAY = 12


def load_cache():
    if os.path.exists(SCHOLAR_CACHE):
        with open(SCHOLAR_CACHE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(SCHOLAR_CACHE, "w") as f:
        json.dump(cache, f, indent=2)


def safe_content(page):
    """Get page content, waiting for navigation to settle."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass
    # Small sleep to let any redirects finish
    time.sleep(0.5)
    try:
        return page.content()
    except Exception:
        time.sleep(2)
        try:
            return page.content()
        except Exception:
            return ""


def is_captcha(content):
    """Check if page content indicates a CAPTCHA or block."""
    if not content:
        return False
    lower = content.lower()[:2000]
    return "captcha" in lower or "unusual traffic" in lower or "are not a robot" in lower


def wait_for_captcha(page):
    """Check if CAPTCHA/block is present. If so, wait for user to solve it."""
    content = safe_content(page)
    if not is_captcha(content):
        return False

    print("\n  ⚠️  CAPTCHA detected! Please solve it in the browser window...")
    print("     Waiting for you to solve it (will auto-resume)...")

    # Wait until the page no longer has CAPTCHA indicators
    while True:
        time.sleep(3)
        content = safe_content(page)
        if not content:
            continue
        if not is_captcha(content):
            print("     ✓ CAPTCHA solved! Resuming...")
            time.sleep(2)
            return True
    return True


def extract_scholar_id(page):
    """Extract Google Scholar user ID from current page."""
    content = safe_content(page)
    user_ids = re.findall(r'user=([A-Za-z0-9_-]{12})', content)
    if user_ids:
        return user_ids[0]
    return None


def strip_middle_initial(name):
    """'Bryan D. Bryson' -> 'Bryan Bryson', 'Kevin B. Burdge' -> 'Kevin Burdge'."""
    # Match single letter followed by optional period, surrounded by spaces
    stripped = re.sub(r'\s+[A-Z]\.?\s+', ' ', name)
    # Also handle multiple initials like "J. A. Formaggio" -> try "J. Formaggio"
    return stripped if stripped != name else None


def search_scholar(page, query):
    """Search Google Scholar for a query, handle CAPTCHA, return user ID or status."""
    url = f"https://scholar.google.com/citations?view_op=search_authors&mauthors={quote(query)}+MIT"

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
    except Exception:
        time.sleep(2)

    time.sleep(1)

    if wait_for_captcha(page):
        time.sleep(2)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
        except Exception:
            time.sleep(2)
        time.sleep(1)
        wait_for_captcha(page)

    content = safe_content(page)
    if "429" in page.url or "Too Many Requests" in content:
        return "RATELIMIT"

    user_ids = re.findall(r'user=([A-Za-z0-9_-]{12})', content)
    if user_ids:
        return user_ids[0]
    return None


def resolve_one(page, name):
    """Try full name first, then without middle initials if no result."""
    result = search_scholar(page, name)
    if result:
        return result

    # Try without middle initial(s): "Bryan D. Bryson" -> "Bryan Bryson"
    stripped = strip_middle_initial(name)
    if stripped:
        time.sleep(random.uniform(3, 5))
        print(f"(retry: {stripped})...", end=" ", flush=True)
        result = search_scholar(page, stripped)
        if result:
            return result

    # Try first + last only (handles "J. A. Formaggio" -> "Formaggio")
    parts = name.split()
    if len(parts) >= 3:
        first_last = f"{parts[0]} {parts[-1]}"
        if first_last != stripped and first_last != name:
            time.sleep(random.uniform(3, 5))
            print(f"(retry: {first_last})...", end=" ", flush=True)
            result = search_scholar(page, first_last)
            if result:
                return result

    return None


def main():
    with open(LABS_FILE) as f:
        labs = json.load(f)

    cache = load_cache()
    found_before = sum(1 for v in cache.values() if v and v not in ("RATELIMIT", "CAPTCHA"))
    print(f"Loaded {len(labs)} labs, {len(cache)} cached ({found_before} resolved)")

    # Build todo list (unique names not yet cached)
    seen = set()
    todo = []
    for lab in labs:
        name = lab["n"]
        if name not in seen and name not in cache:
            todo.append(name)
            seen.add(name)

    print(f"Need to resolve: {len(todo)}")
    if not todo:
        print("All done!")
        return

    import subprocess

    # Launch real Chrome with remote debugging — no automation flags.
    chrome_profile = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".chrome_profile")
    os.makedirs(chrome_profile, exist_ok=True)
    chrome_proc = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        f"--remote-debugging-port=9222",
        f"--user-data-dir={chrome_profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        # Navigate to Google Scholar to establish session
        print("Opening Google Scholar...")
        try:
            page.goto("https://scholar.google.com", wait_until="domcontentloaded", timeout=15000)
        except Exception:
            pass
        time.sleep(2)

        # Check if immediately blocked
        wait_for_captcha(page)

        resolved = 0
        failed = 0

        for idx, name in enumerate(todo):
            delay = random.uniform(MIN_DELAY, MAX_DELAY)

            # Longer break every 30
            if idx > 0 and idx % 30 == 0:
                pause = random.uniform(20, 40)
                print(f"\n  -- Pause {pause:.0f}s after {idx} requests --")
                save_cache(cache)
                time.sleep(pause)

            print(f"[{idx+1}/{len(todo)}] {name}...", end=" ", flush=True)

            try:
                scholar_id = resolve_one(page, name)
            except Exception as e:
                print(f"error: {e}")
                scholar_id = None

            if scholar_id == "RATELIMIT":
                print("Rate limited. Waiting 60s...")
                save_cache(cache)
                time.sleep(60)
                try:
                    scholar_id = resolve_one(page, name)
                except Exception:
                    scholar_id = None
                if scholar_id == "RATELIMIT":
                    print("Still blocked. Saving and stopping.")
                    save_cache(cache)
                    break

            if scholar_id and scholar_id != "RATELIMIT":
                cache[name] = scholar_id
                resolved += 1
                print(f"-> {scholar_id}")
            else:
                cache[name] = None
                failed += 1
                print("-> not found")

            if (resolved + failed) % 10 == 0:
                save_cache(cache)

            time.sleep(delay)

        save_cache(cache)
        browser.close()
        chrome_proc.terminate()

    # ── Apply results to labs.json ──
    applied = 0
    for lab in labs:
        name = lab["n"]
        scholar_id = cache.get(name)
        if scholar_id and scholar_id not in ("RATELIMIT", "CAPTCHA"):
            profile_url = f"https://scholar.google.com/citations?user={scholar_id}"
            if "k" not in lab:
                lab["k"] = {}
            lab["k"]["g"] = profile_url
            applied += 1

    with open(LABS_FILE, "w") as f:
        json.dump(labs, f, separators=(",", ":"))

    total_resolved = sum(1 for v in cache.values() if v and v not in ("RATELIMIT", "CAPTCHA"))
    print(f"\nSession: resolved {resolved}, failed {failed}")
    print(f"Total cached: {len(cache)}, {total_resolved} with profiles")
    print(f"Applied {applied} profile URLs to labs.json")
    remaining = len(todo) - (resolved + failed)
    if remaining > 0:
        print(f"Remaining: {remaining}. Run again to continue.")


if __name__ == "__main__":
    main()
