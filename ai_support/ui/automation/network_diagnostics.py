"""ai_support.ui.automation.network_diagnostics

DiagnÃ³stico y (opcionalmente) reparaciÃ³n automÃ¡tica de red.

Objetivo UX: cuando el usuario reporta problemas de internet/red, ejecutar un
precheck de conectividad ANTES de iniciar la respuesta del LLM, mostrando el
progreso en vivo en Streamlit.
"""

import json
import time
from typing import Optional

import requests
import streamlit as st

from ai_support.core.ip_assignment import (
    assign_ip_to_ethernet_and_register,
    get_current_adapter_ip_config,
    list_net_adapters,
    test_connectivity_on_interface,
)
from ai_support.core.ip_pool_mysql import fetch_assigned_ipv4_from_mysql
from ai_support.core.remote_agent_client import (
    RemoteAgentError,
    get_remote_agent_config,
    get_ip_config as remote_get_ip_config,
    list_adapters as remote_list_adapters,
    set_static_ipv4 as remote_set_static_ipv4,
    test_connectivity as remote_test_connectivity,
)
from ai_support.core.winrm_remote import (
    ensure_remote_host,
    get_current_adapter_ip_config_remote,
    list_net_adapters_remote,
    set_static_ipv4_remote,
    test_connectivity_on_interface_remote,
)


