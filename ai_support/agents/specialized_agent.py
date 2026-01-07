import time
from typing import Any, Callable, Dict, List, Optional

import os

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from ai_support.core.memory import SistemaMemoriaAvanzada
from ai_support.core.config import EmbeddingsProviderConfig, LLMProviderConfig


_FAISS_MATERIAL_ERROR_SEEN: set[str] = set()


class AgenteEspecializado:
    """Agente individual especializado en un área de soporte."""

    def __init__(
        self,
        nombre: str,
        especialidad: str,
        llm_config: Optional[LLMProviderConfig] = None,
        embeddings_config: Optional[EmbeddingsProviderConfig] = None,
        user_id: Optional[str] = None,
    ):
        self.nombre = nombre
        self.especialidad = especialidad
        self.provider = llm_config.provider
        self.user_id = user_id

        # En GitHub Models, prompts grandes + historial suelen aumentar latencia.
        # Activamos un "modo rápido" por defecto para acercarse al comportamiento de smoke tests.
        self.github_fast_mode = False
        if llm_config.provider == "github":
            raw = os.getenv("AI_SUPPORT_GITHUB_FAST_MODE", "true")
            self.github_fast_mode = raw.strip().lower() in {"1", "true", "yes", "y", "on"}

        if llm_config is None:
            raise ValueError("llm_config es requerido")

        # LLM (GitHub Models o LM Studio - ambos compatibles OpenAI)
        # Nota: algunos modelos en GitHub Models rechazan cualquier valor de temperature que no sea el default.
        llm_kwargs: Dict[str, Any] = {
            "base_url": llm_config.base_url,
            "api_key": llm_config.api_key,
            "model": llm_config.model,
            "streaming": True,
        }
        if llm_config.provider != "github":
            llm_kwargs["temperature"] = 0.7

        self.llm = ChatOpenAI(**llm_kwargs)

        # Embeddings (opcional)
        self.embeddings = None
        if embeddings_config is not None and embeddings_config.provider != "none":
            try:
                self.embeddings = OpenAIEmbeddings(
                    base_url=embeddings_config.base_url,
                    api_key=embeddings_config.api_key,
                    model=embeddings_config.model,
                )
            except Exception as e:
                print(f"⚠️ {self.nombre}: Embeddings no disponibles ({e}). Se desactiva RAG/VectorMemory.")
                self.embeddings = None

        self.memoria = SistemaMemoriaAvanzada(self.llm, self.embeddings, user_id=self.user_id)

        # Historial simple (compatibilidad)
        self.historial: List[Any] = []

        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

        self.vectorstore_rag = None

        self.metricas: Dict[str, Any] = {
            "consultas_atendidas": 0,
            "tiempo_promedio": 0,
            "problemas_resueltos": 0,
        }

        self.material_cargado = ""

    def cargar_material(self, contenido: str) -> None:
        """Carga material de conocimiento para el agente usando FAISS."""
        self.material_cargado = contenido

        if self.embeddings is None:
            # Sin embeddings, se usa material directo en prompt
            self.vectorstore_rag = None
            return

        try:
            doc = Document(page_content=contenido, metadata={"source": f"material_{self.especialidad}"})
            chunks = self.text_splitter.split_documents([doc])
            self.vectorstore_rag = FAISS.from_documents(chunks, self.embeddings)
            print(f"✓ {self.nombre}: Material cargado con FAISS ({len(chunks)} chunks)")
        except Exception as e:
            signature = f"{type(e).__name__}:{str(e)[:300]}"
            if signature not in _FAISS_MATERIAL_ERROR_SEEN:
                _FAISS_MATERIAL_ERROR_SEEN.add(signature)
                print(f"⚠️ Error cargando material FAISS para {self.nombre}: {e}")
            # Degradación controlada si embeddings no están disponibles o no hay acceso
            try:
                msg = str(e).lower()
                if "no_access" in msg or "403" in msg or "401" in msg:
                    self.embeddings = None
            except Exception:
                pass
            self.vectorstore_rag = None

    def buscar_contexto_faiss(self, consulta: str) -> str:
        """Busca contexto relevante usando FAISS."""
        if not self.vectorstore_rag:
            return ""

        try:
            docs = self.vectorstore_rag.similarity_search(consulta, k=3)
            return "\n\n".join([doc.page_content for doc in docs])
        except Exception as e:
            print(f"⚠️ Error en búsqueda FAISS para {self.nombre}: {e}")
            return ""

    def procesar_consulta(
        self,
        consulta: str,
        contexto: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """Procesa una consulta y devuelve respuesta."""
        inicio = time.time()

        contexto_memoria = self.memoria.obtener_contexto_completo()
        contexto_faiss = self.buscar_contexto_faiss(consulta)

        material_limit = 600 if self.github_fast_mode else 2000
        if self.github_fast_mode:
            memory_block = f"- Últimas interacciones: {self._formatear_memoria(contexto_memoria.get('window', []))}"
        else:
            memory_block = (
                f"- Resumen de conversaciones anteriores: {self._formatear_memoria(contexto_memoria.get('summary', []))}\n"
                f"- Entidades recordadas: {self._formatear_memoria(contexto_memoria.get('entities', []))}\n"
                f"- Últimas interacciones: {self._formatear_memoria(contexto_memoria.get('window', []))}\n"
                f"- Memoria vectorial: {self._formatear_memoria(contexto_memoria.get('vector', []))}"
            )

        system_prompt = f"""
Eres {self.nombre}, un agente especializado en {self.especialidad}.

Conocimiento del área (FAISS RAG):
{contexto_faiss if contexto_faiss else self.material_cargado[:material_limit]}

Contexto de memoria:
{memory_block}

Directrices:
1. Responde específicamente sobre {self.especialidad}
2. Proporciona soluciones prácticas y paso a paso
3. Si necesitas colaborar con otro agente, indícalo
4. Mantén un tono profesional y útil
5. Usa el contexto de memoria y FAISS para respuestas más personalizadas
6. Si no tienes información específica, indícalo claramente
"""

        messages: List[Any] = [SystemMessage(content=system_prompt)]

        history_n = 1 if self.github_fast_mode else 3
        for msg in self.historial[-history_n:]:
            messages.append(msg)

        consulta_completa = consulta
        if contexto:
            consulta_completa += f"\n\nContexto colaborativo: {contexto.get('info', '')}"

        messages.append(HumanMessage(content=consulta_completa))

        def _is_rate_limit_error(err: Exception) -> bool:
            msg = str(err).lower()
            return (
                "ratelimiterror" in msg
                or "too many requests" in msg
                or "error code: 429" in msg
                or "rate limit" in msg
            )

        respuesta = ""
        stopped = False

        # Importante: NO reintentar automáticamente en GitHub Models.
        # Si estamos rate-limited, reintentos empeoran el bloqueo. La UI aplica cooldown.
        max_retries = 0
        attempt = 0
        backoff_seconds = 0

        while True:
            try:
                for chunk in self.llm.stream(messages):
                    if should_stop is not None and should_stop():
                        stopped = True
                        break
                    delta = getattr(chunk, "content", "") or ""
                    if not delta:
                        continue
                    respuesta += delta
                    if stream_callback is not None:
                        # Enviar texto acumulado para render en vivo
                        stream_callback(respuesta)
                break
            except Exception as e:
                if attempt < max_retries and _is_rate_limit_error(e) and not respuesta:
                    time.sleep(backoff_seconds)
                    attempt += 1
                    continue
                raise

        # Guardar incluso si se detuvo (respuesta parcial)
        self.memoria.agregar_interaccion(consulta, respuesta)

        self.historial.append(HumanMessage(content=consulta))
        self.historial.append(AIMessage(content=respuesta))

        if len(self.historial) > 10:
            self.historial = self.historial[-10:]

        tiempo_respuesta = time.time() - inicio
        self.metricas["consultas_atendidas"] += 1
        self.metricas["tiempo_promedio"] = (
            (self.metricas["tiempo_promedio"] * (self.metricas["consultas_atendidas"] - 1) + tiempo_respuesta)
            / self.metricas["consultas_atendidas"]
        )
        self.metricas["problemas_resueltos"] += 1

        return {
            "agente": self.nombre,
            "respuesta": respuesta,
            "tiempo_respuesta": tiempo_respuesta,
            "categoria": self.especialidad,
            "faiss_usado": bool(contexto_faiss),
            "contexto_faiss": contexto_faiss[:200] if contexto_faiss else "",
            "stopped": stopped,
            "memoria_usada": {
                "buffer": len(contexto_memoria.get("buffer", [])),
                "summary": len(contexto_memoria.get("summary", [])),
                "window": len(contexto_memoria.get("window", [])),
                "entities": len(contexto_memoria.get("entities", [])),
                "vector": len(contexto_memoria.get("vector", [])),
            },
        }

    def _formatear_memoria(self, memoria_messages: List[Any]) -> str:
        if not memoria_messages:
            return "Ninguna información previa"

        formatted: List[str] = []
        for msg in memoria_messages[-3:]:
            if hasattr(msg, "content"):
                formatted.append(str(msg.content)[:200])

        return " | ".join(formatted) if formatted else "Ninguna información previa"

    def colaborar(self, info: str) -> str:
        return f"{self.nombre} ({self.especialidad}): {info}"
