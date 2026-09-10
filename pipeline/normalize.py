from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


SCHEMA_FIELDS = ("id", "name", "facility_type", "sector", "state", "district", "block", "address_raw", "latitude", "longitude", "geocode_precision", "services", "services_raw", "source", "source_url", "retrieved_at")


def load_mapping(path: Path) -> dict[str, list[str]]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def normalize_services(raw: str, mapping: dict[str, list[str]]) -> list[str]:
    haystack = (raw or "").lower()
    return [tag for tag, terms in mapping.items() if any(term.lower() in haystack for term in terms)]


def normalize(record: dict[str, Any], mapping: dict[str, list[str]], retrieved_at: str) -> dict[str, Any]:
    result = {field: record.get(field) for field in SCHEMA_FIELDS}
    result["services"] = normalize_services(record.get("services_raw", ""), mapping)
    result["retrieved_at"] = retrieved_at
    return result
