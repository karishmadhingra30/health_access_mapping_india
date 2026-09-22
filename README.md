# Reproductive health access mapping: Kerala and Uttar Pradesh

A public, static Leaflet map comparing a snapshot of **mapped** reproductive-health-related facilities across Kerala and Uttar Pradesh. These states are deliberately contrasted: Kerala has substantially stronger health indicators while Uttar Pradesh has roughly six times Kerala’s 2011 population. The comparison is useful only when the map is candid about what its data can and cannot support.

## Public deployment and manual refresh

This project has no backend and is designed for the lowest-cost public deployment: **GitHub Pages + one manually triggered GitHub Actions workflow**.

1. Push this repository to its public GitHub remote.
2. In **Settings → Pages**, select **GitHub Actions** as the build source if GitHub asks for a source.
3. Open **Actions → Refresh data and deploy map → Run workflow**. This is the only refresh trigger; there is no schedule.
4. The workflow attempts to retrieve a fresh source snapshot, writes `data/output/*.geojson` plus `refresh_metadata.json` when the refresh completes, commits those published data changes to `main`, and deploys the static site. If an optional live source fails, or if one required state fails while another succeeds, the workflow still deploys the site shell with the last committed full public data and visible refresh metadata.

The deployed URL will be `https://karishmadhingra30.github.io/health_access_mapping_india/` once Pages has completed its first run. The committed output makes every published refresh reviewable in Git history. `refresh_metadata.json` records the exact refresh time, counts, location precision, source status, and limitations that apply to that snapshot.

The frontend uses OpenStreetMap standard raster tiles for the basemap, so the public map does not require a browser-exposed basemap API key. Attribution is kept visible in the map and footer.

## What the map measures

- **Facility points:** source-listed locations, filterable by the source’s sector tags.
- **Facilities per 100,000:** district facility count divided by Census 2011 population. The shared colour scale is deliberately the same in both states. Grey means **no data**, not zero facilities.
- **Service-type coverage:** the number of normalized service tags evidenced at least once in a district, with missing tags listed on click. It is evidence in a source directory, not a claim that a service is operating.
- **Distance:** nearest-facility **straight-line distance** across roughly 5 km grid cells. It is not road travel time and likely overstates practical access, especially in rural areas.

## Current coverage statement

The first source-enabled snapshot is intentionally conservative: it uses OpenStreetMap as an openly accessible supplemental directory, district boundaries from geoBoundaries, and a versioned extract of official Census 2011 denominators. It does **not** yet have an enabled facility-level government registry, NGO clinic directory, or vetted private-directory feed. Therefore it must not be interpreted as a complete count of facilities in either state.

There is no defensible coverage fraction yet: calculating one requires a reviewed official facility count for the same district, facility type, and boundary vintage. The project does not present an invented coverage percentage. Add a source only after running that single-district recall check and recording its outcome here.

## Important limits

Facility presence on a map does not show quality of care, staffing, stockouts, operating hours, affordability, travel safety, discrimination, referral capacity, or whether a listed service is available on a given day. MTP is legal in India under the MTP Act, but a tagged location is not proof of availability. Private coverage is especially incomplete. Population values are from **Census 2011**, because India has not published a newer full Census baseline; they should not be presented as current population estimates.

## Data sources

See [DATA_SOURCES.md](DATA_SOURCES.md) for every enabled source, licence/terms, collection method, current limitations, and the explicit list of sources that were not enabled.

See [PROJECT_GUIDE.md](PROJECT_GUIDE.md) for the architecture, stack, local run flow, major tradeoffs, and next-step roadmap.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pipeline.refresh --force
mkdir -p _site/data
cp -R site/. _site/
cp -R data/output/. _site/data/
python -m http.server 8000 --directory _site
```

Use `python -m pipeline.refresh` without `--force` to reuse local cached source responses. Raw inputs are intentionally not committed.

## Adding a source responsibly

Before enabling any source, document its URL, licence/terms, robots policy if it is web collection, date checked, field mapping, records retrieved, district coverage check, and known gaps in `DATA_SOURCES.md`. Preserve raw facts—not page text—and flag all non-exact locations with `geocode_precision`. Do not use account-gated aggregators, Google Places, or services whose terms do not allow this use.
