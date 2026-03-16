# Prompts Externalizados en MySQL

## 📋 Resumen

Todos los prompts del sistema ahora se **almacenan en MySQL** en lugar de hardcodeados en Python. Esto permite:

✅ **Actualización sin redeploy**  
✅ **Versionado automático de cambios**  
✅ **Auditoría de quién cambió qué y cuándo**  
✅ **Fallback automático a prompts hardcodeados si MySQL no disponible**  
✅ **Caché local para rendimiento**  

---

## 🏗️ Arquitectura

### Antes (❌ Legacy)
```
Código → hardcoded en prompts.py → editar archivo → redeploy
```

### Ahora (✅ Nuevo)
```
UI/Script → MySQL → GestorPromptsMySQL → Python
                  ↓
            (Caché local)
```

**Fallback**: Si MySQL no disponible
```
Python → GestorPromptsMySQL → Prompts por defecto (en memoria)
```

---

## 🗄️ Schema MySQL

### Tabla: `system_prompts`

```sql
CREATE TABLE system_prompts (
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
);
```

### Estructura de datos

| Campo | Tipo | Propósito |
|-------|------|----------|
| `id` | INT | PK autoincremental |
| `nombre` | VARCHAR(100) | ID único del prompt (ej: "system_prompt_agente") |
| `contenido` | LONGTEXT | El prompt en sí (soporta {variables}) |
| `version` | INT | Número de versión (incrementa con cada actualización) |
| `descripcion` | VARCHAR(500) | Breve descripción del prompt |
| `activo` | BOOLEAN | Si está en uso (permite desactivar sin borrar) |
| `creado_en` | TIMESTAMP | Cuándo se creó |
| `actualizado_en` | TIMESTAMP | Cuándo se modificó por última vez |
| `actualizado_por` | VARCHAR(100) | Usuario/sistema que hizo el cambio |

---

## 🔌 Prompts disponibles

```python
# Sistema
obtener_prompt("system_prompt_agente", 
    nombre_agente="Tesorería",
    especialidad="procedimientos de tesorería")

# Colaboración
obtener_prompt("identificar_colaboradores", consulta="...")
obtener_prompt("evaluar_colaboracion", agente_externo="...", contexto="...")

# Enrutamiento
obtener_prompt("analizar_problema", consulta="...")
obtener_prompt("router_system")

# Memoria
obtener_prompt("memory_summarizer", tema="...", contenido="...")
obtener_prompt("collaboration_summary", contenido="...")
```

---

## 💻 Uso en Código

### 1. Obtener un prompt

```python
from ai_support.core.prompts_mysql import obtener_prompt

# Obtener y formatear
system_prompt = obtener_prompt(
    "system_prompt_agente",
    nombre_agente="💰 Agente Tesorería",
    especialidad="procedimientos de tesorería",
    kb_context="Contexto de KB...",
    faiss_context="Contexto FAISS...",
    memory_block="Contexto de memoria..."
)

# Usar en LLM
response = llm.stream(
    [SystemMessage(content=system_prompt)]
)
```

### 2. Actualizar un prompt

```python
from ai_support.core.prompts_mysql import inicializar_gestor

gestor = inicializar_gestor()

# Actualizar
exito = gestor.actualizar(
    nombre="system_prompt_agente",
    contenido="Nuevo contenido del prompt...",
    actualizado_por="admin@fcfm.cl",
    descripcion="Se mejoró la sección de colaboración"
)

if exito:
    print("✅ Prompt actualizado (versión +1)")
```

### 3. Listar prompts

```python
gestor = inicializar_gestor()
prompts = gestor.listar(solo_activos=True)

for nombre, info in prompts.items():
    print(f"{nombre}: v{info['version']} - {info['actualizado_por']}")
```

### 4. Obtener historial

```python
gestor = inicializar_gestor()
historial = gestor.historial("system_prompt_agente", limite=5)

for cambio in historial:
    print(f"v{cambio['version']}: {cambio['actualizado_por']} "
          f"({cambio['actualizado_en']})")
```

---

## 🔧 Configuración

### Variables de entorno

```bash
# Habilitar MySQL para prompts
AI_SUPPORT_MYSQL_ENABLE=true

# Conexión
AI_SUPPORT_MYSQL_HOST=localhost
AI_SUPPORT_MYSQL_USER=root
AI_SUPPORT_MYSQL_PASSWORD=tu_password
AI_SUPPORT_MYSQL_DATABASE=ai_support
AI_SUPPORT_MYSQL_PORT=3306
```

### En `.env`

```bash
# .env
AI_SUPPORT_MYSQL_ENABLE=true
AI_SUPPORT_MYSQL_HOST=127.0.0.1
AI_SUPPORT_MYSQL_USER=ai_support_user
AI_SUPPORT_MYSQL_PASSWORD=secure_password_here
AI_SUPPORT_MYSQL_DATABASE=ai_support_db
AI_SUPPORT_MYSQL_PORT=3306
```

### Fallback automático

Si MySQL no está disponible:
- ✅ Sistema sigue funcionando
- ✅ Usa prompts por defecto (en memoria)
- ⚠️ Los cambios se pierden al reiniciar
- 📝 Se registra en logs

---

## 📊 Flujo de Actualización

### Escenario 1: Cambiar prompt de tesorería

