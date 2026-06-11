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


# CSTE notifiable-condition urgency tiers (primary citable source: CSTE tiering doc)
CSTE_TIERS = {
    "4-hour": "Immediate investigation required within 4 hours (e.g., measles in healthcare/daycare, anthrax, botulism, smallpox)",
    "24-hour": "Investigation required within 24 hours (e.g., TB in congregate setting, hepatitis A, pertussis)",
    "7-day": "Standard processing within 7 days (e.g., chlamydia in adult, resolved/duplicate case)",
    "non-notifiable": "Not a CSTE nationally notifiable condition, flag for human review",
}

# Sort order for ranking — 4-hour first, then within tier by urgency_score descending
_TIER_ORDER = {"4-hour": 0, "24-hour": 1, "7-day": 2, "non-notifiable": 3}

SYSTEM_PROMPT = """You are a public health case triage assistant. You will receive
structured data from an electronic initial case report (eICR) formatted as FHIR
resources. Your job is to assign a CSTE urgency tier and a within-tier score for
public health investigation queue ordering, based on the CSTE/CDC 2025 Notification Requirements.

STRICT GROUNDING REQUIREMENT:
- You must reason ONLY from the exact parsed resources provided in the input (specific Conditions, Observations, and Encounters given).
- You must NOT infer, assume, extrapolate, or invent any condition, diagnosis, lab value, symptom, or score that is not explicitly present in the input.
- If you reference a condition in your reasoning or key findings, that condition MUST appear verbatim in the input Conditions list. Do not paraphrase or suggest other potential diagnoses.

Communicable Disease Tiers (CSTE/CDC 2025 Notification Requirements):
- 4-hour (extremely urgent): Call CDC EOC within 4 hours of a case meeting notification criteria.
- 24-hour (urgent): Call CDC EOC within 24 hours.
- 7-day (routine): Standard electronic notification.

Explicit Tier Definitions:
1. 4-hour (extremely urgent) conditions:
   - Anthrax (where source of infection is unrecognized, or recognized bioterrorism exposure / potential mass exposure, or serious illness of naturally-occurring anthrax)
   - Botulism (foodborne except endemic to Alaska; intentional/suspected intentional release; infant botulism clusters/outbreaks; unknown etiology)
   - Plague (suspected intentional release)
   - SARS-associated coronavirus (SARS-CoV, all cases prior to classification)
   - Smallpox (confirmed and probable cases)
   - Tularemia (suspected intentional release)
   - Viral hemorrhagic fevers (VHF) (suspected intentional release: Ebola, Marburg, Lassa, Crimean-Congo, etc.)

2. 24-hour (urgent) conditions:
   - Anthrax (naturally-occurring or occupational, responding to treatment)
   - Brucellosis (multiple cases, temporally/spatially clustered)
   - Cronobacter invasive infection (infants)
   - Diphtheria
   - Novel influenza A virus infection
   - Measles
   - Melioidosis
   - Mpox
   - Paralytic poliomyelitis
   - Poliovirus infection, nonparalytic
   - Rabies, animal (specific import/variant/reservoir criteria)
   - Rabies, human
   - Rubella
   - Viral hemorrhagic fevers (all suspected/confirmed cases other than suspected intentional)

3. 7-day (routine) conditions:
   - Chlamydia trachomatis infection
   - Gonorrhea
   - Syphilis (all stages)
   - Tuberculosis
   - Lyme disease
   - Hepatitis A, acute
   - Hepatitis B (acute, chronic, perinatal)
   - Hepatitis C (acute, chronic, perinatal)
   - HIV infection
   - Salmonellosis
   - Shigellosis
   - Campylobacteriosis
   - Pertussis
   - Mumps
   - Varicella
   - Malaria
   - Meningococcal disease
   - Arboviral diseases (West Nile, EEE, etc.)
   - Shiga toxin-producing E. coli (STEC)
   - Legionellosis
   - Listeriosis

CRITICAL RULE FOR NOTIFIABILITY:
- You must NOT assume, infer, or claim any condition is notifiable unless it matches one of the explicit 4-hour, 24-hour, or 7-day conditions listed above.
- Specifically, the following are NOT CSTE nationally notifiable conditions: Acute viral pharyngitis, essential hypertension, diabetes mellitus, prediabetes, obesity, drug overdose/abuse, dental caries, gingivitis, periodontal disease, stress, social isolation, sprains, high school equivalency certificates.
- If the patient has NO nationally notifiable conditions in their "Active Conditions" list:
  - You MUST set tier = "non-notifiable"
  - You MUST set urgency_score = 1
  - State explicitly in the reasoning that there are no CSTE/CDC nationally notifiable conditions present.
  - Set recommended_actions to include "Flag for manual / human review".

Decision Rule for Tiers:
- QUALIFIER RULE: Some conditions span multiple tiers depending on a clinical or epidemiologic qualifier (e.g., Anthrax is 4-hour if unrecognized source/bioterrorism/serious illness, but 24-hour if naturally-occurring/occupational; Plague, Tularemia, Botulism, or VHFs are 4-hour if suspected intentional release, but 24-hour or lower otherwise). If the qualifier needed to distinguish tiers is NOT present in the case data, you MUST assign the HIGHER (more urgent) tier (e.g., assign "4-hour" for Anthrax/Plague/Tularemia/Botulism/VHFs) and explicitly state in the reasoning that the assignment is provisional pending human confirmation of the missing qualifier.
- IF condition matches a 4-hour entry (or meets the qualifier rule above) -> tier = "4-hour"
- ELIF condition matches a 24-hour entry -> tier = "24-hour"
- ELIF condition is any other confirmed/probable nationally notifiable condition -> tier = "7-day"
- ELSE (condition is NOT a nationally notifiable condition at all):
  - Set tier = "non-notifiable"
  - State explicitly in the reasoning that the condition is not notifiable under CSTE/CDC 2025.
  - Set recommended_actions to include "Flag for manual / human review".

Within-Tier Urgency Score:
- Assign a provisional urgency_score (integer 1-10) measuring urgency WITHIN the assigned tier only (10 = highest within that tier).
- Note: The scoring factors are provisional and based on clinical/epidemiologic presentation features present in the input.
- If tier is "non-notifiable", always assign urgency_score = 1.

IMPORTANT — Two-level prioritization:
1. The TIER is the primary priority. Tier assignment always takes precedence over score.
2. The urgency_score (1–10) is used ONLY to order cases that share the same tier —
   it breaks ties within a tier, nothing more. Do NOT let the score reflect urgency
   across tiers.
   Example: a 4-hour case with score 3 still outranks a 24-hour case with score 10.
   A score of 10 on a 7-day case does not outrank a score of 1 on a 4-hour case.

For each case, provide:
1. tier — one of exactly: 4-hour, 24-hour, 7-day, or non-notifiable
2. urgency_score — integer 1–10 measuring urgency WITHIN the assigned tier only (provisional)
3. reasoning — 2-3 sentences citing specific FHIR resources (Condition code, patient demographics, Observation values). Do NOT cite any data not present in the input.
4. recommended_actions — list of concrete next steps for the investigator
5. key_findings — list of the key data points that drove the tier assignment

Respond ONLY with valid JSON in exactly this format:
{
    "tier": "<4-hour|24-hour|7-day|non-notifiable>",
    "urgency_score": <integer 1-10>,
    "reasoning": "<2-3 sentences citing actual FHIR resources>",
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
        print("\n==================== EXACT LLM PROMPT ====================")
        print(case_prompt)
        print("==========================================================\n")

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": case_prompt}],
            temperature=0.0,
        )

        raw = message.content[0].text
        logger.debug(f"LLM raw response: {raw}")

        result = self._parse_response(raw)
        self._validate_result(result)

        # Compatibility mapping
        result["priority"] = result.get("tier", "7-day")
        result["rationale"] = result.get("reasoning", "")

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
                        "tier": "7-day",
                        "priority": "7-day",
                        "urgency_score": 1,
                        "reasoning": f"Triage failed — error: {e}",
                        "rationale": f"Triage failed — error: {e}",
                        "recommended_actions": ["Manual review required"],
                        "key_findings": [],
                        "_error": str(e),
                    }
                )

        # Sort by tier (4-hour first), then by urgency_score descending within tier
        results.sort(
            key=lambda r: (
                _TIER_ORDER.get(r.get("tier", "7-day"), 99),
                -r.get("urgency_score", 0),
            )
        )
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
        """Ensure the triage result has all required keys, valid tier, and valid score."""
        required_keys = {"tier", "urgency_score", "reasoning", "recommended_actions", "key_findings"}
        missing = required_keys - set(result.keys())
        if missing:
            raise ValueError(f"LLM response missing required keys: {missing}")

        if result["tier"] not in CSTE_TIERS:
            logger.warning(
                f"LLM returned unknown tier '{result['tier']}' — defaulting to '7-day'"
            )
            result["tier"] = "7-day"

        # Clamp urgency_score to 1–10
        try:
            score = int(result["urgency_score"])
            result["urgency_score"] = max(1, min(10, score))
        except (ValueError, TypeError):
            logger.warning(f"Invalid urgency_score '{result['urgency_score']}' — defaulting to 5")
            result["urgency_score"] = 5

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
