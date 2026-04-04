"""
Step 1: Collect MIT faculty/researchers from OpenAlex (FREE API).

Queries the OpenAlex Authors endpoint filtered by MIT affiliation,
paginates through all results, and saves author data with concepts.
"""

import json
import time
import requests
from datetime import datetime

from config import (
    OPENALEX_EMAIL, MIT_INSTITUTION_ID, ACTIVE_YEARS,
    MIN_WORKS_COUNT, RATE_LIMIT_DELAY, INTERMEDIATE_DIR
)

OPENALEX_API = "https://api.openalex.org"
OUTPUT_FILE = f"{INTERMEDIATE_DIR}/01_openalex_authors.json"


def fetch_authors():
    """Fetch all MIT-affiliated authors from OpenAlex."""
    current_year = datetime.now().year
    min_year = current_year - ACTIVE_YEARS

    authors = []
    cursor = "*"
    page = 0

    print(f"Fetching MIT authors from OpenAlex (active since {min_year})...")

    while cursor:
        page += 1
        url = (
            f"{OPENALEX_API}/authors"
            f"?filter=last_known_institutions.id:{MIT_INSTITUTION_ID}"
            f",works_count:>{MIN_WORKS_COUNT}"
            f"&per_page=200"
            f"&cursor={cursor}"
            f"&mailto={OPENALEX_EMAIL}"
            f"&select=id,display_name,works_count,cited_by_count,"
            f"last_known_institutions,topics,x_concepts,"
            f"works_api_url,summary_stats"
        )

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"  Error on page {page}: {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        for author in results:
            # Extract relevant fields
            entry = {
                "openalex_id": author.get("id", ""),
                "display_name": author.get("display_name", ""),
                "works_count": author.get("works_count", 0),
                "cited_by_count": author.get("cited_by_count", 0),
                "institutions": [],
                "topics": [],
                "x_concepts": [],
                "works_api_url": author.get("works_api_url", ""),
                "summary_stats": author.get("summary_stats", {}),
            }

            # Extract institution details
            for inst in (author.get("last_known_institutions") or []):
                entry["institutions"].append({
                    "id": inst.get("id", ""),
                    "display_name": inst.get("display_name", ""),
                    "type": inst.get("type", ""),
                })

            # Extract topics (newer OpenAlex field)
            for topic in (author.get("topics") or []):
                entry["topics"].append({
                    "id": topic.get("id", ""),
                    "display_name": topic.get("display_name", ""),
                    "subfield": (topic.get("subfield") or {}).get("display_name", ""),
                    "field": (topic.get("field") or {}).get("display_name", ""),
                    "domain": (topic.get("domain") or {}).get("display_name", ""),
                    "count": topic.get("count", 0),
                })

            # Extract legacy concepts
            for concept in (author.get("x_concepts") or []):
                entry["x_concepts"].append({
                    "id": concept.get("id", ""),
                    "display_name": concept.get("display_name", ""),
                    "level": concept.get("level", 0),
                    "score": concept.get("score", 0),
                })

            authors.append(entry)

        cursor = data.get("meta", {}).get("next_cursor")
        total = data.get("meta", {}).get("count", "?")
        print(f"  Page {page}: fetched {len(results)} authors ({len(authors)} total of ~{total})")

        time.sleep(RATE_LIMIT_DELAY)

    return authors


def filter_likely_pis(authors):
    """Filter toward likely PIs using heuristics."""
    filtered = []
    for a in authors:
        # Heuristics for likely PI status:
        # 1. Higher works count suggests established researcher
        # 2. Higher citation count
        # We keep the threshold low — recall > precision
        works = a.get("works_count", 0)
        citations = a.get("cited_by_count", 0)

        # Check for recent activity via summary_stats
        stats = a.get("summary_stats", {})
        recent_works = stats.get("2yr_works_count", 0)

        # Keep if: decent body of work OR recently active with some citations
        if works >= 20 or (recent_works >= 3 and citations >= 50):
            filtered.append(a)

    return filtered


def main():
    authors = fetch_authors()
    print(f"\nTotal authors fetched: {len(authors)}")

    filtered = filter_likely_pis(authors)
    print(f"After PI filtering: {len(filtered)}")

    # Sort by citation count descending
    filtered.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(filtered, f, indent=2)

    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
