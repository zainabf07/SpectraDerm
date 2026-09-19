"""Module U Step 1: deterministic local medical-knowledge corpus loading."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOKEN_TARGET = 500
TOKEN_OVERLAP = 75
_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"


@dataclass(frozen=True)
class KnowledgeSource:
    source_id: str
    title: str
    organization: str
    url: str
    topic: str
    category: str
    retrieved_at: str
    cleaned_text: str


@dataclass(frozen=True)
class KnowledgeChunk:
    source_id: str
    title: str
    organization: str
    url: str
    topic: str
    category: str
    retrieved_at: str
    chunk_id: str
    section: str
    text: str


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _sections(text: str) -> list[tuple[str, list[str]]]:
    """Read ``##`` headings and preserve non-empty paragraph boundaries."""
    current_title = "Overview"
    current_paragraphs: list[str] = []
    result: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("## "):
            if current_paragraphs:
                result.append((current_title, current_paragraphs))
            current_title = line[3:].strip()
            current_paragraphs = []
        elif line:
            current_paragraphs.append(line)
    if current_paragraphs:
        result.append((current_title, current_paragraphs))
    return result


def chunk_cleaned_text(
    text: str, target_tokens: int = TOKEN_TARGET, overlap_tokens: int = TOKEN_OVERLAP
) -> list[tuple[str, str]]:
    """Chunk cleaned text near a token target while preferring paragraphs/sections."""
    if target_tokens <= 0 or overlap_tokens < 0 or overlap_tokens >= target_tokens:
        raise ValueError("require target_tokens > overlap_tokens >= 0")
    chunks: list[tuple[str, str]] = []
    for section, paragraphs in _sections(text):
        buffer: list[str] = []
        for paragraph in paragraphs:
            paragraph_tokens = _tokenize(paragraph)
            if not paragraph_tokens:
                continue
            candidate = buffer + paragraph_tokens
            if buffer and len(candidate) > target_tokens:
                chunks.append((section, " ".join(buffer)))
                buffer = buffer[-overlap_tokens:] + paragraph_tokens if overlap_tokens else paragraph_tokens
            else:
                buffer = candidate
            while len(buffer) > target_tokens:
                chunks.append((section, " ".join(buffer[:target_tokens])))
                buffer = buffer[target_tokens - overlap_tokens:]
        if buffer:
            chunks.append((section, " ".join(buffer)))
    return chunks


def load_sources(data_dir: Path = _DATA_DIR) -> tuple[KnowledgeSource, ...]:
    """Load the fixed, locally cached Module U source catalog."""
    manifest = json.loads((data_dir / "source_manifest.json").read_text(encoding="utf-8"))
    sources = []
    for item in manifest["sources"]:
        text = (data_dir / item["cleaned_text_file"]).read_text(encoding="utf-8").strip()
        sources.append(KnowledgeSource(**{key: item[key] for key in KnowledgeSource.__dataclass_fields__ if key != "cleaned_text"}, cleaned_text=text))
    return tuple(sources)


def build_chunks(data_dir: Path = _DATA_DIR) -> tuple[KnowledgeChunk, ...]:
    """Build deterministic, attribution-preserving chunks from cached sources."""
    chunks: list[KnowledgeChunk] = []
    for source in load_sources(data_dir):
        for index, (section, text) in enumerate(chunk_cleaned_text(source.cleaned_text), start=1):
            chunks.append(KnowledgeChunk(
                source_id=source.source_id, title=source.title, organization=source.organization,
                url=source.url, topic=source.topic, category=source.category,
                retrieved_at=source.retrieved_at, chunk_id=f"{source.source_id}:chunk-{index:04d}",
                section=section, text=text,
            ))
    return tuple(chunks)
