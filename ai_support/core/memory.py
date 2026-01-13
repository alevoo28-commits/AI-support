import os
from typing import Any, Dict, Optional

from langchain_classic.memory import (
    ConversationBufferMemory,
    ConversationBufferWindowMemory,
    ConversationEntityMemory,
    ConversationSummaryMemory,
    VectorStoreRetrieverMemory,
)
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from .user_memory_persistence import (
    UserMemoryPersistence,
    auto_save_user_memory,
    restore_user_memory_to_buffer,
)


_VECTORSTORE_INIT_ERROR_SEEN: set[str] = set()


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


class SistemaMemoriaAvanzada:
    """Sistema que integra múltiples tipos de memoria de LangChain.

    Nota: la persistencia por usuario (si `user_id` está definido) guarda *solo*
    el historial conversacional del buffer.
    """

    def __init__(self, llm, embeddings: Optional[object], user_id: Optional[str] = None):
        self.llm = llm
        self.embeddings = embeddings
        self.user_id = user_id
        self.persistence = UserMemoryPersistence() if user_id else None

        # Algunas memorias (Summary/Entity) generan llamadas adicionales al LLM.
        self.enable_summary_memory = _env_flag("AI_SUPPORT_ENABLE_SUMMARY_MEMORY", False)
        self.enable_entity_memory = _env_flag("AI_SUPPORT_ENABLE_ENTITY_MEMORY", False)
        self.enable_window_memory = _env_flag("AI_SUPPORT_ENABLE_WINDOW_MEMORY", True)

        try:
            self.window_k = int(os.getenv("AI_SUPPORT_WINDOW_MEMORY_K", "5"))
        except Exception:
            self.window_k = 5
        if self.window_k < 1:
            self.window_k = 1

        # 1. ConversationBufferMemory - Historial completo
        self.buffer_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
        )

        # Restaurar historial del usuario si existe
        if self.user_id and self.persistence:
            restored = restore_user_memory_to_buffer(self.user_id, self.buffer_memory, self.persistence)
            # No imprimir en consola (Streamlit re-ejecuta y spamea logs)
            # Si se necesita, usar logging a nivel DEBUG desde la app.

        # 2. ConversationSummaryMemory - Resume cuando es largo
        self.summary_memory = None
        if self.enable_summary_memory:
            self.summary_memory = ConversationSummaryMemory(
                llm=self.llm,
                memory_key="summary_history",
                return_messages=True,
            )

        # 3. ConversationBufferWindowMemory - Solo últimas N interacciones
        self.window_memory = None
        if self.enable_window_memory:
            self.window_memory = ConversationBufferWindowMemory(
                k=self.window_k,
                memory_key="window_history",
                return_messages=True,
            )

        # 4. ConversationEntityMemory - Recuerda entidades
        self.entity_memory = None
        if self.enable_entity_memory:
            self.entity_memory = ConversationEntityMemory(
                llm=self.llm,
                memory_key="entity_history",
                return_messages=True,
            )

        # 5. VectorStoreRetrieverMemory - Memoria a largo plazo
        self.vectorstore = None
        self.vector_memory = None
        if self.embeddings is not None:
            self._inicializar_vectorstore()

    def _inicializar_vectorstore(self) -> None:
        if self.embeddings is None:
            self.vectorstore = None
            self.vector_memory = None
            return

        try:
            docs = [Document(page_content="Memoria inicial del sistema")]
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
            self.vector_memory = VectorStoreRetrieverMemory(
                retriever=retriever,
                memory_key="vector_history",
                return_messages=True,
            )
        except Exception as e:
            signature = f"{type(e).__name__}:{str(e)[:300]}"
            if signature not in _VECTORSTORE_INIT_ERROR_SEEN:
                _VECTORSTORE_INIT_ERROR_SEEN.add(signature)
                print(f"⚠️ Error inicializando vectorstore: {e}")

            try:
                msg = str(e).lower()
                if "no_access" in msg or "403" in msg or "401" in msg:
                    self.embeddings = None
            except Exception:
                pass

            self.vectorstore = None
            self.vector_memory = None

    def agregar_interaccion(self, entrada: str, salida: str) -> None:
        self.buffer_memory.save_context({"input": entrada}, {"output": salida})
        if self.summary_memory:
            self.summary_memory.save_context({"input": entrada}, {"output": salida})
        if self.window_memory:
            self.window_memory.save_context({"input": entrada}, {"output": salida})
        if self.entity_memory:
            self.entity_memory.save_context({"input": entrada}, {"output": salida})

        if self.vector_memory:
            try:
                self.vector_memory.save_context({"input": entrada}, {"output": salida})
            except Exception as e:
                print(f"⚠️ Error guardando en vector memory: {e}")

        # Persistir *solo* el buffer conversacional del usuario
        if self.user_id and self.persistence:
            auto_save_user_memory(self.user_id, self.buffer_memory, self.persistence)

    def obtener_contexto_completo(self) -> Dict[str, Any]:
        contexto: Dict[str, Any] = {}

        try:
            buffer_vars = self.buffer_memory.load_memory_variables({})
            contexto["buffer"] = buffer_vars.get("chat_history", [])
        except Exception:
            contexto["buffer"] = []

        try:
            if self.summary_memory:
                summary_vars = self.summary_memory.load_memory_variables({})
                contexto["summary"] = summary_vars.get("summary_history", [])
            else:
                contexto["summary"] = []
        except Exception:
            contexto["summary"] = []

        try:
            if self.window_memory:
                window_vars = self.window_memory.load_memory_variables({})
                contexto["window"] = window_vars.get("window_history", [])
            else:
                contexto["window"] = []
        except Exception:
            contexto["window"] = []

        try:
            if self.entity_memory:
                entity_vars = self.entity_memory.load_memory_variables({})
                contexto["entities"] = entity_vars.get("entity_history", [])
            else:
                contexto["entities"] = []
        except Exception:
            contexto["entities"] = []

        try:
            if self.vector_memory:
                vector_vars = self.vector_memory.load_memory_variables({})
                contexto["vector"] = vector_vars.get("vector_history", [])
            else:
                contexto["vector"] = []
        except Exception:
            contexto["vector"] = []

        return contexto

    def limpiar_memoria(self) -> None:
        self.buffer_memory.clear()
        if self.summary_memory:
            self.summary_memory.clear()
        if self.window_memory:
            self.window_memory.clear()
        if self.entity_memory:
            self.entity_memory.clear()
        if self.vector_memory:
            self.vector_memory.clear()

        if self.user_id and self.persistence:
            self.persistence.delete_user_memory(self.user_id)

    def get_user_memory_stats(self) -> Optional[Dict[str, Any]]:
        if self.user_id and self.persistence:
            return self.persistence.get_user_stats(self.user_id)
        return None
