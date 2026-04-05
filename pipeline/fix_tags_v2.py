"""
Convert all tags to 4-part format: [category, coarse, fine, focus]

Categories are abbreviated: Bio, Chem, Phys, ESS, CS/AI
Coarse = textbook section level
Fine = specific scientific concept (chapter level)
Focus = what the lab actually does
"""

import json
import re

INPUT_FILE = "../data/labs.json"
OUTPUT_FILE = "../data/labs.json"

# ── Category abbreviation map ──
CAT_ABBREV = {
    "Biology": "Bio",
    "Chemistry": "Chem",
    "Physics": "Phys",
    "Earth & Space": "ESS",
    "CS/AI/Stats": "CS/AI",
}

# ── Mapping: (old_category, old_subcategory) -> (new_coarse, default_fine) ──
# Fine will be further refined by focus keywords when possible.

COARSE_FINE_MAP = {
    # ── Biology ──
    ("Biology", "Aging & Longevity"): ("Genetics", "Epigenetics"),
    ("Biology", "Animal Behavior & Ethology"): ("Ecology", "Animal Behavior"),
    ("Biology", "Animal Genetics & Breeding"): ("Genetics", "Population Genetics"),
    ("Biology", "Apoptosis & Cell Death Pathways"): ("Cell/Molecular Biology", "Apoptosis"),
    ("Biology", "Autoimmune Disease"): ("Anatomy & Physiology", "Immune System"),
    ("Biology", "Bioimaging & Microscopy"): ("Cell/Molecular Biology", "Microscopy"),
    ("Biology", "Bioinformatics & Computational Biology"): ("Genetics", "Bioinformatics"),
    ("Biology", "Bioinorganic Chemistry"): ("Biochemistry", "Metalloenzymes"),
    ("Biology", "CRISPR & Genetic Engineering"): ("Genetics", "Gene Editing"),
    ("Biology", "Calcium Signaling & Binding Proteins"): ("Cell/Molecular Biology", "Cell Signaling"),
    ("Biology", "Cardiovascular System"): ("Anatomy & Physiology", "Cardiovascular System"),
    ("Biology", "Cell Biology"): ("Cell/Molecular Biology", "Cell Structure"),
    ("Biology", "Cell Mechanics & Adhesion"): ("Cell/Molecular Biology", "Cell Adhesion"),
    ("Biology", "Cell Respiration & Mitochondria"): ("Biochemistry", "Oxidative Phosphorylation"),
    ("Biology", "Chromatin Structure & Epigenetics"): ("Genetics", "Epigenetics"),
    ("Biology", "Circadian Rhythms & Biological Clocks"): ("Anatomy & Physiology", "Circadian Rhythms"),
    ("Biology", "Cognition & Language"): ("Anatomy & Physiology", "Nervous System"),
    ("Biology", "DNA Replication & Repair"): ("Cell/Molecular Biology", "DNA Repair Mechanisms"),
    ("Biology", "Digestive System & Metabolism"): ("Anatomy & Physiology", "Digestive System"),
    ("Biology", "Ecology & Biodiversity"): ("Ecology", "Biodiversity"),
    ("Biology", "Endocrine System & Hormones"): ("Anatomy & Physiology", "Endocrine System"),
    ("Biology", "Enzyme Kinetics & Protein Biochemistry"): ("Biochemistry", "Enzyme Kinetics"),
    ("Biology", "Epidemiology & Public Health"): ("Anatomy & Physiology", "Epidemiology"),
    ("Biology", "Evolution & Paleontology"): ("Ecology", "Evolution"),
    ("Biology", "Excretory System"): ("Anatomy & Physiology", "Excretory System"),
    ("Biology", "Exercise Physiology"): ("Anatomy & Physiology", "Musculoskeletal System"),
    ("Biology", "Gene Regulation & Developmental Biology"): ("Genetics", "Gene Regulation"),
    ("Biology", "Genetics & Genomics"): ("Genetics", "Genomics"),
    ("Biology", "Glycobiology & Post-Translational Modification"): ("Biochemistry", "Post-Translational Modification"),
    ("Biology", "Hallmarks of Cancer & Oncogenes/Tumor Suppressors"): ("Cell/Molecular Biology", "Cell Cycle Regulation"),
    ("Biology", "Hematology & Blood"): ("Anatomy & Physiology", "Blood & Circulatory System"),
    ("Biology", "Immune System & Immunology"): ("Anatomy & Physiology", "Immune System"),
    ("Biology", "Integumentary System"): ("Anatomy & Physiology", "Integumentary System"),
    ("Biology", "Membrane Structure & Lipid Biology"): ("Biochemistry", "Lipid Metabolism"),
    ("Biology", "Membrane Transport & Cell Signaling"): ("Cell/Molecular Biology", "Membrane Transport"),
    ("Biology", "Microbiology & Infectious Disease"): ("Microbiology", "Bacterial Genetics"),
    ("Biology", "Molecular Biology & Biochemistry"): ("Biochemistry", "Protein Structure"),
    ("Biology", "Musculoskeletal System"): ("Anatomy & Physiology", "Musculoskeletal System"),
    ("Biology", "Mycology & Fungal Biology"): ("Microbiology", "Fungal Biology"),
    ("Biology", "Nervous System & Neuroscience"): ("Anatomy & Physiology", "Nervous System"),
    ("Biology", "Nutrition & Metabolism"): ("Biochemistry", "Metabolism"),
    ("Biology", "Parasitology & Vector-Borne Disease"): ("Microbiology", "Parasitology"),
    ("Biology", "Pharmacology & Drug Delivery"): ("Biochemistry", "Pharmacology"),
    ("Biology", "Photosynthesis"): ("Plant Biology", "Photosynthesis"),
    ("Biology", "Plant Biology"): ("Plant Biology", "Plant Physiology"),
    ("Biology", "Protein Degradation & Ubiquitin Pathway"): ("Biochemistry", "Protein Degradation"),
    ("Biology", "Psychology & Behavioral Science"): ("Anatomy & Physiology", "Nervous System"),
    ("Biology", "RNA Interference & Gene Regulation"): ("Genetics", "RNA Interference"),
    ("Biology", "Rehabilitation & Motor Control"): ("Anatomy & Physiology", "Nervous System"),
    ("Biology", "Reproductive System & Development"): ("Developmental Biology", "Embryogenesis"),
    ("Biology", "Respiratory System"): ("Anatomy & Physiology", "Respiratory System"),
    ("Biology", "Sensory Systems & Perception"): ("Anatomy & Physiology", "Sensory Systems"),
    ("Biology", "Space Biology & Astrobiology"): ("Anatomy & Physiology", "Space Physiology"),
    ("Biology", "Stem Cells & Tissue Engineering"): ("Cell/Molecular Biology", "Stem Cells"),
    ("Biology", "Transcription & RNA Processing"): ("Cell/Molecular Biology", "Transcription"),
    ("Biology", "Vascular Biology & Signaling"): ("Anatomy & Physiology", "Cardiovascular System"),
    ("Biology", "Virology & Viral Pathogenesis"): ("Microbiology", "Viral Replication"),

    # ── Chemistry ──
    ("Chemistry", "Activation Energy & Catalysis"): ("Physical Chemistry", "Chemical Kinetics"),
    ("Chemistry", "Chemical Kinetics & Dynamics"): ("Physical Chemistry", "Chemical Kinetics"),
    ("Chemistry", "Computational Chemistry"): ("Physical Chemistry", "Quantum Chemistry"),
    ("Chemistry", "Coordination Chemistry & Macrocycles"): ("Inorganic Chemistry", "Coordination Compounds"),
    ("Chemistry", "Electrochemistry & Cell Potential"): ("Materials Chemistry", "Electrochemistry"),
    ("Chemistry", "Enzyme Kinetics & Catalysis"): ("Physical Chemistry", "Chemical Kinetics"),
    ("Chemistry", "General Chemistry"): ("Physical Chemistry", "Chemical Kinetics"),
    ("Chemistry", "Green Chemistry & Sustainability"): ("Environmental Chemistry", "Atmospheric Chemistry"),
    ("Chemistry", "Materials Chemistry & Corrosion"): ("Materials Chemistry", "Corrosion"),
    ("Chemistry", "Nanochemistry & Nanomaterials"): ("Materials Chemistry", "Nanomaterials"),
    ("Chemistry", "Nuclear Chemistry"): ("Nuclear Chemistry", "Radiochemistry"),
    ("Chemistry", "Organic Synthesis & Reaction Mechanisms"): ("Organic Chemistry", "Reaction Mechanisms"),
    ("Chemistry", "Phase Diagrams & Crystal Structure"): ("Physical Chemistry", "Phase Diagrams"),
    ("Chemistry", "Photochemistry & Energy Transfer"): ("Physical Chemistry", "Photochemistry"),
    ("Chemistry", "Polymer Chemistry"): ("Materials Chemistry", "Polymer Chemistry"),
    ("Chemistry", "Solid-State Chemistry & Materials"): ("Materials Chemistry", "Solid-State Chemistry"),
    ("Chemistry", "Spectroscopy (NMR, IR, Mass Spec, UV-Vis)"): ("Analytical Chemistry", "NMR Spectroscopy"),
    ("Chemistry", "Surface Chemistry & Colloids"): ("Physical Chemistry", "Surface Chemistry"),
    ("Chemistry", "Thermochemistry & Energy"): ("Physical Chemistry", "Thermochemistry"),
    ("Chemistry", "Transition Metal Chemistry & Coordination Compounds"): ("Inorganic Chemistry", "Transition Metal Catalysis"),

    # ── Physics ──
    ("Physics", "Condensed Matter Physics"): ("Condensed Matter", "Semiconductor Physics"),
    ("Physics", "Dark Matter & Dark Energy"): ("Astrophysics", "Cosmological Models"),
    ("Physics", "Galaxies & Galactic Structure"): ("Astrophysics", "Galactic Dynamics"),
    ("Physics", "General Relativity & Gravitational Waves"): ("Relativity", "Gravitational Waves"),
    ("Physics", "Lasers & Photonics"): ("Waves & Optics", "Nonlinear Optics"),
    ("Physics", "Maxwell's Equations & Electromagnetism"): ("Electricity & Magnetism", "Maxwell's Equations"),
    ("Physics", "Neutrino Physics"): ("Particle Physics", "Neutrino Physics"),
    ("Physics", "Nonlinear Dynamics & Chaos"): ("Classical Mechanics", "Nonlinear Dynamics"),
    ("Physics", "Nuclear Fusion & Fission"): ("Nuclear Physics", "Nuclear Fusion"),
    ("Physics", "Nuclear Magnetic Resonance"): ("Quantum Mechanics", "Nuclear Magnetic Resonance"),
    ("Physics", "Optics & Interferometry"): ("Waves & Optics", "Interference & Diffraction"),
    ("Physics", "Optics & Wave Phenomena"): ("Waves & Optics", "Interference & Diffraction"),
    ("Physics", "Particle Physics & Detectors"): ("Particle Physics", "Standard Model"),
    ("Physics", "Quantum Field Theory"): ("Quantum Mechanics", "Quantum Field Theory"),
    ("Physics", "Quantum Many-Body Physics"): ("Quantum Mechanics", "Many-Body Physics"),
    ("Physics", "Quantum Mechanics"): ("Quantum Mechanics", "Schrödinger Equation"),
    ("Physics", "Radiation & Detection"): ("Nuclear Physics", "Radiation Detection"),
    ("Physics", "Semiconductor Physics"): ("Condensed Matter", "Semiconductor Physics"),
    ("Physics", "Stellar Evolution & Life Cycles"): ("Astrophysics", "Stellar Evolution"),
    ("Physics", "String Theory & Quantum Gravity"): ("Quantum Mechanics", "Quantum Gravity"),
    ("Physics", "Wave-Particle Duality & Quantum Optics"): ("Waves & Optics", "Wave-Particle Duality"),
    ("Physics", "Astrophysics & Cosmology"): ("Astrophysics", "Cosmological Models"),
    ("Physics", "Computational Physics"): ("Classical Mechanics", "Computational Modeling"),
    ("Physics", "Electromagnetic Induction & Magnetism"): ("Electricity & Magnetism", "Electromagnetic Induction"),
    ("Physics", "Experimental Physics & Instrumentation"): ("Particle Physics", "Particle Detectors"),
    ("Physics", "Fluid Dynamics"): ("Classical Mechanics", "Fluid Mechanics"),
    ("Physics", "Micro/Nano Devices"): ("Condensed Matter", "Nanoscale Devices"),
    ("Physics", "Statistical Mechanics & Thermodynamics"): ("Thermodynamics & Stat Mech", "Statistical Mechanics"),
    ("Physics", "Superconductivity"): ("Condensed Matter", "Superconductivity"),
    ("Physics", "Topological Phases of Matter"): ("Condensed Matter", "Topological Phases"),
    ("Physics", "Thin Films & Surface Physics"): ("Condensed Matter", "Thin Films"),
    ("Physics", "Physics"): ("Quantum Mechanics", "Schrödinger Equation"),

    # ── Earth & Space ──
    ("Earth & Space", "Atmospheric Structure & Composition"): ("Meteorology", "Atmospheric Circulation"),
    ("Earth & Space", "Climate Change & Carbon Cycle"): ("Meteorology", "Climate Modeling"),
    ("Earth & Space", "Earth & Planetary Science"): ("Geology", "Earth Systems"),
    ("Earth & Space", "Earthquakes & Seismology"): ("Geology", "Seismology"),
    ("Earth & Space", "Ecology & Ecosystems"): ("Oceanography", "Marine Ecology"),
    ("Earth & Space", "Energy & Environmental Sustainability"): ("Meteorology", "Climate Modeling"),
    ("Earth & Space", "Environmental Pollution & Toxicology"): ("Hydrology", "Water Quality"),
    ("Earth & Space", "Geochemistry & Mineralogy"): ("Geology", "Mineralogy"),
    ("Earth & Space", "Geology & Earth Processes"): ("Geology", "Stratigraphy"),
    ("Earth & Space", "Geophysics & Earth's Interior"): ("Geology", "Seismology"),
    ("Earth & Space", "Glaciology & Cryosphere"): ("Meteorology", "Climate Modeling"),
    ("Earth & Space", "Hydrology & Water Resources"): ("Hydrology", "Groundwater Flow"),
    ("Earth & Space", "Ocean Circulation & Marine Science"): ("Oceanography", "Ocean Circulation"),
    ("Earth & Space", "Paleontology & Earth History"): ("Geology", "Stratigraphy"),
    ("Earth & Space", "Plate Tectonics & Volcanism"): ("Geology", "Plate Tectonics"),
    ("Earth & Space", "Radiometric Dating & Isotope Geochemistry"): ("Geology", "Radiometric Dating"),
    ("Earth & Space", "Remote Sensing & GIS"): ("Meteorology", "Remote Sensing"),
    ("Earth & Space", "Soil Science & Geomorphology"): ("Geology", "Erosion & Weathering"),
    ("Earth & Space", "Water Treatment & Environmental Engineering"): ("Hydrology", "Water Quality"),
    ("Earth & Space", "Weather Systems & Meteorology"): ("Meteorology", "Severe Weather"),
    ("Earth & Space", "Air Quality & Atmospheric Chemistry"): ("Meteorology", "Atmospheric Chemistry"),

    # ── CS/AI/Stats ──
    ("CS/AI/Stats", "Abstract Algebra & Group Theory"): ("Mathematical Modeling", "Algebraic Structures"),
    ("CS/AI/Stats", "Algorithms & Data Structures"): ("Algorithms & TCS", "Graph Algorithms"),
    ("CS/AI/Stats", "Bayesian Inference & Bayes' Theorem"): ("Probability & Statistics", "Bayesian Inference"),
    ("CS/AI/Stats", "CS Education"): ("Algorithms & TCS", "Programming"),
    ("CS/AI/Stats", "Causal Inference"): ("Machine Learning", "Causal Inference"),
    ("CS/AI/Stats", "Computational Physics & Simulation"): ("Mathematical Modeling", "Numerical Methods"),
    ("CS/AI/Stats", "Computational Social Science"): ("Mathematical Modeling", "Dynamical Systems"),
    ("CS/AI/Stats", "Computer Architecture & Hardware"): ("Computer Systems", "CPU/GPU Architecture"),
    ("CS/AI/Stats", "Computer Graphics & Visualization"): ("Computer Vision", "3D Reconstruction"),
    ("CS/AI/Stats", "Computer Vision"): ("Computer Vision", "Object Detection"),
    ("CS/AI/Stats", "Cryptography & Cybersecurity"): ("Algorithms & TCS", "Cryptography"),
    ("CS/AI/Stats", "Databases & Data Management"): ("Computer Systems", "Database Systems"),
    ("CS/AI/Stats", "Decision Theory & Behavioral Economics"): ("Mathematical Modeling", "Game Theory"),
    ("CS/AI/Stats", "Diffusion Models & Generative AI"): ("Deep Learning", "Diffusion Models"),
    ("CS/AI/Stats", "Dimensionality Reduction & Embeddings"): ("Machine Learning", "Representation Learning"),
    ("CS/AI/Stats", "Distributed & Parallel Computing"): ("Computer Systems", "Parallel Computing"),
    ("CS/AI/Stats", "Econometrics & Statistical Economics"): ("Probability & Statistics", "Regression"),
    ("CS/AI/Stats", "Experimental Design"): ("Probability & Statistics", "Experimental Design"),
    ("CS/AI/Stats", "Formal Methods & Programming Languages"): ("Algorithms & TCS", "Formal Verification"),
    ("CS/AI/Stats", "Fourier Analysis & Signal Processing"): ("Mathematical Modeling", "Fourier Analysis"),
    ("CS/AI/Stats", "Functional Analysis"): ("Mathematical Modeling", "Functional Analysis"),
    ("CS/AI/Stats", "Game Theory & Mechanism Design"): ("Mathematical Modeling", "Game Theory"),
    ("CS/AI/Stats", "Human-Computer Interaction"): ("Computer Systems", "Human-Computer Interaction"),
    ("CS/AI/Stats", "Machine Learning"): ("Machine Learning", "Transfer Learning"),
    ("CS/AI/Stats", "Mathematical Physics"): ("Mathematical Modeling", "Dynamical Systems"),
    ("CS/AI/Stats", "Mathematics"): ("Mathematical Modeling", "Numerical Methods"),
    ("CS/AI/Stats", "Natural Language Processing"): ("NLP & Language Models", "Language Model Training"),
    ("CS/AI/Stats", "Networks & Communication"): ("Computer Systems", "Network Protocols"),
    ("CS/AI/Stats", "Number Theory"): ("Mathematical Modeling", "Number Theory"),
    ("CS/AI/Stats", "Numerical Methods & PDEs"): ("Mathematical Modeling", "Numerical Methods"),
    ("CS/AI/Stats", "Operations Research"): ("Mathematical Modeling", "Optimization"),
    ("CS/AI/Stats", "Optimization (Gradient Descent, Convex)"): ("Machine Learning", "Gradient Descent"),
    ("CS/AI/Stats", "Quantum Computing"): ("Computer Systems", "Quantum Computing Hardware"),
    ("CS/AI/Stats", "Random Matrix Theory"): ("Probability & Statistics", "Random Variables"),
    ("CS/AI/Stats", "Reinforcement Learning"): ("Machine Learning", "Reinforcement Learning"),
    ("CS/AI/Stats", "Robotics & Autonomous Systems"): ("Robotics", "Motion Planning"),
    ("CS/AI/Stats", "Software Engineering"): ("Computer Systems", "Software Engineering"),
    ("CS/AI/Stats", "Statistical Methods & Inference"): ("Probability & Statistics", "Hypothesis Testing"),
    ("CS/AI/Stats", "Stochastic Processes"): ("Probability & Statistics", "Stochastic Processes"),
    ("CS/AI/Stats", "Topology & Manifolds"): ("Mathematical Modeling", "Topology"),
    ("CS/AI/Stats", "Transformers & Attention Mechanism"): ("Deep Learning", "Attention Mechanisms"),
    ("CS/AI/Stats", "Algebraic Geometry"): ("Mathematical Modeling", "Algebraic Structures"),
    ("CS/AI/Stats", "Differential Geometry"): ("Mathematical Modeling", "Differential Geometry"),
    ("CS/AI/Stats", "Dynamical Systems"): ("Mathematical Modeling", "Dynamical Systems"),
    ("CS/AI/Stats", "Graph Theory & Combinatorics"): ("Algorithms & TCS", "Graph Algorithms"),
    ("CS/AI/Stats", "Epidemiological Modeling"): ("Mathematical Modeling", "Dynamical Systems"),
}

