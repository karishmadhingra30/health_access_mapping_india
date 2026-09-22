# Data sources and collection status

This page records the sources actually enabled in the public build. A directory is not enabled merely because it could be useful: it must have a documented, open retrieval route and be suitable for repeatable public use.

| Source | What it provides | Licence / terms | Automated collection | Date checked | Published record count | Known gaps |
| --- | --- | --- | --- | --- | --- | --- |
| [geoBoundaries India ADM1/ADM2](https://www.geoboundaries.org/api.html) | State and district geometries used to select Kerala and Uttar Pradesh and aggregate metrics | `gbOpen` is CC BY 4.0; attribution required | API download, cached locally during a run | 2026-09-10 | Written to `data/output/districts.geojson` after each successful refresh | Boundary vintage may not align exactly with Census 2011 districts; this is explicitly visible as no-data when population cannot be matched. |
| [Census of India: Basic Population Figures, 2011](https://censusindia.gov.in/nada/index.php/catalog/42557/download/46183/2011-IndiaStateDist-0000.xlsx) | District population denominator | Government of India public data | Reviewed, normalized extract versioned in `data/reference/census_2011_district_population.csv`; it is fixed historical data and is not re-fetched per refresh | 2026-09-10 | 14 Kerala and 71 Uttar Pradesh Census-2011 district records | Census 2011 is the latest full Census baseline, not a current population estimate. District boundary/name changes can prevent a match. |
| [OpenStreetMap via Overpass API](https://overpass-api.de/) | Openly mapped hospitals, clinics, and doctors | ODbL 1.0; OSM attribution and licence obligations apply | One bounded query per required state during manual refresh; raw JSON cached locally. No scraping of rendered webpages. | 2026-09-10 | Logged in `data/output/refresh_metadata.json` after each successful or preserved refresh | Supplemental directory only. Facility type, ownership, service tags, and completeness depend on volunteer mapping. It cannot be used to claim all facilities or service availability. |

## Deliberately not enabled yet

The project does **not** currently make a facility-count claim from a national or state government directory, FPAI/Janani, or a private aggregator. During this build, an openly documented, facility-level export with sufficiently clear terms was not verified for automatic collection. The generic government CSV collector is present, but only accepts sources explicitly added to `config/sources.yaml` with fields, licence/terms, and a data-quality note.

This is a substantive limitation rather than a blank to paper over. Until an official facility-level export is added and coverage checked against Rural Health Statistics, the map should be read as a map of the published open-directory snapshot—not a map of every reproductive-health service.

## Collection safeguards

- Raw responses are cached in `data/raw/`, which is excluded from Git. A local rerun without `--force` uses that cache.
- The manual GitHub refresh intentionally uses `--force` to obtain a new snapshot; it makes bounded Overpass requests per required state, uses a transparent user agent, and does not require an account.
- The map retains only facility facts needed to audit the indicator: name, location, category/sector, service tags, source link, and retrieval timestamp.
- Any future HTML collection must document robots.txt and terms here before being enabled. Account-gated or restrictive aggregators are out of scope.
