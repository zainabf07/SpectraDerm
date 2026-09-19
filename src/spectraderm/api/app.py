"""FastAPI application factory for AK–AO."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from spectraderm.api.config import APISettings
from spectraderm.api.dependencies import ServiceContainer, get_container
from spectraderm.api.error_handlers import install_error_handlers
from spectraderm.api.routes import actions, analysis, health, history, reports, scans, users

def create_app(settings: APISettings | None = None, container: ServiceContainer | None = None) -> FastAPI:
    settings = settings or APISettings.from_environment()
    app = FastAPI(title="SpectraDerm API", version="1.0.0")
    app.state.settings, app.state.services = settings, container or ServiceContainer(settings)
    app.dependency_overrides[get_container] = lambda: app.state.services
    if settings.cors_origins: app.add_middleware(CORSMiddleware, allow_origins=list(dict.fromkeys(("http://localhost:5173", "http://127.0.0.1:5173", *settings.cors_origins))), allow_credentials=False, allow_methods=["OPTIONS", "GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type"])
    install_error_handlers(app)
    app.include_router(health.router)
    for route in (users.router, scans.router, analysis.router, history.router, reports.router, actions.router): app.include_router(route, prefix="/api/v1")
    return app

app = create_app()
