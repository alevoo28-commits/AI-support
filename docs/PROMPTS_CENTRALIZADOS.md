# Prompts Centralizados - Arquitectura Multiagente FCFM

## 📋 Descripción General

El sistema FCFM implementa **mejor práctica de arquitectura multiagente**: todos los prompts (instrucciones a los LLMs) están centralizados en un archivo separado `ai_support/core/prompts.py`.

Esto permite:
- ✅ Iterar rápidamente sobre directrices sin modificar código
- ✅ Mantener control de versiones de cambios en prompts
- ✅ Separación clara entre lógica y configuración
- ✅ Código principal más legible y enfocado

## 📂 Estructura de Archivos

```
ai_support/
├── core/
│   ├── prompts.py                    ← TODOS LOS PROMPTS AQUÍ
│   ├── specialized_agent.py          ← Usa prompts.py
│   ├── memory.py
│   ├── config.py
│   └── ...
├── agents/
│   └── specialized_agent.py          ← Lógica del agente (usa prompts)
└── orchestrator/
    └── multi_orchestrator.py         ← Usa orchestrador (usa prompts)
```

## 🎯 Funciones de Prompts

### 1. `get_system_prompt_agente()`
**Responsabilidad**: Generar el prompt del sistema para cada agente especializado

```python
get_system_prompt_agente(
    nombre_agente="💰 Agente Tesorería",
    especialidad="procedimientos de tesorería, presupuestos",
    kb_context="Documentación de tesorería...",
    faiss_context="Contexto recuperado por búsqueda...",
    memory_block="Resumen de conversaciones anteriores..."
)
```

**Estructura del prompt generado**:
```
Eres [nombre], especializado en [especialidad]

Documentación oficial: [kb_context]
Conocimiento del área (FAISS RAG): [faiss_context]
Contexto de memoria: [memory_block]

Directrices:
1. [Responde específicamente sobre el área]
2. [Proporciona soluciones prácticas]
3. [Colabora si es necesario]
4. [Tono profesional]
5. [Usa memoria y FAISS]
6. [Prioriza documentación oficial]
7. [Se honesto si no tienes info]
```

### 2. `PROMPT_IDENTIFICAR_COLABORADORES`
**Responsabilidad**: Determinar qué otros agentes deben colaborar

Usado cuando una consulta requiere múltiples áreas.

```python
{
    "colaboradores": ["infraestructura", "rrhh"],
    "razon": "Se requiere gestión de personal y mantenimiento"
}
```

### 3. `PROMPT_EVALUAR_COLABORACION`
**Responsabilidad**: Evaluar contribución de agentes colaboradores

### 4. `PROMPT_ANALIZAR_PROBLEMA`
**Responsabilidad**: Clasificar consulta según área FCFM

### 5. `get_router_system_prompt()`
**Responsabilidad**: Enrutamiento determinista de consultas

### 6. `get_memory_summarizer_prompt()`
**Responsabilidad**: Resumir conversaciones para memoria

### 7. `get_collaboration_summary_prompt()`
**Responsabilidad**: Resumir colaboración entre agentes

## 🔄 Flujo de Uso

### Cómo se utilizan en `specialized_agent.py`:

```python
# 1. Importar la función
from ai_support.core.prompts import get_system_prompt_agente

# 2. En procesar_consulta(), generar el prompt
system_prompt = get_system_prompt_agente(
    nombre_agente=self.nombre,
    especialidad=self.especialidad,
    kb_context=kb_context,
    faiss_context=contexto_faiss,
    memory_block=memory_block,
)

# 3. Usar en mensajes
messages = [SystemMessage(content=system_prompt)]
messages.append(HumanMessage(content=consulta))

# 4. Enviar al LLM
response = self.llm.stream(messages)
```

## 🛠️ Cómo Iterar Prompts

### Caso 1: Cambiar directrices del agente

**Archivo**: `ai_support/core/prompts.py`

**Encontrar**: Función `get_system_prompt_agente()`

**Cambiar**: La sección "Directrices:"

```python
def get_system_prompt_agente(...):
    # ... código previo ...
    
    system_prompt = f"""...
    
Directrices:
1. ✏️ EDITA AQUÍ: Nueva directriz 1
2. NEW: Cambio importante
3. removed: Directriz antigua
...
"""
```

**Beneficio**: No necesitas entender la lógica del agente, solo las instrucciones

### Caso 2: Agregar nuevo tipo de prompt

**Pasos**:
1. Agregar función o variable en `prompts.py`
2. Importarla donde sea necesaria
3. Usar en el código principal

**Ejemplo**: Nuevo prompt para validar respuestas

```python
# En prompts.py
def get_validation_prompt(tema: str) -> str:
    """Valida que la respuesta sea correcta y completa."""
    return f"""Revisa esta respuesta sobre {tema}.
    
¿Cumple con:
1. Información correcta?
2. Pasos claros?
3. Completa?
    """

# En specialized_agent.py
from ai_support.core.prompts import get_validation_prompt

validation_prompt = get_validation_prompt(self.especialidad)
# ... usar en lógica de validación
```

## 📚 15 Áreas FCFM Soportadas

Cada área tiene su especialidad definida en `prompts.py` (vía `multi_orchestrator.py`):

