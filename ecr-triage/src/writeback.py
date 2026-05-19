"""
Writeback — Create Flag and Task FHIR resources from triage results.

Demonstrates read-write interoperability: the app doesn't just consume
FHIR data, it produces structured outputs back to the server.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


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
    # TODO: Build Flag resource
    # {
    #   "resourceType": "Flag",
    #   "status": "active",
    #   "category": [{ "coding": [{ "system": "...", "code": "triage" }] }],
    #   "code": { "text": priority },
    #   "subject": { "reference": f"Patient/{patient_id}" },
    #   "period": { "start": datetime.now(timezone.utc).isoformat() },
    #   "text": { "status": "generated", "div": rationale }
    # }
    raise NotImplementedError


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
        priority: Task priority (urgent/asap/routine/stat).
        recommended_actions: List of suggested next steps.

    Returns:
        FHIR Task resource as dict, ready to POST.
    """
    # TODO: Build Task resource
    # {
    #   "resourceType": "Task",
    #   "status": "requested",
    #   "intent": "order",
    #   "priority": priority,
    #   "description": description,
    #   "focus": { "reference": f"Patient/{patient_id}" },
    #   "authoredOn": datetime.now(timezone.utc).isoformat(),
    #   "note": [{ "text": action } for action in recommended_actions]
    # }
    raise NotImplementedError
