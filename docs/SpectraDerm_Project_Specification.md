# SpectraDerm — Project Specification

**Document status:** Technical source of truth for implementation  
**Project:** SpectraDerm  
**Primary development environment:** VS Code + Codex  
**Compute environment:** Google Colab / GPU when required  
**Data storage:** Google Drive / approved dataset repositories  
**Repository:** SpectraDerm

---

## 1. Project Overview

SpectraDerm is an AI-based skin monitoring and early-warning system centered on **RGB-to-spectral reconstruction, multimodal skin analysis, and evidence-grounded multi-agent reasoning**.

The system is intended to use conventional RGB facial/skin imagery to estimate additional spectral information and combine visual and spectral-derived information with evidence and structured reasoning to support skin monitoring.

The system is a **research/prototype decision-support system**, not a clinical diagnostic device.

A central scientific distinction must be preserved throughout implementation:

> Reconstructed spectral information is AI-estimated information inferred from RGB. It must not be described as directly measured hyperspectral, multispectral, or NIR data.

---

## 2. Project Goals

The implementation should support the following high-level goals:

1. Acquire and characterize suitable RGB and hyperspectral/spectral datasets.
2. Build reproducible preprocessing and data-loading pipelines.
3. Perform image quality assessment and skin/region segmentation or localization.
4. Develop and evaluate RGB-to-spectral reconstruction.
5. Perform multimodal analysis using RGB and reconstructed spectral information.
6. Incorporate evidence-grounded reasoning and retrieval where required.
7. Use multiple specialized AI agents where defined by the project architecture.
8. Produce interpretable monitoring/reporting outputs.
9. Integrate the components into a usable prototype.
10. Evaluate the system quantitatively and document limitations.

---

## 3. Project Scope

The project is organized into seven implementation phases.

### Phase 1 — Data

Modules:

- **C — Dataset Acquisition**
- **D — Dataset Analysis**
- **E — Data Preprocessing**

Required activities include:

- dataset acquisition/access
- dataset structure inspection
- dimensions and spectral bands
- RGB/spectral pairing
- subject information
- skin-tone diversity where available
- labels/annotations and metadata
- licensing
- missing/invalid data
- manifests
- resizing
- normalization
- alignment
- RGB extraction where applicable
- spectral normalization
- augmentation
- subject-aware train/validation/test splitting

### Phase 2 — Vision / Image Quality / Localization

Modules F–H are to cover the project's image-quality and visual-region processing requirements defined in the Module Plan.

Implementation should establish reliable input images and identify/localize relevant skin regions before downstream spectral and multimodal analysis.

### Phase 3 — RGB-to-Spectral Reconstruction

Modules I–K are to cover the reconstruction pipeline.

Core objective:

```text
RGB image
   ↓
RGB-to-spectral model
   ↓
estimated spectral representation
```

The reconstruction output must have a clearly defined spectral dimensionality and preprocessing convention.

The reconstruction model must be trained and evaluated against available measured spectral/hyperspectral ground truth.

### Phase 4 — Multimodal Analysis

Combine information from:

- original RGB imagery
- reconstructed spectral representation
- visual/region-level features
- relevant metadata where scientifically justified

The implementation should keep the modalities distinguishable so that ablation and modality-specific evaluation remain possible.

### Phase 5 — Evidence-Grounded Multi-Agent AI

The system should use specialized agents where appropriate rather than one unrestricted agent performing every task.

Agent responsibilities should be explicit, testable, and auditable.

Evidence-grounded outputs should distinguish:

- observed evidence
- model-derived features
- retrieved evidence
- reasoning/inference
- uncertainty
- final monitoring interpretation

### Phase 6 — System Integration

Integrate:

- data/preprocessing
- vision
- spectral reconstruction
- multimodal analysis
- evidence/retrieval
- agents
- reporting
- backend
- frontend

The integrated system should expose a consistent input/output contract between components.

