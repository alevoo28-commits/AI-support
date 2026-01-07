# Memorias de Usuario

Este directorio contiene los archivos de memoria persistente de cada usuario del sistema.

## 📁 Estructura

Cada usuario tiene su propio archivo JSON:
- `usuario_memory.json`: Memoria conversacional del usuario

## 🔒 Privacidad

- Los archivos de memoria contienen todo el historial de conversaciones del usuario
- Se recomienda no compartir estos archivos ni subirlos a control de versiones
- Cada archivo está asociado a un usuario específico

## 💾 Formato de Archivo

```json
{
  "user_id": "nombre.usuario",
  "last_updated": "2026-01-07T12:30:45",
  "version": "1.0",
  "messages": [
    {
      "type": "human",
      "data": {
        "content": "Pregunta del usuario",
        "additional_kwargs": {}
      }
    },
    {
      "type": "ai",
      "data": {
        "content": "Respuesta del agente",
        "additional_kwargs": {}
      }
    }
  ],
  "metadata": {}
}
```

## 🗑️ Limpieza

Los usuarios pueden borrar su propio historial desde la interfaz de Streamlit usando el botón "🗑️ Borrar historial".

## 🔐 Seguridad

- Los nombres de usuario se sanitizan para evitar path traversal
- Solo se permiten caracteres alfanuméricos, guiones, puntos y guiones bajos
