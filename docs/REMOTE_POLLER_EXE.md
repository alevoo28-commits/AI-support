# Cliente Polling como .EXE (sin Python en el PC)

## Objetivo

Instalar un `.exe` en cada PC cliente que:

- inicia comunicación **saliente** hacia el servidor (no requiere que el servidor llegue directo al PC),
- hace **polling** de trabajos (`jobs`) en la API del servidor,
- ejecuta localmente pruebas y cambios (PowerShell),
- reporta resultados al servidor.

Este modo usa la API: [ai_support/remote_control/server_api.py](ai_support/remote_control/server_api.py)

## Construcción del .exe

Entry point:
- [ai_support/remote_agent/run_poller.py](ai_support/remote_agent/run_poller.py)

Script de build (PyInstaller):
- [scripts/build_remote_poller_exe.ps1](scripts/build_remote_poller_exe.ps1)

Comando:
- `powershell -ExecutionPolicy Bypass -File .\scripts\build_remote_poller_exe.ps1`

Salida:
- `dist/AI-Support-RemotePoller.exe`

## Configuración en el PC cliente (variables de entorno)

Obligatorias:
- `AI_SUPPORT_REMOTE_CONTROL_URL` (ej: `http://SERVIDOR:8787`)
- `AI_SUPPORT_AGENT_TOKEN` (debe coincidir con el servidor)

Opcionales:
- `AI_SUPPORT_AGENT_ID` (default: hostname)
- `AI_SUPPORT_USER_KEY` (para mapear PC↔usuario si quieres)
- `AI_SUPPORT_AGENT_POLL_INTERVAL_S` (default: `5`)
- `AI_SUPPORT_AGENT_TIMEOUT_S` (default: `25`)

Opcionales (recomendadas si el PC puede quedar "sin IP" / sin gateway/dns al inicio):
- `AI_SUPPORT_NET_DEFAULT_PREFIX_LENGTH` (ej: `24`)
- `AI_SUPPORT_NET_DEFAULT_GATEWAY` (ej: `172.17.87.1`)
- `AI_SUPPORT_NET_DEFAULT_DNS` (ej: `8.8.8.8,8.8.4.4`)

Permisos:
- Si el poller debe **cambiar IP**, ejecutar como **Administrador**.

## Configuración en el servidor

Variables de entorno del servidor para la API de control remoto:
- `AI_SUPPORT_AGENT_TOKEN` (token de agentes)
- `AI_SUPPORT_ADMIN_TOKEN` (token para operaciones admin: crear jobs, listar agentes)

Opcional (para que todo sea automático al levantar Streamlit):
- `AI_SUPPORT_REMOTE_CONTROL_AUTOSTART=true` (inicia la API dentro del proceso Streamlit)
- `AI_SUPPORT_REMOTE_CONTROL_HOST` (default `0.0.0.0`)
- `AI_SUPPORT_REMOTE_CONTROL_PORT` (default `8787`)

Automatización desde la web:
- `AI_SUPPORT_REMOTE_CONTROL_URL` (URL de la API, ej `http://127.0.0.1:8787` si autostart)
- `AI_SUPPORT_REMOTE_CONTROL_AUTO=true` (default true) para que, ante consultas de red, se envíen jobs al PC cliente

Levantar API (ejemplo):
- `uvicorn ai_support.remote_control.server_api:app --host 0.0.0.0 --port 8787`

(En producción: poner detrás de reverse proxy/TLS y restringir firewall.)

## Tipos de jobs soportados por el poller

El cliente implementa estos `job_type`:

- `connectivity_check`
  - payload: `{ "target": "8.8.8.8" }` (opcional)
  - acción: detecta adaptador Up y prueba ping

- `diagnose_and_fix`
  - payload: `{ "target": "8.8.8.8", "allow_changes": true }`
  - acción:
    - si conectividad OK: reporta OK y **no cambia** IP
    - si conectividad falla y `allow_changes=true`: pide pool (`/agent/ip-pool`), elige IP libre (best-effort ping) y aplica IP estática

Notas:
- La elección de IP hace un check local de “en uso” (ping) antes de aplicar.
- Recomendado: el pool venga desde MySQL (ya lo expone `/agent/ip-pool`).

## Ejecutarlo como servicio (recomendado)

Opciones:
- **NSSM**: crear servicio que ejecute `AI-Support-RemotePoller.exe`.
- **Task Scheduler**: tarea “At startup” con “Run with highest privileges”.

Importante:
- Si corre como cuenta sin privilegios, no podrá aplicar cambios de red.
- Si corre como LocalSystem, puede tener restricciones de red/credenciales.

## Seguridad recomendada

- Token fuerte (rotar periódicamente).
- Restringir acceso a la API por IP/VLAN cuando sea posible.
- Preferir TLS (reverse proxy) y logs/alertas de cambios.

## Relación con el agente HTTP

El poller es distinto del agente HTTP (modo servidor → cliente). Si necesitas exponer endpoints en el PC cliente, ver:
- [docs/REMOTE_AGENT.md](docs/REMOTE_AGENT.md)
- [docs/REMOTE_AGENT_EXE.md](docs/REMOTE_AGENT_EXE.md)
