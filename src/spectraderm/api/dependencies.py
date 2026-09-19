"""Overrideable API service container; no route constructs services directly."""
import os
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any, Protocol
from spectraderm.agents.product_agent import ProductAgent, ProductAgentInput
from spectraderm.agents.referral_agent import ReferralAgent
from spectraderm.api.analysis_adapter import AnalysisAdapterConfig, AnalysisOrchestrationAdapter
from spectraderm.api.rag_adapter import RetrievalOnlyRAGPipeline
from spectraderm.rag.llm import OpenAILLMProvider
from spectraderm.api.config import APISettings
from spectraderm.api.exceptions import ServiceUnavailable
from spectraderm.referral.dermatologist_api import DermatologistSearchService, GooglePlacesProvider
from spectraderm.reporting.report_generator import ReportGenerator
from spectraderm.storage.scan_storage import ScanStorage
from spectraderm.users.user_management import FileUserRepository, UserManagement

def to_data(value: Any) -> Any:
    if is_dataclass(value): return {name: to_data(item) for name, item in asdict(value).items()}
    if isinstance(value, dict): return {str(key): to_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)): return [to_data(item) for item in value]
    return value

class AnalysisService(Protocol):
    def analyze(self, scan: Any, payload: dict[str, Any]) -> Any: ...

class UnavailableAnalysisService:
    def analyze(self, scan: Any, payload: dict[str, Any]) -> Any:
        raise ServiceUnavailable("Analysis orchestration adapter is not configured.")

class ActionService:
    def __init__(self, product_agent: Any, referral_agent: Any): self.product_agent, self.referral_agent = product_agent, referral_agent
    def products(self, analysis: Any) -> Any | None:
        safety = _field(analysis, "safety_result")
        if _field(safety, "professional_assessment_recommended") is not False: return None
        monitoring_result = _field(analysis, "monitoring_result")
        evidence_inputs = _field(monitoring_result, "evidence_inputs")
        comparison = evidence_inputs.get("comparison") if isinstance(evidence_inputs, Mapping) else None
        return self.product_agent.recommend(ProductAgentInput(vision_result=_field(analysis, "vision_result"), monitoring_result=monitoring_result, evidence_result=_field(analysis, "evidence_result"), safety_result=safety, comparison=comparison))
    def referrals(self, analysis: Any, location: dict[str, Any] | None, radius_km: float) -> Any | None:
        safety = _field(analysis, "safety_result")
        if _field(safety, "professional_assessment_recommended") is not True: return None
        from spectraderm.agents.referral_agent import ReferralAgentInput
        return self.referral_agent.refer(ReferralAgentInput(safety_result=safety, location=location, radius_km=radius_km))

def _field(value: Any, name: str) -> Any: return value.get(name) if isinstance(value, dict) else getattr(value, name, None)

class ServiceContainer:
    def __init__(self, settings: APISettings):
        self.users = UserManagement(FileUserRepository(settings.storage_root))
        self.scans = ScanStorage(settings.storage_root, self.users)
        provider = DermatologistSearchService(GooglePlacesProvider(api_key=settings.google_maps_api_key), "google_places")
        self.actions = ActionService(ProductAgent(), ReferralAgent(provider))
        # OPENAI_API_KEY is optional: without it, RAG stays retrieval-only
        # (evidence is returned but no generated explanation), exactly as before.
        llm_provider = OpenAILLMProvider() if os.getenv("OPENAI_API_KEY") else None
        self.rag = RetrievalOnlyRAGPipeline(llm=llm_provider)
        self.analysis: AnalysisService = AnalysisOrchestrationAdapter.with_defaults(
            self.scans,
            AnalysisAdapterConfig(
                mstpp_checkpoint_path=settings.mstpp_checkpoint_path,
                mstpp_device=settings.mstpp_device,
            ),
            rag_pipeline=self.rag,
        )
        self.reports = ReportGenerator()
        self.analysis_results: dict[str, Any] = {}

def get_container() -> ServiceContainer:
    raise RuntimeError("Container dependency was not attached to the FastAPI application.")
