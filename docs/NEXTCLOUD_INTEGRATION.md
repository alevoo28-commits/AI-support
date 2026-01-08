# Integración con Nextcloud

Este documento explica cómo configurar la integración con Nextcloud para cargar archivos Excel directamente desde tu servidor Nextcloud.

## Configuración

### 1. Variables de Entorno

Agrega las siguientes variables a tu archivo `.env`:

```env
# Configuración de Nextcloud
NEXTCLOUD_URL="https://tu-servidor-nextcloud.com"
NEXTCLOUD_USERNAME="tu_usuario"
NEXTCLOUD_PASSWORD="tu_contraseña_o_token"
NEXTCLOUD_WEBDAV_PATH="/remote.php/dav/files"
```

### 2. Obtener un Token de Aplicación (Recomendado)

Por seguridad, es mejor usar un **token de aplicación** en lugar de tu contraseña:

1. Inicia sesión en Nextcloud
2. Ve a **Configuración** → **Seguridad**
3. En la sección **Dispositivos y sesiones**, crea un nuevo token de aplicación
4. Copia el token generado
5. Usa este token en la variable `NEXTCLOUD_PASSWORD`

### 3. Configuración del Path WebDAV

Por defecto, Nextcloud usa `/remote.php/dav/files` como ruta WebDAV. Si tu servidor usa una configuración diferente, ajusta la variable `NEXTCLOUD_WEBDAV_PATH`.

## Uso

Una vez configurado:

1. Abre la aplicación
2. Ve a la pestaña **📊 Excel con IA**
3. Selecciona **☁️ Nextcloud** como origen del archivo
4. Navega por tus carpetas (o deja en blanco para la raíz)
5. Selecciona el archivo que deseas analizar
6. Haz clic en **📥 Cargar archivo seleccionado**

## Características

- ✅ Listar archivos Excel (.xlsx, .xls, .csv) desde Nextcloud
- ✅ Descargar archivos directamente a la aplicación
- ✅ Navegar por carpetas
- ✅ Ver tamaño y fecha de modificación
- ✅ Integración con OnlyOffice para edición en línea

## Ejemplo de Configuración

```env
NEXTCLOUD_URL="https://cloud.example.com"
NEXTCLOUD_USERNAME="john.doe"
NEXTCLOUD_PASSWORD="xxxxx-xxxxx-xxxxx-xxxxx-xxxxx"
NEXTCLOUD_WEBDAV_PATH="/remote.php/dav/files"
```

## Solución de Problemas

### No se encuentran archivos

- Verifica que las credenciales sean correctas
- Asegúrate de que la ruta de la carpeta sea correcta
- Verifica que tengas permisos de lectura en la carpeta

### Error de conexión

- Verifica que la URL de Nextcloud sea accesible
- Comprueba que no haya firewall bloqueando la conexión
- Asegúrate de usar HTTPS si tu servidor lo requiere

### Timeout

- Si tienes muchos archivos, aumenta el timeout en el código
- Considera especificar una carpeta más específica en lugar de la raíz

## Seguridad

- ⚠️ **Nunca compartas tu archivo `.env`**
- ✅ Usa tokens de aplicación en lugar de contraseñas
- ✅ Revoca tokens que ya no uses
- ✅ Usa HTTPS para todas las conexiones
