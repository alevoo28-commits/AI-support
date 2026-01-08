from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PowerShellResult:
    command: str
    stdout: str
    stderr: str
    returncode: int


# Permitimos un subconjunto controlado de caracteres necesarios para comandos PowerShell
# internos (pipes, comillas, $, =). No se aceptan backticks ni saltos de línea.
_SAFE_TEXT_RE = re.compile(r"^[\w\s\-_.:;,/\\()\[\]{}@|\$'\"=]+$", re.UNICODE)

# Para argumentos (nombres/paths) usamos una regex MÁS estricta (sin quotes/pipes/$/=)
_SAFE_ARG_RE = re.compile(r"^[\w\s\-_.:;,/\\()\[\]{}@]+$", re.UNICODE)


def _ensure_safe_text(value: str, field: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field} vacío")
    # Los comandos internos (one-liners) pueden ser largos.
    # Mantener un límite razonable para evitar abuso, pero no tan bajo que rompa operaciones válidas.
    if len(value) > 8000:
        raise ValueError(f"{field} demasiado largo")
    if not _SAFE_TEXT_RE.match(value):
        raise ValueError(f"{field} contiene caracteres no permitidos")
    return value


def _ensure_safe_arg_text(value: str, field: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field} vacío")
    if len(value) > 520:
        raise ValueError(f"{field} demasiado largo")
    if not _SAFE_ARG_RE.match(value):
        raise ValueError(f"{field} contiene caracteres no permitidos")
    return value


_IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


def ensure_ipv4(value: str) -> str:
    value = value.strip()
    if not _IPV4_RE.match(value):
        raise ValueError("IP inválida")
    parts = value.split(".")
    if any(int(p) > 255 for p in parts):
        raise ValueError("IP inválida")
    return value


_UNC_RE = re.compile(r"^\\\\[^\\]+\\[^\\]+$")


def ensure_unc_printer(value: str) -> str:
    value = value.strip()
    if not _UNC_RE.match(value):
        raise ValueError("Ruta UNC inválida (usa \\\\SERVIDOR\\IMPRESORA)")
    return value


def run_powershell(command: str, timeout_s: int = 20) -> PowerShellResult:
    """Ejecuta PowerShell en modo seguro (sin perfil).

    Nota: este runner NO acepta comandos arbitrarios del modelo; solo debe ser usado
    desde funciones internas con parámetros validados.
    """

    command = _ensure_safe_text(command, "command")

    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )

    return PowerShellResult(
        command=command,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        returncode=int(completed.returncode or 0),
    )


def safe_printer_command_list_printers() -> str:
    return (
        "Get-Printer | Select-Object Name,DriverName,PortName,Shared,ShareName,PrinterStatus | Format-Table -AutoSize | Out-String"
    )


def safe_printer_command_list_printers_json() -> str:
    # Salida parseable para UI (selector) y automatización.
    return (
        "Get-Printer | Select-Object Name,DriverName,PortName,Shared,ShareName,PrinterStatus | ConvertTo-Json -Compress | Out-String"
    )


def safe_printer_command_list_ports() -> str:
    return "Get-PrinterPort | Select-Object Name,PrinterHostAddress,PortNumber,Protocol | Format-Table -AutoSize | Out-String"


def safe_printer_command_list_ports_json() -> str:
    return (
        "Get-PrinterPort | Select-Object Name,PrinterHostAddress,PortNumber,Protocol | ConvertTo-Json -Compress | Out-String"
    )


def safe_printer_command_get_printer_json(printer_name: str) -> str:
    printer_name = _ensure_safe_arg_text(printer_name, "printer_name")
    return (
        f"Get-Printer -Name '{printer_name}' -ErrorAction Stop | "
        f"Select-Object Name,DriverName,PortName,Shared,ShareName,PrinterStatus | ConvertTo-Json -Compress | Out-String"
    )


def safe_printer_command_get_port_json(port_name: str) -> str:
    port_name = _ensure_safe_arg_text(port_name, "port_name")
    return (
        f"Get-PrinterPort -Name '{port_name}' -ErrorAction Stop | "
        f"Select-Object Name,PrinterHostAddress,PortNumber,Protocol | ConvertTo-Json -Compress | Out-String"
    )


def safe_printer_command_list_jobs(printer_name: str) -> str:
    printer_name = _ensure_safe_arg_text(printer_name, "printer_name")
    # Get-PrintJob puede no estar disponible en algunos entornos; manejamos silenciosamente.
    return (
        f"Get-PrintJob -PrinterName '{printer_name}' -ErrorAction SilentlyContinue | "
        f"Select-Object Id,DocumentName,JobStatus,TotalPages,PagesPrinted,SubmittedTime | ConvertTo-Json -Compress | Out-String"
    )


