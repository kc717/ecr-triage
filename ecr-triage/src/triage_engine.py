"""
Triage Engine — LLM-based prioritization of electronic case reports.

Takes parsed eICR Bundle data, sends it to an LLM with a structured
prompt, and returns a priority score with reasoning grounded in
specific FHIR resource references.
"""

import os
import json
import logging
from typing import Optional

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

Respond in JSON format:
{
    "priority": "<urgent|high|routine|low>",
    "rationale": "<reasoning with resource references>",
    "recommended_actions": ["<action 1>", "<action 2>"],
    "key_findings": ["<finding 1>", "<finding 2>"]
}
"""


class TriageEngine:
    """LLM-powered triage scoring for eICR Bundles."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set — triage calls will fail")

    def triage(self, case_prompt: str) -> dict:
        """Send a parsed eICR case to the LLM for triage scoring.

        Args:
            case_prompt: Structured text from BundleParser.to_triage_prompt()

        Returns:
            Dict with keys: priority, rationale, recommended_actions, key_findings
        """
        # TODO: Call Anthropic API with SYSTEM_PROMPT + case_prompt
        # - Parse JSON response
        # - Validate priority is in PRIORITY_LEVELS
        # - Return structured result
        raise NotImplementedError

    def triage_batch(self, cases: list[str]) -> list[dict]:
        """Triage multiple cases and return ranked results.

        Args:
            cases: List of case prompts from BundleParser.

        Returns:
            List of triage results, sorted by priority (urgent first).
        """
        # TODO: Triage each case, sort by priority
        raise NotImplementedError


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    engine = TriageEngine()
    # TODO: Load sample data and run triage
    print("Triage engine initialized. Add sample data to test.")
