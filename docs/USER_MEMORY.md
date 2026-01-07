# Sistema de Memoria Persistente por Usuario

## 📋 Descripción

El sistema ahora incluye **memoria persistente individual por usuario**, permitiendo que cada persona tenga su propio historial de conversaciones que se guarda automáticamente y se restaura en futuras sesiones.

## ✨ Características

### 1. **Gestión de Usuarios**
- ✅ Inicio de sesión con usuarios existentes
- ✅ Creación de nuevos usuarios
- ✅ Cierre de sesión
- ✅ Eliminación de historial personal

### 2. **Persistencia Automática**
- 🔄 Guardado automático después de cada interacción
- 💾 Almacenamiento en formato JSON legible
- 📂 Archivos separados por usuario en `/user_memories/`
- 🔐 Nombres sanitizados para seguridad

### 3. **Restauración de Contexto**
- 🎯 Al iniciar sesión, se carga automáticamente el historial previo
- 🧠 El agente "recuerda" conversaciones anteriores del mismo usuario
- 📊 Estadísticas de uso por usuario

## 🚀 Uso

### Crear un Nuevo Usuario

1. En el sidebar, selecciona **"Nuevo usuario"**
2. Ingresa un nombre (solo letras, números, `-`, `_`, `.`)
3. Haz clic en **"✨ Crear usuario"**
4. ¡Listo! Tu sesión está activa

### Iniciar Sesión con Usuario Existente

1. En el sidebar, selecciona **"Usuario existente"**
2. Elige tu nombre de la lista desplegable
3. Haz clic en **"🔓 Iniciar sesión"**
4. Se cargará tu historial anterior

### Ver Estadísticas

- Expande **"📊 Estadísticas de Memoria"** en el sidebar
- Verás:
  - Mensajes totales
  - Tus mensajes vs respuestas del agente
  - Tamaño del archivo
  - Última actualización

### Borrar tu Historial

1. Con tu sesión activa, haz clic en **"🗑️ Borrar historial"**
2. Confirma la acción
3. Tu memoria se eliminará (puedes empezar de nuevo)

## 🔧 Implementación Técnica

### Componentes Principales

#### 1. `UserMemoryPersistence` (user_memory_persistence.py)
```python
# Gestión de persistencia
persistence = UserMemoryPersistence(storage_dir="./user_memories")

# Guardar memoria
persistence.save_user_memory(user_id, messages, metadata)

# Cargar memoria
memory_data = persistence.load_user_memory(user_id)

# Estadísticas
stats = persistence.get_user_stats(user_id)
```

#### 2. `SistemaMemoriaAvanzada` (memory.py)
- Ahora acepta parámetro `user_id` opcional
- Restaura automáticamente memoria al inicializar
- Guarda después de cada interacción

#### 3. `AgenteEspecializado` (specialized_agent.py)
- Recibe `user_id` en constructor
- Lo pasa a `SistemaMemoriaAvanzada`

#### 4. `OrquestadorMultiagente` (multi_orchestrator.py)
- Propaga `user_id` a todos los agentes
- Todos comparten la misma memoria de usuario

### Flujo de Datos

```
Usuario inicia sesión
    ↓
UserMemoryPersistence carga archivo JSON
    ↓
Mensajes restaurados en ConversationBufferMemory
    ↓
Usuario hace consulta
    ↓
Agente procesa con contexto completo (historial previo)
    ↓
Auto-guardado en archivo JSON
```

## 📁 Estructura de Archivos

```
user_memories/
├── README.md
├── .gitignore
├── juan.perez_memory.json
├── maria.gonzalez_memory.json
└── admin_memory.json
```

### Formato JSON de Memoria

```json
{
  "user_id": "juan.perez",
  "last_updated": "2026-01-07T14:30:00.123456",
  "version": "1.0",
  "messages": [
    {
      "type": "human",
      "data": {
        "content": "¿Cómo conecto una impresora?",
        "additional_kwargs": {}
      }
    },
    {
      "type": "ai",
      "data": {
        "content": "Para conectar una impresora...",
        "additional_kwargs": {}
      }
    }
  ],
  "metadata": {}
}
```

## 🔒 Seguridad y Privacidad

