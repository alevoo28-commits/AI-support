# 🏛️ Arquitectura del Sistema Multi-Agente FCFM

## Introducción

El sistema ha sido **completamente rediseñado** para servir **FCFM (Facultad de Ciencias Físicas y Matemáticas)** y sus 15 áreas administrativas y académicas durante el decanato y vicedecanato.

### Cambio Fundamental
- **Antes**: Sistema de TI general (soporte a hardware, software, redes, impresoras, etc.)
- **Ahora**: Sistema de procedimientos institucionales (consultas sobre tareas, responsabilidades y procesos de cada área FCFM)

---

## 15 Áreas FCFM y sus Agentes

| Código | Área | Emoji | Responsabilidades |
|--------|------|-------|-------------------|
| `tesoreria` | Tesorería | 💰 | Presupuestos, gastos, viáticos, reembolsos |
| `arquitectura` | Arquitectura | 🏗️ | Diseño, proyectos editoriales, estructuras |
| `infraestructura` | Infraestructura | 🏢 | Mantenimiento de edificios, laboratorios, aulas |
| `proyectos` | Proyectos | 📋 | Becas, investigación, seguimiento de proyectos |
| `atencion_alumnos` | Atención de Alumnos | 👥 | Inscripción, tutorías, becas estudiantiles |
| `postgrado` | Postgrado y Educación Continua | 🎓 | Postgrados, diplomados, cursos, másters, doctorados |
| `sustentabilidad` | Sustentabilidad | 🌱 | Responsabilidad social, sostenibilidad ambiental |
| `comunicaciones` | Comunicaciones | 📢 | Prensa, publicidad, redes sociales, difusión |
| `vinculacion` | Vinculación Externa | 🌍 | Colaboración internacional, relaciones, alianzas |
| `rrhh` | Recursos Humanos | 👔 | Contratación, adquisiciones, administración personal |
| `contabilidad` | Contabilidad | 📊 | Registros contables, auditoría, balances |
| `direccion_economica` | Dirección Económica | 💵 | Análisis financiero, presupuestos generales |
| `direccion_academica` | Dirección Académica | 📚 | Currícula, planes de estudio, docencia |
| `diversidad` | Diversidad e Inclusión | 🌈 | Género, inclusión, equidad, minorías |
| `decanato` | Decanato y Vicedecanato | 🏛️ | Normas institucionales, administración general |

---

## Flujo de Funcionamiento

### 1. **Rotura Determinista por Palabras Clave**

El orquestador **NO usa LLM para enrutamiento**. Es 100% determinista:

```python
consulta = "¿Cuál es el procedimiento para solicitar un viático?"

# → Sistema detecta palabra: "viático"
# → Mapea a área: "tesoreria"
# → Llama agente: 💰 Agente Tesorería
```

**Ventajas:**
- Resultado predecible: misma consulta → mismo agente siempre
- Sin costo de LLM en enrutamiento
- Fácil de auditar y debugar

### 2. **Búsqueda en Base de Conocimiento de Procedimientos**

Una vez determinado el agente, el sistema **busca documen

tos PDF** en el área específica:

```
Usuario sube: "Procedimiento_Solicitud_Viáticos.pdf"
         ↓
Sistema lo indexa bajo "tesoreria"
         ↓
Consulta entra → Agente Tesorería busca en KB de tesorería
         ↓
Agente responde basándose en el PDF
```

### 3. **Colaboración Multi-Área (opcional)**

Si la consulta cruza múltiples dominios, colaboran múltiples agentes:

```
Consulta: "Necesito solicitar recurso para investigación 
           Y coordinar con tesorería Y asegurar sustentabilidad"

Detecta: 3 áreas → [proyectos, tesoreria, sustentabilidad]

Agente principal: 📋 Proyectos
Colaboradores: 💰 Tesorería, 🌱 Sustentabilidad

Orquestador combina respuestas
```

---

## Cómo Subir Procedimientos en PDF

### Paso 1: Acceder a la Sección Base de Conocimiento

En la UI Streamlit:
1. Ve al apartado **"📚 Base de Conocimiento - Procedimientos FCFM"**

### Paso 2: Crear o Selecciona un Área

- Si no existe la área, crea una (ej: "Tesorería")
- Si existe, haz clic para seleccionar

### Paso 3: Subir PDFs

En la columna derecha, bajo **"⬆️ Subir documentos"**:
1. Carga tu archivo PDF (ej: `Solicitud_Viáticos.pdf`)
2. El sistema lo parsea automáticamente
3. Lo trocea en fragmentos (chunks)
4. Lo indexa para búsqueda semántica

### Ejemplo de Nombres Recomendados

```
tesoreria/
  ├─ Solicitud de Viáticos Mediante Viaje.pdf
  ├─ Procedimiento Reembolso Gastos.pdf
  └─ Presupuesto Anual Decanato.pdf

proyectos/
  ├─ Ciclo de Proyectos de Investigación.pdf
  └─ Gestión de Becas y Fondos.pdf

atencion_alumnos/
  ├─ Procedimiento de Inscripción.pdf
  └─ Solicitud de Certificado de Alumno.pdf
```

---

## Arquitectura Técnica

### Componentes Clave

#### 1. **OrquestadorMultiagente** (`multi_orchestrator.py`)

Orquesta 15 agentes especializados y toma decisiones deterministas:

