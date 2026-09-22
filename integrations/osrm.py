import logging
from dataclasses import dataclass

import requests

from integrations.exceptions import NoRouteError, UpstreamServiceError
from integrations.http import build_session, record_external_call

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OsrmRoute:
    distance_meters: float
    duration_seconds: float
    geometry: str  # encoded polyline, precision 5


class OsrmClient:
    def __init__(self, base_url: str, user_agent: str, timeout: float, session: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or build_session(user_agent)

    def route(self, start: tuple[float, float], finish: tuple[float, float]) -> OsrmRoute:
        coordinates = f"{start[1]},{start[0]};{finish[1]},{finish[0]}"
        record_external_call()
        try:
            response = self.session.get(
                f"{self.base_url}/route/v1/driving/{coordinates}",
                params={"overview": "full", "geometries": "polyline", "steps": "false"},
                timeout=self.timeout,
            )
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("OSRM request failed: %s", exc)
            raise UpstreamServiceError("Routing service is unavailable") from exc

        code = payload.get("code")
        if code == "NoRoute":
            raise NoRouteError("No driveable route found between the given locations")
        if code != "Ok" or not payload.get("routes"):
            logger.warning("OSRM returned %s: %s", code, payload.get("message"))
            raise UpstreamServiceError("Routing service returned an unexpected response")

        route = payload["routes"][0]
        return OsrmRoute(
            distance_meters=float(route["distance"]),
            duration_seconds=float(route["duration"]),
            geometry=route["geometry"],
        )
