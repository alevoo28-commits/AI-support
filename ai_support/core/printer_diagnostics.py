from __future__ import annotations

import os
import re
from dataclasses import dataclass
from dataclasses import dataclass
from typing import Optional

from ai_support.core.local_powershell import (
    PowerShellResult,
    run_powershell,
    safe_printer_command_add_shared,
    safe_printer_command_add_ip,
    safe_printer_command_list_drivers,
    safe_printer_command_list_drivers_json,
    safe_driver_command_pnputil_add,
    safe_printer_command_list_ports,
    safe_printer_command_list_printers,
    safe_printer_command_restart_spooler,
    safe_printer_command_set_default,
    safe_printer_command_test_port,
    safe_printer_command_print_test_page,
)


@dataclass(frozen=True)
class PrinterDiagnostics:
    printers: PowerShellResult
    ports: PowerShellResult
    spooler: Optional[PowerShellResult] = None
    test: Optional[PowerShellResult] = None


def collect_printer_diagnostics(
    *,
    include_spooler_status: bool = True,
    test_ip: Optional[str] = None,
    test_port: int = 9100,
) -> PrinterDiagnostics:
    printers = run_powershell(safe_printer_command_list_printers(), timeout_s=20)
    ports = run_powershell(safe_printer_command_list_ports(), timeout_s=20)

    spooler = None
    if include_spooler_status:
        spooler = run_powershell("Get-Service Spooler | Format-List | Out-String", timeout_s=10)

    test = None
    if test_ip:
        test = run_powershell(safe_printer_command_test_port(test_ip, test_port), timeout_s=10)

    return PrinterDiagnostics(printers=printers, ports=ports, spooler=spooler, test=test)


def add_shared_printer(unc_path: str) -> PowerShellResult:
    return run_powershell(safe_printer_command_add_shared(unc_path), timeout_s=60)


def set_default_printer(printer_name: str) -> PowerShellResult:
    return run_powershell(safe_printer_command_set_default(printer_name), timeout_s=30)


def restart_spooler() -> PowerShellResult:
    return run_powershell(safe_printer_command_restart_spooler(), timeout_s=30)


def print_test_page(printer_name: str) -> PowerShellResult:
    return run_powershell(safe_printer_command_print_test_page(printer_name), timeout_s=60)


def list_printer_drivers() -> PowerShellResult:
    return run_powershell(safe_printer_command_list_drivers(), timeout_s=30)


def _list_printer_driver_names() -> list[str]:
    res = run_powershell(safe_printer_command_list_drivers_json(), timeout_s=30)
    raw = (res.stdout or "").strip()
    if not raw:
        return []
    try:
        import json

        payload = json.loads(raw)
    except Exception:
        return []

    names: list[str] = []
    if isinstance(payload, dict):
        n = payload.get("Name")
        if isinstance(n, str) and n:
            names.append(n)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                n = item.get("Name")
                if isinstance(n, str) and n:
                    names.append(n)
    return names


def _find_inf_files(drivers_dir: str) -> list[str]:
    out: list[str] = []
    if not drivers_dir:
        return out
    if not os.path.isdir(drivers_dir):
        return out
    for root, _dirs, files in os.walk(drivers_dir):
        for f in files:
            if f.lower().endswith(".inf"):
                out.append(os.path.join(root, f))
    return out


_WORD_RE = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)


def _score_match(text: str, candidate: str) -> int:
    tokens = {t.lower() for t in _WORD_RE.findall(text or "")}
    if not tokens:
        return 0
    c = (candidate or "").lower()
    return sum(1 for t in tokens if t in c)


@dataclass(frozen=True)
class PrinterAutoConnectLog:
    ok: bool
    ip: str
    details: str


