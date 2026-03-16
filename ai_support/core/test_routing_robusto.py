"""Tests para validar enrutamiento robusto con fuzzy matching."""

from ai_support.core.tools import HerramientaSoporte, normalizar_texto, similitud_fuzzy


def test_normalizacion():
    """Valida que la normalización elimina tildes y normaliza."""
    casos = [
        ("Tesorería", "tesoreria"),
        ("ADMINISTRACIÓN", "administracion"),
        ("Postgrado", "postgrado"),
        ("ACADÉMICO", "academico"),
    ]
    
    for entrada, esperado in casos:
        resultado = normalizar_texto(entrada)
        assert resultado == esperado, f"Esperado '{esperado}', got '{resultado}'"
    
    print("✓ Normalización: PASS")


def test_similitud_fuzzy():
    """Valida que fuzzy matching tolera typos."""
    casos = [
        # (texto1, texto2, min_similitud)
        ("tesoreria", "tesoreria", 0.99),      # Idéntico
        ("tesoreria", "tesorería", 0.99),      # Con tilde (normalizado)
        ("tesoreria", "tesorer", 0.85),        # Typo pequeño
        ("administracion", "administración", 0.99),  # Con tilde
        ("recurso humano", "recurso humano", 0.99),  # Frase exacta
        ("recurso humano", "recursos humanos", 0.75),  # Variaciónde plural
    ]
    
    for t1, t2, min_sim in casos:
        resultado = similitud_fuzzy(t1, t2)
        assert resultado >= min_sim, f"'{t1}' vs '{t2}': expected >= {min_sim}, got {resultado:.2f}"
    
    print("✓ Fuzzy Match: PASS")


def test_enrutamiento_basico():
    """Valida que el enrutamiento funciona para áreas principales."""
    herramienta = HerramientaSoporte()
    
    casos = [
        ("¿Cómo presupuesto gasto financiero?", "tesoreria"),
        ("Infraestructura mantenimiento edificio", "infraestructura"),
        ("Postgrado diplomados cursos", "postgrado"),
        ("Personal recurso humano contratación", "rrhh"),
        ("Decano vicedecanato rectoría", "decanato"),
    ]
    
    for consulta, area_esperada in casos:
        resultado = herramienta.analizar_problema(consulta)
        categoria = resultado["categoria"]
        assert categoria == area_esperada, f"Consulta '{consulta}': esperado '{area_esperada}', got '{categoria}'"
    
    print("✓ Enrutamiento Básico: PASS")


def test_robustez_typos():
    """Valida que el sistema es robusto ante typos comunes."""
    herramienta = HerramientaSoporte()
    
    # Consultas con errores tipográficos pero misma intención
    consultas_typos = [
        ("tesoreria", "tesorería", "tesoreria"),  # Tilde
        ("postgrado", "postgrado", "postgrado"),  # OK
        ("tesorer presupuesto", "tesorero presupuesto", "tesoreria"),  # Typo pequeño
        ("edificio reparacion", "edificio reparación", "infraestructura"),  # Tilde
        ("alumno inscripcion", "alumno inscripción", "atencion_alumnos"),  # Inscripción
    ]
    
    for q_typo, q_ok, area_esperada in consultas_typos:
        r_typo = herramienta.analizar_problema(q_typo)
        r_ok = herramienta.analizar_problema(q_ok)
        
        # Ambas deberían dar la misma categoría
        assert r_typo["categoria"] == r_ok["categoria"], \
            f"Inconsistencia: '{q_typo}' → {r_typo['categoria']}, '{q_ok}' → {r_ok['categoria']}"
        
        # Ambas deberían apuntar al área correcta
        assert r_typo["categoria"] == area_esperada, \
            f"'{q_typo}': esperado '{area_esperada}', got '{r_typo['categoria']}'"
    
    print("✓ Robustez Typos: PASS")


def test_determinismo():
    """Valida que el enrutamiento es determinista (misma entrada = mismo resultado)."""
    herramienta = HerramientaSoporte()
    consulta = "Necesito ayuda con presupuesto y gastos administrativos"
    
    # Ejecutar varias veces
    resultados = [herramienta.analizar_problema(consulta) for _ in range(5)]
    
    # Todos deberían dar la misma categoría
    categorias = [r["categoria"] for r in resultados]
    assert len(set(categorias)) == 1, f"No determinista: {categorias}"
    
    print("✓ Determinismo: PASS")


def test_confianza():
    """Valida que el score de confianza es proporcional a la coincidencia."""
    herramienta = HerramientaSoporte()
    
    # Consulta muy específica (confianza alta)
    r_especifico = herramienta.analizar_problema("Tesorería presupuesto financiero gasto")
    confianza_alt = r_especifico["confianza"]
    
    # Consulta genérica (confianza posiblemente baja)
    r_generico = herramienta.analizar_problema("hola")
    confianza_baja = r_generico["confianza"]
    
    # La confianza específica debería ser mayor
    assert confianza_alt >= confianza_baja, \
        f"Confianza: específica={confianza_alt}, genérica={confianza_baja}"
    
    print("✓ Confianza: PASS")


def test_todas_areas():
    """Valida que podemos detectar cada una de las 15 áreas."""
    herramienta = HerramientaSoporte()
    areas_esperadas = set(herramienta.AREAS_FCFM.keys())
    areas_detectadas = set()
    
    # Para cada área, hacer una consulta con su palabra clave principal
    for area, palabras_clave in herramienta.AREAS_FCFM.items():
        consulta = palabras_clave[0]  # Usar primera palabra clave
        resultado = herramienta.analizar_problema(consulta)
        areas_detectadas.add(resultado["categoria"])
    
    # Todas las áreas deberían ser detectables
    assert areas_detectadas == areas_esperadas, \
        f"Áreas no detectadas: {areas_esperadas - areas_detectadas}"
    
    print("✓ Todas las 15 áreas: PASS")


if __name__ == "__main__":
    print("\n🧪 Ejecutando tests de enrutamiento robusto...\n")
    
    test_normalizacion()
    test_similitud_fuzzy()
    test_enrutamiento_basico()
    test_robustez_typos()
    test_determinismo()
    test_confianza()
    test_todas_areas()
    
    print("\n✅ Todos los tests PASARON\n")
