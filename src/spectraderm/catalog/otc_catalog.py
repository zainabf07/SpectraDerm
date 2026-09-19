"""Controlled, read-only OTC skincare category knowledge for Module AH."""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_PATTERNS = ("pigmentation", "redness_irritation", "acne_like_texture", "dryness_barrier", "unknown")


@dataclass(frozen=True)
class OTCCategory:
    """Neutral category information, not a diagnosis or individualized recommendation."""

    category_id: str
    category_name: str
    relevant_patterns: tuple[str, ...]
    neutral_description: str
    example_ingredient_types: tuple[str, ...]
    general_precautions: tuple[str, ...]
    jurisdiction_note: str | None = None


_JURISDICTION = "Availability, concentration, formulation, and regulation vary by jurisdiction."
_CATALOG = (
    OTCCategory("pigment_correctors", "Pigment correctors", ("pigmentation",), "This category is commonly used in skincare aimed at improving the appearance of uneven pigmentation.", ("azelaic acid", "tranexamic acid", "kojic acid", "licorice-derived ingredients"), ("Introduce products cautiously and follow product labeling.",), _JURISDICTION),
    OTCCategory("topical_antioxidants", "Topical antioxidants", ("pigmentation",), "This category is commonly used in skincare routines focused on the appearance of uneven tone.", ("vitamin C", "L-ascorbic acid"), ("Formulations may be irritating for some people; follow product labeling.",), _JURISDICTION),
    OTCCategory("aha_exfoliants", "AHA exfoliants", ("pigmentation",), "This category is commonly used in skincare focused on surface texture and the appearance of uneven pigmentation.", ("glycolic acid", "lactic acid"), ("Use only as directed on product labeling and consider sensitivity.",), _JURISDICTION),
    OTCCategory("broad_spectrum_sunscreen", "Broad-spectrum sunscreen", ("pigmentation", "redness_irritation"), "This general skincare category is commonly used for broad-spectrum sun protection.", ("SPF 30+ broad-spectrum sunscreen",), ("Follow product labeling and local sun-protection guidance.",), "Formulation and regulatory availability vary by jurisdiction."),
    OTCCategory("barrier_repair_moisturizers", "Barrier-repair moisturizers", ("redness_irritation", "dryness_barrier"), "This category is commonly used in skincare routines focused on supporting the appearance of dry or uncomfortable skin.", ("ceramides", "fatty acids", "cholesterol"), ("Consider fragrance sensitivity and product labeling.",), None),
    OTCCategory("soothing_topicals", "Soothing topicals", ("redness_irritation",), "This category is commonly used in skincare routines focused on the appearance of temporary discomfort or redness.", ("niacinamide", "centella/cica", "colloidal oatmeal", "allantoin"), ("Stop use if irritation occurs and follow product labeling.",), _JURISDICTION),
    OTCCategory("low_potency_topical_corticosteroid", "Low-potency topical corticosteroid", ("redness_irritation",), "This category describes products that may be available for limited OTC use in some jurisdictions.", ("hydrocortisone",), ("Use only according to labeling; seek professional guidance when concerns persist or product use is unclear.",), _JURISDICTION),
    OTCCategory("steroid_free_anti_itch", "Steroid-free anti-itch", ("redness_irritation",), "This category describes skincare-adjacent products that may be used for temporary itch-related comfort where permitted.", ("pramoxine",), ("Use only according to labeling and stop if irritation occurs.",), _JURISDICTION),
    OTCCategory("topical_retinoid", "Topical retinoid", ("acne_like_texture",), "This category is commonly used in skincare routines focused on the appearance of texture.", ("adapalene", "retinol", "retinal"), ("Sensitivity and sun sensitivity may occur; follow product labeling.",), _JURISDICTION),
    OTCCategory("bha_comedolytic", "BHA comedolytic", ("acne_like_texture",), "This category is commonly used in skincare focused on the appearance of congested texture.", ("salicylic acid",), ("Consider sensitivity and follow product labeling.",), _JURISDICTION),
    OTCCategory("antimicrobial_acne_care", "Antimicrobial acne care", ("acne_like_texture",), "This category is commonly used in skincare routines focused on the appearance of blemish-prone texture.", ("benzoyl peroxide",), ("Dryness or irritation may occur; follow product labeling.",), _JURISDICTION),
    OTCCategory("keratolytic", "Keratolytic", ("acne_like_texture",), "This category is commonly used in skincare focused on the appearance of rough or uneven texture.", ("urea", "salicylic acid"), ("Consider sensitivity and follow product labeling.",), _JURISDICTION),
    OTCCategory("fragrance_free_moisturizer", "Fragrance-free moisturizer", ("dryness_barrier",), "This category is commonly used in skincare routines focused on the appearance of dry skin.", (), ("Review the ingredient list for personal sensitivities.",), None),
    OTCCategory("gentle_cleanser", "Gentle cleanser", ("acne_like_texture", "dryness_barrier"), "This category is commonly used for general cleansing without a condition-specific claim.", (), ("Follow product labeling and avoid over-cleansing.",), None),
)

OTC_CATEGORY_IDS = tuple(item.category_id for item in _CATALOG)
_BY_ID = {item.category_id: item for item in _CATALOG}
_PATTERN_IDS = {
    "pigmentation": ("pigment_correctors", "topical_antioxidants", "aha_exfoliants", "broad_spectrum_sunscreen"),
    "redness_irritation": ("barrier_repair_moisturizers", "soothing_topicals", "low_potency_topical_corticosteroid", "steroid_free_anti_itch", "broad_spectrum_sunscreen"),
    "acne_like_texture": ("topical_retinoid", "bha_comedolytic", "antimicrobial_acne_care", "keratolytic", "gentle_cleanser"),
    "dryness_barrier": ("barrier_repair_moisturizers", "fragrance_free_moisturizer", "gentle_cleanser"),
    "unknown": (),
}


def list_categories() -> tuple[OTCCategory, ...]:
    """Return immutable catalog entries in stable, version-controlled order."""
    return _CATALOG


def get_category(category_id: str) -> OTCCategory | None:
    """Return one entry, or None for an unsupported category ID."""
    if not isinstance(category_id, str):
        raise TypeError("category_id must be a string")
    return _BY_ID.get(category_id)


def has_category(category_id: str) -> bool:
    """Report whether a stable controlled ID exists."""
    if not isinstance(category_id, str):
        return False
    return category_id in _BY_ID


def get_categories_for_pattern(pattern: str) -> tuple[OTCCategory, ...]:
    """Return relevance metadata only; unknown intentionally has no categories."""
    if not isinstance(pattern, str) or pattern not in _PATTERN_IDS:
        raise ValueError("pattern must be one of the supported controlled appearance patterns")
    return tuple(_BY_ID[category_id] for category_id in _PATTERN_IDS[pattern])
