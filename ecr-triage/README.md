# eCR-Triage: LLM-Assisted Electronic Case Report Prioritization

> **HL7 FHIR DevDays 2026 — Student Track Project**

## Overview

Public health departments receive thousands of electronic initial case reports (eICRs) weekly and triage them manually. **eCR-Triage** is a SMART on FHIR client that ingests eICR Bundles, uses an LLM to generate ranked triage summaries grounded in FHIR resource references, and writes prioritization decisions back as `Flag` and `Task` resources — keeping humans in the loop.

## Problem Statement

Case investigators at state and local public health agencies spend significant time reviewing incoming electronic case reports to determine which require immediate follow-up (e.g., measles exposure in a daycare worker) versus routine processing. This manual triage creates bottlenecks during outbreaks and delays response times.

## Solution Architecture

```
Synthea (synthetic data) → HAPI FHIR Server → SMART on FHIR Client
                                                     │
                                            ┌────────┴────────┐
                                            │  LLM Triage     │
                                            │  Engine          │
                                            └────────┬────────┘
                                                     │
                                            Flag / Task write-back
```

### FHIR Resources Used

| Resource | Role |
|----------|------|
| `Bundle` | eICR composition container |
| `Patient` | Demographics, age, location |
| `Condition` | Reportable condition (trigger code) |
| `Encounter` | Care setting, timing |
| `Observation` | Lab results, vitals |
| `Flag` | Triage priority output (write-back) |
| `Task` | Investigation assignment (write-back) |

## Tech Stack

- **FHIR Server**: HAPI FHIR (public test server)
- **Synthetic Data**: Synthea patient generator
- **Client**: React + fhirclient.js (SMART on FHIR)
- **LLM Engine**: Python (LangChain / Anthropic SDK)
- **Data Processing**: pandas, fhirpy
- **Visualization**: Jupyter notebooks for EDA

## Project Structure

```
ecr-triage/
├── README.md
├── LICENSE
├── requirements.txt
├── setup.py
├── .gitignore
├── .env.example
├── configs/
│   └── fhir_server.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   └── synthea/
├── docs/
│   ├── architecture.md
│   └── fhir_data_model.md
├── models/
├── notebooks/
│   ├── 01_synthea_exploration.ipynb
│   ├── 02_fhir_bundle_parsing.ipynb
│   └── 03_triage_prototype.ipynb
├── src/
│   ├── __init__.py
│   ├── fhir_client.py
│   ├── bundle_parser.py
│   ├── triage_engine.py
│   ├── writeback.py
│   └── utils.py
└── tests/
    ├── __init__.py
    ├── test_bundle_parser.py
    └── test_triage_engine.py
```

## Getting Started

### Prerequisites

- Python 3.10+
- A running FHIR server (or use the public HAPI test server)
- An LLM API key (Anthropic)

### Installation

```bash
git clone https://github.com/kc717/ecr-triage.git
cd ecr-triage
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Add your API keys
```

### Quick Start

```bash
# 1. Generate synthetic data
cd data/synthea
# Follow Synthea instructions to generate FHIR bundles

# 2. Explore the data
jupyter notebook notebooks/01_synthea_exploration.ipynb

# 3. Run triage pipeline
python -m src.triage_engine
```

## Alignment

- **CDC Data Modernization Initiative (DMI)**: Supports modernized surveillance workflows
- **eCR Now**: Leverages the electronic case reporting pipeline architecture
- **SMART on FHIR**: Standards-based app launch and authorization
- **US Core / eICR IG**: Profiles for interoperability compliance

## Team

| Name | Role | University |
|------|------|-----------|
| Kevin Chen | Lead Developer | Indiana University Indianapolis |
| TBD | | |
| TBD | | |

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

- HL7 FHIR DevDays organizers
- HAPI FHIR community
- Synthea team at MITRE
