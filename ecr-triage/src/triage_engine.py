"""
Triage Engine — LLM-based prioritization of electronic case reports.

Takes parsed eICR Bundle data, sends it to an LLM with a structured
prompt, and returns a priority score with reasoning grounded in
specific FHIR resource references.
"""

import json
import logging
import os
from typing import Optional

import anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# Triage priority levels aligned with configs/fhir_server.yaml
PRIORITY_LEVELS = {
    "urgent": "Immediate investigation required (e.g., measles in daycare, anthrax exposure)",
    "high": "Investigation within 24 hours (e.g., TB in congregate setting)",
    "routine": "Standard processing timeline (e.g., chlamydia in adult)",
    "low": "Batch processing acceptable (e.g., duplicate or resolved case)",
}

# Priority sort order for ranking
_PRIORITY_ORDER = {"urgent": 0, "high": 1, "routine": 2, "low": 3}

SYSTEM_PROMPT = """You are a public health case triage assistant. You will receive
structured data from an electronic initial case report (eICR) formatted as FHIR
resources. Your job is to assess the priority for public health investigation.

For each case, provide:
1. A priority level: urgent, high, routine, or low
2. A 2-3 sentence rationale referencing specific data from the case
3. Recommended next actions for the investigator

Ground your reasoning in the specific FHIR resources provided (e.g., cite the
Condition code, the patient demographics, the Observation values). Do NOT
hallucinate information not present in the input.

Respond ONLY with valid JSON in exactly this format:
{
    "priority": "<urgent|high|routine|low>",
    "rationale": "<reasoning with resource references>",
    "recommended_actions": ["<action 1>", "<action 2>"],
    "key_findings": ["<finding 1>", "<finding 2>"]
}"""


class TriageEngine:
    """LLM-powered triage scoring for eICR Bundles."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set — triage calls will fail")

        self._client: Optional[anthropic.Anthropic] = None

    @property
    def client(self) -> anthropic.Anthropic:
        """Lazy-init the Anthropic client."""
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def triage(self, case_prompt: str) -> dict:
        """Send a parsed eICR case to the LLM for triage scoring.

        Args:
            case_prompt: Structured text from BundleParser.to_triage_prompt()

        Returns:
            Dict with keys: priority, rationale, recommended_actions, key_findings
        """
        logger.info(f"Sending case to LLM ({self.model}) for triage…")

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": case_prompt}],
        )

        raw = message.content[0].text
        logger.debug(f"LLM raw response: {raw}")

        result = self._parse_response(raw)
        self._validate_result(result)

        logger.info(f"Triage result: priority={result['priority']}")
        return result

    def triage_batch(self, cases: list[str]) -> list[dict]:
        """Triage multiple cases and return ranked results.

        Args:
            cases: List of case prompts from BundleParser.

        Returns:
            List of triage results, sorted by priority (urgent first).
        """
        if not cases:
            return []

        logger.info(f"Triaging batch of {len(cases)} cases…")
        results = []

        for i, case_prompt in enumerate(cases, start=1):
            logger.info(f"  Processing case {i}/{len(cases)}…")
            try:
                result = self.triage(case_prompt)
                result["_case_index"] = i
                results.append(result)
            except Exception as e:
                logger.error(f"  Case {i} failed: {e}")
                results.append(
                    {
                        "_case_index": i,
                        "priority": "routine",
                        "rationale": f"Triage failed — error: {e}",
                        "recommended_actions": ["Manual review required"],
                        "key_findings": [],
                        "_error": str(e),
                    }
                )

        # Sort by priority: urgent → high → routine → low
        results.sort(key=lambda r: _PRIORITY_ORDER.get(r.get("priority", "routine"), 99))
        return results

    def triage_bundle(self, bundle: dict) -> dict:
        """Convenience method: parse a Bundle and triage it in one call.

        Args:
            bundle: Raw FHIR Bundle resource as dict.

        Returns:
            Triage result dict augmented with 'patient_id' and 'prompt' keys.
        """
        from src.bundle_parser import BundleParser

        parser = BundleParser()
        parsed = parser.parse_bundle(bundle)
        prompt = parser.to_triage_prompt(parsed)

        result = self.triage(prompt)

        # Attach patient ID for downstream writeback
        patient = parsed.get("Patient", {})
        result["patient_id"] = patient.get("id", "unknown")
        result["patient_name"] = patient.get("name", "Unknown")
        result["_prompt"] = prompt

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_response(self, raw: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        text = raw.strip()

        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}\nRaw: {raw}")
            raise ValueError(f"LLM returned invalid JSON: {e}") from e

    def _validate_result(self, result: dict) -> None:
        """Ensure the triage result has all required keys and valid priority."""
        required_keys = {"priority", "rationale", "recommended_actions", "key_findings"}
        missing = required_keys - set(result.keys())
        if missing:
            raise ValueError(f"LLM response missing required keys: {missing}")

        if result["priority"] not in PRIORITY_LEVELS:
            logger.warning(
                f"LLM returned unknown priority '{result['priority']}' — defaulting to 'routine'"
            )
            result["priority"] = "routine"

        if not isinstance(result["recommended_actions"], list):
            result["recommended_actions"] = [str(result["recommended_actions"])]

        if not isinstance(result["key_findings"], list):
            result["key_findings"] = [str(result["key_findings"])]


if __name__ == "__main__":
    import sys
    from src.utils import setup_logging

    setup_logging()

    engine = TriageEngine()

    # Quick smoke test with a synthetic case
    sample_prompt = """=== ELECTRONIC CASE REPORT (eICR) ===

## PATIENT DEMOGRAPHICS
  ID:     test-patient-001
  Name:   Jane Doe
  Age:    34 years
  Gender: female
  Location: Atlanta, GA

## REPORTABLE CONDITIONS
  - Measles | Code: 186747009 (http://snomed.info/sct) | Onset: 2026-06-01 | Status: active

## LAB RESULTS / OBSERVATIONS
  (none recorded)

## ENCOUNTERS
  - Type: ambulatory | Start: 2026-06-01T09:00:00Z | End: N/A

=== END OF CASE REPORT ==="""

    try:
        result = engine.triage(sample_prompt)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
