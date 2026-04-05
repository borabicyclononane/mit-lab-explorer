"""
Fix all tags in labs.json to use Science Bowl-appropriate subcategories.

Replaces OpenAlex academic taxonomy subcategories with textbook-chapter-level
subcategories that a Science Bowl question writer would recognize.
"""

import json
import re

INPUT_FILE = "../data/labs.json"
OUTPUT_FILE = "../data/labs.json"


# ── Keyword-based subcategory inference ──────────────────────────────────
# Each entry: (keyword_pattern, new_subcategory)
# Checked in order; first match wins. Case-insensitive.

BIO_RULES = [
    # Cancer / Oncology
    (r"cancer|tumor|oncog|leukemia|lymphoma|myeloma|carcinogen|metasta|CAR-T|immuno.?therapy", "Hallmarks of Cancer & Oncogenes/Tumor Suppressors"),
    (r"microRNA|miRNA|siRNA|RNA interference|RNAi", "RNA Interference & Gene Regulation"),
    # Immunology
    (r"T.cell|B.cell|immune|immunol|antibod|antigen|innate|adaptive.immun|cytokine|inflammat|allerg", "Immune System & Immunology"),
    (r"vaccine|vaccin", "Immune System & Immunology"),
    # Neuroscience
    (r"neural|neuron|neurosci|brain|cortex|hippocamp|synap|neurodegenerat|Alzheimer|Parkinson|ALS|amyotrophic|neuroinflam|neuropharmac|neuroplast|neurogenesis", "Nervous System & Neuroscience"),
    (r"optogenetic|photoreceptor", "Nervous System & Neuroscience"),
    (r"visual.percep|retina|ocular|optic|vision|eye", "Sensory Systems & Perception"),
    (r"olfact|taste|auditor|cochlea|tactile|sensory", "Sensory Systems & Perception"),
    (r"cogniti|language|metaphor|reading|literacy|psycholinguis", "Cognition & Language"),
    (r"circadian|melatonin|sleep", "Circadian Rhythms & Biological Clocks"),
    (r"anxiety|depression|psycho|mental.health|personality|emotion|attachment|behavioral.health", "Psychology & Behavioral Science"),
    # Genetics / Molecular
    (r"CRISPR|gene.edit|genetic.engineer", "CRISPR & Genetic Engineering"),
    (r"genetic.map|genetic.divers|genetic.assoc|population.genet|Hardy.Weinberg|phylogenet|genomic|genom(?:e|ics)", "Genetics & Genomics"),
    (r"epigenet|chromatin|histone|methyl|acetyl", "Chromatin Structure & Epigenetics"),
    (r"transcri|mRNA|RNA.process|splicing|ribosom", "Transcription & RNA Processing"),
    (r"DNA.repl|DNA.repair|recombin|mutat", "DNA Replication & Repair"),
    (r"microbiom|microbiota|gut.microb|microbial.commun", "Microbiome & Microbial Ecology"),
    (r"bacteri|antimicrob|antibiotic|clostridium|mycobact|tuberculosis", "Microbiology & Infectious Disease"),
    (r"virus|viral|HIV|hepatitis|SARS|COVID|rabies", "Virology & Viral Pathogenesis"),
    (r"parasit|malaria|mosquito|vector.borne|toxoplasma", "Parasitology & Vector-Borne Disease"),
    # Cell biology
    (r"cell.cycle|mitosis|meiosis|cell.division|microtubul|cytoskelet|spindle", "Cell Cycle & Division"),
    (r"cell.mechani|cellular.mechani|cell.adhesion|extracellular.matrix", "Cell Mechanics & Adhesion"),
    (r"membrane.transport|ion.channel|signal.?transduct|receptor|signaling", "Membrane Transport & Cell Signaling"),
    (r"apoptosis|programmed.cell.death|autophagy|ferroptosis", "Apoptosis & Cell Death Pathways"),
    (r"stem.cell|regenerat|tissue.engineer|scaffold|biomaterial|hydrogel", "Stem Cells & Tissue Engineering"),
    # Organ systems
    (r"heart|cardiac|cardiovasc|coronary", "Cardiovascular System"),
    (r"lung|pulmonar|respirat|ventilat|cystic.fibrosis", "Respiratory System"),
    (r"liver|hepat", "Digestive System & Metabolism"),
    (r"kidney|renal|nephro", "Excretory System"),
    (r"bone|osteo|musculoskeletal|skeletal|cartilage|dental|tooth|endodont", "Musculoskeletal System"),
    (r"endocrin|hormone|insulin|diabetes|thyroid|obesity|adipose|appetite|pancrea", "Endocrine System & Hormones"),
    (r"reproduct|pregnan|preeclampsia|endometri|sperm|fertil|embryo", "Reproductive System & Development"),
    (r"skin|dermat", "Integumentary System"),
    # Other bio
    (r"enzyme|kinetic|catalys|substrate|protein.fold|protein.struct|biosynthesis", "Enzyme Kinetics & Protein Biochemistry"),
    (r"photosynthesis|chloroplast|light.react|dark.react|carbon.fixat", "Photosynthesis"),
    (r"plant|crop|mycotoxin|agricultur", "Plant Biology"),
    (r"ecology|ecosystem|biodivers|conservat|wildlife|species.distrib", "Ecology & Biodiversity"),
    (r"evolution|phylogen|paleont|fossil|stratigraphy", "Evolution & Paleontology"),
    (r"insect|entomolog|Coleoptera|invertebrate|symbiosis", "Entomology & Invertebrate Biology"),
    (r"animal.behav|vocal.commun|mating|zoolog", "Animal Behavior & Ethology"),
    (r"drug.deliv|pharmaceut|pharmacol|pharmacokinet|transdermal|nanoparticle.*drug", "Pharmacology & Drug Delivery"),
    (r"biosenso|biosensing|fluorescen|microscop|imaging|ultrasound|elastograph|electron.microscop", "Bioimaging & Microscopy"),
    (r"bioinformat|health.inform|AI.in.health|artificial.intelligence.*health", "Bioinformatics & Computational Biology"),
    (r"epidemiol|public.health|breastfeed|maternal|global.health", "Epidemiology & Public Health"),
    (r"nutrition|diet|trace.element|food|vitamin|folate", "Nutrition & Metabolism"),
    (r"spaceflight|space.biology|astronaut", "Space Biology & Astrobiology"),
    (r"stroke|rehabilitat|physical.therapy|gait|balance|fall", "Rehabilitation & Motor Control"),
    (r"sport|exercise|training|athlet", "Exercise Physiology"),
    (r"erythrocyte|blood|hematol|anemia|erythropoietin|coagul", "Hematology & Blood"),
    (r"sirtuin|resveratrol|aging|longevity|gerontol|senescen", "Aging & Longevity"),
    # More specific catches before fallback
    (r"mitochondri", "Cell Respiration & Mitochondria"),
    (r"ubiquitin|proteasom|protein.degradat|proteolysi", "Protein Degradation & Ubiquitin Pathway"),
    (r"glycosylat|glycoprotein|carbohydrate.*bio", "Glycobiology & Post-Translational Modification"),
    (r"gene.regulat|regulatory.network|gene.express|developmental.bio", "Gene Regulation & Developmental Biology"),
    (r"nitric.oxide|endothelin|vasoact", "Vascular Biology & Signaling"),
    (r"fungal|yeast|fungi|mycolog", "Mycology & Fungal Biology"),
    (r"S100|annexin|calmodulin|calcium.*signal", "Calcium Signaling & Binding Proteins"),
    (r"lupus|autoimmun|SLE", "Autoimmune Disease"),
    (r"botulinum|tetanus|neurotoxin", "Nervous System & Neuroscience"),
    (r"metal.complex|coordination.*bio|bioinorganic", "Bioinorganic Chemistry"),
    (r"Chinese.medicine|traditional.medicine|herbal", "Pharmacology & Drug Delivery"),
    (r"livestock|animal.breed|genetic.*trait", "Animal Genetics & Breeding"),
    (r"employ|welfare|labor|socio", "Epidemiology & Public Health"),
    (r"geomagneti|paleomagneti|magneti.*earth", "Ecology & Biodiversity"),
    (r"photosynthetic|light.harvest|chlorophyll", "Photosynthesis"),
    (r"DNA|nucleic.acid|nucleotide", "DNA Replication & Repair"),
    (r"lipid|membrane.*struct|phospholipid|liposom", "Membrane Structure & Lipid Biology"),
    (r"spectroscop.*bio|biospectroscop", "Bioimaging & Microscopy"),
    (r"RNA|synthe.*mech", "Transcription & RNA Processing"),
    # Catch-all molecular biology
    (r"molecular|biochem|protein|peptide|amino.acid|carbohydrate|metabolism", "Molecular Biology & Biochemistry"),
    (r"cell|cellular", "Cell Biology"),
    (r"bio", "Molecular Biology & Biochemistry"),
]

