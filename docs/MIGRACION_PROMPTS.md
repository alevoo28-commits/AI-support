# Migración: Prompts.py → Prompts MySQL

## Estado después de la migración

### ✅ Archivos Creados

| Archivo | Propósito |
|---------|----------|
| `ai_support/core/prompts_mysql.py` | Gestor de prompts externalizados en MySQL |
| `ai_support/core/migrate_prompts.py` | Script de migración |
| `docs/PROMPTS_EXTERNALIZADOS.md` | Documentación completa |
| `docs/MIGRACION_PROMPTS.md` | Este archivo |

### ✅ Cambios en Código Existente

| Archivo | Cambio | Antes | Después |
|---------|--------|-------|---------|
| `specialized_agent.py` | Import | `from prompts import get_system_prompt_agente` | `from prompts_mysql import obtener_prompt` |
| `specialized_agent.py` | Llamada | `get_system_prompt_agente(...)` | `obtener_prompt("system_prompt_agente", ...)` |

### ⏳ Archivos Sin Cambios (Por Ahora)

- `ai_support/core/prompts.py` - Mantenido para retrocompatibilidad
- Otros usages de prompts - Se actualizarán gradualmente

---

## 🚀 Cómo activar la migración

### Paso 1: Configurar MySQL

Agregar en `.env`:

```bash
AI_SUPPORT_MYSQL_ENABLE=true
AI_SUPPORT_MYSQL_HOST=localhost
AI_SUPPORT_MYSQL_USER=root
AI_SUPPORT_MYSQL_PASSWORD=tu_password
AI_SUPPORT_MYSQL_DATABASE=ai_support
AI_SUPPORT_MYSQL_PORT=3306
```

### Paso 2: Ejecutar migración

```bash
# Activar venv
.\.venv\Scripts\Activate.ps1

# Ejecutar script
python -m ai_support.core.migrate_prompts
```

**Salida esperada:**
```
╔═══════════════════════════════════════════════════════════════╗
║  MIGRACIÓN: PROMPTS EXTERNALIZADOS EN MYSQL                  ║
╚═══════════════════════════════════════════════════════════════╝

✅ MySQL configurado correctamente
🔄 Inicializando GestorPromptsMySQL...
✅ Migración completada: 7 prompts en MySQL
   - system_prompt_agente: v1
   - identificar_colaboradores: v1
   - evaluar_colaboracion: v1
   - analizar_problema: v1
   - router_system: v1
   - memory_summarizer: v1
   - collaboration_summary: v1
```

### Paso 3: Verificar

```bash
python -c "
from ai_support.core.prompts_mysql import listar_prompts
prompts = listar_prompts()
print(f'✅ Prompts cargados: {len(prompts)}')
for nombre, info in prompts.items():
    print(f'  - {nombre}: v{info[\"version\"]}')"
```

### Paso 4: Testear en la app

```bash
python -m streamlit run ai_support/ui/streamlit_app.py
```

La app ahora obtendrá prompts de MySQL automáticamente.

---

## 🔄 Flujo de datos después de migración

```
┌─────────────────────┐
│  Usuario en Streamlit
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│ specialized_agent.py│
│  .procesar()        │
└──────────┬──────────┘
           │
           ↓
┌──────────────────────────┐
│ obtener_prompt()         │
│ (prompts_mysql.py)       │
└──────────┬───────────────┘
           │
           ├─→ ¿MySQL activado?
           │   ├─ SÍ: Query MySQL → Caché local
           │   └─ NO: Fallback a PROMPTS_POR_DEFECTO
           │
           ↓
┌──────────────────────┐
│ system_prompt        │
│ (formateado)         │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│ LLM (OpenAI/GitHub)  │
│ Streamingresponse    │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│ Usuario ve respuesta │
└──────────────────────┘
```

---

## 📊 Comparativa: Antes vs Después

### Antes (❌ Legacy - prompts.py)

```python
# Edición de prompts:
1. Abrir prompts.py
2. Buscar función get_system_prompt_agente()
3. Editar texto del prompt
4. Guardar y commitear a Git
5. Esperar a deployment
6. Ver cambio en producción (5-30 minutos después)

# Auditoría:
- ❌ ¿Quién cambió? Solo en Git blame
- ❌ ¿Cuándo? Solo en Git log
- ❌ ¿Qué cambió? Solo diffs en Git
```

### Ahora (✅ MySQL - prompts_mysql.py)

