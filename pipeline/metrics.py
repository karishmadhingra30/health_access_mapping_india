from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import geopandas as gpd
import numpy as np
from shapely.geometry import box
from shapely.strtree import STRtree


SERVICE_TAGS = ("family_planning", "contraception_supply", "iud_insertion", "sterilization", "antenatal_care", "delivery", "emergency_obstetric", "post_abortion_care", "mtp", "adolescent_health", "sti_treatment")


def _utm_crs(longitude: float) -> str:
    zone = int((longitude + 180) // 6) + 1
    return f"EPSG:{32600 + zone}"


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
        state_facilities = [f for f in selected if f.get("state") == state["state"]] or selected
        crs = _utm_crs(state.geometry.centroid.x)
        state_geom = gpd.GeoSeries([state.geometry], crs="EPSG:4326").to_crs(crs).iloc[0]
        facility_points = gpd.GeoSeries(gpd.points_from_xy([f["longitude"] for f in state_facilities], [f["latitude"] for f in state_facilities]), crs="EPSG:4326").to_crs(crs)
        tree = STRtree(list(facility_points))
        cell_size_m = cell_km * 1000
        minx, miny, maxx, maxy = state_geom.bounds
        cells = []
        centres = []
        for x in np.arange(minx, maxx, cell_size_m):
            for y in np.arange(miny, maxy, cell_size_m):
                cell = box(x, y, x + cell_size_m, y + cell_size_m)
                centre = cell.centroid
                if not state_geom.intersects(centre):
                    continue
                cells.append(cell)
                centres.append(centre)
        if not cells:
            continue
        nearest_indices = tree.nearest(centres)
        projected = gpd.GeoSeries(cells, crs=crs).to_crs("EPSG:4326")
        for cell, centre, nearest_index in zip(projected, centres, nearest_indices):
            distance_km = centre.distance(facility_points.iloc[int(nearest_index)]) / 1000
            rows.append({"state": state["state"], "distance_km": round(distance_km, 2), "geometry": cell})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
