from typing import Any, Dict


class HerramientaSoporte:
    """Herramientas para análisis de consultas de FCFM (Facultad de Ciencias Físicas y Matemáticas)."""

    # Mapeo de áreas FCFM con palabras clave para enrutamiento determinista
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
        """Analiza consulta FCFM y enruta a área determinista por palabras clave."""
        desc_lower = descripcion.lower()

        # Contar coincidencias por área
        area_scores: Dict[str, int] = {}
        for area, palabras in HerramientaSoporte.AREAS_FCFM.items():
            score = sum(1 for p in palabras if p in desc_lower)
            if score > 0:
                area_scores[area] = score

        # Área con mayor puntuación
        if area_scores:
            categoria = max(area_scores, key=area_scores.get)
            prioridad = "alta"  # Todas las consultas FCFM son importantes
        else:
            categoria = "decanato"  # Fallback a decanato (área general)
            prioridad = "media"

        return {
            "categoria": categoria,
            "prioridad": prioridad,
            "sugerencias": [f"Consultar procedimiento de {categoria.replace('_', ' ')}", f"Revisar documentación en {categoria.replace('_', ' ')}"],
        }
            categoria = "excel"
            prioridad = "media"

        return {
            "categoria": categoria,
            "prioridad": prioridad,
            "sugerencias": [f"Verificar {categoria}", f"Contactar especialista en {categoria}"],
        }
