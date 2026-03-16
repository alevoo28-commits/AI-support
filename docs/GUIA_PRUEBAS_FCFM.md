# 🧪 Guía de Pruebas - Sistema FCFM

## Estado Actual

✅ **Área creada:** Infraestructura  
✅ **Documento:** `Procedimientos_Informatica.docx` (52 fragmentos)  
✅ **Sistema:** Listo para consultas

---

## Consultas de Prueba Recomendadas

### Test 1: Solicitud de Soporte Técnico

**Consulta:**
```
¿Cuál es el procedimiento para solicitar soporte técnico o una incidencia?
```

**Resultado esperado:**
- Agente: 🏢 Infraestructura
- Respuesta: Pasos para completar formulario en https://serviciosfcfm.uchile.cl/incidencias/
- Fuente: "Solicitud de Incidencias vía Formulario Web"

---

### Test 2: Instalación de Software

**Consulta:**
```
¿Cómo se instala Windows en una computadora?
```

**Resultado esperado:**
- Agente: 🏢 Infraestructura
- Respuesta: Pasos de instalación del SO
- Fragmentos: Chunk 24-25 del documento

---

### Test 3: Configuración de Salas de Reuniones

**Consulta:**
```
¿Cómo solicito ayuda técnica para una sala de reuniones?
```

**Resultado esperado:**
- Agente: 🏢 Infraestructura
- Respuesta: Procedimiento de solicitud y asistencia
- Claves: formulario + 24 horas anticipación

---

### Test 4: Tarjeta Inteligente TUI

**Consulta:**
```
¿Cuál es el proceso para solicitar una tarjeta inteligente TUI?
```

**Resultado esperado:**
- Agente: 🏢 Infraestructura
- Respuesta: Procedimiento completo de solicitud, pago, creación
- Contacto: jororttiz@ing.uchile.cl

---

### Test 5: Mantención de Servidores

**Consulta:**
```
¿Con qué frecuencia se realizan respaldos de los servidores?
```

**Resultado esperado:**
- Agente: 🏢 Infraestructura
- Respuesta: Políticas de respaldo (diarios, semanales, mensuales)

---

## Cómo Hacer las Pruebas

### 1. Inicia Streamlit
```powershell
cd c:\Users\info\Documents\GitHub\AI-support
python -m streamlit run ai_support/ui/streamlit_app.py
```

### 2. Ve al Chat o área de consultas

En la UI, busca la sección de chat y escribe una de las consultas de arriba.

### 3. Observa:
- ✅ Agente seleccionado
- ✅ Documento consultado
- ✅ Fragmentos encontrados
- ✅ Respuesta generada

---

## Checklist de Validación

Después de cada consulta, verifica:

- [ ] Agente correcto: "🏢 Infraestructura"
- [ ] Base de conocimiento usada: ✅ KB used
- [ ] Documento encontrado: "Procedimientos_Informatica.docx"
- [ ] Respuesta coherente: contiene pasos o procedimiento
- [ ] Tiempo de respuesta: <10 segundos

---

## Si Algo Falla

### Agente incorrecto

**Síntoma:** Consulta sobre "instalación" va a otro agente  
**Causa:** Palabras clave no coinciden  
**Solución:** Ver `tools.py` en `AREAS_FCFM["infraestructura"]`

### Documento no encontrado

**Síntoma:** Respuesta dice "no tengo información"  
**Causa:** KB no indexó el documento  
**Solución:** 
1. Ve a "📚 Base de Conocimiento"
2. Selecciona "Infraestructura"
3. Verifica que el documento esté listado en "📋 Documentos"

### Respuesta muy genérica

**Síntoma:** No cita el documento, respuesta vaga  
**Causa:** Embeddings no encuentran fragmentos relevantes  
**Solución:** Intenta con palabras del documento (ej: "INFORMAT", "TUI", "Zentyal")

---

## Próximo Paso

Una vez validado el sistema con estos tests, puedes:

1. Crear las otras 14 áreas FCFM
2. Empezar a recopilar procedimientos reales
3. Subirlos gradualmente

¡Adelante! 🚀
