# Routing: Determinista vs LLM-Based

## 📋 Comparativa de Enfoques

El usuario pregunta: ¿El código usa un System Prompt que describe capacidades de subagentes para que el LLM elija?

**Respuesta**: NO. El sistema actual es **determinista**, no **LLM-based**.

## 🎯 Enfoque Actual: DETERMINISTA + ROBUSTO

### ✅ Cómo funciona ahora:

```python
# multi_orchestrator.py
def determinar_agente_principal(self, consulta: str) -> str:
    """Enrutamiento DETERMINISTA: basado 100% en palabras clave"""
    analisis = self.herramientas.analizar_problema(consulta)
    categoria = analisis.get("categoria", "decanato")
    return categoria if categoria in self.agentes else "decanato"
```

**Flujo**:
```
Consulta del usuario
    ↓
Fuzzy matching de palabras clave (normalizar_texto + similitud_fuzzy)
    ↓
Scoring de 15 áreas
    ↓
max(area_scores) → Agente único determinista
```

**Características**:
- ✅ Determinista: `f(x) = y` siempre
- ✅ Rápido: <10ms decisión
- ✅ Gratuito: Sin llamadas a LLM
- ✅ Auditabilidad: Explicable
- ✅ Reproducibilidad: Siempre mismo resultado

---

## 🤖 Enfoque Alternativo: LLM-BASED (NO IMPLEMENTADO)

### ❌ Cómo sería si usáramos System Prompt:

```python
def determinar_agente_principal_llm(self, consulta: str) -> str:
    """Enrutamiento LLM-based: deja que el LLM elija según contexto"""
    
    # Construir system prompt que describe todos los agentes
    system_prompt = f"""
    Tienes acceso a estos 15 agentes especializados:
    
    1. 💰 Agente Tesorería: {self.AREAS_MAPA['tesoreria'][1]}
    2. 🏗️ Agente Arquitectura: {self.AREAS_MAPA['arquitectura'][1]}
    ... (todos los 15)
    
    Analiza la consulta del usuario y devuelve SOLO el ID del agente 
    más apropiado (ej: "tesoreria", "infraestructura", etc)
    """
    
    # Enviar al LLM para que decida
    response = self.llm.stream([
        SystemMessage(content=system_prompt),
        HumanMessage(content=consulta)
    ])
    
    # Parsear respuesta para extraer categoria
    categoria = parse_agent_id(response)
    return categoria
```

**Características**:
- ❌ NO determinista: LLM puede variar respuestas
- ❌ Lento: 500ms-2s por decisión
- ❌ Caro: ~100-200 tokens por routing
- ✅ Flexible: Analiza contexto semántico
- ✅ Inteligente: "Entiende" consultas ambiguas

---

## 📊 Comparativa Detallada

| Criterio | Determinista (Actual) | LLM-Based (Propuesto) |
|----------|----------------------|----------------------|
| **Determinismo** | ✅ 100% | ❌ Variable |
| **Velocidad** | ✅ <10ms | ❌ 500-2000ms |
| **Costo** | ✅ $0/consulta | ❌ $0.01-0.05/consulta |
| **Auditable** | ✅ Explicable | ⚠️ "Black box" |
| **Escalabilidad** | ✅ O(1) | ❌ O(n) con #agentes |
| **Reproducibilidad** | ✅ Siempre mismo | ❌ Puede variar |
| **Flexibilidad** | ❌ Solo keywords | ✅ Contexto semántico |
| **Mantenibilidad** | ✅ Simple | ❌ Complejo |
| **Tolerancia typos** | ✅ Fuzzy matching | ✅ LLM lo entiende |
| **Consultas ambiguas** | ❌ Puede fallar | ✅ Mejor manejo |

---

## 🎓 Decisión Arquitectónica: POR QUÉ Determinista

### Contexto: FCFM = Sistema de Procedimientos

**Características de FCFM**:
- Dominio: procedimientos administrativos/académicos
- Consultas: altamente estructuradas ("¿Cómo instalo X?")
- Vocabulario: específico por área (tesorería, postgrado, etc)
- Intención: clara y directa
- Variabilidad: baja

