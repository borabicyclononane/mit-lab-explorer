"""
Step 2: Validate and supplement faculty data with MIT department pages.

Scrapes public MIT department faculty directories and cross-references
with OpenAlex data to improve coverage.
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

from config import RATE_LIMIT_DELAY, INTERMEDIATE_DIR

INPUT_FILE = f"{INTERMEDIATE_DIR}/01_openalex_authors.json"
OUTPUT_FILE = f"{INTERMEDIATE_DIR}/02_validated_faculty.json"

HEADERS = {
    "User-Agent": "MIT-Lab-Explorer/1.0 (Science Bowl research tool)"
}

# Department scraping configs: (name, url, parser_function_name)
DEPARTMENTS = [
    # Tier 1
    ("CSAIL", "https://www.csail.mit.edu/people?person_type=All&research_area=All&page={page}", "parse_csail"),
    ("EECS", "https://www.eecs.mit.edu/people/faculty-research-staff/", "parse_generic_list"),
    ("Biology", "https://biology.mit.edu/faculty/", "parse_generic_list"),
    ("Chemistry", "https://chemistry.mit.edu/faculty/", "parse_generic_list"),
    ("Physics", "https://physics.mit.edu/faculty/", "parse_generic_list"),
    ("EAPS", "https://eaps.mit.edu/people/", "parse_generic_list"),
    ("Koch Institute", "https://ki.mit.edu/people/faculty", "parse_generic_list"),
    # Tier 2
    ("Math", "https://math.mit.edu/directory/faculty.html", "parse_generic_list"),
    ("BioE", "https://be.mit.edu/directory", "parse_generic_list"),
    ("ChemE", "https://cheme.mit.edu/people/", "parse_generic_list"),
    ("McGovern", "https://mcgovern.mit.edu/principal-investigators/", "parse_generic_list"),
    ("Media Lab", "https://www.media.mit.edu/people/?filter=group&tag=faculty", "parse_generic_list"),
    ("NSE", "https://web.mit.edu/nse/people/faculty.html", "parse_generic_list"),
]


def fetch_page(url, timeout=15):
    """Fetch a web page, return BeautifulSoup or None on error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        print(f"  Warning: Could not fetch {url}: {e}")
        return None


def extract_names_from_page(soup):
    """Generic name extraction — looks for common patterns in faculty pages."""
    names = set()
    if not soup:
        return names

    # Strategy 1: Look for heading tags with person names
    # Most faculty pages use h2, h3, or h4 for names, or links with names
    for tag in soup.find_all(["h2", "h3", "h4"]):
        text = tag.get_text(strip=True)
        # Filter: likely a person name if 2-4 words, mostly alpha
        words = text.split()
        if 2 <= len(words) <= 5 and all(re.match(r"^[A-Za-z\.\-\'\,]+$", w) for w in words):
            # Skip common non-name headings
            lower = text.lower()
            if any(skip in lower for skip in [
                "faculty", "research", "staff", "people", "directory",
                "professor", "department", "institute", "about", "contact",
                "principal", "investigators", "emerit"
            ]):
                continue
            names.add(text)

    # Strategy 2: Look for links that seem to be person profile links
    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "")
        text = a_tag.get_text(strip=True)

        # Check if link goes to a profile-like URL
        if any(pattern in href for pattern in ["/people/", "/faculty/", "/profile/", "/~"]):
            words = text.split()
            if 2 <= len(words) <= 5 and all(re.match(r"^[A-Za-z\.\-\'\,]+$", w) for w in words):
                lower = text.lower()
                if not any(skip in lower for skip in [
                    "faculty", "research", "staff", "all ", "view", "more",
                    "page", "next", "previous"
                ]):
                    names.add(text)

    # Strategy 3: look for card-like divs with class names suggesting people
    for div in soup.find_all(["div", "article", "li"], class_=re.compile(
        r"(person|faculty|member|profile|card|people)", re.I
    )):
        # Look for the name within the card
        name_tag = div.find(["h2", "h3", "h4", "a", "span"], class_=re.compile(
            r"(name|title|heading)", re.I
        ))
        if name_tag:
            text = name_tag.get_text(strip=True)
            words = text.split()
            if 2 <= len(words) <= 5:
                names.add(text)

    return names


