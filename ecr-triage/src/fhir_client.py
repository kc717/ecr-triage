"""
FHIR Client — Read/write operations against a FHIR R4 server.

Handles connection to HAPI FHIR (or any R4 server), Bundle retrieval,
and resource write-back for Flag/Task triage outputs.
"""

import logging
from typing import Optional

import requests
import yaml
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class FHIRClient:
    """Lightweight FHIR R4 client for eICR Bundle operations.

    Uses raw HTTP (requests) so there are no heavy SDK dependencies
    at runtime — fhirpy remains available for advanced use cases.
    """

    def __init__(self, config_path: str = "configs/fhir_server.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        server_key = self.config.get("default_server", "hapi_r4")
        server = self.config["servers"][server_key]
        self.base_url = server["base_url"].rstrip("/")

        # Build a session with sensible defaults
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            }
        )

        # Optional bearer token (set FHIR_AUTH_TOKEN in .env)
        import os
        token = os.getenv("FHIR_AUTH_TOKEN")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

        logger.info(f"FHIR client initialized: {self.base_url}")

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def get_bundles(self, count: int = 10) -> list[dict]:
        """Fetch eICR-style Bundles from the FHIR server.

        Searches for Bundle resources of type 'document' which is the
        standard packaging for eICR / Composition-based reports.

        Args:
            count: Maximum number of Bundles to retrieve.

        Returns:
            List of FHIR Bundle resources as dicts.
        """
        url = f"{self.base_url}/Bundle"
        params = {"type": "document", "_count": count, "_sort": "-_lastUpdated"}

        logger.info(f"Fetching up to {count} Bundles from {url}")
        response = self._get(url, params=params)

        search_set = response
        entries = search_set.get("entry", [])
        bundles = [e["resource"] for e in entries if "resource" in e]

        logger.info(f"Retrieved {len(bundles)} Bundles")
        return bundles

    def get_resource(self, resource_type: str, resource_id: str) -> dict:
        """Fetch a single FHIR resource by type and ID.

        Args:
            resource_type: e.g., 'Patient', 'Condition'
            resource_id: Logical ID of the resource.

        Returns:
            FHIR resource as dict.
        """
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        logger.info(f"Fetching {resource_type}/{resource_id}")
        return self._get(url)

    def search_resources(
        self,
        resource_type: str,
        params: Optional[dict] = None,
        count: int = 10,
    ) -> list[dict]:
        """Search for FHIR resources with arbitrary query parameters.

        Args:
            resource_type: FHIR resource type to search.
            params: Search parameters dict (e.g., {'code': '186747009'}).
            count: Max results.

        Returns:
            List of matching resources.
        """
        url = f"{self.base_url}/{resource_type}"
        search_params = {"_count": count, **(params or {})}
        response = self._get(url, params=search_params)
        entries = response.get("entry", [])
        return [e["resource"] for e in entries if "resource" in e]

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def write_flag(self, patient_id: str, priority: str, rationale: str) -> dict:
        """Write a Flag resource back to the server.

        Args:
            patient_id: Reference to the Patient resource.
            priority: Triage priority code (urgent/high/routine/low).
            rationale: LLM-generated reasoning for the priority.

        Returns:
            Created Flag resource as dict (server response).
        """
        from src.writeback import build_flag_resource

        flag = build_flag_resource(patient_id, priority, rationale)
        logger.info(f"Writing Flag for Patient/{patient_id} — priority={priority}")
        return self._post(f"{self.base_url}/Flag", flag)

    def write_task(self, patient_id: str, description: str, priority: str, recommended_actions: Optional[list[str]] = None) -> dict:
        """Write a Task resource for investigation assignment.

        Args:
            patient_id: Reference to the Patient resource.
            description: Task description for the investigator.
            priority: eCR-Triage priority (urgent/high/routine/low).
            recommended_actions: LLM-suggested next steps.

        Returns:
            Created Task resource as dict (server response).
        """
        from src.writeback import build_task_resource

        task = build_task_resource(
            patient_id=patient_id,
            description=description,
            priority=priority,
            recommended_actions=recommended_actions or [],
        )
        logger.info(f"Writing Task for Patient/{patient_id} — priority={priority}")
        return self._post(f"{self.base_url}/Task", task)

    def write_triage_results(
        self,
        patient_id: str,
        triage_result: dict,
    ) -> dict:
        """Convenience method: write both Flag and Task from a triage result.

        Args:
            patient_id: Patient logical ID.
            triage_result: Output dict from TriageEngine.triage().

        Returns:
            Dict with keys 'flag' and 'task', each containing the
            server's created resource.
        """
        priority = triage_result["priority"]
        rationale = triage_result["rationale"]
        actions = triage_result.get("recommended_actions", [])
        findings = triage_result.get("key_findings", [])

        description = rationale
        if findings:
            description += " Key findings: " + "; ".join(findings)

        flag = self.write_flag(patient_id, priority, rationale)
        task = self.write_task(patient_id, description, priority, actions)

        return {"flag": flag, "task": task}

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Optional[dict] = None) -> dict:
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, url: str, body: dict) -> dict:
        resp = self.session.post(url, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()
