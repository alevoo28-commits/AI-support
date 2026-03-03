from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ai_support.agents.specialized_agent import AgenteEspecializado
from ai_support.core.config import EmbeddingsProviderConfig, LLMProviderConfig
from ai_support.core.tools import HerramientaSoporte


class OrquestadorMultiagente:
    """Sistema que orquesta múltiples agentes especializados."""

    def __init__(
        self,
        llm_config: LLMProviderConfig,
        embeddings_config: EmbeddingsProviderConfig,
        user_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.agentes: Dict[str, AgenteEspecializado] = {
            "hardware": AgenteEspecializado(
                "🔧 Agente Hardware",
                "hardware y componentes físicos",
                llm_config=llm_config,
                embeddings_config=embeddings_config,
                user_id=user_id,
            ),
            "software": AgenteEspecializado(
                "💻 Agente Software",
                "aplicaciones y programas",
                llm_config=llm_config,
                embeddings_config=embeddings_config,
                user_id=user_id,
            ),
            "redes": AgenteEspecializado(
                "🌐 Agente Redes",
                "conectividad y redes informáticas",
                llm_config=llm_config,
                embeddings_config=embeddings_config,
                user_id=user_id,
            ),
            "seguridad": AgenteEspecializado(
                "🔒 Agente Seguridad",
                "seguridad informática y protección",
                llm_config=llm_config,
                embeddings_config=embeddings_config,
                user_id=user_id,
            ),
            "excel": AgenteEspecializado(
                "📊 Agente Excel",
                "Excel, hojas de cálculo y automatización",
                llm_config=llm_config,
                embeddings_config=embeddings_config,
                user_id=user_id,
            ),
            "impresoras": AgenteEspecializado(
                "🖨️ Agente Impresoras",
                "impresoras, colas de impresión y conexión (USB/red)",
                llm_config=llm_config,
                embeddings_config=embeddings_config,
                user_id=user_id,
            ),
            "general": AgenteEspecializado(
                "⚙️ Agente General",
                "soporte técnico general",
                llm_config=llm_config,
                embeddings_config=embeddings_config,
                user_id=user_id,
            ),
        }

        self.herramientas = HerramientaSoporte()
        self.comunicacion_agentes: List[Dict[str, Any]] = []

        self.metricas_globales: Dict[str, Any] = {
            "total_consultas": 0,
            "agentes_involucrados": {},
            "colaboraciones": 0,
        }

    def determinar_agente_principal(self, consulta: str) -> str:
        analisis = self.herramientas.analizar_problema(consulta)
        categoria = analisis.get("categoria", "general")
        return categoria if categoria in self.agentes else "general"

    def procesar_consulta_compleja(
        self,
        consulta: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        self.metricas_globales["total_consultas"] += 1

        agente_principal = self.determinar_agente_principal(consulta)

        # ── Búsqueda en base de conocimiento ────────────────────────────────
        contexto_kb: Optional[Dict[str, Any]] = None
        kb_used = False
        kb_preview = ""
        try:
            from ai_support.core.knowledge_base import get_kb_manager
            kb = get_kb_manager()
            agente_obj = self.agentes[agente_principal]
            embeddings = getattr(agente_obj, "embeddings", None)
            kb_text = kb.get_full_context_for_query(consulta, k=4, embeddings=embeddings)
            if kb_text:
                # Limitar a ~6000 caracteres para no saturar el contexto del LLM
                kb_text_limited = kb_text[:6000] + ("\n[...contenido truncado...]" if len(kb_text) > 6000 else "")
                contexto_kb = {"kb_context": kb_text_limited}
                kb_used = True
                kb_preview = kb_text[:300]
        except Exception as kb_err:
            print(f"⚠️ KB search error (no interrumpe): {kb_err}")

        resultado = self.agentes[agente_principal].procesar_consulta(
            consulta,
            contexto=contexto_kb,
            stream_callback=stream_callback,
            should_stop=should_stop,
        )
        resultado["agente_principal"] = agente_principal
        resultado["kb_usado"] = kb_used
        resultado["kb_preview"] = kb_preview

        necesita_colaboracion = self._evaluar_colaboracion(consulta)

        if necesita_colaboracion:
            agentes_colaboradores = self._identificar_colaboradores(consulta, agente_principal)
            contexto_colaboracion = self._obtener_contexto_colaborativo(agentes_colaboradores, consulta)

            resultado["colaboracion"] = contexto_colaboracion
            resultado["agentes_involucrados"] = [agente_principal] + agentes_colaboradores
            self.metricas_globales["colaboraciones"] += 1
        else:
            resultado["agentes_involucrados"] = [agente_principal]

        for agente in resultado["agentes_involucrados"]:
            self.metricas_globales["agentes_involucrados"][agente] = (
                self.metricas_globales["agentes_involucrados"].get(agente, 0) + 1
            )

        return resultado

    def _evaluar_colaboracion(self, consulta: str) -> bool:
        consulta_lower = consulta.lower()

        palabras_multiple = [
            "y también",
            "además",
            "también necesito",
            "complejo",
            "varios problemas",
            "y otro",
            "múltiples",
            "tanto",
            "como",
            "a la vez",
            "simultáneamente",
            "por otro lado",
            "aparte",
            "igualmente",
            "junto con",
        ]

        categorias_detectadas: List[str] = []
        if any(
            palabra in consulta_lower
            for palabra in ["ram", "memoria", "disco", "procesador", "cpu", "hardware", "componente", "equipo"]
        ):
            categorias_detectadas.append("hardware")
        if any(
            palabra in consulta_lower
            for palabra in ["programa", "software", "aplicación", "instalar", "actualizar", "ejecutar"]
        ):
            categorias_detectadas.append("software")
        if any(
            palabra in consulta_lower
            for palabra in ["wifi", "red", "internet", "conexión", "router", "ip", "ethernet"]
        ):
            categorias_detectadas.append("redes")
        if any(
            palabra in consulta_lower
            for palabra in ["virus", "seguridad", "contraseña", "hackeo", "malware", "antivirus", "firewall"]
        ):
            categorias_detectadas.append("seguridad")
        if any(
            palabra in consulta_lower
            for palabra in ["excel", "hoja de cálculo", "power query", "tabla dinámica", "buscarv", "vlookup", "#n/a", "macro", "vba"]
        ):
            categorias_detectadas.append("excel")

        if len(categorias_detectadas) > 1:
            return True

        if len(consulta) > 100:
            return True

        if any(palabra in consulta_lower for palabra in palabras_multiple):
            return True

        return False

    def _identificar_colaboradores(self, consulta: str, agente_principal: str) -> List[str]:
        colaboradores: List[str] = []
        consulta_lower = consulta.lower()

        if agente_principal != "hardware" and any(
            palabra in consulta_lower for palabra in ["ram", "memoria", "disco", "procesador", "cpu", "hardware", "componente"]
        ):
            colaboradores.append("hardware")

        if agente_principal != "software" and any(
            palabra in consulta_lower for palabra in ["programa", "software", "aplicación", "instalar", "actualizar"]
        ):
            colaboradores.append("software")

        if agente_principal != "redes" and any(
            palabra in consulta_lower for palabra in ["wifi", "red", "internet", "conexión", "router", "ip"]
        ):
            colaboradores.append("redes")

        if agente_principal != "seguridad" and any(
            palabra in consulta_lower for palabra in ["virus", "seguridad", "contraseña", "hackeo", "malware", "antivirus"]
        ):
            colaboradores.append("seguridad")

        if agente_principal != "excel" and any(
            palabra in consulta_lower for palabra in ["excel", "hoja de cálculo", "power query", "tabla dinámica", "buscarv", "vlookup", "macro", "vba", "#n/a"]
        ):
            colaboradores.append("excel")

        if not colaboradores and agente_principal != "general":
            colaboradores.append("general")

        return colaboradores[:2]

    def _obtener_contexto_colaborativo(self, colaboradores: List[str], consulta: str) -> str:
        contexto_completo: List[str] = []

        for agente_nombre in colaboradores:
            agente = self.agentes[agente_nombre]
            respuesta = agente.colaborar(f"Perspectiva sobre: {consulta[:100]}")
            contexto_completo.append(respuesta)

        self.comunicacion_agentes.append(
            {
                "timestamp": datetime.now(),
                "consulta": consulta[:100],
                "agentes": colaboradores,
            }
        )

        return "\n\n".join(contexto_completo)
