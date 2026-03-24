from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ai_support.agents.specialized_agent import AgenteEspecializado
from ai_support.core.config import EmbeddingsProviderConfig, LLMProviderConfig
from ai_support.core.tools import HerramientaSoporte


class OrquestadorMultiagente:
    """Orquestador determinista de agentes especializados en áreas FCFM (Facultad de Ciencias Físicas y Matemáticas).
    
    Gestiona 15 agentes, uno por cada área administrativa/académica.
    El enrutamiento es determinista: basado en palabras clave que coinciden exactamente.
    """

    # Mapeo área -> (nombre agente, especialidad, emoji)
    AREAS_MAPA = {
        "tesoreria": ("💰 Agente Tesorería", "procedimientos y tareas de tesorería, presupuestos, gastos"),
        "arquitectura": ("🏗️ Agente Arquitectura", "procedimientos de arquitectura, diseño, proyectos editoriales"),
        "infraestructura": ("🏢 Agente Infraestructura", "procedimientos de infraestructura, mantenimiento, edificios"),
        "proyectos": ("📋 Agente Proyectos", "procedimientos de proyectos, becas, investigación"),
        "atencion_alumnos": ("👥 Agente Atención Alumnos", "procedimientos de atención a estudiantes, inscripción, tutorías"),
        "postgrado": ("🎓 Agente Postgrado", "procedimientos de postgrado, diplomados, educación continua"),
        "sustentabilidad": ("🌱 Agente Sustentabilidad", "procedimientos de sustentabilidad, sostenibilidad, responsabilidad social"),
        "comunicaciones": ("📢 Agente Comunicaciones", "procedimientos de comunicaciones, prensa, difusión"),
        "vinculacion": ("🌍 Agente Vinculación", "procedimientos de vinculación externa, relaciones internacionales"),
        "rrhh": ("👔 Agente RRHH", "procedimientos de recursos humanos, contratación, adquisiciones, administración"),
        "contabilidad": ("📊 Agente Contabilidad", "procedimientos contables, registros, auditoría, estados financieros"),
        "direccion_economica": ("💵 Agente Dir. Económica", "procedimientos de dirección económica, análisis financiero"),
        "direccion_academica": ("📚 Agente Dir. Académica", "procedimientos académicos, currícula, planes de estudio"),
        "diversidad": ("🌈 Agente Diversidad", "procedimientos de diversidad, género, inclusión, equidad"),
        "decanato": ("🏛️ Agente Decanato", "procedimientos del decanato, normas facultad, administración general"),
    }

    def __init__(
        self,
        llm_config: LLMProviderConfig,
        embeddings_config: EmbeddingsProviderConfig,
        user_id: Optional[str] = None,
        allowed_area_ids: Optional[List[str]] = None,
    ):
        self.user_id = user_id
        self.llm_config = llm_config
        self.embeddings_config = embeddings_config
        self.agentes: Dict[str, AgenteEspecializado] = {}

        self.herramientas = HerramientaSoporte()
        self.comunicacion_agentes: List[Dict[str, Any]] = []

        if allowed_area_ids:
            normalized = [a for a in allowed_area_ids if a in self.AREAS_MAPA]
            self.allowed_area_ids: set[str] = set(normalized)
        else:
            self.allowed_area_ids = set(self.AREAS_MAPA.keys())

        self.metricas_globales: Dict[str, Any] = {
            "total_consultas": 0,
            "agentes_involucrados": {},
            "colaboraciones": 0,
            "institucion": "FCFM - Facultad de Ciencias Físicas y Matemáticas",
        }

    def _build_agent(self, area_id: str) -> AgenteEspecializado:
        nombre_agente, especialidad = self.AREAS_MAPA[area_id]
        return AgenteEspecializado(
            nombre=nombre_agente,
            especialidad=especialidad,
            llm_config=self.llm_config,
            embeddings_config=self.embeddings_config,
            user_id=self.user_id,
        )

    def get_or_create_agent(self, area_id: str) -> AgenteEspecializado:
        if area_id not in self.AREAS_MAPA:
            raise ValueError(f"Área no soportada: {area_id}")
        if area_id not in self.allowed_area_ids:
            raise ValueError(f"Área fuera de alcance para este usuario: {area_id}")
        if area_id not in self.agentes:
            self.agentes[area_id] = self._build_agent(area_id)
        return self.agentes[area_id]

    def initialize_all_allowed_agents(self) -> Dict[str, AgenteEspecializado]:
        for area_id in sorted(self.allowed_area_ids):
            self.get_or_create_agent(area_id)
        return self.agentes

    def get_available_agent_ids(self) -> List[str]:
        return sorted(self.allowed_area_ids)

    def get_initialized_agents(self) -> Dict[str, AgenteEspecializado]:
        return dict(self.agentes)

    def determinar_agente_principal(self, consulta: str) -> str:
        """Enrutamiento DETERMINISTA: analiza la consulta y devuelve el área (agente) responsable.
        
        Sin LLM, sin aleatoriedad. Basado 100% en palabras clave en herramientas.
        """
        analisis = self.herramientas.analizar_problema(consulta)
        categoria = analisis.get("categoria", "decanato")
        if categoria in self.allowed_area_ids:
            return categoria

        if self.allowed_area_ids:
            # Fallback determinista dentro del alcance permitido para el usuario.
            return sorted(self.allowed_area_ids)[0]

        return categoria if categoria in self.AREAS_MAPA else "decanato"

    def procesar_consulta_compleja(
        self,
        consulta: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """Orquesta la consulta: agente principal + colaboradores si es necesario."""
        self.metricas_globales["total_consultas"] += 1

        agente_principal = self.determinar_agente_principal(consulta)

        # ── Búsqueda en base de conocimiento (PDFs de procedimientos subidos) ────────
        contexto_kb: Optional[Dict[str, Any]] = None
        kb_used = False
        kb_preview = ""
        try:
            from ai_support.core.knowledge_base import get_kb_manager
            kb = get_kb_manager()
            agente_obj = self.get_or_create_agent(agente_principal)
            embeddings = getattr(agente_obj, "embeddings", None)
            
            # Buscar en el área específica primero (si existe), luego en todas
            area_context = kb.get_area_context(agente_principal, consulta, k=4, embeddings=embeddings)
            if not area_context:
                # Fallback: búsqueda global
                kb_text = kb.get_full_context_for_query(consulta, k=4, embeddings=embeddings)
            else:
                kb_text = area_context
                
            if kb_text:
                kb_text_limited = kb_text[:6000] + ("\n[...contenido truncado...]" if len(kb_text) > 6000 else "")
                contexto_kb = {"kb_context": kb_text_limited}
                kb_used = True
                kb_preview = kb_text[:300]
        except Exception as kb_err:
            print(f"⚠️ KB search error (no interrumpe): {kb_err}")

        resultado = self.get_or_create_agent(agente_principal).procesar_consulta(
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
        """Evalúa si la consulta requiere colaboración entre múltiples áreas FCFM.
        
        DETERMINISTA: solo colabora si:
        1. Menciona explícitamente múltiples áreas
        2. Contiene palabras indicadoras de complejidad multi-área
        """
        if len(self.allowed_area_ids) <= 1:
            return False

        consulta_lower = consulta.lower()

        palabras_multiple = [
            "y también",
            "además",
            "también necesito",
            "complejo",
            "varios procedimientos",
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
            "coordinación",
            "articulación",
        ]

        # Contar áreas distintas mencionadas
        areas_detectadas: set[str] = set()
        for area, palabras_clave in HerramientaSoporte.AREAS_FCFM.items():
            if area not in self.allowed_area_ids:
                continue
            for palabra in palabras_clave:
                if palabra in consulta_lower:
                    areas_detectadas.add(area)
                    break  # Ya detectamos esta área

        # Si hay 2+ áreas explícitamente mencionadas, colaboración obligatoria
        if len(areas_detectadas) > 1:
            return True

        # Si hay palabras indicadoras de multi-complejidad
        if any(palabra in consulta_lower for palabra in palabras_multiple):
            return True

        return False

    def _identificar_colaboradores(self, consulta: str, agente_principal: str) -> List[str]:
        """Identifica qué otros agentes deben colaborar (máx. 2 adicionales)."""
        colaboradores: List[str] = []
        consulta_lower = consulta.lower()

        # Revisamos cada área para ver si debe colaborar
        for area_id, palabras_clave in HerramientaSoporte.AREAS_FCFM.items():
            if area_id != agente_principal and area_id in self.allowed_area_ids:
                if any(palabra in consulta_lower for palabra in palabras_clave):
                    colaboradores.append(area_id)
                    if len(colaboradores) >= 2:
                        break

        # Si no hay colaboradores identificados pero la consulta es compleja, 
        # el decanato puede colaborar como fallback
        if not colaboradores and agente_principal != "decanato" and "decanato" in self.allowed_area_ids:
            colaboradores.append("decanato")

        return colaboradores[:2]

    def _obtener_contexto_colaborativo(self, colaboradores: List[str], consulta: str) -> str:
        """Obtiene perspectivas de agentes colaboradores."""
        contexto_completo: List[str] = []

        for agente_id in colaboradores:
            if agente_id in self.allowed_area_ids:
                agente = self.get_or_create_agent(agente_id)
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

