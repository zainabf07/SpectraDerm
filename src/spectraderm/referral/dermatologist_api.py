"""Transient, injected external dermatology-provider search infrastructure."""

from __future__ import annotations

import json
import logging
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from spectraderm.agents.referral_agent import DermatologistOption


logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Safe provider boundary error; message content is never returned to callers."""


class HttpJsonClient(Protocol):
    def get(self, endpoint: str, params: Mapping[str, str]) -> Mapping[str, Any]: ...


class DermatologistProvider(Protocol):
    def search_dermatologists(self, location: Mapping[str, Any], radius_meters: int, limit: int) -> Sequence[Mapping[str, Any]]: ...


@dataclass(frozen=True)
class ProviderRecord:
    provider_id: str | None
    name: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    distance_km: float | None
    distance_source: str | None
    provider_category: str | None
    rating: float | None
    opening_hours: str | None
    phone: str | None
    website: str | None
    source: str


@dataclass(frozen=True)
class ProviderSearchResult:
    success: bool
    providers: tuple[ProviderRecord, ...]
    source: str
    query_location_type: str | None
    error_code: str | None = None
    error_message: str | None = None


class UrllibJsonClient:
    """Small standard-library HTTP boundary; not used by tests."""

    def get(self, endpoint: str, params: Mapping[str, str]) -> Mapping[str, Any]:
        request = Request(f"{endpoint}?{urlencode(params)}", headers={"Accept": "application/json"})
        with urlopen(request, timeout=10) as response:  # nosec B310: endpoint is constructor configuration
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, Mapping):
            raise ProviderError("malformed provider response")
        return payload


class GooglePlacesProvider:
    """Production-oriented Google Places adapter with key/configuration injection."""

    def __init__(
        self, client: HttpJsonClient | None = None, api_key: str | None = None,
        api_key_environment: str = "GOOGLE_MAPS_API_KEY", endpoint: str = "https://maps.googleapis.com/maps/api/place",
    ) -> None:
        self._client = client or UrllibJsonClient()
        self._api_key = api_key if api_key is not None else os.getenv(api_key_environment)
        self._endpoint = endpoint.rstrip("/")

    def search_dermatologists(self, location: Mapping[str, Any], radius_meters: int, limit: int) -> Sequence[Mapping[str, Any]]:
        if not self._api_key:
            logger.warning("Google Places request skipped: no API key is configured.")
            raise ProviderError("provider authentication is not configured")
        params = {"key": self._api_key, "radius": str(radius_meters)}
        if "latitude" in location:
            endpoint = f"{self._endpoint}/nearbysearch/json"
            params.update({"location": f"{location['latitude']},{location['longitude']}", "keyword": "dermatology"})
        else:
            endpoint = f"{self._endpoint}/textsearch/json"
            params.update({"query": f"dermatology in {location['city']}"})
        try:
            response = self._client.get(endpoint, params)
        except Exception:
            logger.exception("Google Places request failed (network/transport error).")
            raise
        status = response.get("status")
        if status not in {None, "OK", "ZERO_RESULTS"}:
            # Google reports the real cause here (e.g. REQUEST_DENIED for a bad
            # or unauthorized key, OVER_QUERY_LIMIT for billing/quota issues).
            # Log it so a silently-empty referral list is diagnosable.
            logger.warning(
                "Google Places request failed: status=%s error_message=%s",
                status, response.get("error_message"),
            )
            raise ProviderError(f"external provider request failed: {status}")
        results = response.get("results", ())
        if not isinstance(results, Sequence) or isinstance(results, (str, bytes, Mapping)):
            raise ProviderError("malformed provider response")
        if any(not isinstance(item, Mapping) for item in results):
            raise ProviderError("malformed provider response")
        return tuple(results[:limit])


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _location(location: Any) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if not isinstance(location, Mapping):
        return None, None, "LOCATION_REQUIRED"
    city = _text(location.get("city") or location.get("location"))
    if city:
        return {"city": city}, "manual", None
    latitude, longitude = _number(location.get("latitude")), _number(location.get("longitude"))
    if latitude is None or longitude is None or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None, None, "INVALID_LOCATION"
    return {"latitude": latitude, "longitude": longitude}, "coordinates", None


def _distance_km(latitude: float, longitude: float, provider_latitude: float, provider_longitude: float) -> float:
    phi_1, phi_2 = math.radians(latitude), math.radians(provider_latitude)
    delta_phi, delta_lambda = math.radians(provider_latitude - latitude), math.radians(provider_longitude - longitude)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2) ** 2
    return round(6371.0088 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value)), 3)


def _opening_hours(raw: Mapping[str, Any]) -> str | None:
    value = raw.get("opening_hours")
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, Mapping):
        weekday_text = value.get("weekday_text")
        if isinstance(weekday_text, Sequence) and not isinstance(weekday_text, (str, bytes)):
            return "; ".join(str(item) for item in weekday_text) or None
    return None


def _normalise(raw: Mapping[str, Any], location: Mapping[str, Any], source: str) -> ProviderRecord:
    geometry = raw.get("geometry")
    coordinates = geometry.get("location") if isinstance(geometry, Mapping) else raw.get("location")
    coordinates = coordinates if isinstance(coordinates, Mapping) else {}
    latitude = _number(coordinates.get("lat") if "lat" in coordinates else raw.get("latitude"))
    longitude = _number(coordinates.get("lng") if "lng" in coordinates else raw.get("longitude"))
    external_distance = _number(raw.get("distance_km"))
    if external_distance is None:
        meters = _number(raw.get("distance_meters"))
        external_distance = meters / 1000 if meters is not None else None
    if external_distance is not None:
        distance, distance_source = external_distance, "external"
    elif "latitude" in location and latitude is not None and longitude is not None:
        distance, distance_source = _distance_km(location["latitude"], location["longitude"], latitude, longitude), "calculated"
    else:
        distance, distance_source = None, None
    types = raw.get("types")
    category = _text(raw.get("provider_category"))
    if category is None and isinstance(types, Sequence) and not isinstance(types, (str, bytes)):
        category = ", ".join(str(item) for item in types) or None
    return ProviderRecord(
        provider_id=_text(raw.get("place_id") or raw.get("provider_id")), name=_text(raw.get("name")),
        address=_text(raw.get("formatted_address") or raw.get("vicinity") or raw.get("address")), latitude=latitude,
        longitude=longitude, distance_km=distance, distance_source=distance_source, provider_category=category,
        rating=_number(raw.get("rating")), opening_hours=_opening_hours(raw),
        phone=_text(raw.get("formatted_phone_number") or raw.get("phone")), website=_text(raw.get("website")), source=source,
    )


class DermatologistSearchService:
    """Validate transient search input and return normalized, non-medical records."""

    def __init__(self, provider: DermatologistProvider, source: str = "external_provider") -> None:
        self._provider, self._source = provider, source

    def search_dermatologists(self, location: Any, radius_meters: int = 5000, limit: int = 10) -> ProviderSearchResult:
        safe_location, location_type, location_error = _location(location)
        if location_error:
            message = "A search location is required." if location_error == "LOCATION_REQUIRED" else "A valid manual location or coordinates are required."
            return ProviderSearchResult(False, (), self._source, None, location_error, message)
        if not isinstance(radius_meters, int) or isinstance(radius_meters, bool) or not 1 <= radius_meters <= 50000:
            return ProviderSearchResult(False, (), self._source, location_type, "INVALID_RADIUS", "radius_meters must be an integer from 1 to 50000.")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            return ProviderSearchResult(False, (), self._source, location_type, "INVALID_LIMIT", "limit must be an integer from 1 to 20.")
        try:
            raw_results = self._provider.search_dermatologists(safe_location, radius_meters, limit)
            if not isinstance(raw_results, Sequence) or isinstance(raw_results, (str, bytes, Mapping)) or any(not isinstance(item, Mapping) for item in raw_results):
                raise ProviderError("malformed provider response")
            records = tuple(_normalise(item, safe_location, self._source) for item in raw_results[:limit])
            return ProviderSearchResult(True, records, self._source, location_type)
        except ProviderError as error:
            logger.warning("Dermatologist provider search unavailable: %s", error)
            return ProviderSearchResult(False, (), self._source, location_type, "PROVIDER_UNAVAILABLE", "Provider search is currently unavailable.")
        except Exception:
            logger.exception("Unexpected error during dermatologist provider search.")
            return ProviderSearchResult(False, (), self._source, location_type, "PROVIDER_UNAVAILABLE", "Provider search is currently unavailable.")

    def find_dermatologists(self, location: Mapping[str, Any], radius_km: float, specialty: str = "dermatology") -> tuple[DermatologistOption, ...]:
        """AC-compatible adapter; it always requests broad dermatology only."""
        if not isinstance(radius_km, (int, float)) or isinstance(radius_km, bool) or not math.isfinite(radius_km) or radius_km <= 0:
            return ()
        if not isinstance(specialty, str) or specialty.casefold() != "dermatology":
            return ()
        result = self.search_dermatologists(location, radius_meters=round(float(radius_km) * 1000))
        if not result.success:
            # An unavailable provider (missing key, network or upstream error)
            # must surface as a provider error, not as "no dermatologists found".
            if result.error_code == "PROVIDER_UNAVAILABLE":
                raise ProviderError(result.error_message or "Provider search is currently unavailable.")
            return ()
        return tuple(DermatologistOption(
            name=item.name, address=item.address, specialty=item.provider_category, distance_km=item.distance_km,
            opening_hours=item.opening_hours, phone=item.phone, website=item.website, source=item.source,
        ) for item in result.providers)