def safe_printer_command_clear_jobs(printer_name: str) -> str:
    printer_name = _ensure_safe_arg_text(printer_name, "printer_name")
    # Elimina trabajos en cola (best-effort)
    return (
        f"Get-PrintJob -PrinterName '{printer_name}' -ErrorAction SilentlyContinue | "
        f"Remove-PrintJob -Confirm:$false -ErrorAction SilentlyContinue | Out-String"
    )


def safe_printer_command_restart_spooler() -> str:
    # Solo reinicio del servicio de cola
    return "Restart-Service -Name Spooler -Force; Get-Service Spooler | Format-List | Out-String"


def safe_printer_command_test_port(ip: str, port: int = 9100) -> str:
    ip = ensure_ipv4(ip)
    if port not in {9100, 515, 631}:
        raise ValueError("Puerto no permitido")
    return f"Test-NetConnection -ComputerName {ip} -Port {port} | Format-List | Out-String"


def safe_printer_command_add_shared(unc: str) -> str:
    unc = ensure_unc_printer(unc)
    return f"Add-Printer -ConnectionName '{unc}' | Out-String"


def safe_printer_command_set_default(printer_name: str) -> str:
    printer_name = _ensure_safe_arg_text(printer_name, "printer_name")
    return f"Set-Printer -Name '{printer_name}' -IsDefault $true | Out-String"


def safe_printer_command_remove(printer_name: str) -> str:
    printer_name = _ensure_safe_arg_text(printer_name, "printer_name")
    return f"Remove-Printer -Name '{printer_name}' -ErrorAction Stop | Out-String"


def safe_printer_command_list_drivers() -> str:
    return "Get-PrinterDriver | Select-Object Name | Sort-Object Name | Format-Table -AutoSize | Out-String"


def safe_printer_command_list_drivers_json() -> str:
    # Salida parseable para selección automática
    return "Get-PrinterDriver | Select-Object Name | ConvertTo-Json -Compress | Out-String"


def safe_driver_command_pnputil_add(inf_path: str) -> str:
    inf_path = _ensure_safe_arg_text(inf_path, "inf_path")
    if not inf_path.lower().endswith(".inf"):
        raise ValueError("inf_path debe terminar en .inf")
    # pnputil suele requerir admin según política del equipo/driver.
    return f"pnputil /add-driver '{inf_path}' /install | Out-String"


def safe_printer_command_add_ip(
    ip: str,
    printer_name: str,
    driver_name: str,
    port_number: int = 9100,
) -> str:
    ip = ensure_ipv4(ip)
    printer_name = _ensure_safe_arg_text(printer_name, "printer_name")
    driver_name = _ensure_safe_arg_text(driver_name, "driver_name")
    if port_number not in {9100, 515, 631}:
        raise ValueError("Puerto no permitido")

    port_name = f"IP_{ip}"

    # Crea puerto si no existe; luego intenta crear impresora si no existe.
    # Nota: Add-Printer requiere driver. Si el driver no está instalado, fallará con error legible.
    return (
        f"$ip='{ip}'; $portName='{port_name}'; $printerName='{printer_name}'; $driver='{driver_name}'; "
        f"if (-not (Get-PrinterPort -Name $portName -ErrorAction SilentlyContinue)) {{ "
        f"Add-PrinterPort -Name $portName -PrinterHostAddress $ip -PortNumber {port_number} -ErrorAction Stop | Out-String }}; "
        f"if (-not (Get-Printer -Name $printerName -ErrorAction SilentlyContinue)) {{ "
        f"Add-Printer -Name $printerName -PortName $portName -DriverName $driver -ErrorAction Stop | Out-String }}; "
        f"Get-Printer -Name $printerName -ErrorAction SilentlyContinue | "
        f"Select-Object Name,DriverName,PortName,PrinterStatus | Format-List | Out-String"
    )


def safe_printer_command_print_test_page(printer_name: str) -> str:
    printer_name = _ensure_safe_arg_text(printer_name, "printer_name")
    # PrintUIEntry imprime una página de prueba en la impresora indicada.
    # Nota: puede fallar si el nombre no existe o si la impresora está offline.
    return f"rundll32 printui.dll,PrintUIEntry /k /n \"{printer_name}\" | Out-String"
