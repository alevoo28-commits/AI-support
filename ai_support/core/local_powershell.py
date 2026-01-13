from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from ai_support.core.config import excel_only_mode_enabled


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


def ensure_prefix_length(value: int) -> int:
    try:
        value_int = int(value)
    except Exception as e:
        raise ValueError("PrefixLength inválido") from e
    if value_int < 0 or value_int > 32:
        raise ValueError("PrefixLength inválido")
    return value_int


def run_powershell(command: str, timeout_s: int = 20) -> PowerShellResult:
    """Ejecuta PowerShell en modo seguro (sin perfil).

    Nota: este runner NO acepta comandos arbitrarios del modelo; solo debe ser usado
    desde funciones internas con parámetros validados.
    """

    if excel_only_mode_enabled():
        raise PermissionError(
            "PowerShell está deshabilitado por seguridad (modo Excel-only). "
            "Desactiva AI_SUPPORT_EXCEL_ONLY para habilitar herramientas locales."
        )

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


def safe_net_command_list_adapters_json() -> str:
    # Listado parseable de adaptadores (para selector en UI)
    return (
        "Get-NetAdapter | "
        "Select-Object Name,InterfaceDescription,Status,MacAddress,LinkSpeed | "
        "ConvertTo-Json -Compress | Out-String"
    )


def safe_net_command_get_ipv4_addresses_json(interface_alias: str) -> str:
    interface_alias = _ensure_safe_arg_text(interface_alias, "interface_alias")
    return (
        f"Get-NetIPAddress -InterfaceAlias '{interface_alias}' -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
        "Select-Object InterfaceAlias,IPAddress,PrefixLength,AddressState,Type | "
        "ConvertTo-Json -Compress | Out-String"
    )


def safe_net_command_get_ipconfiguration_json(interface_alias: str) -> str:
    interface_alias = _ensure_safe_arg_text(interface_alias, "interface_alias")
    # IPv4DefaultGateway puede venir como objeto; DNSServer como lista.
    return (
        f"Get-NetIPConfiguration -InterfaceAlias '{interface_alias}' -ErrorAction SilentlyContinue | "
        "Select-Object InterfaceAlias,IPv4DefaultGateway,DNSServer | "
        "ConvertTo-Json -Compress | Out-String"
    )


def safe_net_command_test_ip_in_use(ip: str) -> str:
    ip = ensure_ipv4(ip)
    # Test-NetConnection devuelve True/False con -InformationLevel Quiet
    return f"Test-NetConnection -ComputerName {ip} -InformationLevel Quiet | Out-String"


def safe_net_command_set_static_ipv4(
    *,
    interface_alias: str,
    ip: str,
    prefix_length: int,
    default_gateway: str | None,
    dns_servers: list[str] | None,
) -> str:
    interface_alias = _ensure_safe_arg_text(interface_alias, "interface_alias")
    ip = ensure_ipv4(ip)
    prefix_length = ensure_prefix_length(prefix_length)
    gw = ensure_ipv4(default_gateway) if default_gateway else ""

    dns_list: list[str] = []
    if dns_servers:
        for d in dns_servers:
            dns_list.append(ensure_ipv4(str(d)))

    # Nota: requiere permisos de administrador.
    # Estrategia:
    # - Remueve IPs IPv4 existentes en el alias, excepto la IP objetivo y APIPA (169.254.x.x)
    # - Agrega la IP estática con gateway si se especifica
    # - Configura DNS si se especifica
    dns_ps = "@()"
    if dns_list:
        quoted = ",".join([f"'{d}'" for d in dns_list])
        dns_ps = f"@({quoted})"

    # Evitar wildcard '*' (no permitido por el validador). Usamos StartsWith.
    return (
        f"$alias='{interface_alias}'; $ip='{ip}'; $prefix={prefix_length}; $gw='{gw}'; $dns={dns_ps}; "
        "Get-NetIPAddress -InterfaceAlias $alias -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
        "Where-Object { ($_.IPAddress -ne $ip) -and (-not ($_.IPAddress).StartsWith('169.254.')) } | "
        "Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue | Out-String; "
        "if ($gw) { New-NetIPAddress -InterfaceAlias $alias -IPAddress $ip -PrefixLength $prefix -DefaultGateway $gw -ErrorAction Stop | Out-String } "
        "else { New-NetIPAddress -InterfaceAlias $alias -IPAddress $ip -PrefixLength $prefix -ErrorAction Stop | Out-String }; "
        "if ($dns.Count -gt 0) { Set-DnsClientServerAddress -InterfaceAlias $alias -ServerAddresses $dns -ErrorAction Stop | Out-String }; "
        "Get-NetIPConfiguration -InterfaceAlias $alias | Select-Object InterfaceAlias,IPv4Address,IPv4DefaultGateway,DNSServer | ConvertTo-Json -Compress | Out-String"
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


# ============================================================================
# Comandos de red: adaptadores, conectividad, IP
# ============================================================================

def safe_net_command_test_connectivity(target: str = "8.8.8.8") -> str:
    """Prueba conectividad a un destino (IP o hostname).
    
    Args:
        target: IP o hostname a probar (default: 8.8.8.8 - Google DNS)
    
    Returns:
        Comando PowerShell que prueba la conectividad
    """
    target = _ensure_safe_arg_text(target, "target")
    return f"Test-Connection -ComputerName {target} -Count 2 -ErrorAction SilentlyContinue | ConvertTo-Json -Compress | Out-String"


def safe_net_command_get_adapter_ip(interface_alias: str) -> str:
    """Obtiene la configuración IP de un adaptador específico.
    
    Args:
        interface_alias: Nombre del adaptador (ej: "Ethernet")
    
    Returns:
        Comando PowerShell que retorna IP, Gateway, DNS en formato JSON
    """
    interface_alias = _ensure_safe_arg_text(interface_alias, "interface_alias")
    return (
        f"$adapter = Get-NetIPAddress -InterfaceAlias '{interface_alias}' -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -First 1; "
        f"$gateway = (Get-NetRoute -InterfaceAlias '{interface_alias}' -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue).NextHop; "
        f"$dns = (Get-DnsClientServerAddress -InterfaceAlias '{interface_alias}' -AddressFamily IPv4 -ErrorAction SilentlyContinue).ServerAddresses; "
        f"@{{IPAddress=$adapter.IPAddress; PrefixLength=$adapter.PrefixLength; Gateway=$gateway; DNS=$dns}} | ConvertTo-Json -Compress | Out-String"
    )


def safe_net_command_test_connectivity_on_interface(interface_alias: str, target: str = "8.8.8.8") -> str:
    """Prueba conectividad específicamente desde un adaptador.
    
    Args:
        interface_alias: Nombre del adaptador (ej: "Ethernet")
        target: IP o hostname a probar
    
    Returns:
        Comando PowerShell que prueba conectividad desde ese adaptador
    """
    interface_alias = _ensure_safe_arg_text(interface_alias, "interface_alias")
    target = _ensure_safe_arg_text(target, "target")
    # Get-NetIPAddress para obtener índice del adaptador, luego Test-NetConnection
    return (
        f"$ifIndex = (Get-NetAdapter -Name '{interface_alias}' -ErrorAction SilentlyContinue).ifIndex; "
        f"Test-NetConnection -ComputerName {target} -InformationLevel Detailed -ErrorAction SilentlyContinue | "
        f"Select-Object ComputerName,RemoteAddress,PingSucceeded,PingReplyDetails | ConvertTo-Json -Compress | Out-String"
    )
