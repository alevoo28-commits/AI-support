"""Gestión de prompts externalizados en MySQL.

Permite:
- Almacenar todos los prompts en base de datos
- Actualizar prompts sin código ni redeploy
- Versionar cambios de prompts
- Fallback a valores hardcodeados si MySQL no disponible
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import mysql.connector
from mysql.connector import Error as MySQLError

logger = logging.getLogger(__name__)


class ConfiguracionMySQL:
    """Configuración para conexión a MySQL."""
    
    def __init__(self):
        self.host = os.getenv("AI_SUPPORT_MYSQL_HOST", "localhost")
        self.user = os.getenv("AI_SUPPORT_MYSQL_USER", "root")
        self.password = os.getenv("AI_SUPPORT_MYSQL_PASSWORD", "")
        self.database = os.getenv("AI_SUPPORT_MYSQL_DATABASE", "ai_support")
        self.port = int(os.getenv("AI_SUPPORT_MYSQL_PORT", "3306"))
        self.enabled = (os.getenv("AI_SUPPORT_MYSQL_ENABLE", "false").lower() == "true")
    
    def validar(self) -> bool:
        """Valida que la configuración esté completa."""
        if not self.enabled:
            return False
        
        return bool(self.host and self.user and self.password is not None and self.database)


class GestorPromptsMySQL:
    """Gestor de prompts almacenados en MySQL con fallback local."""
    
    # Prompts por defecto (fallback si MySQL no disponible)
    PROMPTS_POR_DEFECTO = {
        "system_prompt_agente": """Eres {nombre_agente}, un agente especializado en {especialidad}.

Documentación oficial (FUENTE PRINCIPAL):
{kb_context}

Conocimiento del área (FAISS RAG):
{faiss_context}

Contexto de memoria:
{memory_block}

Directrices:
1. Responde específicamente sobre {especialidad}
2. Proporciona soluciones prácticas y paso a paso
3. Si necesitas colaborar con otro agente, indícalo
4. Mantén un tono profesional y útil
5. Usa contexto de memoria y FAISS para respuestas personalizadas
6. Si tienes documentación oficial, responde BASÁNDOTE EN ELLA
7. Si faltan datos, indícalo claramente""",
        
        "identificar_colaboradores": """Analiza esta consulta y determina qué otros agentes deberían involucrados.

Consulta: {consulta}

Responde en JSON:
{{"colaboradores": ["area1", "area2"], "razon": "explicación"}}

Si no se requiere: colaboradores será lista vacía.""",
        
        "evaluar_colaboracion": """Evalúa cómo el agente {agente_externo} puede contribuir.

Contexto: {contexto}

Responde en 1-2 oraciones.""",
        
        "analizar_problema": """Clasifica este problema según área FCFM.

Consulta: {consulta}

Áreas: tesoreria, arquitectura, infraestructura, proyectos, atencion_alumnos,
postgrado, sustentabilidad, comunicaciones, vinculacion, rrhh, contabilidad,
direccion_economica, direccion_academica, diversidad, decanato

Devuelve: nombre_area (lowercase) y prioridad (alta/media/baja).""",
        
        "router_system": """Eres un enrutador de consultas determinista para el sistema FCFM.

Tu trabajo: Seleccionar el agente correcto basado en:
1. Palabras clave del área
2. Contexto de la consulta
3. Especialidad requerida

La decisión debe ser reproducible: misma consulta = mismo agente.""",
        
        "memory_summarizer": """Resume esta conversación sobre {tema} en puntos clave.

Conversación:
{contenido}

Resume en:
- 3-5 puntos principales
- Términos técnicos relevantes
- Decisiones tomadas""",
        
        "collaboration_summary": """Resume la colaboración entre agentes en esta conversación.

Contexto:
{contenido}