def install_printer_drivers_from_folder(
    drivers_dir: str,
    *,
    query_text: str = "",
) -> str:
    """Instala drivers desde una carpeta local (busca .inf y usa pnputil).

    Devuelve un log de texto compacto (para UI/prompt).
    """

    limit = 20
    try:
        limit = int(os.getenv("AI_SUPPORT_PRINTER_DRIVER_INSTALL_LIMIT", "20"))
    except Exception:
        limit = 20
    if limit < 1:
        limit = 1

    infs = _find_inf_files(drivers_dir)
    if not infs:
        return f"[AUTO_PRINTER] No se encontraron .inf en: {drivers_dir}"

    # Prioriza infs que matcheen el texto del usuario
    scored = sorted((( _score_match(query_text, p), p) for p in infs), reverse=True)
    selected = [p for _s, p in scored[:limit]]

    lines: list[str] = []
    lines.append(f"[AUTO_PRINTER] Encontrados {len(infs)} .inf. Instalando {len(selected)}...")
    for p in selected:
        try:
            res = run_powershell(safe_driver_command_pnputil_add(p), timeout_s=120)
            out = (res.stdout or res.stderr).strip()
            lines.append(f"- pnputil: {os.path.basename(p)} -> rc={res.returncode}")
            if out:
                lines.append(out[:800])
        except Exception as e:
            lines.append(f"- pnputil: {os.path.basename(p)} -> ERROR: {e}")
    return "\n".join(lines)[:8000]


def _sanitize_folder_name(value: str) -> str:
    v = (value or "").strip()
    # Windows-safe-ish folder name
    out = []
    for ch in v:
        if ch.isalnum() or ch in {" ", "-", "_", "."}:
            out.append(ch)
    s = "".join(out).strip().strip(".")
    return s[:80] if s else ""


def connect_printer_ip(
    ip: str,
    *,
    printer_name: Optional[str] = None,
    driver_name: Optional[str] = None,
    port_number: int = 9100,
) -> PowerShellResult:
    # Defaults conservadores: intenta con drivers comunes si el usuario no especifica.
    name = printer_name.strip() if isinstance(printer_name, str) else ""
    if not name:
        name = f"IP_{ip}"

    driver = driver_name.strip() if isinstance(driver_name, str) else ""
    if not driver:
        # Drivers típicos presentes en Windows (pueden variar según versión/idioma)
        # Si no existen, Add-Printer devolverá error y la UI puede pedir el driver correcto.
        driver = "Microsoft IPP Class Driver"

    return run_powershell(
        safe_printer_command_add_ip(ip, name, driver, port_number=port_number),
        timeout_s=90,
    )


