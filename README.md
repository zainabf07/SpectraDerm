SpectraDerm 🩺🔬

AI-Based Early Warning & Skin Monitoring Using RGB-to-Spectral Reconstruction, Multimodal Analysis, and Evidence-Grounded Multi-Agent AI

SpectraDerm is an AI-powered skin monitoring prototype that uses ordinary RGB smartphone images to help users identify and monitor subtle changes in their skin over time.

Instead of requiring specialized multispectral or hyperspectral cameras, SpectraDerm uses an AI model to generate estimated spectral information from RGB images. This information is combined with conventional RGB features and a user's previous scans to identify unusual or changing patterns.

The system then uses RAG (Retrieval-Augmented Generation), specialized AI agents, and Model Context Protocol (MCP) tools to provide evidence-grounded explanations, safety checks, and appropriate next-step guidance.

«Important: SpectraDerm is a capstone prototype for skin monitoring and awareness. It is not a diagnostic medical device, does not diagnose skin diseases, and its estimated spectral output is not an actual multispectral or hyperspectral measurement.»

---

🌟 Key Features

📸 1. RGB Image Analysis

Users provide an ordinary RGB photograph of their skin.

The system performs:

- Image quality assessment
- Blur and exposure checking
- Skin-region detection
- Relevant region/lesion localization
- RGB feature extraction

🌈 2. AI Spectral Reconstruction

SpectraDerm reconstructs an AI-estimated spectral representation from the RGB image.

RGB Image
    ↓
Spectral Reconstruction Model
    ↓
AI-Estimated Spectral Image

The spectral representation is used as an additional source of model-derived information.

It must not be interpreted as an actual NIR, multispectral, or hyperspectral measurement.

---

🧬 3. Multimodal Feature Analysis

SpectraDerm combines information from multiple sources:

RGB Features
      +
Estimated Spectral Features
      +
Temporal Features
      ↓
Combined Feature Vector
      ↓
ML Analysis

RGB features may include:

- Color
- Texture
- Shape
- Local contrast
- Pigmentation-related features

Estimated spectral features may include:

- Band-wise intensity
- Spectral ratios
- Spectral differences
- Regional spectral statistics
- Spectral signatures

---

📊 4. Change / Anomaly Detection

The system generates a model-derived change/anomaly score representing how much the observed pattern differs from a reference pattern.

Example:

Stable
   ↓
Monitor
   ↓
Higher Change

A score such as:

Change / Anomaly Score: 72 / 100

does not represent disease probability.

It means that the observed pattern differs from the learned or personal reference pattern.

---

👤 5. Personal Skin Baseline

The first scan establishes a personal baseline.

First Scan
    ↓
RGB + Estimated Spectral Information
    ↓
Personal Baseline

Future scans are compared against this baseline because different people naturally have different skin characteristics.

Example:

Scan 1 → Baseline Established

Scan 2 → Compare with Baseline
          ↓
       Change Detected

Scan 3+ → Longitudinal Comparison
           ↓
        Trend Analysis

---

📈 6. Longitudinal Skin Monitoring

SpectraDerm stores scan history and compares later scans with previous observations.

Possible outputs include:

- Stable
- Changed
- Increasing Change

The interface can also display a difference map highlighting the region where a model-derived change was observed.

---

🧠 RAG-Based Medical Evidence

SpectraDerm uses a dermatology-focused knowledge base to ground AI explanations in retrieved evidence.

The knowledge base covers areas such as:

- General dermatology
- Skin pigmentation
- Melanin
- Hemoglobin/vascular characteristics
- Common skin conditions
- Warning signs
- When professional assessment may be appropriate

The retrieval pipeline follows:

Medical Documents
       ↓
     Clean
       ↓
     Chunk
       ↓
    Embed
       ↓
Vector Database
       ↓
   Retrieval
       ↓
Relevant Evidence
       ↓
      LLM
       ↓
Evidence-Grounded Explanation

This allows the system to answer questions such as:

«"Why was this flagged?"»

using retrieved supporting information rather than relying entirely on the language model's general knowledge.

---

🤖 Multi-Agent AI Architecture

SpectraDerm divides responsibilities between specialized AI agents.

Agent| Responsibility
👁️ Vision Agent| Interprets image analysis, spectral reconstruction, features and ML outputs
📈 Monitoring Agent| Compares scans, reads history and identifies trends
📚 Evidence Agent| Performs RAG retrieval and produces evidence-grounded explanations
🛡️ Safety Agent| Checks safety, claims and whether professional assessment should be suggested
👨‍⚕️ Referral Agent| Finds available dermatologists when professional assessment is appropriate
🛍️ Product Agent| Handles appropriate general skincare recommendations
🎯 Orchestrator Agent| Coordinates the overall workflow

The agent architecture is designed so that commercial product recommendations do not influence the underlying detection result.

---

🔌 MCP Integration

