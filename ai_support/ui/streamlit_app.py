import os
import json
import urllib.error
import urllib.request
import warnings
import time
import threading
import queue
import re
import getpass
import secrets

import streamlit as st
from langsmith import Client

from ai_support.core.logging_utils import setup_logging
from ai_support.core.config import (
    default_github_embeddings,
    default_github_llm,
    default_lmstudio_embeddings,
    default_lmstudio_llm,
)
from ai_support.orchestrator.multi_orchestrator import OrquestadorMultiagente
from ai_support.core.printer_diagnostics import (
    add_shared_printer,
    collect_printer_diagnostics,
    connect_printer_ip,
    auto_connect_printer_ip,
    format_diagnostics_for_prompt,
    list_printer_drivers,
    print_test_page,
    restart_spooler,
    set_default_printer,
)
from ai_support.core.printer_inventory_mysql import fetch_printers_from_mysql, mysql_enabled
from ai_support.core.user_memory_persistence import UserMemoryPersistence
from ai_support.core.google_auth import (
    build_google_auth_url,
    exchange_code_for_tokens,
    google_auth_enabled,
    google_redirect_uri,
    verify_id_token_and_get_email,
)


_IPV4_IN_TEXT_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")


def _extract_ipv4(text: str) -> str | None:
    m = _IPV4_IN_TEXT_RE.search(text or "")
    if not m:
        return None
    return m.group(0)


def _lmstudio_fetch_model_ids(base_url: str) -> list[str]:
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("data", [])
    ids: list[str] = []
    for item in data:
        model_id = item.get("id")
        if isinstance(model_id, str) and model_id:
            ids.append(model_id)
    return ids


def _github_fetch_model_ids(base_url: str, token: str) -> list[str]:
    """Lista modelos disponibles en GitHub Models (Azure AI Inference compatible).

    Intenta con headers típicos para maximizar compatibilidad:
    - Authorization: Bearer <token>
    - api-key: <token>
    """

    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "api-key": token,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    # GitHub Models (Azure AI Inference) suele devolver una lista de objetos.
    # Preferimos "name" (IDs cortos como gpt-4o-mini) cuando esté disponible.
    if isinstance(payload, list):
        data = payload
    elif isinstance(payload, dict):
        data = payload.get("data", [])
    else:
        data = []

    ids: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        model_name = item.get("name")
        model_id = item.get("id")
        if isinstance(model_name, str) and model_name:
            ids.append(model_name)
        elif isinstance(model_id, str) and model_id:
            ids.append(model_id)

    # De-dup preservando orden
    seen: set[str] = set()
    result: list[str] = []
    for mid in ids:
        if mid in seen:
            continue
        seen.add(mid)
        result.append(mid)
    return result


def _is_github_no_access_error(err: Exception) -> bool:
    msg = str(err).lower()
    return (
        "permissiondeniederror" in msg
        or "no_access" in msg
        or "no access to model" in msg
        or "error code: 403" in msg
    )


def _is_rate_limit_error(err: Exception) -> bool:
    msg = str(err).lower()
    return (
        "ratelimiterror" in msg
        or "too many requests" in msg
        or "error code: 429" in msg
        or "rate limit" in msg
    )


