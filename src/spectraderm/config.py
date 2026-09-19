"""Central configuration for filesystem locations and logging."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _path_from_environment(variable: str, default: Path, project_root: Path) -> Path:
    """Return an absolute path using an optional environment override."""
    value = os.getenv(variable)
    path = Path(value) if value else default
    return path if path.is_absolute() else (project_root / path).resolve()


@dataclass(frozen=True)
class Settings:
    """Resolved project paths; use this instead of hard-coding local paths."""

    project_root: Path
    data_dir: Path
    models_dir: Path
    log_level: str
    hyperskin_root: Path
    uminho_hsfd_root: Path

    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def interim_data_dir(self) -> Path:
        return self.data_dir / "interim"

    @property
    def processed_data_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def external_data_dir(self) -> Path:
        return self.data_dir / "external"

    def ensure_local_directories(self) -> None:
        """Create expected local storage directories when a workflow needs them."""
        for directory in (
            self.raw_data_dir,
            self.interim_data_dir,
            self.processed_data_dir,
            self.external_data_dir,
            self.models_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build and cache project settings from defaults and environment variables."""
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    return Settings(
        project_root=project_root,
        data_dir=_path_from_environment("SPECTRADERM_DATA_DIR", Path("data"), project_root),
        models_dir=_path_from_environment("SPECTRADERM_MODELS_DIR", Path("models"), project_root),
        log_level=os.getenv("SPECTRADERM_LOG_LEVEL", "INFO").upper(),
        hyperskin_root=_path_from_environment(
            "SPECTRADERM_HYPERSKIN_ROOT", Path("data/raw/hyper_skin"), project_root
        ),
        uminho_hsfd_root=_path_from_environment(
            "SPECTRADERM_UMINHO_HSFD_ROOT", Path("data/raw/uminho_hsfd"), project_root
        ),
    )
