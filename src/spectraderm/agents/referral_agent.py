"""Deterministic referral orchestration after the Module AA safety decision.

This module intentionally has no geolocation, API, credential, image, or model
dependency.  A caller supplies a location and injects a provider search service.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class DermatologistOption:
    """Normalized business information returned by a provider search service."""

    name: str | None = None
    address: str | None = None
    specialty: str | None = None
    distance_km: float | None = None
    opening_hours: str | None = None
    phone: str | None = None
    website: str | None = None
    source: str | None = None


class DermatologistSearchProvider(Protocol):
    """External search boundary; Module AI will provide a real implementation."""

    def find_dermatologists(
        self, location: Mapping[str, Any], radius_km: float, specialty: str = "dermatology"
    ) -> Sequence[DermatologistOption]:
        """Return already-normalized broad dermatology provider data."""


@dataclass(frozen=True)
class ReferralAgentInput:
    """Inputs consumed transiently for one referral search."""

    safety_result: Any | None = None
    location: Mapping[str, Any] | None = None
    radius_km: float = 25.0


@dataclass(frozen=True)
class ReferralAgentResult:
    status: str
    professional_assessment_recommended: bool
    location_used: Mapping[str, Any] | None
    options: tuple[DermatologistOption, ...]
    reason: str
    safety_message: str
    metadata: Mapping[str, Any]


_SAFETY_MESSAGE = (
    "Professional assessment was recommended by the Safety Agent. The listed dermatology providers are referral "
    "options based on available location and provider information. This is not a diagnosis."
)
_NOT_REQUIRED_MESSAGE = (
    "No referral search was performed because professional assessment was not recommended by the Safety Agent. "
    "This is not a diagnosis."
)


def _field(value: Any, name: str) -> Any | None:
    return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)


def _text_or_none(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalise_location(location: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Copy only supported location fields; never retain the caller's mapping."""
    if not isinstance(location, Mapping):
        return None
    latitude, longitude = _number_or_none(location.get("latitude")), _number_or_none(location.get("longitude"))
    if latitude is not None and longitude is not None:
        return {"latitude": latitude, "longitude": longitude}
    city = _text_or_none(location.get("city"))
    if city:
        return {"city": city}
    supplied = _text_or_none(location.get("location"))
    return {"location": supplied} if supplied else None


def _normalise_option(value: DermatologistOption | Mapping[str, Any] | Any) -> DermatologistOption:
    """Copy provider fields without supplying values that the provider did not return."""
    return DermatologistOption(
        name=_text_or_none(_field(value, "name")),
        address=_text_or_none(_field(value, "address")),
        specialty=_text_or_none(_field(value, "specialty")),
        distance_km=_number_or_none(_field(value, "distance_km")),
        opening_hours=_text_or_none(_field(value, "opening_hours")),
        phone=_text_or_none(_field(value, "phone")),
        website=_text_or_none(_field(value, "website")),
        source=_text_or_none(_field(value, "source")),
    )


def _rank_key(option: DermatologistOption) -> tuple[Any, ...]:
    specialty_match = "dermatology" in (option.specialty or "").casefold()
    return (
        0 if specialty_match else 1,
        option.distance_km if option.distance_km is not None else float("inf"),
        0 if option.opening_hours is not None else 1,
        (option.name or "").casefold(),
        (option.address or "").casefold(),
        (option.source or "").casefold(),
    )


class ReferralAgent:
    """Run a broad, neutral referral search only after the AA gate is affirmative."""

    def __init__(self, provider: DermatologistSearchProvider):
        self._provider = provider

    def refer(self, agent_input: ReferralAgentInput) -> ReferralAgentResult:
        if not isinstance(agent_input, ReferralAgentInput):
            raise TypeError("agent_input must be a ReferralAgentInput")
        decision = _field(agent_input.safety_result, "professional_assessment_recommended")
        base_metadata = {"radius_km": agent_input.radius_km, "specialty_requested": "dermatology"}
        if decision is None:
            return ReferralAgentResult(
                "not_required", False, None, (), "The Safety Agent referral decision was not supplied.",
                _NOT_REQUIRED_MESSAGE, {**base_metadata, "decision_available": False, "provider_search_performed": False},
            )
        if decision is not True:
            return ReferralAgentResult(
                "not_required", False, None, (), "Professional assessment was not recommended by the Safety Agent.",
                _NOT_REQUIRED_MESSAGE, {**base_metadata, "decision_available": True, "provider_search_performed": False},
            )
        location = _normalise_location(agent_input.location)
        if location is None:
            return ReferralAgentResult(
                "location_required", True, None, (),
                "Location permission or a manual city/location input is needed to find nearby dermatology providers.",
                _SAFETY_MESSAGE, {**base_metadata, "decision_available": True, "provider_search_performed": False},
            )
        try:
            found = self._provider.find_dermatologists(location, agent_input.radius_km, "dermatology")
            options = tuple(sorted((_normalise_option(item) for item in found), key=_rank_key))
        except Exception:
            return ReferralAgentResult(
                "provider_error", True, location, (), "Provider search could not be completed.", _SAFETY_MESSAGE,
                {**base_metadata, "decision_available": True, "provider_search_performed": True},
            )
        if not options:
            return ReferralAgentResult(
                "no_results", True, location, (), "No dermatology providers were returned for the available location.",
                _SAFETY_MESSAGE, {**base_metadata, "decision_available": True, "provider_search_performed": True, "provider_count": 0},
            )
        return ReferralAgentResult(
            "referral_options_available", True, location, options,
            "Dermatology referral options were ranked using returned specialty, distance, and opening-hours information.",
            _SAFETY_MESSAGE,
            {**base_metadata, "decision_available": True, "provider_search_performed": True, "provider_count": len(options)},
        )

    process = refer