CHEM_RULES = [
    (r"organic|asymmetric.synth|stereochem|chiral|coupling.react|cyclopropan|carbene|aromatic|surfactant|carbohydrate.chem|named.react", "Organic Synthesis & Reaction Mechanisms"),
    (r"NMR|IR.spectro|mass.spectro|UV-Vis|spectroscop|chromatograph|analytical", "Spectroscopy (NMR, IR, Mass Spec, UV-Vis)"),
    (r"transition.metal|coordinat|metal.organic.framework|MOF|organometal|inorganic.fluorid|metal.catalyz|iron.sulfur|metalloenzym", "Transition Metal Chemistry & Coordination Compounds"),
    (r"catalys|oxidat|hydrogenat|reaction.mechanism", "Activation Energy & Catalysis"),
    (r"electrochem|electrode|fuel.cell|battery|cell.potential|molten.salt", "Electrochemistry & Cell Potential"),
    (r"polymer|conducting.polymer|plastic|electrospun|nanofiber", "Polymer Chemistry"),
    (r"computational.chem|molecular.model|simulation|DFT|ab.initio", "Computational Chemistry"),
    (r"crystal|solubil|phase.diagram|phase.transit|thermal.prop|superconducti", "Phase Diagrams & Crystal Structure"),
    (r"photochem|electron.transfer|photovoltaic|solar|luminescen|fluorescen|optical", "Photochemistry & Energy Transfer"),
    (r"colloid|surface|superhydrophob|coating|emulsion|wetting|interface", "Surface Chemistry & Colloids"),
    (r"molecular.orbital|bonding|electrostatic|intermolecular|van.der.Waals", "Molecular Orbital Theory & Bonding"),
    (r"nanopart|nanomaterial|quantum.dot|nanotub|graphene|nano", "Nanochemistry & Nanomaterials"),
    (r"biomaterial|silk|collagen|calcium.carbonate|diatom|algae.*bio", "Biomaterials & Bioorganic Chemistry"),
    (r"renewable.energ|CO2.reduc|biofuel|sustainab|green.chem|solar.*water|water.purif", "Green Chemistry & Sustainability"),
    (r"combust|engine|energy.engineer|fuel|hydrogen", "Thermochemistry & Energy"),
    (r"corrosion|alloy|metal.*propert|hydrogen.embrittle|steel|iron", "Materials Chemistry & Corrosion"),
    (r"rheolog|fluid|flow|viscosit", "Chemical Kinetics & Dynamics"),
    (r"magnetic|perovskite|ferroelect|piezoelect|metamaterial|liquid.crystal|semiconductor|supercapacitor", "Solid-State Chemistry & Materials"),
    (r"sensor|detect|ion.detect", "Analytical Chemistry & Sensors"),
    (r"enzyme.*struct|enzyme.*funct|biocatalys", "Enzyme Kinetics & Catalysis"),
    (r"nuclear.*material|nuclear.*technolog|fusion.*material|fission.*material|graphite.*nuclear", "Nuclear Chemistry"),
    (r"machine.learn.*material|ML.*material|computational.*material", "Computational Chemistry"),
    (r"porphyrin|phthalocyanine|macrocycl", "Coordination Chemistry & Macrocycles"),
    (r"MXene|MAX.phase|2D.material", "Nanochemistry & Nanomaterials"),
    (r"chalcogenide|phase.change.*material", "Solid-State Chemistry & Materials"),
    (r"thermoelectric|Peltier|Seebeck", "Solid-State Chemistry & Materials"),
    (r"diamond|carbon.*material|fullerene|buckminster", "Nanochemistry & Nanomaterials"),
    (r"impact|ballistic|deformation|mechan.*prop", "Materials Chemistry & Corrosion"),
    (r"oxide|perovskite.*oxide|electronic.*prop", "Solid-State Chemistry & Materials"),
    (r"dynam.*prop|viscoelast", "Chemical Kinetics & Dynamics"),
    (r"chem", "General Chemistry"),
]

