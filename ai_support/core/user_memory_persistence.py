"""Sistema de persistencia de historial por usuario.

Guarda y restaura *solo* el historial de conversación (mensajes) por usuario.
No persiste perfiles, resúmenes, entidades u otros metadatos.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict


class UserMemoryPersistence:
    """Gestiona la persistencia de memoria conversacional por usuario."""

    def __init__(self, storage_dir: str = "./user_memories"):
        """
        Args:
            storage_dir: Directorio donde se guardan las memorias de usuarios
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_user_file(self, user_id: str, format: str = "json") -> Path:
        """Obtiene la ruta del archivo de memoria para un usuario."""
        # Sanitizar user_id para evitar path traversal
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "_-.")
        if not safe_user_id:
            safe_user_id = "default"
        
        return self.storage_dir / f"{safe_user_id}_memory.{format}"
    
    def save_user_memory(
        self,
        user_id: str,
        buffer_messages: list[BaseMessage],
    ) -> bool:
        """
        Guarda la memoria del buffer de un usuario.
        
        Args:
            user_id: Identificador del usuario
            buffer_messages: Mensajes del ConversationBufferMemory
            
        Returns:
            True si se guardó correctamente
        """
        try:
            file_path = self._get_user_file(user_id, "json")
            
            # Convertir mensajes a diccionarios serializables
            messages_dict = messages_to_dict(buffer_messages)
            
            # Preparar datos a guardar
            data = {
                "user_id": user_id,
                "last_updated": datetime.now().isoformat(),
                "messages": messages_dict,
                "version": "1.0"
            }
            
            # Guardar como JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"❌ Error guardando memoria de usuario {user_id}: {e}")
            return False
    
    def load_user_memory(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Carga la memoria guardada de un usuario.
        
        Args:
            user_id: Identificador del usuario
            
        Returns:
            Diccionario con:
                - messages: Lista de BaseMessage
                - last_updated: Fecha de última actualización
            O None si no existe o hay error
        """
        try:
            file_path = self._get_user_file(user_id, "json")
            
            if not file_path.exists():
                return None
            
            # Cargar JSON
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Convertir diccionarios a mensajes
            messages = messages_from_dict(data.get("messages", []))
            
            return {
                "messages": messages,
                "last_updated": data.get("last_updated"),
                "user_id": data.get("user_id")
            }
            
        except Exception as e:
            print(f"⚠️ Error cargando memoria de usuario {user_id}: {e}")
            return None
    
    def delete_user_memory(self, user_id: str) -> bool:
        """Elimina la memoria guardada de un usuario."""
        try:
            file_path = self._get_user_file(user_id, "json")
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"❌ Error eliminando memoria de usuario {user_id}: {e}")
            return False
    
    def list_users(self) -> list[str]:
        """Lista todos los usuarios que tienen memoria guardada."""
        try:
            users = []
            for file_path in self.storage_dir.glob("*_memory.json"):
                user_id = file_path.stem.replace("_memory", "")
                users.append(user_id)
            return sorted(users)
        except Exception as e:
            print(f"⚠️ Error listando usuarios: {e}")
            return []
    
    def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene estadísticas de la memoria de un usuario."""
        try:
            memory_data = self.load_user_memory(user_id)
            if not memory_data:
                return None
            
            messages = memory_data.get("messages", [])
            
            # Contar tipos de mensajes
            human_count = sum(1 for m in messages if m.type == "human")
            ai_count = sum(1 for m in messages if m.type == "ai")
            
            # Calcular tamaño aproximado
            file_path = self._get_user_file(user_id, "json")
            file_size = file_path.stat().st_size if file_path.exists() else 0
            
            return {
                "user_id": user_id,
                "total_messages": len(messages),
                "human_messages": human_count,
                "ai_messages": ai_count,
                "last_updated": memory_data.get("last_updated"),
                "file_size_bytes": file_size,
                "file_size_kb": round(file_size / 1024, 2)
            }
            
        except Exception as e:
            print(f"⚠️ Error obteniendo stats de usuario {user_id}: {e}")
            return None


def restore_user_memory_to_buffer(
    user_id: str,
    buffer_memory,
    persistence: Optional[UserMemoryPersistence] = None
) -> bool:
    """
    Restaura la memoria guardada de un usuario en un ConversationBufferMemory.
    
    Args:
        user_id: Identificador del usuario
        buffer_memory: Instancia de ConversationBufferMemory a restaurar
        persistence: Instancia de UserMemoryPersistence (crea una por defecto)
        
    Returns:
        True si se restauró correctamente
    """
    if persistence is None:
        persistence = UserMemoryPersistence()
    
    try:
        memory_data = persistence.load_user_memory(user_id)
        if not memory_data:
            return False
        
        messages = memory_data.get("messages", [])
        
        # Limpiar memoria actual
        buffer_memory.clear()
        
        # Restaurar mensajes
        # ConversationBufferMemory almacena en chat_memory.messages
        if hasattr(buffer_memory, "chat_memory"):
            buffer_memory.chat_memory.messages = messages
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error restaurando memoria de usuario {user_id}: {e}")
        return False


def auto_save_user_memory(
    user_id: str,
    buffer_memory,
    persistence: Optional[UserMemoryPersistence] = None,
) -> bool:
    """
    Guarda automáticamente la memoria actual de un usuario.
    
    Args:
        user_id: Identificador del usuario
        buffer_memory: Instancia de ConversationBufferMemory
        persistence: Instancia de UserMemoryPersistence (crea una por defecto)
        
    Returns:
        True si se guardó correctamente
    """
    if persistence is None:
        persistence = UserMemoryPersistence()
    
    try:
        # Obtener mensajes del buffer
        messages = []
        if hasattr(buffer_memory, "chat_memory"):
            messages = buffer_memory.chat_memory.messages
        
        return persistence.save_user_memory(user_id, messages)
        
    except Exception as e:
        print(f"❌ Error guardando automáticamente memoria de usuario {user_id}: {e}")
        return False
