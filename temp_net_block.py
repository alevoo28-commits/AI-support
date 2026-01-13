# Bloque de automatización de conectividad reescrito

# Automatización de IP: si se pide conectividad/internet/red, asignar IP automáticamente
# Activado por env AI_SUPPORT_NET_AUTOMATION_AUTO (default true para compatibilidad)
net_auto_enabled = os.getenv("AI_SUPPORT_NET_AUTOMATION_AUTO", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}
if net_auto_enabled:
    net_keywords = [
        "no tengo internet",
        "sin internet",
        "no hay internet",
        "no tengo conexión",
        "sin conexión",
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
        "internet no funciona",
    ]
    net_intent = any(k in consulta.lower() for k in net_keywords)
    
    if net_intent:
        # Inicializar contenedor de mensajes
        st.session_state["_net_diagnostic_messages"] = []
        st.session_state["_net_diagnostic_status"] = "running"
        st.session_state["_show_net_diagnostic"] = True
        
        user_key = str(st.session_state.get("current_user") or "local_user").strip()
        
        # Agregar mensaje inicial
        st.session_state["_net_diagnostic_messages"].append(("info", "🔍 Iniciando diagnóstico de conectividad de red..."))
        
        try:
            # PASO 1: Detectar interfaz Ethernet activa (Up)
            st.session_state["_net_diagnostic_messages"].append(("info", "🔎 Paso 1/4: Detectando adaptador Ethernet..."))
            adapters = list_net_adapters()
            ethernet_adapter = None
            for a in adapters:
                name = str(a.get("Name") or "").strip().lower()
                status_text = str(a.get("Status") or "").strip().lower()
                if "ethernet" in name and status_text == "up":
                    ethernet_adapter = str(a.get("Name") or "").strip()
                    break
            
            if not ethernet_adapter:
                st.session_state["_net_diagnostic_messages"].append(("warning", "⚠️ No se encontró adaptador Ethernet, buscando alternativa..."))
                # Fallback: primera interfaz Up que no sea Wi-Fi/Loopback
                for a in adapters:
                    name = str(a.get("Name") or "").strip().lower()
                    status_text = str(a.get("Status") or "").strip().lower()
                    if status_text == "up" and "wi-fi" not in name and "loopback" not in name:
                        ethernet_adapter = str(a.get("Name") or "").strip()
                        break
            
            if not ethernet_adapter:
                st.session_state["_net_diagnostic_messages"].append(("error", "❌ No se encontró un adaptador de red activo"))
                st.session_state["_net_diagnostic_messages"].append(("info", f"Adaptadores disponibles: {', '.join([a.get('Name', 'Sin nombre') for a in adapters[:5]])}"))
                st.session_state["_net_diagnostic_status"] = "error"
                
                prompt = f"""ACCIÓN AUTOMÁTICA: No se encontró adaptador Ethernet.

RESULTADO:
⚠️ No se encontró un adaptador Ethernet activo (Up).

Adaptadores disponibles:
{chr(10).join([f"- {a.get('Name', 'Sin nombre')} ({a.get('Status', 'Desconocido')})" for a in adapters[:5]])}

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que no encontraste un adaptador Ethernet activo
2. Sugiere verificar que el cable esté conectado y el adaptador habilitado
3. Lista los adaptadores encontrados
4. Mantén tu respuesta breve (3-4 líneas)"""
            else:
                st.session_state["_net_diagnostic_messages"].append(("success", f"✅ Adaptador encontrado: {ethernet_adapter}"))
                
                # PASO 2: Probar conectividad
                st.session_state["_net_diagnostic_messages"].append(("info", "🌐 Paso 2/4: Probando conectividad a Internet (8.8.8.8)..."))
                
                from ai_support.core.ip_assignment import test_connectivity_on_interface, get_current_adapter_ip_config, assign_ip_to_ethernet_and_register
                
                connectivity = test_connectivity_on_interface(ethernet_adapter, "8.8.8.8")
                
                if connectivity["success"]:
                    # Si hay conectividad, no hacer nada más
                    st.session_state["_net_diagnostic_messages"].append(("success", "✅ Conectividad OK - No se requieren cambios"))
                    st.session_state["_net_diagnostic_status"] = "complete"
                    
                    prompt = f"""ACCIÓN AUTOMÁTICA COMPLETADA:

DIAGNÓSTICO DE CONECTIVIDAD:
✅ Conectividad OK - El adaptador {ethernet_adapter} tiene acceso a Internet.

RESULTADO:
No se requieren cambios. La conexión está funcionando correctamente.

INSTRUCCIONES PARA TU RESPUESTA:
1. Informa al usuario que su conectividad está funcionando
2. Sugiere que si tiene problemas específicos, los describa con más detalle
3. Mantén tu respuesta breve (2-3 líneas)"""
                else:
                    # PASO 3: Si no hay conectividad, revisar configuración IP
                    st.session_state["_net_diagnostic_messages"].append(("warning", "⚠️ Sin conectividad a Internet"))
                    st.session_state["_net_diagnostic_messages"].append(("info", "🔧 Paso 3/4: Obteniendo configuración IP actual..."))
                    
                    ip_config = get_current_adapter_ip_config(ethernet_adapter)
                    
                    if ip_config["has_ip"]:
                        # Tiene IP pero sin conectividad → Cambiar IP manteniendo segmento
                        current_ip = ip_config["ip"]
                        st.session_state["_net_diagnostic_messages"].append(("info", f"📋 IP actual: {current_ip} (sin conectividad)"))
                        
                        st.session_state["_net_diagnostic_messages"].append(("info", "⚙️ Paso 4/4: Buscando nueva IP en el mismo segmento..."))
                        
                        # Extraer segmento (primeros 3 octetos)
                        ip_parts = current_ip.split(".")
                        if len(ip_parts) == 4:
                            segment = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                            st.session_state["_net_diagnostic_messages"].append(("info", f"🔍 Segmento detectado: {segment}.x"))
                            
                            # Buscar IP disponible en el mismo segmento
                            from ai_support.core.ip_pool_mysql import fetch_assigned_ipv4_from_mysql
                            assigned_ips = set(fetch_assigned_ipv4_from_mysql())
                            
                            # Generar candidatos en el mismo segmento (evitar .0, .1, .255)
                            candidates = []
                            for last_octet in range(2, 255):
                                candidate = f"{segment}.{last_octet}"
                                if candidate != current_ip and candidate not in assigned_ips:
                                    candidates.append(candidate)
                            
                            st.session_state["_net_diagnostic_messages"].append(("info", f"📊 Encontradas {len(candidates)} IPs disponibles en el segmento"))
                            
                            if candidates:
                                new_ip = candidates[0]
                                st.session_state["_net_diagnostic_messages"].append(("info", f"⚙️ Asignando nueva IP: {new_ip} (mismo segmento {segment}.x)..."))
                                
                                result = assign_ip_to_ethernet_and_register(
                                    user_key=user_key,
                                    interface_alias=ethernet_adapter,
                                    prefix_length=ip_config["prefix_length"],
                                    require_no_ping_response=True,
                                    dry_run=False,
                                    force_ip=new_ip
                                )
                                
                                if result.ok and result.assigned_ip:
                                    st.session_state["_net_diagnostic_messages"].append(("success", f"✅ IP cambiada: {current_ip} → {result.assigned_ip}"))
                                    st.session_state["_net_diagnostic_messages"].append(("info", f"📡 Adaptador: {ethernet_adapter} | Máscara: 255.255.255.0"))
                                    st.session_state["_net_diagnostic_status"] = "complete"
                                    
                                    prompt = f"""ACCIÓN AUTOMÁTICA COMPLETADA:

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
                                    st.session_state["_net_diagnostic_messages"].append(("error", "❌ Error al cambiar IP. Permisos de Administrador requeridos."))
                                    st.session_state["_net_diagnostic_messages"].append(("warning", f"💡 Detalle: {result.details}"))
                                    st.session_state["_net_diagnostic_status"] = "error"
                                    
                                    prompt = f"""ACCIÓN AUTOMÁTICA: Error al cambiar IP por permisos.

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
                                st.session_state["_net_diagnostic_messages"].append(("error", f"❌ No hay IPs disponibles en el segmento {segment}.x"))
                                st.session_state["_net_diagnostic_status"] = "error"
                                
                                prompt = f"""ACCIÓN AUTOMÁTICA: Sin IPs disponibles.

RESULTADO:
⚠️ No hay IPs disponibles en el segmento {segment}.x

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que no hay IPs libres en ese segmento
2. Sugiere contactar al administrador de red
3. Breve (2-3 líneas)"""
                        else:
                            st.session_state["_net_diagnostic_messages"].append(("error", "❌ IP actual inválida"))
                            st.session_state["_net_diagnostic_status"] = "error"
                            prompt = "Error: IP actual inválida"
                    else:
                        # No tiene IP asignada → Asignar del pool
                        st.session_state["_net_diagnostic_messages"].append(("info", "📋 No tiene IP asignada"))
                        st.session_state["_net_diagnostic_messages"].append(("info", "⚙️ Paso 4/4: Asignando IP automáticamente del pool..."))
                        
                        from ai_support.core.ip_assignment import assign_ip_to_ethernet_and_register
                        
                        result = assign_ip_to_ethernet_and_register(
                            user_key=user_key,
                            interface_alias=ethernet_adapter,
                            prefix_length=24,
                            require_no_ping_response=True,
                            dry_run=False,
                        )
                        
                        if result.ok and result.assigned_ip:
                            st.session_state["_net_diagnostic_messages"].append(("success", f"✅ IP asignada: {result.assigned_ip}"))
                            st.session_state["_net_diagnostic_messages"].append(("info", f"📡 Adaptador: {ethernet_adapter} | Máscara: 255.255.255.0"))
                            st.session_state["_net_diagnostic_status"] = "complete"
                            
                            prompt = f"""ACCIÓN AUTOMÁTICA COMPLETADA:

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
                            st.session_state["_net_diagnostic_messages"].append(("error", "❌ Error al asignar IP. Permisos de Administrador requeridos."))
                            st.session_state["_net_diagnostic_status"] = "error"
                            
                            prompt = f"""ACCIÓN AUTOMÁTICA: Error al asignar IP por permisos.

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
            st.session_state["_net_diagnostic_messages"].append(("error", f"❌ Error inesperado: {e}"))
            st.session_state["_net_diagnostic_status"] = "error"
            
            prompt = f"""ACCIÓN AUTOMÁTICA: Error al diagnosticar.

RESULTADO:
❌ Error: {e}

INSTRUCCIONES PARA TU RESPUESTA:
1. Explica que hubo un error al diagnosticar
2. Sugiere ejecutar como Administrador
3. Breve (2-3 líneas)"""