PHYS_RULES = [
    # Particle / Nuclear / HEP
    (r"dark.matter|dark.energy|cosmic|cosmolog", "Dark Matter & Dark Energy"),
    (r"standard.model|fundamental.particl|quark|lepton|boson|Higgs", "Standard Model & Fundamental Particles"),
    (r"neutrino", "Neutrino Physics"),
    (r"particle.phys|particle.detect|collider|hadron|LHC", "Particle Physics & Detectors"),
    (r"black.hole|general.relativ|gravitational.wave|LIGO|pulsar|binary.star|neutron.star", "General Relativity & Gravitational Waves"),
    (r"string.theor|supersymmetr|noncommutative|quantum.gravity|extra.dimension", "String Theory & Quantum Gravity"),
    (r"nuclear.fus|nuclear.fiss|nuclear.phys|nuclear.react|nuclear.structure", "Nuclear Fusion & Fission"),
    (r"radiation.detect|scintillat|X-ray.*imag|radiation", "Radiation & Detection"),
    # Quantum
    (r"quantum.comput|qubit|quantum.algorithm|quantum.circuit|quantum.error", "Quantum Computing"),
    (r"quantum.entangl|Bell|EPR|quantum.information|quantum.teleport", "Quantum Entanglement & Information"),
    (r"quantum.tunnel|quantum.well|potential.barrier", "Quantum Tunneling"),
    (r"quantum.many.body|Bose.Einstein|fermion|boson|ultracold|quantum.gas", "Quantum Many-Body Physics"),
    (r"quantum.electrodynamic|Casimir|QED|QFT|field.theor", "Quantum Field Theory"),
    (r"wave.particle|photon|single.photon|quantum.optic", "Wave-Particle Duality & Quantum Optics"),
    (r"quantum", "Quantum Mechanics"),
    # Classical / Mechanics
    (r"Lagrangian|Hamiltonian|classical.mech|analytical.mech", "Lagrangian & Hamiltonian Mechanics"),
    (r"oscillat|harmonic|resonan|vibrat", "Oscillations & Simple Harmonic Motion"),
    (r"rotational|moment.of.inertia|angular.momentum|torque", "Rotational Mechanics"),
    (r"fluid.dynam|turbulence|aerodynam|Navier|vortex", "Fluid Dynamics"),
    (r"chaos|nonlinear|soliton|fractal|complex.system", "Nonlinear Dynamics & Chaos"),
    # E&M / Optics
    (r"Maxwell|electromagnetic|antenna|microwave|RF", "Maxwell's Equations & Electromagnetism"),
    (r"Faraday|induction|inductor|magnetic.field|magnetism|ferromagnet|spin", "Electromagnetic Induction & Magnetism"),
    (r"laser|photonic|fiber.optic|waveguide|nonlinear.optic", "Lasers & Photonics"),
    (r"adaptive.optic|wavefront|lens|aberrat|telescope|interferom", "Optics & Interferometry"),
    (r"optic|refract|diffract", "Optics & Wave Phenomena"),
    # Condensed matter
    (r"superconducti|BCS|Cooper.pair|Meissner", "Superconductivity"),
    (r"topological|Dirac|Weyl|semimetal|topolog", "Topological Phases of Matter"),
    (r"semiconduc|GaN|transistor|diode|band.gap|band.struct", "Semiconductor Physics"),
    (r"thin.film|surface.phys|deposition|sputtering", "Thin Films & Surface Physics"),
    (r"condensed.matter|solid.state|phonon|lattice", "Condensed Matter Physics"),
    (r"nano.*robot|micro.*robot|MEMS|NEMS", "Micro/Nano Devices"),
    # Astro
    (r"stellar|star|main.sequence|red.giant|white.dwarf|supernova|nova", "Stellar Evolution & Life Cycles"),
    (r"galaxy|galaxies|quasar|AGN|active.galact", "Galaxies & Galactic Structure"),
    (r"exoplanet|planet.*detect|transit.method|radial.velocity|habitable.zone", "Exoplanets & Detection Methods"),
    (r"radio.astro|telescope|observatory|survey", "Observational Astronomy & Telescopes"),
    (r"gamma.ray|X-ray.*astro|high.energy.*astro", "High-Energy Astrophysics"),
    (r"astro|cosmo", "Astrophysics & Cosmology"),
    # Stat mech / thermo
    (r"statistical.mechani|Boltzmann|entropy|partition.funct|thermo", "Statistical Mechanics & Thermodynamics"),
    (r"network.*analy|complex.network", "Statistical Mechanics & Thermodynamics"),
    # More specific before catch-all
    (r"high.energy|collider|collision|accelerator|beam", "Particle Physics & Detectors"),
    (r"NMR|magnetic.resonance", "Nuclear Magnetic Resonance"),
    # Catch-all
    (r"model.reduc|neural.network|computation|simulat", "Computational Physics"),
    (r"experiment|measurement|instrumen", "Experimental Physics & Instrumentation"),
    (r"phys", "Physics"),
]