```
1. Admin hace cambio en UI (futuro)
   ↓
2. API POST /api/prompts/{nombre}
   ↓
3. GestorPromptsMySQL.actualizar()
   ↓
4. INSERT en MySQL (version + 1)
   ↓
5. Caché local invalidado
   ↓
6. Próxima consulta → usa versión nueva
   ↓
7. Auditoría guardada (usuario, timestamp, versión)
```

### Escenario 2: MySQL deshabilitado

```
1. GestorPromptsMySQL.obtener()
   ↓
2. Intenta MySQL → FALLA
   ↓
3. Fallback a PROMPTS_POR_DEFECTO
   ↓
4. Retorna prompt hardcodeado
   ↓
5. ⚠️ Log de warning
```

---

## 🧪 Testing

### Test básico

```python
from ai_support.core.prompts_mysql import obtener_prompt, inicializar_gestor

# Test 1: Obtener prompt
prompt = obtener_prompt("system_prompt_agente", 
                       nombre_agente="Test", 
                       especialidad="test")
assert prompt is not None
assert "Test" in prompt

# Test 2: Actualizar prompt
gestor = inicializar_gestor()
exito = gestor.actualizar("system_prompt_agente", "Nuevo contenido")
assert exito is True

# Test 3: Listar prompts
prompts = gestor.listar()
assert len(prompts) > 0
assert "system_prompt_agente" in prompts
```

---

## 🔄 Migración desde `prompts.py` → `prompts_mysql.py`

### Paso 1: Habilitar MySQL

```bash
# En .env
AI_SUPPORT_MYSQL_ENABLE=true
```

### Paso 2: Ejecutar inicialización

```python
# Automático en primera conexión:
from ai_support.core.prompts_mysql import inicializar_gestor

gestor = inicializar_gestor()
# → Crea tabla system_prompts
# → Migra PROMPTS_POR_DEFECTO
# → Listo para usar
```

### Paso 3: Reemplazar imports

**Antes:**
```python
from ai_support.core.prompts import get_system_prompt_agente

prompt = get_system_prompt_agente(
    nombre_agente="Tesorería",
    especialidad="..."
)
```

**Ahora:**
```python
from ai_support.core.prompts_mysql import obtener_prompt

prompt = obtener_prompt(
    "system_prompt_agente",
    nombre_agente="Tesorería",
    especialidad="..."
)
```

### Paso 4: Actualizar `specialized_agent.py`

```python
# specialized_agent.py (cambio en constructor)

from ai_support.core.prompts_mysql import obtener_prompt

class AgenteEspecializado:
    def __init__(self, area_id: str, nombre: str, especialidad: str):
        self.area_id = area_id
        self.nombre = nombre
        self.especialidad = especialidad
        
        # Obtener prompt dinámicamente de MySQL
        self.system_prompt_template = obtener_prompt(
            "system_prompt_agente",
            nombre_agente=nombre,
            especialidad=especialidad
        )
```

---

## 📈 Ventajas Comparativas

| Criterio | `prompts.py` (Legacy) | `prompts_mysql.py` (Nuevo) |
|----------|----------------------|--------------------------|
| **Editar prompt** | Editar .py → redeploy → 10-30min | UI/API → 1 segundo |
| **Auditoría** | ❌ No | ✅ usuario + timestamp + versión |
| **Versionado** | ❌ No | ✅ Automático (v1, v2, v3...) |
| **Desactivar** | Comentar línea → redeploy | Set `activo=FALSE` → instantáneo |
| **Rollback** | Recompilar versión anterior | SELECT... LIMIT 1 (historial) |
| **Testing** | Cambiar código → test | Cambiar DB → test |
| **A/B Testing** | Imposible sin complejidad | Fácil (crear variantes) |
| **Escalabilidad** | O(1) pero inflexible | O(n) pero dinámico |

---

## 🔐 Seguridad

### Consideraciones

1. **Acceso a BD**: Solo usuarios autenticados pueden actualizar
2. **Validación**: Los prompts se validan antes de guardar
3. **SQL Injection**: Usando prepared statements (`%s`)
4. **Auditoría**: Cada cambio registra usuario y timestamp
5. **Desactivación**: Nunca se borran (soft delete via `activo=FALSE`)

### Restricciones propuestas

```python
# Futuro: Agregar permisos
class PermisosPrompts:
    LEER = "prompts:read"          # Todos
    CREAR = "prompts:create"       # Admin
    EDITAR = "prompts:update"      # Admin
    DESACTIVAR = "prompts:delete"  # Admin
```

---

## 📚 Referencias

**Archivos relacionados:**
- `ai_support/core/prompts_mysql.py` - Nueva implementación
- `ai_support/core/prompts.py` - Legacy (mantener para retrocompatibilidad)
- `ai_support/agents/specialized_agent.py` - Usar nuevo gestor
- `ai_support/orchestrator/multi_orchestrator.py` - Usar nuevo gestor

**Próximos pasos:**
1. ✅ Crear `prompts_mysql.py`
2. ⏳ Crear UI para editar prompts (Streamlit)
3. ⏳ Crear API REST para prompts
4. ⏳ Migrar todos los imports a nuevo sistema
5. ⏳ Tests de integración

---

**Versión**: 2.0 (Externalizados)  
**Fecha**: 2026-03-16  
**Estado**: 🔄 En transición
