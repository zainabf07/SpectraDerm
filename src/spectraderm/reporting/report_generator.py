"""Assemble supplied SpectraDerm outputs without reinterpreting them."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReportItem:
    label: str
    value: Any


@dataclass(frozen=True)
class ReportSection:
    title: str
    status: str
    items: tuple[ReportItem, ...]


@dataclass(frozen=True)
class SpectraDermReport:
    scan_information: ReportSection
    analysis_summary: ReportSection
    visual_region_findings: ReportSection
    spectral_analysis: ReportSection
    model_derived_change: ReportSection
    evidence_explanation: ReportSection
    safety_assessment: ReportSection
    recommended_next_action: ReportSection
    otc_categories: ReportSection
    referral_options: ReportSection
    important_limitations: ReportSection

    @property
    def sections(self) -> tuple[ReportSection, ...]:
        return (
            self.scan_information, self.analysis_summary, self.visual_region_findings, self.spectral_analysis,
            self.model_derived_change, self.evidence_explanation, self.safety_assessment,
            self.recommended_next_action, self.otc_categories, self.referral_options, self.important_limitations,
        )


def _field(value: Any, name: str) -> Any | None:
    return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _section(title: str, status: str, *items: tuple[str, Any]) -> ReportSection:
    return ReportSection(title, status, tuple(ReportItem(label, value) for label, value in items if value is not None))


def _limited(value: Any, names: tuple[str, ...]) -> tuple[ReportItem, ...]:
    return tuple(ReportItem(name, item) for name in names if (item := _field(value, name)) is not None)


class ReportGenerator:
    """Compose a report from existing outputs; never calculate or decide medical content."""

    def generate_report(
        self, scan_info: Any | None, vision: Any | None = None, monitoring: Any | None = None,
        evidence: Any | None = None, safety: Any | None = None, spectral: Any | None = None,
        ml: Any | None = None, product: Any | None = None, referral: Any | None = None,
    ) -> SpectraDermReport:
        scan_items = _limited(scan_info, ("scan_id", "user_id", "timestamp", "created_at", "image_reference"))
        scan_section = ReportSection("Scan Information", "available" if scan_items else "not_provided", scan_items)
        analysis_items = _limited(ml, ("status", "summary", "evaluation"))
        analysis = ReportSection("Analysis Summary", "available" if analysis_items else "not_provided", analysis_items)
        visual = _section("Visual / Region Findings", "available" if vision is not None else "unavailable", ("Model-derived finding", _text(_field(vision, "finding_summary") or _field(vision, "structured_finding"))))
        spectral_items = _limited(spectral, ("status", "summary", "reconstruction_method", "available"))
        spectral = ReportSection("Spectral Analysis", "available" if spectral_items else "not_provided", (ReportItem("Terminology", "AI-estimated spectral representation"), *spectral_items))
        change_items = _limited(monitoring, ("current_change_score", "trend", "current_status", "summary"))
        change = ReportSection("Model-Derived Change", "available" if change_items else "not_provided", (ReportItem("Terminology", "model-derived change"), *change_items))
        evidence_section = self._evidence_section(evidence)
        safety_section, decision = self._safety_section(safety)
        action, otc, referrals = self._action_sections(decision, product, referral)
        limitations = self._limitations(vision, monitoring, evidence, safety, spectral, ml)
        return SpectraDermReport(scan_section, analysis, visual, spectral, change, evidence_section, safety_section, action, otc, referrals, limitations)

    def _evidence_section(self, evidence: Any | None) -> ReportSection:
        if evidence is None:
            return _section("Evidence & Explanation", "unavailable", ("Notice", "Evidence was not available."))
        items: list[ReportItem] = []
        explanation = _text(_field(evidence, "explanation"))
        if explanation:
            items.append(ReportItem("Evidence-grounded explanation", explanation))
        retrieved = _field(evidence, "retrieved_evidence") or ()
        for item in retrieved:
            source = _field(item, "source")
            citation = tuple((name, _field(source, name) if source is not None else _field(item, name)) for name in ("source_id", "title", "organization", "url", "topic"))
            text = _field(item, "text")
            items.append(ReportItem("External evidence", tuple(pair for pair in citation if pair[1] is not None) + (("text", text),) if text is not None else tuple(pair for pair in citation if pair[1] is not None)))
        return ReportSection("Evidence & Explanation", "available" if items else "unavailable", tuple(items) or (ReportItem("Notice", "Evidence was not available."),))

    def _safety_section(self, safety: Any | None) -> tuple[ReportSection, bool | None]:
        decision = _field(safety, "professional_assessment_recommended") if safety is not None else None
        if type(decision) is not bool:
            return _section("Safety Assessment", "unavailable", ("Notice", "Safety decision is unavailable.")), None
        items = _limited(safety, ("safety_status", "concern_level", "reasons", "safety_message"))
        items += (ReportItem("Professional assessment recommended", decision),)
        return ReportSection("Safety Assessment", "available", items), decision

    def _action_sections(self, decision: bool | None, product: Any | None, referral: Any | None) -> tuple[ReportSection, ReportSection, ReportSection]:
        if decision is None:
            return (
                _section("Recommended Next Action", "blocked", ("Notice", "Safety decision is unavailable; downstream actions are blocked.")),
                ReportSection("General OTC Skincare Categories", "not_applicable", ()),
                ReportSection("Dermatology Referral Options", "not_applicable", ()),
            )
        if decision:
            referral_items = self._referral_items(referral)
            return (
                _section("Recommended Next Action", "available", ("Action", "Professional assessment was recommended by the Safety Agent.")),
                ReportSection("General OTC Skincare Categories", "not_applicable", ()),
                ReportSection("Dermatology Referral Options", "available" if referral_items else "unavailable", referral_items),
            )
        product_items = self._product_items(product)
        return (
            _section("Recommended Next Action", "available", ("Action", "Safety Agent did not recommend professional assessment.")),
            ReportSection("General OTC Skincare Categories", "available" if product_items else "unavailable", product_items),
            ReportSection("Dermatology Referral Options", "not_applicable", ()),
        )

    def _product_items(self, product: Any | None) -> tuple[ReportItem, ...]:
        if product is None:
            return ()
        recommendations = _field(product, "recommendations") or ()
        return tuple(ReportItem("General OTC skincare category", tuple((name, _field(item, name)) for name in ("category_id", "category_name", "neutral_description", "reason") if _field(item, name) is not None)) for item in recommendations)

    def _referral_items(self, referral: Any | None) -> tuple[ReportItem, ...]:
        if referral is None:
            return ()
        options = _field(referral, "options") or ()
        names = ("name", "address", "distance_km", "rating", "opening_hours", "phone", "website", "source")
        return tuple(ReportItem("Dermatology referral option", tuple((name, _field(item, name)) for name in names if _field(item, name) is not None)) for item in options)

    def _limitations(self, *inputs: Any) -> ReportSection:
        supplied = tuple(name for name, value in zip(("vision", "monitoring", "evidence", "safety", "spectral", "ml"), inputs) if value is not None)
        return _section("Important Limitations", "available", ("Notice", "This report composes supplied structured outputs and does not establish a medical condition or make a medical decision."), ("Supplied components", supplied or "none"))


def generate_report(scan_info: Any | None, **kwargs: Any) -> SpectraDermReport:
    """Convenience public API for deterministic report generation."""
    return ReportGenerator().generate_report(scan_info, **kwargs)