EARTH_RULES = [
    (r"plate.tectonic|subduct|boundar|mantle|lithosphere|crust|magma|volcan", "Plate Tectonics & Volcanism"),
    (r"earthquake|seism|fault|tectonic", "Earthquakes & Seismology"),
    (r"exoplanet|planet.*detect|habitable", "Exoplanets & Detection Methods"),
    (r"dark.matter|dark.energy|cosmol", "Dark Matter & Dark Energy"),
    (r"stellar|star|supernova|neutron.star", "Stellar Evolution & Life Cycles"),
    (r"atmospher|ozone|aerosol|cloud|climate.model|greenhouse|troposphere|stratosphere", "Atmospheric Structure & Composition"),
    (r"cyclone|hurricane|typhoon|tornado|meteorolog|weather|storm", "Weather Systems & Meteorology"),
    (r"ocean|marine|sea.level|coral|acidif|underwater|acoust|fisheri|coastal", "Ocean Circulation & Marine Science"),
    (r"glacier|ice.sheet|permafrost|Arctic|Antarctic|cryosphere", "Glaciology & Cryosphere"),
    (r"climate.change|global.warm|carbon.dynam|CO2|greenhouse|carbon.cycle", "Climate Change & Carbon Cycle"),
    (r"radiometric|isotope|geochron|dating", "Radiometric Dating & Isotope Geochemistry"),
    (r"geochemi|elemental.analy|mineral|petrology|rock", "Geochemistry & Mineralogy"),
    (r"fossil|paleont|stratigraphy|extinction|evolution", "Paleontology & Earth History"),
    (r"remote.sens|LiDAR|satellite|GPS|GIS", "Remote Sensing & GIS"),
    (r"groundwater|aquifer|hydrology|watershed|water.resource", "Hydrology & Water Resources"),
    (r"soil|erosion|sediment|aeolian|landslide", "Soil Science & Geomorphology"),
    (r"pollut|contaminat|toxic|mercury|arsenic|heavy.metal|endocrine.disrupt", "Environmental Pollution & Toxicology"),
    (r"wastewater|water.treat|membrane.separ|desalinat", "Water Treatment & Environmental Engineering"),
    (r"ecosystem|biodiversity|ecology|species|invasive|conservat|wildlife", "Ecology & Ecosystems"),
    (r"renewable|wind|solar|energy.*environ|sustain|water.energy.food|nexus", "Energy & Environmental Sustainability"),
    (r"air.quality|emission|particulate", "Air Quality & Atmospheric Chemistry"),
    (r"geophys|seismic.imag|inversion|gravit|magneto|core", "Geophysics & Earth's Interior"),
    (r"geolog|formation|basin|stratum", "Geology & Earth Processes"),
    (r"methane.hydrate|gas.hydrate|clathrate", "Geochemistry & Mineralogy"),
    (r"climate.*variab|climate.*model|paleoclim|ice.core", "Climate Change & Carbon Cycle"),
    (r"microbial.fuel|bioremedia", "Environmental Pollution & Toxicology"),
    (r"earth|planet|space", "Earth & Planetary Science"),
]