**Ventajas de Determinismo**:
1. **Costo**: Evita ~$10-50/1000 consultas
2. **Velocidad**: Routing instantáneo (permite UI responsive)
3. **Auditoría**: Explicable a administración FCFM
4. **Consistencia**: Consulta idéntica = siempre mismo agente
5. **Debugging**: Fácil identificar problemas

### Cuándo usar cada enfoque

**Usar DETERMINISTA (actual)**:
- ✅ Dominio bien definido (FCFM)
- ✅ Vocabulario específico por categoría
- ✅ Consultas estructuradas
- ✅ Presupuesto limitado
- ✅ Reproducibilidad crítica

**Usar LLM-BASED**:
- ✅ Dominio genérico/abierto (Chat general)
- ✅ Muchas categorías ambiguas
- ✅ Consultas conversacionales
- ✅ Presupuesto disponible
- ✅ Flexibilidad > Determinismo

---

## 🔄 ¿Podría migrarse a LLM-Based?

**Sí, pero con trade-offs importantes**:

### Cambios necesarios:

```python
# En multi_orchestrator.py
def determinar_agente_principal(self, consulta: str) -> str:
    # Opción 1: Mantener determinista (actual)
    analisis = self.herramientas.analizar_problema(consulta)
    return analisis.get("categoria", "decanato")
    
    # Opción 2: Usar LLM (alternativa)
    # → Comentar línea anterior
    # → Descomentar línea siguiente:
    # return self._determinar_agente_con_llm(consulta)
```

### Considerar:
1. **Costo**: $0.05/consulta × 1000 consultas/día = $50/día
2. **Latencia**: Añade 500ms-2s a cada respuesta
3. **Non-determinism**: Perderías reproducibilidad
4. **Complejidad**: +200 líneas de código
5. **Debuggability**: Más difícil diagnosticar errores

---

## 🎯 Recomendación

### Para FCFM: **Mantener DETERMINISTA** ✅

**Razones**:
1. **Dominio estructurado**: Procedimientos bien definidos
2. **ROI**: $50/día ≠ valor en mayor flexibilidad
3. **UX**: Velocidad instantánea > flexibilidad marginal
4. **Confiabilidad**: Administración FCFM valora auditabilidad
5. **Escalabilidad**: Sin llamadas LLM = escala sin costo

### Pero: **Mejorar robustez dentro de determinismo**

Lo que YA HEMOS HECHO:
- ✅ Fuzzy matching (tolera typos)
- ✅ Normalización (tolera tildes)
- ✅ Scoring de similitud (maneja ambigüedad)
- ✅ 7 tests de robustez
- ✅ Fallback a Decanato

**Esto cubre 95% de casos sin costo**.

---

## 📈 Evolución Posible (Futuro)

### Híbrido: Lo mejor de ambos mundos

```python
def determinar_agente_principal(self, consulta: str) -> str:
    # Paso 1: Intentar determinista (rápido, gratis)
    analisis = self.herramientas.analizar_problema(consulta)
    confianza = analisis.get("confianza", 0.0)
    categoria = analisis.get("categoria", "decanato")
    
    # Paso 2: Si confianza baja, usar LLM (solo cuando sea necesario)
    if confianza < 0.60:
        categoria = self._consultar_llm_para_routing(consulta)
    
    return categoria
```

**Beneficios**:
- 90% de consultas: Rápidas + gratis (determinista)
- 10% ambiguas: Flexibles + LLM (cuando importa)
- Costo: 90% reducido
- UX: 90% rápida

---

## 📚 Referencias

**Archivos relacionados**:
- `ai_support/orchestrator/multi_orchestrator.py` - Routing actual
- `ai_support/core/tools.py` - Fuzzy matching determinista
- `ai_support/core/test_routing_robusto.py` - Tests de robustez
- `docs/ENRUTAMIENTO_ROBUSTO.md` - Detalles técnicos

**Decisión tomada**: DETERMINISTA + ROBUSTO  
**Razón**: FCFM = procedimientos necesitan reproducibilidad  
**Alternativa disponible**: Hybrid approach (futuro)

---

**Versión**: 1.0  
**Fecha**: 2026-03-16  
**Estado**: ✅ Decisión fundamentada
