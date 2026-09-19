# SpectraDerm
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![scikit--learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![MCP](https://img.shields.io/badge/MCP-Tool%20Integration-purple)](https://modelcontextprotocol.io/)
[![RAG](https://img.shields.io/badge/RAG-Evidence%20Grounded-orange)](#-retrieval-augmented-generation-rag)
[![Status](https://img.shields.io/badge/Status-Capstone%20Prototype-yellow)](#-limitations)

### AI-Based Early Warning and Skin Monitoring Using RGB-to-Spectral Reconstruction, Multimodal Analysis, and Evidence-Grounded Multi-Agent AI

## 🎥 Demo Video

See SpectraDerm in action — from **RGB image upload and AI-estimated spectral reconstruction** to **skin analysis, change detection, RAG-based explanation, safety assessment, and the final monitoring report**.



SpectraDerm is an AI-powered skin monitoring prototype that uses ordinary RGB images to help users observe subtle changes in their skin over time.

Instead of requiring specialized multispectral or hyperspectral imaging hardware, SpectraDerm uses AI to generate an **estimated spectral representation** from an RGB image. The system combines RGB features, estimated spectral features, scan history, and personal baseline information to identify model-derived changes or anomalies.

When a change is detected, SpectraDerm uses **Retrieval-Augmented Generation (RAG)** and specialized AI agents to provide evidence-grounded explanations, perform safety checks, and suggest an appropriate next step.

> **Important:** SpectraDerm is a skin monitoring and awareness prototype. It does **not** diagnose skin diseases, provide a disease probability, or replace a dermatologist. Its spectral output is AI-estimated rather than an actual multispectral/hyperspectral measurement.

---

## ✨ Key Features

* 📷 **RGB Image Analysis**

  * Upload/capture ordinary skin images.
  * Perform image quality assessment before analysis.

* 🔍 **Skin & Region Detection**

  * Identify relevant skin regions.
  * Localize areas that can be monitored across scans.

* 🌈 **RGB-to-Spectral Reconstruction**

  * Generate AI-estimated spectral information from RGB images.
  * Visualize the reconstructed spectral representation.

* 🧬 **Multimodal Feature Extraction**

  * RGB color, texture, shape and related features.
  * Estimated spectral features.
  * Temporal/history-based features.

* 🤖 **Machine Learning Analysis**

  * Analyze combined feature representations.
  * Generate a model-derived change/anomaly score.

* 👤 **Personal Baseline**

  * The first scan establishes the user's personal reference.
  * Later scans are compared against previous/baseline scans.

* 📈 **Longitudinal Monitoring**

  * Track changes across multiple scans.
  * Visualize stable, changed, or increasing-change patterns.

* 📚 **RAG-Based Evidence**

  * Retrieve relevant dermatology information from a curated knowledge base.
  * Ground explanations in retrieved evidence rather than relying only on model-generated information.

* 🧠 **Multi-Agent AI**

  * Vision Agent
  * Monitoring Agent
  * Evidence Agent
  * Safety Agent
  * Product Agent
  * Referral Agent
  * Orchestrator Agent

* 🔌 **Model Context Protocol (MCP)**

  * Provides a standardized tool layer for the agents.
  * Exposes core analysis, retrieval, history, referral, and reporting capabilities.

* 👨‍⚕️ **Dermatologist Referral**

  * Supports professional-assessment referral when the safety workflow indicates it may be appropriate.

* 🧴 **General Skincare Guidance**

  * Provides appropriate general skincare/product-category guidance.
  * Product recommendations do not influence the underlying ML detection result.

* 📄 **Structured Final Report**

  * Combines image analysis, spectral analysis, ML findings, historical change, evidence, safety assessment, and recommended action.

The project's planned user journey is **Home → Scan → Analysis → Result → History → Explanation → Next Action**.

---

## 🏗️ System Architecture

```text
                         SPECTRADERM
                              │
                              ▼
                       📷 RGB IMAGE
                              │
                              ▼
                    Image Quality Check
                              │
                              ▼
                    Skin / Region Detection
                              │
                              ▼
                 RGB-to-Spectral Reconstruction
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
           RGB Features              Spectral Features
                 │                         │
                 └────────────┬────────────┘
                              ▼
                       Feature Engine
                              │
                              ▼
                       Machine Learning
                              │
                              ▼
                    Change / Anomaly Score
                              │
                              ▼
                    Personal Baseline
                              │
                              ▼
                    Temporal Comparison
                              │
                              ▼
                       Agent System
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
           Vision        Monitoring        Evidence
           Agent            Agent            Agent
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                         Safety Agent
                          /        \
                         /          \
                        ▼            ▼
                  Product Agent   Referral Agent
                         \          /
                          \        /
                           ▼      ▼
                         MCP SERVER
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
             ML Tools      RAG Tools    External Tools
                │             │             │
                └─────────────┼─────────────┘
                              ▼
                       FINAL REPORT
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
              Analysis     History       Action
```

This architecture follows the project's module plan and integrates computer vision, spectral AI, classical ML, temporal monitoring, RAG, agents, MCP, and reporting into one end-to-end workflow.

---

## 🔄 End-to-End Workflow

```text
RGB Image
   ↓
Image Quality Assessment
   ↓
Skin / Region Detection
   ↓
AI-Estimated Spectral Reconstruction
   ↓
RGB + Spectral Feature Extraction
   ↓
ML Analysis
   ↓
Change / Anomaly Score
   ↓
Personal Baseline & Scan History
   ↓
Longitudinal Comparison
   ↓
Vision / Monitoring / Evidence Agents
   ↓
RAG Evidence Retrieval
   ↓
Safety Assessment
   ↓
Referral / Product Guidance
   ↓
Final Structured Report
```

---

## 🌈 Spectral Reconstruction

SpectraDerm converts an ordinary RGB image into an **AI-estimated spectral representation**.

```text
RGB Image
H × W × 3
      │
      ▼
Spectral Reconstruction Model
      │
      ▼
Estimated Spectral Image
H × W × N
```

The reconstruction is used to obtain additional information that can be combined with conventional RGB features.

The system explicitly labels this output as **AI-estimated spectral information** rather than claiming that it is an actual multispectral or hyperspectral measurement.

---

## 🧬 Feature Engineering

SpectraDerm combines multiple types of information:

### RGB Features

Examples include:

* Color statistics
* Texture
* Shape
* Local contrast
* Pigmentation-related features

### Spectral Features

Examples include:

* Band-wise intensity
* Spectral ratios
* Spectral differences
* Regional spectral statistics
* Spectral signatures

### Temporal Features

Historical scan information is incorporated to support longitudinal monitoring.

The combined representation is then passed to the downstream ML analysis pipeline.

---

## 🤖 Machine Learning & Change Detection

SpectraDerm uses engineered image/spectral features for downstream machine-learning analysis.

The project includes an RGB baseline and an RGB + estimated-spectral representation to investigate whether the additional estimated spectral information provides useful signal.

The resulting value is a **change/anomaly score**, not a disease probability.

For example:

```text
Stable
   ↓
Monitor
   ↓
Higher Change
```

A score such as:

```text
Change / Anomaly Score: 72 / 100
```

means that the observed pattern differs from the learned/reference pattern. It should **not** be interpreted as a 72% probability of disease.

---

## 👤 Personal Baseline & Longitudinal Monitoring

Every user's skin can have different normal characteristics, so SpectraDerm establishes a personal reference.

### First Scan

```text
First Scan
    ↓
RGB + Estimated Spectrum
    ↓
Personal Baseline
```

### Subsequent Scans

```text
Current Scan
     +
Personal Baseline
     ↓
Difference Analysis
     ↓
Stable / Changed / Increasing Change
```

The system can then visualize how the monitored region changes over time.

The project workflow establishes the first scan as the baseline; later scans can be compared longitudinally. A trend visualization becomes more meaningful once multiple comparisons are available.

---

## 📚 Retrieval-Augmented Generation (RAG)

SpectraDerm uses a dermatology-focused knowledge base to support evidence-grounded explanations.

The knowledge base covers topics such as:

* General dermatology
* Skin pigmentation
* Melanin
* Common skin conditions
* Warning signs
* Situations where professional assessment may be appropriate

### RAG Pipeline

```text
Knowledge Documents
       ↓
Cleaning
       ↓
Chunking
       ↓
Embedding
       ↓
Local Vector Representation
       ↓
Semantic Retrieval
       ↓
Relevant Evidence
       ↓
Evidence-Grounded Explanation
```

The RAG component is used when the user asks questions such as:

> **"Why was this flagged?"**

The system retrieves relevant evidence and uses it to ground the explanation.

---

## 🧠 Multi-Agent Architecture

SpectraDerm separates responsibilities across specialized agents.

| Agent                  | Responsibility                                            |
| ---------------------- | --------------------------------------------------------- |
| **Vision Agent**       | Interprets image, spectral, feature, and ML outputs       |
| **Monitoring Agent**   | Handles scan history, comparisons, and trends             |
| **Evidence Agent**     | Performs RAG retrieval and evidence-grounded explanations |
| **Safety Agent**       | Applies safety checks and referral logic                  |
| **Product Agent**      | Handles appropriate skincare/product-category guidance    |
| **Referral Agent**     | Helps surface dermatologist options                       |
| **Orchestrator Agent** | Coordinates the overall workflow                          |

The agents are connected to the underlying application capabilities through MCP.

---

## 🔌 MCP Integration

SpectraDerm uses **Model Context Protocol (MCP)** as the tool/integration layer.

The MCP server exposes tools for the agents, including:

```text
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
```

This allows the agent system to interact with the core SpectraDerm capabilities in a structured way.

---

## 📄 Final Report

The final report combines:

```text
Image Analysis
      +
Spectral Analysis
      +
ML Score
      +
Historical Change
      +
RAG Evidence
      +
Safety Assessment
      +
Recommended Action
      ↓
Final SpectraDerm Report
```

The goal is to present the result as a structured monitoring report rather than simply displaying a numerical score.

---

## 🖥️ Application Flow

```text
Home
  ↓
Start Scan
  ↓
Upload / Capture Image
  ↓
Analysis
  ↓
Spectral Reconstruction
  ↓
Skin Analysis
  ↓
Result
  ↓
Highlighted Region
  ↓
Change / Monitoring Status
  ↓
Why Was This Flagged?
  ↓
Evidence-Grounded Explanation
  ↓
Next Action
  ├── Continue Monitoring
  ├── Consider Professional Assessment
  └── Find Dermatologist
```

---

## 🛠️ Technology Stack

### Frontend

* React
* React DOM
* JavaScript / TypeScript
* Vite

### Backend

* Python
* FastAPI
* Uvicorn
* Pydantic
* python-multipart

### Computer Vision & Image Processing

* OpenCV
* Pillow
* NumPy

### Deep Learning / Spectral AI

* PyTorch
* MST++ / MST-Plus-Plus
* Einops

### Data & Scientific Computing

* Pandas
* NumPy
* SciPy
* h5py / HDF5

### Machine Learning

* scikit-learn
* Random Forest
* Custom feature-engineering pipelines

### RAG

* FastEmbed
* `BAAI/bge-small-en-v1.5`
* 384-dimensional embeddings
* Local NumPy embedding matrix
* Cosine-similarity retrieval

### Agents & Tool Integration

* Custom Python agent architecture
* Official Python MCP SDK

### Storage

* Local filesystem-backed JSON metadata
* Managed image artifacts
* Local NumPy embedding storage for RAG

### Testing

* Pytest
* Vitest
* React Testing Library

### External Integration

* HTTPX
* Google Places-oriented dermatologist referral provider

---

## 📂 Project Structure

```text
SpectraDerm/
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── agents/
│   ├── api/
│   ├── ml/
│   ├── rag/
│   ├── mcp/
│   ├── storage/
│   ├── reporting/
│   └── tests/
│
├── models/
│   └── spectral/
│
├── data/
│   └── knowledge/
│
├── notebooks/
│
├── tests/
│
├── .env.example
├── requirements.txt
└── README.md
```

> The exact directory structure may vary depending on the current local project organization.

---

## ⚙️ Environment Variables

Create a `.env` file in the backend/project environment and configure the required services.

Example:

```env
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

Additional environment variables can be configured according to the backend deployment and enabled integrations.

**Never commit API keys or other secrets to Git.**

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd SpectraDerm
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows**

```bash
.venv\Scripts\activate
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

### 3. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Configure environment variables

Create `.env` using the project's environment configuration requirements.

### 6. Start the backend

```bash
uvicorn backend.main:app --reload
```

### 7. Start the frontend

```bash
cd frontend
npm run dev
```

The frontend will then be available through the Vite development server.

---

## 🧪 Testing

SpectraDerm uses testing at multiple levels.

### Backend

```bash
pytest
```

### Frontend

```bash
npm test
```

Testing covers areas such as:

* Image-processing behavior
* ML functionality
* RAG retrieval
* Agent behavior
* Safety logic
* MCP tools
* Referral workflow
* Frontend components
* End-to-end integration

The project plan specifically identifies ML, agent, MCP, and complete end-to-end testing as important validation stages.

---

## 🔐 Privacy & Safety

Because SpectraDerm processes skin images, privacy and responsible-use considerations are built into the design.

The system is designed around:

* Pseudonymous user IDs
* Minimum-necessary information
* Access controls
* Secure storage
* Consent handling
* Data deletion
* Safety checks before recommendations/referrals

The project is **HIPAA-aware / HIPAA-inspired**, but it does **not claim legal HIPAA compliance**. Actual compliance depends on the organization, deployment environment, data flows, and applicable jurisdiction.

---

## ⚠️ Limitations

SpectraDerm has several important limitations:

1. **Estimated spectral information**

   * The reconstructed spectrum is a model prediction, not a physical multispectral/hyperspectral measurement.

2. **Not a diagnostic system**

   * SpectraDerm does not diagnose skin diseases.

3. **Change score is not disease probability**

   * A high score indicates deviation from a reference pattern, not the probability of having a disease.

4. **Medical significance cannot be guaranteed**

   * A detected change may or may not be medically significant.

5. **Prototype status**

   * SpectraDerm is a capstone prototype and is not a validated clinical device.

6. **Professional assessment**

   * Concerning or persistent changes may warrant professional assessment rather than relying on the system alone.

These limitations are explicitly reflected in the project's proposal and module plan.

---

## 🎯 Project Goals

SpectraDerm demonstrates how several AI technologies can be integrated into one practical application:

```text
Computer Vision
       +
Spectral AI
       +
Feature Engineering
       +
Machine Learning
       +
Longitudinal Monitoring
       +
RAG
       +
Multi-Agent AI
       +
MCP
       +
FastAPI
       +
React
       ↓
SpectraDerm
```

The objective is not to replace dermatologists, but to provide an accessible **monitoring and awareness workflow** that can help users observe changes and understand why the system flagged a particular pattern.

---

## 👥 Team

**SpectraDerm — AI Bootcamp Capstone**

* **Zainab Fatima** — Data, Computer Vision & Spectral AI
* **Ayesha Noor** — Machine Learning, RAG & AI Agents
* **Javaria Akbar** — Backend, Frontend, Privacy & Testing

The project was developed as a collaborative end-to-end AI/ML capstone.

---

## 📌 Disclaimer

SpectraDerm is an educational AI/ML capstone prototype intended for skin monitoring and awareness.

It is **not medical advice**, a medical diagnosis system, or a replacement for professional dermatological assessment.

If a skin change is persistent, concerning, rapidly changing, painful, bleeding, or otherwise worrying, users should seek appropriate professional medical advice.

---

## 📜 License

Add the project's applicable license here.

```text
Copyright © 2026 SpectraDerm Team
```

---

## ⭐ Project Summary

> **SpectraDerm turns an ordinary RGB skin image into an AI-assisted monitoring workflow by combining estimated spectral information, multimodal feature analysis, personal baselines, longitudinal comparison, evidence-grounded RAG, multi-agent AI, and MCP into a single application.**
