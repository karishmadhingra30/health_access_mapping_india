from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd


def write_features(records: list[dict[str, Any]], destination: Path) -> None:
    features = []
    for item in records:
        props = {key: value for key, value in item.items() if key not in {"latitude", "longitude"}}
        features.append({"type": "Feature", "properties": props, "geometry": {"type": "Point", "coordinates": [item["longitude"], item["latitude"]]}})
    destination.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")


def write_geodataframe(frame: gpd.GeoDataFrame, destination: Path) -> None:
    destination.write_text(frame.to_json() if not frame.empty else '{"type":"FeatureCollection","features":[]}', encoding="utf-8")
