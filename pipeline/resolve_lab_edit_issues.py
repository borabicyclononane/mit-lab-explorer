"""
Resolve open `lab-edit` GitHub issues by applying their proposed changes
to data/labs.json.

Each issue is created by the in-page edit form on the website. The form
embeds a fenced ```json lab-edit``` block in the issue body that contains:

    {
      "id": "<lab id>" | null,
      "oa": "<openalex id>" | null,
      "pi_name": "<name>",
      "changes": {
        "n": "...",          # PI name
        "l": "...",          # lab name
        "d": [...],          # departments
        "s": "...",          # research summary
        "k.g": "...",        # google scholar
        "k.w": "...",        # lab website
        "k.p": "...",        # publications page
        "k.m": "...",        # mit profile
        "t":  [[cat, coarse, fine, focus], ...]  # tags
      }
    }

The script matches issues to labs by `id` first, then by exact `pi_name`.
On success it edits labs.json in place and closes the issue with a comment.

Usage:
    python3 resolve_lab_edit_issues.py            # apply + close
    python3 resolve_lab_edit_issues.py --dry-run  # show what would change
    python3 resolve_lab_edit_issues.py --no-close # apply but leave issues open

Requires the `gh` CLI, authenticated against the repo.
"""

import argparse
import json
import os
import re
import subprocess
import sys

LABS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "labs.json")
LABEL = "lab-edit"

# Fields that live under the `k` (links) sub-object
K_FIELDS = {"k.g", "k.w", "k.p", "k.m"}
# Top-level fields
TOP_FIELDS = {"n", "l", "d", "s", "t"}


def run(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def fetch_open_issues():
    """Return list of open issues with the lab-edit label."""
    out = run([
        "gh", "issue", "list",
        "--label", LABEL,
        "--state", "open",
        "--limit", "200",
        "--json", "number,title,body,author",
    ])
    return json.loads(out)


def extract_payload(body):
    """Pull the ```json lab-edit``` fenced block out of an issue body."""
    if not body:
        return None
    m = re.search(r"```json lab-edit\s*\n(.*?)\n```", body, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f"  ! could not parse JSON payload: {e}")
        return None


def find_lab(labs, payload):
    """Match a payload to a lab in labs.json. Returns the lab dict or None."""
    lab_id = payload.get("id")
    if lab_id:
        for lab in labs:
            if lab.get("id") == lab_id:
                return lab
    name = payload.get("pi_name")
    if name:
        matches = [lab for lab in labs if lab.get("n") == name]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            print(f"  ! ambiguous: {len(matches)} labs match name '{name}'")
    return None


def apply_changes(lab, changes):
    """Mutate `lab` in place. Returns list of (field, old, new) tuples."""
    applied = []
    for field, new_val in changes.items():
        if field in TOP_FIELDS:
            old = lab.get(field)
            if old != new_val:
                lab[field] = new_val
                applied.append((field, old, new_val))
        elif field in K_FIELDS:
            sub = field.split(".", 1)[1]
            if "k" not in lab:
                lab["k"] = {}
            old = lab["k"].get(sub)
            if old != new_val:
                if new_val:
                    lab["k"][sub] = new_val
                else:
                    lab["k"].pop(sub, None)
                applied.append((field, old, new_val))
        else:
            print(f"  ! unknown field: {field}")
    return applied


def format_change(field, old, new):
    o = json.dumps(old) if not isinstance(old, str) else old
    n = json.dumps(new) if not isinstance(new, str) else new
    if len(str(o)) > 60:
        o = str(o)[:60] + "..."
    if len(str(n)) > 60:
        n = str(n)[:60] + "..."
    return f"    {field}: {o!r} -> {n!r}"


def close_issue(number, applied):
    summary = "\n".join(f"- `{f}`" for f, _, _ in applied)
    comment = f"Applied to `data/labs.json`:\n\n{summary}\n\n_Resolved by `pipeline/resolve_lab_edit_issues.py`._"
    run(["gh", "issue", "comment", str(number), "--body", comment])
    run(["gh", "issue", "close", str(number)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="show changes without writing or closing")
    parser.add_argument("--no-close", action="store_true", help="apply changes but leave issues open")
    args = parser.parse_args()

    with open(LABS_FILE) as f:
        labs = json.load(f)

    issues = fetch_open_issues()
    print(f"Found {len(issues)} open `{LABEL}` issue(s)")
    if not issues:
        return

    total_applied = 0
    skipped = 0

    for issue in issues:
        num = issue["number"]
        title = issue["title"]
        author = issue.get("author", {}).get("login", "?")
        print(f"\n#{num} ({author}): {title}")

        payload = extract_payload(issue.get("body", ""))
        if not payload:
            print("  ! no JSON payload found, skipping")
            skipped += 1
            continue

        lab = find_lab(labs, payload)
        if lab is None:
            print(f"  ! no matching lab for id={payload.get('id')!r} / name={payload.get('pi_name')!r}")
            skipped += 1
            continue

        changes = payload.get("changes", {})
        if not changes:
            print("  ! payload has no changes")
            skipped += 1
            continue

        # Apply (or simulate)
        if args.dry_run:
            # Dry-run: compute diff against a deep copy
            import copy
            applied = apply_changes(copy.deepcopy(lab), changes)
        else:
            applied = apply_changes(lab, changes)

        if not applied:
            print("  - no-op (already matches current state)")
            if not args.dry_run and not args.no_close:
                close_issue(num, [("(no-op)", None, None)])
            continue

        for f, o, n in applied:
            print(format_change(f, o, n))
        total_applied += 1

        if not args.dry_run and not args.no_close:
            close_issue(num, applied)

    if not args.dry_run:
        with open(LABS_FILE, "w") as f:
            json.dump(labs, f, separators=(",", ":"))
        print(f"\nWrote {LABS_FILE}")

    print(f"\nApplied: {total_applied} | Skipped: {skipped}")
    if args.dry_run:
        print("(dry-run — no files written, no issues closed)")


if __name__ == "__main__":
    main()
