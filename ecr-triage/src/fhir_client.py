"""
FHIR Client — Read/write operations against a FHIR R4 server.

Handles connection to HAPI FHIR (or any R4 server), Bundle retrieval,
and resource write-back for Flag/Task triage outputs.
"""

import os
import logging
from typing import Optional

import yaml
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class FHIRClient:
    """Wrapper around fhirpy for eICR Bundle operations."""

    def __init__(self, config_path: str = "configs/fhir_server.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        server_key = self.config.get("default_server", "hapi_r4")
        server = self.config["servers"][server_key]
        self.base_url = server["base_url"]

        logger.info(f"FHIR client initialized: {self.base_url}")

    def get_bundles(self, count: int = 10) -> list[dict]:
        """Fetch eICR-style Bundles from the FHIR server.

        Args:
            count: Maximum number of Bundles to retrieve.

        Returns:
            List of FHIR Bundle resources as dicts.
        """
        # TODO: Implement Bundle search
        # - Search for Bundle resources of type 'document' or 'message'
        # - Filter by Composition profile if available
        # - Support pagination
        raise NotImplementedError

    def get_resource(self, resource_type: str, resource_id: str) -> dict:
        """Fetch a single FHIR resource by type and ID.

        Args:
            resource_type: e.g., 'Patient', 'Condition'
            resource_id: Logical ID of the resource.

        Returns:
            FHIR resource as dict.
        """
        # TODO: Implement single resource GET
        raise NotImplementedError

    def write_flag(self, patient_id: str, priority: str, rationale: str) -> dict:
        """Write a Flag resource back to the server.

        Args:
            patient_id: Reference to the Patient resource.
            priority: Triage priority code (urgent/high/routine/low).
            rationale: LLM-generated reasoning for the priority.

        Returns:
            Created Flag resource as dict.
        """
        # TODO: Construct and POST Flag resource
        # - Set status, category (triage), code (priority level)
        # - Reference the Patient
        # - Include rationale in Flag.text or extension
        raise NotImplementedError

    def write_task(self, patient_id: str, description: str, priority: str) -> dict:
        """Write a Task resource for investigation assignment.

        Args:
            patient_id: Reference to the Patient resource.
            description: Task description for the investigator.
            priority: Task priority (urgent/asap/routine/stat).

        Returns:
            Created Task resource as dict.
        """
        # TODO: Construct and POST Task resource
        # - Set status=requested, intent=order
        # - Reference Patient as focus
        # - Set priority and description
        raise NotImplementedError
