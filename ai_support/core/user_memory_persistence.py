"""Sistema de persistencia de historial por usuario.

Guarda y restaura *solo* el historial de conversación (mensajes) por usuario.
No persiste perfiles, resúmenes, entidades u otros metadatos.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict


class UserMemoryPersistence:
    """Gestiona la persistencia de memoria conversacional por usuario."""

    def __init__(self, storage_dir: Optional[str] = None, backend: Optional[str] = None):
        """
        Args:
            storage_dir: Directorio donde se guardan las memorias de usuarios
            backend: "auto" | "file" | "mysql". Si no se entrega, se resuelve por env.
        """
        # Resolución de backend
        # - Si se pasa storage_dir explícito (ej. tests), forzamos backend de archivos.
        # - Si backend viene explícito, lo usamos.
        # - Si no, buscamos env AI_SUPPORT_USER_MEMORY_BACKEND, default "auto".
        if storage_dir is not None and backend is None:
            backend = "file"
        if backend is None:
            backend = (os.getenv("AI_SUPPORT_USER_MEMORY_BACKEND") or "auto").strip().lower()
        if backend not in {"auto", "file", "mysql"}:
            backend = "auto"

        self.backend = backend

        # En modo "auto", si MySQL falla una vez, lo deshabilitamos para el resto
        # del proceso para evitar spam de warnings y reintentos costosos.
        self._mysql_disabled_in_auto: bool = False
        self._mysql_disabled_reason: Optional[str] = None
        self._mysql_warning_printed: bool = False

        if storage_dir is None:
            # Permite override explícito por entorno
            env_dir = os.getenv("AI_SUPPORT_USER_MEMORY_DIR")
            if env_dir:
                storage_dir = env_dir
            else:
                # Por defecto: carpeta por-perfil del SO
                # Windows: %LOCALAPPDATA%\AI-support\user_memories
                # Otros: ~/.ai_support/user_memories
                local_app = os.getenv("LOCALAPPDATA")
                if local_app:
                    storage_dir = str(Path(local_app) / "AI-support" / "user_memories")
                else:
                    storage_dir = str(Path.home() / ".ai_support" / "user_memories")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_user_id(self, user_id: str) -> str:
        safe_user_id = "".join(c for c in (user_id or "") if c.isalnum() or c in "_-.")
        if not safe_user_id:
            safe_user_id = "default"
        return safe_user_id[:128]

    def _mysql_enabled_and_configured(self) -> bool:
        raw = (os.getenv("AI_SUPPORT_MYSQL_ENABLE") or "false").strip().lower()
        if raw not in {"1", "true", "yes", "y", "on"}:
            return False

        host = (os.getenv("AI_SUPPORT_MYSQL_HOST") or "").strip()
        user = (os.getenv("AI_SUPPORT_MYSQL_USER") or "").strip()
        password = os.getenv("AI_SUPPORT_MYSQL_PASSWORD")
        database = (os.getenv("AI_SUPPORT_MYSQL_DATABASE") or "").strip()
        return bool(host and user and password is not None and database)

    def _mysql_auto_create_schema_enabled(self) -> bool:
        """Permite crear tabla automáticamente.

        Por defecto está deshabilitado para evitar errores por permisos (CREATE denied)
        en entornos donde la tabla debe ser provisionada por un DBA.
        """
        raw = (os.getenv("AI_SUPPORT_MYSQL_AUTO_CREATE_SCHEMA") or "false").strip().lower()
        return raw in {"1", "true", "yes", "y", "on"}

    def _mark_mysql_unavailable_in_auto(self, e: Exception) -> None:
        if self.backend != "auto":
            return
        if not self._mysql_disabled_in_auto:
            self._mysql_disabled_in_auto = True
            self._mysql_disabled_reason = f"{type(e).__name__}: {str(e)[:400]}"

        if not self._mysql_warning_printed:
            self._mysql_warning_printed = True
            print(f"⚠️ MySQL no disponible para memoria; usando archivos. Detalle: {e}")

    def _mysql_connect(self):
        try:
            import mysql.connector  # type: ignore
        except Exception as e:
            raise RuntimeError("Falta dependencia mysql-connector-python. Instala requirements.") from e

        host = (os.getenv("AI_SUPPORT_MYSQL_HOST") or "").strip()
        user = (os.getenv("AI_SUPPORT_MYSQL_USER") or "").strip()
        password = os.getenv("AI_SUPPORT_MYSQL_PASSWORD")
        database = (os.getenv("AI_SUPPORT_MYSQL_DATABASE") or "").strip()
        port_raw = (os.getenv("AI_SUPPORT_MYSQL_PORT") or "3306").strip()
        try:
            port = int(port_raw)
        except Exception:
            port = 3306

        return mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connection_timeout=8,
        )

    def _mysql_table(self) -> str:
        # Tabla configurable; default conservador
        t = (os.getenv("AI_SUPPORT_MYSQL_USER_MEMORY_TABLE") or "ai_support_user_memory").strip()
        # Sanitizar nombre de tabla (simple: alfanum + _)
        safe = "".join(c for c in t if c.isalnum() or c == "_")
        return safe or "ai_support_user_memory"

    def _mysql_ensure_schema(self, conn) -> None:
        table = self._mysql_table()
        ddl = f"""
