"""
Bundle Parser — Extract and flatten resources from eICR FHIR Bundles.

Parses Bundle entries into structured data suitable for LLM triage input.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BundleParser:
    """Parse eICR Bundles into structured triage-ready summaries."""

    # Resource types we extract from eICR Bundles
    RESOURCE_TYPES = [
        "Patient",
        "Condition",
        "Encounter",
        "Observation",
        "Immunization",
        "Organization",
    ]

    def __init__(self):
        pass

    def parse_bundle(self, bundle: dict) -> dict:
        """Extract all relevant resources from a FHIR Bundle.

        Args:
            bundle: Raw FHIR Bundle resource as dict.

        Returns:
            Dict keyed by resource type, each containing a list of
            parsed resource summaries.
        """
        # TODO: Iterate Bundle.entry, group by resourceType
        # - Extract Patient demographics (age, gender, location)
        # - Extract Condition codes and display names
        # - Extract Encounter class and period
        # - Extract Observation values (labs, vitals)
        raise NotImplementedError

    def extract_patient_summary(self, patient: dict) -> dict:
        """Extract key demographics from a Patient resource.

        Returns:
            Dict with keys: id, age, gender, city, state
        """
        # TODO: Parse Patient.birthDate → age, gender, address
        raise NotImplementedError

    def extract_conditions(self, conditions: list[dict]) -> list[dict]:
        """Extract condition codes and display text.

        Returns:
            List of dicts with keys: code, system, display, onset
        """
        # TODO: Parse Condition.code.coding, Condition.onsetDateTime
        raise NotImplementedError

    def extract_observations(self, observations: list[dict]) -> list[dict]:
        """Extract lab results and vital signs.

        Returns:
            List of dicts with keys: code, display, value, unit, date
        """
        # TODO: Parse Observation.code, valueQuantity, effectiveDateTime
        raise NotImplementedError

    def to_triage_prompt(self, parsed: dict) -> str:
        """Convert parsed Bundle data into a structured text prompt
        suitable for the LLM triage engine.

        Args:
            parsed: Output from parse_bundle().

        Returns:
            Formatted string for LLM input.
        """
        # TODO: Build structured text with patient context,
        # conditions, labs, encounter details
        raise NotImplementedError
