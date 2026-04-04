"""
Run the entire data pipeline.

Each step saves checkpoints to intermediate/, so individual steps
can be re-run independently if needed.
"""

import subprocess
import sys
import time

STEPS = [
    ("01_collect_faculty.py", "Collecting MIT faculty from OpenAlex"),
    ("02_validate_departments.py", "Validating against department pages"),
    ("03_auto_tag.py", "Auto-tagging from OpenAlex concepts"),
    ("04_resolve_links.py", "Resolving external links"),
    ("05_merge_and_output.py", "Merging overrides and outputting labs.json"),
]


def run_step(script, description):
    """Run a pipeline step and return success/failure."""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"Script: {script}")
    print(f"{'='*60}\n")

    result = subprocess.run(
        [sys.executable, script],
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"\n*** STEP FAILED: {script} (exit code {result.returncode}) ***")
        return False

    return True


def main():
    start_time = time.time()
    print("MIT Lab Explorer — Data Pipeline")
    print("=" * 60)

    # Allow running from a specific step
    start_from = 1
    if len(sys.argv) > 1:
        try:
            start_from = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [start_step_number]")
            sys.exit(1)

    failed = False
    for i, (script, description) in enumerate(STEPS, 1):
        if i < start_from:
            print(f"Skipping step {i}: {description}")
            continue

        success = run_step(script, description)
        if not success:
            print(f"\nPipeline stopped at step {i}. Fix the error and run:")
            print(f"  python run_all.py {i}")
            failed = True
            break

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    if failed:
        print(f"Pipeline FAILED after {elapsed:.0f}s")
        sys.exit(1)
    else:
        print(f"Pipeline completed in {elapsed:.0f}s")
        print("Output: ../data/labs.json")


if __name__ == "__main__":
    main()
