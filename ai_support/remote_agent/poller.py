from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests

from ai_support.core.local_powershell import (
    run_powershell,
    safe_net_command_list_adapters_json,
    safe_net_command_test_connectivity_on_interface,
    safe_net_command_get_adapter_ip,
    safe_net_command_set_static_ipv4,
    safe_net_command_test_ip_in_use,
    ensure_ipv4,
    ensure_prefix_length,
)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def _parse_dns_list(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    # Permite formatos: "8.8.8.8,8.8.4.4" o "8.8.8.8; 8.8.4.4"
    parts = [p.strip() for p in raw.replace(";", ",").split(",")]
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        try:
            out.append(ensure_ipv4(p))
        except Exception:
            continue
    return out


def _state_path() -> str:
    # Prefer ProgramData if available
    base = os.getenv("ProgramData") or os.getcwd()
    d = os.path.join(base, "AI-Support")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "agent_state.json")


def _load_state() -> dict[str, Any]:
    p = _state_path()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: dict[str, Any]) -> None:
    p = _state_path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


@dataclass(frozen=True)
class ServerConfig:
    base_url: str
    agent_token: str
    agent_id: str
    user_key: str
    poll_interval_s: int = 5
    timeout_s: int = 25


def load_server_config() -> ServerConfig:
    base = _env("AI_SUPPORT_REMOTE_CONTROL_URL")
    token = _env("AI_SUPPORT_AGENT_TOKEN")
    agent_id = _env("AI_SUPPORT_AGENT_ID")
    user_key = _env("AI_SUPPORT_USER_KEY", "") or ""

    if not base:
        raise RuntimeError("Falta AI_SUPPORT_REMOTE_CONTROL_URL (ej: http://SERVIDOR:8787)")
    if not token:
        raise RuntimeError("Falta AI_SUPPORT_AGENT_TOKEN (debe coincidir con el servidor)")

    if not agent_id:
        # fallback: hostname
        agent_id = socket.gethostname()

    poll_raw = _env("AI_SUPPORT_AGENT_POLL_INTERVAL_S", "5")
    timeout_raw = _env("AI_SUPPORT_AGENT_TIMEOUT_S", "25")
    try:
        poll = int(poll_raw or "5")
    except Exception:
        poll = 5
    try:
        timeout = int(timeout_raw or "25")
    except Exception:
        timeout = 25

    return ServerConfig(
        base_url=base.rstrip("/"),
        agent_token=token,
        agent_id=agent_id,
        user_key=user_key,
        poll_interval_s=max(2, poll),
        timeout_s=max(10, timeout),
    )


def _headers(cfg: ServerConfig) -> dict[str, str]:
    return {"X-AI-SUPPORT-AGENT-TOKEN": cfg.agent_token}


