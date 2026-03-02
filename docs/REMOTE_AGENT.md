# Agente remoto (PC cliente)

## Por qué es necesario

Si instalas Streamlit en un **servidor**, cualquier diagnóstico o cambio de red que hagas con PowerShell se ejecuta **en el servidor**, no en el PC del usuario que solo abre el navegador.

Para poder **cambiar/configurar la IP del PC del usuario**, necesitas ejecutar esas acciones **en el propio PC cliente**. Este repo incluye un *agente remoto* (un servicio HTTP) para ese propósito.

## Cómo funciona (arquitectura)

- **Servidor**: corre Streamlit (UI) y el orquestador.
- **Cliente**: corre el agente `ai_support.remote_agent.client_app`.
- El servidor llama al agente por HTTP para:
  - listar adaptadores,
  - probar conectividad,
  - aplicar IP estática.

## Seguridad (importante)

El agente expone un endpoint capaz de cambiar la red local. Protégelo:

- Define `AI_SUPPORT_REMOTE_AGENT_TOKEN` en el PC cliente.
- Expón el puerto solo al servidor (firewall/ACL), idealmente en una red interna.
- Ejecuta el agente con privilegios de Administrador **solo si** vas a aplicar cambios.

## Variables de entorno

En el **PC cliente** (agente):

- `AI_SUPPORT_REMOTE_AGENT_TOKEN`: token requerido para autorizar llamadas.

En el **servidor** (Streamlit):

- `AI_SUPPORT_REMOTE_AGENT_TOKEN`: mismo token (para llamar al agente).
- `AI_SUPPORT_REMOTE_AGENT_URL`: URL del agente (ej: `http://PC001:8765`).
  - Alternativa: `AI_SUPPORT_REMOTE_AGENT_URL_TEMPLATE` (ej: `http://{user_key}:8765`).

## Ejecutar el agente en el PC cliente

Instala dependencias y levanta el servicio:

- `pip install -r .\requirement.txt`
- `uvicorn ai_support.remote_agent.client_app:app --host 0.0.0.0 --port 8765`

Prueba de salud (desde el servidor):

- `GET http://PC001:8765/health` con header `X-AI-SUPPORT-TOKEN: <token>`

## Endpoints

- `GET /health`
- `GET /adapters`
- `GET /ip-config?interface_alias=Ethernet`
- `POST /connectivity/test` body: `{ "interface_alias": "Ethernet", "target": "8.8.8.8" }`
- `POST /ip/set-static` body:
  - `interface_alias`, `ip`, `prefix_length`, `default_gateway`, `dns_servers`, `dry_run`

## Limitaciones actuales

- En modo remoto, el flujo automático **puede aplicar una IP específica**, pero no elige IP del pool por sí mismo.
  - Recomendación: el servidor debe seleccionar/reservar una IP del pool corporativo y ordenarle al cliente aplicarla.
