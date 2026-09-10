from __future__ import annotations

from pathlib import Path
from typing import Any

import requests


OVERPASS_QUERY = """[out:json][timeout:{timeout}];
area[\"ISO3166-2\"=\"IN-KL\"]->.kerala;
area[\"ISO3166-2\"=\"IN-UP\"]->.uttar_pradesh;
(
  nwr[\"amenity\"~\"^(clinic|hospital|doctors)$\"](area.kerala);
  nwr[\"amenity\"~\"^(clinic|hospital|doctors)$\"](area.uttar_pradesh);
  nwr[\"healthcare\"~\"^(clinic|hospital|doctor)$\"](area.kerala);
  nwr[\"healthcare\"~\"^(clinic|hospital|doctor)$\"](area.uttar_pradesh);
);
out center tags;"""


def collect(config: dict[str, Any], raw_dir: Path, force: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch openly mapped facilities. OSM is supplemental, never a completeness claim."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache_path = raw_dir / "osm_overpass.json"
    query = OVERPASS_QUERY.format(timeout=config.get("query_timeout_seconds", 300))
    if cache_path.exists() and not force:
        payload = __import__("json").loads(cache_path.read_text(encoding="utf-8"))
    else:
        response = requests.post(
            config["url"], data={"data": query}, timeout=360,
            headers={"User-Agent": config["user_agent"]},
        )
        response.raise_for_status()
        cache_path.write_text(response.text, encoding="utf-8")
        payload = response.json()
    return payload.get("elements", []), {
        "name": "OpenStreetMap / Overpass",
        "url": config["url"],
        "license": config["license"],
        "record_count": len(payload.get("elements", [])),
        "cache": str(cache_path),
        "status": "retrieved",
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