def _json_load_maybe(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


def _list_adapters() -> list[dict[str, Any]]:
    res = run_powershell(safe_net_command_list_adapters_json(), timeout_s=20)
    data = _json_load_maybe(res.stdout)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def _pick_up_adapter(adapters: list[dict[str, Any]]) -> Optional[str]:
    for a in adapters:
        status_text = str(a.get("Status") or "").strip().lower()
        if status_text == "up":
            name = str(a.get("Name") or "").strip()
            if name:
                return name
    return None


def _test_connectivity(interface_alias: str, target: str = "8.8.8.8") -> dict[str, Any]:
    res = run_powershell(safe_net_command_test_connectivity_on_interface(interface_alias, target), timeout_s=15)
    data = _json_load_maybe(res.stdout)
    if data and isinstance(data, dict):
        ok = bool(data.get("PingSucceeded", False))
        return {"success": ok, "details": f"Ping a {target}: {'OK' if ok else 'FALLÓ'}", "response": data}
    return {"success": False, "details": f"No se pudo probar conectividad en {interface_alias}", "response": None}


def _get_ip_config(interface_alias: str) -> dict[str, Any]:
    res = run_powershell(safe_net_command_get_adapter_ip(interface_alias), timeout_s=15)
    data = _json_load_maybe(res.stdout)
    if data and isinstance(data, dict):
        ip = data.get("IPAddress")
        prefix = data.get("PrefixLength")
        gw = data.get("Gateway")
        dns = data.get("DNS", [])
        return {
            "has_ip": bool(ip),
            "ip": str(ip or ""),
            "prefix_length": int(prefix) if prefix else 24,
            "gateway": str(gw or ""),
            "dns": dns if isinstance(dns, list) else [],
        }
    return {"has_ip": False, "ip": "", "prefix_length": 24, "gateway": "", "dns": []}


def _ip_in_use(ip: str) -> bool:
    ps = run_powershell(safe_net_command_test_ip_in_use(ip), timeout_s=6)
    raw = (ps.stdout or "").strip().lower()
    return raw == "true"


def _apply_static_ip(
    *,
    interface_alias: str,
    ip: str,
    prefix_length: int,
    default_gateway: Optional[str],
    dns_servers: Optional[list[str]],
) -> dict[str, Any]:
    ip = ensure_ipv4(ip)
    prefix_length = ensure_prefix_length(prefix_length)

    cmd = safe_net_command_set_static_ipv4(
        interface_alias=interface_alias,
        ip=ip,
        prefix_length=prefix_length,
        default_gateway=default_gateway,
        dns_servers=dns_servers,
    )
    res = run_powershell(cmd, timeout_s=45)
    return {
        "ok": res.returncode == 0,
        "returncode": res.returncode,
        "stdout": (res.stdout or "")[-4000:],
        "stderr": (res.stderr or "")[-4000:],
    }


def _fetch_ip_pool(cfg: ServerConfig) -> tuple[list[str], set[str]]:
    r = requests.get(
        f"{cfg.base_url}/agent/ip-pool",
        headers=_headers(cfg),
        timeout=cfg.timeout_s,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ip-pool failed: {r.status_code} {r.text}")
    data = r.json() or {}
    candidates = data.get("candidates")
    assigned = data.get("assigned")
    return (
        candidates if isinstance(candidates, list) else [],
        set(assigned) if isinstance(assigned, list) else set(),
    )


def _choose_new_ip(*, current_ip: str, candidates: list[str], assigned: set[str]) -> Optional[str]:
    # No elige .0/.1/.255 si el pool vino por CIDR; igual filtramos por seguridad
    bad_last = {"0", "1", "255"}
    for ip in candidates:
        try:
            ip_v = ensure_ipv4(str(ip))
        except Exception:
            continue
        if ip_v == current_ip:
            continue
        if ip_v in assigned:
            continue
        last = ip_v.split(".")[-1]
        if last in bad_last:
            continue
        if _ip_in_use(ip_v):
            continue
        return ip_v
    return None


def _do_job_connectivity(cfg: ServerConfig, payload: dict[str, Any]) -> dict[str, Any]:
    target = str(payload.get("target") or "8.8.8.8").strip() or "8.8.8.8"
    adapters = _list_adapters()
    up = _pick_up_adapter(adapters)
    if not up:
        return {
            "ok": False,
            "details": "No se encontró adaptador Up",
            "adapters": adapters[:10],
        }
    test = _test_connectivity(up, target)
    return {
        "ok": bool(test.get("success")),
        "details": test.get("details"),
        "interface": up,
        "ip_config": _get_ip_config(up),
        "response": test.get("response"),
    }


def _do_job_diagnose_and_fix(cfg: ServerConfig, payload: dict[str, Any]) -> dict[str, Any]:
    """Diagnostica y decide si cambia IP.

    - Si hay conectividad, no cambia nada.
    - Si no hay conectividad y allow_changes=true, intenta elegir IP del pool del servidor
      (pero el check de 'en uso' se hace localmente en el cliente).
    """

    allow_changes = bool(payload.get("allow_changes", True))
    target = str(payload.get("target") or "8.8.8.8").strip() or "8.8.8.8"

    adapters = _list_adapters()
    up = _pick_up_adapter(adapters)
    if not up:
        return {"ok": False, "details": "No se encontró adaptador Up", "adapters": adapters[:10]}

    ip_cfg = _get_ip_config(up)
    test = _test_connectivity(up, target)
    if bool(test.get("success")):
        return {
            "ok": True,
            "changed": False,
            "details": "Conectividad OK. No se aplicaron cambios.",
            "interface": up,
            "ip_config": ip_cfg,
        }

    if not allow_changes:
        return {
            "ok": False,
            "changed": False,
            "details": "Sin conectividad y cambios deshabilitados.",
            "interface": up,
            "ip_config": ip_cfg,
            "connectivity": test,
        }

    # Requiere correr como administrador para setear IP.
    candidates, assigned = _fetch_ip_pool(cfg)
    current_ip = str(ip_cfg.get("ip") or "").strip()
    new_ip = _choose_new_ip(current_ip=current_ip, candidates=candidates, assigned=assigned)
    if not new_ip:
        return {
            "ok": False,
            "changed": False,
            "details": "No se encontró IP libre en el pool (o todas responden ping).",
            "interface": up,
            "ip_config": ip_cfg,
        }

    # Defaults por entorno, por si el adaptador no tiene gateway/dns (p.ej. sin IP previa)
    default_gw_env = (_env("AI_SUPPORT_NET_DEFAULT_GATEWAY") or "").strip() or None
    default_prefix_env = (_env("AI_SUPPORT_NET_DEFAULT_PREFIX_LENGTH") or "").strip()
    default_dns_env = _parse_dns_list(_env("AI_SUPPORT_NET_DEFAULT_DNS"))

    gw = str(ip_cfg.get("gateway") or "").strip() or default_gw_env

    dns = ip_cfg.get("dns") if isinstance(ip_cfg.get("dns"), list) else None
    dns_servers = [str(x).strip() for x in (dns or []) if str(x).strip()]
    if not dns_servers:
        dns_servers = default_dns_env or ["8.8.8.8", "8.8.4.4"]

    prefix_length = int(ip_cfg.get("prefix_length") or 24)
    if (not ip_cfg.get("has_ip")) and default_prefix_env:
        try:
            prefix_length = ensure_prefix_length(int(default_prefix_env))
        except Exception:
            prefix_length = prefix_length

    apply = _apply_static_ip(
        interface_alias=up,
        ip=new_ip,
        prefix_length=prefix_length,
        default_gateway=gw,
        dns_servers=dns_servers,
    )

    state = _load_state()
    state["last_attempt_ts"] = time.time()
    state["last_interface"] = up
    state["last_old_ip"] = current_ip
    state["last_new_ip"] = new_ip
    state["last_apply_ok"] = bool(apply.get("ok"))
    _save_state(state)

    if not apply.get("ok"):
        return {
            "ok": False,
            "changed": False,
            "details": "Falló aplicar IP (¿sin permisos de Administrador?).",
            "interface": up,
            "old_ip": current_ip,
            "new_ip": new_ip,
            "apply": apply,
        }

    # Re-test after change
    test2 = _test_connectivity(up, target)
    return {
        "ok": bool(test2.get("success")),
        "changed": True,
        "details": "IP aplicada. Conectividad re-probada.",
        "interface": up,
        "old_ip": current_ip,
        "new_ip": new_ip,
        "apply": apply,
        "connectivity_after": test2,
    }


def run_forever() -> None:
    cfg = load_server_config()

    # Register
    meta = {
        "ts": time.time(),
        "ip": None,
        "state_path": _state_path(),
    }
    try:
        r = requests.post(
            f"{cfg.base_url}/agent/register",
            json={
                "agent_id": cfg.agent_id,
                "hostname": socket.gethostname(),
                "user_key": cfg.user_key,
                "meta": meta,
            },
            headers=_headers(cfg),
            timeout=cfg.timeout_s,
        )
        if r.status_code != 200:
            raise RuntimeError(f"register failed: {r.status_code} {r.text}")
    except Exception as e:
        raise RuntimeError(f"No se pudo registrar con el servidor: {e}")

    while True:
        try:
            poll = requests.get(
                f"{cfg.base_url}/agent/poll",
                params={"agent_id": cfg.agent_id},
                headers=_headers(cfg),
                timeout=cfg.timeout_s,
            )
            if poll.status_code != 200:
                time.sleep(cfg.poll_interval_s)
                continue
            data = poll.json() or {}
            job = data.get("job")
            if not job:
                time.sleep(cfg.poll_interval_s)
                continue

            job_id = str(job.get("job_id") or "")
            job_type = str(job.get("job_type") or "")
            payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}

            ok = True
            result: dict[str, Any] = {}
            err = ""
            try:
                if job_type == "connectivity_check":
                    result = _do_job_connectivity(cfg, payload)
                    ok = bool(result.get("ok"))
                elif job_type == "diagnose_and_fix":
                    result = _do_job_diagnose_and_fix(cfg, payload)
                    ok = bool(result.get("ok"))
                else:
                    ok = False
                    result = {}
                    err = f"job_type desconocido: {job_type}"
            except Exception as e:
                ok = False
                err = f"Error ejecutando job: {type(e).__name__}: {e}"

            try:
                requests.post(
                    f"{cfg.base_url}/agent/report",
                    json={"job_id": job_id, "ok": ok, "result": result, "error": err},
                    headers=_headers(cfg),
                    timeout=cfg.timeout_s,
                )
            except Exception:
                pass

        except Exception:
            time.sleep(cfg.poll_interval_s)
