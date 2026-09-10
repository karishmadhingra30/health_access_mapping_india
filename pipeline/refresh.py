from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import yaml

from pipeline.build_geojson import write_features, write_geodataframe
from pipeline.collect import osm
from pipeline.metrics import distance_grid, district_metrics
from pipeline.normalize import load_mapping, normalize


ROOT = Path(__file__).resolve().parents[1]
RAW, OUTPUT, INTERIM = ROOT / "data/raw", ROOT / "data/output", ROOT / "data/interim"


def clean_name(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def download(url: str, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        return
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    destination.write_bytes(response.content)


def get_boundaries(source: dict, force: bool) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, dict]:
    response = requests.get(source["url"], timeout=60)
    response.raise_for_status()
    boundary_file = RAW / "district_boundaries.geojson"
    download(response.json()["gjDownloadURL"], boundary_file, force)
    districts = gpd.read_file(boundary_file).rename(columns={"shapeName": "district"})
    state_response = requests.get("https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/", timeout=60)
    state_response.raise_for_status()
    state_meta = state_response.json()
    state_file = RAW / "state_boundaries.geojson"
    download(state_meta["gjDownloadURL"], state_file, force)
    states = gpd.read_file(state_file).rename(columns={"shapeName": "state"})
    states = states[states["state"].isin(["Kerala", "Uttar Pradesh"])][["state", "geometry"]].copy()
    districts = gpd.sjoin(districts[["district", "geometry"]], states, predicate="within", how="inner")
    districts = districts.drop(columns=["index_right"]).dissolve(by=["state", "district"], as_index=False)
    return states, districts, {"name": "geoBoundaries", "url": source["url"], "license": source["license"], "record_count": len(districts), "status": "retrieved"}


def get_population(source: dict, force: bool) -> tuple[dict[tuple[str, str], int], dict]:
    path = RAW / "census_2011_district_population.xlsx"
    download(source["url"], path, force)
    data = pd.read_excel(path, sheet_name="Data", dtype={"State": str, "District": str})
    data = data[(data["Level"] == "DISTRICT") & (data["TRU"] == "Total")]
    data["state"] = data["State"].str.zfill(2).map({"32": "Kerala", "09": "Uttar Pradesh"})
    data = data.dropna(subset=["state"])
    values = {(row.state, clean_name(row.Name)): int(row.TOT_P) for row in data.itertuples()}
    return values, {"name": "Census of India, Basic Population Figures 2011", "url": source["url"], "license": source["license"], "record_count": len(values), "status": "retrieved"}


def assign_districts(facilities: list[dict], districts: gpd.GeoDataFrame) -> list[dict]:
    if not facilities:
        return []
    points = gpd.GeoDataFrame(facilities, geometry=gpd.points_from_xy([f["longitude"] for f in facilities], [f["latitude"] for f in facilities]), crs="EPSG:4326")
    joined = gpd.sjoin(points, districts[["state", "district", "geometry"]], how="inner", predicate="within", lsuffix="facility", rsuffix="district")
    output = []
    fields = list(facilities[0])
    for _, row in joined.iterrows():
        item = {field: row.get(f"{field}_facility", row.get(field)) for field in fields}
        item["state"], item["district"] = row["state_district"], row["district_district"]
        output.append(item)
    return output


def run(force: bool) -> None:
    config = yaml.safe_load((ROOT / "config/sources.yaml").read_text(encoding="utf-8"))
    for folder in (RAW, OUTPUT, INTERIM):
        folder.mkdir(parents=True, exist_ok=True)
    refreshed_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    states, districts, boundary_report = get_boundaries(config["boundaries"], force)
    population, population_report = get_population(config["population_2011"], force)
    elements, osm_report = osm.collect(config["osm_facilities"], RAW, force)
    mapping = load_mapping(ROOT / "config/service_mapping.yaml")
    raw_facilities = [osm.to_facility(element) for element in elements]
    raw_facilities = [facility for facility in raw_facilities if facility]
    facilities = [normalize(item, mapping, refreshed_at) for item in assign_districts(raw_facilities, districts)]
    metric_districts = district_metrics(districts, facilities, population)
    grid = distance_grid(states, facilities)
    write_features(facilities, OUTPUT / "facilities.geojson")
    write_geodataframe(metric_districts, OUTPUT / "districts.geojson")
    write_geodataframe(grid, OUTPUT / "grid.geojson")
    exact = sum(item["geocode_precision"] == "exact" for item in facilities)
    metadata = {"refreshed_at": refreshed_at, "refresh_trigger": "manual GitHub Actions workflow_dispatch", "facility_count": len(facilities),
        "geocode_precision": {"exact": exact, "approximated": len(facilities) - exact}, "sources": [boundary_report, population_report, osm_report],
        "important_limitations": ["OSM is a supplemental open directory, not a complete government facility registry.", "Distance is straight-line distance to a mapped facility, not travel time.", "Per-capita values use Census 2011 populations and may not match current district boundaries.", "Facility listing does not establish service availability, staffing, stockouts, hours, affordability, or quality."]}
    payload = json.dumps(metadata, indent=2)
    (OUTPUT / "refresh_metadata.json").write_text(payload, encoding="utf-8")
    (INTERIM / "refresh_metadata.json").write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh the public data snapshot.")
    parser.add_argument("--force", action="store_true", help="Retrieve a fresh source snapshot instead of using local cached downloads.")
    run(**vars(parser.parse_args()))
