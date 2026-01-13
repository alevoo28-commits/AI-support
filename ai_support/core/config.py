from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str  # "github" | "lmstudio"
    base_url: str
    api_key_env: str
    model: str

    @property
    def api_key(self) -> str | None:
        value = os.getenv(self.api_key_env)
        if value:
            return value
        # LM Studio normalmente no valida api_key, pero el cliente OpenAI sí lo exige.
        if self.provider == "lmstudio":
            return "lm-studio"
        return None


@dataclass(frozen=True)
class EmbeddingsProviderConfig:
    provider: str  # "github" | "lmstudio" | "none"
    base_url: str
    api_key_env: str
    model: str

    @property
    def api_key(self) -> str | None:
        value = os.getenv(self.api_key_env)
        if value:
            return value
        if self.provider == "lmstudio":
            return "lm-studio"
        return None


def default_github_llm() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="github",
        base_url=os.getenv("GITHUB_MODELS_BASE_URL", "https://models.inference.ai.azure.com"),
        api_key_env="GITHUB_TOKEN",
        model=os.getenv("GITHUB_LLM_MODEL", "gpt-4o-mini"),
    )


def default_lmstudio_llm() -> LLMProviderConfig:
    # LM Studio suele exponer un endpoint compatible OpenAI en /v1
    return LLMProviderConfig(
        provider="lmstudio",
        base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
        api_key_env="LMSTUDIO_API_KEY",
        model=os.getenv("LMSTUDIO_LLM_MODEL", ""),
    )


def default_github_embeddings() -> EmbeddingsProviderConfig:
    return EmbeddingsProviderConfig(
        provider="github",
        base_url=os.getenv("GITHUB_MODELS_BASE_URL", "https://models.inference.ai.azure.com"),
        api_key_env="GITHUB_TOKEN",
        model=os.getenv("GITHUB_EMBED_MODEL", "text-embedding-3-small"),
    )


def default_lmstudio_embeddings() -> EmbeddingsProviderConfig:
    return EmbeddingsProviderConfig(
        provider="lmstudio",
        base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
        api_key_env="LMSTUDIO_API_KEY",
        model=os.getenv("LMSTUDIO_EMBED_MODEL", ""),
    )


def excel_only_mode_enabled() -> bool:
    """Modo seguro: el sistema SOLO procesa consultas sobre Excel/CSV.

    Cuando está activo, se deben deshabilitar acciones externas (PowerShell, integraciones, automatización).
    Activación por env:
    - AI_SUPPORT_EXCEL_ONLY=true|1|yes
    - o AI_SUPPORT_MODE=excel_only
    """
    mode = (os.getenv("AI_SUPPORT_MODE") or "").strip().lower()
    if mode == "excel_only":
        return True
    raw = (os.getenv("AI_SUPPORT_EXCEL_ONLY") or "").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}
