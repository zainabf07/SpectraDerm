"""Deterministic general-OTC category suggestions guarded by Module AA."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProductCategory:
    category_id: str
    category_name: str
    neutral_description: str


@dataclass(frozen=True)
class ProductRecommendation:
    category_id: str
    category_name: str
    neutral_description: str
    reason: str


@dataclass(frozen=True)
class ProductAgentInput:
    vision_result: Any | None = None
    monitoring_result: Any | None = None
    evidence_result: Any | None = None
    safety_result: Any | None = None
    detected_pattern: str | None = None
    context: str | None = None
    # Module S longitudinal comparison data (see analysis_adapter._comparison_data),
    # used as a best-effort fallback signal when no explicit pattern is supplied.
    comparison: Any | None = None


@dataclass(frozen=True)
class ProductAgentResult:
    status: str
    recommendations: tuple[ProductRecommendation, ...]
    recommendation_reasons: tuple[str, ...]
    safety_gate: str
    professional_assessment_recommended: bool
    detected_pattern: str
    monitoring_context: Any | None
    limitations: tuple[str, ...]
    safety_message: str


CATALOG = {
    "gentle_cleanser": ProductCategory("gentle_cleanser", "Gentle cleanser", "General cleansing category without a product or brand recommendation."),
    "fragrance_free_moisturizer": ProductCategory("fragrance_free_moisturizer", "Fragrance-free moisturizer", "General moisturizing category without fragrance-focused product selection."),
    "moisturizer": ProductCategory("moisturizer", "Moisturizer", "General moisturizing category; not a treatment plan."),
    "non_comedogenic_moisturizer": ProductCategory("non_comedogenic_moisturizer", "Non-comedogenic moisturizer", "General moisturizer category for acne-like/texture-related appearance context."),
    "broad_spectrum_sunscreen": ProductCategory("broad_spectrum_sunscreen", "Broad-spectrum sunscreen", "General protective skincare category; not a medical treatment."),
    "pigment_support_skincare": ProductCategory("pigment_support_skincare", "Pigment-support skincare", "General OTC skincare category for pigmentation-related appearance context."),
    "topical_antioxidant_skincare": ProductCategory("topical_antioxidant_skincare", "Topical antioxidant skincare", "General topical antioxidant skincare category; not a disease-treatment claim."),
    "gentle_chemical_exfoliation": ProductCategory("gentle_chemical_exfoliation", "Gentle chemical exfoliation", "General gentle chemical exfoliation skincare category without usage directions."),
    "soothing_skincare": ProductCategory("soothing_skincare", "Soothing skincare", "General soothing skincare category for redness/irritation-related appearance context."),
    "salicylic_acid_bha_skincare": ProductCategory("salicylic_acid_bha_skincare", "Salicylic-acid/BHA skincare", "General OTC salicylic-acid/BHA skincare category without a dosing or treatment regimen."),
    "benzoyl_peroxide_skincare": ProductCategory("benzoyl_peroxide_skincare", "Benzoyl-peroxide skincare", "General OTC benzoyl-peroxide skincare category without a dosing or treatment regimen."),
}
_PATTERN_MAP = {
    "pigmentation": ("pigment_support_skincare", "topical_antioxidant_skincare", "gentle_chemical_exfoliation", "broad_spectrum_sunscreen", "gentle_cleanser", "moisturizer"),
    "redness_irritation": ("fragrance_free_moisturizer", "soothing_skincare", "gentle_cleanser", "broad_spectrum_sunscreen"),
    "acne_like_texture": ("gentle_cleanser", "non_comedogenic_moisturizer", "salicylic_acid_bha_skincare", "benzoyl_peroxide_skincare", "broad_spectrum_sunscreen"),
    "dryness_barrier": ("gentle_cleanser", "fragrance_free_moisturizer", "moisturizer"),
    # Default, non-specific bucket: used when no pattern-specific signal is
    # available (e.g. a first scan with no comparison history yet) but a
    # professional assessment is not indicated.
    "general": ("gentle_cleanser", "moisturizer", "broad_spectrum_sunscreen"),
    "unknown": (),
}
# A small set of named Module L (RGB) features whose relative change (from
# Module S's longitudinal comparison) can suggest which general appearance
# category is most relevant. This is a coarse, non-diagnostic heuristic used
# only to pick a product *category*; it never feeds back into ML detection.
_COMPARISON_PATTERN_FEATURES = {
    "pigmentation": (
        "rgb.pigmentation_darkness_proxy",
        "rgb.pigmentation_chroma_proxy",
        "rgb.pigmentation_red_green_ratio",
        "rgb.pigmentation_red_blue_ratio",
    ),
    "redness_irritation": ("rgb.color_mean_r", "rgb.local_contrast_r"),
    "acne_like_texture": ("rgb.gradient_mean", "rgb.local_variance_mean", "rgb.grayscale_std"),
}
_COMPARISON_PATTERN_MIN_RELATIVE_CHANGE = 0.15
_SAFETY_MESSAGE = (
    "Recommendations are general OTC skincare categories, not a diagnosis or diagnoses, prescriptions, or disease-treatment plans. "
    "They do not influence SpectraDerm detection, reconstruction, feature extraction, ML scoring, anomaly analysis, or monitoring."
)


def _field(value: Any, name: str) -> Any | None:
    return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)


def _normalize_pattern(value: str | None) -> str:
    text = value.strip().lower().replace("-", "_").replace("/", "_") if isinstance(value, str) else ""
    if "pigment" in text:
        return "pigmentation"
    if "redness" in text or "irritation" in text:
        return "redness_irritation"
    if "acne" in text or "texture" in text:
        return "acne_like_texture"
    if "dryness" in text or "barrier" in text:
        return "dryness_barrier"
    return "unknown"


def _pattern_from_comparison(comparison: Any | None) -> str | None:
    """Best-effort category signal derived from Module S relative-change data.

    Returns ``None`` (not a specific pattern) whenever there is no comparison,
    no usable relative-change data, or the largest observed change is small
    enough to plausibly be normal scan-to-scan variation.
    """
    if not isinstance(comparison, Mapping):
        return None
    relative_change = comparison.get("relative_change")
    feature_status = comparison.get("feature_status")
    if not isinstance(relative_change, Mapping):
        return None
    best_pattern, best_score = None, 0.0
    for pattern, feature_names in _COMPARISON_PATTERN_FEATURES.items():
        magnitudes = []
        for name in feature_names:
            value = relative_change.get(name)
            if value is None:
                continue
            if isinstance(feature_status, Mapping) and feature_status.get(name) != "usable":
                continue
            magnitudes.append(abs(value))
        if not magnitudes:
            continue
        score = sum(magnitudes) / len(magnitudes)
        if score > best_score:
            best_pattern, best_score = pattern, score
    if best_pattern is not None and best_score >= _COMPARISON_PATTERN_MIN_RELATIVE_CHANGE:
        return best_pattern
    return None


def _vision_finding(vision_result: Any | None) -> str | None:
    if vision_result is None:
        return None
    for name in ("structured_finding", "finding_summary"):
        value = _field(vision_result, name)
        if isinstance(value, str) and value.strip():
            return value
    return None


class ProductAgent:
    """Return only controlled category-level suggestions after the AA gate."""

    def recommend(self, agent_input: ProductAgentInput) -> ProductAgentResult:
        if not isinstance(agent_input, ProductAgentInput):
            raise TypeError("agent_input must be a ProductAgentInput")
        professional = bool(_field(agent_input.safety_result, "professional_assessment_recommended"))
        pattern = _normalize_pattern(agent_input.detected_pattern or _vision_finding(agent_input.vision_result))
        # An explicitly supplied but unsupported pattern stays "unknown"; the
        # comparison/general fallback only applies when no pattern was given.
        if pattern == "unknown" and not agent_input.detected_pattern:
            pattern = _pattern_from_comparison(agent_input.comparison) or "general"
        if professional:
            return ProductAgentResult(
                "referral_preferred", (), (), "professional_assessment_required", True, pattern,
                agent_input.monitoring_result,
                ("Professional assessment takes priority over product-category suggestions.",), _SAFETY_MESSAGE,
            )
        if pattern == "unknown":
            return ProductAgentResult(
                "insufficient_context", (), (), "no_referral_signal", False, pattern, agent_input.monitoring_result,
                ("No supported model-derived appearance/pattern category was supplied.",), _SAFETY_MESSAGE,
            )
        if pattern == "general":
            reason = (
                "General baseline skincare category suggested; no specific model-derived "
                "appearance pattern was available for this scan."
            )
            limitations = (
                "Suggestions are category-level only and do not establish a condition or treatment need.",
                "No specific appearance pattern was detected from the supplied image or comparison data.",
            )
        else:
            label = pattern.replace("_", "/")
            reason = f"General skincare category suggested because the model-derived finding includes a {label}-related appearance."
            limitations = ("Suggestions are category-level only and do not establish a condition or treatment need.",)
        recommendations = tuple(ProductRecommendation(
            category.category_id, category.category_name, category.neutral_description, reason,
        ) for category_id in _PATTERN_MAP[pattern] for category in (CATALOG[category_id],))
        return ProductAgentResult(
            "recommendations_available", recommendations, tuple(item.reason for item in recommendations),
            "no_referral_signal", False, pattern, agent_input.monitoring_result,
            limitations, _SAFETY_MESSAGE,
        )