| Área | Especialidad |
|------|-------------|
| **tesoreria** | procedimientos de tesorería, presupuestos, gastos |
| **arquitectura** | procedimientos de arquitectura, diseño, proyectos editoriales |
| **infraestructura** | procedimientos de infraestructura, mantenimiento, edificios |
| **proyectos** | procedimientos de proyectos, becas, investigación |
| **atencion_alumnos** | procedimientos de atención a estudiantes, inscripción, tutorías |
| **postgrado** | procedimientos de postgrado, diplomados, educación continua |
| **sustentabilidad** | procedimientos de sustentabilidad, sostenibilidad, responsabilidad social |
| **comunicaciones** | procedimientos de comunicaciones, prensa, difusión |
| **vinculacion** | procedimientos de vinculación externa, relaciones internacionales |
| **rrhh** | procedimientos de recursos humanos, contratación, adquisiciones, administración |
| **contabilidad** | procedimientos contables, registros, auditoría, estados financieros |
| **direccion_economica** | procedimientos de dirección económica, análisis financiero |
| **direccion_academica** | procedimientos académicos, currícula, planes de estudio |
| **diversidad** | procedimientos de diversidad, género, inclusión, equidad |
| **decanato** | procedimientos del decanato, normas facultad, administración general |

## 🎓 Mejores Prácticas Implementadas

### ✅ Separación de Responsabilidades
- Prompts: `ai_support/core/prompts.py`
- Lógica de agente: `ai_support/agents/specialized_agent.py`
- Orquestración: `ai_support/orchestrator/multi_orchestrator.py`

### ✅ DRY (Don't Repeat Yourself)
- `get_system_prompt_agente()` genera prompts reutilizables
- Mismo formato para todos los 15 agentes
- Fácil de expandir

### ✅ Versionado
- Cambios en prompts = cambios en archivo único
- Git rastrean iteraciones de prompts
- Historial de cambios claro

### ✅ Documentación Inline
```python
def get_system_prompt_agente(
    nombre_agente: str,          # "💰 Agente Tesorería"
    especialidad: str,           # "procedimientos de tesorería..."
    kb_context: str = "",        # Documentación oficial
    faiss_context: str = "",     # Resultados búsqueda RAG
    memory_block: str = "",      # Contexto memoria
) -> str:
```

## 🔍 Ejemplos de Uso Real

### Ejemplo 1: Consulta a Infraestructura

```
Usuario: "¿Cómo instalo el software INFORMAT?"

Sistema:
1. Enruta a: "infraestructura"
2. Busca en KB: Procedimientos INFORMAT
3. Busca en FAISS: Documentación técnica
4. Obtiene memoria: Consultas anteriores sobre software
5. Genera system_prompt con get_system_prompt_agente()
6. Envía al LLM:
   - SystemMessage: prompt del agente (incluye documentación)
   - HumanMessage: la consulta
7. LLM responde basándose en contexto
```

### Ejemplo 2: Cambiar Directrices de Respuesta

**Antes** (en prompts.py):
```python
"2. Proporciona soluciones prácticas y paso a paso"
```

**Después** (modificar y guardar):
```python
"2. Proporciona soluciones prácticas, paso a paso, y siempre con screenshots"
```

✨ **Sin tocar código de lógica del agente, los 15 agentes ahora esperan screenshots**

## 📦 Composición del System Prompt

El prompt final que ve el LLM es una **composición de múltiples fuentes**:

```
┌─────────────────────────────────────────┐
│  Directrices del Agente                 │  ← get_system_prompt_agente()
│  (rol, especialidad, comportamiento)    │
├─────────────────────────────────────────┤
│  Documentación Oficial (KB)             │  ← contexto.get("kb_context")
│  (manuales, procedimientos subidos)     │
├─────────────────────────────────────────┤
│  Conocimiento Especializado (FAISS)     │  ← buscar_contexto_faiss()
│  (búsqueda semántica de procedimientos) │
├─────────────────────────────────────────┤
│  Contexto de Memoria                    │  ← SistemaMemoriaAvanzada
│  (conversaciones anteriores, entidades) │
└─────────────────────────────────────────┘
          ↓
    System Prompt Final enviado al LLM
```

## 🚀 Próximos Pasos (Roadmap)

### Corto plazo
- [ ] A/B testing de prompts (grabar métricas de exactitud)
- [ ] Versioning explícito de prompts (v1.0, v1.1, etc.)
- [ ] Prompts por idioma (español/inglés)

### Mediano plazo
- [ ] Editor visual de prompts en Streamlit UI
- [ ] Panel de métricas para evaluar calidad de respuestas por área
- [ ] Fallback de prompts si el principal falla

### Largo plazo
- [ ] Prompts personalizados por usuario/rol
- [ ] Auto-tuning de prompts basado en feedback
- [ ] Prompts multimodales (texto + imágenes)

## 🔗 Referencias y Archivos

| Archivo | Responsabilidad |
|---------|-----------------|
| `ai_support/core/prompts.py` | **Definición de todos los prompts** |
| `ai_support/agents/specialized_agent.py` | Uso de prompts en lógica de agente |
| `ai_support/orchestrator/multi_orchestrator.py` | Orquestación de múltiples agentes |
| `ai_support/core/memory.py` | Generación de memory_block |
| `ai_support/core/knowledge_base.py` | Recuperación de kb_context |

## ✍️ Changelog

### v1.0 (2026-03-16)
- ✅ Prompts centralizados en `ai_support/core/prompts.py`
- ✅ Función `get_system_prompt_agente()` para generación reutilizable
- ✅ 7 templates de prompts (agente, colaboración, memoria, etc.)
- ✅ Integración con `specialized_agent.py`
- ✅ Documentación completa

---

**Última actualización**: 2026-03-16  
**Mantenedor**: Sistema FCFM  
**Estado**: ✅ Producción
