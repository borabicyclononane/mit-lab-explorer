"""
Merge data/enrichment.json into data/labs.json.

enrichment.json schema (keyed by lab id):
{
  "<lab_id>": {
    "l":  "<lab name>",                # -> labs[].l
    "s":  "<3-sentence summary>",      # -> labs[].s
    "k":  {                            # -> merged into labs[].k
      "w": "<lab website>",
      "p": "<publications page>",
      "g": "<corrected scholar url>"   # only if changed
    },
    "t":  [[cat, coarse, fine, focus], ...],  # full retag, replaces labs[].t
    "scholar_status": "ok|wrong|cleared|not_found",
    "notes": "..."
  }
}

Usage:
    python3 pipeline/merge_enrichment.py            # apply
    python3 pipeline/merge_enrichment.py --dry-run  # show what would change
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABS_FILE = os.path.join(ROOT, "data", "labs.json")
ENRICH_FILE = os.path.join(ROOT, "data", "enrichment.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(LABS_FILE) as f:
        labs = json.load(f)
    if not os.path.exists(ENRICH_FILE):
        sys.exit(f"No enrichment file at {ENRICH_FILE}")
    with open(ENRICH_FILE) as f:
        enrich = json.load(f)

    by_id = {l["id"]: l for l in labs}
    applied = 0
    skipped = 0

    for lab_id, e in enrich.items():
        lab = by_id.get(lab_id)
        if lab is None:
            print(f"  ! no lab with id {lab_id}")
            skipped += 1
            continue
        changed = []
        if "n" in e and e["n"] and lab.get("n") != e["n"]:
            lab["n"] = e["n"]; changed.append("n")
        if "l" in e and e["l"] and lab.get("l") != e["l"]:
            lab["l"] = e["l"]; changed.append("l")
        if "s" in e and e["s"] and lab.get("s") != e["s"]:
            lab["s"] = e["s"]; changed.append("s")
        if "t" in e and e["t"]:
            if lab.get("t") != e["t"]:
                lab["t"] = e["t"]; changed.append("t")
        if "k" in e and isinstance(e["k"], dict):
            if "k" not in lab:
                lab["k"] = {}
            for sub, val in e["k"].items():
                if val and lab["k"].get(sub) != val:
                    lab["k"][sub] = val
                    changed.append(f"k.{sub}")
        # scholar_status: cleared -> remove k.g
        if e.get("scholar_status") == "cleared":
            if lab.get("k", {}).get("g"):
                lab["k"].pop("g", None)
                changed.append("k.g(cleared)")
        if changed:
            applied += 1
            print(f"  {lab_id}: {', '.join(changed)}")

    if not args.dry_run:
        with open(LABS_FILE, "w") as f:
            json.dump(labs, f, separators=(",", ":"))
    print(f"\nApplied: {applied} | Skipped: {skipped}{'  (dry-run)' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
