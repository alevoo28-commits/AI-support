from typing import Any, Dict


class HerramientaSoporte:
    """Conjunto de herramientas para soporte informático."""

    @staticmethod
    def calculadora_matematica(expresion: str) -> str:
        """Calcula expresiones matemáticas para hardware y capacidad."""
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
        """Busca información categorizada por tipo de soporte.

        Mantiene el comportamiento actual: se basa en el material cargado por agentes.
        """
        return f"Información sobre {query} para la categoría {categoria}"

    @staticmethod
    def analizar_problema(descripcion: str) -> Dict[str, Any]:
        """Analiza la descripción del problema y sugiere una categoría."""
        palabras_hardware = ["cpu", "ram", "disco", "hardware", "procesador", "memoria"]
        palabras_software = ["programa", "aplicación", "software", "instalación", "bug", "error"]
        palabras_redes = ["internet", "wifi", "conexión", "red", "router"]
        palabras_seguridad = ["virus", "malware", "seguridad", "antivirus", "firewall"]
        palabras_excel = [
            "excel",
            "hoja de cálculo",
            "celdas",
            "tabla dinámica",
            "tablas dinámicas",
            "power query",
            "buscarv",
            "vlookup",
            "xlookup",
            "macro",
            "vba",
            "#n/a",
            "#valor",
            "#¡div/0!",
        ]

        palabras_impresoras = [
            "impresora",
            "impresoras",
            "printer",
            "cola de impresión",
            "spooler",
            "atasco",
            "sin conexión",
            "offline",
            "usb001",
            "wfp",
            "wsp",
            "tcp/ip",
            "ip_",
            "hp",
            "epson",
            "canon",
            "brother",
            "xerox",
            "ricoh",
        ]

        desc_lower = descripcion.lower()

        categoria = "general"
        prioridad = "media"

        if any(palabra in desc_lower for palabra in palabras_hardware):
            categoria = "hardware"
            prioridad = "alta"
        elif any(palabra in desc_lower for palabra in palabras_software):
            categoria = "software"
            prioridad = "media"
        elif any(palabra in desc_lower for palabra in palabras_redes):
            categoria = "redes"
            prioridad = "alta"
        elif any(palabra in desc_lower for palabra in palabras_seguridad):
            categoria = "seguridad"
            prioridad = "crítica"
        elif any(palabra in desc_lower for palabra in palabras_impresoras):
            categoria = "impresoras"
            prioridad = "alta"
        elif any(palabra in desc_lower for palabra in palabras_excel):
            categoria = "excel"
            prioridad = "media"

        return {
            "categoria": categoria,
            "prioridad": prioridad,
            "sugerencias": [f"Verificar {categoria}", f"Contactar especialista en {categoria}"],
        }