CS_RULES = [
    # ML / AI specifics
    (r"transform|attention.mechan|BERT|GPT|large.language|LLM", "Transformers & Attention Mechanism"),
    (r"CNN|convolutional|image.classif|object.detect", "CNNs (Convolutional Neural Networks)"),
    (r"GNN|graph.neural|graph.network|node.embed", "Graph Neural Networks"),
    (r"diffusion.model|score.based|denoising", "Diffusion Models & Generative AI"),
    (r"reinforcement.learn|Q.learn|policy.gradient|reward|multi.agent|bandit", "Reinforcement Learning"),
    (r"GAN|generative.adversar|variational.auto|VAE|generative.model", "Generative Models (GANs, VAEs)"),
    (r"gradient.descent|SGD|Adam|optim.*algorithm|convex|non.convex|multi.objective", "Optimization (Gradient Descent, Convex)"),
    (r"backpropagat|chain.rule|neural.network.train", "Neural Networks & Backpropagation"),
    (r"decision.tree|random.forest|XGBoost|ensemble|boosting", "Decision Trees & Ensemble Methods"),
    (r"causal.infer|counterfactual|causal", "Causal Inference"),
    (r"Bayes|posterior|prior|MCMC|probabilistic.model|Bayesian", "Bayesian Inference & Bayes' Theorem"),
    (r"hypothesis.test|p.value|confidence.interval|statistical.test", "Hypothesis Testing & Statistical Inference"),
    (r"PCA|dimensionality.reduc|UMAP|t-SNE|manifold.learn|embedding|latent.space|representation.learn|tensor.decompos", "Dimensionality Reduction & Embeddings"),
    (r"random.matri|spectral.theor", "Random Matrix Theory"),
    (r"computer.vision|image.process|video.*track|face.recogn|visual|scene.understand|image.*retriev|denoising", "Computer Vision"),
    (r"natural.language|NLP|text.analysis|topic.model|sentiment|parsing|machine.translat", "Natural Language Processing"),
    (r"robot|path.planning|autonomous|SLAM|manipulat|locomot|grasp", "Robotics & Autonomous Systems"),
    (r"cryptograph|security|malware|cyber|privacy|adversarial.*attack|adversarial.*robust", "Cryptography & Cybersecurity"),
    (r"distributed.system|fault.toleran|consensus|parallel.comput|MapReduce|cloud.comput", "Distributed & Parallel Computing"),
    (r"database|SQL|query|data.manage|storage|indexing", "Databases & Data Management"),
    (r"network.*cod|wireless|communication|5G|spectrum|antenna|cooperat.*commun", "Networks & Communication"),
    (r"interconnect|chip|VLSI|circuit|analog|FPGA|embedded|real.time|hardware|CPU|GPU|TPU|processor|architecture", "Computer Architecture & Hardware"),
    (r"compiler|formal.method|verif|model.check|type.system|logic.*program|program.analy|Petri.net", "Formal Methods & Programming Languages"),
    (r"software.engineer|model.driven|testing|DevOps", "Software Engineering"),
    (r"web.app|mobile.app|user.interface|HCI|human.computer|immersive|display|gesture|interact", "Human-Computer Interaction"),
    (r"computer.graphic|visualization|mesh|render|3D|CAD|computational.geometr", "Computer Graphics & Visualization"),
    (r"data.structure|algorithm|complexity|Big.O|sorting|graph.*algorithm|combinatori", "Algorithms & Data Structures"),
    (r"game.theory|auction|mechanism.design|strateg", "Game Theory & Mechanism Design"),
    (r"econometr|regression|panel.data|instrumental.variable|treatment.effect|wage|labor|employ|merger|competi|trade|tariff|fiscal|monetary|macro.*econ|micro.*econ|market|GDP|inflation|growth.*product|financial.market|banking|investment|crisis|asset.pric|portfolio", "Econometrics & Statistical Economics"),
    (r"experiment.*design|A/B.test|optimal.*design|design.of.experiment", "Experimental Design"),
    (r"statistical.*method|statistical.*model|regression|inference|estimat|distribut|likelihood|nonparametr", "Statistical Methods & Inference"),
    (r"stochastic|Markov|ergodic|martingale|Brownian", "Stochastic Processes"),
    (r"algebra|ring|module|group.theory|representation|Lie|commutative", "Abstract Algebra & Group Theory"),
    (r"number.theor|prime|diophantine|arithmetic|elliptic.curve", "Number Theory"),
    (r"topology|manifold|cohomol|homotop|homolog|fiber.bundle|knot", "Topology & Manifolds"),
    (r"algebraic.geometr|scheme|variety|sheaf|moduli", "Algebraic Geometry"),
    (r"differential.geometr|curvature|Riemann|Riemannian|geodesic", "Differential Geometry"),
    (r"harmonic.analys|Fourier|wavelet|signal.*proc", "Fourier Analysis & Signal Processing"),
    (r"point.process|geometric.inequal|functional.analys|operator.algebra", "Functional Analysis"),
    (r"mathematical.phys|integrab|exact.solut|quantum.*algebra|conformal.*field", "Mathematical Physics"),
    (r"dynamical.system|fractal|chaos|bifurcat|ergod", "Dynamical Systems"),
    (r"numer.*method|finite.element|PDE|partial.differential|ODE|numerical.*solv", "Numerical Methods & PDEs"),
    (r"graph.*theor|combinat|matroid|Ramsey|extremal", "Graph Theory & Combinatorics"),
    (r"deep.learn|neural.net|machine.learn|classification|feature.select|supervised|unsupervised|transfer.learn|few.shot", "Machine Learning"),
    (r"COVID|epidemic|pandemic|SIR.*model|epidemiolog.*model", "Epidemiological Modeling"),
    (r"teach|learn|education|pedagog|online.learn|MOOC|program.*educat", "CS Education"),
    (r"operations.research|supply.chain|schedul|logistics|queueing|inventory", "Operations Research"),
    (r"climate|energy|environment|carbon|sustainab|transport.*polic", "Computational Social Science"),
    (r"decision|behavioral.econ|prospect.theory|utility|choice|bounded.rational", "Decision Theory & Behavioral Economics"),
    (r"speech|dialogue|voice|ASR|TTS", "Natural Language Processing"),
    (r"anomaly.detect|outlier|fault.detect", "Machine Learning"),
    (r"explain.*AI|XAI|interpretab", "Machine Learning"),
    (r"sensor.network|target.track|data.fusion", "Networks & Communication"),
    (r"quantum.*cellular|quantum.*automat", "Quantum Computing"),
    (r"logic|reasoning|knowledge.represent|ontolog|planning", "Formal Methods & Programming Languages"),
    (r"AI.*game|game.*AI|Monte.Carlo.tree", "Reinforcement Learning"),
    (r"topolog.*data|persistent.homolog|TDA", "Dimensionality Reduction & Embeddings"),
    (r"seismol|earthquake|geolog|geochem|geophys", "Computational Social Science"),
    (r"comput.*phys|python.*phys|simulation.*phys", "Computational Physics & Simulation"),
    (r"math|theorem|proof|conjecture|lemma|cogniti.*math", "Mathematics"),
]

