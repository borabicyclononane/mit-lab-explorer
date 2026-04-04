"""
Step 3: Auto-tag faculty from OpenAlex concepts/topics.

Maps OpenAlex concept hierarchy to Science Bowl categories and generates
rough three-layer tags. These are placeholder tags for Iteration 1.
"""

import json
import re

from config import INTERMEDIATE_DIR

INPUT_FILE = f"{INTERMEDIATE_DIR}/02_validated_faculty.json"
OUTPUT_FILE = f"{INTERMEDIATE_DIR}/03_tagged_faculty.json"

# ── Mapping OpenAlex domains/fields to Science Bowl categories ──

DOMAIN_MAP = {
    # Life Sciences
    "Life Sciences": "Biology",
    "Biomedical Sciences": "Biology",

    # Physical Sciences
    "Physical Sciences": None,  # need to look at field level

    # Social Sciences, Arts, etc. — less relevant but might have some
    "Social Sciences": None,
    "Health Sciences": "Biology",
}

FIELD_MAP = {
    # Biology
    "Biochemistry, Genetics and Molecular Biology": "Biology",
    "Agricultural and Biological Sciences": "Biology",
    "Immunology and Microbiology": "Biology",
    "Neuroscience": "Biology",
    "Pharmacology, Toxicology and Pharmaceutics": "Biology",

    # Chemistry
    "Chemistry": "Chemistry",
    "Chemical Engineering": "Chemistry",
    "Materials Science": "Chemistry",

    # Physics
    "Physics and Astronomy": "Physics",
    "Engineering": None,  # too broad

    # Earth & Space
    "Earth and Planetary Sciences": "Earth & Space",
    "Environmental Science": "Earth & Space",

    # CS/AI/Stats
    "Computer Science": "CS/AI/Stats",
    "Mathematics": "CS/AI/Stats",
    "Decision Sciences": "CS/AI/Stats",

    # Other
    "Medicine": "Biology",
    "Nursing": None,
    "Psychology": "Biology",
    "Arts and Humanities": None,
    "Business, Management and Accounting": None,
    "Economics, Econometrics and Finance": "CS/AI/Stats",
    "Energy": "Chemistry",
    "Multidisciplinary": None,
}

# More specific concept-to-category mappings for x_concepts
CONCEPT_CATEGORY_MAP = {
    # CS/AI
    "computer science": "CS/AI/Stats",
    "artificial intelligence": "CS/AI/Stats",
    "machine learning": "CS/AI/Stats",
    "deep learning": "CS/AI/Stats",
    "natural language processing": "CS/AI/Stats",
    "computer vision": "CS/AI/Stats",
    "data mining": "CS/AI/Stats",
    "algorithm": "CS/AI/Stats",
    "statistics": "CS/AI/Stats",
    "mathematics": "CS/AI/Stats",
    "probability": "CS/AI/Stats",
    "linear algebra": "CS/AI/Stats",
    "optimization": "CS/AI/Stats",
    "reinforcement learning": "CS/AI/Stats",
    "neural network": "CS/AI/Stats",
    "robotics": "CS/AI/Stats",
    "cryptography": "CS/AI/Stats",
    "distributed computing": "CS/AI/Stats",
    "programming language": "CS/AI/Stats",
    "operating system": "CS/AI/Stats",
    "database": "CS/AI/Stats",
    "combinatorics": "CS/AI/Stats",
    "graph theory": "CS/AI/Stats",

    # Biology
    "biology": "Biology",
    "genetics": "Biology",
    "molecular biology": "Biology",
    "biochemistry": "Biology",
    "cell biology": "Biology",
    "microbiology": "Biology",
    "neuroscience": "Biology",
    "immunology": "Biology",
    "ecology": "Biology",
    "evolution": "Biology",
    "genomics": "Biology",
    "proteomics": "Biology",
    "bioinformatics": "Biology",
    "cancer research": "Biology",
    "virology": "Biology",
    "botany": "Biology",
    "zoology": "Biology",
    "developmental biology": "Biology",
    "pharmacology": "Biology",
    "physiology": "Biology",
    "pathology": "Biology",
    "biophysics": "Biology",
    "structural biology": "Biology",
    "systems biology": "Biology",
    "synthetic biology": "Biology",
    "gene expression": "Biology",
    "protein": "Biology",
    "enzyme": "Biology",
    "dna": "Biology",
    "rna": "Biology",
    "crispr": "Biology",
    "stem cell": "Biology",

    # Chemistry
    "chemistry": "Chemistry",
    "organic chemistry": "Chemistry",
    "inorganic chemistry": "Chemistry",
    "physical chemistry": "Chemistry",
    "analytical chemistry": "Chemistry",
    "polymer": "Chemistry",
    "catalysis": "Chemistry",
    "materials science": "Chemistry",
    "nanotechnology": "Chemistry",
    "electrochemistry": "Chemistry",
    "spectroscopy": "Chemistry",
    "photochemistry": "Chemistry",
    "chemical engineering": "Chemistry",
    "thermochemistry": "Chemistry",
    "supramolecular chemistry": "Chemistry",
    "stereochemistry": "Chemistry",
    "computational chemistry": "Chemistry",

    # Physics
    "physics": "Physics",
    "quantum mechanics": "Physics",
    "quantum physics": "Physics",
    "condensed matter physics": "Physics",
    "particle physics": "Physics",
    "nuclear physics": "Physics",
    "optics": "Physics",
    "thermodynamics": "Physics",
    "classical mechanics": "Physics",
    "electromagnetism": "Physics",
    "astrophysics": "Physics",
    "plasma": "Physics",
    "quantum computing": "Physics",
    "quantum field theory": "Physics",
    "string theory": "Physics",
    "relativity": "Physics",
    "cosmology": "Physics",
    "semiconductor": "Physics",
    "superconductivity": "Physics",
    "laser": "Physics",
    "photonics": "Physics",

    # Earth & Space
    "geology": "Earth & Space",
    "geophysics": "Earth & Space",
    "oceanography": "Earth & Space",
    "atmospheric science": "Earth & Space",
    "climate": "Earth & Space",
    "meteorology": "Earth & Space",
    "seismology": "Earth & Space",
    "paleontology": "Earth & Space",
    "astronomy": "Earth & Space",
    "planetary science": "Earth & Space",
    "earth science": "Earth & Space",
    "remote sensing": "Earth & Space",
    "hydrology": "Earth & Space",
    "volcanology": "Earth & Space",
    "mineralogy": "Earth & Space",
    "geochemistry": "Earth & Space",
}

