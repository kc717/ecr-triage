# eCR-Triage: LLM-Assisted Electronic Case Report Prioritization

> **HL7 FHIR DevDays 2026 — Student Track Project**

## Overview

Public health departments receive thousands of electronic initial case reports (eICRs) weekly and triage them manually. eCR-Triage is a SMART on FHIR client that ingests eICR Bundles, uses an LLM to generate ranked triage summaries grounded in FHIR resource references, and writes prioritization decisions back as **Flag** and **Task** resources — keeping humans in the loop.

The tool sits **post-RCKMS, pre-investigator** in the eCR pipeline (EHR → eCR Now → AIMS → RCKMS → DOH). It does not determine reportability (RCKMS does that upstream); it orders the investigator's queue among already-reportable cases.

## Problem Statement

Case investigators at state and local public health agencies spend significant time reviewing incoming electronic case reports to determine which require immediate follow-up (e.g., measles exposure in a daycare worker) versus routine processing. This manual triage creates bottlenecks during outbreaks and delays response times.

## Solution Architecture

```
Test Bundles / Synthea (synthetic data) → HAPI FHIR Server (local, Docker)
                                                     │
                                            ┌────────┴────────┐
                                            │  LLM Triage     │
                                            │  Engine (CSTE   │
                                            │  tier rubric)   │
                                            └────────┬────────┘
                                                     │
                                            Flag / Task write-back
```

### FHIR Resources Used

| Resource | Role |
|----------|------|
| Bundle | eICR composition container |
| Patient | Demographics, age, location (read) |
| Condition | Reportable condition / trigger code (read) |
| Encounter | Care setting, timing (read) |
| Observation | Lab results, vitals (read) |
| Flag | Triage priority output (write-back) |
| Task | Investigation assignment (write-back) |

## Triage Logic

Cases are assigned to a tier based on the **CSTE/CDC 2025 Nationally Notifiable Conditions** notification-timeliness categories:

| Tier | Meaning |
|------|---------|
| `4-hour` | Immediately notifiable, extremely urgent (e.g. anthrax w/ unrecognized source, smallpox) |
| `24-hour` | Immediately notifiable, urgent (e.g. measles, diphtheria, novel influenza A) |
| `7-day` | Routinely notifiable (the large majority — e.g. hepatitis, TB, STIs) |
| `non-notifiable` | Not a notifiable condition → flagged for human review, not triaged |

Within a tier, an `urgency_score` (1–10) breaks ties so investigators can prioritize the routine queue. The tier always takes precedence over the score. See `cste_tiers.md` for the full tier reference and source citation.

> The within-tier scoring factors are currently provisional and being grounded in published literature on case-investigation prioritization.

## Tech Stack

- **FHIR Server:** HAPI FHIR, run **locally via Docker**
- **Synthetic Data:** Synthea patient generator + hand-crafted test bundles
- **LLM Engine:** Python, **Anthropic SDK** (Claude), structured prompt + CSTE rubric — no fine-tuning, no agent framework
- **Data Processing:** pandas, fhirpy
- **Visualization:** Jupyter notebooks for EDA

## Project Structure

```
ecr-triage/
├── README.md
├── LICENSE
├── requirements.txt
├── setup.py
├── .gitignore
├── .env.example
├── docker-compose.yml          # local HAPI FHIR server
├── cste_tiers.md               # CSTE tier reference (citable source)
├── configs/
│   └── fhir_server.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   ├── synthea/
│   └── test_bundles/           # 5 known-condition test cases + answer key
│       ├── measles_24hr.json
│       ├── hepA_7day.json
│       ├── tb_7day.json
│       ├── anthrax_4hr.json
│       ├── noncond_control.json
│       └── EXPECTED_TIERS.json
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
│   ├── fhir_client.py          # read/write to HAPI FHIR
│   ├── bundle_parser.py        # parse eICR Bundle → structured prompt
│   ├── triage_engine.py        # LLM call + CSTE rubric → tier/score/reasoning
│   ├── writeback.py            # build Flag/Task resources
│   ├── pipeline.py             # end-to-end runner
│   └── utils.py
└── tests/
    ├── __init__.py
    ├── test_bundle_parser.py
    └── test_triage_engine.py
```

## Getting Started

### Prerequisites

- Python 3.10+
- **Docker Desktop** (runs the local HAPI FHIR server)
- An **Anthropic API key** (each contributor uses their own — keys are never shared or committed)

### Installation

```bash
git clone https://github.com/kc717/ecr-triage.git
cd ecr-triage
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then add YOUR OWN Anthropic API key
```

In `.env`, set:
```
ANTHROPIC_API_KEY=your-key-here
LLM_MODEL=claude-haiku-4-5
```

### Start the local FHIR server

```bash
# Make sure Docker Desktop is running first
docker compose up -d
```

Confirm it's live — this should return a CapabilityStatement:
```bash
curl http://localhost:8080/fhir/metadata
```

### Load test data

Quickest path — use the included known-condition test bundles:
```bash
# POST the 5 test bundles in data/test_bundles/ to the local server
# (each is a FHIR transaction Bundle)
```

Or generate synthetic patients with Synthea (see `data/synthea/`).

### Run the triage pipeline

```bash
python -m src.pipeline --file data/test_bundles/measles_24hr.json
```

The pipeline parses the Bundle, assigns a CSTE tier + urgency score with written reasoning, and writes Flag/Task resources back to HAPI.

### Validate the tier logic

The 5 test bundles each have a known expected tier (`EXPECTED_TIERS.json`). Run them and compare output tiers against the answer key to confirm the rubric behaves.

## Alignment

- **CDC Data Modernization Initiative (DMI):** Supports modernized surveillance workflows
- **eCR Now:** Leverages the electronic case reporting pipeline architecture
- **SMART on FHIR:** Standards-based app launch and authorization
- **APHL FHIR eCR IG 2.1.2:** Alignment target for the FHIR-native transition
- **CSTE/CDC 2025 Notification Requirements:** Basis for tier assignment

## Status

- ✅ Local HAPI FHIR server (Docker) + test data loaded
- ✅ End-to-end pipeline: parse → triage → Flag/Task write-back
- ✅ CSTE tier rubric (4-hour / 24-hour / 7-day / non-notifiable) — validated on known test cases
- ✅ Non-notifiable fallback (flags for human review rather than forcing a tier)
- ⬜ Output validator / guardrails (schema, grounding, notifiability cross-check)
- ⬜ Literature-grounded within-tier scoring rubric
- ⬜ Evaluation framework (concordance, tier accuracy, false-low-urgency rate)

## Team

| Name | Role | University |
|------|------|------------|
| Kevin Chen | Lead Developer | Indiana University Indianapolis |
| Sarah Danziger | Clinical Lead | Columbia University |
| Virginia Lorenzi | Mentor | Columbia University |

## License

MIT License — see `LICENSE` for details.

## Acknowledgments

- HL7 FHIR DevDays organizers
- HAPI FHIR community
- Synthea team at MITRE