### Phase 7 — Evaluation / Demonstration

Evaluate:

- reconstruction quality
- image/region processing performance
- multimodal performance
- robustness and limitations
- computational behavior
- system-level functionality
- interpretability/evidence traceability

The final demonstration must not imply clinical validation unless such validation has actually been performed.

---

## 4. Dataset Strategy

### 4.1 Hyper-Skin

**Role:** Primary dataset for RGB-to-spectral reconstruction.

Current Phase 1 findings:

- 306 RGB samples
- 306 VIS samples
- 306 matched RGB/VIS pairs
- 51 subjects
- 264 training samples / 44 subjects
- 18 validation samples / 3 subjects
- 24 test samples / 4 subjects
- VIS data contain 31 spectral bands
- inspected VIS files use MATLAB v7.3 / HDF5 format
- HDF5 dataset variable: `cube`
- original inspected VIS shape: `(31, 1024, 1024)`
- pipeline convention: `(1024, 1024, 31)`
- RGB sample format: 3-channel uint8
- RGB preprocessing: float32 scaled from `[0,255]` to `[0,1]`
- VIS values are converted to float32 while preserving the original scale
- preprocessing target size: `256 × 256`
- paired augmentation is used
- subject-aware splitting is used
- no subject overlap between train/validation/test

Important limitation:

- No wavelength metadata should be invented. If wavelength labels are required by a downstream component, they must be obtained from authoritative dataset documentation or metadata.

### 4.2 UMINHO-HSFD

**Role:** Secondary dataset for hyperspectral facial skin/spectral analysis and validation.

The official dataset documentation describes:

- 29 hyperspectral face images
- spectral reflectance from 400–720 nm
- 10 nm interval
- 33 wavelengths
- RGB JPG references rendered from hyperspectral reflectance
- RGB images are provided as visual references and are redacted for identity protection
- face metadata including sex, age, Fitzpatrick classification, von Luschan score, and number of discernible colors
- intrinsic facial features such as moles, freckles, scars and other visible characteristics
- documented image artifacts such as movement-related blur/green areas and unwanted hair
- artificial zero reflectance representing surrounding black background
- CC-BY 4.0 licensing

Current Phase 1 findings:

- 29 RGB files
- 29 reflectance MAT files
- 29 matched pairs
- no unmatched pairs
- sample reflectance shape: `(923, 618, 33)`
- MAT variable: `datao`
- reflectance dtype converted to float32
- inspected reflectance range: `0.0` to approximately `1.1102442`
- zero-valued background must not automatically be treated as missing data
- RGB and reflectance spatial dimensions match for the inspected pair
- preprocessing target size: `256 × 256`
- subject-aware split: 20 train / 4 validation / 5 test
- random seed: 42

Important scientific limitations:

- UMINHO-HSFD is not a disease/lesion classification dataset.
- It should primarily support spectral skin analysis and validation.
- Its RGB images are rendered from hyperspectral reflectance and therefore must not be treated as independently captured RGB measurements.
- Skin-tone groups are strongly imbalanced.
- The 20/4/5 split is a reproducible engineering split, not a statistically robust benchmark.

Dataset citation:

Gomes, Andreia E.; Linhares, Joao M. M.; Nascimento, Sergio M. C. (2024). *University of Minho Hyperspectral Faces Database: UMINHO-HSFD*. figshare. Collection.

---

## 5. Data and Storage Policy

Raw datasets must not be committed to Git.

### Keep in cloud storage

- Hyper-Skin archive/raw data
- UMINHO raw reflectance files
- large processed datasets
- model checkpoints
- experiment artifacts
- large generated outputs

### Keep in the repository

- source code
- configuration files
- manifests
- documentation
- reports
- tests
- reproducible notebooks where useful
- small metadata files

Dataset paths must be configurable. Never hard-code a developer-specific absolute path into reusable source code.

---

## 6. Phase 1 Data Contracts

### RGB