ALL_RULES = {
    "Biology": BIO_RULES,
    "Chemistry": CHEM_RULES,
    "Physics": PHYS_RULES,
    "Earth & Space": EARTH_RULES,
    "CS/AI/Stats": CS_RULES,
}


def remap_subcategory(category, old_sub, focus):
    """Given a category, old subcategory, and focus text, return a new subcategory."""
    # Combine old_sub and focus for keyword matching
    text = f"{old_sub} {focus}"
    rules = ALL_RULES.get(category, [])
    for pattern, new_sub in rules:
        if re.search(pattern, text, re.IGNORECASE):
            return new_sub
    # Fallback: return something reasonable per category
    fallbacks = {
        "Biology": "Molecular Biology & Biochemistry",
        "Chemistry": "General Chemistry",
        "Physics": "Physics",
        "Earth & Space": "Earth & Planetary Science",
        "CS/AI/Stats": "Mathematics",
    }
    return fallbacks.get(category, old_sub)


def should_recategorize(category, old_sub, focus):
    """Check if a tag should be moved to a different category entirely."""
    text = f"{old_sub} {focus}"

    # Network analysis in Physics -> CS
    if category == "Physics" and re.search(r"network.*analysis|complex.network|graph.*model", text, re.I):
        return "CS/AI/Stats"
    # Mathematical Physics -> might stay CS or Physics
    if category == "CS/AI/Stats" and re.search(r"superconducti|quantum.*many|condensed|magnetic", text, re.I):
        return "Physics"
    # Economics stuff that's really econ
    if category == "CS/AI/Stats" and re.search(r"^(Economics|Finance|General Economics|General Decision)", old_sub):
        return "CS/AI/Stats"  # Keep in CS/AI/Stats, just remap subcategory
    # Ecology in Biology -> Earth & Space
    if category == "Biology" and re.search(r"ecology|ecosystem|conservation|wildlife|species.distrib|remote.sens", text, re.I):
        return "Earth & Space"
    # Surgery/Orthopedics/Dentistry in Biology -> maybe remove or keep
    return None


