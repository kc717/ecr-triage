"""
Pipeline — End-to-end eCR triage pipeline runner.

Usage:
    python -m src.pipeline               # Fetch live bundles from HAPI FHIR
    python -m src.pipeline --demo        # Run on built-in synthetic cases (no API key needed)
    python -m src.pipeline --file <path> # Run on a local FHIR Bundle JSON file
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from src.bundle_parser import BundleParser
from src.fhir_client import FHIRClient
from src.triage_engine import TriageEngine
from src.utils import setup_logging, save_json

logger = logging.getLogger(__name__)

# Built-in synthetic cases for demo mode (no API calls to FHIR server needed)
DEMO_BUNDLES = [
    {
        "resourceType": "Bundle",
        "type": "document",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "demo-patient-001",
                    "name": [{"family": "Rodriguez", "given": ["Maria"]}],
                    "birthDate": "1990-04-20",
                    "gender": "female",
                    "address": [{"city": "Atlanta", "state": "GA"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "demo-condition-001",
                    "code": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "186747009",
                                "display": "Measles",
                            }
                        ]
                    },
                    "clinicalStatus": {
                        "coding": [{"code": "active", "display": "Active"}]
                    },
                    "subject": {"reference": "Patient/demo-patient-001"},
                    "onsetDateTime": "2026-06-01",
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "demo-encounter-001",
                    "status": "finished",
                    "class": {"code": "AMB", "display": "ambulatory"},
                    "period": {"start": "2026-06-01T09:00:00Z"},
                    "subject": {"reference": "Patient/demo-patient-001"},
                }
            },
        ],
    },
    {
        "resourceType": "Bundle",
        "type": "document",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "demo-patient-002",
                    "name": [{"family": "Thompson", "given": ["James"]}],
                    "birthDate": "1965-11-08",
                    "gender": "male",
                    "address": [{"city": "Indianapolis", "state": "IN"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "demo-condition-002",
                    "code": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "56717001",
                                "display": "Tuberculosis",
                            }
                        ]
                    },
                    "clinicalStatus": {
                        "coding": [{"code": "active", "display": "Active"}]
                    },
                    "subject": {"reference": "Patient/demo-patient-002"},
                    "onsetDateTime": "2026-05-15",
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "demo-obs-001",
                    "status": "final",
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "45323-3",
                                "display": "Mycobacterium tuberculosis culture",
                            }
                        ]
                    },
                    "valueCodeableConcept": {
                        "coding": [{"code": "positive", "display": "Positive"}]
                    },
                    "effectiveDateTime": "2026-05-20",
                    "subject": {"reference": "Patient/demo-patient-002"},
                }
            },
        ],
    },
    {
        "resourceType": "Bundle",
        "type": "document",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "demo-patient-003",
                    "name": [{"family": "Kim", "given": ["Sarah"]}],
                    "birthDate": "2000-07-14",
                    "gender": "female",
                    "address": [{"city": "Chicago", "state": "IL"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "demo-condition-003",
                    "code": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "53741008",
                                "display": "Chlamydial infection",
                            }
                        ]
                    },
                    "clinicalStatus": {
                        "coding": [{"code": "active", "display": "Active"}]
                    },
                    "subject": {"reference": "Patient/demo-patient-003"},
                    "onsetDateTime": "2026-06-05",
                }
            },
        ],
    },
]


def run_demo(output_dir: str = "data/processed") -> list[dict]:
    """Run the full pipeline on built-in synthetic cases."""
    print("\n🧪 Running in DEMO mode (3 synthetic cases)\n")

    parser = BundleParser()
    engine = TriageEngine()
    results = []

    case_prompts = []
    patient_ids = []

    for bundle in DEMO_BUNDLES:
        parsed = parser.parse_bundle(bundle)
        prompt = parser.to_triage_prompt(parsed)
        case_prompts.append(prompt)
        patient_ids.append(parsed.get("Patient", {}).get("id", "unknown"))

    triage_results = engine.triage_batch(case_prompts)

    for result, patient_id in zip(triage_results, patient_ids):
        result["patient_id"] = patient_id
        results.append(result)
        _print_result(result)

    save_json(results, f"{output_dir}/triage_results_demo.json")
    print(f"\n✅ Results saved to {output_dir}/triage_results_demo.json")
    return results


def run_from_file(filepath: str, writeback: bool = False) -> dict:
    """Run the pipeline on a single local FHIR Bundle JSON file."""
    print(f"\n📂 Loading bundle from: {filepath}\n")

    with open(filepath) as f:
        bundle = json.load(f)

    engine = TriageEngine()
    result = engine.triage_bundle(bundle)
    _print_result(result)

    if writeback:
        client = FHIRClient()
        wb = client.write_triage_results(result["patient_id"], result)
        print(f"\n✍️  Flag ID: {wb['flag'].get('id')} | Task ID: {wb['task'].get('id')}")

    return result


def run_live(count: int = 5, writeback: bool = False, output_dir: str = "data/processed") -> list[dict]:
    """Fetch live bundles from HAPI FHIR and triage them."""
    print(f"\n🌐 Fetching {count} Bundles from HAPI FHIR…\n")

    client = FHIRClient()
    bundles = client.get_bundles(count=count)

    if not bundles:
        print("⚠️  No Bundles found on the FHIR server. Try --demo mode instead.")
        return []

    parser = BundleParser()
    engine = TriageEngine()

    case_prompts = []
    patient_ids = []

    for bundle in bundles:
        parsed = parser.parse_bundle(bundle)
        case_prompts.append(parser.to_triage_prompt(parsed))
        patient_ids.append(parsed.get("Patient", {}).get("id", "unknown"))

    triage_results = engine.triage_batch(case_prompts)
    results = []

    for result, patient_id in zip(triage_results, patient_ids):
        result["patient_id"] = patient_id
        results.append(result)
        _print_result(result)

        if writeback and "_error" not in result:
            wb = client.write_triage_results(patient_id, result)
            print(f"   ✍️  Wrote Flag/{wb['flag'].get('id')} + Task/{wb['task'].get('id')}")

    save_json(results, f"{output_dir}/triage_results_live.json")
    print(f"\n✅ Results saved to {output_dir}/triage_results_live.json")
    return results


def _print_result(result: dict) -> None:
    """Pretty-print a single triage result to stdout."""
    priority = result.get("priority", "unknown").upper()
    patient_id = result.get("patient_id", result.get("_case_index", "?"))

    priority_icons = {"URGENT": "🔴", "HIGH": "🟠", "ROUTINE": "🟡", "LOW": "🟢"}
    icon = priority_icons.get(priority, "⚪")

    print(f"{icon} [{priority}] Patient: {patient_id}")
    print(f"   Rationale: {result.get('rationale', 'N/A')}")

    actions = result.get("recommended_actions", [])
    if actions:
        print("   Actions:")
        for a in actions:
            print(f"     • {a}")
    print()


if __name__ == "__main__":
    setup_logging()

    ap = argparse.ArgumentParser(description="eCR-Triage pipeline runner")
    ap.add_argument("--demo", action="store_true", help="Run on built-in synthetic cases")
    ap.add_argument("--file", type=str, help="Path to a local FHIR Bundle JSON file")
    ap.add_argument("--count", type=int, default=5, help="Number of live bundles to fetch")
    ap.add_argument("--writeback", action="store_true", help="Write Flag+Task to FHIR server")
    ap.add_argument("--output", type=str, default="data/processed", help="Output directory for results JSON")
    args = ap.parse_args()

    if args.demo:
        run_demo(output_dir=args.output)
    elif args.file:
        run_from_file(args.file, writeback=args.writeback)
    else:
        run_live(count=args.count, writeback=args.writeback, output_dir=args.output)