Standard internal representation:

```text
shape: H × W × 3
dtype: float32
range: approximately [0,1]
```

### Spectral / VIS

Standard internal representation:

```text
shape: H × W × B
dtype: float32
```

The number of bands is dataset-specific:

```text
Hyper-Skin: 31
UMINHO-HSFD: 33
```

Do not assume that reflectance values are always restricted to `[0,1]`.

### Paired transformations

Any geometric transformation applied to paired RGB and spectral data must use the same spatial transformation.

Examples:

- resize
- crop
- horizontal flip
- spatial augmentation

Augmentation must be applied to training data only unless a specific evaluation experiment requires otherwise.

---

## 7. Data Leakage Prevention

Subject identity must be respected wherever subject information is available.

The preferred principle is:

```text
subject → one split only
```

Do not randomly distribute images from the same subject across training and evaluation sets.

For datasets with very small or imbalanced subject groups, document the limitation rather than claiming statistical representativeness.

---

## 8. Preprocessing Principles

The preprocessing pipeline must be:

- deterministic where appropriate
- reproducible
- configurable
- testable
- shared between experiments
- independent of a single notebook runtime

Recommended flow:

```text
Raw dataset
   ↓
Load
   ↓
Validate
   ↓
Pair / identify subject
   ↓
Spatial preprocessing
   ↓
Normalize
   ↓
Optional training augmentation
   ↓
Model input
```

Preprocessing should not silently:

- clip scientifically meaningful spectral values
- convert background to missing values without justification
- alter spectral band ordering
- invent wavelengths
- introduce RGB/spectral misalignment

---

## 9. Phase 2 Vision Requirements

The vision pipeline should establish image quality and relevant skin-region information before high-level analysis.

It should support, as required by the Module Plan:

- input image quality assessment
- detection/handling of problematic images
- skin/face localization
- segmentation or region-of-interest extraction
- reproducible preprocessing
- visualization of intermediate outputs
- quantitative evaluation of segmentation/localization where ground truth is available
Status: IMPLEMENTED AND VALIDATED

Validation:
- Automated tests: 15 passed.
- Real Hyper-Skin RGB sample evaluated.
- Real UMINHO-HSFD RGB sample evaluated.
- Blur metric tested using controlled Gaussian degradation.
- Quality dimensions implemented: blur, exposure, clipping, lighting, resolution, and framing.
- Thresholds are provisional engineering thresholds and are not clinically validated.

The system should preserve the original image and keep derived masks/regions separately.

---

## 10. Phase 3 Reconstruction Requirements

The RGB-to-spectral model must learn:

```text
RGB → estimated spectral representation
```

The implementation must:

1. define the target spectral representation explicitly;
2. use measured spectral data as ground truth where available;
3. maintain train/validation/test separation;
4. evaluate reconstruction quantitatively;
5. provide visual/spectral comparisons;
6. preserve spectral band ordering;
7. record preprocessing and normalization parameters;
8. save model configuration and checkpoints separately from source code.

Evaluation should include appropriate reconstruction metrics selected for the actual target representation. Metrics must be reported with their definitions and units.

The system must not describe estimated spectra as measured spectra.

---

## 11. Multimodal Analysis Requirements

The multimodal layer should combine complementary information rather than simply concatenate arbitrary outputs.

At minimum, the architecture should preserve:

```text
RGB branch
   +
Spectral / reconstructed-spectral branch
   +
Relevant visual/region features
   ↓
Multimodal representation
   ↓
Analysis
```

The system should support ablation experiments such as:

- RGB only
- spectral/reconstructed spectral only
- RGB + spectral
- RGB + spectral + additional features

This allows the contribution of each modality to be evaluated.

---

## 12. Evidence-Grounded AI Requirements

Where an LLM or agent generates an interpretation:

- factual claims should be grounded in approved evidence;
- retrieved sources should be identifiable;
- evidence should be separated from model inference;
- uncertainty should be represented where appropriate;
- unsupported medical claims must not be generated as established facts.

