from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

import requests


@dataclass(frozen=True)
class RemoteAgentConfig:
    base_url: str
    token: str
    timeout_s: int = 25


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def get_remote_agent_config(
    *,
    user_key: str,
    override_url: Optional[str] = None,
    override_token: Optional[str] = None,
) -> Optional[RemoteAgentConfig]:
    """Resuelve configuración del agente remoto para un usuario/PC.

    Prioridad:
    1) AI_SUPPORT_REMOTE_AGENT_URL (único)
    2) AI_SUPPORT_REMOTE_AGENT_URL_TEMPLATE (ej: http://{user_key}:8765)

    Token requerido: AI_SUPPORT_REMOTE_AGENT_TOKEN
    """

    token = (override_token or _env("AI_SUPPORT_REMOTE_AGENT_TOKEN"))
    if not token:
        return None

    base = (override_url or _env("AI_SUPPORT_REMOTE_AGENT_URL"))
    if not base:
        template = _env("AI_SUPPORT_REMOTE_AGENT_URL_TEMPLATE")
        if template:
            try:
                base = template.format(user_key=user_key)
            except Exception:
                base = None

    if not base:
        return None

    timeout_raw = _env("AI_SUPPORT_REMOTE_AGENT_TIMEOUT_S", "25")
    try:
        timeout_s = int(timeout_raw or "25")
    except Exception:
        timeout_s = 25

    return RemoteAgentConfig(base_url=base.rstrip("/"), token=token, timeout_s=timeout_s)


class RemoteAgentError(RuntimeError):
    pass


def _headers(cfg: RemoteAgentConfig) -> dict[str, str]:
    return {"X-AI-SUPPORT-TOKEN": cfg.token}


def health(cfg: RemoteAgentConfig) -> dict[str, Any]:
    r = requests.get(f"{cfg.base_url}/health", headers=_headers(cfg), timeout=cfg.timeout_s)
    if r.status_code != 200:
        raise RemoteAgentError(f"health failed: {r.status_code} {r.text}")
    return r.json()


def list_adapters(cfg: RemoteAgentConfig) -> list[dict[str, Any]]:
    r = requests.get(f"{cfg.base_url}/adapters", headers=_headers(cfg), timeout=cfg.timeout_s)
    if r.status_code != 200:
        raise RemoteAgentError(f"adapters failed: {r.status_code} {r.text}")
    data = r.json() or {}
    adapters = data.get("adapters")
    return adapters if isinstance(adapters, list) else []


def get_ip_config(cfg: RemoteAgentConfig, *, interface_alias: str) -> dict[str, Any]:
    r = requests.get(
        f"{cfg.base_url}/ip-config",
        params={"interface_alias": interface_alias},
        headers=_headers(cfg),
        timeout=cfg.timeout_s,
    )
    if r.status_code != 200:
        raise RemoteAgentError(f"ip-config failed: {r.status_code} {r.text}")
    data = r.json() or {}
    cfg_data = data.get("config")
    return cfg_data if isinstance(cfg_data, dict) else {}


def test_connectivity(cfg: RemoteAgentConfig, *, interface_alias: str, target: str = "8.8.8.8") -> dict[str, Any]:
    r = requests.post(
        f"{cfg.base_url}/connectivity/test",
        json={"interface_alias": interface_alias, "target": target},
        headers=_headers(cfg),
        timeout=cfg.timeout_s,
    )
    if r.status_code != 200:
        raise RemoteAgentError(f"connectivity test failed: {r.status_code} {r.text}")
    data = r.json() or {}
    result = data.get("result")
    return result if isinstance(result, dict) else {"success": False, "details": "invalid response"}


def set_static_ipv4(
    cfg: RemoteAgentConfig,
    *,
    interface_alias: str,
    ip: str,
    prefix_length: int = 24,
    default_gateway: Optional[str] = None,
    dns_servers: Optional[list[str]] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "interface_alias": interface_alias,
        "ip": ip,
        "prefix_length": int(prefix_length),
        "default_gateway": default_gateway,
        "dns_servers": dns_servers,
        "dry_run": bool(dry_run),
    }
    r = requests.post(
        f"{cfg.base_url}/ip/set-static",
        json=payload,
        headers=_headers(cfg),
        timeout=max(cfg.timeout_s, 45),
    )
    if r.status_code != 200:
        raise RemoteAgentError(f"set-static failed: {r.status_code} {r.text}")
    data = r.json() or {}
    if not isinstance(data, dict):
        raise RemoteAgentError("set-static invalid response")
    return data
