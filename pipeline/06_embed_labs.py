"""
Pre-compute sentence embeddings for all labs in labs.json.

Each lab gets TWO embeddings:
  1. "description" — lab name + PI + summary + tag names
  2. "concepts"   — related scientific terms from the concept-expansion map

At search time the browser takes max(sim_desc, sim_concept) per lab, so a query
like "lotka-volterra" can match via the concepts vector even if the description
embedding doesn't capture it.

Outputs:
  data/lab_embeddings.bin   — raw Float32: N×DIM (description) ++ N×DIM (concepts)
  data/embedding_meta.json  — { model, dim, count, vectors_per_lab }

Usage:
    pip install sentence-transformers
    python3 pipeline/06_embed_labs.py
"""
import json
import os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABS_FILE = os.path.join(ROOT, "data", "labs.json")
OUT_BIN = os.path.join(ROOT, "data", "lab_embeddings.bin")
OUT_META = os.path.join(ROOT, "data", "embedding_meta.json")

MODEL_NAME = "BAAI/bge-base-en-v1.5"
DIM = 768

# ---------------------------------------------------------------------------
# Concept expansion: maps each fine tag → related named phenomena, equations,
# techniques, vocabulary.  Bridges named scientific concepts (which get
# fragmented into meaningless subwords) to the tag taxonomy.
# ---------------------------------------------------------------------------
CONCEPT_MAP = {
    # ── Bio ──
    "Anatomy & Physiology": "organ systems, homeostasis, physiology, gross anatomy",
    "Cardiovascular System": "heart, blood pressure, cardiac cycle, ECG, hemodynamics, Starling law, Poiseuille flow",
    "Circadian Rhythms": "biological clock, melatonin, suprachiasmatic nucleus, photoperiod, zeitgeber, circadian oscillator",
    "Digestive System": "gastrointestinal tract, peristalsis, enzymes, absorption, gut microbiome",
    "Endocrine System": "hormones, insulin, thyroid, pituitary, adrenal, feedback loops, receptor signaling",
    "Epidemiology": "disease spread, SIR model, R-naught, pandemic, endemic, incidence, prevalence, contact tracing",
    "Immune System": "innate immunity, adaptive immunity, T cells, B cells, antibodies, MHC, cytokines, inflammation, vaccine, autoimmunity",
    "Musculoskeletal System": "bone, cartilage, muscle, tendons, biomechanics, Wolff's law, sarcomere, actin myosin",
    "Reproductive System": "gametogenesis, meiosis, fertilization, embryo, placenta, hormonal regulation",
    "Respiratory System": "lungs, gas exchange, alveoli, hemoglobin, Bohr effect, ventilation, spirometry",
    "Sensory Systems": "vision, audition, olfaction, somatosensation, retina, cochlea, mechanoreceptors, photoreceptors",
    "Biochemistry": "metabolism, enzymes, cofactors, ATP, Krebs cycle, glycolysis, amino acids, proteins",
    "Enzyme Kinetics": "Michaelis-Menten, Lineweaver-Burk, catalysis, substrate, Vmax, Km, allosteric regulation, enzyme inhibition, competitive inhibitor",
    "Lipid Metabolism": "fatty acid oxidation, beta-oxidation, lipogenesis, cholesterol, lipoproteins, membranes",
    "Metabolism": "catabolism, anabolism, Krebs cycle, glycolysis, oxidative phosphorylation, metabolomics, metabolic flux",
    "Oxidative Phosphorylation": "electron transport chain, ATP synthase, chemiosmosis, mitochondria, proton gradient, NADH, FADH2",
    "Pharmacology": "drug design, receptor binding, dose-response, pharmacokinetics, pharmacodynamics, IC50, EC50, therapeutic index",
    "Protein Degradation": "ubiquitin, proteasome, autophagy, lysosome, proteolysis",
    "Protein Structure": "X-ray crystallography, cryo-EM, NMR, alpha helix, beta sheet, protein folding, Ramachandran plot, chaperone",
    "Cell Cycle & Division": "mitosis, meiosis, cyclins, CDK, checkpoint, spindle, chromosome segregation, anaphase",
    "Apoptosis": "programmed cell death, caspases, Bcl-2, cytochrome c, necrosis",
    "Cell Adhesion": "cadherins, integrins, selectins, extracellular matrix, focal adhesion, tight junction",
    "Cell Cycle Regulation": "cyclins, CDK, p53, Rb, checkpoint kinase, DNA damage response",
    "Cell Signaling": "signal transduction, MAPK, PI3K, Wnt, Notch, receptor tyrosine kinase, second messengers, GPCR, cAMP",
    "Cell/Molecular Biology": "cell biology, molecular biology, organelles, cytoskeleton, nucleus, membrane",
    "DNA Repair Mechanisms": "base excision repair, nucleotide excision repair, mismatch repair, homologous recombination, NHEJ, double-strand break",
    "Immunotherapy": "CAR-T cells, checkpoint inhibitors, PD-1, PD-L1, CTLA-4, tumor immunology, cancer immunotherapy, adoptive cell transfer",
    "Membrane Transport": "ion channels, pumps, osmosis, active transport, passive transport, Nernst equation, Goldman equation, aquaporin",
    "Microscopy": "fluorescence microscopy, confocal, super-resolution, electron microscopy, SEM, TEM, STORM, PALM, light-sheet",
    "Stem Cells": "pluripotency, iPSC, embryonic stem cells, differentiation, self-renewal, organoids, regenerative medicine",
    "Transcription": "RNA polymerase, promoter, enhancer, transcription factor, mRNA, splicing, gene expression, central dogma",
    "Embryogenesis": "gastrulation, morphogenesis, organogenesis, blastula, axis patterning, Hox genes, developmental biology",
    "Animal Behavior": "ethology, predator-prey, foraging, migration, Lotka-Volterra, population dynamics, behavioral ecology, fitness, food web, trophic, symbiosis, mutualism, competition",
    "Biodiversity": "species richness, ecosystem, conservation, extinction, phylogeny, ecological niche, habitat, population ecology, Lotka-Volterra, predator-prey, food chain, trophic cascade, carrying capacity, logistic growth",
    "Evolution": "natural selection, phylogenetics, speciation, adaptation, molecular evolution, Hardy-Weinberg, genetic drift, fitness landscape, LUCA, tree of life",
    "Bioinformatics": "genomics, sequence alignment, BLAST, genome assembly, next-gen sequencing, RNA-seq, proteomics, systems biology",
    "Epigenetics": "DNA methylation, histone modification, chromatin remodeling, imprinting, X-inactivation, CpG islands",
    "Gene Editing": "CRISPR, Cas9, guide RNA, base editing, prime editing, gene therapy, zinc finger, TALEN",
    "Gene Regulation": "promoter, enhancer, silencer, transcription factor, operon, lac operon, epigenetic, chromatin",
    "Population Genetics": "allele frequency, Hardy-Weinberg, genetic drift, gene flow, bottleneck, founder effect, coalescent theory",
    "RNA Interference": "siRNA, miRNA, RNAi, Dicer, RISC, gene silencing, post-transcriptional regulation, antisense",
    "Bacterial Genetics": "conjugation, transduction, transformation, plasmid, antibiotic resistance, horizontal gene transfer, CRISPR immunity",
    "Fungal Biology": "mycology, yeast, hyphae, spores, fermentation, fungal pathogen, Saccharomyces, Aspergillus",
    "Parasitology": "malaria, Plasmodium, helminth, protozoa, host-parasite interaction, vector-borne disease",
    "Viral Replication": "virus lifecycle, capsid, reverse transcriptase, retrovirus, bacteriophage, viral entry, RNA virus, DNA virus, influenza, SARS",
    "Microbiome & Microbial Ecology": "gut microbiome, metagenomics, 16S rRNA, microbial diversity, symbiosis, dysbiosis, horizontal gene transfer, Lotka-Volterra competition, population dynamics, microbial community, chemostat",
    "Photosynthesis": "chloroplast, Calvin cycle, light reactions, photosystem I II, RuBisCO, carbon fixation, C3 C4 CAM",
    "Plant Physiology": "auxin, transpiration, stomata, xylem, phloem, root growth, photoperiodism, germination",

    # ── CS/AI ──
    "Cryptography": "RSA, AES, elliptic curve, zero-knowledge proof, homomorphic encryption, post-quantum, lattice-based, Diffie-Hellman, hash function, digital signature",
    "Formal Verification": "model checking, theorem proving, type theory, Coq, Isabelle, correctness proof, program analysis, static analysis",
    "Graph Algorithms": "shortest path, Dijkstra, BFS, DFS, network flow, max-flow min-cut, PageRank, graph neural networks, community detection",
    "Programming Languages": "compiler, type system, lambda calculus, functional programming, static analysis, interpreter, semantics, garbage collection",
    "CPU/GPU Architecture": "processor design, cache, pipelining, SIMD, FPGA, ASIC, instruction set, memory hierarchy, parallel hardware",
    "Database Systems": "SQL, NoSQL, query optimization, indexing, transactions, ACID, distributed database, data warehousing",
    "Human-Computer Interaction": "user interface, UX, accessibility, input devices, haptics, AR, VR, visualization, wearable computing",
    "Network Protocols": "TCP/IP, routing, congestion control, wireless, 5G, software-defined networking, SDN, latency, bandwidth, IoT",
    "Parallel Computing": "distributed systems, MapReduce, GPU computing, concurrency, multithreading, MPI, cloud computing, fault tolerance",
    "Software Engineering": "testing, debugging, version control, agile, DevOps, continuous integration, code quality, refactoring",
    "3D Reconstruction": "point cloud, mesh, NeRF, structure from motion, depth estimation, LiDAR, photogrammetry, SLAM",
    "Object Detection": "YOLO, R-CNN, bounding box, segmentation, image classification, feature extraction, anchor-based, transformer vision",
    "Attention Mechanisms": "transformer, self-attention, multi-head attention, BERT, GPT, positional encoding, cross-attention, vision transformer",
    "Diffusion Models": "denoising, score matching, DDPM, stable diffusion, image generation, noise scheduling, latent diffusion",
    "Causal Inference": "causation, correlation, experiment design, randomized controlled trial, instrumental variables, difference-in-differences, propensity score, counterfactual, do-calculus, Granger causality, DAG, confounding",
    "Gradient Descent": "backpropagation, SGD, Adam, learning rate, loss function, optimization landscape, convergence, batch normalization",
    "Reinforcement Learning": "Q-learning, policy gradient, reward, Markov decision process, MDP, exploration-exploitation, multi-agent, actor-critic, Bellman equation",
    "Transfer Learning": "fine-tuning, domain adaptation, few-shot learning, pre-training, foundation model, self-supervised learning",
    "Game Theory": "Nash equilibrium, zero-sum, cooperative game, mechanism design, auction theory, strategic interaction, minimax, Pareto optimal",
    "Numerical Methods": "finite element, finite difference, spectral methods, Monte Carlo, numerical integration, ODE solver, PDE solver, Runge-Kutta, Newton's method",
    "Optimization": "linear programming, convex optimization, gradient descent, combinatorial optimization, constraint satisfaction, integer programming, Lagrangian, simplex",
    "Language Understanding": "NLU, question answering, reading comprehension, sentiment analysis, text classification, semantic parsing, dialogue systems",
    "Speech Recognition": "ASR, acoustic model, language model, phoneme, spectrogram, end-to-end, CTC, attention-based",
    "Topic Modeling": "LDA, latent Dirichlet allocation, document clustering, text mining, word embeddings, semantic similarity",
    "Bayesian Inference": "Bayes theorem, posterior, prior, likelihood, MCMC, variational inference, conjugate prior, credible interval, Bayesian network",
    "Experimental Design": "randomization, blocking, factorial design, A/B testing, sample size, power analysis, control group, placebo, blinding",
    "Hypothesis Testing": "p-value, significance, t-test, chi-square, ANOVA, null hypothesis, confidence interval, effect size, multiple comparisons",
    "Probability & Statistics": "probability distributions, central limit theorem, law of large numbers, regression, correlation, random variable, expectation, variance",
    "Regression": "linear regression, logistic regression, least squares, regularization, LASSO, ridge, polynomial, GLM",
    "Stochastic Processes": "Markov chain, Brownian motion, Poisson process, random walk, martingale, Langevin equation, Fokker-Planck, Lotka-Volterra, birth-death process, master equation, predator-prey dynamics, population dynamics",
    "Mathematical Modeling": "differential equations, simulation, dynamical systems, compartmental models, agent-based models, Lotka-Volterra, predator-prey, SIR, population dynamics",

    # ── Chem ──
    "NMR Spectroscopy": "nuclear magnetic resonance, chemical shift, coupling constant, COSY, NOESY, relaxation, MRI, solid-state NMR",
    "Biomaterials & Bioorganic Chemistry": "hydrogel, scaffold, biocompatible, drug delivery, tissue engineering, peptide, bioconjugate, biopolymer",
    "Atmospheric Chemistry": "ozone, aerosol, NOx, SOx, VOC, smog, photolysis, radical chemistry, stratosphere, troposphere",
    "Coordination Compounds": "metal complex, ligand field theory, crystal field, chelation, organometallic, Werner complex, coordination number",
    "Transition Metal Catalysis": "palladium, platinum, cross-coupling, Suzuki, Heck, Grubbs metathesis, organometallic catalyst, homogeneous catalysis, heterogeneous catalysis",
    "Corrosion": "oxidation, rust, galvanic, passivation, cathodic protection, electrochemical corrosion",
    "Electrochemistry": "battery, fuel cell, electrolysis, cyclic voltammetry, Nernst equation, electrode, redox, lithium-ion, solid-state electrolyte, faradaic",
    "Nanomaterials": "nanoparticle, quantum dot, nanotube, graphene, nanocomposite, self-assembly, nanowire, surface area, nano-scale",
    "Polymer Chemistry": "polymerization, monomer, copolymer, molecular weight, glass transition, viscoelasticity, elastomer, thermoplastic, ring-opening",
    "Solid-State Chemistry": "crystal structure, X-ray diffraction, Bragg's law, unit cell, lattice, perovskite, spinel, defects, doping, phase transition",
    "Radiochemistry": "radioactive decay, isotope, half-life, nuclear transmutation, tracer, actinide, fission products, radiopharmaceutical",
    "Aromatic Substitution": "electrophilic, nucleophilic, benzene, Friedel-Crafts, halogenation, nitration, directing groups",
    "Carbohydrate Chemistry": "sugar, glycan, polysaccharide, glycoprotein, glycosylation, monosaccharide, cellulose, starch",
    "Colloid Chemistry": "emulsion, surfactant, micelle, colloidal suspension, Tyndall effect, zeta potential, DLVO theory",
    "Cross-Coupling Reactions": "Suzuki, Heck, Sonogashira, Stille, Negishi, Buchwald-Hartwig, palladium catalyst, organometallic",
    "Organic Chemistry": "synthesis, retrosynthesis, functional group, reaction mechanism, total synthesis, natural product, stereochemistry",
    "Stereochemistry": "chirality, enantiomer, diastereomer, optical activity, asymmetric synthesis, configuration, conformation, R/S nomenclature",
    "Chemical Kinetics": "reaction rate, rate law, Arrhenius equation, activation energy, transition state, rate constant, half-life, reaction order, collision theory, Michaelis-Menten",
    "Phase Diagrams": "phase boundary, triple point, critical point, eutectic, solidus, liquidus, Gibbs phase rule, lever rule",
    "Photochemistry": "excited state, fluorescence, phosphorescence, photocatalysis, singlet oxygen, Jablonski diagram, photovoltaic, solar energy",
    "Quantum Chemistry": "molecular orbital, DFT, Hartree-Fock, basis set, ab initio, HOMO-LUMO, electron correlation, Born-Oppenheimer",
    "Surface Chemistry": "adsorption, catalysis, Langmuir isotherm, BET, self-assembled monolayer, wetting, contact angle, thin film",
    "Thermochemistry": "enthalpy, entropy, Gibbs free energy, Hess's law, calorimetry, bond energy, heat capacity, thermodynamic equilibrium",

    # ── ESS ──
    "Astrophysics": "stellar evolution, supernova, neutron star, black hole, galaxy formation, Hertzsprung-Russell, main sequence, white dwarf, dark matter, dark energy, cosmic microwave background, Big Bang",
    "Erosion & Weathering": "sediment transport, chemical weathering, physical weathering, soil formation, fluvial, aeolian, glacial erosion, landscape evolution",
    "Mineralogy": "mineral, crystal, silicate, carbonate, dolomite, feldspar, quartz, perovskite, olivine, pyroxene, Mohs hardness, cleavage, X-ray diffraction",
    "Radiometric Dating": "radioactive decay, half-life, carbon-14, uranium-lead, potassium-argon, geochronology, isochron, age of Earth",
    "Seismology": "earthquake, seismic wave, P-wave, S-wave, Richter scale, moment magnitude, fault, plate tectonics, subduction, tomography, Rayleigh wave, Love wave",
    "Stratigraphy": "sedimentary layers, fossils, geological time, biostratigraphy, sequence stratigraphy, unconformity, correlation, basin analysis",
    "Groundwater Flow": "aquifer, permeability, Darcy's law, hydraulic conductivity, water table, porosity, contaminant transport, well hydraulics",
    "Water Quality": "dissolved oxygen, pH, nutrients, eutrophication, pollutant, turbidity, drinking water, wastewater, remediation",
    "Atmospheric Circulation": "Hadley cell, Ferrel cell, jet stream, trade winds, Coriolis effect, monsoon, pressure gradient, general circulation",
    "Climate Modeling": "global warming, greenhouse effect, carbon cycle, GCM, radiative forcing, feedback, IPCC, climate sensitivity, paleoclimate, ice core",
    "Remote Sensing": "satellite, LiDAR, radar, multispectral, hyperspectral, GIS, land use, vegetation index, NDVI, aerial survey",
    "Survey Astronomy": "sky survey, photometry, spectroscopy, catalog, redshift survey, transient, variable star, all-sky, Sloan, Gaia, Rubin/LSST",
    "Marine Ecology": "coral reef, fisheries, plankton, ocean acidification, marine food web, benthic, pelagic, estuary, upwelling, primary production, Lotka-Volterra, predator-prey, population dynamics, trophic cascade",
    "Ocean Circulation": "thermohaline, Gulf Stream, AMOC, deep water formation, Ekman transport, upwelling, eddy, geostrophic flow, tidal mixing",

    # ── Phys ──
    "Nonlinear Dynamics": "chaos theory, strange attractor, Lorenz system, bifurcation, Lotka-Volterra, logistic map, turbulence, soliton, Navier-Stokes, Reynolds number, fluid dynamics, dynamical systems, fixed point, limit cycle, Lyapunov exponent, Duffing oscillator, predator-prey",
    "Semiconductor Physics": "band gap, p-n junction, transistor, MOSFET, doping, silicon, gallium arsenide, photovoltaic, LED, Hall effect, Fermi level",
    "Maxwell's Equations": "electromagnetic, Gauss's law, Faraday's law, Ampere's law, electromagnetic wave, antenna, waveguide, impedance, radiation, polarization",
    "Superconductivity": "BCS theory, Cooper pair, Meissner effect, type I type II, critical temperature, flux quantization, Josephson junction, high-Tc, cuprate",
    "Nuclear Fusion": "plasma, tokamak, stellarator, deuterium-tritium, Lawson criterion, magnetic confinement, inertial confinement, ITER, fusion energy, neutron source",
    "Radiation Detection": "Geiger counter, scintillator, semiconductor detector, dosimetry, gamma ray, neutron detection, spectroscopy, calorimeter",
    "Neutrino Physics": "neutrino oscillation, mass hierarchy, Dirac, Majorana, sterile neutrino, solar neutrino, double beta decay, DUNE, IceCube, cross-section",
    "Standard Model": "quark, lepton, boson, Higgs, QCD, electroweak, gauge symmetry, Feynman diagram, CKM matrix, CP violation, beyond Standard Model",
    "Many-Body Physics": "Hubbard model, mean-field, Ising model, spin chain, quantum magnetism, strongly correlated, Fermi liquid, Bose gas, condensate",
    "Quantum Chaos": "random matrix theory, level spacing, quantum billiards, semiclassical, ergodic, Berry phase, Gutzwiller trace formula",
    "Quantum Chromodynamics": "QCD, quark, gluon, asymptotic freedom, confinement, hadron, lattice QCD, color charge, strong force, jet, parton",
    "Quantum Field Theory": "Feynman diagram, renormalization, gauge theory, path integral, vacuum, anomaly, effective field theory, S-matrix, LSZ",
    "Quantum Gravity": "string theory, loop quantum gravity, black hole thermodynamics, Planck scale, holographic principle, AdS/CFT, entanglement entropy, Bekenstein-Hawking",
    "Quantum Mechanics": "Schrodinger equation, wave function, superposition, entanglement, measurement, uncertainty principle, tunneling, Hilbert space, Dirac notation, Born rule",
    "Quantum Transport": "conductance quantization, ballistic transport, Landauer formula, mesoscopic, quantum dot, quantum Hall, Aharonov-Bohm, spintronics, topological insulator",
    "Schrödinger Equation": "wave function, eigenvalue, Hamiltonian, potential well, harmonic oscillator, hydrogen atom, perturbation theory, variational method, WKB",
    "Gravitational Waves": "LIGO, binary merger, black hole, neutron star, strain, interferometer, chirp mass, inspiral, general relativity, gravitational wave detection",
    "Interference & Diffraction": "double slit, Fresnel, Fraunhofer, Bragg diffraction, Airy pattern, Young's experiment, coherence, holography, thin film",
    "Nonlinear Optics": "harmonic generation, Kerr effect, four-wave mixing, optical soliton, parametric amplification, phase matching, chi-2, chi-3",
    "Photonic Crystals": "photonic band gap, waveguide, optical fiber, metamaterial, plasmonics, photonic integrated circuit, slow light",
    "Wave-Particle Duality": "de Broglie, Compton scattering, photoelectric effect, matter wave, electron diffraction, wave packet, pilot wave, Copenhagen interpretation",
}


