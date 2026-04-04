"""
Step 5: Merge manual overrides and output final labs.json.

Transforms pipeline data into the final schema and merges with
user-provided manual overrides. Manual entries always win.
"""

import json
import re
from datetime import date

from config import INTERMEDIATE_DIR, OUTPUT_DIR

INPUT_FILE = f"{INTERMEDIATE_DIR}/04_links.json"
OVERRIDES_FILE = f"{OUTPUT_DIR}/manual_overrides.json"
OUTPUT_FILE = f"{OUTPUT_DIR}/labs.json"


def slugify(text):
    """Create a URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def infer_lab_name(pi_name):
    """Infer a lab name from PI name (e.g., 'Caroline Uhler' -> 'Uhler Lab')."""
    parts = pi_name.strip().split()
    if parts:
        return f"{parts[-1]} Lab"
    return "Unknown Lab"


def determine_departments(author):
    """Determine department list for display."""
    depts = []

    # From validated departments (scraped)
    for d in author.get("validated_departments", []):
        if d not in depts:
            depts.append(d)

    # From OpenAlex institutions
    for inst in author.get("institutions", []):
        name = inst.get("display_name", "")
        # Skip generic "MIT" — we want specific units
        if name in ("Massachusetts Institute of Technology", "MIT"):
            continue
        # Shorten common names
        short = name.replace("Massachusetts Institute of Technology", "MIT")
        if short not in depts:
            depts.append(short)

    return depts if depts else ["MIT"]


def transform_author(author):
    """Transform a pipeline author entry into the final lab card schema."""
    pi_name = author.get("display_name", "Unknown")
    departments = determine_departments(author)

    # Build a stable ID
    dept_slug = slugify(departments[0]) if departments else "mit"
    lab_id = f"{slugify(pi_name)}-{dept_slug}"

    # Extract OpenAlex ID (short form)
    oa_id = author.get("openalex_id", "")
    if "/" in oa_id:
        oa_id_short = oa_id.split("/")[-1]
    else:
        oa_id_short = oa_id

    entry = {
        "id": lab_id,
        "pi_name": pi_name,
        "lab_name": infer_lab_name(pi_name),
        "departments": departments,
        "research_summary": "",  # Filled in Iteration 2
        "tags": author.get("tags", []),
        "links": author.get("links", {}),
        "openalex_id": oa_id_short,
        "manually_added": False,
        "last_updated": str(date.today()),
    }

    return entry


def merge_overrides(labs, overrides):
    """Merge manual overrides into the labs list."""
    labs_by_id = {lab["id"]: lab for lab in labs}

    # Apply overrides
    for lab_id, override in overrides.get("override", {}).items():
        if lab_id in labs_by_id:
            lab = labs_by_id[lab_id]

            # Override specific fields
            for key in ("pi_name", "lab_name", "departments", "research_summary", "links"):
                if key in override:
                    lab[key] = override[key]

            # Handle tags
            if override.get("replace_tags"):
                lab["tags"] = override.get("tags", [])
            elif "extra_tags" in override:
                lab["tags"].extend(override["extra_tags"])

            lab["last_updated"] = str(date.today())

    # Add manual entries
    for entry in overrides.get("add", []):
        entry.setdefault("manually_added", True)
        entry.setdefault("last_updated", str(date.today()))
        entry.setdefault("research_summary", "")
        entry.setdefault("tags", [])
        entry.setdefault("links", {})

        # Override existing or add new
        if entry.get("id") in labs_by_id:
            labs_by_id[entry["id"]] = entry
        else:
            labs_by_id[entry["id"]] = entry

    return list(labs_by_id.values())


def main():
    # Load pipeline data
    with open(INPUT_FILE) as f:
        faculty = json.load(f)

    print(f"Loaded {len(faculty)} faculty from pipeline")

    # Transform to final schema
    labs = [transform_author(a) for a in faculty]

    # Filter to MIT-affiliated researchers
    MIT_KEYWORDS = [
        "mit", "massachusetts institute of technology", "csail", "eecs",
        "lincoln lab", "broad institute", "koch institute", "mcgovern",
        "media lab", "haystack", "kavli", "plasma science", "fusion",
        "lids", "idss", "rle", "ll mit",
    ]
    MIT_DEPT_NAMES = [
        "CSAIL", "EECS", "Biology", "Chemistry", "Physics", "EAPS",
        "Koch Institute", "Math", "BioE", "ChemE", "McGovern",
        "Media Lab", "NSE",
    ]

    def is_mit_affiliated(lab):
        for dept in lab.get("departments", []):
            dept_lower = dept.lower()
            if any(kw in dept_lower for kw in MIT_KEYWORDS):
                return True
            if dept in MIT_DEPT_NAMES:
                return True
        return False

    mit_labs = [lab for lab in labs if is_mit_affiliated(lab)]
    non_mit = len(labs) - len(mit_labs)
    print(f"MIT-affiliated: {len(mit_labs)}, filtered out: {non_mit}")
    labs = mit_labs

    # Remove entries with no tags (not useful for the tool)
    labs_with_tags = [lab for lab in labs if lab["tags"]]
    labs_without_tags = len(labs) - len(labs_with_tags)
    print(f"Labs with tags: {len(labs_with_tags)}, without tags (excluded): {labs_without_tags}")

    labs = labs_with_tags

    # Load and merge manual overrides
    try:
        with open(OVERRIDES_FILE) as f:
            overrides = json.load(f)
        labs = merge_overrides(labs, overrides)
        print(f"After merging overrides: {len(labs)} labs")
    except FileNotFoundError:
        print("No manual_overrides.json found, skipping merge")
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse manual_overrides.json: {e}")

    # Sort by PI last name
    labs.sort(key=lambda x: x.get("pi_name", "").split()[-1].lower() if x.get("pi_name") else "")

    # Deduplicate by PI name (keep first occurrence which has more data)
    seen_names = set()
    deduped = []
    for lab in labs:
        name_key = lab["pi_name"].lower().strip()
        if name_key not in seen_names:
            seen_names.add(name_key)
            deduped.append(lab)

    print(f"After dedup: {len(deduped)} labs (removed {len(labs) - len(deduped)} duplicates)")
    labs = deduped

    # Category stats
    cat_counts = {}
    for lab in labs:
        cats = set()
        for tag in lab.get("tags", []):
            cats.add(tag.get("category", ""))
        for cat in cats:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print("\nLabs per category:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(labs, f, indent=2)

    print(f"\nFinal output: {len(labs)} labs -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
