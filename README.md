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

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m unittest discover -s tests -v
```

`pytest` is also available after installing `requirements.txt`:

```powershell
python -m pytest
```

## Configuration

Use `spectraderm.config.get_settings()` to access project, data, model, and dataset-root paths. The settings default to directories in this repository and may be overridden with the variables in `.env.example`. Set `SPECTRADERM_HYPERSKIN_ROOT` and `SPECTRADERM_UMINHO_HSFD_ROOT` to local or mounted raw-data locations; application code should use those settings instead of hard-coded paths.

## Safety boundary

Future features must preserve the prototype's safety boundary: no disease diagnosis, no disease-probability framing for change scores, clear AI-estimated spectral terminology, evidence-based escalation to professional assessment where appropriate, and separation of general product categories from ML outputs.
