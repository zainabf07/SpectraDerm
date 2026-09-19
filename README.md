# SpectraDerm

SpectraDerm is a capstone prototype for research-oriented skin monitoring from ordinary RGB images. It is not a medical device and does not diagnose disease.

The planned system will assess image quality, work with relevant skin regions, generate **AI-estimated spectral information** from RGB images, compare feature approaches, track change against a personal baseline, retrieve dermatology evidence, and produce an evidence-grounded report. Any estimated spectral output is predicted information, not a hyperspectral or multispectral measurement. Change or anomaly scores are not disease probabilities.

## Current phase

This repository currently contains scaffolding only. It contains no datasets, trained models, clinical results, diagnoses, or product recommendations.

## Layout

```text
src/spectraderm/   Python package and future pipeline modules
data/              Local raw, interim, processed, and external data locations
models/            Local model artifacts (ignored by Git)
notebooks/         Exploratory work
tests/             Automated checks
docs/              Project documentation
frontend/          Reserved for a future UI
config/            Example configuration assets
```

## Setup

Python 3.10+ (tested on 3.14) and Node 18+. The commands use `npm.cmd` and the
venv's `python.exe` directly so they work even when PowerShell blocks `.ps1`
scripts (the default execution policy on many Windows machines).

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python -m pip install -r requirements.txt scikit-learn
.\.venv\Scripts\python -m pip install -e . --no-deps
Copy-Item .env.example .env   # then set SPECTRADERM_MSTPP_CHECKPOINT=models/mstpp_hyperskin_vis_best_10pairs.pth
cd frontend; npm.cmd install; cd ..
```

## Running the app

Two terminals, both from the repository root:

```powershell
.\.venv\Scripts\python -m uvicorn spectraderm.api.app:app --port 8000
```

```powershell
cd frontend; npm.cmd run dev
```

Open http://localhost:5173. The first analysis downloads the FastEmbed model
(~65 MB) into `models/fastembed_cache` and takes a few extra seconds.

Users, scans, images, feature snapshots and change records persist under
`.spectraderm-api-storage/` (relative to the repository, whichever directory
the server is started from). A change score needs 4 earlier observations of the
same user; a professional-assessment suggestion needs persistent change across
observations plus retrieved evidence that supports it.

## Tests

```powershell
.\.venv\Scripts\python -m pytest
cd frontend; npm.cmd test
```

The test suite never calls OpenAI or Google Places, even if keys are in `.env`.

## Configuration

Use `spectraderm.config.get_settings()` to access project, data, model, and dataset-root paths. The settings default to directories in this repository and may be overridden with the variables in `.env.example`. Set `SPECTRADERM_HYPERSKIN_ROOT` and `SPECTRADERM_UMINHO_HSFD_ROOT` to local or mounted raw-data locations; application code should use those settings instead of hard-coded paths.

## Safety boundary

Future features must preserve the prototype's safety boundary: no disease diagnosis, no disease-probability framing for change scores, clear AI-estimated spectral terminology, evidence-based escalation to professional assessment where appropriate, and separation of general product categories from ML outputs.
