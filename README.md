# Fuel Route Planner API

A Django REST API that plans a road trip between two locations in the USA, returns the route for a map,
and picks the most cost-effective places to refuel using real truck-stop fuel prices.

- Vehicle range: 500 miles, fuel economy: 10 mpg (both configurable).
- Fuel prices come from the supplied OPIS price list (6,626 US stations after de-duplication).
- Routing uses the free [OSRM](http://project-osrm.org/) demo server; geocoding uses [Nominatim](https://nominatim.org/).
- One external call per request in the common case, zero on repeat requests (cached), never more than three.

## Quick start

```bash
git clone <repo-url> && cd <repo>
python -m venv .venv
.venv/Scripts/activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py import_stations  # loads the CSV plus pre-geocoded coordinates, takes ~2 seconds
python manage.py runserver
```

Then open <http://127.0.0.1:8000/?start=New%20York,%20NY&finish=Los%20Angeles,%20CA> for the interactive map, or call the API:

```bash
curl "http://127.0.0.1:8000/api/route/?start=New%20York,%20NY&finish=Los%20Angeles,%20CA"
```

Requires Python 3.12+ (developed on 3.13 with Django 6.1).

## API

### `GET /api/route/?start=<location>&finish=<location>`

`POST /api/route/` with a JSON body `{"start": "...", "finish": "..."}` is also accepted.

A location can be:

| Input | Example | External calls needed |
|-------|---------|-----------------------|
| Coordinates `lat,lon` | `41.8781,-87.6298` | none |
| City and state | `Chicago, IL`, `Chicago, Illinois` | none (local gazetteer: the largest US cities plus every station city) |
| City only | `New York`, `Chicago` | none when the name is a major city or a unique station city; ambiguous names go to Nominatim |
| Anything else | `Denver International Airport` | one Nominatim call (cached for 7 days); a second call if the first answer is a state or county, so `Washington` means the city |

Both locations must be within the USA.

### Response

New York to Los Angeles, trimmed to the first of nine stops:

```json
{
  "start": {"query": "New York, NY", "label": "New York, New York, United States", "latitude": 40.712728, "longitude": -74.006015},
  "finish": {"query": "Los Angeles, CA", "label": "Los Angeles, California, United States", "latitude": 34.053691, "longitude": -118.242766},
  "distance_miles": 2794.0,
  "duration_hours": 49.8,
  "vehicle": {"range_miles": 500.0, "mpg": 10.0, "tank_gallons": 50.0, "starting_fuel_gallons": 50.0},
  "fuel_stops": [
    {
      "stop_number": 1,
      "station": {"opis_id": 72445, "name": "SHEETZ #639", "address": "I-80 Exit 223", "city": "Youngstown", "state": "OH", "latitude": 41.103579, "longitude": -80.652016},
      "location": {"latitude": 41.150756, "longitude": -80.672537},
      "distance_from_start_miles": 390.6,
      "distance_from_route_miles": 3.4,
      "price_per_gallon": 3.059,
      "gallons": 5.49,
      "cost": 16.78,
      "fuel_before_gallons": 10.94,
      "fuel_after_gallons": 16.43
    }
  ],
  "total_fuel_cost": 694.51,
  "total_fuel_gallons": 229.4,
  "fuel_used_gallons": 279.4,
  "fuel_remaining_gallons": 0.0,
  "stations_considered": 456,
  "map_url": "http://127.0.0.1:8000/?start=New+York%2C+NY&finish=Los+Angeles%2C+CA",
  "meta": {"external_api_calls": 1, "processing_ms": 1352.7},
  "route": {"geometry_format": "polyline5", "geometry": "a{wwFrhtbM..."}
}
```

Each stop carries two coordinate pairs: `station.latitude/longitude` is the geocoded city centre used to match
the station to the route, and `location` is the point on the route nearest that city, which is where the
station's highway exit is and where the map draws the marker. `distance_from_route_miles` is the gap between the two.

`route.geometry` is the full-resolution route as a Google encoded polyline (precision 5), the compact
format OSRM, Google and Mapbox all use. `map_url` opens the same trip on the built-in Leaflet map.

### `GET /api/places/?q=<text>&limit=8`

Autocomplete for the map page. Returns US cities whose name starts with the text, the largest cities first
(in population order) and then every city with a fuel station, optionally narrowed by a state after a comma
(`chi, il` or `chi, illinois`). Served entirely from local data, so typing never triggers an external call.

```json
[{"label": "Chicago, IL", "city": "Chicago", "state": "IL", "latitude": 41.875562, "longitude": -87.624421}]
```

### Errors

All errors share one shape: `{"error": {"code": "...", "message": "..."}}`.

| Status | Code | When |
|--------|------|------|
| 400 | `invalid_request` | Missing or malformed parameters (`details` lists the fields) |
| 422 | `location_not_found` | A location could not be resolved to a place in the USA |
| 422 | `route_not_found` | No driveable route between the two points |
| 422 | `trip_not_feasible` | A gap between usable stations exceeds the vehicle range |
| 503 | `upstream_unavailable` | OSRM or Nominatim did not respond |
| 503 | `stations_not_loaded` | `import_stations` has not been run yet |

## Map page

`GET /` serves a small Leaflet page that calls the API and draws the route, the start and finish markers and
each fuel stop with a popup (price, gallons, cost). The Start and Finish inputs autocomplete from
`/api/places/` (largest cities first, then station towns), and the panel shows the resolved locations, trip
totals, the stop list and how many external
calls the request needed. Map tiles are loaded by the browser straight from Esri's key-free World Street Map
service, so they never count against the server-side call budget; set `MAP_TILE_URL` to use another provider
(for example OpenStreetMap's own tiles, which block some browsers and proxies).

## How a request is served

1. **Resolve locations** (`trips/services/locations.py`). Coordinates are parsed directly, `City, ST` inputs are
   looked up in a local gazetteer (the largest US cities in `data/major_cities.json` plus the 3,800 station cities),
   and anything else goes to Nominatim with a 7-day cache.
2. **Fetch the route** (`trips/services/routing.py`). A single OSRM request returns distance, duration and the full
   geometry. Routes are cached for 24 hours keyed by rounded coordinates.
3. **Find stations along the route** (`trips/services/corridor.py`). The route is sampled every mile and each
   sample queries an in-memory grid index of all stations (`stations/index.py`), keeping every station within
   10 miles of the road together with its position along the route. This is pure Python and takes tens of
   milliseconds even for a coast-to-coast trip.
4. **Plan the fuel stops** (`trips/services/fuel_planner.py`). The classic greedy algorithm for the fixed-route
   gas station problem, which is provably cost-optimal: at each station, if a cheaper station is reachable on a
   full tank, buy just enough fuel to get there; otherwise fill up (or buy just enough to finish) and continue to
   the cheapest reachable station. A consolidation pass then folds stops into their neighbours, cheapest merge
   first, as long as the plan stays within `EXTRA_COST_TOLERANCE_USD` (default $2) of the optimal cost, so the
   plan never asks a driver to pull over for three gallons to save a few cents.
5. **Serialize** the plan, including the number of external calls actually made and the processing time.

Typical timings on a laptop: 300 ms for a regional trip to about 1.4 s for New York to Los Angeles on a first
request (dominated by the OSRM response time; add about a second per free-text place that needs Nominatim),
and 20 to 250 ms when the route is cached, depending on its length. New York to Los Angeles considers 456
stations along 2,794 miles of road.

## Assumptions

- The vehicle starts with a full tank (50 gallons). Trips shorter than 500 miles therefore need no stop and
  cost nothing extra; the response still reports `fuel_used_gallons` and `fuel_remaining_gallons`.
- Reported cost is the fuel purchased en route. The vehicle may arrive with an empty tank.
- "Optimal" means cost-optimal with one practical adjustment: the plan may spend up to $2 more than the strict
  optimum to avoid tiny top-up stops, since a real driver would not pull over for that.
- Station coordinates are city centroids: the price file only carries a highway/exit description and a city,
  so each city was geocoded once with Nominatim (`data/city_coordinates.json`). Stations count as being on
  the route when their city is within `STATION_CORRIDOR_MILES` (10) of the road, and each stop is placed at
  the point on the route nearest its city, which approximates the highway exit named in the address.
- When the price file lists the same station several times, the lowest price is used. Canadian rows are ignored.
- Range and economy are settings rather than request parameters, since the assignment fixes them at 500 miles and 10 mpg.

## Station data pipeline

```bash
python manage.py import_stations              # parse the CSV, attach cached coordinates, upsert into SQLite
python manage.py geocode_stations             # only needed for cities missing from data/city_coordinates.json
```

`geocode_stations` respects the Nominatim usage policy (one request per second, identifying User-Agent) and
writes results back to the JSON cache, so the repository ships ready to run without any geocoding.

## Configuration

Copy `.env.example` to `.env` to override defaults. Notable settings:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OSRM_BASE_URL` | `https://router.project-osrm.org` | Routing service (point at a self-hosted OSRM for production) |
| `NOMINATIM_USER_AGENT` | `fuel-route-planner/1.0` | Required by the Nominatim policy; add a contact email |
| `VEHICLE_RANGE_MILES` / `VEHICLE_MPG` | `500` / `10` | Vehicle parameters |
| `STATION_CORRIDOR_MILES` | `10` | How far off the road a station may be |
| `EXTRA_COST_TOLERANCE_USD` | `2` | How much more than the optimal cost the plan may spend to avoid unnecessary stops (0 = strictly optimal) |
| `ROUTE_CACHE_SECONDS` / `GEOCODE_CACHE_SECONDS` | 1 day / 7 days | Cache lifetimes |
| `MAP_TILE_URL` / `MAP_TILE_ATTRIBUTION` | Esri World Street Map | Raster tiles for the map page (any Leaflet URL template) |

The cache backend is the Django in-memory cache; swap `CACHES` for Redis to share it across processes.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
ruff check . && ruff format --check .
```

The suite covers the polyline codec, distance maths, CSV import rules, the spatial index, the corridor search,
the planner (including infeasible trips and tank-cap behaviour), location resolution and the API contract.
External services are faked, so tests never touch the network.

## Project layout

```
config/            Django settings and root URL configuration
geo/               Pure geometry helpers: haversine, polyline codec, US states
integrations/      HTTP clients for Nominatim and OSRM, external-call accounting
stations/          FuelStation model, CSV importer, spatial index, management commands
trips/             API view, serializers, planning services, Leaflet map page
data/              Fuel price CSV and the geocoded city coordinates
postman/           Postman collection with ready-made requests
```
