"""
Resolve Google Scholar profile URLs from search pages.

For each professor, fetches the Google Scholar search page and extracts
the first user= profile ID from the results. Saves progress incrementally.
Uses randomized delays and varied request patterns to avoid rate limiting.
"""

import json
import os
import random
import re
import time
from urllib.parse import quote

LABS_FILE = "../data/labs.json"
CACHE_FILE = "../data/scholar_cache.json"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

MIN_DELAY = 8
MAX_DELAY = 16


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def fetch_scholar_id(name):
    """Fetch Google Scholar search page and extract first profile user ID."""
    import requests

    url = f"https://scholar.google.com/scholar?q=author:%22{quote(name)}%22+MIT"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code == 429:
            return "RATELIMIT"

        if resp.status_code != 200:
            return None

        if "CAPTCHA" in resp.text or "unusual traffic" in resp.text:
            return "CAPTCHA"

        user_ids = re.findall(r'user=([A-Za-z0-9_-]{12})', resp.text)
        if user_ids:
            return user_ids[0]
        return None

    except Exception as e:
        print(f"  Error: {e}")
        return None


def main():
    with open(LABS_FILE) as f:
        labs = json.load(f)

    cache = load_cache()
    found_before = sum(1 for v in cache.values() if v)
    print(f"Loaded {len(labs)} labs, {len(cache)} cached ({found_before} resolved)")

    resolved = 0
    failed = 0
    skipped = 0
    consecutive_fails = 0

    todo = [(i, lab) for i, lab in enumerate(labs) if lab["n"] not in cache]
    print(f"Need to resolve: {len(todo)}")

    for idx, (i, lab) in enumerate(todo):
        name = lab["n"]

        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        # Every 30 requests, take a longer break
        if idx > 0 and idx % 30 == 0:
            pause = random.uniform(30, 60)
            print(f"  -- Pause {pause:.0f}s after {idx} requests --")
            time.sleep(pause)

        print(f"[{idx+1}/{len(todo)}] {name}...", end=" ", flush=True)

        scholar_id = fetch_scholar_id(name)

        if scholar_id in ("RATELIMIT", "CAPTCHA"):
            print(f"-> {scholar_id}! Backing off 120s...")
            save_cache(cache)
            time.sleep(120)
            # Retry once
            scholar_id = fetch_scholar_id(name)
            if scholar_id in ("RATELIMIT", "CAPTCHA"):
                print(f"-> Still blocked. Saving and stopping.")
                save_cache(cache)
                break

        if scholar_id and scholar_id not in ("RATELIMIT", "CAPTCHA"):
            cache[name] = scholar_id
            resolved += 1
            consecutive_fails = 0
            print(f"-> {scholar_id}")
        else:
            cache[name] = None
            failed += 1
            consecutive_fails += 1
            print(f"-> not found")

        if (resolved + failed) % 10 == 0:
            save_cache(cache)

        time.sleep(delay)

    save_cache(cache)

    # Apply all cached results to labs.json
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

    total_resolved = sum(1 for v in cache.values() if v)
    print(f"\nSession: resolved {resolved}, failed {failed}")
    print(f"Total cached: {len(cache)}, {total_resolved} with profiles")
    print(f"Applied {applied} profile URLs to labs.json")
    remaining = len(labs) - len(cache)
    if remaining > 0:
        print(f"Remaining: {remaining}. Run again to continue.")


if __name__ == "__main__":
    main()