CREATE TABLE IF NOT EXISTS `{table}` (
  `user_id` VARCHAR(128) NOT NULL,
  `last_updated` DATETIME(6) NOT NULL,
  `memory_json` JSON NOT NULL,
  `version` VARCHAR(16) NOT NULL,
  PRIMARY KEY (`user_id`)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
""".strip()

        cur = conn.cursor()
        try:
            cur.execute(ddl)
            conn.commit()
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def _should_use_mysql(self) -> bool:
        if self.backend == "file":
            return False
        if self.backend == "mysql":
            return True
        # auto
        if self._mysql_disabled_in_auto:
            return False
        return self._mysql_enabled_and_configured()
        
    def _get_user_file(self, user_id: str, format: str = "json") -> Path:
        """Obtiene la ruta del archivo de memoria para un usuario."""
        # Sanitizar user_id para evitar path traversal
        safe_user_id = self._sanitize_user_id(user_id)
        
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
        safe_user_id = self._sanitize_user_id(user_id)

        # Convertir mensajes a diccionarios serializables
        messages_dict = messages_to_dict(buffer_messages)

        # Preparar datos a guardar
        data = {
            "user_id": safe_user_id,
            "last_updated": datetime.now().isoformat(),
            "messages": messages_dict,
            "version": "1.0",
        }

        if self._should_use_mysql():
            try:
                conn = self._mysql_connect()
                try:
                    table = self._mysql_table()
                    cur = conn.cursor()
                    try:
                        # REPLACE simplifica upsert por PK
                        cur.execute(
                            f"REPLACE INTO `{table}` (user_id, last_updated, memory_json, version) VALUES (%s, %s, %s, %s)",
                            (
                                safe_user_id,
                                datetime.now(),
                                json.dumps(data, ensure_ascii=False),
                                "1.0",
                            ),
                        )
                        conn.commit()
                    finally:
                        try:
                            cur.close()
                        except Exception:
                            pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
                return True
            except Exception as e:
                # Fallback a archivo si estamos en auto
                if self.backend == "auto":
                    # Intento opcional de auto-crear esquema solo si está habilitado.
                    if self._mysql_auto_create_schema_enabled():
                        try:
                            conn2 = self._mysql_connect()
                            try:
                                self._mysql_ensure_schema(conn2)
                            finally:
                                try:
                                    conn2.close()
                                except Exception:
                                    pass
                            # Reintentar una vez
                            try:
                                conn3 = self._mysql_connect()
                                try:
                                    table = self._mysql_table()
                                    cur3 = conn3.cursor()
                                    try:
                                        cur3.execute(
                                            f"REPLACE INTO `{table}` (user_id, last_updated, memory_json, version) VALUES (%s, %s, %s, %s)",
                                            (
                                                safe_user_id,
                                                datetime.now(),
                                                json.dumps(data, ensure_ascii=False),
                                                "1.0",
                                            ),
                                        )
                                        conn3.commit()
                                        return True
                                    finally:
                                        try:
                                            cur3.close()
                                        except Exception:
                                            pass
                                finally:
                                    try:
                                        conn3.close()
                                    except Exception:
                                        pass
                            except Exception as e2:
                                self._mark_mysql_unavailable_in_auto(e2)
                        except Exception as e2:
                            self._mark_mysql_unavailable_in_auto(e2)
                    else:
                        self._mark_mysql_unavailable_in_auto(e)
                else:
                    print(f"❌ Error guardando memoria en MySQL para usuario {safe_user_id}: {e}")
                    return False

        # Backend archivos
        try:
            file_path = self._get_user_file(safe_user_id, "json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error guardando memoria de usuario {safe_user_id}: {e}")
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
        safe_user_id = self._sanitize_user_id(user_id)

        if self._should_use_mysql():
            try:
                conn = self._mysql_connect()
                try:
                    table = self._mysql_table()
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            f"SELECT memory_json, last_updated FROM `{table}` WHERE user_id=%s",
                            (safe_user_id,),
                        )
                        row = cur.fetchone()
                    finally:
                        try:
                            cur.close()
                        except Exception:
                            pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

                if not row:
                    return None

                memory_json, last_updated = row
                if isinstance(memory_json, (dict, list)):
                    data = memory_json
                else:
                    data = json.loads(memory_json)

                messages = messages_from_dict(data.get("messages", []))
                return {
                    "messages": messages,
                    "last_updated": data.get("last_updated") or (last_updated.isoformat() if last_updated else None),
                    "user_id": data.get("user_id") or safe_user_id,
                }
            except Exception as e:
                if self.backend == "auto":
                    # Intento opcional de auto-crear esquema solo si está habilitado.
                    if self._mysql_auto_create_schema_enabled():
                        try:
                            conn2 = self._mysql_connect()
                            try:
                                self._mysql_ensure_schema(conn2)
                            finally:
                                try:
                                    conn2.close()
                                except Exception:
                                    pass
                            # Reintentar una vez
                            try:
                                conn3 = self._mysql_connect()
                                try:
                                    table = self._mysql_table()
                                    cur3 = conn3.cursor()
                                    try:
                                        cur3.execute(
                                            f"SELECT memory_json, last_updated FROM `{table}` WHERE user_id=%s",
                                            (safe_user_id,),
                                        )
                                        row = cur3.fetchone()
                                    finally:
                                        try:
                                            cur3.close()
                                        except Exception:
                                            pass
                                finally:
                                    try:
                                        conn3.close()
                                    except Exception:
                                        pass

                                if not row:
                                    return None

                                memory_json, last_updated = row
                                if isinstance(memory_json, (dict, list)):
                                    data = memory_json
                                else:
                                    data = json.loads(memory_json)
                                messages = messages_from_dict(data.get("messages", []))
                                return {
                                    "messages": messages,
                                    "last_updated": data.get("last_updated")
                                    or (last_updated.isoformat() if last_updated else None),
                                    "user_id": data.get("user_id") or safe_user_id,
                                }
                            except Exception as e2:
                                self._mark_mysql_unavailable_in_auto(e2)
                        except Exception as e2:
                            self._mark_mysql_unavailable_in_auto(e2)
                    else:
                        self._mark_mysql_unavailable_in_auto(e)
                else:
                    print(f"⚠️ Error cargando memoria en MySQL para usuario {safe_user_id}: {e}")
                    return None

        # Backend archivos
        try:
            file_path = self._get_user_file(safe_user_id, "json")
            if not file_path.exists():
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            messages = messages_from_dict(data.get("messages", []))
            return {
                "messages": messages,
                "last_updated": data.get("last_updated"),
                "user_id": data.get("user_id"),
            }
        except Exception as e:
            print(f"⚠️ Error cargando memoria de usuario {safe_user_id}: {e}")
            return None
    
    def delete_user_memory(self, user_id: str) -> bool:
        """Elimina la memoria guardada de un usuario."""
        safe_user_id = self._sanitize_user_id(user_id)

        if self._should_use_mysql():
            try:
                conn = self._mysql_connect()
                try:
                    table = self._mysql_table()
                    cur = conn.cursor()
                    try:
                        cur.execute(f"DELETE FROM `{table}` WHERE user_id=%s", (safe_user_id,))
                        conn.commit()
                        return cur.rowcount > 0
                    finally:
                        try:
                            cur.close()
                        except Exception:
                            pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
            except Exception as e:
                if self.backend == "auto":
                    self._mark_mysql_unavailable_in_auto(e)
                else:
                    print(f"❌ Error eliminando memoria en MySQL para usuario {safe_user_id}: {e}")
                    return False

        try:
            file_path = self._get_user_file(safe_user_id, "json")
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"❌ Error eliminando memoria de usuario {safe_user_id}: {e}")
            return False
    
    def list_users(self) -> list[str]:
        """Lista todos los usuarios que tienen memoria guardada."""
        if self._should_use_mysql():
            try:
                conn = self._mysql_connect()
                try:
                    table = self._mysql_table()
                    cur = conn.cursor()
                    try:
                        cur.execute(f"SELECT user_id FROM `{table}` ORDER BY user_id")
                        rows = cur.fetchall() or []
                    finally:
                        try:
                            cur.close()
                        except Exception:
                            pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
                return [str(r[0]) for r in rows if r and r[0]]
            except Exception as e:
                if self.backend == "auto":
                    self._mark_mysql_unavailable_in_auto(e)
                else:
                    print(f"⚠️ Error listando usuarios desde MySQL: {e}")
                    return []

        try:
            users: list[str] = []
            for file_path in self.storage_dir.glob("*_memory.json"):
                uid = file_path.stem.replace("_memory", "")
                users.append(uid)
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
            # - File backend: bytes del archivo
            # - MySQL backend: bytes del JSON serializado
            file_size = 0
            if self._should_use_mysql():
                try:
                    file_size = len(json.dumps(messages_to_dict(messages), ensure_ascii=False).encode("utf-8"))
                except Exception:
                    file_size = 0
            else:
                file_path = self._get_user_file(user_id, "json")
                file_size = file_path.stat().st_size if file_path.exists() else 0
            
            return {
                "user_id": self._sanitize_user_id(user_id),
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
