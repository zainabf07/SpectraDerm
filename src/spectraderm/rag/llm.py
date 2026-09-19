"""Small provider-agnostic language-generation interfaces for Module W."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """A language-only provider used after attributed evidence is retrieved."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return one explanation for the supplied evidence-grounded prompt."""


class DeterministicMockLLM(LLMProvider):
    """Dependency-free provider for repeatable tests and notebook demonstrations."""

    def __init__(self, response: str = "Mock explanation based only on the supplied evidence.") -> None:
        self.response = response
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        self.prompts.append(prompt)
        return self.response


class OpenAILLMProvider(LLMProvider):
    """Calls the OpenAI Chat Completions API to generate the evidence-grounded explanation.

    This is the only network-calling provider in Module W: it receives an
    already fully-constrained prompt (see rag_pipeline.build_evidence_prompt)
    whose only medical content is the supplied retrieved evidence. It does not
    add, alter, or invent any medical claim itself.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        api_key_environment: str = "OPENAI_API_KEY",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.getenv(api_key_environment)
        self._model = model
        self._timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured; cannot generate an evidence-grounded explanation."
            )
        import httpx  # imported lazily so the dependency-free providers above stay import-safe

        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("OpenAI response did not contain an explanation.") from error
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenAI returned an empty explanation.")
        return content.strip()