def parse_csail(base_url):
    """CSAIL has paginated results."""
    all_names = set()
    for page_num in range(20):  # up to 20 pages
        url = base_url.format(page=page_num)
        soup = fetch_page(url)
        if not soup:
            break
        names = extract_names_from_page(soup)
        if not names and page_num > 0:
            break  # no more pages
        all_names.update(names)
        time.sleep(RATE_LIMIT_DELAY)
    return all_names


def parse_generic_list(url):
    """Generic parser for a single-page faculty listing."""
    soup = fetch_page(url)
    return extract_names_from_page(soup)


def normalize_name(name):
    """Normalize a name for fuzzy matching."""
    # Remove titles, suffixes
    name = re.sub(r"\b(Prof\.?|Dr\.?|Ph\.?D\.?|Jr\.?|Sr\.?|III?|IV)\b", "", name, flags=re.I)
    # Remove punctuation
    name = re.sub(r"[^\w\s]", "", name)
    # Normalize whitespace and lowercase
    return " ".join(name.lower().split())


def fuzzy_match_name(name1, name2, threshold=0.75):
    """Check if two names are likely the same person."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    # Exact match after normalization
    if n1 == n2:
        return True

    # Check if last names match and first name/initial matches
    parts1 = n1.split()
    parts2 = n2.split()
    if parts1 and parts2:
        # Last names match
        if parts1[-1] == parts2[-1]:
            # First names: check initial or fuzzy
            if parts1[0][0] == parts2[0][0]:
                return True

    # Fall back to sequence matching
    return SequenceMatcher(None, n1, n2).ratio() >= threshold


def main():
    # Load OpenAlex data
    with open(INPUT_FILE) as f:
        openalex_authors = json.load(f)

    print(f"Loaded {len(openalex_authors)} authors from OpenAlex")

    # Build lookup by normalized name
    oa_by_name = {}
    for author in openalex_authors:
        norm = normalize_name(author["display_name"])
        oa_by_name[norm] = author

    # Scrape department pages
    dept_faculty = {}  # dept_name -> set of names
    all_dept_names = set()

    for dept_name, url, parser_name in DEPARTMENTS:
        print(f"\nScraping {dept_name}...")

        if parser_name == "parse_csail":
            names = parse_csail(url)
        else:
            names = parse_generic_list(url)

        dept_faculty[dept_name] = names
        all_dept_names.update(names)
        print(f"  Found {len(names)} names")
        time.sleep(RATE_LIMIT_DELAY)

    print(f"\nTotal unique names from department pages: {len(all_dept_names)}")

    # Cross-reference: annotate OpenAlex authors with department info
    matched_oa = set()
    for author in openalex_authors:
        author["validated_departments"] = []
        for dept_name, names in dept_faculty.items():
            for dept_person in names:
                if fuzzy_match_name(author["display_name"], dept_person):
                    author["validated_departments"].append(dept_name)
                    matched_oa.add(author["openalex_id"])
                    break

    print(f"\nOpenAlex authors matched to departments: {len(matched_oa)}")

    # Find department faculty NOT in OpenAlex (potential missing PIs)
    unmatched_dept = []
    for dept_name, names in dept_faculty.items():
        for person_name in names:
            found = False
            for author in openalex_authors:
                if fuzzy_match_name(person_name, author["display_name"]):
                    found = True
                    break
            if not found:
                unmatched_dept.append({
                    "display_name": person_name,
                    "department": dept_name,
                    "openalex_id": "",
                    "works_count": 0,
                    "cited_by_count": 0,
                    "institutions": [],
                    "topics": [],
                    "x_concepts": [],
                    "works_api_url": "",
                    "summary_stats": {},
                    "validated_departments": [dept_name],
                    "source": "department_page_only"
                })

    print(f"Faculty on department pages but not in OpenAlex: {len(unmatched_dept)}")

    # Combine
    all_faculty = openalex_authors + unmatched_dept

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_faculty, f, indent=2)

    print(f"\nTotal faculty entries: {len(all_faculty)}")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