Extrae:
- Agentes involucrados
- Cómo contribuyó cada uno
- Resultado final"""
    }
    
    def __init__(self):
        """Inicializa gestor de prompts con fallback."""
        self.config = ConfiguracionMySQL()
        self.conexion: Optional[mysql.connector.MySQLConnection] = None
        self._prompts_cache: Dict[str, str] = {}
        
        if self.config.validar():
            self._inicializar_mysql()
        else:
            logger.info("⚠️  MySQL deshabilitado o mal configurado. Usando prompts hardcodeados.")
    
    def _inicializar_mysql(self) -> bool:
        """Intenta conectar y crear tabla de prompts."""
        try:
            self.conexion = mysql.connector.connect(
                host=self.config.host,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                port=self.config.port
            )
            
            # Crear tabla si no existe
            cursor = self.conexion.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_prompts (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    nombre VARCHAR(100) UNIQUE NOT NULL,
                    contenido LONGTEXT NOT NULL,
                    version INT DEFAULT 1,
                    descripcion VARCHAR(500),
                    activo BOOLEAN DEFAULT TRUE,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    actualizado_por VARCHAR(100),
                    INDEX idx_nombre (nombre),
                    INDEX idx_activo (activo)
                )
            """)
            
            # Migrar prompts por defecto si no existen
            self._migrar_prompts_por_defecto(cursor)
            
            self.conexion.commit()
            cursor.close()
            
            logger.info("✅ MySQL conectado: tabla 'system_prompts' lista")
            return True
            
        except MySQLError as e:
            logger.warning(f"⚠️  Error MySQL: {e}. Usando fallback local.")
            self.conexion = None
            return False
    
    def _migrar_prompts_por_defecto(self, cursor) -> None:
        """Inserta prompts por defecto si la tabla está vacía."""
        cursor.execute("SELECT COUNT(*) FROM system_prompts")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("📝 Migrando prompts por defecto a MySQL...")
            for nombre, contenido in self.PROMPTS_POR_DEFECTO.items():
                try:
                    cursor.execute("""
                        INSERT INTO system_prompts 
                        (nombre, contenido, descripcion, actualizado_por)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        nombre,
                        contenido,
                        f"Prompt por defecto: {nombre}",
                        "sistema"
                    ))
                except mysql.connector.Error:
                    pass  # Ya existe
    
    def obtener(self, nombre: str, **contexto) -> str:
        """
        Obtiene un prompt y lo formatea con contexto.
        
        Args:
            nombre: Nombre del prompt (ej: 'system_prompt_agente')
            **contexto: Variables para formatear el prompt
        
        Returns:
            Prompt formateado o fallback si no disponible
        """
        # Intentar obtener de MySQL
        if self.conexion:
            prompt = self._obtener_de_mysql(nombre)
            if prompt:
                try:
                    return prompt.format(**contexto)
                except KeyError as e:
                    logger.warning(f"Falta variable en prompt {nombre}: {e}")
                    return prompt
        
        # Fallback: prompts por defecto
        prompt = self.PROMPTS_POR_DEFECTO.get(nombre, "")
        if prompt:
            try:
                return prompt.format(**contexto)
            except KeyError as e:
                logger.warning(f"Falta variable en fallback {nombre}: {e}")
                return prompt
        
        logger.error(f"❌ Prompt no encontrado: {nombre}")
        return ""
    
    def _obtener_de_mysql(self, nombre: str) -> Optional[str]:
        """Obtiene prompt de MySQL con caché."""
        # Verificar caché
        if nombre in self._prompts_cache:
            return self._prompts_cache[nombre]
        
        try:
            cursor = self.conexion.cursor()
            cursor.execute(
                "SELECT contenido FROM system_prompts WHERE nombre = %s AND activo = TRUE",
                (nombre,)
            )
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                contenido = resultado[0]
                self._prompts_cache[nombre] = contenido
                return contenido
        except MySQLError as e:
            logger.warning(f"Error al obtener prompt {nombre}: {e}")
        
        return None
    
    def actualizar(
        self,
        nombre: str,
        contenido: str,
        actualizado_por: str = "sistema",
        descripcion: Optional[str] = None
    ) -> bool:
        """
        Actualiza un prompt en MySQL.
        
        Args:
            nombre: Nombre del prompt
            contenido: Nuevo contenido
            actualizado_por: Usuario que realiza cambio
            descripcion: Descripción del cambio
        
        Returns:
            True si tuvo éxito, False si falló
        """
        if not self.conexion:
            logger.error("❌ MySQL no disponible para actualización")
            return False
        
        try:
            cursor = self.conexion.cursor()
            
            # Incrementar versión
            cursor.execute("""
                UPDATE system_prompts 
                SET contenido = %s,
                    version = version + 1,
                    actualizado_por = %s,
                    actualizado_en = NOW()
                WHERE nombre = %s
            """, (contenido, actualizado_por, nombre))
            
            if cursor.rowcount == 0:
                # Insertar si no existe
                cursor.execute("""
                    INSERT INTO system_prompts 
                    (nombre, contenido, descripcion, actualizado_por)
                    VALUES (%s, %s, %s, %s)
                """, (nombre, contenido, descripcion, actualizado_por))
            
            self.conexion.commit()
            cursor.close()
            
            # Invalidar caché
            self._prompts_cache.pop(nombre, None)
            
            logger.info(f"✅ Prompt actualizado: {nombre} (versión: +1)")
            return True
            
        except MySQLError as e:
            logger.error(f"❌ Error al actualizar prompt: {e}")
            return False
    
    def listar(self, solo_activos: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Lista todos los prompts.
        
        Returns:
            Diccionario con info de cada prompt
        """
        if not self.conexion:
            # Retornar prompts por defecto
            return {
                nombre: {"contenido": contenido, "fuente": "hardcoded"}
                for nombre, contenido in self.PROMPTS_POR_DEFECTO.items()
            }
        
        try:
            cursor = self.conexion.cursor()
            
            query = "SELECT nombre, version, actualizado_en, actualizado_por, activo FROM system_prompts"
            if solo_activos:
                query += " WHERE activo = TRUE"
            
            cursor.execute(query)
            resultados = cursor.fetchall()
            cursor.close()
            
            dic_prompts = {}
            for nombre, version, actualizado_en, actualizado_por, activo in resultados:
                dic_prompts[nombre] = {
                    "version": version,
                    "actualizado_en": str(actualizado_en),
                    "actualizado_por": actualizado_por,
                    "activo": activo,
                    "fuente": "mysql"
                }
            
            return dic_prompts
            
        except MySQLError as e:
            logger.warning(f"Error al listar prompts: {e}")
            return {}
    
    def historial(self, nombre: str, limite: int = 10) -> list:
        """
        Obtiene historial de cambios de un prompt (versiones anteriores).
        
        Nota: Esta es una versión simplificada.
        Para historial completo, necesitaríamos tabla separada.
        """
        if not self.conexion:
            return []
        
        try:
            cursor = self.conexion.cursor()
            cursor.execute("""
                SELECT nombre, version, actualizado_en, actualizado_por
                FROM system_prompts 
                WHERE nombre = %s
                LIMIT %s
            """, (nombre, limite))
            
            resultados = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    "nombre": r[0],
                    "version": r[1],
                    "actualizado_en": str(r[2]),
                    "actualizado_por": r[3]
                }
                for r in resultados
            ]
        except MySQLError as e:
            logger.warning(f"Error al obtener historial: {e}")
            return []
    
    def desactivar(self, nombre: str) -> bool:
        """Desactiva un prompt sin eliminarlo."""
        if not self.conexion:
            return False
        
        try:
            cursor = self.conexion.cursor()
            cursor.execute(
                "UPDATE system_prompts SET activo = FALSE WHERE nombre = %s",
                (nombre,)
            )
            self.conexion.commit()
            cursor.close()
            
            self._prompts_cache.pop(nombre, None)
            logger.info(f"✅ Prompt desactivado: {nombre}")
            return True
        except MySQLError as e:
            logger.error(f"Error desactivando prompt: {e}")
            return False


# Instancia global
_gestor_prompts: Optional[GestorPromptsMySQL] = None


def inicializar_gestor() -> GestorPromptsMySQL:
    """Inicializa gestor global de prompts."""
    global _gestor_prompts
    if _gestor_prompts is None:
        _gestor_prompts = GestorPromptsMySQL()
    return _gestor_prompts


def obtener_prompt(nombre: str, **contexto) -> str:
    """Función auxiliar para obtener prompts."""
    gestor = inicializar_gestor()
    return gestor.obtener(nombre, **contexto)


def listar_prompts() -> Dict[str, Dict[str, Any]]:
    """Función auxiliar para listar prompts."""
    gestor = inicializar_gestor()
    return gestor.listar()
