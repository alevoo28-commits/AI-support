"""Herramientas para análisis determinista y robusto de consultas FCFM.

Implementa enrutamiento a 15 áreas especializadas con:
- Determinismo: siempre mismo agente para misma consulta
- Robustez: tolera tildes, typos y variaciones usando fuzzy matching
- Sin dependencias: usa solo bibliotecas estándar de Python
"""

from typing import Any, Dict
from difflib import SequenceMatcher
import unicodedata


def normalizar_texto(texto: str) -> str:
    """Normaliza texto removiendo tildes y convirtiendo a minúsculas.
    
    Ejemplo:
        "Tesorería" → "tesoreria"
        "ADMINISTRACIÓN" → "administracion"
    """
    # Remover tildes
    nfd = unicodedata.normalize('NFD', texto.lower())
    sin_tildes = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return sin_tildes.strip()


def similitud_fuzzy(texto1: str, texto2: str) -> float:
    """Calcula similitud entre dos strings (0.0 - 1.0).
    
    Usa SequenceMatcher de difflib (determinista, sin dependencias externas).
    Tolerante a typos pequeños.
    
    Args:
        texto1: Primer texto (ej: palabra clave)
        texto2: Segundo texto (ej: consulta del usuario)
        
    Returns:
        Float entre 0.0 (muy diferente) y 1.0 (idéntico)
    """
    t1 = normalizar_texto(texto1)
    t2 = normalizar_texto(texto2)
    return SequenceMatcher(None, t1, t2).ratio()


class HerramientaSoporte:
    """Herramientas para análisis determinista y robusto de consultas FCFM."""

    # Mapeo de 15 áreas FCFM con palabras clave para enrutamiento
    AREAS_FCFM = {
        "tesoreria": ["tesorería", "presupuesto", "gasto", "fondo", "pago", "finanzas", "contrato", "viatico", "reembolso", "factura"],
        "arquitectura": ["arquitectura", "diseño", "plano", "estructura", "proyecto editorial", "infraestructura física"],
        "infraestructura": ["infraestructura", "mantenimiento", "edificio", "laboratorio", "aula", "reparación", "instalación espacial"],
        "proyectos": ["proyecto", "beca", "investigación", "propuesta", "recursos proyecto", "seguimiento"],
        "atencion_alumnos": ["alumno", "estudiante", "inscripción", "tutoría", "becas estudiante", "ayuda alumnos", "acta", "calificación"],
        "postgrado": ["postgrado", "posgrado", "magister", "doctorado", "escuela de postgrado", "posgrado", "educación continua", "diplomado", "cursos"],
        "sustentabilidad": ["sustentabilidad", "ambiental", "sostenible", "reciclaje", "responsabilidad social", "huella"],
        "comunicaciones": ["comunicación", "prensa", "publicidad", "redes sociales", "medios", "difusión"],
        "vinculacion": ["vinculación", "relaciones internacionales", "colaboración externa", "alianza", "cooperación internacional", "networking"],
        "rrhh": ["recurso humano", "rrhh", "personal", "contratación", "administración", "adquisición", "compra", "licitación"],
        "contabilidad": ["contabilidad", "balance", "auditoria", "estado financiero", "registro contable", "asiento"],
        "direccion_economica": ["dirección económica", "economía", "análisis económico", "presupuesto general", "gestión económica"],
        "direccion_academica": ["dirección académica", "académico", "currícula", "plan estudio", "docencia", "carrera", "titulación"],
        "diversidad": ["diversidad", "género", "inclusión", "equidad", "minorías", "desarrollo inclusivo"],
        "decanato": ["decanato", "vicedecanato", "decano", "vicedeacano", "rectoría", "administración facultad", "norma facultad"],
    }

    @staticmethod
    def calculadora_matematica(expresion: str) -> str:
        """Calcula expresiones matemáticas (ej: presupuestos, estadísticas)."""
        try:
            funciones_permitidas = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": lambda x: x**0.5,
                "len": len,
            }
            resultado = eval(expresion, {"__builtins__": {}, **funciones_permitidas})
            return f"Resultado: {resultado}"
        except Exception as e:
            return f"Error en el cálculo: {str(e)}"

    @staticmethod
    def buscar_informacion(query: str, categoria: str = "general") -> str:
        """Busca información en procedimientos del área FCFM."""
        return f"Información sobre {query} del procedimiento en {categoria}"

    @staticmethod
    def analizar_problema(descripcion: str) -> Dict[str, Any]:
        """Analiza consulta FCFM y enruta a área determinista usando fuzzy matching.
        
        DETERMINISTA: Siempre devuelve el mismo área para la misma consulta.
        ROBUSTO: Tolera tildes, typos pequeños y variaciones mediante fuzzy matching.
        
        Estrategia de matching (en orden de prioridad):
        1. Substring exacto normalizado (máxima confianza 0.95)
        2. Fuzzy match (similitud >= 0.85 para palabras largas, >= 0.80 para cortas)
        3. Fallback a decanato
        
        Args:
            descripcion: Consulta del usuario
            
        Returns:
            Dict con:
            - categoria: Área FCFM determinada (ej: "infraestructura")
            - prioridad: "alta", "media", "baja" basada en confianza
            - confianza: Float 0.0-1.0 indicando precisión del enrutamiento
            - sugerencias: Lista de pasos recomendados
        """
        desc_normalizado = normalizar_texto(descripcion)
        palabras_consulta = desc_normalizado.split()
        
        # Calcular puntuación de similitud por área
        area_scores: Dict[str, float] = {}
        
        for area, palabras_clave in HerramientaSoporte.AREAS_FCFM.items():
            max_similitud_area = 0.0
            
            # Estrategia 1: Búsqueda de palabras completas como substring (máxima prioridad)
            for palabra_clave in palabras_clave:
                pc_norm = normalizar_texto(palabra_clave)
                if pc_norm in desc_normalizado:
                    # Coincidencia exacta (substring normalizado)
                    max_similitud_area = max(max_similitud_area, 0.95)
            
            # Estrategia 2: Fuzzy matching palabra por palabra (tolera typos)
            # Pero con umbral más alto para evitar confusiones entre palabras similares
            for palabra_clave in palabras_clave:
                pc_len = len(normalizar_texto(palabra_clave))
                # Umbral adaptativo: más alto para palabras largas (menos ambigüedad)
                umbral = 0.85 if pc_len > 7 else 0.78
                
                for palabra_consulta in palabras_consulta:
                    similitud = similitud_fuzzy(palabra_clave, palabra_consulta)
                    
                    if similitud >= umbral:
                        # Ponderar por longitud relativa
                        similitud_ponderada = similitud * (pc_len / 12.0)
                        max_similitud_area = max(max_similitud_area, similitud_ponderada)
            
            if max_similitud_area > 0:
                area_scores[area] = max_similitud_area

        # Determinar categoría y confianza (DETERMINISTA: max siempre elige lo mismo)
        if area_scores:
            categoria = max(area_scores, key=area_scores.get)
            confianza = area_scores[categoria]
            
            # Prioridad basada en confianza
            if confianza >= 0.90:
                prioridad = "alta"
            elif confianza >= 0.75:
                prioridad = "media"
            else:
                prioridad = "baja"
        else:
            # Fallback: decanato (área general)
            categoria = "decanato"
            prioridad = "media"
            confianza = 0.0

        return {
            "categoria": categoria,
            "prioridad": prioridad,
            "confianza": round(confianza, 2),
            "sugerencias": [
                f"Consultar procedimiento de {categoria.replace('_', ' ')}",
                f"Revisar documentación en {categoria.replace('_', ' ')}"
            ],
        }
