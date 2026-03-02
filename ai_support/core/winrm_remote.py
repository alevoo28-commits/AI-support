from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Optional

from ai_support.core.local_powershell import (
    ensure_ipv4,
    ensure_prefix_length,
    run_powershell,
    safe_net_command_get_adapter_ip,
    safe_net_command_list_adapters_json,
    safe_net_command_set_static_ipv4,
    safe_net_command_test_connectivity_on_interface,
)


_HOST_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def ensure_remote_host(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("host vacío")

    # Permitir IPv4
    try:
        return ensure_ipv4(value)
    except Exception:
        pass

    # Hostname básico (sin espacios, sin backslashes, sin quotes)
    if not _HOST_RE.match(value):
        raise ValueError("host inválido")
    return value


def _json_load_maybe(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


@dataclass(frozen=True)
class WinRMConfig:
    auth: str = "Negotiate"  # Kerberos/Negotiate
    use_ssl: bool = False
    port: Optional[int] = None


def _winrm_config_from_env() -> WinRMConfig:
    auth = (os.getenv("AI_SUPPORT_WINRM_AUTH", "Negotiate") or "Negotiate").strip()
    use_ssl = (os.getenv("AI_SUPPORT_WINRM_USE_SSL", "false") or "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }
    port_raw = (os.getenv("AI_SUPPORT_WINRM_PORT") or "").strip()
    port = None
    if port_raw:
        try:
            port = int(port_raw)
        except Exception:
            port = None
    return WinRMConfig(auth=auth, use_ssl=use_ssl, port=port)


def _invoke_command_ps(*, host: str, inner_ps: str) -> str:
    cfg = _winrm_config_from_env()
    host = ensure_remote_host(host)

    # Nota: no aceptamos credenciales aquí para evitar passwords en texto plano.
    # El proceso Streamlit debe correr bajo una cuenta con permisos (idealmente dominio).

    computer_part = f"-ComputerName '{host}'"
    auth_part = f"-Authentication {cfg.auth}" if cfg.auth else ""
    ssl_part = "-UseSSL" if cfg.use_ssl else ""
    port_part = f"-Port {int(cfg.port)}" if cfg.port else ""

    # Forzar errores para que el caller los pueda detectar.
    # Out-String para que siempre tengamos texto.
    return (
        "Invoke-Command "
        f"{computer_part} {auth_part} {ssl_part} {port_part} "
        f"-ScriptBlock {{ {inner_ps} }} -ErrorAction Stop | Out-String"
    )


def list_net_adapters_remote(host: str) -> list[dict]:
    cmd = _invoke_command_ps(host=host, inner_ps=safe_net_command_list_adapters_json())
    res = run_powershell(cmd, timeout_s=35)
    data = _json_load_maybe(res.stdout)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def test_connectivity_on_interface_remote(host: str, interface_alias: str, target: str = "8.8.8.8") -> dict:
    inner = safe_net_command_test_connectivity_on_interface(interface_alias, target)
    cmd = _invoke_command_ps(host=host, inner_ps=inner)
    res = run_powershell(cmd, timeout_s=25)
    data = _json_load_maybe(res.stdout)
    if data and isinstance(data, dict):
        ping_ok = data.get("PingSucceeded", False)
        return {
            "success": bool(ping_ok),
            "details": f"Ping a {target}: {'OK' if ping_ok else 'FALLÓ'}",
            "response": data,
        }
    return {"success": False, "details": f"No se pudo probar conectividad en {interface_alias}", "response": None}


def get_current_adapter_ip_config_remote(host: str, interface_alias: str) -> dict:
    inner = safe_net_command_get_adapter_ip(interface_alias)
    cmd = _invoke_command_ps(host=host, inner_ps=inner)
    res = run_powershell(cmd, timeout_s=25)
    data = _json_load_maybe(res.stdout)
    if data and isinstance(data, dict):
        ip = data.get("IPAddress")
        prefix = data.get("PrefixLength")
        gateway = data.get("Gateway")
        dns = data.get("DNS", [])
        return {
            "has_ip": bool(ip),
            "ip": str(ip or ""),
            "prefix_length": int(prefix) if prefix else 24,
            "gateway": str(gateway or ""),
            "dns": dns if isinstance(dns, list) else [],
        }
    return {"has_ip": False, "ip": "", "prefix_length": 24, "gateway": "", "dns": []}


def set_static_ipv4_remote(
    host: str,
    *,
    interface_alias: str,
    ip: str,
    prefix_length: int = 24,
    default_gateway: Optional[str] = None,
    dns_servers: Optional[list[str]] = None,
    dry_run: bool = False,
) -> dict:
    ip = ensure_ipv4(ip)
    prefix_length = ensure_prefix_length(prefix_length)
    gw = ensure_ipv4(default_gateway) if default_gateway else None

    dns = None
    if dns_servers:
        dns = [ensure_ipv4(str(x)) for x in dns_servers]

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "planned": {
                "host": ensure_remote_host(host),
                "interface_alias": interface_alias,
                "ip": ip,
                "prefix_length": prefix_length,
                "default_gateway": gw,
                "dns_servers": dns or [],
            },
        }

    inner = safe_net_command_set_static_ipv4(
        interface_alias=interface_alias,
        ip=ip,
        prefix_length=prefix_length,
        default_gateway=gw,
        dns_servers=dns,
    )

    cmd = _invoke_command_ps(host=host, inner_ps=inner)
    res = run_powershell(cmd, timeout_s=60)

    ok = res.returncode == 0
    return {
        "ok": ok,
        "returncode": res.returncode,
        "stdout": (res.stdout or "")[-4000:],
        "stderr": (res.stderr or "")[-4000:],
    }
