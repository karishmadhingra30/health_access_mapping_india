from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

import geopandas as gpd
import numpy as np
from shapely.geometry import box


SERVICE_TAGS = ("family_planning", "contraception_supply", "iud_insertion", "sterilization", "antenatal_care", "delivery", "emergency_obstetric", "post_abortion_care", "mtp", "adolescent_health", "sti_treatment")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def district_metrics(districts: gpd.GeoDataFrame, facilities: list[dict[str, Any]], population: dict[tuple[str, str], int]) -> gpd.GeoDataFrame:
    counts = Counter((item["state"], item.get("district"), item["sector"]) for item in facilities if item.get("district"))
    services: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in facilities:
        if item.get("district"):
            services[(item["state"], item["district"])].update(item["services"])
    rows = []
    for _, row in districts.iterrows():
        key = (row["state"], row["district"])
        normalized_district = "".join(character for character in key[1].lower() if character.isalnum())
        pop = population.get((key[0], normalized_district))
        total = sum(counts[(key[0], key[1], sector)] for sector in ("government", "ngo", "private"))
        found = services[key]
        rows.append({**row.to_dict(), "population_2011": pop, "facility_count": total if pop is not None else None,
            "facilities_per_100k": round(total / pop * 100_000, 2) if pop else None,
            "government_count": counts[(key[0], key[1], "government")], "ngo_count": counts[(key[0], key[1], "ngo")], "private_count": counts[(key[0], key[1], "private")],
            "services_present": sorted(found), "services_missing": [tag for tag in SERVICE_TAGS if tag not in found], "services_available_count": len(found)})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=districts.crs)


def distance_grid(states: gpd.GeoDataFrame, facilities: list[dict[str, Any]], cell_km: float = 5) -> gpd.GeoDataFrame:
    """5 km-ish grid. This is a straight-line distance proxy, not travel time."""
    rows: list[dict[str, Any]] = []
    selected = [f for f in facilities if f.get("latitude") is not None]
    if not selected:
        return gpd.GeoDataFrame(rows, geometry=[], crs="EPSG:4326")
    for _, state in states.iterrows():
        minx, miny, maxx, maxy = state.geometry.bounds
        lat_step = cell_km / 110.574
        lon_step = cell_km / (111.320 * math.cos(math.radians((miny + maxy) / 2)))
        for x in np.arange(minx, maxx, lon_step):
            for y in np.arange(miny, maxy, lat_step):
                cell = box(x, y, x + lon_step, y + lat_step)
                centre = cell.centroid
                if not state.geometry.intersects(centre):
                    continue
                nearest = min(_haversine_km(centre.y, centre.x, f["latitude"], f["longitude"]) for f in selected)
                rows.append({"state": state["state"], "distance_km": round(nearest, 2), "geometry": cell})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
