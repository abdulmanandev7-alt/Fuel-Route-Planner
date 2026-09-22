import logging
from dataclasses import dataclass

import requests

from integrations.exceptions import UpstreamServiceError
from integrations.http import build_session, record_external_call

logger = logging.getLogger(__name__)

ADMINISTRATIVE_AREAS = frozenset({"country", "state", "region", "state_district", "county"})


@dataclass(frozen=True, slots=True)
class GeocodeResult:
    latitude: float
    longitude: float
    display_name: str
    state: str | None = None
    kind: str | None = None

    @property
    def is_administrative_area(self) -> bool:
        return self.kind in ADMINISTRATIVE_AREAS


class NominatimClient:
    def __init__(self, base_url: str, user_agent: str, timeout: float, session: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or build_session(user_agent)

    def search(self, query: str, settlements_only: bool = False) -> GeocodeResult | None:
        return self._search({"q": query, "countrycodes": "us"}, settlements_only)

    def search_city(self, city: str, state_name: str) -> GeocodeResult | None:
        return self._search({"city": city, "state": state_name, "country": "US"}, settlements_only=True)

    def _search(self, params: dict[str, str], settlements_only: bool) -> GeocodeResult | None:
        if settlements_only:
            params = {**params, "featureType": "settlement"}
        record_external_call()
        try:
            response = self.session.get(
                f"{self.base_url}/search",
                params={**params, "format": "jsonv2", "limit": 1, "addressdetails": 1},
                timeout=self.timeout,
            )
            response.raise_for_status()
            results = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Nominatim request failed: %s", exc)
            raise UpstreamServiceError("Geocoding service is unavailable") from exc

        if not results:
            return None
        first = results[0]
        return GeocodeResult(
            latitude=float(first["lat"]),
            longitude=float(first["lon"]),
            display_name=first.get("display_name", ""),
            state=first.get("address", {}).get("state"),
            kind=first.get("addresstype"),
        )
