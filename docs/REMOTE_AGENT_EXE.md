# Agente remoto como .EXE (sin Python en el cliente)

## Objetivo

Instalar opcionalmente un programa `.exe` en el PC cliente que:

- reciba órdenes desde el servidor (Streamlit),
- ejecute diagnóstico/red localmente (PowerShell),
- aplique cambios (IP) si se ejecuta como Administrador,
- **sin requerir Python instalado** en el cliente.

En este repo ya existe el agente HTTP en Python. Este documento explica cómo empaquetarlo como `.exe`.

## Cómo se construye el .exe

Se usa **PyInstaller** para empaquetar:

- Python runtime
- dependencias (`fastapi`, `uvicorn`, etc.)
- tu código del agente

El entrypoint está en: [ai_support/remote_agent/run_agent.py](ai_support/remote_agent/run_agent.py)

Para construir:

- `powershell -ExecutionPolicy Bypass -File .\scripts\build_remote_agent_exe.ps1`

Salida:

- `dist/AI-Support-RemoteAgent.exe`

## Cómo instalar en el PC cliente

1) Copia `AI-Support-RemoteAgent.exe` al PC cliente.

2) Define variables de entorno (por ejemplo como variables del sistema):

- `AI_SUPPORT_REMOTE_AGENT_TOKEN` (obligatoria)
- `AI_SUPPORT_REMOTE_AGENT_HOST` (opcional, default `0.0.0.0`)
- `AI_SUPPORT_REMOTE_AGENT_PORT` (opcional, default `8765`)

3) Ejecuta el EXE:

- Doble click (para diagnóstico)
- O "Ejecutar como administrador" (si necesitas aplicar cambios de red)

## Ejecutarlo como servicio (opciones)

- **NSSM** (simple): crea un servicio que ejecute el EXE.
- **sc.exe**: posible, pero NSSM suele ser más cómodo.

Importante: si el servicio corre como LocalSystem no siempre tendrá acceso de red/credenciales. En dominio suele ser mejor una cuenta gestionada (gMSA) o una cuenta de servicio.

## Seguridad recomendada

- Usa un token fuerte (`AI_SUPPORT_REMOTE_AGENT_TOKEN`).
- Restringe firewall del cliente: permitir el puerto solo desde el servidor.
- Si puedes, usa TLS (reverse proxy interno) o WinRM/Kerberos.
- Firma el `.exe` si vas a desplegarlo ampliamente.

## Nota sobre alternativas

Si no quieres instalar un EXE y tus PCs están en dominio, considera WinRM (PowerShell Remoting): [docs/REMOTE_WINRM.md](docs/REMOTE_WINRM.md)
