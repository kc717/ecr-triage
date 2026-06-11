"""
Writeback — Create Flag and Task FHIR resources from triage results.

Demonstrates read-write interoperability: the app doesn't just consume
FHIR data, it produces structured outputs back to the server.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Map eCR-Triage priority levels to FHIR Task.priority codes
_TASK_PRIORITY_MAP = {
    "urgent": "stat",
    "high": "asap",
    "routine": "routine",
    "low": "routine",
    "4-hour": "stat",
    "24-hour": "asap",
    "7-day": "routine",
}


def build_flag_resource(
    patient_id: str,
    priority: str,
    rationale: str,
) -> dict:
    """Construct a FHIR Flag resource representing triage priority.

    Args:
        patient_id: Logical ID of the Patient resource.
        priority: Triage priority code (urgent/high/routine/low).
        rationale: LLM-generated reasoning.

    Returns:
        FHIR Flag resource as dict, ready to POST.
    """
    now = datetime.now(timezone.utc).isoformat()

    return {
        "resourceType": "Flag",
        "status": "active",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                        "code": "clinical",
                        "display": "Clinical",
                    }
                ],
                "text": "eCR Triage",
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://ecr-triage.example.org/priority",
                    "code": priority,
                    "display": priority.capitalize(),
                }
            ],
            "text": f"Triage Priority: {priority.capitalize()}",
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {"start": now},
        "text": {
            "status": "generated",
            "div": (
                f'<div xmlns="http://www.w3.org/1999/xhtml">'
                f"<p><strong>Triage Priority: {priority.upper()}</strong></p>"
                f"<p>{rationale}</p>"
                f"</div>"
            ),
        },
        "extension": [
            {
                "url": "http://ecr-triage.example.org/StructureDefinition/triage-rationale",
                "valueString": rationale,
            }
        ],
    }


def build_task_resource(
    patient_id: str,
    description: str,
    priority: str,
    recommended_actions: list[str],
) -> dict:
    """Construct a FHIR Task resource for investigation assignment.

    Args:
        patient_id: Logical ID of the Patient resource.
        description: Case summary for the investigator.
        priority: eCR-Triage priority (urgent/high/routine/low) — mapped
                  to FHIR Task priority codes (stat/asap/routine).
        recommended_actions: List of suggested next steps from the LLM.

    Returns:
        FHIR Task resource as dict, ready to POST.
    """
    fhir_priority = _TASK_PRIORITY_MAP.get(priority, "routine")
    now = datetime.now(timezone.utc).isoformat()

    return {
        "resourceType": "Task",
        "status": "requested",
        "intent": "order",
        "priority": fhir_priority,
        "description": description,
        "focus": {"reference": f"Patient/{patient_id}"},
        "authoredOn": now,
        "lastModified": now,
        "note": [{"text": action} for action in recommended_actions],
        "code": {
            "coding": [
                {
                    "system": "http://ecr-triage.example.org/task-type",
                    "code": "ecr-investigation",
                    "display": "eCR Case Investigation",
                }
            ]
        },
        "text": {
            "status": "generated",
            "div": (
                f'<div xmlns="http://www.w3.org/1999/xhtml">'
                f"<p><strong>Case Investigation Task</strong></p>"
                f"<p>{description}</p>"
                f"<ul>{''.join(f'<li>{a}</li>' for a in recommended_actions)}</ul>"
                f"</div>"
            ),
        },
    }
