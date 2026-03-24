"""
Gestión de creación y caching del orquestador de agentes.

Este módulo maneja:
- Creación lazy del OrquestadorMultiagente
- Caching del orquestador con fingerprint de configuración
"""

import streamlit as st
from ai_support.core.config import EmbeddingsProviderConfig, LLMProviderConfig


def create_orchestrator(
    llm_cfg: LLMProviderConfig,
    emb_cfg: EmbeddingsProviderConfig,
    user_id: str | None,
    allowed_area_ids: list[str] | None,
):
    """Factory para crear OrquestadorMultiagente con lazy import.
    
    El import se realiza dentro de la función para reducir el tiempo de 
    startup del módulo streamlit_app.
    """
    # Lazy import para reducir costo de arranque de streamlit_app.
    from ai_support.orchestrator.multi_orchestrator import OrquestadorMultiagente

    return OrquestadorMultiagente(
        llm_config=llm_cfg,
        embeddings_config=emb_cfg,
        user_id=user_id,
        allowed_area_ids=allowed_area_ids,
    )


@st.cache_resource(show_spinner=False)
def create_orchestrator_cached(
    llm_provider: str,
    llm_base_url: str,
    llm_api_key_env: str,
    llm_model: str,
    emb_provider: str,
    emb_base_url: str,
    emb_api_key_env: str,
    emb_model: str,
    user_id: str,
    allowed_area_ids: tuple[str, ...],
):
    """Crea orquestador con cache por configuración.
    
    El cache se invalida cuando cambia cualquier parámetro de configuración.
    """
    llm_cfg = LLMProviderConfig(
        provider=llm_provider,
        base_url=llm_base_url,
        api_key_env=llm_api_key_env,
        model=llm_model,
    )
    emb_cfg = EmbeddingsProviderConfig(
        provider=emb_provider,
        base_url=emb_base_url,
        api_key_env=emb_api_key_env,
        model=emb_model,
    )
    return create_orchestrator(
        llm_cfg=llm_cfg,
        emb_cfg=emb_cfg,
        user_id=user_id or None,
        allowed_area_ids=list(allowed_area_ids) if allowed_area_ids else None,
    )