SpectraDerm uses Model Context Protocol (MCP) as a standardized tool layer between the AI agents and system capabilities.

Potential MCP tools include:

reconstruct_spectrum()
analyze_skin()
extract_features()
calculate_warning_score()
compare_scans()
retrieve_evidence()
get_skin_history()
find_dermatologists()
get_partner_products()
generate_report()

Conceptually:

                AI Agents
                    │
                    ▼
              MCP Server
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
     ML Tools    RAG Tools   External Tools
        │           │           │
        └───────────┼───────────┘
                    ▼
               Final Report

This separates the agent reasoning layer from the underlying tools and application services.

---

🔄 Complete System Workflow

The complete SpectraDerm workflow is:

                 RGB Image
                     │
                     ▼
             Image Quality Check
                     │
                     ▼
          Skin / Region Detection
                     │
                     ▼
          AI Spectral Reconstruction
                     │
            ┌────────┴────────┐
            ▼                 ▼
       RGB Features     Spectral Features
            │                 │
            └────────┬────────┘
                     ▼
              Classical ML
                     │
                     ▼
          Change / Anomaly Score
                     │
                     ▼
             Personal Baseline
                     │
                     ▼
            Temporal Analysis
                     │
                     ▼
               AI Agents
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Vision    Monitoring   Evidence
          │          │          │
          └──────────┼──────────┘
                     ▼
                Safety Agent
                  /     \
                 /       \
                ▼         ▼
           Product      Referral
                \         /
                 \       /
                  ▼     ▼
                MCP Layer
                     │
                     ▼
               Final Report

The proposed end-to-end flow is based on the project architecture: RGB image → quality check → region detection → spectral reconstruction → feature analysis → change scoring → personal baseline/history → agents → RAG/safety → next action → report.

---

📋 Final User Report

The final report brings together:

- Image analysis
- AI-estimated spectral analysis
- ML/change score
- Historical comparison
- RAG evidence
- Safety assessment
- Recommended next action

A typical result can communicate:

Monitoring Recommended

An unusual model-derived change was
detected in one region.

[Highlighted Region]

Why was this flagged?
↓
Evidence-grounded explanation

Next Action
↓
Continue monitoring
or
Consider professional assessment

Persistent or potentially concerning patterns can lead to a suggestion to consider professional assessment and, where appropriate, dermatologist referral.

---

🗂️ Dataset Strategy

The project proposal defines three dataset roles:

Dataset A — RGB-to-Spectral Reconstruction

Hyper-Skin

Used primarily for training and evaluating the RGB-to-spectral reconstruction component.

Dataset B — Spectral Skin Analysis

UMINHO-HSFD

Used for developing and evaluating spectral-based skin analysis.

Dataset C — Testing & Robustness

The proposal states that this dataset was under consideration and not yet finalized.

Dataset selection is intended to consider:

- Availability
- Licensing
- Image quality
- Spectral bands
- Labels
- Subject distribution
- Skin-tone diversity

---

🧪 Model Evaluation

SpectraDerm does not assume that adding estimated spectral information automatically improves performance.

The project compares:

RGB-only Model
       VS
RGB + Estimated Spectral Model

Possible baseline algorithms include:

- Random Forest
- XGBoost
- Logistic Regression

Spectral reconstruction is evaluated using metrics such as:

- MAE
- RMSE
- Spectral Angle / related spectral similarity metrics

The project also considers:

- Generalization
- Skin-tone diversity
- False positives
- False negatives

---

🖥️ Application Flow

The planned frontend follows:

Home
  ↓
Scan
  ↓
Analysis
  ↓
Result
  ↓
History
  ↓
AI Explanation
  ↓
Next Action

Home

SpectraDerm

[ Start Scan ]

[ My Skin History ]

Analysis

RGB
 ↓
Spectral Reconstruction
 ↓
Analysis

Result

🟡 Monitoring Recommended

Unusual change detected
in one region.

[Highlighted Region]

History

May ─ June ─ July ─ Aug
 ●      ●      ●      ●

Stable  Stable  Slight Change

AI Explanation

Why was this flagged?

↓
Evidence-grounded explanation

Next Action

Stable
  ↓
Continue monitoring

OR

Persistent / concerning change
  ↓
Consider professional assessment
  ↓
Find Dermatologist

---

🔐 Privacy & Security

SpectraDerm is designed with privacy-aware principles including:

- Pseudonymous user IDs
- Minimum-necessary data collection
- Access controls
- Secure storage
- Consent management
- Data deletion mechanisms

The project describes its approach as HIPAA-aware / HIPAA-inspired, rather than claiming HIPAA compliance. Actual compliance depends on deployment environment, organization, data flows, and jurisdiction.

---

⚠️ Limitations

SpectraDerm has important limitations:

1. Estimated spectral information is a model prediction, not an actual multispectral or hyperspectral measurement.
2. The change/anomaly score represents deviation from a reference pattern, not disease probability.
3. SpectraDerm does not diagnose skin diseases.
4. It does not replace a dermatologist.
5. A detected change is not guaranteed to be medically significant.
6. The prototype is not a clinically validated medical tool.
7. The project does not claim legal HIPAA compliance.

---

🛠️ Technology Stack

The proposed technology stack includes:

Area| Technology
Programming| Python
Deep Learning| PyTorch
Computer Vision| OpenCV / PyTorch
Spectral Reconstruction| HyperCNN / Pix2HS-style or suitable alternative
Machine Learning| XGBoost / Random Forest / Logistic Regression
Data Processing| NumPy / Pandas / scikit-learn
RAG| Sentence Transformers
Vector Database| FAISS / Chroma
Backend| FastAPI
AI Agents| LLM-based agent framework
Tool Integration| MCP
Frontend| Web application framework

The final technologies may be adjusted according to dataset compatibility, available resources, and capstone constraints.

---

📁 Project Architecture

A high-level project structure can follow:

SpectraDerm/
│
├── frontend/
│   ├── pages/
│   ├── components/
│   └── assets/
│
├── backend/
│   ├── api/
│   ├── models/
│   ├── services/
│   └── database/
│
├── spectral/
│   ├── preprocessing/
│   ├── reconstruction/
│   ├── validation/
│   └── visualization/
│
├── ml/
│   ├── feature_extraction/
│   ├── baseline_model/
│   ├── spectral_model/
│   └── anomaly_detection/
│
├── rag/
│   ├── documents/
│   ├── processing/
│   ├── embeddings/
│   └── retrieval/
│
├── agents/
│   ├── vision_agent/
│   ├── monitoring_agent/
│   ├── evidence_agent/
│   ├── safety_agent/
│   ├── referral_agent/
│   ├── product_agent/
│   └── orchestrator/
│
├── mcp/
│   ├── server/
│   └── tools/
│
├── tests/
│
└── README.md

---

🚀 Development Roadmap

The project follows a dependency-driven development order:

Data
  ↓
Spectral Reconstruction
  ↓
Feature Extraction
  ↓
Classical ML
  ↓
Baseline / Change Detection
  ↓
RAG
  ↓
AI Agents
  ↓
MCP
  ↓
Backend
  ↓
Frontend
  ↓
Integration
  ↓
Testing
  ↓
Demo

The module plan emphasizes this dependency order so that components are integrated progressively rather than developed as disconnected features.

---

👥 Team

SpectraDerm is a 3-person AI/ML Bootcamp capstone project.

Team Member| Primary Focus
Zainab Fatima| Data, Computer Vision & Spectral AI
Ayesha Noor| Machine Learning, RAG & AI Agents
Javaria Akbar| Backend, Frontend, Privacy & Testing

The responsibilities cover the complete pipeline from data and spectral reconstruction through ML, RAG, agents, MCP, application development, privacy, testing, and integration.

---

🎯 Demo Story

The intended final demonstration follows one user's journey rather than showing isolated technical components:

1. User takes/uploads a skin photo
                ↓
2. SpectraDerm performs image analysis
                ↓
3. AI-estimated spectral representation appears
                ↓
4. System identifies a model-derived change
                ↓
5. Baseline vs current scan is shown
                ↓
6. User asks "Why was this flagged?"
                ↓
7. Evidence Agent retrieves supporting information
                ↓
8. Safety Agent evaluates the appropriate next step
                ↓
9. Referral Agent can surface dermatologists
                ↓
10. Final report is generated

This demonstrates how computer vision, spectral AI, ML, temporal monitoring, RAG, agents, MCP, and the application layer work together as one system.

---

📌 Project Status

SpectraDerm is being developed as an AI/ML Bootcamp capstone prototype demonstrating the integration of:

- Computer Vision
- RGB-to-Spectral Reconstruction
- Multimodal Feature Engineering
- Classical Machine Learning
- Change Detection
- Personal Baseline Monitoring
- RAG
- Multi-Agent AI
- MCP
- Backend APIs
- Frontend Application
- Privacy-Aware Design

---

⚕️ Disclaimer

SpectraDerm is intended for monitoring and awareness, not diagnosis.

The system's AI-estimated spectral information and change/anomaly scores are model-derived outputs. They should not be interpreted as clinical measurements or definitive evidence of a medical condition.

Users should seek appropriate professional medical advice when they have concerns about persistent or concerning skin changes.

---

📜 License

Add the project's applicable license here, for example:

MIT License

if the project is ultimately released under MIT.

---

⭐ Acknowledgement

SpectraDerm was developed as an AI/ML Bootcamp capstone demonstrating how computer vision, spectral reconstruction, machine learning, retrieval-augmented generation, multi-agent AI, and MCP can be combined into an end-to-end skin monitoring prototype.