def auto_connect_printer_ip(
    *,
    ip: str,
    user_text: str,
    drivers_dir: str,
    printer_display_name: Optional[str] = None,
    port_number: int = 9100,
) -> PrinterAutoConnectLog:
    """Flujo automático: conectar por IP; si falla, instalar drivers locales y reintentar."""

    log_lines: list[str] = [f"[AUTO_PRINTER] Objetivo: {ip}:{port_number}"]

    # 1) Test de conectividad (rápido)
    try:
        test = run_powershell(safe_printer_command_test_port(ip, port_number), timeout_s=10)
        log_lines.append("[AUTO_PRINTER] Test-NetConnection:")
        log_lines.append(((test.stdout or test.stderr).strip() or "(sin salida)")[:800])
    except Exception as e:
        log_lines.append(f"[AUTO_PRINTER] Test-NetConnection falló: {e}")

    printer_name = f"IP_{ip}"
    if isinstance(printer_display_name, str) and printer_display_name.strip():
        # El nombre real en Windows no puede contener caracteres raros; lo dejamos simple.
        printer_name = printer_display_name.strip()

    # 1) Validar conectividad básica al puerto
    try:
        tn = run_powershell(safe_printer_command_test_port(ip, port=port_number), timeout_s=15)
        log_lines.append(f"[AUTO_PRINTER] Test-NetConnection rc={tn.returncode}")
        log_lines.append(((tn.stdout or tn.stderr).strip() or "(sin salida)")[:800])
    except Exception as e:
        log_lines.append(f"[AUTO_PRINTER] Test-NetConnection falló: {e}")

    # 2) Intento directo con drivers comunes (si están instalados en el PC)
    driver_candidates = [
        "Microsoft IPP Class Driver",
        "Microsoft Enhanced Point and Print Compatibility Driver",
        "Generic / Text Only",
    ]
    for cand in driver_candidates:
        try:
            res = connect_printer_ip(ip, printer_name=printer_name, driver_name=cand, port_number=port_number)
            out = (res.stdout or res.stderr).strip()
            log_lines.append(f"[AUTO_PRINTER] Intento conectar (driver='{cand}') rc={res.returncode}")
            if out:
                log_lines.append(out[:1200])
            if res.returncode == 0:
                try:
                    tp = print_test_page(printer_name)
                    log_lines.append(f"[AUTO_PRINTER] Página de prueba rc={tp.returncode}")
                    log_lines.append(((tp.stdout or tp.stderr).strip() or "(sin salida)")[:800])
                except Exception as e:
                    log_lines.append(f"[AUTO_PRINTER] No se pudo imprimir página de prueba: {e}")
                return PrinterAutoConnectLog(ok=True, ip=ip, details="\n".join(log_lines)[:8000])
        except Exception as e:
            log_lines.append(f"[AUTO_PRINTER] Intento conectar (driver='{cand}') falló: {e}")

    # 3) Instalar drivers desde carpeta local
    try:
        base_dir = drivers_dir
        # Si tenemos nombre/modelo, intenta una subcarpeta específica primero.
        model_folder = _sanitize_folder_name(printer_display_name or user_text)
        tried_any = False
        if model_folder:
            candidate = os.path.join(drivers_dir, model_folder)
            if os.path.isdir(candidate):
                tried_any = True
                log_lines.append(f"[AUTO_PRINTER] Instalando drivers desde carpeta específica: {candidate}")
                log_lines.append(install_printer_drivers_from_folder(candidate, query_text=user_text))

        if not tried_any:
            log_lines.append(f"[AUTO_PRINTER] Instalando drivers desde carpeta base: {base_dir}")
            log_lines.append(install_printer_drivers_from_folder(base_dir, query_text=user_text))
    except Exception as e:
        log_lines.append(f"[AUTO_PRINTER] Instalación de drivers falló: {e}")

    # 4) Elegir mejor driver instalado por heurística y reintentar
    try:
        drivers = _list_printer_driver_names()
        best = ""
        best_score = 0
        for d in drivers:
            s = _score_match(user_text, d)
            if s > best_score:
                best_score = s
                best = d

        if not best:
            # fallback: si existe "Universal" o "PCL" o "PS" en drivers
            for hint in ["universal", "pcl", "ps", "ipp"]:
                for d in drivers:
                    if hint in d.lower():
                        best = d
                        break
                if best:
                    break

        if not best:
            best = "Microsoft IPP Class Driver"

        res2 = connect_printer_ip(ip, printer_name=printer_name, driver_name=best, port_number=port_number)
        out2 = (res2.stdout or res2.stderr).strip()
        log_lines.append(f"[AUTO_PRINTER] Reintento con driver='{best}' rc={res2.returncode}")
        if out2:
            log_lines.append(out2[:1200])

        ok = res2.returncode == 0
        if not ok:
            log_lines.append(
                "[AUTO_PRINTER] Nota: puede requerir driver exacto del fabricante o permisos de administrador para instalar drivers."
            )
        else:
            try:
                tp = print_test_page(printer_name)
                log_lines.append(f"[AUTO_PRINTER] Página de prueba rc={tp.returncode}")
                log_lines.append(((tp.stdout or tp.stderr).strip() or "(sin salida)")[:800])
            except Exception as e:
                log_lines.append(f"[AUTO_PRINTER] No se pudo imprimir página de prueba: {e}")
        return PrinterAutoConnectLog(ok=ok, ip=ip, details="\n".join(log_lines)[:8000])
    except Exception as e:
        log_lines.append(f"[AUTO_PRINTER] Reintento falló: {e}")
        return PrinterAutoConnectLog(ok=False, ip=ip, details="\n".join(log_lines)[:8000])


def format_diagnostics_for_prompt(diag: PrinterDiagnostics) -> str:
    parts: list[str] = []
    parts.append("[DIAGNOSTICO_LOCAL_IMPRESORAS]")
    parts.append("--- Get-Printer ---")
    parts.append(diag.printers.stdout.strip() or diag.printers.stderr.strip() or "(sin salida)")
    parts.append("--- Get-PrinterPort ---")
    parts.append(diag.ports.stdout.strip() or diag.ports.stderr.strip() or "(sin salida)")

    if diag.spooler:
        parts.append("--- Spooler ---")
        parts.append(diag.spooler.stdout.strip() or diag.spooler.stderr.strip() or "(sin salida)")

    if diag.test:
        parts.append("--- Test-NetConnection ---")
        parts.append(diag.test.stdout.strip() or diag.test.stderr.strip() or "(sin salida)")

    return "\n".join(parts)[:8000]