```python
# Inicializa 15 agentes FCFM
CLASS OrquestadorMultiagente:
    def __init__():
        self.agentes = {
            "tesoreria": AgenteEspecializado(...),
            "arquitectura": AgenteEspecializado(...),
            ...  # 15 en total
        }
    
    def determinar_agente_principal(consulta):
        # Análisis determinista por palabras clave
        # Devuelve: "tesoreria" | "arquitectura" | etc.
        return categoria_determinada
    
    def _evaluar_colaboracion(consulta):
        # Devuelve True si necesita múltiples agentes
        # False si solo necesita uno
        
    def _identificar_colaboradores(consulta, agente_principal):
        # Devuelve lista de máx. 2 agentes colaboradores
```

#### 2. **HerramientaSoporte** (`tools.py`)

Define mapeo de palabras clave → áreas FCFM:

```python
AREAS_FCFM = {
    "tesoreria": [
        "tesorería", "presupuesto", "gasto", "viático", 
        "reembolso", "factura", "pago", "finanzas"
    ],
    "arquitectura": [
        "arquitectura", "diseño", "plano", "estructura",
        "proyecto editorial", "infraestructura física"
    ],
    ...
}
```

#### 3. **KnowledgeBaseManager** (`knowledge_base.py`)

Gestiona PDFs por área:

```
knowledge_base/
├─ tesoreria_12345/
│   ├─ documents/
│   │   ├─ 1abc_Solicitud_Viáticos.pdf
│   │   └─ 2def_Reembolso.pdf
│   └─ index/
│       ├─ 1abc_chunks.json
│       └─ 2def_chunks.json
├─ proyectos_67890/
│   ├─ documents/
│   └─ index/
└─ ... (13 áreas más)
```

#### 4. **AgenteEspecializado** (`specialized_agent.py`)

Cada agente:
- Lee los PDFs de su área
- Busca en KB (Knowledge Base) por similaridad semántica
- Construye prompt system especializado
- Responde usando LLM
- Mantiene memoria de conversación

---

## Flujo Completo de Una Consulta

### Ejemplo: "Necesito autorización para un viaje y debo verificar los fondos"

```
1. Usuario escribe consulta
                ↓
2. OrquestadorMultiagente.procesar_consulta_compleja()
                ↓
3. determinar_agente_principal(consulta)
   - Detecta palabras: "viaje" → tesorería
   - Devuelve: "tesoreria"
                ↓
4. _evaluar_colaboracion(consulta)
   - Detecta: "viaje" (tesorería) ✓ + "fondos" (no es otra área)
   - Devuelve: False (no colaboración necesaria)
                ↓
5. Busca en Knowledge Base del área "tesorería"
   - Encuentra: "Solicitud de Viáticos.pdf"
   - Extrae 4 chunks más relevantes
                ↓
6. Agente Tesorería procesa:
   - System prompt: "Eres especialista en tesorería..."
   - Contexto KB: fragmentos del PDF
   - Consulta: "...viaje... fondos..."
                ↓
7. LLM genera respuesta basada en procedimiento
                ↓
8. Respuesta retorna al usuario con:
   - Agente responsable: 💰 Tesorería
   - PDFs consultados
   - Referencia a procedimiento específico
```

---

## Configuración Recomendada

### 1. **Crear las 15 Áreas FCFM**

En la UI, crea las 15 áreas con sus descripciones:

```
Tesorería
└─ "Procedimientos y tareas relacionados con presupuestos, 
    gastos, viáticos y reembolsos"

Arquitectura
└─ "Procedimientos de diseño, proyectos editoriales 
    e infraestructura física"

... (y así para cada área)
```

### 2. **Subir PDFs de Procedimientos**

Por cada área, sube 3-5 PDFs con:
- Procedimientos paso a paso
- Responsables
- Documentos requeridos
- Plazos
- Excepciones

### 3. **Probar el Sistema**

Usa la herramienta de búsqueda integrada para verificar 
que los PDFs se encuentran correctamente.

---

## Puntos Clave de Determinismo

✅ **El enrutamiento de agentes es 100% determinista**
- Misma consulta → Mismo agente siempre
- No hay aleatoriedad en la selección
- Se puede auditar exactamente por qué se eligió un agente

✅ **No hay LLM en enrutamiento**
- Solo análisis léxico de palabras clave
- Muy rápido, costo cercano a 0

✅ **Colaboración también determinista**
- Basada en reglas claras
- Máximo 2 colaboradores por consulta
- Reproducible

---

## Limitaciones Actuales y Mejoras Futuras

### Limitaciones
- ❌ Sistema solo responde si hay PDFs cargados en el área
- ❌ No puede "improvisar" respuestas
- ❌ Palabras clave deben coincidir exactamente (en minúsculas)

### Mejoras Futuras
- 📝 Agregar sinónimos a palabras clave (ej: "viático" = "viatico" = "gasto de viaje")
- 📊 Dashboard de analytics (qué agentes se usan más)
- 🔐 Control de acceso por rol (solo RRHH ve área RRHH)
- 💬 Chat de múltiples turnos con rol memory

---

## Contacto y Soporte

Para preguntas sobre:
- **Procedimientos**: Ver documentación del área
- **Estructura técnica**: Ver `ai_support/orchestrator/multi_orchestrator.py`
- **Base de conocimiento**: Ver `ai_support/core/knowledge_base.py`
