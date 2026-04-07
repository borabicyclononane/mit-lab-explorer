"""Helper for the lab-enrichment task: read a JSON blob from stdin and merge
into data/enrichment.json (overwriting any existing entries with same ids).

Usage:  cat new_entries.json | python3 pipeline/_batch_add.py
"""
import json, os, sys

ENR = os.path.join(os.path.dirname(__file__), "..", "data", "enrichment.json")
with open(ENR) as f:
    cur = json.load(f)
new = json.load(sys.stdin)
cur.update(new)
with open(ENR, "w") as f:
    json.dump(cur, f, indent=2, ensure_ascii=False)
print(f"Now {len(cur)} entries in enrichment.json (added/updated {len(new)})")