# ── Focus-based fine subcategory refinement ──
# When the default fine isn't specific enough, use focus keywords to pick better.
# Format: list of (pattern, fine_subcategory) checked in order.

FINE_REFINE = {
    # Bio refinements
    ("Bio", "Biochemistry"): [
        (r"enzyme|kinetic|catalyt|substrate", "Enzyme Kinetics"),
        (r"protein.fold|misfolding|aggregat|prion|alpha.fold|AlphaFold|structure.predict", "Protein Folding"),
        (r"oxidative.phosphoryl|electron.transport|mitochondri|ATP.synth|respir", "Oxidative Phosphorylation"),
        (r"lipid|lipidom|cholesterol|fatty.acid|phospholipid", "Lipid Metabolism"),
        (r"glycos|glycoprotein|carbohydrate|sugar", "Post-Translational Modification"),
        (r"ubiquitin|proteasom|degradat", "Protein Degradation"),
        (r"metalloenzym|iron.sulfur|metal.*protein|bioinorganic", "Metalloenzymes"),
        (r"pharmaco|drug|toxicol|medicine", "Pharmacology"),
        (r"metabolism|metabol|nutrit|vitamin|diet", "Metabolism"),
        (r"amino.acid|peptide|protein.struct|protein.dynam", "Protein Structure"),
        (r"photosynthes|chloro|light.harvest", "Photosynthesis"),
    ],
    ("Bio", "Cell/Molecular Biology"): [
        (r"cancer|tumor|oncog|leukemia|lymphoma|carcinogen|metasta|hallmark", "Cell Cycle Regulation"),
        (r"CAR-T|immunotherapy|checkpoint.inhib", "Immunotherapy"),
        (r"stem.cell|pluripotent|iPSC|regenerat", "Stem Cells"),
        (r"DNA.repair|BRCA|homologous.recombin|mismatch.repair|mutat", "DNA Repair Mechanisms"),
        (r"chromatin|histone|nucleosome|3D.genome", "Chromatin Structure"),
        (r"membrane.transport|ion.channel|pump|transporter", "Membrane Transport"),
        (r"signal|receptor|pathway|MAPK|Hedgehog|Wnt|Notch", "Cell Signaling"),
        (r"apoptosis|autophagy|ferroptosis|programmed.cell.death|necroptosis", "Apoptosis"),
        (r"cell.adhesion|extracellular.matrix|integrin|cadherin", "Cell Adhesion"),
        (r"cytoskelet|actin|microtubul|motor.protein|kinesin|dynein|mitosis", "Cytoskeleton"),
        (r"transcri|RNA.polymer|promoter|splicing|mRNA", "Transcription"),
        (r"ribosom|translat|codon|tRNA", "Translation"),
        (r"microscop|imaging|fluorescen|biosens|confocal|cryo.EM", "Microscopy"),
        (r"RNA.interfere|siRNA|miRNA|RNAi|gene.silenc", "RNA Interference"),
        (r"cell.cycle|mitosis|checkpoint|cyclin|CDK", "Cell Cycle Regulation"),
    ],
    ("Bio", "Genetics"): [
        (r"CRISPR|gene.edit|Cas9|guide.RNA|base.edit", "Gene Editing"),
        (r"epigenet|methylat|acetylat|histone.modif|imprint", "Epigenetics"),
        (r"population.genet|Hardy.Weinberg|allele.freq|genetic.drift", "Population Genetics"),
        (r"gene.regulat|transcription.factor|enhancer|promoter|regulatory", "Gene Regulation"),
        (r"RNA.interfere|siRNA|miRNA|RNAi|gene.silenc|noncoding", "RNA Interference"),
        (r"bioinformat|computational|sequence.align|BLAST|pipeline|omics", "Bioinformatics"),
        (r"genom|sequenc|whole.genome|exome|GWAS|genetic.assoc|phylogen", "Genomics"),
        (r"aging|longevity|senescen|telomer|sirtuin", "Epigenetics"),
    ],
    ("Bio", "Anatomy & Physiology"): [
        (r"neurosci|neural|neuron|brain|cortex|hippocam|synap|neurodegenerat|Alzheimer|Parkinson|optogenet|circuit|cognit|language|reading|percept|visual|retina", "Nervous System"),
        (r"immune|T.cell|B.cell|antibod|antigen|cytokine|inflamm|innate|adaptive|lymphocyte|macrophage|complement|autoimmun|vaccine|allerg|lupus", "Immune System"),
        (r"cardiovasc|heart|cardiac|coronary|vascular|atheroscler|artery|blood.pressure|hypertens|endothelin|nitric.oxide", "Cardiovascular System"),
        (r"endocrin|hormone|insulin|diabetes|thyroid|pituitary|adrenal|obesity|adipose|pancrea|appetite", "Endocrine System"),
        (r"respirat|lung|pulmonar|alveol|bronch|asthma|cystic.fibrosis|ventilat", "Respiratory System"),
        (r"digest|liver|hepat|intestin|stomach|gut|gastro|colon", "Digestive System"),
        (r"kidney|renal|nephron|urinar|excret|dialysis", "Excretory System"),
        (r"skin|dermat|epiderm|wound|burn", "Integumentary System"),
        (r"musculoskeletal|bone|osteo|cartilage|muscle|joint|skeletal|fracture|dental|tooth", "Musculoskeletal System"),
        (r"reproduct|pregnan|embryo|fertil|sperm|ovary|uterus|placenta|endometri", "Reproductive System"),
        (r"sensory|olfact|taste|auditor|cochlea|tactile|somatosens|propriocept|vestibular|retina|vision|visual", "Sensory Systems"),
        (r"circadian|sleep|melatonin|biological.clock", "Circadian Rhythms"),
        (r"blood|erythrocyt|hematol|anemia|erythropoiet|coagul|platelet|hemoglobin", "Blood & Circulatory System"),
        (r"spaceflight|microgravity|astronaut", "Space Physiology"),
        (r"stroke|rehabilit|gait|balance|motor.control|spinal.cord", "Nervous System"),
        (r"sport|exercise|training|athlet", "Musculoskeletal System"),
        (r"epidemiol|public.health|global.health|breast.?feed|maternal", "Epidemiology"),
        (r"behavior|psychology|emotion|anxiety|depress|personality|cognit", "Nervous System"),
    ],
    ("Bio", "Microbiology"): [
        (r"virus|viral|HIV|hepatitis|SARS|COVID|influenza|rabies|phage|retrovir", "Viral Replication"),
        (r"parasit|malaria|mosquito|plasmodium|toxoplasma|vector", "Parasitology"),
        (r"fung|yeast|mycol|Candida|Aspergillus", "Fungal Biology"),
        (r"bacteri|antibiotic|antimicrob|E.?coli|Staphylo|Strepto|Clostridium|tubercul|biofilm|quorum", "Bacterial Genetics"),
        (r"microbiom|microbiota|gut.flora|commensal", "Microbiome"),
    ],
    ("Bio", "Ecology"): [
        (r"evolut|natural.select|phylogen|speciat|adaptation|Darwin", "Evolution"),
        (r"population.dynam|predator.prey|lotka|carrying.capac", "Population Dynamics"),
        (r"biodivers|species.rich|conservat|endanger|extinct", "Biodiversity"),
        (r"biogeochem|carbon.cycle|nitrogen.cycle|nutrient.cycl", "Biogeochemical Cycles"),
        (r"animal.behav|mating|courtship|migration|communication", "Animal Behavior"),
        (r"paleomag|fossil|paleontol", "Evolution"),
    ],
    ("Bio", "Developmental Biology"): [
        (r"embryo|morphogen|gastrulat|somite|Drosophila|C.?elegans|zebrafish|organogen", "Embryogenesis"),
        (r"reproduct|fertil|gamete|pregnan", "Reproductive Development"),
    ],
    ("Bio", "Plant Biology"): [
        (r"photosynthes|light.react|dark.react|chloroplast|RuBisCO|Calvin", "Photosynthesis"),
        (r"plant.physiol|root|stem|leaf|xylem|phloem|stomata|transpirat", "Plant Physiology"),
        (r"crop|agricultur|yield|drought|irrigat", "Crop Science"),
    ],

    # Chem refinements
    ("Chem", "Organic Chemistry"): [
        (r"cross.coupl|Suzuki|Heck|Sonogashira|palladium|coupling", "Cross-Coupling Reactions"),
        (r"stereochem|chiral|enantio|asymmetric|diastereo", "Stereochemistry"),
        (r"aromatic|electrophilic|nucleophilic.substitut|benzene|heterocy", "Aromatic Substitution"),
        (r"carbonyl|aldol|Grignard|Wittig|aldehyde|ketone", "Carbonyl Chemistry"),
        (r"retrosynthes|total.synth|synthetic.route|target.molecul", "Retrosynthesis"),
        (r"cyclopropan|ring.open|ring.clos|metathesis|carbene|NHC", "Ring Chemistry"),
        (r"radical|free.radical|homolysis", "Radical Reactions"),
        (r"surfactant|colloid|micelle|emuls|detergent", "Colloid Chemistry"),
        (r"carbohydrate|sugar|glyco|saccharide", "Carbohydrate Chemistry"),
    ],
    ("Chem", "Inorganic Chemistry"): [
        (r"MOF|metal.organic.framework|porous|zeolite", "Metal-Organic Frameworks"),
        (r"coordinat|ligand.field|crystal.field|Werner", "Coordination Compounds"),
        (r"catalys|C.H.activ|cross.coupl|hydrogenat|oxidat", "Transition Metal Catalysis"),
        (r"porphyrin|phthalocyanine|macrocycl|heme", "Macrocyclic Chemistry"),
        (r"lanthanide|rare.earth|actinide|f.block", "Lanthanide Chemistry"),
        (r"magnetism|magnetic.*complex|spin.crossover", "Magnetochemistry"),
    ],
    ("Chem", "Physical Chemistry"): [
        (r"kinetic|rate.law|Arrhenius|activat.*energy|reaction.rate|catalys", "Chemical Kinetics"),
        (r"phase.diagram|phase.transit|triple.point|critical.point|crystal", "Phase Diagrams"),
        (r"quantum.chem|DFT|density.function|ab.initio|HF|Hartree|molecular.orbital|computation", "Quantum Chemistry"),
        (r"photochem|excit.*state|fluorescen|phosphorescen|photon|photovoltaic|solar|luminesc", "Photochemistry"),
        (r"surface|adsorpt|desorpt|BET|Langmuir|catalytic.surface|heterogeneous", "Surface Chemistry"),
        (r"thermo|enthalpy|entropy|Gibbs|Hess|calorimetr|heat|combust", "Thermochemistry"),
        (r"rheolog|viscosit|non.Newton|fluid.*dynam|viscoelast", "Chemical Kinetics"),
        (r"equilibr|Le.Chatelier|equilibr.*const|solubil|Ksp", "Thermodynamic Equilibria"),
    ],
    ("Chem", "Analytical Chemistry"): [
        (r"NMR|nuclear.magnetic.reson|chemical.shift|coupling.const", "NMR Spectroscopy"),
        (r"mass.spectrom|MS/MS|MALDI|ESI|m/z", "Mass Spectrometry"),
        (r"X.ray|crystallograph|diffract|Bragg|unit.cell", "X-ray Crystallography"),
        (r"chromatograph|HPLC|GC|column|separation", "Chromatography"),
        (r"IR|infrared|Raman|vibrat.*spectro", "IR/Raman Spectroscopy"),
        (r"UV.Vis|absorption|Beer.*Lambert|colorimetr", "UV-Vis Spectroscopy"),
        (r"sensor|detector|electroanal|potentiometr", "Chemical Sensors"),
        (r"laser|spectroscop", "Laser Spectroscopy"),
    ],
    ("Chem", "Materials Chemistry"): [
        (r"polymer|copolymer|polymeriz|plastic|rubber|chain.growth|step.growth", "Polymer Chemistry"),
        (r"electroch|battery|fuel.cell|electrolyte|electrode|capacitor|supercapacitor|lithium|solid.state.electrolyte", "Electrochemistry"),
        (r"nanomaterial|nanoparticl|nanotub|nanowire|quantum.dot|nanocrystal|graphene|carbon.nanotub", "Nanomaterials"),
        (r"corrosion|oxidat.*metal|rust|passivat|protect.*coat|alloy", "Corrosion"),
        (r"solid.state|ceramic|oxide|perovskite|ferroelect|piezoelect|dielectric", "Solid-State Chemistry"),
        (r"semiconductor|band.gap|photoconductiv|LED|photonic", "Semiconductor Materials"),
        (r"coating|thin.film|deposit|CVD|PVD|epitax", "Thin Film Chemistry"),
        (r"biomaterial|biocompat|scaffold|implant|silk|collagen|hydrogel", "Biomaterials"),
    ],
    ("Chem", "Environmental Chemistry"): [
        (r"atmospher|ozone|smog|aerosol|particulate|NOx|SOx|greenhouse|CO2", "Atmospheric Chemistry"),
        (r"biofuel|renewable|green.chem|sustainab|solar.*water|H2.*generat", "Green Chemistry"),
        (r"water|purif|desal|contaminat|remedi|wastewater", "Water Chemistry"),
    ],
    ("Chem", "Nuclear Chemistry"): [
        (r"radiochem|isotope.*product|technetium|medical.isotop|PET.*tracer", "Radiochemistry"),
        (r"nuclear.*mater|fuel.*rod|reactor.*mater|radiation.*damage", "Nuclear Materials"),
        (r"fusion.*mater|plasma.*facing|tritium", "Fusion Materials"),
    ],

    # Physics refinements
    ("Phys", "Quantum Mechanics"): [
        (r"entangle|Bell.*inequal|EPR|non.?local|quantum.*inform|quantum.*teleport", "Quantum Entanglement"),
        (r"tunnel|barrier|alpha.decay|STM|scanning.tunnel", "Quantum Tunneling"),
        (r"quantum.*comput|qubit|quantum.*gate|quantum.*error|quantum.*circuit", "Quantum Computing"),
        (r"many.body|Bose.Einstein|fermion.*gas|ultracold|quantum.*gas|Hubbard", "Many-Body Physics"),
        (r"quantum.*field|QED|QCD|renormali|Feynman|path.integral|Casimir", "Quantum Field Theory"),
        (r"quantum.*gravity|Planck|loop.*quantum|string|holographic", "Quantum Gravity"),
        (r"chromodynam|quark|gluon|strong.force|QCD|hadron|color.charge", "Quantum Chromodynamics"),
        (r"NMR|magnetic.resonan|Larmor|spin.echo|nuclear.*magnet", "Nuclear Magnetic Resonance"),
        (r"semiconduc|quantum.*well|quantum.*dot|heterostructur|2DEG", "Quantum Confinement"),
        (r"spectroscop|emission|absorpt|transition|selection.rule", "Atomic Spectra"),
        (r"electron.transport|conductance|mesoscopic|quantum.*transport", "Quantum Transport"),
        (r"superfluid|helium|Bose|phonon|condensat", "Many-Body Physics"),
        (r"chaos|semiclass|stadium|billiard", "Quantum Chaos"),
        (r"Schr.dinger|wave.function|eigenvalue|Hilbert|density.matrix|spin", "Schrödinger Equation"),
    ],
    ("Phys", "Particle Physics"): [
        (r"standard.model|electroweak|Higgs|W.boson|Z.boson|symmetry.break", "Standard Model"),
        (r"neutrino|oscillat|mass.hierarch|flavor|solar.neutrino", "Neutrino Physics"),
        (r"dark.matter|WIMP|axion|direct.detect|indirect.detect", "Dark Matter Searches"),
        (r"detector|calorim|tracker|silicon|scintillat|trigger|DAQ", "Particle Detectors"),
        (r"collider|LHC|Tevatron|beam|luminosity|cross.section|collision", "Collider Physics"),
        (r"beyond.*standard|supersymmetry|SUSY|extra.dimen|BSM|new.physics", "Beyond Standard Model"),
    ],
    ("Phys", "Nuclear Physics"): [
        (r"fusion|tokamak|stellarat|plasma.*confin|ITER|inertial.*confin", "Nuclear Fusion"),
        (r"fission|reactor|fuel.cycle|chain.reaction|critical|breeder", "Nuclear Fission"),
        (r"nuclear.struct|shell.model|magic.number|isomer|decay", "Nuclear Structure"),
        (r"radiat.*detect|scintillat|Geiger|dosimetr|X.ray.*imag", "Radiation Detection"),
    ],
    ("Phys", "Astrophysics"): [
        (r"cosmolog|dark.energy|expansion|CMB|cosmic.microwave|inflation|Big.Bang|baryon", "Cosmological Models"),
        (r"stellar.*evolut|main.sequence|red.giant|white.dwarf|supernova|neutron.star|nucleosynthes", "Stellar Evolution"),
        (r"star.form|protostar|molecular.cloud|accretion.*disk|T.Tauri", "Star Formation"),
        (r"galax|galactic|Milky.Way|spiral|elliptical|merger|AGN|quasar", "Galactic Dynamics"),
        (r"exoplanet|habitable|transit.*method|radial.veloc|Kepler|TESS", "Exoplanet Detection"),
        (r"planet|Mars|Jupiter|Saturn|lunar|asteroid|comet|solar.system", "Planetary Science"),
        (r"gravitat.*wave|LIGO|Virgo|binary.*merger|inspiral|pulsar", "Gravitational Waves"),
        (r"gamma.ray|X.ray.*astro|high.energy.*astro|cosmic.ray|blazar", "High-Energy Astrophysics"),
        (r"radio.*astro|interferom|VLBI|SKA|dish|antenna", "Radio Astronomy"),
        (r"solar|heliophys|corona|solar.wind|sunspot|flare|CME|magnetosphere|ionosphere", "Solar Physics"),
        (r"dark.matter|dark.energy|cosmic|cosmo", "Cosmological Models"),
    ],
    ("Phys", "Relativity"): [
        (r"gravitational.*wave|LIGO|binary|inspiral|merger", "Gravitational Waves"),
        (r"black.hole|event.horizon|Hawking|Schwarzschild|Kerr|singularity", "Black Holes"),
        (r"general.*relativ|Einstein.*field|geodesic|curvature|metric", "General Relativity"),
    ],
    ("Phys", "Electricity & Magnetism"): [
        (r"superconducti|BCS|Cooper.pair|Meissner|critical.temp|high.Tc|flux.*vortex", "Superconductivity"),
        (r"Maxwell|electromagnetic.*wave|radiation.*field|antenna|waveguide|RF|microwave", "Maxwell's Equations"),
        (r"induction|Faraday|Lenz|inductor|transformer|generator", "Electromagnetic Induction"),
        (r"magnetic|ferromagnet|antiferromagnet|spin|magnetic.*order|domain|hysteresis", "Magnetism"),
        (r"semiconduc|transistor|diode|p.n.junction|band.gap|MOSFET", "Semiconductor Physics"),
        (r"adaptive.optic|wavefront|deformable", "Electromagnetic Induction"),
    ],
    ("Phys", "Waves & Optics"): [
        (r"nonlinear.*optic|frequency.*comb|second.*harmonic|parametric|four.wave|Kerr", "Nonlinear Optics"),
        (r"laser|stimulated.*emission|optical.*amplif|gain.*medium|mode.lock", "Lasers"),
        (r"photonic.*crystal|photonic.*band|waveguide|optical.*fiber|integrated.*photon", "Photonic Crystals"),
        (r"interferen|diffract|Young|double.slit|grating|holograph", "Interference & Diffraction"),
        (r"wave.particle|photon|single.photon|quantum.*optic|squeezed|entangled.*photon", "Wave-Particle Duality"),
        (r"imaging|microscop|resolution|aberrat|lens|telescope|force.*microscop", "Optical Imaging"),
        (r"topologic|topology|topological.*material", "Topological Photonics"),
        (r"radio.*astro|antenna|receiver|dish|interferom", "Radio Wave Propagation"),
        (r"atomic|atom.*trap|cooling|frequency.*standard|optical.*clock|resonat", "Atomic Spectroscopy"),
        (r"light.*matter|cavity|polariton|strong.*coupl", "Light-Matter Interaction"),
        (r"chemical.*phys|molecular.*phys", "Molecular Spectroscopy"),
    ],
    ("Phys", "Condensed Matter"): [
        (r"topologic|Dirac|Weyl|semimetal|Chern|Berry.phase|edge.state", "Topological Phases"),
        (r"semiconduc|band.struct|exciton|2D.*material|graphene|MoS2|transistor|GaN", "Semiconductor Physics"),
        (r"superconduc|BCS|Cooper|Meissner|critical.*temp|high.Tc", "Superconductivity"),
        (r"nano|MEMS|NEMS|micro.*robot|nano.*robot|micro.*electromech", "Nanoscale Devices"),
        (r"thin.film|epitax|substrate|deposition|MBE|sputtering", "Thin Films"),
        (r"magnet|spin|ferromagnet|antiferromagnet|spin.*wave|magnon", "Magnetism"),
        (r"phonon|lattice.*vibrat|thermal.*conduct|heat.*transport", "Phonon Physics"),
    ],
    ("Phys", "Classical Mechanics"): [
        (r"fluid|turbulence|Navier|Reynolds|vortex|aerodynamic|Bernoulli|viscous", "Fluid Mechanics"),
        (r"nonlinear|chaos|bifurcat|strange.*attract|Lyapunov|soliton|logistic", "Nonlinear Dynamics"),
        (r"Lagrangian|Hamiltonian|variational|principle.*least|action|canonical", "Lagrangian Mechanics"),
        (r"orbital.*mechan|trajectory|Kepler.*orbit|three.body|N.body|celestial", "Orbital Mechanics"),
        (r"oscillat|harmonic|resonan|vibrat|pendulum|spring|normal.mode", "Harmonic Motion"),
        (r"computat|simulat|finite.element|discretiz|numer.*method", "Computational Modeling"),
    ],
    ("Phys", "Thermodynamics & Stat Mech"): [
        (r"statistical.*mechan|Boltzmann|partition.*func|ensembl|microstat|Ising|spin.*model", "Statistical Mechanics"),
        (r"entropy|second.*law|irreversib|information.*thermo", "Entropy"),
        (r"phase.*transit|critical.*phenom|order.*parameter|renormalizat|universality", "Phase Transitions"),
    ],
    ("Phys", "Plasma Physics"): [
        (r"plasma|MHD|magnetohydro|tokamak|confinement", "Plasma Confinement"),
    ],

    # Earth & Space refinements
    ("ESS", "Geology"): [
        (r"seismol|earthquake|seismic.*wave|P.wave|S.wave|magnitude|fault|rupture", "Seismology"),
        (r"plate.*tecton|subduct|convergent|divergent|transform|mid.ocean.ridge|trench", "Plate Tectonics"),
        (r"mineral|crystal|silicate|olivine|garnet|feldspar|high.pressure", "Mineralogy"),
        (r"volcano|magma|lava|eruption|pyroclast|igneous", "Volcanology"),
        (r"stratigraph|sediment|deposit|basin|formation|facies|fossil|paleont", "Stratigraphy"),
        (r"geomorphol|erosion|weather|landscape|landslide|slope", "Erosion & Weathering"),
        (r"radiometr|dating|U.Pb|carbon.14|isotope.*age|geochronol", "Radiometric Dating"),
        (r"geochem|trace.*element|partition.*coeffic|REE|isotope.*ratio", "Geochemistry"),
        (r"geophys|gravity.*anomal|magnetic.*survey|seismic.*imag|tomograph|inversion", "Geophysics"),
        (r"petrol|rock|igneous|metamorph|sedimentary", "Petrology"),
    ],
    ("ESS", "Oceanography"): [
        (r"ocean.*circulat|thermohaline|AMOC|gyre|current|upwelling|eddy", "Ocean Circulation"),
        (r"marine.*ecol|coral|reef|benthic|pelagic|plankton|fisheri|marine.*bio", "Marine Ecology"),
        (r"ocean.*chem|acidif|pH|dissolve|salinity|nutrient.*ocean", "Marine Chemistry"),
        (r"tidal|tide|wave.*energy|coastal.*dynam|storm.*surge|tsunami", "Tidal Dynamics"),
        (r"acoust|sonar|underwater.*sound", "Underwater Acoustics"),
    ],
    ("ESS", "Meteorology"): [
        (r"atmospher.*circulat|Hadley|Ferrel|jet.*stream|polar.*vortex|teleconnect|Arctic.*amplif|monsoon", "Atmospheric Circulation"),
        (r"severe.*weather|hurricane|typhoon|cyclone|tornado|convect.*storm|supercell", "Severe Weather"),
        (r"climate.*model|GCM|general.*circulat|CMIP|RCP|scenario|project|warm|future|ice.*sheet|glacial|cryospher|permafrost", "Climate Modeling"),
        (r"ozone|stratospher.*chem|CFC|aerosol.*chem|photochem.*smog|PM2.*5|air.*quality|emission", "Atmospheric Chemistry"),
        (r"remote.*sens|satellite|LiDAR|radar|MODIS|Landsat|GPS|GIS", "Remote Sensing"),
        (r"paleoclim|ice.*core|proxy|Holocene|Pleistocene|Milankovitch|dendrochronol", "Paleoclimatology"),
        (r"cloud|precipitat|rain|aerosol.*cloud|droplet|convect", "Cloud Physics"),
        (r"carbon.*cycle|CO2|greenhouse|methane|carbon.*flux|carbon.*sequestrat|carbon.*sink", "Carbon Cycle"),
        (r"climate.*change|global.*warm|temperature.*rise|sea.*level.*rise|adapt|mitigat", "Climate Change"),
    ],
    ("ESS", "Hydrology"): [
        (r"groundwater|aquifer|well|pump|permeab|porous.*media|Darcy", "Groundwater Flow"),
        (r"water.*qual|contamin|pollut|treatment|purif|desalin|wastewater", "Water Quality"),
        (r"watershed|runoff|streamflow|flood|precipitation|drainage|hydro", "Surface Hydrology"),
    ],
    ("ESS", "Stellar Astrophysics"): [
        (r"stellar.*evolut|main.*sequence|red.*giant|white.*dwarf|HR.*diagram|supernova|nova|neutron.*star|pulsar", "Stellar Evolution"),
        (r"star.*form|protostar|molecular.*cloud|accretion|T.*Tauri|HII|nebula", "Star Formation"),
        (r"nucleosynthes|r.process|s.process|alpha.*process|element.*origin|abundance", "Stellar Nucleosynthesis"),
        (r"binary|eclips|mass.*transfer|Roche|accretion.*disk", "Binary Stars"),
    ],
    ("ESS", "Planetary Science"): [
        (r"exoplanet|transit|radial.*veloc|habitable|biosignat|TESS|Kepler", "Exoplanet Detection"),
        (r"atmosphere|Mars|Venus|Titan|escape|photochem|haze", "Planetary Atmospheres"),
        (r"interior|mantle|core|differentiat|ice.*giant|rocky", "Planetary Interiors"),
        (r"asteroid|comet|meteorite|small.*bod|impact|crater", "Small Bodies"),
    ],
    ("ESS", "Cosmology"): [
        (r"dark.*matter|WIMP|axion|halo|rotation.*curve|lensing|gravitational.*lens", "Dark Matter"),
        (r"dark.*energy|accelerat.*expansion|cosmological.*constant|quintessence|supernova.*Ia", "Dark Energy"),
        (r"CMB|cosmic.*microwave|polariz|anisotrop|recombinati|Planck.*satellite|WMAP", "Cosmic Microwave Background"),
        (r"inflation|primordial|Big.*Bang|nucleosynth|baryogenesis|horizon.*problem", "Big Bang Cosmology"),
    ],
    ("ESS", "Observational Astronomy"): [
        (r"radio|VLBI|interferom|SKA|dish|21.*cm|pulsar.*timing", "Radio Astronomy"),
        (r"gravitational.*wave|LIGO|Virgo|multi.*messenger|kilonova", "Gravitational Wave Astronomy"),
        (r"telescope|survey|photometr|astrom|catalog|pipeline", "Survey Astronomy"),
    ],

    # CS/AI refinements
    ("CS/AI", "Deep Learning"): [
        (r"attention|transformer|BERT|GPT|LLM|large.*language|self.attention", "Attention Mechanisms"),
        (r"CNN|convolutional|ResNet|VGG|image.*classif|feature.*map", "Convolutional Neural Networks"),
        (r"diffusion|score.*based|denoising.*diffusion|DDPM|stable.*diffusion", "Diffusion Models"),
        (r"GNN|graph.*neural|message.*passing|node.*classif|graph.*convol", "Graph Neural Networks"),
        (r"RNN|LSTM|GRU|recurrent|sequence.*model|time.*series", "Recurrent Neural Networks"),
        (r"GAN|generative.*adversar|discriminat|generator|StyleGAN|CycleGAN", "Generative Adversarial Networks"),
        (r"autoencoder|VAE|variational|latent.*space|reconstruction", "Autoencoders"),
        (r"vanishing.*gradient|exploding|residual.*connect|batch.*norm|layer.*norm|skip.*connect", "Vanishing/Exploding Gradients"),
    ],
    ("CS/AI", "Machine Learning"): [
        (r"gradient.*descent|SGD|Adam|optimizer|learning.*rate|convergence", "Gradient Descent"),
        (r"decision.*tree|random.*forest|XGBoost|boosting|bagging|ensemble", "Decision Trees & Random Forests"),
        (r"reinforcement.*learn|Q.learn|policy.*gradient|reward|MDP|bandit|multi.*agent|RL", "Reinforcement Learning"),
        (r"transfer.*learn|domain.*adapt|fine.tun|pretrain|few.shot", "Transfer Learning"),
        (r"causal.*infer|counterfact|instrument.*variable|do.calculus|causal.*graph", "Causal Inference"),
        (r"represent.*learn|contrastiv|self.*supervis|embedding|feature.*learn|SimCLR|CLIP", "Representation Learning"),
        (r"overfit|regular|dropout|weight.*decay|early.*stop|cross.*valid|bias.*variance", "Overfitting & Regularization"),
        (r"SVM|support.*vector|kernel.*method|kernel.*trick", "Support Vector Machines"),
        (r"clustering|k.means|DBSCAN|hierarchical|mixture.*model|EM.*algorithm", "Clustering"),
        (r"anomaly|outlier|novelty.*detect", "Anomaly Detection"),
    ],
    ("CS/AI", "Probability & Statistics"): [
        (r"hypothes.*test|p.value|confidence.*interval|t.test|chi.square|ANOVA|signific", "Hypothesis Testing"),
        (r"Bayes|posterior|prior|MCMC|Markov.*chain.*Monte|conjugate|credible", "Bayesian Inference"),
        (r"distribut|normal|Gaussian|Poisson|binomial|exponential|heavy.*tail", "Probability Distributions"),
        (r"regression|linear.*model|logistic|OLS|coefficient|predictor|panel.*data", "Regression"),
        (r"bias.*variance|model.*select|cross.*valid|AIC|BIC", "Bias-Variance Tradeoff"),
        (r"stochastic|Markov|random.*walk|Brownian|martingale|ergodic|Poisson.*process", "Stochastic Processes"),
        (r"random.*matri|eigenvalue.*distribut|Wigner|Tracy.*Widom|Marchenko", "Random Variables"),
        (r"experiment.*design|A/B.*test|factorial|optimal.*design|block|randomiz", "Experimental Design"),
        (r"econometr|panel.*data|instrumental.*variable|treatment.*effect|wage|labor|employ|merger|trade|GDP|monetary|fiscal|market|banking|financial|investment|growth|inflation", "Econometrics"),
        (r"causal.*infer|counterfact|do.calculus", "Causal Inference"),
        (r"nonparametr|kernel.*density|bootstrap|permutation.*test", "Nonparametric Methods"),
    ],
    ("CS/AI", "Algorithms & TCS"): [
        (r"graph.*algorithm|shortest.*path|BFS|DFS|minimum.*spanning|network.*flow|matching", "Graph Algorithms"),
        (r"sort|search|binary.*search|hash|tree.*search|cache.*efficien", "Sorting & Search"),
        (r"complex|NP.*hard|NP.*complete|approximat|reduction|decidab|P.*vs.*NP|lower.*bound", "Computational Complexity"),
        (r"data.*struct|queue|stack|heap|trie|hash.*table|concurrent.*data", "Data Structures"),
        (r"cryptograph|encryp|RSA|AES|zero.*knowledge|hash.*function|signature|PKI", "Cryptography"),
        (r"formal.*verif|model.*check|temporal.*logic|proof.*assist|type.*theory|theorem.*prov", "Formal Verification"),
        (r"program|compil|interpret|type.*system|lambda.*calculus|functional|Haskell", "Programming Languages"),
        (r"combinator|Ramsey|extremal|matroid|permutation|partition|generating.*func", "Combinatorics"),
        (r"network.*secur|intrusion|malware|firewall|adversar|privac|differential.*privac", "Network Security"),
    ],
    ("CS/AI", "Computer Systems"): [
        (r"CPU|GPU|TPU|processor|architect|pipeline|cache|FPGA|ASIC|chip|VLSI", "CPU/GPU Architecture"),
        (r"parallel|distributed.*comput|MapReduce|Spark|cluster|MPI|shared.*memory", "Parallel Computing"),
        (r"quantum.*comput|qubit|superconducting.*qubit|ion.*trap|quantum.*error.*correct", "Quantum Computing Hardware"),
        (r"database|SQL|query.*optim|index|transaction|NoSQL|storage", "Database Systems"),
        (r"network|TCP|UDP|protocol|routing|SDN|wireless|5G|spectrum|IoT|edge.*comput|fog", "Network Protocols"),
        (r"HCI|human.*computer|user.*interface|usability|UI|UX|immersive|display|gesture", "Human-Computer Interaction"),
        (r"software.*engineer|test|DevOps|agile|CI/CD|refactor", "Software Engineering"),
        (r"cloud|virtuali|container|Docker|Kubernetes|microservic|serverless", "Cloud Computing"),
        (r"embedded|real.*time|RTOS|firmware|sensor.*network", "Embedded Systems"),
    ],
    ("CS/AI", "NLP & Language Models"): [
        (r"token|subword|BPE|sentencepiece|vocabular", "Tokenization"),
        (r"RLHF|instruct.*follow|alignment|fine.*tun.*LLM|preference.*learn", "Language Model Training"),
        (r"embed|word2vec|GloVe|sentence.*embed|semantic.*similar", "Embeddings"),
        (r"topic.*model|LDA|Dirichlet|latent.*topic", "Topic Modeling"),
        (r"sentiment|opinion|affect|emotion.*detect", "Sentiment Analysis"),
        (r"translat|machine.*translat|multilingual|cross.*lingual", "Machine Translation"),
        (r"speech|ASR|TTS|dialogue|voice|spoken", "Speech Recognition"),
        (r"text.*classif|NER|named.*entity|relation.*extract|information.*extract", "Information Extraction"),
        (r"NLP|natural.*language|parsing|syntax|semantic|pragmatic|text", "Language Understanding"),
    ],
    ("CS/AI", "Computer Vision"): [
        (r"object.*detect|YOLO|SSD|Faster.*R.CNN|anchor|bounding.*box", "Object Detection"),
        (r"segment|mask|semantic.*segment|instance.*segment|panoptic|U.Net", "Image Segmentation"),
        (r"3D|reconstruction|depth|stereo|point.*cloud|mesh|NeRF|rendering|graphic|CAD", "3D Reconstruction"),
        (r"face|express|recognit|biometric|identity", "Face Recognition"),
        (r"track|surveillance|re.identif|MOT|optical.*flow", "Object Tracking"),
        (r"medical.*imag|CT|MRI|patholog|radiol|retina.*scan", "Medical Imaging"),
        (r"multimodal|vision.*language|CLIP|visual.*question|image.*caption", "Multimodal Learning"),
    ],
    ("CS/AI", "Robotics"): [
        (r"motion.*plan|path.*plan|RRT|trajectory|navigation|obstacle.*avoid", "Motion Planning"),
        (r"manipulat|grasp|pick.*place|deformable|contact|dexterous", "Manipulation"),
        (r"autonomous|self.*driv|SLAM|localiz|mapping|perception", "Autonomous Navigation"),
        (r"locomot|legged|bipedal|quadruped|walking|running|balance", "Locomotion"),
    ],
    ("CS/AI", "Mathematical Modeling"): [
        (r"game.*theory|Nash|mechanism.*design|auction|incentive|strategic|equilibrium", "Game Theory"),
        (r"optimiz|convex|linear.*program|integer.*program|gradient|LP|SDP|ADMM", "Optimization"),
        (r"numerical|finite.*element|finite.*differ|PDE|ODE|discretiz|mesh|solver", "Numerical Methods"),
        (r"dynamical.*system|ODE|bifurcat|chaos|attractor|stability|Lyapunov", "Dynamical Systems"),
        (r"Fourier|wavelet|harmonic.*analy|spectral|frequency.*domain|signal", "Fourier Analysis"),
        (r"topolog|homology|manifold|homotopy|cohomology|Betti|simplicial", "Topology"),
        (r"algebraic.*struct|group.*theory|ring|field|module|represent.*theory|Lie", "Algebraic Structures"),
        (r"number.*theory|prime|Diophantine|modular|arithmetic|elliptic.*curve", "Number Theory"),
        (r"differential.*geom|curvature|Riemann|geodesic|tensor", "Differential Geometry"),
        (r"functional.*anal|Banach|Hilbert|operator|spectrum|eigenvalue|eigenvector", "Functional Analysis"),
        (r"math.*phys|integrab|quantum.*algebra|conformal|Yang.Mills", "Mathematical Physics"),
    ],
    ("CS/AI", "Linear Algebra"): [
        (r"eigenvalue|eigenvector|spectral|diagonaliz|PCA|SVD", "Eigenvalues & Eigenvectors"),
        (r"matrix.*decompos|LU|QR|Cholesky|low.*rank|tensor", "Matrix Decompositions"),
    ],
}