def build_description(lab):
    """Build the 'what does this lab do' text — names, summary, tag labels."""
    pi = lab.get("n", "")
    name = lab.get("l", "") or pi
    dept = ", ".join(lab.get("d", []))
    summary = lab.get("s", "") or ""
    tags = lab.get("t", [])
    fine_labels = list(dict.fromkeys(t[2] for t in tags if len(t) >= 3))
    areas = ", ".join(fine_labels)
    return f"{name}. PI: {pi}. Department: {dept}. {summary} Research areas: {areas}."


def build_concepts(lab):
    """Build a concepts-only text from the tag → concept-expansion map."""
    tags = lab.get("t", [])
    concepts = []
    seen = set()
    for t in tags:
        if len(t) >= 3:
            key = t[2]
            if key not in seen and key in CONCEPT_MAP:
                seen.add(key)
                concepts.append(CONCEPT_MAP[key])
    if not concepts:
        return build_description(lab)  # fallback
    return " ".join(concepts)


def main():
    from sentence_transformers import SentenceTransformer

    with open(LABS_FILE) as f:
        labs = json.load(f)

    n = len(labs)
    print(f"Loaded {n} labs")

    desc_texts = [build_description(lab) for lab in labs]
    concept_texts = [build_concepts(lab) for lab in labs]

    print(f"\nSample description (lab 0, {len(desc_texts[0])} chars):")
    print(desc_texts[0][:200] + "...")
    print(f"\nSample concepts (lab 0, {len(concept_texts[0])} chars):")
    print(concept_texts[0][:200] + "...")

    print(f"\nLoading model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    print("Encoding descriptions...")
    desc_emb = model.encode(desc_texts, show_progress_bar=True, normalize_embeddings=True)
    print("Encoding concepts...")
    conc_emb = model.encode(concept_texts, show_progress_bar=True, normalize_embeddings=True)

    assert desc_emb.shape == (n, DIM)
    assert conc_emb.shape == (n, DIM)

    # Layout: [desc_0..desc_N, conc_0..conc_N] (two contiguous blocks)
    combined = np.vstack([desc_emb, conc_emb]).astype(np.float32)
    with open(OUT_BIN, "wb") as f:
        f.write(combined.tobytes())
    print(f"\nWrote {OUT_BIN} ({os.path.getsize(OUT_BIN):,} bytes)")

    meta = {"model": MODEL_NAME, "dim": DIM, "count": n, "vectors_per_lab": 2}
    with open(OUT_META, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Wrote {OUT_META}")


if __name__ == "__main__":
    main()
