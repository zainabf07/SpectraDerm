"""Real image-to-agent adapter for the existing FastAPI analysis endpoint.

This module composes frozen engineering modules and AD. It deliberately does
not create clinical conclusions, synthetic spectral data, provider results, or
evidence. Missing optional model/evidence resources remain explicit in AD's
structured errors and limitations.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, replace
import logging
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np

from spectraderm.agents.evidence_agent import EvidenceAgent, EvidenceAgentInput
from spectraderm.agents.monitoring_agent import HistoricalScanRecord, MonitoringAgent, MonitoringAgentInput
from spectraderm.agents.orchestrator_agent import OrchestratorAgent, OrchestratorInput
from spectraderm.agents.product_agent import ProductAgent
from spectraderm.agents.referral_agent import ReferralAgent
from spectraderm.agents.safety_agent import SafetyAgent
from spectraderm.agents.vision_agent import VisionAgent, VisionAgentInput
from spectraderm.api.exceptions import ArtifactUnavailable, ServiceUnavailable
from spectraderm.features.combined_features import CombinedFeatureResult, FeatureMetadata, combine_features
from spectraderm.features.rgb_features import extract_rgb_features
from spectraderm.features.spectral_features import extract_spectral_features
from spectraderm.monitoring.anomaly import DEFAULT_MINIMUM_REFERENCE_OBSERVATIONS, analyze_change
from spectraderm.monitoring.baseline import build_personal_baseline
from spectraderm.monitoring.change_visuals import build_change_visuals
from spectraderm.monitoring.longitudinal import compare_longitudinal
from spectraderm.monitoring.progress import as_change_result, plain_language_finding, summarize_progress
from spectraderm.spectral.reconstruction import SpectralReconstructionConfig, reconstruct_spectral
from spectraderm.spectral.visualization import (
    HYPERSKIN_VIS_WAVELENGTHS,
    extract_region_spectrum,
    get_band,
    normalize_band,
    spectral_to_false_color,
)
from spectraderm.vision.localization import localize_regions
from spectraderm.vision.quality import assess_image_quality
from spectraderm.vision.segmentation import segment_skin


logger = logging.getLogger(__name__)


class ImageArtifactResolver(Protocol):
    def resolve_image_artifact(self, record: Any) -> Path: ...


class UnconfiguredRAGPipeline:
    """Explicit Module W boundary until a deployed retrieval/LLM adapter is injected."""
    def run(self, model_finding: str, top_k: int = 3) -> Any:
        raise ServiceUnavailable("Evidence retrieval/generation is not configured for analysis orchestration.")


@dataclass(frozen=True)
class AnalysisAdapterConfig:
    mstpp_checkpoint_path: Path | None = None
    mstpp_device: str | None = None
    mstpp_input_size: int = 256


def _summary(value: Any, **extra: Any) -> dict[str, Any]:
    """Return scalar metadata only; never place image arrays/cubes in API output."""
    result = {key: item for key, item in extra.items() if item is not None}
    if value is not None:
        result["available"] = True
    return result


def _comparison_data(comparison: Any | None) -> dict[str, Any] | None:
    """Expose the existing Module S output without deriving a new score."""
    if comparison is None:
        return None
    return {
        "baseline_values": comparison.baseline_values,
        "current_values": comparison.current_values,
        "delta": comparison.delta,
        "absolute_delta": comparison.absolute_delta,
        "relative_change": comparison.relative_change,
        "feature_status": comparison.feature_status,
        "summary": comparison.summary,
        "metadata": comparison.metadata,
    }


def _load_rgb(path: Path) -> np.ndarray:
    decoded = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if decoded is None:
        raise ArtifactUnavailable("The referenced image could not be decoded.")
    return cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)


def _mstpp_input_rgb(rgb: np.ndarray, size: int) -> np.ndarray:
    """Use the existing 256px Hyper-Skin inference contract for browser images.

    The deployed checkpoint was trained and integration-tested on 256px RGB/VIS
    pairs. Browser uploads are often camera-resolution, so passing them directly
    to CPU inference makes the optional stage impractically slow. This resizes
    only the model input; the original artifact remains the scan image.
    """
    if not isinstance(size, int) or size <= 0:
        raise ValueError("mstpp_input_size must be a positive integer")
    return cv2.resize(rgb, (size, size), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0


def _png_data_url(image: np.ndarray, rgb: bool = False) -> str:
    """Encode a Module K display array without serializing a spectral cube."""
    pixels = np.clip(image * 255.0, 0, 255).round().astype(np.uint8)
    if rgb:
        pixels = cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
    encoded, buffer = cv2.imencode(".png", pixels)
    if not encoded:
        raise RuntimeError("Spectral visualization PNG encoding failed.")
    return f"data:image/png;base64,{base64.b64encode(buffer.tobytes()).decode('ascii')}"


def build_spectral_visualization(spectral_cube: np.ndarray, roi_mask: np.ndarray | None) -> dict[str, Any]:
    """Create compact display artifacts strictly from the existing Module K API."""
    false_color = spectral_to_false_color(spectral_cube)
    representative_wavelength_nm = 550
    representative_band = normalize_band(get_band(spectral_cube, representative_wavelength_nm))
    visualization: dict[str, Any] = {
        "available": True,
        "label": "AI-estimated spectral representation",
        "note": "Reconstructed from the RGB image; this is not measured spectroscopy.",
        "wavelength_range_nm": (int(HYPERSKIN_VIS_WAVELENGTHS[0]), int(HYPERSKIN_VIS_WAVELENGTHS[-1])),
        "reconstructed_band_count": int(HYPERSKIN_VIS_WAVELENGTHS.size),
        "false_color_image": _png_data_url(false_color, rgb=True),
        "representative_band": {
            "wavelength_nm": representative_wavelength_nm,
            "image": _png_data_url(representative_band),
        },
    }
    if roi_mask is not None and roi_mask.any():
        visualization["roi_spectrum"] = {
            "wavelengths_nm": [int(value) for value in HYPERSKIN_VIS_WAVELENGTHS],
            "values": [float(value) for value in extract_region_spectrum(spectral_cube, roi_mask)],
        }
    return visualization


class AnalysisOrchestrationAdapter:
    """Run the real available image pipeline and hand structured output to AD."""
    def __init__(
        self, artifact_resolver: ImageArtifactResolver, orchestrator: OrchestratorAgent,
        config: AnalysisAdapterConfig | None = None,
    ) -> None:
        self._artifact_resolver = artifact_resolver
        self._orchestrator = orchestrator
        self._config = config or AnalysisAdapterConfig()

    @classmethod
    def with_defaults(
        cls, artifact_resolver: ImageArtifactResolver, config: AnalysisAdapterConfig | None = None,
        referral_agent: ReferralAgent | None = None, rag_pipeline: Any | None = None,
    ) -> "AnalysisOrchestrationAdapter":
        orchestrator = OrchestratorAgent(
            VisionAgent(), MonitoringAgent(), EvidenceAgent(rag_pipeline or UnconfiguredRAGPipeline()), SafetyAgent(),
            ProductAgent(), referral_agent or ReferralAgent(_NoProvider()),
        )
        return cls(artifact_resolver, orchestrator, config)

    def analyze(self, scan: Any, payload: dict[str, Any]) -> Any:
        if not isinstance(payload, dict):
            raise TypeError("analysis input must be an object")
        try:
            path = self._artifact_resolver.resolve_image_artifact(scan)
        except FileNotFoundError as error:
            raise ArtifactUnavailable() from error
        rgb = _load_rgb(path)
        quality = assess_image_quality(rgb)
        segmentation = segment_skin(rgb)
        mask = segmentation.mask.astype(bool)
        localization = localize_regions(mask) if mask.any() else None
        roi_mask = mask if mask.any() else None
        model_rgb = _mstpp_input_rgb(rgb, self._config.mstpp_input_size)
        model_segmentation = segment_skin((model_rgb * 255.0).round().astype(np.uint8))
        model_mask = model_segmentation.mask.astype(bool)
        model_roi_mask = model_mask if model_mask.any() else None
        rgb_features = extract_rgb_features(model_rgb, model_roi_mask)

        reconstruction, spectral_features, reconstruction_error = self._reconstruct(model_rgb, model_roi_mask)
        spectral_visualization = (
            build_spectral_visualization(reconstruction.spectrum, model_roi_mask)
            if reconstruction is not None else None
        )
        combined, baseline, comparison, q_anomaly, historical_records, progress, history = self._monitoring_inputs(
            scan, rgb_features, spectral_features,
        )
        # Scan 1 = baseline, scan 2 = first change, scan 3+ = trend. Module Q's
        # IQR anomaly score (4+ references) is kept as a technical detail.
        anomaly = as_change_result(progress) if progress is not None else None
        visuals = self._change_visuals(scan, model_rgb, model_mask, history, reconstruction)
        vision_input = VisionAgentInput(
            image_quality_result=quality,
            localization_result=_summary(
                localization, method=localization.method if localization else None,
                candidate_count=len(localization.candidates) if localization else 0,
                segmentation_method=segmentation.method, skin_fraction=segmentation.skin_fraction,
            ),
            reconstruction_result=_summary(
                reconstruction, estimated=getattr(reconstruction, "estimated", None),
                output_bands=getattr(reconstruction, "output_bands", None), model_name=getattr(reconstruction, "model_name", None),
                unavailable_reason=reconstruction_error,
            ) if reconstruction is not None else None,
            spectral_features=_summary(
                spectral_features, feature_count=len(spectral_features.features) if spectral_features else None,
                roi_pixel_count=spectral_features.roi_pixel_count if spectral_features else None,
                unavailable_reason=reconstruction_error,
            ) if spectral_features is not None else None,
            monitoring_change_result=anomaly,
            ml_output=None,
        )
        monitoring_input = MonitoringAgentInput(
            baseline_reference=baseline,
            current_comparison=comparison,
            change_anomaly_result=anomaly,
            historical_scan_records=historical_records,
            current_scan_id=getattr(scan, "scan_id", None),
            current_timestamp=getattr(scan, "timestamp", None).isoformat() if getattr(scan, "timestamp", None) else None,
        )
        evidence_input = EvidenceAgentInput(query=plain_language_finding(progress)) if progress is not None else None
        result = self._orchestrator.run(OrchestratorInput(
            vision_input=vision_input, monitoring_input=monitoring_input, evidence_input=evidence_input,
        ))
        save_change = getattr(self._artifact_resolver, "save_change_record", None)
        if progress is not None and callable(save_change):
            try:
                save_change(scan, progress.change_score, progress.category, extra={
                    "change_percent": progress.change_percent, "status_label": progress.status_label,
                    "trend": progress.trend, "scan_number": progress.scan_number,
                })
            except Exception:
                logger.exception("Failed to persist change record for scan %s.", getattr(scan, "scan_id", None))
        # The agent needs the real Q/R/S objects while it runs, but normal API
        # consumers should receive only their derived monitoring interpretation.
        monitoring_result = getattr(result, "monitoring_result", None)
        if monitoring_result is not None:
            public_monitoring = replace(
                monitoring_result,
                evidence_inputs={
                    "baseline_available": baseline is not None,
                    "comparison_available": comparison is not None,
                    "change_score_available": getattr(anomaly, "change_score", None) is not None,
                    "reference_scan_count": len(historical_records),
                    "minimum_reference_scans": DEFAULT_MINIMUM_REFERENCE_OBSERVATIONS,
                    "comparison": _comparison_data(comparison),
                },
            )
            result = replace(result, monitoring_result=public_monitoring)
            # The evidence agent echoes its monitoring input; keep that copy
            # sanitized too so the response does not carry raw baseline objects.
            for name in ("evidence_result", "product_result"):
                agent_result = getattr(result, name, None)
                if agent_result is not None and hasattr(agent_result, "monitoring_context"):
                    result = replace(result, **{name: replace(agent_result, monitoring_context=public_monitoring)})
        # Preserve actual lightweight engineering metadata next to AD output;
        # this is compatible with AJ and intentionally excludes raw pixels/cubes.
        return replace(result, metadata={**result.metadata, "pipeline": {
            "image_reference": getattr(scan, "image_reference", None),
            "image_shape": tuple(int(value) for value in rgb.shape),
            "rgb_feature_count": len(rgb_features.features),
            "segmentation_method": segmentation.method,
            "model_input_shape": tuple(int(value) for value in model_rgb.shape),
            "spectral_reconstruction_available": reconstruction is not None,
            "spectral_reconstruction_unavailable_reason": reconstruction_error,
            "spectral_visualization": spectral_visualization,
            "progress": progress.to_dict() if progress is not None else None,
            "visuals": visuals,
            "anomaly_model": {
                "available": getattr(q_anomaly, "change_score", None) is not None,
                "score": getattr(q_anomaly, "change_score", None),
                "category": getattr(q_anomaly, "category", None),
                "minimum_reference_scans": DEFAULT_MINIMUM_REFERENCE_OBSERVATIONS,
                "interpretation": getattr(q_anomaly, "interpretation", None),
            } if q_anomaly is not None else None,
            "quality": {
                "status": getattr(getattr(quality, "status", None), "value", None),
                "passed": getattr(quality, "passed", None),
                "reasons": list(getattr(quality, "reasons", []) or []),
            },
            "skin_fraction": getattr(segmentation, "skin_fraction", None),
        }})

    def _monitoring_inputs(self, scan: Any, rgb_features: Any, spectral_features: Any | None) -> tuple[Any, ...]:
        """Build Module N -> R/S/Q inputs and the user-facing progress summary.

        Historical feature vectors are loaded from AG-managed disk storage, so
        the baseline, change and trend survive server restarts. The personal
        baseline is the person's first scan.
        """
        if spectral_features is None:
            return None, None, None, None, (), None, ()
        scan_id = getattr(scan, "scan_id", None)
        user_id = getattr(scan, "user_id", None)
        timestamp = getattr(scan, "timestamp", None)
        historical = self._load_historical_features(scan)
        baseline_source = historical[0][2] if historical else None
        combined = combine_features(
            rgb_features, spectral_features, baseline_features=baseline_source,
            current_timestamp=timestamp,
            baseline_timestamp=baseline_source.metadata.timestamp if baseline_source is not None else None,
            metadata={"observation_id": scan_id, "subject_key": user_id, "roi_available": spectral_features.roi_pixel_count > 0},
        )
        save_snapshot = getattr(self._artifact_resolver, "save_feature_snapshot", None)
        if callable(save_snapshot):
            try:
                save_snapshot(scan, combined.current_features)
            except Exception:
                logger.exception("Failed to persist combined features for scan %s.", scan_id)
        progress = summarize_progress(
            combined.current_features,
            [(item_id, item_time, features.current_features, change) for item_id, item_time, features, change in historical],
            scan_id, timestamp.isoformat() if timestamp else None,
        )
        if not historical:
            return combined, None, None, analyze_change(combined, ()), (), progress, historical
        references = tuple(item[2] for item in historical)
        baseline = build_personal_baseline((historical[0][2],))
        comparison = compare_longitudinal(baseline, combined)
        anomaly = analyze_change(combined, references)
        records = tuple(
            HistoricalScanRecord(
                scan_id=previous_id, timestamp=previous_timestamp,
                change_score=_optional_float(change.get("change_score")) if change else None,
                status=change.get("category") if change and isinstance(change.get("category"), str) else None,
            )
            for previous_id, previous_timestamp, _, change in historical
        )
        return combined, baseline, comparison, anomaly, records, progress, historical

    def _change_visuals(
        self, scan: Any, model_rgb: np.ndarray, model_mask: np.ndarray, history: tuple[Any, ...],
        reconstruction: Any | None,
    ) -> dict[str, Any] | None:
        """Baseline vs current photo, difference map, and highlighted region."""
        try:
            baseline_rgb = baseline_mask = None
            list_scans = getattr(self._artifact_resolver, "list_user_scans", None)
            if history and callable(list_scans):
                baseline_id = history[0][0]
                record = next(
                    (item for item in list_scans(getattr(scan, "user_id", None)) if getattr(item, "scan_id", None) == baseline_id),
                    None,
                )
                if record is not None:
                    baseline_rgb = _mstpp_input_rgb(
                        _load_rgb(self._artifact_resolver.resolve_image_artifact(record)), self._config.mstpp_input_size,
                    )
                    baseline_mask = segment_skin((baseline_rgb * 255.0).round().astype(np.uint8)).mask.astype(bool)
            false_color = spectral_to_false_color(reconstruction.spectrum) if reconstruction is not None else None
            return build_change_visuals(model_rgb, model_mask, baseline_rgb, baseline_mask, false_color)
        except Exception:
            logger.exception("Change visualisation could not be built.")
            return None

    def _load_historical_features(
        self, scan: Any,
    ) -> tuple[tuple[str, str, CombinedFeatureResult, dict[str, Any] | None], ...]:
        """Load previously persisted Module N feature snapshots for this user."""
        scan_id = getattr(scan, "scan_id", None)
        user_id = getattr(scan, "user_id", None)
        list_scans = getattr(self._artifact_resolver, "list_user_scans", None)
        load_snapshot = getattr(self._artifact_resolver, "load_feature_snapshot", None)
        if not callable(list_scans) or not callable(load_snapshot) or user_id is None:
            return ()
        current_timestamp = getattr(scan, "timestamp", None)
        load_change = getattr(self._artifact_resolver, "load_change_record", None)
        historical: list[tuple[str, str, CombinedFeatureResult, dict[str, Any] | None]] = []
        for record in list_scans(user_id):
            if getattr(record, "scan_id", None) == scan_id:
                continue
            # Re-opening an older scan must not treat later scans as its history.
            record_time = getattr(record, "timestamp", None)
            if current_timestamp is not None and record_time is not None and record_time > current_timestamp:
                continue
            try:
                features = load_snapshot(record)
            except Exception:
                logger.exception("Failed to load persisted features for scan %s.", getattr(record, "scan_id", None))
                continue
            if not features:
                continue
            record_timestamp = getattr(record, "timestamp", None)
            timestamp_text = record_timestamp.isoformat() if record_timestamp else ""
            change = None
            if callable(load_change):
                try:
                    change = load_change(record)
                except Exception:
                    logger.exception("Failed to load persisted change record for scan %s.", record.scan_id)
            historical.append((record.scan_id, timestamp_text, _rehydrate_baseline(features, record), change))
        return tuple(sorted(historical, key=lambda item: (item[1], item[0])))

    def _reconstruct(self, rgb: np.ndarray, mask: np.ndarray | None) -> tuple[Any | None, Any | None, str | None]:
        checkpoint = self._config.mstpp_checkpoint_path
        if checkpoint is None:
            logger.warning("MST++ reconstruction skipped: no checkpoint is configured.")
            return None, None, "MST++ reconstruction checkpoint is not configured or unavailable."
        resolved_checkpoint = checkpoint.resolve()
        if not resolved_checkpoint.is_file():
            logger.warning("MST++ reconstruction skipped: configured checkpoint is unavailable at %s.", resolved_checkpoint)
            return None, None, "MST++ reconstruction checkpoint is not configured or unavailable."
        try:
            result = reconstruct_spectral(
                rgb,
                SpectralReconstructionConfig(checkpoint_path=resolved_checkpoint, device=self._config.mstpp_device),
            )
            return result, extract_spectral_features(result.spectrum, mask=mask), None
        except Exception:
            logger.exception(
                "MST++ reconstruction failed for checkpoint %s on device %s.",
                resolved_checkpoint, self._config.mstpp_device or "auto",
            )
            return None, None, "MST++ reconstruction could not be completed."


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _rehydrate_baseline(features: dict[str, float], record: Any) -> CombinedFeatureResult:
    """Rebuild a minimal, valid Module N result from a persisted feature snapshot.

    Only ``current_features`` and ``metadata.timestamp`` are read by downstream
    Module R/S/Q consumers when a result is used purely as historical
    reference input (see combine_features, build_personal_baseline,
    analyze_change), so the remaining fields are populated with honest,
    inert placeholders rather than recomputed or fabricated values.
    """
    timestamp = getattr(record, "timestamp", None)
    metadata = FeatureMetadata(
        observation_id=getattr(record, "scan_id", None),
        timestamp=timestamp,
        subject_key=getattr(record, "user_id", None),
        history_available=False,
        temporal_status="baseline",
        baseline_observation_id=None,
        elapsed_days=None,
        roi_available=True,
        roi_pixel_count=0,
    )
    return CombinedFeatureResult(
        current_features=dict(features),
        temporal_features={},
        combined_features={},
        ml_vector=np.array([], dtype=float),
        feature_names=sorted(features),
        metadata=metadata,
        warnings=[],
    )


class _NoProvider:
    """No network provider used by default analysis; AC stops at location_required."""
    def find_dermatologists(self, location: dict[str, Any], radius_km: float, specialty: str = "dermatology") -> tuple[()]:
        return ()
