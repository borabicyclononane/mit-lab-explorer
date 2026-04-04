# MIT Lab Explorer

A static website that helps MIT Science Bowl question writers find MIT research labs relevant to their Energy questions. Browse labs by Science Bowl category or search by keyword.

**Live site:** https://borabicyclononane.github.io/mit-lab-explorer/

## How to Use

### Browse Mode
Click a category tab (Biology, Chemistry, Physics, Earth & Space, CS/AI/Stats) to see labs with relevant research. Every lab card shows ALL its tags across ALL categories — spot cross-disciplinary angles easily.

### Search Mode
Type a query (e.g., "CRISPR", "gradient descent", "plate tectonics") to find labs with matching research. Results are ranked by relevance.

**Keyboard shortcuts:** `/` focuses search, `Escape` clears it.

## How to Add or Edit Labs

Edit `data/manual_overrides.json`:

```json
{
  "add": [
    {
      "id": "jane-doe-biology",
      "pi_name": "Jane Doe",
      "lab_name": "Doe Lab",
      "departments": ["Biology"],
      "research_summary": "Studies X using Y.",
      "tags": [
        {"category": "Biology", "subcategory": "Genetics/Evolution", "focus": "CRISPR screens"}
      ],
      "links": {"lab_website": "https://example.com"},
      "manually_added": true
    }
  ],
  "override": {
    "existing-lab-id": {
      "research_summary": "Better description here.",
      "extra_tags": [
        {"category": "CS/AI/Stats", "subcategory": "Deep Learning", "focus": "Transformers"}
      ]
    }
  }
}
```

Then re-run the pipeline (step 5 only is fine): `cd pipeline && python 05_merge_and_output.py`

## How to Refresh Data

```bash
pip install -r pipeline/requirements.txt
cd pipeline
python run_all.py
```

This fetches fresh data from OpenAlex and MIT department pages. Takes ~10-30 minutes depending on rate limits. To resume from a specific step: `python run_all.py 3` (starts at step 3).

Commit and push the updated `data/labs.json` to deploy.

## The Tag System

Every lab has structured tags with three layers:

```
[Category: Subcategory — Research Focus]
```

- **Category:** Biology, Chemistry, Physics, Earth & Space, or CS/AI/Stats
- **Subcategory:** Topic area at the level of "what Science Bowl question could I write?"
- **Research Focus:** What the lab specifically does

Example:
```
[CS/AI/Stats: Causal Inference — Causal Graph Discovery]
[Biology: Cell/Molecular Biology — Chromatin Structure & Organization]
```

## Contributing

1. **Add a missing lab:** Edit `data/manual_overrides.json` and submit a PR
2. **Fix tags:** Use the override mechanism to add `extra_tags` or set `replace_tags: true`
3. **Report issues:** Open a GitHub issue

## Tech Stack

- Single-file static site (vanilla HTML/CSS/JS)
- Data pipeline in Python (requests + BeautifulSoup)
- Data from [OpenAlex](https://openalex.org) (free, no API key) and MIT department pages
- Hosted on GitHub Pages (free)

Total cost: **$0**
