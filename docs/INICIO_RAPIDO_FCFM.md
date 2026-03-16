# ⚡ Guía de Inicio Rápido - Sistema FCFM

## 5 Pasos para Empezar

### 1. Inicia la Aplicación Streamlit

```powershell
cd c:\Users\info\Documents\GitHub\AI-support
python -m streamlit run ai_support/ui/streamlit_app.py
```

### 2. Crea las 15 Áreas FCFM

Ve a **"📚 Base de Conocimiento - Procedimientos FCFM"**

Haz clic en **"➕ Crear nueva área"** y crea estas 15:

```
1. Tesorería
2. Arquitectura
3. Infraestructura
4. Proyectos
5. Atención de Alumnos
6. Postgrado y Educación Continua
7. Sustentabilidad
8. Comunicaciones
9. Vinculación Externa
10. Recursos Humanos
11. Contabilidad
12. Dirección Económica
13. Dirección Académica
14. Diversidad e Inclusión
15. Decanato y Vicedecanato
```

### 3. Sube PDFs de Procedimientos

**Ejemplo para Tesorería:**
- Selecciona área "Tesorería"
- Sube archivos PDF:
  - `Procedimiento_Solicitud_Viáticos.pdf`
  - `Procedimiento_Reembolso_Gastos.pdf`
  - `Manual_Presupuesto.pdf`

El sistema:
- Lee automáticamente el PDF
- Lo trocea en fragmentos
- Lo indexa para búsqueda

### 4. Inicia Sesión

Haz clic en **"Iniciar sesión"** (Google OAuth)

### 5. Haz una Consulta

En el chat, escribe:

> "¿Cuál es el procedimiento para solicitar autorización de viático?"

**Sistema:**
1. Detecta palabra "viático" → enruta a **Tesorería**
2. Busca en PDFs del área Tesorería
3. Responde con el procedimiento encontrado

---

## Palabras Clave por Área

El sistema usa estas palabras para enrutar automáticamente:

| Área | Palabras Clave |
|------|---|
| **Tesorería** | tesorería, presupuesto, gasto, viático, reembolso, pago |
| **Arquitectura** | arquitectura, diseño, plano, estructura, editorial |
| **Infraestructura** | infraestructura, mantenimiento, edificio, laboratorio, aula |
| **Proyectos** | proyecto, beca, investigación, propuesta |
| **Atención Alumnos** | alumno, estudiante, inscripción, tutoría, calificación |
| **Postgrado** | postgrado, magister, doctorado, diplomado, continua |
| **Sustentabilidad** | sustentabilidad, ambiental, responsabilidad social |
| **Comunicaciones** | comunicación, prensa, publicidad, difusión |
| **Vinculación** | vinculación, relaciones internacionales, colaboración |
| **RRHH** | recurso humano, contratación, adquisición, compra |
| **Contabilidad** | contabilidad, balance, auditoria, registro contable |
| **Dir. Económica** | dirección económica, análisis financiero |
| **Dir. Académica** | dirección académica, currícula, plan estudio |
| **Diversidad** | diversidad, género, inclusión, equidad |
| **Decanato** | decanato, vicedecanato, norma facultad |

---

## Estructura de Carpetas

```
knowledge_base/
├─ areas.json                      # Registro de todas las áreas
├─ tesoreria_12345/
│   ├─ metadata.json
│   ├─ documents/
│   │   ├─ abc123_Solicitud_Viaticos.pdf
│   │   └─ def456_Reembolso.pdf
│   └─ index/
│       ├─ abc123_chunks.json
│       └─ def456_chunks.json
├─ proyectos_67890/
│   ├─ metadata.json
│   ├─ documents/
│   └─ index/
└─ ... (13 áreas más)
```

---

## Flujo de Consulta (Resumen Visual)

```
Usuario: "¿Cómo solicito un viático?"
                 ↓
    Orquestador (determinar_agente_principal)
                 ↓
    Detecta palabra: "viático"
                 ↓
        ├─ Busca en AREAS_FCFM
        ├─ Encuentra: "tesoreria"
        └─ → 💰 Agente Tesorería
                 ↓
    Busca en Knowledge Base
                 ↓
        ├─ Área: tesoreria
        ├─ Query: "solicitar viático"
        └─ Resultados: 3-4 fragmentos de PRs
                 ↓
    Agente genera respuesta
                 ↓
    Usuario recibe: paso a paso
```

---

## Testing Rápido

### Test 1: Enrutamiento Simple

```
Consulta: "¿Cómo solicito presupuesto?"
Esperado: Agente Tesorería
Resultado: ✅ 
```

### Test 2: Búsqueda en PDF

```
Consulta: "Necesito el formulario de viático"
Esperado: Sistema encuentra y cita el PDF
Resultado: ✅ (si el PDF fue subido)
```

### Test 3: Colaboración

```
Consulta: "Necesito presupuesto Y coordinar con recursos humanos"
Esperado: Agentes: Tesorería + RRHH colaboran
Resultado: ✅
```

---

## Troubleshooting

### ❌ El agente no responde correctamente

**Causa:**
- No hay PDF subido en el área
- Palabra clave no coincide exactamente

**Solución:**
1. Sube PDF de procedimiento
2. En chat, usa palabras del AREAS_FCFM mapping

### ❌ "Área no encontrada"

**Causa:**
- Consultaste un área que aún no existe

**Solución:**
1. Ve a "📚 Base de Conocimiento"
2. Crea la área con "➕ Crear nueva área"

### ❌ PDF se subió pero no aparece

**Causa:**
- Error en parseo del PDF

**Solución:**
1. Intenta con otra formato (DOCX en lugar de PDF)
2. Revisa los logs de terminal
3. Asegúrate que el PDF no está protegido

---

## Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `ai_support/orchestrator/multi_orchestrator.py` | Lógica de orquestación (enrutamiento determinista) |
| `ai_support/core/tools.py` | Mapping de palabras clave → áreas FCFM |
| `ai_support/core/knowledge_base.py` | Gestión de PDFs y búsqueda |
| `ai_support/agents/specialized_agent.py` | Agentes individuales |
| `ai_support/ui/streamlit_app.py` | Interfaz de usuario |

---

## Próximos Pasos

1. ✅ Crea las 15 áreas
2. ✅ Sube PDFs de procedimientos
3. ✅ Prueba consultas
4. 📋 Configura acceso por rol (futuro)
5. 📊 Revisa analíticos de uso (futuro)

---

## Soporte

Para más detalles técnicos, ver: [ARQUITECTURA_FCFM.md](ARQUITECTURA_FCFM.md)
