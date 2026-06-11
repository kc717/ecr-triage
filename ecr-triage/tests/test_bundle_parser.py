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

    def test_parse_bundle_extracts_all_resources(self):
        result = self.parser.parse_bundle(SAMPLE_BUNDLE)
        assert "Patient" in result
        assert "Conditions" in result
        assert "Encounters" in result

    def test_parse_bundle_patient_demographics(self):
        result = self.parser.parse_bundle(SAMPLE_BUNDLE)
        patient = result["Patient"]
        assert patient["id"] == "test-patient-1"
        assert patient["gender"] == "female"
        assert patient["state"] == "GA"
        assert patient["city"] == "Atlanta"
        assert isinstance(patient["age"], int)
        assert patient["age"] > 0

    def test_extract_patient_summary(self):
        patient = SAMPLE_BUNDLE["entry"][0]["resource"]
        summary = self.parser.extract_patient_summary(patient)
        assert summary["gender"] == "female"
        assert summary["state"] == "GA"
        assert summary["id"] == "test-patient-1"

    def test_extract_conditions(self):
        conditions = [SAMPLE_BUNDLE["entry"][1]["resource"]]
        result = self.parser.extract_conditions(conditions)
        assert len(result) == 1
        assert result[0]["display"] == "Measles"
        assert result[0]["code"] == "186747009"
        assert result[0]["onset"] == "2026-05-01"

    def test_extract_observations_empty(self):
        result = self.parser.extract_observations([])
        assert result == []

    def test_extract_observations_with_quantity(self):
        obs = [
            {
                "resourceType": "Observation",
                "status": "final",
                "code": {
                    "coding": [
                        {"code": "8310-5", "display": "Body temperature"}
                    ]
                },
                "valueQuantity": {"value": 39.2, "unit": "Cel"},
                "effectiveDateTime": "2026-05-01",
            }
        ]
        result = self.parser.extract_observations(obs)
        assert len(result) == 1
        assert result[0]["display"] == "Body temperature"
        assert result[0]["value"] == 39.2
        assert result[0]["unit"] == "Cel"

    def test_to_triage_prompt_returns_string(self):
        parsed = self.parser.parse_bundle(SAMPLE_BUNDLE)
        prompt = self.parser.to_triage_prompt(parsed)
        assert isinstance(prompt, str)
        assert "Measles" in prompt

    def test_to_triage_prompt_contains_patient_info(self):
        parsed = self.parser.parse_bundle(SAMPLE_BUNDLE)
        prompt = self.parser.to_triage_prompt(parsed)
        assert "female" in prompt
        assert "GA" in prompt
        assert "Atlanta" in prompt

    def test_empty_bundle(self):
        empty_bundle = {"resourceType": "Bundle", "type": "document", "entry": []}
        result = self.parser.parse_bundle(empty_bundle)
        assert result["Patient"] == {}
        assert result["Conditions"] == []
        assert result["Observations"] == []

    def test_bundle_without_entries_key(self):
        bundle = {"resourceType": "Bundle", "type": "document"}
        result = self.parser.parse_bundle(bundle)
        assert result["Conditions"] == []