def fix_tags_for_lab(lab):
    """Fix all tags for a single lab. Returns new tag list."""
    new_tags = []
    seen = set()

    for tag in lab.get("t", []):
        category = tag[0]
        old_sub = tag[1]
        focus = tag[2] if len(tag) > 2 else ""

        # Check if category should change
        new_cat = should_recategorize(category, old_sub, focus)
        if new_cat:
            category = new_cat

        # Get new subcategory
        new_sub = remap_subcategory(category, old_sub, focus)

        # Clean up focus: remove overly generic focus texts
        if focus and re.match(r"^(General|Various|Diverse|Miscellaneous|Multidisciplinary)", focus, re.I):
            focus = ""

        # Build new tag
        new_tag = [category, new_sub]
        if focus:
            new_tag.append(focus)

        # Deduplicate by (category, subcategory)
        key = (category, new_sub)
        if key not in seen:
            seen.add(key)
            new_tags.append(new_tag)

    return new_tags


def main():
    with open(INPUT_FILE) as f:
        labs = json.load(f)

    print(f"Processing {len(labs)} labs...")

    total_before = sum(len(lab.get("t", [])) for lab in labs)

    for lab in labs:
        lab["t"] = fix_tags_for_lab(lab)

    total_after = sum(len(lab.get("t", [])) for lab in labs)

    # Stats
    print(f"Tags before: {total_before}, after: {total_after}")

    # Show new subcategory distribution
    subcats = {}
    for lab in labs:
        for tag in lab.get("t", []):
            key = f"{tag[0]} | {tag[1]}"
            subcats[key] = subcats.get(key, 0) + 1

    print(f"\nUnique subcategories: {len(subcats)}")
    print("\nTop subcategories:")
    for k, v in sorted(subcats.items(), key=lambda x: -x[1])[:40]:
        print(f"  {v:4d}  {k}")

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(labs, f, separators=(",", ":"))

    import os
    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\nWrote {len(labs)} labs to {OUTPUT_FILE} ({size_kb:.0f}KB)")


if __name__ == "__main__":
    main()
