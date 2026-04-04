"""Pipeline configuration."""

import os

# OpenAlex (free, no key needed)
OPENALEX_EMAIL = "aryan.mit.sciencebowl@gmail.com"
MIT_INSTITUTION_ID = "I63966007"

# How far back to look for active researchers
ACTIVE_YEARS = 3

# Minimum works count to filter toward PIs (low threshold — recall > precision)
MIN_WORKS_COUNT = 15

# Rate limiting
RATE_LIMIT_DELAY = 0.5  # seconds between API calls

# Output paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "data")
INTERMEDIATE_DIR = os.path.join(BASE_DIR, "intermediate")

# Ensure intermediate dir exists
os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