A report should make it possible to trace:

```text
Input
  ↓
Model outputs
  ↓
Features / measurements
  ↓
Retrieved evidence
  ↓
Reasoning
  ↓
Final monitoring output
```

---

## 13. Multi-Agent Architecture

Agents should have narrow responsibilities and explicit interfaces.

Potential responsibilities include:

- image/quality analysis
- spectral analysis
- multimodal interpretation
- evidence retrieval
- evidence verification
- report generation

Exact agent decomposition should be finalized during implementation according to the Module Plan and validated experimentally.

Agents must not be allowed to silently fabricate measurements, citations, diagnoses, or model results.

---

## 14. Monitoring and Change Analysis

If longitudinal or comparative images are available, the system may calculate a change/anomaly score from relevant visual and spectral-derived features.

A change/anomaly score is **not equivalent to disease probability or diagnosis**.

The implementation must distinguish:

```text
observed change
≠
disease probability
≠
clinical diagnosis
```

Any threshold must be justified experimentally and clearly labeled as a research/prototype threshold.

---

## 15. Uncertainty and Safety

The system should communicate uncertainty rather than presenting model outputs as certainty.

Important categories include:

- input-quality uncertainty
- reconstruction uncertainty
- segmentation/localization uncertainty
- model confidence where appropriately calibrated
- evidence availability
- out-of-distribution concerns

If an input is unsuitable for reliable analysis, the system should be able to return an appropriate quality warning rather than forcing a confident interpretation.

---

## 16. Backend / Frontend Integration

The final application should separate:

### Backend

- data handling
- preprocessing
- model inference
- spectral reconstruction
- feature extraction
- agent orchestration
- evidence retrieval
- report generation

### Frontend

- image upload/input
- processing status
- image quality result
- segmentation/localization visualization
- spectral/reconstructed-spectral visualization
- analysis result
- evidence
- uncertainty/limitations
- final report

The UI must not imply clinical certainty.

---

## 17. Configuration

Dataset paths, model paths, preprocessing parameters, random seeds, model names, and runtime settings should be configurable.

Do not scatter constants throughout source files.

Recommended categories:

```text
config/
├── datasets
├── preprocessing
├── models
├── agents
└── application
```

Secrets/API keys must be stored outside source code, using environment variables or an equivalent secret mechanism.

---

## 18. Testing Requirements

Every major reusable component should have tests.

At minimum:

### Data

- file loading
- pairing
- dimensions
- dtype
- normalization
- subject split
- invalid-data detection

### Preprocessing

- deterministic transformations
- paired transformations
- output shapes
- value ranges

### Models

- input/output shapes
- checkpoint loading
- inference

### Agents

- structured input/output
- evidence handling
- failure handling

### Integration

- end-to-end smoke test
- representative sample inference

Tests must not require the entire raw dataset.

---

## 19. Reproducibility

Each experiment should record:

- dataset version/source
- manifest version
- split seed
- preprocessing configuration
- model configuration
- training parameters
- software environment
- evaluation metrics
- checkpoint identifier

Random seeds should be explicit for experiments where reproducibility is required.

---

## 20. Repository Structure

The intended repository structure is:

