"""Tests for TriageEngine."""

import pytest
from src.triage_engine import TriageEngine, PRIORITY_LEVELS


class TestTriageEngine:
    """Test suite for TriageEngine."""

    def setup_method(self):
        self.engine = TriageEngine()

    def test_priority_levels_defined(self):
        assert "urgent" in PRIORITY_LEVELS
        assert "high" in PRIORITY_LEVELS
        assert "routine" in PRIORITY_LEVELS
        assert "low" in PRIORITY_LEVELS

    @pytest.mark.skip(reason="Requires API key — integration test")
    def test_triage_returns_valid_priority(self):
        sample_prompt = """
        Patient: 41-year-old female, Atlanta, GA
        Condition: Measles (SNOMED 186747009), onset 2026-05-01
        Encounter: Ambulatory, 2026-05-01
        Observations: Temperature 39.2°C, Rash present
        """
        result = self.engine.triage(sample_prompt)
        assert result["priority"] in PRIORITY_LEVELS
        assert "rationale" in result

    @pytest.mark.skip(reason="Requires API key — integration test")
    def test_triage_batch_returns_sorted(self):
        cases = ["case prompt 1", "case prompt 2"]
        results = self.engine.triage_batch(cases)
        assert len(results) == 2
