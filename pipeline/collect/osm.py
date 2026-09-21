from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


STATE_AREAS = {
    "Kerala": "IN-KL",
    "Uttar Pradesh": "IN-UP",
}

OVERPASS_QUERY = """[out:json][timeout:{timeout}];
area[\"ISO3166-2\"=\"{iso_code}\"]->.searchArea;
(
  nwr[\"amenity\"~\"^(clinic|hospital|doctors)$\"](area.searchArea);
  nwr[\"healthcare\"~\"^(clinic|hospital|doctor)$\"](area.searchArea);
);
out center tags;"""


def _cache_name(iso_code: str) -> str:
    return f"osm_overpass_{iso_code.lower().replace('-', '_')}.json"


def _fetch_state(config: dict[str, Any], raw_dir: Path, force: bool, state: str, iso_code: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cache_path = raw_dir / _cache_name(iso_code)
    if cache_path.exists() and not force:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return payload.get("elements", []), {"state": state, "record_count": len(payload.get("elements", [])), "status": "cache"}

    query = OVERPASS_QUERY.format(timeout=config.get("query_timeout_seconds", 180), iso_code=iso_code)
    print(f"Fetching OpenStreetMap facilities for {state} ({iso_code})...")
    try:
        response = requests.post(
            config["url"],
            data={"data": query},
            timeout=config.get("request_timeout_seconds", 240),
            headers={"User-Agent": config["user_agent"]},
        )
        response.raise_for_status()
        payload = response.json()
        cache_path.write_text(response.text, encoding="utf-8")
        return payload.get("elements", []), {"state": state, "record_count": len(payload.get("elements", [])), "status": "retrieved"}
    except (requests.RequestException, ValueError) as exc:
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return payload.get("elements", []), {
                "state": state,
                "record_count": len(payload.get("elements", [])),
                "status": "stale_cache_after_error",
                "error": f"{type(exc).__name__}: {exc}",
            }
        return [], {"state": state, "record_count": 0, "status": "failed", "error": f"{type(exc).__name__}: {exc}"}


def collect(config: dict[str, Any], raw_dir: Path, force: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch openly mapped facilities. OSM is supplemental, never a completeness claim."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    elements: list[dict[str, Any]] = []
    state_reports: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for state, iso_code in STATE_AREAS.items():
        state_elements, report = _fetch_state(config, raw_dir, force, state, iso_code)
        state_reports.append(report)
        for element in state_elements:
            key = (str(element.get("type", "")), str(element.get("id", "")))
            if key in seen:
                continue
            seen.add(key)
            elements.append(element)

    failed = [item for item in state_reports if item["status"] == "failed"]
    stale = [item for item in state_reports if item["status"] == "stale_cache_after_error"]
    status = "retrieved"
    if failed and len(failed) == len(state_reports):
        status = "failed"
    elif failed or stale:
        status = "partial"
    return elements, {
        "name": "OpenStreetMap / Overpass",
        "url": config["url"],
        "license": config["license"],
        "record_count": len(elements),
        "state_reports": state_reports,
        "status": status,
    }


def to_facility(element: dict[str, Any]) -> dict[str, Any] | None:
    tags = element.get("tags", {})
    lat = element.get("lat") or element.get("center", {}).get("lat")
    lon = element.get("lon") or element.get("center", {}).get("lon")
    if lat is None or lon is None:
        return None
    amenity = tags.get("amenity") or tags.get("healthcare")
    facility_type = "district_hospital" if amenity == "hospital" and "district" in tags.get("name", "").lower() else "private_clinic"
    government = any(value.lower() in {"government", "public", "govt"} for value in [tags.get("operator:type", ""), tags.get("ownership", ""), tags.get("operator", "")])
    if government:
        facility_type = "district_hospital" if amenity == "hospital" else "phc"
    return {
        "id": f"osm-{element.get('type')}-{element.get('id')}",
        "name": tags.get("name") or f"Unnamed mapped {amenity}",
        "facility_type": facility_type,
        "sector": "government" if government else "private",
        "state": None, "district": None, "block": None,
        "address_raw": ", ".join(filter(None, [tags.get("addr:street"), tags.get("addr:city"), tags.get("addr:postcode")])),
        "latitude": float(lat), "longitude": float(lon), "geocode_precision": "exact",
        "services_raw": "; ".join(f"{key}={value}" for key, value in tags.items() if key.startswith("healthcare") or key.startswith("medical") or key == "amenity"),
        "source": "OpenStreetMap / Overpass",
        "source_url": f"https://www.openstreetmap.org/{element.get('type')}/{element.get('id')}",
    }
