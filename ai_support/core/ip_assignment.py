from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Optional

from ai_support.core.local_powershell import (
    run_powershell,
    safe_net_command_get_ipconfiguration_json,
    safe_net_command_get_ipv4_addresses_json,
    safe_net_command_list_adapters_json,
    safe_net_command_set_static_ipv4,
    safe_net_command_test_ip_in_use,
    safe_net_command_test_connectivity_on_interface,
    safe_net_command_get_adapter_ip,
    ensure_ipv4,
)
from ai_support.core.ip_pool_mysql import (
    fetch_assigned_ipv4_from_mysql,
    fetch_candidate_ipv4_pool_from_mysql,
    register_user_ipv4_in_mysql,
)


@dataclass(frozen=True)
class IPAssignResult:
    ok: bool
    details: str
    assigned_ip: Optional[str] = None


def _json_load_maybe(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


def list_net_adapters() -> list[dict]:
    """Lista adaptadores de red (NetAdapter) como dicts."""
    res = run_powershell(safe_net_command_list_adapters_json(), timeout_s=20)
    data = _json_load_maybe(res.stdout)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def get_adapter_ipv4(interface_alias: str) -> list[dict]:
    res = run_powershell(safe_net_command_get_ipv4_addresses_json(interface_alias), timeout_s=20)
    data = _json_load_maybe(res.stdout)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def test_connectivity_on_interface(interface_alias: str, target: str = "8.8.8.8") -> dict:
    """Prueba conectividad desde un adaptador específico.
    
    Returns:
        dict con claves: success (bool), details (str), response (dict opcional)
    """
    try:
        res = run_powershell(safe_net_command_test_connectivity_on_interface(interface_alias, target), timeout_s=15)
        data = _json_load_maybe(res.stdout)
        
        if data and isinstance(data, dict):
            ping_ok = data.get("PingSucceeded", False)
            return {
                "success": bool(ping_ok),
                "details": f"Ping a {target}: {'OK' if ping_ok else 'FALLÓ'}",
                "response": data
            }
        else:
            return {
                "success": False,
                "details": f"No se pudo probar conectividad en {interface_alias}",
                "response": None
            }
    except Exception as e:
        return {
            "success": False,
            "details": f"Error al probar conectividad: {e}",
            "response": None
        }


def get_current_adapter_ip_config(interface_alias: str) -> dict:
    """Obtiene configuración IP actual del adaptador.
    
    Returns:
        dict con claves: has_ip (bool), ip (str), prefix_length (int), gateway (str), dns (list)
    """
    try:
        res = run_powershell(safe_net_command_get_adapter_ip(interface_alias), timeout_s=15)
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
                "dns": dns if isinstance(dns, list) else []
            }
        else:
            return {"has_ip": False, "ip": "", "prefix_length": 24, "gateway": "", "dns": []}
    except Exception as e:
        return {"has_ip": False, "ip": "", "prefix_length": 24, "gateway": "", "dns": [], "error": str(e)}


def get_adapter_ipconfiguration(interface_alias: str) -> dict:
    res = run_powershell(safe_net_command_get_ipconfiguration_json(interface_alias), timeout_s=20)
    data = _json_load_maybe(res.stdout)
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return {}


def _extract_gateway_from_ipconfig(ipconfig: dict) -> Optional[str]:
    # Get-NetIPConfiguration devuelve IPv4DefaultGateway como objeto con NextHop.
    gw = ipconfig.get("IPv4DefaultGateway")
    if isinstance(gw, dict):
        nh = gw.get("NextHop")
        if isinstance(nh, str) and nh.strip():
            try:
                return ensure_ipv4(nh.strip())
            except Exception:
                return None
    return None


def _extract_dns_from_ipconfig(ipconfig: dict) -> list[str]:
    dns = ipconfig.get("DNSServer")
    out: list[str] = []
    if isinstance(dns, dict):
        addrs = dns.get("ServerAddresses")
        if isinstance(addrs, list):
            for a in addrs:
                if isinstance(a, str) and a.strip():
                    try:
                        out.append(ensure_ipv4(a.strip()))
                    except Exception:
                        pass
    return out


def _local_ipv4_set(interface_alias: str) -> set[str]:
    entries = get_adapter_ipv4(interface_alias)
    out: set[str] = set()
    for e in entries:
        ip = e.get("IPAddress")
        if isinstance(ip, str) and ip.strip():
            try:
                out.add(ensure_ipv4(ip.strip()))
            except Exception:
                pass
    return out