def refine_fine(new_cat, coarse, default_fine, focus):
    """Use focus keywords to pick a more specific fine subcategory."""
    key = (new_cat, coarse)
    if key not in FINE_REFINE:
        return default_fine

    text = f"{default_fine} {focus}"
    for pattern, fine in FINE_REFINE[key]:
        if re.search(pattern, text, re.IGNORECASE):
            return fine
    return default_fine


def convert_tag(old_tag):
    """Convert a 3-part tag to 4-part format."""
    old_cat = old_tag[0]
    old_sub = old_tag[1]
    focus = old_tag[2] if len(old_tag) > 2 else ""

    new_cat = CAT_ABBREV.get(old_cat, old_cat)

    key = (old_cat, old_sub)
    if key in COARSE_FINE_MAP:
        coarse, default_fine = COARSE_FINE_MAP[key]
    else:
        # Fallback: use old subcategory as coarse, empty fine
        coarse = old_sub
        default_fine = old_sub

    fine = refine_fine(new_cat, coarse, default_fine, focus)

    return [new_cat, coarse, fine, focus]


def main():
    with open(INPUT_FILE) as f:
        labs = json.load(f)

    print(f"Converting {len(labs)} labs to 4-part tag format...")

    total_tags = 0
    for lab in labs:
        new_tags = []
        seen = set()
        for tag in lab.get("t", []):
            new_tag = convert_tag(tag)
            # Deduplicate by (cat, coarse, fine)
            key = (new_tag[0], new_tag[1], new_tag[2])
            if key not in seen:
                seen.add(key)
                new_tags.append(new_tag)
        lab["t"] = new_tags
        total_tags += len(new_tags)

    # Stats
    print(f"Total tags: {total_tags}")

    # Show coarse/fine distribution
    coarse_counts = {}
    fine_counts = {}
    for lab in labs:
        for tag in lab.get("t", []):
            ck = f"{tag[0]} | {tag[1]}"
            fk = f"{tag[0]} | {tag[1]} | {tag[2]}"
            coarse_counts[ck] = coarse_counts.get(ck, 0) + 1
            fine_counts[fk] = fine_counts.get(fk, 0) + 1

    print(f"\nUnique coarse subcategories: {len(coarse_counts)}")
    print(f"Unique fine subcategories: {len(fine_counts)}")

    print("\nTop coarse subcategories:")
    for k, v in sorted(coarse_counts.items(), key=lambda x: -x[1])[:25]:
        print(f"  {v:4d}  {k}")

    print("\nTop fine subcategories:")
    for k, v in sorted(fine_counts.items(), key=lambda x: -x[1])[:25]:
        print(f"  {v:4d}  {k}")

    # Write
    with open(OUTPUT_FILE, "w") as f:
        json.dump(labs, f, separators=(",", ":"))

    import os
    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\nWrote {len(labs)} labs to {OUTPUT_FILE} ({size_kb:.0f}KB)")


if __name__ == "__main__":
    main()
