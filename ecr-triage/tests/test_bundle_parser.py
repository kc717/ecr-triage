"""Tests for BundleParser."""

import pytest
from src.bundle_parser import BundleParser


# Sample minimal FHIR Bundle for testing
SAMPLE_BUNDLE = {
    "resourceType": "Bundle",
    "type": "document",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "test-patient-1",
                "birthDate": "1985-03-15",
                "gender": "female",
                "address": [{"city": "Atlanta", "state": "GA"}],
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "test-condition-1",
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "186747009",
                            "display": "Measles",
                        }
                    ]
                },
                "subject": {"reference": "Patient/test-patient-1"},
                "onsetDateTime": "2026-05-01",
            }
        },
        {
            "resource": {
                "resourceType": "Encounter",
                "id": "test-encounter-1",
                "class": {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "AMB",
                    "display": "ambulatory",
                },
                "period": {"start": "2026-05-01T09:00:00Z"},
                "subject": {"reference": "Patient/test-patient-1"},
            }
        },
    ],
}


class TestBundleParser:
    """Test suite for BundleParser."""

    def setup_method(self):
        self.parser = BundleParser()

    @pytest.mark.skip(reason="Not yet implemented")
    def test_parse_bundle_extracts_all_resources(self):
        result = self.parser.parse_bundle(SAMPLE_BUNDLE)
        assert "Patient" in result
        assert "Condition" in result
        assert "Encounter" in result

    @pytest.mark.skip(reason="Not yet implemented")
    def test_extract_patient_summary(self):
        patient = SAMPLE_BUNDLE["entry"][0]["resource"]
        summary = self.parser.extract_patient_summary(patient)
        assert summary["gender"] == "female"
        assert summary["state"] == "GA"

    @pytest.mark.skip(reason="Not yet implemented")
    def test_extract_conditions(self):
        conditions = [SAMPLE_BUNDLE["entry"][1]["resource"]]
        result = self.parser.extract_conditions(conditions)
        assert len(result) == 1
        assert result[0]["display"] == "Measles"

    @pytest.mark.skip(reason="Not yet implemented")
    def test_to_triage_prompt_returns_string(self):
        parsed = self.parser.parse_bundle(SAMPLE_BUNDLE)
        prompt = self.parser.to_triage_prompt(parsed)
        assert isinstance(prompt, str)
        assert "Measles" in prompt
