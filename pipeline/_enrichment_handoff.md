# Lab Enrichment — Self Handoff

**Read this file first if you are resuming the lab-enrichment task in a new session.**
Also read `~/.claude/projects/-Users-aryan-Documents-Aryan-CS/memory/project_lab_enrichment.md` and `…/feedback_lab_enrichment_tags.md` (auto-loaded via MEMORY.md).

---

## What you are doing

Enriching every lab in `mit-lab-explorer/data/labs.json` (515 total) with:
- `n`  — corrected PI name (only when current is wrong, e.g. "B. Russell" → "Brooke Russell")
- `l`  — real lab/group name (not "Lastname Lab" — use the group's self-name like "Improbable AI Lab", "Martin Lab", "CSAIL Programming Languages and Verification Group")
- `s`  — **3-sentence summary** focused on **domains covered + methods used**. Audience is **college students writing Science Bowl questions**, so be factually dense, name actual systems, methods, instruments, model organisms. Plain factual tone. NOT marketing copy.
- `k.w` — lab website URL
- `k.p` — publications page URL (only if confidently found; OK to leave blank)
- `k.g` — corrected Google Scholar profile (only if changed; "cleared" status means delete the existing one)
- `t`  — full retag (replaces existing tags). Aggressive retag — drop bogus tags from old auto-tagger.
- `scholar_status` — "ok" / "cleared" / "wrong" / "not_found"
- `notes` — free text for anything weird

## User preferences (HARD)

1. **Audience** for summaries: Science Bowl question writers. Emphasize domains and methods. ~3 sentences.
2. **Lab names**: group's self-name, NOT "<lastname> Lab".
3. **Tag fit can be loose** — see `feedback_lab_enrichment_tags.md`. Tags only need to *touch* what the lab does, not encompass it. Don't drop labs from non-STEM departments — find loose connections (J-PAL economics → CS/AI Probability & Statistics is fine).
4. **Tag taxonomy is rigid**: only `Bio / CS/AI / Chem / ESS / Phys`. Use the controlled vocabulary dumped below. Schema is `[category, coarse, fine, focus]` where `focus` is usually equal to `fine`.
5. **Wrong scholar links**: option (b) — *clear* `k.g` (set scholar_status: "cleared"). Don't try to find the correct one.
6. **Order**: alphabetical by PI name (`labs[].n`).
7. **No external API / no Anthropic API agent**. Run everything inside this Claude Code session via WebSearch/WebFetch tools. Pure web research, no programmatic LLM calls.
8. **Pace**: chunks of 12–14 labs. Don't pause for per-batch review (validation batch already approved). Only flag anomalies (unfindable, scholar mismatch, ambiguous PI, possible dup, junk entry).

## Tag taxonomy (controlled vocabulary)

Use ONLY these. Schema: `[cat, coarse, fine, focus]`. Focus is usually `fine`. Multi-word fines must match exactly.

```
Bio
  Anatomy & Physiology: Anatomy & Physiology, Cardiovascular System, Circadian Rhythms, Digestive System, Endocrine System, Epidemiology, Immune System, Musculoskeletal System, Reproductive System, Respiratory System, Sensory Systems
  Biochemistry: Biochemistry, Enzyme Kinetics, Lipid Metabolism, Metabolism, Oxidative Phosphorylation, Pharmacology, Protein Degradation, Protein Structure
  Cell Cycle & Division: Cell Cycle & Division
  Cell/Molecular Biology: Apoptosis, Cell Adhesion, Cell Cycle Regulation, Cell Signaling, Cell/Molecular Biology, DNA Repair Mechanisms, Immunotherapy, Membrane Transport, Microscopy, Stem Cells, Transcription
  Developmental Biology: Embryogenesis
  Ecology: Animal Behavior, Biodiversity, Evolution
  Genetics: Bioinformatics, Epigenetics, Gene Editing, Gene Regulation, Population Genetics, RNA Interference
  Microbiology: Bacterial Genetics, Fungal Biology, Parasitology, Viral Replication
  Microbiome & Microbial Ecology: Microbiome & Microbial Ecology
  Plant Biology: Photosynthesis, Plant Physiology
CS/AI
  Algorithms & TCS: Cryptography, Formal Verification, Graph Algorithms, Programming Languages
  Computer Systems: CPU/GPU Architecture, Database Systems, Human-Computer Interaction, Network Protocols, Parallel Computing, Software Engineering
  Computer Vision: 3D Reconstruction, Object Detection
  Deep Learning: Attention Mechanisms, Diffusion Models
  Machine Learning: Causal Inference, Gradient Descent, Reinforcement Learning, Transfer Learning
  Mathematical Modeling: Game Theory, Numerical Methods, Optimization
  NLP & Language Models: Language Understanding, Speech Recognition, Topic Modeling
  Probability & Statistics: Bayesian Inference, Experimental Design, Hypothesis Testing, Probability & Statistics, Regression, Stochastic Processes
Chem
  Analytical Chemistry: NMR Spectroscopy
  Biomaterials & Bioorganic Chemistry: Biomaterials & Bioorganic Chemistry
  Environmental Chemistry: Atmospheric Chemistry
  Inorganic Chemistry: Coordination Compounds, Transition Metal Catalysis
  Materials Chemistry: Corrosion, Electrochemistry, Nanomaterials, Polymer Chemistry, Solid-State Chemistry
  Nuclear Chemistry: Radiochemistry
  Organic Chemistry: Aromatic Substitution, Carbohydrate Chemistry, Colloid Chemistry, Cross-Coupling Reactions, Organic Chemistry, Stereochemistry
  Physical Chemistry: Chemical Kinetics, Phase Diagrams, Photochemistry, Quantum Chemistry, Surface Chemistry, Thermochemistry
ESS
  Cosmology: Astrophysics
  Geology: Erosion & Weathering, Mineralogy, Radiometric Dating, Seismology, Stratigraphy
  Hydrology: Groundwater Flow, Water Quality
  Meteorology: Atmospheric Circulation, Climate Modeling, Remote Sensing
  Observational Astronomy: Survey Astronomy
  Oceanography: Marine Ecology, Ocean Circulation
Phys
  Classical Mechanics: Nonlinear Dynamics
  Condensed Matter: Semiconductor Physics
  Electricity & Magnetism: Maxwell's Equations, Superconductivity
  Nuclear Physics: Nuclear Fusion, Radiation Detection
  Particle Physics: Neutrino Physics, Standard Model
  Quantum Mechanics: Many-Body Physics, Quantum Chaos, Quantum Chromodynamics, Quantum Field Theory, Quantum Gravity, Quantum Mechanics, Quantum Transport, Schrödinger Equation
  Relativity: Gravitational Waves
  Waves & Optics: Interference & Diffraction, Nonlinear Optics, Photonic Crystals, Wave-Particle Duality
```

You can re-derive this anytime via:
```bash
python3 -c "
import json; from collections import defaultdict
labs = json.load(open('data/labs.json'))
tree = defaultdict(lambda: defaultdict(set))
for l in labs:
    for t in l.get('t', []):
        if len(t)>=3: tree[t[0]][t[1]].add(t[2])
for c in sorted(tree):
    print(f'== {c} ==')
    for co in sorted(tree[c]):
        print(f'  {co}: {sorted(tree[c][co])}')
"
```

## Files & helpers (already created in this task)

- `data/labs.json` — the canonical dataset (515 labs). Compact JSON, `separators=(",", ":")`. Sort key for processing: `labs[].n`.
- `data/enrichment.json` — keyed by lab id; what you write per lab. **Never** write directly with the Write tool — that overwrites the whole file. Use:
- `pipeline/_batch_add.py` — `cat new_entries.json | python3 pipeline/_batch_add.py` to merge a JSON blob into enrichment.json (overwriting same-id entries).
- `pipeline/merge_enrichment.py` — applies `data/enrichment.json` → `data/labs.json`. Supports `--dry-run`. Handles fields: `n`, `l`, `s`, `t`, `k.w/p/g/m/o`, plus `scholar_status: "cleared"` removes `k.g`.
- `data/duplicates.txt` — log of dupes / junk entries. Format: free-text with comments.
- `pipeline/_enrichment_handoff.md` — **this file**. Update it with new gotchas as you discover them.

## How to resume — exact steps

1. Read this file. Read MEMORY.md and the two memory files it points to.
2. See what's already done:
   ```bash
   python3 -c "
   import json
   labs = json.load(open('data/labs.json'))
   done = set(json.load(open('data/enrichment.json')).keys())
   print(f'done: {len(done)}, remaining: {len(labs)-len(done)}')
   "
   ```
3. Get the next batch (12–14 labs alphabetically by `n`):
   ```bash
   python3 -c "
   import json
   labs = json.load(open('data/labs.json'))
   done = set(json.load(open('data/enrichment.json')).keys())
   nxt = sorted([l for l in labs if l['id'] not in done], key=lambda l: l['n'])[:14]
   for l in nxt: print(l['id'], '|', l['n'], '|', l.get('d'))
   "
   ```
4. Fire ~12 parallel `WebSearch` calls — one per lab. Use queries like `"<PI Name> MIT <dept> lab <topic-hint>"`. The dept hint helps disambiguate.
5. From the search snippets, write the enrichment record. Don't use WebFetch unless necessary — search snippets usually have enough. Trust the existing `k.g` scholar URL unless something looks odd.
6. Append to enrichment.json via the heredoc → `_batch_add.py` pattern (see git history of this conversation, or any prior `cat <<'JSON' | python3 pipeline/_batch_add.py` block).
7. Every 3–5 batches, run `python3 pipeline/merge_enrichment.py` to push into labs.json.
8. Update progress in this file's "Last checkpoint" section below.

## Known anomalies (so far) — flag these to user

- **`alex-slocum-meche` ≡ `alexander-h-slocum-meche`**: same person (Alexander H. Slocum, MechE / PERG). Logged in `data/duplicates.txt`. Same enrichment applied to both.
- **`b-k-berger-math`**: junk. Beverly K. Berger is at Oakland Univ / former NSF Gravitational Physics PD. No MIT affiliation found. **Did not enrich.** Logged in duplicates.txt.
- **`b-russell-physics`** = "B. Russell" → actually **Brooke Russell**, joined MIT Physics 2025, neutrino physics / DUNE. Enrichment includes `n: "Brooke Russell"` to fix the PI display name. **This is the only case so far where you needed to set `n`** — watch for other initials-only entries (search by single-letter first name in `labs[].n`).
- **Pure mathematicians and economists** often don't have a "lab" — leave `l` blank in those cases. Tags via loose connection (game theory, numerical methods, statistics).
- **MechE / AeroAstro / DMSE labs** generally don't fit Bio/CS/AI/Chem/ESS/Phys cleanly. Lean on `Phys > Classical Mechanics > Nonlinear Dynamics` and `CS/AI > Mathematical Modeling > Optimization` as catch-alls. Materials → `Chem > Materials Chemistry`.

## Watch-outs for the rest

- **Initials-only PI names** (e.g. `A. B. Lastname` or `B. Russell`). Search Wikipedia / MIT physics directory; some may be wrong-person, junk, or just need full-name expansion. Set `n` if you fix.
- **Cross-listed labs** (Chemistry + BioE + Koch). Pick the most-relevant department for the lab description. The `d` field stays as-is.
- **Scholar IDs**: prior pipeline already resolved most via real-browser scraping, so they're usually right. But if a search for the PI's name returns a different `user=` ID than what's in `labs.json`, **clear** the existing one (`scholar_status: "cleared"`, no `k.g` in `k`).
- **Fence the user's site link priority**: `cardUrl()` in `index.html` prioritizes publications page > lab website > scholar > scholar search. So `k.p` and `k.w` are the most user-visible fields — get them right.
- **Don't fetch lab websites with WebFetch** unless you need to disambiguate or grab a non-obvious pubs URL. Search snippets are almost always enough and ~5x cheaper in context.
- **Scholar verification cost**: skip per-lab verification unless something looks wrong. Spot-check ~1 in 10 by searching `"scholar.google.com/citations?user=XYZ" lastname`.

## Batch-add JSON format (copy this skeleton)

```bash
cat <<'JSON' | python3 pipeline/_batch_add.py
{
  "<lab-id>": {
    "l": "Lab Name",
    "s": "Sentence one. Sentence two. Sentence three about methods.",
    "k": { "w": "https://...", "p": "https://.../publications" },
    "t": [
      ["Bio", "Coarse", "Fine", "Focus"],
      ["...", "...", "...", "..."]
    ],
    "scholar_status": "ok"
  }
}
JSON
```

If you need to fix the PI name, add `"n": "Real Name"`. If scholar is wrong, omit `k.g` and set `"scholar_status": "cleared"`.

## Last checkpoint

- **Date**: 2026-04-07
- **Done**: 44 / 515 labs
- **Resume from**: next alphabetical after "Barbara Liskov" — likely starts with "Beatriz", "Ben", "Benedetto", etc. Run the listing snippet in step 3 above to confirm.
- **Last merge**: `merge_enrichment.py` was run after batch 4; labs.json contains all 44 enrichments.
- **Anomalies surfaced**: 1 dup (Slocum), 1 junk (B.K. Berger), 1 name fix (B. Russell → Brooke Russell). All in duplicates.txt.
- **Pending decisions for user**: whether to delete `b-k-berger-math` and one of the two Slocum entries — neither has been touched in labs.json.

When you finish all 515, delete this file.
