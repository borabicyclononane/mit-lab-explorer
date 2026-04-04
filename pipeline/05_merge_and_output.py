"""
Step 5: Merge manual overrides and output final labs.json.

Filters to VERIFIED MIT faculty only (from department directories),
transforms to final schema, merges manual overrides.
"""

import json
import re
from datetime import date

from config import INTERMEDIATE_DIR, OUTPUT_DIR
from verified_faculty import VERIFIED_FACULTY, get_departments_for_name

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
    """Infer a lab name from PI name."""
    parts = pi_name.strip().split()
    if parts:
        return f"{parts[-1]} Lab"
    return "Unknown Lab"


def match_to_verified(display_name):
    """Try to match an OpenAlex author name to verified faculty.
    Returns (canonical_name, departments) or (None, None)."""
    depts = get_departments_for_name(display_name)
    if depts is not None:
        return display_name, depts

    # Try without middle names/initials
    parts = display_name.split()
    if len(parts) > 2:
        short_name = f"{parts[0]} {parts[-1]}"
        depts = get_departments_for_name(short_name)
        if depts is not None:
            return display_name, depts

    return None, None


def transform_author(author, verified_depts):
    """Transform a pipeline author entry into the final lab card schema."""
    pi_name = author.get("display_name", "Unknown")

    # Use verified departments as the primary source
    departments = list(verified_depts) if verified_depts else ["MIT"]

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
        "research_summary": "",
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

    for lab_id, override in overrides.get("override", {}).items():
        if lab_id in labs_by_id:
            lab = labs_by_id[lab_id]
            for key in ("pi_name", "lab_name", "departments", "research_summary", "links"):
                if key in override:
                    lab[key] = override[key]
            if override.get("replace_tags"):
                lab["tags"] = override.get("tags", [])
            elif "extra_tags" in override:
                lab["tags"].extend(override["extra_tags"])
            lab["last_updated"] = str(date.today())

    for entry in overrides.get("add", []):
        entry.setdefault("manually_added", True)
        entry.setdefault("last_updated", str(date.today()))
        entry.setdefault("research_summary", "")
        entry.setdefault("tags", [])
        entry.setdefault("links", {})
        labs_by_id[entry["id"]] = entry

    return list(labs_by_id.values())


def main():
    with open(INPUT_FILE) as f:
        faculty = json.load(f)

    print(f"Loaded {len(faculty)} authors from pipeline")
    print(f"Verified faculty whitelist: {len(VERIFIED_FACULTY)} names")

    # Match OpenAlex authors against verified faculty whitelist
    matched = []
    unmatched_names = []
    for author in faculty:
        name = author.get("display_name", "")
        canonical, depts = match_to_verified(name)
        if canonical is not None:
            matched.append((author, depts))
        else:
            unmatched_names.append(name)

    print(f"Matched to verified faculty: {len(matched)}")
    print(f"Unmatched (excluded): {len(unmatched_names)}")

    # Transform matched authors
    labs = [transform_author(author, depts) for author, depts in matched]

    # Remove entries with no tags
    labs_with_tags = [lab for lab in labs if lab["tags"]]
    print(f"With tags: {len(labs_with_tags)}, without tags (excluded): {len(labs) - len(labs_with_tags)}")
    labs = labs_with_tags

    # Merge manual overrides
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

    # Deduplicate by normalized name
    seen_names = set()
    deduped = []
    for lab in labs:
        name_key = re.sub(r"\s+[A-Z]\.?\s+", " ", lab["pi_name"])  # strip middle initials
        name_key = name_key.lower().strip()
        if name_key not in seen_names:
            seen_names.add(name_key)
            deduped.append(lab)

    print(f"After dedup: {len(deduped)} labs (removed {len(labs) - len(deduped)} duplicates)")
    labs = deduped

    # Category stats
    cat_counts = {}
    for lab in labs:
        cats = set(tag.get("category", "") for tag in lab.get("tags", []))
        for cat in cats:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print("\nLabs per category:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Write compact JSON for frontend
    compact = []
    for lab in labs:
        entry = {"id": lab["id"], "n": lab["pi_name"], "d": lab["departments"]}
        if lab.get("research_summary"):
            entry["s"] = lab["research_summary"]
        default_lab = lab["pi_name"].split()[-1] + " Lab"
        if lab.get("lab_name") and lab["lab_name"] != default_lab:
            entry["l"] = lab["lab_name"]
        entry["t"] = []
        for tag in lab.get("tags", []):
            t = [tag["category"], tag["subcategory"]]
            if tag.get("focus"):
                t.append(tag["focus"])
            entry["t"].append(t)
        links = {}
        short_keys = {"lab_website": "w", "publications_page": "p", "mit_profile": "m",
                      "google_scholar": "g", "semantic_scholar": "ss", "openalex": "o"}
        for key, val in lab.get("links", {}).items():
            if val:
                links[short_keys.get(key, key)] = val
        if links:
            entry["k"] = links
        if lab.get("openalex_id"):
            entry["oa"] = lab["openalex_id"]
        compact.append(entry)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(compact, f, separators=(",", ":"))

    import os
    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\nFinal output: {len(compact)} labs -> {OUTPUT_FILE} ({size_kb:.0f}KB)")


if __name__ == "__main__":
    main()
