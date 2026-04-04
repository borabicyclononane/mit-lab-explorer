"""
Step 4: Resolve external links for each PI.

Constructs links from available data without slow API lookups.
OpenAlex URL and Google Scholar search URL are always available.
Semantic Scholar lookups deferred to Iteration 2 for speed.
"""

import json
from urllib.parse import quote

from config import INTERMEDIATE_DIR

INPUT_FILE = f"{INTERMEDIATE_DIR}/03_tagged_faculty.json"
OUTPUT_FILE = f"{INTERMEDIATE_DIR}/04_links.json"


def construct_google_scholar_search(name):
    """Construct a Google Scholar search URL for the person."""
    return f"https://scholar.google.com/scholar?q=author:%22{quote(name)}%22+MIT"


def construct_openalex_url(openalex_id):
    """Construct OpenAlex author page URL."""
    if openalex_id:
        if openalex_id.startswith("https://"):
            return openalex_id
        return f"https://openalex.org/authors/{openalex_id}"
    return ""


def resolve_links_for_author(author):
    """Resolve available links for an author (fast, no API calls)."""
    name = author.get("display_name", "")
    openalex_id = author.get("openalex_id", "")

    links = {
        "lab_website": "",
        "publications_page": "",
        "mit_profile": "",
        "google_scholar": construct_google_scholar_search(name),
        "semantic_scholar": "",
        "openalex": construct_openalex_url(openalex_id),
    }

    # MIT profile: construct search URL
    if name:
        links["mit_profile"] = f"https://web.mit.edu/search/?q={quote(name)}&site=people"

    return links


def main():
    with open(INPUT_FILE) as f:
        faculty = json.load(f)

    print(f"Resolving links for {len(faculty)} faculty...")

    for author in faculty:
        author["links"] = resolve_links_for_author(author)

    print(f"Done. All entries have Google Scholar + OpenAlex links.")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(faculty, f, indent=2)

    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
