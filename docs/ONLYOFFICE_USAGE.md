# Cómo Usar OnlyOffice con Archivos Subidos

## 📋 Resumen

OnlyOffice necesita que los archivos estén accesibles mediante una URL pública o de red. Este documento explica cómo usar OnlyOffice con archivos que subes desde tu computadora.

## 🎯 Dos Opciones Disponibles

### Opción 1: Ver desde URL Pública (Más Simple)
Si ya tienes el archivo en internet:
1. Ve a "📄 Visor OnlyOffice"
2. Selecciona "🌐 Desde URL pública"
3. Pega la URL del archivo
4. Haz clic en "📂 Abrir en OnlyOffice"

### Opción 2: Subir Archivo (Requiere Configuración)
Para archivos en tu computadora:

#### Paso 1: Subir el Archivo
1. Ve a "📄 Visor OnlyOffice"
2. Selecciona "📤 Subir archivo"
3. Sube tu archivo Excel/Word/PowerPoint
4. El archivo se guardará en `temp_onlyoffice/`

#### Paso 2: Hacer el Archivo Accesible

**Método A: Servidor HTTP Simple (Recomendado)**

1. Abre una **nueva terminal PowerShell**
2. Ejecuta:
```powershell
cd c:\Users\info\Documents\GitHub\AI-support
.\.venv\Scripts\Activate.ps1
python serve_temp_files.py
```

3. Verás:
```
📁 Sirviendo archivos desde: temp_onlyoffice
🌐 Servidor iniciado en: http://localhost:8000
🌐 Acceso en red: http://172.17.87.11:8000
```

4. En la aplicación, usa la URL:
```
http://172.17.87.11:8000/nombre-del-archivo.xlsx
```

**Método B: Comando Manual**
```powershell
cd c:\Users\info\Documents\GitHub\AI-support\temp_onlyoffice
python -m http.server 8000
```

**Método C: Servidor Web Existente**
- Copia el archivo de `temp_onlyoffice/` a tu servidor web
- Usa la URL pública del servidor

#### Paso 3: Abrir en OnlyOffice
1. Pega la URL del archivo (ej: `http://172.17.87.11:8000/mi-archivo.xlsx`)
2. Haz clic en "📂 Abrir en OnlyOffice"
3. El documento se abrirá en el visor

## 🔧 Solución de Problemas

### OnlyOffice no carga el archivo
- ✅ Verifica que el servidor HTTP esté corriendo
- ✅ Confirma que la URL sea accesible (ábrela en tu navegador)
- ✅ Asegúrate de usar la IP de red: `172.17.87.11` (no `localhost`)

### Error CORS
- ✅ Usa el script `serve_temp_files.py` que ya incluye headers CORS
- ✅ Si usas otro servidor, agrega headers CORS

### No puedo acceder desde la red
- ✅ Verifica que el firewall permita el puerto 8000
- ✅ Usa la IP correcta de tu máquina

## 💡 Tips

- **Mantén el servidor corriendo** mientras uses OnlyOffice
- **Detén el servidor** con `Ctrl+C` cuando termines
- **Archivos temporales** se guardan en `temp_onlyoffice/` (puedes eliminarlos después)
- **Para producción**, considera usar un servidor web real o Nextcloud

## 🚀 Alternativa: Solo Análisis de Datos

Si solo necesitas analizar datos (no editar visualmente):
1. Ve a "📊 Excel con IA"
2. Sube tu archivo
3. Verás la vista de datos automáticamente
4. Pregunta lo que necesites en el chat
5. No necesitas OnlyOffice para esto

Esta opción es más simple y no requiere configuración adicional.
