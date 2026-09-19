"""Small environment-backed API configuration without secrets in source."""
from dataclasses import dataclass
import logging
import os
from pathlib import Path

from dotenv import load_dotenv


LOCAL_FRONTEND_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
logger = logging.getLogger(__name__)

def _project_path(value: str) -> Path:
    """Resolve relative paths against the repository, not the launch directory."""
    path = Path(value)
    return path if path.is_absolute() else (_PROJECT_ROOT / path).resolve()


@dataclass(frozen=True)
class APISettings:
    environment: str = "development"
    storage_root: Path = Path(".spectraderm-api-storage")
    cors_origins: tuple[str, ...] = LOCAL_FRONTEND_ORIGINS
    google_maps_api_key: str | None = None
    mstpp_checkpoint_path: Path | None = None
    mstpp_device: str | None = None

    @classmethod
    def from_environment(cls) -> "APISettings":
        dotenv_loaded = load_dotenv(_PROJECT_ROOT / ".env")
        configured_origins = tuple(item.strip() for item in os.getenv("SPECTRADERM_CORS_ORIGINS", "").split(",") if item.strip())
        origins = tuple(dict.fromkeys((*LOCAL_FRONTEND_ORIGINS, *configured_origins)))
        checkpoint_value = os.getenv("SPECTRADERM_MSTPP_CHECKPOINT")
        checkpoint = Path(checkpoint_value) if checkpoint_value else None
        if checkpoint is not None and not checkpoint.is_absolute():
            checkpoint = (_PROJECT_ROOT / checkpoint).resolve()
        logger.info(
            "API MST++ configuration: dotenv_loaded=%s checkpoint_configured=%s checkpoint_exists=%s device=%s",
            dotenv_loaded, checkpoint is not None, checkpoint.is_file() if checkpoint is not None else False,
            os.getenv("SPECTRADERM_MSTPP_DEVICE") or "auto",
        )
        return cls(
            os.getenv("SPECTRADERM_ENV", "development"),
            _project_path(os.getenv("SPECTRADERM_STORAGE_ROOT") or ".spectraderm-api-storage"),
            origins,
            os.getenv("GOOGLE_MAPS_API_KEY"),
            checkpoint,
            os.getenv("SPECTRADERM_MSTPP_DEVICE"),
        )