def pick_free_ip_from_mysql_pool(
    *,
    interface_alias: str,
    require_no_ping_response: bool = True,
    max_checks: int = 200,
) -> tuple[Optional[str], str]:
    """Elige una IP candidata que no esté registrada en MySQL y que no esté configurada localmente.

    Si require_no_ping_response=True, además exige que la IP NO responda a Test-NetConnection.
    """
    assigned = fetch_assigned_ipv4_from_mysql()
    candidates = fetch_candidate_ipv4_pool_from_mysql()
    local_ips = _local_ipv4_set(interface_alias)

    checked = 0
    for ip in candidates:
        if ip in assigned:
            continue
        if ip in local_ips:
            continue
        if require_no_ping_response:
            ps = run_powershell(safe_net_command_test_ip_in_use(ip), timeout_s=5)
            raw = (ps.stdout or "").strip().lower()
            if raw == "true":
                continue
        checked += 1
        if checked >= max_checks:
            break
        return ip, (
            f"Elegida IP candidata {ip}. "
            f"(MySQL assigned={len(assigned)}, candidates={len(candidates)}, local={sorted(local_ips)})"
        )

    return None, (
        f"No se encontró IP libre en el pool. "
        f"(MySQL assigned={len(assigned)}, candidates={len(candidates)}, local={sorted(local_ips)})"
    )


def iter_free_ips_from_pool(
    *,
    interface_alias: str,
    require_no_ping_response: bool = True,
    max_candidates: int = 300,
):
    """Generador que yield IPs libres del pool una a una (no asignadas en MySQL, sin ping).

    Permite iterar sobre candidatas y probar conectividad tras cada asignación.
    """
    assigned = fetch_assigned_ipv4_from_mysql()
    candidates = fetch_candidate_ipv4_pool_from_mysql()
    local_ips = _local_ipv4_set(interface_alias)

    checked = 0
    for ip in candidates:
        if ip in assigned:
            continue
        if ip in local_ips:
            continue
        if require_no_ping_response:
            ps = run_powershell(safe_net_command_test_ip_in_use(ip), timeout_s=5)
            raw = (ps.stdout or "").strip().lower()
            if raw == "true":
                continue
        yield ip
        checked += 1
        if checked >= max_candidates:
            break


def assign_ip_until_connectivity(
    *,
    user_key: str,
    interface_alias: str,
    prefix_length: int = 24,
    default_gateway: Optional[str] = None,
    dns_servers: Optional[list] = None,
    connectivity_target: str = "8.8.8.8",
    max_attempts: int = 10,
    wait_secs: float = 3.0,
) -> IPAssignResult:
    """Asigna IPs del pool una a una hasta encontrar una que dé conectividad.

    Flujo por cada candidata:
    1. Aplica la IP en el adaptador local (requiere admin).
    2. Espera wait_secs.
    3. Prueba ping a connectivity_target.
    4. Si hay conectividad → registra en MySQL y retorna ok=True.
    5. Si no → prueba la siguiente IP del pool.
    6. Si se agotan max_attempts → retorna ok=False con última IP intentada.
    """
    import time as _time

    gw = default_gateway or "172.17.87.1"
    dns = dns_servers or ["172.17.66.9", "172.17.40.9"]

    last_ip: Optional[str] = None
    attempt = 0

    for ip in iter_free_ips_from_pool(interface_alias=interface_alias):
        attempt += 1
        last_ip = ip

        # Aplicar IP
        cmd = safe_net_command_set_static_ipv4(
            interface_alias=interface_alias,
            ip=ip,
            prefix_length=int(prefix_length),
            default_gateway=gw,
            dns_servers=dns,
        )
        res = run_powershell(cmd, timeout_s=40)
        if res.returncode != 0:
            if attempt >= max_attempts:
                return IPAssignResult(ok=False, assigned_ip=ip, details=f"Falló asignación PowerShell en {ip}: {res.stderr[-500:]}")
            continue

        # Esperar a que se aplique
        _time.sleep(wait_secs)

        # Probar conectividad
        conn = test_connectivity_on_interface(interface_alias, connectivity_target)
        if conn.get("success"):
            # Registrar en MySQL
            try:
                rows = register_user_ipv4_in_mysql(user_key=user_key, ip=ip)
            except Exception as reg_err:
                rows = 0
                return IPAssignResult(
                    ok=True,
                    assigned_ip=ip,
                    details=f"IP {ip} con conectividad OK. Advertencia: no se registró en MySQL: {reg_err}",
                )
            return IPAssignResult(
                ok=True,
                assigned_ip=ip,
                details=f"IP {ip} asignada con conectividad OK (intento {attempt}). MySQL filas={rows}.",
            )

        if attempt >= max_attempts:
            break

    if last_ip:
        return IPAssignResult(
            ok=False,
            assigned_ip=last_ip,
            details=f"Se probaron {attempt} IPs del pool sin obtener conectividad a {connectivity_target}. Última IP intentada: {last_ip}.",
        )
    return IPAssignResult(ok=False, details="No se encontraron IPs disponibles en el pool.")