# Subcategory mappings for common concepts
SUBCATEGORY_MAP = {
    # CS/AI
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "artificial intelligence": "Machine Learning",
    "natural language processing": "Deep Learning",
    "computer vision": "Deep Learning",
    "reinforcement learning": "Reinforcement Learning",
    "neural network": "Deep Learning",
    "algorithm": "Algorithms & Theoretical CS",
    "data mining": "Machine Learning",
    "statistics": "Probability & Statistics",
    "probability": "Probability & Statistics",
    "optimization": "Mathematical Modeling",
    "robotics": "Practical CS/Computer Engineering",
    "cryptography": "Algorithms & Theoretical CS",
    "distributed computing": "Practical CS/Computer Engineering",
    "programming language": "Algorithms & Theoretical CS",
    "linear algebra": "Linear Algebra",
    "combinatorics": "Algorithms & Theoretical CS",
    "graph theory": "Algorithms & Theoretical CS",

    # Biology
    "genetics": "Genetics/Evolution",
    "molecular biology": "Cell/Molecular Biology",
    "biochemistry": "Biochemistry",
    "cell biology": "Cell/Molecular Biology",
    "microbiology": "Physiology",
    "neuroscience": "Nervous System & Neuroscience",
    "immunology": "Immune System & Immunology",
    "ecology": "Ecology",
    "evolution": "Genetics/Evolution",
    "genomics": "Genomics & Bioinformatics",
    "bioinformatics": "Genomics & Bioinformatics",
    "cancer research": "Hallmarks of Cancer",
    "developmental biology": "Cell/Molecular Biology",
    "pharmacology": "Biochemistry",
    "physiology": "Physiology",
    "systems biology": "Cell/Molecular Biology",
    "synthetic biology": "CRISPR & Genetic Engineering",
    "gene expression": "Genetics/Evolution",
    "protein": "Biochemistry",
    "enzyme": "Biochemistry",
    "crispr": "CRISPR & Genetic Engineering",
    "stem cell": "Cell/Molecular Biology",
    "structural biology": "Biochemistry",
    "proteomics": "Genomics & Bioinformatics",
    "virology": "Immune System & Immunology",

    # Chemistry
    "organic chemistry": "Organic Chemistry",
    "inorganic chemistry": "Descriptive Chemistry",
    "physical chemistry": "Thermodynamics",
    "analytical chemistry": "Miscellaneous",
    "polymer": "Polymer Chemistry",
    "catalysis": "Kinetics & Equilibria",
    "materials science": "Materials Chemistry",
    "nanotechnology": "Materials Chemistry",
    "electrochemistry": "Redox Chemistry",
    "spectroscopy": "Spectroscopy",
    "computational chemistry": "Computational Chemistry",
    "stereochemistry": "Stereochemistry",

    # Physics
    "quantum mechanics": "Quantum Mechanics",
    "quantum physics": "Quantum Mechanics",
    "condensed matter physics": "Quantum Mechanics",
    "particle physics": "Particle Physics",
    "nuclear physics": "Particle Physics",
    "optics": "Waves/Optics",
    "thermodynamics": "Thermodynamics",
    "classical mechanics": "Classical Mechanics",
    "electromagnetism": "Electricity & Magnetism",
    "astrophysics": "Astronomy",
    "plasma": "Particle Physics",
    "quantum computing": "Quantum Computing",
    "semiconductor": "Electricity & Magnetism",
    "superconductivity": "Quantum Mechanics",
    "laser": "Waves/Optics",
    "photonics": "Waves/Optics",
    "cosmology": "Cosmology",
    "relativity": "Relativity",

    # Earth & Space
    "geology": "Rocks & Minerals",
    "geophysics": "Tectonics/Volcanism/Geology",
    "oceanography": "Hydrology/Oceanography",
    "atmospheric science": "Meteorology",
    "climate": "Meteorology",
    "meteorology": "Meteorology",
    "seismology": "Seismology",
    "paleontology": "Earth Sciences",
    "astronomy": "Astronomy",
    "planetary science": "Solar System/Planetary Science",
    "remote sensing": "Observational",
    "hydrology": "Hydrology/Oceanography",
    "mineralogy": "Rocks & Minerals",
    "geochemistry": "Earth Sciences",
}


