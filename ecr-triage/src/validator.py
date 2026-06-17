"""Validator — Output guardrails for triage results.

Runs independent validation checks on LLM triage output to detect hallucinations,
schema violations, and logical inconsistencies. Any failures route the case to
needs human review without modifying the model's original response text.
"""

import logging
import re
import yaml
from pathlib import Path
from typing import Tuple, List, Optional

logger = logging.getLogger(__name__)

DISEASE_KEYWORDS = {
    "measles": "measles",
    "anthrax": "anthrax",
    "hepatitis": "hepatitis",
    "tuberculosis": "tuberculosis",
    "pharyngitis": "pharyngitis",
    "chlamydia": "chlamydia",
    "gonorrhea": "gonorrhea",
    "syphilis": "syphilis",
    "lyme": "lyme",
    "botulism": "botulism",
    "plague": "plague",
    "tularemia": "tularemia",
    "diphtheria": "diphtheria",
    "influenza": "influenza",
    "mpox": "mpox",
    "polio": "polio",
    "rabies": "rabies",
    "rubella": "rubella",
    "brucellosis": "brucellosis",
    "cronobacter": "cronobacter",
    "melioidosis": "melioidosis",
    "varicella": "varicella",
    "malaria": "malaria",
    "mumps": "mumps",
    "pertussis": "pertussis",
    "smallpox": "smallpox",
    "ebola": "ebola",
    "marburg": "marburg",
    "lassa": "lassa",
    "hypertension": "hypertension",
    "diabetes": "diabetes",
    "obesity": "obesity",
    "overdose": "overdose"
}


def parse_cste_tiers_at_runtime(md_path: Optional[str] = None) -> dict:
    """Read and parse the YAML blocks inside cste_tiers.md at runtime."""
    if md_path is None:
        md_path = str(Path(__file__).resolve().parent.parent / "data" / "cste_tiers.md")
    try:
        with open(md_path, "r") as f:
            content = f.read()
        
        # Extract all code blocks labeled yaml
        blocks = re.findall(r"```yaml\n(.*?)\n```", content, re.DOTALL)
        
        parsed_data = {}
        for block in blocks:
            data = yaml.safe_load(block)
            if isinstance(data, dict):
                parsed_data.update(data)
        return parsed_data
    except Exception as e:
        logger.error(f"Failed to parse cste_tiers.md at runtime: {e}")
        return {}


def normalize_name(n: str) -> str:
    """Normalize condition names for matching."""
    n = n.lower().strip()
    if "hepatitis" in n:
        if "type a" in n or "hep a" in n or "hepatitis a" in n:
            return "hepatitis a"
        if "type b" in n or "hep b" in n or "hepatitis b" in n:
            return "hepatitis b"
        if "type c" in n or "hep c" in n or "hepatitis c" in n:
            return "hepatitis c"
    return n


def get_expected_tier(condition_display: str, cste_data: dict) -> str:
    """Map a condition name/display to its expected CSTE/CDC 2025 Notification Tier."""
    name = normalize_name(condition_display)
    
    # Check 4-hour conditions
    for item in cste_data.get("tier_4_hour", []):
        cond = normalize_name(item.get("condition", ""))
        if cond in name or name in cond:
            return "4-hour"
            
    # Check 24-hour conditions
    for item in cste_data.get("tier_24_hour", []):
        cond = normalize_name(item.get("condition", ""))
        if cond in name or name in cond:
            return "24-hour"
            
    # Check 7-day conditions
    for item in cste_data.get("tier_7_day_examples", []):
        cond_str = item if isinstance(item, str) else str(item)
        cond = normalize_name(cond_str)
        if cond in name or name in cond:
            return "7-day"
            
    return "non-notifiable"


def notifiability_check(triage_output: dict, parsed_case: dict) -> Tuple[bool, str]:
    """Flag if the model claims a tier/notifiable status that doesn't match CSTE reference in cste_tiers.md."""
    cste_data = parse_cste_tiers_at_runtime()
    conditions = parsed_case.get("Conditions", [])
    active_conds = [c for c in conditions if c.get("clinical_status") == "active"]
    
    tier_order = {"non-notifiable": 0, "7-day": 1, "24-hour": 2, "4-hour": 3}
    
    # Calculate the max expected tier based on active conditions
    max_expected_val = 0
    expected_tier = "non-notifiable"
    for c in active_conds:
        tier = get_expected_tier(c["display"], cste_data)
        val = tier_order.get(tier, 0)
        if val > max_expected_val:
            max_expected_val = val
            expected_tier = tier
            
    assigned_tier = triage_output.get("tier")
    if assigned_tier != expected_tier:
        return False, f"Assigned tier '{assigned_tier}' does not match expected CSTE tier '{expected_tier}' based on active conditions: {[c['display'] for c in active_conds]}."
        
    return True, ""


def grounding_check(triage_output: dict, parsed_case: dict) -> Tuple[bool, str]:
    """Confirm the conditions cited in reasoning actually appear in the input bundle's parsed conditions."""
    reasoning = triage_output.get("reasoning", "").lower()
    conditions = parsed_case.get("Conditions", [])
    parsed_displays = [c["display"].lower() for c in conditions]
    
    for word, display_repr in DISEASE_KEYWORDS.items():
        if word in reasoning:
            # Check if any parsed condition contains this keyword
            if not any(word in disp for disp in parsed_displays):
                return False, f"Reasoning references condition keyword '{word}', which is not present in the input patient conditions: {parsed_displays}."
                
    return True, ""


def schema_check(triage_output: dict, parsed_case: dict) -> Tuple[bool, str]:
    """Confirm output has tier, urgency_score, and reasoning in the correct types/values."""
    if not isinstance(triage_output, dict):
        return False, "Triage output is not a dictionary."
        
    tier = triage_output.get("tier")
    valid_tiers = {"4-hour", "24-hour", "7-day", "non-notifiable"}
    if tier not in valid_tiers:
        return False, f"Output 'tier' ('{tier}') is invalid. Must be one of {valid_tiers}."
        
    score = triage_output.get("urgency_score")
    if not isinstance(score, int):
        return False, f"Output 'urgency_score' ('{score}') is not an integer."
        
    reasoning = triage_output.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        return False, "Output 'reasoning' is missing or empty."
        
    return True, ""


def consistency_check(triage_output: dict, parsed_case: dict) -> Tuple[bool, str]:
    """Flag internal contradictions (e.g. score out of range, or non-notifiable with a score > 1)."""
    score = triage_output.get("urgency_score")
    if isinstance(score, int) and (score < 1 or score > 10):
        return False, f"Urgency score {score} is out of range 1-10."
        
    tier = triage_output.get("tier")
    if tier == "non-notifiable" and score != 1:
        return False, f"Condition is non-notifiable, but assigned urgency score is {score} (must be 1)."
        
    return True, ""


def validate_triage_result(triage_output: dict, parsed_case: dict) -> dict:
    """Run all validation checks and return a validation report dict."""
    checks = {
        "schema_check": schema_check(triage_output, parsed_case),
        "consistency_check": consistency_check(triage_output, parsed_case),
        "notifiability_check": notifiability_check(triage_output, parsed_case),
        "grounding_check": grounding_check(triage_output, parsed_case),
    }
    
    passed = True
    failures = []
    
    for name, (chk_passed, reason) in checks.items():
        if not chk_passed:
            passed = False
            failures.append(f"{name}: {reason}")
            
    report = {
        "passed": passed,
        "failures": failures,
        "results": {name: {"passed": chk_passed, "reason": reason} for name, (chk_passed, reason) in checks.items()}
    }
    
    return report
