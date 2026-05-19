"""
Utility helpers for eCR-Triage.
"""

import os
import json
import logging
from datetime import datetime, date
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def load_config(path: str = "configs/fhir_server.yaml") -> dict:
    """Load YAML configuration file."""
    with open(path) as f:
        return yaml.safe_load(f)


def calculate_age(birth_date_str: str) -> int:
    """Calculate age from a FHIR-format date string (YYYY-MM-DD)."""
    birth = date.fromisoformat(birth_date_str)
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def save_json(data: dict | list, filepath: str) -> None:
    """Save data to a JSON file, creating directories as needed."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info(f"Saved: {filepath}")


def load_json(filepath: str) -> dict | list:
    """Load data from a JSON file."""
    with open(filepath) as f:
        return json.load(f)


def setup_logging(level: str = None) -> None:
    """Configure logging for the project."""
    level = level or os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
