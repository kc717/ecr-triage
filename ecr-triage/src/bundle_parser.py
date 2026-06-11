"""
Bundle Parser — Extract and flatten resources from eICR FHIR Bundles.

Parses Bundle entries into structured data suitable for LLM triage input.
"""

import logging
from datetime import date
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_bundle(self, bundle: dict) -> dict:
        """Extract all relevant resources from a FHIR Bundle.

        Args:
            bundle: Raw FHIR Bundle resource as dict.

        Returns:
            Dict keyed by resource type, each containing a list of
            parsed resource summaries.
        """
        grouped: dict[str, list[dict]] = {rt: [] for rt in self.RESOURCE_TYPES}

        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            rt = resource.get("resourceType")
            if rt in grouped:
                grouped[rt].append(resource)

        parsed: dict = {}

        # Patient — expect exactly one, but handle multiples gracefully
        patients = grouped["Patient"]
        if patients:
            parsed["Patient"] = self.extract_patient_summary(patients[0])
        else:
            parsed["Patient"] = {}
            logger.warning("Bundle contains no Patient resource")

        parsed["Conditions"] = self.extract_conditions(grouped["Condition"])
        parsed["Observations"] = self.extract_observations(grouped["Observation"])
        parsed["Encounters"] = self._extract_encounters(grouped["Encounter"])
        parsed["Immunizations"] = self._extract_immunizations(grouped["Immunization"])
        parsed["Organization"] = self._extract_organization(grouped["Organization"])

        return parsed

    def extract_patient_summary(self, patient: dict) -> dict:
        """Extract key demographics from a Patient resource.

        Returns:
            Dict with keys: id, age, gender, city, state
        """
        patient_id = patient.get("id", "unknown")
        gender = patient.get("gender", "unknown")

        # Age from birthDate
        birth_date_str = patient.get("birthDate")
        age: Optional[int] = None
        if birth_date_str:
            try:
                age = self._calculate_age(birth_date_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse birthDate: {birth_date_str}")

        # Address — take first entry
        address = {}
        addresses = patient.get("address", [])
        if addresses:
            address = addresses[0]

        # Name — take first entry
        name = "Unknown"
        names = patient.get("name", [])
        if names:
            family = names[0].get("family", "")
            given = " ".join(names[0].get("given", []))
            name = f"{given} {family}".strip() or "Unknown"

        return {
            "id": patient_id,
            "name": name,
            "age": age,
            "gender": gender,
            "city": address.get("city", "Unknown"),
            "state": address.get("state", "Unknown"),
            "postal_code": address.get("postalCode"),
        }

    def extract_conditions(self, conditions: list[dict]) -> list[dict]:
        """Extract condition codes and display text.

        Returns:
            List of dicts with keys: code, system, display, onset
        """
        results = []
        for condition in conditions:
            code_block = condition.get("code", {})
            codings = code_block.get("coding", [])

            code = "unknown"
            system = "unknown"
            display = code_block.get("text", "Unknown condition")

            if codings:
                first = codings[0]
                code = first.get("code", "unknown")
                system = first.get("system", "unknown")
                display = first.get("display", display)

            results.append(
                {
                    "id": condition.get("id"),
                    "code": code,
                    "system": system,
                    "display": display,
                    "onset": condition.get("onsetDateTime") or condition.get("onsetString"),
                    "clinical_status": self._safe_coding_display(
                        condition.get("clinicalStatus", {})
                    ),
                    "verification_status": self._safe_coding_display(
                        condition.get("verificationStatus", {})
                    ),
                }
            )
        return results

    def extract_observations(self, observations: list[dict]) -> list[dict]:
        """Extract lab results and vital signs.

        Returns:
            List of dicts with keys: code, display, value, unit, date
        """
        results = []
        for obs in observations:
            code_block = obs.get("code", {})
            codings = code_block.get("coding", [])

            code = "unknown"
            display = code_block.get("text", "Unknown observation")
            if codings:
                code = codings[0].get("code", "unknown")
                display = codings[0].get("display", display)

            # Value — handle quantity, string, boolean, codeable concept
            value = None
            unit = None
            if "valueQuantity" in obs:
                vq = obs["valueQuantity"]
                value = vq.get("value")
                unit = vq.get("unit") or vq.get("code")
            elif "valueString" in obs:
                value = obs["valueString"]
            elif "valueBoolean" in obs:
                value = obs["valueBoolean"]
            elif "valueCodeableConcept" in obs:
                value = self._safe_coding_display(obs["valueCodeableConcept"])

            results.append(
                {
                    "code": code,
                    "display": display,
                    "value": value,
                    "unit": unit,
                    "date": obs.get("effectiveDateTime") or obs.get("issued"),
                    "status": obs.get("status"),
                    "interpretation": self._safe_coding_display(
                        obs.get("interpretation", [{}])[0]
                        if obs.get("interpretation")
                        else {}
                    ),
                }
            )
        return results

    def to_triage_prompt(self, parsed: dict) -> str:
        """Convert parsed Bundle data into a structured text prompt
        suitable for the LLM triage engine.

        Args:
            parsed: Output from parse_bundle().

        Returns:
            Formatted string for LLM input.
        """
        lines = ["=== ELECTRONIC CASE REPORT (eICR) ===\n"]

        # Patient
        pt = parsed.get("Patient", {})
        if pt:
            lines.append("## PATIENT DEMOGRAPHICS")
            lines.append(f"  ID:     {pt.get('id', 'N/A')}")
            lines.append(f"  Name:   {pt.get('name', 'N/A')}")
            lines.append(f"  Age:    {pt.get('age', 'N/A')} years")
            lines.append(f"  Gender: {pt.get('gender', 'N/A')}")
            lines.append(f"  Location: {pt.get('city', 'N/A')}, {pt.get('state', 'N/A')}")
            lines.append("")

        # Conditions
        conditions = parsed.get("Conditions", [])
        lines.append("## REPORTABLE CONDITIONS")
        if conditions:
            for c in conditions:
                lines.append(
                    f"  - {c['display']} | Code: {c['code']} ({c['system']}) | "
                    f"Onset: {c['onset'] or 'N/A'} | "
                    f"Status: {c['clinical_status'] or 'N/A'}"
                )
        else:
            lines.append("  (none recorded)")
        lines.append("")

        # Observations
        observations = parsed.get("Observations", [])
        lines.append("## LAB RESULTS / OBSERVATIONS")
        if observations:
            for o in observations:
                val_str = f"{o['value']} {o['unit'] or ''}".strip() if o["value"] is not None else "N/A"
                interp = f" [{o['interpretation']}]" if o.get("interpretation") else ""
                lines.append(
                    f"  - {o['display']} ({o['code']}): {val_str}{interp} | "
                    f"Date: {o['date'] or 'N/A'}"
                )
        else:
            lines.append("  (none recorded)")
        lines.append("")

        # Encounters
        encounters = parsed.get("Encounters", [])
        lines.append("## ENCOUNTERS")
        if encounters:
            for e in encounters:
                lines.append(
                    f"  - Type: {e['class_display']} | "
                    f"Start: {e['start'] or 'N/A'} | "
                    f"End: {e['end'] or 'N/A'}"
                )
        else:
            lines.append("  (none recorded)")
        lines.append("")

        # Immunizations
        immunizations = parsed.get("Immunizations", [])
        if immunizations:
            lines.append("## IMMUNIZATIONS")
            for imm in immunizations:
                lines.append(
                    f"  - {imm['display']} | Date: {imm['date'] or 'N/A'} | Status: {imm['status']}"
                )
            lines.append("")

        # Organization
        org = parsed.get("Organization", {})
        if org:
            lines.append("## REPORTING ORGANIZATION")
            lines.append(f"  {org.get('name', 'N/A')} | Type: {org.get('type', 'N/A')}")
            lines.append("")

        lines.append("=== END OF CASE REPORT ===")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_encounters(self, encounters: list[dict]) -> list[dict]:
        results = []
        for enc in encounters:
            enc_class = enc.get("class", {})
            class_display = enc_class.get("display") or enc_class.get("code", "unknown")
            period = enc.get("period", {})
            results.append(
                {
                    "id": enc.get("id"),
                    "class_display": class_display,
                    "start": period.get("start"),
                    "end": period.get("end"),
                    "status": enc.get("status"),
                }
            )
        return results

    def _extract_immunizations(self, immunizations: list[dict]) -> list[dict]:
        results = []
        for imm in immunizations:
            vaccine = imm.get("vaccineCode", {})
            codings = vaccine.get("coding", [])
            display = vaccine.get("text", "Unknown vaccine")
            if codings:
                display = codings[0].get("display", display)
            results.append(
                {
                    "display": display,
                    "date": imm.get("occurrenceDateTime") or imm.get("occurrenceString"),
                    "status": imm.get("status"),
                }
            )
        return results

    def _extract_organization(self, organizations: list[dict]) -> dict:
        if not organizations:
            return {}
        org = organizations[0]
        org_type = ""
        types = org.get("type", [])
        if types:
            org_type = self._safe_coding_display(types[0])
        return {
            "id": org.get("id"),
            "name": org.get("name", "Unknown"),
            "type": org_type,
        }

    def _safe_coding_display(self, codeable_concept: dict) -> str:
        """Get the best display string from a CodeableConcept."""
        if not codeable_concept:
            return ""
        text = codeable_concept.get("text", "")
        codings = codeable_concept.get("coding", [])
        if codings:
            return codings[0].get("display") or codings[0].get("code") or text
        return text

    @staticmethod
    def _calculate_age(birth_date_str: str) -> int:
        """Calculate age from FHIR-format date string (YYYY-MM-DD)."""
        birth = date.fromisoformat(birth_date_str)
        today = date.today()
        return today.year - birth.year - (
            (today.month, today.day) < (birth.month, birth.day)
        )
