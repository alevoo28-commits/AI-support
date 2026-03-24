"""
Detección y obtención de modelos desde GitHub Models y LM Studio.

Este módulo maneja:
- Listado de modelos disponibles en GitHub Models
- Listado de modelos disponibles en LM Studio
- Detección de errores de acceso y rate limiting
"""

import json
import urllib.request


def lmstudio_fetch_model_ids(base_url: str) -> list[str]:
    """Obtiene la lista de modelos disponibles en LM Studio."""
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("data", [])
    ids: list[str] = []
    for item in data:
        model_id = item.get("id")
        if isinstance(model_id, str) and model_id:
            ids.append(model_id)
    return ids


def github_fetch_model_ids(base_url: str, token: str) -> list[str]:
    """Lista modelos disponibles en GitHub Models (Azure AI Inference compatible).

    Intenta con headers típicos para maximizar compatibilidad:
    - Authorization: Bearer <token>
    - api-key: <token>
    """
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "api-key": token,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    # GitHub Models (Azure AI Inference) suele devolver una lista de objetos.
    # Preferimos "name" (IDs cortos como gpt-4o-mini) cuando esté disponible.
    if isinstance(payload, list):
        data = payload
    elif isinstance(payload, dict):
        data = payload.get("data", [])
    else:
        data = []

    ids: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        model_name = item.get("name")
        model_id = item.get("id")
        if isinstance(model_name, str) and model_name:
            ids.append(model_name)
        elif isinstance(model_id, str) and model_id:
            ids.append(model_id)

    # De-dup preservando orden
    seen: set[str] = set()
    result: list[str] = []
    for mid in ids:
        if mid in seen:
            continue
        seen.add(mid)
        result.append(mid)
    return result


def is_github_no_access_error(err: Exception) -> bool:
    """Detecta si el error es por falta de acceso a GitHub Models."""
    msg = str(err).lower()
    return (
        "permissiondeniederror" in msg
        or "no_access" in msg
        or "no access to model" in msg
        or "error code: 403" in msg
    )


def is_rate_limit_error(err: Exception) -> bool:
    """Detecta si el error es por rate limiting de GitHub Models."""
    msg = str(err).lower()
    return (
        "ratelimiterror" in msg
        or "too many requests" in msg
        or "error code: 429" in msg
        or "rate limit" in msg
    )
