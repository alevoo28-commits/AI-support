# Diagnóstico/cambio de IP remoto con WinRM (sin Python en el cliente)

## Resumen

Si Streamlit corre en un **servidor** y el usuario accede por navegador, cualquier acción de PowerShell corre en el servidor.

Para cambiar la IP del **PC cliente** sin Python, puedes usar **WinRM (PowerShell Remoting)**: el servidor ejecuta `Invoke-Command` y el cliente aplica la configuración.

## Requisitos

- El servidor tiene conectividad hacia el PC cliente (misma LAN/VPN).
- El PC cliente permite WinRM (puertos 5985 HTTP o 5986 HTTPS).
- La cuenta que ejecuta Streamlit en el servidor tiene permisos en el PC cliente (ideal: dominio/AD).

## Habilitar WinRM en el PC cliente (rápido)

Ejecutar en el PC cliente **como Administrador**:

- `Enable-PSRemoting -Force`

Esto configura WinRM y crea reglas de firewall básicas.

## Hardening recomendado

### 1) Dominio (AD) + Kerberos (recomendado)

- Usa cuentas de dominio, Kerberos por defecto.
- Restringe firewall para que solo el servidor pueda conectarse:
  - Permitir entrada WinRM solo desde la IP del servidor.

### 2) Workgroup (evitar si es posible)

Requiere `TrustedHosts` o listener HTTPS con certificados.

- `Set-Item WSMan:\localhost\Client\TrustedHosts -Value "SERVIDOR" -Force`

### 3) Preferir HTTPS (5986) si no hay Kerberos

Configurar listener HTTPS implica certificado; depende del entorno.

## Integración en la app

En la UI (sidebar) → "🛰️ Ejecución remota (PC cliente)":

- Selecciona "Cliente (WinRM/PowerShell Remoting)"
- Ingresa "PC cliente (hostname o IP)"

Variables opcionales en el servidor:

- `AI_SUPPORT_WINRM_AUTH` (default: `Negotiate`)
- `AI_SUPPORT_WINRM_USE_SSL` (`true/false`)
- `AI_SUPPORT_WINRM_PORT` (ej: `5986` si usas SSL)

## Notas importantes

- Cambiar IP requiere privilegios admin en el PC cliente.
- Si Streamlit corre como un usuario sin privilegios remotos, `Invoke-Command` fallará.
- Para mayor seguridad, considera JEA (Just Enough Administration) para exponer solo comandos específicos.