### Sanitización de Nombres
```python
# Solo se permiten: a-z, A-Z, 0-9, _, -, .
safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "_-.")
```

### Control de Acceso
- Cada usuario solo puede ver/modificar su propia memoria
- Los archivos están en `.gitignore` para no subirlos al repositorio
- No hay autenticación de contraseña (apropiado para entorno controlado)

### Privacidad
- ⚠️ Los archivos contienen todo el historial de conversaciones
- 🔐 No compartir archivos de memoria
- 🗑️ Los usuarios pueden eliminar su historial en cualquier momento

## 🎯 Beneficios

### Para el Usuario
1. **Continuidad**: El agente "recuerda" conversaciones previas
2. **Personalización**: Aprende de tus consultas específicas
3. **Eficiencia**: No repetir contexto en cada sesión
4. **Control**: Puedes borrar tu historial cuando quieras

### Para el Agente
1. **Mejor contexto**: Conoce el historial completo del usuario
2. **Respuestas relevantes**: Puede referenciar conversaciones anteriores
3. **Aprendizaje**: Se adapta a las necesidades del usuario
4. **Coherencia**: Mantiene el hilo de conversaciones largas

## 🔄 Migración de Sesiones Antiguas

Si ya tenías conversaciones antes de este update:
- Las sesiones antiguas **no se guardarán** automáticamente
- Debes crear un usuario e iniciar una nueva sesión
- El sistema anterior de memoria en sesión sigue funcionando (sin persistencia)

## 🧪 Testing

### Crear usuario de prueba
```bash
# Iniciar la app
streamlit run ai_support/ui/streamlit_app.py

# 1. Crear usuario "test"
# 2. Hacer varias consultas
# 3. Cerrar el navegador
# 4. Volver a abrir y loguearse como "test"
# 5. Verificar que el historial se restaura
```

### Verificar persistencia
```python
from ai_support.core.user_memory_persistence import UserMemoryPersistence

p = UserMemoryPersistence()
users = p.list_users()
print(f"Usuarios: {users}")

stats = p.get_user_stats("test")
print(f"Stats: {stats}")
```

## 📊 Estadísticas Disponibles

- `total_messages`: Total de mensajes (usuario + IA)
- `human_messages`: Mensajes del usuario
- `ai_messages`: Respuestas del agente
- `last_updated`: Fecha/hora de última actualización
- `file_size_bytes`: Tamaño del archivo en bytes
- `file_size_kb`: Tamaño del archivo en KB

## 🚧 Limitaciones Conocidas

1. **No hay autenticación de contraseña**: Cualquiera puede loguearse como cualquier usuario
   - Apropiado para entorno interno/controlado
   - Para producción pública, agregar autenticación

2. **Almacenamiento local**: Los archivos están en el servidor
   - No hay sincronización en la nube
   - Backups manuales recomendados

3. **Sin encriptación**: Los archivos JSON están en texto plano
   - Apropiado para datos no sensibles
   - Para información confidencial, agregar encriptación

## 🔮 Futuras Mejoras

- [ ] Autenticación con contraseña (opcional)
- [ ] Exportar/importar historial (JSON/CSV)
- [ ] Búsqueda en historial del usuario
- [ ] Límite de tamaño de memoria (auto-limpieza)
- [ ] Compartir conversaciones entre usuarios
- [ ] Estadísticas agregadas (admin)
- [ ] Encriptación de archivos (opcional)
- [ ] Sincronización con base de datos (opcional)

## 📝 Variables de Entorno

No hay variables nuevas específicas para este feature. El directorio de almacenamiento se puede cambiar en el código:

```python
# En streamlit_app.py
persistence = UserMemoryPersistence(storage_dir="./custom_path")
```

## 🆘 Troubleshooting

### El historial no se carga
- Verifica que el archivo existe en `/user_memories/`
- Comprueba que el nombre de usuario es correcto
- Revisa los logs de consola por errores

### Archivos muy grandes
- Usa "🗑️ Borrar historial" para empezar de nuevo
- Considera implementar límite de mensajes

### Permisos de archivo
- Asegura que la app tiene permisos de lectura/escritura en `/user_memories/`

## 📞 Soporte

Para reportar bugs o sugerir mejoras en la funcionalidad de memoria de usuario, crea un issue en el repositorio.
