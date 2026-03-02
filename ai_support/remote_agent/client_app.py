from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from ai_support.core.ip_assignment import (
    get_current_adapter_ip_config,
    list_net_adapters,
    test_connectivity_on_interface,
)
from ai_support.core.local_powershell import (
    ensure_ipv4,
    ensure_prefix_length,
    run_powershell,
    safe_net_command_set_static_ipv4,
)


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def _require_token(x_ai_support_token: Optional[str]) -> None:
    expected = _env("AI_SUPPORT_REMOTE_AGENT_TOKEN")
    if not expected:
        raise RuntimeError(
            "Falta AI_SUPPORT_REMOTE_AGENT_TOKEN en el agente. "
            "Define un token para proteger el endpoint."
        )

    got = (x_ai_support_token or "").strip()
    if not got or got != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def auth_dependency(x_ai_support_token: Optional[str] = Header(default=None)) -> None:
    _require_token(x_ai_support_token)


app = FastAPI(title="AI Support Remote Agent", version="0.1.0")


class ConnectivityTestRequest(BaseModel):
    interface_alias: str = Field(..., min_length=1)
    target: str = Field(default="8.8.8.8", min_length=1)


class SetStaticIPv4Request(BaseModel):
    interface_alias: str = Field(..., min_length=1)
    ip: str = Field(..., min_length=7)
    prefix_length: int = Field(default=24, ge=0, le=32)
    default_gateway: Optional[str] = None
    dns_servers: Optional[list[str]] = None
    dry_run: bool = False


@app.get("/health")
def health(_: None = Depends(auth_dependency)):
    return {"ok": True, "ts": time.time()}


@app.get("/adapters")
def adapters(_: None = Depends(auth_dependency)):
    return {"adapters": list_net_adapters()}


@app.get("/ip-config")
def ip_config(interface_alias: str, _: None = Depends(auth_dependency)):
    interface_alias = interface_alias.strip()
    if not interface_alias:
        raise HTTPException(status_code=400, detail="interface_alias requerido")
    return {"config": get_current_adapter_ip_config(interface_alias)}


@app.post("/connectivity/test")
def connectivity_test(req: ConnectivityTestRequest, _: None = Depends(auth_dependency)):
    return {"result": test_connectivity_on_interface(req.interface_alias, req.target)}


@app.post("/ip/set-static")
def set_static_ip(req: SetStaticIPv4Request, _: None = Depends(auth_dependency)):
    # Validaciones seguras
    interface_alias = req.interface_alias.strip()
    if not interface_alias:
        raise HTTPException(status_code=400, detail="interface_alias requerido")

    ip = ensure_ipv4(req.ip)
    prefix = ensure_prefix_length(req.prefix_length)

    gw = ensure_ipv4(req.default_gateway) if req.default_gateway else None
    dns = None
    if req.dns_servers:
        dns = [ensure_ipv4(x) for x in req.dns_servers]

    if req.dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "planned": {
                "interface_alias": interface_alias,
                "ip": ip,
                "prefix_length": prefix,
                "default_gateway": gw,
                "dns_servers": dns or [],
            },
        }

    cmd = safe_net_command_set_static_ipv4(
        interface_alias=interface_alias,
        ip=ip,
        prefix_length=prefix,
        default_gateway=gw,
        dns_servers=dns,
    )

    # Esto requiere privilegios de Administrador en el PC cliente.
    res = run_powershell(cmd, timeout_s=45)
    ok = res.returncode == 0
    return {
        "ok": ok,
        "returncode": res.returncode,
        "stdout": (res.stdout or "")[-4000:],
        "stderr": (res.stderr or "")[-4000:],
    }
