"""User-facing SpectraDerm skin monitoring report.

Combines image analysis, AI-estimated spectral information, the change score,
historical change, retrieved evidence, the safety review and the next action
into one structured report. Wording describes what was measured; it never
names a condition or a disease probability.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from spectraderm.api.rag_adapter import FALLBACK_CLOSING

DISCLAIMER = (
    "SpectraDerm is an AI-based skin monitoring and awareness prototype. It does not diagnose skin diseases, "
    "determine disease probability, replace a dermatologist, or guarantee that a detected change is medically "
    "significant. Estimated spectral information is a model prediction rather than a direct spectral measurement."
)
SCORE_NOTE = (
    "This score represents deviation from your own baseline pattern. It is not a disease probability or diagnosis."
)
SPECTRAL_NOTE = (
    "Spectral information is AI-estimated from the ordinary RGB photo. It is not an actual multispectral or "
    "hyperspectral measurement."
)

_TONES = {"Baseline established": "baseline", "Stable": "stable", "Slight change": "monitor", "Change detected": "change"}


def _get(value: Any, *path: str) -> Any:
    for name in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(name)
    return value


def _display_id(number: int | None) -> str:
    return f"SD-{number:03d}" if isinstance(number, int) else "SD"


def _overall(progress: Mapping[str, Any] | None, referral: bool) -> dict[str, Any]:
    if not progress:
        return {
            "tone": "baseline", "status_label": "Observation recorded",
            "headline": "Your observation was recorded",
            "summary": "Change information is not available for this scan.",
        }
    stage = progress.get("stage")
    label = progress.get("status_label") or "Recorded"
    percent = progress.get("change_percent")
    if stage == "baseline":
        headline, summary = "Baseline established", (
            "This first scan is your personal baseline. Your next scans will be compared with it."
        )
    elif label == "Slight change" and not referral:
        headline, summary = "Slight change — keep monitoring", (
            f"A small change of {percent:.0f}% was detected in the monitored skin region compared with your "
            "personal baseline."
        )
    elif label == "Stable":
        headline, summary = "Stable — no meaningful change", (
            f"The monitored skin region is close to your personal baseline (overall change {percent:.0f}%)."
        )
    else:
        headline = "Change detected — monitoring recommended" if not referral else "Change detected — consider a professional assessment"
        summary = (
            f"A measurable change of {percent:.0f}% was detected in the monitored skin region compared with your "
            "personal baseline."
        )
    return {"tone": _TONES.get(label, "monitor"), "status_label": label, "headline": headline, "summary": summary}


def _reliability(quality: Mapping[str, Any] | None, spectral_available: bool) -> dict[str, Any]:
    status = str(_get(quality, "status") or "").upper()
    reasons = list(_get(quality, "reasons") or [])
    if status == "GOOD" and spectral_available:
        label = "High"
    elif status == "REJECT":
        label = "Low"
    else:
        label = "Moderate"
    if not spectral_available:
        reasons.append("AI-estimated spectral information was not available for this scan.")
    return {"label": label, "reasons": reasons}


def _explanation(evidence: Mapping[str, Any] | None, safety: Mapping[str, Any] | None) -> dict[str, Any]:
    text = _get(evidence, "explanation")
    blocked = set(_get(safety, "blocked_claims") or [])
    withheld = bool(text) and text in blocked
    sources = [
        {
            "title": _get(item, "source", "title"), "organization": _get(item, "source", "organization"),
            "url": _get(item, "source", "url"), "excerpt": item.get("text"),
        }
        for item in (_get(evidence, "retrieved_evidence") or [])
        if isinstance(item, Mapping)
    ]
    if not text or withheld:
        origin = "unavailable"
    elif FALLBACK_CLOSING in text:
        origin = "retrieved_sources"
    else:
        origin = "language_model"
    return {
        "text": None if withheld else text, "withheld": withheld, "origin": origin,
        "sources": sources, "evidence_count": len(sources),
    }


def _next_action(stage: str | None, label: str | None, referral: bool) -> dict[str, Any]:
    if referral:
        return {
            "type": "professional", "title": "Consider a professional assessment",
            "steps": [
                "Show this report to a dermatologist or GP.",
                "Keep scanning under the same lighting and position so changes stay comparable.",
                "Use “Find a dermatologist” to see options near you.",
            ],
        }
    if stage == "baseline":
        return {
            "type": "monitor", "title": "Take your next scan",
            "steps": [
                "Scan the same area again in 2–4 weeks.",
                "Use similar lighting, distance and angle as this photo.",
                "Your next scan will show the first change from this baseline.",
            ],
        }
    return {
        "type": "monitor", "title": "Continue monitoring",
        "steps": [
            "Repeat the scan in 2–4 weeks under similar lighting and positioning.",
            "Each scan is compared against your personal baseline.",
            "Watch whether the change persists or increases." if label != "Stable" else "Keep a regular routine so any future change is noticed early.",
        ],
    }


def build_monitoring_report(scan: Any, analysis: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble the report from a serialized orchestrator result (``to_data``)."""
    pipeline = _get(analysis, "metadata", "pipeline") or {}
    progress = pipeline.get("progress") or None
    visuals = pipeline.get("visuals") or {}
    spectral = pipeline.get("spectral_visualization") or None
    safety = _get(analysis, "safety_result") or {}
    referral = safety.get("professional_assessment_recommended") is True
    stage = _get(progress, "stage")
    label = _get(progress, "status_label")
    scan_number = _get(progress, "scan_number")
    history_points = list(_get(progress, "history") or [])
    timestamp = getattr(scan, "timestamp", None)
    baseline_point = history_points[0] if history_points else None

    parameters = [
        {
            "label": item.get("label"), "baseline": item.get("baseline"), "current": item.get("current"),
            "change": item.get("change"), "change_percent": item.get("change_percent"), "direction": item.get("direction"),
        }
        for item in (_get(progress, "parameters") or [])
        if item.get("current") is not None
    ]
    history = [
        {
            "scan_number": point.get("scan_number"), "date": point.get("timestamp"), "status": point.get("status_label"),
            "change_percent": point.get("change_percent"), "change_score": point.get("change_score"), "is_current": False,
        }
        for point in history_points
    ] + [{
        "scan_number": scan_number, "date": timestamp.isoformat() if timestamp else None, "status": label,
        "change_percent": _get(progress, "change_percent"), "change_score": _get(progress, "change_score"), "is_current": True,
    }]
    quality = pipeline.get("quality") or {}
    region = visuals.get("region")
    anomaly = pipeline.get("anomaly_model") or {}
    safety_status = safety.get("safety_status")
    return {
        "scan": {
            "scan_id": getattr(scan, "scan_id", None), "display_id": _display_id(scan_number),
            "scan_number": scan_number, "date": timestamp.isoformat() if timestamp else None,
            "reference": None if stage == "baseline" or not baseline_point else {
                "label": "Personal baseline — Scan 1", "date": baseline_point.get("timestamp"),
            },
        },
        "overall": {
            **_overall(progress, referral),
            "stage": stage, "change_score": _get(progress, "change_score"), "change_percent": _get(progress, "change_percent"),
            "direction": _get(progress, "direction_vs_previous"), "trend": _get(progress, "trend"),
            "trend_text": _get(progress, "trend_text"),
            "reliability": _reliability(quality, bool(spectral and spectral.get("available"))),
            "score_note": SCORE_NOTE,
        },
        "detected_change": {
            "available": stage not in (None, "baseline"), "overall_change_percent": _get(progress, "change_percent"),
            "parameters": parameters,
        },
        "region": {
            "baseline_image": visuals.get("baseline_image"), "current_highlighted": visuals.get("current_highlighted"),
            "difference_map": visuals.get("difference_map"), "spectral_highlighted": visuals.get("spectral_highlighted"),
            "region": region,
            "note": "The difference map compares this photo with your baseline photo; it assumes similar framing and lighting.",
        },
        "spectral": {
            "available": bool(spectral and spectral.get("available")),
            "false_color_image": _get(spectral, "false_color_image"),
            "band_image": _get(spectral, "representative_band", "image"),
            "band_wavelength_nm": _get(spectral, "representative_band", "wavelength_nm"),
            "wavelength_range_nm": _get(spectral, "wavelength_range_nm"),
            "band_count": _get(spectral, "reconstructed_band_count"),
            "note": SPECTRAL_NOTE,
        },
        "history": {"points": history, "trend": _get(progress, "trend"), "trend_text": _get(progress, "trend_text")},
        "explanation": {"finding": _get(analysis, "evidence_result", "query"), **_explanation(_get(analysis, "evidence_result"), safety)},
        "safety": {
            "professional_assessment_recommended": referral,
            "assessment": (
                "Professional assessment may be appropriate." if referral
                else "Continue monitoring. No professional-assessment signal from this scan."
                if stage != "baseline" else "Baseline recorded. Nothing to assess yet."
            ),
            "claims_reviewed": safety_status in {"safe_to_present", "professional_assessment_consideration", "insufficient_evidence"},
            "notes": ["The detected change does not mean that a disease has been identified."],
        },
        "next_action": _next_action(stage, label, referral),
        "technical": {
            "image_quality": {"status": quality.get("status"), "passed": quality.get("passed"), "reasons": quality.get("reasons") or []},
            "skin_detected": bool((pipeline.get("skin_fraction") or 0) > 0),
            "monitored_region": "Region A" if region else None,
            "rgb_input_shape": pipeline.get("image_shape"),
            "model_input_shape": pipeline.get("model_input_shape"),
            "spectral_output_shape": (
                [*(pipeline.get("model_input_shape") or [])[:2], spectral.get("reconstructed_band_count")]
                if spectral and spectral.get("available") else None
            ),
            "reconstruction_status": "Passed" if pipeline.get("spectral_reconstruction_available") else "Unavailable",
            "rgb_feature_count": pipeline.get("rgb_feature_count"),
            "features_used": ["RGB features", "AI-estimated spectral features", "Temporal features"],
            "change_score_method": "Deviation of key RGB and AI-estimated spectral features from the personal baseline (scan 1)",
            "anomaly_model": anomaly,
        },
        "disclaimer": DISCLAIMER,
    }