def classify_concept(concept_name):
    """Map an OpenAlex concept to (category, subcategory) or None."""
    lower = concept_name.lower().strip()

    for keyword, category in CONCEPT_CATEGORY_MAP.items():
        if keyword in lower:
            subcategory = SUBCATEGORY_MAP.get(keyword, concept_name)
            return category, subcategory

    return None, None


def classify_topic(topic):
    """Map an OpenAlex topic to (category, subcategory, focus)."""
    field = topic.get("field", "")
    subfield = topic.get("subfield", "")
    display_name = topic.get("display_name", "")
    domain = topic.get("domain", "")

    # Try field-level mapping first
    category = FIELD_MAP.get(field)

    # Fall back to domain
    if not category:
        category = DOMAIN_MAP.get(domain)

    if not category:
        return None

    # Subcategory from subfield
    subcategory = subfield if subfield else field

    # Focus from display_name
    focus = display_name if display_name != subfield else ""

    return category, subcategory, focus


def generate_tags(author):
    """Generate three-layer tags for an author from OpenAlex data."""
    tags = []
    seen = set()  # avoid duplicate tags

    # From topics (newer, more structured)
    for topic in author.get("topics", []):
        result = classify_topic(topic)
        if result is None:
            continue
        category, subcategory, focus = result

        key = (category, subcategory, focus)
        if key not in seen:
            seen.add(key)
            tags.append({
                "category": category,
                "subcategory": subcategory,
                "focus": focus
            })

    # From x_concepts (legacy, broader)
    for concept in author.get("x_concepts", []):
        score = concept.get("score", 0)
        if score < 20:  # skip very low-relevance concepts
            continue

        concept_name = concept.get("display_name", "")
        category, subcategory = classify_concept(concept_name)

        if category:
            # Use concept as focus if we already have the subcategory
            focus = concept_name if concept_name != subcategory else ""
            key = (category, subcategory, focus)
            if key not in seen:
                seen.add(key)
                tags.append({
                    "category": category,
                    "subcategory": subcategory,
                    "focus": focus
                })

    # Limit to top 15 tags (sorted by specificity — prefer topics over concepts)
    return tags[:15]


def main():
    with open(INPUT_FILE) as f:
        faculty = json.load(f)

    print(f"Loaded {len(faculty)} faculty entries")

    tagged_count = 0
    total_tags = 0

    for author in faculty:
        tags = generate_tags(author)
        author["tags"] = tags
        if tags:
            tagged_count += 1
            total_tags += len(tags)

    print(f"Faculty with tags: {tagged_count}/{len(faculty)}")
    print(f"Total tags generated: {total_tags}")
    if tagged_count > 0:
        print(f"Average tags per tagged faculty: {total_tags / tagged_count:.1f}")

    # Show category distribution
    cat_counts = {}
    for author in faculty:
        for tag in author.get("tags", []):
            cat = tag.get("category", "Unknown")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print("\nTag distribution by category:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(faculty, f, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