def assign_ip_to_ethernet_and_register(
    *,
    user_key: str,
    interface_alias: str,
    prefix_length: int = 24,
    require_no_ping_response: bool = True,
    dry_run: bool = False,
    force_ip: Optional[str] = None,
) -> IPAssignResult:
    """Asigna una IP estática a una interfaz y la registra en MySQL.

    Flujo:
    1) Si force_ip está especificado, usa esa IP (debe estar disponible).
    2) Si no, obtiene pool de IPs candidatas desde MySQL.
    3) Obtiene IPs ya asignadas/registradas desde MySQL (por defecto personal.ip).
    4) Elige una IP libre (sin escanear toda la red, solo prueba candidatas).
    5) Setea IP en el adaptador (requiere admin).
    6) Ejecuta UPDATE/INSERT configurable para registrar la IP del usuario.

    IMPORTANTE: La query de registro debe configurarse en env:
      AI_SUPPORT_MYSQL_REGISTER_USER_IP_QUERY
    """

    try:
        if force_ip:
            # Usar IP específica (validar que esté disponible)
            ip = ensure_ipv4(force_ip)
            assigned = fetch_assigned_ipv4_from_mysql()
            if ip in assigned:
                return IPAssignResult(ok=False, details=f"IP {ip} ya está asignada en MySQL.")
            
            if require_no_ping_response:
                ps = run_powershell(safe_net_command_test_ip_in_use(ip), timeout_s=5)
                raw = (ps.stdout or "").strip().lower()
                if raw == "true":
                    return IPAssignResult(ok=False, details=f"IP {ip} está en uso (responde a ping).")
            
            why = f"IP forzada: {ip}"
        else:
            ip, why = pick_free_ip_from_mysql_pool(
                interface_alias=interface_alias,
                require_no_ping_response=require_no_ping_response,
            )
            if not ip:
                return IPAssignResult(ok=False, details=why)

        ipconfig = get_adapter_ipconfiguration(interface_alias)
        gw = _extract_gateway_from_ipconfig(ipconfig)
        dns = _extract_dns_from_ipconfig(ipconfig)

        if dry_run:
            return IPAssignResult(
                ok=True,
                assigned_ip=ip,
                details=(
                    "DRY RUN - no se aplicaron cambios.\n"
                    f"Interface: {interface_alias}\n"
                    f"IP: {ip}/{int(prefix_length)}\n"
                    f"Gateway: {gw or '(none)'}\n"
                    f"DNS: {dns or '(inherit/none)'}\n"
                    f"Decision: {why}"
                ),
            )

        # Setear IP local
        cmd = safe_net_command_set_static_ipv4(
            interface_alias=interface_alias,
            ip=ip,
            prefix_length=int(prefix_length),
            default_gateway=gw,
            dns_servers=dns,
        )
        res = run_powershell(cmd, timeout_s=40)
        if res.returncode != 0:
            return IPAssignResult(
                ok=False,
                assigned_ip=ip,
                details=(
                    "Falló la asignación en PowerShell.\n"
                    f"stdout: {res.stdout[-2000:]}\n"
                    f"stderr: {res.stderr[-2000:]}"
                ),
            )

        # Registrar en MySQL
        rows = register_user_ipv4_in_mysql(user_key=user_key, ip=ip)
        if rows <= 0:
            return IPAssignResult(
                ok=False,
                assigned_ip=ip,
                details=(
                    "IP aplicada localmente, pero el UPDATE/INSERT en MySQL no afectó filas.\n"
                    "Revisa AI_SUPPORT_MYSQL_REGISTER_USER_IP_QUERY y el user_key.\n"
                    f"PowerShell result: {res.stdout[-1500:]}"
                ),
            )

        return IPAssignResult(
            ok=True,
            assigned_ip=ip,
            details=(
                f"OK. IP {ip} asignada a {interface_alias} y registrada en MySQL (filas afectadas={rows}).\n"
                f"Decision: {why}"
            ),
        )

    except Exception as e:
        return IPAssignResult(ok=False, details=f"Error: {type(e).__name__}: {e}")