```python
# Edición de prompts:
1. Ejecutar actualización (API/Script/UI):
   gestor = inicializar_gestor()
   gestor.actualizar("system_prompt_agente", "Nuevo contenido")
2. ✅ Cambio instantáneo (sin redeploy)
3. Próxima consulta usa nueva versión

# Auditoría:
- ✅ ¿Quién cambió? Campo 'actualizado_por' en BD
- ✅ ¿Cuándo? Campo 'actualizado_en' (TIMESTAMP)
- ✅ ¿Qué cambió? Campo 'version' (autoincremental)
- ✅ ¿Historial? Tabla separada (futuro)
```

---

## 🧪 Testing después de migración

### Test 1: MySQL disponible

```bash
# Debe pasar:
python -c "
from ai_support.core.prompts_mysql import inicializar_gestor
gestor = inicializar_gestor()
assert gestor.conexion is not None
print('✅ MySQL conectado')
"
```

### Test 2: Obtener prompts

```bash
python -c "
from ai_support.core.prompts_mysql import obtener_prompt
prompt = obtener_prompt('system_prompt_agente',
    nombre_agente='Test',
    especialidad='testing',
    kb_context='',
    faiss_context='',
    memory_block='')
assert '$' not in prompt  # Sin variables sin reemplazar
assert 'Test' in prompt
print('✅ Prompts obtenidos correctamente')
"
```

### Test 3: Actualizar prompt

```bash
python -c "
from ai_support.core.prompts_mysql import inicializar_gestor
gestor = inicializar_gestor()
if gestor.conexion:
    exito = gestor.actualizar('router_system', 'Nuevo contenido test')
    assert exito
    print('✅ Actualización exitosa')
else:
    print('⚠️  MySQL no disponible (esperado si MySQL_ENABLE=false)')
"
```

### Test 4: App Streamlit

```bash
# Debe iniciar sin errores:
python -m streamlit run ai_support/ui/streamlit_app.py

# Verificar en logs:
# - ✅ "MySQL conectado: tabla 'system_prompts' lista"
# - ✅ No hay "Error al obtener prompt"
```

---

## 🎯 Rollback (en caso de problemas)

Si necesitas volver a `prompts.py`:

### Opción A: Desactivar MySQL

```bash
# En .env
AI_SUPPORT_MYSQL_ENABLE=false
```

La app seguirá funcionando con prompts por defecto.

### Opción B: Revertir código

```bash
git revert <commit_migración>
```

---

## 📈 Próximos pasos (futuro cercano)

1. **✅ Implementado**: Gestor MySQL
2. **✅ Implementado**: Migración automática
3. **✅ Implementado**: Fallback a prompts.py
4. **⏳ TODO**: UI Streamlit para editar prompts
5. **⏳ TODO**: API REST para actualizaciones
6. **⏳ TODO**: Historial de versiones (tabla separada)
7. **⏳ TODO**: Permisos de acceso
8. **⏳ TODO**: A/B testing de prompts

---

## 🔒 Consideraciones de Seguridad

### ✅ Implementado

- Prepared statements (SQL injection protection)
- Caché local (reduce queries a BD)
- Fallback automático
- Soft delete (no se borran prompts)

### ⏳ Futuro

- Autenticación para actualizaciones
- Permisos granulares (RBAC)
- Rate limiting en API de prompts
- Encriptación de prompts sensibles
- Backup automático

---

## 📞 Troubleshooting

### Error: "MySQL no disponible"

**Causa**: MySQL_ENABLE no configurado o credenciales incorrectas

**Solución**:
```bash
# Verificar .env
echo $env:AI_SUPPORT_MYSQL_ENABLE

# Debe mostrar "true"
```

### Error: "Tabla system_prompts no existe"

**Causa**: Primera ejecución sin ejecutar migración

**Solución**:
```bash
python -m ai_support.core.migrate_prompts
```

### Prompts vacíos o incompletos

**Causa**: Variables no formateadas correctamente

**Solución**:
```python
# Verificar que pasas todas las variables requeridas:
obtener_prompt(
    "system_prompt_agente",
    nombre_agente="...",      # Requerido
    especialidad="...",       # Requerido
    kb_context="...",         # Requerido (puede ser "")
    faiss_context="...",      # Requerido (puede ser "")
    memory_block="..."        # Requerido (puede ser "")
)
```

---

**Versión**: 1.0  
**Completado**: 2026-03-16  
**Estado**: 🟢 En transición a MySQL