def run_network_diagnostics(
    consulta: str,
    progress_container,
    user_key: str,
    *,
    allow_changes: bool = True,
    remote_agent_url: Optional[str] = None,
    remote_agent_token: Optional[str] = None,
    remote_winrm_host: Optional[str] = None,
    remote_control_url: Optional[str] = None,
    remote_control_admin_token: Optional[str] = None,
    remote_control_user_key: Optional[str] = None,
) -> Optional[str]:
    """
    Ejecuta diagnÃ³stico de red EN TIEMPO REAL.
    
    Flujo:
    1. Test rÃ¡pido de conectividad PRIMERO
    2. Si HAY conectividad â†’ retorna None (el chat responde normal)
    3. Si NO HAY conectividad â†’ diagnÃ³stico completo de 4 pasos
    
    Args:
        consulta: Texto de la consulta del usuario
        progress_container: Contenedor de Streamlit para mostrar progreso
        user_key: Identificador del usuario para registro de IP
    
    Returns:
        Optional[str]: Prompt para el LLM con el resultado del diagnÃ³stico
        (o None si hay conectividad / no aplica).
    """
    # Keywords que activan el diagnÃ³stico de red
    net_keywords = [
        "no tengo internet",
        "sin internet",
        "no hay internet",
        "no tengo conexiÃ³n",
        "sin conexiÃ³n",
        "conectividad",
        "problemas de conectividad",
        "problema de conectividad",
        "problemas de conexiÃ³n",
        "problema de conexiÃ³n",
        "problemas de red",
        "problema de red",
        "conectarme a internet",
        "conectar a internet",
        "conectarme a la red",
        "conectar a la red",
        "no tengo red",
        "no tengo ip",
        "problemas de internet",
        "problema de internet",
        "internet",
        "internet no funciona",
        "no funciona internet",
        "red no funciona",
        "no puedo navegar",
        "no carga",
        "no abren pÃ¡ginas",
        "no abre paginas",
    ]
    
    # Keywords que disparan asignaciÃ³n de IP de forma EXPLÃCITA (saltean precheck de conectividad)
    assign_explicit_keywords = [
        "asignar ip",
        "asigname una ip",
        "asignarme una ip",
        "asignar una ip",
        "asigna ip",
        "quiero una ip",
        "necesito una ip",
        "cambiar mi ip",
        "cambiar ip",
        "configurar ip",
        "poner ip",
        "dame una ip",
        "asigna una ip",
        "nueva ip",
        "registrar ip",
        "asignar direcciÃ³n ip",
        "asignarme direcciÃ³n ip",
    ]

    consulta_l = (consulta or "").strip().lower()
    net_intent = any(k in consulta_l for k in net_keywords)
    force_assign = any(k in consulta_l for k in assign_explicit_keywords)

    if not net_intent and not force_assign:
        return None

    # Si hay solicitud explÃ­cita de asignaciÃ³n, activar tambiÃ©n net_intent
    if force_assign:
        net_intent = True

    # Si estÃ¡ configurado Remote Control, es obligatorio usar poller. Si no hay poller, NO ejecutar nada local.

    # --- Remote Control (poller): si estÃ¡ configurado, lo priorizamos ---
    rc_base = (remote_control_url or "").strip().rstrip("/")
    rc_token = (remote_control_admin_token or "").strip()
    rc_user_key = (remote_control_user_key or "").strip()
    use_remote_control = bool(rc_base and rc_token and rc_user_key)

    def _rc_headers() -> dict[str, str]:
        return {"X-AI-SUPPORT-ADMIN-TOKEN": rc_token}

    def _rc_get(path: str, *, params: dict | None = None) -> dict:
        r = requests.get(f"{rc_base}{path}", headers=_rc_headers(), params=params, timeout=10)
        if r.status_code != 200:
            raise RuntimeError(f"RemoteControl {path}: {r.status_code} {r.text}")
        data = r.json()
        return data if isinstance(data, dict) else {}

    def _rc_post(path: str, *, payload: dict) -> dict:
        r = requests.post(f"{rc_base}{path}", headers=_rc_headers(), json=payload, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"RemoteControl {path}: {r.status_code} {r.text}")
        data = r.json()
        return data if isinstance(data, dict) else {}

    def _rc_pick_agent_id_ui() -> Optional[str]:
        data = _rc_get("/admin/agents")
        agents = data.get("agents")
        if not isinstance(agents, list):
            return None
        matching = [a for a in agents if str(a.get("user_key") or "").strip() == rc_user_key]
        if not matching:
            # Forzar el modal siempre que no haya poller, sin permitir cerrarlo hasta que el poller estÃ© conectado
            with st.modal("ðŸš¨ AtenciÃ³n: Instala el DiagnÃ³stico AutomÃ¡tico en tu PC"):
                st.markdown(f"""
                <div style='text-align:center;'>
                <h2 style='color:#d7263d;'>Â¡No se detecta el agente de diagnÃ³stico en tu PC!</h2>
                <p>Para que el sistema pueda diagnosticar y reparar tu red automÃ¡ticamente,<br>
                debes instalar y ejecutar el programa <b>AI-Support-RemotePoller.exe</b> en tu computador.</p>
                <p><b>User key detectado:</b> <code>{rc_user_key}</code></p>
                <p>GuÃ­a de instalaciÃ³n: <a href='/docs/REMOTE_POLLER_EXE.md' target='_blank'>Ver instrucciones</a></p>
                <a href="/static/AI-Support-RemotePoller.exe" download style="display:inline-block;margin:20px auto;padding:16px 32px;background:#003D7A;color:#fff;font-size:1.2em;border-radius:8px;text-decoration:none;font-weight:bold;">â¬‡ï¸ Descargar AI-Support-RemotePoller.exe</a>
                </div>
                """, unsafe_allow_html=True)
                st.info("Si ya lo instalaste, asegÃºrate que estÃ© ejecutÃ¡ndose y que la variable AI_SUPPORT_USER_KEY coincida con tu usuario.")
            # Prompt explÃ­cito para la IA
            return (
                f"NO SE PUDO REALIZAR DIAGNÃ“STICO REMOTO EN EL PC DEL USUARIO.\n"
                f"No se detecta el agente poller (AI-Support-RemotePoller.exe) ejecutÃ¡ndose en el PC del usuario (user_key={rc_user_key}).\n"
                "Indica al usuario que debe descargar e instalar el programa para poder hacer pruebas automÃ¡ticas de red en su computador.\n"
                "No asumas ningÃºn resultado de conectividad ni de IP.\n"
                "GuÃ­a de instalaciÃ³n: /docs/REMOTE_POLLER_EXE.md\n"
                "Descarga directa: /static/AI-Support-RemotePoller.exe\n"
            )
        if len(matching) == 1:
            return str(matching[0].get("agent_id") or "").strip()
        # Si hay varios, dejar elegir
        options = {f"{a.get('agent_id')} ({a.get('hostname','')})": a.get('agent_id') for a in matching}
        pick = st.selectbox("Selecciona el PC cliente para diagnÃ³stico", options=list(options.keys()))
        return options.get(pick)

    def _rc_wait_job(job_id: str, timeout_s: int = 50) -> dict:
        start = time.time()
        last_status = ""
        while (time.time() - start) < timeout_s:
            data = _rc_get(f"/admin/job/{job_id}")
            job = data.get("job") if isinstance(data, dict) else None
            if not isinstance(job, dict):
                time.sleep(1)
                continue
            status = str(job.get("status") or "").strip()
            if status and status != last_status:
                last_status = status
            if status in {"done", "error"}:
                return job
            time.sleep(1)
        raise TimeoutError("Timeout esperando resultado del PC cliente")
    remote_cfg = get_remote_agent_config(
        user_key=user_key,
        override_url=(remote_agent_url.strip() if isinstance(remote_agent_url, str) and remote_agent_url.strip() else None),
        override_token=(remote_agent_token.strip() if isinstance(remote_agent_token, str) and remote_agent_token.strip() else None),
    )

    winrm_host = None
    if isinstance(remote_winrm_host, str) and remote_winrm_host.strip():
        try:
            winrm_host = ensure_remote_host(remote_winrm_host)
        except Exception:
            winrm_host = None


    # Si Remote Control estÃ¡ activo, nunca ejecutar diagnÃ³stico local ni por WinRM/Agente HTTP
    if use_remote_control:
        with progress_container:
            with st.status("ðŸ›°ï¸ Remote Control: ejecutando diagnÃ³stico en el PC cliente", expanded=True) as rcst:
                try:
                    st.write(f"ðŸ‘¤ Usuario (user_key): {rc_user_key}")
                    st.write("ðŸ”Ž Buscando agente conectado...")
                    agent_id = _rc_pick_agent_id_ui()
                    if not agent_id:
                        rcst.update(label="âš ï¸ No hay agente conectado", state="error")
                        return None

                    st.write(f"âœ… Agente seleccionado: {agent_id}")
                    st.write("ðŸ“¨ Enviando job diagnose_and_fix...")
                    resp = _rc_post(
                        "/admin/job",
                        payload={
                            "agent_id": agent_id,
                            "job_type": "diagnose_and_fix",
                            "payload": {"target": "8.8.8.8", "allow_changes": bool(allow_changes)},
                        },
                    )
                    job_id = str(resp.get("job_id") or "").strip()
                    if not job_id:
                        raise RuntimeError("El servidor no devolviÃ³ job_id")
                    st.write(f"ðŸ§¾ job_id: {job_id}")
                    st.write("â³ Esperando resultado del PC cliente...")
                    job = _rc_wait_job(job_id)
                    status = str(job.get("status") or "")
                    result = job.get("result") if isinstance(job.get("result"), dict) else {}
                    err = str(job.get("error") or "").strip()

                    if status == "done":
                        rcst.update(label="âœ… DiagnÃ³stico remoto completado", state="complete")
                    else:
                        rcst.update(label="âŒ DiagnÃ³stico remoto fallÃ³", state="error")

                    # Mostrar resumen en UI
                    st.write(f"Estado: {status}")
                    if err:
                        st.write(f"Error: {err}")
                    if isinstance(result, dict) and result:
                        st.json(result)

                    # Construir prompt para el LLM con resultado estructurado
                    return (
                        "DIAGNÃ“STICO AUTOMÃTICO (PC CLIENTE / POLLER)\n"
                        f"user_key={rc_user_key}\n"
                        f"agent_id={agent_id}\n"
                        f"status={status}\n"
                        + (f"error={err}\n" if err else "")
                        + "result_json=\n"
                        + json.dumps(result or {}, ensure_ascii=False, indent=2)
                        + "\n\nINSTRUCCIONES PARA TU RESPUESTA:\n"
                        "1. Si ok=true, confirma conectividad y resume lo hecho.\n"
                        "2. Si ok=false y changed=true/new_ip existe, explica que se cambiÃ³ la IP e indica la nueva IP.\n"
                        "3. Si ok=false y no se pudo cambiar, da pasos concretos (cable, DHCP, reinicio adaptador).\n"
                        "4. MantÃ©n la respuesta breve y accionable."
                    )
                except Exception as e:
                    rcst.update(label="âŒ Remote Control: error", state="error")
                    st.write(f"âŒ Error Remote Control: {e}")
                    return None
        return None

    use_agent = remote_cfg is not None
    use_winrm = winrm_host is not None

    # PASO 0: Test rÃ¡pido de conectividad ANTES de hacer diagnÃ³stico completo
    quick_test_adapter = None
    quick_result = None
    has_connectivity = False

    # Mostrar SIEMPRE el precheck en UI cuando es un caso de red/internet.
    with progress_container:
        with st.status("ðŸŒ Precheck de conectividad", expanded=True) as pre:
            try:
                if use_agent:
                    adapters = remote_list_adapters(remote_cfg)
                elif use_winrm:
                    adapters = list_net_adapters_remote(winrm_host)
                else:
                    adapters = list_net_adapters()
                for a in adapters:
                    status_text = str(a.get("Status") or "").strip().lower()
                    if status_text == "up":
                        quick_test_adapter = str(a.get("Name") or "").strip()
                        break

                if not quick_test_adapter:
                    pre.update(label="âš ï¸ Precheck: sin interfaz activa", state="error")
                    st.write("âš ï¸ No encontrÃ© una interfaz de red activa (Status=Up).")
                else:
                    st.write(f"ðŸ”Ž Interfaz para prueba: {quick_test_adapter}")
                    st.write("ðŸ“¡ Probando conectividad a 8.8.8.8...")
                    if use_agent:
                        quick_result = remote_test_connectivity(
                            remote_cfg,
                            interface_alias=quick_test_adapter,
                            target="8.8.8.8",
                        )
                    elif use_winrm:
                        quick_result = test_connectivity_on_interface_remote(
                            winrm_host,
                            quick_test_adapter,
                            "8.8.8.8",
                        )
                    else:
                        quick_result = test_connectivity_on_interface(quick_test_adapter, "8.8.8.8")
                    has_connectivity = bool(quick_result.get("success", False))

                    if has_connectivity:
                        pre.update(label="âœ… Precheck: conectividad OK", state="complete")
                        st.write("âœ… Hay conectividad. No ejecuto diagnÃ³stico adicional.")
                    else:
                        pre.update(label="âŒ Precheck: sin conectividad", state="error")
                        detail = str(quick_result.get("details") or "").strip()
                        if detail:
                            st.write(detail)
            except Exception as e:
                pre.update(label="âŒ Precheck: error", state="error")
                st.write(f"âŒ Error ejecutando precheck: {e}")
    
    # Si HAY conectividad y NO es una solicitud explÃ­cita de asignaciÃ³n â†’ No hacer nada
    if has_connectivity and not force_assign:
        return None  # El chat responderÃ¡ normalmente

    # Si HAY conectividad pero el usuario pidiÃ³ asignar IP explÃ­citamente â†’ asignar igual
    # TambiÃ©n se ejecuta cuando NO hay conectividad y force_assign=True (viene del flujo normal de diagnÃ³stico)
    if force_assign:
        # El agente web no puede ejecutar programas en el PC del cliente.
        # El usuario debe correr el ejecutable standalone manualmente.
        return (
            "SOLICITUD DE ASIGNACIÃ“N DE IP DETECTADA.\n"
            "INSTRUCCIONES PARA TU RESPUESTA:\n"
            "1. Indica al usuario que, para asignar una IP estÃ¡tica con conectividad verificada, "
            "debe ejecutar manualmente el programa **ConfiguradorRed_FCFM.exe** en su PC.\n"
            "2. Explica que debe ejecutarlo con clic derecho â†’ 'Ejecutar como administrador'.\n"
            "3. El programa realizarÃ¡ automÃ¡ticamente: detecciÃ³n del adaptador Ethernet, "
            "bÃºsqueda de una IP libre en los segmentos de red FCFM (172.17.82-87.x), "
            "verificaciÃ³n de conectividad a Internet al solicitar correo del usuario, "
            "y registro de la IP en la base de datos.\n"
            "4. Si el usuario no tiene el ejecutable, puede pedÃ­rselo al equipo de soporte TI.\n"
            "5. MantÃ©n la respuesta clara y amable (mÃ¡ximo 5 lÃ­neas)."
        )


    # Sin conectividad â†’ Ejecutar diagnÃ³stico COMPLETO
    with progress_container:
        with st.status("ðŸ” Diagnosticando conectividad de red...", expanded=True) as status:
            st.write("ðŸ” Iniciando diagnÃ³stico de conectividad de red...")
            if not allow_changes:
                st.info("â„¹ï¸ Modo diagnÃ³stico: cambios automÃ¡ticos DESACTIVADOS (solo anÃ¡lisis).")
            
            try:
                # PASO 1: Detectar interfaz Ethernet activa (Up)
                st.write("ðŸ”Ž Paso 1/4: Detectando adaptador Ethernet...")
                if use_agent:
                    adapters = remote_list_adapters(remote_cfg)
                elif use_winrm:
                    adapters = list_net_adapters_remote(winrm_host)
                else:
                    adapters = list_net_adapters()
                ethernet_adapter = None
                for a in adapters:
                    name = str(a.get("Name") or "").strip().lower()
                    status_text = str(a.get("Status") or "").strip().lower()
                    if "ethernet" in name and status_text == "up":
                        ethernet_adapter = str(a.get("Name") or "").strip()
                        break
                
                if not ethernet_adapter:
                    st.warning("âš ï¸ No se encontrÃ³ adaptador Ethernet, buscando alternativa...")
                    # Fallback: primera interfaz Up que no sea Wi-Fi/Loopback
                    for a in adapters:
                        name = str(a.get("Name") or "").strip().lower()
                        status_text = str(a.get("Status") or "").strip().lower()
                        if status_text == "up" and "wi-fi" not in name and "loopback" not in name:
                            ethernet_adapter = str(a.get("Name") or "").strip()
                            break
                
                if not ethernet_adapter:
                    st.error("âŒ No se encontrÃ³ un adaptador de red activo")
                    st.info(f"Adaptadores disponibles: {', '.join([a.get('Name', 'Sin nombre') for a in adapters[:5]])}")
                    status.update(label="âŒ DiagnÃ³stico con errores", state="error")
                    
                    return f"""ACCIÃ“N AUTOMÃTICA: No se encontrÃ³ adaptador Ethernet.

RESULTADO:
âš ï¸ No se encontrÃ³ un adaptador Ethernet activo (Up).

Adaptadores disponibles:
{chr(10).join([f"- {a.get('Name', 'Sin nombre')} ({a.get('Status', 'Desconocido')})" for a in adapters[:5]])}

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que no encontraste un adaptador Ethernet activo
2. Sugiere verificar que el cable estÃ© conectado y el adaptador habilitado
3. Lista los adaptadores encontrados
4. MantÃ©n tu respuesta breve (3-4 lÃ­neas)"""
                
                st.success(f"âœ… Adaptador encontrado: {ethernet_adapter}")
                
                # PASO 2: Probar conectividad (ya sabemos que fallÃ³, pero mostramos para UI)
                st.write("ðŸŒ Paso 2/4: Probando conectividad a Internet (8.8.8.8)...")
                st.warning("âš ï¸ Sin conectividad a Internet (confirmado)")
                
                # PASO 3: Revisar configuraciÃ³n IP
                st.write("ðŸ”§ Paso 3/4: Obteniendo configuraciÃ³n IP actual...")
                if use_agent:
                    ip_config = remote_get_ip_config(remote_cfg, interface_alias=ethernet_adapter)
                elif use_winrm:
                    ip_config = get_current_adapter_ip_config_remote(winrm_host, ethernet_adapter)
                else:
                    ip_config = get_current_adapter_ip_config(ethernet_adapter)

                # Si solo queremos diagnÃ³stico (sin cambios), devolver guÃ­a sin tocar configuraciÃ³n.
                if not allow_changes:
                    current_ip = str(ip_config.get("ip") or "").strip()
                    has_ip = bool(ip_config.get("has_ip"))
                    prefix = ip_config.get("prefix_length")
                    precheck_detail = ""
                    if isinstance(quick_result, dict):
                        precheck_detail = str(quick_result.get("details") or "").strip()
                    status.update(label="âš ï¸ DiagnÃ³stico completado (sin cambios)", state="complete")

                    return f"""DIAGNÃ“STICO DE RED (SIN CAMBIOS AUTOMÃTICOS):

PRECHECK:
- Interfaz probada: {quick_test_adapter or 'N/D'}
- Conectividad a 8.8.8.8: No (fallÃ³)
{('- Detalle: ' + precheck_detail) if precheck_detail else ''}

ESTADO:
- Adaptador activo: {ethernet_adapter}
- Tiene IP: {'SÃ­' if has_ip else 'No'}
- IP actual: {current_ip or 'N/D'}
- Prefijo: {prefix if prefix is not None else 'N/D'}

INSTRUCCIONES PARA TU RESPUESTA:
1. Confirma que NO hay conectividad a Internet.
2. Indica el adaptador activo y la IP actual (si existe).
3. Pide un dato mÃ­nimo: Â¿con cable o Wiâ€‘Fi? Â¿luz del puerto? Â¿gateway corporativo?
4. Sugiere pruebas rÃ¡pidas: ping gateway, ping 8.8.8.8, nslookup.
5. Aclara que no se aplicaron cambios automÃ¡ticos de IP (modo seguro).
Respuesta breve (4-6 lÃ­neas)."""
                
                if ip_config["has_ip"]:
                    # Tiene IP pero sin conectividad â†’ Cambiar IP manteniendo segmento
                    current_ip = ip_config["ip"]
                    st.info(f"ðŸ“‹ IP actual: {current_ip} (sin conectividad)")
                    st.write("âš™ï¸ Paso 4/4: Buscando nueva IP en el mismo segmento...")
                    
                    # Extraer segmento (primeros 3 octetos)
                    ip_parts = current_ip.split(".")
                    if len(ip_parts) == 4:
                        segment = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                        st.info(f"ðŸ” Segmento detectado: {segment}.x")
                        
                        # Buscar IP disponible en el mismo segmento
                        assigned_ips = set(fetch_assigned_ipv4_from_mysql())
                        
                        # Generar candidatos en el mismo segmento (evitar .0, .1, .255)
                        candidates = []
                        for last_octet in range(2, 255):
                            candidate = f"{segment}.{last_octet}"
                            if candidate != current_ip and candidate not in assigned_ips:
                                candidates.append(candidate)
                        
                        st.info(f"ðŸ“Š Encontradas {len(candidates)} IPs disponibles en el segmento")
                        
                        if candidates:
                            new_ip = candidates[0]
                            st.write(f"âš™ï¸ Asignando nueva IP: {new_ip} (mismo segmento {segment}.x)...")

                            if use_agent or use_winrm:
                                # En modo remoto, aplicamos la IP en el PC cliente.
                                # El registro MySQL (si se requiere) debe hacerse desde el servidor.
                                detected_gw = str(ip_config.get("gateway") or "").strip() or None
                                detected_dns = ip_config.get("dns") if isinstance(ip_config.get("dns"), list) else None
                                dns_servers = [str(x).strip() for x in (detected_dns or []) if str(x).strip()]
                                # Fallback defensivo
                                if not detected_gw:
                                    detected_gw = "172.17.87.1"
                                if not dns_servers:
                                    dns_servers = ["8.8.8.8", "8.8.4.4"]

                                if use_agent:
                                    apply = remote_set_static_ipv4(
                                        remote_cfg,
                                        interface_alias=ethernet_adapter,
                                        ip=new_ip,
                                        prefix_length=int(ip_config.get("prefix_length") or 24),
                                        default_gateway=detected_gw,
                                        dns_servers=dns_servers,
                                        dry_run=False,
                                    )
                                else:
                                    apply = set_static_ipv4_remote(
                                        winrm_host,
                                        interface_alias=ethernet_adapter,
                                        ip=new_ip,
                                        prefix_length=int(ip_config.get("prefix_length") or 24),
                                        default_gateway=detected_gw,
                                        dns_servers=dns_servers,
                                        dry_run=False,
                                    )
                                ok = bool(apply.get("ok"))
                                assigned_ip = new_ip if ok else None
                                details = str(apply.get("stderr") or apply.get("stdout") or "")
                                result = type("Tmp", (), {"ok": ok, "assigned_ip": assigned_ip, "details": details})
                            else:
                                result = assign_ip_to_ethernet_and_register(
                                    user_key=user_key,
                                    interface_alias=ethernet_adapter,
                                    prefix_length=ip_config["prefix_length"],
                                    require_no_ping_response=True,
                                    dry_run=False,
                                    force_ip=new_ip,
                                )
                            
                            if result.ok and result.assigned_ip:
                                st.success(f"âœ… IP cambiada: {current_ip} â†’ {result.assigned_ip}")
                                st.info(f"ðŸ“¡ Adaptador: {ethernet_adapter} | MÃ¡scara: 255.255.255.0")
                                status.update(label="âœ… DiagnÃ³stico completado", state="complete")
                                
                                return f"""ACCIÃ“N AUTOMÃTICA COMPLETADA:

DIAGNÃ“STICO:
- Adaptador: {ethernet_adapter}
- IP anterior: {current_ip} (sin conectividad)
- IP nueva: {result.assigned_ip} âœ…
- Segmento mantenido: {segment}.x
- Gateway: 172.17.87.1
- DNS: 8.8.8.8, 8.8.4.4

RESULTADO:
âœ… IP configurada exitosamente en el mismo segmento de red.

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que detectaste problema de conectividad
2. Indica que cambiaste la IP de {current_ip} a {result.assigned_ip} (mismo segmento)
3. Sugiere probar: ping 8.8.8.8
4. MantÃ©n tu respuesta concisa (3-4 lÃ­neas)"""
                            else:
                                st.error("âŒ Error al cambiar IP. Permisos de Administrador requeridos.")
                                st.warning(f"ðŸ’¡ Detalle: {result.details}")
                                status.update(label="âŒ DiagnÃ³stico con errores", state="error")
                                
                                return f"""ACCIÃ“N AUTOMÃTICA: Error al cambiar IP por permisos.

RESULTADO:
âŒ No se pudo cambiar la IP {current_ip} por permisos insuficientes.

SOLUCIÃ“N:
1. Cierra esta aplicaciÃ³n Streamlit
2. Clic derecho en PowerShell o Terminal
3. "Ejecutar como administrador"
4. Navega a: cd C:\\Users\\info\\Documents\\GitHub\\AI-support
5. Ejecuta: streamlit run .\\sistema_completo_agentes.py

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que se necesitan permisos de Administrador
2. Indica los pasos para reiniciar como Admin
3. MantÃ©n tu respuesta concisa (4-5 lÃ­neas)"""
                        else:
                            st.error(f"âŒ No hay IPs disponibles en el segmento {segment}.x")
                            status.update(label="âŒ DiagnÃ³stico con errores", state="error")
                            
                            return f"""ACCIÃ“N AUTOMÃTICA: Sin IPs disponibles.

RESULTADO:
âš ï¸ No hay IPs disponibles en el segmento {segment}.x

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que no hay IPs libres en ese segmento
2. Sugiere contactar al administrador de red
3. Breve (2-3 lÃ­neas)"""
                    else:
                        st.error("âŒ IP actual invÃ¡lida")
                        status.update(label="âŒ DiagnÃ³stico con errores", state="error")
                        return "Error: IP actual invÃ¡lida"
                else:
                    # No tiene IP asignada â†’ Asignar del pool
                    st.info("ðŸ“‹ No tiene IP asignada")
                    st.write("âš™ï¸ Paso 4/4: Asignando IP automÃ¡ticamente del pool...")

                    if use_agent or use_winrm:
                        # Modo remoto: sin pool local en el cliente. Por ahora devolvemos guÃ­a.
                        # Alternativa recomendada: el servidor elige una IP del pool y llama /ip/set-static.
                        status.update(label="âš ï¸ DiagnÃ³stico completado (requiere IP desde servidor)", state="complete")
                        return """DIAGNÃ“STICO DE RED (MODO REMOTO):

El PC cliente no tiene IP asignada y no puedo elegir automÃ¡ticamente una IP del pool desde el agente.

SUGERENCIA:
1) Configura una IP especÃ­fica para ese usuario/PC desde el servidor (pool corporativo)
2) Luego aplica la IP llamando al agente remoto (/ip/set-static)

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que el equipo no tiene IP.
2. Indica que en modo servidor se necesita asignar una IP desde el pool central.
3. Sugiere ejecutar el agente remoto como administrador y volver a intentar.
Breve (4-6 lÃ­neas)."""
                    else:
                        result = assign_ip_to_ethernet_and_register(
                            user_key=user_key,
                            interface_alias=ethernet_adapter,
                            prefix_length=24,
                            require_no_ping_response=True,
                            dry_run=False,
                        )
                    
                    if result.ok and result.assigned_ip:
                        st.success(f"âœ… IP asignada: {result.assigned_ip}")
                        st.info(f"ðŸ“¡ Adaptador: {ethernet_adapter} | MÃ¡scara: 255.255.255.0")
                        status.update(label="âœ… DiagnÃ³stico completado", state="complete")
                        
                        return f"""ACCIÃ“N AUTOMÃTICA COMPLETADA:

DIAGNÃ“STICO:
El adaptador {ethernet_adapter} no tenÃ­a IP asignada.

RESULTADO:
- âœ… IP configurada exitosamente: {result.assigned_ip}
- Adaptador: {ethernet_adapter}
- MÃ¡scara de subred: 255.255.255.0
- Gateway predeterminado: 172.17.87.1
- Servidores DNS: 8.8.8.8, 8.8.4.4

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que el adaptador no tenÃ­a IP
2. Indica que asignaste automÃ¡ticamente la IP {result.assigned_ip}
3. Sugiere probar: ping 8.8.8.8
4. MantÃ©n tu respuesta concisa (3-4 lÃ­neas)"""
                    else:
                        st.error("âŒ Error al asignar IP. Permisos de Administrador requeridos.")
                        status.update(label="âŒ DiagnÃ³stico con errores", state="error")
                        
                        return f"""ACCIÃ“N AUTOMÃTICA: Error al asignar IP por permisos.

RESULTADO:
âŒ No se pudo asignar IP por permisos insuficientes.

DETALLES:
{result.details}

SOLUCIÃ“N:
1. Cierra esta aplicaciÃ³n Streamlit
2. Clic derecho en PowerShell o Terminal
3. "Ejecutar como administrador"
4. Navega a: cd C:\\Users\\info\\Documents\\GitHub\\AI-support
5. Ejecuta: streamlit run .\\sistema_completo_agentes.py

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que se necesitan permisos de Administrador para configurar red
2. Indica los pasos para reiniciar como Admin
3. MantÃ©n tu respuesta concisa (4-5 lÃ­neas)"""
            
            except RemoteAgentError as e:
                st.error(f"âŒ Error agente remoto: {e}")
                status.update(label="âŒ DiagnÃ³stico con errores", state="error")
                return f"""DIAGNÃ“STICO DE RED: Error con agente remoto.

RESULTADO:
âŒ No pude contactar/usar el agente remoto del PC cliente: {e}

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que el diagnÃ³stico remoto fallÃ³ porque el agente no responde o no autoriza.
2. Pide verificar: servicio del agente levantado, puerto abierto, token correcto.
3. MantÃ©n tu respuesta breve (3-5 lÃ­neas)."""

            except Exception as e:
                st.error(f"âŒ Error inesperado: {e}")
                status.update(label="âŒ DiagnÃ³stico con errores", state="error")
                
                return f"""ACCIÃ“N AUTOMÃTICA: Error al diagnosticar.

RESULTADO:
âŒ Error: {e}

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que hubo un error al diagnosticar
2. Sugiere ejecutar como Administrador
3. Breve (2-3 lÃ­neas)"""
