"""Collector contract for reviewed government facility CSV/GeoJSON exports.

The repository intentionally ships with no enabled government scrape until an
open, facility-level government export and its terms are recorded in sources.yaml
and DATA_SOURCES.md. This avoids turning absent evidence into false zeroes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests


def collect_csv(source: dict[str, Any], raw_dir: Path) -> list[dict[str, Any]]:
    """Download one reviewed CSV and map its declared fields to the common schema."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / source["cache_name"]
    if not path.exists():
        response = requests.get(source["url"], headers={"User-Agent": source["user_agent"]}, timeout=120)
        response.raise_for_status()
        path.write_bytes(response.content)
    frame = pd.read_csv(path)
    fields = source["fields"]
    records = []
    for _, row in frame.iterrows():
        records.append({key: row.get(column) for key, column in fields.items()} | {"sector": "government", "source": source["source_name"], "source_url": source["url"]})
    return records