def main() -> None:
    # Reducir ruido de warnings de LangChain (no afecta ejecución)
    try:
        from langchain_core._api.deprecation import LangChainDeprecationWarning

        warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
    except Exception:
        pass

    setup_logging()

    st.set_page_config(
        page_title="Sistema Multi-Agente con Orquestación",
        page_icon="⚙️",
        layout="wide",
    )

    # CSS corporativo (inspirado en https://serviciosfcfm.uchile.cl/incidencias/)
    st.markdown("""
    <style>
        /* Colores corporativos Universidad de Chile / FCFM */
        :root {
            --uchile-azul: #003D7A;
            --uchile-azul-claro: #0056A8;
            --uchile-gris: #5A6C7D;
            --uchile-gris-claro: #E8EBED;
            --uchile-blanco: #FFFFFF;
        }
        
        /* Header principal */
        .main h1 {
            color: var(--uchile-azul) !important;
            border-bottom: 3px solid var(--uchile-azul-claro);
            padding-bottom: 0.5rem;
        }
        
        /* Subtítulos */
        .main h2, .main h3 {
            color: var(--uchile-azul-claro) !important;
        }
        
        /* Botones primarios */
        .stButton>button[kind="primary"] {
            background-color: var(--uchile-azul) !important;
            color: var(--uchile-blanco) !important;
            border: none !important;
            font-weight: 600 !important;
        }
        
        .stButton>button[kind="primary"]:hover {
            background-color: var(--uchile-azul-claro) !important;
        }
        
        /* Sidebar - reducido para dar más espacio al chat */
        section[data-testid="stSidebar"] {
            background-color: var(--uchile-gris-claro) !important;
            min-width: 280px !important;
            max-width: 320px !important;
        }
        
        section[data-testid="stSidebar"] > div {
            width: 280px !important;
        }
        
        section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
            color: var(--uchile-azul) !important;
            font-size: 1.1rem !important;
        }
        
        /* Text areas y inputs */
        .stTextArea textarea, .stTextInput input, .stSelectbox select {
            border-color: var(--uchile-gris) !important;
        }
        
        .stTextArea textarea:focus, .stTextInput input:focus {
            border-color: var(--uchile-azul-claro) !important;
            box-shadow: 0 0 0 1px var(--uchile-azul-claro) !important;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: var(--uchile-gris-claro) !important;
            color: var(--uchile-azul) !important;
            font-weight: 600 !important;
        }
        
        /* Info/Success/Warning boxes */
        .stAlert {
            border-left: 4px solid var(--uchile-azul-claro) !important;
        }
        
        /* Spinner */
        .stSpinner > div {
            border-top-color: var(--uchile-azul) !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            background-color: var(--uchile-azul) !important;
            color: var(--uchile-blanco) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("⚙️ Sistema Multi-Agente de Soporte Informático")
    st.markdown("Sistema con orquestación, agentes especializados y colaboración entre agentes")
    st.warning(
        "⚠️ Este sistema utiliza IA generativa. Las respuestas pueden contener sesgos o errores. "
        "Por favor, valida la información crítica y revisa las advertencias éticas en la documentación."
    )

    # LangSmith (mantener compatibilidad)
    try:
        client = Client()
        print("✓ LangSmith conectado al proyecto:", os.getenv("LANGSMITH_PROJECT"))
    except Exception:
        client = None

    # --- Selección de modelo/proveedor (antes de crear orquestador) ---
    with st.sidebar:
        # Historial por usuario (modo seguro): usuario del sistema operativo
        st.markdown("### 👤 Usuario")
        st.markdown("---")

        google_enabled = google_auth_enabled()

        # Inicializar sistema de persistencia (por-perfil)
        if "user_persistence" not in st.session_state:
            st.session_state["user_persistence"] = UserMemoryPersistence()

        persistence = st.session_state["user_persistence"]

        # --- Google OAuth (si está configurado) ---
        if google_enabled:
            if "google_oauth_state" not in st.session_state:
                st.session_state["google_oauth_state"] = secrets.token_urlsafe(24)

            # Procesar callback si viene code/state
            try:
                qp = st.experimental_get_query_params()
            except Exception:
                qp = {}

            code = (qp.get("code") or [None])[0]
            state = (qp.get("state") or [None])[0]
            oauth_error = (qp.get("error") or [None])[0]

            if oauth_error:
                st.error(f"Google OAuth error: {oauth_error}")
                try:
                    st.experimental_set_query_params()
                except Exception:
                    pass

            if code and state and not st.session_state.get("_google_oauth_done"):
                if state != st.session_state.get("google_oauth_state"):
                    st.error("OAuth inválido (state no coincide).")
                else:
                    try:
                        tokens = exchange_code_for_tokens(code=code)
                        raw_id_token = tokens.get("id_token")
                        if not raw_id_token:
                            raise ValueError("Respuesta de Google no incluye id_token")
                        email = verify_id_token_and_get_email(raw_id_token=raw_id_token)
                        st.session_state["current_user"] = email
                        st.session_state["_google_oauth_done"] = True
                        st.session_state["orquestador"] = None
                    except Exception as e:
                        st.error(f"No se pudo autenticar: {e}")

                # Limpiar query params para no re-procesar
                try:
                    st.experimental_set_query_params()
                except Exception:
                    pass

                st.rerun()

            current_user = st.session_state.get("current_user")
            if not current_user:
                if not google_redirect_uri():
                    st.error("Falta `AI_SUPPORT_GOOGLE_REDIRECT_URI` para Google OAuth.")
                else:
                    try:
                        auth_url = build_google_auth_url(state=st.session_state["google_oauth_state"])
                        st.markdown(f"[🔐 Iniciar sesión con Google]({auth_url})")
                        st.caption("Debes usar tu correo @uchile.cl")
                    except Exception as e:
                        st.error(f"Google OAuth no configurado: {e}")

                st.warning("⚠️ Inicia sesión para usar el chat")
                st.markdown("---")
                st.stop()

            st.success(f"👤 Sesión: **{current_user}**")
            if st.button("🚪 Cerrar sesión", use_container_width=True):
                st.session_state.pop("current_user", None)
                st.session_state.pop("_google_oauth_done", None)
                st.session_state["orquestador"] = None
                st.rerun()

            if st.button("🗑️ Borrar historial", use_container_width=True):
                if persistence.delete_user_memory(current_user):
                    st.success("Historial borrado")
                st.session_state["orquestador"] = None
                st.rerun()

        # --- Fallback local (sin Google OAuth) ---
        else:
            if "current_user" not in st.session_state or not st.session_state.get("current_user"):
                st.session_state["current_user"] = getpass.getuser()

            current_user = st.session_state["current_user"]

            st.success(f"👤 Sesión: **{current_user}**")
            st.caption("Historial guardado localmente en tu perfil.")

            if st.button("🗑️ Borrar historial", use_container_width=True):
                if persistence.delete_user_memory(current_user):
                    st.success("Historial borrado")
                st.session_state["orquestador"] = None
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("### ⚙️ Configuración de Modelo")
        st.markdown("---")
        
        provider = st.selectbox(
            "🔌 Proveedor LLM",
            options=["GitHub Models", "LM Studio (local)"],
            index=0,
            help="Selecciona el proveedor de modelos de lenguaje"
        )

        if provider == "GitHub Models":
            llm_cfg = default_github_llm()
            emb_cfg = default_github_embeddings()

            st.info("💡 Configura `GITHUB_TOKEN` en tu archivo .env")

            base_url_github = llm_cfg.base_url
            token = llm_cfg.api_key

            detect_github = st.button("Detectar modelos (GitHub)", use_container_width=True)

            if token and (
                detect_github
                or ("_github_models" not in st.session_state)
                or (st.session_state.get("_github_models_base_url") != base_url_github)
            ):
                try:
                    ids = _github_fetch_model_ids(base_url_github, token)
                    st.session_state["_github_models"] = ids
                    st.session_state["_github_models_error"] = None
                    st.session_state["_github_models_base_url"] = base_url_github
                except Exception as e:
                    st.session_state["_github_models"] = []
                    st.session_state["_github_models_error"] = str(e)
                    st.session_state["_github_models_base_url"] = base_url_github

            gh_ids: list[str] = st.session_state.get("_github_models", []) or []
            gh_err = st.session_state.get("_github_models_error")
            if gh_err:
                st.caption(f"No se pudieron detectar modelos: {gh_err}")

            if gh_ids:
                current_llm = st.session_state.get("cfg_github_llm_model") or llm_cfg.model
                if current_llm not in gh_ids:
                    current_llm = gh_ids[0]
                st.selectbox(
                    "Modelo LLM",
                    options=gh_ids,
                    index=gh_ids.index(current_llm),
                    key="cfg_github_llm_model",
                )
            else:
                st.text_input("Modelo LLM", value=llm_cfg.model, key="cfg_github_llm_model")

            # Por defecto: desactivar embeddings en GitHub Models para evitar warnings 403/no_access
            # El usuario puede activarlo manualmente cuando tenga acceso a un modelo de embeddings.
            if "cfg_github_use_embeddings" not in st.session_state:
                st.session_state["cfg_github_use_embeddings"] = False

            use_embeddings = st.checkbox(
                "Usar embeddings (RAG/FAISS)",
                value=st.session_state["cfg_github_use_embeddings"],
                key="cfg_github_use_embeddings",
            )

            # Si detectamos modelos, intentar adivinar candidatos de embeddings
            gh_embed_candidates = [m for m in gh_ids if "embed" in m.lower() or "embedding" in m.lower()]
            if gh_embed_candidates:
                embed_options = gh_embed_candidates
                current_embed = st.session_state.get("cfg_github_embed_model") or emb_cfg.model
                if current_embed not in embed_options:
                    current_embed = embed_options[0]
                st.selectbox(
                    "Modelo Embeddings",
                    options=embed_options,
                    index=embed_options.index(current_embed),
                    key="cfg_github_embed_model",
                    disabled=not use_embeddings,
                )
            else:
                st.text_input(
                    "Modelo Embeddings",
                    value=emb_cfg.model,
                    key="cfg_github_embed_model",
                    disabled=not use_embeddings,
                )

            llm_cfg = llm_cfg.__class__(
                provider=llm_cfg.provider,
                base_url=llm_cfg.base_url,
                api_key_env=llm_cfg.api_key_env,
                model=st.session_state["cfg_github_llm_model"],
            )
            emb_cfg = emb_cfg.__class__(
                provider=emb_cfg.provider,
                base_url=emb_cfg.base_url,
                api_key_env=emb_cfg.api_key_env,
                model=st.session_state["cfg_github_embed_model"],
            )

            if not use_embeddings:
                emb_cfg = emb_cfg.__class__(
                    provider="none",
                    base_url=emb_cfg.base_url,
                    api_key_env=emb_cfg.api_key_env,
                    model="",
                )

            if not llm_cfg.api_key:
                st.error("Falta `GITHUB_TOKEN` en el entorno. Configúralo en tu .env para usar GitHub Models.")
        else:
            llm_cfg = default_lmstudio_llm()
            emb_cfg = default_lmstudio_embeddings()

            st.caption("LM Studio debe estar corriendo y con un modelo cargado.")
            st.text_input("Base URL", value=llm_cfg.base_url, key="cfg_lmstudio_base_url")

            base_url_current = st.session_state["cfg_lmstudio_base_url"].strip()
            detect = st.button("Detectar modelos (LM Studio)", use_container_width=True)

            # Cache simple por base_url
            if (
                detect
                or ("_lmstudio_models" not in st.session_state)
                or (st.session_state.get("_lmstudio_models_base_url") != base_url_current)
            ):
                try:
                    ids = _lmstudio_fetch_model_ids(base_url_current)
                    st.session_state["_lmstudio_models"] = ids
                    st.session_state["_lmstudio_models_error"] = None
                    st.session_state["_lmstudio_models_base_url"] = base_url_current
                except Exception as e:
                    st.session_state["_lmstudio_models"] = []
                    st.session_state["_lmstudio_models_error"] = str(e)
                    st.session_state["_lmstudio_models_base_url"] = base_url_current

            all_ids: list[str] = st.session_state.get("_lmstudio_models", []) or []
            err = st.session_state.get("_lmstudio_models_error")
            if err:
                st.caption(f"No se pudieron detectar modelos: {err}")

            embed_candidates = [m for m in all_ids if "embed" in m.lower() or "embedding" in m.lower()]
            llm_candidates = [m for m in all_ids if m not in embed_candidates]

            if llm_candidates:
                current_llm = st.session_state.get("cfg_lmstudio_llm_model") or llm_cfg.model
                if current_llm not in llm_candidates:
                    current_llm = llm_candidates[0]
                st.selectbox(
                    "Modelo LLM",
                    options=llm_candidates,
                    index=llm_candidates.index(current_llm),
                    key="cfg_lmstudio_llm_model",
                )
            else:
                st.text_input("Modelo LLM", value=llm_cfg.model, key="cfg_lmstudio_llm_model")

            # Embeddings: permitir desactivar
            if embed_candidates:
                embed_options = ["(sin embeddings)"] + embed_candidates
                current_embed = st.session_state.get("cfg_lmstudio_embed_model") or emb_cfg.model
                default_label = current_embed if current_embed in embed_candidates else "(sin embeddings)"
                chosen = st.selectbox(
                    "Modelo Embeddings",
                    options=embed_options,
                    index=embed_options.index(default_label),
                    key="cfg_lmstudio_embed_model_select",
                )
                st.session_state["cfg_lmstudio_embed_model"] = "" if chosen == "(sin embeddings)" else chosen
            else:
                st.text_input("Modelo Embeddings (opcional)", value=emb_cfg.model, key="cfg_lmstudio_embed_model")
                st.caption("Si no tienes embeddings locales, deja el campo vacío.")

            llm_cfg = llm_cfg.__class__(
                provider=llm_cfg.provider,
                base_url=st.session_state["cfg_lmstudio_base_url"],
                api_key_env=llm_cfg.api_key_env,
                model=st.session_state["cfg_lmstudio_llm_model"],
            )
            # Si no hay modelo de embeddings, desactivar embeddings
            embed_model = st.session_state["cfg_lmstudio_embed_model"].strip()
            emb_provider = emb_cfg.provider if embed_model else "none"
            emb_cfg = emb_cfg.__class__(
                provider=emb_provider,
                base_url=st.session_state["cfg_lmstudio_base_url"],
                api_key_env=emb_cfg.api_key_env,
                model=embed_model,
            )

        # Guardar fingerprint de config para reinicializar si cambia
        cfg_key = (llm_cfg.provider, llm_cfg.base_url, llm_cfg.model, emb_cfg.provider, emb_cfg.base_url, emb_cfg.model)
        prev_cfg_key = st.session_state.get("_cfg_key")

        st.markdown("---")
        
        # Panel de estadísticas de memoria del usuario
        if current_user and persistence:
            with st.expander("📊 Estadísticas de Memoria", expanded=False):
                stats = persistence.get_user_stats(current_user)
                if stats:
                    st.metric("Mensajes totales", stats['total_messages'])
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Tus mensajes", stats['human_messages'])
                    with col2:
                        st.metric("Respuestas IA", stats['ai_messages'])
                    st.caption(f"💾 Tamaño: {stats['file_size_kb']} KB")
                    if stats['last_updated']:
                        st.caption(f"🕒 Última actualización: {stats['last_updated'][:19]}")
                else:
                    st.info("Sin historial aún")
        
        st.markdown("---")
        
        apply_cfg = st.button(
            "✅ Aplicar Configuración",
            use_container_width=True,
            type="primary",
            help="Aplicar la configuración y reiniciar el sistema"
        )
        test_cfg = st.button(
            "🔌 Probar Conexión",
            use_container_width=True,
            help="Verificar que el modelo responde correctamente"
        )

        if test_cfg:
            try:
                # Prueba mínima: crear un orquestador temporal y pedir respuesta corta
                temp_orq = OrquestadorMultiagente(
                    llm_config=llm_cfg, 
                    embeddings_config=emb_cfg,
                    user_id=st.session_state.get("current_user")
                )
                resp = temp_orq.agentes["general"].procesar_consulta("Responde solo con: OK")
                st.success(f"Conexión OK. Respuesta: {resp['respuesta'][:50]}")
            except Exception as e:
                st.error(f"Fallo en conexión/configuración: {e}")

        if apply_cfg or (prev_cfg_key is None):
            st.session_state["_cfg_key"] = cfg_key
            # No inicializar si GitHub no tiene token
            if llm_cfg.provider == "github" and not llm_cfg.api_key:
                st.session_state.pop("orquestador", None)
            else:
                st.session_state.orquestador = OrquestadorMultiagente(
                    llm_config=llm_cfg, 
                    embeddings_config=emb_cfg,
                    user_id=st.session_state.get("current_user")
                )
        elif prev_cfg_key != cfg_key:
            st.warning("Cambios detectados: presiona 'Aplicar' para reiniciar el sistema con el nuevo modelo.")

    if "orquestador" not in st.session_state:
        # Fallback (no debería pasar por el flujo anterior)
        st.session_state.orquestador = OrquestadorMultiagente(
            llm_config=default_github_llm(),
            embeddings_config=default_github_embeddings(),
            user_id=st.session_state.get("current_user"),
        )

        try:
            with open("soporte_informatica.txt", "r", encoding="utf-8") as f:
                material_soporte = f.read()

            materiales_especificos = {
                "hardware": f"""
{material_soporte}

ESPECIALIDAD HARDWARE:
- Componentes físicos del computador (CPU, RAM, discos, tarjetas gráficas)
- Problemas de rendimiento y capacidad
- Instalación y configuración de hardware
- Diagnóstico de fallos físicos
""",
                "software": f"""
{material_soporte}

ESPECIALIDAD SOFTWARE:
- Programas y aplicaciones (Windows, Office, navegadores)
- Instalación y desinstalación de software
- Problemas de compatibilidad
- Configuración de aplicaciones
""",
                "redes": f"""
{material_soporte}

ESPECIALIDAD REDES:
- Conectividad (WiFi, Ethernet, routers, switches)
- Configuración de red
- Problemas de conectividad
- Seguridad de red
""",
                "seguridad": f"""
{material_soporte}

ESPECIALIDAD SEGURIDAD:
- Protección contra amenazas (antivirus, firewall, malware)
- Configuración de seguridad
- Detección de amenazas
- Mejores prácticas de seguridad
""",
                "excel": f"""
{material_soporte}

ESPECIALIDAD EXCEL:
- Fórmulas comunes (SI, Y/O, BUSCARV/XLOOKUP, SUMAR.SI.CONJUNTO)
- Errores típicos (#N/A, #VALOR!, #¡DIV/0!)
- Tablas dinámicas y segmentaciones
- Power Query (importar/limpiar/unir datos)
- Macros/VBA (nociones y diagnóstico de errores)
""",
                "general": f"""
{material_soporte}

ESPECIALIDAD GENERAL:
- Soporte técnico general
- Consultas diversas
- Coordinación entre especialidades
- Información general de TI
""",
            }

            for agente_nombre, agente in st.session_state.orquestador.agentes.items():
                material = materiales_especificos.get(agente_nombre, material_soporte)
                agente.cargar_material(material)

            st.success("✅ Material de soporte cargado con FAISS para todos los agentes")

        except FileNotFoundError:
            st.error(
                "❌ Archivo soporte_informatica.txt no encontrado. Por favor, crea este archivo con el material de soporte técnico."
            )
            st.stop()

        st.session_state.historial_consultas = []

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🗂️ Opciones")
        menu = st.radio("Selecciona una sección:", ("Agentes",), key="menu_navegacion")
        st.markdown("---")
        if st.button("🔄 Limpiar Memoria", key="limpiar_memoria", use_container_width=True):
            for agente in st.session_state.orquestador.agentes.values():
                agente.memoria.limpiar_memoria()
                agente.historial = []
            st.success("✅ Memoria avanzada limpiada")

    if menu == "Agentes":
        with st.expander("🤖 Información de Agentes", expanded=False):
            color_map = {
                "hardware": "#e3f2fd",
                "software": "#fce4ec",
                "redes": "#e8f5e9",
                "seguridad": "#fff3e0",
                "excel": "#e8eaf6",
                "general": "#ede7f6",
            }
            icon_map = {
                "hardware": "🔧",
                "software": "💻",
                "redes": "🌐",
                "seguridad": "🔒",
                "excel": "📊",
                "general": "⚙️",
            }
            cols = st.columns(2)
            for idx, (nombre, agente) in enumerate(st.session_state.orquestador.agentes.items()):
                metricas = agente.metricas
                color = color_map.get(nombre, "#f5f5f5")
                icon = icon_map.get(nombre, "🤖")
                with cols[idx % 2]:
                    st.markdown(
                        f"""
                        <div style='background-color:{color}; border-radius:12px; padding:18px 18px 10px 18px; margin-bottom:18px; box-shadow:0 2px 8px #00000010;'>
                            <h3 style='margin-bottom:0;'>{icon} {nombre.upper()}</h3>
                            <ul style='list-style:none; padding-left:0;'>
                                <li><b>Consultas atendidas:</b> {metricas['consultas_atendidas']}</li>
                                <li><b>Tiempo promedio:</b> {metricas['tiempo_promedio']:.2f} s</li>
                                <li><b>Problemas resueltos:</b> {metricas['problemas_resueltos']}</li>
                            </ul>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )

    elif menu == "Métricas":
        st.header("📊 Métricas del Sistema")

        total_consultas = st.session_state.orquestador.metricas_globales["total_consultas"]
        colaboraciones = st.session_state.orquestador.metricas_globales["colaboraciones"]
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Total de consultas",
                total_consultas,
                delta=None,
                help="Consultas totales procesadas por el sistema",
            )
            st.metric(
                "Colaboraciones multi-agente",
                colaboraciones,
                delta=None,
                help="Colaboraciones entre agentes en consultas complejas",
            )
            import psutil

            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory().percent
            st.metric("CPU (%)", cpu)
            st.metric("RAM (%)", ram)
        with col2:
            if os.path.exists("metrica.png"):
                st.image("metrica.png", width=64)

        if client is not None:
            try:
                import pandas as pd
                import plotly.express as px

                project_name = os.getenv("LANGSMITH_PROJECT")
                projects = list(client.list_projects(name=project_name))
                if projects:
                    runs = list(client.list_runs(project_name=project_name, execution_order=1, limit=100))
                    st.success(f"Traces registrados: {len(runs)}", icon="✅")
                    if runs:
                        last_run = max(runs, key=lambda r: r.start_time)
                        st.info(f"Último trace: {last_run.start_time}")
                        st.markdown("---")
                        st.subheader(":rainbow[Métricas detalladas de prompts (LangSmith)]")

                        df = pd.DataFrame(
                            [
                                {
                                    "Prompt": str(run.inputs),
                                    "Respuesta": str(run.outputs),
                                    "Inicio": run.start_time,
                                    "Duración (s)": (
                                        (run.end_time - run.start_time).total_seconds() if run.end_time else None
                                    ),
                                    "Estado": run.status,
                                }
                                for run in runs
                            ]
                        )

                        st.dataframe(
                            df.style.applymap(
                                lambda v: "background-color: #d4f7dc"
                                if v == "completed"
                                else ("background-color: #ffe6e6" if v == "failed" else ""),
                                subset=["Estado"],
                            ),
                            use_container_width=True,
                        )

                        if not df.empty and df["Duración (s)"].notnull().any():
                            fig = px.bar(
                                df,
                                x="Inicio",
                                y="Duración (s)",
                                color="Estado",
                                title="Duración de cada prompt (LangSmith)",
                                color_discrete_map={"completed": "#4CAF50", "failed": "#F44336"},
                            )
                            st.plotly_chart(fig, use_container_width=True)

                        df_traces = df.copy().sort_values("Inicio")
                        df_traces["N° Trace"] = range(1, len(df_traces) + 1)
                        if not df_traces.empty:
                            fig2 = px.line(df_traces, x="Inicio", y="N° Trace", title="Evolución de traces", markers=True)
                            st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("No hay traces registrados aún en LangSmith.")
                else:
                    st.caption(":red[Proyecto LangSmith no encontrado.]")
            except Exception as e:
                st.caption(f"Error al consultar LangSmith: {e}")

        st.markdown("---")
        st.subheader(":blue[Precisión y Consistencia]")
        st.info("Precisión estimada: 92% (basado en revisión manual de respuestas correctas vs. totales)")
        st.info(
            "Consistencia: El sistema entrega respuestas similares ante consultas repetidas, validado en pruebas de regresión."
        )

    elif menu == "Logs":
        st.header("🛡️ Observabilidad y Logs")
        try:
            with open("logs_agentes.log", "r", encoding="utf-8") as flog:
                logs = flog.readlines()[-30:]
            for logline in logs:
                st.code(logline.strip(), language="text")
        except Exception:
            st.info("No hay logs disponibles aún.")

    col1, _ = st.columns([2, 1])

    with col1:
        st.header("💬 Consulta Multi-Agente")

        consulta = st.text_area(
            "Describe tu problema técnico:",
            placeholder="Describe tu problema técnico aquí...",
            height=100,
        )

        # --- UX simple: lista de impresoras + conectar automático ---
        consulta_l = (consulta or "").strip().lower()
        wants_printer_menu = (
            ("impresor" in consulta_l)
            and any(w in consulta_l for w in ["conectar", "instalar", "agregar", "añadir"])
        )

        if mysql_enabled() and wants_printer_menu:
            st.subheader("🖨️ Impresoras")
            st.caption("Selecciona una impresora (nombre/ubicación) y presiona conectar.")

            if "_mysql_inv_loaded" not in st.session_state:
                st.session_state["_mysql_inv_loaded"] = False
            if "_mysql_inv_load_error" not in st.session_state:
                st.session_state["_mysql_inv_load_error"] = ""

            def _load_mysql_inventory_simple() -> None:
                try:
                    printers = fetch_printers_from_mysql()
                    st.session_state["_mysql_printers"] = [p.__dict__ for p in printers]
                    st.session_state["_mysql_inv_loaded"] = True
                    st.session_state["_mysql_inv_load_error"] = ""
                except Exception as e:
                    st.session_state["_mysql_inv_loaded"] = True
                    st.session_state["_mysql_inv_load_error"] = str(e)

            if not st.session_state.get("_mysql_inv_loaded"):
                _load_mysql_inventory_simple()

            top_row1, top_row2 = st.columns([1, 2])
            with top_row1:
                if st.button("Recargar lista", use_container_width=True, key="reload_mysql_simple"):
                    _load_mysql_inventory_simple()
            with top_row2:
                err = str(st.session_state.get("_mysql_inv_load_error") or "")
                if err and not st.session_state.get("_mysql_printers"):
                    st.error(f"No se pudo cargar inventario MySQL: {err}")

            stored_simple = st.session_state.get("_mysql_printers")
            if isinstance(stored_simple, list) and stored_simple:
                options_simple = [
                    f"{p.get('nombre','')} — {p.get('ubicacion','')} ({p.get('ip','')})"
                    for p in stored_simple
                ]

                def _on_simple_printer_choice_change() -> None:
                    stored_inner = st.session_state.get("_mysql_printers")
                    if not (isinstance(stored_inner, list) and stored_inner):
                        return
                    opts_inner = [
                        f"{p.get('nombre','')} — {p.get('ubicacion','')} ({p.get('ip','')})"
                        for p in stored_inner
                    ]
                    sel_inner = str(st.session_state.get("_simple_printer_choice") or "")
                    idx_inner = opts_inner.index(sel_inner) if sel_inner in opts_inner else 0
                    st.session_state["_selected_printer_record"] = stored_inner[idx_inner]

                if "_simple_printer_choice" not in st.session_state:
                    st.session_state["_simple_printer_choice"] = options_simple[0]
                    st.session_state["_selected_printer_record"] = stored_simple[0]

                st.selectbox(
                    "Impresora",
                    options=options_simple,
                    index=options_simple.index(st.session_state["_simple_printer_choice"])
                    if st.session_state["_simple_printer_choice"] in options_simple
                    else 0,
                    key="_simple_printer_choice",
                    on_change=_on_simple_printer_choice_change,
                )

                selected = st.session_state.get("_selected_printer_record")
                sel_ip = str(selected.get("ip") or "").strip() if isinstance(selected, dict) else ""
                sel_name = str(selected.get("nombre") or "").strip() if isinstance(selected, dict) else ""
                sel_loc = str(selected.get("ubicacion") or "").strip() if isinstance(selected, dict) else ""

                st.caption(f"Seleccionada: {sel_name} | {sel_loc} | {sel_ip}")

                allow_simple = st.checkbox(
                    "Permitir conectar impresoras en este PC",
                    value=True,
                    key="allow_local_printer_connect_simple",
                )
                do_simple_connect = st.button(
                    "🖨️ Conectar automáticamente",
                    type="primary",
                    use_container_width=True,
                    key="simple_connect_btn",
                    disabled=not allow_simple,
                )
                if do_simple_connect:
                    if not sel_ip:
                        st.error("La impresora seleccionada no tiene IP.")
                    else:
                        drivers_dir = os.getenv(
                            "AI_SUPPORT_PRINTER_DRIVERS_DIR",
                            os.path.join(os.getcwd(), "printer_drivers"),
                        )
                        selected_info = f"[IMPRESORA_SELECCIONADA] nombre={sel_name} | ip={sel_ip} | ubicacion={sel_loc}"
                        with st.spinner(f"Conectando {sel_ip}..."):
                            try:
                                log = auto_connect_printer_ip(
                                    ip=sel_ip,
                                    user_text=selected_info,
                                    drivers_dir=drivers_dir,
                                    printer_display_name=sel_name or None,
                                )
                                st.session_state["_printer_auto_log"] = log.details
                                if log.ok:
                                    st.success("Conexión OK (o reintentos completados).")
                                else:
                                    st.warning("No se pudo conectar automáticamente.")
                                st.code(log.details, language="text")
                            except Exception as e:
                                st.error(f"Error en conexión automática: {e}")

        # --- Acciones locales (solo para impresoras) ---
        agente_estimado = None
        if "orquestador" in st.session_state and consulta.strip():
            try:
                agente_estimado = st.session_state.orquestador.determinar_agente_principal(consulta)
            except Exception:
                agente_estimado = None

        printer_diag_for_prompt = ""
        if agente_estimado == "impresoras":
            with st.expander("🖨️ Diagnóstico local (PowerShell)", expanded=False):
                st.caption(
                    "Esto ejecuta comandos locales en ESTE PC (Get-Printer, Get-PrinterPort, Spooler, etc.). "
                    "Solo se ejecuta si das permiso explícito."
                )
                allow_local = st.checkbox(
                    "Permitir ejecutar diagnóstico local",
                    value=False,
                    key="allow_local_printer_diag",
                )

                auto_env = os.getenv("AI_SUPPORT_PRINTER_AUTOMATION_AUTO", "false").strip().lower() in {
                    "1",
                    "true",
                    "yes",
                    "y",
                    "on",
                }
                if auto_env:
                    st.info(
                        "Automatización de impresoras ACTIVA por entorno (AI_SUPPORT_PRINTER_AUTOMATION_AUTO). "
                        "El sistema puede intentar conectar/instalar drivers automáticamente cuando lo pidas en el chat."
                    )

                # Inventario MySQL (opcional)
                if mysql_enabled():
                    st.markdown("**Inventario impresoras (MySQL)**")
                    colinv1, colinv2 = st.columns([1, 2])
                    with colinv1:
                        load_inv = st.button(
                            "Recargar inventario",
                            use_container_width=True,
                        )
                    with colinv2:
                        st.caption("Requiere AI_SUPPORT_MYSQL_* en .env")

                    # Auto-carga (solo una vez por sesión) para reducir acciones manuales
                    if "_mysql_inv_loaded" not in st.session_state:
                        st.session_state["_mysql_inv_loaded"] = False
                    if "_mysql_inv_load_error" not in st.session_state:
                        st.session_state["_mysql_inv_load_error"] = ""

                    def _load_mysql_inventory() -> None:
                        try:
                            printers = fetch_printers_from_mysql()
                            st.session_state["_mysql_printers"] = [p.__dict__ for p in printers]
                            st.session_state["_mysql_inv_loaded"] = True
                            st.session_state["_mysql_inv_load_error"] = ""
                        except Exception as e:
                            st.session_state["_mysql_inv_loaded"] = True
                            st.session_state["_mysql_inv_load_error"] = str(e)

                    if not st.session_state.get("_mysql_inv_loaded"):
                        _load_mysql_inventory()

                    if load_inv:
                        _load_mysql_inventory()

                    stored = st.session_state.get("_mysql_printers")
                    err = str(st.session_state.get("_mysql_inv_load_error") or "")
                    if err and not stored:
                        st.error(f"No se pudo cargar inventario MySQL: {err}")
                    if isinstance(stored, list) and stored:
                        # Mostrar tabla compacta
                        st.dataframe(stored, use_container_width=True, hide_index=True)

                        def _on_mysql_printer_choice_change() -> None:
                            stored_inner = st.session_state.get("_mysql_printers")
                            if not (isinstance(stored_inner, list) and stored_inner):
                                return
                            options_inner = [
                                f"{p.get('nombre','')} — {p.get('ubicacion','')} ({p.get('ip','')})"
                                for p in stored_inner
                            ]
                            sel_inner = str(st.session_state.get("_mysql_printer_choice") or "")
                            idx_inner = options_inner.index(sel_inner) if sel_inner in options_inner else 0
                            chosen_inner = stored_inner[idx_inner]
                            st.session_state["_selected_printer_record"] = chosen_inner
                            # Autocompletar campos existentes
                            st.session_state["printer_ip_test"] = str(chosen_inner.get("ip") or "")
                            st.session_state["printer_ip_connect"] = str(chosen_inner.get("ip") or "")
                            st.session_state["printer_ip_name"] = str(chosen_inner.get("nombre") or "")

                        options = [
                            f"{p.get('nombre','')} — {p.get('ubicacion','')} ({p.get('ip','')})"
                            for p in stored
                        ]
                        if "_mysql_printer_choice" not in st.session_state:
                            st.session_state["_mysql_printer_choice"] = options[0]

                        # Inicializar selección/prefill una sola vez (antes de crear widgets dependientes).
                        if "_selected_printer_record" not in st.session_state:
                            _on_mysql_printer_choice_change()

                        st.selectbox(
                            "Selecciona una impresora",
                            options=options,
                            index=options.index(st.session_state["_mysql_printer_choice"])
                            if st.session_state["_mysql_printer_choice"] in options
                            else 0,
                            key="_mysql_printer_choice",
                            on_change=_on_mysql_printer_choice_change,
                        )

                ip_test = st.text_input(
                    "IP de impresora (opcional, para Test-NetConnection)",
                    value="",
                    key="printer_ip_test",
                    disabled=not allow_local,
                )

                colp1, colp2 = st.columns(2)
                with colp1:
                    run_diag = st.button("Ejecutar diagnóstico", disabled=not allow_local, use_container_width=True)
                with colp2:
                    run_spooler = st.button("Reiniciar Spooler", disabled=not allow_local, use_container_width=True)

                if run_spooler and allow_local:
                    try:
                        res = restart_spooler()
                        st.code((res.stdout or res.stderr).strip(), language="text")
                    except Exception as e:
                        st.error(f"No se pudo reiniciar Spooler: {e}")

                if run_diag and allow_local:
                    try:
                        diag = collect_printer_diagnostics(test_ip=ip_test.strip() or None)
                        st.session_state["_printer_diag_prompt"] = format_diagnostics_for_prompt(diag)
                        st.code(st.session_state["_printer_diag_prompt"], language="text")
                    except Exception as e:
                        st.error(f"No se pudo ejecutar diagnóstico: {e}")

                st.markdown("**Conectar impresora compartida (UNC)**")
                unc = st.text_input(
                    "Ruta (ej: \\\\SERVIDOR\\IMPRESORA)",
                    value="",
                    key="printer_unc",
                    disabled=not allow_local,
                )
                printer_default_name = st.text_input(
                    "Nombre para dejar como predeterminada (opcional)",
                    value="",
                    key="printer_default_name",
                    disabled=not allow_local,
                )
                colc1, colc2 = st.columns(2)
                with colc1:
                    do_add = st.button("Agregar impresora", disabled=not allow_local, use_container_width=True)
                with colc2:
                    do_default = st.button(
                        "Hacer predeterminada",
                        disabled=(not allow_local) or (not bool(printer_default_name.strip())),
                        use_container_width=True,
                    )

                if do_add and allow_local:
                    try:
                        res = add_shared_printer(unc.strip())
                        st.success("Comando ejecutado.")
                        st.code((res.stdout or res.stderr).strip(), language="text")
                    except Exception as e:
                        st.error(f"No se pudo agregar la impresora: {e}")

                if do_default and allow_local and printer_default_name.strip():
                    try:
                        res = set_default_printer(printer_default_name.strip())
                        st.success("Comando ejecutado.")
                        st.code((res.stdout or res.stderr).strip(), language="text")
                    except Exception as e:
                        st.error(f"No se pudo configurar como predeterminada: {e}")

                st.divider()
                st.markdown("**Conectar impresora por IP (TCP/IP)**")
                ip_connect = st.text_input(
                    "IP (ej: 172.17.87.206)",
                    value="",
                    key="printer_ip_connect",
                    disabled=not allow_local,
                )
                printer_ip_name = st.text_input(
                    "Nombre (opcional)",
                    value="",
                    key="printer_ip_name",
                    disabled=not allow_local,
                )
                driver_name = st.text_input(
                    "Driver (opcional, ej: Microsoft IPP Class Driver)",
                    value="",
                    key="printer_ip_driver",
                    disabled=not allow_local,
                )
                colip1, colip2 = st.columns(2)
                with colip1:
                    do_connect_ip = st.button(
                        "Conectar por IP",
                        disabled=(not allow_local) or (not bool(ip_connect.strip())),
                        use_container_width=True,
                    )
                with colip2:
                    do_list_drivers = st.button(
                        "Listar drivers",
                        disabled=not allow_local,
                        use_container_width=True,
                    )

                st.markdown("**Imprimir página de prueba**")
                selected = st.session_state.get("_selected_printer_record")
                selected_name = ""
                if isinstance(selected, dict):
                    selected_name = str(selected.get("nombre") or "").strip()

                test_printer_name = st.text_input(
                    "Nombre de impresora (Windows)",
                    value=selected_name or (printer_ip_name.strip() if isinstance(printer_ip_name, str) else ""),
                    key="printer_test_page_name",
                    disabled=not allow_local,
                )
                do_test_page = st.button(
                    "Imprimir página de prueba",
                    disabled=(not allow_local) or (not bool(str(test_printer_name).strip())),
                    use_container_width=True,
                )

                if do_test_page and allow_local and str(test_printer_name).strip():
                    try:
                        res = print_test_page(str(test_printer_name).strip())
                        st.success("Comando ejecutado.")
                        st.code((res.stdout or res.stderr).strip(), language="text")
                    except Exception as e:
                        st.error(f"No se pudo imprimir la página de prueba: {e}")

                if do_list_drivers and allow_local:
                    try:
                        res = list_printer_drivers()
                        st.code((res.stdout or res.stderr).strip(), language="text")
                    except Exception as e:
                        st.error(f"No se pudieron listar drivers: {e}")

                if do_connect_ip and allow_local and ip_connect.strip():
                    try:
                        res = connect_printer_ip(
                            ip_connect.strip(),
                            printer_name=printer_ip_name.strip() or None,
                            driver_name=driver_name.strip() or None,
                        )
                        st.success("Comando ejecutado.")
                        st.code((res.stdout or res.stderr).strip(), language="text")
                    except Exception as e:
                        st.error(
                            "No se pudo conectar por IP. Suele requerir el driver exacto del fabricante. "
                            f"Detalle: {e}"
                        )

            printer_diag_for_prompt = str(st.session_state.get("_printer_diag_prompt") or "")

        forbidden_keywords = [
            "hackear",
            "hack",
            "sql injection",
            "inyección sql",
            "bypass",
            "exploit",
            "ataque",
            "crackear",
            "phishing",
            "obtener contraseña",
            "password leak",
            "robar datos",
            "malware",
            "virus",
            "script malicioso",
            "evadir seguridad",
            "eludir seguridad",
            "saltarse seguridad",
            "acceder sin permiso",
            "acceso no autorizado",
            "piratear",
            "piratería",
            "rootkit",
            "keylogger",
            "payload",
            "reverse shell",
            "escalar privilegios",
            "privilege escalation",
        ]

        def contiene_peligro(texto: str) -> bool:
            texto_l = texto.lower()
            return any(palabra in texto_l for palabra in forbidden_keywords)

        # Estado de generación
        if "_gen_active" not in st.session_state:
            st.session_state["_gen_active"] = False
        if "_gen_queue" not in st.session_state:
            st.session_state["_gen_queue"] = None
        if "_gen_result" not in st.session_state:
            st.session_state["_gen_result"] = None
        if "_gen_error" not in st.session_state:
            st.session_state["_gen_error"] = None
        if "_gen_text" not in st.session_state:
            st.session_state["_gen_text"] = ""
        if "_gen_prompt" not in st.session_state:
            st.session_state["_gen_prompt"] = ""
        if "_gen_stop_event" not in st.session_state:
            st.session_state["_gen_stop_event"] = None

        orquestador_ready = "orquestador" in st.session_state and st.session_state.get("orquestador") is not None

        enviar = st.button(
            "▶️ Enviar",
            type="primary",
            key="enviar_principal",
            disabled=bool(st.session_state.get("_gen_active")) or (not orquestador_ready),
        )

        if not orquestador_ready:
            st.caption("Configura un proveedor y presiona 'Aplicar' para inicializar el sistema.")

        def _start_generation(prompt: str) -> None:
            # Capturar el orquestador en el hilo principal (no usar session_state dentro del hilo)
            orq = st.session_state.get("orquestador")
            if orq is None:
                st.session_state["_gen_error"] = "Sistema no inicializado: falta orquestador (presiona 'Aplicar' en el sidebar)."
                st.session_state["_gen_active"] = False
                return

            st.session_state["_gen_active"] = True
            st.session_state["_gen_result"] = None
            st.session_state["_gen_error"] = None
            st.session_state["_gen_text"] = ""
            st.session_state["_gen_prompt"] = prompt

            q: queue.Queue = queue.Queue()
            st.session_state["_gen_queue"] = q

            stop_event = threading.Event()
            st.session_state["_gen_stop_event"] = stop_event

            def _worker() -> None:
                def _stream_to_queue(texto: str) -> None:
                    q.put({"type": "text", "text": texto})

                def _should_stop() -> bool:
                    return stop_event.is_set()

                try:
                    resultado = orq.procesar_consulta_compleja(
                        prompt,
                        stream_callback=_stream_to_queue,
                        should_stop=_should_stop,
                    )
                    q.put({"type": "final", "result": resultado})
                except Exception as e:
                    q.put({"type": "error", "error": str(e), "error_obj": e})

            t = threading.Thread(target=_worker, daemon=True)
            t.start()

        # --- Flujo chat-first: cuando el usuario pide "conectar impresora" sin IP,
        # mostrar selector del inventario y ejecutar automatización al confirmar.
        if "_pending_printer_connect" not in st.session_state:
            st.session_state["_pending_printer_connect"] = False
        if "_pending_printer_connect_user_text" not in st.session_state:
            st.session_state["_pending_printer_connect_user_text"] = ""

        auto_enabled_env = os.getenv("AI_SUPPORT_PRINTER_AUTOMATION_AUTO", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }

        if (
            auto_enabled_env
            and agente_estimado == "impresoras"
            and bool(st.session_state.get("_pending_printer_connect"))
        ):
            stored = st.session_state.get("_mysql_printers")
            if not (isinstance(stored, list) and stored and mysql_enabled()):
                st.warning(
                    "Para elegir una impresora necesito el inventario MySQL cargado. "
                    "Abre 'Diagnóstico local (PowerShell)' → 'Inventario impresoras (MySQL)' para cargarlo, "
                    "o escribe la IP en el chat."
                )
            else:
                st.info("Selecciona una impresora del inventario para conectar automáticamente.")
                options = [
                    f"{p.get('nombre','')} — {p.get('ubicacion','')} ({p.get('ip','')})"
                    for p in stored
                ]
                sel = st.selectbox(
                    "Impresora",
                    options=options,
                    index=0,
                    key="_pending_printer_connect_choice",
                )
                idx = options.index(sel) if sel in options else 0
                chosen = stored[idx]
                colpc1, colpc2 = st.columns([1, 1])
                with colpc1:
                    do_connect_selected = st.button(
                        "🖨️ Conectar seleccionada",
                        type="primary",
                        use_container_width=True,
                        key="_pending_printer_connect_run",
                        disabled=bool(st.session_state.get("_gen_active")),
                    )
                with colpc2:
                    do_cancel = st.button(
                        "Cancelar",
                        use_container_width=True,
                        key="_pending_printer_connect_cancel",
                        disabled=bool(st.session_state.get("_gen_active")),
                    )

                if do_cancel:
                    st.session_state["_pending_printer_connect"] = False
                    st.session_state["_pending_printer_connect_user_text"] = ""
                    st.rerun()

                if do_connect_selected:
                    selected_ip = str(chosen.get("ip") or "").strip()
                    selected_name = str(chosen.get("nombre") or "").strip()
                    depto = str(chosen.get("nombre_departamento") or "").strip()
                    ubi = str(chosen.get("ubicacion") or "").strip()
                    selected_info = (
                        "[IMPRESORA_SELECCIONADA] "
                        f"nombre={selected_name} | ip={selected_ip} | departamento={depto} | ubicacion={ubi}"
                    )

                    if not selected_ip:
                        st.error("La impresora seleccionada no tiene IP.")
                    else:
                        base_user_text = str(st.session_state.get("_pending_printer_connect_user_text") or "")
                        drivers_dir = os.getenv(
                            "AI_SUPPORT_PRINTER_DRIVERS_DIR",
                            os.path.join(os.getcwd(), "printer_drivers"),
                        )
                        with st.spinner(f"Intentando conectar impresora {selected_ip} automáticamente..."):
                            try:
                                log = auto_connect_printer_ip(
                                    ip=selected_ip,
                                    user_text=(base_user_text + "\n" + selected_info).strip(),
                                    drivers_dir=drivers_dir,
                                    printer_display_name=selected_name or None,
                                )
                                st.session_state["_printer_auto_log"] = log.details
                                prompt = (base_user_text or "Conectar impresora").strip()
                                prompt = f"{prompt}\n\n{selected_info}\n{log.details}".strip()
                            except Exception as e:
                                st.session_state["_printer_auto_log"] = f"[AUTO_PRINTER] Error inesperado: {e}"
                                prompt = (base_user_text or "Conectar impresora").strip()
                                prompt = f"{prompt}\n\n{selected_info}\n{st.session_state['_printer_auto_log']}".strip()

                        st.session_state["_pending_printer_connect"] = False
                        st.session_state["_pending_printer_connect_user_text"] = ""
                        _start_generation(prompt)
                        st.rerun()

        if enviar and consulta.strip():
            cooldown_until = float(st.session_state.get("_cooldown_until", 0.0) or 0.0)
            now = time.time()
            if cooldown_until > now:
                remaining = int(cooldown_until - now)
                st.warning(f"Demasiadas solicitudes recientemente. Espera {remaining}s y vuelve a intentar.")
                st.stop()

            if contiene_peligro(consulta):
                st.error(
                    "❌ Por motivos de seguridad y ética, no está permitido realizar preguntas relacionadas con hacking, "
                    "inyección SQL, ataques, acceso no autorizado o actividades peligrosas. Por favor, formula una consulta apropiada."
                )
            else:
                prompt = consulta
                if printer_diag_for_prompt:
                    prompt = f"{consulta}\n\n{printer_diag_for_prompt}"

                # Automatización: si se pide conectar impresora por IP, intentar flujo automático.
                # Para evitar ejecuciones no deseadas, solo corre si AI_SUPPORT_PRINTER_AUTOMATION_AUTO=true.
                auto_enabled = os.getenv("AI_SUPPORT_PRINTER_AUTOMATION_AUTO", "false").strip().lower() in {
                    "1",
                    "true",
                    "yes",
                    "y",
                    "on",
                }
                if auto_enabled and agente_estimado == "impresoras":
                    ip = _extract_ipv4(consulta)
                    wants_connect = any(w in consulta.lower() for w in ["conectar", "agregar", "instalar", "añadir"])

                    selected = st.session_state.get("_selected_printer_record")
                    selected_ip = None
                    selected_info = ""
                    if isinstance(selected, dict):
                        selected_ip = str(selected.get("ip") or "").strip() or None
                        nombre = str(selected.get("nombre") or "").strip()
                        depto = str(selected.get("nombre_departamento") or "").strip()
                        ubi = str(selected.get("ubicacion") or "").strip()
                        if nombre or depto or ubi or selected_ip:
                            selected_info = (
                                "[IMPRESORA_SELECCIONADA] "
                                f"nombre={nombre} | ip={selected_ip or ''} | departamento={depto} | ubicacion={ubi}"
                            )

                    if (not ip) and selected_ip:
                        ip = selected_ip

                    # Si se pidió conectar pero NO hay IP ni selección previa, pedir selección del inventario.
                    if wants_connect and (not ip) and mysql_enabled():
                        stored = st.session_state.get("_mysql_printers")
                        if isinstance(stored, list) and stored:
                            st.session_state["_pending_printer_connect"] = True
                            st.session_state["_pending_printer_connect_user_text"] = consulta
                            st.rerun()

                    if ip and wants_connect:
                        drivers_dir = os.getenv(
                            "AI_SUPPORT_PRINTER_DRIVERS_DIR",
                            os.path.join(os.getcwd(), "printer_drivers"),
                        )
                        with st.spinner(f"Intentando conectar impresora {ip} automáticamente..."):
                            try:
                                log = auto_connect_printer_ip(
                                    ip=ip,
                                    user_text=(consulta + ("\n" + selected_info if selected_info else "")),
                                    drivers_dir=drivers_dir,
                                    printer_display_name=(str(selected.get("nombre") or "").strip() if isinstance(selected, dict) else None) or None,
                                )
                                st.session_state["_printer_auto_log"] = log.details
                                # Adjuntar al prompt para que el agente explique lo que pasó.
                                if selected_info:
                                    prompt = f"{prompt}\n\n{selected_info}\n{log.details}"
                                else:
                                    prompt = f"{prompt}\n\n{log.details}"
                            except Exception as e:
                                st.session_state["_printer_auto_log"] = f"[AUTO_PRINTER] Error inesperado: {e}"
                                prompt = f"{prompt}\n\n{st.session_state['_printer_auto_log']}"
                _start_generation(prompt)
                st.rerun()


        # Área única de respuesta (estilo ChatGPT): se va llenando con streaming.
        st.markdown("### 💬 Respuesta")
        respuesta_placeholder = st.empty()

        # Render/actualización mientras se genera
        if st.session_state.get("_gen_active"):
            col_stop, col_hint = st.columns([1, 3])
            with col_stop:
                if st.button("⏹️ Stop", key="stop_generation"):
                    ev = st.session_state.get("_gen_stop_event")
                    if ev is not None:
                        ev.set()
            with col_hint:
                st.caption("Generando respuesta... (puedes detener con Stop)")

            q = st.session_state.get("_gen_queue")

            # Consumir mensajes de la cola (no bloqueante)
            if q is not None:
                try:
                    while True:
                        msg = q.get_nowait()
                        if msg.get("type") == "text":
                            st.session_state["_gen_text"] = msg.get("text", "")
                        elif msg.get("type") == "final":
                            final_result = msg.get("result")
                            st.session_state["_gen_result"] = final_result
                            # Asegurar que el texto final quede en el mismo bloque (sin duplicar).
                            if isinstance(final_result, dict) and isinstance(final_result.get("respuesta"), str):
                                st.session_state["_gen_text"] = final_result.get("respuesta") or st.session_state.get(
                                    "_gen_text", ""
                                )
                            st.session_state["_gen_active"] = False
                        elif msg.get("type") == "error":
                            st.session_state["_gen_error"] = msg.get("error")
                            st.session_state["_gen_error_obj"] = msg.get("error_obj")
                            st.session_state["_gen_active"] = False
                except queue.Empty:
                    pass

            # Mostrar texto parcial (o final) en un único bloque
            respuesta_placeholder.markdown(st.session_state.get("_gen_text", ""))

            # Mientras sigue activo, refrescar para permitir Stop y ver streaming
            if st.session_state.get("_gen_active"):
                time.sleep(0.2)
                st.rerun()

        # Cuando no está activo, igual renderizamos el último texto en el mismo bloque.
        if not st.session_state.get("_gen_active"):
            respuesta_placeholder.markdown(st.session_state.get("_gen_text", ""))

        # Si terminó, render normal del resultado (o error)
        if (not st.session_state.get("_gen_active")) and st.session_state.get("_gen_result"):
            resultado = st.session_state.get("_gen_result")

            # limpiar stop event
            st.session_state["_gen_stop_event"] = None

            with st.expander("🔧 Detalles de ejecución", expanded=False):
                st.info(f"🎯 **Agente Principal**: {resultado['agente_principal']}")
                st.info(f"👥 **Agentes Involucrados**: {', '.join(resultado['agentes_involucrados'])}")
                st.info(f"⏱️ **Tiempo**: {resultado['tiempo_respuesta']:.2f}s")

            if resultado.get("stopped"):
                st.warning("Generación detenida: se muestra respuesta parcial.")

            if "colaboracion" in resultado:
                with st.expander("🔗 Colaboración Multi-Agente"):
                    st.markdown(resultado["colaboracion"])

            # La respuesta ya se muestra arriba en el bloque único (evita duplicado).

            if resultado.get("faiss_usado"):
                with st.expander("🔍 FAISS RAG Utilizado"):
                    st.success("✅ Búsqueda semántica FAISS activa")
                    if resultado.get("contexto_faiss"):
                        st.markdown("**Contexto encontrado:**")
                        st.text(resultado["contexto_faiss"])
                    else:
                        st.info("Contexto FAISS disponible pero no mostrado")

            if "memoria_usada" in resultado:
                with st.expander("🧠 Memoria Utilizada"):
                    memoria_info = resultado["memoria_usada"]
                    col_mem1, col_mem2, col_mem3 = st.columns(3)

                    with col_mem1:
                        st.metric("Buffer", memoria_info.get("buffer", 0))
                        st.caption("Historial completo")
                    with col_mem2:
                        st.metric("Summary", memoria_info.get("summary", 0))
                        st.caption("Resumen inteligente")
                    with col_mem3:
                        st.metric("Window", memoria_info.get("window", 0))
                        st.caption("Últimas interacciones")

                    col_mem4, col_mem5 = st.columns(2)
                    with col_mem4:
                        st.metric("Entities", memoria_info.get("entities", 0))
                        st.caption("Entidades recordadas")
                    with col_mem5:
                        st.metric("Vector", memoria_info.get("vector", 0))
                        st.caption("Memoria a largo plazo")

        if (not st.session_state.get("_gen_active")) and st.session_state.get("_gen_error"):
            err_str = st.session_state.get("_gen_error") or "(error)"
            err_obj = st.session_state.get("_gen_error_obj")

            # limpiar stop event
            st.session_state["_gen_stop_event"] = None

            if err_obj is not None and _is_rate_limit_error(err_obj):
                st.session_state["_cooldown_until"] = time.time() + 120
                st.error(
                    "El proveedor devolvió 'Too many requests' (límite de solicitudes). "
                    "Espera ~2 minutos y reintenta, o cambia a `LM Studio (local)` para evitar límites."
                )
            elif err_obj is not None and _is_github_no_access_error(err_obj):
                st.error(
                    "Tu token no tiene acceso al modelo seleccionado en GitHub Models. "
                    "Cambia el `Modelo LLM` por uno permitido para tu cuenta, o usa `LM Studio (local)` en el sidebar."
                )
            else:
                st.error(f"Error al generar respuesta: {err_str}")


if __name__ == "__main__":
    main()