```text
SpectraDerm/
│
├── config/
│
├── data/
│   ├── external/
│   ├── interim/
│   ├── manifests/
│   │   ├── hyperskin_manifest.csv
│   │   └── uminho_hsfd_manifest.csv
│   ├── processed/
│   └── raw/
│
├── docs/
│   ├── datasets/
│   │   └── uminho_hsfd/
│   ├── dataset_acquisition.md
│   ├── Module Plan.docx
│   ├── SpectraDerm_Project_Proposal.docx
│   └── SpectraDerm_Project_Specification.md
│
├── frontend/
│
├── models/
│
├── notebooks/
│   └── SpectraDerm_Phase1_Data.ipynb
│
├── reports/
│   └── phase1/
│
├── src/
│   └── spectraderm/
│       ├── agents/
│       ├── backend/
│       ├── data/
│       ├── features/
│       ├── mcp/
│       ├── ml/
│       ├── monitoring/
│       ├── preprocessing/
│       ├── rag/
│       ├── reports/
│       ├── spectral/
│       └── vision/
│
├── tests/
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 21. Current Phase 1 Status

Phase 1 is complete for the currently characterized datasets.

### Hyper-Skin

- [x] acquisition/access
- [x] dataset inspection
- [x] RGB/VIS pairing
- [x] manifest
- [x] RGB loader
- [x] VIS loader
- [x] normalization
- [x] alignment check
- [x] resize
- [x] quality checks
- [x] paired augmentation
- [x] subject-aware split
- [x] final pipeline

### UMINHO-HSFD

- [x] collection/API inspection
- [x] documentation
- [x] sample inspection
- [x] RGB/reflectance pairing
- [x] manifest
- [x] RGB loader
- [x] reflectance loader
- [x] normalization
- [x] spatial correspondence check
- [x] resize
- [x] quality checks
- [x] paired augmentation
- [x] subject-aware split
- [x] final pipeline
- [x] Phase 1 report

---

## 22. Implementation Rules for Codex

Codex must follow these rules when modifying the project:

1. **Read this specification and the Module Plan before implementing a new module.**
2. Treat completed Phase 1 work as established unless a reproducible error is found.
3. Do not delete or rewrite working Phase 1 logic merely for stylistic reasons.
4. Do not add raw datasets to Git.
5. Do not hard-code local machine paths.
6. Do not invent dataset properties, wavelengths, labels, diagnoses, or clinical claims.
7. Do not claim that reconstructed spectra are measured spectra.
8. Do not claim UMINHO-HSFD is a disease/lesion dataset.
9. Do not treat UMINHO rendered RGB as an independently captured RGB modality.
10. Prevent subject leakage in every experiment.
11. Prefer small, testable modules over one large script.
12. Add tests for reusable functionality.
13. Keep configuration separate from implementation.
14. Preserve reproducibility.
15. Explain architectural changes before making destructive changes.
16. Do not introduce a new ML model solely because it is popular; justify model selection against the project's data and objectives.
17. Do not build the complete application before the underlying model/data interfaces are validated.
18. Keep experimental code separate from production inference code.
19. Never fabricate evidence, citations, measurements, or evaluation results.
20. When requirements are ambiguous, identify the ambiguity and use the project's source documents as the primary authority.

---

## 23. Definition of Done

The project is complete only when:

- all required phases/modules have an implemented counterpart;
- data pipelines are reproducible;
- reconstruction is quantitatively evaluated;
- multimodal analysis is evaluated;
- agent/evidence behavior is traceable;
- the integrated prototype works end-to-end;
- tests pass;
- important limitations are documented;
- no unsupported medical claims are made;
- results can be reproduced from documented configuration and dataset manifests.

---

## 24. Source-of-Truth Hierarchy

When sources disagree, use this order:

1. Actual dataset files and official dataset documentation
2. Approved project Module Plan
3. Approved project proposal
4. This technical specification
5. Implementation decisions documented during development
6. General engineering/model knowledge

Any material change to project scope or scientific assumptions should be documented rather than silently changing the specification.

---

## 25. Current Implementation Principle

SpectraDerm should be developed incrementally:

```text
Phase 1
Data + preprocessing
        ↓
Phase 2
Vision + image quality + localization
        ↓
Phase 3
RGB → spectral reconstruction
        ↓
Phase 4
Multimodal analysis
        ↓
Phase 5
Evidence + multi-agent reasoning
        ↓
Phase 6
Integration
        ↓
Phase 7
Evaluation + demonstration
```

Each phase must produce testable outputs before the next phase becomes dependent on it.
