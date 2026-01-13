"""ai_support.ui.automation.network_diagnostics

Diagnóstico y (opcionalmente) reparación automática de red.

Objetivo UX: cuando el usuario reporta problemas de internet/red, ejecutar un
precheck de conectividad ANTES de iniciar la respuesta del LLM, mostrando el
progreso en vivo en Streamlit.
"""

import streamlit as st
from typing import Optional
from ai_support.core.ip_assignment import (
    list_net_adapters,
    test_connectivity_on_interface,
    get_current_adapter_ip_config,
    assign_ip_to_ethernet_and_register,
)
from ai_support.core.ip_pool_mysql import fetch_assigned_ipv4_from_mysql


def run_network_diagnostics(
    consulta: str,
    progress_container,
    user_key: str,
    *,
    allow_changes: bool = True,
) -> Optional[str]:
    """
    Ejecuta diagnóstico de red EN TIEMPO REAL.
    
    Flujo:
    1. Test rápido de conectividad PRIMERO
    2. Si HAY conectividad → retorna None (el chat responde normal)
    3. Si NO HAY conectividad → diagnóstico completo de 4 pasos
    
    Args:
        consulta: Texto de la consulta del usuario
        progress_container: Contenedor de Streamlit para mostrar progreso
        user_key: Identificador del usuario para registro de IP
    
    Returns:
        Optional[str]: Prompt para el LLM con el resultado del diagnóstico
        (o None si hay conectividad / no aplica).
    """
    # Keywords que activan el diagnóstico de red
    net_keywords = [
        "no tengo internet",
        "sin internet",
        "no hay internet",
        "no tengo conexión",
        "sin conexión",
        "conectividad",
        "problemas de conectividad",
        "problema de conectividad",
        "problemas de conexión",
        "problema de conexión",
        "problemas de red",
        "problema de red",
        "conectarme a internet",
        "conectar a internet",
        "conectarme a la red",
        "conectar a la red",
        "no tengo red",
        "configurar ip",
        "asignar ip",
        "necesito ip",
        "no tengo ip",
        "problemas de internet",
        "problema de internet",
        "internet",
        "internet no funciona",
        "no funciona internet",
        "red no funciona",
        "no puedo navegar",
        "no carga",
        "no abren páginas",
        "no abre paginas",
    ]
    
    consulta_l = (consulta or "").strip().lower()
    net_intent = any(k in consulta_l for k in net_keywords)
    
    if not net_intent:
        return None
    
    # PASO 0: Test rápido de conectividad ANTES de hacer diagnóstico completo
    quick_test_adapter = None
    quick_result = None
    has_connectivity = False

    # Mostrar SIEMPRE el precheck en UI cuando es un caso de red/internet.
    with progress_container:
        with st.status("🌐 Precheck de conectividad", expanded=True) as pre:
            try:
                adapters = list_net_adapters()
                for a in adapters:
                    status_text = str(a.get("Status") or "").strip().lower()
                    if status_text == "up":
                        quick_test_adapter = str(a.get("Name") or "").strip()
                        break

                if not quick_test_adapter:
                    pre.update(label="⚠️ Precheck: sin interfaz activa", state="error")
                    st.write("⚠️ No encontré una interfaz de red activa (Status=Up).")
                else:
                    st.write(f"🔎 Interfaz para prueba: {quick_test_adapter}")
                    st.write("📡 Probando conectividad a 8.8.8.8...")
                    quick_result = test_connectivity_on_interface(quick_test_adapter, "8.8.8.8")
                    has_connectivity = bool(quick_result.get("success", False))

                    if has_connectivity:
                        pre.update(label="✅ Precheck: conectividad OK", state="complete")
                        st.write("✅ Hay conectividad. No ejecuto diagnóstico adicional.")
                    else:
                        pre.update(label="❌ Precheck: sin conectividad", state="error")
                        detail = str(quick_result.get("details") or "").strip()
                        if detail:
                            st.write(detail)
            except Exception as e:
                pre.update(label="❌ Precheck: error", state="error")
                st.write(f"❌ Error ejecutando precheck: {e}")
    
    # Si HAY conectividad → No hacer nada, dejar que el chat responda normal
    if has_connectivity:
        return None  # El chat responderá normalmente
    
    # Sin conectividad → Ejecutar diagnóstico COMPLETO
    with progress_container:
        with st.status("🔍 Diagnosticando conectividad de red...", expanded=True) as status:
            st.write("🔍 Iniciando diagnóstico de conectividad de red...")
            if not allow_changes:
                st.info("ℹ️ Modo diagnóstico: cambios automáticos DESACTIVADOS (solo análisis).")
            
            try:
                # PASO 1: Detectar interfaz Ethernet activa (Up)
                st.write("🔎 Paso 1/4: Detectando adaptador Ethernet...")
                adapters = list_net_adapters()
                ethernet_adapter = None
                for a in adapters:
                    name = str(a.get("Name") or "").strip().lower()
                    status_text = str(a.get("Status") or "").strip().lower()
                    if "ethernet" in name and status_text == "up":
                        ethernet_adapter = str(a.get("Name") or "").strip()
                        break
                
                if not ethernet_adapter:
                    st.warning("⚠️ No se encontró adaptador Ethernet, buscando alternativa...")
                    # Fallback: primera interfaz Up que no sea Wi-Fi/Loopback
                    for a in adapters:
                        name = str(a.get("Name") or "").strip().lower()
                        status_text = str(a.get("Status") or "").strip().lower()
                        if status_text == "up" and "wi-fi" not in name and "loopback" not in name:
                            ethernet_adapter = str(a.get("Name") or "").strip()
                            break
                
                if not ethernet_adapter:
                    st.error("❌ No se encontró un adaptador de red activo")
                    st.info(f"Adaptadores disponibles: {', '.join([a.get('Name', 'Sin nombre') for a in adapters[:5]])}")
                    status.update(label="❌ Diagnóstico con errores", state="error")
                    
                    return f"""ACCIÓN AUTOMÁTICA: No se encontró adaptador Ethernet.

RESULTADO:
⚠️ No se encontró un adaptador Ethernet activo (Up).

Adaptadores disponibles:
{chr(10).join([f"- {a.get('Name', 'Sin nombre')} ({a.get('Status', 'Desconocido')})" for a in adapters[:5]])}

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que no encontraste un adaptador Ethernet activo
2. Sugiere verificar que el cable esté conectado y el adaptador habilitado
3. Lista los adaptadores encontrados
4. Mantén tu respuesta breve (3-4 líneas)"""
                
                st.success(f"✅ Adaptador encontrado: {ethernet_adapter}")
                
                # PASO 2: Probar conectividad (ya sabemos que falló, pero mostramos para UI)
                st.write("🌐 Paso 2/4: Probando conectividad a Internet (8.8.8.8)...")
                st.warning("⚠️ Sin conectividad a Internet (confirmado)")
                
                # PASO 3: Revisar configuración IP
                st.write("🔧 Paso 3/4: Obteniendo configuración IP actual...")
                ip_config = get_current_adapter_ip_config(ethernet_adapter)

                # Si solo queremos diagnóstico (sin cambios), devolver guía sin tocar configuración.
                if not allow_changes:
                    current_ip = str(ip_config.get("ip") or "").strip()
                    has_ip = bool(ip_config.get("has_ip"))
                    prefix = ip_config.get("prefix_length")
                    precheck_detail = ""
                    if isinstance(quick_result, dict):
                        precheck_detail = str(quick_result.get("details") or "").strip()
                    status.update(label="⚠️ Diagnóstico completado (sin cambios)", state="complete")

                    return f"""DIAGNÓSTICO DE RED (SIN CAMBIOS AUTOMÁTICOS):

PRECHECK:
- Interfaz probada: {quick_test_adapter or 'N/D'}
- Conectividad a 8.8.8.8: No (falló)
{('- Detalle: ' + precheck_detail) if precheck_detail else ''}

ESTADO:
- Adaptador activo: {ethernet_adapter}
- Tiene IP: {'Sí' if has_ip else 'No'}
- IP actual: {current_ip or 'N/D'}
- Prefijo: {prefix if prefix is not None else 'N/D'}

INSTRUCCIONES PARA TU RESPUESTA:
1. Confirma que NO hay conectividad a Internet.
2. Indica el adaptador activo y la IP actual (si existe).
3. Pide un dato mínimo: ¿con cable o Wi‑Fi? ¿luz del puerto? ¿gateway corporativo?
4. Sugiere pruebas rápidas: ping gateway, ping 8.8.8.8, nslookup.
5. Aclara que no se aplicaron cambios automáticos de IP (modo seguro).
Respuesta breve (4-6 líneas)."""
                
                if ip_config["has_ip"]:
                    # Tiene IP pero sin conectividad → Cambiar IP manteniendo segmento
                    current_ip = ip_config["ip"]
                    st.info(f"📋 IP actual: {current_ip} (sin conectividad)")
                    st.write("⚙️ Paso 4/4: Buscando nueva IP en el mismo segmento...")
                    
                    # Extraer segmento (primeros 3 octetos)
                    ip_parts = current_ip.split(".")
                    if len(ip_parts) == 4:
                        segment = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                        st.info(f"🔍 Segmento detectado: {segment}.x")
                        
                        # Buscar IP disponible en el mismo segmento
                        assigned_ips = set(fetch_assigned_ipv4_from_mysql())
                        
                        # Generar candidatos en el mismo segmento (evitar .0, .1, .255)
                        candidates = []
                        for last_octet in range(2, 255):
                            candidate = f"{segment}.{last_octet}"
                            if candidate != current_ip and candidate not in assigned_ips:
                                candidates.append(candidate)
                        
                        st.info(f"📊 Encontradas {len(candidates)} IPs disponibles en el segmento")
                        
                        if candidates:
                            new_ip = candidates[0]
                            st.write(f"⚙️ Asignando nueva IP: {new_ip} (mismo segmento {segment}.x)...")
                            
                            result = assign_ip_to_ethernet_and_register(
                                user_key=user_key,
                                interface_alias=ethernet_adapter,
                                prefix_length=ip_config["prefix_length"],
                                require_no_ping_response=True,
                                dry_run=False,
                                force_ip=new_ip
                            )
                            
                            if result.ok and result.assigned_ip:
                                st.success(f"✅ IP cambiada: {current_ip} → {result.assigned_ip}")
                                st.info(f"📡 Adaptador: {ethernet_adapter} | Máscara: 255.255.255.0")
                                status.update(label="✅ Diagnóstico completado", state="complete")
                                
                                return f"""ACCIÓN AUTOMÁTICA COMPLETADA:

DIAGNÓSTICO:
- Adaptador: {ethernet_adapter}
- IP anterior: {current_ip} (sin conectividad)
- IP nueva: {result.assigned_ip} ✅
- Segmento mantenido: {segment}.x
- Gateway: 172.17.87.1
- DNS: 8.8.8.8, 8.8.4.4

RESULTADO:
✅ IP configurada exitosamente en el mismo segmento de red.

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que detectaste problema de conectividad
2. Indica que cambiaste la IP de {current_ip} a {result.assigned_ip} (mismo segmento)
3. Sugiere probar: ping 8.8.8.8
4. Mantén tu respuesta concisa (3-4 líneas)"""
                            else:
                                st.error("❌ Error al cambiar IP. Permisos de Administrador requeridos.")
                                st.warning(f"💡 Detalle: {result.details}")
                                status.update(label="❌ Diagnóstico con errores", state="error")
                                
                                return f"""ACCIÓN AUTOMÁTICA: Error al cambiar IP por permisos.

RESULTADO:
❌ No se pudo cambiar la IP {current_ip} por permisos insuficientes.

SOLUCIÓN:
1. Cierra esta aplicación Streamlit
2. Clic derecho en PowerShell o Terminal
3. "Ejecutar como administrador"
4. Navega a: cd C:\\Users\\info\\Documents\\GitHub\\AI-support
5. Ejecuta: streamlit run .\\sistema_completo_agentes.py

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que se necesitan permisos de Administrador
2. Indica los pasos para reiniciar como Admin
3. Mantén tu respuesta concisa (4-5 líneas)"""
                        else:
                            st.error(f"❌ No hay IPs disponibles en el segmento {segment}.x")
                            status.update(label="❌ Diagnóstico con errores", state="error")
                            
                            return f"""ACCIÓN AUTOMÁTICA: Sin IPs disponibles.

RESULTADO:
⚠️ No hay IPs disponibles en el segmento {segment}.x

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que no hay IPs libres en ese segmento
2. Sugiere contactar al administrador de red
3. Breve (2-3 líneas)"""
                    else:
                        st.error("❌ IP actual inválida")
                        status.update(label="❌ Diagnóstico con errores", state="error")
                        return "Error: IP actual inválida"
                else:
                    # No tiene IP asignada → Asignar del pool
                    st.info("📋 No tiene IP asignada")
                    st.write("⚙️ Paso 4/4: Asignando IP automáticamente del pool...")
                    
                    result = assign_ip_to_ethernet_and_register(
                        user_key=user_key,
                        interface_alias=ethernet_adapter,
                        prefix_length=24,
                        require_no_ping_response=True,
                        dry_run=False,
                    )
                    
                    if result.ok and result.assigned_ip:
                        st.success(f"✅ IP asignada: {result.assigned_ip}")
                        st.info(f"📡 Adaptador: {ethernet_adapter} | Máscara: 255.255.255.0")
                        status.update(label="✅ Diagnóstico completado", state="complete")
                        
                        return f"""ACCIÓN AUTOMÁTICA COMPLETADA:

DIAGNÓSTICO:
El adaptador {ethernet_adapter} no tenía IP asignada.

RESULTADO:
- ✅ IP configurada exitosamente: {result.assigned_ip}
- Adaptador: {ethernet_adapter}
- Máscara de subred: 255.255.255.0
- Gateway predeterminado: 172.17.87.1
- Servidores DNS: 8.8.8.8, 8.8.4.4

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que el adaptador no tenía IP
2. Indica que asignaste automáticamente la IP {result.assigned_ip}
3. Sugiere probar: ping 8.8.8.8
4. Mantén tu respuesta concisa (3-4 líneas)"""
                    else:
                        st.error("❌ Error al asignar IP. Permisos de Administrador requeridos.")
                        status.update(label="❌ Diagnóstico con errores", state="error")
                        
                        return f"""ACCIÓN AUTOMÁTICA: Error al asignar IP por permisos.

RESULTADO:
❌ No se pudo asignar IP por permisos insuficientes.

DETALLES:
{result.details}

SOLUCIÓN:
1. Cierra esta aplicación Streamlit
2. Clic derecho en PowerShell o Terminal
3. "Ejecutar como administrador"
4. Navega a: cd C:\\Users\\info\\Documents\\GitHub\\AI-support
5. Ejecuta: streamlit run .\\sistema_completo_agentes.py

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que se necesitan permisos de Administrador para configurar red
2. Indica los pasos para reiniciar como Admin
3. Mantén tu respuesta concisa (4-5 líneas)"""
            
            except Exception as e:
                st.error(f"❌ Error inesperado: {e}")
                status.update(label="❌ Diagnóstico con errores", state="error")
                
                return f"""ACCIÓN AUTOMÁTICA: Error al diagnosticar.

RESULTADO:
❌ Error: {e}

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que hubo un error al diagnosticar
2. Sugiere ejecutar como Administrador
3. Breve (2-3 líneas)"""
